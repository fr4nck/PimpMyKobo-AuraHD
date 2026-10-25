# PMKB — Kobo Whiteboard et ses quatre forks : audit et idée d'application Store

**Audit statique du 25 octobre 2026.** Dépôt source : [benkaiser/kobo-whiteboard](https://github.com/benkaiser/kobo-whiteboard), branche `master`, HEAD `d2a37b3df836747baa7033357269a90ab012855f`, dernier commit du **24 août 2024**. Projet commencé le **25 septembre 2023**, licence **MIT** (© 2023 Benjamin Kaiser). Comparaison des forks publics via l'API GitHub et lecture du HTML, JavaScript serveur, configuration de dépendances et branche secondaire.

**Décision : P2 / IDÉE D'APPLICATION `Tableau blanc` dans le Store `*.pmkb` ; NON INTÉGRABLE TEL QUEL au socle PMKB sans navigateur.** Les deux fonctions utiles sont **le dessin tactile simple et le partage optionnel d'un tableau avec un ordinateur**. **Aucun patch FBInk, ZForce, EPDC, noyau ou démarrage Aura HD n'est apporté par ce dépôt.** FIRST BOOT et P2 restent inchangés.

## 1. Ce que fait réellement l'application

[Kobo Whiteboard](https://github.com/benkaiser/kobo-whiteboard/blob/master/README.md) se présente comme **une page web `canvas` pour le navigateur bêta de la liseuse**, à laquelle un participant accède sur un ordinateur pour afficher le même dessin, notamment en visioconférence. Il ne s'agit ni d'un programme Linux framebuffer ni d'un plugin FBInk.

| Brique source vérifiée | Comportement réel | Conséquence PMKB |
| --- | --- | --- |
| [`index.html`](https://github.com/benkaiser/kobo-whiteboard/blob/master/index.html) | **HTML Canvas 2D** superposé, JS pour contacts souris/tactile `touchstart/move/end`, outils `Sketch` et `Erase`, épaisseur 1–25, couleurs, effacement global, plein écran, rotation CSS/canvas, rechargement | **Inspiration UX** ; développer un rendu local **monochrome/16 gris** via notre PMKB-UI/FBInk, pas embarquer de navigateur permanent |
| [`index.js`](https://github.com/benkaiser/kobo-whiteboard/blob/master/index.js) | Serveur **Node 18 + Express 4 + express-ws 5** ; création aléatoire de salles numérotées de **1000 à 9999**, WebSocket à la racine, messages `join`, `addState`, `clear`, retransmission à tous les autres clients de la salle | **Partage local éventuel** avec serveur explicite **hors Kobo** ou composant réseau à la demande après qualification ; aucune obligation d'un service Node sur les 512 Mio de l'Aura HD |
| **Modèle des coups de pinceau** | Un trait contient outil/couleur/épaisseur/coordonnées de départ et une suite de segments `fromX/fromY/toX/toY`. Le client publie `addState` **à la fin du trait** (au relâchement), pas à chaque événement de mouvement | **Retenir le journal compact de traits** pour rejouer/annuler/exporter. Ne pas annoncer une synchronisation de chaque point instantanément. |
| **Salles / synchronisation** | `GET /` redirige vers `/r/NNNN`, et un client rejoint `window.location.pathname.substring(1)`. À la connexion le serveur renvoie tous les traits `state`. Lorsqu'une salle n'a plus de clients, `cleanupRooms` efface son état lors du passage horaire suivant | **Ne pas utiliser comme stockage** : état en RAM seulement, aucune sauvegarde disque/`P3`, pas d'export texte/SVG/PNG ou d'undo/redo implémenté dans le code lu |
| [`Dockerfile`](https://github.com/benkaiser/kobo-whiteboard/blob/master/Dockerfile) | Image `node:18-alpine` et `npm install`, écoute par défaut `8080` | Référence de démo serveur uniquement ; pas de conteneur ni de dépendances téléchargées pour PMKB |
| [`LICENSE`](https://github.com/benkaiser/kobo-whiteboard/blob/master/LICENSE) | Licence **MIT** | Le code peut être adapté en respectant copyright et notice MIT, mais **aucune incorporation ni redistribution** dans cet audit |

**Limites de l'auteur, confirmées ou explicables par les sources :** le navigateur peut **zoomer involontairement** pendant le dessin, le mode plein écran ne restitue pas la barre d'outils sans rechargement, et l'affichage en rotation de 270° est incorrect depuis le navigateur de l'ordinateur. Le code utilise en outre une translation fixe de **955 pixels** (`rotateCanvas`), inappropriée comme règle générale pour notre dalle **1080×1440**. Un redimensionnement réinitialise les buffers `canvas`, et ne redemande pas systématiquement l'historique si la rotation n'est pas active.

## 2. Tous les forks publics vérifiés : quatre

La métadonnée GitHub de [benkaiser/kobo-whiteboard](https://github.com/benkaiser/kobo-whiteboard) indique **4 forks publics**. Les quatre ont été retrouvés, et leurs **branches `master`** comparées à `benkaiser:master`. Aucun fork ne transforme le projet en application native Kobo ou en backend EPDC.

| Fork | Comparaison Git de `master` | Branches / nouveautés | Décision |
| --- | --- | --- | --- |
| [Eloitor/kobo-whiteboard](https://github.com/Eloitor/kobo-whiteboard) | **0 ahead / 0 behind** | `master` uniquement ; copie identique | ARCHIVE |
| [pmpbaptista/kobo-whiteboard](https://github.com/pmpbaptista/kobo-whiteboard) | **0 ahead / 0 behind** | `master` identique après fusion amont du Dockerfile fourni via sa PR #1 (août 2024) ; branche `pb/docker` **derrière** `master` ; branche `pb/rate-limit` **+1 commit** | **Seule piste secondaire à examiner** pour la limitation réseau ; voir ci-dessous |
| [pedrosaraiva/kobo-whiteboard](https://github.com/pedrosaraiva/kobo-whiteboard) | **0 ahead / 2 behind** | Copie antérieure à l'ajout Docker/merge | ARCHIVE |
| [JoeyEremondi/kobo-whiteboard](https://github.com/JoeyEremondi/kobo-whiteboard) | **1 ahead / 2 behind** | [`421fea5`](https://github.com/JoeyEremondi/kobo-whiteboard/commit/421fea5e11e64d4db2dcd4f5eded7b83bfa5cc4f), 17 janvier 2024 : **seulement port 8080 → 10000** si `PORT` absent | Aucune innovation PMKB |

### Branche `pmpbaptista:pb/rate-limit`

[Commit `54c3559`](https://github.com/pmpbaptista/kobo-whiteboard/commit/54c35594181cf8e2dde3a9f9e9fba90c96a13d41) : ajout de `express-rate-limit@7.4.0` et d'un middleware `app.use(limiter)` avec **100 requêtes HTTP par IP pour 15 minutes**.

**Contrôle critique : ce limiteur HTTP ne borne pas le nombre, la taille ni la cadence des messages WebSocket `addState`/`clear` une fois la connexion ouverte.** Il ne répond donc pas à l'essentiel du risque lié au flux collaboratif. Pas de test indépendant de cette protection constaté. Conserver seulement l'idée d'une **régulation de flux multi-couches**, sans adopter la branche comme un correctif complet.

## 3. Points d'architecture et sécurité à ne pas recopier

1. **Identité de salle non secrète :** les salles sont **4 chiffres aléatoires** sans vérification d'unicité et aucun mécanisme de contrôle d'accès ne protège `join`. L'accès repose sur la connaissance du chemin ; une salle peut être devinée ou tomber en collision avec une salle existante. **Éviter tout partage public de contenu sensible** avec la version historique.
2. **Payloads non bornés :** `JSON.parse(msg)` sans gestion d'erreur dans le listener WebSocket, absence de schéma/limites sur `msg.state`, absence de quotas de traits et de taille des salons. Une entrée malformée, excessive ou intentionnellement hostile peut perturber le service. Le serveur ne vérifie pas non plus la validité des coordonnées dessinées.
3. **Historique fragile :** `roomState` global en RAM, nettoyage périodique des salles inactives, perte totale au redémarrage ; pas de sauvegarde/export P3 et pas de réconciliation après panne. L'outil n'est **pas** un gestionnaire de notes ou de documents.
4. **Ergonomie e-ink :** le JS est écrit pour `canvas` de navigateur, non pour une HAL à région/EPDC ; palette colorée inadaptée à un écran monochrome ; l'action `Erase` utilise des rectangles de **50×50** décalés par rapport au contact ; sauvegarde du coup de pinceau uniquement au relâchement. Aucun contrôle précis du ghosting, des marqueurs d'update ou de la consommation énergétique.
5. **Compatibilité matérielle :** le projet ne démontre **aucun test sur notre Aura HD E606C0 sans Nickel**. Un contact tactile sur l'Aura HD n'est pas une tablette graphique avec pression/stylet actif garanti ; précision et latence doivent être qualifiées physiquement.

Le logiciel original affiche un site hébergé `kobo.kaiser.lol` et recommande le partage d'URL, mais **la disponibilité de l'hébergement en octobre 2026 n'a pas été vérifiée** et n'est pas requise par PMKB.

## 4. Application native PMKB à envisager après FIRST BOOT

**Nom de travail : `Tableau blanc`**, application optionnelle `*.pmkb` utilisant **PMKB-UI/HAL existante**, sans Nickel, navigateur, Express ni serveur permanent.

| Lot | Objectif minimal à qualifier |
| --- | --- |
| **TB0 — hors ligne** | Une surface 1080×1440 qui capte **DOWN/MOVE/UP**, points dans bornes, dessine/crée des traits, gomme, efface et **annule/rétablit** ; commandes tactiles adaptées à la précision réelle et aux contraintes du socle UI |
| **TB1 — persistance** | Journal de traits compact (format local versionné) avec sauvegarde atomique vers les données utilisateur en P3 ; restauration après fermeture/reboot ; export PNG monochrome ou 16 gris et éventuellement SVG ; **aucune écriture dans P2** |
| **TB2 — moteur e-ink** | Invalidation de **rectangles** sans rafraîchir tout l'écran à chaque échantillon ; stratégie partielle et plein rafraîchissement à tester sur formes d'ondes et ghosting de l'Aura HD ; mise à jour d'écran différée à fréquence et coût CPU mesurés, aucun nombre « magique » |
| **TB3 — partage facultatif** | Partage sur LAN uniquement après action explicite, salles à identifiant suffisamment imprévisible / autorisation, limite de messages/tailles, contrôle des origines et des connexions, borne mémoire, journal durable, vérification des messages avant dessin ; **aucune connexion automatique** |
| **Recette** | Contrats hôte : traces tactiles synthétiques E606C0, rotations, trous d'événements, effacement, undo, restauration et coupure réseau ; tests d'intégration physique **seulement après qualification FIRST BOOT** |

Le modèle **de journal de traits**, **la coopération Kobo ↔ ordinateur** et **la licence MIT** sont les apports utiles. Le reste n'est pas un candidat de dépendance PMKB. **Ce lot n'autorise pas à créer une nouvelle architecture concurrente de PMKB-UI ni à modifier Mes Notes avant lecture et respect d'ADR-005.**

## 5. Bilan daté

- **PASS, inventaire public : 4/4 forks** administrativement reliés à l'original, `master` comparées, branche additionnelle `pb/rate-limit` inspectée.
- **PASS, inspection statique :** lecture du README, `index.html`, `index.js`, `package.json`, `Dockerfile`, `LICENSE`, comparaison des changements des forks et de la branche.
- **OBSERVÉ :** 2 copies identiques, 1 copie en retard, 1 branche principale divergente **qui ne change que le port**, plus **1 branche expérimentale ajoutant seulement la régulation des requêtes HTTP**.
- **NON QUALIFIÉ :** disponibilité du site hébergé, bon fonctionnement Kobo Aura HD, consommation CPU/RAM, efficacité e-ink, sécurité effective en hébergement externe, tests physiques et de charge.
- **0 téléchargement de dépendances ou de code, 0 exécution Node/Docker, 0 test de la Kobo, 0 intégration de code tiers, 0 changement de P1/P2/P3, 0 écriture sur le FIRST BOOT scellé.**
