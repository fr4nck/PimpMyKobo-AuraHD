#!/usr/bin/env python3
"""Create a small synthetic bundle used only to prove the Live ISO build in CI."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

MIB = 1024 * 1024


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: make_qualification_live_fixture.py OUTPUT_DIR")
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)

    pre = b"P" * MIB
    old_p1 = b"O" * (8 * MIB)
    candidate = b"\0" * (8 * MIB)
    p2 = b"R" * (8 * MIB)
    p3 = b"U" * (15 * MIB)
    full = pre + old_p1 + p2 + p3

    candidate_path = out / "fixture.img"
    candidate_path.write_bytes(candidate)

    image_sha = digest(candidate)
    pre_sha = digest(pre)
    p2_sha = digest(p2)
    p3_sha = digest(p3)
    suffix_sha = digest(p2 + p3)
    full_sha = digest(full)

    manifest = {
        "schema": 1,
        "project": "PimpMyKobo-AuraHD",
        "model": "CI synthetic fixture",
        "head": "cafebabecafebabecafebabecafebabecafebabe",
        "image_name": "fixture.img",
        "image_size": len(candidate),
        "image_sha256": image_sha,
        "disk": {
            "size": len(full),
            "partition_table": "dos",
            "sector_size": 512,
        },
        "pre_p1": {
            "offset": 0,
            "size": len(pre),
            "sha256": pre_sha,
        },
        "partitions": [
            {
                "number": 1,
                "offset": len(pre),
                "size": len(candidate),
                "role": "rootfs",
            },
            {
                "number": 2,
                "offset": len(pre) + len(candidate),
                "size": len(p2),
                "role": "recoveryfs",
                "sha256": p2_sha,
            },
            {
                "number": 3,
                "offset": len(pre) + len(candidate) + len(p2),
                "size": len(p3),
                "role": "KOBOeReader",
            },
        ],
    }
    (out / "candidate.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )

    provenance = {
        "kind": "legacy/imported",
        "association": "declared_not_verified",
        "scope": "local_rootfs_reconstruction_only",
        "physical_restore_eligible": False,
    }
    fake_hash = lambda label: hashlib.sha256(label.encode("ascii")).hexdigest()
    plan = {
        "schema_version": 1,
        "tool": "prepare-p1-restore",
        "status": "prepared",
        "write_authorized": False,
        "physical_restore_eligible": False,
        "input_provenance": provenance,
        "required_target_full_sha256": full_sha,
        "disk_size": len(full),
        "p1_offset": len(pre),
        "p1_size": len(candidate),
        "replacement_sha256": image_sha,
        "preserved_sha256": {
            "pre_p1": pre_sha,
            "suffix_after_p1": suffix_sha,
            "p2": p2_sha,
            "p3": p3_sha,
        },
        "evidence_sha256": {
            "legacy_manifest": fake_hash("legacy"),
            "rebuild_report": fake_hash("rebuild"),
            "acquisition_report": fake_hash("acquisition"),
            "simulation_report": fake_hash("simulation"),
        },
        "rollback": {
            "source": "verified_full_backup",
            "offset": len(pre),
            "size": len(candidate),
        },
        "limitations": [
            "Synthetic CI-only fixture; never valid for a physical device."
        ],
    }
    (out / "plan.json").write_text(
        json.dumps(plan, indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
