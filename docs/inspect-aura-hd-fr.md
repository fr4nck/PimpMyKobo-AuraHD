# Inspecter automatiquement une Kobo Aura HD

**Français** | [English](inspect-aura-hd-en.md)

`tools/inspect-aura-hd.py` inspecte une microSD complète, une image disque ou les disques locaux afin d'identifier une Kobo Aura HD / Dragon / E606C0.

L'outil est **strictement en lecture seule** : aucune source n'est ouverte en écriture et aucun montage n'est réalisé.

## Ce que l'outil vérifie

Il :

1. lit le MBR ;
2. recherche `HW CONFIG ` à l'offset Netronix `0x80000` ;
3. lit la version et la taille du HWCONFIG ;
4. confirme l'Aura HD uniquement pour `HW CONFIG v1.7`, charge utile de 39 octets et `bPCB = 28` ;
5. signale un PCB 28 dans un autre format comme probable mais non confirmé ;
6. vérifie les indicateurs de démarrage MBR, les chevauchements et, lorsque la taille de la source est connue, les partitions qui dépassent la fin du support ;
7. détecte les signatures ext et FAT et leurs labels sans monter les partitions ;
8. peut calculer le SHA-256 de la zone brute avant P1, uniquement après identification positive et MBR valide.

Les lectures bas niveau sont alignées sur 512 octets, notamment pour `\\.\PhysicalDriveN` sous Windows.

## Important : lecture seule de l'outil ≠ support physiquement protégé

Même si l'outil n'écrit rien, le système d'exploitation peut écrire sur une carte insérée :

- **Windows** peut attribuer une lettre à P3 FAT32 et proposer de formater les partitions ext4 : toujours annuler une proposition de formatage et éviter d'ouvrir la partition utilisateur pendant le diagnostic ;
- **Linux de bureau** peut automonter une partition et rejouer un journal ext4 : désactiver l'automontage et, si possible, placer le périphérique bloc en lecture seule côté noyau après l'avoir identifié avec certitude.

Pour une analyse approfondie, travailler sur une image locale reste préférable.

## Windows

L'accès brut à `\\.\PhysicalDriveN` nécessite normalement un PowerShell lancé en administrateur.

Depuis la racine du dépôt :

```powershell
python .\tools\inspect-aura-hd.py --hash-boot
```

L'outil utilise `Get-Disk` pour récupérer les numéros et tailles actuels. Si PowerShell est absent, si `Get-Disk` échoue ou dépasse le délai, l'erreur d'énumération est affichée et la commande retourne un code d'erreur au lieu de scanner aveuglément des numéros de disques.

Pour afficher aussi les disques simplement ignorés :

```powershell
python .\tools\inspect-aura-hd.py --verbose --hash-boot
```

Les erreurs de lecture réellement rencontrées sont affichées même sans `--verbose`.

## Linux

Depuis la racine du dépôt :

```bash
sudo python3 ./tools/inspect-aura-hd.py --hash-boot
```

Le scan utilise `/sys/block`. Les périphériques `loop`, `nbd`, `rpmb` et les pseudo-partitions de boot sont ignorés afin de réduire le bruit.

Pour un périphérique bloc fourni explicitement, l'outil tente aussi de déterminer sa taille par un seek jusqu'à la fin lorsque `fstat` ne fournit pas de taille exploitable.

## WSL

WSL ne voit pas nécessairement un lecteur USB Windows comme périphérique bloc Linux. Dans ce cas, exécuter l'inspecteur avec le Python Windows depuis PowerShell est recommandé.

## Source explicite

L'outil accepte aussi le chemin d'une image disque complète ou d'un périphérique brut explicitement choisi. Quand un chemin est fourni, le scan automatique est désactivé.

Les erreurs d'ouverture ou de lecture sont alors toujours affichées explicitement.

## Sortie attendue sur l'exemplaire E606C0 étudié

```text
KOBO AURA HD IDENTIFIÉE
HWCONFIG: v1.7 @ 0x80000, 39 bytes
PCB: 28 -> E606C0
Identification: Kobo Aura HD / Dragon / E606C0
```

Le partitionnement est ensuite lu directement depuis le support. Sur l'exemplaire étudié :

```text
P1: offset=9,961,472    size=268,435,968  type=0x83  ext label="rootfs"
P2: offset=278,397,440  size=268,435,968  type=0x83  ext label="recoveryfs"
P3: offset=546,833,408  ...              type=0x0C  FAT32 label="KOBOeReader"
```

Ces valeurs ne sont jamais utilisées pour choisir arbitrairement un disque.

## Sortie JSON

```powershell
python .\tools\inspect-aura-hd.py --json
```

Le document JSON contient `schema_version`, `discovery_errors` et `results`. Chaque résultat expose notamment `source_size`, `errors[]`, `warnings[]`, le MBR et le HWCONFIG.

## Codes de retour

- `0` : Aura HD E606C0 confirmée et aucun défaut bloquant détecté ;
- `1` : aucune Aura HD confirmée, sans erreur d'accès empêchant le diagnostic ;
- `2` : erreur d'accès/lecture, échec d'énumération bloquant, ou Aura confirmée avec incohérence bloquante.

Un disque GPT ordinaire ou un autre support simplement non compatible n'est donc pas traité comme une erreur d'accès.

## Contrôler ensuite `recoveryfs`

L'inspecteur ne parcourt pas l'arborescence ext4 depuis le disque brut. Pour contrôler `fs.tgz`, `db.tgz`, U-Boot et le kernel, utiliser [`verify-recovery.py`](verify-recovery-fr.md) sur une image ou un montage explicitement en lecture seule.

## Tests

Les tests synthétiques couvrent notamment le parcours complet sur un faux lecteur qui refuse toute lecture bas niveau non alignée sur 512 octets. Une CI GitHub exécute la suite sous Linux et Windows sur plusieurs versions de Python.
