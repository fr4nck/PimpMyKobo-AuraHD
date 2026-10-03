# Outils / Tools

Les outils publics du projet privilégient la **lecture seule**. L'exécuteur Linux de restauration P1 est séparé, explicite et protégé par des garde-fous supplémentaires ; préparer son code n'autorise aucune écriture physique.

## Commande pmkb et paquet Debian

`python3 tools/pmkb.py --help` regroupe les outils sans modifier leurs arguments ni garde-fous. Le paquet `.deb` fournit la commande `pmkb`. Voir [Français](../docs/cli-install-fr.md) / [English](../docs/cli-install-en.md). `build-deb.py` construit le paquet local avec dpkg-deb, sans installation ni accès aux périphériques.

## `inspect-aura-hd.py`

Inspecteur bas niveau d'une microSD complète ou d'une image disque Aura HD.

Il :

- scanne les disques accessibles strictement en lecture seule ;
- cherche le HWCONFIG Netronix à `0x80000` ;
- identifie `E606C0 / Dragon / Kobo Aura HD` ;
- décode les principaux champs HWCONFIG connus ;
- lit le MBR ;
- détecte les labels `rootfs`, `recoveryfs` et `KOBOeReader` sans monter les partitions ;
- peut calculer le SHA-256 de toute la zone brute située avant P1 ;
- peut produire une sortie JSON.

Documentation :

- [Français](../docs/inspect-aura-hd-fr.md)
- [English](../docs/inspect-aura-hd-en.md)

Sous Windows, depuis la racine du dépôt :

```powershell
python .\tools\inspect-aura-hd.py --hash-boot
```

Sous Linux :

```bash
sudo python3 ./tools/inspect-aura-hd.py --hash-boot
```

Aucun numéro de disque n'est codé en dur et aucun chemin d'écriture vers un périphérique physique n'existe dans cet outil.

## `verify-recovery.py`

Vérificateur d'une partition `recoveryfs` déjà montée ou copiée localement.

Il contrôle :

- `fs.md5sum` et les fichiers qu'il couvre ;
- la lecture intégrale tar+gzip de `upgrade/fs.tgz` ;
- la lecture intégrale tar+gzip de `upgrade/db.tgz` ;
- la présence de l'U-Boot `E606C0` ;
- la présence du kernel `uImage-E606C0` ;
- en option, les SHA-256 des quatre fichiers critiques.

Documentation :

- [Français](../docs/verify-recovery-fr.md)
- [English](../docs/verify-recovery-en.md)

Exemple :

```bash
sudo python3 ./tools/verify-recovery.py /mnt/aurahd-recovery --hash-files
```

## `backup-aura-hd.py`

Sauvegarde d'une Aura HD **E606C0 confirmée** : zone pré-P1, P1 `rootfs`, P2 `recoveryfs`, et P3 uniquement avec `--include-userdata`. La source est ouverte en `rb` uniquement ; seul le dossier de destination fourni est écrit. Chaque fichier est vérifié par SHA-256 (source, seconde lecture, relecture destination) et décrit dans `backup-manifest.json` avec une empreinte cible.

Documentation :

- [Français](../docs/backup-aura-hd-fr.md)
- [English](../docs/backup-aura-hd-en.md)

```bash
sudo python3 ./tools/backup-aura-hd.py /dev/sdX ~/Aura-backup --dry-run
```

## `verify-backup-aura-hd.py`

Vérification **hors ligne et en lecture seule** d'un dossier produit par `backup-aura-hd.py`. Aucune carte n'est nécessaire. L'outil contrôle le manifeste, les tailles et SHA-256 recalculés, `SHA256SUMS`, la géométrie, le HWCONFIG et l'empreinte cible relus dans `pre-p1.bin`. Verdicts : `valid` (0), `incomplete` (1), `inconsistent` (2), `invalid` (3). Un verdict valide prouve la cohérence avec le manifeste, ni l'authenticité ni l'aptitude à une restauration.

Documentation :

- [Français](../docs/verify-backup-aura-hd-fr.md)
- [English](../docs/verify-backup-aura-hd-en.md)

```bash
python3 ./tools/verify-backup-aura-hd.py ~/Aura-backup
```

## Import historique pour reconstruction locale

`import-legacy-backup.py` qualifie les fichiers pré-P1 et P2 avec une
provenance `legacy/imported`, sans prétendre à une sauvegarde complète.
`rebuild-rootfs.py` exige `--accept-legacy-import` et relit les preuves.
Cet import ne peut pas autoriser de restauration physique.

- [Français](../docs/import-legacy-backup-fr.md)
- [English](../docs/import-legacy-backup-en.md)

## Simulation locale du remplacement de P1

`restore-rootfs.py` vérifie un plan par défaut. Avec `--simulate`, il crée
une nouvelle copie d'une image disque locale et remplace uniquement P1.
Il vérifie tous les octets hors P1 et ne possède aucun mode physique.

- [Français](../docs/restore-rootfs-simulation-fr.md)
- [English](../docs/restore-rootfs-simulation-en.md)

## Plan local avant restauration P1

`prepare-p1-restore.py` relie la sauvegarde complète, la reconstruction et la simulation par leurs empreintes et produit un plan sans autoriser d'écriture physique. Voir [la procédure](../docs/prepare-p1-restore-fr.md).

## Tests

La première restauration physique dispose d'un exécuteur Linux Live distinct : `restore-p1-linux.py`. Son mode par défaut vérifie uniquement les fichiers locaux. Voir [Français](../docs/restore-p1-linux-fr.md) / [English](../docs/restore-p1-linux-en.md) pour les refus, l'autorisation séparée et les limites.

Des tests unitaires synthétiques sans firmware Kobo sont présents dans `tests/`.

Ils peuvent être exécutés avec la bibliothèque standard Python uniquement :

```bash
python3 -m unittest discover -s tests -v
```

Ils reconstruisent en mémoire ou dans des fichiers temporaires uniquement les structures minimales nécessaires : MBR, HWCONFIG, superblocs, archives tar+gzip et manifeste MD5. Aucun blob Kobo n'est inclus dans les tests.

## À venir

- Retour arrière physique automatisé : non implémenté. `restore-rootfs.py` reste un simulateur local ; la première écriture P1 relève de l'exécuteur Linux Live séparé.

Voir la [roadmap actualisée](../docs/ROADMAP.fr.md) pour distinguer fonctionnalités implémentées et qualification matérielle restante.

## `audit-arm-runtime.py`

Audit statique en lecture seule d'un rootfs extrait localement : ELF ARM32 little-endian, chargeur, dépendances et SHA-256. Disponible via `pmkb audit-arm-runtime`. Aucun ELF exécuté, aucun montage ni écriture. Voir [le contrat et ses limites](../docs/audit-arm-runtime-fr.md). L’option `--check-bootstrap` vérifie aussi les fichiers de lancement, permissions et actions `inittab` du prototype hors ligne (POSIX uniquement). L’option indépendante `--check-storage` contrôle les répertoires `/mnt` et `/mnt/onboard`, sans montage ni accès à P3. Ce contrôle ne qualifie pas le démarrage matériel ni une restauration physique.

## `preflight-koreader.py`

`pmkb preflight-koreader ROOTFS_OU_IMAGE_LOCALE` agrège les contrôles hors matériel existants, avec verdicts `PASS`, `FAIL`, `UNQUALIFIED`. Aucun montage ni restauration ; toutes les qualifications matérielles restent `UNQUALIFIED`. Voir [la portée exacte, le scanner Nickel optionnel et les limites des images](../docs/preflight-koreader-fr.md).
