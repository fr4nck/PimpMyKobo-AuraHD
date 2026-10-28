"""Pure, proposed SDIO/RTC resume checkpoints for E606C0 host fixtures.

Not a proven i.MX50 suspend sequence: no filesystem, device, clock, or Wi-Fi
access. A declared checkpoint is never evidence that hardware reached it.
"""

EVENTS = frozenset((
    "sdio_quiesced", "suspend", "resume", "mmc_ready", "sdio_ready",
    "rtc_untrusted", "time_source_confirmed", "rtc_sync_confirmed",
))
MAX_EVENTS = 128


def replay(events):
    """Check a conservative dependency order, not a driver implementation."""
    base = {
        "status": "refused", "scope": "synthetic_resume_order_only",
        "hardware_verified": False, "mmc_resume_verified": False,
        "sdio_resume_verified": False, "rtc_verified": False,
    }
    if (type(events) not in (list, tuple) or len(events) > MAX_EVENTS or
            any(type(e) is not str or e not in EVENTS for e in events)):
        return {**base, "error": "invalid_events"}

    sleeping = False
    quiesced = False
    mmc = False
    sdio = False
    rtc_trusted_claim = False
    time_source_fresh = False
    suspends = 0
    resumes = 0

    for index, event in enumerate(events):
        error = None
        if event == "sdio_quiesced":
            if sleeping:
                error = "asleep"
            else:
                quiesced, mmc, sdio = True, False, False
        elif event == "suspend":
            if sleeping:
                error = "already_suspended"
            elif not quiesced:
                error = "sdio_not_quiesced"
            else:
                sleeping, mmc, sdio = True, False, False
                time_source_fresh = False
                suspends += 1
        elif event == "resume":
            if not sleeping:
                error = "not_suspended"
            else:
                sleeping, quiesced, mmc, sdio = False, False, False, False
                time_source_fresh = False
                resumes += 1
        elif event == "mmc_ready":
            if sleeping:
                error = "asleep"
            else:
                mmc = True
                sdio = False  # a new host checkpoint revokes stale SDIO claims
                quiesced = False  # host wake invalidates a previous sleep gate
        elif event == "sdio_ready":
            if sleeping:
                error = "asleep"
            elif not mmc:
                error = "mmc_not_ready"
            else:
                sdio = True
        elif event == "rtc_untrusted":
            rtc_trusted_claim = False
            time_source_fresh = False
        elif event == "time_source_confirmed":
            if sleeping:
                error = "asleep"
            else:
                time_source_fresh = True
        elif event == "rtc_sync_confirmed":
            if sleeping:
                error = "asleep"
            elif not time_source_fresh:
                error = "time_source_missing"
            else:
                rtc_trusted_claim = True
                time_source_fresh = False
        if error:
            return {**base, "error": error, "event_index": index}

    return {
        **base, "status": "consistent_unverified",
        "suspended": sleeping, "mmc_symbolically_ready": mmc,
        "sdio_symbolically_ready": sdio,
        "rtc_trusted_claim": rtc_trusted_claim,
        "suspend_count": suspends, "resume_count": resumes,
    }
