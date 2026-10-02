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

Dans ce cas, le résultat contient `ok: false`, `partial: true` et `status: "incomplete"`. Si un autre contrôle détecte une anomalie, le statut devient `inconsistent` et le résumé humain affiche **RECOVERY INCOHÉRENT** : `--skip-md5` ne masque jamais une corruption.

## Les trois verdicts

| Verdict affiché | `status` | `ok` | `partial` | Signification |
|---|---|---|---|---|
| **RECOVERY COHÉRENT POUR LES CONTRÔLES EFFECTUÉS** | `ok` | `true` | `false` | tous les contrôles obligatoires ont réussi |
| **VÉRIFICATION INCOMPLÈTE** | `incomplete` | `false` | `true` | aucune incohérence trouvée, mais au moins un contrôle obligatoire n'a pas pu être effectué (fichier illisible, `--skip-md5`) |
| **RECOVERY INCOHÉRENT** | `inconsistent` | `false` | `false`, ou `true` si un contrôle n'a pas non plus pu être effectué | au moins une anomalie positive : fichier absent, MD5 incorrect, entrée de manifeste invalide, archive corrompue ou tronquée, U-Boot absent ou vide, `uImage` invalide |

Une **vérification incomplète n'est pas un recovery validé**. Elle signifie seulement qu'aucune corruption n'a été détectée parmi les fichiers effectivement lus.

Cas réel : sur un recovery monté sans les droits suffisants, `bin/antiword` n'était pas lisible. Le résultat est alors :

```text
VÉRIFICATION INCOMPLÈTE

1 fichier n'a pas pu être lu avec les droits actuels.
Aucune corruption n'a été détectée parmi les fichiers vérifiés.

Relancez avec les droits nécessaires pour obtenir un verdict complet.
```

Relancer avec `sudo` (ou en administrateur) est nécessaire pour obtenir un verdict `ok`.

En JSON, `inconsistencies[]` liste les anomalies détectées, `incomplete_checks[]` les contrôles non effectués et `unreadable_count` le nombre de fichiers illisibles. `checks_ok` conserve sa signification antérieure.

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
- `1` : vérification incomplète (`status: "incomplete"`, y compris `--skip-md5`) ou recovery incohérent (`status: "inconsistent"`) — consulter `status` pour les distinguer ;
- `2` : chemin recovery invalide ou inaccessible au point d'empêcher le contrôle (`status: "error"`).

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
- fichier illisible (`PermissionError` simulée, portable Linux/Windows) classé `incomplete` et jamais `ok` ;
- MD5 incorrect, fichier absent, archive corrompue et `uImage` invalide classés `inconsistent`, y compris avec un fichier illisible ;
- absence d'ouverture en écriture pendant la vérification.

La CI GitHub exécute les tests sous Linux et Windows sur plusieurs versions de Python. Aucun blob Kobo n'est inclus dans les tests.

## Sécurité

Le vérificateur ne répare rien et n'écrit rien. Il sert uniquement à décider si une copie de `recoveryfs` constitue une base suffisamment cohérente pour une reconstruction locale ultérieure.
