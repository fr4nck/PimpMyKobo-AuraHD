# `rebuild-rootfs` — contrat V1

Statut : spécification du prochain outil. Cette étape ne touche jamais une microSD ni un périphérique bloc.

## But

Reconstruire une image locale de `rootfs` à partir d'une sauvegarde PMKB et d'un `recoveryfs` déjà validés. L'outil produit uniquement un nouveau fichier image dans une destination explicitement choisie.

## Frontière de sécurité

`rebuild-rootfs` refuse toute entrée qui ressemble à un périphérique bloc (`/dev/...`, `\\.\PhysicalDriveN`). Il ne monte, démonte, formate ni n'écrit aucun support physique. Il n'appelle ni `dd`, ni `diskpart`, ni un futur outil de restauration.

Le fichier de sortie est créé sous un nom temporaire puis validé avant renommage. Un fichier existant n'est jamais écrasé implicitement.

## Entrées V1

Obligatoires :

- un `backup-manifest.json` PMKB déclaré complet et cohérent ;
- une copie locale de P2 `recoveryfs` référencée par ce manifeste ;
- une destination locale explicite pour la nouvelle image P1.

L'outil vérifie avant construction :

- version de schéma comprise ;
- identité E606C0 / Aura HD ;
- taille et SHA-256 de la copie P2 ;
- géométrie P1 enregistrée dans le manifeste ;
- présence des éléments recovery nécessaires ;
- validation du recovery selon les mêmes règles que `verify-recovery`.

Aucune donnée propriétaire n'est embarquée dans PMKB.

## Taille de la nouvelle P1

La géométrie MBR sauvegardée fait autorité. La taille de sortie V1 doit être exactement la taille P1 enregistrée dans le manifeste de sauvegarde.

La valeur observée sur l'exemplaire de développement (268 435 968 octets dans le MBR) est une donnée de référence, jamais une constante de validation.

## Construction

V1 reconstruit un système de fichiers ext compatible avec le recovery de la machine, puis extrait le contenu de `upgrade/fs.tgz` sans laisser l'archive choisir une destination hors de la racine reconstruite.

Les noms de membres absolus ou contenant `..`, les liens physiques sortant de l'archive, et tout membre qui serait extrait *à travers* un lien symbolique de l'archive sont refusés. Les **cibles** de liens symboliques absolues ou relatives avec `..` (par exemple `../../bin/busybox`) sont en revanche normales dans un rootfs : elles sont conservées telles quelles et ne sont jamais suivies pendant l'extraction.

### Paramètres ext4 (implémentation Linux actuelle)

- Les paramètres du système de fichiers sont **repris du superbloc de l'image recovery** (P2), écrite par les outils Kobo : liste exacte des fonctions ext4, taille de bloc et taille d'inode. Les drapeaux d'état (`needs_recovery`, `orphan_present`) ne sont pas recopiés.
- `mke2fs` est lancé avec une configuration vide (`MKE2FS_CONFIG`) et `-O none,<liste>`. Les réglages par défaut de l'hôte, par exemple `metadata_csum` ou `64bit`, ne peuvent donc pas s'ajouter : un kernel 2.6.35 ne saurait pas les monter.
- L'image est créée à la taille exacte de P1. Le système de fichiers occupe `taille_P1 // taille_de_bloc` blocs ; le reste (512 octets sur l'exemplaire étudié) est laissé à zéro.
- Après construction, les paramètres sont relus avec `dumpe2fs` et doivent être identiques à la référence ; le label doit être `rootfs`.
- Extraction et `mke2fs -d` tournent dans une seule session `fakeroot` : propriétaires numériques, modes (y compris setuid), liens et nœuds de périphérique sont préservés sans droits root.

Les détails dépendant d'outils système (`mkfs.ext4`, montage loop ou méthode sans montage) doivent être détectés explicitement. L'outil doit échouer proprement si les prérequis ne sont pas présents ; il ne doit jamais compenser en accédant à un disque physique.

## Validation de sortie

Une reconstruction n'est `complete` qu'après :

1. taille exacte de l'image ;
2. paramètres ext4 identiques à la référence recovery, label `rootfs` ;
3. `e2fsck -f -n` sans aucune anomalie (code 0) ;
4. relecture de l'image avec `debugfs`, en lecture seule et sans montage. Pour **chaque** membre de `fs.tgz` : présence, type, mode, UID/GID, cible des liens symboliques, majeur/mineur des nœuds de périphérique ;
5. contenu de **chaque** fichier régulier comparé par SHA-256 à `fs.tgz` ;
6. vérification par le `fs.md5sum` contenu dans `fs.tgz`, s'il existe ;
7. SHA-256 de l'image finale ;
8. écriture du manifeste de reconstruction `<sortie>.rebuild.json`, dont les champs `checks` reflètent les contrôles réellement effectués.

En cas d'écart, l'image reste sous son nom temporaire `.part`, n'est jamais renommée, et le résultat est `failed`.

Le SHA-256 historique `ADC8995C3F0754CBCF80ABA1540A69CF043DE9823800A359EC75167354B2993C` est une preuve de notre reconstruction manuelle, pas une valeur attendue par l'outil.

## Manifeste de reconstruction

Nom proposé : `rebuild-manifest.json`.

Champs V1 :

- `schema_version` ;
- `tool` ;
- `created_utc` ;
- `status`: `ok`, `incomplete` ou `failed` ;
- `backup_manifest_sha256` ;
- `source_fingerprint` repris sans modification du backup ;
- `device`: `E606C0` ;
- `rootfs_size` ;
- `rootfs_sha256` ;
- `recovery_sha256` ;
- `checks.filesystem` ;
- `checks.manifest` ;
- `checks.size` ;
- `warnings` ;
- `errors`.

Le chemin local du fichier n'est pas une identité persistante.

## Contrat avec un futur restore

Le futur outil de restauration ne devra pas faire confiance au seul SHA de l'image reconstruite. Il devra vérifier séparément l'identité du support cible contre le `source_fingerprint` de la sauvegarde.

`rebuild-rootfs` ne définit aucune règle autorisant une écriture physique : cette décision appartient exclusivement au futur `restore-rootfs`.

## Tests minimum avant implémentation utilisable

- rejet `/dev/sdX` et `\\.\PhysicalDriveN` ;
- manifeste absent, invalide, incomplet ou d'une version inconnue ;
- mauvais E606C0 ;
- P2 absente, taille fausse ou SHA faux ;
- archive recovery corrompue ou traversal ;
- collision sur la destination ;
- espace insuffisant ;
- interruption laissant uniquement un artefact temporaire non validé ;
- image de taille exacte ;
- contrôle filesystem et manifeste ;
- JSON stable ;
- chemins Unicode/espaces ;
- test mécanique interdisant toute ouverture en écriture d'une entrée ;
- CI Linux et Windows, les fonctions nécessitant un environnement ext4 réel étant séparées des tests unitaires portables.
