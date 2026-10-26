# PMKB L06-D6f — contrat de détachement avant destruction

Statut : implementation publiee dans la PR #31, qualification CI a verifier au SHA `2b11b537e11bea3dbeb344272b891cb3fb55aba9`.

## Regle pour le futur routeur

Lorsque le routeur emprunte un `PMKBAppHost` et une `PMKBSurface` au garde Store, il DOIT appeler `pmkb_store_launcher_guard_before_destroy(&guard)` **avant** de detruire ou liberer l'un des deux objets. Il peut aussi utiliser `pmkb_store_launcher_guard_leave`, mais la nouvelle fonction nomme explicitement la frontiere de duree de vie. L'appel est idempotent, et ne dereference ni l'hote ni la surface empruntes.

Le routeur doit aussi : garantir un buffer Store distinct et vivant ; ne jamais laisser l'aperçu pointer sur une surface locale deja sortie de portee ; re-entrer explicitement apres un changement d'application ; signaler les ecritures externes avec `external_draw` ; ne pas appeler le garde apres sa propre destruction. Aucun verrou de concurrence n'est fourni.

## Test

`native/test_store_launcher_isolation.c` utilise le vrai bridge Launcher epingle par la CI existante et des doubles Notes/Calculatrice. Les trois transitions successives testeent maintenant le detach avant fermeture d'application, la suppression des pointeurs et un second detach idempotent.

## Limites

Ce contrat est une **obligation de l'appelant**, pas une garantie automatique contre les use-after-free. Il n'existe toujours aucune route Store active (`runnable=false`). Aucun essai ARM/Kobo, EPDC ou tactile. FIRST BOOT, P1/P2/P3, recoveryfs, Notes ADR-005 et huit illustrations sont inchanges. Ne pas fusionner les PR #30/#31.

## Prochain petit lot D6g

Revoir seulement les appels de cycle de vie exposes par le routeur reel, puis verifier le comportement face a un `leave` suivi d'un `draw` et a une re-entree. Pas d'activation du Store sans contrat d'integration explicite.
