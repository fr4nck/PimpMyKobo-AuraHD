# PMKB L06-D6x — reutilisation du framebuffer Store

Le routeur passif reutilise desormais le tampon gris dont il est deja proprietaire lorsqu'une nouvelle previsualisation demande exactement la meme geometrie. Le garde est **reinitialise et revalide a chaque appel** (`pmkb_store_launcher_guard_enter`) : identite de l'application active, presence du buffer et absence de chevauchement avec Notes/Calculatrice. Tout refus ferme la surface; une geometrie differente emprunte le chemin precedent de fermeture et nouvelle allocation.

Cas testes : deux apercus successifs 320x480 conservent le meme pointeur gris, changement 1080x1440 puis retour 320x480 controle la taille des pixels. Le banc existant continue a verifier les cas catalogue absent, transitions et fermeture.

Limites : reutilisation du **seul** buffer Store; il n'y a aucun partage avec le framebuffer Notes/Calculatrice, ni mesure de `malloc`/RSS, ni preuve e-ink/ARM. Le Store demeure `runnable=false`, PR #30/#31 non fusionnees et support materiel non modifie.

Code `3654d5483cb16fed16bc44962ce8a59ea20cdc48`, tests `57f6fae645bb2fa2b2d3109ea8d9b2944cbca0af`. Attendre la CI au commit des tests avant de qualifier PASS.
