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
| Réseau | Désactivé par défaut ; aucun socket d'écoute, contrôles continus encore à concevoir | Fermé par défaut ; LAN restreint ; aucun service public automatique ; Telnet interdit |
| Noyau | Ancien, **non maintenu**, risque explicitement accepté pour usage hors ligne borné | Branche maintenue + correctifs suivis, drivers E606C0 audités |
| Privilèges | Objectif lecteur non root ; ABI devices/permissions à qualifier | Non root + mécanismes d'isolation vérifiables sur ARMv7, sans supposer disponibilité de Landlock/seccomp |
| Disque | FIRST BOOT/P1/P2 conservés ; systèmes critiques ro lorsque possible ; écriture utilisateur isolée | Idem + mises à jour atomiques/authentifiées et reprise indépendante |
| Fichiers | EPUB/PDF/plugins non fiables, parser et chaîne LuaJIT à auditer | Idem, avec durcissement actif, politiques plugins et dépendances maintenues |
| Chiffrement/intégrité | SHA des backups utiles, mais **pas** de Secure Boot démontré, pas de secret protégé contre accès physique | Signature des images/updates à partir d'une clé racine de confiance ; limites d'anti-rollback et de boot vérifié à expliciter |
| Énergie | Référence de mesure batterie à obtenir | Comparaison réellement mesurée, avec EPDC et veille fonctionnels |
| Statut de sortie | Non qualifié physiquement. Utilisation OFFLINE seulement après gates critiques spécifiques et acceptation du noyau ancien | **NON AUTORISÉ** aujourd'hui ; aucun manifest synthétique ne peut autoriser connexion/déploiement |

**Règle bloquante** : ni le noyau historique, ni une branche LTS, ni la signature d'un fichier ne certifient les applications ou les pilotes. Le profil CONNECTED requiert une preuve non synthétique pour chaque gate critique, un modèle de confiance/revocation, l'absence de Telnet et des essais de récupération/énergie. Tout contrôle matériel reste interdit dans ce lot.

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

- Le **contrôle documentaire** peut refuser le réseau actif dans OFFLINE, tout Telnet, SSH sans clé ou root, écoute Internet, service non autorisé, root lecteur, racine rw, contenu autorun, updates non signés, CONNECTED sur 2.6.35.3 et valeurs inconnues critiques.
- Les tests utilisent uniquement des déclarations **synthetic**, jamais des preuves récupérées d'un vrai appareil ; un `claimed_met` reste **UNKNOWN** côté gate, même si cohérent.
- `not_applicable` n'est autorisé que pour SEC-09 en OFFLINE si `updates=none`, avec justification. Le noyau ancien non maintenu est explicitement consigné comme limitation, pas caché.
- Sorties : `refused` (contrat malformé), `blocked` (contradiction ou prérequis critique inconnu) ou `declarations_consistent_unverified` (déclarations compatibles **mais non authentifiées**). **deployment_allowed, connected_ready, security_certified, hardware_verified sont toujours false**.
- Le simulateur ne prouve pas le rootfs en lecture seule, ne lit aucun socket, ne scanne pas de CVE, ne mesure pas la RF et ne peut pas transformer une autodéclaration en attestation.

## Décision et prochaines gates

1. **OFFLINE d'abord :** auditer les privilèges et limites effectifs de KOReader, modules et permissions par source; définir une politique de nœuds et d'utilisateur sans modifier l'init actuel ; établir des vérifications de configuration strictes.
2. **CONNECTED ultérieurement :** choisir entre 6.12 et 6.18 sur preuves, porter l'EPDC/mémoire/MCU/veille, qualifier la maintenance et les mises à jour signées, interdire Telnet et toute écoute non maîtrisée.
3. Avant essais réels : identité mémoire U-Boot, sauvegardes et restauration indépendante, autorisation nouvelle et conditions d'échec documentées. Aucun changement FIRST BOOT, P1/P2/P3, rcS, image, MCU ni noyau pendant ce lot.

Ce dossier ne doit **jamais** déclencher une activation du Wi-Fi ou une écriture physique. Voir [passation Claude](security-contract-v1-claude-handoff-fr.md).
