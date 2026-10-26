# PMKB L06-D6d — garde frugal de surface au point de jonction Store

Le fichier `pmkb_store_launcher_guard.h` de la **PR #31** définit un
contrat C11 *header-only* destiné à la **prévisualisation passive** du Store.
Il dépend du **véritable** `pmkb_launcher_bridge.h` de la PR #30 et réutilise
`pmkb_store_ui_preview.h`, sans modifier le Launcher ni ses routes.

## Garanties et limites

- Un appel `enter(guard, host, dedicated_surface)` exige un hôte valide
  et une surface distincte de celle exposée par `pmkb_app_host_screen(host)`.
  Une simple copie de la structure pointant sur **le même buffer gris** est
  également refusée. Les dimensions restent vérifiées par D6a.
- Le garde mémorise l'application et son pointeur d'instance au moment de
  l'entrée. `draw()` revérifie **avant chaque dessin, y compris un cache-hit**.
  Si une autre application a été lancée/fermée, si un alias a été introduit
  ou si l'état du Launcher est incohérent, l'aperçu est **détaché sans dessin**.
- Le Store emprunte une surface déjà créée séparément : **aucun deuxième
  framebuffer n'est alloué par le garde**, aucune activité d'arrière-plan,
  réseau, disque, rafraîchissement EPDC, événement tactile ou exécution
  d'application. `PMKB_APP_STORE` demeure `runnable=false`.
- `leave()` détache la surface et vide le cache. Après un dessin externe
  **sur le buffer Store**, appeler `external_draw()` reste obligatoire.
  Le garde ne peut pas détecter les écritures effectuées sans notification.
- Un test de **séparation de pointeur/buffer** n'est **pas une preuve formelle
  de propriété mémoire** : des zones partiellement chevauchantes ou des
  allocations volontairement falsifiées restent hors contrat. Le vrai
  routeur devra créer et posséder la surface Store et garantir sa durée
  de vie (hôte et surface plus longs que le garde). La fonction D6a brute
  demeure disponible ; tout nouveau branchement au Launcher doit utiliser
  **exclusivement cette façade gardée**, pas la fonction brute.

## Qualification

`native/test_store_launcher_isolation.c` est étendu, dans le banc déjà
réalisé en CI sur les **sources exactes** `pmkb_launcher_bridge.c`,
`pmkb_surface.c`, `pmkb_backend.c` et les en-têtes PR #30 épinglés
et vérifiés par leurs empreintes Git. Notes et Calculatrice restent
**des doubles de cycle de vie**, pas leurs implémentations métier.

Les cas testés couvrent : absence d'hôte, Store passif à Launcher vide,
transition vers Notes puis refus d'un ancien `draw`, refus de la
surface Notes ou d'un alias de son buffer, acceptation d'un buffer Store
distinct et préservation de Notes, notification d'écriture externe,
fermeture de Notes et refus du `draw` périmé, puis mêmes refus pour
Calculatrice. Une erreur ne doit pas dessiner sur l'autre surface.

**NON EXÉCUTÉS** : véritable Kobo, ARM, EPDC, tactile, 16 gris matériel,
consommation, données réelles Notes ADR-005 et accès P3. FIRST BOOT,
P2/recoveryfs, huit illustrations et PR #30 restent inchangés.
Les PR #30/#31 demeurent séparées et non fusionnées.

**Prochain L06-D6e** : vérifier CI et fiabiliser si nécessaire la
discipline de durée de vie des surfaces lors des transitions, avant toute
intégration effective au Launcher. Ne pas entamer L07.
