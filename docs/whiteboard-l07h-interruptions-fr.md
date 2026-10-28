# PMKB L07-H — interruptions entre tronçons et saturation

Qualification de L07-G à vérifier sur le workflow [#40396453662](https://github.com/fr4nck/PimpMyKobo-AuraHD/actions/runs/40396453662).

Le banc `tests/whiteboard_stream_tests.c` comprend deux nouvelles régressions :

- Quand un geste a déjà franchi 96 points et validé son premier tronçon, un événement `INTERRUPT` abandonne seulement le tronçon courant. Le tronçon validé reste visible et peut ensuite être retiré/rétabli par Undo/Redo.
- À 63 traits déjà enregistrés, une tentative de segmenter le 64e trait refuse de produire un tronçon qui ne pourrait pas être poursuivi. `PMKB_WB_LIMIT` est retourné, le journal des 63 traits est préservé et les 96 points du geste en cours restent annulables.

Le modèle C11 reste sous `32768` octets par contrat statique ; aucune allocation ni bibliothèque supplémentaire. Les tests sont exécutés par `tests/test_whiteboard_model.py` sur Linux/Windows en CI Python 3.11. Aucun résultat L07-H n'est déclaré avant le verdict de la CI au commit de test `b78e61d79af51eaa0f53f233a8c9f8e9ef16e811`.

La Kobo physique, P1/P2/P3 et FIRST BOOT ne sont pas modifiés ; pas de backend tactile, EPDC ni service.
