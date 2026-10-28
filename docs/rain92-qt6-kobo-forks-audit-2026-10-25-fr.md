# PMKB — Qt6 Kobo Platform Plugin (Rain92) et ses forks

**Audit statique du 25 octobre 2026.** Source : [Rain92/qt6-kobo-platform-plugin](https://github.com/Rain92/qt6-kobo-platform-plugin), HEAD `50ecc846a26e032032235c7ea1903d0b0c2e1172`, commit code majeur `9286f750e0d04a052d29da477454470796e0f72a` du **17 octobre 2026**. Licence principale **GPLv3**, sous-module **NiLuJe/FBInk**. C'est un **plugin QPA Qt 5.15/Qt 6**, pas un OS ni un lecteur.

**Décision PMKB : P1 / R1-R5 — référence de recherche de premier plan pour EPDC, touch ZForce et 16 gris ; PAS de nouveau socle Qt6 imposé à PMKB-UI.** Un runtime Qt facultatif dans le Store `*.pmkb` ne pourrait être envisagé qu'après FIRST BOOT et mesures RAM/CPU/stockage/ABI/licences sur Aura HD 512 Mio.

## 1. Sept forks : piège de nommage et comparaison Git

**Résolution du problème de recherche :** `Rain92/qt5-kobo-platform-plugin` est l'**ancien nom redirigé** vers `Rain92/qt6-kobo-platform-plugin` (GitHub repository ID **264268309**, le même pour les deux URLs). Les **7 forks** ont conservé le nom `qt5-kobo-platform-plugin` ou assimilé. La recherche du seul texte « qt6 » ne les montre pas. GitHub affiche **7 forks** ; sept dépôts de même filiation Git ont été trouvés et comparés à `Rain92:master`. Les forks privés ou supprimés sont hors inventaire.

| Fork | Delta par rapport au parent | Dernière activité / portée |
| --- | --- | --- |
| [Quill-OS/qt5-kobo-platform-plugin](https://github.com/Quill-OS/qt5-kobo-platform-plugin) | **+44 / −10**, divergé | 19 août **2026** : Qt5 pour InkBox/Quill-OS, clavier/souris, rotation ; délègue Wi-Fi, éclairage, boutons à ses services OS. **P2 inspiration architecturale**, non une correction Aura HD |
| [Aryetis/qt5-kobo-platform-plugin](https://github.com/Aryetis/qt5-kobo-platform-plugin) | **+52 / −3**, divergé | 7 mai **2025** : sélecteur `moderntouchhandler` ; anciens modèles `mark < 7` gardent le gestionnaire legacy par défaut, ajout couleurs. **P1 comparateur tactile** |
| [Szybet/qt5-kobo-platform-plugin](https://github.com/Szybet/qt5-kobo-platform-plugin) | **+31 / −10**, divergé | 9 janvier **2024** : choix de waveforms plein/partiel/rapide, mode nuit, hotplug tactile. **P1 idées e-ink**, ne pas importer ses dépendances |
| [Aryetis-Volt/Rain92-qt5-kobo-platform-plugin](https://github.com/Aryetis-Volt/Rain92-qt5-kobo-platform-plugin) | **+3 / −3**, divergé | 4 mai **2024** : qmake, intégration FBInk NiLuJe, **déjà présente dans le parent actualisé en octobre 2026** |
| [kiwilex/qt5-kobo-platform-plugin](https://github.com/kiwilex/qt5-kobo-platform-plugin) | **0 / −10** | 22 mai **2022** : en retard, aucun nouveau commit |
| [lawmx/qt5-kobo-platform-plugin](https://github.com/lawmx/qt5-kobo-platform-plugin) | **0 / −7** | 6 juin **2022** : en retard ; branche `SageFix` **+1** spécifique à Sage |
| [kpen-bit/qt5-kobo-platform-plugin](https://github.com/kpen-bit/qt5-kobo-platform-plugin) | **0 / −72** | 14 juillet **2020** : en retard |

**Bilan vérifié : 3 forks sans commits propres sur `master`, 4 divergents.** Branches spécifiques vues : `lawmx:SageFix` (+1), `Aryetis-Volt:GloHDFix` et `sleepCoverFix` (aucun commit en avance), branches `deviceoverhaul`, `touchupdate`, `qt5` du parent (désormais en retard). Aucun fork n'a de **qualification publiée spécifique à notre Aura HD E606C0** dans les sources examinées.

## 2. Code du parent actuel : preuves et limites

| Domaine | Source et comportement réel | Conséquence PMKB |
| --- | --- | --- |
| **Aura HD explicitement connue** | [`src/kobodevicedescriptor.cpp`](https://github.com/Rain92/qt6-kobo-platform-plugin/blob/master/src/kobodevicedescriptor.cpp) : `DEVICE_KOBO_AURA_HD` → `KoboAuraHD`, `mark=4`, **265 ppp** | **Candidat de comparaison**, pas de preuve de fonctionnement sur E606C0 |
| **Tactile legacy / autodétection** | [`src/koboinputmanager.cpp`](https://github.com/Rain92/qt6-kobo-platform-plugin/blob/master/src/koboinputmanager.cpp) utilise `fbink_input_scan`, sans fixer `event0/event1` ; [`src/kobotouchhandler.cpp`](https://github.com/Rain92/qt6-kobo-platform-plugin/blob/master/src/kobotouchhandler.cpp) traite les protocoles `legacy`, `snow`, `phoenix` et `std` et les relâchements `ABS_PRESSURE` / `BTN_TOUCH` | **P1 / R1** : réutiliser les **scénarios de qualification** dans la HAL PMKB-UI, pas le code dépendant de Qt |
| **Tests de rejeu tactile** | [`tests/touchreplay/main.cpp`](https://github.com/Rain92/qt6-kobo-platform-plugin/blob/master/tests/touchreplay/main.cpp) injecte des événements simulés dans le **véritable `KoboTouchHandler`** par pipe, vérifie des traces attendues et produit `PASS/FAIL` ; cas legacy **Kobo Touch B**, mais **aucune trace Aura HD identifiée** | **Très bonne piste de méthode** pour fabriquer des fixtures E606C0 après observation de notre entrée physique ; **aucun PASS revendiqué** |
| **Régions e-ink / fenêtre** | [`src/kobofbscreen.cpp`](https://github.com/Rain92/qt6-kobo-platform-plugin/blob/master/src/kobofbscreen.cpp) évite certaines compositions Qt quand une fenêtre suffit, sinon composite, puis `fbink_refresh` ; option `profile` mesure dessin/compositing/tramage/refresh | **P1 / UI** : étude des rectangles sales et timings réels, sans imposer QFbScreen |
| **16 gris et NEON** | [`src/dither.cpp`](https://github.com/Rain92/qt6-kobo-platform-plugin/blob/master/src/dither.cpp) : tramage ordonné **8×8**, **16 niveaux**, version **ARM NEON** + fallback scalaire ; motif indexé par coordonnées absolues pour les limites des zones partielles | **P1** : comparer avec la production de PNG 16 gris approuvée et nos réaffichages partiels ; pas de performance E606C0 démontrée |
| **Clavier, boutons, lumière, batterie** | Configurations `src/kobodevicedescriptor.cpp`, APIs `src/koboplatformfunctions.h`, détection de périphériques d'entrée | **P2** : contrats matériels à adapter à la HAL, sans supposer les chemins `sysfs`/event d'une autre Kobo |
| **Wi-Fi** | [`src/kobowifimanager.cpp`](https://github.com/Rain92/qt6-kobo-platform-plugin/blob/master/src/kobowifimanager.cpp) exécute via `/bin/sh` les scripts [`restore-wifi.sh`](https://github.com/Rain92/qt6-kobo-platform-plugin/blob/master/scripts/restore-wifi.sh) et [`disable-wifi.sh`](https://github.com/Rain92/qt6-kobo-platform-plugin/blob/master/scripts/disable-wifi.sh). Ils supposent `/drivers/.../wifi`, `wlarm_le`, `/bin/kobo_config.sh`, `dhcpcd`/`udhcpc`, etc. | **NE PAS EXÉCUTER** dans notre Linux sans Nickel ni reprendre les scripts à l'aveugle. Rester sur le contrat PMKB Wi-Fi à la demande |
| **Dépendances et licence** | [`CMakeLists.txt`](https://github.com/Rain92/qt6-kobo-platform-plugin/blob/master/CMakeLists.txt) : Qt6 `CorePrivate`/`GuiPrivate`/`FbSupportPrivate`, C++17, FBInk compilé en PIC et lié en statique ; [`LICENSE`](https://github.com/Rain92/qt6-kobo-platform-plugin/blob/master/LICENSE) GPLv3 | **Aucune dépendance obligatoire** dans le système 512 Mio ; vérifier RAM, ABI Qt privé, stockage et obligations GPL si paquet optionnel |

**Précision d'actualité :** commit [`9286f750`](https://github.com/Rain92/qt6-kobo-platform-plugin/commit/9286f750e0d04a052d29da477454470796e0f72a), **17 octobre 2026**, migrations vers **NiLuJe/FBInk**, support Qt6/CMake, traitement tactile refondu, optimisation de la composition et du tramage. Le [README actuel](https://github.com/Rain92/qt6-kobo-platform-plugin/blob/master/README.md) cite explicitement Aura HD dans le protocole `legacy`. Les forks historiques ne remplacent pas ce code actuel.

## 3. Décision opérationnelle PMKB

1. **FIRST BOOT reste prioritaire** : KOReader v2026.07.1, PMKB autonome sans Nickel, P1 scellée, **P2 protégée**. Aucun Qt6 ajouté au boot, pas de modification U-Boot/noyau/microSD.
2. **R1/HAL tactile** : qualifier ZForce E606C0 en utilisant les idées de `fbink_input_scan` et du rejeu d'événements : DOWN/MOVE/UP, suppression d'anciens événements, limites, rotations. Contrairement au test amont Touch B, préparer des fixtures issues de notre appareil.
3. **PMKB-UI** : étudier les mises à jour partielles, ancrage spatial du tramage 8×8, choix de waveform et instrumentation. Confronter au socle natif déjà décidé au lieu de développer deux runtimes.
4. **Store** : `Qt6` seulement **optionnel**, pour des applications tierces qui le nécessiteraient réellement, après profil mémoire/CPU et étude des droits. Une application Qt ne doit pas lancer automatiquement les scripts réseau tiers.

**Qualification de cet audit** : **7/7 forks publics répertoriés et branches principales comparées ; 3 sans nouveaux commits, 4 divergeant ; 0 téléchargement de sources complètes/firmwares, 0 compilation, 0 tests matériel PMKB, 0 code intégré, 0 écriture P1/P2/P3.** La présence de `KoboAuraHD` dans le code n'est **PAS** une validation sur E606C0.
