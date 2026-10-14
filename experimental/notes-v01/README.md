# PMKB Notes V0.2 — éditeur épuré, typographie et croquis (prototype PC)

**Statut : prototype hôte indépendant, non installé sur la Kobo.** Cette application est le premier outil PDA PMKB : un carnet de notes avec une petite palette graphique optionnelle. Elle ne dépend pas du launcher et ne modifie aucun composant FIRST BOOT.


## V0.2 — édition pleine largeur et choix de polices

La V0.2 est développée **sur une branche empilée sur la PR Notes V0.1 (#26)**, indépendamment du launcher V0.6 (#25).

- **Espace d'écriture prioritaire** : « Mes notes » est fermé au démarrage, accessible via « ☰ Mes notes », et refermé après ouverture d'une note. Liste, recherche et sauvegardes JSON restent dans ce panneau. Fermeture par ×, clic à l'extérieur ou Échap.
- **Barre compacte** : nouvelle note, Mes notes, enregistrer, menu de suppression. Croquis reste facultatif et sa palette est désormais escamotable.
- **Deux lignes maximum pour tout le haut de l'écran** : commandes, puis titre et onglets Texte/Croquis. Le bandeau de présentation et la palette de dessin sont dans Plus. Aucun état au chargement ou au repos ; l'enregistrement remplace brièvement le libellé du bouton, sans espace entre les raccourcis. À petite largeur, les commandes secondaires deviennent des icônes nommées pour l'accessibilité.
- **Typographie discrète et sur demande** : bouton « Aa » ouvrant un petit panneau flottant (fermeture clic extérieur ou Échap), police pour la note entière et taille compacte de 12 à 36 pixels. L'interligne n'est plus un champ visible : les anciennes valeurs du JSON sont conservées sans altération. Pas de mise en forme différente par ligne ou passage sélectionné. Les préférences restent dans le JSON pmkb-notes-v1 compatible V0.1.
- **Import local** : TTF, OTF, WOFF et WOFF2, jusqu'à 2 Mo, contrôle extension et signature, chargement avec FontFace. Les familles système de repli peuvent utiliser des polices Linux/Windows, sans prétendre inventorier toutes les polices installées.
- **Limitation explicite** : les fichiers de polices importées ne sont **ni conservés ni intégrés au JSON**, seul leur identifiant y figure. Après actualisation, une police de repli est utilisée jusqu'au réimport. Le TXT ne conserve pas la typographie. Aucun téléchargement automatique depuis DaFont : respecter les licences.
- Ni mise en forme caractère par caractère, ni export PDF dans ce lot. Pas de réseau, pas de dépendance cloud.

**Qualification manuelle PC requise avant fusion** : panneau replié, import TTF/OTF, changement de note, rafraîchissement, lecture des notes V0.1, JSON, croquis. Aucune qualification e-ink, tactile ou système Kobo.

## Fonctions disponibles

Les commandes courantes sont des pictogrammes : disquette pour enregistrer, T/crayon pour les modes, flèche sortante pour l'export. La famille Fluent est embarquée localement, avec licence MIT ; noms accessibles et infobulles restent présents. Pas de bibliothèque distante ni de police d'icônes. La politique UX documente désormais le Design System et l'iconographie PMSL, en plus de l'ADR-005.

Le bouton « + » seul crée une note. Pour sortir : **Plus → Quitter Notes**, avec vérification de l'enregistrement avant retour au simulateur du launcher. Si le stockage échoue, un rappel d'export JSON et une confirmation précèdent la sortie. Ce retour navigateur n'active pas la tuile Notes du launcher et n'est pas une intégration matériel.

L'export de la note est en haut, sur la même ligne que le titre et Texte/Croquis : TXT en mode Texte, PNG en mode Croquis. Les détails des formats et les [sources d'inspiration](../../docs/notes-ux-policy.md#sources-dinspiration-complémentaires) sont documentés ; l'export JSON du carnet reste dans Mes notes.

**Règle UX durable et obligatoire** : [politique Notes issue de l'ADR-005](../../docs/notes-ux-policy.md). L'état court est placé près d'Enregistrer, sans grande case. Les erreurs apparaissent seulement si nécessaires et proposent une correction ; le rappel d'export JSON est dans Mes notes. Les contrôles courts utilisent des largeurs sémantiques communes. La fusion des PR #25/#26/#27 exige la validation visuelle explicite de l'utilisateur.

- Liste de notes : création, sélection, renommage, recherche plein texte et suppression avec confirmation.
- Éditeur de texte UTF-8, fonctionnement hors ligne, limites explicites (100 notes, 120 000 caractères par note).
- Onglet **Croquis** par note : crayon, gomme, traits fins/moyens/épais, annuler/rétablir, effacer avec confirmation, tracés au doigt ou à la souris via Pointer Events.
- Dessins stockés sous forme de traits éditables, pas d'aplatissement dans la sauvegarde JSON. Export facultatif en **PNG**.
- Sauvegarde automatique dans le **stockage local du navigateur** si disponible, avec bouton « Enregistrer » et état de sauvegarde. Export manuel du carnet entier en **JSON** et de la note en **TXT** ; import JSON validé avec confirmation de remplacement.
- Aucun compte, réseau, backend serveur, service persistant, SDK ou dépendance JavaScript tierce. Aucun moteur e-ink, clavier virtuel Kobo ou synchronisation Wi-Fi activés.

### Important — stockage

Le stockage du navigateur **n'est pas une sauvegarde durable garantie**. Il peut être effacé lors du nettoyage des données du navigateur, d'un changement de profil ou d'origine HTTP, ou bloqué selon le navigateur. **Exporter régulièrement le fichier JSON** : il contient textes et croquis. L'import remplace volontairement le carnet actuel **après confirmation**. Le format JSON est versionné (\`pmkb-notes-v1\`), avec validation stricte et limites de taille ; aucun HTML/script importé n'est interprété.

## Démarrage sur PC — Debian WSL

Terminal **Debian WSL**, dépôt \`fr4nck/PimpMyKobo-AuraHD\` :

\`\`\`bash
cd /home/Deniel/pmkb-test || exit 1
git fetch origin
git switch --detach origin/feat/pmkb-notes-v02-typography-drawer
python3 -m http.server 8766 --bind 127.0.0.1
\`\`\`

Puis ouvrir sur **le même PC** : http://localhost:8766/experimental/notes-v01/index.html

Le serveur Python sert seulement les fichiers locaux à votre navigateur. Le carnet utilise \`localStorage\` sur cette origine locale stable (même adresse et port à chaque ouverture). **Il ne synchronise rien**. Arrêter avec Ctrl+C. Éviter \`file://\` pour l'enregistrement automatique, car certains navigateurs bloquent le stockage local sur ces pages.

## Architecture et tests

- \`notes-core.js\` : modèle de données indépendant du DOM, export/import JSON, validation, recherche, traits dessinés, limites, noms de fichiers sûrs. Portable vers un autre moteur d'interface/une autre liseuse.
- \`notes-app.js\` : interface navigateur, écoute tactile/souris, rendu canvas, export de fichiers et stockage browser-local.
- \`index.html\` : interface monochrome responsive, onglet Texte / Croquis.
- \`tests/test_notes_core.cjs\` : tests Node natifs du modèle, export/import, limites, intégrité et cas invalides.
- `tests/test_notes_app.cjs` : tests de l'adaptateur réel avec stockage/DOM simulés, erreurs conditionnelles, quota, import refusé, retry et export ; CI Node 22 Windows/Linux.
- \`tests/test_notes_host_assets.py\` : contrôles de structure, hors réseau/matériel, inclus dans la CI Python.

Depuis la racine du dépôt :

\`\`\`bash
node --test tests/test_notes_core.cjs
python3 -m unittest discover -s tests -p test_notes_host_assets.py -v
\`\`\`

La première **qualification visuelle et fonctionnelle sur navigateur PC** doit être effectuée avant fusion de la PR. La sauvegarde effective dans le navigateur, l'export PNG, la précision du doigt et le comportement sur écran réduit nécessitent un essai interactif manuel : les tests automatiques ne les prouvent pas.

## Limites avant matériel

Aucun affichage EPDC, clavier virtuel tactile Kobo, frontlight, pilote Wi-Fi, gestion d'énergie, sauvegarde dans P3, lancement depuis le bouton Notes de notre launcher, ni test tactile réel. Ces opérations feront l'objet de qualifications séparées. Il faudra aussi mesurer la faisabilité du dessin **au doigt** (pas de stylet actif fourni par l'Aura HD) et le coût des rafraîchissements e-ink. L'intégration au launcher V0.6, encore en PR dédiée, n'est **pas** réalisée.

**Aucune image PNG manga validée, aucune partition P1/P2/P3 ni composant FIRST BOOT, \`rcS\` ou \`pmkb-reader\` n'est modifié.**
