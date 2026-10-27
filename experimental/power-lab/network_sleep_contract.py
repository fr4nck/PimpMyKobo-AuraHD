"""Offline symbolic Wi-Fi / sleep contract for PMKB E606C0 (not a driver).

Events represent claims from synthetic traces. They do not power SDIO,
control the radio, acquire RTC time, or establish a hardware resume sequence.
"""

ALLOWED = frozenset((
    "network_request", "mmc_ready", "sdio_ready", "sdio_quiesced",
    "wifi_on", "wifi_off", "network_release", "suspend", "resume",
))
MAX_EVENTS = 128


def replay(events):
    """Evaluate a small event sequence; return a non-authoritative verdict.

    User intent is deliberately not persisted across suspend/resume. A resumed
    device requires a fresh opt-in and new SDIO-ready observation before Wi-Fi
    is allowed, avoiding the *software* policy of automatic reconnection.
    """
    report = {
        "status": "refused", "scope": "synthetic_network_policy_only",
        "hardware_verified": False, "sdio_resume_verified": False,
        "wifi_power_cut_verified": False, "rtc_verified": False,
    }
    if (type(events) not in (list, tuple) or len(events) > MAX_EVENTS or
            any(type(event) is not str or event not in ALLOWED for event in events)):
        return {**report, "error": "invalid_events"}
    requested = False
    wifi = False
    sdio = False
    sleeping = False
    sleeps = 0
    wakes = 0
    for index, event in enumerate(events):
        error = None
        if event == "network_request":
            if sleeping:
                error = "asleep"
            else:
                requested = True
        elif event in ("mmc_ready", "sdio_quiesced"):
            if sleeping:
                error = "asleep"
            elif wifi:
                error = "wifi_still_enabled"
            else:
                # Invalidate the previous SDIO-ready claim on host reset or
                # quiescence. Preparing to sleep also revokes user intent.
                sdio = False
                if event == "sdio_quiesced":
                    requested = False
        elif event == "sdio_ready":
            if sleeping:
                error = "asleep"
            else:
                sdio = True
        elif event == "wifi_on":
            if sleeping:
                error = "asleep"
            elif not requested:
                error = "no_explicit_request"
            elif not sdio:
                error = "sdio_not_ready"
            else:
                wifi = True
        elif event == "wifi_off":
            if sleeping:
                error = "asleep"
            else:
                wifi = False
        elif event == "network_release":
            if sleeping:
                error = "asleep"
            elif wifi:
                error = "wifi_still_enabled"
            else:
                requested = False
        elif event == "suspend":
            if sleeping:
                error = "already_suspended"
            elif wifi:
                error = "wifi_still_enabled"
            else:
                # No kernel claim: this clears only symbolic policy state.
                requested = False
                sdio = False
                sleeping = True
                sleeps += 1
        elif event == "resume":
            if not sleeping:
                error = "not_suspended"
            else:
                sleeping = False
                requested = False
                sdio = False
                wakes += 1
        if error:
            return {**report, "error": error, "event_index": index}
    return {
        **report, "status": "consistent_unverified",
        "network_requested": requested, "wifi_symbolically_on": wifi,
        "sdio_symbolically_ready": sdio, "suspended": sleeping,
        "suspend_count": sleeps, "resume_count": wakes,
    }
