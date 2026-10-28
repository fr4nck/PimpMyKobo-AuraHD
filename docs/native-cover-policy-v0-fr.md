# PMKB — housse magnétique : politique hôte V0 (28 octobre 2026)

**État : code C11 hôte uniquement, qualification matérielle non commencée.**
L'Aura HD N204/E606C0 expose un capteur Hall TLE4913 dans son HWCONFIG historique. La relation précise capteur → GPIO/IRQ → evdev → gestionnaire de veille n'est pas encore démontrée sur notre exemplaire. L'utilisateur rapporte des réveils parfois impossibles sans brancher l'USB : il s'agit d'un symptôme, **pas** d'une preuve de panne du capteur Hall.

## Contrat C11 livré

- Le module PMKB-HAL contient **PMKBPowerPolicy**, qui démarre avec cover_enabled=false.
- Les événements sémantiques COVER_CLOSED/COVER_OPENED sont ignorés quand le réglage est OFF. En mode ON, seule une transition de niveau est transmise ; une rafale de niveaux identiques n'est pas relayée.
- Les événements BUTTON_PRESSED et BUTTON_RELEASED restent toujours transmis, quelle que soit la configuration de la housse. Le module n'exécute pas la veille : il autorise ou refuse uniquement la transmission de l'événement à un futur gestionnaire d'alimentation.
- Changer le réglage ne rejoue pas la dernière position de l'aimant (aucune mise en veille surprise à l'activation).
- Le réglage peut être sérialisé et relu comme **octets de configuration exacts** : pmkb-cover-v1 suivi de magnetic_cover=off ou magnetic_cover=on, avec fin de ligne. Erreurs de format, version inconnue et troncature sont refusées avant toute mutation ; aucun chemin d'écriture n'est introduit.
- Trois booléens embarqués, pas de heap, threads, boucle, timer, service permanent, ioctl, montage, sysfs ni accès réseau.

Les valeurs COVER_* sont **déjà classifiées par leur source**. Un futur adaptateur doit valider le périphérique et ses capacités avant de traduire des codes evdev. **Ne jamais traiter tous les KEY_F1 / code 59 comme un capteur Hall** : il pourrait s'agir d'un clavier externe. Le code 116 du bouton Power, utilisé par KOReader sur Kobo, n'est pas réécrit ici.

## Contrats distincts et inconnues

1. **KOReader en FIRST BOOT** : son réglage existant ignore_power_sleepcover=true permet d'ignorer les événements de housse. Il est à configurer et à vérifier dans le runtime réel, indépendamment du module C11. Ne pas confondre les paramètres persistants du lecteur avec defaults.custom.lua ni supprimer un réglage utilisateur préexistant. Source : https://github.com/koreader/koreader/blob/master/frontend/ui/elements/common_settings_menu_table.lua .
2. **Raccordement PMKB natif** : créer ultérieurement un adaptateur evdev qualifié (identité + capacités), une option Réglages et un stockage persistant qualifié hors P1/P2. Le format sérialisé V0 ne constitue pas une sauvegarde P3.
3. **Noyau et veille** : ignorer un événement en userspace **n'empêche pas** le noyau, le PMIC ou le MCU de réveiller le système via une IRQ. Le masquage éventuel du wakeup GPIO exige une revue séparée, sans perdre le bouton physique ni les autres sources de réveil.
4. **Diagnostic matériel** : reproduire plusieurs cycles avec/sans housse, en veille longue, au bouton, puis relever cause de réveil, batterie, alimentation USB et consommation. Ne pas attribuer le défaut au Hall sans preuves.
5. **Qualification** : premiers tests synthétiques HAL, puis compilation ARM et recette physique avec autorisation sur carte de test séparée. Aucun test C11 n'autorise une modification des partitions physiques.

## Vérification hôte

Dans le dépôt : make -C experimental/native-ui test ; le test cover_policy_contract appartient à pmkb-hal-tests. La CI Native PMKB UI (GCC, ASan/UBSan) est requise sur la PR. Le code ne modifie ni FIRST BOOT, ni P1/P2/P3, ni firmware, ni microSD.


## Audit du code Hall E606C0 et traducteur evdev — 28 octobre 2026

Sources publiques historiques de la branche pazos/linux-2.6.35.3-kobo, commit 1f43a4a01a727a9b440f2e8830b67734b6373a10 :

- [Pilote TLE4913](https://github.com/pazos/linux-2.6.35.3-kobo/blob/1f43a4a01a727a9b440f2e8830b67734b6373a10/drivers/input/keyboard/tle4913_keypad.c) : GPIO_5_25, pad SD3_D5, IRQ montante/descendante, iWakeup=1, anti-rebond 1 tick ; KEY_F1=59 si interface client, KEY_H=35 sinon. Niveau bas = pressé / housse fermée, niveau haut = relâché / ouverte. Enregistrement conditionnel à bHallSensor==1.
- [gpiofn.c](https://github.com/pazos/linux-2.6.35.3-kobo/blob/1f43a4a01a727a9b440f2e8830b67734b6373a10/drivers/input/keyboard/gpiofn.c) : gpiofn_register appelle enable_irq_wake sur une IRQ marquée iWakeup=1.
- [mx50_ntx_io.c](https://github.com/pazos/linux-2.6.35.3-kobo/blob/1f43a4a01a727a9b440f2e8830b67734b6373a10/arch/arm/mach-mx5/mx50_ntx_io.c) : distribution des touches via gpio-keys ou matrice selon bPCB_Flags ; bouton d'alimentation indépendant, KEY_POWER=116.
- [KOReader v2026.07.1](https://github.com/koreader/koreader/blob/v2026.07.1/frontend/device/kobo/device.lua) mappe 35/59 à SleepCover et 116 à Power. Son filtrage utilisateur ne neutralise pas l'interruption wake du noyau.

Le nouveau PMKBPowerEvdev init/feed décode des trames EV_KEY **seulement si** un adaptateur extérieur a déjà qualifié la source NTX (ce projet ne possède pas encore cet adaptateur réel). Le code Hall est choisi explicitement : KEY_H **ou** KEY_F1, jamais les deux simultanément pour un profil donné. Une entrée clavier externe est refusée ; KEY_POWER reste relayé indépendamment du réglage. Les répétitions de touche value=2 sont ignorées, les doublons de niveau sont filtrés, et SYN_DROPPED entraîne un retour à un niveau connu sans produire de faux réveil. Un bouton Power fonctionnel est relayé après SYN_REPORT, sans attendre le changement d'état du Hall.

**Limites strictes** : ce module reste un décodeur de trames synthétiques ; l'identification de périphérique par nom et capacités, la liaison à un gestionnaire de veille natif, la gestion des IRQ réelles, la persistance P3 et la recette avec/sans USB restent à qualifier. Ne pas désactiver l'IRQ Hall ou retirer le capteur sur la base de cette seule analyse ; aucune preuve de panne matérielle n'a été établie.


## Inventaire des entrées mxckpd : profil candidat V0 (28 octobre 2026)

**Résultat :** le nom de périphérique mxckpd apparaît dans deux chemins historiques distincts, pas dans un pilote Hall autonome : drivers/input/keyboard/gpio_keys.c attribue input->name=pdev->name (mxckpd via mx50_ntx_io.c) ; drivers/input/keyboard/mxc_keyb.c fixe aussi le nom mxckpd. Le choix historique est conditionné par bPCB_Flags (mode sans matrice ou matriciel) ; ce drapeau réel et les capacités disponibles sur notre exemplaire doivent être relevés. La désignation /dev/input/eventN est dynamique.

Dans le noyau historique :
- Le chemin gpio-keys annonce BUS_HOST=0x19, KEY_POWER, KEY_F1 et KEY_H dans sa liste de capacités. Référence : [gpio_keys.c](https://github.com/pazos/linux-2.6.35.3-kobo/blob/1f43a4a01a727a9b440f2e8830b67734b6373a10/drivers/input/keyboard/gpio_keys.c).
- Le chemin matriciel annonce BUS_HOST, KEY_F1 via NTX_KEY_CODE_ARRAY et les touches de sa matrice. Il ne garantit pas que KEY_H et KEY_POWER figurent dans le bitset exporté, malgré l'existence de ntx_report_key(KEY_POWER) dans l'autre module. Référence : [mxc_keyb.c](https://github.com/pazos/linux-2.6.35.3-kobo/blob/1f43a4a01a727a9b440f2e8830b67734b6373a10/drivers/input/keyboard/mxc_keyb.c).
- Un événement KEY_F1 ou la simple présence de mxckpd ne prouve ni la présence réelle du Hall sur la carte test, ni sa liaison, ni une panne : d'autres touches ou claviers pourraient partager ces codes.

**Nouvelle API C11** pmkb_power_probe_inputs : accepte un petit inventaire préalablement obtenu par un futur adaptateur, sans ouverture de périphérique et sans allocation. Pour chaque source, elle examine nom mxckpd, bus hôte, EV_KEY et capacité KEY_F1 ou KEY_H. Elle renvoie CANDIDATE pour une seule source plausible, NONE pour aucune, AMBIGUOUS pour plusieurs, INVALID si l'appel est incorrect. Elle ne décide jamais quel code est celui du Hall, ne renvoie aucun statut SOURCE_NTX_VERIFIED et ne lie pas l'entrée au décodeur. L'index retourné est la position dans l'inventaire fourni, pas un numéro eventN.

**Porte suivante (non franchie)** : identifier la source en lecture seule (/sys/class/input/event*/device/name, capacités et identité EVIOCGID/EVIOCGNAME), démontrer par un relevé contrôlé l'association capteur/événements, choisir 59 ou 35, puis vérifier le bouton physique indépendant. Le nom et les capacités, même cohérents, restent des indices ; tant que ces preuves ne sont pas présentes, la liaison native est refusée.

## Réveil Hall au niveau du noyau : décision préparatoire (aucun patch appliqué)

Les sources historiques font enregistrer le GPIO 5_25 (Hall) sur les deux fronts avec iWakeup=1 ; gpiofn_register applique enable_irq_wake() pour ce drapeau. L'interrupteur physique est sur un autre chemin, GPIO 4_10, avec IRQ de réveil dédiée selon la configuration historique ; le MSP430 peut également participer à la reprise. KEY_F1 et KEY_POWER partagent possiblement le périphérique input mxckpd, donc désactiver entièrement ce périphérique, saisir EVIOCGRAB ou ignorer tout son flux ferait perdre le bouton.

**Candidate pour une modification de noyau futur, pas pour installation :** ne retirer que la capacité de réveil de l'IRQ déclarée par gtTLE4913_GPIO_data, en préservant son enregistrement/anti-rebond et la publication des événements lorsque la machine est éveillée. Dans cette famille de sources, la variation de .iWakeup dans le pilote Hall est le point de sélection le plus localisé ; vérifier la sémantique exacte de la branche utilisée, les retours enable_irq_wake/disable_irq_wake, et l'état d'activation initial avant de proposer une valeur de remplacement. Ne jamais appliquer un disable_irq, un gpio_free, un unbind de mxckpd ou une modification de GPIO_4_10 pour atteindre cet objectif.

**Gates pour toute recette :** source et binaire du noyau effectivement exécuté correspondants, IRQ/GPIO observés en lecture seule, sauvetage et carte test indépendante, comparaison répétée avec et sans capot aimanté, vérification Power/USB/charge et absence de boucle suspend/resume, preuve que les autres sources wake ne régressent pas. La suppression de wake dans un BSP ne prouve pas la résolution de l'incident original. Aucune modification du firmware, des blobs ou des partitions n'est autorisée ici.
