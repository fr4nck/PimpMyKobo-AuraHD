# Outils / Tools

## `inspect-aura-hd.py`

Premier outil de diagnostic du projet.

Il scanne les disques accessibles **strictement en lecture seule**, cherche le HWCONFIG Netronix à `0x80000`, identifie une Aura HD `E606C0 / Dragon`, lit le MBR et détecte les labels `rootfs`, `recoveryfs` et `KOBOeReader` sans monter les partitions.

Documentation :

- [Français](../docs/inspect-aura-hd-fr.md)
- [English](../docs/inspect-aura-hd-en.md)

Sous Windows, depuis la racine du dépôt :

```powershell
python .\tools\inspect-aura-hd.py
```

Sous Linux :

```bash
sudo python3 ./tools/inspect-aura-hd.py
```

Aucun numéro de disque n'est codé en dur et aucun chemin d'écriture vers un périphérique physique n'existe dans cet outil.

## À venir

- `verify-recovery` : vérifier `recoveryfs`, `fs.tgz`, `db.tgz` et les fichiers E606C0 ;
- `backup-aura-hd` : produire des sauvegardes locales avec empreintes ;
- `rebuild-rootfs` : reconstruire P1 depuis le `fs.tgz` de sa propre liseuse ;
- `restore-rootfs` : restauration encadrée avec garde-fous et vérification après écriture.
