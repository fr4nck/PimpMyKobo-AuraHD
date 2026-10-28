# PMKB Store — L08-I : preuves croisées ELF ARM, archive et export

## Objectif

Relier les diagnostics préexistants L08-A/C (ELF et DT_NEEDED), L08-E/G
(inventaire et empreinte interne d'un export déjà extrait), L08-F
(alias symboliques) et L08-H/H2 (concordance archive TAR.GZ ↔ export).

Le module arm_runtime_evidence.py reçoit **en mémoire** trois objets
fournis explicitement : octets d'un binaire ELF32 ARM, octets TAR.GZ et
rapport d'observation L08-E. Aucune extraction, aucune écriture, aucun
périphérique Kobo et aucune exécution ARM. Les empreintes attendues sont
comparées lorsqu'elles sont fournies, mais ne sont jamais authentifiées.

## Contrat du lot

API : inspect_arm_runtime_evidence(candidate, archive_bytes, snapshot,
expected_candidate_sha256=None, expected_archive_sha256=None,
expected_audit_sha256=None, expected_source_id=None).

1. Contrôle la taille du candidat ELF (16 Mio au plus), son identité
   ARM EABI5 et ses entrées DT_NEEDED.
2. Vérifie le rapport L08-E et ses empreintes internes, éventuellement
   son identifiant et digest d'audit attendus (L08-G).
3. Compare strictement l'archive TAR.GZ fournie avec cet export (L08-H2,
   en incluant footer CRC et refus de données gzip résiduelles).
4. Résout **uniquement en mémoire** les chaînes d'alias des bibliothèques
   demandées, sous lib/ et usr/lib/ (L08-F).
5. Ne qualifie un en-tête ELF que si le TAR et l'export concordent entièrement
   dans ce périmètre et si **tous les éléments** de la chaîne d'alias figurent
   dans les chemins comparés.
6. Examine séparément PT_INTERP si le chemin est couvert par ces deux
   répertoires, et refuse d'en déduire la présence d'un chargeur fonctionnel.

La catégorie header_matched_in_supplied_archive_only signifie uniquement
un fichier avec un **en-tête ARM EABI5 ET_DYN observé** dans des données
fournies par l'appelant et cohérentes dans le périmètre de scan. Un fichier
manquant dans les répertoires sondés reste inconnu sur le matériel ; ne pas
le qualifier d'absent de la Kobo.

Un inventaire partiel, une divergence TAR/export, une chaîne ambiguë,
un alias sortant du périmètre ou un chemin PT_INTERP non couvert ne deviennent
jamais des preuves favorables. Les rejets de source malformée déclenchent
ArmRuntimeEvidenceError ; aucun mécanisme d'installation n'est présent.

## Limites et provenance

Ce lot **ne vérifie pas** :

- l'empreinte d'une véritable image ext4 P1, ni sa provenance ;
- le lien image ext4 → extraction → export, même si l'archive et l'export
  concordent ;
- la présence de fichiers hors lib/ et usr/lib/ ;
- les versions des symboles, DT_RPATH/RUNPATH, la libc réelle, les
  dépendances transitives et l'ABI du chargeur ;
- la compatibilité noyau Linux 2.6.35.3, les pilotes, l'énergie,
  l'exécution sur Aura HD, ni les droits réels.

Le rapport rend toujours False pour image_hash_verified,
image_to_export_link_verified, archive_origin_authenticated,
loader_abi_verified, symbol_versions_verified,
transitive_dependencies_verified, hardware_verified,
runtime_compatible et launchable.

Les tests ne consomment que des ELF/TAR synthétiques et des répertoires
temporaires. Ils vérifient les cas de concordance, désaccord, alias,
bibliothèque non observée, export partiel, interpréteur, CRC corrompu,
empreintes contradictoires et absence de lecture hôte dans le comparateur.

## Prochaine étape

Avant toute qualification Kobo : mesure indépendante de l'image ext4 source,
export autorisé reproductible, empreinte indépendante de chaque artefact,
puis validation des interpréteurs, versions de symboles et dépendances
transitives. Conserver les artefacts privés hors dépôt, P2 intacte et les
partitions FIRST BOOT inchangées. Le résultat L08-I ne permet **ni installation
ni lancement** d'un paquet sur le matériel.
