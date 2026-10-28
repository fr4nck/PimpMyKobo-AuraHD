# PMKB L07-D7r — discipline d'annulation integree au cycle de vie

L'adaptateur facultatif `pmkb_store_eink_lifecycle.h` rassemble un routeur Store passif et son marqueur E-Ink simule. Avant fermeture, redimensionnement ou nouvel apercu, il annule automatiquement un marqueur en attente, puis transmet l'operation au routeur existant. Les confirmations tardives sont rejetees et le buffer ferme ne peut pas etre acquitte apres coup.

Le test C11 verifie: submit, resize avec annulation, refus du marqueur obsolete, nouvelle soumission, fermeture, refus du marqueur annule, reouverture, confirmation valide et shutdown.

**Portee** : contrat hote seulement. La soumission reste un modele sans pilote ni copie de framebuffer pour DMA. Le wrapper n'intercepte pas les usages directs de `pmkb_store_router_dismiss` en dehors de son interface; les futurs appels devront utiliser ce controleur de cycle de vie pour avoir la garantie d'annulation. Les operations sont sequentielles, pas thread-safe. Aucun acces EPDC/i.MX50 ni ecriture Kobo/FIRST BOOT/P2 ; PR #30 et #31 restent non fusionnees.

Code : `cdbaf265b0aac8c642773ea86a5911a6b1d6d5b5`. Tests : `529b7ccf14c38b15f15078e760acf9af207f023f`. CI doit etre terminee avant PASS.
