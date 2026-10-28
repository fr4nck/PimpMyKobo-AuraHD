# PMKB L07-D7t — epuisement du compteur de marqueurs

Le banc C11 force le compteur de marqueurs au voisinage de la limite maximale de `unsigned`. La dernière soumission autorisée utilise cette valeur, puis toute nouvelle création est refusée par `PMKB_LIMIT` sans remise à zéro et sans réutilisation d'identifiant. Une confirmation dupliquée est rejetée.

Le même contrôle est effectué à travers `pmkb_store_eink_async_submit` : un compteur épuisé ne doit ni créer d'opération en attente, ni remplacer le marqueur de sortie, ni acquitter les rectangles `dirty` d'une surface Store valide. Aucun changement de code de production n'est nécessaire : le garde-fou existant est couvert par une régression dédiée.

Test : `02faf9a05618c3cad7645940808544ce951fcea9`. Qualifier avec la CI de ce commit avant PASS. Pas de pilote MXCFB, de Kobo physique, de fusion PR #30/#31 ni d'écriture FIRST BOOT/P2.
