# PMKB L06-D6k — plages memoire des surfaces Store

Audit du vrai `pmkb_launcher_bridge.c` de la PR #30 : le bridge alloue separement les buffers Notes et Calculatrice avec `pmkb_surface_init`, puis les libere a `pmkb_app_host_close`. Le garde Store est emprunteur et ne doit jamais survivre a ses objets sans detachement.

## Defaut identifie et correction

Le garde D6j rejetait un `gray` identique mais acceptait `notes->gray + 1` comme buffer Store distinct. Le nouveau controle compare les intervalles d'octets `[gray, gray + width * height)` par valeurs `uintptr_t` apres controles de dimensions et de depassement. Il refuse les intervalles qui se chevauchent, meme partiellement. Ce contrat ne remplace pas la garantie de provenance/duree de vie des allocations chez l'appelant.

Le test `test_store_launcher_isolation.c` utilise un alias synthetique volontairement decale d'un octet dans le buffer Notes ; `enter` doit renvoyer INVALID, detacher l'aperçu et ne pas modifier les pixels Notes.

## Qualification

Code `b93249792615cd3c0db3243943ecc78964772d84`, test `16d3016876b7956a4025d306df4727d21c535420`. Consulter la CI exacte avant d'affirmer PASS. Aucun changement de route active, de Notes ADR-005, de Launcher PR #30, de P1/P2/P3 ou du FIRST BOOT. Kobo/ARM/EPDC non testes. Les PR demeurent ouvertes et non fusionnees.
