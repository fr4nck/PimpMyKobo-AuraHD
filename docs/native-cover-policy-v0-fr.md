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
