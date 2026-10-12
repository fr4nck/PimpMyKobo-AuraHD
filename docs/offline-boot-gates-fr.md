# Conditions de premier démarrage autonome — audit du 12 octobre 2026

Suite de l'[audit des trois interfaces matérielles](offline-hardware-qualification-fr.md), uniquement sur sources locales. Aucun changement du prototype de démarrage, aucune image reconstruite, aucun accès à un périphérique physique. Ce document prépare les critères d'un futur essai ; il ne qualifie pas une image et n'autorise aucune écriture.

## Watchdog : correction du relevé précédent

Le relevé précédent indiquait correctement que le probe appelle `mxc_wdt_disable`, mais sans examiner assez précisément cette fonction. **Son corps est vide** et porte le commentaire « disable not supported by this chip ». L'appel ne désactive donc rien. Il ne faut pas en déduire qu'un watchdog hérité du bootloader est arrêté.

Autre distinction nécessaire : le noyau sauvegardé compile `CONFIG_MXC_WATCHDOG=y`, mais l'enregistrement du périphérique `mxc_wdt_device` est commenté dans la plateforme `mx50_rdp.c:2792`. Le `module_init` du pilote enregistre un *driver* ; il ne crée pas à lui seul le périphérique plateforme qui déclencherait son probe. Dans les sources examinées, les enregistrements actifs trouvés concernent d'autres cartes. Ni la configuration compilée ni la présence d'un fichier nommé watchdog ne suffisent à établir qu'un probe a eu lieu sur l'Aura HD.

| Chemin | Preuve locale | Conclusion et limite |
| --- | --- | --- |
| Watchdog i.MX | `drivers/watchdog/mxc_wdt.c:96–111` : enable écrit WDE, disable est vide. `open:149–159` configure, active et alimente le compteur. `release:164–179` ne l'arrête pas avec NOWAYOUT. | Ne jamais ouvrir ce nœud pour une simple vérification. Le premier open peut changer irréversiblement l'état du compteur jusqu'au reset. Aucun daemon watchdog ne doit être ajouté sur la seule base de CONFIG_WATCHDOG. |
| Enregistrement plateforme | `arch/arm/mach-mx5/mx50_rdp.c:2792` : enregistrement commenté ; `mxc_wdt.c:349–365` : platform_driver_register. | Driver compilé ≠ périphérique enregistré ≠ probe exécuté ≠ compteur actif. Le noyau binaire exact et l'état matériel hérité restent distincts de la source publiée. |
| U-Boot MX50 | `cpu/arm_cortexa8/mx50/interrupts.c:36–39` : `reset_cpu` écrit 4 au registre WDOG1. | Chemin de reset, pas preuve d'activation au démarrage normal. Ce fichier source local ne qualifie pas à lui seul tous les chemins du binaire U-Boot conservé. |
| Watchdog MSP430 | `drivers/mxc/pmic/core/pmic_core_i2c.c:56` : NEWMSP dépend de l'identifiant lu `0xe916`. `msp430_probe:584–595` lit cet identifiant et, seulement dans cette branche, envoie la commande 22/0xff annotée disable watchdog. | La version du MCU ne se déduit pas de HWCONFIG. Le retour de la commande n'est pas contrôlé par le probe : son succès ne prouve pas l'effet de désactivation. |
| Transport MCU | `msp430_cmd:439–479` peut retourner -EIO après tentatives ; `msp430_setwatchdog:851–855` ne fait rien pour les autres MCU et ne propage pas un résultat. | Ni l'existence du client I²C ni un probe déclaré réussi n'établissent la santé du MCU ou l'état de son watchdog. Aucune commande de désactivation hypothétique proposée. |
| Ouverture NTX | `mx50_ntx_io.c:564–575` : open/release ajustent Driver_Count ; la commande 205 de keep-alive est un cas ioctl distinct à 767–777. | Le chemin d'ouverture utilisé par kobolight n'exécute pas automatiquement keep-alive. Ne pas ajouter l'ioctl 205 comme prétendu correctif watchdog : son rôle est une politique d'alimentation distincte. |

Ce travail n'établit pas qu'un watchdog est actuellement actif, ni qu'un arrêt du lecteur provoquerait un reset. Il établit pourquoi un tel risque ne peut pas être exclu avec les seuls appels nommés « disable ». Au premier essai futur, les logs de boot, l'identifiant MCU si le noyau le rapporte et la stabilité sur la durée seront nécessaires. Ne pas lire des registres par `/dev/mem`, ni envoyer un ioctl « pour voir ».

## Présence des nœuds et disponibilité réelle

| Composant | Ce que prouve une entrée sysfs | Ce qu'elle ne prouve pas | Critère de futur essai |
| --- | --- | --- | --- |
| `fb0` | Le framebuffer a été publié ; son numéro peut être obtenu par `graphics/fb0/dev`. | `mxc_epdc_fb.c:4788–4800` enregistre le framebuffer **avant** de lancer l'initialisation matérielle ; `hw_ready` est une variable interne. À 2679–2683, un rafraîchissement est refusé par -EPERM tant qu'elle est fausse. | Ne pas traiter l'apparition de fb0 comme une preuve que l'E-Ink est prêt. Vérifier la géométrie et le résultat d'un rafraîchissement contrôlé lors de l'essai autorisé. Aucun attribut « ready » n'est inventé. |
| `eventN` | `drivers/input/evdev.c:797–846` attribue le premier minor disponible, fixe le parent input et publie le device. | Le numéro n'identifie ni le tactile ni les boutons ; la présence du nœud ne prouve pas la réponse I²C ou les coordonnées. | Identifier le tactile par le parent `zForce-ir-touch`, confirmer les capacités evdev, puis observer appui/relâchement et les coordonnées. Ne pas fabriquer event1 comme solution à une entrée absente. |
| `ntx_io` | `drivers/char/misc.c:186–224` publie le misc device à partir du nom/major/minor ; `mx50_ntx_io.c:2518–2525` effectue misc_register avant gpio_initials. | Publication ≠ succès observé de l'initialisation électrique et du MCU. Dans le boot normal, les initcalls synchrones précèdent l'init utilisateur ; cet ordre source ne démontre donc pas à lui seul une course avec notre rcS. | Nœud cohérent avec sysfs, pilote/MCU identifiés dans les logs, puis lumière observée après commande contrôlée. Aucun PWM/GPIO utilisateur à réimplémenter. |
| MSP430 | `mx50_rdp.c:1955–1960,2918` déclare le client I²C bus 2, adresse 0x43. | La présence de `2-0043` seule ne démontre pas un driver lié ni un échange valide. | Relever le driver lié et la version rapportée, sans lancer de commande intrusive. La lumière effective reste le test de bout en bout. |

Une attente bornée de fichiers sysfs peut résoudre leur apparition tardive ; elle ne transforme pas leur présence en résultat matériel validé. Aucun délai arbitraire n'est ajouté aujourd'hui. Le timeout et les critères de refus devront être définis dans un futur lot d'intégration, puis testés sur des snapshots synthétiques.

## Écarts démontrés du prototype courant, sans correction appliquée

- Le contrôle final exige event0/event1, sans identifier leur parent. Il ne vérifie pas ntx_io, alors que le frontlight utilise ce périphérique.
- Le parcours de sysfs crée des nœuds, sans appliquer les permissions particulières de la recovery ni distinguer une entrée apparue plus tard. Il ne gère pas les événements à chaud. Le noyau sauvegardé n'offre pas devtmpfs.
- Le lecteur part directement sans préparation explicite de profondeur/rotation framebuffer. La présence de fb0 est insuffisante pour qualifier cette voie.
- Les deux réglages Nickel corrigés et testés sont encore une proposition séparée : ils ne sont pas installés dans l'image v3.
- Le contrôle réseau est une condition de lancement, pas une surveillance continue ni une mesure radio. Cet audit watchdog/périphériques n'ajoute aucune preuve de zéro trafic matériel.

Ces écarts n'appellent pas l'ajout immédiat d'un service Kobo, d'udev complet ou d'un daemon watchdog. Les sources suffisent à fixer les interfaces et les refus nécessaires ; elles ne suffisent pas à choisir des contournements électriques.

## Prochain lot possible

Avant une nouvelle image, préparer un contrôle de snapshots sysfs strictement sur fichiers : identifier framebuffer, tactile et NTX, refuser données manquantes, identité ambiguë et numéros invalides, produire un résultat explicitement limité à la cohérence du snapshot. Tester aussi les cas où eventN change, le tactile manque et fb0 existe sans preuve de disponibilité matérielle. Ce contrôle ne doit ni créer des nœuds ni ouvrir `/dev`.

L'intégration de ce contrôle, du profil indépendant et de la préparation framebuffer modifierait le prototype de démarrage. Elle reste séparée de cet audit conformément à la consigne de le conserver inchangé. Aucun essai physique ne peut commencer sans un contrat d'essai/retour arrière et une nouvelle autorisation explicite.

## Preuves et validation

Les sept fichiers noyau examinés ont été comparés à l'[archive Aura HD épinglée](https://github.com/kobolabs/Kobo-Reader/blob/7a762964e7fa71ad8e8df50dd1b6eee721a43217/hw/imx507-aurahd/linux-2.6.35.3.tar.gz), SHA-256 `01eb66e755243e3c916092dc7dc2d35b259d8f080ae6ad95698e4e69773d0c51` : tous correspondent. Les assertions statiques confirment le corps vide de disable, l'activation dans open, l'enregistrement plateforme commenté, la publication du framebuffer avant son initialisation et le refus d'update avant hw_ready. Aucun de ces tests n'exécute le code noyau.

Les relevés privés du 12 octobre sont conservés hors dépôt dans `artifacts/boot-gates-audit-2026-10-12`, avec les SHA des fichiers et un manifeste des contrôles. Aucun firmware, dump ou fichier personnel ajouté au dépôt. Les fichiers sous sources/ et les arborescences Netronix locales sont lus seulement.
