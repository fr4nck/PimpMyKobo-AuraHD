# PMKB Store L08-O — Preuve statique des symboles depuis archive vérifiée

## Objectif

Relier L08-M (archive TAR.GZ rapprochée du snapshot rootfs et graphe
DT_NEEDED) à L08-N (symboles dynamiques, noms et nœuds de version).
Jusqu'ici, L08-N acceptait un dictionnaire de bibliothèques fourni par
l'appelant ; L08-O constitue lui-même ce dictionnaire **uniquement**
à partir des octets de bibliothèques déjà trouvés dans l'archive et
vérifiés par SHA-256 contre le snapshot.

## API

Le contrat conserve la fonction existante
`inspect_arm_archive_dependency_graph(candidate, archive_bytes, snapshot, ...)`
dans `experimental/store-v0/arm_runtime_archive_evidence.py`.

Le rapport ajoute `candidate_symbol_report` :

- Si le rapprochement archive ↔ snapshot est incomplet ou divergent,
  `verdict=not_evaluated_due_to_archive_verdict`, sans analyse symbolique.
- Sinon, les bibliothèques ET_DYN validées et atteintes dans le graphe sont
  transmises à `compare_required_symbols`, sans accès au disque ni
  bibliothèque arbitraire. Les noms étrangers à DT_NEEDED restent exclus
  par le contrat de L08-N.
- Si le symbole ou son nœud manque, le rapport dit
  `symbol_pairs_incomplete`; si la table de symboles manque, il dit
  `candidate_symbol_table_unavailable`. Un ELF malformé conduit à
  `comparison_refused`, pas à une preuve positive.
- `symbol_pairs_observed` signifie uniquement que les octets de l'archive
  concordante contiennent les noms et nœuds requis **dans le périmètre
  observé**. Ce n'est pas une relocation réellement effectuée.

Le graphe conserve ses plafonds (32 objets, profondeur 8, 256 arêtes ;
64 Mio cumulés de bibliothèques, 16 Mio par objet). L'analyse supplémentaire
reste **sur l'hôte**, sans service permanent sur le matériel 512 Mio.
Elle concerne uniquement le binaire candidat : pas encore les symboles
indéfinis de chaque bibliothèque transitive.

## Garde-fous

L08-O ne modifie pas les décisions de lancement. Un graphe complet, un
rapport symbolique positif et une concordance des empreintes SHA-256 ne
prouvent ni provenance P1, ni compatibilité réelle du chargeur Linux
2.6.35.3, ni ABI, ordre de résolution, relocations, noyau ou matériel.

Tous les indicateurs `symbol_versions_verified`,
`transitive_dependencies_verified`, `hardware_verified`,
`runtime_compatible`, `launchable` restent faux. Aucune extraction,
montage, réseau, exécution ARM, écriture P1/P2/P3, utilisation de Nickel
ou opération sur microSD. La présence réelle des bibliothèques Kobo
reste UNKNOWN tant qu'une P1 de provenance connue n'a pas été fournie.

## Qualification

Les tests synthétiques de
`tests/test_store_arm_runtime_archive_evidence.py` vérifient la
concordance symboles+versions, la différence de nom, le refus de
l'archive non concordante avant analyse des symboles, les symboles
absents et les tables malformées. La CI Linux/Windows qualifie
uniquement cette logique hôte.
