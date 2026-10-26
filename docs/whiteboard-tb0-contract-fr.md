# PMKB — Tableau blanc TB0, modèle hors ligne (L07-A)

**Périmètre : journal de traits C11 et qualification sur hôte.** C'est le premier sous-lot de l'application optionnelle `Tableau blanc`, d'après l'audit `docs/kobo-whiteboard-forks-audit-2026-10-25-fr.md`. Aucun code du projet JavaScript tiers n'est incorporé.

## Contrat livré

Source : `experimental/whiteboard-v0/pmkb_whiteboard_model.h`.

- Surface logique de 1 à 1440 pixels sur chaque axe (inclut 320×480, 1080×1440 et 1440×1080).
- `DOWN` démarre un trait avec un niveau de gris **0–15** et une épaisseur **1–25** ; `MOVE` ajoute un point ; `UP` valide le trait, y compris un point isolé. Les coordonnées hors limites sont refusées, jamais tronquées silencieusement.
- `CANCEL` supprime uniquement le trait en cours, sans effacer l'historique d'annulation.
- `UNDO` / `REDO` changent le curseur de visibilité dans un journal borné. Un nouveau trait **validé** après undo remplace la branche redo ; les modifications non validées ne la détruisent pas.
- `CLEAR` est un effacement explicite, destructif et **non annulable** dans TB0. Toute opération d'historique pendant un trait actif est refusée.
- Limites fixes : **64 traits**, **96 points par trait**, coordonnées `uint16_t`, aucun allocateur ou tableau de pixels inclus. Contrôle `_Static_assert` : modèle < 32 KiB. Le modèle seul ne contient aucune boucle d'événements ni timer.

Les codes de retour distinguent `OK`, `INVALID`, `LIMIT` et `NO_CHANGE`. Un dépassement de points conserve le trait en cours (annulable) ; un dépassement de traits ne modifie pas le journal.

## Qualification et compatibilité

- Source des tests : `tests/whiteboard_model_tests.c`.
- Pont de CI : `tests/test_whiteboard_model.py`, compilation par un compilateur C11 déjà installé, sans installation de dépendance. En Actions, exécuter la preuve sur Linux et Windows, Python 3.11 uniquement, pour éviter huit compilations identiques.
- Scénarios : validation géométrique et entrée, dot et coins extrêmes, niveaux de gris/épaisseurs, événements invalides, duplicata de points, undo/redo, `CANCEL`, branche redo remplacée à `UP`, débordement de traits et de points, effacement.
- Une présence du test n'est **pas** un PASS : attendre une exécution effective de CI et enregistrer son résultat.

## Hors périmètre TB0

Aucun framebuffer, bitmap, traçage de segments, rétablissement après reboot, enregistrement P3, export PNG/SVG, pression de stylet, gomme, synchronisation réseau, accès `evdev`/ZForce, ioctl EPDC/MXCFB, intégration au Store ou au Launcher. Le Tableau blanc ne devient **pas** une application exécutable avec ce lot.

**L07-B envisagé :** transformer les traits validés en pixels sur la surface gris 8 bits PMKB-UI déjà existante, avec invalidations bornées et tests hôte. **TB1** traitera séparément une éventuelle persistance versionnée et atomique sur les données utilisateur P3 ; ne jamais écrire dans P2.

La cible physique Kobo Aura HD (i.MX50, 512 Mio) reste **non qualifiée**, et les images FIRST BOOT/P1/P2/P3/recoveryfs ainsi que les propriétés de récupération ne sont pas modifiées. Aucun téléchargement de firmware ni accès physique.
