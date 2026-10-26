# PMKB L07-M — Store synchronisé et Tableau blanc raccordé au Launcher

Cette branche a reçu depuis `main` les sources `pmkb_store_app.c/.h`, le Makefile, les sources du pont Launcher, ses tests, le système de prévisualisation et le workflow natif. Le Store est bien référencé comme application **runnable**, sans écraser son cycle de vie ni la méthode `pmkb_app_host_store_load`.

Le pont Launcher reconnaît désormais `PMKB_APP_WHITEBOARD` (ID `whiteboard`) ; lancement à la demande, surface PMKB-UI, saisie synthétique DOWN/MOVE/UP/CANCEL/INTERRUPT via `pmkb_app_host_whiteboard_touch`, Undo via `pmkb_app_host_whiteboard_undo`, protection `PMKB_UNSAVED` pour une session dessinée et fermeture explicite avec `discard=true`. Pas d'autosauvegarde. Le test `whiteboard_via_launcher` dans `native_bridge_tests.c` vérifie qu'il est impossible d'ouvrir le Store pendant le Tableau blanc et que le Store reste accessible après fermeture.

**Qualification à confirmer** sur le commit de test `37d2026c829d4a64b5e0bba63885217822dbe943` : publication des fichiers et tests ne constitue pas un résultat CI. Ne pas fusionner la PR avant les jobs natifs et les tests généraux SUCCESS.

Le Store dans `main`, les autres applications et le matériel Kobo restent inchangés. Aucun accès tactile réel, EPDC, FIRST BOOT, P1/P2/P3 ou recoveryfs et aucun déploiement de package `.pmkb`.
