"""Pure arithmetic for PMKB energy traces: never samples or controls hardware."""
import json
import math

FORMAT = "pmkb-power-trace-v1"
PROVENANCE = frozenset(("synthetic", "user_entered"))
SCENARIOS = frozenset(("reading_idle", "page_turn", "frontlight", "wifi", "suspend"))
MAX_JSON_CHARS = 512 * 1024
MAX_SAMPLES = 20000
MAX_DURATION_S = 7 * 24 * 3600


class TraceError(ValueError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def require(condition, code):
    if not condition:
        raise TraceError(code)


def number(value, minimum, maximum):
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value) and minimum <= value <= maximum
    except (OverflowError, ValueError):
        return False


def validate(trace):
    """Return a normalized validated trace; inputs remain untouched."""
    require(type(trace) is dict and set(trace) == {
        "format", "provenance", "device", "scenario", "conditions", "samples"
    }, "invalid_schema")
    require(trace["format"] == FORMAT, "invalid_format")
    require(type(trace["provenance"]) is str and
            trace["provenance"] in PROVENANCE, "invalid_provenance")
    require(trace["device"] == "E606C0", "invalid_device")
    require(type(trace["scenario"]) is str and
            trace["scenario"] in SCENARIOS, "invalid_scenario")
    conditions = trace["conditions"]
    require(type(conditions) is dict and set(conditions) == {
        "workload", "kernel", "instrument", "wifi", "frontlight_percent", "power_source"
    }, "invalid_conditions")
    for field in ("workload", "kernel", "instrument"):
        value = conditions[field]
        require(type(value) is str and bool(value.strip()) and len(value) <= 100,
                "invalid_conditions")
    require(conditions["wifi"] in ("on", "off") and
            type(conditions["wifi"]) is str, "invalid_conditions")
    require(type(conditions["frontlight_percent"]) is int and
            0 <= conditions["frontlight_percent"] <= 100, "invalid_conditions")
    # Battery-discharge samples only: charging requires a distinct signed-current contract.
    require(conditions["power_source"] == "battery", "invalid_power_source")
    samples = trace["samples"]
    require(type(samples) is list and 2 <= len(samples) <= MAX_SAMPLES,
            "invalid_samples")
    validated = []
    last = -1.0
    for sample in samples:
        require(type(sample) is dict and set(sample) == {
            "elapsed_s", "voltage_mv", "current_ma"
        }, "invalid_sample")
        elapsed = sample["elapsed_s"]
        require(number(elapsed, 0, MAX_DURATION_S) and elapsed > last,
                "invalid_elapsed")
        require(number(sample["voltage_mv"], 1, 20000) and
                number(sample["current_ma"], 0, 10000), "invalid_electrical_sample")
        validated.append((float(elapsed), float(sample["voltage_mv"]),
                          float(sample["current_ma"])))
        last = elapsed
    require(validated[0][0] == 0, "invalid_elapsed_origin")
    return {
        "provenance": trace["provenance"], "device": trace["device"],
        "scenario": trace["scenario"], "conditions": dict(conditions),
        "samples": validated
    }


def _blank_report():
    return {"status": "refused", "scope": "offline_arithmetic_only",
            "hardware_verified": False, "energy_saving_verified": False,
            "measurements_authenticated": False, "errors": []}


def analyze(trace):
    """Integrate battery discharge samples, without inferring battery lifetime."""
    report = _blank_report()
    try:
        data = validate(trace)
        total_mwh = 0.0
        total_mah = 0.0
        samples = data["samples"]
        for (t0, v0, i0), (t1, v1, i1) in zip(samples, samples[1:]):
            hours = (t1 - t0) / 3600.0
            total_mwh += ((v0 * i0 + v1 * i1) / 2000.0) * hours
            total_mah += (i0 + i1) / 2.0 * hours
        duration = samples[-1][0]
        report.update(status="calculated", provenance=data["provenance"],
                      device=data["device"], scenario=data["scenario"],
                      conditions=data["conditions"], sample_count=len(samples),
                      duration_s=duration,
                      energy_mwh=round(total_mwh, 6),
                      discharge_mah=round(total_mah, 6),
                      mean_power_mw=round(total_mwh * 3600.0 / duration, 6))
    except TraceError as error:
        report["errors"] = [{"code": error.code}]
    return report


def compare(baseline, candidate):
    """Compare matched workload mean power only; never certify improvements."""
    result = {"status": "refused", "scope": "offline_arithmetic_only",
              "energy_saving_verified": False, "hardware_verified": False,
              "measurements_authenticated": False, "errors": []}
    a, b = analyze(baseline), analyze(candidate)
    if a["status"] != "calculated" or b["status"] != "calculated":
        result["errors"] = [{"code": "invalid_trace"}]
        return result
    keys = ("workload", "instrument", "wifi", "frontlight_percent", "power_source")
    if (a["provenance"] != b["provenance"] or
            a["device"] != b["device"] or a["scenario"] != b["scenario"] or
            any(a["conditions"][k] != b["conditions"][k] for k in keys)):
        result["errors"] = [{"code": "conditions_mismatch"}]
        return result
    if (abs(a["duration_s"] - b["duration_s"]) >
            0.05 * max(a["duration_s"], b["duration_s"])):
        result["errors"] = [{"code": "duration_mismatch"}]
        return result
    if not a["mean_power_mw"]:
        result["errors"] = [{"code": "zero_baseline"}]
        return result
    result.update(status="calculated_unverified",
                  provenance=a["provenance"],
                  baseline_mean_mw=a["mean_power_mw"],
                  candidate_mean_mw=b["mean_power_mw"],
                  arithmetic_difference_percent=round(100 *
                      (a["mean_power_mw"] - b["mean_power_mw"]) /
                      a["mean_power_mw"], 4))
    return result


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate_json_key")
        result[key] = value
    return result


def _reject_constant(_):
    raise TraceError("invalid_json")


def analyze_json(text):
    """Decode externally supplied JSON without file I/O or duplicate-key loss."""
    if type(text) is not str or len(text) > MAX_JSON_CHARS:
        return {**_blank_report(), "errors": [{"code": "invalid_json_text"}]}
    try:
        data = json.loads(text, object_pairs_hook=_unique_pairs,
                          parse_constant=_reject_constant)
    except TraceError as error:
        return {**_blank_report(), "errors": [{"code": error.code}]}
    except (ValueError, RecursionError):
        return {**_blank_report(), "errors": [{"code": "invalid_json"}]}
    return analyze(data)
