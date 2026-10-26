# PMKB — Store *.pmkb V0 : contre-qualification hors matériel

**Lot : L06-B2f — 26 octobre 2026.** Dépôt `fr4nck/PimpMyKobo-AuraHD`, PR [#31 Store V0](https://github.com/fr4nck/PimpMyKobo-AuraHD/pull/31) (OPEN, DRAFT, non fusionnée), branche `feat/pmkb-store-v0` au HEAD **`d352591d29ce108f78b612a55bfe25bfb4309152`**.

## Résultat CI vérifié

[GitHub Actions Tests #40205215577](https://github.com/fr4nck/PimpMyKobo-AuraHD/actions/runs/40205215577) : **COMPLETED / SUCCESS au HEAD exact**. **10 jobs PASS / 0 FAIL** : 8 jobs `unittest` Python 3.10–3.13 sur Ubuntu/Windows, plus 2 jobs Qt. Chacun des huit jobs Python a terminé l'étape `Run unit tests` avec `SUCCESS`. Le workflow utilise `python -m unittest discover -s tests -v`.

Lecture directe des logs Python 3.11 : **345 tests découverts** sur Linux (7 skipped, 0 fail) et Windows (46 skipped, 0 fail). Les méthodes du fichier `test_store_pending_cleanup.py` sont explicitement exécutées : les cas incompatibles avec les droits de création de symlink du runner Windows sont marqués `skipped`, **et non PASS**. Aucune nouvelle exécution locale des tests n'a été réalisée en L06-B2f ; on n'ajoute pas ces résultats aux runs CI.

### Complément de qualification L06-C2 — 26 octobre 2026

PR #31 au HEAD `8f0bb3811f87e51fbce94b568143ac82bc2fe7ac`, toujours ouverte, brouillon et non fusionnée. La [CI #40275103618](https://github.com/fr4nck/PimpMyKobo-AuraHD/actions/runs/40275103618) est **COMPLETED / SUCCESS** au SHA exact : **10/10 jobs PASS, 0 FAIL** (huit `unittest` Linux/Windows Python 3.10–3.13, deux Qt). Les étapes `Run unit tests` des huit jobs Python sont réussies.

Les logs réellement lus sur Python 3.11 annoncent **361 tests découverts** sur chaque plateforme : Linux **7 SKIP / 0 FAIL**, Windows **49 SKIP / 0 FAIL**. Les **16 tests de `test_store_catalog.py`** sont visibles : **16 PASS Linux** ; **13 PASS + 3 SKIP Windows**, ces derniers concernant les symlinks non disponibles sur ce runner Windows sans privilèges supplémentaires. Aucun nouveau test local ni test Kobo effectué dans L06-C2. La CI n'établit ni l'authenticité des paquets ni l'utilisation réelle sur P3.

## Matrice Store V0 — état prouvé

| Fonction | Verdict | Portée et limites |
|---|---|---|
| Manifeste versionné (`manifest_contract.py`) | **PASS hôte** | Validation JSON, compatibilité déclarée, dépendances et demande réseau. Aucune isolation effective du réseau. |
| Archive ZIP (`archive_contract.py`) | **PASS hôte** | Précontrôle des chemins bruts, membres, types et limites. Aucune authentification de provenance. |
| Installation (`install_contract.py`) | **PASS hôte** | Racine Temp synthétique marquée, CRC à l'extraction, inventaire SHA-256, staging, renommage et rollback simulé. Ni P3 ni Kobo. |
| Désinstallation (`uninstall_contract.py`) | **PASS hôte** | Code détaché puis purgé, `data/` conservé. Nettoyage après détachement non atomique. |
| Retraits incomplets (`pending_cleanup_contract.py`) | **PASS hôte** | Inventaire borné et non destructif des `.pmkb-remove-*`. Aucune restauration ni purge automatique. |
| Catalogue local synthétique en lecture seule | **PASS hôte (L06-C)** | `catalog_contract.py` valide les dossiers `apps/`, manifestes et entrées, maximum 64 applications/512 entrées ; retours `installed_unverified` et `cleanup_pending`. Ce n'est pas une preuve d'exécution sur Kobo. |
| Interface Store dans PMKB-UI/Launcher | **NON IMPLÉMENTÉE** | Catalogue pas encore relié à l'interface ni à l'exécution native. |
| Enregistrement et lancement des applications dans PMKB-UI/Launcher | **NON QUALIFIÉ** | Aucun binaire ARM ni point d'entrée natif exécuté ; exemple de paquet fictif. |
| Permissions réelles, licences et authenticité des éditeurs | **NON QUALIFIÉ** | Déclarations et empreintes ne constituent pas une signature, une sandbox ou une autorisation effective. |
| Concurrence, récupération après coupure brutale, filesystem réel | **NON QUALIFIÉ** | Le marqueur Temp ne protège pas contre un autre processus ayant accès aux mêmes fichiers. |
| Kobo Aura HD, ARM, e-ink, microSD P3, énergie, FIRST BOOT physique | **NON EXÉCUTÉ** | Aucun accès au matériel ; partitions protégées et image scellée inchangées. |

## Suites ordonnées, à exécuter séparément

**L06-C : DONE (contrat local uniquement)** — le catalogue a été publié dans la PR #31 et contre-qualifié dans la CI GitHub. Voir le complément L06-C2 ci-dessus.

**L06-D (prochain sous-lot unique)** : consommation volontaire du catalogue par PMKB-UI/Launcher sans remplacer les huit illustrations ou contredire Notes ADR-005. **L06-E (ultérieur)** : contrats de permissions/identité/licences et préparation ARM ; vérifier séparément compatibilité matérielle et consommation avant usage sur Kobo.

**Invariants** : aucune fusion de la PR #31, aucune modification de FIRST BOOT, P2/recoveryfs, HWCONFIG, waveform, PRE-P1, P1/P3, aucun firmware ni dépendance téléchargé. Le LOT 06 n'est **pas clôturé**, les sous-lots L06-A à L06-B2f et L06-C sont qualifiés dans leurs limites.
