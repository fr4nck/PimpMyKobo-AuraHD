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
