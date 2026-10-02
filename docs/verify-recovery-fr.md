# Vérifier `recoveryfs`

**Français** | [English](verify-recovery-en.md)

`tools/verify-recovery.py` contrôle en lecture seule une partition `recoveryfs` déjà montée, ou une copie de son contenu.

L'outil ne monte pas lui-même la microSD et n'écrit jamais dans le recovery.

## Ce qu'il contrôle

Par défaut :

- présence et cohérence de `fs.md5sum` ;
- lecture complète de `upgrade/fs.tgz` et `upgrade/db.tgz` ;
- validation de la structure tar ;
- consommation complète du flux gzip afin de vérifier CRC32, taille de fin et troncatures ;
- rejet des données non nulles trouvées après la fin logique du tar ;
- présence d'au moins un U-Boot `u-boot_mddr_512-E606C0-*.bin` non vide ;
- validation du kernel `uImage-E606C0` comme image U-Boot legacy : magic `0x27051956`, CRC d'en-tête, taille déclarée et CRC des données ;
- refus des chemins critiques qui sortent de l'arborescence recovery via lien symbolique ou traversal.

Aucun fichier n'est extrait sur disque pendant ces contrôles.

Avec `--hash-files`, l'outil calcule également le SHA-256 des archives et des artefacts E606C0 sélectionnés.

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

Dans ce cas, le résultat contient `partial: true`, `ok: false` et le programme ne renvoie pas un succès global. Un futur outil de reconstruction ne doit donc jamais interpréter ce mode comme un recovery validé.

## Variantes U-Boot

Le type de RAM est encodé dans le nom du fichier U-Boot. Le vérificateur n'impose plus uniquement `K4X2G323PC` : il accepte les variantes correspondant au motif :

```text
u-boot_mddr_512-E606C0-*.bin
```

Il conserve le nom réellement trouvé dans le résultat JSON.

## Manifestes `fs.md5sum`

Les chemins absolus, `../` et liens symboliques qui sortent du recovery sont refusés.

Les noms de fichiers échappés au format GNU `md5sum` sont décodés uniquement lorsque la ligne est réellement préfixée par `\`, afin d'éviter de transformer des séquences littérales par erreur.

L'outil distingue fichier absent, fichier illisible, empreinte incorrecte et entrée de manifeste invalide.

## Codes de sortie

- `0` : tous les contrôles obligatoires sont conformes ;
- `1` : recovery incomplet/incohérent, ou vérification volontairement partielle avec `--skip-md5` ;
- `2` : chemin recovery invalide ou inaccessible au point d'empêcher le contrôle.

## Tests synthétiques

Les tests du dépôt couvrent notamment :

- archive tronquée ;
- CRC gzip corrompu ;
- données parasites après l'archive ;
- traversal et lien symbolique sortant ;
- U-Boot vide ;
- variante de nom U-Boot ;
- magic et CRC `uImage` invalides ;
- manifeste échappé ;
- mode `--skip-md5` partiel.

Ils utilisent uniquement des fichiers synthétiques et aucun blob Kobo.

## Sécurité

Le vérificateur ne répare rien et n'écrit rien. Il sert uniquement à décider si la copie de `recoveryfs` est suffisamment cohérente pour devenir une source de reconstruction locale.
