# PMKB — Modèle de menaces SECURITY CONTRACT V1

**18 octobre 2026 — audit documentaire et hôte seulement.** Cible : Kobo Aura HD N204 / dragon / E606C0, i.MX507, 512 Mio, FIRST BOOT KOReader v2026.07.1. Aucune preuve de qualification matérielle de sécurité. Ne pas confondre la présence de code, la configuration historique et le démarrage effectif.

## Actifs, adversaires, hypothèses

Actifs : intégrité du code, des livres et des notes ; confidentialité des contenus/personnalisation/secrets ; disponibilité de la lecture et de l'alimentation ; **récupérabilité indépendante** via sauvegardes et conservation de P2. Adversaires : livre ou fichier importé malformé, application/plugin compromis, terminal USB non fiable, hôte réseau local hostile, accès physique à la microSD, fournisseur ou mise à jour compromis. La simple erreur utilisateur ou corruption de stockage menace aussi disponibilité/récupération.

**Limite physique :** la microSD interne peut être retirée. Aucune authentification de la Boot ROM, du U-Boot ou du noyau au démarrage n'a été démontrée. SHA-256 des copies = intégrité de sauvegardes comparables, **pas** racine matérielle de confiance, chiffrement au repos, protection anti-rollback ou Secure Boot. Ne pas annoncer la confidentialité face à un adversaire avec accès physique. Données sensibles dans P3 ou les sauvegardes = accès possible si non chiffrées.

## Surfaces et mesures, avec statut de preuve

Provenances : **[SRC-REPO]** code GitHub de la branche ; **[AUDIT-PRÉC]** précédents audits de sauvegardes privées (non relues ici) ; **[AMONT]** sources officielles versionnées ; **[INCONNU]** observation absente. Aucun constat ci-dessous ne doit être compris comme un essai sur Kobo.

| Menace, actif touché | Preuve et risque | Réduction recommandée ; contrôle hors matériel | Qualification nécessaire ensuite |
| --- | --- | --- | --- |
| Exploit du noyau 2.6.35.3 (intégrité, disponibilité, confidentialité) | [AUDIT-PRÉC] noyau 2013 non maintenu ; kernel compilé ≠ vulnérabilités corrigées | Maintenir OFFLINE isolé, supprimer services, surveiller entrées et privilégier noyau maintenu pour CONNECTED ; auditer IKCONFIG et appels privilégiés | Configuration exacte et comportement au boot, version/patches réels |
| PDF/EPUB/image malveillant (intégrité, confidentialité) | [SRC-REPO] KOReader/LuaJIT et décodeurs consultent des fichiers utilisateurs ; aucune sandbox démontrée | Inventorier bibliothèques, plugins, correctifs, parsing non fiable ; ouvrir en utilisateur non root si réalisable ; fixtures de documents synthétiques | Test d'ouverture sécurisé et permissions réelles |
| Plugins / LuaJIT / scripts (intégrité) | [SRC-REPO] lecteur exécuté via reader.lua ; autorun de plugins non audité | Politique d'installation/signatures, pas d'autorun de contenus importés, séparer données/code | Vérification du chargement effectif des plugins |
| Lecteur privilégié, nœuds /dev (intégrité, disponibilité) | [SRC-REPO] `pmkb-reader` ne change pas d'UID ; `rcS` crée des nœuds par balayage sysfs et `mknod` sans politique modes explicite | Stratégie de privilèges et groupe d'accès fb/input/ntx adaptée au noyau, validation des liens/type/permissions ; tests sur snapshot | Besoin d'ouverture des devices et identité effective |
| Wi-Fi / réseau involontaire (confidentialité, intégrité, batterie) | [SRC-REPO] `pmkb-check-offline` refuse les interfaces hors `lo` **à deux instants de lancement**, ne démontre ni radio RF éteinte, ni absence de trafic pendant la session, ni absence de sockets | Pas de service, réseau désactivé par défaut, contrôle hors matériel des déclarations ; garde runtime continu à concevoir sans présumer de sysfs disponible | Mesurer la radio, liste interfaces et sockets après boot / après hotplug |
| USB et hôtes inconnus (intégrité, confidentialité) | [AUDIT-PRÉC] handlers USB du recovery/KOReader, hotplug et export non qualifiés | Pas d'export de volume monté, permissions et politique d'import, absence d'autorun | Énumération USB/OTG sans exposition de P1/P2/P3 |
| Données personnelles et secrets (confidentialité) | [SRC-REPO] XDG profile temporaire sous /tmp ; persistance, effacement et séparation non prouvés | Secrets minimaux, répertoires dédiés, chiffrement seulement si clés/protection crédibles ; purge mémoire/temp, contrôle permissions | Vérifier points de montage et risques résiduels d'accès microSD |
| rootfs ou P2 modifiés (intégrité, récupération) | [SRC-REPO] rcS monte P3 en ro, mais P1 ro et verrouillage de P2 ne sont pas attestés dans le runtime ; restauration P2 comporte des opérations destructives [AUDIT-PRÉC] | Sauvegardes scellées hors appareil, preflight, lecture seule, aucun essai recovery destructif | Chaîne réelle d'amorçage/retour arrière |
| Mise à jour compromise (intégrité, disponibilité) | Aucun mécanisme PMKB CONNECTED signé installé et qualifié | Signature authentifiée **avec clés de confiance protégées**, numéros de version et anti-rollback selon capacité matérielle ; staged/rollback non destructif | Mise à jour de test indépendante et récupération validée |
| Blobs MCU/Wi-Fi/waveform (intégrité, disponibilité) | [AUDIT-PRÉC] firmware/protocole/licence non qualifiés ; driver ntxec moderne peut refuser le MCU | Ne pas flasher de firmware, portage/source review, définir trust boundary et liste autorisée des blobs | Identifiants/probe et tests physiques encadrés |
| Veille, watchdog, batterie (disponibilité) | [AUDIT-PRÉC] disable watchdog vide et probe inconnu, suspend/énergie non démontrés | Ne jamais ouvrir /dev/watchdog « pour tester » ; contrôler source et contrats de mesure, aucun mode énergie conjectural | Essais de stabilité et mesures batterie prudentes |
| Charge/driver ou chaîne de démarrage modifiée (récupération) | [AUDIT-PRÉC] offsets pré-P1 critiques ; pas de vérification cryptographique embarquée démontrée | Préserver U-Boot/P1/P2 et SHA de référence ; copies et plan de retour indépendant ; tester en lecture seule sur hôte | Preuve de chaîne de récupération indépendante de P2, avant toute carte de test |

## Frontières de confiance et principes

1. **Contenus importés ≠ code de confiance.** Distinguer documents, plugins, firmware, configuration et exécutables.
2. **Le réseau local n'est pas une zone de confiance.** Telnet interdit ; SSH uniquement par clé, non root, pas de mots de passe distants ni d'écoute Internet par défaut.
3. **La conservation des SHA et partitions ne constitue pas une chaîne de boot authentifiée.**
4. **La disponibilité est un actif de sécurité :** un pilote économe mais instable, un MCU injoignable ou un EPDC inutilisable fait échouer la cible CONNECTED.
5. **L'absence de Wi-Fi visible avant lancement n'est pas l'absence de trafic.** La désactivation radio devra avoir une preuve indépendante.
6. **Aucune garantie contre une attaque physique forte** sans mécanisme matériel de confiance et politique de secrets adaptée.

## Source et statut

- Scripts prototype : [rcS](../experimental/offline-rootfs/etc/init.d/rcS), [pmkb-reader](../experimental/offline-rootfs/usr/bin/pmkb-reader), [pmkb-check-offline](../experimental/offline-rootfs/usr/bin/pmkb-check-offline).
- [Écarts boot documentés](offline-boot-gates-fr.md), [audit matériel](offline-hardware-qualification-fr.md), [préparation runtime](offline-startup-spec-fr.md), [contrat boot](boot-contract-v1-fr.md).
- [Matrice pilote](kernel-driver-matrix-v1-fr.md) et [profil sécurité](security-contract-v1-fr.md).
- Ce modèle **n'inclut ni scan de vulnérabilités, ni SBOM authentifié, ni preuve de durcissement effectif**. Aucun test sur la Kobo.
