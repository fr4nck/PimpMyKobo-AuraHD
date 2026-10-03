# FIRST BOOT #1 — protocole de qualification Aura HD E606C0

**Français** | [English](first-boot-qualification-en.md)

État : **protocole préparé, aucun essai réalisé**. Tous les tests matériels
ci-dessous sont **NOT TESTED**. Ce document n'autorise ni écriture microSD,
ni démarrage, ni restauration. P2/recoveryfs reste intouchable.

Périmètre : premier démarrage d'une P1 PMKB démarrant directement KOReader,
sans Nickel ni activation Kobo. Pas de veille, réseau, export USB/Calibre,
mise à jour MCU ou optimisation dans cette campagne.

## 0. Références figées et vocabulaire

- **A** : [audit matériel à `235085e`](https://github.com/fr4nck/PimpMyKobo-AuraHD/blob/235085ea27ff6680a03bf10e2798d7589f1c8f97/docs/offline-hardware-qualification-fr.md),
  sections E-Ink, Neonode, frontlight, recovery et watchdog. Preuves source,
  configuration du noyau sauvegardé et call-flows ; pas de qualification physique.
- **I** : intégration relue à
  [`a8ce226`](https://github.com/fr4nck/PimpMyKobo-AuraHD/tree/a8ce226bcd46483feb8e35e49f826fa076098bfb),
  notamment `experimental/offline-rootfs/etc/init.d/rcS`, `etc/inittab`,
  `usr/bin/pmkb-reader`, `pmkb-check-onboard`, `pmkb-check-offline`,
  `tools/preflight-koreader.py` et `docs/pmkb-first-boot-1-fr.md`.
  C'est une référence documentaire, pas une image autorisée. Figer le SHA
  complet réellement retenu après consolidation et revérifier les différences.
- **K/Q** : sources noyau Kobo et paquet KOReader exacts référencés et hachés
  dans A. Les lignes citées sont celles des fichiers internes des archives.
  L'identité de tout le binaire noyau avec ces sources n'est pas démontrée.

| Verdict | Signification | Conséquence |
| --- | --- | --- |
| PASS | Test exécuté, résultat attendu observé et preuves conservées | Autorise seulement la suite indiquée pour ce test |
| FAIL | Contradiction constatée, erreur ou résultat attendu non obtenu avec une observation fiable | Bloquer la dépendance concernée ; appliquer STOP si dangereux |
| UNQUALIFIED | Essai/indice disponible mais insuffisant : log absent, identité ambiguë, seuil ou mesure non établi | Jamais assimilé à PASS ; bloquer les dépendances essentielles |
| NOT TESTED | Aucun essai de ce test n'a été effectué | Ne donne aucune conclusion sur le matériel |

Un contrôle hors ligne PASS ne devient pas un PASS matériel. Un préflight
**sans FAIL n'est pas une autorisation d'écriture** : il peut contenir des
UNQUALIFIED logiciels applicables. Une fonctionnalité omise reste NOT TESTED,
pas « non nécessaire donc PASS ». Toute dérogation future doit être explicite,
motivée et enregistrée ; aucune n'est accordée ici.

## 1. Checklist préalable — avant une éventuelle autorisation d'écriture

Cocher dans l'ordre ; un point non établi bloque la demande de GO physique.

- [ ] **G01 — Figer le candidat** : commit complet, SHA-256 et taille de
  l'image FIRST BOOT, version/hash KOReader et runtime, manifeste de build,
  paramètres ext4. Relier l'arbre audité aux octets de cette image ; deux
  constructions avec les mêmes entrées ne prouvent pas seules cette identité.
- [ ] **G02 — Examiner les deux volets du préflight** : image (intégrité)
  et contenu extrait de cette même image (ARM, bibliothèques, bootstrap,
  permissions, stockage, réglages sans Nickel). Aucun FAIL ; chaque contrôle
  logiciel applicable doit être PASS ou son manque résolu avant le GO.
  Les contrôles matériels UNQUALIFIED sont précisément l'objet de l'essai futur.
  Les champs `physical_restore_eligible=false` et `hardware_qualified=false`
  du préflight ne sont pas à contourner. Ne pas réutiliser un contrat de
  restauration recovery pour autoriser implicitement une image expérimentale.
- [ ] **G03 — Identifier la cible du futur plan** : Aura HD/dragon/E606C0,
  HWCONFIG v1.7/39 octets/PCB 28, géométrie MBR réelle, taille et offset P1,
  compatibilité ext4 avec le noyau conservé. Aucun numéro de disque historique
  n'est une identité. Le fingerprint est une preuve de contenu, pas un CID.
- [ ] **G04 — Préserver les données** : sauvegarde privée vérifiée pré-P1,
  ancienne P1, P2 et P3/données utilisateur ; manifeste, tailles et SHA-256.
  Si des zones entre partitions ou après P3 ne sont pas sauvegardées, le
  déclarer ; ne pas prétendre disposer d'une image intégrale.
- [ ] **G05 — Qualifier le parachute sur copie** : P2/recoveryfs et ses
  archives vérifiées hors ligne. Conserver son hash de référence. Lire les
  scripts comme des données ; aucune exécution ni montage RW de P2.
- [ ] **G06 — Limiter le futur plan à P1** : plages exactes, marge/ext4,
  contrôle de tous les octets hors P1 dans une simulation locale, vérification
  prévue après copie. MBR, pré-P1, P2 et P3 hors cible. Privilégier une carte
  de travail préparée dans un lot séparément autorisé ; conserver l'originale.
- [ ] **G07 — État physique et alimentation** : carte installée et identifiée,
  connecteurs corrects, batterie sans anomalie, alimentation stable ; consigner
  durée de charge, câble et source. Aucun seuil de batterie « sûr » n'est
  démontré par A. Toute anomalie observable impose STOP, pas une charge forcée.
- [ ] **G08 — Observabilité et extraction des preuves** : définir avant POWER
  un canal utilisable dès l'init, et un moyen de sortir les logs volatils sans
  écrire sur P2/P3. La console série, son brochage/niveau électrique et sa
  disponibilité ne sont pas qualifiés ici. L'USB n'est pas une console prouvée.
  Ne pas ouvrir `/dev/watchdog` ni activer stockage USB pour obtenir des logs.
  Si aucun canal pré-UI n'est disponible, le diagnostic noyau/bootstrap sera
  UNQUALIFIED : résoudre ce manque ou obtenir une limitation explicitement
  acceptée lors du GO, jamais inventer des logs accessibles après un écran blanc.
- [ ] **G09 — Préparer le dossier d'essai privé** : identifiant, opérateur,
  date/heure, caméra/chronomètre, schéma de repérage du panneau, livre de test
  connu sans DRM, moyens de sauvegarder les preuves avant toute extinction.
- [ ] **G10 — Autorisation distincte** : faire approuver le candidat, la cible,
  les seules plages d'écriture, les inconnues, les conditions STOP et le retour
  arrière. Après la future écriture autorisée, exiger les hashes relus et la
  confirmation de P2/pré-P1/P3 inchangés avant tout GO de démarrage.

Preuves G01–G10 : rapports complets, plans et hashes dans le dossier privé.
**État présent : contrôles du candidat à renseigner, aucune écriture autorisée.**

## 2. Invariants de préservation

P2 n'est ni un emplacement de logs ni un environnement d'essai. Préserver ses
octets, sa géométrie et ses archives. Aucun replay de journal, fsck réparateur,
formatage, extraction sur place ou installation en P2. Conserver également
MBR, U-Boot, noyau, HWCONFIG et waveform de pré-P1, l'ancienne P1 et P3.

Dans I, P3 est prévue en FAT **ro** sur `/mnt/onboard` ; profil/réglages sont
volatils sous `/tmp/pmkb`. Un problème d'accès aux livres ne justifie jamais
un remount RW. La combinaison éclairage + alimentation de factory reset
n'est **pas** un redémarrage neutre ni notre retour arrière : les scripts P2
audités peuvent reformater P1/P3 et écrire U-Boot [A]. Ne pas la déclencher.

## 3. Ordre réel des dépendances

L'ordre observable dans I est : noyau → `rcS` → proc/sysfs/tmpfs/cold-plug →
garde réseau → nœuds attendus → montage P3 ro → `/run/pmkb-ready` →
`pmkb-reader` → profil temporaire → recheck P3 → `exec luajit reader.lua`.

Il faut donc prouver **P3 et le lancement logiciel avant de qualifier les
interactions graphiques**. L'ouverture evdev par KOReader active le Neonode ;
on ne peut pas exiger toutes les interactions tactiles avant cette ouverture.
Les tests E-Ink/tactile/frontlight ci-dessous utilisent ensuite le lecteur ou
un outil déjà validé pour le candidat. Aucun outil ni mire ne sont installés
par ce lot ; leur disponibilité est un prérequis à renseigner.

## 4. Dès POWER — observations et écran blanc

Filmer avant l'appui pour conserver l'état initial. T0 est l'action POWER
normale, sans bouton lumière. Consigner USB branché ou non et ne pas changer
cette condition au milieu d'un essai sans le noter.

| ID / test futur | Résultat attendu / décision | Preuve à conserver | Bloquant |
| --- | --- | --- | --- |
| B01 LED | Relever couleur, fixe/clignotant, extinction et durée ; aucun motif de succès n'est établi dans A/I. LED seule : UNQUALIFIED, jamais PASS de boot | Vidéo horodatée, temps des transitions et condition USB | Non pour la suite si aucune anomalie électrique ; oui pour toute conclusion tirée de la LED seule |
| B02 progression noyau/init | Identité du noyau attendu, init démarré, pas de panic/oops, boucle de reset ni erreurs critiques | Capture console si canal qualifié, `dmesg`, `/proc/version`, `/proc/cmdline`, uptime | Oui pour qualification du boot ; log inaccessible : UNQUALIFIED |
| B03 premier changement écran | Relever premier flash/contenu puis écran utilisable ; aucun logo Kobo/animation Nickel n'est requis | Vidéo T0→premier changement→première UI ; photo avant/après | Oui pour affichage ; absence de changement ne localise pas la panne |
| B04 durées des phases | Mesurer Tnoyau/Tinit/TP3/Texec/Tpremier-refresh/TUI et la stabilité ; durées typiques inconnues | Temps relatifs + timestamps noyau ; préciser résolution de mesure | Non comme seuil de performance ; blocage confirmé d'une phase bloque sa suite |

**Repères opérateur, pas temps de boot démontrés** : observer à environ
5, 15, 30, 60 et 120 secondes après T0, et dater chaque événement réel entre
ces repères. À 120 s sans progrès observable, suspendre la campagne et
collecter les preuves ; ce budget de diagnostic ne prouve pas une panne
électrique ni une durée limite constructeur. Pas de boucles d'allumage.

### Si l'écran reste blanc

1. Ne pas conclure « pas de système » ou « batterie vide » à partir de l'écran
   ou de la LED. Pas de factory reset, réécriture, waveform de substitution,
   écriture GPIO ou `neocmd` pour essayer.
2. Consigner LED, température observée sans instrument invasif, USB, temps et
   éventuel écran antérieur ; rechercher une progression par le canal qualifié.
3. Avec preuves noyau absentes : **UNQUALIFIED, stade de panne inconnu**.
   Avec noyau/init attestés : lire framebuffer/sysfs et état de P3/bootstrap.
4. `fb0` absent oriente vers probe/devnode ; `fb0` présent ne prouve pas
   `hw_ready`. Examiner HWCONFIG/waveform dans cmdline et erreurs EPDC.
5. P3 absente/montage refusé : lancement lecteur refusé attendu dans I ; pas de
   fallback graphique documenté. Marqueur ready présent mais processus absent :
   lire sortie du launcher, loader/Lua et recheck P3. Processus vivant mais blanc :
   qualifier géométrie et chaîne de refresh, sans incriminer le tactile.
6. Conserver les logs **avant** toute nouvelle manipulation. Si une écriture
   recovery semble en cours, ne pas couper aveuglément pour satisfaire un délai :
   arrêter les commandes supplémentaires et réévaluer la situation.

## 5. Montage P3 et lancement KOReader

| ID / test futur | Résultat attendu | Preuve/log | Bloquant |
| --- | --- | --- | --- |
| S01 provenance et montage | Entrée noyau pour la P3 identifiée, filesystem vfat, mountpoint exact `/mnt/onboard`, option ro, aucun montage P2 ; nœud bloc cohérent avec sysfs | `/proc/mounts`, `/proc/partitions`, sysfs bloc, géométrie/hashes privés | Oui ; simple répertoire existant ≠ montage, mauvais disque/RW/P2 touchée → STOP |
| S02 livres | Livre témoin attendu visible puis lisible dans le file manager ; pas une fausse bibliothèque de P1 sous le mountpoint | Liste du témoin (sans bibliothèque personnelle), photo UI, hash du témoin local | Oui pour qualification lecture ; tester après lancement, P3 réelle déjà PASS |
| S03 absence au boot | Dans un futur scénario séparément approuvé, absence de P3 bloque rcS avant ready ; lecteur non lancé, sans formatage/réparation [I] | Erreur mount/nœud, absence ready, état processus | Oui si lancement malgré absence ; scénario non provoqué ici, NOT TESTED |
| S04 perte avant exec | Une perte entre rcS et le recheck est refusée par `pmkb-check-onboard` | `/proc/mounts` capturé, échec du garde, absence du lecteur | Oui ; test futur contrôlé seulement, aucun démontage forcé ni retrait à chaud |
| S05 perte après exec | Comportement non établi : I n'a pas de surveillance continue et le garde ne contrôle que le mountpoint, pas sa source/type/ro | Logs et chronologie si incident spontané ; rapport du manque | UNQUALIFIED ; interdit de revendiquer résilience. Ne pas provoquer sur la carte au premier boot |
| K01 lancement direct | PRODUCT=dragon/PLATFORM=ntx508 ; LuaJIT et reader.lua prévus ; modèle dragon observé ; UI stable sans login/activation/retour Nickel | `/proc` du processus identifié, sortie launcher/KOReader, photo UI, versions | Oui ; crash/loader manquant/modèle différent → FAIL |
| K02 profil indépendant | Réglages démarrés sous HOME/XDG temporaires ; `KOBO_LIGHT_ON_START=-1` et synchronisation Nickel false dans le candidat [I] | Rapport statique du profil + fichiers réellement présents, logs d'erreur éventuels | Oui ; présence d'un module de compatibilité n'est pas une preuve d'accès Nickel |
| K03 première lecture | Ouvrir le témoin puis tourner 3 pages et revenir ; UI ne disparaît pas, pas de crash | Photos, stdout/stderr, temps/erreurs, nom neutre du témoin | Oui pour qualifier le lecteur ; ne prouve pas stabilité longue durée |

Pour K01, consigner l'environnement du **processus** plutôt que celui d'un
shell de diagnostic différent. Un écran Kobo ancien peut être une image
résiduelle : photo seule insuffisante pour identifier le processus courant.

## 6. Qualification E-Ink

Condition : S01/K01 et accès d'observation disponibles. Ne pas écrire des
octets bruts dans fb0, lancer des ioctls arbitraires ou installer une waveform.

| ID / test futur | Résultat attendu | Preuve/log | Bloquant |
| --- | --- | --- | --- |
| E01 framebuffer | fb0 caractère lié à son sysfs ; mode FBIO réellement relevé, profondeur/stride/mémoire/dimensions cohérents ; panneau 1080×1440 physique [A] | sysfs fb0/dev,bits_per_pixel,rotate ; FBIO et outil/version si disponible ; dmesg | Oui pour refresh. Mode réel 8/16 bpp et rotation init non qualifiés ; ne pas imposer 0 ou 8 par supposition |
| E02 orientation | Mire/texte asymétrique lisible, coins repérés, haut physique/haut UI concordants ; rotation logicielle explicitée | Photo quatre coins et relevés avant/après éventuelle préparation déjà validée | Oui pour tactile/lecture ; dimensions échangées selon rotation ≠ panne en soi |
| E03 full refresh | Action full connue du lecteur/outillage validé ; zone entière renouvelée, résultat final attendu ; absence erreur SEND/WAIT | Photos avant/après, vidéo, action exacte, logs/retour de marqueur si exposé | Oui pour qualification E-Ink. Un flash noir seul ne prouve pas fin de refresh ; retour ioctl seul ne prouve pas résultat visuel |
| E04 partial refresh | Mettre à jour une petite zone contrôlée ; résultat local correct, pas de dommage hors zone ni erreur ; action réellement partial attestée | Région/coordonnées, photos avant/après, logs mode/région/marker si disponibles | Oui pour PASS partial ; full fallback automatique → UNQUALIFIED partial, pas PASS. Lecture full-only peut continuer diagnostiquement |
| E05 ghosting | Après 5 changements contrôlés, relever traces ; full refresh restitue le motif témoin sans résidu gênant observé | Photos exposition/éclairage constants à changements 0/1/5 puis full | Résidu persistant après full → FAIL affichage ; traces en partial documentées. Seuil quantitatif constructeur inconnu, appréciation qualitative seulement |

L'ABI de 68 octets, SEND_UPDATE `0x4044462e` et WAIT `0x4004462f`
est vérifiée hors matériel [A] ; cela n'autorise pas un nouvel appel ioctl.
La préparation `fbdepth` du lanceur amont n'est pas automatiquement celle de
FIRST BOOT : relever ce que le candidat fait réellement, avant et après.

## 7. Qualification Neonode v2 / IR

Condition : géométrie E01/E02 connue. Ouvrir evdev est une **action matérielle**
qui active le contrôleur [A], pas une lecture neutre de fichier ; uniquement
dans la campagne future autorisée. Pas de programmation BSL/MASS_ERASE,
écriture `neocmd`, bus I²C ou calibration conjecturale.

| ID / test futur | Résultat attendu | Preuve/log | Bloquant |
| --- | --- | --- | --- |
| N01 détection | Identifier l'eventN nommé `zForce-ir-touch`, capacités ABS_X/Y/PRESSURE, BTN_TOUCH ; client I²C attendu 0-0050 | `/proc/bus/input/devices`, sysfs name/dev, lien I²C, dmesg | Oui pour interaction ; event0/event1 seuls ne prouvent pas l'identité |
| N02 acquisition | Un appui/relâchement produit les événements attendus, sans flot permanent de contacts fantômes | Trace evdev datée obtenue par outil validé, position physique de l'appui | Oui pour interaction. Trace indisponible mais clic UI visible → raw UNQUALIFIED |
| N03 axes/orientation | Mouvement physique droite/bas correspond à droite/bas UI après transformations dragon ; pas miroir ni permutation restante | Trace brute + coordonnées UI + photo du repère | Oui pour navigation fiable ; bornes ABS annoncées seules ≠ calibration |
| N04 zones écran | Tester centre, quatre coins légèrement en retrait, milieux des quatre bords : 3 appuis par zone, relâchement et cible obtenue | Grille 3×3, positions, coordonnées brutes/UI, réussites/ratés, photos | Oui pour PASS tactile global ; zone manquée → FAIL concerné, pas qualification partielle silencieuse |

Consigner dimensions UI, marge du bord et taille des cibles. A ne fournit ni
tolérance en pixels ni exigence de multitouch ; aucun seuil de précision ou
nombre de contacts n'est inventé. La grille est un test fonctionnel proposé,
pas une calibration firmware.

## 8. Qualification frontlight et bouton lumière

Condition : UI stable et commande frontlight disponible, alimentation sans
anomalie. La LED de signalisation n'est pas le frontlight. Ne pas écrire
`pmic_light.1/lit`, GPIO ou un prétendu `backlight/brightness` pour le régler.

| ID / test futur | Résultat attendu | Preuve/log | Bloquant |
| --- | --- | --- | --- |
| F01 chaîne NTX | ntx_io caractère cohérent avec `/sys/class/misc/ntx_io/dev`, probe PMIC/MSP430 et pas d'erreur critique | sysfs/devnode, dmesg, source candidate | Oui pour essais lumière ; minor 190 documenté, pas permis de fabriquer le nœud par supposition |
| F02 extinction | Demander 0 via interface déjà validée ; éclairage du panneau effectivement éteint après stabilisation | Niveau demandé, temps de stabilisation observé, photo dans conditions fixes | Oui pour sécurité/contrôle ; échec → pas de montée en puissance |
| F03 gradation | Progression proposée 1→10→30→60→100→0 via UI, une valeur à la fois ; variations visibles et stables, retour 0 effectif | Valeurs demandées, photos sans auto-exposition variable, erreurs et temps | Oui pour PASS frontlight. 100 est borne logicielle [A], pas un niveau sûr thermiquement prouvé ; interrompre avant si anomalie |
| F04 bouton lumière | Si event et liaison au lecteur existent : appui seul produit l'effet annoncé dans le candidat, sans reset | Identité input/bouton, événement brut, niveau avant/après, photo | Non pour diagnostics lecteur si UI lumière fonctionne ; obligatoire pour revendiquer bouton qualifié. Mapping inconnu → UNQUALIFIED, pas combinaison POWER |

L'ioctl 241 attend un entier 0–100 [A], pas un pointeur. Aucun programme
ioctl n'est fourni. Un retour réussi peut masquer l'absence du client MSP430 :
la preuve lumineuse reste indispensable. Les valeurs proposées ne sont pas
des mesures de lux ni une échelle linéaire supposée.

## 9. Logs, interfaces précises et conservation des preuves

Sources A et I sont distinguées : **identifié dans la source** n'est pas
« présent sur la vraie machine ». Conserver les sorties complètes ; les mots
de recherche ci-dessous ne remplacent pas une capture noyau intégrale.

| Observation | Chemin/identifiant établi | Ce qu'il prouve / limite |
| --- | --- | --- |
| Noyau/boot | `/proc/version`, `/proc/cmdline`, `/proc/uptime`, ring buffer `dmesg` | Version/arguments/chronologie si accessible ; noyau préservé de A : `2.6.35.3-850-gbc67621+`, pas un contrat pour un noyau remplacé |
| Waveform/HWCONFIG | Arguments `waveform_p`, `waveform_sz`, `hwcfg_p`, `hwcfg_sz` [A] | Passage RAM attendu ; leur présence ne démontre pas l'intégrité runtime ni panneau prêt |
| E-Ink | `/dev/fb0`, `/sys/class/graphics/fb0/{dev,rotate,bits_per_pixel}` [A] | `hw_ready` est un état interne source, **pas** un sysfs démontré ; vérifier FBIO avec un outil disponible et qualifié |
| Neonode | `/proc/bus/input/devices`, `/sys/class/input/eventN/device/name`, `/sys/class/input/eventN/dev`, `/dev/input/eventN` [A] | Nom input `zForce-ir-touch` ; board name `zforce-ir-touch`, casse distincte. Chemin client I²C attendu `0-0050`, ne pas forcer une ouverture |
| Frontlight | `/sys/class/misc/ntx_io/dev`, `/dev/ntx_io` [A] | Identité de nœud ; transport MSP430 vérifiable par probe/logs, visibilité effective encore inconnue |
| LED | Référence `pmic_light.1/lit` dans recovery [A] | LED de signalisation uniquement ; chemin absolu sysfs et motif du candidat non qualifiés |
| Batterie | `/sys/class/power_supply/mc13892_bat/{capacity,status}` dans l'audit initial [A] | Chemin hérité candidat, présence/précision matérielles UNQUALIFIED ; ne pas inventer un % fiable |
| Bootstrap | `/run/pmkb-ready`, `/proc/mounts`, source `rcS`/`pmkb-reader` [I] | Ready atteste un passage, pas le montage actuel ni la vie du lecteur ; `/run` est volatile |
| Profil | HOME `/tmp/pmkb`, XDG config/data/cache sous ce répertoire, KO_MULTIUSER=1 [I] | Paramètres exportés, pas preuve que tous les logs résident ici ; fichiers à inventorier réellement |
| Processus | PID reader/LuaJIT identifié, `/proc/PID/{cmdline,environ,status}`, stdout/stderr | Après exec PID/nom peut varier selon lancement ; préserver uniquement données nécessaires, pas tout l'environnement privé |

### Messages noyau : ne pas inventer de signatures de réussite

A identifie les fichiers et fonctions exacts :

- `drivers/video/mxc/mxc_epdc_fb.c` : `epdc_firmware_func`,
  `mxc_epdc_fb_init_hw`, handler d'initialisation et traitement SEND/WAIT ;
  `mxc_epdc_fake_s1d13522.c` : branche `FW_IN_RAM`/données Netronix.
- `drivers/input/touchscreen/zforce_i2c.c` : probe, open, réponses des commandes
  v2 ; le nom input est établi, mais une chaîne imprimée « BootComplete »
  avec casse/texte garantis n'est pas reproduite dans A.
- `mx50_ntx_io.c` et pilote PMIC/MSP430 cités par A :
  misc_register, transport, table lumineuse ; les chemins complets de certains
  fichiers doivent être confirmés dans l'archive avant citation d'une ligne.
- `drivers/watchdog/mxc_wdt.c` : activation à l'ouverture ; ne pas le tester
  par une ouverture pour chercher un message.

Pistes de recherche dans les logs : EPDC, waveform, HWCONFIG, zforce/Neonode,
input, I²C, MSP430, ntx_io, MMC, VFS/ext4, FAT, panic/oops et erreurs du loader.
**Ce sont des mots de tri, pas des messages littéraux garantis**. Les audits
disponibles n'établissent pas une liste exacte de printk de réussite. Aucun
message absent n'est un FAIL automatique : niveau de log/configuration peuvent
changer. Conserver d'abord le ring buffer complet et les retours système.

### Où récupérer les logs ?

I ne lance pas de syslogd/klogd, ne redirige pas explicitement le lecteur vers
un fichier et n'offre pas de console shell/USB/série qualifiée. `/var/log/messages`,
`crash.log`, pstore/ramoops ou un fichier `/run/pmkb-boot.log` **ne sont pas
des sorties garanties**. Les rechercher uniquement s'ils sont démontrés dans
le candidat, avec leur chemin réel. Une voie de collecte reste à préparer par
le chantier bootstrap si nécessaire ; ce protocole ne l'ajoute pas.

Après **chaque ID**, conserver : verdict, résultat attendu/obtenu, heure relative,
photo/vidéo, delta dmesg + capture complète, sortie outil/version/retour si utilisé,
état mount/processus pertinent. Si une preuve n'est pas accessible, le noter
explicitement, sans la reconstituer de mémoire comme un log.

Les logs en RAM sont perdus à l'arrêt ; prévoir leur export vers le PC via
un canal séparément qualifié **avant** redémarrage. Ne pas utiliser P2 ni P3
comme destination de secours. Le manifeste de preuves sur le PC peut contenir
SHA-256, tailles et chemins relatifs des captures ; garder serials, livres,
bases Kobo, fichiers `device.xml`, `.kobo.zip` et autres données personnelles
hors du dépôt. Ces fichiers utilisateur ne prouvent pas un boot PMKB réussi.

## 10. STOP immédiat et dépendances bloquées

- Chauffe anormale, odeur, gonflement, fumée, alimentation/connectique instable :
  arrêter l'essai et mettre le matériel en sécurité ; ne pas poursuivre pour finir
  les logs. L'intervention électrique dépend de la situation, pas d'un script.
- Écriture/montage RW de P2, écriture pré-P1/MBR inattendue, reset usine,
  formatage/fsck réparateur, identité de carte ou plage douteuse : arrêter les
  commandes supplémentaires, préserver preuves et données ; aucune restauration
  automatique. Ne pas arracher la carte pendant une opération active.
- P3 RW/mauvaise source, ouverture watchdog non prévue, activité réseau/export
  USB ou programmation Neonode/MCU non autorisée : arrêter la suite du protocole.
- Panic/oops, resets en boucle, erreur MMC critique, refresh qui ne termine pas,
  lumière impossible à éteindre : STOP de la campagne, collecter sans nouvelle
  sollicitation du composant défaillant si cela reste sûr.
- Observation essentielle impossible, image/hash/préflight non reliés ou canal
  de logs non défini : STOP de qualification avec UNQUALIFIED ; ce n'est pas
  forcément une panne matérielle ni une consigne de coupure immédiate.

**STOP signifie cesser les nouvelles actions du test**, pas exécuter un factory
reset, un reboot forcé ou une restauration. Hors danger électrique immédiat,
préserver les logs et déterminer si une écriture est en cours avant extinction.

## 11. Retour arrière conceptuel avec P2 — non exécutable, non autorisé

1. Arrêter la campagne, sauver les preuves volatiles si possible et dater l'état.
2. Vérifier hors ligne la copie P2 et son hash de référence ; contrôler ce qui a
   réellement changé, sans toucher à la recovery. P2 corrompue/inconnue → STOP.
3. Option de référence : retour à la carte originale conservée, seulement dans
   une future intervention autorisée et alimentation mise en état sûr. Ce n'est
   pas une restauration garantie si l'originale ne démarrait déjà pas.
4. Si reconstruction nécessaire : utiliser **la copie locale vérifiée de P2**
   comme source des archives recovery pour reconstruire une P1 Kobo de secours
   dans un fichier local. Cela abandonne temporairement l'UI PMKB, pas P2.
   Vérifier archives, géométrie, filesystem, provenance et hashes hors ligne.
5. Préparer ensuite un plan séparé limité à P1, simulation, identification actuelle,
   sauvegarde de l'état d'échec et contrôle de conservation pré-P1/P2/P3. Faire
   approuver spécifiquement cette restauration avant toute écriture.
6. Après cette future opération seulement : relire hashes et qualifier séparément
   le boot de secours. Aucune promesse de réussite matérielle depuis un SHA seul.

**Ne pas exécuter l'init de P2 ni déclencher son reset usine** : il peut écrire
P1/P3/U-Boot [A]. P2 fournit les données de secours ; sa présence n'est pas
une autorisation d'activer son mécanisme destructif. Aucune commande de retour
arrière physique n'est fournie dans ce protocole.

## 12. Fiche à remplir lors de la campagne future

| Champ | Valeur à renseigner |
| --- | --- |
| Essai / opérateur / date / condition USB | — |
| Commit candidat complet / image SHA-256 / taille | — |
| Rapports image + contenu reliés / sauvegarde / plan / autorisations | — |
| Pré-P1 / P2 / P3 hashes avant et après opération autorisée | — |
| Canal de capture / extraction des logs / outil mires-événements | — |
| Repères 5/15/30/60/120 s et phases réellement observées | — |
| Chaque ID : verdict / résultat / preuves / décision de suite | NOT TESTED tant que non exécuté |
| STOP / inconnues / dernier stade prouvé / retour arrière demandé | — |

Conclusion permise : « candidat X, étapes Y PASS avec preuves Z, étapes restantes
UNQUALIFIED/NOT TESTED ». Pas « matériel qualifié » si un contrôle essentiel
reste sans preuve. USB/Calibre, veille/réveil, autonomie, persistance, performance
et robustesse de perte P3 après exec restent hors de ce premier jalon.
