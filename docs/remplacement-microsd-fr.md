# PMKB — Remplacer la microSD d'une Kobo Aura HD

## Objectif

Le parcours normal de réparation n'est pas de modifier la microSD originale.

La carte d'origine sert de **donneuse en lecture seule**. Le Live PMKB y récupère les éléments indispensables propres à la Kobo, puis demande une **autre microSD** et construit dessus une carte PMKB complète.

La donneuse doit rester conservée comme sauvegarde matérielle.

## Parcours opérateur

1. Démarrer le PC sur la clé PMKB Live.
2. Choisir **Créer / réparer une nouvelle microSD PMKB**.
3. Insérer la microSD originale de l'Aura HD.
4. Saisir explicitement son disque complet, par exemple `/dev/sdb`.
5. PMKB ouvre la donneuse en lecture seule et vérifie :
   - disque complet amovible via USB ;
   - secteurs logiques de 512 octets ;
   - Aura HD E606C0 reconnue par HWCONFIG ;
   - géométrie système attendue ;
   - PRE-P1/HWCONFIG identique à la référence qualifiée ;
   - P2/recoveryfs identique à la référence qualifiée.
6. PMKB copie en staging Live uniquement :
   - PRE-P1, environ 9,5 Mio ;
   - P2/recoveryfs, 256 Mio ;
   - un manifeste de capture.
7. Retirer la microSD originale.
8. Insérer la nouvelle microSD et saisir explicitement son disque complet.
9. PMKB vérifie que la cible est amovible, USB, inutilisée, de taille suffisante et qu'elle ne ressemble pas à la carte donneuse.
10. PMKB prépare un plan lié à la taille et à une empreinte de la nouvelle carte.
11. Le plan affiche la capacité de la nouvelle carte et la taille de la future P3.
12. Aucune écriture n'a encore lieu. L'opérateur doit recopier la phrase d'autorisation qui contient la cible et le SHA-256 du plan.
13. Après cette confirmation seulement, PMKB construit la nouvelle carte et relit les zones critiques.

La carte donneuse n'est jamais ouverte en écriture dans ce parcours.

## Géométrie

Les zones système Aura HD restent aux offsets qualifiés :

- PRE-P1 : octets `0..9 961 471` ;
- P1/rootfs : offset `9 961 472`, taille `268 435 968` ;
- P2/recoveryfs : offset `278 397 440`, taille `268 435 968` ;
- P3/KOBOeReader : commence à `546 833 408`.

Sur la nouvelle carte :

- PRE-P1 provient de la donneuse, avec uniquement la taille MBR de P3 adaptée à la capacité cible ;
- P1 contient le candidat PMKB FIRST BOOT qualifié ;
- P2 est recopiée bit pour bit depuis la donneuse et doit conserver son SHA-256 qualifié ;
- P3 est créée en FAT32 avec le label `KOBOeReader` et utilise le reste disponible de la carte.

Les offsets de P1, P2 et du début de P3 ne changent donc pas quand la capacité de la nouvelle carte change.

## Taille de la nouvelle carte

Le backend ne demande pas une carte de 32 Go.

Il calcule la taille utilisable à partir de la capacité réelle de la cible. Le contrat actuel réserve au minimum **1 Gio pour P3**, en plus des zones système. Le minimum théorique est donc :

`546 833 408 + 1 073 741 824 = 1 620 575 232 octets`

Une carte annoncée **2 Go ou plus** satisfait ce minimum théorique. En pratique, PMKB est destiné à des cartes nettement plus grandes ; 16 Go, 32 Go, 64 Go, etc. utilisent la même logique.

La géométrie MBR limite également P3 à un nombre de secteurs codable sur 32 bits. La compatibilité matérielle réelle de très grandes capacités avec l'Aura HD reste à qualifier sur l'appareil ; le backend ne doit pas présenter cette compatibilité matérielle comme acquise avant test.

## Deux modes séparés

Le backend historique `restore-p1-linux.py` reste inchangé et conserve son contrat strict :

- cible = carte originale connue ;
- carte complète identique à la sauvegarde qualifiée ;
- seule P1 peut être écrite ;
- tout l'extérieur de P1 doit rester identique.

Le nouveau backend `replace-microsd-linux.py` a un autre contrat :

- source = carte originale, lecture seule ;
- cible = nouvelle microSD explicitement choisie ;
- PRE-P1 adapté uniquement pour la taille P3 du MBR ;
- P1 = PMKB ;
- P2 = recovery originale ;
- P3 = FAT32 `KOBOeReader` neuve.

Les deux contrats ne doivent pas être fusionnés : accepter arbitrairement une carte différente dans le backend de restauration P1 supprimerait un garde-fou important.

## Échec pendant la création

Une nouvelle carte est considérée comme jetable/reconstructible jusqu'à validation complète.

Si une erreur survient après le début de l'écriture :

- PMKB signale que la cible peut être partielle ;
- aucune tentative automatique de récupération n'est faite ;
- la carte originale reste intacte ;
- on recommence la création de la nouvelle carte après diagnostic.

Le FIRST BOOT matériel, l'écran, le tactile, le frontlight, le montage de P3 et l'USB restent **UNQUALIFIED** jusqu'au démarrage réel de l'Aura HD sur une carte ainsi créée.


## Progression opérateur

Les opérations longues restent volontairement sobres dans FIRST BOOT #1. Le Live affiche une progression texte pendant les lectures, copies et relectures importantes :

`Lecture originale P2 recovery: 72% (184.3/256.0 MiB, 18.4 MiB/s)`

Le même format est utilisé pour la capture PRE-P1/P2, l'écriture P1/P2 et leur vérification. Aucun effet graphique ou animation n'est requis avant la qualification matérielle de la Kobo.
