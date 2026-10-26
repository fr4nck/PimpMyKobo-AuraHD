# PMKB — L07-C : événements tactiles synthétiques

L'adaptateur C11 `pmkb_whiteboard_touch.h` relie les événements DOWN/MOVE/UP/CANCEL au modèle de traits et au rendu PMKB-UI. Les coordonnées sont logiques et déjà normalisées ; aucun `evdev`, ZForce, pilote ni calibration tactile n'est activé.

Le dessin est **différé jusqu'au UP** : les MOVE alimentent seulement le journal provisoire, l'annulation CANCEL n'inscrit aucun pixel, et un UP valide déclenche le rendu du trait confirmé via `pmkb_wb_render_commit`. Les événements hors bornes et les doublons DOWN/UP sont refusés sans acquitter ni modifier le framebuffer. Les changements du framebuffer restent suivis par `pmkb_surface_rect`.

Tests : `tests/whiteboard_touch_tests.c` compilé avec le vrai `pmkb_surface.c` par `tests/test_whiteboard_model.py` sur les hôtes Linux et Windows. Contrôles : MOVE isolé, DOWN concurrent, coordonnées invalides, CANCEL sans image modifiée, UP valide, rectangles dirty, TAP point isolé en bordure, type inconnu, écran libéré.

**Réserve :** aucune trace physique Aura HD, résolution multitouch, coordonnées brutes, échantillonnage, pression ou rendu en cours de mouvement. Les longs gestes demeurent bornés à 96 points. Aucun accès matériel, microSD, P1/P2/P3, FIRST BOOT ou serveur.

La qualification dépend du résultat effectif de la CI du commit de test `c5174ee3f5e523196c284d5e579ef08ae1072c10`.
