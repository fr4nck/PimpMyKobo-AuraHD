# PimpMyKobo-AuraHD — Feuille de route

**Français** | [English](ROADMAP.md)

État au **6 octobre 2026**, référence d'intégration `integration/pmkb-first-boot-1@27e33654626fb996398284d8ca683fd81737262c`.

Une fonctionnalité codée et testée sur fichiers ne constitue pas une validation sur la vraie Kobo. **Aucune écriture physique sur une microSD Kobo n'a encore été réalisée dans ce chantier.** Cette roadmap n'autorise aucune écriture implicite.

## Objectif immédiat

Le jalon prioritaire n'est plus de restaurer P1 sur la microSD originale.

Le parcours normal visé est désormais :

**microSD originale en lecture seule → prélèvement PRE-P1 + P2 → retrait de l'originale → construction d'une nouvelle microSD PMKB → relecture complète → FIRST BOOT matériel sur l'Aura HD.**

La microSD originale doit rester intacte et être conservée comme sauvegarde matérielle.

La ligne d'arrivée immédiate est simple :

**fabriquer une nouvelle microSD, l'installer dans l'Aura HD et qualifier enfin le premier démarrage réel.**

## Où nous en sommes

| Étape | État réel | Limite restante |
|---|---|---|
| Candidat P1 PMKB FIRST BOOT #1 | **FIGÉ / qualifié logiciel** — 268 435 968 octets, SHA-256 `7980fec15cb62ca3c2cabcb64cbbb683446fbf64070d75b45acf9a5e99e0f67c` | Démarrage matériel non essayé |
| PRE-P1 / HWCONFIG de référence | **Qualifié** | À relire sur la donneuse réelle lors de la création |
| P2 / recoveryfs de référence | **Qualifié** — SHA-256 `fe7885d391a5627cf2b04bd75518cf8fb5b0f379b29032727adb29cba35b968a` | À relire sur la donneuse réelle lors de la création |
| Backend de remplacement `replace-microsd-linux.py` | **Implémenté et fusionné** via PR #16 | Écriture réelle sur carte de remplacement non qualifiée |
| Donneuse originale | Contrat **lecture seule** implémenté | Lecture matérielle réelle du nouveau parcours à effectuer |
| Staging Live | PRE-P1 + P2 seulement, environ 278 Mio ; un seul lecteur de cartes suffit | À exercer sur le Live réel |
| Nouvelle P3 | Création FAT32 `KOBOeReader`, taille adaptée à la cible | Montage réel par la Kobo non qualifié |
| Live UX | Français/anglais, AZERTY, parcours remplacement prioritaire, progression texte | Rapport opérateur à rendre plus lisible sur un écran unique |
| Identité du Live | **Fusionnée via PR #17** — séparation `candidate_head` / `live_head`, CI #130 verte | Le nouveau Live réel doit maintenant être reconstruit depuis cette référence |
| Boot du PC sur un ancien Live PMKB | **Observé** jusqu'au menu PMKB | Le nouveau Live intégrant le parcours de remplacement doit être reconstruit et requalifié |
| FIRST BOOT Aura HD | **UNQUALIFIED** | Boot, écran, tactile, frontlight, P3, USB/Calibre |

Voir [remplacement-microsd-fr.md](remplacement-microsd-fr.md), [qualification-usb-fr.md](qualification-usb-fr.md) et [pmkb-first-boot-1-fr.md](pmkb-first-boot-1-fr.md).

## 1. Aligner et figer le Live de préparation

Avant toute microSD réelle :

1. partir de la référence Live qualifiée issue de la PR #17, avec identités distinctes du candidat P1 et du code Live ;
2. reconstruire l'ISO depuis un checkout Git propre de cette référence exacte ;
3. conserver le SHA-256 de l'ISO produite ;
4. vérifier dans l'ISO le candidat, les backends, le manifest, le plan et l'identité de build ;
5. garder l'interface principale sur **un écran unique** : progression, résultats essentiels et erreurs lisibles au même endroit ;
6. présenter les analyses sous forme synthétique `OK / ERREUR / À TESTER`, avec détails techniques accessibles sans imposer une autre console ;
7. versionner dans Git les sources graphiques utiles et leur provenance ; leur affichage dans le Live reste un raffinement, pas un prérequis de sécurité.

Aucun effet graphique ou animation complexe n'est requis pour FIRST BOOT #1.

## 2. Rendre disponible le candidat P1 exact

Le nouveau parcours peut reprélever PRE-P1 et P2 depuis la microSD originale, mais **pas le candidat P1 PMKB**.

Avant de construire le Live réel, il faut donc disposer exactement de :

- `PMKB-FIRST-BOOT-1-0b00d858.img`
- taille : `268435968`
- SHA-256 : `7980fec15cb62ca3c2cabcb64cbbb683446fbf64070d75b45acf9a5e99e0f67c`

Cet artefact peut venir du build privé existant ou d'un ancien Live privé qui l'embarque, sous réserve de vérification du SHA-256.

## 3. Construire puis démarrer le nouveau Live réel

1. construire l'ISO PMKB avec le candidat exact et le plan scellé ;
2. vérifier son SHA-256 ;
3. écrire l'ISO sur la clé USB de qualification, jamais sur une microSD Kobo ;
4. démarrer le portable en Linux Live natif ;
5. vérifier l'arrivée sur PMKB, le français/AZERTY et l'identité affichée du candidat et du Live.

L'ancien boot réussi sur le PC prouve seulement que cette famille de Live peut démarrer sur ce portable ; il ne qualifie pas la nouvelle ISO.

## 4. Lire la microSD originale — strictement en lecture seule

Parcours normal :

1. choisir **Créer / réparer une nouvelle microSD PMKB** ;
2. insérer la microSD originale ;
3. saisir explicitement son disque complet, par exemple `/dev/sdb` ;
4. vérifier support amovible USB, secteurs 512 octets, géométrie et Aura HD E606C0 ;
5. relire et vérifier PRE-P1 / HWCONFIG ;
6. relire et vérifier P2 / recoveryfs ;
7. copier en staging Live uniquement :
   - PRE-P1 : environ 9,5 Mio ;
   - P2 : 256 Mio ;
   - manifeste de capture.

La carte originale est ouverte en lecture seule. **Aucune écriture n'est requise sur elle dans ce parcours.**

Le staging tient en RAM ; un seul lecteur de cartes suffit.

## 5. Retirer et préserver l'originale

Après capture réussie :

1. retirer physiquement la microSD originale ;
2. la ranger et la conserver comme sauvegarde matérielle ;
3. ne plus en dépendre pour la phase d'écriture de la nouvelle carte.

La donneuse ne doit pas avoir besoin d'être présente pendant l'écriture de la cible.

## 6. Préparer la nouvelle microSD

1. insérer une autre microSD ;
2. saisir explicitement son disque complet ;
3. vérifier qu'elle est amovible, USB, inutilisée et suffisamment grande ;
4. refuser une cible qui ressemble à la donneuse ;
5. calculer la P3 à partir de la capacité réelle ;
6. afficher la capacité cible, la future P3 et le plan exact ;
7. lier le plan à l'identité et à l'empreinte de cette cible ;
8. demander la confirmation destructive exacte.

Géométrie système conservée :

- PRE-P1 : offset 0, taille 9 961 472 ;
- P1 : offset 9 961 472, taille 268 435 968 ;
- P2 : offset 278 397 440, taille 268 435 968 ;
- P3 commence à 546 833 408.

Le contrat actuel réserve au minimum 1 Gio à P3, soit un minimum théorique total d'environ 1,51 Gio. **La capacité de la cible n'a pas à être identique à celle de la donneuse et aucune capacité commerciale particulière ne doit être codée en dur.** Toute cible dont la capacité réelle satisfait les contraintes du profil peut être préparée ; la compatibilité matérielle aux différentes capacités reste à qualifier sur l'Aura HD.

## 7. Construire la nouvelle carte

Après confirmation seulement :

1. écrire le PRE-P1 issu de la donneuse en n'adaptant que la taille MBR de P3 ;
2. écrire P1 avec le candidat PMKB figé ;
3. écrire P2 bit pour bit depuis le staging ;
4. créer P3 en FAT32 avec le label `KOBOeReader`.

Les opérations longues affichent une progression texte, par exemple :

`Lecture originale P2 recovery: 72% (184.3/256.0 MiB, 18.4 MiB/s)`

Aucun retry automatique et aucun rollback automatique implicite.

## 8. Relire et qualifier la nouvelle carte avant la Kobo

La création n'est réussie que si les contrôles post-écriture passent :

- PRE-P1 relu et conforme ;
- P1 relue avec le SHA-256 attendu ;
- P2 relue avec le SHA-256 attendu ;
- MBR et géométrie conformes ;
- P3 FAT32 valide ;
- label `KOBOeReader` valide.

Le rapport opérateur doit distinguer clairement :

- **OK** : démontré par lecture/contrôle ;
- **ERREUR** : opération invalide ou interrompue ;
- **À TESTER** : dépend du matériel Kobo et ne peut pas être déduit de la carte seule.

Une carte cible partiellement écrite reste reconstruisible ; en cas d'échec, on diagnostique puis on recommence sur la cible. L'originale reste intacte.

## 9. FIRST BOOT matériel sur l'Aura HD

Installer la nouvelle carte dans la Kobo puis qualifier explicitement :

1. démarrage réel ;
2. framebuffer / affichage E-Ink ;
3. lancement de KOReader ;
4. tactile ;
5. frontlight ;
6. montage de P3 `/mnt/onboard` ;
7. accès aux livres/fichiers ;
8. USB / Calibre ;
9. stabilité après redémarrage.

Tant que ces essais ne sont pas réalisés sur l'appareil réel, ces points restent **UNQUALIFIED**.

Le résultat matériel doit être rattaché au SHA du candidat P1, au commit du Live, à l'identité de la carte construite et au rapport de session.

## 10. Le backup complet de 31,9 Go n'est plus un prérequis du parcours normal

Le backup complet existant reste une archive utile, notamment pour conserver une photographie exacte de l'ancienne P3 et des données utilisateur.

Mais le nouveau parcours de remplacement n'en dépend pas :

- PRE-P1 peut être reprélevé sur l'originale ;
- P2 peut être reprélevée sur l'originale ;
- P3 est recréée ;
- P1 PMKB vient du candidat figé.

Politique cible :

- conserver la microSD originale intacte ;
- conserver les hashes, manifests, scripts, documentation et petites sources dans Git ;
- conserver les gros dumps comme archives froides facultatives, pas comme service 24/24 ;
- ne pas synchroniser 31,9 Go uniquement pour rendre le parcours courant possible.

## 11. La restauration P1 sur l'originale reste un contrat avancé séparé

`restore-p1-linux.py` n'est pas supprimé.

Il garde son contrat historique strict :

- cible = carte originale connue ;
- carte complète identique à la sauvegarde qualifiée ;
- seule P1 peut être écrite ;
- tout l'extérieur de P1 reste inchangé.

Ce mode est une voie avancée de restauration, **pas le parcours normal de réparation**.

Il ne faut jamais assouplir ce backend pour accepter arbitrairement une autre carte : le remplacement complet appartient à `replace-microsd-linux.py`.

## 12. Après FIRST BOOT seulement — phase produit PMKB

Aucun développement produit ne doit retarder le premier démarrage matériel.

Une fois FIRST BOOT qualifié :

- stabiliser KOReader comme jalon V1 ;
- concevoir le launcher e-ink PMKB ;
- organiser les entrées Books / Apps / Games / Store / Web / Notes / Recipes / Settings ;
- poursuivre les applications légères, outils réseau/diagnostic, PDA, cartes hors ligne et autres fonctions prévues ;
- maintenir les services optionnels non résidents en RAM ;
- étudier ensuite le split 2 panneaux et les raffinements d'interface ;
- garder thèmes rétro, Ikari Mode et autres Easter eggs hors de tous les chemins de sécurité.

## 13. Rendre ensuite le sauvetage reproductible sur d'autres Aura HD

Après succès sur l'appareil de développement :

- qualifier le même parcours sur d'autres E606C0 ;
- documenter les variantes matérielles et géométries non prises en charge ;
- conserver tests synthétiques et documentation FR/EN ;
- ne publier aucun dump, recovery ou firmware privé ;
- décider séparément ce qui peut devenir une distribution publique légère.

## Invariant d'architecture

Le parcours principal doit rester segmenté :

```text
microSD originale
      |
      | lecture seule
      v
PRE-P1 + P2 + identification E606C0
      |
      | staging Live (~278 Mio)
      v
retirer l'originale
      |
      v
nouvelle microSD explicitement choisie
      |
      | plan + confirmation destructive
      v
PRE-P1 + P1 PMKB + P2 + P3 FAT32
      |
      | relecture / vérification
      v
FIRST BOOT sur l'Aura HD
```

**Lire l'originale → la retirer → construire une autre carte → relire → tester le matériel.**

Aucun bouton, raccourci ou amélioration d'interface ne doit transformer cette chaîne en écriture implicite sur la carte originale.
