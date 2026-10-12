# Prototype autonome hors ligne — Aura HD E606C0

Direction validée le 3 octobre 2026 : remplacer l'environnement utilisateur Kobo par KOReader, sans compte, portail d'activation ou services Kobo. L'autorisation de restauration physique reste retirée. La préparation se fait uniquement dans de nouveaux fichiers locaux.

## Périmètre du premier prototype

- Conserver pour l'instant U-Boot, le noyau, HWCONFIG et les données E-Ink propres à la carte. Ce n'est pas encore une pile entièrement reconstruite depuis les sources ni une certification de liberté de tous les composants matériels.
- Créer un rootfs distinct avec BusyBox, les bibliothèques GNU nécessaires et le paquet officiel `koreader-kobo` v2026.07.1. Les composants GNU compatibles proviennent d'une liste explicite dans la mise à jour présente dans la sauvegarde privée ; cette mise à jour n'est jamais appliquée intégralement.
- Remplacer l'init par les sources de `experimental/offline-rootfs`. Aucun Nickel, Hindenburg, watchdog applicatif Kobo, script de mise à jour Kobo ou lanceur retournant vers Nickel n'est installé dans le prototype.
- Ne pas inclure de modules Wi-Fi ou de règles de chargement automatique. Refuser de lancer le lecteur si `/sys/class/net` n'existe pas, si `lo` manque ou si une autre interface est présente. Ce contrôle n'est pas une preuve absolue d'absence de communications du noyau ou du matériel.
- Monter P3 en lecture seule ; ne pas lancer de réparation FAT, traitement de `KoboRoot.tgz`, formatage ou changement de partitions. Les réglages et caches sont temporaires dans `/tmp`.
- Lancer directement `luajit reader.lua`, sans le lanceur Kobo habituel. Aucun redémarrage, retour à Nickel ou retry automatique n'est défini par l'init expérimental à la sortie du lecteur.

Le firmware inspecté contient une archive `KoboRoot.tgz` en attente qui changerait le système au démarrage d'origine. La conserver sur P3 ne présente pas la même sémantique : le nouvel init n'interprète jamais cette archive. Le simple fait de conserver une base utilisateur ne garantit pas une activation valide ; le prototype ne dépend pas de cette activation.

## État de validation et limites

L'[audit statique du matériel](offline-hardware-audit-fr.md) précise les écarts identifiés avant tout essai : éclairage NTX, préparation du framebuffer, réglages Nickel encore actifs dans le paquet KOReader et différences entre cold-plug et udev. Cet audit ne modifie pas l'image expérimentale existante.

BusyBox et LuaJIT ARM ont été exécutés sous QEMU user-mode, dans un espace réseau isolé ; les 36 bibliothèques ELF fournies dans `koreader/libs` se chargent avec le runtime choisi. Ce test utilise le noyau du PC, pas celui de l'Aura HD. Les tests synthétiques vérifient le refus des interfaces inconnues et la syntaxe des scripts sans exécuter les commandes matérielles.

L'image locale de développement est contrôlée avec `e2fsck -f -n`. Son rapport est marqué `experimental`, `complete=false`, `physical_restore_eligible=false` et porte un nom de tool distinct. Ce rapport n'est pas un rapport de reconstruction recovery et ne doit jamais être présenté au pipeline existant comme une reconstruction qualifiée.

Restent non qualifiés : démarrage matériel, création des nœuds de périphériques par cold-plug, initialisation/rotation/rafraîchissement E-Ink, tactile, éclairage, batterie, veille, alimentation, watchdog du noyau et USB. Les règles cold-plug ne gèrent pas encore le branchement à chaud. Les réglages ne persistent pas. Une panne peut donc empêcher le lecteur de démarrer ; aucune promesse de démarrage ou de zéro trafic sur matériel réel n'est faite.

Avant tout essai matériel, examiner séparément la nouvelle image, établir un contrat de validation et un retour arrière adaptés, et obtenir une nouvelle autorisation physique. Les anciens rapports de reconstruction et de simulation ne qualifient pas cette image différente. Aucun dump, archive Kobo ou binaire privé ne doit être ajouté au dépôt.

## Références de conception

- [Sources et paquet officiel KOReader v2026.07.1](https://github.com/koreader/koreader/releases/tag/v2026.07.1).
- [Support `dragon` dans KOReader](https://github.com/koreader/koreader/blob/v2026.07.1/frontend/device/kobo/device.lua).
- [Lanceur Kobo de référence](https://github.com/koreader/koreader/blob/v2026.07.1/platform/kobo/koreader.sh), à distinguer du démarrage autonome.
- [okreader](https://github.com/lgeek/okreader) sert de référence historique ; son README ne qualifie pas l'Aura HD comme une cible prête à installer.
