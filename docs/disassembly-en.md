# Kobo Aura HD disassembly

[Français](disassembly-fr.md)

This guide explains how to open a **Kobo Aura HD / N204** in order to reach its **internal system microSD card**.

The procedure is based on our own disassembly of a real Aura HD and then **cross-checked against iFixit and MobileRead**, with sources attached to each relevant step.

> **Project rule:** external technical information is cited; observations made directly on the PimpMyKobo-AuraHD device are identified as such.

## Before you start

Power the reader off completely and disconnect USB.

Recommended tools:

- plastic spudger, guitar pick or thin plastic card;
- precision Phillips screwdriver;
- clean, flat, non-conductive work surface;
- microSD reader for the later backup stage.

Avoid metal tools when opening the case whenever possible. The E-Ink panel is mechanically fragile and should not be flexed.

## Operation map

```text
      KOBO AURA HD
           |
           v
  +-------------------+
  | front bezel       |
  +-------------------+
           |
       unclip it
           v
  +-------------------+
  | 4 internal screws |
  +-------------------+
           |
       remove them
           v
  +-------------------+
  | display + PCB     |
  +-------------------+
           |
   lift from rear case
           v
  +-------------------+
  | back of PCB       |
  |                   |
  | [system microSD]  | <--- target
  +-------------------+
```

The ASCII diagrams are part of the documentation rather than decoration: this guide remains understandable in text browsers such as **Lynx** even when no image is displayed.

---

## 1. Remove the front bezel

Start at a corner with a thin plastic tool and work slowly around the edge, releasing clips one after another instead of pulling hard on the bezel.

```text
Simplified side view

       front bezel
   __________________
  /                  \
 /____________________\
   ^  ^  ^  ^  ^  ^
      plastic clips

   +------------------+
   |    rear case     |
   +------------------+
```

The MobileRead wiki reports **at least six latches along each long edge**, plus double-sided tape between the bezel and display. iFixit starts at the bottom-right corner with a plastic spudger and works along the bottom and around the device.

**Sources:**

- iFixit — [Kobo Aura HD Screen Replacement](https://www.ifixit.com/Guide/Kobo+Aura+HD+Screen+Replacement/96135), step 1.
- MobileRead Wiki — [Aura HD](https://wiki.mobileread.com/wiki/Aura_HD), *Hacking* section.
- MobileRead Forum — [Aura HD Replacing internal SD card?](https://www.mobileread.com/forums/showthread.php?t=214272).

---

## 2. Remove the four screws holding the electronics assembly

After the bezel is removed, four screws near the corners hold the **display + motherboard assembly** to the rear case.

```text
   o----------------------o
   |                      |
   |       display        |
   |                      |
   o----------------------o

   o = screw to remove
```

MobileRead calls these **PH00** screws; iFixit specifies **Phillips #000**. Those names are close but not exactly identical, so use the precision bit that properly fills the screw head without forcing it.

**Sources:**

- iFixit — [Kobo Aura HD Screen Replacement](https://www.ifixit.com/Guide/Kobo+Aura+HD+Screen+Replacement/96135), step 2.
- MobileRead Wiki — [Aura HD](https://wiki.mobileread.com/wiki/Aura_HD).

---

## 3. Lift the display + motherboard assembly from the rear shell

Once the four screws are out, the electronics assembly can be removed from the back plate.

You do **not** need to separate the display from the motherboard to reach the system microSD card.

```text
          FRONT
     +-------------+
     | E-Ink panel |
     +-------------+
           ||
           \/
     +-------------+
     | motherboard |
     +-------------+
          BACK
```

**Source:**

- iFixit — [Kobo Aura HD Screen Replacement](https://www.ifixit.com/Guide/Kobo+Aura+HD+Screen+Replacement/96135), step 2.

---

## 4. Disconnect the battery before handling the microSD

This reduces the risk of shorting the board or manipulating storage while the motherboard is still powered.

The battery connector is lifted **perpendicular to the motherboard**. Do not pull on the wires.

```text
          battery wires
              ||
          [connector]
              ^
              |
          lift upward

  ============================  motherboard
```

**Source:**

- iFixit — [Kobo Aura HD Screen Replacement](https://www.ifixit.com/Guide/Kobo+Aura+HD+Screen+Replacement/96135), step 3.

---

## 5. Identify the internal system microSD

The Aura HD uses a **removable microSD card as system storage**. MobileRead places it on the **back side of the board**, i.e. the side opposite the display.

```text
Back of motherboard — functional map

+------------------------------------------------+
|                                                |
|  [ SYSTEM microSD ]                            |
|       ^                                        |
|       +---- boot / rootfs / recovery           |
|                                                |
|                         [ battery ]             |
|                                                |
|        electronics / CPU / RAM / controllers   |
|                                                |
|                               [USB] [ext. microSD]
+------------------------------------------------+
```

### Do not confuse the two microSD roles

```text
INTERNAL SYSTEM microSD
  -> contains the Kobo system
  -> rootfs / recoveryfs / KOBOeReader
  -> should be backed up before modification

USER EXPANSION microSD SLOT
  -> accessible from the outside edge
  -> located near the USB connector
  -> is NOT the system card
```

This distinction was directly confirmed on the PimpMyKobo-AuraHD device.

**Sources:**

- MobileRead Wiki — [Aura HD](https://wiki.mobileread.com/wiki/Aura_HD).
- MobileRead Forum — [Aura HD Accessible Internal uSD card](https://www.mobileread.com/forums/showthread.php?t=217702).
- MobileRead Forum — [Aura HD Replacing internal SD card?](https://www.mobileread.com/forums/showthread.php?t=214272).

---

## 6. Remove the system microSD

With the battery disconnected, remove the card without bending it or forcing the socket.

Do not write anything to it yet.

PimpMyKobo-AuraHD recommends **read-only inspection first**, followed by a **full backup** before any repair attempt.

Continue with:

1. [Inspect the microSD read-only](inspect-aura-hd-en.md)
2. [Recover the recovery files](recover-files-en.md)
3. [Verify `recoveryfs`](verify-recovery-en.md)
4. [Understand the rescue procedure](rescue-en.md)

A 2015 MobileRead report explicitly describes recovering books and the `.kobo` directory after removing the Aura HD internal microSD from a device with an unusable touchscreen.

**Source:**

- MobileRead Forum — [how to recover aura hd internal sd data on a broken screen?](https://www.mobileread.com/forums/showthread.php?t=266182).

---

## 7. Reassembly and touchscreen test

Reassemble in reverse order.

One important trap: **the touchscreen may not respond until the front bezel is reinstalled**. Both iFixit and MobileRead document this behavior.

Do not immediately diagnose a failed touchscreen when testing the reader while it is still open.

**Sources:**

- iFixit — [Kobo Aura HD Screen Replacement](https://www.ifixit.com/Guide/Kobo+Aura+HD+Screen+Replacement/96135), step 10.
- MobileRead Wiki — [Aura HD](https://wiki.mobileread.com/wiki/Aura_HD).

---

## Text-browser and accessibility design

This guide is intentionally usable without graphics:

- all essential instructions are written out;
- critical layouts are reproduced as ASCII diagrams;
- project photographs are intended to receive meaningful alt text;
- no step depends solely on arrows or annotations in a picture.

Classic ASCII is preferred over Unicode braille-art because it is more robust across Lynx, SSH sessions, serial consoles and old terminals. A real refreshable braille display can still present the textual content through the user's accessibility stack.

---

## Sources and acknowledgements

This documentation does not claim discovery of the Aura HD opening method.

It combines:

- our own real-world disassembly of the PimpMyKobo-AuraHD device;
- the iFixit **Kobo Aura HD Screen Replacement** guide;
- the **MobileRead Wiki — Aura HD** page;
- historical MobileRead forum reports about opening the case and accessing the internal microSD.

### Main references

- iFixit — https://www.ifixit.com/Guide/Kobo+Aura+HD+Screen+Replacement/96135
- MobileRead Wiki — https://wiki.mobileread.com/wiki/Aura_HD
- MobileRead — https://www.mobileread.com/forums/showthread.php?t=214272
- MobileRead — https://www.mobileread.com/forums/showthread.php?t=217702
- MobileRead — https://www.mobileread.com/forums/showthread.php?t=266182

The MobileRead Aura HD wiki page credits Dale DePriest, Chris Ridd and an anonymous contributor, and states that its content is available under **Creative Commons Attribution-NonCommercial-ShareAlike**.

Original photographs intended for this guide come from the actual Aura HD disassembled for **PimpMyKobo-AuraHD**; they do not reproduce iFixit or MobileRead photography.

Photos: © Franck, 2026 — used within the PimpMyKobo-AuraHD project.
