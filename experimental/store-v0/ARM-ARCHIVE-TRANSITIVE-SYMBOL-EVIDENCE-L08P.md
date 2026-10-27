# PMKB Store — L08-P : audit des imports symboliques transitifs

Le graphe L08-M/L08-O contient des bibliothèques ARM trouvées en mémoire
dans une archive TAR.GZ auparavant rapprochée d'un export rootfs.
L08-P analyse les importations symboliques de **chaque bibliothèque
observée**, et non seulement celles du binaire candidat.

L'API existante `inspect_arm_archive_dependency_graph(...)` ajoute
`dependency_symbol_reports` (noms, chemins archive, comparaisons L08-N),
`interpreter_symbol_report` (PT_INTERP, distinct) et
`symbol_audited_dependency_objects`. Les fournisseurs admis pour un
objet sont limités aux entrées **DT_NEEDED directes** de cet objet et
aux bibliothèques déjà observées dans l'archive vérifiée.

Une dépendance non observée, un symbole ou une version absente, une table
indéchiffrable ou une archive divergente ne produisent jamais un succès.
Si l'archive ne concorde pas avec l'export, aucune analyse symbolique
candidate/transitive/chargeur n'est exécutée.

Le coût de l'analyse est réservé à l'hôte. Plafonds hérités : 32 objets,
8 niveaux, 256 arêtes, 16 Mio par ELF, 64 Mio cumulés pour les
bibliothèques. Les tests utilisent des ELF/archives/exports synthétiques :
import transitif versionné, symbole manquant, fournisseur non observé,
hash malformé, import depuis PT_INTERP et court-circuit archive divergente.

**Limites** : la correspondance statique ne simule pas l'ordre de
recherche du chargeur, ses relocalisations, la visibilité effective,
l'ABI, le noyau ou le matériel Kobo. Aucun lien physique attesté avec
une vraie image P1. Les champs `symbol_versions_verified`,
`transitive_dependencies_verified`, `runtime_compatible`,
`hardware_verified` et `launchable` demeurent toujours faux.
Aucun montage, périphérique /dev, extraction, lancement ARM ou écriture
sur P1/P2/P3. Il s'agit d'une qualification logiciel hôte, pas Kobo.
