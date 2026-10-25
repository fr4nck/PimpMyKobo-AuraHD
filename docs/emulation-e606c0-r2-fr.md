# PMKB — R2 : émulation E606C0 et qualification PRE-P1 (25 octobre 2026)

**Livraison : audit ciblé de l'émulateur QEMU E606C0, verdict sur son usage avec FIRST BOOT #1, et outil hors matériel de qualification de la zone PRE-P1.** Aucun boot émulé n'a été exécuté : QEMU n'est ni construit ni installé dans cet environnement. Aucune image, carte, P2, U-Boot ou noyau modifié.

## État vérifié avant développement

- `main` : `b1d953c9aae06646dcc4954263a02b840f5dd8a5`. L'audit des quatre noyaux et de ZForce du 24 octobre (lot A) y est déjà publié et n'est **pas** refait ici : [audit communautaire noyau](https://github.com/fr4nck/PimpMyKobo-AuraHD/blob/main/docs/kernel-community-audit-2026-10-24-fr.md).
- PR #28 (cette branche, brouillon) : `644a79e3bcf40a6d7fbd074c7f5f7ceabe7518e3` avant ce lot.
- PR #7 `integration/pmkb-first-boot-1` : `6b0506a085c3f19d818f71fbeebcd7c8da8c3abf`, non modifiée.
- FIRST BOOT #1 : `PMKB-FIRST-BOOT-1-0b00d858.img`, SHA-256 `7980fec15cb62ca3c2cabcb64cbbb683446fbf64070d75b45acf9a5e99e0f67c`. Le fichier est absent de la session : **aucune revérification d'empreinte revendiquée**. L'outil livré exige cette empreinte exacte.

## Sources lues (révisions figées, lecture ciblée sans blob ni build)

| Alias | Source | Révision | Fichiers lus |
| --- | --- | --- | --- |
| EE | [katadelos/eink-emulator](https://github.com/katadelos/eink-emulator/tree/81ae873f57ea5a8aba71a00774118dc3ad8462e7) | `81ae873f57ea5a8aba71a00774118dc3ad8462e7` | `docs/kobo-aura-hd.md`, `docs/firmware.md`, `scripts/carve-kobo.py`, `eink_emulator/images/kobo.py`, `kobo_sd.py`, `models.json` |
| EQ | [katadelos/qemu, branche eink-emulator](https://github.com/katadelos/qemu/tree/ed82906f2911db495ee3fc89fadbe8c2b1852741) | `ed82906f2911db495ee3fc89fadbe8c2b1852741` | `hw/arm/imx50-kobo-aura-hd.c`, `hw/i2c/zforce.c`, `hw/i2c/kobotouch_msp430.c`, `hw/display/imx50_epdc.c` (extraits) |
| P | [pazos/linux-2.6.35.3-kobo](https://github.com/pazos/linux-2.6.35.3-kobo/tree/1f43a4a01a727a9b440f2e8830b67734b6373a10) | `1f43a4a01a727a9b440f2e8830b67734b6373a10` (même révision que l'audit du 24/10) | `arch/arm/mach-mx5/mx50_rdp.c`, `mx50_rdp_pmic_mc13892.c` |

Les références de câblage citées par EE (`katadelos/linux-ereader` et `u-boot-ereader`, branche `kobolabs/imx507-aurahd`) **ne sont pas accessibles** en lecture anonyme : dépôts privés ou absents. Leurs affirmations restent de seconde main.

## Ce que l'émulateur modélise réellement

| Élément | Constat (source) | Statut pour PMKB |
| --- | --- | --- |
| Machine | `imx50-kobo-aura-hd`, 512 Mio obligatoires, RAM à `0x70000000` (EQ l.36-37, 310-313, 342) | Cohérent avec nos 512 Mio ; base RAM = modèle, pas mesure |
| Démarrage | `-bios` = U-Boot **extrait de la carte**. La ROM plug-in DDR est sautée et l'émulateur entre dans l'IVT SDRAM (EQ l.178-218). U-Boot lit ensuite lui-même HWCONFIG, uImage et waveform | Le vrai U-Boot s'exécute : bon banc pour observer machine ID/ATAG **dans l'émulateur** |
| Machine ID | `2988 /* MACH_TYPE_MX50_RDP */` utilisé **seulement** sans `-bios` (`arm_load_kernel`, EQ l.38, 348-358) | Corrobore l'inférence 2988 du BOOT CONTRACT ; pas une preuve sur notre U-Boot |
| Machine noyau | `MACHINE_START(MX50_RDP, …)` unique dans `mx50_rdp.c:3044` (P) | Un noyau historique sans DT n'accepte que ce numéro |
| Stockage | Carte interne sur eSDHC3, Wi-Fi BCM43362 SDIO sur eSDHC2 (EQ l.287-294, 345-346, EE doc) | Wi-Fi émulé ≠ module réel de notre exemplaire (UNQUALIFIED) |
| Tactile | zForce I²C0 0x50, 1080×1440, protocole « framé » Kobo (EQ l.267-273, `zforce.c`) | Réutilisable pour tester l'évdev PMKB-UI, pas le contrôleur réel |
| MSP430 | I²C2 0x43, version par défaut **`0xb83a` (Kobo Mini)** ; variante `0xe916` disponible mais non choisie pour l'Aura HD (EQ `kobotouch_msp430.c:25-26,248-249`) | Version MCU réelle E606C0 **inconnue** ; branche NEWMSP non exercée par défaut |
| PMIC | MC13892 sur **SPI3** (EQ l.278-283) ; P l'enregistre sur SPI bus 3 CS 0 (`mx50_rdp_pmic_mc13892.c:429-441`) | Corrige la matrice (« I²C » était inexact) ; présence physique non démontrée |
| E-Ink | EPDC « 16 LUT », minutage waveform **réduit**, rotation CCW, TPS65185 I²C1 0x68 (EQ `imx50_epdc.c:4-6`, l.257-265, 325) | Rafraîchissements et marqueurs testables ; ghosting, contraste, énergie **non reproduits** |
| Veille | Deep suspend ; alarme RTC de réveil **non modélisée** (EE doc) | Pas de qualification d'autonomie possible |

Géométrie : EE garde les offsets du MBR source (P1 au secteur 19 456, 524 289 secteurs ; P2 au secteur 543 745). Ce sont exactement les valeurs du [partitionnement PMKB](partition-layout-fr.md) : **concordance PASS sur sources**, pas sur notre fichier privé.

## Verdict : ne pas utiliser le constructeur d'image de l'émulateur avec FIRST BOOT #1

`kobo_sd.build()` (EE) prépare toujours la rootfs avant de l'écrire. Il lance `e2fsck -p`, supprime `/etc/udev.tgz`, ajoute un service réseau et **réécrit `rcS` et `/etc/passwd`** (mot de passe root vidé). Il refuse un `rcS` sans la ligne exacte `/usr/local/Kobo/hindenburg &`. Il exige donc la chaîne Nickel. Conséquences :

1. sur notre P1 PMKB sans Nickel, la construction **échoue** (`kobo.prepare_network` : « Unrecognized Kobo rcS: expected one Hindenburg launch ») ;
2. même contournée, elle **modifierait P1** : le SHA-256 scellé ne correspondrait plus, et l'essai ne qualifierait plus FIRST BOOT #1.

**Décision : RETENIR l'émulateur QEMU (EQ) comme banc de boot ; ÉCARTER son constructeur d'image (EE) pour PMKB ; ne pas modifier notre installateur pour le satisfaire.** Une carte virtuelle PMKB doit copier P1 et P2 octet pour octet et ne changer que la taille P3 du MBR. P3 y est un volume FAT32 neuf : FIRST BOOT vérifie le montage de P3 (`pmkb-check-onboard`). Il faut ensuite lancer QEMU en mode snapshot.

## Livrable : `experimental/boot-region/boot_region.py`

Outil Python sans dépendance, implémenté indépendamment à partir des formats publics : MBR, IVT i.MX, en-tête U-Boot `uImage`, en-tête zImage. Il **ne reprend aucun code** de EE, dont le dépôt ne porte aucune licence, ni de EQ. Documentation : [README](../experimental/boot-region/README.md).

- **Gates BOOT CONTRACT désormais mesurables en lecture seule sur la sauvegarde privée :** IH_LOAD, IH_EP, IH_SIZE et CRC du uImage ; adresse de chargement et point d'entrée d'U-Boot, preuve indirecte de la base DRAM qu'il utilise ; étendue réelle d'U-Boot par rapport au HWCONFIG ; marqueur waveform.
- `u_boot_handoff` reste **toujours UNQUALIFIED** : r1, r2 et la cmdline exigent le code U-Boot ou un journal série.
- **Plan de carte virtuelle compacte : 1 Gio** au lieu des 2 Gio d'EE, P3 de 526 908 416 octets, sans remplissage, P1/P2 inchangées.
- Refus explicites : fichiers non réguliers (`/dev/*`, répertoires) ; P1 dont l'empreinte diffère du FIRST BOOT scellé.

Le module est pur (analyse de `bytes`) ; seule la CLI ouvre des fichiers, en lecture seule.

## Qualification

| Contrôle | PASS | FAIL | SKIP | UNQUALIFIED |
| --- | --- | --- | --- | --- |
| Tests `test_boot_region` | **12/12** (Python 3.13.16) | 0 | — | — |
| Fuzz : 3 000 régions mutées sur IVT, uImage, HWCONFIG, MBR | 0 exception ; 2 594 refus, 406 cohérentes (mutations neutres) | 0 | — | — |
| Mutation du code : 16 mutants | 16 détectés après ajout de 2 tests et retrait d'un contrôle redondant | 3 survivants initiaux corrigés | — | — |
| Suite complète du dépôt | **334 exécutés, OK** | 0 | 15 (fakeroot, Qt, LuaJIT ou KOReader absents) | — |
| Boot émulé de FIRST BOOT #1 | — | — | **SKIP** : QEMU non construit, fichiers privés absents | Boot, KOReader, affichage |
| Fichiers privés (PRE-P1, P1, P2) | — | — | **SKIP** : absents de la session | Valeurs IH_LOAD/IH_EP réelles |
| Composition de carte et FAT32 | — | — | **SKIP** : non implémentées, `mkfs.fat` absent | — |

**Coût mesuré sur hôte :** analyse d'une région de 9,5 Mio en 4 ms ; pic d'allocation Python supplémentaire de 3,15 Mo (copie de la charge uImage), en plus de la région lue. Outil de poste, **jamais embarqué sur la Kobo** : 0 octet de RAM ou de rootfs côté appareil.

## Licences

EQ : SPDX `GPL-2.0-or-later` (`imx50-kobo-aura-hd.c:9`). EE : **aucun fichier de licence** dans l'arbre, donc aucune réutilisation de code possible sans accord. Usage local seulement, comme outil. P : GPLv2 (audit du 24/10). Aucun firmware, U-Boot, waveform ou dump publié par ce lot.

## Prochain travail exact

1. **Sur le poste privé, sans écriture**, quand l'utilisateur le décidera : lancer `boot_region.py` sur la PRE-P1, la P1 scellée et la P2 sauvegardées. Ajouter les valeurs IH_LOAD/IH_EP et l'adresse U-Boot au BOOT CONTRACT. Ne publier que les champs, jamais les blobs.
2. **Composer la carte virtuelle 1 Gio :** copie PRE-P1 avec taille P3 corrigée (réutiliser `patch_pre_p1` de `replace-microsd-linux.py` plutôt que réécrire), P1/P2 à l'identique avec revérification SHA, FAT32 neuf via `mkfs.fat --offset` ou formateur Python testé. Fichier image uniquement.
3. **Construire EQ** (téléchargement de QEMU et dépendances : autorisation explicite requise), démarrer en mode snapshot, journaliser la console série. Relever machine ID/ATAG si U-Boot les affiche, puis l'arrivée jusqu'à KOReader. Un succès émulé reste UNQUALIFIED pour l'E-Ink, la batterie et la veille réelles.
