# Première restauration P1 sous Linux Live USB

`tools/restore-p1-linux.py` est un exécuteur distinct de l'import legacy et du simulateur. Son mode par défaut vérifie uniquement les fichiers locaux et n'ouvre aucun périphérique. Il ne promeut jamais l'import legacy en sauvegarde native. Une écriture nécessite une autorisation explicite séparée, liée au SHA-256 du plan examiné.

## Environnement et données

Utiliser Linux Live démarré directement sur le PC, 64 bits x86_64 ou aarch64, Python 3.10 ou plus et e2fsprogs (`e2fsck`). WSL, Windows, les conteneurs reconnus et un espace de montage distinct de celui de PID 1 sont refusés pour l'accès physique. `--ack-linux-live` déclare l'environnement Live ; le programme ne prouve pas l'origine du démarrage.

Les huit fichiers d'entrée sont le plan préparé, le manifeste legacy, le rapport de reconstruction, P1 reconstruite, la sauvegarde complète, son rapport d'acquisition, la simulation complète et son rapport. Les fichiers pré-P1/P2 référencés par le manifeste doivent aussi être accessibles. **Conserver la hiérarchie relative des fichiers du manifeste en les transférant** : modifier ses chemins changerait son empreinte et invaliderait les rapports liés. Les fichiers complets nécessitent un support acceptant des fichiers de plus de 4 Go.

Le journal et ses deux fichiers voisins doivent être placés sur un support persistant distinct de la carte Kobo, avec au moins deux fois la taille de P1 plus 4 Mio libres. Sont acceptés ext2/3/4, XFS, Btrfs, FAT, exFAT et NTFS3 si leur synchronisation réussit. RAM Live, overlay, FUSE (dont ntfs-3g) et réseau sont refusés. Aucun fichier existant n'est écrasé. Le programme n'effectue aucun montage, démontage, changement de protection, partitionnement ou réparation automatique.

## Vérifications sans écriture physique

Depuis la racine du dépôt, adapter les chemins de fichiers locaux :

```sh
python3 tools/restore-p1-linux.py \
  plan.json legacy.json rebuilt.img.rebuild.json rebuilt.img \
  full-card.img full-card.img.backup.json simulated.img simulated.img.simulation.json \
  /media/persistent/restore.journal.jsonl
```

Ce mode recrée temporairement le plan depuis les fichiers, compare exactement son contenu, puis supprime le plan temporaire. Il ne crée pas de journal et n'ouvre pas la carte, même si `--device` est fourni seul. Les données d'entrée restent en lecture seule.

Pour une comparaison physique **en lecture seule**, après identification manuelle de la carte entière et démontage manuel de ses partitions, ajouter `--check-device --device /dev/disk/by-id/IDENTIFIANT_DE_LA_CARTE --ack-linux-live` et exécuter comme root. L'identifiant ci-dessus est un emplacement réservé, jamais un disque choisi automatiquement. Le programme résout le chemin, vérifie sysfs, prend un descripteur exclusif `O_RDONLY|O_EXCL` et compare tous les octets à la sauvegarde. Aucun journal ni staging n'est créé dans ce mode.

Le mode d'écriture utilise `--write-p1` et `--authorize-plan-sha256` avec l'empreinte exacte du plan approuvé, ainsi que la cible et la déclaration Live. **Ces options ne constituent pas une autorisation donnée dans une conversation. Ne pas lancer ce mode avant autorisation explicite de restauration.** Il n'existe ni cible par défaut, ni détection automatique, ni option permettant d'ignorer un contrôle échoué.

## Contrôles et écriture bornée

1. Revalider les preuves locales, la sauvegarde et les régions conservées de la simulation. Refuser tout plan modifié, rapport incohérent ou sortie déjà présente.
2. Copier P1 reconstruite dans un nouveau fichier `.replacement.img`, synchroniser et relire son empreinte. Exécuter `e2fsck -f -n` sur ce fichier uniquement ; toute sortie non nulle est un refus. Vérifier à nouveau l'empreinte.
3. Synchroniser le journal et son répertoire. La cible doit être une carte entière amovible dans un lecteur USB, sans partitions montées, swap actif ni holders LVM/RAID/device-mapper. Les secteurs logiques doivent être de 512 octets.
4. Ouvrir la cible `O_RDWR|O_EXCL|O_NOFOLLOW`, vérifier le type et le numéro du descripteur, puis conserver **ce même descripteur** jusqu'à la fin. Vérifier la longueur par ioctl et comparer l'empreinte de la carte complète à celle de la sauvegarde.
5. Sauver P1 actuelle dans `.original-p1.img`, synchroniser puis relire ce fichier. Son empreinte doit correspondre à P1 dans la sauvegarde complète. Recontrôler la cible complète immédiatement avant l'intention d'écriture.
6. Synchroniser l'événement `writing_p1` avant le premier octet écrit. Écrire exactement la taille de P1 à son offset validé ; prendre en charge les écritures courtes sans sortir de ces bornes.
7. Synchroniser le périphérique, vider son cache de blocs (`BLKFLSBUF`), recontrôler son identité/capacité puis relire P1 et **l'intégralité des zones hors P1**. Comparer les empreintes avant de publier l'événement `verified`.

L'ouverture exclusive refuse les utilisations connues du noyau. Elle ne fournit pas une isolation contre tout autre programme privilégié effectuant des accès bruts : ne pas utiliser d'autres outils de disque pendant l'opération. Une correspondance intégrale identifie le contenu attendu, pas un numéro matériel unique. Les rapports ne sont pas signés ; leur cohérence est vérifiée, leur authenticité n'est pas prouvée.

## Arrêt et retour arrière

Toute interruption après `writing_p1` peut laisser P1 partiellement restaurée. Les artefacts et le journal sont conservés, aucun rollback ou retry automatique n'est lancé. Garder la carte hors de la Kobo, conserver la sauvegarde complète et `.original-p1.img`, puis faire examiner le journal avant toute nouvelle écriture. Un nouveau lancement refuse les fichiers existants et une cible qui diffère de la sauvegarde initiale. Le retour arrière nécessite une procédure distincte et une nouvelle autorisation ; il n'est pas implémenté comme mode automatique ici.

`ok` certifie la relecture de P1 et la conservation de tout ce qui l'entoure. Il ne certifie pas le démarrage, la santé de P3 ou la compatibilité matérielle du noyau reconstruit. `input_provenance` et `physical_restore_eligible=false` décrivent toujours les limites du contrat legacy : l'intention explicite de l'opérateur et la nouvelle comparaison physique sont enregistrées séparément.

## Validation

Les tests utilisent uniquement des fichiers synthétiques, des métadonnées sysfs/proc temporaires et des descripteurs simulés. Un test Linux vérifie aussi un véritable ext4 synthétique avec `e2fsck` sans modification. Aucune carte réelle n'est écrite par les tests ; le verrouillage et les ioctl sur matériel réel restent à vérifier lors d'une opération autorisée.

Références : [open(2), O_EXCL sur périphérique bloc](https://www.man7.org/linux/man-pages/man2/open.2.html), [interfaces ioctl Linux](https://github.com/torvalds/linux/blob/master/include/uapi/linux/fs.h), [e2fsck(8), mode -n](https://man7.org/linux/man-pages/man8/e2fsck.8.html).
