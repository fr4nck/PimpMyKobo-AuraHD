# PMKB — SECURITY CONTRACT V1 : OFFLINE / CONNECTED

**18 octobre 2026. Contrat documentaire, tests de déclaration synthétiques, pas une certification.** Cible : Kobo Aura HD N204/E606C0. Révision contrôlée avant le lot : `87d786e`, PR #28 (PowerLab, **DRAFT**). Le SECURITY CONTRACT est un **sous-lot expérimental adjacent**, explicitement ajouté au descriptif de la PR, non une modification implicite du FIRST BOOT. [Menaces](security-threat-model-v1-fr.md) ; [candidats LTS](security-kernel-candidates-v1-fr.md).

## Statuts, frontières et preuves

- **PASS** : contrôle précis réellement passé, preuve vérifiable. **Jamais** par simple booléen synthétique.
- **FAIL** : exigence réellement contredite, ou démonstration directe d'une lacune du prototype **dans son périmètre**.
- **SKIP** : non applicable ou non exécuté, raison documentée.
- **UNKNOWN** : ni succès ni incompatibilité démontrés. Une configuration synthétique « claimed_met » demeure UNKNOWN.
- Provenances : `SRC-REPO` (code de GitHub lu), `AUDIT-PRÉC` (audit binaires/sources historiques déjà documenté, non rejoué), `AMONT` (versions Linux officielles), `SYNTH` (test local/CI sans Kobo), `MATÉRIEL` (non disponible).
- Une CI verte **ne démontre ni une radio éteinte, ni une absence de CVE, ni un noyau bootable**.

## Profils et conditions de sortie

| Sujet | A : OFFLINE — noyau de référence 2.6.35.3 | B : CONNECTED — noyau maintenu et portage |
| --- | --- | --- |
| Usage | Livres/notes locaux, sans réseau | Wi-Fi, SFTP/SSH, Store/synchronisation éventuels |
| Réseau | Désactivé par défaut ; Wi-Fi/diagnostic réseau activables ponctuellement par choix explicite (non intégrés) | Fermé par défaut ; SSH préféré ; Telnet manuel possible avec avertissement, jamais démarré automatiquement |
| Noyau | Ancien, **non maintenu**, risque explicitement accepté pour usage hors ligne borné | Branche maintenue + correctifs suivis, drivers E606C0 audités |
| Privilèges | Non-root souhaitable si compatible ; root fonctionnel possible avec risque documenté | Non-root recommandé, root optionnel avec risque élevé et sans certification |
| Disque | FIRST BOOT/P1/P2 conservés ; systèmes critiques ro lorsque possible ; écriture utilisateur isolée | Idem + mises à jour atomiques/authentifiées et reprise indépendante |
| Fichiers | EPUB/PDF/plugins non fiables, parser et chaîne LuaJIT à auditer | Idem, avec durcissement actif, politiques plugins et dépendances maintenues |
| Chiffrement/intégrité | SHA des backups utiles, mais **pas** de Secure Boot démontré, pas de secret protégé contre accès physique | Signature des images/updates à partir d'une clé racine de confiance ; limites d'anti-rollback et de boot vérifié à expliciter |
| Énergie | Référence de mesure batterie à obtenir | Comparaison réellement mesurée, avec EPDC et veille fonctionnels |
| Statut de sortie | Non qualifié physiquement ; choix possibles sans certificat de sécurité | Non qualifié physiquement ; usages réseau expérimentaux peuvent être envisagés par décision séparée, jamais autorisés par un manifeste synthétique |

**Règle de vérité** : ni noyau historique, ni LTS, ni signature de fichier ne certifient applications/pilotes. Les options à risque sont des choix, pas des preuves. Les protections recommandées pour une connexion régulière restent maintenance, chiffrement réseau et récupération qualifiée. Tout essai matériel exige une autorisation distincte : aucun manifeste ne l'accorde.

## Audit factuel du prototype étudié (non exécuté sur la Kobo)

- [rcS](../experimental/offline-rootfs/etc/init.d/rcS) monte proc/sysfs et tmpfs (dont /tmp en 1777), balaye `/sys/class/*/*/dev`, fait `mknod` puis monte P3 en lecture seule. Il **n'applique pas explicitement une politique de droits aux nœuds** et ne prouve ni P1 rootfs ro ni intégrité de P2.
- [pmkb-check-offline](../experimental/offline-rootfs/usr/bin/pmkb-check-offline) n'accepte que l'interface `lo` dans le répertoire réseau *au moment du contrôle*. Il est invoqué au boot et avant KOReader, mais **ne vérifie ni Wi-Fi RF, ni sockets, ni absence de trafic après ces instants**.
- [pmkb-reader](../experimental/offline-rootfs/usr/bin/pmkb-reader) lance LuaJIT/KOReader sans `su` ni changement d'UID explicite ; [inittab](../experimental/offline-rootfs/etc/inittab) démarre le script sans identifiant configuré. L'absence d'abaissement des privilèges est démontrée dans le script ; l'UID effectif sur une Kobo physique ne l'est pas.
- L'analyse précédente montre que le paquet KOReader peut emprunter deux chemins de configuration Nickel, et que les valeurs indépendantes ont été testées sur source amont, **mais pas installées** dans l'image v3 ; [audit matériel](offline-hardware-qualification-fr.md). Ce n'est pas une preuve de sécurité de tous les plugins, PDF/EPUB et décodages.
- Le noyau 2.6.35.3 documenté possède des pilotes intégrés, sans preuve d'un durcissement moderne sur l'image embarquée. Ne pas supposer `seccomp-bpf`, `Landlock`, namespaces ou signatures de modules ; vérifier IKCONFIG et patches avant toute recommandation applicable.
- Le watchdog peut être dangereux à sonder : `mxc_wdt_disable` vide et probe non établi selon [boot gates](offline-boot-gates-fr.md).
- Les copies privées P2/boot et licences blobs n'ont **pas** été relues pendant ce lot.

## Matrice de qualification SEC-01 à SEC-12

Les résultats ci-dessous concernent **l'état documenté / prototype**, pas une Kobo réellement testée. Le profil B ne dispose d'aucune qualification de sortie.

| Gate | Profil | Attendu et preuve / résultat initial | Test hôte ; essai physique futur |
| --- | --- | --- | --- |
| SEC-01 FIRST BOOT | A/B | **UNKNOWN** : invariants et SHA documentés (AUDIT-PRÉC), mais aucune comparaison binaire de l'exemplaire pendant ce lot | Diff Git limité ; comparaison privée SHA séparée, sans écrire |
| SEC-02 Boot/recovery | A/B | **UNKNOWN** : contrat et P2 documentés, restauration physique et retour indépendant non qualifiés | Audit boot contract ; validation récupération indépendante future |
| SEC-03 Réseau non autorisé | A/B | **UNKNOWN** : guard `lo` présent (SRC-REPO), aucune preuve RF/sockets continus | Test négatif déclaratif ; relevés et veille réseau futurs |
| SEC-04 Services minimaux | A/B | **UNKNOWN** : init minimal décrit, aucun inventaire runtime exhaustif | Revue inittab/rcS ; futurs process/sockets |
| SEC-05 Privilèges /dev | A/B | **FAIL (prototype)** : lecteur sans abaissement UID et `mknod` sans politique permissions explicite | Tests de futurs fichiers de permissions ; ouvertures matérielles futures |
| SEC-06 Données et ro | A/B | **UNKNOWN** : P3 ro explicite (SRC-REPO) ; P1/P2 et confinement écritures non qualifiés | Contrôle montages déclarés ; observation réelle future |
| SEC-07 Fichiers non fiables | A/B | **UNKNOWN** : parsers EPUB/PDF/LuaJIT et plugins non audités intégralement | Inventaire et fixtures, aucune exploitation sur appareil |
| SEC-08 Intégrité | A/B | **UNKNOWN** : SHA sauvegarde ≠ confiance au boot ; pas d'attestation de composants au runtime | Vérification signatures/chaîne de clés en environnement de test, sans firmware privé |
| SEC-09 Mises à jour signées | A : **SKIP** seulement si aucun mécanisme update ; B : **FAIL** aujourd'hui, updater authentifié non construit | Tests de refus manifest unsigned ; mise à jour signée non installée |
| SEC-10 Maintenance | A : **FAIL** vis-à-vis d'un noyau encore maintenu (risque accepté et limité) ; B : **UNKNOWN** malgré LTS amont | Audit versions et cadence correctifs, SBOM, support drivers portés |
| SEC-11 Drivers matériels | A/B | **UNKNOWN** : interfaces identifiées, ni sécurité du driver ni portage physique qualifié | Sources/ABI statiques ; EPDC, ZForce, MCU, watchdog physiques futurs |
| SEC-12 Énergie et sécurité | A/B | **UNKNOWN** : PowerLab calcule seulement énergie déclarée, sans mesures Kobo | Scénarios identiques ; batterie / suspend / lecture réels futurs |

Ces états ne sont **pas** alimentés automatiquement par le validateur de scénarios : seuls un audit indépendant et des observations attestées pourraient les améliorer.

## Gate déclarative synthétique : design et limites

Outil Python standard [security_contract.py](../experimental/security-contract/security_contract.py), [tests](../tests/test_security_contract.py) et [mode d'emploi](../experimental/security-contract/README.md). Fonction pure `analyze(dict)` et `analyze_json(str)` ; aucun fichier lu, aucun réseau ouvert, aucune commande externe. Schéma exact comprenant E606C0, OFFLINE/CONNECTED, état déclaré FIRST BOOT/P2, rootfs, UID lecteur, autorun, updates, famille noyau/maintenance, Wi-Fi et réseau par défaut, services actifs, 12 gate_claims et attestations **toujours false**.

- **Sans option déclarée**, le contrôle refuse les usages à risque précédemment bloqués : Telnet, SSH mot de passe/root, Wi-Fi en OFFLINE, lecteur root, etc. **Avec `opt_ins` explicite**, il consigne l'écart dans `risk_advisories`, sans le faire passer pour sûr. Les risques non choisis restent bloquants ; les modifications de FIRST BOOT/recovery restent bloquantes quelle que soit l'option.
- Les tests utilisent uniquement des déclarations **synthetic**, jamais des preuves récupérées d'un vrai appareil ; un `claimed_met` reste **UNKNOWN** côté gate, même si cohérent.
- `not_applicable` n'est autorisé que pour SEC-09 en OFFLINE si `updates=none`, avec justification. Le noyau ancien non maintenu est explicitement consigné comme limitation, pas caché.
- Sorties : `refused` (contrat malformé), `blocked` (écart non accepté ou prérequis critique inconnu), `declarations_consistent_unverified` (déclarations ordinaires) ou `choices_consistent_unverified` (choix à risque déclarés, non authentifiés). **deployment_allowed, connected_ready, security_certified, hardware_verified sont toujours false**.
- Le simulateur ne prouve pas le rootfs en lecture seule, ne lit aucun socket, ne scanne pas de CVE, ne mesure pas la RF et ne peut pas transformer une autodéclaration en attestation.

## Décision et prochaines gates

1. **OFFLINE d'abord :** auditer les privilèges et limites effectifs de KOReader, modules et permissions par source; définir une politique de nœuds et d'utilisateur sans modifier l'init actuel ; établir des vérifications de configuration strictes.
2. **CONNECTED ultérieurement :** choisir entre 6.12 et 6.18 sur preuves, porter EPDC/MCU/veille et les mesures ; documenter Telnet optionnel (texte clair), privilégier SSH et ne lancer aucun service par défaut.
3. Avant essais réels : identité mémoire U-Boot, sauvegardes et restauration indépendante, autorisation nouvelle et conditions d'échec documentées. Aucun changement FIRST BOOT, P1/P2/P3, rcS, image, MCU ni noyau pendant ce lot.

Ce dossier ne doit **jamais** déclencher une activation du Wi-Fi ou une écriture physique. Voir [passation Claude](security-contract-v1-claude-handoff-fr.md).

## Addendum — PMSL-Arch / sécurité frugale (18 octobre 2026)

Une protection ne doit pas monopoliser des ressources de l'Aura HD (512 Mio). Voir [plan frugal de permissions](frugal-device-access-v1-fr.md), [planificateur synthétique](../experimental/offline-audit/device_access_plan.py) et [tests](../tests/test_device_access_plan.py).

- **0 processus résident nouveau, 0 polling, 0 framework ou Python ajouté au rootfs.** Le planificateur n'est exécuté que sur hôte/CI. Aucune empreinte RAM réelle ni économie de batterie n'est prétendue mesurée.
- **SEC-05 n'est pas une obligation irréaliste de non-root au FIRST BOOT.** Le prototype actuel sans abaissement d'UID reste un écart documenté. Sans choix explicite, le refus de politique V1 demeure. Avec `opt_ins=["reader_root"]`, root (y compris `root_transitional`) devient un choix documenté, en OFFLINE comme CONNECTED, avec `SEC-05=UNKNOWN`, avertissement et **aucune autorisation de déploiement**.
- Les groupes Unix, modes 0640/0660 et séparation éventuelle init/lecteur ne sont que des **candidats** : `/dev/ntx_io` expose potentiellement d'autres ioctls (énergie, Wi-Fi, watchdog), donc autoriser l'ouverture n'isole pas automatiquement les commandes. Aucun `chmod`, `chown`, `mknod` ou `su` n'est ajouté à la Kobo aujourd'hui.
- **Priorité à la compatibilité** : si le non-root échoue avec l'EPDC, le tactile ou l'éclairage, préserver le mode OFFLINE fonctionnel, puis quantifier le risque et rechercher la solution la moins coûteuse. Aucun daemon/proxy de sécurité introduit seulement pour faire passer une gate.
- Ces choix ne déclarent pas l'ancien noyau sûr et ne constituent jamais une autorisation d'activer physiquement le Wi-Fi ou d'exécuter SSH/Telnet ; leur activation future sera volontaire, ponctuelle et séparément qualifiée.

Le reste du contrat demeure inchangé. Les prochaines décisions devront comparer la compatibilité fonctionnelle et **le coût mesuré** en RAM, CPU, énergie et maintenance, sans valeur inventée.

## Addendum — Liberté de configuration et risque explicite (18 octobre 2026)

**PMSL-Arch : l'outil conseille, il n'interdit pas arbitrairement.** Les fonctionnalités root, Telnet, SSH par mot de passe/root, serveur local, Wi-Fi OFFLINE temporaire, ancien noyau connecté et autres choix avancés peuvent être **déclarés explicitement** par `opt_ins`. Chaque dérogation produit une entrée française dans `risk_advisories`, conserve les gates à UNKNOWN et le statut `choices_consistent_unverified`. Exemple synthétique : `opt_ins: ["telnet", "offline_service"]` pour décrire un service Telnet local ponctuel, réseau par défaut toujours coupé. **Telnet ne chiffre pas les données ; ne pas l'exposer à Internet.** Aucun mot de passe ni ouverture réseau ne sont créés.

Les manifestes sont synthétiques et ne savent pas vérifier qui a exprimé ces choix. Aucune option ne peut modifier ou autoriser une écriture sur FIRST BOOT/P1/P2/P3, signer une mise à jour, activer le matériel ni prouver l'absence de CVE. Le `network_default="on"` reste une violation de la politique de **désactivation par défaut** : la liberté concerne l'activation à la demande et non un service ajouté silencieusement au boot. Le validateur s'exécute **sur hôte seulement** (zéro processus/daemon, zéro RAM réservée sur la Kobo par ce lot).

La liste exhaustive des noms d'options, leurs avertissements et les tests de compatibilité se trouvent dans [README du validateur](../experimental/security-contract/README.md). [PR #28](https://github.com/fr4nck/PimpMyKobo-AuraHD/pull/28) reste en brouillon. La gate SEC-05 du prototype est toujours non démontrée sur Kobo.
