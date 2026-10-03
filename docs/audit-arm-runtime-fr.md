# Audit local du runtime ARM

Le prochain jalon est P1 minimal → KOReader directement, sans Nickel. Le prototype de démarrage est déjà présent sur la branche `feat/rebuild-rootfs-spec` (commits `bec7fd5`, `6522092`), mais pas dans `main` au moment de cet ajout. Cet outil complète ce chantier sans reproduire son init ni construire une autre image.

```sh
python3 tools/pmkb.py audit-arm-runtime /chemin/rootfs-local
```

Utiliser uniquement un répertoire extrait localement, jamais une carte montée. L'outil ne monte rien, n'exécute aucun ELF, ne lance pas `ldd` et n'écrit aucun fichier. Il refuse les chemins spéciaux `/dev`, `/proc`, `/sys`, les fichiers non réguliers et les liens sortant de l'arbre. Les liens absolus sont interprétés dans le rootfs invité, pas dans le système hôte. P2/recoveryfs n'est pas un argument ni une destination.

Le JSON sur stdout contient les SHA-256 et les dépendances `DT_NEEDED` de chaque ELF, ainsi que `PT_INTERP`. Code de sortie 0 : contrôles statiques satisfaits ; 1 : dépendance absente/invalide, ELF incompatible ou erreur de lecture. Tous les ELF doivent être ARM ELF32 little-endian de type exécutable ou bibliothèque. Les scripts et autres fichiers ordinaires sont ignorés ; les bibliothèques transitives sont contrôlées lors du parcours complet. Un répertoire sans ELF est refusé.

Le contrat de recherche retenu pour ce premier audit est `/opt/koreader/libs`, `/lib`, `/usr/lib`, dans cet ordre. Une dépendance trouvée mais invalide bloque la résolution. RPATH/RUNPATH et les dépendances à chemin relatif sont refusés pour examen séparé. Le cache du chargeur, ses variantes de recherche, les versions de symboles, les attributs ARM/ABI flottante, les permissions d'exécution, les chargements `dlopen` et les bibliothèques choisies par Lua ne sont pas qualifiés. Adapter la configuration effective du futur lanceur à ce contrat reste nécessaire.

**Validation : tests synthétiques locaux seulement.** Aucun binaire Kobo n'est redistribué. Un verdict `ok` ne prouve ni l'absence de dépendance à Nickel, ni un démarrage matériel, ni la compatibilité avec le noyau Aura HD. Le rapport porte toujours `physical_restore_eligible=false` et `hardware_qualified=false` ; il ne remplace aucun rapport ou garde-fou de restauration.

## Résultat du lot (3 octobre 2026)

Sur l'hôte Linux : 250 tests exécutés, 244 réussis, 5 ignorés (Qt indisponible), 1 échec préexistant : `LinuxDestinationDetectionTests.test_unknown_device_is_undetermined`. Ce dernier a été reproduit avec les fichiers de `main` inchangés dans un répertoire temporaire. Les 5 tests du nouvel audit, l'intégration CLI et le paquet Debian passent. Les tests de construction d'images synthétiques nécessitent une exécution hors du confinement fakeroot de cet hôte. La matrice Windows reste à vérifier en CI.

Audit de non-écriture : le nouvel outil ne contient aucune ouverture en écriture, aucun sous-processus et aucun chemin de restauration ; ses fixtures seules écrivent dans des répertoires temporaires. Aucun périphérique physique ni P2 n'a été modifié.

## Contrat de lancement du prototype (lot suivant)

```sh
python3 tools/pmkb.py audit-arm-runtime /chemin/rootfs-local --check-bootstrap
```

Cette option ajoute un contrôle des fichiers de la chaîne du prototype : `/sbin/init`, `/bin/sh`, `/bin/busybox`, LuaJIT, les quatre scripts PMKB, `inittab` et `reader.lua`. Le contrat vient des sources `experimental/offline-rootfs` de la branche `feat/rebuild-rootfs-spec`, examinées au commit `b2f9180`. Aucune copie de l'init n'est ajoutée à cette branche.

Les quatre exécutables doivent être des ELF ARM compatibles avec l'audit et les exécutables/scripts doivent avoir au moins un bit d'exécution. Les scripts doivent commencer par `#!/bin/sh` et utiliser LF. Le shell et les liens BusyBox sont résolus dans l'arbre invité. `inittab` doit contenir exactement les trois actions du prototype (sysinit rcS, once pmkb-reader, shutdown umount), sans action additionnelle, manquante ou dupliquée ; commentaires et lignes vides sont acceptés. `reader.lua` doit être un fichier régulier non vide. Les modes, chemins résolus et SHA-256 apparaissent dans `bootstrap_files`.

Le contrôle des permissions nécessite une extraction sur un système POSIX qui conserve les modes ; l'option est refusée sous Windows. L'audit ELF sans cette option reste disponible sous Windows. Une extraction qui perd les modes ne représente pas les permissions de l'image cible.

**Manque observé :** les quatre scripts du prototype sont enregistrés dans Git en `100644`. Une copie brute de l'overlay sans permissions explicites ne constitue pas une chaîne exécutable. La préparation du rootfs doit poser les modes appropriés. L'audit a refusé les quatre scripts exacts, copiés dans une fixture locale avec ces modes, puis a accepté la même fixture après passage des scripts en `0755`. Les ELF de cette expérience étaient synthétiques ; les permissions de l'image privée existante n'ont pas été inspectées.

Ce contrôle ne vérifie pas la syntaxe Lua/shell, le contenu fonctionnel de rcS/pmkb-reader, les applets compilées dans BusyBox, les autres commandes résolues via PATH, les permissions des répertoires ni l'intégrité de l'image ext4. Il ne prouve pas que BusyBox init traite ces actions sur l'appareil. Aucun init ou script cible n'est exécuté.

L'audit matériel déjà présent sur la branche du prototype (`docs/offline-hardware-audit-fr.md`) reste pertinent : présence de `/dev/fb0` et d'event0/event1 insuffisante pour qualifier framebuffer/tactile, `/dev/ntx_io` non exigé par rcS, réglages Nickel encore actifs. Aucune stratégie d'initialisation de ces périphériques n'est choisie ici. P3 reste en lecture seule dans ce prototype ; persistance des réglages, transfert des livres depuis Calibre et export USB restent à concevoir/qualifier séparément. Ce lot ne modifie ni P3 ni ce choix de stockage.

Validation du second lot : 10 tests de l'audit réussis, dont 5 nouveaux tests de lancement. Suite complète Linux hors confinement fakeroot : 255 tests exécutés, 249 réussis, 5 ignorés, le même échec préexistant de détection de destination documenté ci-dessus. CLI et paquet Debian passent ; le nouveau contrôle POSIX nécessite encore l'exécution de la CI. Le diff ne modifie aucun script du prototype ni outil physique ; seules les fixtures temporaires écrivent des fichiers et changent des permissions.
