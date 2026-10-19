# PMKB — chantier noyau ouvert et autonomie (14 octobre 2026)

**Statut : étude et outillage hôte V0. Aucune optimisation physique démontrée.** Ce lot ne modifie ni FIRST BOOT, ni Linux, U-Boot, recovery, rcS, P1/P2/P3, les images ou les pilotes en service. Aucune écriture sur microSD interne ou de test n'est autorisée.

## Ambition

Faire de l'Aura HD E606C0 une liseuse ouverte, maintenable, sobre et réellement efficace énergétiquement. **Un noyau plus récent n'est pas en soi une preuve de gain d'autonomie.** Le portage peut perdre les fonctions E-Ink, réveil et MCU ; comparer des mesures avant de décider.

## Point de départ vérifié sur sources et sauvegardes

- Plateforme dragon, PCB E606C0, i.MX507 Cortex-A8, 512 Mio ; écran EPDC 1080 x 1440, tactile ZForce v2 et frontlight via ntx_io / MSP430. Voir [matériel](hardware-fr.md) et [audit matériel](offline-hardware-qualification-fr.md).
- Noyau sauvegardé Linux 2.6.35.3-850-gbc67621+ (28 mars 2013). Les pilotes FB_MXC_EINK_PANEL, TOUCHSCREEN_ZFORCE, INPUT_EVDEV et PMIC MC13892 sont compilés selon son IKCONFIG. Leur fonctionnement sur le futur boot PMKB n'est pas qualifié.
- U-Boot/Netronix transmettent HWCONFIG et données waveform à l'EPDC via mémoire réservée. Ni firmware libre alternatif ni équivalence avec un pilote DRM moderne ne sont démontrés.
- Un relevé tiers d'E606C0 évoque Wi-Fi WC121A2, capteur de mouvement et batterie 1500 mAh : https://phj.hu/auraHD/ . À traiter comme **hypothèses à vérifier sur l'exemplaire**, pas comme éléments déjà qualifiés.
- Inconnus : vraie profondeur de veille, horloges/rails, protocole de reprise, watchdog, autonomie de la batterie vieillissante, version MCU, effet Wi-Fi, mesures de puissance.

## Deux voies parallèles

| Voie | Développement permis maintenant | Condition d'essai physique |
| --- | --- | --- |
| **A : noyau préservé** (2.6.35.3) | PMKB-HAL léger au-dessus des interfaces existantes ; inventaire, simulation, état radio, logique de luminosité et de rafraîchissement | Comparaison sur carte de test qualifiée, pas de changement P2 |
| **B : noyau moderne expérimental** | Recherche source, matrice drivers/boot, compilation croisée et preuves binaires hors appareil | Chaîne de récupération indépendante, console, compatibilité vérifiée et autorisation explicite avant carte de test |

La fiche postmarketOS [Kobo Aura](https://wiki.postmarketos.org/wiki/Kobo_Aura_%28kobo-aura%29) concerne **l'Aura 6 pouces, différente de l'Aura HD**. Son échec de portage ne prouve rien directement sur notre PCB mais illustre la difficulté des noyaux 2.6 anciens. Le [guide de portage KOReader](https://github.com/koreader/koreader/blob/master/doc/Porting.md) décrit les interfaces MXCFB/evdev. Le [fil KOReader/postmarketOS](https://github.com/koreader/koreader/issues/12226) traite de Kobo plus récents et du choix fbdev/DRM ; aucune compatibilité automatique avec EPDC i.MX50. [FBInk](https://github.com/NiLuJe/FBInk) est une piste d'interface framebuffer à étudier ; licence GPLv3+ à respecter.

## Gates pour envisager un portage noyau

1. Préserver les sauvegardes et SHA pré-P1, P1 et P2, HWCONFIG, waveform ; ne jamais publier des blobs privés ou propriétaires.
2. Identifier la chaîne U-Boot réelle, le machine ID, les ATAG, les possibilités DTB, la mémoire réservée waveform et les dépendances init/kernel : aucun numéro de version LTS choisi avant cet inventaire.
3. Évaluer et porter séparément EPDC/waveform, input ZForce et boutons, NTX/MSP430, SD, PMIC/batterie, Wi-Fi, USB, veille et watchdog. Source GPL ≠ disponibilité d'un firmware redistribuable.
4. Construire hors matériel, enregistrer toolchain, configs, patches, checksums, tailles et dépendances ; QEMU user-mode ne peut pas qualifier les contrôleurs physiques.
5. Définir un diagnostic de boot sans écran et une récupération hors de P2, sans ouvrir /dev/watchdog ou envoyer des ioctls à l'aveugle.
6. Avant une écriture sur **microSD vierge distincte**, obtenir autorisation explicite pour l'action précise et revérifier identification, capacité, rollback et sauvegardes. La microSD d'origine est hors limites.
7. Après accord seulement, qualifier visuellement E-Ink, tactile, éclairage, batterie, veille/réveil et stabilité ; rejeter un candidat qui régresse même s'il est plus récent.

## Contrat de mesure d'énergie

Mesurer des scénarios identiques : reading_idle, page_turn, frontlight, wifi, suspend. Tenir constants ouvrage, activité, intensité, radio, température et méthode d'instrumentation. La consommation à l'entrée USB en charge ne remplace pas une mesure de **décharge batterie**. Une mesure en série sur une batterie Li-ion demande équipement et compétence adaptés. La capacité utile réelle doit être mesurée avant toute projection d'autonomie.

Le module [PowerLab V0](../experimental/power-lab/README.md) intègre **hors matériel**, par méthode trapézoïdale, des séries tension/courant de décharge en mWh et mAh, puis calcule une différence arithmétique de puissance moyenne entre essais déclarés comparables. Provenances acceptées : synthetic et user_entered. Le calcul n'authentifie jamais les entrées ; ses sorties conservent hardware_verified=false, measurements_authenticated=false et energy_saving_verified=false. Aucune collecte réelle, lecture /sys ou /dev, ioctl, réseau, GPIO, shell, manipulation de fréquence ou de lumière. Pas de prédiction de « semaines d'autonomie ».

Exemple **entièrement synthétique** : 4 000 mV * 100 mA pendant 3 600 secondes = 400 mWh et 400 mW moyens. Ce n'est pas une mesure de la Kobo.

## Étapes suivantes

- **V0 (ce lot)** : code de calcul/validation énergétique, tests de non-I/O, doctrine noyau et garde-fous.
- **V0.1** : contrats PMKB-HAL simulés pour écran, tactile, lumière et énergie, en réutilisant le validateur sysfs existant sans confondre métadonnées et état matériel.
- **V0.2** : relever les dépendances, structurer des expériences comparables et caractériser l'énergie une fois le matériel qualifié.
- **V1 expérimental** : candidat noyau alternatif construit et audité séparément ; aucun remplacement physique sans démonstration et accord.

Aucune action implicite sur les PR #7, #25, #26 et #27. Aucune écriture P1/P2/P3, aucun chargement de pilote, aucune reprogrammation Neonode/MSP430, aucune modification watchdog.
