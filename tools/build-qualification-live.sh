#!/bin/sh
set -eu

usage() {
    cat <<'EOF'
Usage:
  sudo tools/build-qualification-live.sh CANDIDATE_IMG RESTORE_PLAN [OUTPUT_DIR] [MANIFEST]

Builds a Debian Live ISO dedicated to the reviewed PMKB FIRST BOOT candidate.
The candidate and reviewed restore plan are embedded locally and never uploaded.

RESTORE_PLAN must be a plan produced by prepare-p1-restore.py. Its exact SHA-256
is sealed into the Live image. The physical target is still requalified at
runtime by restore-p1-linux.py before any write.

Optional MANIFEST defaults to live/pmkb-qualification/candidate.json.
Required host packages: live-build, xorriso, squashfs-tools, python3.
EOF
}

[ $# -ge 2 ] && [ $# -le 4 ] || { usage >&2; exit 2; }

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
CANDIDATE=$(readlink -f "$1")
PLAN=$(readlink -f "$2")
OUTPUT_DIR=${3:-"$REPO_DIR/private/qualification-usb"}
OUTPUT_DIR=$(mkdir -p "$OUTPUT_DIR" && readlink -f "$OUTPUT_DIR")
MANIFEST=${4:-"$REPO_DIR/live/pmkb-qualification/candidate.json"}
MANIFEST=$(readlink -f "$MANIFEST")

UI="$REPO_DIR/tools/pmkb-qualification-usb.py"
BACKEND="$REPO_DIR/tools/restore-p1-linux.py"
PREPARE="$REPO_DIR/tools/prepare-p1-restore.py"
SIMULATION="$REPO_DIR/tools/restore-rootfs.py"
REBUILD="$REPO_DIR/tools/rebuild-rootfs.py"
LEGACY="$REPO_DIR/tools/import-legacy-backup.py"
INSPECTOR="$REPO_DIR/tools/inspect-aura-hd.py"
SERVICE="$REPO_DIR/live/pmkb-qualification/pmkb-qualification.service"
LOGO="$REPO_DIR/assets/branding/pmkb-logo-original.png"

[ "$(id -u)" -eq 0 ] || { echo "STOP: lancez ce builder avec sudo." >&2; exit 2; }
for tool in lb xorriso mksquashfs sha256sum stat python3; do
    command -v "$tool" >/dev/null 2>&1 || { echo "STOP: outil requis absent: $tool" >&2; exit 2; }
done
for file in "$CANDIDATE" "$PLAN" "$MANIFEST" "$UI" "$BACKEND" "$PREPARE" "$SIMULATION" "$REBUILD" "$LEGACY" "$INSPECTOR" "$SERVICE"; do
    [ -f "$file" ] || { echo "STOP: fichier PMKB absent: $file" >&2; exit 2; }
done

IMAGE_NAME=$(python3 - "$MANIFEST" <<'PY'
import json, sys
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
name = data.get("image_name")
if not isinstance(name, str) or not name or Path(name).name != name:
    raise SystemExit("manifest image_name invalide")
print(name)
PY
)
HEAD=$(python3 - "$MANIFEST" <<'PY'
import json, sys
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
head = data.get("head")
if not isinstance(head, str) or not head:
    raise SystemExit("manifest head invalide")
print(head)
PY
)
EXPECTED_SIZE=$(python3 - "$MANIFEST" <<'PY'
import json, sys
from pathlib import Path
print(int(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["image_size"]))
PY
)
EXPECTED_SHA=$(python3 - "$MANIFEST" <<'PY'
import json, sys
from pathlib import Path
print(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["image_sha256"])
PY
)

SIZE=$(stat -c %s "$CANDIDATE")
[ "$SIZE" = "$EXPECTED_SIZE" ] || { echo "STOP: taille candidat $SIZE != $EXPECTED_SIZE" >&2; exit 2; }
SHA=$(sha256sum "$CANDIDATE" | awk '{print $1}')
[ "$SHA" = "$EXPECTED_SHA" ] || { echo "STOP: SHA candidat $SHA != $EXPECTED_SHA" >&2; exit 2; }

PLAN_SHA=$(sha256sum "$PLAN" | awk '{print $1}')
MANIFEST_SHA=$(sha256sum "$MANIFEST" | awk '{print $1}')

python3 - "$BACKEND" "$PLAN" "$CANDIDATE" "$PLAN_SHA" "$MANIFEST" <<'PY'
import importlib.util
import json
import sys
from pathlib import Path

backend_path = Path(sys.argv[1])
plan_path = Path(sys.argv[2])
candidate_path = Path(sys.argv[3])
plan_sha = sys.argv[4]
manifest_path = Path(sys.argv[5])

spec = importlib.util.spec_from_file_location("pmkb_restore_backend_build", backend_path)
if spec is None or spec.loader is None:
    raise SystemExit("backend PMKB non chargeable")
backend = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = backend
spec.loader.exec_module(backend)

plan, actual_sha = backend.validate_sealed_plan(plan_path, candidate_path, plan_sha)
if actual_sha != plan_sha:
    raise SystemExit("plan SHA incohérent")

manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
p1 = next((p for p in manifest["partitions"] if int(p["number"]) == 1), None)
p2 = next((p for p in manifest["partitions"] if int(p["number"]) == 2), None)
if p1 is None or p2 is None:
    raise SystemExit("manifest sans P1/P2")
if (
    plan["disk_size"] != int(manifest["disk"]["size"])
    or plan["p1_offset"] != int(p1["offset"])
    or plan["p1_size"] != int(p1["size"])
    or plan["replacement_sha256"] != manifest["image_sha256"]
    or plan["preserved_sha256"]["pre_p1"] != manifest["pre_p1"]["sha256"]
    or plan["preserved_sha256"]["p2"] != p2.get("sha256")
):
    raise SystemExit("STOP: plan scellé et manifest Aura HD divergent")
PY

SHORT=$(printf '%s' "$HEAD" | cut -c1-8 | tr -cd 'A-Za-z0-9._-')
[ -n "$SHORT" ] || { echo "STOP: identifiant HEAD inutilisable" >&2; exit 2; }

WORK=$(mktemp -d /tmp/pmkb-live-build.XXXXXX)
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT INT TERM
cd "$WORK"

lb config \
  --mode debian \
  --distribution bookworm \
  --architectures amd64 \
  --linux-flavours amd64 \
  --binary-images iso-hybrid \
  --debian-installer none \
  --archive-areas "main" \
  --security false \
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
  config/includes.chroot/opt/pmkb/tools \
  config/includes.chroot/opt/pmkb/branding \
  config/includes.chroot/etc/systemd/system \
  config/includes.chroot/etc/systemd/system/multi-user.target.wants

install -m 0755 "$UI" config/includes.chroot/usr/local/sbin/pmkb-qualification
install -m 0644 "$BACKEND" config/includes.chroot/opt/pmkb/tools/restore-p1-linux.py
install -m 0644 "$PREPARE" config/includes.chroot/opt/pmkb/tools/prepare-p1-restore.py
install -m 0644 "$SIMULATION" config/includes.chroot/opt/pmkb/tools/restore-rootfs.py
install -m 0644 "$REBUILD" config/includes.chroot/opt/pmkb/tools/rebuild-rootfs.py
install -m 0644 "$LEGACY" config/includes.chroot/opt/pmkb/tools/import-legacy-backup.py
install -m 0644 "$INSPECTOR" config/includes.chroot/opt/pmkb/tools/inspect-aura-hd.py
install -m 0644 "$MANIFEST" config/includes.chroot/opt/pmkb/candidate.json
install -m 0644 "$PLAN" config/includes.chroot/opt/pmkb/restore-plan.json
install -m 0644 "$CANDIDATE" "config/includes.chroot/opt/pmkb/$IMAGE_NAME"
install -m 0644 "$SERVICE" config/includes.chroot/etc/systemd/system/pmkb-qualification.service
ln -s /etc/systemd/system/pmkb-qualification.service \
  config/includes.chroot/etc/systemd/system/multi-user.target.wants/pmkb-qualification.service
ln -s /dev/null config/includes.chroot/etc/systemd/system/getty@tty1.service
if [ -f "$LOGO" ]; then
    install -m 0644 "$LOGO" config/includes.chroot/opt/pmkb/branding/pmkb-logo-original.png
fi

cat > config/includes.chroot/opt/pmkb/BUILD-IDENTITY.json <<EOF
{
  "schema": 1,
  "project": "PimpMyKobo-AuraHD",
  "head": "$HEAD",
  "image_name": "$IMAGE_NAME",
  "image_sha256": "$EXPECTED_SHA",
  "manifest_sha256": "$MANIFEST_SHA",
  "plan_sha256": "$PLAN_SHA"
}
EOF

lb build
ISO=$(find . -maxdepth 1 -type f \( -name 'live-image-*.hybrid.iso' -o -name 'live-image-*.iso' \) | head -n 1)
[ -n "$ISO" ] && [ -f "$ISO" ] || { echo "STOP: ISO live-build introuvable" >&2; exit 2; }
OUT="$OUTPUT_DIR/PMKB-Qualification-USB-$SHORT.iso"
cp "$ISO" "$OUT"
sha256sum "$OUT" > "$OUT.sha256"

printf '\nOK — ISO créé localement, aucune microSD touchée:\n%s\n' "$OUT"
cat "$OUT.sha256"
