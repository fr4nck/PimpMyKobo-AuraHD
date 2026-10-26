# PMKB L06-D4b — Qualification de la vraie surface PMKB-UI

Le test `tests/test_store_real_surface.py` lie `pmkb_surface.c` et
`pmkb_ui.h` du commit épinglé `e2907a1` (PR #30) à l'adaptateur Store
de la PR #31. Les deux fichiers réels sont récupérés dans GitHub Actions
par un **fetch Git filtré, profondeur 1, du même dépôt**, puis leur SHA Git
est vérifié. Aucun dépôt complet, firmware, dépendance ou archive téléchargé.
Les fichiers sources restent uniquement dans le répertoire Temp du runner,
sans vendoring, fusion ni changement de la PR #30.

L'essai C11 examine trois dimensions, les pixels noirs et gris, les rectangles
invalidés, l'absence de mutation du catalogue et le refus d'une page forgée
**avant tout dessin**. Il ne déclenche aucun `surface_present`, EPDC,
tactile, réseau ou lancement d'application. Il se limite aux jobs GitHub
Actions Python 3.11 Linux/Windows disposant déjà d'un compilateur C11 ;
ailleurs il signale SKIP, pas PASS.

Résultat local du sous-lot avant CI : **nouveau test non exécuté avec les deux
vraies sources** ; la CI doit confirmer la compilation et les assertions.
Les tests D4a, précédemment verts, ne suffisent pas à qualifier cette liaison.
Aucune recette Kobo, ARM ou e-ink physique n'est revendiquée.
