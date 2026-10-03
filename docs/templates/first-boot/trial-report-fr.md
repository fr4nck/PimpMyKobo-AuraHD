# FIRST BOOT — modèle de compte rendu

[Protocole](../../first-boot-qualification-fr.md) · commit du protocole : `ff4e8c1a97d77fe02fe5b1d487c2299633d44fcf`

**Modèle vierge ; aucun essai ni autorisation d'écriture.** Copier dans un dossier
d'essai privé hors Git. Remplacer — par un fait ou une inconnue explicite.
Résultats autorisés : NOT TESTED / PASS / FAIL / UNQUALIFIED. Une preuve manquante
ne vaut pas PASS. Un compte rendu par appui POWER ; conserver les essais précédents.

## Identité et état initial

| Champ | Valeur / référence de preuve |
| --- | --- |
| ID essai (UTC AAAAMMJJTHHMMSSZ-fbNN) | — |
| Identifiant image / nom local / taille / SHA-256 image | — |
| Commit exact du candidat (40 caractères hexadécimaux) / arbre de build modifié ? | — |
| SHA-256 / taille de l'image P1 ; référence de relecture après écriture précédemment autorisée | — |
| Manifeste build / runtime / rapports preflight image et contenu extrait | — |
| Version KOReader / SHA-256 paquet / version réellement observée | — |
| Date/heure ISO 8601 avec fuseau / pseudonyme opérateur | — |
| POWER T0 / source et précision horloge / décalage heure civile–uptime noyau | — |
| Matériel : Aura HD E606C0/dragon annoncé ; identification réellement obtenue | — |
| HWCONFIG : v1.7, 39 octets, PCB 28 attendus ; valeurs observées / preuve | — |
| ID privé carte/cible / taille / géométrie MBR / référence fingerprint | — |
| État initial carte : originale/copie de travail, ancienne P1, dernier boot connu, opérations autorisées antérieures | — |
| Écran / LED initiaux / alimentation / USB / historique charge / anomalies | — |
| Vérification sauvegarde / originale préservée / plages permises et autorisations | — |
| Canal de capture / export / limitations et outils disponibles | — |
| SHA-256 P2 référence / taille / géométrie / origine et date | — |
| Référence contrôle P2 après opération/en lecture seule, SHA-256 / date | — |
| Confirmation explicite de préservation P2 | **NON CONFIRMÉE** — inscrire « P2 n'a pas été modifiée » seulement avec méthode/preuve et périmètre |
| P2 montée ? écriture inattendue ? preuves de préservation pré-P1/P3 | — |

Déclarer les inconnues. Un hash identique couvre le contenu et l'intervalle mesurés,
pas toutes les opérations historiques. Ce formulaire n'autorise pas de nouveaux
accès au périphérique pour compléter ses champs.

## Dix prérequis

Se reporter à G01–G10 dans le protocole, sans recopier leurs procédures.
État initial : NOT TESTED.

| Prérequis | Résultat | Constat factuel / preuve | Limitation restante / référence autorisation |
| --- | --- | --- | --- |
| G01 | NOT TESTED | — | — |
| G02 | NOT TESTED | — | — |
| G03 | NOT TESTED | — | — |
| G04 | NOT TESTED | — | — |
| G05 | NOT TESTED | — | — |
| G06 | NOT TESTED | — | — |
| G07 | NOT TESTED | — | — |
| G08 | NOT TESTED | — | — |
| G09 | NOT TESTED | — | — |
| G10 | NOT TESTED | — | — |

## Chronologie

Repères uniquement : **ni ordre d'exécution garanti ni durées attendues**.
Préciser l'ordre réel et ajouter les resets/erreurs. Temps indisponible → INCONNU,
pas zéro. Distinguer mesure et inférence ; repérer chaque redémarrage.

| Repère | Heure civile (fuseau) | T+ secondes / incertitude | Observation / preuve / log |
| --- | --- | --- | --- |
| POWER | — | 0 (définition ; renseigner seulement lors de l'essai) | — |
| Transitions LED | — | — | — |
| Première modification E-Ink | — | — | — |
| Framebuffer utilisable (comment établi ?) | — | — | — |
| Tactile détecté (identité/preuve ?) | — | — | — |
| P3 disponible (montage réel ?) | — | — | — |
| Lancement KOReader (tentative ou processus confirmé) | — | — | — |
| Premier écran KOReader utilisable | — | — | — |

## Relevé des 25 tests

Le blocage est un rappel du protocole, **pas un GO**. Lire l'ID pour ses conditions ;
consigner dépendance bloquée/décision réelle dans les notes.
Preuves/logs : chemins relatifs du dossier privé ou IDs de l'index.
— signifie non renseigné ; expliciter toute preuve indisponible/non capturée.

| ID / libellé | Résultat | Heure ou T+ / incertitude | Observation factuelle | Preuve | Log | Bloquant (protocole) | Notes / décision réelle |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B01 LED | NOT TESTED | — | — | — | — | Conditionnel ; voir B01 | — |
| B02 Noyau/init | NOT TESTED | — | — | — | — | Oui ; voir B02 | — |
| B03 Premier changement écran | NOT TESTED | — | — | — | — | Oui affichage ; voir B03 | — |
| B04 Durées des phases | NOT TESTED | — | — | — | — | Conditionnel ; voir B04 | — |
| S01 Provenance/montage P3 | NOT TESTED | — | — | — | — | Oui ; voir S01 | — |
| S02 Livres | NOT TESTED | — | — | — | — | Oui lecture ; voir S02 | — |
| S03 Absence P3 au boot | NOT TESTED | — | — | — | — | Oui si lancement ; voir S03 | — |
| S04 Perte P3 avant exec | NOT TESTED | — | — | — | — | Oui ; voir S04 | — |
| S05 Perte P3 après exec | NOT TESTED | — | — | — | — | Résilience non qualifiée ; voir S05 | — |
| K01 Lancement direct | NOT TESTED | — | — | — | — | Oui ; voir K01 | — |
| K02 Profil indépendant | NOT TESTED | — | — | — | — | Oui ; voir K02 | — |
| K03 Première lecture | NOT TESTED | — | — | — | — | Oui ; voir K03 | — |
| E01 Framebuffer | NOT TESTED | — | — | — | — | Oui ; voir E01 | — |
| E02 Orientation | NOT TESTED | — | — | — | — | Oui ; voir E02 | — |
| E03 Full refresh | NOT TESTED | — | — | — | — | Oui ; voir E03 | — |
| E04 Partial refresh | NOT TESTED | — | — | — | — | Oui partial ; voir E04 | — |
| E05 Ghosting | NOT TESTED | — | — | — | — | Conditionnel ; voir E05 | — |
| N01 Détection Neonode | NOT TESTED | — | — | — | — | Oui ; voir N01 | — |
| N02 Acquisition | NOT TESTED | — | — | — | — | Oui ; voir N02 | — |
| N03 Axes/orientation tactile | NOT TESTED | — | — | — | — | Oui ; voir N03 | — |
| N04 Zones écran | NOT TESTED | — | — | — | — | Oui ; voir N04 | — |
| F01 Chaîne NTX | NOT TESTED | — | — | — | — | Oui ; voir F01 | — |
| F02 Extinction frontlight | NOT TESTED | — | — | — | — | Oui ; voir F02 | — |
| F03 Gradation frontlight | NOT TESTED | — | — | — | — | Oui ; voir F03 | — |
| F04 Bouton lumière | NOT TESTED | — | — | — | — | Conditionnel ; voir F04 | — |

## Transmission

- Dernier stade démontré / preuve : —
- STOP déclenché ? heure, raison et état sûr actuel : —
- Incidents (chemins relatifs des rapports) : —
- Bilan PASS / FAIL / UNQUALIFIED / NOT TESTED, manques essentiels : —
- Confirmation P2 et preuves revues par/date : —
- Logs volatils exportés ? preuves manquantes et cause : —
- Diagnostic suivant proposé / actions bloquées / autorisation distincte requise : —

Ne pas conclure « matériel qualifié » tant qu'un test essentiel manque de preuve.
