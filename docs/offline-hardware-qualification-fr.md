# Aura HD E606C0 : interfaces matérielles sans Nickel

Audit du 3 octobre 2026, sur sources et sauvegardes locales uniquement. Les scripts sous `experimental/offline-rootfs` et l'image expérimentale v3 restent inchangés. Le lot séparé `experimental/offline-audit` contient uniquement une proposition de réglages KOReader ; il n'est pas intégré au démarrage, au paquet CLI ou à une image.

**Résultat : les trois interfaces et leurs chemins d'initialisation sont identifiés sans Nickel. Leur fonctionnement physique ne peut pas être certifié hors matériel.** Le blocage lié aux réglages Nickel est, lui, reproduit et supprimé dans un test isolé des fonctions amont réelles. Cela ne qualifie pas le démarrage complet.

## Provenance et degré de preuve

Les sources sont présentes dans `aura-hd/aurahd-src/linux-2.6.35.3`, les archives dans le checkout local Kobo-Reader à la révision `7a762964e7fa71ad8e8df50dd1b6eee721a43217`.

- **K** : [archive officielle Aura HD](https://github.com/kobolabs/Kobo-Reader/blob/7a762964e7fa71ad8e8df50dd1b6eee721a43217/hw/imx507-aurahd/linux-2.6.35.3.tar.gz), SHA-256 `01eb66e755243e3c916092dc7dc2d35b259d8f080ae6ad95698e4e69773d0c51`. Les 19 fichiers source/configuration examinés correspondent octet pour octet à cette archive. Les numéros de ligne K ci-dessous désignent ses fichiers internes.
- **B** : sources U-Boot locales `u-boot-2009.08/board/freescale/mx50_rdp/ntx_comm.c`, notamment lignes 14–29 et 201–299. Leurs fichiers ont été hachés dans le relevé local ; l'identité du binaire U-Boot avec une compilation de ces sources n'est pas démontrée.
- **H** : tables locales du [U-Boot Aura H2O](https://github.com/kobolabs/Kobo-Reader/blob/7a762964e7fa71ad8e8df50dd1b6eee721a43217/hw/imx507-aurah2o/u-boot-2009.08.tar.bz2), utilisées uniquement pour décoder les champs HWCONFIG v1.7 absents du vieux schéma Aura HD. Aucun pilote Aura H2O n'est proposé pour l'Aura HD. `ntx_hwconfig.c:199–242` associe 6 à `TABLE3+` et 0 à `SY7201` ; `ntx_hwconfig.h:195` place le champ LED à l'indice 38.
- **R** : archive rootfs locale `AuraHD-recovery-fs.tgz`, et textes lus directement dans l'image P2 avec `debugfs` sans `-w`. Les scripts sont examinés comme des données, jamais exécutés.
- **Q** : [paquet officiel KOReader v2026.07.1](https://github.com/koreader/koreader/releases/tag/v2026.07.1), archive Kobo SHA-256 `0f36a62ce73b12516f969e4ad7862cc06920afb03c7bd4db29a0d990bdd84b2f`. Les chemins Q désignent les fichiers de ce paquet, pas une branche amont mouvante.

La copie pré-P1 vérifiée contient un uImage à l'offset 1 048 576 ; ses CRC d'en-tête et de contenu sont valides. Son payload SHA-256 est `4735dcc0a3a2515606840c4831f8bcd27f31053a86dae9f2b7b11b5ac6fb4412`. Le noyau indique `2.6.35.3-850-gbc67621+`, build `#1027`, 28 mars 2013. Sa configuration embarquée IKCONFIG est identique au `.config` de K, SHA-256 `136a390685c4cd38f2dc9708006a75d5341f5be11de83962d4d64a769049d4ae`. Cela confirme la configuration du vrai noyau sauvegardé ; cela ne prouve pas que tout son code binaire est reproductible depuis K.

Cette configuration intègre `ARCH_MX50`, `MACH_MX50_RDP`, `FB_MXC_EINK_PANEL`, `TOUCHSCREEN_ZFORCE`, `INPUT_EVDEV`, `MXC_PMIC_MC13892` et `MXC_PMIC_I2C`. `DEVTMPFS` est désactivé : un montage automatique de devtmpfs ne remplace pas la création des nœuds. `FW_LOADER` est actif, mais la branche E-Ink analysée emploie les données en RAM.

Le HWCONFIG réel confirme `PCB=28`, `TouchCtrl=8` (Neonode v2), `TouchType=4` (IR), `DisplayResolution=3`, `FrontLight=6`, `FrontLight_Flags=0`, `PCB_Flags=1`, dernier champ LED=0. Le vieux pilote décide de la table par `bFrontLight`, sans avoir besoin du nouveau champ de nom du circuit LED.

## 1. Framebuffer E-Ink

| Élément demandé | Preuve et conséquence |
| --- | --- |
| Composant | EPDC i.MX50 et panneau 1080 × 1440, bus HWCONFIG `16Bits_mirror`. |
| Interface matérielle attendue | Framebuffer Linux mmap, informations FBIO, puis ioctls MXCFB d'envoi et d'attente des rafraîchissements. |
| Fichier/devnode/sysfs | `/dev/fb0` ; `/sys/class/graphics/fb0/dev`, `rotate`, `bits_per_pixel` ; paramètres noyau `waveform_p`, `waveform_sz`, `hwcfg_p`, `hwcfg_sz`. La présence de `fb0` seule ne prouve pas que le panneau est prêt. |
| Code/source | K `drivers/video/mxc/mxc_epdc_fb.c:1133` inclut `mxc_epdc_fake_s1d13522.c`, qui définit `FW_IN_RAM` à la ligne 11. `epdc_firmware_func` à 2316 transmet `gpbWF_vaddr/gdwWF_size` au handler ; `mxc_epdc_fb_init_hw:4081` lance ce travail ; le handler initialise l'EPDC et marque `hw_ready` à 4039. K `fake_s1d13522.c:206–358` parse/réserve la mémoire. K `include/linux/mxcfb.h:139–140` et `mxc_epdc_fb.c:3061–3140` définissent/traitent SEND_UPDATE et WAIT_FOR_UPDATE_COMPLETE. Q `ffi/framebuffer_linux.lua:51–142` ouvre/mappe le framebuffer ; `ffi/framebuffer_mxcfb.lua` fournit les appels MXCFB. |
| Séquence d'initialisation nécessaire | Conserver la chaîne de boot qui charge HWCONFIG/waveform en RAM ; laisser le pilote intégré initialiser le panneau ; créer le nœud à partir de son entrée sysfs ; vérifier dimensions/profondeur/rotation ; préparer la géométrie avant l'ouverture/map KOReader ; ensuite seulement produire un rafraîchissement et attendre sa fin. Le lanceur Q prévoit `fbdepth -d 8 -R UR` pour les panneaux monochromes. Ce n'est pas une preuve que cette commande, sans contrôle du mode initial et de son résultat, suffit sur notre démarrage autonome. |
| Dépendance à un binaire Kobo | Aucun besoin Nickel démontré. R `on-animator.sh` utilise `pickel showpic` pour l'animation, mais l'initialisation EPDC existe dans le noyau avant cette animation. `fbdepth` est un outil livré avec KOReader, pas `pickel` ; l'animation n'est pas une étape nécessaire déduite des sources. |
| Libre / propriétaire / inconnu | Pilote K GPL ; code KOReader/FBInk libre. Données waveform propres au panneau : licence et possibilité de reconstruction inconnues. Les conserver n'établit pas une chaîne entièrement libre. |
| Test possible hors matériel | Configuration IKCONFIG réelle, comparaison de sources, schéma des ioctls, lecture des en-têtes Netronix et SHA de la waveform, simulation de la géométrie et des appels. En-tête waveform valide à 7 340 032, taille 1 158 319, SHA-256 `9335791cd91e8c66b9fa700cb81f7885b800571f2361b35a9eae42fb48183efb`. L'intégrité du fichier n'est pas une validation électrique ou visuelle. |
| Test nécessitant la vraie Aura HD | État réel du panneau au boot, mode 8/16 bpp et orientation, rafraîchissement complet/partiel, fin des marqueurs, contraste/ghosting, reprise après veille. Ces essais produisent des écritures matérielles et exigent une autorisation future distincte. |

B fixe le début waveform au secteur 14336 et charge les blobs Netronix après validation d'un en-tête `ff f5 af ff`, puis ajoute leurs adresses/tailles à la ligne de commande noyau. La copie pré-P1 contient cet en-tête et cette plage complète. Dans K, `FW_IN_RAM` sélectionne la branche qui ne demande pas de fichier waveform à udev. Il serait donc erroné de recopier systématiquement la génération `epdc_E60_V220.fw` du script `freescale` pour la cible `ntx508`.

Le test ARM isolé `framebuffer-abi.lua` confirme aussi le layout classique NTX : structure de 68 octets, alternate buffer à l'offset 36, SEND_UPDATE `0x4044462e`, WAIT_FOR_UPDATE_COMPLETE `0x4004462f`. Ce sont les tailles/encodages du header K et de la branche Q pour les anciens Kobo. Le test ne réalise aucun ioctl ; le succès d'un rafraîchissement reste matériel.

## 2. Tactile Neonode v2 / IR

| Élément demandé | Preuve et conséquence |
| --- | --- |
| Composant | Neonode ZForce IR, branche protocole v2 choisie par `bTouchCtrl=8`. |
| Interface matérielle attendue | I²C 0, adresse 0x50, IRQ GPIO ; sortie Linux input/evdev, événements ABS_X, ABS_Y, ABS_PRESSURE et BTN_TOUCH. |
| Fichier/devnode/sysfs | `/dev/input/eventN` identifié comme `zForce-ir-touch`, pas supposé être toujours event1 ; `/sys/class/input/eventN/device/name` et `/sys/class/input/eventN/dev`. Attribut optionnel `neocmd` du client I²C, normalement visible sous le périphérique `0-0050` ; ne pas l'écrire pour « essayer ». |
| Code/source | K `mx50_rdp.c:1921–1927` déclare `zforce-ir-touch`, 0x50 et IRQ ; sa branche IR à 2873 enregistre le client. K `zforce_i2c.c:511–615` probe et enregistre l'input ; `zforce_i2c_open:482–494` envoie Active v2. Les réponses aux commandes à 174–214 enchaînent résolution, fréquence et demande des données tactiles. `DEVICE_ATTR(neocmd,0644,...)` est à 428. Q `device/kobo/device.lua:1065` sélectionne le protocole legacy pour dragon ; `initEventAdjustHooks:1122` corrige les axes et le miroir. |
| Séquence d'initialisation nécessaire | Laisser le noyau enregistrer l'I²C/IRQ et gérer le protocole ; attendre l'apparition de l'input ; identifier son nom et ses capacités ; créer son nœud depuis sysfs ; l'ouvrir avec KOReader, ce qui déclenche l'activation par le pilote ; laisser les réponses I²C enchaîner résolution/fréquence/acquisition ; appliquer les corrections d'axes du modèle dragon. Les numéros event0/event1 ne sont pas un contrat d'identité. |
| Dépendance à un binaire Kobo | Aucun besoin Nickel ni outil utilisateur d'activation démontré. `root/neonode/ReadMe` appelle `BSL_scripter` ; son `script.txt` contient MASS_ERASE et RX_DATA_BLOCK : c'est un outil de programmation du contrôleur, pas une étape de démarrage à reproduire. |
| Libre / propriétaire / inconnu | Pilote GPLv2, gestion des événements KOReader libre. Firmware déjà embarqué dans le contrôleur, `Target_m.txt` et outil BSL : licence/provenance non qualifiées ; ne pas les reprogrammer. |
| Test possible hors matériel | Configuration/probe/call-flow, format de trames v2, événements synthétiques et transformations des coordonnées. HWCONFIG UIStyle=1 active la branche `gIsCustomerUi` ; la rotation dépend aussi du framebuffer. Cela ne justifie aucune calibration inventée. |
| Test nécessitant la vraie Aura HD | Réponses IRQ/I²C et BootComplete, ordre effectif des eventN, appui/relâchement, précision aux quatre coins et au centre, bouton lumière/power, réveil et reprise. |

Le pilote fixe certaines bornes ABS avant de recalculer la résolution selon HWCONFIG. Les bornes annoncées par evdev ne doivent donc pas être considérées comme une calibration garantie : le test de coordonnées réelles reste nécessaire. Aucun correctif noyau conjectural n'est proposé.

## 3. Frontlight SY7201 / TABLE3+

| Élément demandé | Preuve et conséquence |
| --- | --- |
| Composant | HWCONFIG `FrontLight=6` et LED driver=0 ; noms TABLE3+/SY7201 décodés par H. Le pilote Aura HD emploie `FL_table3`. |
| Interface matérielle attendue | Misc device NTX ; ioctl entier 241 avec un niveau 0–100, transport PWM via MSP430/I²C et GPIO FL_EN/FL_R_EN. Ce n'est pas un pilote SY7201 à charger à la main ni un réglage standard `backlight/brightness` sur cette branche. |
| Fichier/devnode/sysfs | `/dev/ntx_io`, attendu via `/sys/class/misc/ntx_io/dev` ; minor déclaré 190 dans K. Vérifier l'entrée sysfs au boot au lieu de fabriquer un nœud sur la seule foi du nom. `pmic_light.1/lit` sert aux LED de signalisation, pas à cette table de luminosité. |
| Code/source | K `mx50_ntx_io.c:116–117,180` nomme ntx_io, minor 190, CM_FRONT_LIGHT_SET=241 ; `driverDevice:1331` et `initDriver:2514` font misc_register. `ioctlDriver:720` lit l'argument comme un entier, pas un pointeur ; `1130–1244` choisit TABLE3 pour bFrontLight=6, écrit PWM/fréquence et GPIO, puis éteint via travail différé. `gpio_initials:2154–2165` configure les GPIO. K `pmic_core_i2c.c:528–555` transporte msp430_write ; `msp430_probe:562` installe le client. Q `ffi/kobolight.lua:29–43` valide 0–100, ouvre ntx_io et appelle ioctl 241. |
| Séquence d'initialisation nécessaire | Conserver HWCONFIG ; laisser les pilotes PMIC/MSP430 et NTX intégrés effectuer leur probe/init ; créer ntx_io depuis sysfs ; vérifier les réglages KOReader indépendants de Nickel ; KOReader ouvre le nœud puis demande une intensité. Le pilote assure la table PWM et les temporisations ; ne pas les réimplémenter dans un script GPIO. |
| Dépendance à un binaire Kobo | Aucune dans ce chemin : KOReader → ioctl → pilote NTX → MSP430. La dépendance restante du paquet Q est le fichier de réglages Nickel, désactivable comme décrit ci-dessous. |
| Libre / propriétaire / inconnu | Pilotes K et code KOReader libres. Firmware interne du MSP430 et circuit LED : source/licence non qualifiées ; aucune mise à jour du MCU n'est prévue. |
| Test possible hors matériel | Comparaison des valeurs HWCONFIG, correspondance ioctl entier/table, contrôle de plage dans kobolight, tests des réglages sans accès Nickel. Un retour ioctl réussi n'établit pas à lui seul que la lumière fonctionne : msp430_write peut retourner 0 si le client n'est pas probé. |
| Test nécessitant la vraie Aura HD | Présence du nœud/MSP430, lumière effective, progression de faible à moyenne intensité, extinction, bouton lumière, comportement après veille ; niveaux sûrs et observation de l'écran réel. |

## Règles et scripts rootfs/recovery

| Élément audité | Observation locale | Conséquence pour PMKB |
| --- | --- | --- |
| `/dev` dans R | Quelques nœuds statiques root:root, dont fb0 29:0, mode 0660 ; pas de ntx_io ni d'événements d'entrée dans l'archive rootfs. L'init recouvre `/dev` avec tmpfs. | Les nœuds statiques de l'archive ne remplacent pas le cold-plug. Le nom ntx_io provient du noyau, les eventN de l'ordre d'enregistrement. |
| udev | `/sbin/udevd` et `udevadm` présents. `rcS` démarre udev, fixe STARTUP=1, trigger, settle --timeout=2, puis efface STARTUP. | Ne pas assimiler cet ensemble à un seul parcours sysfs. Les permissions et les nœuds tardifs doivent être gérés séparément ; les helpers Kobo ne sont pas nécessaires pour les trois interfaces étudiées. |
| `50-udev-default.rules` | `event*` → `input/%k`, mode 0640 ; règles consoles, block et char ; liens par numéros majeurs/mineurs. | KOReader root peut ouvrir les entrées. Le futur choix de permissions PMKB reste à implémenter ; ne pas transformer tous les périphériques en 0666. |
| `kobo.rules` | Helpers Kobo pour carte externe, usb_host et usb_plug. Les helpers écrivent dans `/tmp/nickel-hardware-status`. | Compatibilité SD/USB du système Kobo ; pas un bootstrap requis par E-Ink/ZForce/NTX light. Q possède aussi des événements USB `fake_events`, sans dépendance obligatoire à ce fichier. |
| Firmware udev | `50-firmware.rules` invoque `firmware.sh`, qui fournit les fichiers demandés via `/sys$DEVPATH/loading` et `/data`. | Inutile pour la waveform dans la branche FW_IN_RAM démontrée ; ne pas généraliser à tous les futurs pilotes. Le prototype n'implémente pas ce service. |
| mdev | Lien BusyBox et `etc/mdev.conf` présents dans R ; règle SD écrivant le statut Nickel. `rcS` utilise udev. | Présence de mdev ≠ utilisation au boot. Le BusyBox différent du prototype n'offre pas l'applet mdev : aucune réutilisation implicite. |
| `kobo_config.sh` | Mode 0744 root:root ; appelle ntx_hwconfig sur mmcblk0 et traduit E606C* en dragon. | Marqueur compatible nécessaire à la détection Q, pas obligation d'utiliser ce script ni son binaire. PMKB possède déjà son propre marqueur ; le prototype n'est pas modifié. |
| Environnement | R construit PATH, runlevel, prevlevel, PRODUCT et PLATFORM ; son init normal lance Hindenburg/Nickel. PMKB exporte dragon/ntx508, HOME/XDG temporaires, KO_MULTIUSER, LANG et chemin GNU/KOReader. Q `datastorage.lua:18–49` utilise XDG_CONFIG_HOME/koreader lorsque KO_MULTIUSER est présent. | La proposition `defaults.custom.lua` serait à placer dans le futur profil temporaire, pas automatiquement dans `/opt/koreader`. Aucun profil installé aujourd'hui. |
| P2 réelle | Son rcS recrée P1/P3, applique des archives et écrit U-Boot ; ses commandes `pmic_light.1/lit` font clignoter les LED de signalisation. | Script de restauration destructif : jamais utilisé comme init autonome, jamais exécuté dans cet audit. P2 reste inchangée, SHA avant/après confirmé. |

Les scripts init, les outils BSL et les helpers lisibles de R n'ont pas pour autant une licence libre démontrée. Ils servent de preuves de comportement, pas de composants à redistribuer. udev/BusyBox ont des projets amont libres ; l'audit ne requalifie pas leur provenance binaire exacte.

## Nickel : chemins effectifs et correction isolée

| Chemin | Catégorie | Effet réel | Désactivation propre |
| --- | --- | --- | --- |
| `KOBO_LIGHT_ON_START=-2` → `_syncKoboLightOnStart()` → `NickelConf.frontLightLevel.get()` | Valeur par défaut héritée créant une dépendance réelle à un fichier, pas au processus Nickel | Si FrontLightLevel manque, le getter appelle le setter de secours ; celui-ci ouvre le fichier en écriture avec assert. Le relevé privé ne contient pas ce réglage. P3 en lecture seule peut donc provoquer un échec dès la synchronisation de départ. | `KOBO_LIGHT_ON_START=-1` choisit les réglages KOReader, avec la valeur initiale interne de 20 % en absence de réglage. |
| `KOBO_SYNC_BRIGHTNESS_WITH_NICKEL=true` → `saveSettings()` | Compatibilité héritée, inutile dans PMKB, activée par défaut | Lit et peut modifier le fichier Kobo ; peut provoquer le même échec. | Valeur booléenne false dans defaults.custom.lua ; LuaDefaults préserve false comme une surcharge réelle. |
| `require(device/kobo/nickel_conf)` | Module de compatibilité | Charger ce module définit les fonctions ; ne lit pas immédiatement le fichier. Ce n'est pas un appel au service Nickel. | Pas besoin de mutiler le module : les deux options évitent les chemins de lecture/écriture audités. |
| Marqueur `/bin/kobo_config.sh`, PRODUCT=dragon | Détection matérielle réelle | Q choisit le backend Kobo, puis le modèle dragon. | Conserver le marqueur PMKB propre et PRODUCT ; « Kobo » dans un nom de backend ne signifie pas Nickel. |
| Références Nickel dans les commentaires des fonctions d'affichage/veille | Documentation de compatibilité | Les fonctions travaillent sur framebuffer, ioctl et sysfs. Les commentaires ne constituent pas une dépendance au processus. | Ne pas supprimer du code matériel sur la base d'une recherche de chaînes. |
| Lanceur shell habituel : retour Nickel, KFMon, restauration du mode écran | Compatibilité de lancement inutilisée | Le prototype appelle reader.lua directement, sans ce lanceur. | Déjà contourné ; cela impose de qualifier séparément la préparation matérielle, sans recopier ses chemins de sortie. |
| `invertPageTurnButtons` cité dans le device générique | Commentaire comparant un réglage Nickel | `Device:invertButtons()` transforme la table locale des événements ; il ne lit pas la configuration Kobo. | Aucun réglage Nickel à désactiver dans ce chemin. |
| `external_keyboard_otg_mode_on_start` et remarque Nickel du plugin clavier | Réglage KOReader indépendant, commentaire concernant d'autres modèles | Le plugin consulte G_reader_settings et les interfaces USB/debugfs ; il ne demande pas Nickel. | À traiter dans l'audit USB, sans l'assimiler aux deux options de luminosité. |
| Références Nickel dans `dbg.lua` et `ffi/rtc.lua` | Exemple de documentation et comparaison RTC | L'exemple dbg est un commentaire ; RTC utilise ses propres appels noyau. | Aucun service Nickel à retirer pour ces références. |

Le test `tests/offline-audit/nickel-settings.lua` charge les vrais `powerd.lua`, `nickel_conf.lua`, `luadefaults.lua` et `defaults.lua` du paquet Q vérifiés par SHA. Les fonctions matérielles et dépendances périphériques sont remplacées par des objets factices. Chaque ouverture du fichier Nickel est interceptée, jamais transmise au système de fichiers : le défaut est reproduit avec un fichier manquant/lecture seule, au départ et à la sauvegarde. Avec les deux surcharges proposées, aucun accès au fichier Nickel ne survient, et les réglages KOReader sont conservés. Ni Device:init ni le framebuffer ni un ioctl n'est exécuté.

Ce test valide ces deux call-flows ; il ne prétend pas certifier tout KOReader ou l'ensemble des plugins. Le profil reste modifiable par KOReader ; ces options ne sont pas une barrière de sécurité immuable. Le montage P3 en lecture seule reste une protection distincte.

## Séquence minimale crédible, non installée

1. Conserver les données pré-P1 et la chaîne U-Boot/noyau qui passent HWCONFIG et waveform en RAM. Aucune écriture de ces zones.
2. Au futur boot, laisser les probes intégrés initialiser EPDC, ZForce et PMIC/MSP430/NTX. Attendre et identifier les entrées sysfs ; l'attente ne doit pas être remplacée par un délai arbitraire sans limite ni critères.
3. Créer les nœuds nécessaires depuis sysfs avec permissions explicites, en vérifiant le type et l'identité des entrées. Le prototype courant ne couvre pas encore tous ces contrôles.
4. Observer et préparer la géométrie framebuffer avant KOReader. `fbdepth` du paquet est une voie libre crédible ; le mode choisi et le résultat nécessitent une qualification matérielle. Aucun `pickel` ni script d'animation Kobo requis par le chemin source identifié.
5. Monter P3 en lecture seule ; préparer le profil temporaire et ses deux surcharges Nickel ; lancer le backend dragon. L'ouverture evdev active le tactile ; l'ioctl 241 pilote le frontlight à travers le noyau. Ne pas programmer le contrôleur Neonode ni réimplémenter son I²C/GPIO.
6. Lors d'un essai autorisé ultérieurement, valider les trois résultats observables avant veille/USB/persistance.

Le noyau réel active aussi `MXC_WATCHDOG` et `WATCHDOG_NOWAYOUT`. Le pilote `mxc_wdt.c:247–283` appelle disable pendant le probe et l'active dans open à 149–159 ; cela n'établit pas l'état physique effectif de tous les watchdogs, notamment du MCU. Ne pas ouvrir `/dev/watchdog` comme simple test de présence. Ce point et les états d'alimentation ne sont pas qualifiés par les trois interfaces ci-dessus.

## Conclusion de qualification

| Point | Levé hors matériel | Essai réel restant |
| --- | --- | --- |
| E-Ink | Pilote intégré, interfaces MXCFB, données waveform présentes, chaîne RAM et absence de dépendance Nickel dans ce chemin | Géométrie initiale et après préparation, panneau prêt, rafraîchissement réel |
| Neonode v2 | Identité HWCONFIG, pilote intégré, client I²C, activation/acquisition gérées dans le noyau, protocole evdev | Réponses du contrôleur, noms eventN effectifs, coordonnées, boutons et reprise |
| TABLE3+/SY7201 | Décodage HWCONFIG recoupé, misc NTX et ioctl 241, table PWM/MSP430, correction des réglages Nickel testée | Probe du MCU, nœud effectif, lumière/gradation/extinction et reprise |

Il n'est plus nécessaire de supposer Nickel pour ces trois fonctions. Il est encore nécessaire de les tester sur la vraie Aura HD avant de qualifier une image bootable. Le lot séparé est une proposition et une preuve de correction locale ; il n'autorise aucune écriture physique et ne transforme pas le rapport expérimental en contrat recovery.

Pour rejouer le test amont local : fournir `PMKB_AUDIT_KOREADER_ROOT` (racine du paquet Kobo Q déjà vérifié) et `PMKB_AUDIT_LUAJIT` (LuaJIT natif du PC), puis lancer `python -m unittest discover -s tests -p test_offline_audit.py -v`. Le test refuse les quatre sources si leurs SHA diffèrent. Il n'initialise aucun matériel. Sans ces variables, la CI exécute le contrôle statique du lot et marque le test amont comme ignoré ; le résultat local complet doit être conservé séparément.

Le contrôle ABI ARM peut être activé avec `PMKB_AUDIT_QEMU_ARM` (QEMU user-mode) en conservant PMKB_AUDIT_KOREADER_ROOT vers le runtime ARM du prototype lu uniquement. Il vérifie le SHA du header Q et utilise ce LuaJIT ARM avec son runtime, sans Device:init. Les trois tests du lot ont été exécutés localement dans un espace réseau isolé. La suite complète doit tourner dans l'environnement Debian habituel : placer ses tests fakeroot existants dans un nouveau namespace utilisateur a provoqué huit échecs de construction synthétique ; leur rejeu hors de ce namespace a réussi.
