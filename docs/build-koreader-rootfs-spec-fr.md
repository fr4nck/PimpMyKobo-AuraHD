# `build-koreader-rootfs` — contrat V1

[English](build-koreader-rootfs-spec-en.md) | **Français**

Statut : assemblage local et validation hors ligne implémentés. La construction ext4 `--build`, Linux uniquement, dispose de tests unitaires conditionnés à un hôte Linux/WSL2 natif avec e2fsprogs+fakeroot, mais n'a pas encore été exercée avec une vraie version de KOReader ni de vrais composants runtime d'origine Kobo. Aucune écriture physique n'existe dans cet outil.

## But

Assembler, puis éventuellement construire, une image P1 locale expérimentale qui démarre directement dans KOReader sur l'Aura HD E606C0, sans Nickel dans le chemin de démarrage normal :

`boot Netronix -> noyau -> ce rootfs -> KOReader`

Ceci est distinct de [`rebuild-rootfs`](rebuild-rootfs-spec-fr.md), qui reconstruit le rootfs *d'origine* Kobo à partir d'une sauvegarde vérifiée. `build-koreader-rootfs` ne lit jamais `fs.tgz` ni aucun manifeste de sauvegarde ; il se contente de fusionner des entrées locales explicitement fournies.

## Entrées (toutes locales ; jamais un périphérique)

1. `koreader_dir` — une version de KOReader Kobo extraite localement. Son contenu est placé sous `/opt/koreader` dans l'arbre assemblé (fournir donc le répertoire qui contient directement `reader.lua`, `luajit`, `libs/`, etc.).
2. `runtime_dir` — un répertoire local de composants runtime supplémentaires fusionnés à la racine du rootfs (par exemple un binaire BusyBox et des bibliothèques partagées extraits de la propre sauvegarde de l'utilisateur). **Ce répertoire n'est jamais committé dans le dépôt.** Sa provenance, sa licence et sa redistribuabilité restent de la responsabilité de l'opérateur ; voir [les notes de libération hors ligne](offline-liberation-fr.md).
3. La surcouche `experimental/offline-rootfs` du dépôt (init, inittab, marqueur de sonde matérielle, garde hors-ligne/réseau, lanceur KOReader) est fusionnée automatiquement ; elle n'est pas un argument de la ligne de commande.
4. Pour `--build` uniquement : `--reference-recovery` (une image P2 `recoveryfs` locale fournissant la géométrie ext4 de référence, exactement comme pour `rebuild-rootfs`) et `--size` (la taille exacte de sortie P1, en octets).

## Frontière de sécurité

`build-koreader-rootfs` refuse toute entrée ou sortie qui ressemble à un périphérique bloc (`/dev/...`, `\\.\PhysicalDriveN`). Il ne monte, ne formate et n'écrit jamais de support physique. L'image de sortie est créée sous un nom temporaire `.part` puis renommée seulement après que tous les contrôles ci-dessous ont réussi ; un fichier de sortie ou un manifeste de construction déjà existant n'est jamais écrasé implicitement.

## Assemblage (`plan_rootfs`, multiplateforme, lecture seule sur ses entrées)

L'assemblage fusionne trois sources en un seul manifeste, indexé par chemin relatif au rootfs, sans nécessiter d'outil réservé à Linux :

1. la surcouche (mode forcé à `0755`, car le bit exécutable suivi par Git n'est pas fiable sur tous les checkouts) ;
2. les répertoires de montage de base (`proc`, `sys`, `dev`, `dev/input`, `dev/pts`, `run`, `tmp`, `mnt`, `mnt/onboard`, `opt`, `opt/koreader`) pour que l'arbre soit complet même avec une entrée KOReader/runtime partielle ;
3. `koreader_dir`, placé sous `opt/koreader` ;
4. `runtime_dir`, placé à la racine.

Des répertoires peuvent être apportés par plusieurs sources à la fois (par exemple `etc/` depuis la surcouche et depuis `runtime_dir`) et sont alors fusionnés. Un fichier ou un lien symbolique ne peut jamais remplacer ce qu'une source précédente a déjà placé ; une telle collision fait échouer tout l'assemblage sans sortie partielle. Les liens symboliques sont enregistrés avec leur cible brute et ne sont jamais suivis ni réécrits, dans le même esprit que le traitement des liens d'archive par `rebuild-rootfs` : des cibles absolues ou en `..` sont normales dans un rootfs (applets BusyBox, liens `.so` versionnés) et sont conservées telles quelles.

Points d'entrée requis, vérifiés après assemblage : `etc/init.d/rcS`, `etc/inittab`, `usr/bin/pmkb-check-offline`, `usr/bin/pmkb-check-onboard`, `usr/bin/pmkb-reader`, `bin/kobo_config.sh`, `opt/koreader/reader.lua`, `opt/koreader/luajit`.

### Recherche de références à Nickel

Une heuristique bornée, à effort raisonnable, signale ce qui ressemble à une dépendance involontaire au runtime Nickel/Kobo :

- tout chemin du manifeste dont le nom correspond à `nickel`, `hindenburg` ou `kobo ereader.conf` (insensible à la casse) ;
- tout fichier régulier de 2 Mio ou moins, provenant uniquement de `koreader_dir` ou `runtime_dir`, dont le contenu contient `Nickel`, `Hindenburg`, `nickel_conf`, `/usr/local/Kobo` ou `KoboRoot.tgz`.

La surcouche propre au dépôt est exclue de l'analyse de contenu (mais pas de l'analyse par nom de chemin) : ses sources sont déjà relues dans ce dépôt, et ses commentaires peuvent légitimement *décrire* le contournement de Nickel sans en dépendre. Une alerte signifie « à examiner avant de faire confiance à l'image », pas une preuve automatique de problème ; l'absence d'alerte n'est pas non plus une preuve d'absence. Chaque alerte est rapportée dans `nickel_scan`.

## Construction (`--build`, Linux uniquement)

Réutilise les fonctions ext4 de `rebuild-rootfs` plutôt que de les réimplémenter :

- la liste de fonctionnalités ext4, la taille de bloc et la taille d'inode proviennent du superbloc de `--reference-recovery` (`dumpe2fs -h`), exactement comme pour `rebuild-rootfs` ; `mke2fs` s'exécute avec un `MKE2FS_CONFIG` vide et `-O none,<liste>` pour qu'aucun défaut de l'hôte (`metadata_csum`, `64bit`) ne puisse s'ajouter ;
- l'image est créée exactement à la taille `--size` demandée ; le système de fichiers utilise `size // block_size` blocs, le reste demeure à zéro ;
- l'arbre assemblé est matérialisé dans un répertoire temporaire, passé en `chown -R 0:0`, puis fourni à `mke2fs -d` dans une seule session `fakeroot` (la fidélité des propriétaires/modes du contenu de `koreader_dir`/`runtime_dir` dépend donc des permissions POSIX déjà correctes sur leur système de fichiers *source* — ceci ne fonctionne de manière fiable que si ces entrées ont été extraites sous Linux/WSL2, pas assemblées depuis un essai à blanc côté Windows) ;
- la propriété par fichier au-delà d'un `root:root` uniforme n'est pas encore prise en charge ; ceci est noté dans le rapport sous `owner_policy` et devra être revu si un futur composant exige un propriétaire différent de root.

## Validation de sortie

Une construction est `experimental` (jamais `complete`/qualifiée au sens matériel) seulement après :

1. taille d'image exacte ;
2. paramètres ext4 identiques à la référence de récupération, label `rootfs` ;
3. `e2fsck -f -n` sans aucun problème (code de sortie 0) ;
4. une relecture en lecture seule, sans montage, de l'image avec `debugfs` pour chaque entrée du manifeste : présence, type, mode (liens symboliques exclus) et, pour les liens, cible du lien rapide ;
5. le contenu de chaque fichier régulier comparé par SHA-256 à la valeur calculée lors de l'assemblage ;
6. un rapport `<sortie>.koreader-build.json`, avec `status=experimental`, `complete=true`, `physical_restore_eligible=false`, `hardware_qualified=false`, le SHA-256 final de l'image et les paramètres ext4 effectivement utilisés.

En cas d'écart, l'image reste sous son nom temporaire `.part` et le résultat est `failed`.

## Contrat d'entrée réel (pour qui lance `--build` sous Linux/WSL2)

Cet outil n'effectue lui-même aucune validation ELF/ABI (c'est le rôle d'`audit-arm-runtime`, voir ci-dessous) et ne télécharge ni ne redistribue rien ; il fusionne seulement les fichiers locaux qu'on lui désigne. Concrètement :

- **Structure de `koreader_dir`.** Fournir le répertoire dont le contenu immédiat doit atterrir sous `/opt/koreader` — typiquement le répertoire `koreader/` *à l'intérieur* d'une archive officielle `koreader-kobo-vX.Y.Z` extraite, pas le répertoire englobant de l'archive. Il doit au minimum contenir `reader.lua` et un binaire ARM `luajit` (les deux points d'entrée requis sous `opt/koreader/`) ; en pratique une vraie version apporte aussi `libs/` (bibliothèques partagées embarquées) et des sources Lua, tous copiés tels quels.
- **Architecture attendue.** Le noyau cible est ARM (i.MX50, Aura HD/`dragon`), donc `luajit` et chaque `.so` sous `libs/` doivent être des ELF32 ARM little-endian. Cet outil ne le vérifie pas — il copie les octets tels quels. `audit-arm-runtime` est le contrôle statique ELF/ARM ; l'exécuter sur l'arbre assemblé par cet outil (ou, une fois `--build` exercé de bout en bout, avant `--build`), et ne jamais traiter un succès de `build-koreader-rootfs` seul comme une preuve de compatibilité ARM.
- **Structure de `runtime_dir`.** Également un simple répertoire, fusionné à la racine du rootfs exactement comme `koreader_dir` est fusionné sous `opt/koreader/` : le chemin relatif d'un fichier sous `runtime_dir` est son chemin final dans l'arbre (donc `runtime_dir/bin/busybox` devient `/bin/busybox`). Aucune structure n'est imposée au-delà de « ne pas entrer en collision avec les fichiers propres de la surcouche sous `bin/`, `etc/`, `usr/bin/` » (voir la règle de collision ci-dessus) et « fournir ce dont BusyBox/libc/`luajit`/KOReader ont réellement besoin pour fonctionner », ce que cet outil n'énumère ni ne vérifie.
- **Composants d'origine Kobo potentiellement nécessaires.** La position actuelle du projet (voir [libération hors ligne](offline-liberation-fr.md)) est qu'un binaire BusyBox et un petit ensemble explicitement choisi de bibliothèques partagées GNU/libc extraites de la propre sauvegarde de l'utilisateur peuvent être nécessaires pour la V1, faute de remplacement entièrement reconstruit depuis les sources. Rien de plus large n'est présumé nécessaire ; ne pas ajouter de fichiers Kobo à `runtime_dir` « par précaution ». Tout ajout doit être extrait localement par l'opérateur — **jamais committé dans ce dépôt, jamais téléchargé par cet outil.**
- **Refus des composants Nickel non nécessaires.** `runtime_dir` et `koreader_dir` ne devraient contenir que ce dont KOReader/BusyBox ont réellement besoin pour lancer `reader.lua` contre `/mnt/onboard` — pas de binaires Nickel, pas de modules Lua de Nickel, pas de `nickel_conf.lua`, pas du fichier de configuration propre à Nickel. La recherche bornée ci-dessus existe précisément pour détecter une inclusion accidentelle de ce type ; une alerte doit être traitée comme « retirer ceci de `runtime_dir`/`koreader_dir` et reconstruire », pas ignorée silencieusement.
- **Dépendance dynamique manquante.** Cet outil n'a aucune notion de « dépendance manquante » : si un `.so` requis par un binaire est absent de `runtime_dir`/`koreader_dir`, l'assemblage réussit quand même (le fichier manquant n'est simplement pas là) et, sous Linux uniquement, `--build` produit quand même une image. **Détecter cela est exactement le rôle de la résolution `DT_NEEDED` d'`audit-arm-runtime`** contre `/opt/koreader/libs`, `/lib`, `/usr/lib` (voir sa propre documentation) ; il rapporte `missing or invalid ARM dependency <nom>` précisément dans ce cas. Ne jamais traiter un succès de `build-koreader-rootfs` comme une preuve que KOReader peut réellement se charger.

## Lien avec les autres chantiers en cours, et chaîne vérifiée

`build-koreader-rootfs` (cet outil) → le répertoire qu'il assemble → `audit-arm-runtime --check-bootstrap --check-storage` (audit ELF/dépendances/bootstrap/stockage) → `preflight-koreader` (agrégateur) sont censés former une seule chaîne, chaque étape lisant la sortie locale de la précédente, aucune n'exécutant quoi que ce soit ni ne touchant un périphérique. Ceci a été vérifié de bout en bout dans une fusion locale, à usage unique, de cette branche avec `feat/audit-arm-runtime` au commit `908b2a1` (jamais poussée, jamais fusionnée dans l'une ou l'autre branche réelle — le worktree a été supprimé après vérification) :

- [`feat/rebuild-rootfs-spec`](rebuild-rootfs-spec-fr.md) a déjà produit `experimental/offline-rootfs` (la surcouche init/lancement que cet outil consomme) et l'[audit matériel hors ligne](offline-hardware-audit-fr.md) documentant ce qui reste non qualifié (préparation du framebuffer, nœuds tactile/éclairage, batterie, veille, USB). Cet outil ne redérive ni ne contredit cet audit ; il donne seulement au prototype un chemin reproductible et vérifiable vers un vrai fichier image.
- Le `tools/audit-arm-runtime.py` de `feat/audit-arm-runtime` s'exécute sans modification sur un répertoire que cet outil matérialise (via l'arbre temporaire de `--build`, ou en appelant directement `_copy_tree(..., write=True)` sous-jacent à `plan_rootfs`) — confirmé mécaniquement : `--check-storage` rapporte correctement `/mnt` et `/mnt/onboard` comme de vrais répertoires (pas des liens) sur un arbre assemblé synthétique, et `--check-bootstrap` (POSIX uniquement) relit les mêmes points d'entrée requis que cet outil impose.
- Son agrégateur `preflight-koreader.py` appelle déjà `_copy_tree`/`_scan_for_nickel` de cet outil directement sur l'arbre déjà fusionné lorsque `build-koreader-rootfs.py` se trouve à côté de lui (sa propre documentation le dit explicitement). **Cela a reproduit un faux positif permanent** lors de la vérification locale : le commentaire propre à `usr/bin/pmkb-reader` (« bypassing ... Nickel paths ») est indiscernable d'un contenu externe une fois fusionné, donc toute vraie construction échouerait `nickel_signatures`. `scan_tree_for_nickel(root)` est le correctif — un nouveau point d'entrée public et stable de cet outil, pensé spécifiquement pour un répertoire *déjà fusionné*, qui exclut les fichiers propres de la surcouche de l'analyse de contenu en les recalculant depuis `experimental/offline-rootfs` plutôt que depuis leur provenance pré-fusion. Rejouer l'appel corrigé localement a confirmé que `nickel_signatures` passe d'un `FAIL` permanent à `PASS` sur une construction synthétique propre, et continue à correctement `FAIL`er quand un fichier externe est modifié pour référencer Nickel. **`feat/audit-arm-runtime` n'a pas encore adopté ce correctif** (ce n'est pas la branche de cet outil à modifier) ; son assistant `nickel()` dans `tools/preflight-koreader.py` devrait passer de `builder._copy_tree(...)`/`builder._scan_for_nickel(...)` à `builder.scan_tree_for_nickel(root)` lors de sa prochaine synchronisation.
- `build-koreader-rootfs` ne duplique volontairement pas l'analyse ELF ni la résolution de dépendances — voir le contrat d'entrée ci-dessus pour exactement quel manque `audit-arm-runtime` comble.

## Défauts de bootstrap trouvés par `audit-arm-runtime --check-bootstrap`/`--check-storage`, et leur correction ici

Cet audit (documenté dans `docs/audit-arm-runtime-fr.md`) a trouvé trois manques concrets dans le prototype `experimental/offline-rootfs` lui-même, examinés et corrigés dans la branche de cet outil plutôt que laissés comme limite documentée :

1. les quatre scripts de lancement étaient suivis en `100644` dans Git. Cet outil forçait déjà `0755` sur chaque fichier de la surcouche qu'il copie (`force_mode=0o755`), donc sa propre sortie n'a jamais été affectée — mais une copie brute de la surcouche, sans passer par cet outil, ne serait pas exécutable. Corrigé directement dans l'index Git (`git update-index --chmod=+x`), en renfort de `force_mode`, pas en remplacement.
2. `rcS` montait `/mnt/onboard` sans le créer ; seule la garantie de répertoires squelettes de cet outil (`SKELETON_DIRS` inclut `mnt`/`mnt/onboard`) rendait cela sûr. `rcS` exécute maintenant aussi `mkdir -p /mnt/onboard` lui-même, pour qu'un rootfs assemblé différemment (pas par cet outil) monte quand même correctement.
3. `pmkb-reader` ne vérifiait que `/run/pmkb-ready` (posé une seule fois, pendant `rcS`), donc un montage perdu entre les étapes `sysinit` et `once` de l'init passerait inaperçu et KOReader serait lancé contre un `/mnt/onboard` obsolète/vide. Une nouvelle garde, `usr/bin/pmkb-check-onboard` (même forme que `pmkb-check-offline` existant : lecture seule, refuse sur table de montage absente/illisible, argument de chemin injectable pour les tests), revérifie le montage via `/proc/mounts` immédiatement avant que `pmkb-reader` n'exécute KOReader. C'est désormais un point d'entrée requis.

## Tests minimaux avant un essai matériel réel

Couverts par `tests/test_build_koreader_rootfs.py` : rejet des chemins périphériques et des entrées non-répertoires, détection des points d'entrée requis manquants, collisions fichier/lien entre sources, fusions de répertoires légitimes, recherche bornée de références à Nickel à la fois avant fusion (`plan_rootfs`, par nom et par contenu, y compris le cas d'exclusion de la surcouche) et après fusion (`scan_tree_for_nickel`, y compris le cas de régression du faux positif ci-dessus), stabilité du JSON, court-circuit hors Linux, et refus d'écraser une sortie existante — le tout sans aucun outil réservé à Linux. `tests/test_offline_guard.py` ajoute un test d'exécution pour la nouvelle garde `pmkb-check-onboard` et des contrôles statiques d'ordre (`mkdir` avant `mount` ; garde avant `exec`) sur les sources de la surcouche elles-mêmes, sans exécuter `rcS`/`pmkb-reader` (toujours dépendants de root/du matériel). Un test conditionné à Linux (`BuildRootfsLinuxBuildTests`) exerce le chemin réel `fakeroot`/`mke2fs`/`e2fsck`/`debugfs` de bout en bout avec des fixtures synthétiques — confirmé réussi sur la CI Ubuntu ; il reste à répéter avec une vraie version extraite de KOReader et de vrais composants runtime locaux avant tout essai matériel.
