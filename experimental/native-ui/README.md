# PMKB-UI Native V0 — C11, sans KOReader/Nickel

**Branche dédiée depuis main. Non intégré au démarrage ni installé sur la Kobo.**

## Pourquoi ce lot

L'Aura HD (dragon/E606C0, i.MX507, 512 Mio) doit à terme exécuter
Notes, calculatrice et Store sans navigateur ni instance résidente de KOReader.
Le socle PMKB-UI a donc une interface C11 indépendante du backend matériel.
Les sources de la PR #29 restent les références fonctionnelles ; elles ne
sont pas fusionnées ni modifiées par ce travail.

## État réel du code

- **Éditeur UTF-8 natif** : titre/texte dynamiques, curseur et sélection
  en offsets d'octets aux frontières Unicode, remplacement, effacement,
  gauche/droite, limites **en unités UTF-16** pour les respecter comme
  \`notes-core.js\` (\`100\` titre, \`120000\` corps). UTF-8 illégal refusé
  avant mutation. Un accent en caractères combinés est traité comme deux
  points de code, sans déchirer les octets.
- **Clavier réutilisable** : AZERTY (é è à ç), majuscules, page numérique
  puis symboles, espace, retour arrière, entrée, curseur, fermeture.
  **Quatrième mode : SCIENTIFIC**, pour la future Calculatrice native :
  sin/cos/tan, arcsin/arccos/arctan via INV, ln/log/sqrt, puissances,
  parenthèses, pourcentages, pi, e, Ans, C, DEG/RAD et =. Ce mode
  réutilise le même curseur, la sélection et l'insertion UTF-8.
  La touche = renvoie l'intention `PMKB_EVALUATE`, sans calcul ; le
  moteur mathématique C et l'affichage du résultat restent à porter.
  Le mode scientifique est explicitement demandé par une application,
  sans apparaître dans le cycle de pages du clavier Notes.
  \`PMKBKeyboard\` est indépendant de Notes : cible arbitraire \`PMKBText\`.
  L'état ne survit pas à la fermeture. Les cases tactiles font au moins
  **44 px de hauteur** et 53 px de largeur dans la simulation 320 px.
  Pas de service permanent.
- **Notes RAM** : 100 notes au maximum allouées à la demande, création,
  sélection, édition, liste récente, réouverture et export **en mémoire**
  au format \`pmkb-notes-v1\`. Champ \`strokes\` présent mais vide,
  typographie par défaut. Aucune importation JSON, sauvegarde disque,
  historique d'annulation, croquis ou police externe dans ce lot.
  **Toute note sera perdue en quittant le prototype.**
- **Interface native de simulation** : deux lignes en tête, menus sobres,
  labels persistants, focus visible, zone texte prioritaire, clavier
  masqué au repos. Même événement indépendant de la source d'entrée pour
  tap simulé, texte d'un clavier physique et clavier virtuel. Le rendu
  hôte dessine vraiment en gris 8 bits dans un seul tampon ; seule la
  région où les pixels changent est signalée. Aucun timer de rendu.
  Le glyphage de simulation n'est qu'une police bitmap ASCII de diagnostic :
  accents et emoji ne sont **pas** rendus fidèlement, même si leurs
  octets sont conservés dans les notes et le JSON.
- **PMKB-HAL** : contrat à intégrer ultérieurement via adaptateur :
  aucun \`/dev/fb0\`, \`/dev/input/event*\`, \`/dev/ntx_io\`, ni ioctl,
  mutex matériel ou gestion de veille. Ne pas utiliser les buffers
  hôtes comme preuve de rafraîchissement EPDC.

## Évaluer LVGL sans dépendance ajoutée

LVGL reste le candidat privilégié pour widgets/typographie/rendu natifs.
Aucun runtime ni en-tête LVGL n'est livré par PMKB main. La couche C11
portable est compilée **sans LVGL**, et la future couche \`pmkb_lvgl_*\`
devra implémenter l'affichage et la saisie via PMKB-UI/PMKB-HAL.
Ne pas déclarer LVGL fonctionnel sur i.MX507 avant compilation ARM,
vérification de sa licence, RAM réelle et traduction des update markers
MXCFB. FBInk est une autre piste pour les rafraîchissements.
Ni l'un ni l'autre n'est installé ou téléchargé ici.

[Limites et contrats HAL](../../docs/native-ui-v0-contract-fr.md)

## Tests reproductibles

Sur un hôte disposant déjà de GCC, make et Python 3 :

\`\`\`sh
cd experimental/native-ui
make test
\`\`\`

Test C : UTF-8/UTF-16, accents, sélection, pavé scientifique,
fonctions inverses, bascule DEG/RAD, intention de calcul, garde-fous,
export JSON, limites de carnet, calcul des dirty rects, événements souris/
clavier simulés, Notes (création → édition → liste → réouverture), écran
1080 × 1440. Le contrôle Python compare le JSON exporté au schéma
\`pmkb-notes-v1\` et aux données accentuées. Le job natif C11 GitHub Actions
utilise GCC, Python et sanitizers préinstallés. **Pas d'apt/pip/npm,
pas de téléchargement de bibliothèque ni de modèle.**

La compilation hôte ne prouve ni la compilation croisée ARM, ni LVGL,
ni evdev/EPDC réel, ni la consommation et l'autonomie.

## Prochaines portes de qualification

1. Fonctions de dessin multiligne complet, défilement tactile et glyphes
   français dans une implémentation de production (LVGL sous réserve de
   vérification), sans dépasser les deux lignes supérieures.
2. Import/export JSON via un emplacement explicitement qualifié en écriture,
   écriture atomique + stratégie de récupération, jamais P1/P2.
3. Backend PMKB-HAL : buffers alternatifs EPDC, marker et attente
   d'update, rotation dragon, eventN ZForce identifié par sysfs,
   calibration tactile et frontlight. Tests d'abord simulés.
4. Compilation croisée pour ARMv7/i.MX507 et budget de RAM/Cycles.
5. **Autorisation spécifique avant toute écriture sur microSD physique**.
   FIRST BOOT et récupération restent inchangés.

Règle UX : ADR-005 PMSL-Arch (blob \`4017615213eea812b8864a221a3bb4babe9ee2bf\`),
\`docs/notes-ux-policy.md\` depuis PR #29 ; deux lignes, densité
productive, pas de dashboard, labels et focus, aucun contrôle tronqué.

## Calculatrice scientifique native C11 (lot de continuation)

Le moteur \`pmkb_calculator.c\` analyse les expressions sans \`eval\`,
sans réseau et sans locale imposée. Il prend en charge \`+\`, \`-\`,
\`*\`, \`/\`, parenthèses, \`^\` (associativité droite), pourcentage
postfixe, \`sin/cos/tan\`, \`asin/acos/atan\`, \`log/ln\`, \`sqrt/√\`,
\`abs\`, \`π\`, \`e\` et \`Ans\`. L'angle est en DEG ou RAD suivant le
clavier partagé. Maximum 192 unités de texte, 128 jetons et 48 niveaux
d'imbrication. Erreurs de syntaxe, domaine, division par zéro,
dépassement numérique et dépassement de limites distinctes.

\`pmkb_calculator_ui.c\` réutilise **PMKBKeyboard** et **PMKBSurface** :
expression éditable, pavé tactile à six colonnes, résultat, mémoire Ans,
C (effacer la saisie sans perdre Ans), AC (effacer également Ans et
l'historique) et huit calculs conservés **en RAM uniquement**.
La touche = déclenche réellement l'évaluation C. Les entrées tactiles
ou les événements génériques clavier physique passent par le même
éditeur UTF-8 que Notes. Aucune boucle de rendu ni nouveau service.

Le simulateur hôte produit des pixels et des rectangles modifiés ;
l'affichage ASCII de diagnostic ne représente pas fidèlement les glyphes
π/√ : les expressions sont cependant conservées et évaluées en UTF-8.
La double précision \`double\` et le rendu à 12 chiffres significatifs
ne conviennent pas à des calculs exigeant une précision arbitraire.

Tests indépendants \`pmkb-calculator-tests\` : expressions de référence,
règles de priorité, DEG/RAD, domaines, limites, attaques syntaxiques,
saisie tactile simulée, bouton =, erreurs sans altérer Ans, C/AC,
rendu incrémental et formats 320×480 / 1080×1440. Voir \`make test\`.


## Rendu hôte vérifiable et pont PMKB Launcher / HAL

\`pmkb_surface.c\` dessine maintenant une **petite fonte bitmap 5×10**
directement sur un tampon gris : accents français courants (é, è, ê, à,
ç, ù, etc.), lettres majuscules accentuées, π, √, ×, ÷, °,
flèches et accents combinants les plus courants. La liste est bornée :
\`pmkb_surface_glyph_supported()\` distingue les glyphes implémentés
des caractères encore non couverts (emoji, autres écritures). Ce n'est
pas un remplacement de LVGL ni un système typographique Unicode complet.
\`pmkb_surface_text_box()\` limite la peinture au rectangle du champ
et évite de recouvrir le clavier avec du texte trop long.

Le pavé des simulations 1080×1440 utilise des rangées de 94 pixels pour
ne pas traiter 44 pixels physiques comme 44 pixels CSS ; à 320×480 les
rangées restent à 44 pixels. Sur grand écran, la calculatrice dessine
son historique de session dans l'espace laissé libre au-dessus du
clavier. Les tests conservent l'invariant **deux lignes en haut** et
l'absence de boucle de rafraîchissement.

Pour **produire six vraies images PNG issues du code C**, sans
dépendance graphique téléchargée :

~~~sh
cd experimental/native-ui
make
make preview OUT=./host-previews
~~~

Les douze images générées sont : Notes, Calculatrice, Store (liste et
détail), planche de glyphes et Tableau blanc, chacune en 320×480 et
1080×1440. Le programme natif
\`pmkb-host-preview\` produit un PGM P5 ; le script Python
\`tools/render_host_previews.py\` valide dimensions/contraste/données,
puis le convertit en PNG via la bibliothèque standard.
En CI, les images sont produites uniquement dans un répertoire
temporaire, vérifiées puis effacées. Il n'y a aucun accès réseau.
Ces images **ne sont pas des captures de la liseuse**.

\`pmkb_launcher_bridge.c\` fournit les identifiants stables
\`notes\` / \`calculator\` / \`store\` pour le futur launcher natif,
une seule application chargée à la fois, et une fonction commune de
présentation qui relaie les rectangles modifiés à un callback PMKB-HAL.
Le Store est **réservé, non implémenté**. Le pont ne modifie pas la
PR #25 : son Launcher V0.6 reste un prototype hôte séparé.

La fermeture de Notes contenant une note encore seulement en RAM est
refusée (\`PMKB_UNSAVED\`) sauf décision explicite de perdre la session ;
aucune fermeture silencieuse et aucune écriture sur P1/P2/P3.
L'application Calculatrice peut être déchargée normalement et sa
mémoire Ans est alors perdue. Tous les accès E-Ink, ZForce, frontlight
et MXCFB restent **non implémentés** : le seul backend testé accuse
réception des rectangles sur un mock sans périphérique.


## PMKB-HAL V0 — ébauche testable sans périphérique

Le module indépendant \`pmkb_hal.h/c\` introduit deux contrats :
- **Tactile ZForce legacy** : accepte seulement \`EV_ABS/ABS_X/ABS_Y\`,
  \`EV_KEY/BTN_TOUCH\` et \`EV_SYN/SYN_REPORT\` (une seule pression).
  Il attend un press/release complet, normalise des plages ABS fournies
  explicitement, applique inversion et rotation, puis émet **un tap**
  uniquement si le doigt n'a pas glissé au-delà du seuil déclaré.
  \`SYN_DROPPED\`, coordonnées invalides ou geste sans coordonnées
  annulent la saisie. Pas de numéro \`eventN\` fixé arbitrairement.
- **E-Ink** : \`PMKBEink\` enveloppe un pilote injecté sous forme de
  trois callbacks : \`copy\`, \`send(marker)\`, \`wait(marker)\`.
  Les surfaces PMKB sont signalées comme présentées **après attente
  réussie**. Sur erreur d'attente, le marqueur reste en vol et un
  nouvel envoi n'est pas autorisé tant qu'il n'est pas résolu.
  Si le contenu a changé entre les tentatives, une nouvelle mise à
  jour est nécessaire avant tout acquittement. Modes partiel/complet
  choisis explicitement : aucune politique de waveform inventée.

Tout cela reste simulé : aucun vrai \`/dev/input/eventN\`,
\`/dev/fb0\`, \`mmap\`, \`ioctl\`, I²C ni changement de firmware,
de configuration ou de partition. Les tests utilisent des traces
d'événements et un tampon framebuffer fictifs, pas la Kobo.

Pour qualifier sur hôte, \`make test\` inclut désormais
\`pmkb-hal-tests\` et la CI vérifie aussi cette suite sous
ASan/UBSan. Une étape de compilation croisée ARM **sans installation**
est conditionnée à la présence d'un compilateur ARM déjà installé ;
elle produit seulement des fichiers objets temporaires. Le résultat
\`SKIP\` est explicite si le compilateur n'existe pas. Même des objets
ARM valides ne prouveraient ni l'ABI du rootfs KOReader ni le
rafraîchissement du panneau réel.

Voir \`docs/native-hal-v0-offline-qualification-fr.md\` pour les
hypothèses matérielles archivées et les portes de vérification.


## Transfert JSON des Notes vers le futur Launcher natif (V0)

Le pont fournit maintenant pmkb_app_host_notes_export_snapshot(),
qui copie le carnet pmkb-notes-v1 **en mémoire uniquement**, sous
condition de l'identifiant de génération de la session. Une réponse
différée d'une ancienne session n'accède donc pas aux notes suivantes.

**Export en RAM n'est pas sauvegarde** : quitter une session contenant
des notes sans discard explicite reste refusé. L'adaptateur de stockage
P3 et son accusé de persistance atomique ne sont pas implémentés.
Voir docs/native-notes-session-export-v0-fr.md pour les limites et
le protocole. Le rendu approuvé et les PR #25/#26/#27/#29 ne sont pas
modifiés ; les trois premières restent soumises à validation visuelle.


## Artefacts visuels de simulation native

Le workflow Native PMKB UI publie les douze captures PNG du raster C11 :
Notes, Calculatrice, Store (liste et détail), Tableau blanc et glyphes,
en deux résolutions. Les fichiers sont dans l'artefact GitHub Actions
pmkb-host-native-previews-* et portent un manifeste checksums.sha256.
L'artefact expire après 30 jours et ne contient pas de données privées.
Il ne s'agit PAS de captures de la Kobo, ni d'une acceptation visuelle.
Voir docs/native-ui-host-visual-review-fr.md pour la recette de revue.
