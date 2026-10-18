# PMKB Native V0 — frontières matériel / UI (19 octobre 2026)

**Décision : livrer le cœur C11 et une preuve de rendu hôte, sans inventer
un portage ARM, LVGL ou EPDC.** Cette note complète le README.

## Contrats et dépendances

| Module | Entrée / sortie | Dépendance runtime |
| --- | --- | --- |
| \`pmkb_text_keyboard.c\` | UTF-8, UTF-16, curseur, clavier AZERTY/numérique/symboles | C11 |
| \`pmkb_notebook.c\` | notes dynamiques, horodatage explicite, JSON \`pmkb-notes-v1\` en RAM | C11 |
| \`pmkb_app.c\` | vues Notes, focus, événements génériques \`TAP/TEXT/ENTER\` | PMKB-UI uniquement |
| \`pmkb_surface.c\` | 8 bpp gris, pixels modifiés, bitmap de démonstration | C11 |
| \`pmkb_backend.c\` | callback de présentation des rectangles, accusé de réception requis | Aucun accès matériel |
| LVGL, FBInk, evdev, MXCFB | non raccordés | **non qualifiés** |

Le consommateur des événements devra fournir des coordonnées normalisées au
référentiel PMKB-UI. Le futur backend peut convertir les mesures multitouch
\`eventN\` depuis ZForce et les marqueurs de mise à jour du panneau EPDC.
Aucun appel d'ioctl ne doit être émis par le modèle ou les widgets.

Le contrat \`pmkb_surface_present()\` appelle le backend avec le **seul
rectangle marqué comme modifié**. Si le backend signale une erreur, le
rectangle reste en attente et la couche HAL peut réessayer. Un callback
qui renvoie OK n'est pas la preuve d'un rafraîchissement physique : le HAL
devra attendre le marqueur MXCFB avant d'accuser réception. Le prototype
utilise un tampon complet 8 bits pour les captures hôtes ; une stratégie
plus frugale peut venir après les premières mesures.

## Budget mémoire de base

- Surface simulée 320 × 480 : **153 600 octets** de pixels.
- Surface E-Ink 1080 × 1440 à 8 bpp : **1 555 200 octets**
  (~1,48 Mio), hors pile, heap, glyphes, notes et buffers noyau.
- Notes : allocation dynamique jusqu'à 100, limite de texte par note
  120 000 unités UTF-16, pas de tableau préalloué de 12 Mo.
- Clavier : disposition statique, aucun thread ni boucle de rendu.
- Toute énergie/batterie/autonomie reste **non mesurée**.

## Contrôles UX ADR-005

Deux lignes maximum en haut (48 px chacune en simulation V0);
contrôles carrés tactiles 48 px et grille clavier 44 px de haut.
Titre et focus visibles, édition prioritaire, menus non résidents.
Cette simulation n'est **pas** une recette visuelle à 320 px/200 % ni
une application Kobo. Les glyphes accentués ne sont pas encore correctement
dessinés par la petite police ASCII embarquée.

## Choix LVGL, laissé ouvert et explicite

LVGL est un candidat pertinent pour l'interface finale, mais le dépôt
\`main\` ne fournit pas ses headers, sa configuration ni une dépendance
vérifiée pour libc/toolchain ARM Cortex-A8. Installer LVGL maintenant
sans essais contradictoires fragiliserait l'objectif 512 Mio.
Privilégier un adaptateur fin utilisant le modèle et le clavier C11
plutôt que réécrire Notes. Ne pas lier les API LVGL au contrat applicatif.

Porte suivante : évaluer une version LVGL précise, la compiler pour
ARM, vérifier les ABI/fonctions mémoire, puis relier les zones sales aux
\`MXCFB_SEND_UPDATE\` / \`WAIT_FOR_UPDATE_COMPLETE\` avec waveforms
conservées, d'abord sur banc simulé. Pas de changement P1/P2/U-Boot,
pas de flash, pas de téléchargements dans ce lot.
