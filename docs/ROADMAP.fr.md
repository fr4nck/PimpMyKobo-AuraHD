# PimpMyKobo-AuraHD — Feuille de route

**Français** | [English](ROADMAP.md)

État au 3 octobre 2026, branche `feat/rebuild-rootfs-spec`. Une fonctionnalité codée et testée sur fichiers ne constitue pas une validation sur la vraie Kobo. Cette roadmap ne donne aucune autorisation d'écriture physique.

## Où nous en sommes

| Étape | État | Limite restante |
|---|---|---|
| Inspection et vérification du recovery | Outils et tests disponibles | Qualification des accès selon l'environnement |
| Import historique | Implémenté ; vrais fichiers pré-P1/P2 qualifiés | Provenance `legacy/imported`, association déclarée, aucun faux manifeste natif |
| Sauvegarde complète de notre carte | Copie et relectures complètes concordantes | Acquisition spécifique à cette tâche, distincte du futur outil natif |
| Reconstruction de P1 | Réalisée sur nos données ; filesystem, contenu, permissions, liens et empreintes vérifiés | Démarrage non essayé |
| Simulation complète | Réalisée sur la vraie sauvegarde ; seule P1 change dans une copie du PC | Aucune restauration physique |
| Exécuteur P1 sous Linux Live | Garde-fous implémentés et tests synthétiques réussis | Verrouillage/ioctl et restauration sur matériel réel non qualifiés |
| Commande `pmkb` et paquet `.deb` 0.1.0 | Construits ; paquet extrait et lanceur vérifiés ; 140 tests Linux et CI Linux/Windows | Installation APT sur l'environnement Live de référence à valider |
| Application Qt/PySide6 | Direction retenue après la CLI | Interface non implémentée |

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

## 3. Construire l'application Qt/PySide6 — prochain lot logiciel

Première version centrée sur les fichiers locaux :

- sélectionner sauvegardes, recovery et rapports ;
- afficher qualification, provenance et contrôles manquants ;
- piloter reconstruction et simulation à travers les commandes existantes ;
- présenter erreurs, progression et rapports JSON ;
- préserver les décisions et garde-fous de la CLI.

La première interface n'effectuera pas de restauration physique. Une future interface d'écriture demandera une conception et une qualification séparées. Ce lot local peut avancer pendant que les essais matériels attendent l'opérateur. Qt n'est pas une dépendance du paquet CLI actuel.

## 4. Rendre le sauvetage reproductible sur d'autres Aura HD

- Intégrer et qualifier le contrat natif `backup-aura-hd`, développé séparément ; ne pas convertir artificiellement les preuves historiques en sauvegarde native.
- Valider la chaîne inspection → sauvegarde → reconstruction → simulation → restauration protégée sur d'autres exemplaires E606C0.
- Documenter les variantes et les géométries non prises en charge avec des diagnostics explicites.
- Choisir la licence du code propre au projet avant de planifier une distribution publique du paquet.
- Garder les tests synthétiques et la documentation FR/EN ; ne publier aucun dump ou firmware privé.

## 5. Libérer la Kobo — après sauvetage et retour arrière éprouvés

- Documenter et extraire la waveform E-Ink de manière reproductible.
- Compiler les références U-Boot/kernel et qualifier les contraintes E606C0.
- Construire un userspace minimal maintenable puis intégrer KOReader.
- Conserver une voie documentée de retour à la sauvegarde originale vérifiée.
- Tester une microSD libérée sur le matériel réel avant toute généralisation.

Les thèmes rétro et Easter eggs restent facultatifs, hors des chemins de détection, qualification, confirmation ou écriture.

## Règle commune

**Sauvegarder → reconstruire hors ligne → vérifier → simuler → autoriser séparément → restaurer P1 → relire → tester le démarrage.**

Aucun bouton ou raccourci ne doit transformer cette chaîne en écriture implicite « réparer ma Kobo ».
