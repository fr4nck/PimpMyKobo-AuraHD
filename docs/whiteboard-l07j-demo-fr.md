# PMKB L07-J — démonstration graphique reproductible

Le fichier `experimental/whiteboard-v0/whiteboard_host_demo.c` crée une surface **320×480 en niveaux de gris**, dessine deux traits via le modèle et le rendu C11 réels puis émet sur stdout une image **PGM binaire P5**. Aucun stockage, réseau ou accès à la Kobo ; ce format brut est volontairement disponible sans bibliothèque d'image additionnelle.

Qualification automatique : `test_demo_pgm_is_deterministic` dans `tests/test_whiteboard_model.py` compile le programme avec `pmkb_surface.c`, l'exécute deux fois et exige des octets identiques, l'entête `P5`, exactement 153600 pixels, les pixels noirs/gris attendus et le fond blanc. Les autres tests de modèle, tactile, segmentation et cohérence restent actifs.

Le rendu est uniquement une **démonstration sur hôte** ; ni tactile réel, ni rafraîchissement EPDC, ni application Kobo ni sauvegarde P3. Aucun changement FIRST BOOT/P1/P2/P3/recoveryfs. Attendre le résultat GitHub Actions du commit de test `d20e83af26c965e8c0981e879cdfeb02b57fd11c` avant de qualifier L07-J.
