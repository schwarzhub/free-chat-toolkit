"""Off-box code execution via a guardrailed GitHub Actions workflow (run-code.yml on the toolkit repo).

The chat runs bounded Python in a sandbox that is NOT this box: a `workflow_dispatch` triggers a
no-network, resource-capped docker container inside an ephemeral GitHub-hosted runner (the workflow
has `permissions: {}` and no secrets). We dispatch → poll the run → download the result artifact.
Free (public repo), fully isolated, and in-bounds when scoped to toolkit validation.

Strictly bounded: gated on a least-privilege Actions token, a global concurrency cap, a per-IP daily
cap, a code-size cap, and a bounded wait (past which we return the run URL to check later).
"""
from __future__ import annotations

import base64
import gzip
import io
import json
import secrets
import threading
import time
import urllib.error
import urllib.request
import zipfile

from . import config

_API = "https://api.github.com"
_LOCK = threading.Lock()
_ip_hits: dict[str, list] = {}
_sem = None


def available() -> bool:
    return bool(config.GH_ACTIONS_TOKEN)


def _semaphore():
    global _sem
    if _sem is None:
        _sem = threading.BoundedSemaphore(max(1, config.RUN_CODE_CONCURRENCY))
    return _sem


def _api(method: str, path: str, body=None, timeout: int = 25):
    data = json.dumps(body).encode() if body is not None else None
    h = {"Authorization": "Bearer " + config.GH_ACTIONS_TOKEN,
         "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if data:
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(_API + path, data=data, method=method, headers=h)
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
        return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception:
        return None, b""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a):
        return None


def _download_result(run_id: int):
    """Fetch the run's result artifact. The archive URL 302s to a SIGNED blob URL — auth goes only
    to api.github.com; the signed URL must be fetched WITHOUT the token (else 401)."""
    st, b = _api("GET", f"/repos/{config.GH_ACTIONS_REPO}/actions/runs/{run_id}/artifacts")
    if st != 200:
        return None
    arts = (json.loads(b) or {}).get("artifacts", [])
    if not arts:
        return None
    h = {"Authorization": "Bearer " + config.GH_ACTIONS_TOKEN, "Accept": "application/vnd.github+json"}
    loc = None
    try:
        urllib.request.build_opener(_NoRedirect).open(
            urllib.request.Request(arts[0]["archive_download_url"], headers=h), timeout=25)
    except urllib.error.HTTPError as e:
        loc = e.headers.get("Location")
    except Exception:
        return None
    if not loc:
        return None
    try:
        zb = urllib.request.urlopen(loc, timeout=30).read()        # signed URL, no auth header
        return json.loads(zipfile.ZipFile(io.BytesIO(zb)).read("result.json"))
    except Exception:
        return None


def _rate_ok(ip_hash: str) -> bool:
    now = time.time()
    with _LOCK:
        hits = [t for t in _ip_hits.get(ip_hash, []) if now - t < 86400]
        if len(hits) >= config.RUN_CODE_DAILY_CAP:
            _ip_hits[ip_hash] = hits
            return False
        hits.append(now)
        _ip_hits[ip_hash] = hits
        return True


def run(code: str, ip_hash: str = "") -> dict:
    if not available():
        return {"ok": False, "error": "code execution isn't configured on this server"}
    code = code or ""
    if not code.strip():
        return {"ok": False, "error": "code is required"}
    if len(code.encode("utf-8", "ignore")) > config.RUN_CODE_MAX_BYTES:
        return {"ok": False, "error": f"code too large (max {config.RUN_CODE_MAX_BYTES} bytes)"}
    if not _rate_ok(ip_hash):
        return {"ok": False, "error": f"daily code-run limit reached ({config.RUN_CODE_DAILY_CAP}/day)"}
    if not _semaphore().acquire(timeout=config.RUN_CODE_SLOT_WAIT_S):
        return {"ok": False, "error": "too many code runs in progress right now — try again shortly"}
    try:
        repo = config.GH_ACTIONS_REPO
        rid = "c" + secrets.token_hex(5)
        cb = base64.b64encode(gzip.compress(code.encode("utf-8"))).decode()
        st, b = _api("POST", f"/repos/{repo}/actions/workflows/run-code.yml/dispatches",
                     {"ref": "main", "inputs": {"rid": rid, "code_b64": cb}})
        if st != 204:
            return {"ok": False, "error": f"could not start the run (HTTP {st})"}
        run_id, status, deadline = None, None, time.time() + config.RUN_CODE_MAX_WAIT_S
        while time.time() < deadline:
            time.sleep(config.RUN_CODE_POLL_S)
            st, b = _api("GET", f"/repos/{repo}/actions/runs?event=workflow_dispatch&per_page=30")
            if st != 200:
                continue
            m = [r for r in (json.loads(b) or {}).get("workflow_runs", [])
                 if r.get("name") == f"run-code {rid}"]
            if m:
                run_id, status = m[0]["id"], m[0]["status"]
                if status == "completed":
                    break
        run_url = f"https://github.com/{repo}/actions/runs/{run_id}" if run_id else None
        if status != "completed":
            return {"ok": False, "pending": True, "run_url": run_url,
                    "error": "the run is still going — check back shortly at run_url"}
        res = _download_result(run_id)
        if res is None:
            return {"ok": False, "error": "the run finished but no result was produced", "run_url": run_url}
        res["ok"] = True
        res["run_url"] = run_url
        return res
    finally:
        _semaphore().release()
