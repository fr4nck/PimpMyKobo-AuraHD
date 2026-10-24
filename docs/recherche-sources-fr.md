# PMKB — Registre de recherche et sources externes

**Création : 24 octobre 2026.** Registre évolutif pour la **Kobo Aura HD N204 / Netronix E606C0 / i.MX507 / 512 Mio**. À consulter avant de lancer un audit, de concevoir un composant ou de réimplémenter une fonctionnalité déjà explorée ailleurs.

**Finalité :** garder ensemble les **sources d'information**, les **sources d'inspiration** et les **candidats à une intégration technique**. Un lien ici ne signifie **ni code accepté, ni licence compatible, ni fonctionnement sur notre exemplaire**. Les caractéristiques proviennent des README ou des fichiers ciblés consultés ; la compilation et les essais matériels restent à faire.

**Priorité absolue inchangée : FIRST BOOT KOReader sans Nickel sur une carte de test distincte.** Les recherches sont parallèles et ne doivent pas le retarder. Le candidat FIRST BOOT scellé, PRE-P1, P2, les sauvegardes privées et leurs SHA-256 ne sont pas modifiés par cette feuille.

## Mode d'emploi

- **INFO** : documentation, historique matériel, techniques ou retours d'expérience ; pas nécessairement du code à copier.
- **INSPIRATION** : idées d'ergonomie, d'interface, d'architecture ou d'outillage, à adapter à PMKB.
- **CANDIDAT** : source pouvant être comparée, patchée, adaptée ou réutilisée **après qualification du diff, dépendances, licences et ABI**.
- **P0** : essentiel au FIRST BOOT / support E606C0 ; **P1** : socle natif, Notes, terminal et services ; **P2** : idées, options futures ou dépendances Nickel.
- **À analyser** = piste identifiée et code ou README consulté ; **NON QUALIFIÉ** = aucune preuve de fonctionnement sur notre Kobo / notre PMKB. Un test QEMU n'est pas un test sur écran E-Ink, batterie ou veille réels.

## A. Matériel, noyau, bootloader et émulation

| Priorité | Source | Usages | Intérêt précis et vérifications requises |
| --- | --- | --- | --- |
| P0 | [Kobo-Reader / hw/imx507-aurahd](https://github.com/kobolabs/Kobo-Reader/tree/master/hw/imx507-aurahd) | INFO / CANDIDAT | Sources historiques Netronix du noyau 2.6.35.3 et U-Boot ; référence E606C0, à comparer à nos copies et configurations, sans publication de firmware propriétaire. |
| P0 | [pazos/linux-2.6.35.3-kobo](https://github.com/pazos/linux-2.6.35.3-kobo) | INFO / CANDIDAT | Arbre Linux 2.6.35.3 avec code Netronix et la chaîne ZForce ; comparaison ciblée avec l'image noyau 2.6.35.3-850-gbc67621+, sans supposer une égalité binaire. |
| P0 | [lgeek/linux-okreader](https://github.com/lgeek/linux-okreader) | INFO / CANDIDAT | Noyau 2.6.35.3 et `localversion` `-850-gbc67621` ; examiner adaptations Linux, EPDC, tactile, intégration Debian/KOReader. |
| P0 | [lgeek/u-boot-okreader](https://github.com/lgeek/u-boot-okreader) | INFO / CANDIDAT | Source d'étude des transitions U-Boot, HWCONFIG, paramètres noyau et waveform ; **pas de remplacement du bootloader**. |
| P0 | [lgeek/okreader](https://github.com/lgeek/okreader) | INFO / INSPIRATION | Debian + KOReader sans Nickel sur certaines Kobo i.MX507 ; **Aura HD indiquée comme nécessitant potentiellement un patch noyau**. Séparer concept validé ailleurs et compatibilité E606C0. |
| P0 | [giorgio130/linux-2.6.35-kobo-multitouch](https://github.com/giorgio130/linux-2.6.35-kobo-multitouch) | INFO / CANDIDAT | Diff concret de `drivers/input/touchscreen/zforce_i2c.c` : `ABS_MT_POSITION_X/Y`, contacts multiples et `BTN_TOOL_DOUBLETAP` ; vérifier protocole ZForce v2, axes, veille, stabilité et compatibilité avec l'image PMKB. Aucun multitouch matériel encore qualifié. |
| P0 | [katadelos/eink-emulator](https://github.com/katadelos/eink-emulator) — [profil Aura HD](https://github.com/katadelos/eink-emulator/blob/main/docs/kobo-aura-hd.md) | INFO / CANDIDAT | Émulateur QEMU **E606C0** expérimental ; valide une géométrie PRE-P1/P1/P2 conforme aux offsets connus et recrée une petite P3. Explorer boot de notre P1 scellée, logs et input en **simulation**, avec fichiers privés locaux seulement. |
| P0 | [katadelos/qemu, branche eink-emulator](https://github.com/katadelos/qemu/tree/eink-emulator) | INFO / CANDIDAT | Carte virtuelle `imx50-kobo-aura-hd` : i.MX507, ZForce, MSP430, PMIC, stockage, réseau. Le machine ID **2988** qu'elle utilise est une **hypothèse à recouper sur U-Boot réel**, pas une preuve de notre machine. |
| P1 | [brunotl/kernel-kobo-mx50-ntx](https://github.com/brunotl/kernel-kobo-mx50-ntx) | INFO / CANDIDAT | Autre arbre Linux 2.6.35.3 i.MX50/NTX ; établir d'abord son historique et ses différences réelles, notamment USB, alimentation et périphériques, avant de retenir quoi que ce soit. |
| P2 | [pazos/linux-3.0.35-kobo](https://github.com/pazos/linux-3.0.35-kobo) | INFO | Arbre Linux 3.0.35 pour d'autres générations de Kobo ; comparateur architectural **non démontré compatible Aura HD** et non retenu comme noyau PMKB. |
| P2 | [postmarketOS / pmaports](https://gitlab.com/postmarketOS/pmaports) — [portage Clara HD](https://gitlab.com/postmarketOS/pmaports/-/merge_requests/2334) | INFO / INSPIRATION | Techniques de portage E-Ink, extraction de waveform et intégration userspace ; **Clara HD i.MX6SLL ≠ Aura HD i.MX507**. Pas de transposition de pilotes sans preuve. |
| P2 | [twhitehead/notes-kobohacking](https://github.com/twhitehead/notes-kobohacking) | INFO | Notes sur U-Boot, extraction du `uImage`, console série, recovery et USB, sur Kobo Aura/Glo. Les commandes d'écriture et manipulations MSP430 sont **des exemples historiques, jamais à exécuter directement**. |

## B. Rendu E-Ink, interface native, clavier et applications

| Priorité | Source | Usages | Intérêt précis et vérifications requises |
| --- | --- | --- | --- |
| P0 | [NiLuJe/FBInk](https://github.com/NiLuJe/FBInk) | INFO / INSPIRATION / CANDIDAT | Couche C framebuffer/EPDC, texte, images, rotations et rafraîchissement. Le code distingue explicitement **Aura HD / dragon**. Candidat de comparaison pour PMKB-UI et sa HAL ; vérifier ABI et licence **GPLv3+** avant toute incorporation. |
| P1 | [pazos/kobo-clock](https://github.com/pazos/kobo-clock) | INSPIRATION / CANDIDAT | Application native C/SDL 1.2 pour Aura HD ; boucle d'événements, affichage, fontes et coûts mémoire. Inspirer nos applets horloge/calculatrice, pas ajouter SDL par défaut. |
| P1 | [koreader/koxtoolchain](https://github.com/koreader/koxtoolchain) | INFO / CANDIDAT | Chaînes de compilation croisée adaptées aux Kobo anciennes ; vérifier libc/ARM hard-float, taille binaire et reproductibilité avant de standardiser les builds de PMKB-UI. |
| P1 | [olup/kobowriter](https://github.com/olup/kobowriter) | INSPIRATION / CANDIDAT | Éditeur de texte léger en Go et FBInk, saisie AZERTY via clavier USB et USB-OTG. Test déclaré sur **Glo HD seulement** : idées pour Mes Notes et raccourcis ; dépendance OTG/alimentation à valider sur E606C0. |
| P1 | [llandsmeer/inkvt](https://github.com/llandsmeer/inkvt) | INSPIRATION / CANDIDAT | Terminal VT100 E-Ink fondé sur FBInk et libvterm ; saisie clavier virtuel expérimentale. Référence pour terminal PMKB, **pas d'activation automatique d'un serveur HTTP de saisie en clair**. Licence GPLv3+. |
| P1 | [Nayeem170/kobo-core](https://github.com/Nayeem170/kobo-core) | INFO / INSPIRATION | SDK Rust d'abstractions écran, tactile, énergie, lumière et rendu ; liste Aura HD/dragon. **Support déclaré dans le README ≠ test du SDK sur notre noyau 2.6.35.3** ; mesurer les dépendances avant d'envisager une réutilisation. |
| P2 | [Rain92/qt5-kobo-platform-plugin](https://github.com/Rain92/qt5-kobo-platform-plugin) | INFO / INSPIRATION | Piste Qt/QPA E-Ink ; étudier le rendu sans Nickel, mais éviter d'imposer Qt et sa consommation au système minimal. |
| P2 | [baskerville/plato](https://github.com/baskerville/plato) | INSPIRATION | Lecteur alternatif et ergonomie E-Ink ; benchmark d'interface seulement, puisque KOReader est le lecteur retenu. |

## C. Réseau, maintenance et catalogue d'idées

| Priorité | Source | Usages | Intérêt précis et vérifications requises |
| --- | --- | --- | --- |
| P1 | [pazos/kobo-minimal-tools](https://github.com/pazos/kobo-minimal-tools) | INFO / CANDIDAT | Recettes minimales Dropbear/fmon ; examiner le binaire SSH, sa configuration, ses dépendances et les droits, **sans importer le mécanisme d'installation KoboRoot.tgz/Nickel**. |
| P1 | [boringrgb/kobo-aura-remote](https://github.com/boringrgb/kobo-aura-remote) | INFO / INSPIRATION | SSH/FTP/Telnet via une mise à jour Kobo Aura, firmware 3.15.0. **Mot de passe root fixe dans le README : ne jamais reprendre les identifiants ou exposer automatiquement les services**. |
| P2 | [shermp/kobo-rclone](https://github.com/shermp/kobo-rclone) | INSPIRATION | Synchronisation de fichiers et métadonnées Calibre/SFTP. La logique Nickel/SQLite et l'usage de rclone ne sont pas directement adaptés ; ne retenir qu'une synchronisation optionnelle chargée à la demande. |
| P2 | [RiccardoSilva42/Kobo-Hacks-Comp](https://github.com/RiccardoSilva42/Kobo-Hacks-Comp) | INFO / INSPIRATION | Catalogue externe à consulter pour nouvelles applications, réglages et pratiques de la communauté ; la plupart des méthodes visent Nickel. |
| P2 | [skinkie/kobomail](https://github.com/skinkie/kobomail) | INFO | Projet annonçant un client courriel pour **Aura HD**, mais **dernier commit vérifié : simple README, pas d'implémentation**. Archiver l'idée PDA, aucune intégration possible en l'état. |
| P2 | [ProGTX/Kobo-Aura-HD-Clean-Articles](https://github.com/ProGTX/Kobo-Aura-HD-Clean-Articles) | INFO | Outil C++ de nettoyage d'anciens articles Pocket dans `KoboReader.sqlite` de Nickel. **Hors périmètre runtime sans Nickel** ; renseigne seulement les formats historiques et la migration de données. |
| P2 | [NiLuJe/kfmon](https://github.com/NiLuJe/kfmon), [pgaskin/NickelMenu](https://github.com/pgaskin/NickelMenu), [baskerville/fmon](https://github.com/baskerville/fmon) | INSPIRATION | Lancement d'applications, anti-double-instance, gestion d'événements. **Ne pas intégrer les hooks, les bases de données ou les déclencheurs Nickel** ; PMKB possède son launcher indépendant. |
| P2 | [XCSoar/XCSoar](https://github.com/XCSoar/XCSoar) | INFO | Piste historique USB-OTG et connectique de clavier/GPS sur Kobo ; déterminer la variante matérielle réellement couverte avant d'évoquer un clavier externe Aura HD. |

## D. Dictionnaires, bibliothèque et ressources éditoriales

| Priorité | Source | Usages | Intérêt précis et vérifications requises |
| --- | --- | --- | --- |
| P1 | [Oniricorpe — Kobo hacks & mods](https://oniricorpe.eu/log/tech/kobo-hacks-mods/) | INFO / INSPIRATION | Panorama francophone daté du **8 octobre 2022**, mis à jour le **27 août 2025** : dictionnaires, polices, KOReader/Plato, configuration, Calibre, synchronisation et pratiques communautaires. **Majoritairement Nickel** : retenir les références documentaires, pas ses instructions d'installation dans PMKB sans Nickel. |
| P1 | [reader-dict/monolingual](https://github.com/reader-dict/monolingual) / [reader.dict](https://www.reader-dict.com/) | INFO / CANDIDAT | Dictionnaires issus de ressources libres ; distinguer **format Kobo natif destiné à Nickel** et **format StarDict utilisable par KOReader**. Mesurer taille, mémoire, temps d'indexation et vérifier les licences des données avant toute distribution PMKB. Ne pas embarquer de gros dictionnaires dans P1 par défaut. |
| P2 | [shermp/Kobo-UNCaGED](https://github.com/shermp/Kobo-UNCaGED) | INFO / INSPIRATION | Client **Calibre sans fil**, fonctions envoi/réception, séries, couvertures et métadonnées ; protocole et interface intéressants pour PMKB. L'application actuelle exige **Nickel, NickelMenu, NickelDBus**, et annonce **AGPL-3.0** : pas de réutilisation directe dans notre système sans Nickel. |
| P2 | [NotSimone/Kobo-Metadata](https://github.com/NotSimone/Kobo-Metadata) | INFO / INSPIRATION | Plugin **Calibre sur PC** récupérant titres, auteurs, résumés, séries et couvertures ; une piste de flux de métadonnées, **pas une application Kobo native**. Accès à des services tiers et leurs conditions à vérifier. |
| P2 | [Z-Library — accès FR communiqué](https://fr.z-library.sk/) | INFO / RÉFÉRENCE À VÉRIFIER | Lien externe transmis par l'utilisateur (24 octobre 2026), **non validé comme domaine officiel ni comme source autorisée**. La plateforme Z-Library a fait l'objet de décisions de blocage pour atteintes au droit d'auteur en France (tribunal judiciaire de Paris, 12 septembre 2024) ; le domaine communiqué fait également l'objet de signalements de sécurité tiers. **Aucun téléchargement automatisé, aucune indexation du catalogue dans le Store PMKB, aucune redistribution de contenus sans droits vérifiés.** À conserver comme référence documentaire uniquement, avec statut juridique et technique non qualifié. |

### Compatibilité des dictionnaires et des livres

Le guide Oniricorpe distingue les fichiers de dictionnaires destinés à **Nickel**
des fichiers **StarDict** destinés à **KOReader/Plato**. Notre lecteur cible
KOReader : ne pas demander la création de `.kobo/custom-dict` comme prérequis
du FIRST BOOT. Les dictionnaires volumineux doivent rester des ressources
facultatives de bibliothèque ou de P3, jamais un prérequis à la lecture.

Les plateformes documentées mais non vérifiées sur le plan du droit d'auteur ou de la sécurité restent **hors du flux d'acquisition et de distribution PMKB** ; ce registre ne constitue pas une recommandation de téléchargement.

Même principe pour Calibre : **connexion sans fil en option**, après qualification
du Wi-Fi et du modèle de permissions PMKB, sans NickelDBus, sans activation réseau
au démarrage et sans incorporation implicite de code AGPL.

## Feuille de route de recherche — tâches et critères de sortie

| Ordre | Recherche | Travail hors matériel | Sortie attendue / décision |
| --- | --- | --- | --- |
| **R0** | **FIRST BOOT prioritaire** | Conserver intégralement le candidat et ses SHA ; effectuer, si utile, des revues documentaires parallèles. | **FIRST BOOT physique reste UNQUALIFIED** jusqu'à observation réelle. Aucune recherche ne doit le bloquer. |
| **R1** | **Provenance et delta du noyau E606C0** | Comparer sources Kobo/Netronix, `pazos/linux-2.6.35.3-kobo` et `lgeek/linux-okreader` ; identifier .config, pilotes EPDC, ZForce, NTX/MSP430, stockage, USB et correctifs de sécurité réellement manquants. | Tableau fichier/commit/raison/licence/effet attendu ; 0 patch noyau non justifié ; conserver noyau de référence tant que l'alternative n'a pas gagné sa qualification. |
| **R2** | **Simulation de notre FIRST BOOT** | Examiner `katadelos/eink-emulator` et sa carte QEMU E606C0, comparaison géométrie/bootloader ; envisager une image virtuelle compacte PRE-P1 + P1 PMKB + P2 + P3 neuve. | Contrôle d'identités et journal boot reproductible sur fichiers privés, sans téléchargement implicite ; résultats hôte ≠ qualification E-Ink physique. |
| **R3** | **Tactile et HAL graphique** | Diff du pilote ZForce multitouch `giorgio130` et intégration avec `pazos` ; audit FBInk rotations, framebuffer, waveform et rafraîchissement ; comparer à la HAL PMKB existante. | Décision argumentée **garder / adapter / écarter** par composant, coût RAM/binaire, ABI, droits et tests synthétiques, puis matériel autorisé séparément. |
| **R4** | **Applications PMKB natives** | Étudier C/SDL de `kobo-clock`, éditeur `KoboWriter`, terminal `InkVT`, SDK `kobo-core`. Réutiliser les idées compatibles avec **Notes, clavier commun, calculatrice, terminal, split 2 panneaux**. | Composants légers indépendants de Nickel, chargement à la demande, pas de gros runtime systématique ; aucune application externe présumée compatible. |
| **R5** | **Réseau et sécurité mesurée** | Examiner Dropbear, USB-OTG et sync facultative ; qualifier les CVE applicables au noyau 2.6.35.3, éventuels backports, permissions et services. | SSH à la demande, idéalement par clés ; éviter mot de passe root partagé, Telnet ouvert en permanence et dépendances gourmandes ; profil connecté examiné séparément. |
| **R6** | **Veille communautaire utile** | À chaque découverte : ajouter URL, cible, provenance, statut, licence à contrôler, hypothèse utile et prochaine action dans **ce registre**. | Aucune piste perdue et aucune adoption automatique ; revue par priorité et mesure du gain réel plutôt que collection de dépôts. |

| **R7** | **Dictionnaires et bibliothèque sans Nickel** | Examiner formats StarDict pour KOReader, licences/langues, tailles et indexation ; étudier les flux Calibre (`Kobo-UNCaGED` comme référence, pas composant installable). | Catalogues et métadonnées optionnels, import hors P1 système, consommation mesurée ; intégration dépendante de Nickel écartée. |

### Règles de reprise de code et de qualification

1. **Ne jamais fusionner un arbre noyau tiers « en bloc ».** Diff limité et motivé, ABI E606C0 vérifiée, tests hôte avant tout test matériel et contrôle énergétique après boot.
2. **Vérifier les licences fichier par fichier** et conserver notices/attributions exigées. Le fait qu'un dépôt soit public ne donne pas un droit de copier sans condition ; étudier également les firmwares propriétaires.
3. **Ne pas confondre compatibilité de famille** (i.MX50, « Kobo », framebuffer) avec compatibilité de notre **E606C0 / ZForce v2 / frontlight SY7201 / MSP430**.
4. **Pas de téléchargement lourd, clone de noyau, build ou mise à jour du firmware sans accord adapté.** Cette inscription de références n'exécute aucun code externe.
5. **Ne pas modifier** PRE-P1, U-Boot, P1 scellée, P2, image originale 32 Go ou microSD de test 16 Go depuis une simple étape de recherche ; chaque écriture requiert une décision distincte.
6. **Distinguer les preuves** : sources relues, build PASS, tests simulés, puis tests matériels. Tout ce qui n'a pas été observé reste `UNQUALIFIED`.

## Liens de pilotage PMKB

- [Roadmap principale](ROADMAP.fr.md)
- [Jalon FIRST BOOT #1](pmkb-first-boot-1-fr.md) (selon la branche d'intégration)
- [Architecture utilisateur sans Nickel](offline-liberation-fr.md)
- [Documentation générale](README.md)

Ce document est l'**index canonique des références externes** pour les travaux futurs PMKB : préférer enrichir la même entrée et préciser le statut plutôt que disperser des liens dans les commentaires et conversations.
