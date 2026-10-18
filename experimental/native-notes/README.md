# PMKB Notes — prototype natif KOReader V0 (18 octobre 2026)

**Statut : code hote et maquettes d'API ; jamais charge sur l'Aura HD.**
Cette preuve d'integration a l'objectif de lever l'obstacle principal : un ecran HTML
ne peut pas etre execute sur la rootfs PMKB sans moteur de navigateur. Le
prototype natif Lua charge des composants du **KOReader v2026.07.1** :
\`WidgetContainer\`, \`InputDialog\`, \`ButtonDialog\` et \`UIManager\`.

## Fonctionnement prototype

- L'arborescence \`pmkbnotes.koplugin\` est un plugin KOReader valide,
  identique dans sa forme d'entree aux plugins officiels.
- L'item **PMKB Notes (essai natif)** s'insere dans le menu des outils.
- Nouvelle note : titre puis edition plein ecran. L'editeur declenche
  **le clavier tactile natif KOReader** par \`onShowKeyboard()\`.
- Reouverture des six dernieres notes de la session.
- Les donnees utilisent le schema **\`pmkb-notes-v1\`** : \`id\`, \`title\`,
  \`text\`, \`strokes\`, \`typography\`, \`created\`, \`updated\`.
  Les croquis sont preserves en memoire mais leur dessin n'est pas implemente
  dans ce lot. Le module modele est sans dependance KOReader.
- Tous les changements restent **en RAM et sont perdus a l'arret**.
  L'interface l'indique explicitement. Ne pas utiliser pour des notes
  importantes : import/export JSON, sauvegarde P3 et restauration sont
  **non implementes** dans cette variante. Le prototype navigateur garde
  son import/export et son stockage local independants.
- Aucune nouvelle gestion de framebuffer, EPDC, ZForce, orientation
  ou clavier par pilotes maison : KOReader les pilote via les API existantes.
  Ce code ne garantit ni leur bon fonctionnement ni la reprise de veille.
- L'ouverture d'un plugin natif ne garantit pas son integration au launcher
  PMKB autonome ; le chargement doit etre teste dans le runtime KOReader
  utilise par PMKB, sans toucher aux images scellees ni a P2.

## Compatibilite et provenance

Sources API lues sur \`koreader/koreader\`, tag **v2026.07.1** :
- \`plugins/hello.koplugin/main.lua\` (menu plugin, SHA \`8fbef77c0467d78725631087db25fa878d4de8ef\`).
- \`plugins/texteditor.koplugin/main.lua\` (éditeur natif, SHA \`9a8c7dac6edc46d11a6964f42027ba97ff6d9ed7\`).
- \`frontend/ui/widget/inputdialog.lua\` (plein écran, save_callback, clavier, SHA \`ec798241a55a4c83c8b0c758261d7bf7d60a4542\`).
- \`frontend/pluginloader.lua\` (forme \`.koplugin\` et chemin des modules).

Le plugin ne copie aucun code KOReader : il utilise seulement des API publiques.
Il reste sous \`experimental/native-notes\`, non ajoute au paquet/boot.

## Tests

Lancer depuis la racine du dépôt : \`lua tests/test_pmkb_notes_native.lua\`.
Exécutions CI dans le job Linux disposant déjà de Lua 5.1. Les tests de
module sont purs ; la couche KOReader est testee par stubs, **pas** par
l'ecran physique. Aucun \`/dev/fb0\`, \`/dev/input\`, \`/dev/ntx_io\`,
\`/dev/watchdog\` ou partition n'est ouvert.

## Gates avant integration

1. Faire qualifier hors appareil les versions des interfaces requises
   dans le paquet exact KOReader v2026.07.1 conservé.
2. Choisir/qualifier un emplacement persistant pour les notes **sans
   ecriture sur P1 RO/P2** et avec secours import/export JSON avant
   d'autoriser une sauvegarde automatique. Ne pas utiliser un chemin
   suppose de \`DataStorage\` par defaut.
3. Effectuer une recette tactile sur la vraie Aura HD, avec
   clavier apparaitre/disparaitre, appui long/accent, saisie, sortie,
   rotation et test de ghosting. Cette etape necessitera autorisation
   physique specifique.
4. Comparer les fichiers JSON generes au contrat JS original et
   traiter les cas d'erreur de stockage/recovery avant la fusion.
5. Conserver la PR #29 en brouillon ; ne pas activer l'application
   dans la carte microSD ni le launcher sur simple CI verte.

**Pourquoi ce lot frugal ?** Aucune dépendance de navigateur,
aucun service de clavier additionnel : KOReader gère le rafraîchissement,
le clavier et le tactile. On conserve de la RAM et du temps CPU au repos.
Cela n'est pas encore une mesure de gain d'autonomie.
