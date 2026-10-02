# Vérifier `recoveryfs`

**Français** | [English](verify-recovery-en.md)

`tools/verify-recovery.py` contrôle en lecture seule une partition `recoveryfs` déjà montée, ou une copie de son contenu.

L'outil ne monte pas lui-même la microSD et n'écrit jamais dans le recovery.

## Ce qu'il contrôle

Par défaut :

- présence et cohérence de `fs.md5sum` ;
- lecture complète de `upgrade/fs.tgz` et `upgrade/db.tgz` ;
- validation du flux gzip jusqu'au footer afin de vérifier CRC32, ISIZE et troncatures ;
- présence des deux blocs nuls de 512 octets qui marquent la fin correcte d'une archive tar ;
- lecture de toutes les entrées tar et de tout le contenu des fichiers réguliers ;
- refus d'une archive vide ou ne contenant aucun fichier régulier ;
- présence d'au moins un U-Boot `u-boot_mddr_512-E606C0-*.bin` non vide ;
- validation du kernel `uImage-E606C0` comme image U-Boot legacy : magic `0x27051956`, CRC d'en-tête, taille déclarée et CRC des données ;
- acceptation d'un éventuel remplissage nul après les données déclarées du `uImage`, mais refus de tout octet non nul dans cette zone ;
- refus des chemins critiques qui sortent de l'arborescence recovery via lien symbolique ou traversal.

Aucun fichier n'est extrait sur disque pendant ces contrôles.

Avec `--hash-files`, l'outil calcule aussi le SHA-256 des deux archives, de tous les candidats U-Boot E606C0 valides et du kernel.

## Pourquoi le marqueur de fin tar est vérifié

Un flux gzip peut être parfaitement valide alors qu'il contient un tar tronqué, par exemple si une production `tar | gzip` est interrompue mais que gzip termine proprement son flux. Une simple vérification gzip, ou une lecture tar qui s'arrête silencieusement, peut alors produire un faux positif.

Le vérificateur exige donc explicitement les **1024 octets nuls de fin tar** avant de déclarer l'archive cohérente.

## Préparation recommandée

Travailler de préférence sur une **copie de P2**, pas directement sur la carte originale.

Montage d'une image P2 déjà copiée :

```bash
sudo mkdir -p /mnt/aurahd-recovery
sudo mount -o loop,ro,noload AuraHD-p2-recovery.img /mnt/aurahd-recovery
```

`ro,noload` évite le rejeu du journal ext4 de l'image montée.

## Utilisation

```bash
sudo python3 ./tools/verify-recovery.py /mnt/aurahd-recovery --hash-files
```

Sortie JSON :

```bash
sudo python3 ./tools/verify-recovery.py /mnt/aurahd-recovery --json
```

## `--skip-md5` n'est pas un verdict vert

Le contrôle du manifeste peut être ignoré pour du diagnostic :

```bash
sudo python3 ./tools/verify-recovery.py /mnt/aurahd-recovery --skip-md5
```

Dans ce cas, le résultat contient `partial: true` et `ok: false`. Si un autre contrôle échoue également, le résumé humain reste **INCOMPLET OU INCOHÉRENT** et ne masque pas cette erreur derrière le statut partiel.

## Variantes U-Boot

Le vérificateur accepte les fichiers correspondant au motif :

```text
u-boot_mddr_512-E606C0-*.bin
```

Un fichier vide est refusé. Si un seul candidat valide est présent, il peut être retenu comme candidat unique. Si plusieurs variantes sont présentes, aucune n'est sélectionnée automatiquement : le résultat le signale afin qu'un futur outil de restauration choisisse à partir du HWCONFIG / type de RAM plutôt que d'une simple position alphabétique.

## Manifestes `fs.md5sum`

Les chemins absolus, `../` et liens symboliques qui sortent du recovery sont refusés.

Les noms de fichiers échappés au format GNU `md5sum` sont décodés uniquement lorsque la ligne est réellement préfixée par `\`. Les séquences `\n`, `\r` et `\\` sont prises en charge.

L'outil distingue fichier absent, fichier illisible, empreinte incorrecte et entrée de manifeste invalide.

## Codes de sortie

- `0` : tous les contrôles obligatoires sont conformes ;
- `1` : recovery incomplet/incohérent, ou vérification volontairement partielle avec `--skip-md5` ;
- `2` : chemin recovery invalide ou inaccessible au point d'empêcher le contrôle.

## Tests synthétiques

La suite de tests couvre notamment :

- gzip tronqué et CRC corrompu ;
- gzip valide contenant un tar tronqué ;
- archive ne contenant que des répertoires ;
- données parasites ;
- traversal et lien symbolique sortant ;
- U-Boot vide, variante RAM et variantes multiples ;
- magic/CRC `uImage` invalides ;
- `uImage` complété par des zéros ;
- manifeste GNU échappé ;
- `--skip-md5` partiel avec et sans autre erreur ;
- absence d'ouverture en écriture pendant la vérification.

La CI GitHub exécute les tests sous Linux et Windows sur plusieurs versions de Python. Aucun blob Kobo n'est inclus dans les tests.

## Sécurité

Le vérificateur ne répare rien et n'écrit rien. Il sert uniquement à décider si une copie de `recoveryfs` constitue une base suffisamment cohérente pour une reconstruction locale ultérieure.
