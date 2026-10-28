# PMKB — OKReader : audit des forks publics, branches et composants (25 octobre 2026)

**Statut : audit statique de dépôts GitHub, sans compilation ni essai matériel.**
Cible PMKB : Kobo Aura HD / `dragon` / E606C0 / i.MX507 / 512 Mio.
À lire après [M01 : audit du projet original](recherche-sources-fr.md#m01-okreader) et [l'audit noyau R1/R3](kernel-community-audit-2026-10-24-fr.md).

## Périmètre et méthode

Référence : [lgeek/okreader](https://github.com/lgeek/okreader), branche `master`, HEAD `2c253e5becbf22fd16960edca4f37eba2c03556a` (29 juin 2018). Recherche GitHub des forks publics portant le nom `okreader`, puis comparaison Git entre `lgeek:master` et `master` de **16 forks**. Une comparaison `ahead/behind` comptabilise les commits, **pas** les fonctionnalités qualifiées. L'index ne prouve pas l'exhaustivité d'éventuels forks privés, renommés ou non accessibles.

Examen complémentaire : recherche des branches sur les 16 forks, comparaison des branches communes `glohd_bringup` et `wip` avec l'original, comparaison des branches propres à certains forks, puis des **5 forks publics retrouvés** des sous-modules `lgeek/linux-okreader` et `lgeek/u-boot-okreader`. Sources ciblées relues par l'interface GitHub : README, scripts, Makefiles, correctifs et commits cités.

**Aucun clone, téléchargement de firmware, installation, exécution de script tiers, build, essai sur microSD ou patch PMKB pendant l'audit.**

## 1. Forks directs de l'OS : 16 comparés sur master

| Statut comparé à `lgeek:master` | Nombre | Forks / constat |
| --- | ---: | --- |
| Identique (0 ahead, 0 behind) | **11** | `farmers-tan`, `Velsoth`, `jnetod`, `rudals`, `marcosxaviergil`, `Ilgrim`, `cota809522`, `Pandinosaurus`, `SuperTaiyaki`, `cafeinecake`, `duf42` |
| En retard (0 ahead, 2 behind) | **3** | `kratz00`, `pazos`, `justinvreeland` : aucun commit nouveau sur `master` |
| Avance réelle | **2** | [prokinkd/okreader](https://github.com/prokinkd/okreader) : **11 ahead**, 14 fichiers modifiés ; [BloodRagg/okreader](https://github.com/BloodRagg/okreader) : **1 ahead**, nouveau `files/gnu_hwconfig.sh` de 180 lignes |

**Décision :** les onze copies inchangées et les trois versions en retard n'apportent rien de nouveau **sur leur branche principale** ; vérifier les branches supplémentaires séparément avant de conclure qu'un fork entier est sans intérêt.

## 2. Deux forks avec code nouveau

### BloodRagg : table HWCONFIG étendue — priorité P1 documentaire

[Commit du 1er avril 2019](https://github.com/BloodRagg/okreader/commit/8fa1a3116c822657ffbd90ad7e1d0a114b872b7b) ; [source du décodeur shell](https://github.com/BloodRagg/okreader/blob/master/files/gnu_hwconfig.sh).

- Script de **180 lignes** recensant **70 champs** (index 0–69), parmi lesquels PCB, Wi-Fi, toucher, RAM, écran, éclairage, pilotes et types de stockage.
- L'association `E606C* → dragon` est présente. **Contrôle statique : 9/9 valeurs de la table concordent** avec notre [HWCONFIG v1.7](hwconfig-fr.md) et [matériel observé](hardware-fr.md) : PCB `28→E606C0`, RAM `512MB`, RAMType `K4X2G323PC`, résolution `1440x1080`, lumière `TABLE3+`, CPUFreq `1G`, Hall `TLE4913`, bus `16Bits_mirror`, LED `SY7201`.
- Ce n'est **pas** 9 tests d'exécution du décodeur. Le script lit directement `/dev/mmcblk0` à l'offset `0x80000`, **sans sélection ni vérification de l'appareil** ; son shebang `#!/bin/sh` coexiste avec des substitutions et chaînes **spécifiques à Bash**. La détection de longueur et de version exige aussi une relecture avant adaptation.
- La commande d'aide annonce **GPLv2** : confirmer le cadre exact des droits avant reprise de code ; ne pas importer la table sans gestion de versions, limites de champs et attribution.

**RETENIR les valeurs comme comparateur documentaire**, pas le script tel quel. Toute extension PMKB se fera par décodeur original, en lecture seule, sur buffers synthétiques et fichiers locaux, avec validation de taille/version avant indexation.

### prokinkd : cross-build et Glo HD — priorité P1 outillage

[Historique du fork](https://github.com/prokinkd/okreader/commits/master) et [README](https://github.com/prokinkd/okreader/blob/master/README.md), dernière activité sur `master` observée le **14 juillet 2019**.

- Build séparant i.MX5 (noyau **2.6.35.3**) et i.MX6 (**3.0.35**) ; les deux branches historiques existent dans `lgeek/linux-okreader`, dont [`imx6` et sa configuration `alyssum`](https://github.com/lgeek/linux-okreader/blob/imx6/arch/arm/configs/imx6s_ntx_alyssum_okreader_defconfig).
- Ajoute compilation croisée ARM, `qemu-debootstrap` pour générer le rootfs, compression `dpkg-deb -Z gzip`, paquet KOReader **2019.02**, correction de dictionnaires via lien de stockage, adaptation d'un module Broadcom SDIO.
- Le README revendique un essai sur **Kobo Glo HD** ; l'**Aura HD reste libellée « kernel upg? »**. Ne pas confondre `alyssum` (Glo HD) et `dragon` (Aura HD).
- Reste basé sur **Debian Wheezy** et des versions anciennes de KOReader ; la stratégie de stockage des dictionnaires suppose un montage externe spécifique à OKReader.

**RETENIR les idées de cross-compilation, séparation des cibles, génération contrôlée de rootfs et empaquetage conditionné à l'ABI** ; pas de portage i.MX6 ni de Wheezy dans PMKB.

## 3. Branches supplémentaires des forks directs

- **Branches historiques communes** : `lgeek/okreader` publie déjà `glohd_bringup` et `wip`. Les **14 forks** qui les conservent sont **identiques à l'original sur ces mêmes branches** (0 ahead/0 behind). La branche [`lgeek: glohd_bringup`](https://github.com/lgeek/okreader/tree/glohd_bringup) a elle-même 2 commits d'avance et 3 de retard sur `master` ; elle explore i.MX6/Glo HD, **pas un boot Aura HD qualifié**.
- [Velsoth, `feature/booting-external-microsd`](https://github.com/Velsoth/okreader/tree/feature/booting-external-microsd) : **1 commit / README seul**. Décrit copie entre cartes puis modification de l'octet **0x3F d'un bloc HWCONFIG**, avec écriture brute sur carte. **ÉCARTER comme recette PMKB** : notre HWCONFIG v1.7 a **39 octets de payload** ; aucun contrat de ce commutateur ni compatibilité `dragon` démontrés.
- [prokinkd, `external-sd-instruction`](https://github.com/prokinkd/okreader/tree/external-sd-instruction) : documentation du même type (+ instructions SSH historiques) ; **aucun boot externe Aura HD attesté** et écritures HWCONFIG incompatibles avec nos invariants.
- [pazos, `patch-1` et `patch-2`](https://github.com/pazos/okreader/branches) : **1 commit documentaire chacune**, signalant le stockage de l'environnement U-Boot à partir du secteur **768** (128 secteurs) et une idée de démarrage alternatif. Ce n'est ni un outil de validation, ni une preuve sur l'U-Boot E606C0.
- [SuperTaiyaki, `ext4-instructions`](https://github.com/SuperTaiyaki/okreader/tree/ext4-instructions) : **1 ligne documentaire** recommandant de désactiver `metadata_csum` lors d'un formatage ext4 pour anciens noyaux. **INFO** : confronter à notre profil ext4 testé sur fichiers ; **aucun formatage de carte autorisé**.
- [jnetod, `jnetod-gitmodules-https`](https://github.com/jnetod/okreader/tree/jnetod-gitmodules-https) : **1 commit `.gitmodules` seulement** convertissant les URL SSH en HTTPS. Confort d'accès source, sans adaptation matérielle.

**Politique de conservation :** ne jamais altérer P2/recoveryfs, HWCONFIG, waveform, PRE-P1 ou FIRST BOOT scellé pour reproduire ces recettes. Aucun octet matériel n'a été touché dans cet audit.

## 4. Forks des sous-modules — comparaison à leur parent

| Source | Comparaison `master` | Décision PMKB |
| --- | --- | --- |
| [kratz00/linux-okreader](https://github.com/kratz00/linux-okreader) | **Identique** à `lgeek/linux-okreader` sur `master` et `imx6` | Aucun delta neuf. |
| [DroopCat/linux-okreader](https://github.com/DroopCat/linux-okreader) | Divergence massive (**967 913 ahead / 124 behind**), Makefile **Linux 6.3.0-rc1**, historique de merges Linux généraux ; `mx50_kobo_defconfig` et `mx50_ntx_io.c` historiques absents aux chemins vérifiés | **Ne pas présenter comme portage moderne E606C0**. Compteur de commits ≠ compatibilité EPDC/tactile/frontlight. Aucune preuve ciblée d'un noyau fonctionnel. |
| [kratz00/u-boot-okreader](https://github.com/kratz00/u-boot-okreader) | **Identique** à `lgeek/u-boot-okreader` | Aucun delta neuf. |
| [GNUtoo/u-boot-okreader](https://github.com/GNUtoo/u-boot-okreader) | **207 ahead / 1 behind** ; [reprise de patches Freescale/Kobo sur base historique](https://github.com/GNUtoo/u-boot-okreader/commit/466fec49eed3b0041d4e4a0e16aad54ebc06ead8) ; comparaison de très nombreux fichiers | Comparateur U-Boot **R1** uniquement. Ce nombre de commits reflète une histoire de branche remaniée, pas 207 correctifs validés pour notre Kobo. |
| [prokinkd/u-boot-okreader](https://github.com/prokinkd/u-boot-okreader) | **208 ahead / 1 behind** vs `lgeek`, mais seulement **1 commit d'avance** sur `GNUtoo:master` | [Correctif GCC 6.3.1](https://github.com/prokinkd/u-boot-okreader/commit/da8d0d767455e45e6a8039a5d38293ef3daf48c1) : retire `inline` devant des symboles à alias faibles dans `common/main.c` et `lib_arm/board.c`. **À tester uniquement si cette erreur est reproduite** dans notre toolchain. Aucun changement de bootloader décidé. |

Les outils GitHub limitent l'inventaire des énormes diffs à un sous-ensemble de fichiers (jusqu'à 300 dans les résultats observés). **Aucun audit complet des arbres U-Boot/Linux n'est revendiqué.**

## 5. Matrice de réutilisation et prochaine qualification

| Priorité | Hypothèse à qualifier | Critère de sortie |
| --- | --- | --- |
| **P1** | Ajouter au dossier HWCONFIG la table BloodRagg comme comparateur de valeurs multi-générations | Vérifier versions/tailles et licence ; tests de buffers tronqués/inconnus ; **zéro ouverture automatique de `/dev/*`** |
| **P1** | Étudier le correctif GCC de prokinkd si les références U-Boot bloquent à la compilation | Reproduire d'abord le diagnostic sur sources autorisées ; isoler le diff ; compiler hors carte |
| **P1** | Tirer des idées de `qemu-debootstrap`, toolchains ARM et compatibilité ext4 historique | Reproductibilité, dépendances, taille P1, coûts RAM/CPU mesurés ; conserver notre P1 et nos SHA |
| **P2** | Comparer docs external-SD et U-Boot avec notre analyseur PRE-P1 / matrice de boot | Analyse statique et preuves indépendantes ; **ne modifier ni l'offset 0x3F HWCONFIG, ni l'environnement U-Boot sur matériel** |
| **Écarté** | Installer OKReader historique, transplanter Linux 6.3-rc1 DroopCat comme « support Aura HD », mettre Glo HD sur `dragon` | Absence de preuve E606C0, runtime et recovery non conformes |

**Bilan audit : 16 forks directs comparés, branches des 16 inspectées, 5 forks de sous-modules comparés, 9/9 correspondances HWCONFIG de table, 0 compilation, 0 test matériel, 0 téléchargement, 0 modification des binaires PMKB ou de la carte.** Les comparaisons de GitHub sont des observations datées, susceptibles d'évoluer. Le FIRST BOOT physique reste **NON QUALIFIÉ**.
