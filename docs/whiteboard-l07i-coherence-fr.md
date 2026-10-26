# PMKB L07-I — cohérence du journal et des pixels

Les CI L07-G et L07-H ont toutes deux terminé avec `SUCCESS` (Actions #40396453662 et #40396669616).

Le nouveau banc C11 `tests/whiteboard_coherence_tests.c` reconstruit à chaque contrôle une surface indépendante à partir des seuls traits visibles du journal et compare exactement tous ses octets avec l'écran courant (`memcmp` sur 320×480 pixels). Il couvre une interruption après segmentation à 96 points, Undo/Redo, CANCEL d'un trait provisoire, nouvel ajout, CLEAR, et bornage de la zone dirty. Le banc est intégré aux tests Python existants sur Linux/Windows 3.11, compilé sans dépendance supplémentaire.

Contrat : les opérations du modèle qui changent l'historique (`undo`, `redo`, `clear`) doivent être suivies de `pmkb_wb_render_replay`. Les segments validés peuvent être dessinés par `pmkb_wb_render_commit`. Une interruption n'efface pas les segments déjà validés. Le test compare le rendu observable au journal, sans prétendre qualifier un rafraîchissement physique de l'E-Ink.

Tests matériels, evdev, EPDC, FIRST BOOT/P1/P2/P3 et recoveryfs : **non concernés, non modifiés**. La réussite L07-I dépend de la CI sur le commit `8d22cbc643aadfc26b4dc525bc82f9630991af02`.
