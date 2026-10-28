# PMKB — L07-D : gestes tactiles interrompus

Le flux tactile peut perdre `UP` (contact interrompu, application suspendue, perte du périphérique). Dans ce cas, il est interdit d'inventer un trait complet ou de laisser un geste en cours bloquer la session.

L'API host-only fournit désormais `PMKB_WB_TOUCH_INTERRUPT` et `pmkb_wb_touch_interrupt(board)`. Ces deux chemins annulent le trait **non validé**, sans toucher aux traits déjà enregistrés ni au framebuffer. L'appel de secours direct fonctionne même si la surface PMKB-UI a été libérée. Appeler explicitement cette opération lorsqu'une perte de flux est détectée par le futur adaptateur tactile ; il n'y a pas de délai arbitraire ni de surveillance active.

Les coordonnées hors bornes pendant `MOVE`/`UP` sont refusées et ne valident pas le trait ; le producteur doit appeler `INTERRUPT` s'il détermine que le contact ne reviendra pas. Un nouveau `DOWN` pendant un trait encore actif reste refusé : aucun abandon implicite de données. Un `UP` reçu après une interruption est rejeté. Les appels répétés à l'interruption sont idempotents (`NO_CHANGE`).

Test C11 dans `tests/whiteboard_touch_tests.c` : perte `UP`, aucune écriture graphique, conservation des traits validés, refus d'un `UP` tardif, interruption sans surface et entrée nulle. Qualification CI de `9afb27f7e4e86abb1fca2920ecdf8b32f6247c41` requise avant PASS.

Simulation séquentielle sur hôte uniquement, aucun accès ZForce/evdev, Kobo, microSD, P1/P2/P3 ou recoveryfs.
