# Sauvetage d'une Kobo Aura HD

**Français** | [English](rescue-en.md)

Cette documentation décrit une méthode de diagnostic et de reconstruction d'une Kobo Aura HD dont une réinitialisation d'usine a été interrompue.

## Matériel étudié

- Kobo Aura HD / N204
- nom de code : `dragon`
- PCBA : `E606C0`
- plateforme : Netronix / Freescale i.MX50
- RAM : 512 Mio
- type de RAM : `K4X2G323PC`
- HW CONFIG : v1.7

## Symptôme observé

Après une réinitialisation usine interrompue :

- P1 `rootfs` était un ext4 valide mais quasiment vide ;
- P2 `recoveryfs` était intacte ;
- le recovery contenait encore les archives et les binaires nécessaires à la restauration.

Un `e2fsck -f -n` sur P1 ne signalait pas d'erreur structurelle, car le système de fichiers vide était lui-même sain.

## Ce que fait le recovery Kobo

Le script `recoveryfs:/etc/init.d/rcS` :

1. lit le HWCONFIG ;
2. sélectionne éventuellement U-Boot et le kernel adaptés ;
3. reformate P1 en ext4 avec le label `rootfs` ;
4. reformate P3 en FAT32 avec le label `KOBOeReader` ;
5. monte P1 ;
6. extrait `/upgrade/fs.tgz` dans P1 ;
7. monte P3 ;
8. extrait `/upgrade/db.tgz` dans P3.

Une coupure ou une erreur entre le formatage et l'extraction de `fs.tgz` laisse donc exactement le type de P1 vide observé ici.

## Fichiers de recovery observés

Le recovery de l'exemplaire E606C0 contenait notamment :

    upgrade/fs.tgz
    upgrade/db.tgz
    upgrade/ntx508/u-boot_mddr_512-E606C0-K4X2G323PC.bin
    upgrade/ntx508/uImage-E606C0

## Contrôles réalisés

### Recovery filesystem

Le système `recoveryfs` a passé les cinq passes de `e2fsck -f -n` sans incohérence.

Son manifeste `fs.md5sum` a été vérifié intégralement en root.

### Archives usine

    gzip -t upgrade/fs.tgz
    gzip -t upgrade/db.tgz

Les deux archives ont été validées.

`fs.tgz` contenait 2529 entrées et environ 160,8 Mo décompressés.

## Reconstruction de P1 hors ligne

Une nouvelle image de 256 Mio a été créée sur le PC, puis formatée en ext4 avec le label `rootfs`.

`fs.tgz` y a été extrait.

Le rootfs obtenu contenait notamment :

    bin/
    dev/
    drivers/
    etc/
    lib/
    libexec/
    root/
    sbin/
    usr/
    linuxrc
    fs.md5sum

Le manifeste `fs.md5sum` du rootfs reconstruit n'a remonté aucune différence.

`e2fsck -f -n` a également terminé sans erreur :

    rootfs: 2260/65536 files, 183174/262144 blocks

## Écriture ciblée de P1

L'image reconstruite a été écrite uniquement à partir de l'offset de P1.

La relecture directe de la zone écrite a donné le même SHA-256 que l'image source :

    ADC8995C3F0754CBCF80ABA1540A69CF043DE9823800A359EC75167354B2993C

Cette empreinte documente l'image reconstruite dans ce cas précis ; elle n'est pas destinée à être une empreinte universelle pour toutes les Aura HD.

## Ce qu'il ne faut pas publier

Le projet ne publie pas :

- l'image P1 reconstruite ;
- les dumps de la microSD ;
- `fs.tgz` ou `db.tgz` ;
- les blobs extraits d'une liseuse lorsque leur redistribution n'est pas clairement autorisée.

L'objectif est de fournir les outils permettant à chaque propriétaire d'utiliser les données déjà présentes sur sa propre Aura HD.

## Règles de sécurité

- sauvegarder avant toute écriture ;
- conserver `recoveryfs` ;
- conserver le HWCONFIG ;
- identifier le matériel avant d'écrire ;
- lire et vérifier réellement la table de partitions ;
- reconstruire et contrôler les images hors ligne ;
- relire les octets écrits et comparer leur empreinte ;
- ne jamais coder en dur un numéro de disque physique dans un outil distribué.
