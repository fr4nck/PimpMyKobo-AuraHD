# PMKB L06-D6n — premier proprietaire de surface Store passive

## Code

`pmkb_store_surface_owner.h` ajoute un `PMKBStoreSurfaceOwner` C11 qui possede une seule `PMKBSurface` et embarque son garde Launcher. `init` prepare l'objet, `open` valide une geometrie prise en charge puis alloue la surface et attache le garde ; `close` detache avant de liberer les pixels, y compris en appels repetes. Aucun Store executable, processus, thread ni reseau.

Il ne faut ni copier cet objet apres initialisation, ni appeler `init` sur un objet deja ouvert, ni detruire l'hote emprunte avant `close`.

## Cout des pixels

- 320 x 480 : 153 600 octets, 150 Kio.
- 1080 x 1440 (ou inverse) : 1 555 200 octets, 1 518,75 Kio.
- Hors structures C, tas et eventuelle surface des Notes/Calculatrice.

## Tests

`test_store_launcher_isolation.c` ajoute les cas taille refusee, creation, peinture, transition Notes, reouverture, fermeture repetee, liberte du buffer, puis geometrie 1080x1440. Les metiers Notes/Calculatrice sont des doubles de test, mais le bridge et la surface proviennent des sources PR #30 epinglees.

Code `17838b3967d0e2d181722330efea2dc7576c5c66`, test `4b59c98316796b6833e9ee637bc53dd6f49e7265`. **Qualification CI de ce dernier commit a verifier avant de declarer PASS.** Aucun essai ARM/Kobo/EPDC.

Aucun changement FIRST BOOT, P1/P2/P3, Notes ADR-005 ou fusion de PR #30/#31.
