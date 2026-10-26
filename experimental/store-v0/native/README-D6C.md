# PMKB L06-D6c — isolation entre le Launcher et le Store passif

Le **vrai** `pmkb_launcher_bridge.c` de la PR #30 conserve
`PMKB_APP_STORE` avec `runnable=false`. Le Launcher n'a aucun écran
Store : `pmkb_app_host_screen()` n'expose que Notes ou Calculatrice.

Cette qualification ajoute `native/test_store_launcher_isolation.c`.
Le test GitHub Actions Python 3.11 récupère seulement les sources/en-têtes
requis du commit PR #30 **épinglé**, vérifie les SHA Git individuels puis
compile le vrai bridge, la vraie surface et le vrai backend de présentation
avec le Store natif de la PR #31. Aucune fusion, aucun checkout complet
ni téléchargement de dépendance ou de firmware.

**Portée exacte :** Notes et Calculatrice sont représentées par des
*doubles de cycle de vie* (initialisation/libération de surfaces synthétiques,
gestion fictive d'événements). Leurs véritables moteurs métier, le stockage
Notes ADR-005 et les calculs ne sont **pas** testés ici.

Les tests contrôlent :
- tentative de lancer Store lorsque le Launcher est vide : refus sans
  créer d'instance ou exposer une surface Store ;
- lancement Notes : vrais appels du bridge, surface Notes autonome,
  événements toujours routés, backend de présentation dirigé vers Notes ;
- prévisualisation Store sur **un buffer dédié distinct** : la surface Notes
  et le compteur synthétique de notes non enregistrées demeurent inchangés ;
- lancement Store pendant Notes : refus, Notes demeure active ;
  `pmkb_app_host_close(false)` renvoie `PMKB_UNSAVED` sans fermer Notes ;
- fermeture explicite Notes et libération indépendante de la surface Store ;
- Calculatrice active : refus de lancer Store sans altérer ni libérer
  l'instance Calculatrice.

**Risque subsistant :** l'API bas niveau de l'aperçu Store accepte une
`PMKBSurface *` empruntée, y compris potentiellement une surface Notes si
un futur appelant commet une erreur. La présence du test n'empêche pas
physiquement ce mauvais branchement. L'intégration devra imposer une surface
Store dédiée (ou un garde explicite côté hôte) avant toute nouvelle route UI.
Le présent lot ne crée aucune route Launcher.

NON EXÉCUTÉS : véritable Kobo Aura HD, ARM, EPDC, tactile, P3 et autonomie.
PR #30/#31 toujours séparées, FIRST BOOT, P2, Notes ADR-005 et illustrations
inchangés.

**Prochain sous-lot L06-D6d :** confirmer la CI, puis ajouter si nécessaire
un garde de propriété de surface au point de jonction passif, sans activer
les applications ou fusionner les PR.
