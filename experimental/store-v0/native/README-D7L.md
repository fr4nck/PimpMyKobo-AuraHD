# PMKB D7l — echecs repetes du backend

Le banc C11 ajoute trois tentatives de presentation Store consecutivement refusees par le backend simule. Apres chaque erreur, la zone dirty doit rester presente et les 153600 octets de framebuffer 320x480 restent sous la propriete du routeur. Lorsque le backend redevient disponible, une presentation doit enfin acquitter la zone ; l'appel suivant renvoie `PMKB_NO_CHANGE`.

Test `17d34ca3588a54575016684e34c1d8a7b7cc703c`. CI a qualifier avant PASS. Le test ne prouve pas la fiabilite du pilote E-Ink reel, et ne lance aucun rafraichissement EPDC. Store non executable, PR #30/#31 non fusionnees, FIRST BOOT/P2 inchanges.
