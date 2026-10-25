# PMKB — Registre de recherche et sources externes

**Création : 24 octobre 2026.** Registre évolutif pour la **Kobo Aura HD N204 / Netronix E606C0 / i.MX507 / 512 Mio**. À consulter avant de lancer un audit, de concevoir un composant ou de réimplémenter une fonctionnalité déjà explorée ailleurs.

**Finalité :** garder ensemble les **sources d'information**, les **sources d'inspiration** et les **candidats à une intégration technique**. Un lien ici ne signifie **ni code accepté, ni licence compatible, ni fonctionnement sur notre exemplaire**. Les caractéristiques proviennent des README ou des fichiers ciblés consultés ; la compilation et les essais matériels restent à faire.

**Priorité absolue inchangée : FIRST BOOT KOReader sans Nickel sur une carte de test distincte.** Les recherches sont parallèles et ne doivent pas le retarder. Le candidat FIRST BOOT scellé, PRE-P1, P2, les sauvegardes privées et leurs SHA-256 ne sont pas modifiés par cette feuille.

## Mode d'emploi

- **INFO** : documentation, historique matériel, techniques ou retours d'expérience ; pas nécessairement du code à copier.
- **INSPIRATION** : idées d'ergonomie, d'interface, d'architecture ou d'outillage, à adapter à PMKB.
- **CANDIDAT** : source pouvant être comparée, patchée, adaptée ou réutilisée **après qualification du diff, dépendances, licences et ABI**.
- **P0** : essentiel au FIRST BOOT / support E606C0 ; **P1** : socle natif, Notes, terminal et services ; **P2** : idées, options futures ou dépendances Nickel.
- **À analyser** = piste identifiée et code ou README consulté ; **NON QUALIFIÉ** = aucune preuve de fonctionnement sur notre Kobo / notre PMKB. Un test QEMU n'est pas un test sur écran E-Ink, batterie ou veille réels.

## A. Matériel, noyau, bootloader et émulation

| Priorité | Source | Usages | Intérêt précis et vérifications requises |
| --- | --- | --- | --- |
| P0 | [Kobo-Reader / hw/imx507-aurahd](https://github.com/kobolabs/Kobo-Reader/tree/master/hw/imx507-aurahd) | INFO / CANDIDAT | Sources historiques Netronix du noyau 2.6.35.3 et U-Boot ; référence E606C0, à comparer à nos copies et configurations, sans publication de firmware propriétaire. |
| P0 | [pazos/linux-2.6.35.3-kobo](https://github.com/pazos/linux-2.6.35.3-kobo) | INFO / CANDIDAT | Arbre Linux 2.6.35.3 avec code Netronix et la chaîne ZForce ; comparaison ciblée avec l'image noyau 2.6.35.3-850-gbc67621+, sans supposer une égalité binaire. |
| P0 | [lgeek/linux-okreader](https://github.com/lgeek/linux-okreader) | INFO / CANDIDAT | Noyau 2.6.35.3 et `localversion` `-850-gbc67621` ; examiner adaptations Linux, EPDC, tactile, intégration Debian/KOReader. |
| P1 | [marek-g/kobo-kernel-2.6.35.3-marek](https://github.com/marek-g/kobo-kernel-2.6.35.3-marek) — [audit M02](marek-kobo-kernel-audit-2026-10-25-fr.md) — [audit des 16 copies M02bis](marek-kernel-forks-audit-2026-10-25-fr.md) | INFO / CANDIDAT CIBLÉ EPDC | Noyau Kobo Touch **N905C** (2013) : détection des régions e-ink par CRC16 de tuiles 16×8, rafraîchissement complet au-delà de 3/4 des lignes, réduction de **10 à 1 buffer** EPDC (gain **15 Mo revendiqué sur Touch**, pas mesuré sur Aura HD), ZForce dual-touch. **Aucune qualification E606C0** ; défauts de bornage tactile et d'allocation observés. Comparateur frugal PMKB-UI, **pas de remplacement de noyau**. |
| P1 | [marek-g/kobo-kernel-2.6.35.3-android](https://github.com/marek-g/kobo-kernel-2.6.35.3-android) — [audit M03](kobo-service-android-audit-2026-10-25-fr.md) | INFO / CANDIDAT CIBLÉ EPDC/ZForce | Noyau issu de **Tolino Shine / Kobo Glo sous Android** (2013) ; API e-ink 4 modes via `ioctl(0x40044633 / 0x80044634)`, tramage **Atkinson Y8→Y1**, chemin NEON présent mais non appelé, **4 buffers** EPDC selon RAM, rotation ZForce et configuration **1440×1080** selon HWCONFIG. Application compagnon `kobo-service` ci-dessous. **Pas de boot Aura HD démontré**, ABI à vérifier avant toute adaptation. |
| P0 | [lgeek/u-boot-okreader](https://github.com/lgeek/u-boot-okreader) | INFO / CANDIDAT | Source d'étude des transitions U-Boot, HWCONFIG, paramètres noyau et waveform ; **pas de remplacement du bootloader**. |
| P0 | [lgeek/okreader](https://github.com/lgeek/okreader) | INFO / INSPIRATION | Debian + KOReader sans Nickel sur certaines Kobo i.MX507 ; **Aura HD non testée (« kernel upg? »)**. **[Fiche matérielle M01](#m01-okreader)** : architecture, USB, réseau, licences et écarts avec PMKB E606C0. |
| P0 | [giorgio130/linux-2.6.35-kobo-multitouch](https://github.com/giorgio130/linux-2.6.35-kobo-multitouch) | INFO / CANDIDAT | Diff concret de `drivers/input/touchscreen/zforce_i2c.c` : `ABS_MT_POSITION_X/Y`, contacts multiples et `BTN_TOOL_DOUBLETAP` ; vérifier protocole ZForce v2, axes, veille, stabilité et compatibilité avec l'image PMKB. Aucun multitouch matériel encore qualifié. |
| P0 | [katadelos/eink-emulator](https://github.com/katadelos/eink-emulator) — [profil Aura HD](https://github.com/katadelos/eink-emulator/blob/main/docs/kobo-aura-hd.md) | INFO / CANDIDAT | Émulateur QEMU **E606C0** expérimental ; valide une géométrie PRE-P1/P1/P2 conforme aux offsets connus et recrée une petite P3. Explorer boot de notre P1 scellée, logs et input en **simulation**, avec fichiers privés locaux seulement. |
| P0 | [katadelos/qemu, branche eink-emulator](https://github.com/katadelos/qemu/tree/eink-emulator) | INFO / CANDIDAT | Carte virtuelle `imx50-kobo-aura-hd` : i.MX507, ZForce, MSP430, PMIC, stockage, réseau. Le machine ID **2988** n'y sert qu'au démarrage direct `-kernel` ; avec `-bios`, c'est le vrai U-Boot de la carte qui le transmet. Hypothèse à recouper sur notre U-Boot réel : voir *Exploitation R2*. |
| P1 | [brunotl/kernel-kobo-mx50-ntx](https://github.com/brunotl/kernel-kobo-mx50-ntx) | INFO / CANDIDAT | Autre arbre Linux 2.6.35.3 i.MX50/NTX ; établir d'abord son historique et ses différences réelles, notamment USB, alimentation et périphériques, avant de retenir quoi que ce soit. |
| P2 | [pazos/linux-3.0.35-kobo](https://github.com/pazos/linux-3.0.35-kobo) | INFO | Arbre Linux 3.0.35 pour d'autres générations de Kobo ; comparateur architectural **non démontré compatible Aura HD** et non retenu comme noyau PMKB. |
| P2 | [postmarketOS / pmaports](https://gitlab.com/postmarketOS/pmaports) — [portage Clara HD](https://gitlab.com/postmarketOS/pmaports/-/merge_requests/2334) | INFO / INSPIRATION | Techniques de portage E-Ink, extraction de waveform et intégration userspace ; **Clara HD i.MX6SLL ≠ Aura HD i.MX507**. Pas de transposition de pilotes sans preuve. |
| P2 | [twhitehead/notes-kobohacking](https://github.com/twhitehead/notes-kobohacking) | INFO | Notes sur U-Boot, extraction du `uImage`, console série, recovery et USB, sur Kobo Aura/Glo. Les commandes d'écriture et manipulations MSP430 sont **des exemples historiques, jamais à exécuter directement**. |

### M01 OKReader

**Inventaire élargi (25 octobre 2026) :** [60 dépôts publics du compte lgeek et qualification Kobo/ARM](lgeek-account-audit-2026-10-25-fr.md). Les 60 noms sont recensés ; seules les pistes utiles ont fait l'objet d'une lecture de code et de comparaisons ciblées. Les branches KOReader Wi-Fi, veille et RTC y sont analysées contre des sources upstream récentes.

**Complément :** [audit des 16 forks directs, branches expérimentales et 5 forks des sous-modules](okreader-forks-audit-2026-10-25-fr.md) (25 octobre 2026) ; comparaison des apports réels, risques HWCONFIG/boot et décisions R1/R5.

**Bibliothèque des adaptations matérielles Kobo — fiche du 25 octobre 2026.** La matrice ci-dessus reste l'index des projets ; cette fiche consigne les faits **lus dans les sources** et les décisions PMKB, sans constituer une recette d'installation.

**Référence figée :** [lgeek/okreader, `2c253e5becbf22fd16960edca4f37eba2c03556a`](https://github.com/lgeek/okreader/tree/2c253e5becbf22fd16960edca4f37eba2c03556a) (dernier commit observé : 29 juin 2018). Lecture statique de `README.md`, `LICENSE`, `.gitmodules`, `build.sh`, `build_rootfs.sh`, `files/fstab`, `files/rc.local`, `files/okreader.sh`, `files/enable-wifi.sh`, `files/disable-wifi.sh`, `files/obtain-ip.sh`, `files/release-ip.sh` et `files/defaults.persistent.lua`. **Aucun téléchargement, compilation, démarrage, essai E606C0 ni copie de code tiers.** Les sous-modules `linux-okreader`, `u-boot-okreader` et `koreader` sont distincts : pour les deux premiers, utiliser également le [comparatif R1/R3](kernel-community-audit-2026-10-24-fr.md), qui a déjà audité neuf fichiers noyau à des révisions épinglées.

| Couche / preuve | Comportement observé dans OKReader | Décision pour PMKB Aura HD |
| --- | --- | --- |
| **Compatibilité** — [README](https://github.com/lgeek/okreader/blob/2c253e5becbf22fd16960edca4f37eba2c03556a/README.md) | Tests annoncés sur **Touch, Mini, Aura** ; Glo confirmé par un tiers. Aura **HD : « kernel upg? »** dans le tableau de compatibilité, et possibles modifications U-Boot/noyau. | **NON QUALIFIÉ E606C0**. Ne pas extrapoler du simple SoC i.MX507 à `dragon` (résolution, frontlight, HWCONFIG et pilotes). |
| **Bootloader** — [build.sh](https://github.com/lgeek/okreader/blob/2c253e5becbf22fd16960edca4f37eba2c03556a/build.sh), [.gitmodules](https://github.com/lgeek/okreader/blob/2c253e5becbf22fd16960edca4f37eba2c03556a/.gitmodules) | Compilation `mx50_rdp_config` depuis `lgeek/u-boot-okreader` ; installation historique avec réécriture du bootloader. | **INFO / COMPARATEUR R1** : confronter les adaptations Netronix au vrai U-Boot E606C0, sans flash ni remplacement PRE-P1. |
| **Noyau / drivers** — [build.sh](https://github.com/lgeek/okreader/blob/2c253e5becbf22fd16960edca4f37eba2c03556a/build.sh) | `mx50_kobo_defconfig`, `uImage`, modules Linux **2.6.35.3** ; backport `brcmfmac` provenant de **backports 3.14.22-1**. | **INFO / CANDIDAT CIBLÉ R1** : comparer les configurations et patches EPDC/ZForce/MMC/NTX ; **aucun nouveau noyau retenu**. Reprendre l'audit R1/R3 existant plutôt que le dupliquer. |
| **HWCONFIG / waveform** — [README](https://github.com/lgeek/okreader/blob/2c253e5becbf22fd16960edca4f37eba2c03556a/README.md), [build.sh](https://github.com/lgeek/okreader/blob/2c253e5becbf22fd16960edca4f37eba2c03556a/build.sh) | Repère historique HWCONFIG au secteur **1024** (offset `0x80000`) ; description d'une zone initiale **15 Mio** sur les cartes documentées. Génération d'un paquet `kobo_hwconfig`. | Sur **notre** Aura HD, HWCONFIG `0x80000` est effectivement observé, mais PRE-P1 mesure **9 961 472 octets = 9,5 Mio**, pas 15 Mio. Valider les données réelles via [partitionnement](partition-layout-fr.md), jamais recopier la géométrie OKReader. |
| **Rootfs / RAM** — [build_rootfs.sh](https://github.com/lgeek/okreader/blob/2c253e5becbf22fd16960edca4f37eba2c03556a/build_rootfs.sh), [fstab](https://github.com/lgeek/okreader/blob/2c253e5becbf22fd16960edca4f37eba2c03556a/files/fstab) | `debootstrap --arch=armhf --variant=minbase wheezy`, puis OpenSSH, udev, dhcpcd, outils réseau ; `tmpfs` pour logs, `/tmp` et documentation. | **ÉCARTER le rootfs de 2018** : Debian Wheezy obsolète ; mesurer RAM/stockage/veille pour une base moderne à **512 Mio**, sans gros démons permanents. Les idées `tmpfs` exigent un budget RAM et une voie de diagnostic. |
| **Wi-Fi / services** — [activation](https://github.com/lgeek/okreader/blob/2c253e5becbf22fd16960edca4f37eba2c03556a/files/enable-wifi.sh), [désactivation](https://github.com/lgeek/okreader/blob/2c253e5becbf22fd16960edca4f37eba2c03556a/files/disable-wifi.sh), [fetch.sh](https://github.com/lgeek/okreader/blob/2c253e5becbf22fd16960edca4f37eba2c03556a/fetch.sh) | `brcmfmac` et `sdio_wifi_pwr`, `wpa_supplicant`, `dhcpcd` ; firmware fourni pour les **révisions testées**, pas automatiquement pour E606C0. Le rootfs inclut un serveur SSH et des DNS externes codés en dur. | **INFO R5** : contrôler la puce et le firmware du véritable E606C0, Wi-Fi/SSH **à la demande** ; aucun réseau ou compte exposé par défaut. |
| **USB de stockage** — [rc.local](https://github.com/lgeek/okreader/blob/2c253e5becbf22fd16960edca4f37eba2c03556a/files/rc.local), [README](https://github.com/lgeek/okreader/blob/2c253e5becbf22fd16960edca4f37eba2c03556a/README.md) | `rc.local` tente automatiquement `modprobe g_file_storage file=$DATA_PART`, ciblant `/dev/mmcblk1p3` si présent, sinon `/dev/mmcblk0p3`. L'auteur signale le risque de corruption par écritures simultanées lecteur/hôte. | **ÉCARTER l'export USB automatique** : ne pas exposer P3 en masse-stockage monté/actif ; éventuel transfert contrôlé plus tard. Préserver aussi la voie Calibre → P3 → KOReader. |
| **Application de lecture** — [okreader.sh](https://github.com/lgeek/okreader/blob/2c253e5becbf22fd16960edca4f37eba2c03556a/files/okreader.sh), [build_rootfs.sh](https://github.com/lgeek/okreader/blob/2c253e5becbf22fd16960edca4f37eba2c03556a/build_rootfs.sh) | Lance KOReader/LuaJIT dans une boucle infinie, sans temporisation après sortie ; empaquette `koreader_2018.06-1_armhf.deb`. | **INSPIRATION UNIQUEMENT** : KOReader moderne reste notre cible, lancé par l'init PMKB avec stratégie de redémarrage bornée et coût CPU/RAM mesuré. **OKReader est un OS, pas un paquet du Store `*.pmkb`.** |
| **Licences** — [LICENSE](https://github.com/lgeek/okreader/blob/2c253e5becbf22fd16960edca4f37eba2c03556a/LICENSE), [.gitmodules](https://github.com/lgeek/okreader/blob/2c253e5becbf22fd16960edca4f37eba2c03556a/.gitmodules) | Licence permissive de type BSD pour le dépôt d'orchestration ; sous-modules, noyau Linux, `kobo_hwconfig` et firmware ont leurs droits propres. | **INFO** : garder les attributions et revoir la licence de **chaque** composant avant incorporation ; aucun droit de copier des blobs EPD/Wi-Fi déduit de la licence racine. |

**Différence de géométrie décisive :** les **15 Mio** du README OKReader sont un constat sur ses supports de référence et une exigence de sa procédure ; **ils ne décrivent pas la zone PRE-P1 mesurée de notre microSD**. Notre P1 commence au secteur `19456` (9 961 472 octets) ; P2, HWCONFIG et waveform restent des données protégées. Les instructions d'OKReader qui **suppriment P2, repartitionnent P1 et écrivent U-Boot/uImage sur le périphérique brut sont explicitement rejetées** pour notre FIRST BOOT scellé.

**Décisions et suite courte :**

1. **RETENIR** OKReader comme preuve historique de conception « Linux + KOReader sans Nickel » sur d'autres appareils et comme comparateur des choix d'initialisation, stockage, USB, Wi-Fi et gestion mémoire ; **aucun code intégré**.
2. **COMPARER sous R1** uniquement les éléments U-Boot/EPDC/MMC spécifiques à `dragon` et le comportement `kobo_hwconfig` au HWCONFIG E606C0 déjà décodé ; utiliser le dossier [R1/R3](kernel-community-audit-2026-10-24-fr.md) et la [qualification PRE-P1 de R2](https://github.com/fr4nck/PimpMyKobo-AuraHD/blob/feat/pmkb-powerlab-kernel-v0/docs/emulation-e606c0-r2-fr.md), sans lancer de script d'installation historique.
3. **QUALIFIER sous R5** un éventuel mode USB/Calibre et le Wi-Fi facultatif, avec accès exclusif aux données, politique de services à la demande et mesure de consommation, **après** FIRST BOOT.
4. **NE PAS FAIRE** : installer Debian Wheezy, importer le paquet KOReader 2018, modifier U-Boot/P2/P3, ou déduire un test Aura HD des réussites sur Touch, Mini, Aura ou Glo.

**Bilan documentaire M01 :** 13 fichiers source ciblés lus, décisions explicites ci-dessus ; **0 code/binaire externe ajouté, 0 téléchargement, 0 écriture sur carte, 0 test matériel, 0 PASS matériel revendiqué**. L'audit reste **statique** et ne modifie ni l'image FIRST BOOT, ni la HAL PMKB, ni la future architecture du Store.

### Exploitation R1/R3 — 24 octobre 2026

La première livraison de développement issue de ce corpus est documentée dans
[l'audit noyau/ZForce et sa matrice de décisions](kernel-community-audit-2026-10-24-fr.md).
Les révisions complètes et les blobs des **36 fichiers comparés** y sont conservés.
Ce complément ne remplace ni R0–R10, ni les qualifications historiques.

| Source / priorité | Composants effectivement comparés | Licence vérifiée / compatibilité | Utilisation et qualification |
| --- | --- | --- | --- |
| [pazos/linux-2.6.35.3-kobo](https://github.com/pazos/linux-2.6.35.3-kobo/tree/1f43a4a01a727a9b440f2e8830b67734b6373a10) — P0 | ZForce, EPDC/fake S1D/header, NTX/frontlight, MSP430, PM, MMC, USB | COPYING GPLv2 ; ZForce GPLv2, sources Freescale GPLv2+, header MXCFB LGPLv2.1+ ; support source HD identifié, binaire réel non identifié à cet arbre | RETENIR comme comparateur ; pas de nouveau noyau. Défauts de validation des trames à traiter séparément. |
| [lgeek/linux-okreader](https://github.com/lgeek/linux-okreader/tree/2a4689f1c0d2608e555bd0b12c8da89ca4a98724) — P0 | Les mêmes neuf fichiers | Même cadre de licences ; ZForce fonctionnellement identique à pazos ; comportement HD non qualifié | Aucun gain tactile de ce fichier ; EPDC/MMC/NTX à tester par patch isolé. |
| [giorgio130/multitouch](https://github.com/giorgio130/linux-2.6.35-kobo-multitouch/tree/b46a506b300e1eebc9bd1bf9c5369ae92fb7e200) — P0 | Les mêmes neuf fichiers, ZForce intégral | GPLv2 pour ZForce ; branche HD présente, aucun essai matériel PMKB | ÉCARTER l'import direct : ID négatif possible, compteur incrémenté sur MOVE, tailles/reset/timeout incohérents. RETENIR l'idée du multi-contact borné ; aucun code repris. |
| [brunotl/kernel-kobo-mx50-ntx](https://github.com/brunotl/kernel-kobo-mx50-ntx/tree/884fec254ce71a11f7e71d2e88e751772ccd1bc3) — P1 | Les mêmes neuf fichiers | COPYING GPLv2 et notices individuelles ; branche résolution HD absente du ZForce examiné | ÉCARTER comme remplacement ZForce HD ; changements PMIC/alarme et suppression de gardes non repris. |
| [FBInk](https://github.com/NiLuJe/FBInk/tree/886f25f13368859ad8a899b88d04c26e19cda32e) — P0 | fbink.c : refresh Kobo legacy, attente, mode FULL/PARTIAL, marqueurs, no_refresh et régions minces ; LICENSE | SPDX GPL-3.0-or-later ; chemin NTX ancien étudié, écran réel UNQUALIFIED | RETENIR les contrats déjà proches de la HAL PMKB ; pas de bibliothèque copiée/liée, pas de changement graphique spéculatif. |
| [Kobo officiel Aura HD](https://github.com/kobolabs/Kobo-Reader/tree/7a762964e7fa71ad8e8df50dd1b6eee721a43217/hw/imx507-aurahd) — P0 | Métadonnées de l'archive et audit historique existant | Archive noyau 132 718 922 octets non téléchargée ; licences internes à vérifier avant reprise | Pas de nouvelle extraction revendiquée ; reprendre les preuves historiques sans les transformer en compilation/boot. |
| [Contrat input Linux v6.18](https://github.com/torvalds/linux/blob/v6.18/Documentation/input/event-codes.rst) — P0 | SYN_DROPPED, état evdev et BTN_TOOL_DOUBLETAP | Documentation primaire, aucune copie de code ; contrat userspace, pas qualification du BSP | Correction originale de la HAL pure ; snapshot EVIOCG* réel encore absent. |

**Livré :** [correctif natif 9514eff](https://github.com/fr4nck/PimpMyKobo-AuraHD/commit/9514effd3a1a00febb49882049fcc433428ecd6e)
sur la branche existante de la **PR #30, toujours draft**. Annule les gestes
signalés à deux doigts et rejette les trames après SYN_DROPPED ; attend un
relâchement propre avant le nouvel appui. **939 assertions / 28 groupes PASS,
0 FAIL**, JSON 1/1 et images 6/6 ; coûts hôte et limite LeakSanitizer consignés
dans le dossier. Aucun malloc, service ou dépendance ajouté.
Le pilote pazos/lgeek actuel ne rapporte pas le deuxième doigt : ce filtre
n'active pas le multitouch et ne peut détecter ce que le noyau ne signale pas.

**Suite R1/R3 :** valider tailles/IDs/lectures courtes sur la base officielle
exacte, puis seulement étudier un backport multitouch ; ensuite R2/QEMU.
Compilation ARM/noyau non exécutée, tactile/E-Ink/RAM/énergie Kobo UNQUALIFIED.
FIRST BOOT scellé et tous les artefacts protégés inchangés.

## B. Rendu E-Ink, interface native, clavier et applications

| Priorité | Source | Usages | Intérêt précis et vérifications requises |
| --- | --- | --- | --- |
| P1 | [Rain92/qt6-kobo-platform-plugin](https://github.com/Rain92/qt6-kobo-platform-plugin) — [audit du plugin et des 7 forks](rain92-qt6-kobo-forks-audit-2026-10-25-fr.md) | INFO / INSPIRATION / CANDIDAT R1-R5 | **Qt QPA pour Qt 6 et 5.15**, actualisé **17/10/2026**, avec FBInk, entrée tactile **Aura HD / protocole legacy**, détection des périphériques par capacité, rafraîchissement EPDC ciblé, tramage ordonné **8×8 → 16 gris** et chemin **ARM NEON**. Les **7 forks ont été comparés** : 4 divergents dont Quill-OS, Aryetis, Szybet et Aryetis-Volt ; 3 en retard. **Priorité à l'étude d'algorithmes/contrats pour PMKB-UI natif**, sans ajouter Qt6 au socle ni reprendre les scripts Wi-Fi hérités. Un runtime Qt facultatif pour le Store exige d'abord mesures RAM/CPU, ABI et GPLv3 ; aucune validation physique E606C0. |
| P0 | [NiLuJe/FBInk](https://github.com/NiLuJe/FBInk) — [audit des 31 forks et des particularités Aura HD](fbink-forks-audit-2026-10-25-fr.md) | INFO / INSPIRATION / CANDIDAT | Couche C framebuffer/EPDC **déjà étudiée dans R1/R3** à la révision `886f25f` (août 2026). **31 forks publics analysés** : 26 en retard, 3 divergents (outillage), 1 avance CI, 1 identique ; **aucun correctif Aura HD neuf démontré** sur `master`. Le code canonique documente **Dragon / Mark 4 / 265 ppp**, le profil tactile non-MT historique et la rotation `NTX_ROTA_ALL_INVERTED` (4 remappages à qualifier). Priorité au cœur NiLuJe pour la HAL frugale, aux tests `fbink_input_scan` et rectangles EPDC, sans importer de code GPLv3+ ni alourdir PMKB-UI. |
| P2 | [marek-g/kobo-service](https://github.com/marek-g/kobo-service) — [audit M03](kobo-service-android-audit-2026-10-25-fr.md) | INFO / INSPIRATION | **Panneau Android 2.3/API 10**, pas un service Linux : rotation tactile via `EV_LED/LED_CAPSL` sur `/dev/input/event2`, 4 profils de rafraîchissement e-ink, ouverture de l'interface Android du stockage USB. Lié au noyau `marek-g/kobo-kernel-2.6.35.3-android`, **pas à notre noyau PMKB**. JNI `armeabi` binaire sans source retrouvé ; licences non établies. Retenir des idées de réglages PMKB-UI natifs sans importer APK, Android, JNI ou gadget USB automatique. |
| P1 | [redphx/kobo-tweaks](https://github.com/redphx/kobo-tweaks) | INFO / INSPIRATION / CANDIDAT PARTIEL | Widgets configurables du lecteur (heure, batterie, livre, chapitre, progression), marges et hauteurs des barres, styles clair/sombre et signets personnalisables via `settings.ini`. **Code vérifié** : `src/widgets/battery_widget.h` saute les mises à jour d'affichage quand l'état ne change pas ; `src/widgets/clock_widget.h` utilise une cadence espacée et suspend son timer quand le widget est caché ; `src/settings/settings.cc` valide les bornes. **Dépend de NickelHook + Qt5Widgets : incompatible directement avec PMKB sans Nickel.** Licence principale **MIT**, licences des dépendances et des ressources à vérifier. Inspirez-en la barre système et les applets PMKB-UI, sans installer `KoboRoot.tgz` ni copier les hooks Nickel. |
| P1 | [pazos/kobo-clock](https://github.com/pazos/kobo-clock) | INSPIRATION / CANDIDAT | Application native C/SDL 1.2 pour Aura HD ; boucle d'événements, affichage, fontes et coûts mémoire. Inspirer nos applets horloge/calculatrice, pas ajouter SDL par défaut. |
| P1 | [koreader/koxtoolchain](https://github.com/koreader/koxtoolchain) | INFO / CANDIDAT | Chaînes de compilation croisée adaptées aux Kobo anciennes ; vérifier libc/ARM hard-float, taille binaire et reproductibilité avant de standardiser les builds de PMKB-UI. |
| P1 | [olup/kobowriter](https://github.com/olup/kobowriter) | INSPIRATION / CANDIDAT | Éditeur de texte léger en Go et FBInk, saisie AZERTY via clavier USB et USB-OTG. Test déclaré sur **Glo HD seulement** : idées pour Mes Notes et raccourcis ; dépendance OTG/alimentation à valider sur E606C0. |
| P1 | [llandsmeer/inkvt](https://github.com/llandsmeer/inkvt) | INSPIRATION / CANDIDAT | Terminal VT100 E-Ink fondé sur FBInk et libvterm ; saisie clavier virtuel expérimentale. Référence pour terminal PMKB, **pas d'activation automatique d'un serveur HTTP de saisie en clair**. Licence GPLv3+. |
| P1 | [Nayeem170/kobo-core](https://github.com/Nayeem170/kobo-core) | INFO / INSPIRATION | SDK Rust d'abstractions écran, tactile, énergie, lumière et rendu ; liste Aura HD/dragon. **Support déclaré dans le README ≠ test du SDK sur notre noyau 2.6.35.3** ; mesurer les dépendances avant d'envisager une réutilisation. |
| P2 | [Rain92/qt5-kobo-platform-plugin](https://github.com/Rain92/qt5-kobo-platform-plugin) | INFO / INSPIRATION | Piste Qt/QPA E-Ink ; étudier le rendu sans Nickel, mais éviter d'imposer Qt et sa consommation au système minimal. |
| P2 | [baskerville/plato](https://github.com/baskerville/plato) | INSPIRATION | Lecteur alternatif et ergonomie E-Ink ; benchmark d'interface seulement, puisque KOReader est le lecteur retenu. |

## C. Réseau, maintenance et catalogue d'idées

| Priorité | Source | Usages | Intérêt précis et vérifications requises |
| --- | --- | --- | --- |
| P1 | [pazos/kobo-minimal-tools](https://github.com/pazos/kobo-minimal-tools) | INFO / CANDIDAT | Recettes minimales Dropbear/fmon ; examiner le binaire SSH, sa configuration, ses dépendances et les droits, **sans importer le mécanisme d'installation KoboRoot.tgz/Nickel**. |
| P1 | [boringrgb/kobo-aura-remote](https://github.com/boringrgb/kobo-aura-remote) | INFO / INSPIRATION | SSH/FTP/Telnet via une mise à jour Kobo Aura, firmware 3.15.0. **Mot de passe root fixe dans le README : ne jamais reprendre les identifiants ou exposer automatiquement les services**. |
| P2 | [shermp/kobo-rclone](https://github.com/shermp/kobo-rclone) | INSPIRATION | Synchronisation de fichiers et métadonnées Calibre/SFTP. La logique Nickel/SQLite et l'usage de rclone ne sont pas directement adaptés ; ne retenir qu'une synchronisation optionnelle chargée à la demande. |
| P2 | [RiccardoSilva42/Kobo-Hacks-Comp](https://github.com/RiccardoSilva42/Kobo-Hacks-Comp) | INFO / INSPIRATION | Catalogue externe à consulter pour nouvelles applications, réglages et pratiques de la communauté ; la plupart des méthodes visent Nickel. |
| P2 | [skinkie/kobomail](https://github.com/skinkie/kobomail) | INFO | Projet annonçant un client courriel pour **Aura HD**, mais **dernier commit vérifié : simple README, pas d'implémentation**. Archiver l'idée PDA, aucune intégration possible en l'état. |
| P2 | [ProGTX/Kobo-Aura-HD-Clean-Articles](https://github.com/ProGTX/Kobo-Aura-HD-Clean-Articles) | INFO | Outil C++ de nettoyage d'anciens articles Pocket dans `KoboReader.sqlite` de Nickel. **Hors périmètre runtime sans Nickel** ; renseigne seulement les formats historiques et la migration de données. |
| P2 | [NiLuJe/kfmon](https://github.com/NiLuJe/kfmon), [pgaskin/NickelMenu](https://github.com/pgaskin/NickelMenu), [baskerville/fmon](https://github.com/baskerville/fmon) | INSPIRATION | Lancement d'applications, anti-double-instance, gestion d'événements. **Ne pas intégrer les hooks, les bases de données ou les déclencheurs Nickel** ; PMKB possède son launcher indépendant. |
| P2 | [XCSoar/XCSoar](https://github.com/XCSoar/XCSoar) | INFO | Piste historique USB-OTG et connectique de clavier/GPS sur Kobo ; déterminer la variante matérielle réellement couverte avant d'évoquer un clavier externe Aura HD. |

### Homonymes « Kobo » sans rapport avec la liseuse

- **ÉCARTÉ — [ElliottMess/koboAPI](https://github.com/ElliottMess/koboAPI)** (consultation du 25 octobre 2026, `main` : `ec6b6ef90c8ed1343d42e5e0be655668c617dd14`). Malgré son nom, c'est un paquet **R** `koboAPI` v1.0.1, licence **GPL-3**, consacré aux API de **KoBoToolbox** (questionnaires humanitaires), et non aux liseuses Kobo. `DESCRIPTION`, `R/kobo_api.R`, `R/get_form.R`, `R/get_data.R` et `NAMESPACE` relus : authentification HTTP, extraction de formulaires XLSForm et de réponses ; aucune couche EPDC, Linux Kobo, KOReader, Nickel ou PMKB. **Aucune intégration au Store ou au système** ; simple faux ami archivé pour éviter une nouvelle analyse. Dernier commit observé : 9 mai 2022. Aucun code téléchargé ni exécuté.

## D. Dictionnaires, bibliothèque et ressources éditoriales

| Priorité | Source | Usages | Intérêt précis et vérifications requises |
| --- | --- | --- | --- |
| P1 | [Oniricorpe — Kobo hacks & mods](https://oniricorpe.eu/log/tech/kobo-hacks-mods/) | INFO / INSPIRATION | Panorama francophone daté du **8 octobre 2022**, mis à jour le **27 août 2025** : dictionnaires, polices, KOReader/Plato, configuration, Calibre, synchronisation et pratiques communautaires. **Majoritairement Nickel** : retenir les références documentaires, pas ses instructions d'installation dans PMKB sans Nickel. |
| P1 | [reader-dict/monolingual](https://github.com/reader-dict/monolingual) / [reader.dict](https://www.reader-dict.com/) | INFO / CANDIDAT | Dictionnaires issus de ressources libres ; distinguer **format Kobo natif destiné à Nickel** et **format StarDict utilisable par KOReader**. Mesurer taille, mémoire, temps d'indexation et vérifier les licences des données avant toute distribution PMKB. Ne pas embarquer de gros dictionnaires dans P1 par défaut. |
| P2 | [shermp/Kobo-UNCaGED](https://github.com/shermp/Kobo-UNCaGED) | INFO / INSPIRATION | Client **Calibre sans fil**, fonctions envoi/réception, séries, couvertures et métadonnées ; protocole et interface intéressants pour PMKB. L'application actuelle exige **Nickel, NickelMenu, NickelDBus**, et annonce **AGPL-3.0** : pas de réutilisation directe dans notre système sans Nickel. |
| P2 | [NotSimone/Kobo-Metadata](https://github.com/NotSimone/Kobo-Metadata) | INFO / INSPIRATION | Plugin **Calibre sur PC** récupérant titres, auteurs, résumés, séries et couvertures ; une piste de flux de métadonnées, **pas une application Kobo native**. Accès à des services tiers et leurs conditions à vérifier. |
| P2 | [Z-Library — accès FR communiqué](https://fr.z-library.sk/) | INFO / RÉFÉRENCE À VÉRIFIER | Lien externe transmis par l'utilisateur (24 octobre 2026), **non validé comme domaine officiel ni comme source autorisée**. La plateforme Z-Library a fait l'objet de décisions de blocage pour atteintes au droit d'auteur en France (tribunal judiciaire de Paris, 12 septembre 2024) ; le domaine communiqué fait également l'objet de signalements de sécurité tiers. **Aucun téléchargement automatisé, aucune indexation du catalogue dans le Store PMKB, aucune redistribution de contenus sans droits vérifiés.** À conserver comme référence documentaire uniquement, avec statut juridique et technique non qualifié. |

### Compatibilité des dictionnaires et des livres

Le guide Oniricorpe distingue les fichiers de dictionnaires destinés à **Nickel**
des fichiers **StarDict** destinés à **KOReader/Plato**. Notre lecteur cible
KOReader : ne pas demander la création de `.kobo/custom-dict` comme prérequis
du FIRST BOOT. Les dictionnaires volumineux doivent rester des ressources
facultatives de bibliothèque ou de P3, jamais un prérequis à la lecture.

Les plateformes documentées mais non vérifiées sur le plan du droit d'auteur ou de la sécurité restent **hors du flux d'acquisition et de distribution PMKB** ; ce registre ne constitue pas une recommandation de téléchargement.

Même principe pour Calibre : **connexion sans fil en option**, après qualification
du Wi-Fi et du modèle de permissions PMKB, sans NickelDBus, sans activation réseau
au démarrage et sans incorporation implicite de code AGPL.

## E. Retours d'expérience Aura HD et performances historiques

| Priorité | Source | Usages | Intérêt précis et vérifications requises |
| --- | --- | --- | --- |
| P1 | [pled.fr — Downgrade de ma liseuse Kobo Aura HD (13 juin 2025)](https://pled.fr/post/2025/06/downgrade-de-ma-liseuse-kobo-aura-hd/) | INFO / INSPIRATION | Retour utilisateur sur **notre modèle Aura HD** : firmware 4.38 perçu lent au changement de page, 3.17 instable avec certains livres, puis 4.17.13651 perçu fluide. **Témoignage, pas benchmark, pas preuve d'un problème noyau** ; ne pas reproduire la rétrogradation sur FIRST BOOT scellé. Définit des axes de mesure (latence/page, stabilité, compatibilité bibliothèque). |
| P2 | [pled.fr — Kobo Aura HD : installation de Plato (14 novembre 2024)](https://pled.fr/post/2024/11/kobo-aura-hd-installation-de-plato/) | INFO / INSPIRATION | Parcours lecteur alternatif, gestes et zones tactiles personnalisables, veille et ergonomie ; Plato lancé à côté du système Kobo dans ce témoignage. Inspiration pour zones du launcher et PMKB-UI ; **ne démontre pas** un lancement autonome sans Nickel. |

**Lecture critique :** ces récits n'autorisent ni téléchargement de firmware
historique, ni mise à jour de PRE-P1, ni manipulation de la carte de test.
Le bénéfice perçu après rétrogradation peut tenir au logiciel, au contenu
de la bibliothèque et aux réglages ; ne pas l'attribuer au noyau sans
mesures comparables.

## F. Forums techniques et autres pistes historiques

| Priorité | Source | Usages | Intérêt précis et vérifications requises |
| --- | --- | --- | --- |
| P1 | [MobileRead — List of Tweaks / Hacks / Mods (fil 217160)](https://www.mobileread.com/forums/showthread.php?t=217160) | INFO / INSPIRATION / INDEX | **Index communautaire Kobo lancé en juillet 2013 ; premier message édité au moins jusqu'au 17 avril 2022.** Recense anciens KoboLauncher (Notepad, calculatrice, jeux, USB network, Dropbear SSH/SFTP), KOReader, outils de compilation, modes d'écran, sauvegardes, dictionnaires, Calibre et retours microSD. **Historique multi-modèles, souvent dépendant de Nickel et de versions firmware anciennes ; aucun statut de compatibilité Aura HD / PMKB actuel.** Explorer les fils originaux plutôt que considérer l'index comme une procédure testée. |
| P1 | [MobileRead — KoboLauncher et applications natives (fil 201632)](https://www.mobileread.com/forums/showthread.php?t=201632) | INFO / INSPIRATION | Exemple précoce de lanceur configurable de programmes C++/Qt, incluant Notepad, calculatrice et jeux et accès USB-network/SSH/SFTP. Comparer uniquement les contrats UX, processus et les besoins minimaux avec PMKB Launcher/PMKB-UI ; **pas de dépendance Nickel ou ancien Qt à importer**. |
| P1 | [dbeinder/kobo-nightmode](https://github.com/dbeinder/kobo-nightmode) | INFO / CANDIDAT DE RECHERCHE | Inversion d'écran, gestion du rafraîchissement et **commande par appui long sur le bouton d'éclairage** ; le README cite explicitement l'Aura HD. Implémentation historique par interception `ioctl()` / `mmap()` avec `LD_PRELOAD` sur Nickel et modification de `rcS` : **ne pas intégrer ce mécanisme**. Étudier surtout le comportement EPDC, l'inversion, le ghosting et les seuils d'appui. |
| P2 | [ah-/koboplugins](https://github.com/ah-/koboplugins) | INFO / INSPIRATION | **Ancienne génération « Kobo Tweaks » (2013), distincte de [redphx/kobo-tweaks](https://github.com/redphx/kobo-tweaks)**. Code de plugins Qt/QtScript et `kobotweaks.ini` ; dépendant de l'ancien environnement Nickel. Piste historique de configuration d'applications, pas d'intégration directe. |
| P2 | [softapalvelin/kobo-grive-sync](https://github.com/softapalvelin/kobo-grive-sync) | INFO | Ancienne synchronisation Google Drive sur Kobo Touch. **README explicitement incompatible avec firmware 2.6.1 et suivants** : piste obsolète ; ne pas réutiliser les scripts, les anciens liens de téléchargement, ni le modèle d'authentification. |

### Constats techniques à convertir en tests PMKB

- **microSD : petits blocs avant la classe annoncée.** Le fil cite des mesures
  et essais d'utilisateurs montrant qu'une carte plus rapide en séquentiel
  peut être beaucoup plus lente sur les accès aléatoires. **Ce sont des
  anecdotes et mesures sur des cartes/lecteurs différents, non un résultat
  sur notre E606C0.** Construire un protocole de mesures lecture aléatoire
  de petits blocs, débit séquentiel, démarrage à froid et ouverture des livres
  pour la carte PMKB de test. N'effectuer **aucun benchmark destructif ou
  écriture de charge sur l'originale** ; les tests d'écriture nécessitent une
  cible sacrificielle choisie et une validation explicite.
- **EPDC : latence / ghosting / fréquence de nettoyage.** Comparer rafraîchis-
  sements partiels et complets, inversion clair/sombre, lisibilité après des
  pages répétées et énergie. Les anciennes instructions `numPartialUpdatePageTurns`
  visent Nickel : elles ne constituent pas un réglage PMKB ni une preuve de gain.
- **Boot sans Nickel : bilan des composants requis.** Les essais KOReader
  historiques signalaient alors des manques de veille et de gestion de lumière.
  Ils ne décrivent **pas** l'état de KOReader v2026.07.1 ni de notre P1 scellée :
  mesurer ces fonctions sur le FIRST BOOT, indépendamment de l'ancien forum.
- **Launcher et services :** comparer un lancement d'application unique,
  sortie propre, clavier, menus jeux/Notes/calculatrice et SSH/SFTP facultatifs.
  Ne pas réutiliser les scripts `KoboRoot.tgz`, hooks d'installation Nickel
  ou commandes de modification de `upgrade-wifi.sh` / firmware citées dans ce
  fil ; elles ne respectent pas notre contrat de sauvegarde immuable.

## G. Veille MobileRead — communauté Kobo et systèmes alternatifs (24 octobre 2026)

| Priorité | Source | Usages | Intérêt précis et vérifications requises |
| --- | --- | --- | --- |
| P1 | [MobileRead — Kobo Reader (forum 223)](https://www.mobileread.com/forums/forumdisplay.php?f=223) | INFO / VEILLE | **Forum général de la communauté Kobo** : firmwares, incidents et retours d'expérience, microSD, Calibre, dictionnaires, lecteurs alternatifs. Source vivante : chaque observation doit être remontée à son fil, à une date et au modèle exact ; **aucune affirmation communautaire ne qualifie notre matériel**. |
| **P0** | [MobileRead — Kobo Developer's Corner (forum 247)](https://www.mobileread.com/forums/forumdisplay.php?f=247) | INFO / VEILLE / SOURCES | **Sous-forum spécialisé en développement et modifications matérielles/logicielles Kobo**. Index vivant des fils noyau/USB, microSD, init, émulation, lecteurs alternatifs. À consulter avant de redévelopper une fonction ; filtrer les sujets **Aura HD / dragon / E606C0 / i.MX507**. |
| **P0** | [MobileRead — kos, un système minimal pour KOReader (fil 375221)](https://www.mobileread.com/forums/showthread.php?t=375221) | INFO / INSPIRATION / CANDIDAT D'ÉTUDE | Présenté en **septembre 2026** : système autonome remplaçant l'OS Kobo et lançant directement KOReader. **Support revendiqué : Clara Colour uniquement** ; aucun support Aura HD ni compatibilité i.MX507 démontrés. Étudier sa séparation kernel/rootfs, sa fabrication, ses contrôles d'intégrité et récupération. **Ne jamais appliquer son installateur : les instructions modifient des partitions critiques**, et sa chaîne de boot est différente. |
| P1 | [koreader-os — rootfs, builder, installer](https://github.com/koreader-os) | INFO / CANDIDAT D'ÉTUDE | Organisation source de `kos`, dépôts [rootfs](https://github.com/koreader-os/rootfs), [builder](https://github.com/koreader-os/builder) et [installer](https://github.com/koreader-os/installer) accessibles ; le README d'`installer` renvoie au fil MobileRead. Comparer les scripts/outils de fabrication d'un OS compact, sans exécuter de script tiers ni télécharger de firmware. **Pas d'intégration directe sur E606C0**. |
| P1 | [MobileRead — InkBox / Quill OS (fil 337972)](https://www.mobileread.com/forums/showthread.php?t=337972) — [Quill-OS](https://github.com/Quill-OS) | INFO / INSPIRATION | Remplacement de l'environnement Kobo par une pile libre fondée sur **Alpine / Buildroot et Qt5**, avec diagnostic/recovery, applications, Wi-Fi, veille et mises à jour. Les modèles listés dans le fil **n'incluent pas l'Aura HD**. **Plus lourd qu'une solution minimaliste PMKB** ; comparer les contrats d'initialisation, diagnostic et rollback, pas copier ses images ou imposer Qt. |
| P2 | [notmarek/KoboTolinoFindings](https://github.com/notmarek/KoboTolinoFindings) — [audit PMKB](kobo-tolino-findings-audit-2026-10-25-fr.md) | INFO / INSPIRATION R10 | Rétro-ingénierie **Kobo Libra Colour / Clara BW & Colour / Tolino, MT8512** : OTA **stage1 rootfs → stage2 recovery**, formats `update.tar`, hash SHA-256, récupération et script de découverte de mises à jour officielles (codes **690/691**). **Aucun pilote ni amorçage i.MX507/Aura HD applicable.** Les mises à jour de type recovery **remplacent recoveryfs**, interdites pour notre P2 protégée ; ne pas exécuter `update.sh` (inclut `git push`) ni importer firmwares, clés ou binaires. Dossier [R10](kobo-tolino-findings-audit-2026-10-25-fr.md) : modèle conceptuel seulement, priorité FIRST BOOT inchangée. |
| P1 | [Quill-OS/inkbox-os-init](https://github.com/Quill-OS/inkbox-os-init) — [Quill-OS/imgtool](https://github.com/Quill-OS/imgtool) | INFO / CANDIDAT D'ÉTUDE | Init C compilé statiquement selon le README ; outil de génération d'image reproductible, nécessitant notamment Docker, `nbd` et des droits élevés. Sources d'inspiration pour l'init frugal, la signature/contrôle d'image et la reproductibilité, **sans reprendre les commandes privilégiées ni les partitions de ces autres Kobo**. |
| P1 | [MobileRead — Adding alternative readers (fil 226456)](https://www.mobileread.com/forums/showthread.php?t=226456) | INFO / INSPIRATION | Historique KOReader, Kobo Start Menu, fmon et autres lecteurs ; les instructions classiques passent par les images traitées par Nickel et `KoboRoot.tgz`. Identifier les fonctions que notre launcher doit gérer **sans ces dépendances**. |
| P1 | [MobileRead — Terminal emulator for Kobo (fil 371768)](https://www.mobileread.com/forums/showthread.php?t=371768) — [OGKevin/cadmus](https://github.com/OGKevin/cadmus) | INFO / INSPIRATION | Discussions de janvier 2026 sur terminal **local avec clavier à l'écran**, InkVT et Cadmus (fork de Plato). Des démos de terminal y sont mentionnées, **sans preuve d'une livraison sur Aura HD**. À relier au clavier commun PMKB et à un terminal natif hors réseau. |
| P1 | [MobileRead — Index of Custom Dictionaries (fil 232883)](https://www.mobileread.com/forums/showthread.php?t=232883) — [pettarin/penelope](https://github.com/pettarin/penelope) | INFO / INSPIRATION | Index multilingue et convertisseur de dictionnaires au **format Kobo**. Vérifier **formats attendus de KOReader (dont StarDict)**, langue, licences par dictionnaire et absence de paquet volumineux dans P1 ; ne pas présumer de la compatibilité directe avec notre lecteur. |
| P2 | [MobileRead — Recovery après mise à jour ratée (fil 369653)](https://www.mobileread.com/forums/showthread.php?t=369653) | INFO / CONTRE-EXEMPLE | Procédure d'août 2025 écrite pour **Aura Edition 2 N236**, avec réinitialisation usine ; **N236 ≠ Aura HD N204**, et un reset peut réécrire nos partitions. Documenter comme anti-pattern pour notre chemin « donneuse immuable → nouvelle microSD », **jamais comme recette à appliquer**. |
| P1 | [MobileRead — Kobalt, lecteur alternatif (fil 375691)](https://www.mobileread.com/forums/showthread.php?t=375691) — [nicoverbruggen/kobalt](https://github.com/nicoverbruggen/kobalt) | INFO / INSPIRATION / CANDIDAT LIMITÉ | **Premier billet : 11 octobre 2026 ; sources GitHub et README relus.** Lecteur EPUB alternatif, **CREngine dérivé de KOReader + interface Qt**, UX simplifiée et priorité à la vitesse. La version Kobo s'intègre à **Nickel**, utilise ses données de progression/dictionnaires, et ses packages ciblent les firmwares **4.38–4.46 (Qt5)** et **5.x/6.x (Qt6)** ; **pas une application autonome prouvée sur notre Aura HD / Linux 2.6.35.3**. Code propre sous **MIT**, correctifs CREngine sous **GPLv2+**, distribution combinée déclarée **AGPLv3** : vérifier intégralement licences, ABI et tailles. Inspiration pour la bibliothèque et l'ergonomie de KOReader, sans installer de paquet Kobo. |

### Point d'attention : projets très proches, matériel différent

`kos` constitue une **preuve de concept intéressante** de l'architecture
« Linux minimal → KOReader » sur **Clara Colour**, et Quill OS documente
un OS alternatif complet sur d'autres Kobo. Cela **ne démontre pas**
un FIRST BOOT PMKB sur E606C0 ni la disponibilité de pilotes EPDC/ZForce
équivalents. Les méthodes de récupération et mises à jour peuvent être très
dépendantes du bootloader : **aucune commande d'installateur tiers ou de reset
usine n'est autorisée sur la carte originale ou notre P1 scellée**.

Réutiliser, si utile, des **idées et des contrats techniques** : init minimal,
fabrication de rootfs, mesures RAM/binaire, vérification d'intégrité, diagnostic,
choix d'un système alternatif, reprise d'une application après veille,
rollback et bibliothèque de lecteurs. Pour chaque reprise effective de code :
diff ciblé, attribution, licence, compatibilité armv7/libc/noyau,
tests hôte, puis essais physiques séparément autorisés.

### Exploitation R2 — 25 octobre 2026

Dossier : [émulation E606C0 et qualification PRE-P1](https://github.com/fr4nck/PimpMyKobo-AuraHD/blob/feat/pmkb-powerlab-kernel-v0/docs/emulation-e606c0-r2-fr.md), publié sur la branche de la **PR #28, draft**, commit [6ac37a8](https://github.com/fr4nck/PimpMyKobo-AuraHD/commit/6ac37a8).

| Source / priorité | Éléments examinés | Licence | Décision |
| --- | --- | --- | --- |
| [katadelos/qemu](https://github.com/katadelos/qemu/tree/ed82906f2911db495ee3fc89fadbe8c2b1852741) `ed82906` — P0 | Carte Aura HD : RAM 0x70000000/512 Mio, exécution du **vrai U-Boot** via `-bios`, eSDHC3, zForce 0x50, MSP430 0x43 **version Kobo Mini 0xb83a par défaut**, MC13892 SPI3, TPS65185 0x68, EPDC à minutage waveform réduit, alarme RTC non modélisée | GPL-2.0-or-later | **RETENIR comme banc de boot** ; aucun résultat E-Ink, batterie ou veille réel. QEMU non construit (téléchargement à autoriser) |
| [katadelos/eink-emulator](https://github.com/katadelos/eink-emulator/tree/81ae873f57ea5a8aba71a00774118dc3ad8462e7) `81ae873` — P0 | Extraction et constructeur Kobo : offsets P1 19 456 / P2 543 745 identiques à PMKB ; le constructeur lance e2fsck, modifie `rcS` et `passwd` et exige `hindenburg` | **Aucune licence** : pas de reprise de code | **ÉCARTER son constructeur pour FIRST BOOT** : il modifierait ou refuserait P1 scellée |
| [pazos/linux-2.6.35.3-kobo](https://github.com/pazos/linux-2.6.35.3-kobo/tree/1f43a4a01a727a9b440f2e8830b67734b6373a10) — P0 | `MACHINE_START(MX50_RDP)` unique ; MC13892 enregistré sur SPI bus 3, CS 0 | GPLv2 | Corrige la matrice pilotes (« I²C » inexact) ; machine ID 2988 = inférence forte, non prouvée sur notre U-Boot |

**Livré :** `experimental/boot-region/boot_region.py`, analyseur pur en lecture seule de la PRE-P1. Il couvre la géométrie MBR, le HWCONFIG PCB 28, la chaîne IVT/plug-in et l'étendue d'U-Boot, les CRC et IH_LOAD/IH_EP du uImage, le zImage et le marqueur waveform. La remise U-Boot reste toujours UNQUALIFIED. Il produit aussi un plan de carte virtuelle **1 Gio** avec P1/P2 copiées à l'identique, et exige l'empreinte du FIRST BOOT scellé. **12/12 tests PASS**, fuzz de 3 000 régions sans exception, 16 mutants détectés, suite complète de 334 tests OK (15 SKIP). Coût : outil de poste, 0 octet sur la Kobo.

**SKIP :** boot émulé, fichiers privés. **Complément du même jour :** `virtual_card.py` assemble la carte 1 Gio sur fichiers ordinaires. PRE-P1 n'y change que sur les octets 490-493 ; les SHA-256 de P1 et P2 sont contrôlés avant et après copie ; P3 est une FAT32 « KOBOeReader » écrite en Python pur et relue par `blkid`/`file`. 11/11 tests, 16/16 mutants détectés. **Suite R2 :** exécuter les deux outils sur les fichiers privés, puis construire QEMU après autorisation.

## Feuille de route de recherche — tâches et critères de sortie

| Ordre | Recherche | Travail hors matériel | Sortie attendue / décision |
| --- | --- | --- | --- |
| **R0** | **FIRST BOOT prioritaire** | Conserver intégralement le candidat et ses SHA ; effectuer, si utile, des revues documentaires parallèles. | **FIRST BOOT physique reste UNQUALIFIED** jusqu'à observation réelle. Aucune recherche ne doit le bloquer. |
| **R1** | **Provenance et delta du noyau E606C0** | Comparer sources Kobo/Netronix, `pazos/linux-2.6.35.3-kobo` et `lgeek/linux-okreader` ; identifier .config, pilotes EPDC, ZForce, NTX/MSP430, stockage, USB et correctifs de sécurité réellement manquants. | Tableau fichier/commit/raison/licence/effet attendu ; 0 patch noyau non justifié ; conserver noyau de référence tant que l'alternative n'a pas gagné sa qualification. |
| **R2** | **Simulation de notre FIRST BOOT** | Examiner `katadelos/eink-emulator` et sa carte QEMU E606C0, comparaison géométrie/bootloader ; envisager une image virtuelle compacte PRE-P1 + P1 PMKB + P2 + P3 neuve. **25/10 : audit fait, analyseur PRE-P1 livré, puis assembleur de carte virtuelle 1 Gio (profil `virtual-qemu`, distinct du profil physique de la PR #7) livré et qualifié sur données synthétiques à taille réelle (PR #28, `f74fbc0`). Restent les mesures sur fichiers privés et le build QEMU.** | Contrôle d'identités et journal boot reproductible sur fichiers privés, sans téléchargement implicite ; résultats hôte ≠ qualification E-Ink physique. |
| **R3** | **Tactile et HAL graphique** | Diff du pilote ZForce multitouch `giorgio130` et intégration avec `pazos` ; audit FBInk rotations, framebuffer, waveform et rafraîchissement ; comparer à la HAL PMKB existante. | Décision argumentée **garder / adapter / écarter** par composant, coût RAM/binaire, ABI, droits et tests synthétiques, puis matériel autorisé séparément. |
| **R4** | **Applications PMKB natives** | Étudier C/SDL de `kobo-clock`, éditeur `KoboWriter`, terminal `InkVT`, SDK `kobo-core`. Réutiliser les idées compatibles avec **Notes, clavier commun, calculatrice, terminal, split 2 panneaux**. | Composants légers indépendants de Nickel, chargement à la demande, pas de gros runtime systématique ; aucune application externe présumée compatible. |
| **R5** | **Réseau et sécurité mesurée** | Examiner Dropbear, USB-OTG et sync facultative ; qualifier les CVE applicables au noyau 2.6.35.3, éventuels backports, permissions et services. | SSH à la demande, idéalement par clés ; éviter mot de passe root partagé, Telnet ouvert en permanence et dépendances gourmandes ; profil connecté examiné séparément. |
| **R6** | **Veille communautaire utile** | À chaque découverte : ajouter URL, cible, provenance, statut, licence à contrôler, hypothèse utile et prochaine action dans **ce registre**. | Aucune piste perdue et aucune adoption automatique ; revue par priorité et mesure du gain réel plutôt que collection de dépôts. |
| **R7** | **Dictionnaires et bibliothèque sans Nickel** | Examiner formats StarDict pour KOReader, licences/langues, tailles et indexation ; étudier les flux Calibre (`Kobo-UNCaGED` comme référence, pas composant installable). | Catalogues et métadonnées optionnels, import hors P1 système, consommation mesurée ; intégration dépendante de Nickel écartée. |
| **R8** | **Réactivité, stockage et initialisation sans Nickel** | Comparer en lecture seule les chemins de démarrage et les ajustements du lecteur ; métriques changement de page, double-appui tactile, veille, RAM et boot. Ajouter tests **lecture aléatoire petits blocs vs débit séquentiel microSD** et compromis rafraîchissements partiels/complets/ghosting inspirés du forum MobileRead ; privilégier des tests hôte et ne pas lancer d'écritures sans autorisation explicite. | Protocole de benchmark reproductible Aura HD, comparaison carte de test et paramètres E-Ink, avec contrôles PASS/FAIL et mesures ; aucune conclusion matérielle à partir d'un témoignage, aucune altération de la carte donneuse ni du FIRST BOOT. |
| **R9** | **Widgets graphiques frugaux** | Étudier `redphx/kobo-tweaks` : widgets d'heure/batterie/progression, configuration INI bornée, rafraîchissements déclenchés par changement d'état, arrêt du timer si masqué, densité des barres ; comparer avec le launcher et la HAL PMKB-UI. | Spécification de widgets **sans Nickel**, budget rafraîchissement/RAM, tests hôte de transitions et stabilité ; refuser l'intégration directe de NickelHook/Qt5Widgets. |
| **R10** | **Comparatif OS minimal sans Nickel et récupération** | Étudier `kos` (Clara Colour uniquement) et `Quill OS` (autres modèles) : composition du rootfs, taille binaire, budget RAM, init, modules noyau, intégrité/signature, mise à jour et rollback. Examiner aussi la couche lecture **Kobalt/CREngine** pour l'expérience utilisateur, en conservant KOReader comme cible PMKB. Comparer au candidat scellé PMKB sans installer ni modifier quoi que ce soit. Croiser `Kobo Developer's Corner` et les essais QEMU E606C0. | Tableau **PMKB / kos / Quill OS** : faisabilité et coût d'adaptation E606C0, licence et chaîne de confiance, méthode non destructive ; décision **retenir / adapter / écarter** étayée. FIRST BOOT physique reste prioritaire et `UNQUALIFIED`. |

### Règles de reprise de code et de qualification

1. **Ne jamais fusionner un arbre noyau tiers « en bloc ».** Diff limité et motivé, ABI E606C0 vérifiée, tests hôte avant tout test matériel et contrôle énergétique après boot.
2. **Vérifier les licences fichier par fichier** et conserver notices/attributions exigées. Le fait qu'un dépôt soit public ne donne pas un droit de copier sans condition ; étudier également les firmwares propriétaires.
3. **Ne pas confondre compatibilité de famille** (i.MX50, « Kobo », framebuffer) avec compatibilité de notre **E606C0 / ZForce v2 / frontlight SY7201 / MSP430**.
4. **Pas de téléchargement lourd, clone de noyau, build ou mise à jour du firmware sans accord adapté.** Cette inscription de références n'exécute aucun code externe.
5. **Ne pas modifier** PRE-P1, U-Boot, P1 scellée, P2, image originale 32 Go ou microSD de test 16 Go depuis une simple étape de recherche ; chaque écriture requiert une décision distincte.
6. **Distinguer les preuves** : sources relues, build PASS, tests simulés, puis tests matériels. Tout ce qui n'a pas été observé reste `UNQUALIFIED`.

## Liens de pilotage PMKB

- [Roadmap principale](ROADMAP.fr.md)
- [Jalon FIRST BOOT #1](pmkb-first-boot-1-fr.md) (selon la branche d'intégration)
- [Architecture utilisateur sans Nickel](offline-liberation-fr.md)
- [Documentation générale](README.md)

Ce document est l'**index canonique des références externes** pour les travaux futurs PMKB : préférer enrichir la même entrée et préciser le statut plutôt que disperser des liens dans les commentaires et conversations.
