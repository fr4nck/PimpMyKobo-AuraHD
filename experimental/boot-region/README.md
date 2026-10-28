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

`virtual_card_plan()` décrit une carte d'émulateur de **1 Gio** (taille puissance de deux exigée par la carte SD QEMU). PRE-P1 n'y change que la taille P3 du MBR. P1 et P2 y sont copiées **à l'identique** : SHA-256 à recontrôler après copie. P3 y est un volume FAT32 neuf et vide. Le plan lui-même n'écrit rien.

## Assemblage de la carte virtuelle : `virtual_card.py`

Profil **`virtual-qemu`**, distinct du profil de remplacement physique de `tools/replace-microsd-linux.py` (PR #7). Le profil physique garde son minimum P3 de 1 Gio et n'est ni importé, ni modifié, ni assoupli. Le profil virtuel accepte une P3 de 64 Mio minimum, pour une carte de 2 Gio maximum ; par défaut, la carte fait **1 Gio** et P3 **526 908 416 octets**.

L'assembleur travaille **uniquement sur des fichiers ordinaires** et crée un **nouveau** fichier. Il :

1. refuse une sortie existante, un répertoire absent, une sortie sous `/dev`, `/proc` ou `/sys`, et toute entrée non régulière ;
2. refuse une PRE-P1 que `boot_region.py` n'estime pas cohérente ;
3. vérifie **avant copie** la taille, le magic ext et le SHA-256 de P1 (celui du FIRST BOOT #1 scellé, sans dérogation possible en ligne de commande) et de P2 (`--expected-p2-sha256`, obligatoire) ;
4. copie PRE-P1 en ne changeant que **les quatre octets 490-493** (taille de P3 dans le MBR), puis P1 et P2 octet pour octet ;
5. écrit une **FAT32 vide « KOBOeReader »** en Python pur, dimensionnée selon la méthode de référence Microsoft (`fatgen103`) : secteurs cachés égaux au départ de P3, FSInfo, secteurs de sauvegarde, deux FAT, label dans le secteur de boot et le répertoire racine ;
6. **relit après écriture** : PRE-P1 identique hors des octets 490-493, SHA-256 de P1 et P2 inchangés, FAT32 revérifiée champ par champ, PRE-P1 réanalysée ;
7. publie seulement si tout est PASS, par lien sans écrasement ; sinon il supprime le fichier temporaire.

Le numéro de série FAT est dérivé des empreintes P1/P2 : le même jeu d'entrées produit la même image (SHA-256 reproductible). L'image reste `boot_verified=false`.

```sh
python3 experimental/boot-region/virtual_card.py PRE-P1.img PMKB-FIRST-BOOT-1-0b00d858.img P2.img carte-virtuelle.img --expected-p2-sha256 <sha-p2>
```

Le fichier est créé en mode 0600. À lancer en QEMU **en mode snapshot**, pour que P1 reste intacte à chaque démarrage.

## Utilisation sur fichiers privés (jamais sur `/dev`)

```sh
python3 experimental/boot-region/boot_region.py PRE-P1.img --p1 PMKB-FIRST-BOOT-1-0b00d858.img --p2 P2.img
```

Seuls les fichiers réguliers sont acceptés ; périphériques et répertoires sont refusés. `--p1` exige le SHA-256 du candidat FIRST BOOT #1 scellé (`7980fec1…f67c`). La sortie JSON peut contenir des empreintes et des adresses : ne publier ni les blobs ni le JSON brut sans relecture.

Tests synthétiques : `python -m unittest discover -s tests -p 'test_boot_region.py' -v` et `-p 'test_virtual_card.py'`.
