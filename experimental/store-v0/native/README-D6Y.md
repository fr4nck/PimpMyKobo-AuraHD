# PMKB L06-D6y — page invalide et cache graphique

Le routeur Store passif possede son framebuffer et le garde possede les metadonnees de cache. Lorsqu'une nouvelle demande de page (ici 9999) echoue, `pmkb_store_router_preview` doit detacher le garde et fermer son framebuffer plutot que conserver un cache visuellement perime. Une demande valide ulterieure doit reouvrir et repeindre.

Le banc C11 teste une surface 320x480 reutilisee, puis le refus de la page invalide, l'absence de pointeur gris, `cache.valid == false`, zero pixels comptabilises, et une reouverture de la page 0. Ce lot ajoute une regression, sans changer le code de production ou introduire des services. Le chemin de reentree valide invalide deja le cache via `pmkb_store_ui_preview_enter`.

Commit de test : `f314b0545060eb92f5841294e4dedba82d997e03`. CI a verifier avant qualification D6y. Aucune fusion PR #30/#31, Store non executable, FIRST BOOT/P2 et Kobo non touches.
