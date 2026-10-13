# PMKB — Launcher V0, prototype isolé

Le launcher v0 est un **modèle de menu Lua** et un aperçu SVG noir/blanc à utiliser **sur l'ordinateur**. Ce n'est pas un launcher embarqué sur la Kobo.

## Architecture

- Lua standard (syntaxe compatible Lua 5.1/LuaJIT), sans dépendances graphiques, réseau, disque ou système pour le module de navigation.
- Huit catégories identifiées par leurs IDs stables : `books`, `apps`, `games`, `store`, `web`, `notes`, `recipes`, `settings`.
- L'entrée Books renvoie l'**intention inerte** `{kind="intent",name="open_reader"}` ; elle ne démarre pas de programme. Le lanceur effectif KOReader doit être conçu et qualifié séparément.
- Les autres catégories sont visibles mais **inactives** (`kind="unavailable"`) : pas de faux Store, réseau, ni service persistant.
- Navigation par sélection, directions gauche/droite/haut/bas et coordonnées de tap. Aucun gestionnaire evdev réel.
- Grille logique 2 colonnes en portrait, 4 en paysage ; adapté automatiquement à la taille de l'écran. La vraie orientation et la transformation tactile restent à mesurer sur matériel.
- Rendu SVG statique monochrome sur l'hôte. Pas de gestion framebuffer, rafraîchissement e-ink ou énergie ; pas d'écriture image P1/P2/P3.

## Utilisation sur PC, depuis la racine du dépôt

Avec `lua`, `luajit` ou `texlua` disponible dans le terminal :

```sh
lua tests/test_launcher_v0.lua
lua experimental/launcher-v0/preview.lua 1080 1440 > /tmp/pmkb-launcher-portrait.svg
lua experimental/launcher-v0/preview.lua 1440 1080 > /tmp/pmkb-launcher-paysage.svg
```

Les scripts sont exclusivement hors matériel ; `preview.lua` écrit le SVG sur la sortie standard. Sur une machine équipée uniquement de `texlua`, remplacer `lua` par `texlua`.

Tests locaux du lot réalisés avec `texlua` (Lua 5.3) : **PASS** sur le modèle, les huit entrées, tap, navigation, grille, non-activation des catégories futures et rendu SVG ; XML SVG parsé avec succès. **LuaJIT ARM et la vraie Kobo non testés dans ce lot**.

## Invariants de reprise

- Ne pas modifier `experimental/offline-rootfs/etc/init.d/rcS`, `experimental/offline-rootfs/usr/bin/pmkb-reader`, ni le candidat FIRST BOOT scellé.
- Ne pas intégrer ce module dans une image disque et ne pas toucher aux périphériques physiques.
- Déterminer sur appareil les interfaces framebuffer EPDC, evdev tactile ZForce, gestion frontlight NTX, rotation/coordonnées, veille et politiques d'actualisation.
- Conserver la compatibilité future Calibre → bibliothèque P3 → KOReader et le chargement des applications seulement à la demande.
- Aucune écriture physique sans qualification et autorisation distinctes.

## Trajectoire possible

1. V0 : logique de menu/test et maquette PC (**ce lot**).
2. V0.1 : simulation hôte des événements clavier/tap et choix visuels, sans intégrer le boot.
3. V1 : backend e-ink léger et cycle de vie du lecteur, intégrés uniquement après qualification hardware/boot, avec refus sûrs et sans retour Nickel automatique.
