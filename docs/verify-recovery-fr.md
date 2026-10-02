# Vérifier `recoveryfs`

**Français** | [English](verify-recovery-en.md)

`tools/verify-recovery.py` contrôle en lecture seule une partition `recoveryfs` déjà montée, ou une copie de son contenu.

L'outil ne monte pas lui-même la microSD et n'écrit jamais dans le recovery.

## Ce qu'il contrôle

Par défaut :

- présence de `fs.md5sum` ;
- vérification de chaque fichier couvert par ce manifeste ;
- lecture complète de `upgrade/fs.tgz` pour vérifier le flux gzip ;
- lecture complète de `upgrade/db.tgz` ;
- présence de l'U-Boot Aura HD E606C0 :
  `upgrade/ntx508/u-boot_mddr_512-E606C0-K4X2G323PC.bin` ;
- présence du kernel Aura HD E606C0 :
  `upgrade/ntx508/uImage-E606C0`.

Avec `--hash-files`, il calcule aussi le SHA-256 des deux archives et des deux fichiers E606C0 afin de permettre à l'utilisateur de documenter sa propre sauvegarde privée.

## Préparation recommandée

Il est préférable de travailler sur une image de P2 et de la monter explicitement en lecture seule sans rejouer le journal ext4 :

```bash
sudo mkdir -p /mnt/aurahd-recovery
sudo mount -o loop,ro,noload AuraHD-p2-recovery.img /mnt/aurahd-recovery
```

La procédure permettant de retrouver et copier P2 est décrite dans [Retrouver les fichiers de recovery](retrouver-fichiers-fr.md).

## Utilisation

Depuis la racine du dépôt :

```bash
sudo python3 ./tools/verify-recovery.py /mnt/aurahd-recovery
```

Pour conserver aussi les empreintes SHA-256 :

```bash
sudo python3 ./tools/verify-recovery.py /mnt/aurahd-recovery --hash-files
```

Sortie JSON exploitable par d'autres outils :

```bash
sudo python3 ./tools/verify-recovery.py /mnt/aurahd-recovery --json
```

Le contrôle du manifeste peut être ignoré ponctuellement avec `--skip-md5`, mais ce mode réduit fortement la valeur du diagnostic.

## Pourquoi les droits root peuvent être nécessaires

Sur le recovery étudié, `bin/antiword` n'était pas lisible par un utilisateur ordinaire. Le manifeste paraissait donc en échec sans `sudo`, alors que les fichiers étaient conformes.

L'outil distingue :

- fichier absent ;
- fichier illisible ;
- empreinte MD5 incorrecte ;
- ligne de manifeste invalide.

## Codes de sortie

- `0` : tous les contrôles demandés sont conformes ;
- `1` : au moins un contrôle demandé est absent, illisible ou incorrect.

## Sécurité

Le chemin source est uniquement ouvert en lecture. L'outil n'a aucune fonction de réparation, d'extraction ou d'écriture vers la microSD.

Le contrôle permet donc de décider si le recovery constitue une base crédible avant de lancer une reconstruction locale de P1.