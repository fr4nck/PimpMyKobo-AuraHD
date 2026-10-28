# PMKB L07-G — Undo/Redo d'un geste segmenté

CI L07-F [#40395858149](https://github.com/fr4nck/PimpMyKobo-AuraHD/actions/runs/40395858149) : **SUCCESS**.

Chaque tronçon contient désormais un seul octet logique `continuation`, renseigné uniquement lorsque le moteur L07-F coupe un geste au 96e point. `pmkb_wb_undo()` recule jusqu'au début du geste ; `pmkb_wb_redo()` rétablit tous les tronçons consécutifs du même geste. Les traits indépendants demeurent indépendants. Le modèle reste sous la limite statique de 32 KiB et n'alloue aucune mémoire.

Le test `whiteboard_stream_tests.c` vérifie le découpage en deux tronçons, l'annulation de **tout** le geste en une commande, le rétablissement complet, puis la suppression de l'ancienne branche redo après un nouveau geste. Les anciennes fonctions de tracé et le rendu s'appuient toujours sur `PMKBSurface`.

**Limite à conserver :** un geste encore actif doit être terminé ou interrompu avant Undo/Redo. Une interruption après un tronçon déjà confirmé conserve celui-ci dans l'historique. L'annulation Undo le retirera ensuite. Aucun moteur graphique matériel, réseau, gestion de gestes multitouch, écriture P3 ou changement FIRST BOOT/P2.

**Qualification** : attendre la CI correspondant au commit de test `a6cc20e8973c4160cbad03b9ddea5ed8503bcdc5` avant d'annoncer PASS.
