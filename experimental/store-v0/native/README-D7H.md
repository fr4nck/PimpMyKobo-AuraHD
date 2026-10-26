# PMKB D7h — interdiction de presenter apres fermeture

Test de cycle de vie : ouverture d'un apercu Store, fermeture explicite, tentative de presentation avec un backend simule. Aucun callback ne doit se produire et aucun octet de pixels Store ne doit demeurer alloue. Une nouvelle ouverture explicite doit permettre la presentation normale.

Commit de test : `2096d94c47be7f431626e671f187a17a8c48f5be`. Attendre les resultats CI pour declarer PASS. Le Store reste non executable, les PR #30/#31 ne sont pas fusionnees et aucune partition ni Kobo physique n'est modifiee.
