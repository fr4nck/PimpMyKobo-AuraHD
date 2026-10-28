# PMKB L07-N — aperçu natif Tableau blanc

Le raccord `PMKB_APP_WHITEBOARD` est désormais présent dans le pont Launcher de la branche PR #32, avec Store conservé exécutable. La prévisualisation hôte `pmkb_host_preview.c` accepte désormais le mode `whiteboard` ; elle lance réellement l'application, injecte un geste synthétique puis exporte sa surface PGM. Le script de contrôle `render_host_previews.py` génère et vérifie douze aperçus (320×480 et 1080×1440, incluant Notes, Calculatrice, Store, détail Store, glyphes et Tableau blanc) au lieu de dix.

**Important** : ces aperçus valident le moteur sur hôte, pas l'écran tactile de la Kobo. Les modifications de code `12f68f0` et `d553286` sont publiées, mais la qualification dépend des CI du dernier commit. Toute erreur des tests doit être traitée avant de considérer L07-N terminé ou de fusionner la PR.

Le lancement simultané d'applications reste interdit, la fermeture d'un Tableau blanc contenant des traits reste soumise à `discard`, les Notes et le Store conservent leur gestion indépendante. Aucun accès EPDC, microSD, P1/P2/P3, FIRST BOOT, recoveryfs ou installation *.pmkb.
