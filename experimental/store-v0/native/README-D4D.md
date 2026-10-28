# PMKB Store L06-D4d — suppression facultative des redessins identiques

Le rendu historique `pmkb_store_paint_page()` demeure inchangé : la mesure
sur la véritable surface PMKB-UI sert de **témoin** et ses invalidations
restent comptabilisées. Le nouveau `pmkb_store_paint_page_cached()` est
une variante strictement **facultative**. Elle valide d'abord toutes les
géométries, calcule une empreinte FNV-1a 64 bits du contenu visible de la
page (dimensions, pagination, libellés, versions, identifiants et état
des suppressions), puis évite tous les callbacks si le rendu est identique.

L'état `PMKBStorePaintCache` tient en quelques dizaines d'octets,
sans allocation dynamique, réseau, disque, bibliothèque externe ou daemon.
Il reste lié au contexte et aux fonctions de dessin. Le cache **n'est pas
une preuve cryptographique** et ne valide aucune application installée.

**Règle impérative d'utilisation :** l'appelant possède le cache et appelle
`pmkb_store_paint_cache_reset(&cache)` dès qu'un autre écran, un autre
dessinateur, un rafraîchissement complet ou une réinitialisation du buffer
peut modifier la surface, même si les métadonnées Store sont inchangées.
Sans cette invalidation explicite, l'optimisation ne garantit pas un rendu
correct. L'API par défaut, sans cache, reste disponible. Ne pas relier
implicitement cette optimisation au Launcher tant que la PR #30 et la
PR #31 demeurent séparées.

Le banc `test_store_real_surface.c` mesure, sur les trois géométries
de simulation, `changed_pixels` après deux dessins du même catalogue :
1. témoin ancien : nombre de pixels réécrits non nul ;
2. variant cache : 0 pixel réécrit et aucun dirty rectangle ;
3. une modification de libellé ou du compteur de retraits réactive le
dessin ; une surface modifiée ailleurs doit être explicitement réarmée ;
4. une page forgée ne modifie aucun pixel, même avec un cache rempli.

La CI Python 3.11 sur Linux et Windows utilise les deux fichiers
`pmkb_ui.h` et `pmkb_surface.c` **réels, épinglés** de la PR #30,
sans les fusionner. Le runner affiche les métriques du banc natif.
Ces mesures hôte ne sont ni des mesures de consommation d'énergie,
ni une qualification du vrai framebuffer EPDC, de l'ARM, du tactile ou
du rafraîchissement 16 gris de la Kobo.

**Reprise L06-D4e :** confirmer la CI et les métriques, puis requalifier
les contrats d'invalidation et la consommation mémoire avant toute
connexion effective au Launcher/PMKB-UI. Aucune PR fusionnée.
