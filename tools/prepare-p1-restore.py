#!/usr/bin/env python3
"""Prepare a local, reviewable P1 restoration plan. Never access a device."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import importlib.util

spec = importlib.util.spec_from_file_location("simulation", Path(__file__).with_name("restore-rootfs.py"))
simulation = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(simulation)
legacy = simulation.legacy


def prepare(manifest: Path, rebuild: Path, rootfs: Path, backup: Path,
            acquisition: Path, simulated: Path, simulation_report: Path,
            output: Path) -> dict:
    result = {"schema_version": 1, "tool": "prepare-p1-restore", "status": "refused",
              "write_authorized": False, "physical_restore_eligible": False,
              "errors": []}
    try:
        for path in (acquisition, simulated, simulation_report):
            legacy.regular(path)
        legacy.reject_device(output)
        if output.exists() or output.is_symlink():
            raise ValueError("plan output already exists; no overwrite")
        # Revalidate the legacy evidence and rebuild against the actual full backup.
        check = simulation.preflight(manifest, rebuild, rootfs, backup, output,
                                     accept_legacy_import=True, require_copy_space=False)
        if check["status"] != "ready":
            raise ValueError("local evidence refused: " + "; ".join(check["errors"]))
        acquired = simulation.read_json(acquisition)
        sha = check["target_sha256"]
        if (acquired.get("schema_version") != 1
                or acquired.get("tool") != "read-only-full-card-acquisition"
                or acquired.get("status") != "ok" or acquired.get("complete") is not True
                or acquired.get("errors") != [] or acquired.get("source_open_mode") != "rb"
                or acquired.get("image_size") != check["disk_size"]
                or any(acquired.get(key) != sha for key in
                       ("image_sha256", "source_stream_sha256", "source_reread_sha256"))
                or any(acquired.get("checks", {}).get(key) is not True for key in
                       ("mbr_hwconfig", "historical_prefix_p2", "exact_physical_length",
                        "destination_readback", "whole_source_reread"))):
            raise ValueError("complete acquisition report inconsistent with full backup")
        report = simulation.read_json(simulation_report)
        if (report.get("tool") != "restore-rootfs" or report.get("schema_version") != 1
                or report.get("mode") != "disk_image_simulation" or report.get("status") != "ok"
                or report.get("complete") is not True or report.get("errors") != []
                or report.get("input_provenance") != legacy.PROVENANCE
                or report.get("physical_restore_eligible") is not False
                or any(report.get(key) != check[key] for key in
                       ("disk_size", "partitions", "p1_offset", "p1_size", "rootfs_sha256",
                        "target_sha256", "backup_manifest_sha256", "rebuild_report_sha256"))
                or simulated.stat().st_size != check["disk_size"]
                or report.get("output_sha256") != legacy.digest(simulated)):
            raise ValueError("simulation report inconsistent with local inputs")
        p1, p2, p3 = check["partitions"]
        with simulated.open("rb") as handle:
            after = {"pre_p1": simulation.hash_region(handle, 0, p1["offset"]),
                     "suffix_after_p1": simulation.hash_region(handle, p1["end"], check["disk_size"] - p1["end"]),
                     "p2": simulation.hash_region(handle, p2["offset"], p2["size"]),
                     "p3": simulation.hash_region(handle, p3["offset"], p3["size"])}
            if (after != check["preserved_before"]
                    or simulation.hash_region(handle, p1["offset"], p1["size"]) != check["rootfs_sha256"]):
                raise ValueError("simulated P1 or preserved regions differ")
        result.update(status="prepared", input_provenance=legacy.PROVENANCE,
                      required_target_full_sha256=sha, disk_size=check["disk_size"],
                      p1_offset=p1["offset"], p1_size=p1["size"],
                      replacement_sha256=check["rootfs_sha256"], preserved_sha256=after,
                      evidence_sha256={"legacy_manifest": legacy.digest(manifest),
                                       "rebuild_report": legacy.digest(rebuild),
                                       "acquisition_report": legacy.digest(acquisition),
                                       "simulation_report": legacy.digest(simulation_report)},
                      rollback={"source": "verified_full_backup", "offset": p1["offset"], "size": p1["size"]},
                      limitations=["Unsigned reports: consistency verified, not authenticity.",
                                   "Physical target identity and exclusive access still require verification.",
                                   "Bootability has not been tested. Separate explicit write approval required."])
        with output.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    except (OSError, ValueError, TypeError, KeyError) as exc:
        result.update(status="refused", errors=[str(exc)])
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("manifest", "rebuild", "rootfs", "backup", "acquisition",
                 "simulated", "simulation_report", "output"):
        parser.add_argument(name, type=Path)
    result = prepare(**vars(parser.parse_args()))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "prepared" else 1


if __name__ == "__main__":
    raise SystemExit(main())
