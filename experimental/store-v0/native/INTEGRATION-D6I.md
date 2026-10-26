# PMKB L06-D6i — matrice d'integration passive Store / Launcher

Statut : contrat d'integration uniquement. Store NON executable. PR #30 et #31 restent ouvertes, separees, brouillons et non fusionnees.

## Invariants du routeur

| Transition | Preconditions | Action obligatoire | Echec attendu |
| --- | --- | --- | --- |
| Aucun hote -> apercu Store | Hote initialise, instance NULL, surface Store dediee et vivante | guard_init, guard_enter, guard_draw | Surface NULL ou sans pixels : INVALID |
| Store -> Notes | La surface Store appartient au routeur | guard_before_destroy avant toute liberation de la surface ou de l'hote | Un ancien draw doit retourner INVALID sans modifier Notes |
| Store -> Calculatrice | Meme contrat | Detach, puis launch Calculator | Aucun dessin Store dans le framebuffer Calculatrice |
| Notes/Calculatrice -> Store passif | Instance et surface applicative vivantes, buffer Store independant | guard_enter distinct, guard_draw | Surface partagee ou copie alias : INVALID |
| Ecriture externe sur Store | Surface vivante et empruntee | guard_external_draw avant le prochain draw | Sinon cache obsolete possible : contrat non garanti |
| Store -> aucune application | Emprunts valides | guard_before_destroy puis liberer les objets proprietaires | Aucun pointeur emprunte conserve |
| Reentree | Surface nouvellement valide, etat hote coherent | guard_enter explicite | draw sans enter : INVALID |

## Proprietes a verifier lors du vrai raccord

1. Aucun appel direct du routeur a `pmkb_store_ui_preview_enter/draw` : passer par `pmkb_store_launcher_guard_*`.
2. L'instance `PMKBAppHost` et la `PMKBSurface` Store vivent jusqu'au detach ; ne jamais laisser le garde emprunter un objet temporaire.
3. La memoire des pixels Store ne recouvre aucun framebuffer Notes/Calculatrice. Les comparaisons de pointeurs seules ne prouvent pas l'absence de chevauchement partiel.
4. Apres changement d'application, toute reentree passe par le garde et son controle d'identite.
5. Aucun event tactile, processus, acces reseau ou operation disque declenche par le Store passif ; `PMKB_APP_STORE` reste `runnable=false`.
6. Respect des contraintes 512 MiB : ne pas creer de deuxieme framebuffer uniquement pour le garde et mesurer les allocations du vrai routeur avant activation.
7. Aucun changement de comportement des Notes ADR-005, du clavier commun, de la Calculatrice ou du rendu KOReader.

## Qualification existante et manquante

Les CI hote du garde atteignent 10/10 jobs au D6h (run #40338996143). Les tests sur le vrai pont Launcher epingle remplacent l'implementation metier Notes/Calculatrice par des doubles. Les points 1-7 sont des criteres d'integration future, pas des preuves d'execution sur Kobo.

**BLOQUANTS avant activation** : absence de surface proprietaire garantie, duree de vie ambigue, alias de pixels non detecte, tests ARM/EPDC non realises, ou route Store executable sans parcours explicite de revue.

## Reprise D6j

Effectuer uniquement l'audit statique des API de jonction entre PR #30 et #31 et ajouter des tests negatifs synthetiques si une lacune precise est trouvee. Ne pas fusionner les PR, ne pas modifier le firmware, FIRST BOOT, P2/recoveryfs ou la microSD physique.
