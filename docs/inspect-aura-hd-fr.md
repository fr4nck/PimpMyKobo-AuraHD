# Inspecter automatiquement une Kobo Aura HD

**Français** | [English](inspect-aura-hd-en.md)

`tools/inspect-aura-hd.py` évite les manipulations manuelles de numéros de disques, d'offsets et de structures binaires.

L'outil est **strictement en lecture seule** : la source est ouverte en `rb` et aucun chemin d'écriture vers un périphérique physique n'existe dans le script.

## Ce que l'outil vérifie

Sans argument, il recherche les disques accessibles puis :

1. lit le MBR ;
2. valide la signature, les indicateurs de boot, les limites des partitions et les chevauchements ;
3. cherche `HW CONFIG ` à l'offset Netronix `0x80000` ;
4. lit le HWCONFIG avec des lectures alignées sur 512 octets, nécessaires pour les disques bruts Windows ;
5. ne confirme `E606C0 / Dragon / Aura HD` que pour le format observé `v1.7` de 39 octets ;
6. détecte les signatures ext et FAT directement, sans monter les partitions ;
7. signale les lectures incomplètes et les partitions situées au-delà de la taille réelle du support ;
8. peut calculer le SHA-256 de la zone avant P1, uniquement après identification positive et validation du MBR.

Un HWCONFIG contenant `PCB = 28` mais une version ou une taille différente est signalé comme **E606C0 probable**, pas comme identification confirmée.

## Windows

Pour lire `\\.\PhysicalDriveN`, lancer PowerShell **en administrateur**.

Depuis la racine du dépôt :

```powershell
python .\tools\inspect-aura-hd.py --hash-boot
```

Le script utilise `Get-Disk` pour obtenir les numéros réellement présents. Aucun `PhysicalDriveN` n'est codé en dur.

Les erreurs d'accès ne sont plus assimilées à « pas une Kobo » : elles sont affichées explicitement. Lorsqu'une source fournie manuellement est inaccessible, le programme renvoie le code `2`.

## Linux

Depuis la racine du dépôt :

```bash
sudo python3 ./tools/inspect-aura-hd.py --hash-boot
```

Le scan s'appuie sur `/sys/block` et ignore les périphériques virtuels courants (`loop`, `nbd`, `rpmb`, etc.).

## WSL

WSL ne voit pas nécessairement un lecteur de cartes USB Windows comme périphérique bloc Linux. Pour un lecteur USB Windows, utiliser de préférence **Python Windows dans PowerShell administrateur**.

## Important : les outils sont en lecture seule, pas nécessairement le système d'exploitation

Brancher une carte peut provoquer des écritures extérieures au script.

- **Windows** : ne jamais accepter une proposition de formatage des partitions ext4. Éviter également d'ouvrir la partition FAT32 inutilement pendant les opérations de sauvegarde.
- **Linux de bureau** : désactiver l'automontage avant de manipuler la carte. Un montage ext4 en lecture-écriture peut rejouer le journal.

Pour travailler de façon particulièrement conservatrice sous Linux, le support peut être placé en lecture seule côté noyau avant inspection. Vérifier d'abord le vrai nom du périphérique avec `lsblk` ; les noms comme `/dev/sdX` utilisés dans la documentation sont des exemples et ne doivent jamais être copiés littéralement.

## Sortie attendue sur l'exemplaire E606C0 étudié

```text
KOBO AURA HD IDENTIFIÉE
HWCONFIG: v1.7 @ 0x80000, 39 bytes
PCB: 28 -> E606C0
Identification: Kobo Aura HD / Dragon / E606C0
```

Le script affiche ensuite les partitions réellement lues, avec leur type MBR, leur offset, leur taille, le système de fichiers détecté et le label lorsqu'il est disponible.

## Sortie JSON

```powershell
python .\tools\inspect-aura-hd.py --json
```

Le document JSON contient `schema_version`, les résultats par source, `source_size`, `errors[]`, `warnings[]`, le MBR, le HWCONFIG décodé et les labels détectés.

## Codes de retour

- `0` : Aura HD E606C0 confirmée ;
- `1` : aucune Aura HD confirmée, sans erreur d'accès déterminante ;
- `2` : erreur d'accès ou de lecture empêchant le diagnostic demandé.

## Contrôler ensuite `recoveryfs`

`inspect-aura-hd.py` ne parcourt volontairement pas l'arborescence ext4 du recovery depuis le disque brut. Utiliser ensuite [`verify-recovery.py`](verify-recovery-fr.md) sur une copie ou un montage explicitement en lecture seule.

## Sécurité

Les garde-fous actuels comprennent :

- ouverture source en `rb` uniquement ;
- lectures bas niveau alignées sur 512 octets ;
- aucun numéro de disque codé en dur ;
- validation de la taille et de la géométrie MBR ;
- identification stricte `v1.7 / 39 octets / PCB 28` ;
- empreinte de boot limitée à 64 Mio et seulement après identification positive ;
- erreurs de lecture visibles au lieu d'être transformées en faux négatifs silencieux.
