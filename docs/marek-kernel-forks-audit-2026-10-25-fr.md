# PMKB — M02bis : forks du noyau Marek 2.6.35.3

**Audit du 25 octobre 2026.** Source : [marek-g/kobo-kernel-2.6.35.3-marek](https://github.com/marek-g/kobo-kernel-2.6.35.3-marek), branche `linux`, HEAD `70889a3c6208c94abfab0eb90cfff3ccea3b3579` (2013). Complète [M02, audit EPDC/ZForce](marek-kobo-kernel-audit-2026-10-25-fr.md) et le registre [R1/R3](kernel-community-audit-2026-10-24-fr.md).

**Méthode :** recherche GitHub des copies publiques de même nom, **comparaison réelle de chaque branche `linux` à `marek-g:linux`**, inventaire des branches de tous les dépôts retrouvés, puis lecture ciblée des sources/diffs/commits des trois forks à nouveaux commits. **Aucune archive, clone, firmware ou binaire téléchargé, aucun build ni test sur notre Aura HD.**

## 1. Inventaire et bilan de la comparaison

La recherche de dépôts GitHub remonte **17 dépôts de même nom, dont l'original**, donc **16 copies publiquement accessibles ayant un ancêtre Git commun sur `linux`**. Le compteur de la page GitHub de Marek indique **15 forks** à cette date : les deux sources de comptage divergent (cache de compteurs ou relation de fork non publique/non vérifiée). **Ne pas présenter les 16 comme 16 forks directs administrativement confirmés.**

| Statut `linux` vs parent | Nombre | Dépôts |
| --- | ---: | --- |
| **Identique** (0 ahead/0 behind) | **12** | [LeChuck42](https://github.com/LeChuck42/kobo-kernel-2.6.35.3-marek) · [cecell3000](https://github.com/cecell3000/kobo-kernel-2.6.35.3-marek) · [takeokt](https://github.com/takeokt/kobo-kernel-2.6.35.3-marek) · [yan2anfei](https://github.com/yan2anfei/kobo-kernel-2.6.35.3-marek) · [rudals](https://github.com/rudals/kobo-kernel-2.6.35.3-marek) · [Nasfald](https://github.com/Nasfald/kobo-kernel-2.6.35.3-marek) · [MSylvia](https://github.com/MSylvia/kobo-kernel-2.6.35.3-marek) · [guchai25](https://github.com/guchai25/kobo-kernel-2.6.35.3-marek) · [awenocur](https://github.com/awenocur/kobo-kernel-2.6.35.3-marek) · [JohnOH](https://github.com/JohnOH/kobo-kernel-2.6.35.3-marek) · [robintel](https://github.com/robintel/kobo-kernel-2.6.35.3-marek) · [hakat0m](https://github.com/hakat0m/kobo-kernel-2.6.35.3-marek) |
| **Du code ou de la documentation en avance** | **3** | [Mizuho32](https://github.com/Mizuho32/kobo-kernel-2.6.35.3-marek) **+6**, [clo2](https://github.com/clo2/kobo-kernel-2.6.35.3-marek) **+2**, [kaminchu](https://github.com/kaminchu/kobo-kernel-2.6.35.3-marek) **+1** |
| **En retard** | **1** | [twobob](https://github.com/twobob/kobo-kernel-2.6.35.3-marek) : **0 ahead / 4 behind** |

**Branches :** tous possèdent `linux`. Branches supplémentaires observées : Mizuho32 (`real-suspend-baseline-test`, `track-l-9-clock-buswidth-timing-fix`, `wifi-hostsleep-fix`) ; kaminchu (`feature/ci`) ; hakat0m (`master`, **sans ancêtre Git commun** avec `marek-g:linux` sur cette branche, donc ne pas lui attribuer des nouveautés Marek).

**Conclusion de balayage : un seul fork apporte de nouveaux changements matériels significatifs : Mizuho32.** Les deux autres portent des correctifs d'outillage/CI.

## 2. Mizuho32 : correction SDIO du 29 septembre 2026

[Branche `linux`](https://github.com/Mizuho32/kobo-kernel-2.6.35.3-marek/tree/linux), HEAD `4c4b58d3910456470a315cda6415daf735d8d76c`, dernier commit du **29 septembre 2026**, six commits depuis le parent. Le [README](https://github.com/Mizuho32/kobo-kernel-2.6.35.3-marek/blob/linux/README.md) ajoute un volet **Wi-Fi SDIO en veille/réveil** au noyau historique.

### Correctif fondamental (à étudier, pas à importer)

Le [commit `764cdbea`](https://github.com/Mizuho32/kobo-kernel-2.6.35.3-marek/commit/764cdbea6329a1593953ef813db5eeda8dcc6f90) modifie uniquement `drivers/mmc/host/mx_sdhci.c` pour deux pannes distinctes après un suspend réel :

1. Un `SDHCI_RESET_ALL` de reprise effaçait des réglages du contrôleur (notamment **largeur de bus HOST_CONTROL et horloges/auto-gating**). Le patch les sauvegarde/restaure **immédiatement après le reset**, avec une temporisation de stabilisation de 2 ms. Selon l'auteur, une restauration plus tardive ne corrigeait pas la panne.
2. Une tentative antérieure d'activer trop tôt `SDHCI_INT_CARD_INT` dans `SIGNAL_ENABLE` déclenchait une **tempête d'IRQ**. Le patch conserve le masque initial puis réactive l'interruption SDIO **après `mmc_resume_host()`**, lorsque le thread de gestion est en état de l'absorber.

**Preuve déclarée par l'auteur :** message du commit `764cdbea` : **plus de dix cycles physiques veille (`echo mem`) → réveil → reprise**, y compris avec son flux complet de suspension, Wi-Fi reconnecté avec **0 % de pertes ping**, sans blocage. C'est un **résultat de test réel rapporté, mais non contre-qualifié indépendamment**, sur **un appareil dont l'identité exacte n'est pas établie par les fichiers étudiés**, et **aucune preuve propre à PMKB E606C0**.

L'initialisation SDIO touche potentiellement plus que le seul Wi-Fi : elle est critique pour nos interactions MMC/microSD. Il faut un audit du vrai contrôleur et du noyau E606C0 avant toute proposition de patch.

### Autres changements du fork : expérimentation, pas livraison PMKB

- [`arch/arm/mach-mx5/mx50_ntx_io.c`](https://github.com/Mizuho32/kobo-kernel-2.6.35.3-marek/blob/linux/arch/arm/mach-mx5/mx50_ntx_io.c) : activation de `_WIFI_ALWAYS_ON_` pour éviter la coupure 3,3 V du Wi-Fi durant la veille. **Risque direct pour l'autonomie**, particulièrement contraire au « Wi-Fi à la demande » de PMKB tant que la consommation n'est pas mesurée.
- [`drivers/mmc/core/sdio.c`](https://github.com/Mizuho32/kobo-kernel-2.6.35.3-marek/blob/linux/drivers/mmc/core/sdio.c) : diagnostics et propositions de réutilisation de l'état SDIO durant une veille avec `MMC_PM_KEEP_POWER` ; un commutateur `kobowm_light_resume` apparaît **désactivé par défaut**. Ne pas déduire une optimisation universelle du protocole.
- [`drivers/mmc/host/dhd_hostsleep_hook/dhd_hostsleep_hook.c`](https://github.com/Mizuho32/kobo-kernel-2.6.35.3-marek/blob/linux/drivers/mmc/host/dhd_hostsleep_hook/dhd_hostsleep_hook.c) : module externe qui **modifie à l'exécution** le pointeur `dev_pm_ops` du pilote propriétaire/historique `bcmsdh_sdmmc` fourni par `dhd.ko`. Le commentaire de ce module le signale explicitement **« UNTESTED on real hardware as of this file »**. Certaines parties du code relatent d'anciens échecs et essais isolés. **Ne pas confondre ce statut avec les cycles physiques revendiqués pour le correctif `mx_sdhci.c`.**
- [`build_and_install.sh`](https://github.com/Mizuho32/kobo-kernel-2.6.35.3-marek/blob/linux/drivers/mmc/host/dhd_hostsleep_hook/build_and_install.sh) : si une adresse IP est passée, script de **déploiement SSH** qui copie le module et **modifie `/etc/init.d/rcS`** pour un chargement automatique. Dépend d'un chroot/de la topologie **KoboWM** et active des paramètres `ssh-rsa` hérités. **INTERDIT D'EXÉCUTER sur notre Kobo ou une image PMKB** sans lot spécifique de qualification et validation expresse. Aucun usage de ce script dans cet audit.
- **EPDC et ZForce inchangés sur `linux`** : `drivers/video/mxc/mxc_epdc_fb.c` a exactement le même SHA de blob que Marek (`50c0fe9d...`) et `drivers/input/touchscreen/zforce_i2c.c` également (`c9e858f4...`). **Ce fork n'apporte aucun correctif e-ink ou tactile nouveau** pour notre écran 1440 × 1080.

### Branches expérimentales de Mizuho32

| Branche | Delta à `marek-g:linux` | Ce que démontre l'inspection |
| --- | ---: | --- |
| [`wifi-hostsleep-fix`](https://github.com/Mizuho32/kobo-kernel-2.6.35.3-marek/tree/wifi-hostsleep-fix) | **+5 commits**, fichiers MMC, noyau et module `dhd_hostsleep_hook` | Version antérieure à l'ajout documentaire du `linux` courant |
| [`real-suspend-baseline-test`](https://github.com/Mizuho32/kobo-kernel-2.6.35.3-marek/tree/real-suspend-baseline-test) | **+12 commits**, `mx_sdhci.c` avec ~921 lignes de changement cumulé | Branche de diagnostic « baseline », **pas 12 correctifs matériels indépendamment prouvés** |
| [`track-l-9-clock-buswidth-timing-fix`](https://github.com/Mizuho32/kobo-kernel-2.6.35.3-marek/tree/track-l-9-clock-buswidth-timing-fix) | **+22 commits**, `mx_sdhci.c` avec ~1143 lignes de changement cumulé | Investigations et variantes plus volumineuses que la branche finale ; **ne pas préférer ce nombre de commits au patch ciblé du `linux` actuel** |

**Point spécifique PMKB :** notre modèle **E606C0** est documenté, mais les fichiers de matériel PMKB consultés n'attestent pas **l'identité exacte du module Wi-Fi ni la présence de `dhd.ko`** sur notre image. Ne pas affirmer que le module `bcmsdh_sdmmc` ou la chaîne KoboWM existent sur notre système sans vérification. La technologie SDIO partagée **ne suffit pas** à prouver la compatibilité du patch.

## 3. Les deux autres forks qui changent quelque chose

**[clo2/kobo-kernel-2.6.35.3-marek](https://github.com/clo2/kobo-kernel-2.6.35.3-marek)** — +2 commits (**7 août 2017**), 3 fichiers : `kernel/timeconst.pl` remplace le vieux `defined(@val)` devenu incompatible avec certaines versions de Perl par un test direct de tableau ; `build.sh` ajoute des commandes de cross-compilation ARM ; `memo.md` documente GCC 4.9, Ubuntu 16.04 et la construction `uImage`. **RETENIR conditionnellement le correctif Perl pour la reproductibilité si une erreur identique se reproduit**, pas de modification EPDC/ZForce/SDIO.

**[kaminchu/kobo-kernel-2.6.35.3-marek](https://github.com/kaminchu/kobo-kernel-2.6.35.3-marek)** — +1 commit sur `linux` (**30 septembre 2018**), `.gitlab-ci.yml` et `.gitignore` seulement. La branche [`feature/ci`](https://github.com/kaminchu/kobo-kernel-2.6.35.3-marek/tree/feature/ci) atteint **+8 commits**, toujours uniquement sur ces fichiers ; CI historique sous **Ubuntu 14.04**. **Pas de nouveauté kernel, pas de PASS de compilation démontré** par simple présence de la configuration CI.

**[twobob/kobo-kernel-2.6.35.3-marek](https://github.com/twobob/kobo-kernel-2.6.35.3-marek)** — `linux` **0 ahead / 4 behind** : pas de nouveau correctif. Les douze copies identiques n'ont aucune divergence sur leur `linux`.

## 4. Décision pour PMKB

| Objet | Décision |
| --- | --- |
| Fork Marek **Mizuho32** | **P1 / R5 : comparateur à haute valeur** pour veille/réveil **SDIO/Wi-Fi** à étudier une fois FIRST BOOT et identité radio/driver qualifiés ; **pas de remplacement de noyau ni d'import de hook** |
| Comportement SDHCI `RESET_ALL` / IRQ différée | **Hypothèse technique vérifiable** sur noyau cible : reproduire d'abord défaut et timing, puis contre-tester des correctifs minimalistes dans un environnement hors carte |
| Alimentation Wi-Fi maintenue / hook `dhd.ko` | **NON RETENUS en l'état** : risques autonomie, compatibilité ABI, interaction avec propriétaire, mémoire et stabilité |
| Fork clo2 | **P2 / outillage** si Perl/GCC existants posent problème ; prioriser toolchain reproductible |
| Fork kaminchu | **INFO / CI ancienne**, aucun changement matériel |
| Douze copies et twobob | **ARCHIVE**, pas de nouvelle piste de runtime |

**Bilan documentaire :** 16 copies de même nom avec ascendance `linux` comparées, 12 identiques, 3 en avance, 1 en retard ; branches inspectées ; 3 branches Mizuho32 supplémentaires comparées, plus CI de kaminchu. Sources ciblées lues, contre-qualification du code et des affirmations de test. **0 build, 0 PASS matériel PMKB, 0 téléchargement d'archive ou de firmware, 0 exécution de script distant, 0 modification du runtime PMKB, 0 changement de la carte ou de P2**. Les récits de tests réels de Mizuho32 sont des déclarations tierces et ne qualifient **pas** notre Aura HD.
