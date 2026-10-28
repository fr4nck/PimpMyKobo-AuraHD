# PMKB — Inventaire vérifié des dépôts publics du compte lgeek

**Date de consultation : 25 octobre 2026** — cible : Kobo Aura HD / `dragon` / E606C0 / 512 Mio. Ce document prolonge [l'audit racine OKReader M01](recherche-sources-fr.md#m01-okreader) et [l'audit de ses forks](okreader-forks-audit-2026-10-25-fr.md).

## Périmètre et vérité des preuves

- Inventaire GitHub par recherche `user:lgeek` : **60 dépôts publics accessibles**, page suivante vide ; requête `user:lgeek fork:false` : **38 dépôts non-forks**, soit **22 forks** parmi les 60. Les dépôts privés ou effacés ne sont naturellement pas comptés.
- Tous les **60 dépôts ont été recensés par nom et classés thématiquement** dans l'index en fin de document. Les classes sont **des filtres de recherche**, parfois fondés sur le seul nom du dépôt ; elles ne prétendent pas que chaque fichier a été audité.
- Les **conclusions techniques** ci-dessous reposent uniquement sur la lecture de README, fichiers source, historiques et diffs Git précis. Une lecture du code n'est ni une compilation ni une preuve de fonctionnement sur E606C0. Aucun package, clone, firmware ou modèle tiers téléchargé.
- **Aucune modification** de P1, P2, P3, PRE-P1, U-Boot, waveform, FIRST BOOT scellé ni des exécutables PMKB. Aucune autorisation d'écriture physique déduite de cet inventaire.

## Résultat : seulement quelques dépôts méritent une exploitation PMKB

| Niveau | Dépôt | Observation effectivement vérifiée | Suite autorisée |
| --- | --- | --- | --- |
| **P0 / déjà connu** | [okreader](https://github.com/lgeek/okreader) | OS Debian/KOReader sans Nickel, historique **2018** ; support **Aura HD incertain** | Conserver [M01](recherche-sources-fr.md#m01-okreader), ne jamais appliquer son installation destructive |
| **P0 / déjà audité** | [linux-okreader](https://github.com/lgeek/linux-okreader) | Noyau legacy i.MX50 2.6.35.3, branche i.MX6 3.0.35 séparée | Se référer à [R1/R3](kernel-community-audit-2026-10-24-fr.md), comparer seulement des patches ciblés |
| **P0 / comparateur** | [u-boot-okreader](https://github.com/lgeek/u-boot-okreader) | Ancienne adaptation Freescale/Netronix ; aucune preuve de boot amélioré sur E606C0 | Comparaison U-Boot/HWCONFIG en lecture seule, pas de flash |
| **P1 / historique** | [koreader](https://github.com/lgeek/koreader) | `master` arrêté à `d3d30c405a32` (28 juin 2018), commit présent aussi dans le dépôt upstream ; **5 branches annexes** et des corrections de veille/Wi-Fi/horloge | Contrats historiques à comparer à KOReader moderne, voir ci-dessous |
| **P1 / historique** | [koreader-base](https://github.com/lgeek/koreader-base) | `master` arrêté à `d15c92c552f0` (7 février 2015), commit également présent dans l'upstream ; branche `wpacli` | Voir uniquement le client WPA optionnel et ses dépendances |
| **P1 / outil hôte conditionnel** | [crc_rev](https://github.com/lgeek/crc_rev) | Code C GPLv2+, déduit les paramètres d'un CRC à partir d'échantillons et de CRC connus ; 2013 | Utile si CRC propriétaire **inconnu** rencontré lors d'un audit HWCONFIG/U-Boot ; inutile pour les CRC déjà documentés |
| **P1 / mesure future** | [tinymembench](https://github.com/lgeek/tinymembench) | Teste débit/latence mémoire, exemples de compilation statique ARM Cortex-A8, `readme.txt` et `Makefile` lus ; fork ancien (2016) | Prévoir des mesures après premier boot, pas un service embarqué ni une nouvelle dépendance permanente |
| **P1 / diagnostic CPU** | [arm_tlb_huge_pages](https://github.com/lgeek/arm_tlb_huge_pages) | Documentation et test `tlb_test` sur les TLB ARM, tableau incluant Cortex-A8 ; dernière activité observée 2017 | Ressource de profilage ; **ne pas activer des huge pages** sur Aura HD par simple analogie |
| **P2 / idée terminal** | [ptmux](https://github.com/lgeek/ptmux) | Source C `ptmux.c` : multiplexeur de pseudo-terminaux par `select()`, avec routage de caractères ; dernier commit 2012 | **Inspiration** pour terminal/sessions PMKB ; ne fournit **ni interface e-ink ni clavier virtuel** |
| **P2 / matériel étranger** | [uboot-sdwifi](https://github.com/lgeek/uboot-sdwifi) | U-Boot de cartes SD Wi-Fi **Transcend KA2000**, avec choix du second-stage pour réduire les risques de flash | Exemple de conception/diagnostic, **pas U-Boot pour E606C0** |
| **P2 / puce non établie** | [MTK5931](https://github.com/lgeek/MTK5931) | Code Wi-Fi MediaTek MT5931 / BT MT6622 ; pas de preuve que notre module SDIO est cette puce | **Ne pas importer** avant identification matérielle de la puce Kobo |
| **P2 / BSP étranger** | [linux-2.6.35.3-imx53](https://github.com/lgeek/linux-2.6.35.3-imx53) | Noyau Freescale i.MX53, derniers commits 2011, dont correction vidéo HDMI/VGA 1080p | Comparateur historique limité ; **i.MX53 ≠ i.MX507** |
| **ÉCARTER** | [qshttpd](https://github.com/lgeek/qshttpd) | Auteur décrit lui-même un serveur HTTP C de formation, non prêt pour la production et potentiellement vulnérable | Ne pas embarquer dans PMKB ; garder des services réseau optionnels maintenus |
| **Hors architecture** | [xf86-video-fbturbo](https://github.com/lgeek/xf86-video-fbturbo), [Linux3188](https://github.com/lgeek/Linux3188) | Accélération graphique Rockchip pour **Xorg/LCDC** ; ce n'est pas le contrôleur EPDC de l'Aura HD | Aucun portage direct à PMKB-UI |

## Correctifs précis des branches KOReader de lgeek

Les références ci-dessous proviennent de **diffs Git de commits**, non d'une simple interprétation des titres des branches :

| Branche | Diff ou commit observé | Comparaison avec le KOReader upstream examiné en 2026 | Décision |
| --- | --- | --- | --- |
| [`async_wifi_suspend`](https://github.com/lgeek/koreader/commit/848d9b4895ce395f0ca54d37a53dc84490ea1e1b) | Affiche le screensaver et rafraîchit l'écran **avant** la coupure Wi-Fi différée ; programme `self.suspend` ensuite | [`frontend/device/generic/device.lua` actuel](https://github.com/koreader/koreader/blob/master/frontend/device/generic/device.lua) emploie déjà `UIManager:forceRePaint()` **avant** `network_manager:disableWifi()` puis gère `beforeSuspend` / la temporisation. Fonctionnement équivalent sur ce point, mais non identique ligne à ligne | **RETENIR le contrat**, **NE PAS copier** le correctif 2018 ; test veille réelle différé |
| [`wifi_fix`](https://github.com/lgeek/koreader/commit/0ad20ef31b0abe9c643f2ac0127377d236aad1b5) | Ajoute `self.info.psk = nil` au changement de mot de passe Wi-Fi | [`networksetting.lua` actuel](https://github.com/koreader/koreader/blob/master/frontend/ui/widget/networksetting.lua) **contient la même invalidation** | **DÉJÀ PRÉSENT en upstream**, aucune réimplémentation |
| [`ntpd_fix`](https://github.com/lgeek/koreader/commit/3b7836dfbb1a2f62f9de87b1d5f622ec0aee2b69) | Ancien `ntpd -q -n -g` après reset RTC lié à une batterie épuisée ; `-g` lève un seuil de décalage pour l'implémentation concernée | [`timesync.koplugin/main.lua` actuel](https://github.com/koreader/koreader/blob/master/plugins/timesync.koplugin/main.lua) utilise, dans sa branche BusyBox, `ntpd -q -n -p pool.ntp.org` **sans `-g`** et possède une détection d'implémentation | **QUESTION OUVERTE** : mesurer sur l'implémentation exacte de PMKB, **ne pas conclure à une régression** |
| [`base-update`](https://github.com/lgeek/koreader/tree/base-update) | Une mise à jour de pointeur de sous-module | Évolution historique sans preuve de fonction unique à conserver | Archive |
| [`typo`](https://github.com/lgeek/koreader/tree/typo) | Correction mineure texte/code | Aucun besoin PMKB distinct | Archive |
| [`wpacli` dans koreader-base](https://github.com/lgeek/koreader-base/commit/260127102bed6ac9f0f06f47414fd2559cd0eefa) | Ajoute le sous-module [`koreader/lj-wpaclient`](https://github.com/koreader/lj-wpaclient), ses liens Lua et ses règles Makefile | Conception du client WPA dans une pile datée de 2015, pas la situation de nos pilotes et ABI | Comparaison documentaire sous R5 seulement |

**Précaution de version :** les fichiers upstream « actuels » ci-dessus ont été consultés sur la branche par défaut de KOReader à la date de cet audit ; cela **ne prouve pas** que toutes les mêmes lignes se trouvent dans le paquet KOReader **v2026.07.1** préparé par PMKB. Ne pas annoncer de test sur notre P1 scellée.

## Directions retenues

1. **FIRST BOOT prioritaire** : ne pas remplacer U-Boot ni P1 pour explorer ces dépôts. Les conclusions des audits du noyau déjà conduits restent valides.
2. **R5, veille/Wi-Fi/RTC** : préparer une petite matrice de scénarios matériels : veille avec Wi-Fi activé ; écran visible avant arrêt du réseau ; sortie de veille ; changement de mot de passe ; décharge complète puis remise à l'heure (sans provoquer artificiellement une décharge profonde). Observer consommation, délai écran et processus, distinguer KOReader et couche PMKB.
3. **Diagnostic technique conditionnel** : utiliser les travaux `tinymembench`, `arm_tlb_huge_pages`, `crc_rev` seulement en environnement de qualification, lorsque des mesures ou données le justifient ; ne pas les installer dans P1 par défaut.
4. **Applications futures** : `ptmux` inspire une gestion frugale des sessions pseudo-terminal, mais **ne crée aucune application du Store** à lui seul.
5. **Matériel** : ne tirer aucune conclusion de compatibilité Aura HD à partir des ports i.MX6, i.MX53, Rockchip, Transcend KA2000 ou MediaTek sans preuve propre E606C0.

## Index exhaustif des 60 noms de dépôts publics visibles

Classement thématique *approximatif*, volontairement distinct de l'évaluation technique ci-dessus : les projets ici indexés n'ont **pas** tous été audités ligne par ligne. Inventaire établi à partir des résultats GitHub de la session (y compris l'unique dépôt archivé `Python-Spectrograph`).

### Pile Kobo / KOReader (5)

[okreader](https://github.com/lgeek/okreader) · [linux-okreader](https://github.com/lgeek/linux-okreader) · [u-boot-okreader](https://github.com/lgeek/u-boot-okreader) · [koreader](https://github.com/lgeek/koreader) · [koreader-base](https://github.com/lgeek/koreader-base)

### Linux embarqué, amorçage et matériel hors Kobo (24)

[gnu-linux-on-acer-chromebook-13](https://github.com/lgeek/gnu-linux-on-acer-chromebook-13) · [jetson_hw_hacking](https://github.com/lgeek/jetson_hw_hacking) · [uboot-sdwifi](https://github.com/lgeek/uboot-sdwifi) · [linux-2.6.35.3-imx53](https://github.com/lgeek/linux-2.6.35.3-imx53) · [Linux3188](https://github.com/lgeek/Linux3188) · [linux-tronsmart-orion-r28](https://github.com/lgeek/linux-tronsmart-orion-r28) · [kernel_rockchip](https://github.com/lgeek/kernel_rockchip) · [linux-mainline-nyan-big](https://github.com/lgeek/linux-mainline-nyan-big) · [MTK5931](https://github.com/lgeek/MTK5931) · [xf86-video-fbturbo](https://github.com/lgeek/xf86-video-fbturbo) · [xf86-video-rk30fb](https://github.com/lgeek/xf86-video-rk30fb) · [nxp_lpc_usb_bootloader_script](https://github.com/lgeek/nxp_lpc_usb_bootloader_script) · [PKGBUILDs](https://github.com/lgeek/PKGBUILDs) · [libopencm3](https://github.com/lgeek/libopencm3) · [orpsoc](https://github.com/lgeek/orpsoc) · [u-boot-orpsoc](https://github.com/lgeek/u-boot-orpsoc) · [adv_debug_sys](https://github.com/lgeek/adv_debug_sys) · [Arduino-Color-LCD](https://github.com/lgeek/Arduino-Color-LCD) · [Arduino-Wii-Nunchuk](https://github.com/lgeek/Arduino-Wii-Nunchuk) · [RF24](https://github.com/lgeek/RF24) · [lpc_part_ids](https://github.com/lgeek/lpc_part_ids) · [bldc](https://github.com/lgeek/bldc) · [vesc_tool](https://github.com/lgeek/vesc_tool) · [lcd_bracket](https://github.com/lgeek/lcd_bracket)

### Mesure, analyse binaire, terminal et diagnostics (12)

[arm_tlb_huge_pages](https://github.com/lgeek/arm_tlb_huge_pages) · [arm_ret_microbench](https://github.com/lgeek/arm_ret_microbench) · [tinymembench](https://github.com/lgeek/tinymembench) · [cache_size](https://github.com/lgeek/cache_size) · [crc_rev](https://github.com/lgeek/crc_rev) · [ptmux](https://github.com/lgeek/ptmux) · [pie-arm](https://github.com/lgeek/pie-arm) · [LPATHBench](https://github.com/lgeek/LPATHBench) · [spec_poc_arm](https://github.com/lgeek/spec_poc_arm) · [dynamorio_pin_escape](https://github.com/lgeek/dynamorio_pin_escape) · [dynamorio](https://github.com/lgeek/dynamorio) · [ioli_crackme_dbm_solution](https://github.com/lgeek/ioli_crackme_dbm_solution)

### Autres : radio, multimédia, réseau, web, pilotes PC (19)

[sdr-examples](https://github.com/lgeek/sdr-examples) · [Python-Spectrograph](https://github.com/lgeek/Python-Spectrograph) · [h107_rev](https://github.com/lgeek/h107_rev) · [catalyst-test-compat-headless-opencl](https://github.com/lgeek/catalyst-test-compat-headless-opencl) · [Soundcloud-playlists](https://github.com/lgeek/Soundcloud-playlists) · [save_email](https://github.com/lgeek/save_email) · [xrandr-set-outputs](https://github.com/lgeek/xrandr-set-outputs) · [dump1090](https://github.com/lgeek/dump1090) · [ricochet](https://github.com/lgeek/ricochet) · [polyglossy](https://github.com/lgeek/polyglossy) · [catalyst-intel-select](https://github.com/lgeek/catalyst-intel-select) · [qshttpd](https://github.com/lgeek/qshttpd) · [cellminer](https://github.com/lgeek/cellminer) · [QTV-fork](https://github.com/lgeek/QTV-fork) · [uominfo](https://github.com/lgeek/uominfo) · [FFmpeg](https://github.com/lgeek/FFmpeg) · [catalyst-test-compat](https://github.com/lgeek/catalyst-test-compat) · [grid-apps](https://github.com/lgeek/grid-apps) · [twilio-auth](https://github.com/lgeek/twilio-auth)


## Qualification et limites

- **PASS (inventaire GitHub) : 60/60** noms publics présents dans la liste obtenue ; 38 non-forks / 22 forks par filtrage GitHub.
- **PASS (comparaison statique ciblée)** : lecture des 4 branches KOReader/`koreader-base` utiles et des trois chemins upstream de veille, réseau, horloge ; `wifi_fix` retrouvé dans l'upstream, ordre d'affichage/arrêt Wi-Fi déjà présent.
- **PASS (source examinée)** : `ptmux.c`, `crc_rev.c` et son README, `tinymembench/readme.txt` et Makefile, `arm_tlb_huge_pages/readme.md`, `uboot-sdwifi/README.md`, `MTK5931/README.md`, plusieurs autres README ciblés.
- **NON QUALIFIÉ** : exhaustivité des branches de tous les 60 dépôts, état des licences de chaque fork, compatibilité des binaires avec E606C0, performance/énergie/veille sur Kobo physique, audit complet de chaque arbre source.
- **0 téléchargement de code ou firmware, 0 build, 0 modification de runtime PMKB, 0 écriture de support physique.** Documents seuls, sans modification du contrat FIRST BOOT ni des SHA préservés.
