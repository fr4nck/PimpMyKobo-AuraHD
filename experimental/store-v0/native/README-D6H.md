# PMKB L06-D6h — liberation de la surface empruntee

Sous-lot de qualification sur hote, sans activation du Store.

La suite `test_store_launcher_isolation.c` verifie desormais qu'apres `pmkb_store_launcher_guard_before_destroy`, le proprietaire peut liberer sa surface Store et que tout `draw` ulterieur est refuse. Elle reinitialise une surface synthetique pour terminer les verifications existantes. Le test utilise le bridge Launcher reel epingle et des doubles des metiers Notes/Calculatrice.

L'API reste une discipline d'appel, pas une detection automatique des objets deja liberes. Pas de surface partagee, pas d'ecriture physique, pas de route Store executable, pas de modification P1/P2/P3, FIRST BOOT, Notes ADR-005, ou du Launcher PR #30. Un test hote ne vaut pas qualification ARM/Kobo/EPDC.

Qualification : consulter la CI correspondant au commit `882655883e293fee1baa18d9f1dfbdb3187f2414` ; ne pas declarer PASS avant sa conclusion.

Prochaine reprise : si CI PASS, clore D6h au journal sur main; envisager la matrice d'integration sans fusion des PR #30/#31.
