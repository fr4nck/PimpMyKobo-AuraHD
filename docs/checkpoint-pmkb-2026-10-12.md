# PMKB — checkpoint du 12 octobre 2026

Session Windows PowerShell + Debian 13 WSL2, sans Work/Codex. **Bilan : image virtuelle 14 Gio assemblée, contrôles structurels PASS, démarrage matériel NON qualifié.** Aucune écriture sur microSD, aucune restauration physique autorisée.

## Traces locales

- Dépôt local : `/home/Deniel/pmkb-test`, `git status --short` propre au dernier contrôle.
- Pré-P1 historique : `/mnt/c/Users/Ordi/AuraHD-original-boot.bin`, 9961472 octets, SHA256 `4b0c72f9d38a2d81d4d5ffb316b1b0d1efcb8e4bf0fa8610025e75fef837c2b6`.
- P2 historique : `/mnt/c/Users/Ordi/AuraHD-p2-recovery.img`, 268435968 octets, SHA256 `fe7885d391a5627cf2b04bd75518cf8fb5b0f379b29032727adb29cba35b968a`.
- Import historique : `/mnt/c/Users/Ordi/AuraHD-legacy-import.json`, `qualified`, `qualified_for_rebuild=true`, provenance déclarée uniquement, restauration physique interdite.
- P1 Kobo reconstruite : `/home/Deniel/pmkb-output/AuraHD-rootfs-rebuilt.img`, 268435968 octets, SHA256 `9e1a9f6035fa1953125ba2d36f7617424eccc6b4b84673d1c3d0038406c3ad86`. Rapport voisin `.rebuild.json` : `ok`, `complete=true`, `e2fsck clean`, 2529/2529 métadonnées, 1753/1753 contenus, 1751/1751 MD5.
- P1 PMKB FIRST BOOT retenue, **différente** de la P1 Kobo : `private/koreader-real-build-2026-10-03/PMKB-FIRST-BOOT-1-0b00d858.img`, 268435968 octets, SHA256 `7980fec15cb62ca3c2cabcb64cbbb683446fbf64070d75b45acf9a5e99e0f67c`, ext4 rootfs déclaré clean.
- Image disque virtuelle : `/home/Deniel/pmkb-output/PMKB-FIRST-BOOT-1-test16g-14GiB.img` ; rapport `.local.json`. Taille logique 15032385536 octets (14 Gio). Constituée de pré-P1 modifiée **seulement sur les 4 octets de longueur MBR P3**, P1 PMKB, P2 recovery, P3 FAT32 neuve et vide. Les SHA P1 et P2 ont été revérifiés dans l'image locale. Le SHA du pré-P1 intérieur n'est donc pas égal à celui du pré-P1 historique complet.
- Outil local : `dosfstools` Debian, `mkfs.fat` 4.2. Script d'assemblage ad hoc **non versionné** (variable `$script` PowerShell dans la session) ; à industrialiser dans un changement séparé si souhaité.

## Géométrie observée et contrôles

MBR secteurs de 512 octets : P1 type 83 LBA 19456 / 524289 secteurs ; P2 type 83 LBA 543745 / 524289 secteurs ; P3 type 0b LBA 1068034 / 28292094 secteurs. Fin P3 = fin de l'image au secteur 29360128.

FAT32 BPB : 28292040 secteurs ; 54 secteurs (27648 octets) inutilisés à la fin de la partition MBR, sans débordement. Taille cluster 8 secteurs, réservés 32, 2 FAT de 27576 secteurs, hidden sectors 1068034. Label `KOBOeReader`.

Dernière sortie réelle : **MBR PASS ; Limites P3 PASS ; Geometrie FAT32 PASS ; FSInfo PASS ; Boot secondaire PASS ; Tables FAT PASS ; VALIDATION STRUCTURELLE PASS ; QUALIFICATION MATERIELLE EN ATTENTE**. La comparaison des FAT n'a porté que sur leurs 4096 premiers octets : pas une vérification intégrale de la FAT32 ni un essai de boot.

## Limites, sécurité et reprise

- Aucun lecteur microSD branché : Windows ne détectait que le SSD Crucial T500. La capacité réelle de la carte 16 Go reste inconnue.
- Les images sont locales et privées ; ne jamais les committer dans Git.
- Aucune écriture autorisée sur la carte d'origine. La construction locale n'autorise **aucun flash** de carte test non plus sans procédure et autorisation explicites.
- À la reprise : relire ce checkpoint, vérifier les fichiers/hashes et la capacité cible, effectuer qualification FAT32 plus complète et SHA intégral de l'image 14 Gio, préparer sauvegarde/rollback et essai matériel séparé (écran, tactile, éclairage, boot, USB, P3). Ne pas refaire les qualifications déjà passées sans fait nouveau.
