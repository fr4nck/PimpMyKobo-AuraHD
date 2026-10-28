# PMKB — PMSL-Arch : accès matériel minimal / sécurité frugale V1

18 octobre 2026. **Audit statique et outil hôte seulement.** Aucune intervention sur FIRST BOOT, U-Boot, P1/P2/P3, rcS, pilotes, système de fichiers ni appareil physique. Source : [SECURITY CONTRACT V1](security-contract-v1-fr.md), [audit matériel](offline-hardware-qualification-fr.md), [gates de boot](offline-boot-gates-fr.md).

## Pourquoi une politique de permissions, pas un superviseur

Le prototype [rcS](../experimental/offline-rootfs/etc/init.d/rcS) crée les nœuds selon les métadonnées sysfs via BusyBox `mknod`, mais n'impose ni umask explicite ni modes/groupes spécifiques. Son [inittab](../experimental/offline-rootfs/etc/inittab) démarre le [reader](../experimental/offline-rootfs/usr/bin/pmkb-reader) sans directive d'utilisateur ; le script ne change pas d'UID avant le `exec ./luajit reader.lua`. **On ne prouve pas l'UID réel d'une Kobo avec cette observation source.**

KOReader v2026.07.1 [déclare KoboDragon et les devices Kobo](https://github.com/koreader/koreader/blob/v2026.07.1/frontend/device/kobo/device.lua) ; le [powerd Kobo](https://github.com/koreader/koreader/blob/v2026.07.1/frontend/device/kobo/powerd.lua) recourt à `ffi/kobolight` pour les modèles sans lumière naturelle. Les audits précédents documentent MXCFB, ZForce v2 et l'ioctl NTX du frontlight. **On ne démontre pas les flags O_RDONLY/O_RDWR exacts ou les capacités du noyau** avec ces seules références.

Le lancement PMKB bypass le [launcher Kobo standard KOReader](https://github.com/koreader/koreader/blob/v2026.07.1/platform/kobo/koreader.sh) ; ses opérations au démarrage ne doivent pas être imputées automatiquement au prototype PMKB. Le contrôle [pmkb-check-offline](../experimental/offline-rootfs/usr/bin/pmkb-check-offline) est ponctuel et ne mesure pas la RF.

## Deux stratégies à comparer, sans forcer le changement

| Stratégie | Réalité / cible | Bénéfice | Coût / inconnue |
| --- | --- | --- | --- |
| **root_transitional** | Continuer provisoirement le chemin historique OFFLINE, sans toucher l'init | Aucun daemon ni groupe nouveau ; conserve potentiellement la compatibilité ioctl/DMA | Documents importés et plugins exécutés avec des privilèges possiblement élevés ; exception à analyser explicitement |
| **nonroot_candidate** | Privilégier un seul utilisateur KOReader et un groupe Unix matériel (nom de travail `pmkb-hw`) si faisable | Réduit les accès DAC hors des nœuds permis | Accès noyau/ioctl à qualifier ; des permissions Unix seules ne bornent **pas** les commandes offertes par `/dev/ntx_io` |

N'ajouter **aucun démon permanent, conteneur, watchdog logiciel, scan périodique, surcouche de sécurité ou nouveau module kernel** pour ce lot. Aucun Python embarqué. Le script de test hôte ne devient pas un service du boot.

### Trois nœuds candidats uniquement

| Rôle | Origine d'identité | Accès candidat pour non-root | Risque / limite |
| --- | --- | --- | --- |
| Framebuffer | `class/graphics/fb0/dev` → `/dev/fb0` | `rw`, groupe `pmkb-hw`, mode **0660** hypothétique | mmap et ioctls MXCFB peuvent imposer contraintes driver indépendantes des droits Unix |
| Tactile ZForce | parent `zForce-ir-touch` → `/dev/input/eventN` (N variable) | `r`, groupe `pmkb-hw`, mode **0640** hypothétique | Événements et axes à vérifier ; jamais supposer `event1` |
| Frontlight | `class/misc/ntx_io/dev` → `/dev/ntx_io` | `rw`, groupe `pmkb-hw`, mode **0660** hypothétique | Le driver NTX expose aussi des ioctls autres que la luminosité ; un accès ouvert ne restreint pas les codes ioctl |

Les chemins des **boutons** ne sont pas qualifiés par le snapshot : le planificateur **ne fabrique pas event0**. Les nœuds /dev/mmcblk*, /dev/watchdog, /dev/mem, /dev/i2c-* et les autres nœuds ne sont **jamais proposés**. La lecture P3 et les écritures de profil en tmpfs requièrent une qualification indépendante. Aucun changement de mode n'est opéré.

### Outillage hors matériel

[device_access_plan.py](../experimental/offline-audit/device_access_plan.py) réutilise **sans le copier** [sysfs_snapshot.py](../experimental/offline-audit/sysfs_snapshot.py) et son décodeur JSON strict. L'outil accepte uniquement une représentation `synthetic` déjà fournie en mémoire, valide l'identité des trois périphériques, puis construit un **plan descriptif inerte**. Entrée `plan_device_access(snapshot_json, strategy="nonroot_candidate")` ; stratégie alternative `root_transitional`.

**Sorties** : `candidate_unverified` si les métadonnées sont cohérentes ; `refused` si invalides. Tous les rapports conservent `hardware_verified=false`, `permission_applied=false`, `reader_started=false`, `deployable=false`, `security_certified=false` ; coût RAM **non mesuré**. L'outil n'exécute aucun `chmod`, `chown`, `mknod`, `su`, mount ou ouverture de fichier/dev ; les valeurs numériques affichées sont des **propositions**, pas des permissions constatées.

[Tests](../tests/test_device_access_plan.py) : événements renumérotés, périphérique manquant, JSON hostile/dupliqué, modes candidates restreints, absence d'identité boutons inventée, stratégie root explicite, absence de file I/O/subprocess/réseau.

## Budget de frugalité — objectif, pas mesure

| Ressource | Décision du lot | Mesure terrain |
| --- | --- | --- |
| Processus résidents ajoutés | **0** : aucun code déployé sur la Kobo | Non applicable au lot ; vérifier au prochain boot autorisé |
| RAM sur la Kobo | **0 code ajouté au rootfs** | RSS réel inchangé par ce lot, mais non mesuré ; mesure de référence à faire |
| CPU au repos | Aucun polling ni cron introduit | Non mesuré physiquement |
| Batterie | Aucun comportement énergétique modifié | À mesurer sur scénario de lecture identique |
| Maintenance | Python standard sur hôte, réutilisation du snapshot existant | Coût de portage à examiner avant intégration |

### Conditions avant toute intégration éventuelle

1. Relever sans commande invasive les vrais nœuds, modes, propriétaires, UID/GID, boutons et groupe disponible.
2. Auditer les ioctls accessibles de `ntx_io`, les opérations framebuffer et les besoins de KOReader pour connaître le vrai jeu d'accès minimal.
3. Tester une configuration non-root uniquement dans un environnement autorisé distinct, avec retour arrière hors P2. Sinon conserver temporairement le fonctionnement root OFFLINE, **sans déclarer SEC-05 réussi**.
4. Comparer la RAM, latence de démarrage, lecture/touch/frontlight et autonomie face à la référence. Ne pas choisir une sandbox lourde pour satisfaire un chiffre de couverture.
5. Ne jamais déduire de ce travail une autorisation d'activer le Wi-Fi ou un statut CONNECTED.

**Verdict** : politique simple et réversible formulée ; faisabilité non-root **INCONNUE** avant qualification réelle. Le chemin historique reste inchangé.

## Option de politique utilisateur (après le lot de planification)

SECURITY CONTRACT V1 accepte désormais un opt-in déclaratif `reader_root` même en scénario CONNECTED : **risque signalé**, aucune certification ou modification runtime. Les deux stratégies du planificateur matériel ci-dessus restent expérimentales ; ce changement n'installe aucune capacité, n'active aucun service et n'ajoute aucun processus résident. Wi-Fi, SSH et Telnet éventuels se décrivent dans [le contrat](security-contract-v1-fr.md), avec réseau OFF au démarrage. Les droits matériels et la préservation de FIRST BOOT/recovery ne sont pas négociés par un tel manifeste.
