# PMKB Store — L08-H : archive `tar.gz` rootfs ↔ inventaire exporté

## Pourquoi ce lot

Les lots L08-E/F/G peuvent inventorier des bibliothèques depuis un répertoire déjà extrait, résoudre des alias **uniquement en mémoire**, puis vérifier la cohérence de l'inventaire. Aucun de ces contrôles ne prouve que l'export provient d'une image de partition Kobo authentifiée.

L08-H ajoute une **confrontation indépendante des octets d'une archive `tar.gz` rootfs** fournie par l'appelant avec les hachages des fichiers observés par L08-E. Le code ne lit pas de périphérique, n'ouvre pas de chemin hôte, ne monte ni n'extrait l'archive et n'exécute aucun programme ARM. C'est un jalon intermédiaire qui réduit l'écart entre archive source et export, **sans le combler pour une image ext4**.

## API et vérifications

`compare_tar_archive_to_snapshot(archive_bytes, snapshot, expected_archive_sha256=None)` :

- Valide le rapport L08-E via `verify_snapshot_evidence` (L08-G), avant de lire le TAR.
- Calcule le SHA-256 des octets compressés de l'archive en mémoire ; compare éventuellement à une empreinte fournie explicitement, **non authentifiée** par le module.
- Valide **un unique membre gzip** jusqu'au footer/CRC, avec un plafond de 896 Mio de données décompressées. Refuse les membres gzip concaténés et tout octet ajouté après le footer, afin qu'un second flux ne puisse pas être ignoré par la lecture du TAR. La vérification est en mémoire bornée mais nécessite un second passage pour inventorier le TAR.
- Parcourt l'archive en lecture séquentielle, sans `extract` ni `extractall`. Accepte les entrées racine `./` et les chemins de fichiers `./lib/...` habituels.
- Contrôle uniquement les fichiers `*.so*` immédiatement sous `lib/` et `usr/lib/`, comme le scanner L08-E. Les chemins qui sortent de l'archive et les noms ambigus sont refusés.
- Compare taille et SHA-256 des fichiers réguliers ; compare le texte des cibles des liens symboliques sans les suivre. Les liens matériels (`hardlink`) et fichiers spéciaux sous ces chemins sont refusés.
- Signale séparément les objets absents de l'archive, ceux absents de l'export, les noms comparés et les divergences.
- Impose des plafonds (archive compressée 128 Mio, au plus 40 000 entrées, 768 Mio de tailles déclarées, 512 bibliothèques, 16 Mio par bibliothèque, 96 Mio lus dans les bibliothèques). Une archive dépassant ces seuils est refusée ; **aucune augmentation automatique**.

## Verdicts et portée

| Verdict | Ce qu'il prouve effectivement |
| --- | --- |
| `scoped_content_match` | Pour les deux répertoires parcourus et les noms reconnus, octets des bibliothèques et cibles des liens déclarés concordent avec cette archive |
| `partial_scope` | Noms observés concordants, mais au moins un répertoire n'a pas été complètement inventorié par L08-E |
| `mismatch` | Au moins une divergence de contenu ou de présence dans le périmètre |

Même avec `scoped_content_match` et une empreinte compressée concordant avec la valeur de l'appelant, les sorties `archive_is_original_ext4_image`, `original_image_hash_verified`, `archive_origin_authenticated`, `export_matches_original_image`, `hardware_verified`, `runtime_compatible`, `launchable` restent **fausses**.

La vérification ne parcourt pas les autres emplacements Linux possibles, ne valide pas l'ensemble des métadonnées ext4, et ne résout pas les versions de symboles, la libc et l'interpréteur. L'archive TAR n'est pas une image ext4 : ce lot ne vérifie **ni P1**, **ni P2/recoveryfs**. L'empreinte calculée du TAR ne constitue pas une signature ni une preuve d'origine. L'inventaire L08-E n'a pas vocation à garantir un export sécurisé face à un attaquant modifiant simultanément son répertoire.

## Tests et prochaine frontière

`tests/test_store_rootfs_archive_reconcile.py` crée un TAR.GZ synthétique **en mémoire** et un répertoire rootfs artificiel **temporaire**. Les tests couvrent concordance, divergence des octets, noms absents, export partiel, alias, chemins hostiles, doublons, hardlinks et corruption. La CI GitHub doit valider Linux/Windows avant de conclure PASS.

**Aucune archive réelle n'est utilisée ici**. Pour une preuve image ext4 → export, il faudra introduire un lecteur/outil d'extraction ext4 en lecture seule, avec hash vérifié de l'image et journal de provenance de l'extraction, puis le qualifier sur source autorisée. Aucune image privée ni bibliothèque propriétaire ne doit être publiée sur GitHub.

Aucun téléchargement de toolchain, aucune écriture de carte, aucune modification FIRST BOOT/P1/P2/P3.
