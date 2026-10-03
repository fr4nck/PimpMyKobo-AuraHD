# Démontage de la Kobo Aura HD

[English](disassembly-en.md) | [Version texte / Lynx](disassembly-lynx-fr.txt)

Ce guide décrit l’ouverture d’une **Kobo Aura HD / N204** afin d’accéder à sa **microSD système interne**.

La procédure part d’un démontage réel, puis est **recoupée avec les sources iFixit et MobileRead** indiquées à chaque étape. Les photographies montrent l’exemplaire démonté pour ce projet ; aucune photographie iFixit ou MobileRead n’est reproduite ici.

> **Principe du projet :** quand une information provient d’une source externe, elle est citée. Quand une observation provient directement de la machine étudiée, elle est signalée comme telle.
>
> **Navigation texte :** aucune étape ne dépend des photographies. Avec Lynx ou un terminal sans images, le texte alternatif, les légendes et les schémas ASCII fournissent l’information nécessaire. Une [version texte pur](disassembly-lynx-fr.txt) est également disponible.

## Avant de commencer

Éteindre complètement la liseuse et débrancher le câble USB.

Matériel conseillé :

- médiator, carte plastique fine ou spudger en plastique ;
- petit tournevis cruciforme de précision ;
- surface propre, plane et non conductrice ;
- lecteur de cartes microSD pour la sauvegarde ultérieure.

Éviter autant que possible les outils métalliques pour déclipser la coque. L’écran E-Ink repose sur un substrat fragile et supporte mal la torsion.

## Carte rapide de l’opération

```text
      KOBO AURA HD
           |
           v
  +-------------------+
  |  cadre avant      |
  +-------------------+
           |
      déclipser
           v
  +-------------------+
  |  4 vis internes   |
  +-------------------+
           |
      les retirer
           v
  +-------------------+
  | écran + carte mère|
  +-------------------+
           |
     sortir du fond
           v
  +-------------------+
  | dos carte mère    |
  |                   |
  | [microSD système] | <--- celle qui nous intéresse
  +-------------------+
```

---

## 1. Retirer le cadre avant

Commencer dans un coin, de préférence avec un outil plastique fin, puis progresser lentement le long du bord. Il faut libérer les clips successivement au lieu de tirer brutalement sur le cadre.

```text
Vue de profil simplifiée

       cadre avant
   __________________
  /                  \
 /____________________\
   ^  ^  ^  ^  ^  ^
   |  |  |  |  |  |
      clips plastique

   +------------------+
   |  coque arrière   |
   +------------------+

Action :
  - soulever doucement le cadre ;
  - écarter légèrement la coque ;
  - avancer clip après clip.
```

![Cadre avant noir posé en diagonale au-dessus de la coque arrière ouverte de la Kobo Aura HD, montrant les deux éléments séparés.](images/disassembly/01-bezel-rear-shell.jpg)

*Cadre avant et coque arrière séparés.*

![Vue latérale rapprochée du cadre et de la coque arrière de la Kobo Aura HD, montrant la rangée de clips plastiques qui retiennent le cadre avant.](images/disassembly/02-bezel-clips.jpg)

*Détail des clips périphériques. Cette vue explique pourquoi il vaut mieux progresser clip par clip plutôt que tirer sur le cadre.*

Le wiki MobileRead indique **au moins six clips sur chaque grand côté** et du ruban adhésif double-face entre le cadre et l’écran. Le guide iFixit recommande de commencer au coin inférieur droit avec un spudger en plastique, puis de progresser le long du bas et autour de l’appareil.

**Sources :**

- iFixit — [Kobo Aura HD Screen Replacement](https://www.ifixit.com/Guide/Kobo+Aura+HD+Screen+Replacement/96135), étape 1 ;
- MobileRead Wiki — [Aura HD](https://wiki.mobileread.com/wiki/Aura_HD), section *Hacking* ;
- MobileRead Forum — [Aura HD Replacing internal SD card?](https://www.mobileread.com/forums/showthread.php?t=214272), retour de démontage détaillant les clips et l’adhésif.

### Ce que nous avons observé

Sur l’exemplaire démonté ici, le cadre et la coque se séparent bien par une succession de clips périphériques. La vue latérale ci-dessus permet d’en voir directement la forme et l’espacement.

---

## 2. Retirer les quatre vis qui maintiennent l’ensemble électronique

Une fois le cadre retiré, quatre vis situées vers les coins maintiennent l’ensemble **écran + carte mère** dans la coque arrière.

```text
Vue schématique

   o----------------------o
   |                      |
   |        écran         |
   |                      |
   |                      |
   o----------------------o

   o = vis à retirer
```

Le wiki MobileRead parle de vis **PH00**. Le guide iFixit utilise un tournevis **Phillips #000**. Ces désignations sont proches mais ne sont pas strictement identiques : utiliser un embout de précision qui remplit correctement l’empreinte, sans forcer.

**Sources :**

- iFixit — [Kobo Aura HD Screen Replacement](https://www.ifixit.com/Guide/Kobo+Aura+HD+Screen+Replacement/96135), étape 2 ;
- MobileRead Wiki — [Aura HD](https://wiki.mobileread.com/wiki/Aura_HD), section *Hacking*.

---

## 3. Sortir l’ensemble écran + carte mère de la coque arrière

Après retrait des quatre vis, l’ensemble électronique peut être séparé du fond de la coque.

Ne pas chercher à séparer l’écran de la carte mère pour accéder à la microSD : **ce n’est pas nécessaire**.

```text
          AVANT
     +-------------+
     | écran E-Ink |
     +-------------+
           ||
           || assemblage
           \/
     +-------------+
     | carte mère  |
     +-------------+
          ARRIÈRE
```

![Module écran E-Ink de la Kobo Aura HD vu de face après retrait de la coque.](images/disassembly/03-eink-panel.jpg)

*Module écran E-Ink sorti de la coque. La dalle doit être manipulée sans torsion.*

Le guide iFixit confirme qu’après retrait des quatre vis, l’ensemble écran/carte mère se retire de la plaque arrière.

**Source :**

- iFixit — [Kobo Aura HD Screen Replacement](https://www.ifixit.com/Guide/Kobo+Aura+HD+Screen+Replacement/96135), étape 2.

---

## 4. Déconnecter la batterie avant de manipuler la microSD

Cette précaution limite le risque de court-circuit ou de manipulation du stockage alors que la carte mère est encore alimentée.

Le connecteur de batterie se soulève **perpendiculairement à la carte mère**. Ne pas tirer sur les fils.

```text
          fils batterie
             ||
             ||
          [connecteur]
              ^
              |
       soulever verticalement

  ============================  carte mère
```

**Source :**

- iFixit — [Kobo Aura HD Screen Replacement](https://www.ifixit.com/Guide/Kobo+Aura+HD+Screen+Replacement/96135), étape 3.

---

## 5. Identifier la microSD système interne

C’est le point essentiel du démontage.

La Kobo Aura HD possède une **microSD amovible utilisée comme stockage système**. MobileRead la situe sur le **dos de la carte mère**, c’est-à-dire le côté opposé à l’écran.

```text
Dos de la carte mère — représentation fonctionnelle

+------------------------------------------------+
|                                                |
|  [ microSD SYSTÈME ]                           |
|       ^                                        |
|       |                                        |
|       +---- contient boot / rootfs / recovery  |
|                                                |
|                         [ batterie ]            |
|                                                |
|        électronique / CPU / RAM / contrôleurs  |
|                                                |
|                               [USB] [SD externe]|
+------------------------------------------------+
```

![Gros plan de la carte mère de la Kobo Aura HD avec la microSD système noire encore insérée dans son logement interne.](images/disassembly/04-internal-system-microsd.jpg)

*La microSD système encore en place sur la carte mère. C’est cette carte qu’il faut sauvegarder pour travailler sur le système interne.*

### Attention : il y a deux usages microSD différents

Ne pas confondre :

```text
MICROSD INTERNE SYSTÈME
    carte mère
       |
       +--> contient le système Kobo
       +--> rootfs / recoveryfs / KOBOeReader
       +--> doit être sauvegardée avant modification

MICROSD D’EXTENSION UTILISATEUR
    bord de la liseuse, près du connecteur USB
       |
       +--> stockage additionnel accessible normalement
       +--> ce n’est PAS la carte système
```

Cette distinction est visible directement sur l’exemplaire démonté ici.

**Sources :**

- MobileRead Wiki — [Aura HD](https://wiki.mobileread.com/wiki/Aura_HD) : « An internal SD card is on the back side of the board » ;
- MobileRead Forum — [Aura HD Accessible Internal uSD card](https://www.mobileread.com/forums/showthread.php?t=217702) ;
- MobileRead Forum — [Aura HD Replacing internal SD card?](https://www.mobileread.com/forums/showthread.php?t=214272).

---

## 6. Retirer la microSD système

Une fois la batterie déconnectée, retirer la microSD sans la tordre et sans exercer de force sur son logement.

![MicroSD système d’origine retirée de la Kobo Aura HD et posée sur une table en bois.](images/disassembly/05-original-microsd.jpg)

*MicroSD système d’origine après extraction.*

**Ne rien écrire dessus à ce stade.**

La première opération recommandée par ce projet est une **inspection en lecture seule**, puis une **sauvegarde complète** avant toute tentative de réparation.

Voir ensuite :

1. [Inspecter la microSD en lecture seule](inspect-aura-hd-fr.md)
2. [Retrouver les fichiers de recovery](retrouver-fichiers-fr.md)
3. [Vérifier `recoveryfs`](verify-recovery-fr.md)
4. [Comprendre la procédure de sauvetage](rescue-fr.md)

Un retour MobileRead de 2015 décrit explicitement la récupération des livres et du dossier `.kobo` après extraction de la microSD interne d’une Aura HD dont l’écran tactile était inutilisable.

**Source :**

- MobileRead Forum — [how to recover aura hd internal sd data on a broken screen?](https://www.mobileread.com/forums/showthread.php?t=266182).

---

## 7. Remontage et test du tactile

Le remontage s’effectue dans l’ordre inverse.

Il existe toutefois un piège important : **le tactile peut ne pas répondre lorsque le cadre avant n’est pas remis en place**. Ce comportement est documenté à la fois par iFixit et MobileRead.

Ne pas conclure trop vite à une panne du tactile en testant la liseuse complètement ouverte.

**Sources :**

- iFixit — [Kobo Aura HD Screen Replacement](https://www.ifixit.com/Guide/Kobo+Aura+HD+Screen+Replacement/96135), étape 10 ;
- MobileRead Wiki — [Aura HD](https://wiki.mobileread.com/wiki/Aura_HD), section *Hacking*.

---

## Version texte, Lynx et accessibilité

Ce document est conçu pour rester exploitable sans rendu graphique :

- chaque photographie possède un **texte alternatif descriptif** ;
- chaque information essentielle est répétée dans le texte adjacent ;
- les schémas importants existent en ASCII ;
- aucune étape ne dépend uniquement d’une flèche ou d’une annotation graphique ;
- une édition texte pur est disponible dans [`disassembly-lynx-fr.txt`](disassembly-lynx-fr.txt).

Un afficheur braille peut naturellement restituer le texte via son logiciel d’accès. Nous n’utilisons pas de pseudo-images en caractères braille Unicode : les caractères ASCII classiques sont plus robustes dans Lynx, SSH, consoles série et terminaux anciens.

---

## Sources et remerciements

Cette documentation ne revendique pas la découverte de la méthode de démontage de l’Aura HD.

Elle a été construite à partir :

- de notre démontage réel de la Kobo Aura HD utilisée par le projet ;
- du guide iFixit **Kobo Aura HD Screen Replacement** ;
- du **MobileRead Wiki — Aura HD** ;
- des retours historiques de la communauté MobileRead concernant l’ouverture et le remplacement de la microSD interne.

### Références principales

- iFixit — https://www.ifixit.com/Guide/Kobo+Aura+HD+Screen+Replacement/96135
- MobileRead Wiki — https://wiki.mobileread.com/wiki/Aura_HD
- MobileRead — https://www.mobileread.com/forums/showthread.php?t=214272
- MobileRead — https://www.mobileread.com/forums/showthread.php?t=217702
- MobileRead — https://www.mobileread.com/forums/showthread.php?t=266182

Le wiki MobileRead indique que sa page Aura HD a été modifiée par Dale DePriest et repose notamment sur le travail de Chris Ridd et d’un contributeur anonyme. Le contenu du wiki est publié sous licence **Creative Commons Attribution-NonCommercial-ShareAlike**.

Les photographies de ce guide proviennent de l’exemplaire démonté pour ce projet. Elles ne reprennent pas les photographies d’iFixit ou de MobileRead.
