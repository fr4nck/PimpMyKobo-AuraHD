# PMKB — L07-K : propriété de l'application native Tableau blanc

La CI précédente a démontré que la sortie PGM P5 passait sur Linux mais échouait sur Windows 3.11, à cause de la traduction des fins de ligne en mode texte. Correctif `d37a8fc4` : `_setmode(_fileno(stdout), _O_BINARY)` sous Windows uniquement ; qualification CI en cours.

L07-K ajoute `pmkb_whiteboard_app.h`, un **propriétaire d'application autonome** préparant le futur raccord au Launcher : le modèle C11 est alloué seulement à l'ouverture, PMKB-UI possède le framebuffer gris, fermeture libère les deux, événements tactiles synthétiques et opérations undo/redo/clear synchronisent le journal et les pixels. Le moteur existant ne change pas, aucun service permanent ou accès Kobo.

Le test `whiteboard_app_tests.c` vérifie création, dessin, undo/redo, clear, fermeture répétée et géométrie invalide. `tests/test_whiteboard_model.py` l'exécute par compilation C11 sur Linux/Windows Python 3.11.

**La PR #32 reste brouillon.** Le pont Launcher natif `PMKB_APP_WHITEBOARD` n'est pas encore ajouté : commencer par une CI verte de ce propriétaire, puis qualifier une intégration avec `pmkb_launcher_bridge.{c,h}` sans perturber Notes, Calculatrice et Store. Aucune installation automatique depuis le Store, aucun packaging `*.pmkb`, aucun accès P3/P2/EPDC/evdev ou matériel.

Preuves : CI PGM Windows et cycle de vie app **en attente** au dernier relevé ; ne pas les compter PASS avant statut SUCCESS.
