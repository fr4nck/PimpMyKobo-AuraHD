# PMKB — Wi-Fi Kobo Aura HD E606C0 : inventaire et plan de qualification

Date : 5 novembre 2026. Statut : **sources et témoignages historiques identifiés ; aucun accès matériel ni Wi-Fi PMKB qualifié**.

## Besoin utilisateur

Le Wi-Fi est une exigence de PMKB V1 : transfert de livres sans câble USB, pilotage depuis PMKB et récupération depuis Calibre. La lecture hors connexion doit rester possible et le coût RAM/énergie doit être mesuré. Le défaut de prise micro-USB constaté sur l'exemplaire rend la voie sans fil prioritaire.

## Sources et faits (ne pas confondre modèles)

- **Aura HD N204 / E606C0** : un relevé matériel indépendant donne `Wifi: WC121A2` et décrit un module WLAN CyberTan WC121 sur la carte. Référence : https://phj.hu/auraHD/ . Ce relevé concerne une Aura HD, **pas une preuve sur notre carte précise**.
- **Aura HD** : un utilisateur documente le chargement de `/drivers/ntx508/wifi/sdio_wifi_pwr.ko` puis de `/drivers/ntx508/wifi/dhd.ko`, une interface `eth0`, `wpa_supplicant` et `udhcpc` pour transférer une image par Wi-Fi. Référence : https://www.mobileread.com/forums/showthread.php?t=212474&page=3 . C'est un **témoignage de fonctionnement historique**, pas un script PMKB prêt à exécuter.
- **Sources officielles du noyau Aura HD** : https://github.com/kobolabs/Kobo-Reader/tree/master/hw/imx507-aurahd/ (archive `linux-2.6.35.3.tar.gz`).
- **Source Broadcom DHD publiée séparément** dans les sources Kobo : https://github.com/kobolabs/Kobo-Reader/blob/master/hw/imx508/ntx/bcm-dhd-falcon-5901132-03112011.tgz . **Ne pas présumer que cette archive produit à l'identique le `dhd.ko` de l'Aura HD** : version, correctifs, ABI et firmware doivent être rapprochés.
- **Écueil réel** : issue https://github.com/kobolabs/Kobo-Reader/issues/105 ; `dhd.ko` et `sdio_wifi_pwr.ko` peuvent être chargés sans que le Wi-Fi fonctionne, notamment si les firmwares d'origine manquent.
- **Comparateur non interchangeable** : la Kobo Aura **N514/E606F0B** comporte un WC121/BCM43362 selon son DTS, mais ce DTS et son matériel ne qualifient pas la **Aura HD E606C0**. Ne pas copier de paramètres SDIO, GPIO, alimentation ou firmware d'une autre révision.

## État du dépôt PMKB au 5 novembre 2026

- `experimental/offline-rootfs/usr/bin/pmkb-check-offline` n'autorise que `lo`.
- `experimental/offline-rootfs/etc/init.d/rcS` ne prévoit ni chargeur de firmware, ni démarrage Wi-Fi ; P3 est montée en lecture seule.
- `experimental/power-lab/network_sleep_contract.py` et les tests associés simulent des décisions de politique et **ne commandent aucun composant**.
- Aucun transfert Wi-Fi PMKB ni association WPA sur E606C0 ne sont attestés.

## Ordre de travail concret

1. **Après clonage et essai de démarrage du clone**, conserver la microSD originale et la sauvegarde hors de toute écriture PMKB. Toute modification physique ultérieure doit être précisément ciblée et autorisée séparément.
2. **Inventaire en lecture seule du rootfs d'origine et/ou de la sauvegarde** : présence, tailles et SHA-256 de `drivers/ntx508/wifi/sdio_wifi_pwr.ko`, `drivers/ntx508/wifi/dhd.ko` et firmwares associés (`lib/firmware`, éventuels chemins de firmware prévus par le module) ; vérifier les scripts de chargement et `uname -r` de la version embarquée. Ne pas supposer que des noms identiques signifient ABI compatible.
3. **Contrôle de compatibilité** : architecture ELF ARM, dépendances des modules, `vermagic` si disponible, noyau effectivement conservé et mécanisme d'alimentation SDIO ; identifier les firmwares exacts. Ne pas distribuer de blobs propriétaires.
4. **Conception PMKB CONNECTED** distincte du chemin OFFLINE fonctionnel : activation du Wi-Fi à la demande, association WPA, DHCP, extinction effective radio, désactivation des services réseau lors de la lecture si souhaité. Ne pas neutraliser le contrôle hors ligne actuel avant tests dédiés.
5. **Transfert de fichiers** : répertoire de livres sur P3, protocole authentifié (SFTP avec serveur réellement disponible, ou alternative explicitement validée), transferts atomiques et réindexation KOReader. Garder un seul propriétaire du stockage ; éviter l'export USB mass-storage simultané.
6. **Critères terrain** : association et transfert de livre, reprise après veille, bouton lumière et tactile, consommation au repos, absence de connexion au démarrage non sollicitée, restauration du fonctionnement hors ligne.

## Refus et limites

**Aucune écriture sur PRE-P1, P2 ou la microSD originale ; aucun téléchargement automatique, aucune manipulation du pilote ou du firmware à l'aveugle.** Un nom de module, la présence de `eth0` ou un test hôte ne prouvent pas une connexion effective. Aucun statut PASS matériel ne doit être annoncé avant les essais réels.
