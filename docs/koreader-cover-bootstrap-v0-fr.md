# PMKB — réglage de la housse dans KOReader (28 octobre 2026)

**État : prototype d'amorçage, vérification matérielle NON EFFECTUÉE.**

Dans KOReader v2026.07.1, reader.lua ouvre le fichier settings.reader.lua dans le répertoire retourné par DataStorage:getDataDir(). Avec les variables KO_MULTIUSER=1 et XDG_CONFIG_HOME=/tmp/pmkb/config fournies par notre lanceur, le chemin est /tmp/pmkb/config/koreader/settings.reader.lua.

Les sources KOReader v2026.07.1 confirment que ignore_power_sleepcover=true retire les gestionnaires SleepCoverClosed/SleepCoverOpened sans retirer celui du bouton physique Power. Voir https://github.com/koreader/koreader/blob/v2026.07.1/frontend/device/kobo/device.lua et https://github.com/koreader/koreader/blob/v2026.07.1/datastorage.lua .

Le nouveau script pmkb-cover-init, exécuté avant le garde final de montage P3, écrit un petit tableau Lua exclusivement dans XDG_CONFIG_HOME/koreader **si settings.reader.lua est absent**. Il ne remplace jamais les préférences existantes ; un changement effectué depuis KOReader est conservé durant la session. La création est privée (umask 077), refuse les liens symboliques et utilise le noclobber shell. Le builder exige le fichier et l'inclut dans son audit des scripts de démarrage.

**Limites :** les préférences résident dans /tmp : elles ne survivent pas à un redémarrage complet. Le stockage P3 reste en lecture seule et la persistance nécessite une qualification séparée. Filtrer les événements KOReader **ne désactive pas les IRQ Hall ou les réveils noyau** ; l'incident rapporté (réveil parfois possible seulement après branchement USB) peut impliquer batterie, PMIC, MCU ou suspend/resume. L'interface native C11 de la PR #55 est un mécanisme distinct, pas encore relié à un capteur réel.

Tests hôte : python3 -m unittest discover -s tests -p test_koreader_cover_init.py -v. Aucun téléchargement de firmware, accès /dev, écriture sur microSD, P1/P2/P3 ou modification de FIRST BOOT scellé.
