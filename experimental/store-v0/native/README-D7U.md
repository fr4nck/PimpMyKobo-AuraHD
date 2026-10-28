# PMKB D7u — compteurs diagnostiques saturants

Le modèle E-Ink simulé garde des compteurs distincts de confirmations réussies et échouées. Lorsqu'un compteur atteint la valeur maximale de `unsigned`, il reste saturé : aucun retour à zéro susceptible de tromper les diagnostics. Les marqueurs, leur unicité et le retour de `pmkb_store_eink_complete` sont inchangés.

Le test place les deux compteurs à `UINT_MAX - 1`, confirme deux succès puis deux échecs et contrôle leur saturation respective, sans bloquer les cycles suivants. Il s'agit d'un contrat hôte, pas d'une validation des marqueurs EPDC réels.

Correctif `e7aef93a55c91edc05180664c9e874e49192c57e`, test `6efd39af73376fcc7dd6053a1d69791c256eb299`. Résultat CI à vérifier avant PASS. Store non exécutable, PR #30/#31 non fusionnées, FIRST BOOT/P2 inchangés.
