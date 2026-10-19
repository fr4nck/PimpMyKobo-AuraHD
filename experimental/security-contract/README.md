# SECURITY CONTRACT V1 — vérification synthétique et inerte

Outil Python standard, **non intégré à l'appareil**. `security_contract.py` ne lit ni fichiers, ni périphériques, ni interfaces réseau ; aucune commande, aucune collecte, aucun service ou système de mise à jour. Il travaille uniquement sur des dictionnaires ou des chaînes JSON **déjà fournis** au processus.

## API

- `analyze(declaration: dict)` : statut de cohérence déclarative.
- `analyze_json(text: str)` : décodage JSON strict avec refus des clés dupliquées, constantes non standard et chaînes trop grandes (131072 caractères).

Compatibilité : le schéma V1 existant reste accepté sans changement. Une clé optionnelle `opt_ins` (liste d'identifiants uniques figurant dans `OPT_INS`) décrit les fonctionnalités choisies dans un scénario. Une entrée synthétique **ne vérifie pas l'identité de l'utilisateur**, ne tient pas lieu de consentement matériel et n'active aucun service. Sans opt-in, les refus de la politique précédente restent inchangés.

Clés exactes du document : `format` = `pmkb-security-declaration-v1`, `device` = `E606C0`, `profile` = `OFFLINE` ou `CONNECTED`, `provenance` = `synthetic`, `configuration` (les champs listés dans CONFIG_ENUMS), `services` (services actifs déclarés), `gate_claims` (SEC-01 à SEC-12), `attestations` (trois booléens **false**).

Les 12 gate_claims sont strictement `claimed_met`, `claimed_unmet`, `unknown`, `not_applicable`. Le SKIP n'est admis que pour SEC-09 en OFFLINE et `updates=none`. Un `claimed_met` ne devient **jamais PASS** : la sortie gate est UNKNOWN, même si le manifeste n'a aucune contradiction. Les écarts non choisis restent FAIL ; les risques explicitement déclarés restent UNKNOWN avec avertissement. Les SKIP sont motivés et toute sortie garde `connected_ready=false`, `security_certified=false`, `hardware_verified=false`, `deployment_allowed=false`.

**Options configurables, désactivées par défaut** : `offline_wifi`, `offline_service`, `telnet`, `ssh_password`, `ssh_root`, `extra_service`, `public_listener`, `reader_root`, `writable_rootfs`, `untrusted_autorun`, `unsigned_updates`, `connected_no_updates`, `legacy_connected`, `unmaintained_kernel`. Chaque exception **doit être décrite dans `opt_ins`** ; sinon le scénario reste `blocked`. Les options dangereuses restent signalées dans `risk_advisories` avec risque en clair, niveau et gate concernée. `choices_consistent_unverified` signifie exclusivement que ces choix ont été déclarés et sont cohérents. Il n'est jamais synonyme de « sûr » ni d'autorisation d'exécution.

**Invariants non négociables de ce lot** : la modification déclarée de FIRST BOOT ou de recovery reste `FAIL`, aucune option ne permet à un manifeste de certifier l'appareil ou de déployer quoi que ce soit. Le réseau reste **désactivé par défaut** (`network_default="off"`) ; des services ou Wi-Fi peuvent être prévus à la demande, sans démarrage automatique. Telnet est du texte clair : réserver ses essais éventuels à un réseau isolé et contrôlé ; préférer SSH pour un usage régulier. L'analyse ne lit ni configuration réelle ni état radio.

**Limite :** aucune déclaration, y compris « maintained », n'est authentifiée. Ce contrôle n'analyse pas le vrai kernel, ses permissions, ports, vulnérabilités ou signatures. Les tests utilisent des fixtures fabriquées en mémoire ; ils ne reflètent pas l'état physique de l'Aura HD.

Qualification visée : `python -m unittest discover -s tests -p test_security_contract.py -v`. La CI existante lance également la suite complète. Aucune nouvelle dépendance installée sur la Kobo.
