# PMKB Store L08-L — métadonnées ELF dynamiques et nœuds de versions

## But

Étendre le diagnostic ARM hôte sans exécuter de binaire et sans supposer
que les bibliothèques requises existent sur la Kobo. Le module
arm_elf_runtime_metadata.py expose inspect_arm_runtime_metadata() et
compare_required_version_nodes().

L'inventaire couvre :
- PT_INTERP et les DT_NEEDED déjà analysés par L08-C ;
- DT_SONAME, DT_RPATH et DT_RUNPATH, y compris les chemins absolus,
  les jetons $ORIGIN et les segments vides pouvant référencer le répertoire
  courant ;
- les drapeaux DT_TEXTREL, DT_BIND_NOW, DT_FLAGS et DT_FLAGS_1 ;
- DT_VERNEED/DT_VERNEEDNUM et les noms des versions requises ;
- DT_VERDEF/DT_VERDEFNUM et les noms de nœuds de versions déclarés par
  une bibliothèque fournie.

Les tables sont lues depuis des bytes fournis explicitement. Limites :
ELF32 little-endian ARM EABI5, 16 Mio par ELF, 32 segments, 4096 octets
par table dynamique et par table de chaînes, 128 enregistrements de version
et 128 auxiliaires par enregistrement. Les pointeurs virtuels doivent être
mappés sans ambiguïté dans un PT_LOAD, les chaînes sont bornées, les chaînes
de version cycliques ou malformées sont refusées.

## Comparaison des nœuds de version

compare_required_version_nodes(executable_bytes, {DT_NEEDED: library_bytes})
compare les noms de nœuds DT_VERNEED avec DT_VERDEF de la bibliothèque
correspondante, après vérification de son type ET_DYN et de son DT_SONAME
lorsqu'il est présent. Il rapporte explicitement les bibliothèques non
fournies, les SONAME divergents et les nœuds manquants.

**Cela ne vérifie pas les symboles eux-mêmes.** La présence d'un nœud de
version dans DT_VERDEF ne garantit pas que le symbole requis est exporté
sous cette version. Le code ne résout pas DT_VERSYM/DT_SYMTAB/DT_STRTAB
symbole par symbole, les relocations, les dépendances transitives complètes,
les règles de recherche du chargeur ni les extensions propres à uClibc/glibc.
Tous les champs symbol_versions_verified, transitive_dependencies_verified,
runtime_compatible, hardware_verified et launchable restent False.

RPATH/RUNPATH sont signalés, jamais interprétés pour ouvrir ou rechercher
un chemin. Les composants vides et absolus génèrent des avertissements.
La présence simultanée de RPATH et RUNPATH est documentée sans présumer
de la sémantique exacte du chargeur historique Kobo.

## Tests et limites

tests/test_store_arm_elf_runtime_metadata.py crée des ELF ARM synthétiques
en mémoire, teste les chemins, drapeaux, versions, incohérences, limites
et refus d'entrées malformées. Aucune bibliothèque propriétaire Kobo n'est
redistribuée et aucune image ou partition physique n'est lue.

Une CI verte qualifie seulement le parseur sur l'hôte. Pour aller plus loin,
il faudra des ELF et bibliothèques issus d'une sauvegarde P1 de provenance
connue, puis analyser leurs versions et symboles sans conclure à la
compatibilité matérielle avant un essai séparé.
