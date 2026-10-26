# PMKB L07-D7v — invariants de confirmation asynchrone

Le test C11 verifie que les confirmations nulles, inconnues, dupliquees et anciennes ne changent ni les statistiques de completions/echecs, ni le marqueur encore en attente, ni les pixels dirty. Une confirmation valide incremente uniquement les succes et acquitte les pixels. Une nouvelle soumission suivie d'une confirmation d'un ancien marqueur doit rester active, et un echec valide doit incrementer uniquement les echecs sans effacer dirty.

Test `2c9262ac22e4301ee3eb12be2e5167b884c9b20d`, CI a verifier avant qualification. Tests sur hote uniquement, pas de thread ou pilote EPDC reel, Store non executable, PR #30 et #31 non fusionnees, FIRST BOOT/P2 inchanges.
