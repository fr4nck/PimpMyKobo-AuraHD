# Planificateur inerte du démarrage autonome

Contrat v1, séparé du prototype de boot. Le module
experimental/offline-audit/startup_plan.py produit uniquement des données.
Il n'ouvre aucun fichier ou périphérique, ne lance aucun helper et ne possède
aucun exécuteur. Il utilise le décodeur strict du snapshot déjà fourni sous
forme de texte JSON. Aucun collecteur de sysfs réel n'est ajouté.

## Interface

`plan_startup(snapshot_json, scenario=None)` reçoit :

- une chaîne JSON du [contrat de snapshot synthétique](sysfs-snapshot-fr.md) ;
- éventuellement un dictionnaire de scénario inerte, décrit ci-dessous.

L'import du module et de sysfs_snapshot charge leur code Python normalement,
avant la planification. La garantie sans I/O porte sur les appels de
plan_startup : les tests chargent les modules et les fixtures ordinaires avant
d'intercepter les ouvertures de fichiers, accès aux métadonnées et helpers.
Ce n'est ni une sandbox de Python ni un logiciel installé sur la liseuse.

## Contrat de scénario

`default_scenario()` renvoie un dictionnaire neuf :

- schema_version = 1 (entier, pas booléen) ;
- scope = synthetic_scenario ;
- preconditions : chaque clé attendue est unknown ;
- decisions : chaque clé attendue est unresolved ;
- failure_at = null.

Les clés sont exactes. Aucun champ command, callback, timeout, permission
numérique ou write_authorized n'est admis. Aucun objet appelable n'est accepté
comme état. Le scénario reçu est un dictionnaire en mémoire, pas un texte JSON ;
il n'y a pas de second décodeur de scénario ni d'évaluation de chaîne.

Une précondition a seulement trois états : unknown, assumed_satisfied ou
assumed_failed. Une décision a seulement deux états : unresolved ou
assumed_resolved. Les deux états assumed ne sont jamais des preuves ni des
choix réellement validés. Ils servent uniquement à exercer le modèle.
Même le libellé resolved, sans assumed, est refusé.

| Étape | Préconditions du scénario | Décisions requises dans le scénario |
| --- | --- | --- |
| identify_devices | Snapshot cohérent calculé par le validateur, indépendamment du scénario | Aucune |
| prepare_nodes | device_bindings_and_types | device_wait_policy, permissions_policy |
| prepare_framebuffer | framebuffer_geometry, panel_ready | framebuffer_preparation |
| prepare_profile | p3_read_only, temporary_profile, nickel_independent_settings | Aucune |
| consider_reader_launch | runtime_and_environment, offline_launch_check | diagnostic_policy, reader_exit_policy, watchdog_policy, physical_trial_contract |

Le nom watchdog_policy exprime une décision encore ouverte. Il ne crée
aucune étape watchdog, ne choisit pas un daemon et n'appelle aucune commande.
De même, offline_launch_check n'active aucun réseau et ne mesure pas la radio.

failure_at vaut null ou l'un des cinq noms d'étapes. Il injecte un échec
uniquement quand l'étape est atteinte et ses conditions de scénario passent.
Il ne permet pas de contourner un blocage plus tôt dans la trace.

## Plan, trace et garanties

Le plan contient les descriptions successives atteintes avec leurs dépendances
et leurs conditions. Une entrée peut figurer dans le plan puis échouer dans
la simulation. Une étape bloquée n'est pas ajoutée au plan ; elle apparaît
dans la trace comme blocked. Les étapes suivantes sont dans not_reached.

Une identité refusée ne produit aucun plan. Une identité cohérente n'autorise
pas immédiatement les nœuds : la trace d'identification doit avoir passé et
les hypothèses des conditions des nœuds doivent être présentes.
Les identités copiées dans l'entrée prepare_nodes restent explicitement
synthetic_identities. Aucun chemin /dev cible, mode, mknod ou commande shell
n'est émis.

Statuts possibles :

- refused : scénario invalide ou snapshot refusé ;
- blocked : précondition unknown/assumed_failed ou décision unresolved ;
- simulated_failure : échec injecté à l'étape atteinte ;
- simulation_complete : toutes les étapes du modèle ont passé sous hypothèses.

Aucun statut ne signifie « prêt à démarrer ». Dans tous les rapports :

- plan_executable, launch_performed, hardware_verified, boot_qualified et
  physical_restore_eligible restent false ;
- performed reste false sur chaque entrée du plan et de la trace ;
- real_decisions_unresolved conserve la liste entière des décisions réelles ;
- hardware_evidence_missing conserve les preuves matérielles nécessaires.

checked_preconditions ne contient que la cohérence des métadonnées synthétiques
effectivement calculée. scenario_preconditions et scenario_decisions sont
des copies des hypothèses, jamais présentées comme des vérifications.
Ni le contrat d'essai physique ni une autorisation ne peuvent être fournis ou
validés par cette API. Toutes les décisions réelles restent ouvertes même si
leur équivalent de scénario est assumed_resolved.

Le défaut n'invente aucune valeur : les états unknown/unresolved provoquent
un blocage à prepare_nodes. Pour exercer toute la trace dans un test, il est
possible d'utiliser assumed_satisfied/assumed_resolved pour toutes les clés.
Le résultat simulation_complete reste explicitement inerte.

## Absence de fallback

Les seules opérations descriptives sont les cinq étapes ci-dessus.
Aucun retour recovery/Nickel, reboot, retry, flash, réseau ou traitement
watchdog n'est ajouté en cas de refus, sortie ou échec. Le prototype de
démarrage et les fonctions internes de KOReader ne sont pas modifiés par
ce modèle ; leur comportement réel ne doit pas être déduit de sa trace.

## Tests et validation

tests/test_startup_plan.py couvre :

- défaut bloqué avant les nœuds et absence de lancement ;
- ordre complet sous hypothèses, avec plan toujours non exécutable ;
- chaque décision unresolved et chaque précondition unknown/assumed_failed ;
- échec injecté à chacune des cinq étapes, sans atteindre les dépendants ;
- les douze fixtures sysfs existantes, via le décodeur strict ;
- refus des commandes, callbacks, autorisations et états non contractuels ;
- absence d'opérations de fallback ;
- absence d'accès fichier, métadonnées et helpers pendant la planification ;
- absence de mutation des entrées et d'état partagé entre rapports.

Après récupération du lot, les commandes de validation sont :

```sh
python -m unittest discover -s tests -p test_startup_plan.py -v
python -m unittest discover -s tests -v
git diff --check
```

Ces commandes testent des données et des traces, jamais l'init matériel.
Le module se charge avec sysfs_snapshot importable depuis le même répertoire ;
les tests utilisent un chargement explicite temporaire sans modifier
durablement sys.path ou sys.modules.

## Limites et suite

La [spécification de démarrage](offline-startup-spec-fr.md) demeure la
référence des décisions et critères. Le modèle ne choisit aucune permission,
attente, calibration, préparation écran, politique d'arrêt ou stratégie de
watchdog. La complétude du snapshot et les observations matérielles ne sont
pas vérifiées.

Un prochain lot sans carte peut qualifier le profil KOReader temporaire sur
des fixtures de fichiers ordinaires : résolution du chemin de configuration,
valeurs effectives -1/false, refus des valeurs héritées et absence d'accès au
fichier Nickel. Cela reste un lot hôte séparé, sans copie dans une image ni
modification de rcS. Réutiliser les preuves du test amont existant, sans
inventer un interpréteur de configuration Lua.

Toute intégration réelle du boot doit d'abord traiter les décisions ouvertes,
le contrat d'essai/retour arrière et une nouvelle autorisation physique.
