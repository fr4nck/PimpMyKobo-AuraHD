# PMKB L07-D7y — transitions Launcher pendant une mise à jour en attente

## Objectif

Éviter qu'un marqueur de rafraîchissement Store survive au changement d'application et puisse acquitter à tort une autre surface. Le Store reste un aperçu **passif** : aucune route Store exécutable n'est enregistrée.

## Modification

Le contrôleur expérimental `pmkb_store_eink_lifecycle.h` expose deux opérations :

- `pmkb_store_eink_lifecycle_launch_app(owner, kind, width, height)` : annule d'abord le marqueur simulé, ferme la surface Store, puis délègue au Launcher pour ouvrir Notes ou Calculatrice.
- `pmkb_store_eink_lifecycle_close_app(owner, discard)` : applique le même ordre avant de demander la fermeture de l'application active. Le refus `PMKB_UNSAVED` de Notes reste respecté.

Les transitions contournant ce contrôleur (appel direct au routeur ou au Launcher) ne disposent **pas** de cette garantie. L'adaptateur ne remplace ni un pilote matériel ni la synchronisation des accès DMA.

## Tests

Le banc C11 du vrai pont Launcher (avec doubles métier Notes/Calculatrice) vérifie :

1. Aperçu Store → soumission → ouverture Notes : annulation, absence de pixels Store résiduels et refus d'un ancien acquittement.
2. Notes modifiées → nouvel aperçu et soumission → fermeture sans abandon : `PMKB_UNSAVED`, Notes préservées, Store libéré, marqueur invalidé.
3. Fermeture explicite des Notes avec abandon.
4. Aperçu Store → soumission → lancement Calculatrice : même invalidation et conservation du cycle de vie de Calculatrice.
5. Store toujours non lançable (`PMKB_NOT_FOUND` depuis un hôte vide).

Code `3458768c4d9648048a7b43d74e587afe04c2afa4` ; tests `eacb57c98c7413f08308aa6b61a4e4c8ae6f21b7`. **La qualification D7y requiert une CI réussie sur ce commit de test.**

## Limites

Simulation séquentielle sur hôte uniquement : aucune preuve de sûreté en cas de callbacks concurrents, de rafraîchissement EPDC réellement en vol ou de fermeture physique d'un buffer partagé. PR #30 et #31 non fusionnées. Aucune écriture sur la Kobo, FIRST BOOT, P1, P2, P3 ou recoveryfs.
