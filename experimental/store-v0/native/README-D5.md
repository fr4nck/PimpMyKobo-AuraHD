# PMKB Store — L06-D5 : contrat minimal du cycle de vie d'écran

Ce sous-lot ajoute `pmkb_store_screen.h`, un petit adaptateur C11 **sans allocation** ni processus permanent au cache facultatif L06-D4d. Il ne remplace ni le rendu classique, ni le moteur PMKB-UI, ni le Launcher.

## Contrat des transitions

1. `pmkb_store_screen_init(&screen)` : objet prêt mais **invisible** ; dessiner le Store est refusé.
2. `pmkb_store_screen_enter(&screen)` : entrée ou retour au Store ; le cache est vidé et le prochain dessin est réel.
3. `pmkb_store_screen_paint(&screen, view, page, painter)` : rendu **uniquement si visible** ; deux dessins de contenus identiques peuvent réutiliser le cache.
4. `pmkb_store_screen_external_draw(&screen)` : l'appelant annonce toute écriture d'un autre composant sur la même surface, pour forcer le prochain dessin Store.
5. `pmkb_store_screen_leave(&screen)` : sortie, changement d'écran ou fermeture ; le cache est vidé, tout rendu Store est refusé jusqu'à une nouvelle entrée.

**Limite impérative :** cette API ne peut pas détecter une écriture directe au framebuffer si l'appelant n'a pas annoncé cette écriture. L'intégration devra imposer la notification à chaque point où la surface est partagée, ou rester avec le dessin sans cache. Un cache de 64 bits n'est ni une preuve d'intégrité ni une permission d'exécution.

## Qualification sur hôte

Le fichier existant `native/test_store_real_surface.c` est étendu. La CI Python 3.11 Linux/Windows lie **les vrais** `pmkb_ui.h` et `pmkb_surface.c` du commit épinglé de la PR #30, sans fusion. Les scénarios exercent l'état invisible, la première entrée, le hit de cache, l'écriture par un autre composant suivie d'une notification, la sortie, la nouvelle entrée et le rejet d'une page forgée. Le test rapporte la taille réelle de `PMKBStoreScreen`, bornée à 64 octets sur l'hôte.

**Non qualifiés** : appel réel depuis le Launcher, écran physique e-ink, EPDC, tactile, ARM, énergie et accès P3. La PR #30 reste intacte, la PR #31 en brouillon, le FIRST BOOT scellé et P2 protégés.

**Prochain sous-lot L06-D5b** : vérifier la CI au nouveau HEAD ; si nécessaire, corriger un défaut effectivement reproduit avant tout raccordement au Launcher.
