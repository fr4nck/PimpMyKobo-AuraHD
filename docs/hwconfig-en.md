# Netronix HWCONFIG — Kobo Aura HD

[Français](hwconfig-fr.md) | **English**

## Observed location

The hardware configuration block is located at:

    524288 bytes
    0x80000

Observed signature:

    HW CONFIG v1.7

## Structure

The studied header contains:

    char cMagicNameA[10];
    char cVersionNameA[5];
    unsigned char bHWConfigSize;

On the analyzed device:

- version: `v1.7`
- declared size: 39 bytes
- first payload byte: `bPCB = 0x1c = 28`

## PCB identification

The Netronix table maps:

    28 -> E606C0

Okreader also maps `E606C0` to the `dragon` codename and the Aura HD model.

## Confirmed trailing fields

Successive versions add, among others:

- v1.0: `DisplayResolution`
- v1.1: `FrontLight`
- v1.2: `CPUFreq`
- v1.3: `HallSensor`
- v1.4: `DisplayBusWidth`
- v1.5: `FrontLight_Flags`
- v1.6: `PCB_Flags`
- v1.7: `FrontLight_LED_Driver`

Observed values:

| Field | Raw | Meaning |
|---|---:|---|
| DisplayResolution | 3 | 1440 × 1080 |
| FrontLight | 6 | `TABLE3+` |
| CPUFreq | 2 | 1 GHz |
| HallSensor | 1 | `TLE4913` |
| DisplayBusWidth | 3 | `16Bits_mirror` |
| FrontLight_Flags | 0 | no flags |
| PCB_Flags | 1 | `NO_KeyMatrix` |
| FrontLight_LED_Driver | 0 | `SY7201` |

## Caution

The HWCONFIG format evolved across Netronix/Kobo generations. A decoder must always account for the version and size declared in the header.

The project treats the original HWCONFIG as critical hardware data that should be backed up and preserved.
