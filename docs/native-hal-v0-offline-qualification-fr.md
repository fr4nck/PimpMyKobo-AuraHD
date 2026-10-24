# PMKB-HAL V0 — qualification hors appareil (19 octobre 2026)

## Portée

Cette étape construit les deux interfaces manquantes pour porter
PMKB-UI vers la Kobo Aura HD \`dragon\` : événements tactiles et
transactions de rafraîchissement E-Ink. **Ce n'est pas un pilote
matériel actif.** Elle n'ouvre aucun device et ne modifie ni le noyau,
ni U-Boot, ni les images scellées, ni les partitions P1/P2/P3.

Référence locale de qualification matérielle :
\`docs/offline-hardware-qualification-fr.md\` (archive noyau Kobo
2.6.35.3/NTX comparée aux sauvegardes, HWCONFIG réel, paquet KOReader
v2026.07.1). Ne pas extrapoler l'ABI d'un noyau moderne à ce noyau.

## Écran EPDC / MXCFB legacy

L'audit du dépôt établit les éléments suivants pour le noyau Kobo
historique :
- panneau E-Ink logique **1080 × 1440 en portrait** ; les informations
  écran FBIO, rotation et profondeur effective restent à lire sur la
  vraie machine (le mode matériel peut être 1440 × 1080 selon l'axe) ;
- framebuffer \`/dev/fb0\` créé d'après sysfs, initialisation EPDC
  par le noyau, données waveform déjà en RAM ; ne pas les remplacer ;
- ABI Kobo/NTX du noyau 2.6.35.3 : mise à jour avec la variante de
  structure **68 octets**, alternate buffer à l'offset 36 ;
  commandes confirmées hors appareil \`SEND_UPDATE=0x4044462e\` et
  \`WAIT_FOR_UPDATE_COMPLETE=0x4004462f\` (ancien \`uint32_t\`),
  et non l'enveloppe \`mxcfb_update_marker_data\` des noyaux récents.

**Le lot V0 n'utilise aucun de ces codes ioctl**. Le backend réel,
ultérieur, devra embarquer le header K exact, et qualifier les
offsets ABI avec des assertions de compilation. Un pilote qui
prendrait le nouveau \`MXCFB_WAIT_FOR_UPDATE_COMPLETE\` sans
qualification serait incorrect sur cette machine. Aucun refresh
forcé au démarrage dans cette étape.

\`PMKBEinkOps\` rend les transitions explicites :
\`copy(framebuffer, rectangle)\` → \`send(marker)\` →
\`wait(marker)\`. L'appelant choisit \`PARTIAL\` ou \`FULL\`, sans
waveform devinée. \`PMKBBackend\` n'accuse la zone de rafraîchissement
qu'après succès de \`wait\`. En cas de \`wait\` non conclu, le
même marqueur reste en attente, sans double-submit. Si des pixels
changent dans l'intervalle, le HAL doit aussi soumettre ces
changements, pas simplement accepter la confirmation ancienne.

## Tactile ZForce

Le pilote historique \`zforce_i2c.c\` expose au noyau Linux un
**tactile simple** (sur l'Aura HD legacy), avec événements
\`EV_ABS: ABS_X/ABS_Y\`, \`EV_KEY: BTN_TOUCH\`, \`EV_SYN\`. Le nom
attendu d'entrée est \`zForce-ir-touch\`, mais \`event0/event1\`
ne sont **pas** des identifiants stables. Le contrôleur I²C est
initialisé par le pilote : aucun accès à \`neocmd\`, I²C/IRQ
ou firmware depuis PMKB-HAL.

\`PMKBTouchConfig\` contient dimensions, plages ABS mesurées,
inversions et orientation 0/90/180/270, et seuil de déplacement en
pixels logiques. Ces valeurs sont injectées, non codées « au hasard »
pour dragon. Un tap est émis après **une pression et un relâchement**
et à condition qu'une paire de coordonnées valides soit reçue.
\`SYN_DROPPED\` et glissements suppriment le tap. Le multitouch,
le drag et le long-press ne sont pas implémentés.

Avant une recette sur l'écran physique, il faut confronter les quatre
coins/centre et les transformations \`dragon\` avec les indications
du backend KOReader et le mode FB réellement lu ; aucune table
d'orientation de production n'est affirmée aujourd'hui.

## Qualification sans téléchargement

L'API \`pmkb_touch_feed\` accepte les valeurs synthétiques conformes
à \`linux/input.h\` quand cet en-tête est disponible. Les tests C11
comparent les codes numériques EV/ABS/BTN aux définitions Linux
sur le runner, mais **ne lisent aucun périphérique**. Une trace
synthétique pilote aussi les vrais écrans Notes par le pont Launcher.

L'adaptateur E-Ink est qualifié par un simulateur 8 bpp qui contrôle
les zones copiées et les marqueurs envoyés/attendus, y compris
\`copy\` refusé, \`send\` refusé, \`wait\` échoué, marqueur encore
en attente, changements intermédiaires et renouvellement du marqueur.
Le volume mémoire cible connu pour le tampon seul reste
1 555 200 octets en 8 bpp à 1080 × 1440, hors mémoire du pilote.

Compilation hôte GCC C11, ASan/UBSan et test JSON existants.
Compilation croisée vers objets ARM **uniquement si** une toolchain
adaptée est déjà installée sur GitHub Actions ; sinon \`SKIP\`,
sans \`apt\`, \`pip\`, téléchargement d'image ou action locale.
Un objet ARM n'établit pas à lui seul l'ABI libc du rootfs historique.

## Gates restant avant essai

1. Lier un véritable backend evdev à \`pmkb_touch_feed\` après
   identification du device par **nom + capacités**, calibration
   sur lectures réelles et contrôle de permission minimale.
2. Lier un vrai framebuffer MXCFB **ancien ABI** : vérification
   du bit depth/stride, transformation 8-bit vers format FB,
   copie partielle, SEND_UPDATE/WAIT avec vraies valeurs de
   waveform du panneau ; ne jamais supposer que callback=succès
   signifie mise à jour visible sans attente réelle.
3. Compiler/lier avec la libc et le compilateur du rootfs
   ARM exact, sans prendre une toolchain moderne comme preuve
   de compatibilité binaire.
4. Recette explicite sur **carte séparée**, avec consentement
   matériel : affichage initial, coins et centre tactile,
   accents, recalage rotation, waveforms, ghosting, veille et
   récupération après panne d'alimentation.
5. Aucune fusion de la PR #30, ni mise en production de Notes,
   tant que la persistance hors P1/P2 n'est pas qualifiée.

Aucune donnée matérielle n'est inventée par ces tests.

# Complément du 24 octobre 2026 — trames perdues et deux doigts

L'audit communautaire est capitalisé dans
[le dossier noyau/ZForce](https://github.com/fr4nck/PimpMyKobo-AuraHD/blob/main/docs/kernel-community-audit-2026-10-24-fr.md)
et le registre canonique de `main`. Il ne change ni les résultats historiques
ci-dessous, ni le noyau ou FIRST BOOT.

## Défauts reproduits et correctif natif

Au HEAD initial `e6d5e75e602a55bffb2b445f558aa927ae077f62`, deux
séquences synthétiques émettent un faux TAP : une pression suivie de
`BTN_TOOL_DOUBLETAP=1` puis du relâchement ; et un `SYN_DROPPED` suivi
d'une pression dans la trame à jeter puis d'un relâchement propre.
Les deux faux TAP disparaissent avec le correctif.

`pmkb_touch_feed()` ignore désormais tous les événements jusqu'au
`SYN_REPORT` inclus après une perte, puis attend un `BTN_TOUCH=0` explicite
dans une trame propre. Le signal deux doigts annule le geste entier,
y compris si l'on revient à un doigt avant de tout relâcher. Les coordonnées
de la trame rejetée sont oubliées ; seul un nouvel appui complet peut produire
un TAP. Notes et Calculatrice utilisent cette primitive commune.

Ce filtrage **n'implémente pas le multitouch**. Le pilote pazos/lgeek étudié
n'émet pas `BTN_TOOL_DOUBLETAP` ; ce chemin prépare la compatibilité avec un
futur pilote corrigé. Un pilote qui ne signale pas le second contact ne peut
pas être rendu capable de le détecter par ce filtrage. Aucun pilote tiers copié.

La [documentation Linux v6.18](https://github.com/torvalds/linux/blob/v6.18/Documentation/input/event-codes.rst)
demande aussi de relire l'état par `EVIOCG*` après `SYN_DROPPED`.
Cette API pure n'ouvre aucun périphérique : **la resynchronisation complète
reste à réaliser dans l'adaptateur evdev réel**. En son absence, elle peut
perdre un appui supplémentaire si le relâchement est survenu dans la trame
jetée. Ce choix conservateur empêche un faux clic ; il ne qualifie pas la
reprise après veille et ne remplace pas le protocole de réinitialisation.

## Qualification exécutée sur hôte Linux x86_64

- GCC 13.3.0, Python 3.12.14 ; C11 `-O2 -Wall -Wextra -Werror -Wpedantic`.
- Avant : **877 assertions / 26 groupes / 0 FAIL**.
- Après : **939 assertions / 28 groupes / 0 FAIL** : UI 421, Calculatrice
  248, Launcher/rendu 60, HAL 210 (62 assertions ajoutées).
- Non-régression : ordre des signaux dans la trame, deuxième doigt tardif,
  retour de deux doigts à un, pertes répétées, relâchement dans la trame
  perdue, axes rejetés, puis nouvel appui normal. Intégration Notes : un
  faux appui sur « + » ne crée aucune note ; les trois vrais appuis suivants
  créent la note, ouvrent le clavier puis saisissent « a ».
- JSON Notes **1/1 PASS** et images hôte **6/6 PASS** ; les six empreintes
  de pixels correspondent à la version antérieure. Pas de changement UX
  ou d'exception à l'ADR-005 PMSL-Arch (blob `4017615213eea812b8864a221a3bb4babe9ee2bf` relu).
- ASan/UBSan : mêmes tests et images **PASS** avec
  `ASAN_OPTIONS=detect_leaks=0 UBSAN_OPTIONS=halt_on_error=1`.
  La première tentative avec LeakSanitizer échoue car l'environnement
  ne peut lire `/proc/.../task` ; **détection de fuites locale SKIP**,
  pas une réussite implicite. La CI native existante conserve ses contrôles.
- GCC `-fanalyzer` sur `pmkb_hal.c` : **PASS**, aucun diagnostic.
- Mesure comparative, même GCC `-O2`, objet x86_64 `pmkb_hal.o` : section
  texte **2 237 → 2 509 octets (+272)**, data/bss 0 ;
  `sizeof(PMKBTouch)` **72 → 72 octets** (trois booléens utilisent du padding
  sur cet ABI). **Aucune allocation, dépendance, thread ou service ajouté**.
  Ce ne sont ni le binaire ARM lié, ni la RAM au repos sur Kobo.
- Compilation ARM **SKIP** : aucun compilateur croisé préinstallé.
  Compilation noyau, firmware et QEMU **non exécutés**.
- Tactile/E-Ink réels, RAM totale, latence et énergie Aura HD :
  **UNQUALIFIED**. Aucune image privée ou carte n'est disponible/utilisée ici.

Rejeu hôte : `make -C experimental/native-ui test`. Pour le contrôle mémoire,
recompiler avec les flags ASan/UBSan du workflow natif ; ne désactiver
LeakSanitizer que si l'environnement impose cette limite et la consigner.
