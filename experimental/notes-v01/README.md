# PMKB Notes V0.1 — texte + croquis (prototype PC)

**Statut : prototype hôte indépendant, non installé sur la Kobo.** Cette application est le premier outil PDA PMKB : un carnet de notes avec une petite palette graphique optionnelle. Elle ne dépend pas du launcher et ne modifie aucun composant FIRST BOOT.

## Fonctions disponibles

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
git switch --detach origin/feat/pmkb-notes-v01-host
python3 -m http.server 8766 --bind 127.0.0.1
\`\`\`

Puis ouvrir sur **le même PC** : http://localhost:8766/experimental/notes-v01/index.html

Le serveur Python sert seulement les fichiers locaux à votre navigateur. Le carnet utilise \`localStorage\` sur cette origine locale stable (même adresse et port à chaque ouverture). **Il ne synchronise rien**. Arrêter avec Ctrl+C. Éviter \`file://\` pour l'enregistrement automatique, car certains navigateurs bloquent le stockage local sur ces pages.

## Architecture et tests

- \`notes-core.js\` : modèle de données indépendant du DOM, export/import JSON, validation, recherche, traits dessinés, limites, noms de fichiers sûrs. Portable vers un autre moteur d'interface/une autre liseuse.
- \`notes-app.js\` : interface navigateur, écoute tactile/souris, rendu canvas, export de fichiers et stockage browser-local.
- \`index.html\` : interface monochrome responsive, onglet Texte / Croquis.
- \`tests/test_notes_core.cjs\` : tests Node natifs du modèle, export/import, limites, intégrité et cas invalides.
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
