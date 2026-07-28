"""JS-rendered fetch via camoufox (headless, stealth Firefox) — for SPAs where a plain fetch gets an
empty shell. Ported from the NewsRAG scrape stack's camoufox launcher (os=host fingerprint coherence,
cert prefs for revoked/odd CAs, ignore_https_errors, humanize).

HEAVY and shared: a full Firefox on a small box. So it is strictly bounded and BOX-CONTENTION-AWARE —
exactly ONE render runs box-wide at a time (a global lock), a short cooldown smooths bursts, and it
REFUSES to launch when the box is low on memory or under load (rather than piling a browser onto a
stressed box). Inert unless camoufox is installed (self-gated via available()).
"""
from __future__ import annotations

import os
import platform
import threading
import time

from . import config

_LOCK = threading.Lock()            # exactly one render at a time, box-wide
_last_start = 0.0
_avail = None

# Firefox prefs: don't hard-fail on revoked/odd CAs (NewsRAG: many outlets present such certs).
_FF_PREFS = {
    "security.OCSP.enabled": 0,
    "security.OCSP.require": False,
    "security.pki.crlite_mode": 1,
    "security.cert_pinning.enforcement_level": 0,
}


def available() -> bool:
    """True only if enabled AND camoufox is importable (browser actually installed)."""
    global _avail
    if not config.RENDER_ENABLED:
        return False
    if _avail is None:
        try:
            import camoufox.sync_api  # noqa: F401
            _avail = True
        except Exception:
            _avail = False
    return _avail


def _mem_available_mb():
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) // 1024
    except Exception:
        pass
    return None


def box_status() -> tuple[bool, str]:
    """Refuse to launch when the box is contended — the primary rate limit."""
    mb = _mem_available_mb()
    if mb is not None and mb < config.RENDER_MIN_FREE_MB:
        return False, f"the server is low on memory right now ({mb} MB free) — try again shortly"
    try:
        load1 = os.getloadavg()[0]
        if load1 > config.RENDER_MAX_LOAD:
            return False, f"the server is busy right now (load {load1:.1f}) — try again shortly"
    except Exception:
        pass
    return True, ""


def render(url: str) -> tuple[str | None, str, str | None]:
    """Render `url` in headless camoufox. Returns (html, final_url, error). Contention-gated."""
    ok, why = box_status()
    if not ok:
        return None, url, why
    if not _LOCK.acquire(timeout=config.RENDER_LOCK_WAIT_S):
        return None, url, "another page render is already running — try again in a moment"
    try:
        global _last_start
        gap = time.monotonic() - _last_start
        if gap < config.RENDER_COOLDOWN_S:                 # burst smoothing while holding the slot
            time.sleep(config.RENDER_COOLDOWN_S - gap)
        _last_start = time.monotonic()
        osname = {"Darwin": "macos", "Windows": "windows"}.get(platform.system(), "linux")
        from camoufox.sync_api import Camoufox
        with Camoufox(os=osname, headless=True, humanize=True, i_know_what_im_doing=True,
                      firefox_user_prefs=_FF_PREFS) as b:
            ctx = b.new_context(ignore_https_errors=True)
            page = ctx.new_page()
            try:
                page.goto(url, wait_until="load", timeout=config.RENDER_TIMEOUT_MS)
                page.wait_for_timeout(config.RENDER_SETTLE_MS)
                return page.content(), page.url, None
            finally:
                page.close()
    except Exception as e:
        return None, url, f"render failed ({type(e).__name__})"
    finally:
        _LOCK.release()
