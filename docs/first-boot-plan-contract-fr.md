# Contrat de preuve FIRST BOOT : simulation et plan P1

Base : `integration/pmkb-first-boot-1`, commit
`1ca255791d71a99351497c16f373d11309c3545a`.
Branche de correction : `fix/pmkb-first-boot-plan-contract`.

## Correction

La chaîne accepte explicitement deux producteurs : `rebuild-rootfs` et
`build-koreader-rootfs`. Les contrôles de reconstruction legacy restent exigés
pour le premier. Pour le second, le rapport original doit décrire un candidat
E606C0 complet, expérimental, sans erreur et non qualifié matériellement.
Aucun rapport PMKB n'est transformé en rapport `rebuild-rootfs`.

Pour PMKB, les paramètres ext4 réels sont comparés au rapport : label, taille
des blocs, taille des inodes, features, nombre de blocs et octets de queue.
Les paramètres de compatibilité sont comparés à la référence P2 préservée.
`e2fsck -f -n` doit ensuite retourner zéro sur le fichier candidat.

La simulation crée une nouvelle copie complète du backup et remplace P1
uniquement dans cette copie. P1 est relue ; le préfixe, P2, P3 et tout le
suffixe après P1 doivent rester identiques. Le backup source est revérifié.
`prepare-p1-restore` revalide les entrées, le rapport d'acquisition, le rapport
de simulation et les octets de l'image simulée. Le plan conserve le type et
le SHA du rapport producteur, le SHA du candidat, le SHA du backup complet,
le SHA de la simulation complète et les SHA des autres preuves.

Le scellement local est le SHA-256 exact du JSON du plan, contrôlé par
`validate_sealed_plan` avec le candidat exact. Aucun ISO Live n'est généré
par cette validation. Les anciens plans sans les nouveaux liens de preuve
doivent être régénérés, puis scellés à nouveau.

## Tests

Commande : `python3 -m unittest discover -s tests`.
Résultat : **343 tests, succès, 7 ignorés**.
Journal local : `/tmp/pmkb-plan-contract-all-tests-final.log`.

Le nouveau test d'intégration utilise un vrai ext4 créé avec e2fsprogs et
un runtime synthétique, sans firmware redistribué. Il parcourt
`build-koreader-rootfs → simulation complète → prepare-p1-restore → validation du scellement`.
Les refus couvrent notamment les SHA incohérents, les métadonnées ext4
altérées, les divergences avec P2, les échecs/absences d'e2fsck, un type de
producteur falsifié, les anciennes preuves incomplètes et les autorisations
physiques activées. Le test legacy de reconstruction nécessite ici une
exécution hors sandbox en raison de la restriction `chown` sous fakeroot.

## Fichiers modifiés par rapport à la base

- `tools/restore-rootfs.py`
- `tools/prepare-p1-restore.py`
- `tools/restore-p1-linux.py`
- `tests/test_restore_rootfs.py`
- `tests/test_prepare_p1_restore.py`
- `tests/test_restore_p1_linux.py`
- `tests/make_qualification_live_fixture.py`
- `docs/restore-rootfs-simulation-fr.md`
- `docs/restore-rootfs-simulation-en.md`
- `docs/prepare-p1-restore-fr.md`
- `docs/first-boot-plan-contract-fr.md`

## Vérification sur les fichiers réels préservés — 4 octobre 2026

Les SHA ci-dessous ont été recalculés. La nouvelle simulation est une copie
du backup complet fourni ; seules ses bornes P1 ont été remplacées.

| Fichier | SHA-256 |
| --- | --- |
| Candidat `PMKB-FIRST-BOOT-1-0b00d858.img` | `7980fec15cb62ca3c2cabcb64cbbb683446fbf64070d75b45acf9a5e99e0f67c` |
| Backup `AuraHD-full-card-2026-10-03.img` | `522a4a7c52516e6fd91030397d5c04352a0074789d2403bb2fa9360c0cbe733a` |
| Nouvelle simulation complète | `b0a8f6d8eb0731a66ce0c89cef11d8c6bc42aef4491da53671e588c4bf56fded` |

Taille de l'image complète : **31 914 983 424 octets**.
P1 : offset **9 961 472**, taille **268 435 968 octets**.
Le SHA de P1 relue correspond au candidat. Les SHA pré-P1, P2, P3 et du
suffixe après P1 sont identiques avant/après. Le backup source est inchangé.
P2 conservée : `fe7885d391a5627cf2b04bd75518cf8fb5b0f379b29032727adb29cba35b968a`.

Le rapport producteur original conserve `tool=build-koreader-rootfs` et
le SHA `80d54bc08ded38f7814eb21e0d662c9c10901d444a021f8a055eb9f80a86a7c9`.
La revalidation ext4 réelle confirme le label `rootfs`, des blocs de 1024
octets, des inodes de 128 octets, 262 144 blocs et 512 octets de queue.
Les features correspondent au rapport et à P2. `e2fsck -f -n` retourne **0**.

Les artefacts et le script de reproduction local sont conservés dans
`private/first-boot-plan-contract-2026-10-04/`, hors Git : image simulée,
rapport `.simulation.json`, résultats de préparation, plan, scellement,
`SHA256SUMS` et journaux. Les données Kobo privées ne sont pas redistribuées.

Nouveau plan : `PMKB-FIRST-BOOT-1.restore-plan.json`.
SHA-256 scellé et accepté par `validate_sealed_plan` :
`58c6a988310e90b9c4b7a891914b2aef626082d710ec131f30b6e47622ca456c`.
SHA du nouveau rapport de simulation :
`00ca61e8cb14c0fffd5bcf31eb00826d2e8923a1dc5785665ad0c66a4560e3a1`.

**Verdict : chaîne locale complète validée**, jusqu'au plan scellé.
`physical_restore_eligible=false` et `write_authorized=false` restent
inchangés. Aucune écriture sur un périphérique ou une P1 physique, aucune
modification de P2 physique, aucun merge. Le démarrage sur Aura HD n'a pas
été qualifié ; ces preuves portent sur les fichiers réels préservés et
leur simulation locale.
