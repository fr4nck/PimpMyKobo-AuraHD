"""Validate synthetic sysfs metadata only; no filesystem or device access."""
import json
import re

EVENT = r"event(?:0|[1-9][0-9]{0,3})"
FB = r"fb(?:0|[1-9][0-9]{0,3})"
PATH = re.compile(
    rf"class/graphics/{FB}/(?:dev|bits_per_pixel|rotate)"
    rf"|class/input/{EVENT}/(?:dev|device/name)"
    r"|class/misc/ntx_io/dev"
)
DEV = re.compile(r"(0|[1-9][0-9]{0,6}):(0|[1-9][0-9]{0,6})")


class SnapshotError(ValueError):
    def __init__(self, code, path=None):
        self.detail = {"code": code}
        if path is not None:
            self.detail["path"] = path


def _require(condition, code, path=None):
    if not condition:
        raise SnapshotError(code, path)


def _line(files, path):
    _require(path in files, "missing_file", path)
    return files[path].removesuffix("\n")


def _dev(files, path):
    value = _line(files, path)
    _require(DEV.fullmatch(value) is not None, "invalid_dev", path)
    major, minor = map(int, value.split(":"))
    # Contract limits for Linux major/minor metadata, not proof of a driver.
    _require(0 < major <= 4095 and 0 <= minor <= 1048575, "invalid_dev", path)
    return major, minor


def validate_snapshot(snapshot):
    """Return coherence of supplied synthetic data, never hardware readiness."""
    report = {
        "schema_version": 1,
        "tool": "pmkb-synthetic-sysfs",
        "scope": "synthetic_metadata_only",
        "status": "refused",
        "snapshot_coherent": False,
        "hardware_verified": False,
        "boot_qualified": False,
        "physical_restore_eligible": False,
        "identified": {},
        "errors": [],
        "unverified": [
            "snapshot_completeness_and_authenticity",
            "framebuffer_driver_binding_and_panel_readiness",
            "evdev_capabilities_and_touch_coordinates",
            "mcu_probe_and_frontlight_operation",
            "watchdog_power_usb_and_network",
        ],
    }
    try:
        _require(type(snapshot) is dict, "invalid_schema")
        _require(set(snapshot) == {"schema_version", "provenance", "files"},
                 "invalid_schema")
        _require(type(snapshot["schema_version"]) is int
                 and snapshot["schema_version"] == 1, "invalid_schema")
        _require(snapshot["provenance"] == "synthetic", "invalid_provenance")
        records = snapshot["files"]
        _require(type(records) is list and len(records) <= 256, "invalid_files")
        files = {}
        for item in records:
            _require(type(item) is dict and set(item) == {"path", "text"},
                     "invalid_record")
            path, value = item["path"], item["text"]
            _require(type(path) is str and len(path) <= 128
                     and PATH.fullmatch(path) is not None, "unsupported_path")
            _require(path not in files, "duplicate_path", path)
            _require(type(value) is str and len(value) <= 256
                     and value.isascii(), "invalid_text", path)
            line = value.removesuffix("\n")
            _require(bool(line) and all(32 <= ord(c) <= 126 for c in line),
                     "invalid_text", path)
            files[path] = value

        framebuffers = sorted({p.split("/")[2] for p in files
                               if p.startswith("class/graphics/")})
        _require(framebuffers == ["fb0"], "framebuffer_identity_ambiguous_or_missing")
        fb_path = "class/graphics/fb0/dev"
        fb_dev = _dev(files, fb_path)
        _require(fb_dev == (29, 0), "unexpected_framebuffer_dev", fb_path)
        bpp_path = "class/graphics/fb0/bits_per_pixel"
        rotation_path = "class/graphics/fb0/rotate"
        bpp = _line(files, bpp_path)
        rotation = _line(files, rotation_path)
        _require(bpp in {"8", "16", "32"}, "unsupported_bpp", bpp_path)
        _require(rotation in {"0", "1", "2", "3"}, "invalid_rotation", rotation_path)

        ntx_path = "class/misc/ntx_io/dev"
        ntx_dev = _dev(files, ntx_path)
        _require(ntx_dev == (10, 190), "unexpected_ntx_dev", ntx_path)
        events = sorted({p.split("/")[2] for p in files
                         if p.startswith("class/input/")})
        used = {fb_dev, ntx_dev}
        touches = []
        for event in events:
            prefix = "class/input/" + event
            name_path, dev_path = prefix + "/device/name", prefix + "/dev"
            name = _line(files, name_path)
            number = _dev(files, dev_path)
            _require(number not in used, "duplicate_dev", dev_path)
            used.add(number)
            if name == "zForce-ir-touch":
                touches.append({"sysfs_path": prefix, "dev": list(number)})
        _require(len(touches) == 1, "touch_identity_ambiguous_or_missing")

        report.update(
            status="coherent",
            snapshot_coherent=True,
            identified={
                "framebuffer": {"sysfs_path": "class/graphics/fb0",
                                "dev": list(fb_dev),
                                "bits_per_pixel": int(bpp), "rotate": int(rotation)},
                "touch": touches[0],
                "frontlight_interface": {"sysfs_path": "class/misc/ntx_io",
                                        "dev": list(ntx_dev)},
            },
        )
    except SnapshotError as error:
        report["errors"].append(error.detail)
    return report


MAX_JSON_CHARACTERS = 128 * 1024


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, "duplicate_json_key")
        result[key] = value
    return result


def _reject_constant(value):
    raise SnapshotError("invalid_json")


def validate_snapshot_json(text):
    """Decode an already supplied JSON string, without opening any file.

    Unlike json.loads defaults, reject duplicate object keys and non-JSON
    constants before information can disappear into a Python dictionary.
    """
    try:
        _require(type(text) is str and len(text) <= MAX_JSON_CHARACTERS,
                 "invalid_json_text")
        snapshot = json.loads(text, object_pairs_hook=_unique_object,
                              parse_constant=_reject_constant)
    except SnapshotError as error:
        report = validate_snapshot(None)
        report["errors"] = [error.detail]
        return report
    except (ValueError, RecursionError):
        report = validate_snapshot(None)
        report["errors"] = [{"code": "invalid_json"}]
        return report
    return validate_snapshot(snapshot)
