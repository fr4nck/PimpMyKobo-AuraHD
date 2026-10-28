# PMKB L06-D6s — routeur passif C11

Le nouveau `pmkb_store_passive_router.h` possede un `PMKBAppHost` et un `PMKBStoreSurfaceOwner`. Ce prototype de laboratoire utilise les sources natives reelles du pont Launcher PR #30, sans changer le bridge ni declarer Store executable.

- `router_init` initialise les deux objets possedes ;
- `router_preview` alloue la surface, attache son garde, construit et dessine l'aperçu passif ; une erreur de rendu detache/libere ;
- `router_dismiss` libere les pixels, sans service resident ;
- `router_launch_app` et `router_close_app` detachment d'abord, puis deleguent au bridge, dont le refus `PMKB_UNSAVED` pour Notes doit rester intact.

Le test C11 ajoute le parcours Store -> tentative de lancement Store refusee -> Notes -> aperçu Store -> refus de fermeture Notes non sauvegardees -> fermeture explicite -> dimensions invalides. L'implementation metier Notes/Calculatrice est toujours remplacee par des doubles dans ce banc. Ne pas appeler `router_init` deux fois sur un objet deja ouvert ni copier le routeur par valeur. Le prototype ne comporte pas encore de destructeur global d'hote : le routeur appelant reste responsable de fermer explicitement Notes/Calculatrice selon leur contrat.

CI : consulter le run #40352575061 au commit `097970f2321a751763e17cbca887969c523124e6`; aucune declaration PASS avant la conclusion. Aucun test Kobo/ARM/EPDC, aucune fusion PR #30/#31, aucune modification de FIRST BOOT ou P2.
