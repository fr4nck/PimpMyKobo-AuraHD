# PMKB — qualification des visuels V0.2, 13 octobre 2026

**Périmètre : optimisation hors matériel du visuel VALIDÉ. Aucun nouveau dessin. Aucun changement du launcher Lua ni du FIRST BOOT.**

## Source canonique

- Nom du PNG source : `PMKB-launcher-V0.2-ordre-valide.png`.
- Format : **1086 × 1448, RGB, 1 933 866 octets**.
- SHA-256 : `4596389be32ba4cded6dde0940ec7528d3f0fc91e25638b0006802907a886d6d`.
- **Archivé dans Git depuis le commit [`cd154a92`](https://github.com/fr4nck/PimpMyKobo-AuraHD/commit/cd154a92faaf912fc39b2f4984d0c48fcea07854)** : [`experimental/launcher-v0/assets/v02/source/PMKB-launcher-V0.2-ordre-valide.png`](../experimental/launcher-v0/assets/v02/source/PMKB-launcher-V0.2-ordre-valide.png). Source conservée sans modification.
- Un aperçu 1-bit de 128 px est déjà versionné sous `experimental/launcher-v0/assets/pmkb-v02-layout-thumbnail-128.png` (ce n'est **pas** le PNG original).
- Décision utilisateur : **ne plus changer la composition ni les dessins**. Grille portrait : Livres | Applications ; Jeux | Web ; Recettes | Notes ; Boutique | Réglages. Fond blanc, atmosphère manga/pixel-art, mascotte Kobo, bandeau de raccourcis en bas.

## Essai de compression hors matériel

Réduction à la **résolution native 1080 × 1440** par interpolation LANCZOS, conversion en luminance, quantification en palette de gris à niveaux équidistants sans dithering supplémentaire. PNG optimisés (Pillow).

| Variante | Taille octets | PNG réel | SHA-256 |
| --- | ---: | --- | --- |
| Grayscale8 (256 gris) | 728 594 | 8-bit luminance | `c6e680c9dd1020db954e8182bdfdd3fe679fed57aa05d50bbc7cad2ef6c8c485` |
| **16 gris — conseillé** | **250 757** | **PNG indexé palette, 4 bpp** | `d4408b0a04d27f3d493e68acdcee21b4905db76f8c845f08e8a97619227819b6` |
| 4 gris — alternatif | 98 919 | PNG indexé palette, 2 bpp | `260d5e2cc35a125a3184cefc208971f328e63df958a4a834a135563075861b25` |
| Noir/blanc 1-bit — dégradé visuel | 46 780 | PNG grayscale, 1 bpp | `23de94889bd83cf670c1886230a14a86f0a5117bb12df903e040d7e586426456` |

Soit environ **87 % de réduction pour les 16 gris** et **95 % pour les 4 gris** par rapport au PNG source RGB. Ces valeurs sont des *tailles de fichier sur disque*, **pas des mesures de RAM ou de latence de rafraîchissement e-ink**.

La variante 16 gris affiche un rendu visuellement très proche de la source, avec une perte mesurée PSNR **36,16 dB** sur le PNG source ramené à 1080 × 1440 en luminance ; la variante 4 gris est plus agressive (**25,23 dB**) et le noir/blanc 1 bit simplifie nettement les ombres (**16,57 dB**). Il s'agit de mesures numériques, pas d'une qualification sur écran physique.

Les variantes optimisées sont désormais **commitées dans GitHub** : [répertoire `experimental/launcher-v0/assets/v02/`](../experimental/launcher-v0/assets/v02/) avec `source/`, `optimise/` et [`MANIFEST-validated.json`](../experimental/launcher-v0/assets/v02/MANIFEST-validated.json). Le commit `cd154a92` a été poussé sur `main` et sa CI est **verte**. **Cela ne signifie pas que les graphismes sont intégrés dans le rendu Lua ou qualifiés sur la Kobo**.

Le ZIP de transmission reste dans les artefacts de la conversation (les fichiers extraits sont maintenant dans Git) : `PMKB-launcher-V0.2-assets-optimises.zip`, **2 670 637 octets**, SHA-256 `312583af3ebc8b4d5c230a58be9e49752303c980a20f851e41c6e057276ebc52`. Il contient la source canonique, les variantes 16/4/1-bit, un zoom comparatif et un manifeste à empreintes.

## Limites d'architecture

- Le rendu Lua actuel dans `experimental/launcher-v0/launcher.lua` affiche encore les anciens pictogrammes vectoriels : les scènes manga sont **une maquette PNG**, pas encore un atlas navigable.
- Dans le visuel, Wi-Fi connecté et batterie 87 % sont **des exemples fictifs**. Pour une vraie interface, cette barre doit être **redessinée par les données runtime**, pas laissée en état figé dans le fond PNG. Le contraste et le frontlight devront être reliés au matériel après qualification.
- Les huit scènes pourraient être découpées sans altération pour constituer un atlas graphique statique distinct des zones de statut dynamiques ; ne pas figer les métriques d'interface avant essai sur Aura HD.
- Le décodage PNG, la rotation/coordonnées, le rafraîchissement e-ink, le tactile et la consommation RAM réelle restent à tester sur Kobo.
- Les images P1/P2/P3, `rcS`, `pmkb-reader` et FIRST BOOT restent intacts. Pas de flash ou montage physique autorisé par cette note.

**Étape suivante :** étudier la découpe sans altération des huit tuiles et la séparation de la barre de statut dynamique ; qualifier l'affichage sur matériel avant toute intégration boot. L'import Git des images est **terminé**. Préférer **16 gris / PNG 4 bits** comme point de départ et conserver l'original RGB comme référence immuable.
