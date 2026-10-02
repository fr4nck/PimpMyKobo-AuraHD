# Inspecter automatiquement une Kobo Aura HD

**Français** | [English](inspect-aura-hd-en.md)

`tools/inspect-aura-hd.py` évite les manipulations manuelles de numéros de disques, d'offsets et de structures binaires.

Il fonctionne **strictement en lecture seule** : les sources sont toujours ouvertes avec le mode Python `rb` et aucun chemin d'écriture vers un disque physique n'existe dans l'outil.

## Ce que l'outil fait

Sans argument, il recherche les disques accessibles puis :

1. lit le MBR ;
2. cherche la signature `HW CONFIG ` à l'offset Netronix `0x80000` ;
3. lit la version et la taille du HWCONFIG ;
4. décode les champs connus de la structure v1.7 ;
5. reconnaît l'Aura HD étudiée si `bPCB = 28`, soit `E606C0 / Dragon` ;
6. lit les quatre entrées de partition du MBR ;
7. détecte directement les signatures ext et FAT sans monter les partitions ;
8. affiche les labels `rootfs`, `recoveryfs` et `KOBOeReader` lorsqu'ils sont présents ;
9. peut calculer, sur demande, le SHA-256 de toute la zone brute située avant P1.

L'outil **ne suppose pas** que la Kobo est `PhysicalDrive2`, `/dev/sdb` ou un autre nom particulier.

## Prérequis

- Python 3.10 ou plus récent recommandé ;
- aucun module Python externe ;
- Windows ou Linux.

Sous Windows, l'accès brut à `\\.\PhysicalDriveN` peut nécessiter un PowerShell lancé en administrateur.

Sous Linux, la lecture d'un périphérique bloc brut peut nécessiter `sudo`.

## Windows : détection automatique

Depuis la racine du dépôt :

```powershell
python .\tools\inspect-aura-hd.py
```

L'outil appelle `Get-Disk` pour obtenir la liste actuelle des disques, puis tente uniquement des ouvertures en lecture.

Pour afficher également les disques ignorés ou inaccessibles :

```powershell
python .\tools\inspect-aura-hd.py --verbose
```

Pour calculer en plus le SHA-256 de la zone située entre l'octet 0 et le début réel de P1 :

```powershell
python .\tools\inspect-aura-hd.py --hash-boot
```

## Linux

Depuis la racine du dépôt :

```bash
sudo python3 ./tools/inspect-aura-hd.py
```

Le scan utilise `/sys/block` et ne dépend pas d'un nom de périphérique prédéfini.

## WSL

WSL ne voit pas nécessairement un lecteur de cartes USB Windows comme périphérique bloc Linux. Dans ce cas, lancer l'outil avec le Python Windows depuis PowerShell est la méthode recommandée.

L'outil accepte aussi, comme argument positionnel, le chemin d'une image disque complète ou d'un périphérique brut explicitement choisi. Lorsqu'un chemin est fourni, la détection automatique est désactivée pour cette exécution.

## Sortie attendue sur une E606C0

L'outil doit notamment retrouver :

```text
KOBO AURA HD IDENTIFIÉE
HWCONFIG: v1.7 @ 0x80000, 39 bytes
PCB: 28 -> E606C0
Identification: Kobo Aura HD / Dragon / E606C0
  RAM: 3 -> 512MB
  RAM type: 2 -> K4X2G323PC
  CPU: 2 -> mx50
  CPU frequency: 2 -> 1G
  Display: 3 -> 1440x1080
  Frontlight: 6 -> TABLE3+
  Hall sensor: 1 -> TLE4913
  Display bus: 3 -> 16Bits_mirror
  Frontlight LED driver: 0 -> SY7201
```

Puis le partitionnement réellement lu dans le MBR, par exemple sur la machine étudiée :

```text
P1: offset=9,961,472    size=268,435,968  ext label="rootfs"
P2: offset=278,397,440  size=268,435,968  ext label="recoveryfs"
P3: offset=546,833,408  ...              FAT32 label="KOBOeReader"
```

Ces offsets ne servent pas à identifier arbitrairement le disque : ils sont affichés après lecture de sa propre table de partitions.

## Sortie JSON

Pour réutiliser le résultat dans de futurs scripts :

```powershell
python .\tools\inspect-aura-hd.py --json
```

La sortie contient notamment la source inspectée, les métadonnées du disque, le MBR, les partitions, le HWCONFIG décodé, l'identification E606C0 et les labels de systèmes de fichiers.

## Langue anglaise

```powershell
python .\tools\inspect-aura-hd.py --lang en
```

## Codes de retour

- `0` : une Aura HD E606C0 a été identifiée ;
- `1` : aucune Aura HD E606C0 n'a été identifiée.

## Contrôler ensuite le contenu de `recoveryfs`

L'inspecteur détecte P2 et son label `recoveryfs` directement depuis les structures du système de fichiers, mais il ne parcourt volontairement pas l'arborescence ext4 depuis le disque brut.

Le contrôle des fichiers suivants est réalisé par l'outil séparé [`verify-recovery.py`](verify-recovery-fr.md), à partir d'un montage ou d'une copie de P2 en lecture seule :

```text
/upgrade/fs.tgz
/upgrade/db.tgz
/upgrade/ntx508/u-boot_mddr_512-E606C0-K4X2G323PC.bin
/upgrade/ntx508/uImage-E606C0
```

Cette séparation garde l'inspection du support physique minimale et limite la surface de risque.

## Sécurité

La conception suit quatre règles :

- aucune ouverture `r+b`, `wb` ou équivalente ;
- aucun numéro de disque codé en dur ;
- identification par données réellement lues sur le support ;
- aucune écriture même après identification positive.

L'objectif est qu'une commande de diagnostic puisse être lancée sans transformer une erreur d'identification en destruction de données.