# PMKB — Contrat de démarrage de l'Aura HD E606C0

**Audit documentaire, 15 octobre 2026.** État : informations recoupées dans les documents PMKB, sans compilation nouvelle et sans essai sur l'appareil. Aucune écriture sur P1/P2/P3 ni sur les images FIRST BOOT.

## Carte de la zone pré-P1 observée

| Offset de la copie étudiée | Élément documenté | Limites |
| --- | --- | --- |
| 524 288 octets (0x80000) | HWCONFIG Netronix v1.7 ; `bPCB=28` désigne E606C0 / dragon | Ne pas généraliser ces offsets sans contrôle du support |
| 1 048 576 octets (0x100000) | `uImage` historique : CRC de l'en-tête et du contenu vérifiés ; Linux `2.6.35.3-850-gbc67621+` | L'exacte reproductibilité binaire depuis les sources n'est pas prouvée |
| Secteur 14 336 = 7 340 032 octets (0x700000) | En-tête Netronix `ff f5 af ff` et waveform du panneau E-Ink ; taille du blob extrait : 1 158 319 octets | Vérification de l'intégrité, pas validation électrique ni licence libre |
| 9 961 472 octets | Début de P1 / rootfs dans le partitionnement observé | La zone précédente reste critique pour le démarrage |

L'emplacement, la version et les fonctions exactes du tout premier code exécuté par la Boot ROM, ainsi que l'identité binaire de l'U-Boot réellement utilisé, ne sont **pas** établis de bout en bout par ce tableau. Ne pas confondre copie de sauvegarde et support d'origine défaillant.

## Contrat U-Boot / Linux historique

- Le HWCONFIG de l'Aura HD porte `bPCB=28`. Les routines Netronix analysées effectuent un remappage interne vers la valeur `11`. **Ce 11 n'est pas identifié ici comme le machine ID ARM** : le machine ID réel reste à vérifier.
- Les sources U-Boot Netronix examinées décrivent le chargement de la configuration matérielle et de la waveform en mémoire, avec transmission des paramètres noyau `hwcfg_p`, `hwcfg_sz`, `waveform_p` et `waveform_sz`.
- Le pilote E-Ink historique utilise la branche `FW_IN_RAM` : il obtient la waveform déjà présente en mémoire ; l'initialisation du panneau n'exige pas, sur ce chemin étudié, que Nickel soit lancé.
- Les adresses RAM concrètes transmises, leur alignement, leur réservation vis-à-vis du nouveau noyau, les paramètres de chargement `uImage`, le machine ID et le contenu des ATAG ne sont pas encore qualifiés.
- La présence de `/dev/fb0` seule ne prouve pas que le matériel est prêt : la phase d'initialisation EPDC peut ne pas être achevée (`hw_ready`).

## Obstacles à résoudre avant de choisir un noyau moderne

| Blocage | Vérification hors matériel attendue |
| --- | --- |
| Boot ROM / premier chargeur / U-Boot en service | Comparer en lecture seule sauvegardes privées, en-têtes et sources, sans publier de blobs |
| Point d'entrée du noyau, adresses, machine ID, ATAGs | Décoder le noyau et auditer U-Boot, produire des valeurs vérifiables |
| Passage à Device Tree (DTB) | Déterminer si le bootloader conservé peut transmettre un DTB ou si un mécanisme de transition est nécessaire |
| Waveform et HWCONFIG en RAM | Spécifier le contrat de réservation mémoire, vérifier les chevauchements |
| EPDC / framebuffer MXCFB | Identifier les interfaces à maintenir/porter et leurs dépendances |
| ZForce, NTX/MSP430, PMIC MC13892, microSD, Wi-Fi, USB | Matrice de pilotes et de dépendances source par source |
| Watchdogs et reprise | Analyser sans ouvrir `/dev/watchdog`, sans ioctl matériel de test et sans présumer d'un compteur désactivé |
| Démarrage sans affichage et retour arrière | Préparer un diagnostic et une récupération réellement indépendants de P2 |

La source historique montre que `mxc_wdt_disable` est vide ; la déclaration du périphérique watchdog est commentée sur la plateforme étudiée. Cela ne démontre ni que le compteur est actif ni qu'il est arrêté. **Ne pas activer de service watchdog à l'aveugle.**

## Décision et ordre d'exécution

1. Conserver noyau Linux 2.6.35.3 et chaîne actuelle comme référence pour qualifier FIRST BOOT avec KOReader.
2. Effectuer un audit **lecture seule** du binaire `uImage`, du bootloader et des paramètres de boot issus des copies privées préservées.
3. Définir le contrat précis machine ID / ATAG / DTB et les régions mémoire HWCONFIG / waveform.
4. Étudier ensuite la compatibilité d'un noyau moderne sur i.MX50. Linux 6.18 est **une hypothèse à comparer, pas un choix validé**.
5. Produire hors machine une matrice pilotes et des tests de cohérence ; ne compiler ou flasher un candidat physique qu'après des critères de récupération explicites.
6. Comparer les consommations réelles seulement une fois le démarrage stable et la mesure possible ; aucun gain énergétique n'est acquis aujourd'hui.

**Exclus du lot :** aucun patch de noyau, aucune commande sur la Kobo, aucun accès à GPIO/I²C/`/dev`, aucun changement U-Boot, `rcS`, P1/P2/P3 ou images FIRST BOOT, aucun firmware propriétaire publié.

## Références PMKB

- [Identification E606C0](hardware-fr.md)
- [HWCONFIG v1.7](hwconfig-fr.md)
- [Partitionnement observé](partition-layout-fr.md)
- [Audit pilotes et boot Netronix](offline-hardware-qualification-fr.md)
- [Audit prérequis FIRST BOOT et watchdog](offline-boot-gates-fr.md)
- [PowerLab V0 : noyau et autonomie](kernel-energy-roadmap-fr.md)

## Jalonnement BOOT CONTRACT V1 (18 octobre 2026)

Le contrat documentaire, la table de réservations et le verdict conditionnel sont consignés dans [BOOT CONTRACT V1](boot-contract-v1-fr.md). La [matrice Linux 6.18](kernel-driver-matrix-v1-fr.md) et la [passation d'audit indépendant](claude-boot-contract-v1-handoff-fr.md) complètent ce jalon. Les adresses RAM, r1 et r2 restent des inconnues à démontrer ; un test synthétique ne constitue pas une qualification matérielle.
