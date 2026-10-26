# PMKB L07-D7z — validation du Launcher lors des confirmations asynchrones

## Problème corrigé

Le contrôleur Store asynchrone annulait correctement un rafraîchissement lors des transitions effectuées **par ses propres méthodes**, mais pas si un appel direct à `pmkb_app_host_launch` changeait l'application active pendant qu'un marqueur Store était en attente. La confirmation pouvait auparavant effacer le `dirty` de l'ancien aperçu.

## Correctif C11

`pmkb_store_eink_lifecycle_surface_valid` revérifie, avant **chaque soumission et confirmation** :

- La présence du framebuffer Store encore alloué ;
- L'attachement du garde à ce routeur et de l'aperçu à cette surface ;
- La visibilité de l'aperçu ;
- L'identité `active` / `instance` du Launcher depuis l'entrée de l'aperçu ;
- La séparation mémoire entre Store et application active.

En cas d'incohérence, le contrôleur **annule le marqueur avant de fermer le Store**, refuse l'opération et laisse l'application réellement active intacte. Les identifiants de marqueurs ne sont pas recyclés.

## Régressions

- Le Launcher démarre directement Calculatrice après une soumission : la confirmation périmée est refusée, les pixels Store sont libérés, Calculatrice reste active. Une réouverture explicite puis un nouveau marqueur permettent une confirmation correcte.
- Le Launcher démarre directement Notes avant toute soumission : celle-ci est refusée sans changement de la valeur de sortie ni conservation d'un framebuffer Store.
- Le routeur Store est fermé directement pendant un marqueur en attente : l'ancienne confirmation est refusée et le marqueur simulé est annulé lors de l'appel au contrôleur.

Code : `2e4a814a41f5c5727aab2a2edce50e9f558e07cc`.
Tests : `fe1ec551ed113fb987eeb696464ce192147f208b`.

## Limites et risques

La comparaison de l'identité du Launcher utilise `active` et `instance` : elle n'établit **pas** de compteur de génération d'instance. Un changement externe suivi d'une réallocation à la même adresse pourrait échapper au contrôle. Un raccordement matériel devra imposer un propriétaire unique, un identifiant de génération et une synchronisation explicite des requêtes en vol.

Tests sur hôte avec doubles métier Notes/Calculatrice uniquement. La CI du commit de test doit être **SUCCESS** avant qualification D7z. Aucun pilote EPDC, accès Kobo, modification FIRST BOOT/P1/P2/P3/recoveryfs, lancement du Store ou fusion des PR #30/#31.
