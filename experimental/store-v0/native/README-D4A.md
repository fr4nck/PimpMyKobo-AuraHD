# PMKB Store L06-D4a - raccord de dessin passif

`pmkb_store_paint_page(view, page, painter)` emet des operations de rectangles
et de texte **uniquement** dans le moteur de surface fourni par l'appelant.
Pas de moteur graphique concurrent, framebuffer, EPDC, pilote tactile,
installation, suppression, reseau ou lancement d'application.

Le contrat `PMKBStorePainter` a deux callbacks : `rect` et `text_box`.
Leurs parametres correspondent aux operations existantes de la PR #30
(`pmkb_surface_rect`, `pmkb_surface_text_box`). La compatibilite est
proposee via de petits wrappers C11 dans `pmkb_store_paint.h` : la branche
qui possede `pmkb_ui.h` doit **inclure ce fichier avant** l'entete Store.
Les wrappers ne sont compiles que si `PMKB_UI_H` est defini ; **aucune
fusion de la PR #30 ou activation de `PMKB_APP_STORE` n'a lieu ici**.

Exemple de branchement ulterieur (apres integration explicite de la PR #30) :

~~~c
#include "pmkb_ui.h"            /* PMKBSurface de la PR #30 */
#include "pmkb_store_paint.h"   /* callbacks passifs */

/* `surface` est deja initialise par le moteur PMKB-UI. */
PMKBStorePainter painter = pmkb_store_painter_for_ui(surface);
PMKBStorePage page;
if (pmkb_store_page_build(view, surface->width, surface->height,
                          index, &page) == PMKB_STORE_PAGE_OK) {
    (void)pmkb_store_paint_page(view, &page, &painter);
}
~~~

L'appel est **statique et volontaire**, et ne fait ni `pmkb_surface_present`
ni rafraichissement physique : l'application qui controle PMKB-UI decide
quand presenter le dirty rectangle. Le rendu dessine un fond blanc, un
en-tete `STORE - APERCU`, des lignes alternant blanc/gris, les noms et
versions, puis une pagination et un nombre de suppressions inachevees.
Les noms des dossiers de quarantaine restent invisibles. Tous les textes
restent inertes. Le moteur PMKB-UI a un repertoire de glyphes restreint :
un caractere non pris en charge peut etre rendu comme `?`.

Les petits ajustements de hauteur du cadre version (20 ou 30 pixels au
lieu de 16 ou 21) respectent les glyphes de 20/30 pixels du moteur de
surface de la PR #30. Le prevol reconstruit et compare la geometrie
complete avant le premier callback pour refuser les pages forgees.

Validation hote : `tests/test_store_paint_c11.py` compile le code natif
sans telecharger de toolchain et appelle des doubles **compatibles avec les
signatures** de la PR #30. Le vrai moteur de la PR #30 n'est pas lie dans
la CI Store tant que les deux branches restent distinctes. Les essais
locaux et la CI ne prouvent ni le rendu physique e-ink ni la performance ARM.

**Suite L06-D4b** : verifier la CI, puis tester la jonction avec la
vraie source `pmkb_surface.c` dans un environnement hote sans fusionner
les PR, si les fichiers disponibles le permettent. Aucune autorisation
d'ecriture physique n'est donnee par cette documentation.
