# PMKB — LOT 01-A : matrice FIRST BOOT et conditions de preuve

**Relevé : 25 octobre 2026.** Périmètre : inventaire opérationnel des barrières FIRST BOOT de la Kobo Aura HD N204 / `dragon` / E606C0, **sans reconstruction, téléchargement, écriture sur support ni démarrage**. Il ne constitue **pas** une autorisation de manipulation matérielle.

## Révisions et références contrôlées

- `main@a53f9f9f9968bb65c9d8b18bd51fb96a835985e2` au début du lot.
- PR [#7 FIRST BOOT](https://github.com/fr4nck/PimpMyKobo-AuraHD/pull/7) : ouverte, non fusionnée, `integration/pmkb-first-boot-1@6b0506a085c3f19d818f71fbeebcd7c8da8c3abf`. [État de convergence](https://github.com/fr4nck/PimpMyKobo-AuraHD/blob/6b0506a085c3f19d818f71fbeebcd7c8da8c3abf/docs/pmkb-first-boot-1-fr.md) ; ses recettes sont des descriptions historiques, **pas des commandes à exécuter dans ce lot**.
- PR [#28 PowerLab/R2](https://github.com/fr4nck/PimpMyKobo-AuraHD/pull/28) : ouverte, **draft**, `feat/pmkb-powerlab-kernel-v0@f74fbc0335fc22c6188f752e9526eca66704a41e`. [BOOT CONTRACT V1](https://github.com/fr4nck/PimpMyKobo-AuraHD/blob/f74fbc0335fc22c6188f752e9526eca66704a41e/docs/boot-contract-v1-fr.md), [audit R2/émulateur](https://github.com/fr4nck/PimpMyKobo-AuraHD/blob/f74fbc0335fc22c6188f752e9526eca66704a41e/docs/emulation-e606c0-r2-fr.md).
- `main` : [partitionnement observé](partition-layout-fr.md), [conditions de boot / watchdog](offline-boot-gates-fr.md) et [règles AGENTS](../AGENTS.md). Les constats historiques tirés de sauvegardes et de sources sont **des preuves documentaires antérieures**, pas de nouvelles mesures du LOT 01-A.

**Convention :** `DOCUMENTÉ` = cohérence des fichiers/contrats lue dans GitHub ; `TEST HÔTE RAPPORTÉ` = essai décrit dans un document existant, non réexécuté ici ; `INCONNU` = preuve absente ; `À QUALIFIER PHYSIQUEMENT` = essai sur Aura HD nécessaire. Aucun de ces termes ne signifie `PASS matériel`.

## Intégrité, géométrie et séparation des supports

L'image FIRST BOOT déjà scellée est **`PMKB-FIRST-BOOT-1-0b00d858.img`**, taille déclarée **268 435 968 octets**, SHA-256 déclaré **`7980fec15cb62ca3c2cabcb64cbbb683446fbf64070d75b45acf9a5e99e0f67c`** (source R2). Elle n'a **pas** été ouverte ou re-hachée ici. La correspondance binaire avec le HEAD actuel de la PR #7 n'est **pas** établie par la seule lecture de GitHub : **ne jamais la supposer**.

| Zone / partition | Offset documenté | Taille documentée | Protection et preuve |
| --- | ---: | ---: | --- |
| PRE-P1 : MBR, U-Boot, HWCONFIG, uImage, waveform | 0 | 9 961 472 octets | **IMMUTABLE** ; emplacements historiques connus, binaire effectif et transfert RAM encore à prouver |
| P1 `rootfs` (ext4) | 9 961 472 | 268 435 968 octets | Seule zone système candidate ; utiliser une **copie**, ne jamais altérer l'image scellée |
| P2 `recoveryfs` (ext4) | 278 397 440 | 268 435 968 octets | **IMMUTABLE**, restaurateur potentiellement destructif : ne jamais l'exécuter pour amorcer PMKB |
| P3 `KOBOeReader` (FAT32) | 546 833 408 | 31 368 150 016 octets | Stockage livres/données ; conserver chemin Calibre, contrôler le partage USB exclusif |

Les offsets proviennent du partitionnement **observé sur l'exemplaire**, pas d'une disposition universelle Kobo. Le profil **QEMU `virtual-qemu` 1 Gio** de R2 conserve les offsets de P1/P2 mais **redimensionne P3** ; son banc ne se confond pas avec la carte de remplacement physique de 32 Go ni avec `replace-microsd-linux.py` de la PR #7.

## Matrice des portes de qualification

| Gate | Résultat documentaire au 25/10 | Preuve disponible et limite | Critère encore requis |
| --- | --- | --- | --- |
| G01 — identité E606C0 | **DOCUMENTÉ** | HWCONFIG réel rapporté : PCB 28, i.MX507, écran 1080×1440 ; remappage Netronix 28→11 ≠ machine ID ARM | Confirmation sur support de test lors d'une opération distinctement autorisée |
| G02 — intégrité P1 scellée | **EMPREINTE CONNUE, NON REVÉRIFIÉE** | Nom/taille/SHA publiés dans R2, fichier privé absent de cette session | SHA-256 calculé sur **copie locale autorisée** et concordance, avant toute étape expérimentale |
| G03 — préservation PRE-P1/P2 | **CONTRAT DOCUMENTÉ** | R2 teste la copie à l'identique sur fichiers **synthétiques** ; pas de données privées relues ici | Comparaison SHA et zones protégées sur copies réelles ; aucun accès physique en écriture |
| G04 — U-Boot / uImage / handoff | **INCONNU POUR LE BINAIRE EFFECTIF** | Offset HWCONFIG 0x80000, uImage 0x100000, waveform 0x700000 rapportés ; CRC historiques du uImage ; ID 2988 uniquement inféré des sources et de QEMU sans `-bios` | IH_LOAD/IH_EP, place U-Boot, adresse RAM, r0/r1/r2, ATAG/cmdline et préservation de waveform à relever ; ne pas déduire des offsets disque des adresses RAM |
| G05 — P1 ext4 / constructeur | **OUTILS INTÉGRÉS À #7** | `build-koreader-rootfs` + structure minimaliste, droits bootstrap et répertoires ; construction Linux réelle citée dans la PR, mais pas reconstruite ici | Rejouer le builder sur ressources locales autorisées, comparer manifests, contenu et empreintes sans altérer l'image scellée |
| G06 — ABI ARM / liens ELF | **OUTIL ET CORRECTIF DOCUMENTÉS** | `audit-arm-runtime` résout `$ORIGIN` de façon bornée et vérifie scripts/stockage ; tests anciens rapportés | Audit du véritable arbre assemblé à partir des binaires et bibliothèques de l'image candidate ; aucune conclusion d'exécution ARM à partir d'un test synthétique |
| G07 — init et démarrage KOReader | **CHEMIN STATIQUE DOCUMENTÉ** | `rcS`, `pmkb-reader`, `pmkb-check-onboard` dans #7 ; dernier contrôle P3 juste avant `exec` ; démarrage direct de `reader.lua` | Vérifier l'exécution réelle des scripts, nœuds et capacités après boot autorisé |
| G08 — indépendance Nickel | **CONTRÔLE HÔTE RAPPORTÉ** | #7 installe `defaults.custom.lua` ; `KOBO_LIGHT_ON_START=-1` et `KOBO_SYNC_BRIGHTNESS_WITH_NICKEL=false` ; deux chemins Nickel évités dans tests Lua isolés | Contrôler la présence et les valeurs dans **l'image exacte** et l'absence d'accès Nickel au démarrage réel ; ne pas assimiler tous les plugins au chemin audité |
| G09 — montage P3 | **GARDE LOGICIEL EXISTANTE** | L'outil vérifie `/proc/mounts` avant lancement ; modèle FAT32 R2 synthétique | Montage réel de P3, cohérence périphérique/partition et accès livres ; contrôle `p3_mount` du préflight reste `UNQUALIFIED` |
| G10 — écran EPDC | **INTERFACE IDENTIFIÉE ; MATÉRIEL NON QUALIFIÉ** | Noyau 2.6.35.3 + waveform en RAM, ioctls MXCFB ; apparition de `fb0` **ne garantit pas** `hw_ready` | Profondeur, rotation, rafraîchissement, attente effective et lisibilité sur Aura HD |
| G11 — ZForce tactile | **INTERFACE IDENTIFIÉE ; MATÉRIEL NON QUALIFIÉ** | Neonode v2, entrée `zForce-ir-touch` ; un numéro `eventN` ne constitue **pas** son identité | Contact, relâchement, coordonnées, ordre des entrées, reprise après veille |
| G12 — frontlight NTX/MSP430 | **INTERFACE IDENTIFIÉE ; MATÉRIEL NON QUALIFIÉ** | `ntx_io` / ioctl 241 ; présence sysfs et version MCU ne démontrent pas la lumière | Extinction, paliers, bouton, état après veille ; ne pas remplacer par GPIO improvisé |
| G13 — USB / Calibre | **À QUALIFIER PHYSIQUEMENT** | Exigence V1 conservée dans AGENTS ; aucun test end-to-end relevé | Accès exclusif à P3, import Calibre, livre visible et lisible par KOReader |
| G14 — watchdog / veille / Wi-Fi | **INCONNU** | `mxc_wdt_disable` est vide dans les sources analysées ; état MSP430 inconnu. Déclarations « hors ligne » ≠ radio physiquement coupée | Stabilité sans ouverture intrusive de `/dev/watchdog`, comportement énergétique et reprise **après** boot ; réseau à la demande |
| G15 — QEMU E606C0 | **OUTILLAGE SYNTHÉTIQUE RAPPORTÉ** | R2 : analyseur PRE-P1 + assembleur `virtual_card.py`, copie P1/P2 conservée sur données synthétiques | U-Boot privé/artefacts autorisés, QEMU construit **avec autorisation de téléchargement**, exécution en snapshot et journal console ; un boot QEMU ≠ essai E-Ink physique |

Le `preflight-koreader` de la PR #7 contient **six gates explicitement `UNQUALIFIED`** : `framebuffer`, `touch`, `frontlight`, `p3_mount`, `usb_calibre`, `hardware_boot`. **Interdit de transformer leur présence dans un JSON ou des tests synthétiques en `PASS`.**

## Preuves et divergences recoupées

- La documentation de la PR #7 **rapporte** 315 tests Windows, 0 échec et 59 ignorés, ainsi qu'un préflight synthétique et des correctifs d'audit ELF/Nickel. **Non réexécutés et aucune CI recontrôlée dans L01-A**.
- Le rapport R2 **rapporte** 12/12 tests d'analyse PRE-P1, 11/11 tests d'assembleur, 16/16 mutants détectés pour celui-ci, et une suite complète de 344 tests exécutés (15 SKIP) au dernier état cité. Ce ne sont **pas** les résultats de cette exécution L01-A.
- R2 documente un profil virtuel de 1 Gio et la lecture FAT32 de la carte **synthétique**, mais **ni boot émulé, ni passage réel U-Boot → Linux → KOReader**.
- Les anciens documents `offline-boot-gates-fr.md` / `offline-hardware-qualification-fr.md` décrivent encore les deux réglages anti-Nickel comme « proposition séparée » de l'image v3. **Ce constat historique précède leur intégration dans le builder de la PR #7** ; ne pas conclure que l'image FIRST BOOT scellée a nécessairement été reconstruite avec ces réglages.
- Le `BOOT CONTRACT V1` de la PR #28 est volontairement déclaratif : `consistent_unverified` n'est **pas** un boot validé. Un noyau 6.18 et un DTS Kobo Aura N514 ne constituent pas une solution de remplacement démontrée pour E606C0.

## Décision L01-A et sortie

**Satisfait sur le papier :** géométrie de référence, garde de P2/PRE-P1, outillage constructeur/audit/préflight, neutralisation des deux chemins Nickel identifiés, analyseur et carte virtuelle synthétique sans outil installable sur Kobo.

**Non satisfait :** preuve de concordance `image scellée ↔ code actuel`, contrôle de la vraie PRE-P1/U-Boot, champs IH_LOAD/IH_EP et r1/r2 effectifs, lancement réel du noyau/KOReader et observation E-Ink/tactile/lumière/USB. **GO matériel = NON ACCORDÉ** par ce document.

**Sous-lot suivant L01-B :** examiner seulement les tests et le code de `preflight-koreader` de la PR #7 pour vérifier que les six gates matérielles ne peuvent jamais être promues abusivement en PASS, et qu'un défaut de P3 refuse correctement le lancement. Si lacune démontrée, ajouter une fixture/test synthétique minimal sur la branche #7 ; sinon consigner l'absence de défaut. Aucun matériel, aucun téléchargement et aucune fusion.

**Bilan L01-A :** consultation statique GitHub, **0 tests exécutés, 0 CI déclenchée, 0 test matériel, 0 code changé**, une matrice documentaire publiable. Ne pas modifier les images ou les PR existantes dans ce sous-lot.
