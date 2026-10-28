# PMKB — FBInk : audit complémentaire de ses forks et de son écosystème

**Audit statique : 25 octobre 2026.** Source canonique [NiLuJe/FBInk](https://github.com/NiLuJe/FBInk), `master` `886f25f13368859ad8a899b88d04c26e19cda32e` (dernier commit **6 août 2026**). Bibliothèque C et CLI e-ink/framebuffer/EPDC, licence **GPL-3.0-or-later**. **Déjà étudiée** pour la HAL dans [R1/R3](kernel-community-audit-2026-10-24-fr.md) et dans le [registre des sources](recherche-sources-fr.md). Le présent dossier vérifie **ce qui manque : ses forks et le code spécifique à Aura HD**. Cible PMKB : **Kobo Aura HD N204 / dragon / E606C0 / 1440×1080 / 512 Mio**.

## 1. Nombre réel des forks et comparaison Git

La métadonnée officielle GitHub de `NiLuJe/FBInk` indique **31 forks** au 25 octobre 2026 (`forks_count=31`). La recherche nominative a renvoyé **32 dépôts publics appelés FBInk/fbink hors parent**. Le dépôt [squaremoshi/FBInk](https://github.com/squaremoshi/FBInk) est un **homonyme sans rapport**, affichant le README du CMS PHP GetSimple : GitHub le marque `fork=false` et la comparaison Git échoue. **Il reste donc 31 forks publics de FBInk, tous comparés** à `NiLuJe:master` sur leur branche principale.

| État des 31 forks | Nombre | Dépôts et portée |
| --- | ---: | --- |
| **En retard, 0 commit supplémentaire sur master** | **26** | [gandro](https://github.com/gandro/FBInk) · [yparitcher](https://github.com/yparitcher/FBInk) · [esrodi](https://github.com/esrodi/FBInk) · [ivy-rew](https://github.com/ivy-rew/FBInk) · [cwybruce](https://github.com/cwybruce/FBInk) · [RolandMa1986](https://github.com/RolandMa1986/FBInk) · [pazos](https://github.com/pazos/FBInk) · [taphier](https://github.com/taphier/FBInk) · [4gra](https://github.com/4gra/FBInk) · [lgtm-migrator](https://github.com/lgtm-migrator/FBInk) · [stefan9090](https://github.com/stefan9090/FBInk) · [OrigamiEngineer](https://github.com/OrigamiEngineer/FBInk) · [Szybet](https://github.com/Szybet/FBInk) · [Rain92](https://github.com/Rain92/FBInk) · [shermp](https://github.com/shermp/FBInk) · [zhyh329](https://github.com/zhyh329/FBInk) · [fulldecent](https://github.com/fulldecent/FBInk) · [iCodeIN](https://github.com/iCodeIN/FBInk) · [tcrs](https://github.com/tcrs/FBInk) · [throwoutofcoffeeexception](https://github.com/throwoutofcoffeeexception/FBInk) · [Quill-OS](https://github.com/Quill-OS/FBInk) · [wesley6j](https://github.com/wesley6j/FBInk) · [fuzzyghosty](https://github.com/fuzzyghosty/FBInk) · [hewenhao2008](https://github.com/hewenhao2008/FBInk) · [stdyg](https://github.com/stdyg/FBInk) · [GallenLin](https://github.com/GallenLin/FBInk). Ce sont des instantanés historiques ; aucune nouveauté propre sur `master`. Certaines conservent des branches de travail historiques, étudiées séparément ci-dessous. |
| **Identique (0 ahead, 0 behind)** | **1** | [benoit-pierre/FBInk](https://github.com/benoit-pierre/FBInk) : miroir du HEAD canonique. |
| **En avance de 2 commits** | **1** | [JuanDavid9905/fbink](https://github.com/JuanDavid9905/fbink) : **2 modifications de `.github/workflows/build.yaml`**, datées du **3 septembre 2026** ; **aucune modification du cœur C**. |
| **Branches principales divergentes** | **3** | [Ramblurr/FBInk](https://github.com/Ramblurr/FBInk) (**+1 / −15** : environnement/package **Nix**, 4 fichiers d'outillage), [mlapaglia/FBInk](https://github.com/mlapaglia/FBInk) (**+2 / −15** : workflow de release, 1 fichier CI), [KindleModding/FBInk](https://github.com/KindleModding/FBInk) (**+11 / −8** : workflow CI et `.gitmodules`, 2 fichiers). Aucune de ces divergences de `master` n'apporte un correctif EPDC/ZForce propre à l'Aura HD. |

**Conclusion du balayage : aucune amélioration fonctionnelle Aura HD démontrée sur le `master` des 31 forks.** Les compteurs `ahead`/`behind` indiquent une filiation Git et l'avancée d'une branche, **pas** des PASS matériels, ni 31 propositions techniques différentes.

## 2. Branches annexes avec modifications, et leurs limites

Les branches des **31 forks** ont été inventoriées. Une très grande partie des noms `fonts`, `image`, `kobo16`, `kobo-boot-rota`, `kobo-viewport`, `raw-scanlines`, `sunxi-kobo`, etc., sont **partagés avec le dépôt original** et ne constituent pas à eux seuls de nouveaux travaux des forks.

| Branche annexe réellement examinée | Écart / constat | Valeur PMKB |
| --- | --- | --- |
| [taphier/FBInk:master2](https://github.com/taphier/FBInk/tree/master2) | **+1** vs son `master` : ajout d'un contrôleur **MediaTek MT8115**, d'un en-tête `eink/mt8115-kobo.h` marqué `MediaTekProprietary` et de modifications à `fbink.c`. Branche expérimentale 2025. | **ÉCARTER** pour i.MX507/dragon. **Ne pas copier** d'en-tête propriétaire, et aucune preuve d'une amélioration Aura HD. |
| [KindleModding/FBInk:in-memory-fonts](https://github.com/KindleModding/FBInk/tree/in-memory-fonts) | Variante **+5 / −45** par rapport à son master, avec nouvelles API `fbink_add_ot_font_from_memory` et `..._v2` absentes de `NiLuJe:master` consulté. Charge des polices depuis un pointeur mémoire **sans longueur de buffer dans la signature publique** ; la validation des limites n'est pas démontrée. | **IDÉE** pour les ressources embarquées dans des paquets `*.pmkb`, mais **NE PAS IMPORTER**. Sûreté et modèle mémoire à spécifier séparément, après FIRST BOOT. |
| [yparitcher/FBInk:marker](https://github.com/yparitcher/FBInk/tree/marker) | **+1** vs sa branche master (2022) : garde empêchant les animations swipe si région plus petite que le nombre de pas, pour **Kindle Paperwhite MediaTek**. | Principe générique de **bornage des rectangles**, déjà attendu dans notre HAL ; **pas un pilote Kobo E606C0**. |
| [shermp/FBInk:go-bindings](https://github.com/shermp/FBInk/tree/go-bindings) | **+4** commits : wrappers/liaisons Go dans `gofbink/`. | **INSPIRATION outillage** seulement ; ne pas imposer cgo/Go à notre socle Linux frugal. |
| [mlapaglia:hard-float](https://github.com/mlapaglia/FBInk/tree/hard-float), [ivy-rew:latest](https://github.com/ivy-rew/FBInk/tree/latest), [lgtm-migrator:codeql](https://github.com/lgtm-migrator/FBInk/tree/codeql), [fulldecent:patch-8](https://github.com/fulldecent/FBInk/tree/patch-8) | Configurations CI, packages et retouches anciennes d'aide CLI. | Aucun correctif matériel à retenir. |

**Méthode :** HEAD, diffs de `compare_commits`, quelques commits/fichiers de branches secondaires ; **ce n'est pas** une revue de toutes les lignes de tous les arbres. Pas de tests upstream relancés. Les branches de fork peuvent être abandonnées et contenir du code dangereux : privilégier systématiquement le master récent de NiLuJe.

## 3. FBInk et notre Aura HD : précision nouvelle sur les quirks

[Code canonique `fbink_device_id.c`](https://github.com/NiLuJe/FBInk/blob/886f25f13368859ad8a899b88d04c26e19cda32e/fbink_device_id.c), `case DEVICE_KOBO_AURA_HD` :

- `deviceName = "Aura HD"`, `deviceCodename = "Dragon"`, `devicePlatform = "Mark 4"`, **265 ppp**.
- `isKoboNonMT = true` : **profil d'entrée historique à un contact**, qui ne doit **pas** être interprété comme une démonstration de l'impossibilité de modifications expérimentales du pilote ZForce.
- `ntxBootRota = FB_ROTATE_UR` ; `ntxRotaQuirk = NTX_ROTA_ALL_INVERTED`.
- **Correspondance interne des quatre rotations** : `FB_ROTATE_UR → FB_ROTATE_CW`, `FB_ROTATE_CW → FB_ROTATE_UR`, `FB_ROTATE_UD → FB_ROTATE_CCW`, `FB_ROTATE_CCW → FB_ROTATE_UD`. **Ce sont les conventions internes du code FBInk**, à tester contre les rotations physiques/réelles de notre noyau et de PMKB-UI ; **ne pas copier comme un mapping tactile final** sans qualification.
- La référence officielle [`fbink_input_scan`](https://github.com/NiLuJe/FBInk/blob/master/fbink_input_scan.c) classifie les `/dev/input/event*` d'après leurs capacités : bonne **méthode de découverte dynamique** plutôt que de figer `event0` ou `event2`.

Le socle PMKB doit préserver sa HAL indépendante : **HWCONFIG E606C0 effectivement lu et validé** > identifiants déduits des tables de fournisseurs ; [fiche matérielle](hardware-fr.md), [HWCONFIG](hwconfig-fr.md) et [tests de première qualification](kernel-community-audit-2026-10-24-fr.md). La rotation et les waveforms dépendent de l'ABI **effective** du noyau installé.

### Frugalité concrète

Le [README canonique](https://github.com/NiLuJe/FBInk/blob/master/README.md) prévoit `MINIMAL=1` avec réactivation ciblée de `DRAW`, `BITMAP`, `IMAGE`, `OPENTYPE` et `INPUT` ; `fbink_refresh_rect` offre un contrat de rafraîchissement par rectangle, et `fbink_input_scan` une classification des entrées. **Choisir uniquement les fonctionnalités nécessaires** et mesurer en cible l'empreinte binaire, les dépendances dynamiques, le RSS, l'invalidation partielle et l'énergie. Aucun résultat de RAM/CPU sur **notre** Aura HD n'a été mesuré : **pas de nombre inventé**.

**Droits :** FBInk et ses liaisons sont principalement **GPLv3+**, avec éléments tiers selon leurs licences. Une incorporation ou liaison à PMKB doit respecter les obligations de licence pertinentes ; le **simple audit de comportement** n'intègre aucun code tiers.

## 4. Écosystème adjacent : ce ne sont PAS des forks du cœur FBInk

Quelques projets **utilisant** FBInk méritent d'être conservés comme sources d'idées **Store**, sans les ajouter au chiffre des 31 forks :

| Projet | Ce qui est effectivement documenté | Priorité PMKB |
| --- | --- | --- |
| [NiLuJe/lua-fbink](https://github.com/NiLuJe/lua-fbink) | Liaison **LuaJIT FFI**, adaptée à des applications Lua de type KOReader | **P2** : possible passerelle facultative, pas une dépendance de PMKB-UI |
| [NiLuJe/py-fbink](https://github.com/NiLuJe/py-fbink) | Liaison **Python cFFI** : pratique pour des prototypes sur hôte | **P2**, pas un runtime Python obligatoire sur 512 Mio |
| [shermp/go-fbink-v2](https://github.com/shermp/go-fbink-v2) | Bibliothèque Go + cgo, déclarée liée à **FBInk 1.23.0**, avec archive C statique distribuée dans le projet | **P2** si un paquet Go justifie vraiment ABI/tailles, pas au boot |
| [sublipri/fbink-rs](https://github.com/sublipri/fbink-rs) | Liaison Rust `bindgen` **unsafe**, wrapper sûr explicitement **incomplet** dans son README ; dépend d'un outil de compilation croisée | **INFO** : pas de garantie d'API sûre ni de petit binaire |
| [Quill-OS/egui-fbink](https://github.com/Quill-OS/egui-fbink) | Piste egui/Rust, README très sommaire, aucun fonctionnement E606C0 démontré | **INFO / UI lourde non justifiée** |
| [kintsugi-computer/kobo-fbink](https://github.com/kintsugi-computer/kobo-fbink) | Packaging **Alpine APK** dans un chroot, testé selon l'auteur sur **Kobo Aura N514** (pas Aura HD N204) | **INFO / packaging** seulement : **APK signifie ici paquet Alpine, pas Android ni format PMKB** |
| [schuhumi/fbink-xdamage](https://github.com/schuhumi/fbink-xdamage) | Rafraîchissement via **XDamage/X11** sur Kindle | **ÉCARTER** : Xorg, gestionnaire d'événements et dépendances disproportionnés pour PMKB natif |
| [NiLuJe/inkvt](https://github.com/NiLuJe/inkvt) | Terminal e-ink basé sur FBInk et libvterm ; README avertit de la saisie **HTTP non chiffrée** et de l'arrêt du développement actif | **P2 / idée déjà recensée** dans le registre ; terminal PMKB futur natif, réseau à la demande et aucune saisie HTTP ouverte par défaut |

Ces projets ont été examinés sur leurs README (et sources ponctuelles), **pas compilés ni exécutés** ; certains peuvent contenir des archives binaires ou licences qui demanderaient un audit séparé.

## 5. Décisions et qualification

1. **RETENIR FBInk canonique** comme **référence P0 de HAL** : choix d'orientation Dragon, détection des entrées, rafraîchissement rectangulaire, règles de waveform et de synchronisation. **Ne pas installer de fork** : aucun gain propre à l'Aura HD démontré sur leurs branches principales.
2. **Comparer, non remplacer** : confirmer avec le noyau réel l'orientation du framebuffer, `1440×1080`, l'input ZForce legacy, l'axe tactile/coordonnées, et les marqueurs `MXCFB`. Utiliser des buffers/traces synthétiques sur hôte pour les premiers tests, puis une validation physique autorisée après FIRST BOOT.
3. **MINIMAL d'abord** si FBInk devait être distribué comme outil séparé ou dépendance d'un paquet : prouver la taille/RSS et les licences de la configuration. **PMKB-UI n'a pas à devenir Qt, Python, Lua ou Go**.
4. **Aucune procédure d'installation historique sur la carte**, aucune écriture de partition. L'OS KOReader sans Nickel et l'image FIRST BOOT scellée restent inchangés ; P2/recoveryfs demeure protégée.

**Bilan vérifié : 31/31 forks publics recensés et comparés (26 en retard, 3 divergents, 1 en avance de 2 commits CI, 1 identique), branches inventoriées, candidats particuliers contre-examinés ; 1 homonyme écarté. 0 téléchargement de dépôt, 0 build, 0 test physique Aura HD, 0 code tiers incorporé, 0 écriture physique, 0 modification P1/P2/P3.**
