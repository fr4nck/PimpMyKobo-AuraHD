# PMKB L07-F — segmentation optionnelle des gestes longs

La CI du lot L07-E [#40395374644](https://github.com/fr4nck/PimpMyKobo-AuraHD/actions/runs/40395374644) est SUCCESS. Le lot L07-F ajoute `pmkb_wb_touch_stream_move`, une opération **opt-in** de MOVE : le comportement strict historique reste inchangé.

Au 97e point, le journal peut valider les 96 points déjà présents, dessiner ce tronçon, puis reprendre un nouveau trait à partir de son dernier point ; le nouveau point est enregistré dans cette seconde portion. La frontière est donc répétée sans trou dans la ligne et les propriétés d'épaisseur et de gris sont conservées. La segmentation n'intervient pas s'il manque de la place pour deux portions dans le journal de 64 traits : `PMKB_WB_LIMIT` est renvoyé avant toute modification et les 96 points restent en cours. Les événements invalides sont rejetés.

**Limite fonctionnelle explicite :** une fois un tronçon validé, une interruption ne peut annuler que la portion encore provisoire. Undo/Redo opèrent par tronçon et non par geste continu ; une commande Undo globale par geste pourra être étudiée ultérieurement. Aucun pixel n'est tracé avant la validation d'une portion. Aucune opération de stockage, de réseau ou d'affichage matériel.

Tests C11 : continuité du point 95, passage au point 96, confirmation finale au point 97, invalidation du rectangle exact et undo de la dernière portion. Test hôte Linux/Windows via `tests/test_whiteboard_model.py`, CI à qualifier sur le commit `8b22995c1ec3343076d496c88a3838385a20d203`.
