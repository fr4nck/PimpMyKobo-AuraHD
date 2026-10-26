# PMKB L06-D6r — plan d'integration du proprietaire natif

## Objet

Raccorder ulterieurement `PMKBStoreSurfaceOwner` au routeur natif sans activer `PMKB_APP_STORE` et sans ajouter de framebuffer resident. Le module de la PR #31 alloue une surface uniquement sur `open`, la previsualisation emprunte cette surface, puis `close` detache avant de liberer.

## Frontiere entre PR #30 et #31

Le vrai `pmkb_launcher_bridge.c` de la PR #30 possede les instances Notes/Calculatrice, mais pas le Store. La PR #31 ne doit pas modifier ce bridge en avance de phase. Le futur routeur sera responsable d'un `PMKBAppHost`, d'un `PMKBStoreSurfaceOwner` initialise une seule fois et de la sequence suivante :

1. Initialiser l'hote et le proprietaire Store.
2. Lors d'une previsualisation passive, appeler `pmkb_store_owner_open` puis `pmkb_store_launcher_guard_draw`.
3. Avant de changer/fermer l'application active ou d'abandonner la vue Store, appeler `pmkb_store_owner_close`.
4. Fermer Notes avec le mecanisme existant `PMKB_UNSAVED`, sans contournement.
5. A l'arret du routeur, fermer le Store avant de detruire l'hote.
6. Garder `PMKB_APP_STORE` reserve et `runnable=false` tant qu'une implementation de route et son test d'integration ne sont pas disponibles.

## Criteres avant raccord effectif

- Tests du vrai routeur, sans doubles metier, couvrant creation/destruction, retour Notes non sauvegardees, alias de pixels et defauts de surface.
- Mesures sur hote du pic memoire et du nombre d'allocations, puis sur ARM/Kobo sous controle specifique.
- Aucune dependance a Nickel, aucun service permanent et aucune ecriture FIRST BOOT/P2/P3.
- Evaluer la necessite d'une surface Store pleine resolution : si possible, rendre vers un tampon partage uniquement avec un arbitre exclusif prouve. Ne jamais partager directement le buffer Notes par convenience.
- PR #30 et #31 restent ouvertes et non fusionnees pendant cette phase.

## Statut

Documentation d'integration uniquement, aucun raccord effectif ni activation Store. CI D6q a controler separément. Prochain lot : prototype routeur passif hors Launcher en laboratoire avec banc C11, sans modification du bridge PR #30.
