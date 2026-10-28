# PMKB D7s — réinitialisation et marqueurs tardifs

Le contrôleur expérimental dispose d'une opération `pmkb_store_eink_lifecycle_reset` réservée aux instances déjà initialisées. Elle annule la soumission éventuelle, ferme l'aperçu Store, ferme l'application hôte avec abandon explicite et remet à zéro les propriétaires, **sans remettre à zéro le compteur monotone des marqueurs**. Un ancien marqueur ne peut donc pas être confondu avec la nouvelle génération de surface.

Le test vérifie soumission, reset, rejet d'un ancien acquittement, réouverture, nouveau marqueur distinct, rejet de l'ancien, puis acquittement valide. `init` reste réservé à la première initialisation et ne doit pas être rappelé sur un propriétaire vivant. Il ne s'agit pas d'un contrôle de concurrence ni d'un protocole EPDC réel.

Tests au commit `a00c74aa599678ed16f5bfd4e37cf38556e9fbd5`, à qualifier par CI. Aucune modification des partitions, de FIRST BOOT ou de la Kobo ; Store non exécutable et PR #30/#31 non fusionnées.
