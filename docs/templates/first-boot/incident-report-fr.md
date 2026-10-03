# FIRST BOOT — modèle de rapport d'incident

[Protocole](../../first-boot-qualification-fr.md) · commit de référence :
`ff4e8c1a97d77fe02fe5b1d487c2299633d44fcf`.
Copier hors Git ; un incident par symptôme cohérent. Aucun nouvel essai ni écriture autorisé.

## Contexte

- ID incident / ID essai parent / chemin relatif du compte rendu : —
- Commit exact candidat / identifiant image / SHA-256 P1 / version lecteur (ou INCONNU) : —
- Date/heure/fuseau / T+ / incertitude / numéro de redémarrage : —
- Observateur / alimentation et USB actuels / matériel et état initial carte : —
- Canal de capture disponible ? logs perdus/partiels/inaccessibles ? pourquoi ? —
- IDs de tests concernés et résultat (NOT TESTED / PASS / FAIL / UNQUALIFIED) : —

## Symptôme (cocher ; ne vaut pas diagnostic)

- [ ] Écran blanc
- [ ] Écran figé
- [ ] Bootloop
- [ ] KOReader absent
- [ ] Tactile absent
- [ ] Tactile inversé / axes permutés
- [ ] Affichage inversé
- [ ] P3 absente
- [ ] Frontlight anormale
- [ ] Autre : —

Comportement exact observé, répétition **déjà constatée**, temps/fréquence,
dernier contenu écran, transitions LED, lumière demandée/réelle : —
Ne pas répéter POWER ni injecter une panne pour compléter le rapport.

## Dernier stade démontré et preuves

| Stade | Observé / inconnu / contredit | Heure / preuve / log / limites d'interprétation |
| --- | --- | --- |
| Alimentation / LED | — | — |
| Noyau / init | — | — |
| Identité fb0 / refresh réel | — | — |
| Identité tactile / événements bruts / correspondance UI | — | — |
| P3 source/type/options réels / ready | — | — |
| Launcher / loader / lecteur vivant / UI utilisable | — | — |

Noter les identités montage/processus/nœuds capturées, pas un eventN supposé.
Lier dmesg complet, sortie boot et horodatages si disponibles ; un mot-clé ou
nœud seul ne démontre pas un matériel prêt. Référencer photos/vidéos.

## Actions et préservation

| Heure / T+ | Action déjà effectuée (commande/action UI exacte/version outil) | Résultat/retour / preuve | État ou octets éventuellement modifiés |
| --- | --- | --- | --- |
| — | — | — | — |

- Condition STOP et heure / nouvelles actions arrêtées / état sûr actuel : —
- P2 inchangée : **NON CONFIRMÉE** ; hashes référence/après, périmètre/méthode/preuve : —
- Préservation pré-P1/P3 / éventuel RW/écriture inattendu / opération active : —
- Index des preuves, logs volatils exportés / preuves manquantes : —

## Reprise du diagnostic

- Faits établis / preuves : —
- Hypothèses (non démontrées ; faits favorables et contradictoires) : —
- Dernier stade démontré / première dépendance non qualifiée : —
- Observation suivante proposée, preuve discriminante attendue et prérequis : —
- Actions bloquées / autorisation distincte nécessaire / repreneur : —

Ce rapport n'autorise aucun reset usine, reboot forcé, écriture périphérique
ou exécution du recovery P2. Pour le retour arrière conceptuel, lire le protocole ;
ne pas le transformer ici en procédure de restauration exécutable.
