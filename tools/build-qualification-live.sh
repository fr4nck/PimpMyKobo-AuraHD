#!/bin/sh
set -eu

usage() {
    cat <<'EOF'
Usage: sudo tools/build-qualification-live.sh CANDIDATE_IMG [OUTPUT_DIR]

Builds a local Debian Live ISO dedicated to PMKB Aura HD FIRST BOOT #1.
The candidate image is embedded locally in the ISO and is never uploaded.
Required host packages: live-build, xorriso, squashfs-tools, rsync, python3.
EOF
}

[ $# -ge 1 ] && [ $# -le 2 ] || { usage >&2; exit 2; }

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
CANDIDATE=$(readlink -f "$1")
OUTPUT_DIR=${2:-"$REPO_DIR/private/qualification-usb"}
OUTPUT_DIR=$(mkdir -p "$OUTPUT_DIR" && readlink -f "$OUTPUT_DIR")
MANIFEST="$REPO_DIR/live/pmkb-qualification/candidate.json"
TOOL="$REPO_DIR/tools/pmkb-qualification-usb.py"
SERVICE="$REPO_DIR/live/pmkb-qualification/pmkb-qualification.service"
LOGO="$REPO_DIR/assets/branding/pmkb-logo-original.png"
EXPECTED_SIZE=268435968
EXPECTED_SHA=7980fec15cb62ca3c2cabcb64cbbb683446fbf64070d75b45acf9a5e99e0f67c
IMAGE_NAME=PMKB-FIRST-BOOT-1-0b00d858.img

[ "$(id -u)" -eq 0 ] || { echo "STOP: lancez ce builder avec sudo." >&2; exit 2; }
for tool in lb sha256sum stat rsync python3; do
    command -v "$tool" >/dev/null 2>&1 || { echo "STOP: outil requis absent: $tool" >&2; exit 2; }
done
[ -f "$CANDIDATE" ] || { echo "STOP: candidat absent: $CANDIDATE" >&2; exit 2; }
[ -f "$MANIFEST" ] && [ -f "$TOOL" ] && [ -f "$SERVICE" ] || { echo "STOP: fichiers PMKB incomplets" >&2; exit 2; }

SIZE=$(stat -c %s "$CANDIDATE")
[ "$SIZE" = "$EXPECTED_SIZE" ] || { echo "STOP: taille candidat $SIZE != $EXPECTED_SIZE" >&2; exit 2; }
SHA=$(sha256sum "$CANDIDATE" | awk '{print $1}')
[ "$SHA" = "$EXPECTED_SHA" ] || { echo "STOP: SHA candidat $SHA != $EXPECTED_SHA" >&2; exit 2; }

WORK=$(mktemp -d /tmp/pmkb-live-build.XXXXXX)
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT INT TERM
cd "$WORK"

lb config \
  --mode debian \
  --distribution trixie \
  --architectures amd64 \
  --binary-images iso-hybrid \
  --debian-installer none \
  --archive-areas "main" \
  --apt-recommends false \
  --bootappend-live "boot=live components hostname=pmkb-qualification"

mkdir -p config/package-lists
cat > config/package-lists/pmkb.list.chroot <<'EOF'
python3
util-linux
fdisk
coreutils
e2fsprogs
parted
udev
systemd-sysv
ca-certificates
EOF

mkdir -p \
  config/includes.chroot/usr/local/sbin \
  config/includes.chroot/opt/pmkb/branding \
  config/includes.chroot/etc/systemd/system \
  config/includes.chroot/etc/systemd/system/multi-user.target.wants

install -m 0755 "$TOOL" config/includes.chroot/usr/local/sbin/pmkb-qualification
install -m 0644 "$MANIFEST" config/includes.chroot/opt/pmkb/candidate.json
install -m 0644 "$CANDIDATE" "config/includes.chroot/opt/pmkb/$IMAGE_NAME"
install -m 0644 "$SERVICE" config/includes.chroot/etc/systemd/system/pmkb-qualification.service
ln -s /etc/systemd/system/pmkb-qualification.service \
  config/includes.chroot/etc/systemd/system/multi-user.target.wants/pmkb-qualification.service
ln -s /dev/null config/includes.chroot/etc/systemd/system/getty@tty1.service
if [ -f "$LOGO" ]; then
    install -m 0644 "$LOGO" config/includes.chroot/opt/pmkb/branding/pmkb-logo-original.png
fi

cat > config/includes.chroot/opt/pmkb/BUILD-IDENTITY.txt <<EOF
PMKB Qualification USB
HEAD=0b00d858e26c8c65c5764ef939052704350eaaa9
IMAGE=$IMAGE_NAME
IMAGE_SIZE=$EXPECTED_SIZE
IMAGE_SHA256=$EXPECTED_SHA
EOF

lb build
ISO=$(find . -maxdepth 1 -type f \( -name 'live-image-*.hybrid.iso' -o -name 'live-image-*.iso' \) | head -n 1)
[ -n "$ISO" ] && [ -f "$ISO" ] || { echo "STOP: ISO live-build introuvable" >&2; exit 2; }
OUT="$OUTPUT_DIR/PMKB-Qualification-USB-0b00d858.iso"
cp "$ISO" "$OUT"
sha256sum "$OUT" > "$OUT.sha256"

printf '\nOK — ISO créé localement, aucune microSD touchée:\n%s\n' "$OUT"
cat "$OUT.sha256"
