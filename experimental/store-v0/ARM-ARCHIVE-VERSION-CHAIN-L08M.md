# PMKB Store L08-M — graphe borné des dépendances ELF depuis une archive rootfs

## Objectif

Relier les diagnostics L08-L aux octets de bibliothèques d'une archive
TAR.GZ qui concorde avec un inventaire rootfs L08-E. Le module
arm_runtime_archive_evidence.py expose
inspect_arm_archive_dependency_graph(candidate, archive_bytes, snapshot, ...).

Le flux de contrôle est strict :
1. mesurer le SHA-256 du candidat ELF et comparer toute empreinte attendue ;
2. vérifier le digest d'observations du snapshot et ses ancres explicites ;
3. valider le TAR.GZ entier (un seul flux gzip, footer/CRC inclus) et
   comparer ses bibliothèques aux fichiers exportés via L08-H ;
4. refuser de construire un graphe si le verdict n'est pas
   scoped_content_match ;
5. relire en mémoire les fichiers *.so* de l'archive dans les limites
   prévues, puis résoudre les alias uniquement depuis le snapshot ;
6. analyser PT_INTERP, DT_NEEDED et les métadonnées ELF de chaque
   dépendance trouvée, puis recommencer sur les DT_NEEDED de ces bibliothèques.

## Limites opérationnelles

- Uniquement les enfants immédiats de lib/ et usr/lib/.
- Au plus 32 objets de dépendance, profondeur 8 et 256 arêtes.
- ELF individuel 16 Mio ; budget cumulé de métadonnées de bibliothèques
  64 Mio. Un dépassement est refusé.
- Un lien symbolique est interprété depuis les observations rootfs et
  confirmé dans le TAR ; aucun lien hôte n'est suivi.
- RPATH/RUNPATH sont signalés comme métadonnées, jamais utilisés pour
  rechercher ou charger un fichier.
- Les dépendances dont le nom n'est pas observé, dont l'alias est ambigu,
  dont les octets manquent ou dont le SONAME/type ELF ne concorde pas
  restent explicitement non résolues.

Le résultat dependency_graph_complete_in_scanned_scope=true signifie
uniquement que tous les noms parcourus ont des métadonnées ELF cohérentes
dans le périmètre de scan. Cela ne prouve pas la sémantique de recherche
du chargeur, les dépendances hors de ce périmètre ni la compatibilité réelle.

## Nœuds de versions et PT_INTERP

Pour le binaire et chaque bibliothèque observée, L08-M appelle la comparaison
L08-L des nœuds DT_VERNEED/DT_VERDEF. Les rapports signalent les nœuds
manquants et les bibliothèques non fournies. Aucun symbole précis n'est
résolu : la présence du nœud GLIBC/uClibc n'établit pas que l'export
requis existe sous cette version. DT_VERSYM, DT_SYMTAB, les relocations,
les symboles, l'ABI et les règles du chargeur Kobo restent non vérifiés.

PT_INTERP est rapporté séparément. Si son fichier se trouve dans le périmètre
scanné, ses métadonnées peuvent être observées et ses DT_NEEDED ajoutés au
graphe. Le rapport n'en déduit jamais que le noyau pourra l'exécuter.

Tous les champs symbol_versions_verified, transitive_dependencies_verified,
runtime_compatible, hardware_verified et launchable restent False. La
provenance physique de P1 n'est pas authentifiée par ce module.

## Tests

tests/test_store_arm_runtime_archive_evidence.py construit des ELF, un TAR.GZ
et un export rootfs synthétiques. Il couvre le graphe direct/transitif,
les alias, PT_INTERP, les versions absentes, les dépendances manquantes,
la corruption gzip, les limites de profondeur et l'absence d'E/S hôte.
Aucune bibliothèque propriétaire ni image de Kobo n'est publiée.

La CI qualifie seulement le code sur l'hôte. Avant d'utiliser des artefacts
réels, il faudra une sauvegarde P1 dont la provenance est connue ; même alors,
un graphe complet ne sera pas une validation matérielle.
