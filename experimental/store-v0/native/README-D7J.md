# PMKB D7j — presentation echouee apres redimensionnement

Le banc natif C11 ouvre une surface Store 320x480 puis 1080x1440. Un backend simule refuse la premiere presentation de la nouvelle surface : l'erreur est propagee, le rectangle dirty demeure actif et le buffer redimensionne reste possede (1 555 200 octets de pixels). Le second essai accepte le rendu et acquitte le dirty ; le suivant retourne `PMKB_NO_CHANGE`.

Test : `9c25f7f9f93f4ae5914e1d2efd53d23fe739d014`. Attendre sa CI avant PASS. Pas d'EPDC reel, de mesure RSS, d'activation Store, de fusion PR #30/#31 ou d'ecriture FIRST BOOT/P2.
