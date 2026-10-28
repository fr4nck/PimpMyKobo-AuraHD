# PMKB D7g — changement d'application avant presentation

Le banc C11 cree un apercu Store, puis fait demarrer Calculatrice **directement via le vrai bridge Launcher**, volontairement sans prevenir le routeur. Un appel ulterieur a `pmkb_store_router_present` doit refuser la presentation, ne jamais appeler le backend, detacher le garde et liberer le buffer Store. L'application Calculatrice demeure proprietaire de sa surface propre et doit pouvoir etre fermee.

Test `dcb87eaedd46aeb4d0ac37cc3a49f9448bb43344` ; conclusion CI requise avant PASS. Il s'agit d'une transition sequentielle sur hote, pas d'une mutation concurrente pendant un callback. Aucun pilote EPDC, activation Store, fusion PR #30/#31 ou ecriture Kobo/FIRST BOOT/P2.
