# PMKB — Calculatrice scientifique V0 (prototype navigateur hors ligne)

Application autonome **non installée sur la Kobo** :
\`experimental/calculator-v01/index.html\`. Aucun compte, service, réseau, stockage persistant ni dépendance téléchargée.

Le moteur \`calculator-core.js\` est pur et indépendant du DOM. Il analyse et évalue les expressions sans \`eval()\` ni exécution de code. Fonctions : quatre opérations, parenthèses, puissances \`^\`, pourcentages (division par 100), \`sin\`/\`cos\`/\`tan\`, \`asin\`/\`acos\`/\`atan\`, \`ln\`, \`log\` (base 10), \`sqrt\` / \`√\`, \`abs\`, constantes \`π\` et \`e\`, mémoire \`Ans\`. Le mode DEG/RAD s'applique aux fonctions trigonométriques. Les résultats sont limités par la précision standard \`Number\` JavaScript (IEEE-754), affichés sur 12 chiffres significatifs et refusés si non finis. Aucun calcul symbolique ou précision arbitraire.

L'écran propose un pavé tactile monochrome à six colonnes, chaque bouton d'au moins 44 px de haut, et un historique limité aux huit derniers calculs **de la session seulement**. \`C\` efface l'expression ; \`AC\` efface aussi \`Ans\` et l'historique. \`Ans\` récupère la dernière valeur, sans écriture permanente.

Depuis Notes, **Plus → Calculatrice** déclenche la vérification de sauvegarde déjà utilisée pour quitter l'application. Si la sauvegarde échoue, l'utilisateur doit confirmer la navigation et peut exporter son carnet JSON. La calculatrice offre un lien de retour vers Notes, sans transfert automatique de résultat.

### Vérification sur PC

Dans le même serveur local que Notes, ouvrir : \`http://localhost:8766/experimental/calculator-v01/index.html\`.

Tests : \`node --test tests/test_calculator_core.cjs tests/test_calculator_app.cjs\` et \`python -m unittest discover -s tests -p test_calculator_host_assets.py -v\`.

Tests automatisés sur données synthétiques seulement. Aucun essai EPDC/ZForce/performances/consommation ou mesure d'autonomie Aura HD n'est revendiqué. Rendu à 320 px, zoom 200 %, ergonomie tactile et comportement navigateur réel restent à qualifier avant fusion.
