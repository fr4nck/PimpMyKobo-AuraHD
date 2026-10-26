# PMKB L07-D7q — annulation avant destruction de surface

Ajout de `pmkb_store_eink_async_cancel` au contrat asynchrone simulé. L'appelant doit annuler le marqueur **avant** toute fermeture ou réallocation du framebuffer concerné. Cette annulation détache le pointeur mémorisé sans le déréférencer, et rend invalide une confirmation tardive. Le compteur de marqueurs reste monotone : un nouvel aperçu ne peut pas réutiliser l'identifiant annulé.

Le test C11 simule une soumission, une annulation, une fermeture, une confirmation tardive rejetée, puis une réouverture. Il confirme qu'un ancien marqueur ne peut pas acquitter les pixels du nouvel aperçu, tandis que le nouveau marqueur valide peut les acquitter.

**Limites** : il s'agit d'une discipline volontaire de cycle de vie, non d'un dispositif de synchronisation matérielle ou de concurrence multithread. Une fermeture qui oublie `cancel` ne devient pas sûre par magie ; le raccordement réel devra organiser explicitement `cancel -> close` (ou attendre la fin du refresh). Le matériel MXCFB/EPDC n'est pas sollicité.

Test : `e56ca6433c9863da8173d2e37a4d6d274925b7cd`. CI à vérifier avant PASS. Store non exécutable, PR #30/#31 non fusionnées, FIRST BOOT/P2 intacts.
