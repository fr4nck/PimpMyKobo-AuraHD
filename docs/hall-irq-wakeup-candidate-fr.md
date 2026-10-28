# PMKB — candidat de neutralisation du réveil Hall (source seule)

28 octobre 2026 — **CANDIDAT NON APPLIQUÉ, aucun test matériel**.

## Origine traçable

Source publique : pazos/linux-2.6.35.3-kobo, commit 1f43a4a01a727a9b440f2e8830b67734b6373a10.
Pilote : drivers/input/keyboard/tle4913_keypad.c.
Empreinte du blob Git d'origine : d7d3e3632b15526f1dcd06027f7bdbea74eef7a4.

Le fichier expérimental experimental/power-lab/candidates/tle4913-hall-wakeup-off-v0.patch ne contient **qu'une modification** : dans la déclaration de gtTLE4913_GPIO_data, passer .iWakeup de 1 à -1. Il n'est pas appliqué aux sources, à une image, à une partition, ni au matériel.

## Pourquoi -1 plutôt que 0 ?

Dans ce BSP, gpiofn_register appelle enable_irq_wake(irq) pour iWakeup==1, disable_irq_wake(irq) pour iWakeup==0, et ne fait **aucun** changement de comptage wake pour toute autre valeur. iWakeup=-1 évite donc de demander un disable_irq_wake() potentiellement non équilibré lors de l'enregistrement initial d'une IRQ non encore marquée wake.

La fonction demande toujours gpio_to_irq, set_irq_type et request_irq. Le callback de touches reste enregistré, le GPIO 5_25 reste déclaré, son anti-rebond reste actif et sa conversion en KEY_F1/KEY_H ne change pas. Le bouton physique KEY_POWER, associé historiquement au GPIO 4_10, n'est pas modifié.

**Important :** cette modification ne garantit pas à elle seule que le Hall sera incapable de réveiller le noyau si un autre chemin marque la même IRQ comme source wake, si le firmware embarqué diffère ou si la plateforme active une autre voie de reprise. Le fonctionnement réel n'est pas établi.

## Conditions non satisfaites

1. Confirmer par lecture seule la provenance et la configuration exacte du noyau exécuté sur l'Aura HD E606C0 ; un ancien fork public ne prouve pas l'identité avec le binaire de la Kobo.
2. Qualifier les GPIO, les sources d'IRQ, le rôle éventuel du MSP430 et les comportements du bouton physique, sans modifier les registres.
3. Vérifier hors matériel que le patch s'applique exclusivement au blob source attendu et que sa compilation ne change pas le traitement normal des touches.
4. Sur une **microSD de test séparée**, et seulement après autorisation matérielle explicite, comparer des cycles de suspension et de réveil avec ou sans aimant, vérifier Power, USB, batterie et tous les autres wake sources.
5. Établir les traces du défaut rapporté (réveil parfois possible seulement en branchant USB) avant d'attribuer la panne au TLE4913.

Le prototype ne doit pas appeler disable_irq(), unbind mxckpd ou empêcher la publication générale des événements KEY_POWER. L'option KOReader ignore_power_sleepcover est indépendante de ce candidat de noyau.

Les tests disponibles vérifient uniquement que **le diff déposé** est restreint à un seul champ du pilote historique. Ils ne prouvent pas que le patch est compatible avec le binaire, appliqué ou efficace.

**Aucune autorisation** de flash, de changement du firmware, du FIRST BOOT scellé, de P1/P2/P3, du noyau de production ou des microSD n'est donnée par ce candidat.
