# PMKB D7k — fermeture apres echec de presentation

Le test C11 cree un apercu Store puis fait echouer son callback de presentation. La zone dirty reste presente jusqu'a la fermeture. `pmkb_store_router_dismiss` detache alors le garde et libere le framebuffer ; une presentation apres fermeture doit etre refusee sans callback supplementaire. Une nouvelle ouverture suivie d'une presentation reussie repart avec un framebuffer propre.

Test publie au commit `aa22bec655c61b99af461a2e1bfc6d77ac83daf7`. Sa CI doit etre verifiee avant de declarer PASS. Aucun acces EPDC, activation Store, fusion des PR #30/#31 ou ecriture FIRST BOOT/P2.
