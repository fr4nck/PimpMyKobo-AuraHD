# PimpMyKobo-AuraHD — Feuille de route

**Français** | [English](ROADMAP.md)

État au 3 octobre 2026, branche `feat/rebuild-rootfs-spec`. Une fonctionnalité codée et testée sur fichiers ne constitue pas une validation sur la vraie Kobo. Cette roadmap ne donne aucune autorisation d'écriture physique.

## Recherche externe et composants candidats — 24 octobre 2026

Le [registre permanent des sources et de la recherche](recherche-sources-fr.md) centralise les dépôts Kobo/Netronix, noyaux, pilotes EPDC et ZForce, émulation E606C0, FBInk, outils ARM, Notes, terminal, SSH, dictionnaires et synchronisation Calibre. Toute nouvelle ressource pertinente, notamment [Oniricorpe — Kobo hacks & mods](https://oniricorpe.eu/log/tech/kobo-hacks-mods/), doit y être classée **INFO / INSPIRATION / CANDIDAT** et rattachée à un jalon R0–R10.

Le registre suit aussi désormais [Kobo Reader](https://www.mobileread.com/forums/forumdisplay.php?f=223) et son [Kobo Developer's Corner](https://www.mobileread.com/forums/forumdisplay.php?f=247), notamment les projets **kos (KOReader OS)**, **Quill OS / InkBox**, **Kobalt** et les fils de récupération : voir **R10**. Les OS tiers couvrent d'autres modèles ; la compatibilité Aura HD E606C0 n'est pas démontrée.

Décision R2 (25 octobre 2026) : l'émulateur QEMU E606C0 de katadelos est retenu comme banc de boot, mais **son constructeur d'image est écarté pour FIRST BOOT**, car il réécrit `rcS` et `passwd` et exige Nickel. Une carte virtuelle PMKB copie P1/P2 à l'identique, voir [Exploitation R2](recherche-sources-fr.md#exploitation-r2--25-octobre-2026).

Priorité : FIRST BOOT sans Nickel reste bloquant pour le matériel. Recherche, documentation et prototypes hors matériel peuvent avancer en parallèle, sans modifier le candidat scellé, PRE-P1, P2 ou les cartes. **Une source consultée ne vaut ni intégration ni qualification matérielle** ; chaque reprise de code exige diff, licence, compatibilité E606C0, tests et décision distincte.

## Ajout du 13 octobre 2026 — launcher expérimental (hôte uniquement)

| Jalons | État vérifiable | Limitations |
| --- | --- | --- |
| V0.2 — composition manga et versions optimisées | **Validé et conservé dans Git** : PNG RGB, 16 gris (1080 × 1440, 250 757 octets), 4 gris, 1 bit et manifeste SHA-256 | Pas une interface embarquée |
| V0.3 — barre système simulée Lua | **Implémenté et testé** : batterie, Wi-Fi, éclairage, contraste, rafraîchissement, veille et réglages | Demandes inertes ; aucune mesure réelle |
| V0.4 — [accueil illustré cliquable sur PC](../experimental/launcher-v0/simulator.html) | **Fusionné dans main** : huit scènes approuvées, navigation clavier/souris et états fictifs | KOReader non lancé ; navigateur/tactile matériel non qualifiés |
| V0.5 — dock et sélection | **Prototype hôte** : dock applicatif distinct, favoris configurables en session, états clair/sombre via composition CSS, sans modifier les images | Compromis d'espace et de contraste e-ink à valider sur matériel |

Détails et commandes : [README du launcher](../experimental/launcher-v0/README.md). L'ordre approuvé reste **Livres / Applications, Jeux / Web, Recettes / Notes, Boutique / Réglages**. Le PNG original **ne doit pas être redessiné**. Le chemin FIRST BOOT, `rcS`, `pmkb-reader`, P1/P2/P3 restent protégés. **Toute qualification matérielle (écran, tactile, frontlight, énergie, Wi-Fi, veille, boot, lancement KOReader) est en attente** ; aucune opération d'écriture n'est autorisée par ces versions.

## Où nous en sommes

| Étape | État | Limite restante |
|---|---|---|
| Inspection et vérification du recovery | Outils et tests disponibles | Qualification des accès selon l'environnement |
| Import historique | Implémenté ; vrais fichiers pré-P1/P2 qualifiés | Provenance `legacy/imported`, association déclarée, aucun faux manifeste natif |
| Sauvegarde complète de notre carte | Copie et relectures complètes concordantes | Acquisition spécifique à cette tâche, distincte du futur outil natif |
| Reconstruction de P1 | Réalisée sur nos données ; filesystem, contenu, permissions, liens et empreintes vérifiés | Démarrage non essayé |
| Simulation complète | Réalisée sur la vraie sauvegarde ; seule P1 change dans une copie du PC | Aucune restauration physique |
| Exécuteur P1 sous Linux Live | Garde-fous implémentés et tests synthétiques réussis | Verrouillage/ioctl et restauration sur matériel réel non qualifiés |
| Commande `pmkb` et paquet `.deb` 0.2.0 | Construits ; paquet extrait et lanceur vérifiés ; 150 tests Linux (5 Qt ignorés sans dépendance) et CI Linux/Windows | Installation APT sur l'environnement Live de référence à valider |
| Application Qt/PySide6 | Premier atelier local implémenté et testé | Qt optionnel ; aucune restauration physique |

## 1. Préparer l'environnement de référence — prochaine étape

- Préparer Linux Live USB natif et les fichiers de preuve sur un support persistant accessible.
- Valider l'installation de `pmkb`, ses dépendances et ses commandes locales.
- Conserver la hiérarchie des fichiers référencés par le manifeste historique.
- Prévoir l'espace pour P1 reconstruite et P1 originale, ainsi qu'un journal durable hors de la carte Kobo.

La création d'une clé Live écrit aussi sur un support physique : elle nécessite une autorisation préalable. L'installation du paquet sur le PC ne lance aucun accès à la Kobo. Voir [l'installation CLI](cli-install-fr.md).

## 2. Qualifier la restauration réelle — en attente de l'opérateur

1. Identifier explicitement la carte entière, puis effectuer la comparaison exclusive **en lecture seule** avec la sauvegarde complète.
2. Préciser/documenter le retour à P1 originale avant la première écriture. Les données de retour existent ; le rollback automatique n'est pas implémenté.
3. Examiner cible, bornes de P1 et plan exact, puis obtenir une autorisation humaine distincte de lancer la restauration.
4. Restaurer P1 seule sous Linux Live, synchroniser et relire P1 ainsi que toutes les zones préservées.
5. Essayer le démarrage sur la Kobo et consigner le résultat réel. Une interruption exige l'examen du journal avant toute autre écriture ; aucun retry automatique.

Les étapes précédentes ne prouvent ni le démarrage ni la santé du filesystem P3. Le contrat legacy conserve ses limites : les vérifications contemporaines et l'intention de l'opérateur sont distinctes. Voir [la procédure Linux Live](restore-p1-linux-fr.md).

## 3. Application Qt/PySide6 — premier lot local

Première version centrée sur les fichiers locaux :

- sélectionner sauvegardes, recovery et rapports ;
- afficher qualification, provenance et contrôles manquants ;
- piloter reconstruction et simulation à travers les commandes existantes ;
- présenter erreurs, progression et rapports JSON ;
- préserver les décisions et garde-fous de la CLI.

La première interface n'effectue pas de restauration physique. Voir [l’atelier local](gui-fr.md). Une future interface d'écriture demandera une conception et une qualification séparées. Ce lot local peut avancer pendant que les essais matériels attendent l'opérateur. Qt reste une dépendance optionnelle ; la CLI fonctionne sans lui.

## 4. Rendre le sauvetage reproductible sur d'autres Aura HD

- Intégrer et qualifier le contrat natif `backup-aura-hd`, développé séparément ; ne pas convertir artificiellement les preuves historiques en sauvegarde native.
- Valider la chaîne inspection → sauvegarde → reconstruction → simulation → restauration protégée sur d'autres exemplaires E606C0.
- Documenter les variantes et les géométries non prises en charge avec des diagnostics explicites.
- Choisir la licence du code propre au projet avant de planifier une distribution publique du paquet.
- Garder les tests synthétiques et la documentation FR/EN ; ne publier aucun dump ou firmware privé.

## 5. Libérer la Kobo — prototype local en cours, matériel en attente

- Direction validée : démarrage direct de KOReader, sans interface/services Kobo ; réseau refusé au lancement hors loopback. Voir [le prototype autonome](offline-liberation-fr.md).
- L’autorisation de restauration physique est retirée ; les anciens plans ne qualifient pas la nouvelle image.
- Documenter et extraire la waveform E-Ink de manière reproductible.
- Compiler les références U-Boot/kernel et qualifier les contraintes E606C0.
- Construire un userspace minimal maintenable puis intégrer KOReader.
- Conserver une voie documentée de retour à la sauvegarde originale vérifiée.
- Tester une microSD libérée sur le matériel réel avant toute généralisation.

Les thèmes rétro et Easter eggs restent facultatifs, hors des chemins de détection, qualification, confirmation ou écriture.

## Règle commune

**Sauvegarder → reconstruire hors ligne → vérifier → simuler → autoriser séparément → restaurer P1 → relire → tester le démarrage.**

Aucun bouton ou raccourci ne doit transformer cette chaîne en écriture implicite « réparer ma Kobo ».
