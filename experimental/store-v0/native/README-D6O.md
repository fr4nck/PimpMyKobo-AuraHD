# PMKB L06-D6o — echec de reouverture du proprietaire de surface

Le test natif C11 `test_store_launcher_isolation.c` verifie qu'une reouverture sur une geometrie invalide (319x480) apres une ouverture valide (320x480) ferme d'abord l'ancien buffer et detache le garde, sans conserver de pointeur. Le test rouvre ensuite sur 320x480 et controle la quantite de pixels alloues.

Il s'agit de la politique actuelle de `pmkb_store_owner_open` : **une tentative de reouverture remplace ou ferme l'etat precedent**, elle ne garantit pas la conservation de la vue en cas d'erreur. Le routeur futur devra en tenir compte.

Commit de test : `71f3d8e4810b18970fb797a13b1edeff4ee65ece`. Verifier la CI avant de declarer D6o PASS. Aucun changement Store executable, Notes ADR-005, PR #30, FIRST BOOT, P2, microSD ou materiel Kobo.
