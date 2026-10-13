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
2. V0.1 : **pictogrammes vectoriels, retour visuel de sélection et scénario de navigation simulé** (PR #21 fusionnée dans `main`). Le modèle sait également décoder les taps, mais n'a pas de backend tactile physique.
3. V0.2 : **direction graphique validée et assets archivés** ; le banc de prévisualisation tactile interactif et la stratégie d'actualisation e-ink restent à réaliser hors matériel.
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

Le visuel de référence a été assemblé sans redessiner les scènes et est **désormais archivé en haute résolution dans Git**, à l'emplacement [`assets/v02/source/PMKB-launcher-V0.2-ordre-valide.png`](assets/v02/source/PMKB-launcher-V0.2-ordre-valide.png). Dimensions **1086 × 1448** ; taille **1 933 866 octets** ; SHA-256 `4596389be32ba4cded6dde0940ec7528d3f0fc91e25638b0006802907a886d6d`. Import vérifié dans `main`, commit [`cd154a92`](https://github.com/fr4nck/PimpMyKobo-AuraHD/commit/cd154a92faaf912fc39b2f4984d0c48fcea07854) ; CI verte.

### Assets V0.2 sauvegardés (sans modification des dessins)

- [Source RGB approuvée](assets/v02/source/PMKB-launcher-V0.2-ordre-valide.png) — 1 933 866 octets, référence immuable.
- [Version **16 gris**, recommandée pour l'étude](assets/v02/optimise/PMKB-V0.2-16gris.png) — 1080 × 1440, **250 757 octets**, PNG indexé 4 bits.
- [Version 4 gris](assets/v02/optimise/PMKB-V0.2-4gris.png) — 98 919 octets.
- [Version noir/blanc 1 bit](assets/v02/optimise/PMKB-V0.2-1bit.png) — 46 780 octets.
- [Comparatif agrandi](assets/v02/optimise/PMKB-comparatif-zoom.png).
- [Manifeste et SHA-256](assets/v02/MANIFEST-validated.json).
- [Note de qualification et mesures](../../docs/launcher-v02-asset-qualification-2026-10-13-fr.md).

Le [miniature 1 bit 128 px](assets/pmkb-v02-layout-thumbnail-128.png) reste disponible pour la documentation, mais **ne remplace pas les images pleine résolution**. La maquette reste conceptuelle : les indications Wi-Fi connecté et batterie 87 % sont fictives. **Le rendu Lua actuel utilise encore les anciens pictogrammes vectoriels** ; les graphismes approuvés ne sont pas encore découpés en tuiles ni reliés au moteur d'affichage e-ink.

La grille logique de navigation a été réordonnée dans `launcher.lua` ; `tests/test_launcher_v0.lua` contient désormais une assertion d'ordre exacte. Le rendu visuel final riche n'est **pas** encore implémenté en Lua ni vérifié sur l'Aura HD. Aucune modification du FIRST BOOT, de `rcS`, de `pmkb-reader` ou de stockage Kobo autorisée par ce lot.

## V0.3 — bandeau d'état (simulation PC seulement)

- Le modèle Lua inclut maintenant **sept zones** sous la grille : batterie/charge, Wi-Fi, frontlight, contraste logiciel, rafraîchissement e-ink, veille et réglages.
- **Valeurs inconnues par défaut** : jamais de faux Wi-Fi connecté ni de pourcentage de batterie inventé.
- `launcher.with_status(state, telemetry)` reçoit des **mesures fournies de l'extérieur**, les valide (pourcentages entiers 0–100 ; états Wi-Fi énumérés), et crée un nouvel état sans modifier le précédent. Aucune interrogation de la Kobo.
- Les taps sur le bandeau produisent uniquement `{kind="quick_request",id="wifi"|...}` : demandes **inertes**, aucun Wi-Fi activé, aucune écriture sysfs, aucun changement de luminosité ou de veille.
- Le nouveau bandeau est visible dans **l'ancien aperçu SVG technique à pictogrammes**, pas encore superposé au PNG manga validé. L'original RGB et ses variantes optimisées sont strictement inchangés.
- La capture de données batterie/USB, réseau, rétroéclairage, framebuffer/EPDC et mise en veille nécessitera un backend séparé, qualifié sur le matériel, **hors du candidat FIRST BOOT scellé**.

Depuis la racine du dépôt, avec Lua 5.1/5.3/LuaJIT :

```sh
lua tests/test_launcher_v0.lua
lua tests/test_launcher_statusbar.lua
lua experimental/launcher-v0/status-preview.lua > /tmp/pmkb-v03-status-preview.svg
```

Le scénario `status-preview.lua` injecte des valeurs **fictives et clairement simulées** (batterie 87 %, Wi-Fi coupé, frontlight 25 %) afin de vérifier visuellement la maquette technique. Aucune interaction matérielle.

## V0.4 — accueil manga réel, simulateur tactile hors matériel

Le fichier [`simulator.html`](simulator.html) ouvre l'illustration **16 gris / 4 bits validée** directement depuis `assets/v02/optimise/PMKB-V0.2-16gris.png` (250 757 octets, SHA dans le manifeste). **Aucun PNG n'est redessiné, recadré ni réenregistré** : l'image reste en fond et les huit surfaces cliquables se superposent à ses panneaux aux coordonnées fixes de 1080 × 1440. Cette maquette est portrait uniquement.

La zone inférieure `x=58, y=1325, w=965, h=66` du PNG comporte des valeurs fictives : elle est **recouverte uniquement à l'affichage** par une nouvelle barre, dont les sept raccourcis reprennent les IDs du modèle Lua V0.3 (`battery`, `wifi`, `frontlight`, `contrast`, `refresh`, `sleep`, `settings`). L'image stockée dans Git reste octet pour octet identique à la source approuvée.

Par défaut : données inconnues. Le panneau de démonstration propose des scénarios explicitement **fictifs**, plus des curseurs batterie/frontlight. Les clics des raccourcis n'allument aucun matériel : ils affichent uniquement `quick_request`. Les livres produisent l'intention inerte `open_reader` (ne lance **pas** KOReader) ; les sept autres rubriques restent « à venir ». Navigation par clic, flèches et Entrée.

### Ouvrir sur le PC

**Debian WSL, depuis la racine du dépôt** (aucune dépendance externe ni serveur nécessaires) :

```bash
cd /home/Deniel/pmkb-test
git switch main
git pull --ff-only origin main
explorer.exe "$(wslpath -w experimental/launcher-v0/simulator.html)"
```

Le fichier local ouvre le navigateur Windows. En cas de restrictions locales sur les fichiers `file://`, démarrer depuis la racine du dépôt `python3 -m http.server 8765 --bind 127.0.0.1` et ouvrir `http://localhost:8765/experimental/launcher-v0/simulator.html` (serveur **local** seulement).

`simulator.js` reprend à l'identique l'ordre des huit IDs Lua et les sept zones de V0.3. Cette interface DOM JavaScript ne réemploie pas directement l'exécution Lua, mais des tests automatiques contrôlent cette correspondance. Il n'y a ni backend réseau, ni usage de `fetch`, ni stockage local, ni accès aux partitions.

Tests : `python -m unittest discover -s tests -p test_launcher_simulator_assets.py -v` et `node --test tests/test_launcher_simulator.cjs`; CI Python multi-OS et Node dans un seul job Linux. La vérification tactile réelle de l'Aura HD reste **UNQUALIFIED**.
