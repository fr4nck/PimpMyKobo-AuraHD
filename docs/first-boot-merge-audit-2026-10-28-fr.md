# PMKB — Préparation de la convergence de FIRST BOOT #7

Date : 28 octobre 2026. Périmètre exclusivement GitHub, sans reconstruction ou écriture de microSD, FIRST BOOT, P1/P2/P3 ni firmware.

## Provenance immuable

- Branche de départ FIRST BOOT #7 : `4b23f8c4d1d3171fc9ec6e7d78c7a5d14badd029` ; ancêtre commun : `f2234302203525ac1118e6243c213e96471e0135`.
- Dernier `main` pris en compte : `1f1428f1b3c86fea960c4fc0910934ea178b19f3`.
- La branche FIRST BOOT comptait **99** commits propres et **503** commits supplémentaires dans `main`; 64 chemins différaient depuis l'ancêtre commun et 19 chemins avaient été touchés des deux côtés.

## Résolution sans perte volontaire

- Base du nouvel arbre de fusion : `main`, pour ne retirer **aucun** des derniers travaux Launcher, Notes, Store, PowerLab, HAL ni audit ARM.
- Les ajouts et corrections de FIRST BOOT (builder, audit ARM, preflight, PMKB Live, garde P3, détection ZForce/NTX, tests) sont réintroduits depuis la branche #7 par empreinte de blobs Git, sans modifier leurs octets.
- `.github/workflows/tests.yml` : les jobs Python/Qt et les tests Launcher Lua/Node actuels sont préservés ; le job **qualification-live** de FIRST BOOT est ajouté. Ce job peut installer des dépendances uniquement sur le runner GitHub Actions ; aucune opération sur le poste utilisateur.
- `docs/ROADMAP.fr.md` et `docs/ROADMAP.md` : versions actuelles de `main` conservées. Les anciens plans FIRST BOOT sont publiés séparément, étiquetés comme **archives sans autorisation matérielle**.
- `docs/offline-hardware-qualification-fr.md` : conserver la correction watchdog datée du 12/10 sur `main`, absente de la vieille branche.
- `tools/rebuild-rootfs.py` : conserver le bit exécutable de `main` ; les nouveaux scripts boot PR #7 conservent leur mode 0755.

## Prochaines portes (ne pas confondre)

1. Contrôler l'état mergeable après mise à jour #7 et que le diff ne touche aucun autre fichier de `main`.
2. Exécuter la CI du **HEAD de fusion exact**, incluant tests Python/Qt, Lua/Node et ISO Linux Live ; corriger tout échec avant d'envisager la fusion.
3. Auditer la concordance de l'image FIRST BOOT scellée avec les sources et les outils, puis qualifier séparément une nouvelle image, les bibliothèques ARM et le démarrage E606C0.
4. La PR #56 KOReader est **empilée sur la branche #7** ; son HEAD devra être requalifié après cette synchronisation. La PR #55 HAL est indépendante, non fusionnée dans ce lot.

**Aucune qualification matérielle n'est déduite de la CI.**
