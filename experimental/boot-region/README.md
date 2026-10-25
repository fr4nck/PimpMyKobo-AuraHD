# PMKB — qualification de la zone PRE-P1 (lecture seule)

Lire d'abord [l'audit R2 de l'émulation E606C0](../../docs/emulation-e606c0-r2-fr.md) et le [BOOT CONTRACT V1](../../docs/boot-contract-v1-fr.md).

`boot_region.py` décode, **sans rien écrire**, les structures que la Boot ROM i.MX50, U-Boot et Linux lisent dans les 9 961 472 octets précédant P1 :

| Contrôle | Ce qui est vérifié | Ce qui n'est PAS vérifié |
| --- | --- | --- |
| `mbr_*` | Signature, P1/P2 ext (0x83) aux secteurs 19 456 / 543 745 de 524 289 secteurs, P3 FAT32 au secteur 1 068 034, P4 vide | Système de fichiers réel |
| `hwconfig_*` | `HW CONFIG ` à 0x80000, taille de charge bornée, `bPCB=28` (E606C0) | Les autres champs (voir `inspect-aura-hd`) |
| `ivt_*`, `uboot_extent` | IVT `D1 00 20 40` à 0x400, plug-in DDR de la ROM puis IVT principale, adresse de chargement/entrée d'U-Boot dans la RAM déclarée, image entièrement sous le HWCONFIG | Signature HAB, contenu DCD, comportement d'U-Boot |
| `uimage_*`, `zimage_size` | Magic, CRC d'en-tête et de charge, OS/arch/type, **IH_LOAD / IH_EP**, taille avant la waveform ; en-tête zImage si non compressé | Décompression, adresse finale du noyau |
| `waveform_magic` | Marqueur Netronix `ff f5 af ff` à 0x700000 | Longueur, format, validité électrique |
| `u_boot_handoff` | Toujours `UNQUALIFIED` : machine ID, r2 ATAG/DTB et cmdline exigent le code U-Boot ou un journal de boot | — |

Statuts : `PASS`, `FAIL` (refus global) ou `UNQUALIFIED` (non démontrable ici). Le résultat global est `refused` ou `consistent_unverified`, jamais un certificat de boot. La base RAM 0x70000000 est une **hypothèse déclarée** (fenêtre CSD0 de l'i.MX50) : passer `ram_base` pour la contester.

`virtual_card_plan()` décrit une carte d'émulateur de **1 Gio** (taille puissance de deux exigée par la carte SD QEMU). PRE-P1 n'y change que la taille P3 du MBR. P1 et P2 y sont copiées **à l'identique** : SHA-256 à recontrôler après copie. P3 y est un volume FAT32 neuf et vide. Le plan n'écrit rien : la composition et le formatage FAT32 ne sont pas implémentés dans ce lot.

## Utilisation sur fichiers privés (jamais sur `/dev`)

```sh
python3 experimental/boot-region/boot_region.py PRE-P1.img --p1 PMKB-FIRST-BOOT-1-0b00d858.img --p2 P2.img
```

Seuls les fichiers réguliers sont acceptés ; périphériques et répertoires sont refusés. `--p1` exige le SHA-256 du candidat FIRST BOOT #1 scellé (`7980fec1…f67c`). La sortie JSON peut contenir des empreintes et des adresses : ne publier ni les blobs ni le JSON brut sans relecture.

Tests synthétiques : `python -m unittest discover -s tests -p test_boot_region.py -v`.
