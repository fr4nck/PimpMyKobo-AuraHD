# SECURITY CONTRACT V1 — vérification synthétique et inerte

Outil Python standard, **non intégré à l'appareil**. `security_contract.py` ne lit ni fichiers, ni périphériques, ni interfaces réseau ; aucune commande, aucune collecte, aucun service ou système de mise à jour. Il travaille uniquement sur des dictionnaires ou des chaînes JSON **déjà fournis** au processus.

## API

- `analyze(declaration: dict)` : statut de cohérence déclarative.
- `analyze_json(text: str)` : décodage JSON strict avec refus des clés dupliquées, constantes non standard et chaînes trop grandes (131072 caractères).

Clés exactes du document : `format` = `pmkb-security-declaration-v1`, `device` = `E606C0`, `profile` = `OFFLINE` ou `CONNECTED`, `provenance` = `synthetic`, `configuration` (les champs listés dans CONFIG_ENUMS), `services` (services actifs déclarés), `gate_claims` (SEC-01 à SEC-12), `attestations` (trois booléens **false**).

Les 12 gate_claims sont strictement `claimed_met`, `claimed_unmet`, `unknown`, `not_applicable`. Le SKIP n'est admis que pour SEC-09 en OFFLINE et `updates=none`. Un `claimed_met` ne devient **jamais PASS** : la sortie gate est UNKNOWN, même si le manifeste n'a aucune contradiction. Les erreurs déclarées sont FAIL, les SKIP sont motivés, et toute sortie garde `connected_ready=false`, `security_certified=false`, `hardware_verified=false`, `deployment_allowed=false`.

L'outil refuse entre autres : Telnet, SSH avec mot de passe ou root, services non prévus, port Internet, Wi-Fi actif ou socket déclaré en OFFLINE, image FIRST BOOT/P2 déclarée modifiée, lecteur root, rootfs rw, autorun de fichier importé, updates unsigned, profil CONNECTED utilisant 2.6.35.3 ou un noyau non maintenu déclaré. Les services autorisés par le modèle CONNECTED V1 sont exclusivement SSH LAN/loopback par clé non-root ; tout autre service requiert une nouvelle revue de politique, pas une modification silencieuse.

**Limite :** aucune déclaration, y compris « maintained », n'est authentifiée. Ce contrôle n'analyse pas le vrai kernel, ses permissions, ports, vulnérabilités ou signatures. Les tests utilisent des fixtures fabriquées en mémoire ; ils ne reflètent pas l'état physique de l'Aura HD.

Qualification visée : `python -m unittest discover -s tests -p test_security_contract.py -v`. La CI existante lance également la suite complète. Aucune nouvelle dépendance installée sur la Kobo.
