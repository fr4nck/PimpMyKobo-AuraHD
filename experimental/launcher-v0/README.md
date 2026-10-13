# PMKB — Launcher V0, prototype isolé

Le launcher v0 est un **modèle de menu Lua** et des aperçus SVG noir/blanc à utiliser **sur l'ordinateur**. Ce n'est pas un launcher embarqué sur la Kobo.

## Architecture

- Lua standard (syntaxe compatible Lua 5.1/LuaJIT), sans dépendances graphiques, réseau, disque ou système pour le module de navigation.
- Huit catégories identifiées par leurs IDs stables : `books`, `apps`, `games`, `web`, `recipes`, `notes`, `store`, `settings`.
- L'entrée Books renvoie l'**intention inerte** `{kind="intent",name="open_reader"}` ; elle ne démarre pas de programme. Le lanceur effectif KOReader doit être conçu et qualifié séparément.
- Les autres catégories sont visibles mais **inactives** (`kind="unavailable"`) : pas de faux Store, réseau, ni service persistant.
- Navigation par sélection, directions gauche/droite/haut/bas et coordonnées de tap. Aucun gestionnaire evdev réel.
- Grille logique 2 colonnes en portrait, 4 en paysage ; adapté automatiquement à la taille de l'écran. La vraie orientation et la transformation tactile restent à mesurer sur matériel.
- Rendu SVG statique monochrome sur l'hôte, avec **8 pictogrammes vectoriels dessinés en tracés 100×100** : aucune police d'icônes, image raster ou CDN.
- Indicateur de sélection en pied de page : module choisi et état « DISPONIBLE » / « BIENTOT ». C'est une **maquette de présentation**, non une mesure de rendu sur e-ink.
- Pas de gestion framebuffer, rafraîchissement e-ink ou énergie ; pas d'écriture image P1/P2/P3.

## Utilisation sur PC, depuis la racine du dépôt

Avec `lua`, `luajit` ou `texlua` disponible dans le terminal :

```sh
lua tests/test_launcher_v0.lua
lua experimental/launcher-v0/preview.lua 1080 1440 > /tmp/pmkb-launcher-portrait.svg
lua experimental/launcher-v0/preview.lua 1440 1080 > /tmp/pmkb-launcher-paysage.svg
# Aperçu avec sélection déplacée : case APPS, puis case WEB
lua experimental/launcher-v0/preview.lua 1080 1440 right > /tmp/pmkb-launcher-apps.svg
lua experimental/launcher-v0/preview.lua 1080 1440 right down > /tmp/pmkb-launcher-web.svg
```

Les scripts sont exclusivement hors matériel ; `preview.lua` écrit le SVG sur la sortie standard. Les arguments directionnels ne font que changer la sélection dans une simulation **sans touche physique, sans action déclenchée et sans lecture/écriture de carte**. Sur une machine équipée uniquement de `texlua`, remplacer `lua` par `texlua`.

Tests locaux du lot réalisés avec `texlua` (Lua 5.3) : **PASS** sur le modèle, les huit entrées, tap, navigation, grille, non-activation des catégories futures et rendu SVG ; XML SVG parsé avec succès. **LuaJIT ARM et la vraie Kobo non testés dans ce lot**.

## Invariants de reprise

- Ne pas modifier `experimental/offline-rootfs/etc/init.d/rcS`, `experimental/offline-rootfs/usr/bin/pmkb-reader`, ni le candidat FIRST BOOT scellé.
- Ne pas intégrer ce module dans une image disque et ne pas toucher aux périphériques physiques.
- Déterminer sur appareil les interfaces framebuffer EPDC, evdev tactile ZForce, gestion frontlight NTX, rotation/coordonnées, veille et politiques d'actualisation.
- Conserver la compatibilité future Calibre → bibliothèque P3 → KOReader et le chargement des applications seulement à la demande.
- Aucune écriture physique sans qualification et autorisation distinctes.

## Trajectoire possible

1. V0 : logique de menu et maquette hôte (premier commit).
2. V0.1 : **pictogrammes vectoriels, retour visuel de sélection et scénario de navigation simulé** (sur cette PR). Le modèle sait également décoder les taps, mais n'a pas de backend tactile physique.
3. V0.2 : éventuel banc de prévisualisation tactile interactif sur PC et stratégie d'actualisation e-ink *simulée* sans matériel.
4. V1 : backend e-ink léger et cycle de vie du lecteur, intégrés uniquement après qualification hardware/boot, avec refus sûrs et sans retour Nickel automatique.

## Validation du lot V0.1

Le 13 octobre 2026, une **copie hôte du code de la PR** a été testée avec **texlua (LuaTeX)** : suite `tests/test_launcher_v0.lua` **PASS** (géométrie portrait/paysage, navigation, actions inertes, huit icônes, pied de page). Les SVG `1080×1440`, `1440×1080` et la sélection `right down` ont été analysés en XML : **PASS**, huit tracés vectoriels chacun ; conversion PNG également **PASS**. Le rendu utilise un ordre d'attributs SVG déterministe. **LuaJIT ARM et matériel Kobo non testés pour la V0.1**. Le programme ne modifie toujours aucun init ni image.

## Composition validée du launcher manga/game-boy (13 octobre 2026)

Ordre **approuvé par l'utilisateur** en portrait : 

| Ligne | À gauche | À droite |
| --- | --- | --- |
| 1 | Books / Livres | Apps / Applications |
| 2 | Games / Jeux | Web |
| 3 | Recipes / Recettes | Notes |
| 4 | Store / Boutique | Settings / Réglages |

Boutique est immédiatement à gauche de Réglages ; Web occupe l'ancienne position de Boutique, Recettes l'ancienne position de Web. La barre inférieure d'accès rapide (réseau, batterie, lumière, contraste, autres raccourcis) doit rester hors de la grille.

Direction artistique approuvée : fond blanc, scènes manga/pixel-art monochromes à gris limités, **même mascotte Kobo anthropomorphe déclinée dans les huit univers**, aucune grande bannière PMKB, aucun paysage de décoration hors cartes. L'ancienne famille d'icônes vectorielles génériques de `launcher.lua` reste une **maquette technique**, non représentative de ce design visuel final.

Le visuel de référence de la conversation a été assemblé **localement** (permutation des trois panneaux de l'illustration approuvée, sans refaire les dessins), au chemin `/mnt/data/PMKB-launcher-V0.2-ordre-valide.png`. Taille 1 933 866 octets ; SHA-256 `4596389be32ba4cded6dde0940ec7528d3f0fc91e25638b0006802907a886d6d`. **Ce chemin est celui du conteneur de la conversation, pas celui du poste WSL de l'utilisateur et pas un fichier Git.** Le binaire PNG reste **à transférer dans le dépôt** ; ne pas annoncer qu'il y est déjà. L'image reste un concept : Wi-Fi connecté et batterie 87 % sont des valeurs illustratives, pas un relevé matériel.

La grille logique de navigation a été réordonnée dans `launcher.lua` ; `tests/test_launcher_v0.lua` contient désormais une assertion d'ordre exacte. Le rendu visuel final riche n'est **pas** encore implémenté en Lua ni vérifié sur l'Aura HD. Aucune modification du FIRST BOOT, de `rcS`, de `pmkb-reader` ou de stockage Kobo autorisée par ce lot.
