# PMKB L07-D7p — contrat asynchrone de zone dirty

L'interface experimentale `pmkb_store_eink_async.h` distingue la soumission (marqueur en attente, dirty conserve) et la confirmation. Un echec ou un marqueur errone ne peuvent pas acquitter la surface. Une completion positive ne consomme le dirty que si la meme surface encore vivante est fournie et si son compteur de pixels modifies est inchange depuis la soumission. Une mutation entre submit et complete oblige a soumettre de nouveau.

Le test C11 du Store couvre soumission, refus d'un marqueur concurrent, mauvais marqueur, echec, reprise, mutation avant confirmation, puis confirmation sans mutation.

**Limites importantes :** modele purement hote sans transport EPDC ni attente materielle. L'appelant doit garantir la duree de vie et l'exclusivite de la surface fournie jusqu'a la confirmation ; apres fermeture, ne jamais repasser un pointeur detruit. Pas encore de copie immuable des pixels envoyes : le modele ne vaut pas protocole de DMA ni de transport asynchrone reel. Les mutations synchrones sont detectees par le compteur `changed_pixels`, sans garantie de synchronisation multithread. Aucun acces Kobo, FIRST BOOT/P2, aucune activation Store ni fusion PR.

Code/test : `4025457b96acb56ef55e0ac7a863dacb834b15e2`, `8f43a9a29359ea9473276ad155c1c2461a48de15`. CI a qualifier.
