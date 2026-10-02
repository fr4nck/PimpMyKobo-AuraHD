# Protecting the microSD on Windows before inspection

[Français](windows-preservation-fr.md) | **English**

This procedure reduces the risk that the Windows host writes to the internal microSD of a Kobo Aura HD during inspection.

`inspect-aura-hd.py` and `verify-recovery.py` are designed never to write to their source. That does not prevent **Windows itself** from mounting a volume, creating metadata or offering to format an unknown filesystem.

## Important principle

Never assume that the `IsReadOnly` state of removable media survives:

- a reboot;
- a power loss;
- removal/reinsertion;
- a different card reader or USB port;
- device re-enumeration.

After any such event, treat the card as writable again until the protection state has been **verified again**.

## Recommended sequence

### 1. Start Windows without the card

Whenever practical, do not leave the microSD connected during a reboot intended for preservation work.

After an unexpected power loss, remove the card before restarting if doing so is physically safe.

### 2. Open an Administrator PowerShell

Raw access to `\\.\PhysicalDriveN` and `Set-Disk` normally require elevation.

### 3. Temporarily disable automount before inserting the card

Ready-to-run command:

```powershell
mountvol /N
```

This disables automatic mounting of newly discovered volumes. It **does not make the medium physically write-protected**.

Insert the microSD afterwards.

Never accept a Windows prompt asking to format the ext4 partitions.

### 4. Identify the card with the project inspector

From the repository root:

```powershell
python .\tools\inspect-aura-hd.py --json --hash-boot
```

Identification is confirmed only when HWCONFIG matches the observed `v1.7 / 39-byte / PCB 28` format and the source is coherent with an E606C0 Aura HD.

### 5. Mark only the confirmed Aura HD read-only

The following block is ready to paste from the repository root. It refuses to continue unless **exactly one** confirmed Aura HD is found, and refuses any disk Windows marks as boot or system media.

```powershell
$report = (python .\tools\inspect-aura-hd.py --json | ConvertFrom-Json)
$matches = @($report.results | Where-Object { $_.aura_hd -eq $true })
if ($matches.Count -ne 1) { throw "STOP: exactly one confirmed Aura HD is required." }
if ($matches[0].source -notmatch 'PhysicalDrive([0-9]+)$') { throw "STOP: unexpected Windows PhysicalDrive source." }
$diskNumber = [int]$Matches[1]
$disk = Get-Disk -Number $diskNumber
if ($disk.IsBoot -or $disk.IsSystem) { throw "STOP: Windows marks this disk as boot/system media." }
Set-Disk -Number $diskNumber -IsReadOnly $true
$check = Get-Disk -Number $diskNumber
if (-not $check.IsReadOnly) { throw "STOP: read-only state was not confirmed." }
$check | Format-List Number,FriendlyName,BusType,Size,PartitionStyle,IsReadOnly,IsOffline,IsBoot,IsSystem
```

The important output line is:

```text
IsReadOnly : True
```

Do not continue otherwise.

### 6. Perform inspection while the disk is read-only

```powershell
python .\tools\inspect-aura-hd.py --hash-boot --verbose
```

The script itself does not write anything, and the device now has a second Windows-side barrier.

### 7. Take the disk offline when raw inspection is complete

After inspection, the disk can be taken offline to reduce normal filesystem exposure further:

```powershell
$report = (python .\tools\inspect-aura-hd.py --json | ConvertFrom-Json)
$matches = @($report.results | Where-Object { $_.aura_hd -eq $true })
if ($matches.Count -ne 1) { throw "STOP: exactly one confirmed Aura HD is required." }
if ($matches[0].source -notmatch 'PhysicalDrive([0-9]+)$') { throw "STOP: unexpected Windows PhysicalDrive source." }
$diskNumber = [int]$Matches[1]
$disk = Get-Disk -Number $diskNumber
if (-not $disk.IsReadOnly) { throw "STOP: disk is not confirmed read-only." }
if ($disk.IsBoot -or $disk.IsSystem) { throw "STOP: boot/system disk refused." }
Set-Disk -Number $diskNumber -IsOffline $true
Get-Disk -Number $diskNumber | Format-List Number,FriendlyName,IsReadOnly,IsOffline
```

Expected state:

```text
IsReadOnly : True
IsOffline  : True
```

Offline mode is mainly useful when the card must remain connected between operations. It is not presented as a physical guarantee against writes; a hardware write blocker remains the stronger option.

### 8. After removing the card

Restore normal Windows automount behavior:

```powershell
mountvol /E
```

## After a reboot or power loss

Do not resume by trusting the previous state.

Start the full sequence again:

1. Windows booted;
2. automount disabled;
3. card inserted;
4. Aura HD identified;
5. `IsReadOnly` applied and read back;
6. only then inspect.

If the card remained connected through a reboot or power loss, absence of Windows writes is **not proven**. Recheck at least the partition geometry, HWCONFIG and known hashes before continuing.

## What each protection provides

| Protection | What it does | What it does not guarantee |
|---|---|---|
| `mountvol /N` | disables automount of newly discovered volumes | does not block raw writes |
| `Set-Disk -IsReadOnly $true` | asks Windows to treat the disk as read-only | must not be assumed persistent across re-enumeration/reboot |
| `Set-Disk -IsOffline $true` | removes volumes from normal Windows access paths | may need to be undone for some low-level operations |
| PimpMyKobo tools | never open the source for writing | do not control host OS behavior |
| hardware write blocker | blocks writes at the hardware/interface level | requires dedicated equipment |

## Project rule

For any future sensitive operation:

> A protection state is never assumed to persist. It must be verified again after every reconnect, re-enumeration, reboot or power loss.
