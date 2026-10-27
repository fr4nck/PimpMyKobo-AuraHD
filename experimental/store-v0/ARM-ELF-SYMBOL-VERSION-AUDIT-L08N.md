# PMKB L08-N — audit statique des symboles dynamiques et des versions ELF

## Objectif

Ajouter un contrôle au niveau des symboles, après L08-L (métadonnées et
nœuds de versions) et L08-M (graphe des dépendances). Le module
arm_elf_symbol_resolution.py expose compare_required_symbols(candidate,
libraries_by_needed_name).

Le parseur borne l'ELF32 à 16 Mio, la table dynamique de symboles à 65 536
entrées et les données de bibliothèques à 64 Mio. Il accepte les tables
de hachage SysV DT_HASH et GNU DT_GNU_HASH pour borner le nombre de symboles,
puis examine DT_SYMTAB, DT_SYMENT et DT_VERSYM. Il associe les indices
DT_VERSYM des symboles indéfinis à DT_VERNEED et les indices des symboles
définis à DT_VERDEF.

Pour un symbole versionné, le contrôle exige un nom de symbole défini dans
la bibliothèque DT_NEEDED correspondante et un nœud de version égal. Pour
un symbole non versionné, il cherche seulement un nom compatible parmi les
bibliothèques fournies. Les bibliothèques absentes, le SONAME divergent,
la table de versions absente, l'index non mappé et le symbole/version manquant
ont des états distincts.

## Ce que cela ne prouve pas

La sortie symbol_and_version_node_observed_in_library prouve uniquement que
les métadonnées fournies contiennent un symbole exporté et un nœud de version
de même nom. Elle ne prouve pas une relocation réussie, les règles de
visibilité/interposition, l'ordre de recherche du chargeur, le chargement
de l'objet attendu ou l'existence de toutes les dépendances transitives.

Le nombre de symboles est borné à partir de DT_HASH ou DT_GNU_HASH. Le module
vérifie la structure et les limites de ces tables, mais ne prouve pas
indépendamment que les tables de hachage et la table dynamique de symboles
correspondent parfaitement à toutes les relocations du binaire. Un ELF sans
table de hachage exploitable est non qualifié plutôt que considéré vide.

Les symboles faibles sont signalés. Les champs symbol_versions_verified,
dynamic_symbol_resolution_verified, transitive_dependencies_verified,
runtime_compatible, hardware_verified et launchable restent False. Aucun
ELF ARM n'est exécuté ; aucun chemin hôte n'est ouvert ; aucune bibliothèque
Kobo réelle n'est versée au dépôt.

## Tests

tests/test_store_arm_elf_symbol_resolution.py construit des tables ELF32
synthétiques et vérifie les symboles versionnés, les noms absents, les
nœuds de versions divergents, les tables SysV/GNU, les hash malformés,
les métadonnées fournisseur refusées et l'absence d'E/S hôte. Ces tests
qualifient le parseur seulement, pas le chargeur Linux 2.6.35.3 de l'Aura HD.

## Revue supplémentaire : preuves admises pour les symboles non versionnés

La présence d'une bibliothèque arbitraire dans le dictionnaire fourni
par l'appelant ne démontre pas qu'elle soit chargée par le binaire.
Pour les symboles non versionnés, seuls les objets dont le nom figure
dans le DT_NEEDED **direct du candidat** peuvent satisfaire la
concordance diagnostique ; les autres figurent dans
`libraries_not_in_candidate_needed` et sont exclus des succès.
Les bibliothèques transitives peuvent en pratique fournir des
symboles, mais **les règles réelles du chargeur ne sont pas simulées**
par cet analyseur. La conclusion reste un inventaire statique, jamais
une garantie d'exécution.
