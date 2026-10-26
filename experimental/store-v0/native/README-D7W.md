# PMKB L07-D7w — modifications pendant une presentation asynchrone

Le test C11 soumet une surface Store, effectue deux modifications de pixels dans des zones eloignees alors que le premier marqueur est en attente, puis confirme la premiere soumission. La confirmation compte comme terminee, **sans acquitter les modifications apparues pendant l'attente**. Une nouvelle soumission avec un marqueur distinct est ensuite necessaire avant la disparition de l'etat dirty.

Le test controle egalement le refus d'une deuxieme soumission simultanee, ainsi que `PMKB_NO_CHANGE` lorsque le second envoi a ete confirme.

Commit test : `70f95f9021d60c33e88fc4134fa27b218c8eaa96`. CI a qualifier avant PASS. Simulateur sur hote uniquement, aucun appareil EPDC ou DMA utilise, Store non executable, PR #30/#31 non fusionnees, FIRST BOOT/P2 inchanges.
