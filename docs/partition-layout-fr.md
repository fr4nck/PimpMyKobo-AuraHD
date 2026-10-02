# Partitionnement observé — Kobo Aura HD

**Français** | [English](partition-layout-en.md)

Disposition observée sur la microSD interne de l'Aura HD étudiée.

| Partition | Offset | Taille | Système | Rôle |
|---|---:|---:|---|---|
| P1 | 9 961 472 | 268 435 968 | ext4 | `rootfs` |
| P2 | 278 397 440 | 268 435 968 | ext4 | `recoveryfs` |
| P3 | 546 833 408 | 31 368 150 016 | FAT32 | `KOBOeReader` |

La zone précédant P1 fait 9 961 472 octets et contient des données de bas niveau nécessaires au démarrage.

## Règle de sécurité

Les valeurs ci-dessus documentent l'exemplaire étudié. Un outil automatisé doit lire et valider la table de partitions réelle avant toute opération d'écriture.

Il doit au minimum vérifier :

1. la taille physique du support ;
2. le style de partitionnement ;
3. les offsets ;
4. les tailles ;
5. le HWCONFIG ;
6. l'identification E606C0 lorsque cette cible est requise ;
7. l'intégrité des sauvegardes ;
8. l'intégrité de l'image reconstruite.

Le mode par défaut doit rester en lecture seule.
