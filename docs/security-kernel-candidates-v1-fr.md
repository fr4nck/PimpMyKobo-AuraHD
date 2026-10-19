# PMKB — Sécurité et maintenance : candidats Linux 6.12 / 6.18

**18 octobre 2026 — comparaison de sources, sans clone, compilation, flash ni mesure sur E606C0.** Le noyau 2.6.35.3-850-gbc67621+ (2013) est la référence fonctionnelle, **pas une base de maintenance de sécurité suffisante pour un PDA connecté**.

## Support réel au 18/10/2026

Source primaire : [kernel.org — releases](https://www.kernel.org/category/releases.html), [releases courantes](https://www.kernel.org/). Publication affichée le 15 octobre 2026 :

| Branche | Correctif courant au 15/10/2026 | Fin de maintenance prévue | Avantage / limite |
| --- | --- | --- | --- |
| 6.12 LTS | 6.12.113 | Décembre 2028 | LTS plus ancienne, même horizon annoncé ; migration et comparatif de patches nécessaires |
| 6.18 LTS | 6.18.57 | Décembre 2028 | LTS plus récente, même horizon annoncé ; aucune démonstration de compatibilité Aura HD |

Les revues de code ci-dessous portent sur les **tags de base v6.12 et v6.18**, pas sur l'ensemble des correctifs .113/.57. Le calendrier est une projection éditable, pas une garantie PMKB de patch ni de support spécifique du portage.

## Relecture ciblée comparative des sources amont

| Question | 6.12 | 6.18 | Conclusion E606C0 |
| --- | --- | --- | --- |
| i.MX50 / ARMv7 | [mach-imx50.c](https://github.com/torvalds/linux/blob/v6.12/arch/arm/mach-imx/mach-imx50.c) : DT_MACHINE_START | [mach-imx50.c](https://github.com/torvalds/linux/blob/v6.18/arch/arm/mach-imx/mach-imx50.c) : DT_MACHINE_START | Base SoC, **pas** U-Boot DT de notre machine démontré |
| DTS de base | [imx50.dtsi 6.12](https://github.com/torvalds/linux/blob/v6.12/arch/arm/boot/dts/nxp/imx/imx50.dtsi), sans nœud EPDC dans le fichier | [imx50.dtsi 6.18](https://github.com/torvalds/linux/blob/v6.18/arch/arm/boot/dts/nxp/imx/imx50.dtsi), sans nœud EPDC | Portage EPDC/waveform majeur ; un autre Kobo DTS N514 ≠ E606C0 |
| Veille profonde | [pm-imx5.c 6.12](https://github.com/torvalds/linux/blob/v6.12/arch/arm/mach-imx/pm-imx5.c) : init 51/53, pas 50 | [pm-imx5.c 6.18](https://github.com/torvalds/linux/blob/v6.18/arch/arm/mach-imx/pm-imx5.c) : même constat | Suspend/DVFS et gains énergétiques **non démontrés** |
| Touchscreen | [zforce_ts.c 6.12](https://github.com/torvalds/linux/blob/v6.12/drivers/input/touchscreen/zforce_ts.c) | [zforce_ts.c 6.18](https://github.com/torvalds/linux/blob/v6.18/drivers/input/touchscreen/zforce_ts.c) | Pilote présent, mais protocole v2, IRQ, axes/multitouch non qualifiés |
| MCU Netronix | [ntxec 6.12](https://github.com/torvalds/linux/blob/v6.12/drivers/mfd/ntxec.c) | [ntxec 6.18](https://github.com/torvalds/linux/blob/v6.18/drivers/mfd/ntxec.c) | Trois versions reconnues (0xd726, 0xe135, 0xf110), pas de preuve de version MSP430 E606C0 |
| MC13892 | [regulator 6.12](https://github.com/torvalds/linux/blob/v6.12/drivers/regulator/mc13892-regulator.c) | [regulator 6.18](https://github.com/torvalds/linux/blob/v6.18/drivers/regulator/mc13892-regulator.c) | Driver amont ; **puce présente physiquement non démontrée** |

Le relevé plus large réalisé lors de la contre-expertise BOOT CONTRACT V1 conclut à l'absence de pilote EPDC i.MX50 exploitable en amont Linux v6.18. Ici, seules les sources ciblées listées ont été relues pour comparer les deux tags ; **une absence de nœud dans imx50.dtsi 6.12 ne vaut pas audit exhaustif de tous les drivers 6.12**.

## Conséquences de sécurité

- Un noyau maintenu **réduit le risque de vulnérabilités non corrigées** seulement si un opérateur maintient réellement et distribue les correctifs, y compris ceux du code E606C0 porté.
- Un pilote EPDC ancien porté sans revue de gestion mémoire, DMA, ioctls et entrées non fiables peut réintroduire des vulnérabilités malgré le noyau LTS. Il faut revoir également les interfaces NTX, ZForce, USB/SDIO, firmware, veille et watchdog.
- La compatibilité U-Boot ↔ DTB, les adresses uImage/ATAG, la conservation waveform et la chaîne de confiance restent inconnues ([Boot contract](boot-contract-v1-fr.md)).
- Fonctionnalités de sécurité usuelles (isolation de processus, mécanismes d'intégrité, module signing, permissions) doivent être validées **dans la configuration ARM effectivement construite**, pas extrapolées de la version amont.
- La chaîne de mise à jour nécessitera signatures, clés/revocation, provenance des paquets, mécanisme anti-rollback si justifié et réalisable, et une voie de récupération qui ne repose pas sur une P2 modifiée.
- Les mesures d'autonomie en batterie sur scénarios identiques restent nécessaires ; aucune supériorité énergétique de 6.12 ou 6.18 n'est établie.

**Verdict :** aucun choix final aujourd'hui. 6.12 et 6.18 sont tous deux LTS jusqu'en décembre 2028 selon kernel.org. Décider après le relevé bootloader, une matrice de portage EPDC/MCU et une comparaison de la maintenance réelle/effort/régression énergétique. Conserver 2.6.35.3 comme référence OFFLINE pendant l'étude, sans le qualifier pour CONNECTED.
