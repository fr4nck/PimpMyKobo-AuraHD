# Retrouver les fichiers de recovery sur sa propre Aura HD

**Français** | [English](recover-files-en.md)

Le dépôt ne publie volontairement pas les images système, `fs.tgz`, `db.tgz`, les dumps complets de microSD ni les blobs précompilés extraits d'une liseuse.

Ce n'est normalement pas bloquant : une Aura HD encore équipée de sa microSD peut déjà contenir une grande partie des éléments nécessaires à son propre sauvetage.

Cette page explique où ils se trouvent et comment les récupérer à partir de **sa propre liseuse**.

## Avant toute chose : empêcher les écritures involontaires

Les outils du projet sont en lecture seule, mais le système d'exploitation peut écrire sur la carte sans leur intervention.

- **Windows** : toujours annuler une proposition de formatage des partitions ext4. Éviter d'ouvrir inutilement la partition FAT32 `KOBOeReader` pendant la préservation.
- **Linux de bureau** : désactiver l'automontage. Un montage ext4 en lecture-écriture peut rejouer le journal.
- Pour l'analyse détaillée, créer d'abord une image locale puis travailler sur cette copie.

## Où se trouvent les fichiers utiles ?

Sur l'Aura HD E606C0 étudiée, la microSD contient trois partitions et une zone brute avant P1.

| Zone | Rôle principal |
|---|---|
| zone brute avant P1 | U-Boot, kernel, HWCONFIG et données bas niveau E-Ink |
| P1 `rootfs` | système Linux principal |
| P2 `recoveryfs` | système de récupération et archives usine |
| P3 `KOBOeReader` | données utilisateur et base Kobo |

Les fichiers de recovery les plus utiles observés dans P2 sont :

```text
/upgrade/fs.tgz
/upgrade/db.tgz
/upgrade/ntx508/u-boot_mddr_512-E606C0-K4X2G323PC.bin
/upgrade/ntx508/uImage-E606C0
/fs.md5sum
```

`fs.tgz` permet de reconstruire le contenu de P1. `db.tgz` contient les données initiales destinées à P3. Les fichiers `E606C0` correspondent au matériel Aura HD / Dragon étudié ici.

## 1. Identifier la carte sans supposer son numéro

La méthode recommandée est désormais l'inspecteur du projet :

```powershell
python .\tools\inspect-aura-hd.py --verbose --hash-boot
```

Sous Windows, lancer cette commande depuis un PowerShell administrateur. Elle utilise `Get-Disk`, ne code aucun numéro en dur et ne confirme une Aura HD que si le HWCONFIG correspond au format `v1.7 / 39 octets / PCB 28` attendu.

Pour simplement afficher les disques Windows sans rien lire en brut :

```powershell
Get-Disk | Format-Table Number,FriendlyName,BusType,Size,PartitionStyle -AutoSize
```

Sous Linux :

```bash
lsblk -o NAME,MODEL,SIZE,TYPE,FSTYPE,LABEL,MOUNTPOINTS
```

Ne jamais supposer qu'un numéro de disque ou un nom de périphérique reste identique après débranchement/rebranchement.

Sur l'exemplaire étudié, la géométrie était :

```text
P1  offset 9 961 472     taille 268 435 968
P2  offset 278 397 440   taille 268 435 968
P3  offset 546 833 408   FAT32, reste du support
```

Ces valeurs documentent uniquement l'exemplaire étudié. Les outils doivent relire la table réelle du support.

## 2. Sauvegarder P2 `recoveryfs` avant de l'explorer

La méthode recommandée consiste à travailler sur une **image de P2**, et non directement sur la partition originale.

Sous Linux, après avoir identifié avec certitude la vraie partition recovery, une copie brute peut être créée vers un fichier local. Le projet évite volontairement de publier ici une commande générique contenant un nom de périphérique factice : l'identifiant doit être déterminé sur la machine réelle avant toute lecture brute.

Sous Windows, certains lecteurs USB ne sont pas exposés comme périphériques bloc dans WSL. La méthode utilisée lors du sauvetage réel consistait alors à lire P2 depuis le `PhysicalDrive` identifié, en utilisant **l'offset et la taille réellement lus**, puis à écrire cette lecture dans un fichier local.

Cette opération doit toujours aller **de la microSD vers un fichier**, jamais l'inverse.

Pour l'exemplaire étudié :

```text
P2 offset : 278 397 440
P2 taille : 268 435 968 octets
```

L'image obtenue était un ext4 portant le label `recoveryfs`.

## 3. Vérifier l'image P2 sans la modifier

Avant montage :

```bash
e2fsck -f -n AuraHD-p2-recovery.img
```

L'option `-n` interdit les réparations.

Montage sans rejeu du journal ext4 :

```bash
sudo mkdir -p /mnt/aurahd-recovery
sudo mount -o loop,ro,noload AuraHD-p2-recovery.img /mnt/aurahd-recovery
```

## 4. Retrouver `fs.tgz`, `db.tgz`, U-Boot et le kernel

Une fois l'image P2 montée :

```bash
find /mnt/aurahd-recovery/upgrade -maxdepth 3 -type f -printf '%p  %s bytes\n' | sort
```

Sur l'exemplaire étudié, on retrouvait notamment :

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

## 5. Vérifier réellement le recovery

Le vérificateur du projet contrôle le manifeste, le gzip, les marqueurs de fin tar, le contenu des archives et les artefacts E606C0 :

```bash
sudo python3 ./tools/verify-recovery.py /mnt/aurahd-recovery --hash-files
```

Lors du sauvetage initial, les contrôles indépendants suivants avaient également été utilisés :

```bash
gzip -t /mnt/aurahd-recovery/upgrade/fs.tgz
gzip -t /mnt/aurahd-recovery/upgrade/db.tgz
sudo sh -c 'cd /mnt/aurahd-recovery && md5sum -c fs.md5sum'
```

Sur l'exemplaire étudié, `bin/antiword` nécessitait les droits root pour que le contrôle du manifeste puisse être complet.

## 6. Retrouver le HWCONFIG

Le HWCONFIG n'est pas un fichier dans une partition : il se trouve dans la zone brute précédant P1.

Sur l'exemplaire étudié :

```text
HWCONFIG offset : 524 288 octets = 0x80000
signature       : HW CONFIG v1.7
```

Après avoir sauvegardé la zone brute précédant P1 dans un fichier local :

```bash
grep -aob 'HW CONFIG' AuraHD-original-boot.bin
```

Puis :

```bash
dd if=AuraHD-original-boot.bin bs=1 skip=524288 count=110 status=none | od -Ax -tx1z
```

L'exemplaire étudié déclarait notamment PCB 28 / E606C0, 512 Mio de RAM, résolution 1440×1080, `TABLE3+`, `TLE4913`, bus `16Bits_mirror` et driver LED `SY7201`.

## 7. Sauvegarder la zone brute de démarrage

La zone brute s'étend du début de la microSD jusqu'au début réel de P1.

Sur l'exemplaire étudié, P1 commençait à l'offset 9 961 472 : les 9 961 472 premiers octets ont donc été sauvegardés localement. Cette zone contient notamment le HWCONFIG et des données critiques de bas niveau.

Elle ne doit pas être publiée telle quelle dans ce dépôt.

## 8. Et la waveform E-Ink ?

Les sources Netronix montrent qu'U-Boot charge également une waveform E-Ink depuis la zone de données bas niveau. Son offset exact sur l'Aura HD E606C0 n'est **pas encore documenté avec suffisamment de certitude** pour publier une commande d'extraction.

## 9. Reconstruire P1 sans distribuer une image Kobo

Une fois `fs.tgz` récupéré depuis sa propre P2, il est possible de créer localement une nouvelle image ext4 `rootfs`, d'y extraire l'archive puis de tout vérifier avant écriture. C'est la stratégie décrite dans [rescue-fr.md](rescue-fr.md).

## À conserver en privé

Conserver hors Git, avec leurs empreintes :

- sauvegarde de la zone brute avant P1 ;
- image P1 originale ;
- image P2 `recoveryfs` ;
- `fs.tgz` ;
- `db.tgz` ;
- U-Boot et kernels précompilés extraits ;
- toute future extraction de waveform.

Le dépôt public doit fournir les outils permettant de **retrouver et vérifier** ces éléments, pas nécessairement les éléments eux-mêmes.
