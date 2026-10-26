# PMKB L06-D6a — passerelle d'aperçu Store sur la vraie surface PMKB-UI

La PR #30 définit des surfaces distinctes pour Notes et Calculatrice et réserve
`PMKB_APP_STORE` avec `runnable=false`. Nous **ne modifions pas** cet état.
Ce sous-lot fournit `pmkb_store_ui_preview.h` à la PR #31 : un adaptateur
C11 d'aperçu **passif** vers une surface `PMKBSurface` fournie par l'hôte.

Contrat minimal :
- `pmkb_store_ui_preview_init` : instance cachée, aucune surface attachée.
- `pmkb_store_ui_preview_enter` : attache une surface PMKB-UI valide pour
  320×480, 1080×1440 ou 1440×1080 et invalide le cache avant le premier dessin.
- `pmkb_store_ui_preview_draw` : calcule et contrôle la page demandée,
  transmet les rectangles/textes aux **primitives existantes** ;
  aucune commande `present()`, EPDC, lancement ou installateur.
- `pmkb_store_ui_preview_external_draw` : notification obligatoire si
  une autre vue modifie la surface empruntée.
- `pmkb_store_ui_preview_leave` : cache vidé et surface détachée, tout dessin
  refusé jusqu'à `enter`. Les paramètres invalides échouent sans peindre.

L'adaptateur emprunte la surface, n'alloue pas de framebuffer, n'ouvre aucun
fichier, ne télécharge rien et ne gère aucun événement tactile. La PR #30
reste séparée. Le code s'appuie sur `pmkb_ui.h` **réel** uniquement lorsque
le test GitHub Actions Python 3.11 récupère ses deux sources épinglées et
les compile avec Store : pas de copie permanente ni de fusion.

Le banc `test_store_real_surface.c` exerce une surface réellement initialisée :
entrée, premier dessin, cache-hit sans invalidation, modification externe
explicitement notifiée, changement de page, rejet d'une page hors limites,
sortie, retour, attachement invalide, conservation du catalogue, détachement.
Le test ne peut pas garantir qu'un futur Launcher signale **toutes** ses
écritures externes ; cette responsabilité reste hors de ce sous-lot.

Non exécuté/qualifié : lien permanent dans le Launcher, ARM, Kobo physique,
e-ink 16 gris, EPDC, tactile, P3, autonomie. FIRST BOOT et P2 préservés.

**Suite L06-D6b** : vérifier CI et logs du raccord réel, puis examiner les
contrats de présentation/dirty rectangles et les limites de partage de surface
avant tout branchement au Launcher. Aucun Store exécutable et aucune PR fusionnée.
