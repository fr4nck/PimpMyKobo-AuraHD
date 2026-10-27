# PMKB Store — L08-F : chaînes de liens SONAME sans traversée de fichiers

## Périmètre

Le scanner L08-E (PR #37) observe les enfants immédiats de `lib/` et `usr/lib/` dans un export rootfs en lecture seule. Il enregistre les liens symboliques sans les suivre. L08-F ajoute `rootfs_snapshot_aliases.py`, un **résolveur entièrement en mémoire** de ces liens à partir des observations déjà enregistrées.

Le module ne reçoit **aucun chemin hôte** et n'effectue **aucun accès au système de fichiers**. Il n'ouvre ni n'exécute de bibliothèque et n'installe pas de paquet. Les liens absolus (p. ex. `/lib/libc-2.19.so`) sont interprétés **dans l'espace de noms de l'export rootfs**, jamais comme des chemins absolus sur l'ordinateur hôte.

## États possibles

- `direct_arm_header_observed_only` : le nom demandé désigne directement un fichier dont le scanner a relevé un en-tête ELF partagé ARM EABI5 et un SHA-256.
- `alias_to_arm_header_observed_only` : un ou plusieurs liens observés aboutissent à un fichier de ce type.
- `alias_target_not_observed` : un chemin cible situé dans les dossiers parcourus n'apparaît pas dans les observations.
- `alias_target_not_scanned` : la cible sort des dossiers parcourus. **Inconnu, pas « absent ».**
- `unsafe_alias_target` : chemin qui s'échappe de la racine, composant invalide, NUL, UNC ou syntaxe Windows.
- `alias_cycle` et `alias_hop_limit` : chaîne cyclique ou trop longue (au plus 8 transitions).
- `ambiguous_export_name` : le même SONAME existe dans plusieurs dossiers observés.
- `nonmatching_library_header` : fichier observé mais aucun en-tête ELF ARM partagé qualifié.
- `not_observed_in_scanned_directories` : nom non observé dans le **périmètre partiel**.

Même un alias résolu signifie seulement « en-tête cohérent et octets hachés dans une fixture / export », et non « bibliothèque utilisable sur la Kobo ». Le SHA-256 porte sur les **octets effectivement lus dans l'export**, pas nécessairement sur l'original de la microSD.

Chaque réponse conserve `launchable=false`, `hardware_verified=false`, `runtime_compatible=false` et `source_hash_verified=false`. La provenance reste déclarative tant que l'original et la méthode d'export ne sont pas attestés. Le modèle ne valide pas les versions de symboles ELF, les instructions CPU, la libc, les relocations, les dépendances indirectes ni le chargeur dynamique.

## Preuves et suite

Les tests `tests/test_store_rootfs_snapshot_aliases.py` comprennent résolution directe, chaîne relative, lien absolu, cycle, limite de sauts, sortie de racine, cible hors périmètre, ambiguïté, faux rapport se déclarant vérifié et intégration au scanner avec répertoire temporaire. Sur des hôtes ne permettant pas la création de symlinks, le seul cas d'intégration matérielle au système de fichiers peut être `SKIP` ; les tests de résolution sur données pures restent actifs.

**Aucun snapshot de Kobo n'a été fourni à ce lot.** La CI de la PR constitue une qualification du code sur fixtures. Un lot distinct devra recevoir un export autorisé avec provenance vérifiable, sans publier de blobs propriétaires. L'installation de paquets `*.pmkb` reste désactivée par ces contrôles.

Ne modifier ni FIRST BOOT, ni P1/P2/P3, ni recoveryfs, ni la microSD physique.
