# PMKB L08-A — prévol de format ARM (hôte uniquement)

Ce lot ajoute un premier diagnostic **nécessaire mais insuffisant** pour un futur paquet `*.pmkb` contenant un programme natif : vérifier qu'un en-tête binaire indique `ELF32`, little-endian et `EM_ARM`, avec type `ET_EXEC` ou `ET_DYN`.

L'API `inspect_arm_elf(bytes)` ne lit aucun disque, ne télécharge rien, n'exécute rien et retourne explicitement `launchable: false` même en cas de succès. Les tests utilisent des en-têtes synthétiques, jamais un binaire ARM réel. Cette vérification n'établit ni le sous-type ARM, ni EABI, ni les instructions CPU, ni l'interpréteur dynamique, ni les dépendances, ni la compatibilité du noyau Kobo. Elle ne certifie pas l'intégrité, la provenance ou la sécurité de l'exécutable.

Étape suivante : resserrer le contrat ABI, examiner les segments `PT_INTERP`, les dépendances et le périmètre de confiance, puis obtenir un binaire compilé par une toolchain explicitement autorisée, **sans téléchargement ni écriture microSD**. Le moteur Python d'installation reste réservé aux racines temporaires synthétiques.

Aucun changement du Launcher réel, du Store sur la Kobo, du FIRST BOOT, de P1/P2/P3 ou de recoveryfs.
