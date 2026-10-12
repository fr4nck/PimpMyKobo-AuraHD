# Spécification du futur démarrage autonome Aura HD

Statut : spécification hors matériel, non installée, sans autorisation physique.
Référence relue : commit 18ff92a068e84737315cf062aea03b18b3c8a6d4.
Ce lot ne change ni rcS, ni pmkb-reader, ni une image. Il ne fournit aucun
exécuteur de création de nœuds, montage, ioctl ou lancement du lecteur.

## Périmètre et preuves

Les [interfaces matérielles](offline-hardware-qualification-fr.md) et les
[conditions de boot](offline-boot-gates-fr.md) établissent les chemins source
E-Ink, ZForce et NTX. Le [contrat de snapshot](sysfs-snapshot-fr.md) valide
seulement des données synthétiques. Son validateur Python est un outil d'audit
du dépôt, pas une dépendance à installer sur la liseuse.

Les résultats antérieurs de runtime ARM et d'ABI ne prouvent pas le démarrage
du noyau Aura HD. Les logs et sauvegardes privées ne sont pas relus dans ce lot :
leurs conclusions proviennent des audits publiés, pas d'une nouvelle mesure.

## États à ne pas confondre

- Un document syntaxiquement valide peut être incohérent.
- Un snapshot cohérent peut être incomplet ou inventé.
- Un périphérique publié peut ne pas être prêt.
- Une préparation utilisateur réussie ne qualifie pas l'écran, le tactile ou
  l'éclairage.
- Une image expérimentale n'est pas un rapport recovery qualifié.

Les champs hardware_verified, boot_qualified et physical_restore_eligible
restent false pour tous les résultats de snapshots, y compris les fixtures
cohérentes. Aucun attribut ready artificiel ne remplace hw_ready du noyau.

## Étapes et conditions

| Étape future | Préconditions | Preuves disponibles | Refus requis | Validation nécessitant le matériel |
| --- | --- | --- | --- | --- |
| 1. Identifier l'image et le matériel | Image distincte, contrat d'essai et retour arrière adaptés, autorisation physique nouvelle ; E606C0 confirmé sans supposition commerciale | Audits HWCONFIG et image expérimentale séparée des contrats recovery | Mauvaise cible, provenance inconnue, ancien contrat recovery présenté pour la nouvelle image | La chaîne de boot réellement exécutée et l'identité de la carte d'essai |
| 2. Conserver la chaîne noyau/waveform | Pré-P1 conservé, HWCONFIG et waveform transmis selon la chaîne source auditée | Pilotes intégrés, waveform présente dans la sauvegarde, branche FW_IN_RAM | Données absentes ou identité incohérente ; aucun firmware de remplacement supposé | Paramètres effectifs du noyau, initialisation EPDC et image visible |
| 3. Préparer l'environnement de l'init | Proc/sysfs et espace temporaire nécessaires ; aucune réparation, mise à jour Kobo ou opération sur P2 | rcS courant et différences documentées avec udev ; DEVTMPFS désactivé | Échec de préparation ; pas de poursuite après une erreur ni de fallback vers la recovery destructrice | Montage et disponibilité réels ; stratégie de diagnostic au démarrage |
| 4. Identifier les périphériques | Métadonnées sysfs disponibles et stables pour les entrées ciblées | fb0, parent input zForce-ir-touch, misc ntx_io ; v1 modélise ces attributs | Tactile absent/ambigu, attributs incomplets, numéros invalides ou incohérents ; jamais supposer event1 | Binding des pilotes, capacités evdev et périphériques effectivement présents |
| 5. Préparer les nœuds | Identités validées, numéros issus de sysfs, type attendu, permissions explicites | Règles recovery input/permissions et publication des classes dans les sources | Nœud existant de mauvais type/numéro ; parent inattendu ; aucune création de remplacement sur numéros devinés | Ouvertures réelles, activation tactile et disponibilité MCU |
| 6. Préparer le framebuffer | Pilote EPDC identifié, géométrie initiale relevée, voie de préparation validée séparément | fbdepth du paquet, ABI MXCFB contrôlée ; fb0 publié avant hw_ready | Géométrie inconnue/incohérente, erreur de préparation ; présence de fb0 insuffisante | Mode/profondeur/rotation, dimensions, rafraîchissements et fin des marqueurs |
| 7. Préparer le stockage et le profil | P3 protégée en lecture seule ; profil KOReader temporaire propre | KO_MULTIUSER et XDG_CONFIG_HOME ; proposition indépendante defaults.custom.lua | P3 non protégée, profil incorrect/inaccessible, options Nickel absentes ou erronées | Montage réel et comportement des plugins/écritures annexes |
| 8. Charger les réglages indépendants | Profil effectif correspondant au DataStorage utilisé par KOReader | -1 pour KOBO_LIGHT_ON_START, false pour KOBO_SYNC_BRIGHTNESS_WITH_NICKEL ; fonctions amont testées dans le lot précédent | Valeurs effectives héritées -2/true, tentative d'accès au fichier Nickel ; aucun « getter de secours » sur P3 | Lumière réelle et comportement du lecteur complet ; les tests de réglages ne couvrent pas tous les plugins |
| 9. Contrôler le réseau avant lancement | Contrôle hors ligne disponible ; état réel de la plateforme documenté | Guard actuel exige lo seul, sans modules Wi-Fi inclus | Interface inattendue ou données réseau manquantes ; pas de fallback réseau | État radio et absence de trafic ; un contrôle ponctuel n'est pas une garantie continue |
| 10. Lancer directement le lecteur | Étapes utilisateur précédentes réussies ; marker PMKB, PRODUCT=dragon et environnement cohérent ; runtime connu | pmkb-reader appelle LuaJIT/reader.lua sans lanceur Nickel | Toute étape précédente refusée ; identité/env/runtime incohérent | Lecture affichée, saisie tactile et frontlight ; maintien sur la durée |
| 11. Gérer refus/sortie | Politique de diagnostic et de sortie définie séparément | Prototype sans retry/retour Nickel ; fonctions internes KOReader d'arrêt/reboot encore présentes | Aucun retry, reset, watchdog ou retour recovery ajouté comme contournement | Stabilité, consommation, état MCU/watchdog et arrêt effectif |

Dans l'étape 5, « permissions explicites » est une exigence, pas une politique
nouvelle fixée dans ce document. Les modes recovery sont des références de
compatibilité ; ils ne qualifient pas automatiquement un modèle de privilèges
PMKB. Les nœuds internes à /dev dans un boot futur ne sont pas créés ici.

Dans l'étape 6, aucun timeout, appel ioctl de probe ni mode obligatoire choisi
par défaut. La voie fbdepth est crédible d'après les sources, mais son emploi
au boot autonome reste à définir à partir d'une qualification séparée.
Dans l'étape 8, defaults.custom.lua serait au profil effectif
XDG_CONFIG_HOME/koreader, pas simplement copié à côté des exécutables.
Le profil temporaire n'est ni immuable ni persistant.

Le marker /run/pmkb-ready du prototype actuel indique seulement qu'une séquence
de commandes s'est terminée. Il ne représente pas une qualification matérielle.
Sa sémantique et son emploi devront être revus au moment de l'intégration,
sans changer ce marker dans ce lot.

## Vérifiable sans carte

- Décodage JSON strict, données/identités uniques et refus déterministes.
- Fixtures positives/négatives versionnées et invariants du rapport.
- Ordre d'un futur plan d'actions simulé : aucun lancement après refus, aucune
  création de nœud avant résolution de son identité, aucun fallback destructif.
- Valeurs et emplacement logique du profil ; tests isolés des chemins Nickel.
- Conservation des fichiers du boot dans le diff du lot ; aucun test ne doit
  exécuter l'init sur l'hôte.

Le contrôle de snapshot ne porte pas sur les capacités input, le driver
framebuffer, la géométrie complète, le réseau live ou les montages. Ajouter ces
preuves demanderait un contrat distinct explicitant leur origine et leurs
limites. Aucun lecteur de sysfs live n'est introduit par extension implicite.

## Décisions ouvertes, sans choix conjectural

| Sujet | Ce qui manque avant l'intégration |
| --- | --- |
| Apparition des périphériques | Stratégie et limite d'attente fondées sur la plateforme, sans délai inventé |
| Identité input et binding | Preuves supplémentaires pour capacités/driver et boutons, au-delà du seul nom |
| Permissions et privilèges | Politique PMKB à définir et tester, sans reprendre aveuglément tout udev |
| Préparation écran | Critères de géométrie initiale, vérification de la conversion et politique d'échec |
| Diagnostic de refus | Moyen de récupérer des logs si écran et tactile ne fonctionnent pas ; pas de stockage privé ou réseau activé implicitement |
| Sortie du lecteur | Politique d'attente/arrêt après échec ou sortie ; aucun redémarrage automatique choisi |
| Watchdog et alimentation | État MCU/compteur réel ; disable vide ne justifie aucun traitement de substitution |
| Essai physique | Support, contrat de validation et retour arrière à revoir ; nouvelle autorisation obligatoire |

Ces décisions ne bloquent pas le lot présent de fixtures et de spécification :
aucune d'elles n'est tranchée ni implémentée. Elles bloqueront un exécuteur
réel de boot. Les essais physiques de rafraîchissement, coordonnées tactiles,
gradation/extinction puis veille/USB restent obligatoires pour une qualification.

## Audit du contrôle existant

La fonction mémoire respecte son périmètre documenté. Des nombres input
plausibles, un autre pilote derrière fb0 ou un snapshot incomplet peuvent être
acceptés comme métadonnées : ces preuves sont explicitement non vérifiées.
Cela ne doit pas être présenté comme une qualification.

Le défaut d'entrée démontré est l'écrasement silencieux de clés répétées par
json.loads ordinaire. Les fixtures duplicate-root-key et duplicate-record-key
reproduisent un dictionnaire accepté après cette perte d'information. Le
décodeur strict refuse le texte avant cette transformation. Il conserve
exactement le même statut matériel non qualifié et n'ajoute aucune I/O.

## Prochain lot concret sans carte

Préparer un planificateur purement en mémoire et ses traces d'actions factices :
modéliser les étapes 4–10, des préconditions explicites et des refus injectés,
puis vérifier l'ordre et l'absence de lancement après refus. Les opérations
matérielles restent des descriptions inertes, sans exécuteur. Les décisions
ouvertes demeurent « non résolues » et doivent provoquer un refus de plan
exécutable, jamais être remplacées par des valeurs par défaut.
