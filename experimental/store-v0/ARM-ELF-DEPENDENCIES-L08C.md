# PMKB L08-C — inventaire des dépendances ELF ARM

Le prévol lit en mémoire les segments ELF32, la table dynamique et les entrées `DT_NEEDED`, sans charger ni exécuter les bibliothèques. Les offsets, longueurs et noms sont bornés ; les dépendances restent **non résolues**. Toute sortie renvoie `launchable=false`.

Les tests utilisent exclusivement des ELF synthétiques en mémoire : dépendance libc, binaire sans table dynamique, offset de nom invalide. Ni ces fixtures ni les vérifications EABI5 ne prouvent la compatibilité avec le noyau i.MX50, l'ABI matérielle, la libc ou le chargeur de la Kobo. Le champ de dépendances ne constitue jamais une liste autorisée.

Hors périmètre : téléchargements de toolchain ou bibliothèques, construction ARM, installation ou écriture sur microSD/P1/P2/P3/FIRST BOOT. La CI du nouveau commit est requise avant qualification.
