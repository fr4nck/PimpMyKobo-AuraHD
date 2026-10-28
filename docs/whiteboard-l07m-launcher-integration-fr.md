# PMKB L07-M — prévol d'intégration Launcher / Store

Le propriétaire du Tableau blanc et son adaptateur de session (`pmkb_whiteboard_app.h`, `pmkb_whiteboard_launch_seam.h`) ont été ajoutés avec tests Linux/Windows au lot L07-L. La CI de ce lot doit rester la référence tant que sa qualification n'est pas terminée.

**Blocage de synchronisation confirmé** : au prévol, la branche `feat/pmkb-whiteboard-tb0` ne contient pas `experimental/native-ui/pmkb_store_app.c`, pourtant présent dans `main`, où le Store est exécutable. Copier uniquement le pont Launcher actuel de `main` rendrait la branche non compilable. Les deux modifications provisoires du pont ont donc été annulées sur la branche, sans toucher à `main` ni à la PR.

La suite nécessite d'abord de synchroniser complètement les fichiers du Store et le système de compilation depuis `main` vers la branche, puis de tester leur cycle de vie. Ensuite seulement : enregistrement de `PMKB_APP_WHITEBOARD`, écran associé, événements de dessin séparés de `PMKBEvent`, refus de fermeture avec dessin non sauvegardé, tests de non-régression Notes/Calculatrice/Store/Tableau blanc.

**Statut** : raccordement Launcher réel NON FAIT ; aucune fusion et aucun changement à la Kobo, P1, P2, P3, FIRST BOOT ou recoveryfs. L'adaptateur Tableau blanc est isolé et présent. Les modifications documentaires n'appellent pas de nouvelle CI.
