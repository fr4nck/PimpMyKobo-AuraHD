# Préparer un plan de restauration P1

`prepare-p1-restore.py` prépare un plan vérifiable exclusivement à partir de fichiers locaux. Il n'ouvre aucun périphérique et n'effectue aucune restauration. Le choix du backend physique et de son verrouillage reste distinct.

```sh
python3 tools/prepare-p1-restore.py legacy.json rebuilt.img.rebuild.json rebuilt.img \
  full-card.img full-card.img.backup.json simulated.img simulated.img.simulation.json plan.json
```

Pour FIRST BOOT, passer le rapport producteur original, sans modifier son `tool` ni fabriquer des contrôles de reconstruction :

```sh
python3 tools/prepare-p1-restore.py legacy.json candidate.img.koreader-build.json candidate.img \
  full-card.img full-card.img.backup.json simulated.img simulated.img.simulation.json first-boot-plan.json
sha256sum first-boot-plan.json
```

Les anciens plans sans `candidate_source`, `evidence_sha256.rootfs_report` ou `simulation_sha256` doivent être régénérés à partir des preuves ; le validateur scellé les refuse.

Le rapport d'acquisition doit suivre le contrat `read-only-full-card-acquisition`, version 1 : acquisition complète réussie, source ouverte `rb`, longueur exacte, MBR/HWCONFIG et références historiques vérifiés, empreintes identiques de la copie, de sa relecture et de la deuxième lecture complète de la source. Ce rapport n'est pas un manifeste natif `backup-aura-hd`.

L'outil recalcule les empreintes des fichiers, revalide le contrat legacy et le rapport typé `rebuild-rootfs` ou `build-koreader-rootfs`, et relit P1 ainsi que toutes les zones conservées dans la simulation. Un rapport non signé démontre une cohérence, pas une authenticité. Pour `build-koreader-rootfs`, il relit les paramètres ext4 (label, blocs, taille, inodes, features et octets de queue), les compare au rapport et à la référence P2 préservée, puis exécute `e2fsck -f -n` en lecture seule. Pour `rebuild-rootfs`, il vérifie les contrôles déclarés du rapport. Aucun essai de démarrage n'est effectué. Les fichiers doivent rester stables pendant ces contrôles ; un futur exécuteur devra les revérifier avant toute écriture.

Le plan décrit l'empreinte complète exigée de la future carte cible, les bornes exactes de P1, l'empreinte de remplacement et les régions à préserver, `simulation_sha256` pour l'image simulée complète et `candidate_source` pour le type et l'empreinte du rapport producteur. Aucun rapport PMKB n'est converti en rapport de reconstruction. La sauvegarde complète constitue la source du retour arrière de P1. La provenance legacy reste inchangée ; `write_authorized` et `physical_restore_eligible` restent faux. Le plan ne contourne pas les refus de l'import ou du simulateur.

L'[exécuteur Linux Live séparé](restore-p1-linux-fr.md) identifie et verrouille exclusivement la carte, refuse les volumes utilisés, compare sa totalité à la sauvegarde avant écriture, conserve un journal durable et la P1 d'origine, ne modifie que P1 puis relit les zones modifiées et conservées. Son utilisation en écriture exige une autorisation explicite distincte. Préparer ce plan ne donne pas cette autorisation.

La sortie est créée sans écrasement. Les chemins de périphériques et fichiers spéciaux sont refusés. Aucun espace pour une seconde copie complète n'est exigé : cette étape ne produit que du JSON.

Le plan est scellé par son SHA-256 exact, vérifié avec `validate_sealed_plan` avant toute utilisation. Le validateur exige le type explicite du producteur, la cohérence du SHA de son rapport et les empreintes du candidat et de la simulation. Ce scellement local ne construit pas une ISO Live et ne donne aucune autorisation physique.
