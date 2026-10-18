# PMKB — Audit contradictoire SECURITY CONTRACT V1 (Claude Code)

**18 octobre 2026.** Lire la PR #28 et le HEAD distant réel ; ne pas supposer de PC 5700X, de sauvegardes privées, de machine Kobo ou d'un logiciel déjà installé.

## Fichiers du sous-lot

- [Modèle de menaces](security-threat-model-v1-fr.md)
- [Contrat OFFLINE / CONNECTED et gates](security-contract-v1-fr.md)
- [Candidats LTS](security-kernel-candidates-v1-fr.md)
- [Validateur pur](../experimental/security-contract/security_contract.py), [tests négatifs](../tests/test_security_contract.py), [README](../experimental/security-contract/README.md)
- Relire [BOOT CONTRACT V1](boot-contract-v1-fr.md), [audit boot](offline-boot-gates-fr.md), [audit matériel](offline-hardware-qualification-fr.md), [démarrage expérimental](../experimental/offline-rootfs/etc/init.d/rcS).

## À contester prioritairement

1. Modèle de menaces : accès physique, USB, fichiers EPUB/PDF, plugins LuaJIT, coûts de la disponibilité/énergie, secrets dans /tmp ou P3, confiance des firmwares.
2. Niveau de preuve : le montage P3 en ro et le test `lo` suffisent-ils à démontrer une absence de réseau ? (Non attendu.) L'UID de KOReader est-il réellement réduit ? Vérifier scripts sans exécuter l'init.
3. Privilèges /dev : quels nœuds sont créés par la boucle sysfs, quelles permissions héritées, quelles interfaces ioctl exposées ? Quels contournements seraient dangereux (watchdog, /dev/mem, MCU) ?
4. Noyau 2.6.35.3 : vulnérabilités non corrigées, mitigations absentes, charge des bibliothèques et éventuels patches historiques ; ne pas attribuer un CVE non vérifié à l'exemplaire.
5. 6.12 vs 6.18 : vérifier sur source versionnée le support DT-only, l'absence de nœud EPDC, les contraintes du portage DRM/MXCFB/waveform, les limites PM i.MX50 et du ntxec, et les horizons LTS actuels chez kernel.org.
6. SECURITY GATES : des booléens déclarés peuvent-ils être mal pris pour une preuve ? Vérifier qu'aucune entrée ne permet `security_certified=true`, `deployment_allowed=true` ou PASS matériel.
7. Tester l'API pure sur JSON hostile, duplicates, types inattendus, faux SKIP, fakes de version maintenue, services telnet, SSH mot de passe/root, écoute Internet, réseaux imprévus, root lecteur, rootfs rw, mises à jour non signées, processus/fichiers non fiables.
8. La gate SEC-10 OFFLINE reflète-t-elle clairement le risque noyau ancien sans mentir sur l'acceptabilité d'un usage strictement hors ligne ?
9. Les garde-fous contre une mise à jour partielle, le retour arrière, la corruption et les secrets sont-ils explicites et effectivement vérifiables ?

## Bornes

- Audit indépendant, critiques justifiées, corrections minimales de code/tests **seulement si défaut démontré** et après contrôle HEAD/concurrence.
- Aucune nouvelle branche ni PR, aucun merge, aucune écriture FIRST BOOT/P1/P2/P3, ni U-Boot, ni firmware, ni GPIO/I²C/MCU, ni watchdog.
- Aucune installation, téléchargement ou activation réseau sans approbation. Aucune exigence que l'utilisateur exécute une commande.
- Toute exécution de test doit être correctement attribuée à l'environnement d'audit ; aucune preuve sur Kobo n'est disponible.
- Ne pas transformer ce dossier en un développement d'applications, Store, Notes, launcher ou portage noyau.

## Autoprompt prêt à transmettre

**MISSION CLAUDE CODE — CONTRE-EXPERTISE SECURITY CONTRACT V1 PMKB.** Dépôt `fr4nck/PimpMyKobo-AuraHD`, branche `feat/pmkb-powerlab-kernel-v0`, PR #28 en brouillon. Vérifie HEAD actuel et concurrence avant tout. Lis `docs/security-threat-model-v1-fr.md`, `docs/security-contract-v1-fr.md`, `docs/security-kernel-candidates-v1-fr.md`, `experimental/security-contract/security_contract.py`, `tests/test_security_contract.py`, puis les audits boot/driver et les scripts `rcS`, `pmkb-check-offline` et `pmkb-reader`. Réfute méthodiquement tout statut de sécurité non démontré, examine P1/P2 et l'absence de Secure Boot authentifié, privilèges de KOReader, /dev, PDF/EPUB/plugins, réseau radio, SSH, firmware, mises à jour, énergie et rollback. Compare 6.12/6.18 sur sources officielles maintenues et la réalité du portage i.MX50. Attaque le validateur avec tests adversariaux, et prouve qu'aucune déclaration synthétique ne certifie matériel ou CONNECTED. Rejoue les tests seulement si l'environnement le permet et sans téléchargement ; distingue PASS/FAIL/SKIP/UNKNOWN. Aucun accès physique ni écriture sur FIRST BOOT, images, partitions, U-Boot, rcS, pilotes ou MCU. Aucun nouveau PR/branche/merge. Corrige seulement les défauts vérifiés, sans écraser les travaux concurrents ; publie un verdict contradictoire, sources précises et pistes de correction. Ne présume jamais de l'environnement local 5700X.
