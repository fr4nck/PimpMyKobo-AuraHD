# Audit statique du prototype Aura HD — 3 octobre 2026

Cet audit porte sur les sources du paquet officiel KOReader `v2026.07.1`, les scripts de démarrage extraits des sauvegardes locales et l'init expérimental du dépôt. Aucun script matériel n'a été exécuté, aucun périphérique physique ouvert et aucune image modifiée. Ce document ne qualifie ni le démarrage ni une restauration.

L'[audit approfondi des sources Netronix et de la recovery](offline-hardware-qualification-fr.md) complète ce premier relevé : configuration extraite du vrai noyau sauvegardé, chaîne waveform en RAM, activation ZForce, ioctl NTX et preuve de correction des réglages Nickel. Le prototype reste inchangé.

## Résultat

Le support logiciel `dragon` existe dans KOReader, mais cela ne prouve pas qu'un rootfs autonome initialise correctement une Aura HD. Le lancement direct contourne des préparations du lanceur de référence. Le prototype actuel doit conserver son statut expérimental.

| Fonction | Observation vérifiée dans les sources | Écart restant |
| --- | --- | --- |
| Écran E-Ink | `KoboDragon` utilise le backend MXCFB ; le lanceur lit la rotation et la profondeur du framebuffer puis prévoit une préparation avec `fbdepth`. | Notre init vérifie seulement le type caractère de `/dev/fb0`. Présence du pilote, profondeur, rotation, dimensions et ioctls de rafraîchissement non qualifiés. La préparation du lanceur ne doit pas être copiée aveuglément. |
| Boutons et tactile | Les chemins de repli sont `/dev/input/event0` et `event1`. KOReader essaie aussi une détection des périphériques d'entrée ; `dragon` déclare un tactile sans multitouch. | Notre init exige ces deux indices sans vérifier leurs identités. Le cold-plug ne déclenche pas les événements udev, ne charge pas de modules et ne gère pas les apparitions tardives. |
| Éclairage | Pour ce modèle sans lumière naturelle, `powerd.lua` utilise `ffi/kobolight.lua`, qui ouvre `/dev/ntx_io` et pilote l'éclairage par ioctl. | `/dev/ntx_io` n'est pas une condition de lancement dans notre init. Son exposition dans sysfs, sa création et les ioctls doivent être qualifiés ; aucun numéro majeur/mineur ne doit être inventé. |
| Réglages hérités | `defaults.lua` contient `KOBO_LIGHT_ON_START = -2` et `KOBO_SYNC_BRIGHTNESS_WITH_NICKEL = true`. `powerd.lua` peut lire et tenter de modifier `Kobo eReader.conf`. | Désactiver explicitement ces deux dépendances dans la prochaine préparation du profil. `KO_MULTIUSER=1` ne suffit pas à désactiver ces chemins. P3 en lecture seule empêche les écritures réussies, sans démontrer que les erreurs sont inoffensives. |
| Batterie | Le chemin hérité est `/sys/class/power_supply/mc13892_bat`, avec lecture de `capacity` et `status`. | Existence et valeurs du pilote réel non vérifiées. Un chargement réussi des bibliothèques ne valide pas la mesure de batterie. |
| Veille et réveil | Le code écrit notamment dans `/sys/power/state` et `state-extended` et gère les alarmes RTC. | Interfaces du noyau, réveil par bouton, reprise du tactile/écran et consommation pendant la veille non qualifiés. |
| Arrêt et redémarrage | Le code Kobo de KOReader appelle des commandes système `poweroff` et `reboot`. | L'absence de retour à Nickel dans notre lanceur ne désactive pas ces fonctions internes. Comportement de BusyBox init, RTC et extinction matérielle à vérifier. |
| Réseau | Notre init ne charge pas de module Wi-Fi et refuse le lancement du lecteur avec une interface autre que `lo`. | Ce contrôle n'est ni une vérification de la configuration du noyau, ni une surveillance continue, ni une mesure radio. Il ne permet pas de certifier zéro trafic matériel. |
| USB | KOReader comporte des chemins de gestion du stockage USB et des événements de connexion. | Pas de qualification de hot-plug ou d'export de stockage. Ne pas activer l'export USB de P3 montée, même en lecture seule, avant audit dédié. |

## Différence avec le démarrage sauvegardé

Le script recovery sauvegardé prépare `/dev` avec udev, déclenche les événements puis attend leur traitement. Notre cold-plug crée seulement des nœuds pour les entrées sysfs déjà présentes. Ces mécanismes ne sont pas équivalents : une entrée sysfs absente ne peut pas être réparée par la création d'un nœud arbitraire.

Le script recovery ne génère le fichier `epdc_E60_V220.fw` que dans sa branche `freescale`, tandis que la présence de HWCONFIG sélectionne `ntx508`. Cela ne suffit pas à prouver comment le noyau exact de notre carte obtient ses données E-Ink. La configuration du noyau, les règles udev et la provenance des données utilisées par les pilotes restent à examiner sur copies locales. Le script de la mise à jour en attente n'est pas une preuve de l'état du noyau actuellement conservé.

## Ordre de travail avant un essai matériel

1. Examiner sur copies locales le noyau conservé et les règles de périphériques recovery : pilotes intégrés/modules, noms sysfs, firmware requis et watchdog. Conserver les inconnues explicitement ; ne pas déduire une configuration du seul numéro de version.
2. Préparer un nouveau profil KOReader indépendant des réglages Nickel, puis tester sur fichiers synthétiques que les anciens réglages ne sont ni lus ni écrits.
3. Qualifier la création des nœuds et les conditions de lancement avec une simulation de sysfs et des commandes factices. Aucun test ne doit exécuter l'init sur le PC.
4. Préparer séparément la stratégie framebuffer, veille/arrêt et USB à partir des résultats. Les résultats QEMU user-mode actuels couvrent uniquement le runtime ARM et les chargements de bibliothèques.
5. Définir un contrat d'essai et un retour arrière pour une carte distincte. Obtenir une nouvelle autorisation explicite avant toute écriture physique, y compris sur cette carte distincte.

L'image expérimentale existante n'a pas été corrigée par cet audit. Les anciens contrats de restauration recovery ne s'appliquent pas à elle.

## Sources examinées

- Paquet officiel `koreader-kobo-v2026.07.1.zip`, SHA-256 `0f36a62ce73b12516f969e4ad7862cc06920afb03c7bd4db29a0d990bdd84b2f`, notamment `defaults.lua`, `frontend/device/kobo/powerd.lua`, `nickel_conf.lua`, `ffi/kobolight.lua` et `framebuffer_mxcfb.lua`.
- [Support matériel KOReader au tag examiné](https://github.com/koreader/koreader/blob/v2026.07.1/frontend/device/kobo/device.lua) et [lanceur de référence](https://github.com/koreader/koreader/blob/v2026.07.1/platform/kobo/koreader.sh), disponibles aussi dans les copies locales de recherche.
- Scripts `rcS` lus dans la reconstruction recovery et dans l'archive en attente de la sauvegarde privée ; aucune archive privée ou donnée personnelle n'est publiée ici.
- Sources propres du dépôt sous `experimental/offline-rootfs`.
