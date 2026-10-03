# Sauvegarder une Kobo Aura HD

**Français** | [English](backup-aura-hd-en.md)

`tools/backup-aura-hd.py` copie les zones utiles d'une microSD d'Aura HD **E606C0 positivement identifiée** vers un dossier de sauvegarde, puis vérifie chaque copie par SHA-256.

> **La source n'est jamais modifiée par PimpMyKobo.** Elle est ouverte uniquement en lecture (`rb`). L'outil ne monte, ne démonte, ne formate et ne repartitionne rien, et n'appelle ni `dd`, ni `diskpart`. Le seul endroit où il écrit est le dossier de destination que vous indiquez.
>
> **Le système d'exploitation hôte peut, lui, écrire sur la carte** : automontage Linux, lettre de lecteur et propositions de formatage sous Windows, indexation… Voir [Protéger la microSD sous Windows](windows-preservation-fr.md) et la section « Écritures du système d'exploitation » de [l'inspecteur](inspect-aura-hd-fr.md).

Cet outil **ne restaure rien**. Aucune commande de restauration n'est fournie.

## Parcours rapide en 4 étapes

Aucune de ces commandes n'écrit sur la carte. Seule l'étape 3 écrit, et uniquement dans le dossier de sauvegarde que vous indiquez.

Avant de commencer :

- branchez la microSD **sans ouvrir** la lettre de lecteur proposée par Windows ;
- **refusez** toute proposition de formatage ;
- sous Linux, désactivez l'automontage ;
- prévoyez un dossier de sauvegarde sur **un autre disque que la carte**, avec environ 600 Mio libres (plus environ 30 Go avec `--include-userdata`).

> **Les valeurs `PhysicalDrive2`, `/dev/sdb`, `D:\Aura-backup` et `~/Aura-backup` ci-dessous sont des exemples.** Remplacez-les par le disque réellement affiché à l'étape 1 et par votre propre dossier de sauvegarde. Si vous vous trompez de disque, l'outil refuse la sauvegarde, car il exige une Aura HD E606C0 confirmée. Il n'écrit jamais sur la source.

### Windows (PowerShell lancé en administrateur, depuis la racine du dépôt)

1. Identifier la carte. Notez la ligne `Source:`, par exemple `\\.\PhysicalDrive2` :

   ```powershell
   python .\tools\inspect-aura-hd.py --verbose
   ```

2. Simuler la sauvegarde. Aucun fichier n'est créé :

   ```powershell
   python .\tools\backup-aura-hd.py \\.\PhysicalDrive2 D:\Aura-backup --dry-run
   ```

3. Sauvegarder. Le dossier `D:\Aura-backup` ne doit pas exister ou doit être vide :

   ```powershell
   python .\tools\backup-aura-hd.py \\.\PhysicalDrive2 D:\Aura-backup
   ```

4. Vérifier le dossier obtenu. La carte peut alors être débranchée :

   ```powershell
   python .\tools\verify-backup-aura-hd.py D:\Aura-backup
   ```

### Linux (depuis la racine du dépôt)

1. Identifier la carte. Notez la ligne `Source:`, par exemple `/dev/sdb` :

   ```bash
   sudo python3 ./tools/inspect-aura-hd.py --verbose
   ```

2. Simuler la sauvegarde :

   ```bash
   sudo python3 ./tools/backup-aura-hd.py /dev/sdb ~/Aura-backup --dry-run
   ```

3. Sauvegarder :

   ```bash
   sudo python3 ./tools/backup-aura-hd.py /dev/sdb ~/Aura-backup
   ```

4. Vérifier, sans `sudo` si le dossier vous appartient :

   ```bash
   python3 ./tools/verify-backup-aura-hd.py ~/Aura-backup
   ```

### Résultats attendus

| Étape | Résultat attendu | Sinon |
|---|---|---|
| 1 | `KOBO AURA HD IDENTIFIÉE`, `PCB: 28 -> E606C0` | ne pas continuer |
| 2 | `Plan de sauvegarde` puis `Simulation (--dry-run) : aucun fichier n'a été créé.` | `REFUS DE SAUVEGARDE` : lire les raisons, rien n'a été écrit |
| 3 | `SAUVEGARDE COMPLÈTE ET VÉRIFIÉE` (code `0`) | `SAUVEGARDE ÉCHOUÉE` : garder le dossier comme preuve et refaire une sauvegarde dans un **nouveau** dossier |
| 4 | `SAUVEGARDE VALIDE` (code `0`) | voir [les verdicts du vérificateur](verify-backup-aura-hd-fr.md#les-quatre-verdicts) |

Pour inclure P3 (livres et données utilisateur), ajoutez `--include-userdata` aux étapes 2 et 3.

Ensuite, conservez le dossier en lieu sûr et **ne le publiez pas** : il contient des fichiers Kobo propriétaires et vos données personnelles.

## Ce qui est sauvegardé

| Fichier | Contenu | Obligatoire |
|---|---|---|
| `pre-p1.bin` | de l'octet 0 jusqu'au début de P1 : MBR, U-Boot, HWCONFIG, données bas niveau | oui |
| `p1-rootfs.img` | copie binaire exacte de P1 `rootfs` | oui |
| `p2-recoveryfs.img` | copie binaire exacte de P2 `recoveryfs` | oui |
| `p3-userdata.img` | copie binaire exacte de P3 `KOBOeReader` | **non**, uniquement avec `--include-userdata` |
| `backup-manifest.json` | manifeste machine-readable | oui |
| `SHA256SUMS` | empreintes des fichiers vérifiés, format `sha256sum` | oui |

Les tailles proviennent **toujours de la table MBR de la carte lue**, jamais d'un fichier existant. Sur l'exemplaire étudié : zone pré-P1 = 9 961 472 octets, P1 = P2 = 268 435 968 octets. Une image `rootfs` reconstruite de 268 435 456 octets n'a donc pas la même taille que la partition réelle.

## Ce qui n'est pas sauvegardé

- P3 par défaut (environ 30 Go sur la carte étudiée), car elle contient surtout les livres et données utilisateur, et sa copie est longue ;
- les zones éventuelles entre partitions et après P3 : elles sont mesurées et signalées dans le manifeste (`gaps_not_backed_up`, `unpartitioned_tail_bytes`) ;
- le numéro de série matériel de la carte (CID) : il n'est pas lisible de façon fiable à travers un lecteur USB.

## Identification obligatoire

Avant de créer quoi que ce soit, l'outil réutilise l'inspecteur qualifié et exige :

- `HW CONFIG` v1.7, 39 octets, PCB 28 / E606C0 ;
- un MBR valide, sans chevauchement ni partition au-delà de la fin du support ;
- exactement P1, P2, P3, dans cet ordre ;
- P1 en ext avec le label `rootfs`, P2 en ext avec le label `recoveryfs`, P3 en FAT. Un label P3 différent de `KOBOeReader` ne produit qu'un avertissement ;
- une zone pré-P1 plausible, contenant le HWCONFIG, d'au plus 64 Mio.

Sinon : **REFUS DE SAUVEGARDE**, code de sortie `2`, et aucun dossier n'est créé.

Si la taille du support ne peut pas être déterminée, l'outil vérifie que le dernier secteur de P3 est lisible avant d'accepter la géométrie.

## Destination

- Elle doit être donnée explicitement et ne pas exister, ou être un dossier vide. Toute collision est refusée.
- L'espace libre est vérifié avant copie : composants demandés + 16 Mio de marge.
- L'outil refuse une destination située **sur la carte source** lorsque cela peut être déterminé :
  - sous Linux, via `/sys/dev/block` et `/proc/self/mountinfo`, en suivant les empilements dm (LUKS, LVM), md et loop jusqu'au disque réel ;
  - sous Windows, via `Get-Partition -DriveLetter`, une requête en lecture seule.
- Si ce n'est pas déterminable (chemin réseau, volume Windows réparti sur plusieurs disques, périphérique virtuel d'origine inconnue, etc.), l'outil refuse, sauf avec `--allow-unverified-destination`. N'utilisez cette option que si vous êtes certain que la destination n'est pas sur la carte.

## Utilisation

Toujours commencer par une simulation, qui ne crée aucun fichier :

```powershell
python .\tools\backup-aura-hd.py \\.\PhysicalDriveN D:\Aura-backup --dry-run
```

Puis la sauvegarde, dans un PowerShell administrateur :

```powershell
python .\tools\backup-aura-hd.py \\.\PhysicalDriveN D:\Aura-backup
```

Sous Linux :

```bash
sudo python3 ./tools/backup-aura-hd.py /dev/sdX ~/Aura-backup
```

`N` et `sdX` sont des exemples : utilisez le disque réellement identifié par `inspect-aura-hd.py`.

Options :

- `--include-userdata` : sauvegarde aussi P3 ;
- `--single-pass` : ne relit pas une seconde fois chaque plage source (plus rapide, moins de contrôle) ;
- `--json` : seul le manifeste JSON est écrit sur la sortie standard, la progression allant sur la sortie d'erreur ;
- `--quiet` : pas de progression ;
- `--lang en`.

Codes de sortie :

- `0` : sauvegarde complète et vérifiée (ou simulation réussie) ;
- `1` : sauvegarde échouée ;
- `2` : refus avant toute copie ;
- `130` : interruption.

## Vérification des copies

Pour chaque composant :

1. les octets lus sur la source sont hachés pendant la copie (`sha256_stream`) ;
2. la plage source est relue et hachée une seconde fois (`sha256_source_reread`, sauf `--single-pass`) ;
3. le fichier est écrit en `.part`, synchronisé sur disque, puis **relu depuis la destination** (`sha256_destination`) ;
4. seulement si les trois empreintes et la taille concordent, le `.part` est renommé avec son nom final.

En cas d'écart, le fichier est renommé en `.FAILED` : il est conservé comme preuve, mais n'est jamais considéré comme valide. La sauvegarde est alors marquée `failed`.

En fin de sauvegarde, la zone pré-P1 est relue pour vérifier que la carte n'a pas changé entre-temps (`identity_recheck`).

Vérifier plus tard une sauvegarde complète, hors ligne et sans carte connectée : [`verify-backup-aura-hd.py`](verify-backup-aura-hd-fr.md) recontrôle le manifeste, les tailles, les SHA-256, `SHA256SUMS` et l'empreinte cible.

Contrôle manuel des seules empreintes :

```bash
cd ~/Aura-backup && sha256sum -c SHA256SUMS
```

Sous Windows :

```powershell
Get-FileHash .\p1-rootfs.img -Algorithm SHA256
```

Comparez le résultat à `SHA256SUMS` ou au champ `sha256` du composant dans le manifeste.

Limite : sous Linux, la seconde lecture d'un périphérique bloc peut être servie par le cache du système. Elle détecte surtout un lecteur instable, pas une dégradation physique de la carte.

## Interpréter `backup-manifest.json`

| Champ | Signification |
|---|---|
| `schema_version` | version du format (1) |
| `status` | `in_progress`, `complete`, `failed` ou `interrupted` |
| `complete` | `true` **uniquement** si tous les composants demandés sont `verified` et que la recheck d'identité concorde |
| `source.path_at_backup_time` | nom utilisé ce jour-là, **pas une identité** (`path_is_identity: false`) |
| `source.size`, `source.size_from` | taille du support et provenance de cette information |
| `identification` | HWCONFIG décodé : version, taille, PCB, RAM, type de RAM, CPU, écran, champs bruts |
| `mbr` | géométrie complète, types, labels, SHA-256 du secteur 0, zones non couvertes |
| `components[]` | pour chaque fichier : offset, taille, statut (`verified`, `failed`, `interrupted`, `not_started`, `not_requested`), empreintes, erreur éventuelle |
| `target_fingerprint` | empreinte cible (voir ci-dessous) |
| `identity_recheck` | relecture finale de la zone pré-P1 |
| `warnings`, `errors` | avertissements et erreurs |

Le manifeste est réécrit de manière atomique après chaque composant. Une sauvegarde interrompue laisse donc un manifeste lisible avec `complete: false`.

Un fichier `.part` n'est **jamais** valide.

## Empreinte cible (`target_fingerprint`)

Algorithme `pmkb-target-v1` : SHA-256 du JSON canonique (clés triées, compact) contenant :

- la taille et le SHA-256 de la zone pré-P1 ;
- le SHA-256 du bloc HWCONFIG (en-tête et données) ;
- la géométrie MBR : numéro, type, LBA de début et nombre de secteurs de chaque partition.

Elle est calculée **uniquement à partir d'octets lus sur la source**. Les noms `PhysicalDrive2`, `/dev/sdb`, etc. n'en font jamais partie. La taille du support est enregistrée à côté mais exclue du calcul, car elle n'est pas toujours déterminable.

Ce qu'elle permet : vérifier qu'une carte présente **le même contenu bas niveau et la même géométrie** que celle qui a été sauvegardée.

Ses limites :

- elle identifie un **contenu**, pas une carte physique : un clone bit à bit a la même empreinte ;
- toute écriture future dans la zone pré-P1 la change : mise à jour Kobo, nouveau U-Boot ou nouveau kernel ;
- son unicité entre deux Aura HD n'est **pas démontrée**, car on ignore si la zone pré-P1 contient des données propres à chaque appareil ;
- elle ne dit rien de l'état de P1, P2 et P3.

Elle **ne doit pas** devenir à elle seule la règle d'autorisation d'une future restauration. Les règles de restauration restent à décider explicitement.

## Décisions retenues

1. L'empreinte cible est un **indice de concordance**, jamais le seul critère autorisant une restauration.
2. L'unicité de la zone pré-P1 entre deux Aura HD **reste inconnue**.
3. La sauvegarde stricte (P1 `rootfs` reconnue) reste le comportement par défaut. Un futur mode de secours pour une P1 corrompue sera un chantier distinct, non implémenté.
4. La sauvegarde couvre les composants sélectionnés (pré-P1, P1, P2, et P3 en option), **pas l'intégralité de la carte**.

## Données à garder privées

Les fichiers produits contiennent des données propriétaires et personnelles : U-Boot, kernel, système Kobo, livres. **Ne les publiez pas.** Le `.gitignore` du dépôt exclut déjà `*.bin`, `*.img` et `backups/`.
