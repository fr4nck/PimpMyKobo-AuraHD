# PMKB L06-D6z — pagination du Store passif

Le test de routeur utilise un catalogue synthetique de 64 applications non lancables et effectue le parcours page 0 -> page 1 -> page 0. Il verifie que le framebuffer Store 320x480 reste le meme objet alloue et que sa taille logique demeure 153600 octets. Chaque reentree passe par le garde et invalide le cache de peinture avant d'afficher la page demandee.

Le nouveau test ne mesure pas l'aire des rectangles de pixels modifiee, ne commande aucun rafraichissement EPDC et ne prouve pas que la page physique serait actualisee. Il ne partage pas de buffer avec Notes ou Calculatrice.

Commit de test `a697a193622934a6e8fd72803c55b9eba05adb21`, validation CI au SHA a verifier. Store toujours non executable, PR #30 et #31 non fusionnees, FIRST BOOT/P2 et carte Kobo inchanges.
