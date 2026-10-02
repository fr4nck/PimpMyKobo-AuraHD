# Protéger la microSD sous Windows avant inspection

**Français** | [English](windows-preservation-en.md)

Cette procédure vise à réduire au minimum le risque qu'un Windows hôte écrive sur la microSD interne d'une Kobo Aura HD pendant une inspection.

Les outils `inspect-aura-hd.py` et `verify-recovery.py` sont conçus pour ne jamais écrire sur leur source. Cela ne suffit toutefois pas à empêcher **Windows lui-même** de monter un volume, d'initialiser des métadonnées ou de proposer un formatage.

## Principe important

Ne jamais supposer que l'état `IsReadOnly` d'un disque amovible survivra à :

- un redémarrage ;
- une coupure de courant ;
- un retrait/réinsertion ;
- un changement de lecteur de cartes ou de port USB ;
- une ré-énumération du périphérique.

Après chacun de ces événements, considérer la carte comme de nouveau inscriptible jusqu'à ce que l'état ait été **revérifié**.

## Séquence recommandée

### 1. Démarrer Windows sans la carte

Dans la mesure du possible, ne pas laisser la microSD branchée pendant un redémarrage destiné à une opération de conservation.

Après une coupure imprévue, retirer la carte avant le redémarrage si cela peut être fait sans risque matériel.

### 2. Ouvrir PowerShell en administrateur

L'accès brut à `\\.\PhysicalDriveN` et les commandes `Set-Disk` nécessitent normalement une console élevée.

### 3. Désactiver temporairement l'automontage avant d'insérer la carte

Commande prête à exécuter :

```powershell
mountvol /N
```

Cette commande désactive l'automontage des nouveaux volumes. Elle **ne rend pas le support matériellement non inscriptible**.

Insérer ensuite la microSD.

Ne jamais accepter une proposition Windows du type « Vous devez formater le disque avant de pouvoir l'utiliser » pour les partitions ext4.

### 4. Identifier la carte avec l'inspecteur du projet

Depuis la racine du dépôt :

```powershell
python .\tools\inspect-aura-hd.py --json --hash-boot
```

L'identification n'est confirmée que si le HWCONFIG correspond au format observé `v1.7 / 39 octets / PCB 28` et que le support est cohérent avec une Aura HD E606C0.

### 5. Passer uniquement l'Aura HD confirmée en lecture seule

Le bloc ci-dessous est prêt à copier depuis la racine du dépôt. Il refuse de continuer s'il ne trouve pas **exactement une** Aura HD confirmée et refuse de toucher à un disque marqué système ou boot par Windows.

```powershell
$report = (python .\tools\inspect-aura-hd.py --json | ConvertFrom-Json)
$matches = @($report.results | Where-Object { $_.aura_hd -eq $true })
if ($matches.Count -ne 1) { throw "STOP : exactement une Aura HD confirmée est requise." }
if ($matches[0].source -notmatch 'PhysicalDrive([0-9]+)$') { throw "STOP : source Windows PhysicalDrive inattendue." }
$diskNumber = [int]$Matches[1]
$disk = Get-Disk -Number $diskNumber
if ($disk.IsBoot -or $disk.IsSystem) { throw "STOP : Windows considère ce disque comme disque de boot/système." }
Set-Disk -Number $diskNumber -IsReadOnly $true
$check = Get-Disk -Number $diskNumber
if (-not $check.IsReadOnly) { throw "STOP : le passage en lecture seule n'a pas été confirmé." }
$check | Format-List Number,FriendlyName,BusType,Size,PartitionStyle,IsReadOnly,IsOffline,IsBoot,IsSystem
```

La ligne importante dans la sortie est :

```text
IsReadOnly : True
```

Si ce n'est pas le cas, ne pas poursuivre.

### 6. Effectuer l'inspection pendant que le disque est en lecture seule

```powershell
python .\tools\inspect-aura-hd.py --hash-boot --verbose
```

Le script lui-même n'écrit rien et le support a désormais une seconde barrière côté Windows.

### 7. Mettre le disque hors ligne lorsque l'inspection brute est terminée

Une fois l'inspection terminée, on peut réduire encore l'exposition aux volumes en plaçant le disque hors ligne :

```powershell
$report = (python .\tools\inspect-aura-hd.py --json | ConvertFrom-Json)
$matches = @($report.results | Where-Object { $_.aura_hd -eq $true })
if ($matches.Count -ne 1) { throw "STOP : exactement une Aura HD confirmée est requise." }
if ($matches[0].source -notmatch 'PhysicalDrive([0-9]+)$') { throw "STOP : source Windows PhysicalDrive inattendue." }
$diskNumber = [int]$Matches[1]
$disk = Get-Disk -Number $diskNumber
if (-not $disk.IsReadOnly) { throw "STOP : le disque n'est pas confirmé en lecture seule." }
if ($disk.IsBoot -or $disk.IsSystem) { throw "STOP : disque boot/système refusé." }
Set-Disk -Number $diskNumber -IsOffline $true
Get-Disk -Number $diskNumber | Format-List Number,FriendlyName,IsReadOnly,IsOffline
```

État attendu :

```text
IsReadOnly : True
IsOffline  : True
```

Le mode hors ligne est surtout utile lorsque la carte doit rester branchée entre deux opérations. Il n'est pas présenté comme une garantie physique contre toute écriture : un write-blocker matériel reste la protection supérieure.

### 8. Après retrait de la carte

Réactiver l'automontage normal de Windows :

```powershell
mountvol /E
```

## Après un redémarrage ou une coupure

Ne pas reprendre une procédure en se fiant à l'état précédent.

Repartir de la séquence complète :

1. Windows démarré ;
2. automontage désactivé ;
3. carte insérée ;
4. Aura HD identifiée ;
5. `IsReadOnly` appliqué puis relu ;
6. seulement ensuite, inspection.

Si la carte est restée branchée pendant un redémarrage ou une coupure, considérer que l'absence d'écriture par Windows **n'est pas démontrée**. Vérifier au minimum la géométrie, le HWCONFIG et les empreintes connues avant de poursuivre.

## Ce que chaque protection apporte

| Protection | Ce qu'elle fait | Ce qu'elle ne garantit pas |
|---|---|---|
| `mountvol /N` | empêche l'automontage des nouveaux volumes | ne bloque pas les écritures brutes |
| `Set-Disk -IsReadOnly $true` | demande à Windows de traiter le disque comme lecture seule | ne doit pas être supposé persistant après ré-énumération/reboot |
| `Set-Disk -IsOffline $true` | retire les volumes du chemin d'accès normal de Windows | peut devoir être annulé pour certaines opérations bas niveau |
| outils PimpMyKobo | n'ouvrent pas la source en écriture | ne contrôlent pas les comportements du système hôte |
| write-blocker matériel | bloque physiquement/logiquement les écritures au niveau matériel | nécessite un équipement dédié |

## Règle du projet

Pour toute future opération sensible :

> Un état de protection n'est jamais supposé persistant. Il doit être vérifié à nouveau après chaque reconnexion, ré-énumération, redémarrage ou coupure.
