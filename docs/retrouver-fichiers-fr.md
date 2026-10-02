# Retrouver les fichiers de recovery sur sa propre Aura HD

**Français** | [English](recover-files-en.md)

Le dépôt ne publie volontairement pas les images système, `fs.tgz`, `db.tgz`, les dumps complets de microSD ni les blobs précompilés extraits d'une liseuse.

Ce n'est normalement pas bloquant : une Aura HD encore équipée de sa microSD peut déjà contenir une grande partie des éléments nécessaires à son propre sauvetage.

Cette page explique où ils se trouvent et comment les récupérer à partir de **sa propre liseuse**.

## Où se trouvent les fichiers utiles ?

Sur l'Aura HD E606C0 étudiée, la microSD contient trois partitions et une zone brute avant P1.

| Zone | Rôle principal |
|---|---|
| zone brute avant P1 | U-Boot, kernel, HWCONFIG et données bas niveau E-Ink |
| P1 `rootfs` | système Linux principal |
| P2 `recoveryfs` | système de récupération et archives usine |
| P3 `KOBOeReader` | données utilisateur et base Kobo |

Les fichiers de recovery les plus utiles se trouvaient dans P2 :

```text
/upgrade/fs.tgz
/upgrade/db.tgz
/upgrade/ntx508/u-boot_mddr_512-E606C0-K4X2G323PC.bin
/upgrade/ntx508/uImage-E606C0
/fs.md5sum
```

`fs.tgz` permet de reconstruire le contenu de P1. `db.tgz` contient les données initiales destinées à P3. Les deux fichiers `E606C0` correspondent au matériel Aura HD / Dragon observé ici.

## 1. Identifier d'abord la bonne microSD

Ne jamais supposer qu'un numéro de disque reste identique d'un branchement à l'autre.

Sous Windows, les commandes de lecture seule suivantes permettent d'afficher les disques puis leurs partitions :

```powershell
Get-Disk | Format-Table Number,FriendlyName,BusType,Size,PartitionStyle -AutoSize
```

Après avoir identifié visuellement la microSD, afficher ses partitions avec le numéro réellement observé :

```powershell
Get-Partition -DiskNumber N | Format-Table PartitionNumber,DriveLetter,Type,Size,Offset -AutoSize
```

`N` doit être remplacé par le numéro effectivement affiché par `Get-Disk`.

Sur l'exemplaire étudié, la disposition observée était :

```text
P1  offset 9 961 472     taille 268 435 968
P2  offset 278 397 440   taille 268 435 968
P3  offset 546 833 408   FAT32, reste du support
```

Ces valeurs documentent le cas étudié. Un futur outil doit toujours relire la table de partitions réelle avant d'agir.

## 2. Sauvegarder P2 `recoveryfs` avant de l'explorer

La méthode recommandée consiste à travailler sur une **image de P2**, et non directement sur la partition originale.

Sous Linux, lorsque la microSD apparaît directement comme un périphérique bloc, commencer par l'identifier :

```bash
lsblk -o NAME,MODEL,SIZE,TYPE,FSTYPE,LABEL,MOUNTPOINTS
```

Puis copier uniquement la partition de recovery vers un fichier local. Le nom du périphérique dépend de la machine (`/dev/sdX2`, `/dev/mmcblkXp2`, etc.) et doit être vérifié avant la copie.

Sous Windows avec WSL, certains lecteurs USB ne sont pas exposés comme périphériques bloc Linux. Dans ce cas, la méthode testée sur ce projet consiste à lire la région P2 depuis `\\.\PhysicalDriveN` en utilisant l'offset et la taille obtenus par `Get-Partition`, puis à écrire cette lecture dans un fichier `AuraHD-p2-recovery.img` sur le PC.

Cette opération doit être une **lecture de la microSD vers un fichier**, jamais l'inverse.

Pour l'exemplaire étudié :

```text
P2 offset : 278 397 440
P2 taille : 268 435 968 octets
```

L'image obtenue faisait exactement 268 435 968 octets et son système de fichiers était identifié comme :

```text
Linux ext4, label "recoveryfs"
```

## 3. Vérifier P2 sans la modifier

Avant montage :

```bash
e2fsck -f -n AuraHD-p2-recovery.img
```

L'option `-n` interdit les réparations.

Pour monter l'image sans rejouer son journal ext4 :

```bash
sudo mkdir -p /mnt/aurahd-recovery
sudo mount -o loop,ro,noload AuraHD-p2-recovery.img /mnt/aurahd-recovery
```

`ro,noload` est important : le montage reste en lecture seule et ne rejoue pas le journal.

## 4. Retrouver `fs.tgz`, `db.tgz`, U-Boot et le kernel

Une fois P2 montée :

```bash
find /mnt/aurahd-recovery/upgrade -maxdepth 3 -type f -printf '%p  %s bytes\n' | sort
```

Sur l'E606C0 étudiée, cette commande a retrouvé notamment :

```text
/mnt/aurahd-recovery/upgrade/fs.tgz
/mnt/aurahd-recovery/upgrade/db.tgz
/mnt/aurahd-recovery/upgrade/ntx508/u-boot_mddr_512-E606C0-K4X2G323PC.bin
/mnt/aurahd-recovery/upgrade/ntx508/uImage-E606C0
```

Pour conserver une copie privée hors du dépôt :

```bash
mkdir -p ~/AuraHD-private-backup
cp -a /mnt/aurahd-recovery/upgrade/fs.tgz ~/AuraHD-private-backup/
cp -a /mnt/aurahd-recovery/upgrade/db.tgz ~/AuraHD-private-backup/
cp -a /mnt/aurahd-recovery/upgrade/ntx508/u-boot_mddr_512-E606C0-K4X2G323PC.bin ~/AuraHD-private-backup/
cp -a /mnt/aurahd-recovery/upgrade/ntx508/uImage-E606C0 ~/AuraHD-private-backup/
```

Ces copies restent locales et ne doivent pas être ajoutées au dépôt public.

## 5. Vérifier l'intégrité des archives récupérées

Les archives gzip peuvent être testées sans extraction :

```bash
gzip -t /mnt/aurahd-recovery/upgrade/fs.tgz
gzip -t /mnt/aurahd-recovery/upgrade/db.tgz
```

Le recovery contient également un manifeste `fs.md5sum` pour son propre système :

```bash
sudo sh -c 'cd /mnt/aurahd-recovery && md5sum -c fs.md5sum'
```

Sur l'exemplaire étudié, l'exécution en simple utilisateur échouait sur `bin/antiword` à cause des permissions ; le contrôle en root était entièrement conforme.

Il est également conseillé de conserver des empreintes SHA-256 de ses copies privées :

```bash
sha256sum ~/AuraHD-private-backup/*
```

## 6. Retrouver le HWCONFIG

Le HWCONFIG n'est pas un fichier dans une partition : il se trouve dans la zone brute précédant P1.

Sur l'exemplaire étudié :

```text
HWCONFIG offset : 524 288 octets = 0x80000
signature       : HW CONFIG v1.7
```

Après avoir sauvegardé la zone brute précédant P1 dans un fichier local, on peut localiser la signature :

```bash
grep -aob 'HW CONFIG' AuraHD-original-boot.bin
```

Puis afficher le bloc :

```bash
dd if=AuraHD-original-boot.bin bs=1 skip=524288 count=110 status=none | od -Ax -tx1z
```

La machine étudiée déclarait notamment :

```text
PCB                    28 -> E606C0
codename                dragon
RAM                     512 Mio
DisplayResolution       1440x1080
FrontLight              TABLE3+
CPUFreq                 1 GHz
HallSensor              TLE4913
DisplayBusWidth         16Bits_mirror
FrontLight_LED_Driver   SY7201
```

## 7. Sauvegarder la zone brute de démarrage

La zone brute s'étend du début de la microSD jusqu'au début de P1.

Sur l'exemplaire étudié, P1 commençait à l'offset 9 961 472. Les 9 961 472 premiers octets ont donc été copiés dans un fichier local.

Cette sauvegarde contient le HWCONFIG et d'autres données critiques de bas niveau.

Elle ne doit pas être publiée telle quelle dans ce dépôt.

## 8. Et la waveform E-Ink ?

Les sources Netronix montrent qu'U-Boot charge également une waveform E-Ink depuis la zone de données bas niveau.

Le projet n'a **pas encore documenté de manière suffisamment vérifiée son offset exact sur l'Aura HD E606C0**.

En conséquence, cette documentation ne donne volontairement pas encore de commande d'extraction de waveform. La priorité est d'établir précisément son emplacement et son format avant de publier une procédure reproductible.

## 9. Reconstruire P1 sans distribuer une image Kobo

Une fois `fs.tgz` récupéré depuis sa propre P2, il est possible de créer localement une nouvelle image ext4 `rootfs`, d'y extraire `fs.tgz`, puis de la vérifier avant toute écriture sur la liseuse.

C'est la stratégie utilisée dans [rescue-fr.md](rescue-fr.md).

Elle permet au projet de documenter une restauration reproductible sans héberger une image système Kobo prête à télécharger.

## À conserver en privé

Il est conseillé de conserver hors Git, avec leurs empreintes :

- la sauvegarde de la zone brute avant P1 ;
- l'image P1 originale ;
- l'image P2 `recoveryfs` ;
- `fs.tgz` ;
- `db.tgz` ;
- les U-Boot et kernels précompilés extraits ;
- toute future extraction de waveform.

Le dépôt public doit contenir la documentation et les outils permettant de **retrouver et vérifier** ces éléments, pas nécessairement les éléments eux-mêmes.
