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
