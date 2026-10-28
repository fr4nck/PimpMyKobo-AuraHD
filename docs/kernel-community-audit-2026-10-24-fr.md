# PMKB — audit communautaire noyau/ZForce, lot R1/R3 du 24 octobre 2026

**Livraison : comparaison ciblée de quatre noyaux, décision de ne pas importer leur pilote ZForce en bloc, et correctif du filtrage tactile natif.** Aucun noyau, bootloader, image, carte ou firmware modifié. Les résultats historiques sont conservés.

## État vérifié avant développement

Dépôt : `fr4nck/PimpMyKobo-AuraHD`.

- `main` : `4df1e2aea33d3951afb2b41b4dfd82075ece540e` ; derniers commits documentaires R0–R10.
- PR #7 ouverte, non fusionnée : `integration/pmkb-first-boot-1`, HEAD `6b0506a085c3f19d818f71fbeebcd7c8da8c3abf`.
- PR #28 ouverte en brouillon : `feat/pmkb-powerlab-kernel-v0`, HEAD `644a79e3bcf40a6d7fbd074c7f5f7ceabe7518e3`.
- PR #30 ouverte en brouillon : `feat/pmkb-ui-native-v0`, initial `e6d5e75e602a55bffb2b445f558aa927ae077f62`.
- PR #25–#27 et #29 ouvertes sur les prototypes Launcher/Notes ; aucun de leurs fichiers modifié. Les refs ont été revérifiées avant publication ; aucun changement concurrent constaté sur les deux branches éditées pendant ce lot.
- Instructions `AGENTS.md` identiques sur ces branches, sans instruction imbriquée dans les arbres examinés. README, roadmap, registre, dossier matériel, qualification hors appareil, FIRST BOOT, ADR-005, contrats natifs et sécurité/frugalité de #28 relus.

Le code est publié dans la branche native existante, commit
[9514effd3a1a00febb49882049fcc433428ecd6e](https://github.com/fr4nck/PimpMyKobo-AuraHD/commit/9514effd3a1a00febb49882049fcc433428ecd6e), **PR #30 toujours en brouillon, sans merge**.
Le présent dossier et le registre sont publiés séparément sur `main` :
aucune fusion des chantiers anciens ni nouvelle branche nécessaire.

FIRST BOOT protégé : `PMKB-FIRST-BOOT-1-0b00d858.img`,
SHA-256 `7980fec15cb62ca3c2cabcb64cbbb683446fbf64070d75b45acf9a5e99e0f67c`.
Ce fichier n'est pas présent dans l'environnement de cette session : **aucune
nouvelle vérification de son empreinte n'est revendiquée**. Le diff livré
ne touche ni son générateur, ni PRE-P1, P1/P2/P3, U-Boot, HWCONFIG ou waveform.

## Sources et méthode reproductible

Lecture ciblée par GitHub à révisions figées, sans clone noyau, archive,
firmware, dépendance ou toolchain téléchargés. Comparaison intégrale des
quatre fichiers ZForce ; comparaison des autres fichiers listés ci-dessous,
avec lecture ciblée des différences utiles. **Ce n'est pas un audit complet
des quatre arbres ni une preuve d'identité avec notre uImage.**

| Alias | Source | Révision examinée |
| --- | --- | --- |
| P | [pazos/linux-2.6.35.3-kobo](https://github.com/pazos/linux-2.6.35.3-kobo/tree/1f43a4a01a727a9b440f2e8830b67734b6373a10) | `1f43a4a01a727a9b440f2e8830b67734b6373a10` |
| L | [lgeek/linux-okreader](https://github.com/lgeek/linux-okreader/tree/2a4689f1c0d2608e555bd0b12c8da89ca4a98724) | `2a4689f1c0d2608e555bd0b12c8da89ca4a98724` |
| G | [giorgio130/linux-2.6.35-kobo-multitouch](https://github.com/giorgio130/linux-2.6.35-kobo-multitouch/tree/b46a506b300e1eebc9bd1bf9c5369ae92fb7e200) | `b46a506b300e1eebc9bd1bf9c5369ae92fb7e200` |
| B | [brunotl/kernel-kobo-mx50-ntx](https://github.com/brunotl/kernel-kobo-mx50-ntx/tree/884fec254ce71a11f7e71d2e88e751772ccd1bc3) | `884fec254ce71a11f7e71d2e88e751772ccd1bc3` |

Autres sources effectivement lues :

- [FBInk, révision 886f25f13368859ad8a899b88d04c26e19cda32e](https://github.com/NiLuJe/FBInk/tree/886f25f13368859ad8a899b88d04c26e19cda32e) : `fbink.c` (fonctions `refresh_kobo`, `wait_for_complete_kobo`, `refresh`, marqueurs), SPDX et `LICENSE`.
- [Documentation Linux v6.18 des événements input](https://github.com/torvalds/linux/blob/v6.18/Documentation/input/event-codes.rst) : état evdev, `SYN_DROPPED`, `BTN_TOOL_DOUBLETAP`. C'est une référence de contrat userspace, pas une preuve de la totalité du comportement du BSP 2.6.35.3.
- [Sources officielles Aura HD](https://github.com/kobolabs/Kobo-Reader/tree/7a762964e7fa71ad8e8df50dd1b6eee721a43217/hw/imx507-aurahd) : métadonnées de l'archive noyau **132 718 922 octets**, non téléchargée. L'audit historique [hors appareil](offline-hardware-qualification-fr.md) avait déjà comparé 19 fichiers à cette archive ; il conserve cette preuve et ses limites. **Aucune nouvelle extraction ou comparaison officielle intégrale cette session.**
- ADR-005 PMSL-Arch : blob `4017615213eea812b8864a221a3bb4babe9ee2bf` relu. Correction centralisée dans la primitive commune, sans changer le layout Notes.

### Empreintes Git des fichiers comparés

Chaque colonne renvoie à la révision complète ci-dessus ; un blob identique
prouve l'égalité de ce fichier uniquement, pas des configurations, de ses
dépendances ou des binaires. Les chemins sont relatifs à la racine du noyau.

| Fichier | P | L | G | B |
| --- | --- | --- | --- | --- |
| `drivers/input/touchscreen/zforce_i2c.c` | `7a1694f0927aeb916c6d4c7b78b6060aab52ccac` | `8ab55028a2f5097afc8e94e4710a62ff41ef9fe9` | `7efd47b8a64c3f73b770e81e9305579095b03b84` | `9d903ee3dc0285a004dbe9ba59dae0760399fabc` |
| `drivers/video/mxc/mxc_epdc_fb.c` | `5b8d2b55713bb3e1e785c2d67d4e65e76bee2ce2` | `8ac02d98cbebff02e0da65dd911e9fe29ff48765` | `f16ff808b5e9e73ccd21418af7b00a6bdf9a40b7` | `8a88f664417bac4c1723a4c195764813ffbd3d0f` |
| `drivers/video/mxc/mxc_epdc_fake_s1d13522.c` | `be14190b85bfa459aa2e006eafe248811d4dc2a5` | `a7e27b79271ab9a7f26251c3d621468a7e0884e3` | `a7e27b79271ab9a7f26251c3d621468a7e0884e3` | `1e5c9eaf3478e93ee4e237dcf067654228374104` |
| `drivers/mxc/pmic/core/pmic_core_i2c.c` | `38d6abd4f000e8707c8dbca5bdb403010727a05b` | `38d6abd4f000e8707c8dbca5bdb403010727a05b` | `38d6abd4f000e8707c8dbca5bdb403010727a05b` | `2d0c6d4c6fe55e5c4269f48fa6e88c91387b0294` |
| `arch/arm/mach-mx5/mx50_ntx_io.c` | `5833e69094268027e3993cf103a3d813496c6cdf` | `8aa7839bb122d322d0f78fa6f554a8c1ce87c826` | `8aa7839bb122d322d0f78fa6f554a8c1ce87c826` | `a39802ea30b8ff1da3ba88fe0dd9a0d5feb9c12f` |
| `arch/arm/mach-mx5/pm.c` | `2fa9d7758b9ff6985505a2ce6b640cc5633b9f54` | `2fa9d7758b9ff6985505a2ce6b640cc5633b9f54` | `2fa9d7758b9ff6985505a2ce6b640cc5633b9f54` | `2fa9d7758b9ff6985505a2ce6b640cc5633b9f54` |
| `drivers/mmc/host/mx_sdhci.c` | `455b5ce98dc3041cbb3782a57f6f5a340724316c` | `750073773cd390e61e6aab5456464c5c92e0519a` | `750073773cd390e61e6aab5456464c5c92e0519a` | `e76b085cd6206026ebf388a073a244a1236d829d` |
| `arch/arm/mach-mx5/usb_dr.c` | `183a7822898775a859820d199cab7eab7fd5da32` | `183a7822898775a859820d199cab7eab7fd5da32` | `183a7822898775a859820d199cab7eab7fd5da32` | `183a7822898775a859820d199cab7eab7fd5da32` |
| `include/linux/mxcfb.h` | `18892a100af84c346c876a253468f20163d105d7` | `251be2477c0c3b1507b66e06b4458585c6f6c11b` | `251be2477c0c3b1507b66e06b4458585c6f6c11b` | `18892a100af84c346c876a253468f20163d105d7` |

Les quatre `COPYING` ont le même blob
`ca442d313d86dc67e0a2e5d584b465bd382cbf5c`.

## ZForce : différences et décision

Fonctions examinées en entier dans P/L/G/B :
réception, handshake, rapport input, queue/work, reset (lorsqu'il existe),
probe/axes, open/close et suspend/resume.

1. **P contre L :** une ligne blanche ajoutée dans suspend, aucun changement
   fonctionnel de `zforce_i2c.c`. L ne fournit donc pas une correction
   multitouch ou une amélioration tactile démontrée par ce fichier.
2. **P/L :** le récepteur déplace les enregistrements de 9 octets en v2
   (7 dans l'ancien protocole), mais le rapporteur ne traite que le premier.
   Sortie `ABS_X/Y/PRESSURE` et `BTN_TOUCH`, sans `ABS_MT_*`.
3. **G :** handshake Activation → Résolution → Configuration dual touch
   (`0x03`, charge `01 00 00 00`) → Fréquence → TouchData.
   La relance après overrun ajoute aussi l'étape Configuration. Le compteur
   de contacts est conservé dans la trame ; parcours de tous les contacts,
   identifiants dérivés du champ de quatre bits moins un. Ajout
   `ABS_MT_TRACKING_ID/POSITION_X/Y/TOUCH_MAJOR/WIDTH_MAJOR`,
   `input_mt_sync()` entre contacts et `input_sync()` en fin de rapport.
   Les slots sont commentés : **protocole de type A, pas type B**.
   `BTN_TOOL_DOUBLETAP` signale deux contacts selon son compteur.
4. **Coordonnées :** en mode customer UI, P/L et G font miroir sur X brut
   puis permutation des axes ; hors customer UI, P/L permutent les axes
   alors que G conserve X/Y bruts. G calcule la résolution avant les bornes
   ABS et annonce largeur/hauteur moins un, là où P/L enregistrent encore
   leurs valeurs initiales. Le couplage de ces bornes aux axes permutés
   reste à vérifier ; **ne pas en déduire une calibration dragon**.
5. **B :** fréquence v2 10 au lieu de 50 pour le premier paramètre ;
   absence de branche `DisplayResolution=3` 1080×1440 ; suppression du reset
   GPIO, des vérifications négatives I²C et du relâchement de secours.
   Replanification sur IRQ plutôt que sur contact maintenu. Ce n'est pas
   un remplacement adapté à notre HD en l'état.

### Défauts statiques empêchant une reprise de G en bloc

- `id=((champ>>2)&0x0f)-1` : un champ ID nul produit **-1**, utilisé
  aussitôt pour indexer les tableaux, sans validation.
- `fingers_down++` est exécuté à chaque DOWN **et MOVE**, pas seulement
  lors de la transition inactif → actif ; une seule levée ne compense pas
  plusieurs déplacements. Le nombre de doigts et les touches peuvent donc
  rester erronés. L'état 3, traité comme invalide/libération dans P, entre
  également dans la branche active de G.
- Longueur I²C et nombre de contacts non bornés contre les buffers de
  **129 octets** ; `memmove` repose sur le compteur reçu. La longueur
  de réception, les lectures courtes et le produit taille×compteur doivent
  être validés **avant** toute boucle ou copie. P/L/B ont déjà des
  insuffisances de validation ; cela ne rend pas G acceptable.
- Le secours de relâchement hérité écrit encore à `[4]`, alors que G
  place un compteur devant les contacts : la position/les bits du champ
  état/ID ne correspondent plus. Le travail différé ne suit que
  `g_touch_pressed[0]` ; la garde suspend n'examine que [0]/[1].
- Le reset efface les flags de contact mais pas le compteur statique local
  `fingers_down` ni tous les historiques. Suspend/resume conserve la
  séquence Deactive/Active héritée : aucune preuve de remise à zéro propre
  ou de fonctionnement énergétique.

Ces constats proviennent du code : **pas d'exploitation, CVE attribuée,
test I²C ou exécution du pilote noyau** pendant ce lot.

**Décision : ÉCARTER l'import direct de G ; RETENIR l'idée d'une prise en
charge multi-contact bornée, avec compteur fondé sur les transitions,
contrat evdev choisi et tests de trames invalides.** Un backport ciblé sur
le BSP 2.6.35.3 est une voie de travail plausible puisque les interfaces MT
sont utilisées dans ce fork de cette génération ; **compilation et
compatibilité Aura HD non démontrées**. La base officielle exacte doit
être confrontée avant un patch noyau, dans un artefact expérimental distinct.

## Matrice de décisions

| Composant | Source / code examiné | Modification | Bénéfice envisagé | Risque | Décision |
| --- | --- | --- | --- | --- | --- |
| ZForce legacy | P/L, `zforce_i2c.c` | Identiques hors blanc ; 1 contact rapporté | Base comprise et conservée | Lectures courtes, tailles, axes historiques | RETENIR comme comparateur, TESTER les validations avant toute évolution |
| ZForce MT | G, même fichier | Dual touch, type A, IDs, nouvelle initialisation | Gestes à deux doigts ultérieurs | ID négatif, comptage, taille, reset et axes | ÉCARTER en bloc ; TESTER une réécriture ciblée |
| ZForce ancien | B, même fichier | Fréquence, reset/replanification, résolution HD absente | Aucun gain HD prouvé | Régression résolution/erreurs/reprise | ÉCARTER comme pilote de remplacement |
| EPDC | P/L/G/B, `mxc_epdc_fb.c`, fake S1D, `mxcfb.h` | L/G ajoutent mode/waveform, buffers/queue et mutex/workqueue ; header ORG supplémentaire | Gestion de collisions et modes à étudier | Diff important, waveform/RAM/DMA, ABI et verrouillage | TESTER seulement des hunks isolés ultérieurs ; pas de remplacement |
| HAL E-Ink | FBInk `refresh_kobo/wait_for_complete_kobo/refresh` contre PMKB surface/backend/HAL | FULL/PARTIAL, marqueur non nul, attente, évitement de refresh demandé, rejet zones ≤1 | Confirme nos primitives existantes | Contraintes d'alignement et régions minces à qualifier | RETENIR les contrats ; backend physique doit normaliser les rectangles, aucun patch écran spéculatif ici |
| MSP430/PMIC | `pmic_core_i2c.c` | P=L=G ; B réactive probes MC13892 et change alarme | Pas de gain démontré pour notre MCU | Réveil/RTC/rails, version réelle inconnue | RETENIR la chaîne historique ; ÉCARTER le transplant B |
| Frontlight / alimentation | `mx50_ntx_io.c` | L/G réorganisent tables lumière, timers batterie et ajoutent branches PCB/Wi-Fi/DVFS | Ajustements ponctuels à étudier | Table SY7201, GPIO d'autres PCB ; workaround DVFS conditionnel | TESTER séparément après mesure, pas reprendre le fichier entier |
| Suspend/reprise plateforme | `arch/arm/mach-mx5/pm.c` | P=L=G=B | Aucun delta dans ce fichier | Les autres chemins PM diffèrent | RETENIR le fichier ; aucune amélioration d'autonomie conclue |
| MMC/SDIO | `mx_sdhci.c` | L/G ajoutent attente DAT0 bornée 250 ms et modifient comptage SDIO | Stabilité commandes BUSY à examiner | Attente active sous verrou, latence/énergie et SDIO | TESTER isolément avec les appelants et vraie carte, pas de backport immédiat |
| USB/OTG | `arch/arm/mach-mx5/usb_dr.c` | P=L=G=B | Aucun delta dans ce fichier | VBUS, câblage et autres fichiers non qualifiés | RETENIR pour comparaison ; OTG E606C0 reste UNQUALIFIED |
| Sécurité | Réception ZForce et contrats #28 | Tailles/IDs non validés identifiés ; aucun correctif CVE importé | Stabilité et mémoire avant nouvelles fonctions | L'ancien noyau reste non maintenu | RETENIR un prochain lot parser ; aucune certification sécurité |

Pour EPDC, la lecture des différences porte notamment sur les buffers,
les choix de waveform, le changement de verrou, la sélection des LUT et
la synchronisation ; **pas une validation de chaque hunk**. `pm.c` et
`usb_dr.c` identiques ne signifient ni alimentation ni USB globalement
identiques. Aucun des quatre noyaux n'a été compilé dans cette session.

## Amélioration développée : le filtre de gestes PMKB

Le signal deux doigts étudié dans G était ignoré par `pmkb_touch_feed()`.
Un geste à deux doigts pouvait devenir TAP. Après `SYN_DROPPED`, la HAL
annulait le geste en cours, mais acceptait immédiatement la trame suivante
alors qu'elle devait être jetée. Les deux défauts ont été **reproduits sur
le code de production hôte avant correction**, puis contre-qualifiés.

Le correctif commun :
- annule le geste signalé à deux doigts jusqu'au relâchement complet ;
- ignore la trame perdue jusqu'au `SYN_REPORT` inclus ;
- attend une libération explicite dans une trame propre ;
- oublie les coordonnées rejetées et permet ensuite un nouvel appui normal.

Fichiers modifiés :
`experimental/native-ui/pmkb_hal.c`, `pmkb_hal.h`,
`tests/native_hal_tests.c` et `docs/native-hal-v0-offline-qualification-fr.md`.
Aucun changement Notes/Calculatrice particulier : la primitive est commune.
**Pas d'activation multitouch ni d'acquisition evdev réelle.** Le pilote
P/L ne signale pas le deuxième doigt ; cette protection ne peut donc pas
détecter les contacts que le noyau ne rapporte pas.

L'adaptateur evdev futur devra relire l'état `EVIOCG*` après perte. L'API
pure ne le fait pas et peut ignorer un appui supplémentaire si la libération
était dans la trame perdue. Cette limite est documentée dans son header :
ne pas présenter ce filtre comme une resynchronisation matérielle complète.

## Licences et attributions vérifiées

- P/L/G/B : `COPYING` GPLv2, et notices individuelles conservées en
  référence. ZForce déclare explicitement **GPLv2** et Joseph Lai comme
  auteur. EPDC et plusieurs fichiers Freescale déclarent **GPLv2+**.
- `include/linux/mxcfb.h` déclare **LGPL-2.1-or-later**.
  `mx50_ntx_io.c` et le fake S1D n'ont pas de notice individuelle claire
  en tête : obligations de provenance à revoir avant toute reprise effective.
- FBInk `fbink.c` : SPDX **GPL-3.0-or-later**, `LICENSE` vérifié.
- **Aucun code de ces projets copié, lié ou distribué par ce lot** ;
  constantes du protocole et comportement documentés, implementation
  originale dans PMKB. Aucun blob, waveform, firmware ou dump publié.
  La licence propre du projet PMKB reste à choisir comme indiqué au README.

## Qualification démontrée

| Contrôle | PASS | FAIL | SKIP | UNQUALIFIED |
| --- | --- | --- | --- | --- |
| Sources et provenance | 4 révisions et 36 fichiers comparés, 4 COPYING ; FBInk et contrat input | 0 | Archive officielle 132,7 Mo non récupérée | Identité binaire/source du noyau réel |
| Comparaison pilotes | ZForce complet ; autres fichiers/deltas délimités ci-dessus | 0 test exécuté en échec final | Exhaustivité des arbres et CVE hors lot | Comportement réel I²C/IRQ |
| Tests logiciels hôte | **939 assertions / 28 groupes**, JSON **1/1**, images **6/6** ; 2 défauts avant/après ; analyse GCC sans diagnostic | **0 final** ; défauts antérieurs reproduits | LeakSanitizer local bloqué par /proc | Fidélité physique des flux synthétiques |
| Compilation | C11 GCC 13.3.0 strict ; ASan/UBSan avec detect_leaks=0 | 0 après adaptation de l'environnement | ARM : compilateur absent ; kernel/QEMU non construits | ABI liée au rootfs historique |
| Aura HD | Aucun PASS physique revendiqué | Aucun essai physique | Aucun accès appareil | Tactile, EPDC, veille/réveil et boot |
| RAM et énergie | Mesure hôte : PMKBTouch **72→72 octets**, objet HAL texte **2237→2509 (+272)**, data/bss 0 ; aucune allocation ajoutée | 0 | Mesures matérielles non lancées | RAM totale, latence et autonomie Kobo |

La première tentative ASan/UBSan avec LeakSanitizer activé s'est arrêtée
sur une erreur de lecture de `/proc/.../task` de l'environnement. Le rejeu
avec **seule la détection de fuites désactivée** a réussi ; ce n'est pas une
preuve de LeakSanitizer. Les tests standards et le rejeu sanitizers comptent
les mêmes 939 assertions, **ne pas les additionner**.

Rejeu : `make -C experimental/native-ui test` sur la branche native.
Détails des scénarios, flags et coûts dans
[la qualification native au commit livré](https://github.com/fr4nck/PimpMyKobo-AuraHD/blob/9514effd3a1a00febb49882049fcc433428ecd6e/docs/native-hal-v0-offline-qualification-fr.md).
La CI native [push](https://github.com/fr4nck/PimpMyKobo-AuraHD/actions/runs/40131946318)
et [PR](https://github.com/fr4nck/PimpMyKobo-AuraHD/actions/runs/40131949216)
est terminée avec **SUCCESS** au commit publié. Ses logs confirment les
939 assertions, JSON 1/1 et images 6/6, ainsi que le rejeu ASan/UBSan sans
la désactivation locale de LeakSanitizer. L'étape ARM affiche explicitement
ARM_OBJECTS=SKIP (compilateur absent). La [suite générale du dépôt](https://github.com/fr4nck/PimpMyKobo-AuraHD/actions/runs/40131949253)
a également **10/10 jobs terminés SUCCESS** (Linux/Windows, Python 3.10–3.13
et Qt). Aucun workflow relancé manuellement.

## Reprise immédiate et mesures futures

1. **Lot suivant recommandé :** réception ZForce bornée sur base officielle
   exacte, tests hôte des trames tronquées, tailles/count/ID nuls et trop
   grands, état 3, déplacements répétés, reset et reprise. Choisir ensuite
   type A ou B en fonction de l'API 2.6.35.3 et des consommateurs KOReader.
   Aucun pilote/image noyau nouveau tant que la comparaison officielle et
   la compilation ne sont pas disponibles.
2. **Backend natif ensuite :** découverte evdev par identité/capacités,
   snapshot après perte, axes dragon explicites ; EPDC avec header exact,
   bornes/stride/rotation, régions minces et marqueurs, sans changer la waveform.
3. **Émulation QEMU :** reprendre R2, examiner la carte E606C0, ne pas
   substituer des fixtures au vrai FIRST BOOT. Aucun binaire QEMU ou fichier
   privé de carte disponible/utilisé pour ce lot. Les lots C/D/E/F complets
   ne sont pas prétendus terminés.
4. **Qualification sur vraie Kobo, seulement après autorisation spécifique :**
   carte expérimentale distincte et rollback préservé ; conserver mêmes
   fichiers et réglages, documenter versions/empreintes et au moins cinq
   répétitions. Tactile aux coins/centre, appuis répétés, second contact,
   glissement, perte/reprise ; capturer les événements et compter TAP
   attendus/émis. Affichage fixe puis petits changements : compter
   soumissions/attentes, observer ghosting et complet/partiel. Mesurer RAM
   au repos, temps boot/page/tap et énergie dans des scénarios identiques,
   avec appareil de mesure et durée consignés. Garder séparés observations
   et témoignages MobileRead ; **aucun gain matériel chiffré à ce stade**.

Aucune restriction de sécurité nouvelle ni service permanent ajouté.
FIRST BOOT #1 reste le candidat intact ; sa qualification physique reste
distincte de toutes ces recherches.
