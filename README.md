# PimpMyKobo-AuraHD

**Français** | [English](README.en.md)

Résurrection, sauvetage, libération et modernisation de la Kobo Aura HD.

La commande `pmkb` regroupe les outils du projet. [Installation Debian/Ubuntu et WSL](docs/cli-install-fr.md). Les modes physiques restent réservés à Linux natif et à une autorisation explicite de restauration.

## Objectif

Construire un système de lecture léger, libre et indépendant pour la Kobo Aura HD, tout en documentant une procédure de sauvetage reproductible pour les machines abandonnées après une réinitialisation ou une corruption logicielle.

Le projet poursuit deux buts complémentaires :

1. **Sauver une Aura HD** à partir de sa propre microSD, sans redistribuer d'images Kobo propriétaires.
2. **Libérer l'Aura HD** en conservant les couches matérielles nécessaires puis en remplaçant progressivement l'environnement utilisateur Kobo par une pile minimale centrée sur KOReader et des composants libres.

## Matériel cible

- Kobo Aura HD / N204
- Nom de code : `dragon`
- PCBA Netronix : `E606C0`
- Freescale i.MX507 / famille i.MX50
- ARM Cortex-A8
- 512 Mio de RAM
- RAM : `K4X2G323PC`
- écran E-Ink 6,8 pouces
- résolution 1440 × 1080
- stockage système sur microSD interne

## Valeurs observées sur l'exemplaire étudié

L'exemplaire étudié contient un bloc `HW CONFIG v1.7` à l'offset `0x80000` (`524288`).

| Champ | Valeur |
|---|---|
| PCB | `28` → `E606C0` |
| Codename | `dragon` |
| Modèle | Kobo Aura HD |
| RAM | 512 Mio |
| CPU | i.MX50 |
| CPUFreq | 1 GHz |
| DisplayResolution | 1440 × 1080 |
| FrontLight | `TABLE3+` |
| HallSensor | `TLE4913` |
| DisplayBusWidth | `16Bits_mirror` |
| FrontLight LED driver | `SY7201` |

La version v1.7 observée contient 39 octets de configuration. Le champ ajouté après `PCB_Flags` est `FrontLight_LED_Driver`.

## Sources Kobo retrouvées

Les sources spécifiques à l'Aura HD se trouvent dans :

    Kobo-Reader/hw/imx507-aurahd/

Elles contiennent notamment :

    linux-2.6.35.3.tar.gz
    u-boot-2009.08.tar.gz

U-Boot contient les adaptations Netronix, notamment `NTX_HWCONFIG`, les paramètres RAM, la gestion de l'écran E-Ink et le chargement des données matérielles.

## Architecture de démarrage

    Boot ROM i.MX507
            |
            v
    U-Boot 2009.08 / Netronix
            |
            +-- HWCONFIG
            +-- paramètres matériels
            +-- waveform E-Ink
            |
            v
    Linux 2.6.35.3 / Kobo-Netronix
            |
            v
         rootfs
            |
            v
       environnement utilisateur

La cible finale est de conserver le strict nécessaire à l'initialisation matérielle tout en remplaçant l'environnement utilisateur Kobo.

## MicroSD originale

Taille physique observée :

    31 914 983 424 octets

Table de partitions : MBR.

| Zone | Offset | Taille | Rôle |
|---|---:|---:|---|
| Zone brute de démarrage | 0 | 9 961 472 octets | U-Boot / kernel / HWCONFIG / données E-Ink |
| Partition 1 | 9 961 472 | 268 435 968 octets | `rootfs` ext4 |
| Partition 2 | 278 397 440 | 268 435 968 octets | `recoveryfs` ext4 |
| Partition 3 | 546 833 408 | reste du support | `KOBOeReader` FAT32 |

La première partition commence à 9,5 Mio, soit 19 456 secteurs de 512 octets.

## Sauvegarde de la zone de démarrage

Les 9 961 472 premiers octets ont été copiés en lecture seule.

SHA-256 :

    4b0c72f9d38a2d81d4d5ffb316b1b0d1efcb8e4bf0fa8610025e75fef837c2b6

Cette sauvegarde binaire n'est volontairement pas publiée dans le dépôt.

## Sauvetage d'une Aura HD après reset interrompu

Sur la machine étudiée, une réinitialisation usine avait commencé puis échoué.

Conséquence observée :

- P1 `rootfs` : ext4 valide, mais pratiquement vide ;
- P2 `recoveryfs` : intacte et cohérente ;
- P3 `KOBOeReader` : recréée par la procédure de recovery.

Le script de récupération Kobo présent dans `recoveryfs` lit le HWCONFIG, sélectionne les artefacts matériels lorsqu'ils sont disponibles, reformate P1/P3 puis extrait `upgrade/fs.tgz` dans P1 et `upgrade/db.tgz` dans P3.

La partition recovery de l'exemplaire étudié contient notamment :

- `upgrade/fs.tgz`
- `upgrade/db.tgz`
- `upgrade/ntx508/u-boot_mddr_512-E606C0-K4X2G323PC.bin`
- `upgrade/ntx508/uImage-E606C0`

Les archives `fs.tgz` et `db.tgz` ont passé un contrôle `gzip -t`. Le recovery a également été contrôlé par son manifeste `fs.md5sum`.

Une nouvelle image ext4 `rootfs` de 256 Mio a été construite localement, alimentée avec `fs.tgz`, vérifiée par `fs.md5sum`, puis contrôlée avec `e2fsck`.

Après écriture ciblée dans P1, le SHA-256 relu directement depuis la microSD était strictement identique à celui de l'image source :

    ADC8995C3F0754CBCF80ABA1540A69CF043DE9823800A359EC75167354B2993C

Cette procédure montre qu'une Aura HD dont `rootfs` a été vidée peut parfois être reconstruite à partir de sa propre partition recovery, sans télécharger d'image système tierce.

## Outils actuels

### `inspect-aura-hd.py`

Inspecteur Python sans dépendance externe et strictement en lecture seule. Il récupère la liste actuelle des disques, lit leur MBR et leur HWCONFIG, confirme `E606C0 / Dragon` uniquement avec le format HWCONFIG attendu et détecte les labels `rootfs`, `recoveryfs` et `KOBOeReader` sans monter les partitions.

Sous Windows :

```powershell
python .\tools\inspect-aura-hd.py --hash-boot
```

Voir [la documentation de l'inspecteur](docs/inspect-aura-hd-fr.md).

### `verify-recovery.py`

Vérificateur en lecture seule d'une partition `recoveryfs` déjà montée ou copiée localement. Il contrôle `fs.md5sum`, le flux gzip complet, les marqueurs de fin tar, le contenu des archives, les artefacts E606C0 et peut calculer leurs SHA-256.

```bash
sudo python3 ./tools/verify-recovery.py /mnt/aurahd-recovery --hash-files
```

Voir [la documentation de `verify-recovery`](docs/verify-recovery-fr.md).

Des tests synthétiques sans firmware Kobo sont présents dans `tests/`. La CI les exécute sous Linux et Windows avec Python 3.10 à 3.13.

## Philosophie de publication

Ce dépôt ne doit pas redistribuer :

- les images complètes de microSD ;
- les dumps personnels ;
- `fs.tgz` ou `db.tgz` extraits d'une liseuse ;
- les blobs Kobo précompilés lorsque leur redistribution n'est pas clairement autorisée.

Le dépôt doit en revanche fournir documentation, inspection, validation, sauvegarde et reconstruction locale à partir des données déjà présentes sur l'appareil de l'utilisateur.

## Règles de sécurité

- lecture seule par défaut ;
- jamais de numéro de disque codé en dur dans un outil public ;
- validation de la taille et des offsets avant toute écriture ;
- identification du HWCONFIG et du PCBA ;
- sauvegarde obligatoire avant modification ;
- vérification cryptographique après écriture ;
- conservation de `recoveryfs` et du HWCONFIG autant que possible.

### Attention aux écritures du système d'exploitation

« Outil en lecture seule » ne signifie pas que le système hôte ne peut rien écrire sur la carte.

- Sous Windows, toujours **annuler** les propositions de formatage des partitions ext4 et éviter d'ouvrir inutilement P3 FAT32 pendant une opération de préservation.
- Sous Linux de bureau, désactiver l'automontage : un montage ext4 en lecture-écriture peut rejouer le journal. Pour les manipulations sensibles, préférer une image locale ou placer le périphérique identifié en lecture seule côté noyau avant analyse.

## État du projet

- [x] Sources officielles Aura HD retrouvées
- [x] MicroSD originale retrouvée et cartographiée
- [x] Zone de boot sauvegardée
- [x] HWCONFIG v1.7 décodé
- [x] PCBA identifié : E606C0 / Dragon
- [x] Recovery factory analysé
- [x] Cas réel de `rootfs` vidée diagnostiqué
- [x] `rootfs` reconstruite depuis `recoveryfs/upgrade/fs.tgz`
- [x] Reconstruction vérifiée par MD5, e2fsck et SHA-256
- [x] Outil `inspect-aura-hd` en lecture seule
- [x] Outil `verify-recovery` en lecture seule
- [x] Tests synthétiques sans blobs Kobo
- [x] CI Linux/Windows Python 3.10–3.13
- [ ] Valider `inspect-aura-hd` sur la microSD physique via le lecteur Windows
- [ ] Extraire et documenter précisément la waveform E-Ink
- [ ] Écrire les outils de sauvegarde et de reconstruction locale
- [ ] Compiler U-Boot et le kernel de référence
- [ ] Construire un userspace minimal moderne
- [ ] Intégrer KOReader
- [ ] Tester une microSD totalement libérée

## Documentation

- [Index de la documentation](docs/README.md)
- [Sauvetage d'une Aura HD](docs/rescue-fr.md)
- [Retrouver les fichiers de recovery](docs/retrouver-fichiers-fr.md)
- [Inspecteur Aura HD](docs/inspect-aura-hd-fr.md)
- [Vérifier recoveryfs](docs/verify-recovery-fr.md)
- [Matériel Aura HD](docs/hardware-fr.md)
- [HWCONFIG Netronix](docs/hwconfig-fr.md)
- [Partitionnement](docs/partition-layout-fr.md)

## Licence

La licence du code propre au projet reste à choisir. Les composants et sources tiers conservent leurs licences respectives.
