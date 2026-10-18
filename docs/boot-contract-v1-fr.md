# PMKB — BOOT CONTRACT V1 (E606C0)

Date : 18 octobre 2026. Statut : **contrat documentaire / cohérence de métadonnées**, non pas contrat de boot physiquement qualifié. Référence historique conservée : Linux 2.6.35.3 + U-Boot Netronix 2009.08. FIRST BOOT, P1/P2/P3, toutes les images et les firmwares restent hors périmètre.

## Sources et qualification des affirmations

- **[BIN-DOC]** : constat documenté à partir des sauvegardes privées déjà inspectées ; le binaire n'a PAS été relu pendant ce lot. [Audit précédent](imx50-boot-chain-audit-fr.md), [matériel](hardware-fr.md), [HWCONFIG](hwconfig-fr.md), [partitions](partition-layout-fr.md).
- **[SRC-H]** : analyse déjà documentée des sources historiques Kobo/Netronix, sans preuve d'équivalence exacte entre source et U-Boot embarqué. [Audit matériel](offline-hardware-qualification-fr.md), [boot gates](offline-boot-gates-fr.md). Référence source Kobo : https://github.com/kobolabs/Kobo-Reader/tree/7a762964e7fa71ad8e8df50dd1b6eee721a43217/hw/imx507-aurahd .
- **[SRC-M]** : fichiers amont Linux **v6.18** consultés, non compilés : https://github.com/torvalds/linux/tree/v6.18/arch/arm/boot/dts/nxp/imx et https://github.com/torvalds/linux/blob/v6.18/Documentation/arch/arm/booting.rst .
- **[INF]** : déduction d'ingénierie, jamais constat physique. **[UNKNOWN]** : valeur non établie.

La correspondance HWCONFIG bPCB=28 → E606C0 et le remappage logique Netronix 28 → 11 sont documentés [BIN-DOC, SRC-H]. **11 n'est pas ici un machine ID ARM attesté.**

## Chaîne de boot et table de preuves

| Étape / objet | Connu et provenance | À prouver avant tout noyau alternatif |
| --- | --- | --- |
| i.MX50 Boot ROM → chargeur initial | SoC i.MX507 [BIN-DOC] ; présence de couches Netronix [SRC-H] | Support exact de boot, premier chargeur, binaire et emplacement effectifs [UNKNOWN] |
| U-Boot historique | Source famille Netronix 2009.08 [SRC-H] | Version et empreinte du binaire effectif ; séquence complète de chargement [UNKNOWN] |
| HWCONFIG pré-P1 | Offset disque 0x80000 ; v1.7, payload annoncé 39 octets, PCB 28 [BIN-DOC] | Adresse *RAM* et espace réservé [UNKNOWN] |
| uImage pré-P1 | Offset disque 0x100000 ; CRC header/payload vérifiés dans audit antérieur ; noyau 2.6.35.3-850-gbc67621+ [BIN-DOC] | Champs IH_LOAD, IH_EP, taille réelle de la charge, r0/r1/r2 [UNKNOWN] |
| Waveform pré-P1 | En-tête à 0x700000 ; blob extrait 1 158 319 octets [BIN-DOC] | Adresse *RAM*, allocation arrondie, conservation après décompression [UNKNOWN] |
| P1 ext4 | Offset disque 9 961 472 octets [BIN-DOC] | Ne doit JAMAIS servir de zone test durant ce lot |
| U-Boot → Linux | Sources : paramètres hwcfg_p, hwcfg_sz, waveform_p, waveform_sz [SRC-H] | Chaîne de commande effective et taille/pointeurs valides [UNKNOWN] |
| Entrée ARM | Convention ARM32 : r0=0 ; r1=machine ID si ATAG, r2=adresse de la liste ATAG ou du DTB [SRC-M] | Machine ID *réel*, bootargs/ATAG exacts, registres effectifs [UNKNOWN] |
| Données ATAG | Transmission plausible par U-Boot ancien [INF] | Liste ATAG_CORE…ATAG_NONE réelle et sa plage RAM [UNKNOWN] |
| Device Tree natif | i.MX50 mainline possède des DTS/DTSI ; pas une preuve de DTB transmis par l'U-Boot Kobo [SRC-M] | Capacité DTB du binaire sauvegardé [UNKNOWN] |

**Important : tous les offsets 0x80000/0x100000/0x700000 sont des offsets de STOCKAGE, pas des adresses RAM.** Les CRC historiques ne révèlent pas à eux seuls IH_LOAD/IH_EP. Un éventuel wrapper U-Boot/Netronix et son placement sont à caractériser séparément.

## Mémoire physique et réservations

512 Mio de RAM sont identifiés matériellement [BIN-DOC], mais **la base physique DRAM et ses sous-régions réellement utilisées au démarrage sur E606C0 ne sont pas qualifiées dans ce lot**. L'adresse 0x70000000 apparaît dans les DTS d'autres cartes i.MX50 (EVK et Kobo Aura N514) [SRC-M] ; elle n'est donc **pas adoptée comme valeur du contrat E606C0**.

| Région | Début RAM réel | Taille réellement réservée | Taille de donnée connue | Précaution |
| --- | --- | --- | --- | --- |
| noyau uImage et zone de décompression | INCONNU | INCONNUE | Champ IH_SIZE non relu ici | Vérifier les deux empreintes chargé/décompressé |
| HWCONFIG | INCONNU | INCONNUE | payload annoncé 39 octets, enveloppe possiblement supérieure | Ne pas assimiler taille payload / réservation |
| waveform EPDC | INCONNU | INCONNUE | 1 158 319 octets extraits [BIN-DOC] | Arrondi et durée de vie mémoire à prouver |
| ATAG ou DTB | INCONNU | INCONNUE | INCONNUE | Pointeur r2, alignement, chevauchement, éventuelle écrasement |
| autres réservations U-Boot/DMA/framebuffer | INCONNU | INCONNUE | INCONNUE | Énumérer avant de valider la carte finale |

[INF] Si la waveform est chargée dans une mémoire réutilisée lors de la décompression ou par l'allocateur noyau, le pilote EPDC peut perdre sa donnée ; une réservation explicite ou une copie contrôlée peut être nécessaire. Aucune valeur de carte mémoire n'est déduite sans relevé.

## Conditions du saut Linux

1. Décoder en **lecture seule** les 64 octets de l'en-tête uImage privé (magic, header CRC, payload CRC, architecture, type, compression, taille, load, entry). Vérifier la concordance avec le bootloader exact et le payload sauvegardé.
2. Établir physiquement la fenêtre DRAM et toutes les plages chargées. Le framebuffer/DMA et les blocs waveform/HWCONFIG exigent une analyse de leur conservation après la prise de contrôle noyau.
3. Identifier le machine ID ARM et les registres r0/r1/r2, ainsi que la sérialisation des ATAG et de la cmdline (la valeur 11 du remappage PCBA n'est pas une substitution).
4. Pour une voie DT : préférer un DTB réellement remis à r2. Étudier, **sans le présumer compatible**, ARM_APPENDED_DTB et ARM_ATAG_DTB_COMPAT pour un ancien U-Boot ; les données mémoire dynamiques et bootargs doivent être reprises explicitement.
5. Écrire un DTS **E606C0 spécifique**, ne pas copier le DTS Kobo Aura N514 : cette autre machine est E606F0B, tactile Elan et stockage eMMC (sources Linux 6.18). Faire l'inventaire des GPIO, horloges, régulateurs et contrôleurs Aura HD.
6. Un bootloader ancien pourrait charger une uImage contenant une charge zImage/DTB compatible [INF] ; la prise en charge des formats, l'adresse d'entrée, la compression et la remise de registres restent à **prouver sur le binaire réellement conservé**. Ne pas conclure à un boot opérationnel.

## Verdict V1

- **Conserver U-Boot : OUI, comme baseline et choix de sûreté.** Sa capacité à amorcer un noyau moderne reste INCONNUE.
- **Linux 6.18 : candidat de comparaison documentaire**, pas version choisie pour installation. Socle i.MX50 présent, mais contrat DRAM, EPDC, MCU, réveil et Device Tree E606C0 non validés.
- **Obstacle prouvé** : on ne peut pas utiliser tel quel le DTS N514 pour E606C0 ; identification des cartes différente [SRC-M, BIN-DOC].
- **Aucun obstacle de boot matériel démontré** ; plusieurs gates non franchies ne sont pas des incompatibilités avérées.
- Ne pas changer FIRST BOOT, U-Boot, P1/P2/P3, recovery, microSD ou image. Prochaine pièce manquante : relevé privé et déterministe des champs uImage + machine ID + RAM en lecture seule, hors publication des blobs.

## Validateur hors matériel (sémantique bornée)

API pure : experimental/power-lab/boot_contract.py (analyze et analyze_json) ; tests : tests/test_boot_contract.py. Il exige un JSON déclaratif complet : format, device, provenance, ram, regions, image, handoff, parameters. Quatre régions obligatoires : kernel, boot_data, hwconfig, waveform ; autres réservations déclarables. Il vérifie 512 Mio, bornage entier 32 bits, alignement de départ/tailles réservées à 4 octets, non-chevauchement, correspondances pointeurs/tailles/zone noyau et r2 dans boot_data. Les tailles brutes HWCONFIG/waveform peuvent ne pas être multiples de 4 : **c'est la région réservée qui l'est**.

Il ne vérifie **ni le contenu réel des ATAG/DTB, ni l'intégrité du uImage, ni les adresses de décompression, ni l'activation du matériel**. Ses sorties sont uniquement refused ou consistent_unverified, jamais un PASS boot ni un permis d'écrire. Des champs inconnus doivent refuser l'entrée. **Toutes les adresses de tests sont purement synthétiques**, y compris 0x70000000 et r1=1234.
