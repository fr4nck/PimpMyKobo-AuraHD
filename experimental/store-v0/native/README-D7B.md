# PMKB L07-D7b — presentation par backend hote simule

Le test C11 appelle le vrai `pmkb_surface_present` de PMKB-UI sur le framebuffer Store passif, avec un callback de presentation sans peripherique. Un premier acquittement simule echoue : l'operation retourne l'erreur et conserve la zone dirty. Le backend est ensuite retabli : le rappel reussit, la zone dirty est acquittee, puis un appel sans nouveau dessin retourne `PMKB_NO_CHANGE`. Le callback borne et valide la zone recue.

Ce test n'est pas une simulation du pilote MXCFB : il ne mesure ni marqueurs EPDC, ni delai, ni consommation electrique. Il n'y a aucune ecriture physique Kobo, aucune fusion de PR ni activation du Store.

Commit C11 `b7468de0305af3c4dec8ed63eb4e5030b224ffd6`. La CI correspondante doit etre terminee avant de qualifier le lot.
