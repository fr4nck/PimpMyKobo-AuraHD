# PMKB L06-D6q — cycles repétés du propriétaire Store

Le banc natif execute 16 cycles successifs d'ouverture/fermeture de `PMKBStoreSurfaceOwner`, alternant entre les geometries 320x480 et 1080x1440. Chaque ouverture controle la taille logique des pixels (153600 ou 1555200 octets) et la presence d'une surface ; chaque fermeture controle que le pointeur est nul, le garde detache et le compteur de pixels nul.

Ces assertions ne mesurent pas les allocations residentes reelles, le tas ni le RSS : elles verifient uniquement le contrat de surface et la comptabilite interne. Aucun Store executable, aucun hardware Kobo, aucune fusion PR #30/#31.

Commit de test : `8d65039bc3379e54426c2b6180aa0340f257dc31`. Qualification CI a verifier au SHA exact.
