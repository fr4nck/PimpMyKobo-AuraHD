# PMKB D7f — presentation par le routeur

Le routeur passif fournit maintenant `pmkb_store_router_present`, qui transmet uniquement sa surface Store possedee au callback `PMKBBackend` existant. Avant la presentation, il verifie la propriete, l'identite de l'application du bridge et la separation des buffers. Un etat incoherent detache le Store et refuse la presentation. Les erreurs du backend conservent les rectangles dirty selon le contrat PMKB-UI.

Tests au commit `cc9ebe56926b89f8164d8968b271e41b60d8f6fb` : backend NULL, callback manquant puis reprise valide a travers le routeur. CI a verifier avant de declarer PASS. Aucun backend EPDC reel, aucune activation Store, aucune fusion PR #30/#31 ou ecriture Kobo/FIRST BOOT/P2.
