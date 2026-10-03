# Outils / Tools

Les outils publics du projet privilégient la **lecture seule**. Toute opération future d'écriture sur une microSD devra être séparée, explicite et protégée par des garde-fous supplémentaires.

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

## Tests

Des tests unitaires synthétiques sans firmware Kobo sont présents dans `tests/`.

Ils peuvent être exécutés avec la bibliothèque standard Python uniquement :

```bash
python3 -m unittest discover -s tests -v
```

Ils reconstruisent en mémoire ou dans des fichiers temporaires uniquement les structures minimales nécessaires : MBR, HWCONFIG, superblocs, archives tar+gzip et manifeste MD5. Aucun blob Kobo n'est inclus dans les tests.

## À venir

- `backup-aura-hd` : produire des sauvegardes locales avec empreintes ;
- `rebuild-rootfs` : reconstruire P1 depuis le `fs.tgz` de sa propre liseuse ;
- `restore-rootfs` physique : contrat distinct encore à concevoir ; l'outil actuel simule uniquement sur fichiers locaux.
