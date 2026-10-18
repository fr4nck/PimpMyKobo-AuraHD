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

Test C : UTF-8/UTF-16, accents, sélection, touches virtuelles, garde-fous,
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
