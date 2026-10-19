# PMKB — Matrice de compatibilité pilotes E606C0 / Linux 6.18

18 octobre 2026. **Aucun pilote moderne n'a été qualifié sur la Kobo Aura HD.** CONFIRMÉ signifie ici qu'une interface/une source historique est directement documentée, *pas* que le pilote moderne fonctionne. PARTIEL signifie qu'un équivalent amont existe mais que l'intégration matérielle reste ouverte ; INCONNU signifie absence de preuve suffisante. BLOQUANT seulement après incompatibilité démontrée : **aucun BLOQUANT matériel identifié à ce stade**.

Sources historiques vérifiées dans les précédents audits : [qualification](offline-hardware-qualification-fr.md), [watchdog et boot](offline-boot-gates-fr.md), [énergie](kernel-energy-roadmap-fr.md). Sources Linux modernes **tag v6.18** consultées : https://github.com/torvalds/linux/tree/v6.18 .

| Composant | Historique / interface et dépendances | Équivalent moderne identifié | Statut portage | Travail, tests hors appareil → test matériel futur |
| --- | --- | --- | --- | --- |
| EPDC E-Ink / waveform | mxc_epdc_fb, mxc_epdc_fake_s1d13522, MXCFB ioctl ; FW_IN_RAM ; framebuffer/DMA/horloges et waveform conservée en RAM | Un DRM générique LCDIF ne constitue **pas** un pilote EPDC i.MX50 ; équivalence amont **non démontrée** | **INCONNU** | Portage EPDC, waveform, IRQ, DMA, refresh, ABI KOReader ; comparer interfaces et ABI → vrai rafraîchissement, contraste, ghosting et reprise |
| Neonode ZForce v2 | zforce_i2c, I2C bus 0 à 0x50, IRQ, evdev, commande Active v2, miroir dragon | drivers/input/touchscreen/zforce_ts.c ; compatible neonode,zforce ; version/protocole IRQ/reset à confronter | **PARTIEL** | Diff de trames commandes/événements et wiring DT, scénarios tactiles synthétiques → I²C/IRQ, précision, axes, veille |
| Frontlight SY7201 / NTX | mx50_ntx_io, ioctl 241 entier, TABLE3+, GPIO/PMW via MSP430, pas interface backlight générique garantie | drivers/pwm/pwm-ntxec.c peut être une brique mais **aucune correspondance TABLE3+ prouvée** | **INCONNU** | Mapper chaîne SY7201, table PWM, GPIO, dépendance MCU, HAL luminosité → gradation, extinction, réveil |
| MSP430 | pmic_core_i2c / msp430_* ; bus 2 à 0x43 ; firmware, alimentation, watchdog et lumière | drivers/mfd/ntxec.c reconnaît certaines versions **et refuse les inconnues (ENODEV)** | **PARTIEL** | Identifier version MCU et protocole exact, ne pas envoyer de commandes intrusives ; test de tables/version hors appareil → version, arrêt/réveil observables |
| PMIC Freescale MC13892 | MXC_PMIC_MC13892 / I²C, rails, batterie | drivers/mfd/mc13xxx-core.c, drivers/regulator/mc13892-regulator.c | **PARTIEL** | DTS rails/IRQ/probe, ordre alimentation, batteries/charge → mesures sûres des rails/batterie |
| microSD interne/externe | contrôleurs eSDHC i.MX50, SD/MMC ; microSD système critique et sockets à identifier | imx50.dtsi eSDHC1…4, hôte SDHCI/FSL ; mapping de slots différent selon cartes | **PARTIEL** | Identifier bus, broches/pinctrl, powerseq et timings sans copier N514 ; comparaison source/DT → lecture seule carte de test distincte |
| USB | hôte/device i.MX50, phy, connectique et helpers Kobo | imx50.dtsi usb-otg, usbh1 ; dr_mode selon DT | **PARTIEL** | Auditer PHY/VBUS, endpoints, mode OTG et alimentation → énumération autorisée |
| Wi-Fi | modèle de module E606C0 non vérifié sur exemplaire (WC121A2 : relevé tiers), SDIO/firmware probable | couches MMC/SDIO et pilotes possibles, **aucun couple chipset/firmware démontré** | **INCONNU** | Identifier composant, firmware/licences, alimentation et consommation → radio off/on et association contrôlées |
| Boutons / Hall | TLE4913 documenté HWCONFIG ; GPIO IRQ et key mappings à retrouver ; aucun KeyMatrix selon flags | gpio-keys, gpio-keys-polled, input switch générique ; broches N514 non transposables | **PARTIEL** | Audit pinmux et polarités E606C0 → événements power, lumière, Hall |
| Horloges / DVFS | Freescale CCM, CPUFreq 1 GHz HWCONFIG ; rails/OPP et thermiques à relever | imx50.dtsi CCM ; support CPUfreq précis sur E606C0 non démontré | **PARTIEL** | Comparaison OPP/voltage/clk, aucune manipulation fréquence réelle → stabilité et énergie à chaque état |
| Suspend / réveil | BSP plateforme et MCU, PMIC, IRQ wake, EPDC/touch/SDIO | frameworks Linux PM, wakeup/irqchip ; séquence E606C0 non prouvée | **INCONNU** | Diagramme transitions avec composants dépendants, snapshot/contrôle statique → suspend/resume avec mesure énergétique |
| Watchdog | mxc_wdt compilé ; disable **vide**, périphérique plateforme commenté ; MCU conditionnel | imx50.dtsi wdog1 / pilote i.MX moderne ; MCU firmware inconnu | **PARTIEL** | Audit de probe, ownership, timeout et handoff sans ouverture /dev/watchdog → état via diagnostics sûrs, jamais ioctl de découverte |

## Risques transversaux

1. **DTS d'une autre carte :** v6.18 imx50-kobo-aura.dts cible N514/E606F0B, tactile Elan I2C à 0x15 et stockage eMMC ; notre HD E606C0 est ZForce à 0x50 et microSD interne. Ne réutiliser ni pinctrl ni rails sans preuve.
2. **Version MCU :** v6.18 ntxec.c lit la version et retourne -ENODEV pour les versions non reconnues. Ce n'est pas une preuve que **notre** MCU est refusé, puisque son identifiant reste inconnu.
3. **Écran :** simple présence de /dev/fb0 ou d'un driver DRM ne valide pas EPDC, waveform, mode d'update et interface KOReader.
4. **Énergie :** aucun gain démontré, aucun chiffre d'autonomie légitime sans scénarios et mesures réels.
5. **Licence :** sources GPL disponibles ne libèrent pas automatiquement les firmwares Wi-Fi, MSP430, Neonode ou la waveform.
6. **Mémoire :** base RAM, buffers DMA, HWCONFIG/waveform, taille décompressée et pointeur bootdata encore inconnus.

## Qualification et gates

- Hors appareil : revue comparative des sources épinglées ; compilation arm32 et DTS spécifique envisagées dans un **lot ultérieur avec dépendances autorisées** ; contrôle de schéma mémoire purement synthétique ; essais de négatifs, absence de réseau/IO.
- Sur appareil, **après autorisation séparée et récupération indépendante de P2** : diagnostic de boot sans écran, microSD vierge distincte, framebuffer/refresh, tactile, frontlight, stockage, Wi-Fi, veille/réveil, watchdog (sans commande exploratoire), énergie batterie.
- **Aucun statut de la matrice ne signifie compatible physiquement.** Ni l'absence de code amont ni le manque de preuve ne sont nommés BLOQUANT.
