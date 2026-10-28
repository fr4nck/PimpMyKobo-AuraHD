# PMKB Store — L08-G : contrôle de cohérence des observations rootfs

## Objet

L08-E a introduit l'inventaire en lecture seule d'un **export déjà extrait**, L08-F la résolution purement en mémoire des alias ELF. L08-G vérifie maintenant la **cohérence interne** du rapport produit par L08-E, sans lire un quelconque disque.

Module : `experimental/store-v0/rootfs_evidence_contract.py`.

`verify_snapshot_evidence(snapshot, expected_audit_sha256=None, expected_source_id=None)` vérifie strictement la forme du rapport, les observations de répertoires, les noms relatifs, les tailles et empreintes des fichiers, les en-têtes ARM enregistrés, les champs de provenance et le SHA-256 canonique des observations. Les nombres de fichiers et de bytes sont bornés et les chemins ne peuvent sortir des deux répertoires autorisés (`lib/` et `usr/lib/`).

Un hash attendu ou identifiant de source attendu peut être fourni explicitement. Cela vérifie uniquement une **égalité avec des valeurs données par l'appelant**, sans établir leur confiance.

## Ce que vérifie le digest

Le `audit_sha256` créé par L08-E couvre la représentation JSON canonique de :

- `directories` : répertoires parcourus et états d'observation ;
- `libraries` : noms, tailles, hachages, types ELF, états et cibles des liens enregistrés.

Il ne couvre **pas** le contenu original de l'image rootfs, `source_id` ni `declared_source_sha256`. Une personne peut modifier les observations puis recalculer le digest : il s'agit donc d'un **contrôle d'intégrité interne**, pas d'une signature. `expected_audit_sha256` peut servir d'ancre seulement si sa provenance est vérifiée **hors de ce module**.

## Sémantique et garde-fous

Sorties toujours limitées à `scope=internal_snapshot_consistency_only`. Les indicateurs `image_hash_verified`, `source_provenance_authenticated`, `export_matches_source_image`, `hardware_verified`, `runtime_compatible`, `launchable` sont **toujours faux**, même si toutes les comparaisons internes passent.

Les erreurs `audit_digest_mismatch`, `expected_digest_mismatch`, `expected_source_mismatch` et codes de rejet des champs malformés ne déclenchent aucune correction, écriture ou lancement de binaire.

Les tests `tests/test_store_rootfs_evidence_contract.py` construisent des snapshots *synthétiques* dans des répertoires temporaires et recherchent les falsifications de hachages, tailles, identifiants de source, en-têtes ELF, structure et bornes.

## Étape qui restera à faire

Pour passer de `internal_snapshot_consistency_only` à une preuve exploitable pour la Kobo Aura HD, il faudra un **export autorisé** avec preuve de provenance, empreinte de l'image source mesurée indépendamment, et validation du lien image → extraction → fichiers inventoriés. Il faudra également étudier les dépendances transitives, les versions de symboles, le chargeur et le noyau.

Un résultat L08-G ne justifie pas la fusion d'une image système, l'installation d'un `*.pmkb` ou la modification de la microSD. Aucune lecture de P1/P2/P3, aucun téléchargement et aucune opération physique ne sont effectués pendant ce lot.
