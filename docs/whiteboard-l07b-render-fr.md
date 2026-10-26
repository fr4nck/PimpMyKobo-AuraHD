# PMKB Tableau blanc — L07-B : rendu sur PMKB-UI (hôte)

Le modèle C11 de L07-A est rendu directement dans le framebuffer gris 8 bits existant de PMKB-UI, sans deuxième tampon image. Le module `experimental/whiteboard-v0/pmkb_whiteboard_render.h` propose un rendu de segment entier (Bresenham), des empreintes carrées d'épaisseur 1 à 25, un mapping des 16 gris vers 0..255 (`shade*17`) et deux modes : `render_commit` pour le dernier trait validé ; `render_replay` après undo/redo/clear.

Les surfaces sont conservées par leur propriétaire. Toutes les écritures passent par `pmkb_surface_rect`, qui borne les rectangles et suit les pixels effectivement modifiés. Aucun `pmkb_surface_present`, callback EPDC ou rafraîchissement réel ne fait partie de ce lot. Après une annulation undo, la relecture efface puis redessine ; le coût est supérieur à un simple ajout de trait, mais borné et sans allocation supplémentaire.

Le test `tests/whiteboard_render_tests.c` vérifie des segments, les 16 gris représentés par le gris 8 bpp, les limites dirty, undo, redo, clear et les refus sur géométrie incompatible. `tests/test_whiteboard_model.py` compile ce banc avec le vrai `pmkb_surface.c` sur GitHub Actions Linux et Windows (Python 3.11) sans installation de nouvelle dépendance. **La CI au commit final doit être SUCCESS avant qualification PASS.**

Limitations : entrée tactile réelle, épaisseur circulaire, gomme, restauration P3, export graphique, réutilisation du framebuffer entre sessions et politique de rafraîchissement partiel EPDC ne sont pas qualifiés. Application Tableau blanc toujours non lancée ; FIRST BOOT, P1, P2, P3 et recoveryfs restent intacts.
