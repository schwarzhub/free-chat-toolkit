"""Tiny IN-MEMORY store for generated binary artifacts (e.g. GIFs from frames_to_gif).

Policy (deliberate — no disk volume): artifacts are throwaway. Eviction is **FIFO**, plus a total-
bytes cap so a hog can't crowd everything out, plus a **TTL** so nothing lingers. Nothing here is
tied to a chat key, so nothing persists beyond the TTL; served same-origin via /g/<id> and lost on
restart. Long-lived storage would require keyed persistence + a disk volume we intentionally don't run.
"""
from __future__ import annotations

import secrets
import threading
import time

from . import config

_LOCK = threading.Lock()
_STORE: dict[str, tuple[bytes, str, float]] = {}    # id -> (data, content_type, created_monotonic)
_ORDER: list[str] = []
_MAX_ITEMS = 60
_MAX_TOTAL = 40 * 1024 * 1024                        # 40 MB cap across all artifacts


def _evict_locked(now: float) -> None:
    # 1) TTL: drop anything past its lifetime (oldest are at the front).
    while _ORDER:
        v = _STORE.get(_ORDER[0])
        if v and now - v[2] > config.ARTIFACT_TTL_S:
            _STORE.pop(_ORDER.pop(0), None)
        else:
            break
    # 2) FIFO by count + total bytes (a hog trips the byte cap and pushes oldest out).
    total = sum(len(v[0]) for v in _STORE.values())
    while _ORDER and (len(_ORDER) > _MAX_ITEMS or total > _MAX_TOTAL):
        v = _STORE.pop(_ORDER.pop(0), None)
        if v:
            total -= len(v[0])


def put(data: bytes, content_type: str) -> str:
    gid = secrets.token_urlsafe(9)
    now = time.monotonic()
    with _LOCK:
        _STORE[gid] = (data, content_type, now)
        _ORDER.append(gid)
        _evict_locked(now)
    return gid


def get(gid: str):
    now = time.monotonic()
    with _LOCK:
        v = _STORE.get(gid)
        if not v:
            return None
        if now - v[2] > config.ARTIFACT_TTL_S:        # expired on read
            _STORE.pop(gid, None)
            try:
                _ORDER.remove(gid)
            except ValueError:
                pass
            return None
        return (v[0], v[1])
