# PMKB L06-D6j — audit negatif du raccord Store/Launcher

## Changement

Le test `native/test_store_launcher_isolation.c` verifie le refus d'un hote inactif mais incoherent (`active == PMKB_APP_NONE` avec instance non nulle), puis l'invalidation d'un garde actif quand cet etat est introduit entre deux dessins. Le test remet explicitement l'hote synthetique dans un etat coherent apres chaque scenario.

Le code du garde, les modules Notes/Calculatrice et le bridge Launcher ne sont pas modifies. Les fonctions Store bas niveau restent reservees a l'adaptateur passif et ne constituent pas une route executable.

## Limites et suivi

Verifier la CI sur le commit `7e2e92082413c3aadcd906bf2c45ffafc15e1559` avant de qualifier ce lot. La fixture emploie le pont Launcher reel et des doubles de metier Notes/Calculatrice. Ceci n'etablit aucune qualification ARM, Kobo physique, EPDC, tactile ou memoire embarquee.

Ne pas modifier FIRST BOOT, P2/recoveryfs, P3 physique ou fusionner PR #30/#31. La prochaine reprise doit d'abord qualifier la CI D6j, et n'ajouter du code que si un defaut concret est identifie.
