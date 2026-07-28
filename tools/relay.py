"""Bring-your-own-compute relay: let a key-linked chat run commands on the USER'S OWN machine.

The user runs a tiny stdlib-only runner (served at /api/runner/script) that dials OUT to this box,
authenticates with their key, and — by default — asks them to APPROVE each command in their own
terminal before it runs. The box never opens an inbound connection to the user; it only queues
commands and hands back results. The `run_local` chat tool enqueues a command for that key's runner
and waits for the result.

Why this is safe(r) than on-box exec:
  * The code runs on the user's machine, at their explicit opt-in, with a runner THEY started.
  * confirm-before-run (default) means neither a prompt-injected model NOR a compromised relay can
    run anything the user didn't read and approve in their terminal. `--yolo` opts out knowingly.
  * The box holds nothing but an in-memory, per-key command queue (lost on restart) and never
    persists commands or output to disk.

Everything is in-memory and bounded: a runner is "online" only if it polled within RUNNER_TTL_S;
queues and results are capped and expire.
"""
from __future__ import annotations

import secrets
import threading
import time

from . import config, keys

_LOCK = threading.Lock()
# key_hash -> {"seen": ts, "info": {...}, "queue": [ {id, code, ts} ], "results": {id: (ts, result)} }
_R: dict[str, dict] = {}


def _kh(key: str) -> str | None:
    return keys.key_hash(key) if keys.looks_valid(key) else None


def _slot(kh: str) -> dict:
    return _R.setdefault(kh, {"seen": 0.0, "info": {}, "queue": [], "results": {}})


def _gc(now: float) -> None:
    """Drop stale runners / expired results. Caller holds _LOCK."""
    for kh in list(_R):
        r = _R[kh]
        r["results"] = {i: (t, v) for i, (t, v) in r["results"].items()
                        if now - t < config.RUN_LOCAL_RESULT_TTL_S}
        if now - r["seen"] > config.RUNNER_TTL_S and not r["queue"] and not r["results"]:
            del _R[kh]


def hello(key: str, info: dict | None = None) -> str | None:
    """Register / refresh a runner for this key. Returns the key_hash, or None if the key is bad."""
    kh = _kh(key)
    if not kh:
        return None
    now = time.time()
    with _LOCK:
        r = _slot(kh)
        r["seen"] = now
        if info:
            r["info"] = {k: str(v)[:120] for k, v in info.items() if k in ("host", "platform", "cwd", "user")}
        _gc(now)
    return kh


def online(kh: str) -> bool:
    if not kh:
        return False
    with _LOCK:
        r = _R.get(kh)
        return bool(r) and (time.time() - r["seen"] < config.RUNNER_TTL_S)


def runner_info(kh: str) -> dict:
    with _LOCK:
        r = _R.get(kh)
        return dict(r["info"]) if r else {}


def poll(key: str) -> tuple[str | None, list]:
    """Runner asks for pending commands. Returns (key_hash, [commands]) — commands are drained."""
    kh = _kh(key)
    if not kh:
        return None, []
    now = time.time()
    with _LOCK:
        r = _slot(kh)
        r["seen"] = now
        cmds = r["queue"]
        r["queue"] = []
        _gc(now)
    return kh, [{"id": c["id"], "code": c["code"]} for c in cmds]


def submit_result(key: str, cmd_id: str, result: dict) -> bool:
    kh = _kh(key)
    if not kh or not cmd_id:
        return False
    with _LOCK:
        r = _R.get(kh)
        if not r:
            return False
        r["results"][cmd_id] = (time.time(), result)
    return True


def enqueue(kh: str, code: str) -> str | None:
    """Chat side: queue a command for this key's runner. Returns a command id, or None if the
    per-key backlog is full."""
    cid = "l" + secrets.token_hex(6)
    with _LOCK:
        r = _slot(kh)
        if len(r["queue"]) >= config.RUN_LOCAL_QUEUE_MAX:
            return None
        r["queue"].append({"id": cid, "code": code, "ts": time.time()})
    return cid


def wait_result(kh: str, cid: str, timeout: float) -> dict | None:
    """Chat side: block until the runner reports this command's result, or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        with _LOCK:
            r = _R.get(kh)
            if r and cid in r["results"]:
                return r["results"].pop(cid)[1]
        time.sleep(config.RUN_LOCAL_POLL_S)
    return None


# ---------------------------------------------------------------------------
# The local runner. Stdlib-only so `curl -s <url>/api/runner/script | python3 - --key KEY` just works
# with no pip install. Served verbatim by GET /api/runner/script.
# ---------------------------------------------------------------------------
RUNNER_SCRIPT = r'''#!/usr/bin/env python3
"""free-chat.ai local runner — lets a key-linked chat run commands on THIS machine, with your
per-command approval. Stdlib only.

    python3 runner.py --key YOUR_KEY [--url https://free-chat.ai] [--dir .] [--timeout 60] [--yolo]

By default every command is printed and waits for you to type 'y' before it runs. --yolo disables
that (auto-run everything the chat sends — only on a machine you're willing to hand over). Ctrl-C to
stop; closing the runner takes the run_local tool offline for your key.
"""
import argparse, json, os, platform, socket, subprocess, sys, time, urllib.error, urllib.request

def _post(url, obj, timeout):
    data = json.dumps(obj).encode()
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read() or b"{}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True)
    ap.add_argument("--url", default="https://free-chat.ai")
    ap.add_argument("--dir", default=".")
    ap.add_argument("--timeout", type=int, default=60, help="per-command timeout (s)")
    ap.add_argument("--interval", type=float, default=1.2, help="seconds between polls when idle")
    ap.add_argument("--yolo", action="store_true", help="auto-run every command without asking")
    a = ap.parse_args()
    base = a.url.rstrip("/")
    workdir = os.path.abspath(os.path.expanduser(a.dir))
    info = {"host": socket.gethostname(), "platform": platform.platform(),
            "cwd": workdir, "user": os.environ.get("USER") or os.environ.get("USERNAME") or "?"}

    print("free-chat.ai local runner")
    print("  machine :", info["host"], "(" + info["platform"] + ")")
    print("  workdir :", workdir)
    print("  mode    :", "AUTO-RUN (--yolo)" if a.yolo else "approve each command")
    print("  server  :", base)
    if a.yolo:
        print("  ! yolo: the chat can run ANY command here without asking. Only on a machine you trust it with.")
    print("Linked to your key. Ask the chat to use run_local. Ctrl-C to stop.\n")

    backoff = 1.0
    while True:
        try:
            _post(base + "/api/runner/hello", {"key": a.key, "info": info}, 15)
            r = _post(base + "/api/runner/poll", {"key": a.key}, 40)
            backoff = 1.0
        except urllib.error.HTTPError as e:
            print("[runner] server said", e.code, "- is the key valid?", file=sys.stderr)
            time.sleep(min(backoff, 15)); backoff *= 2; continue
        except Exception as e:
            print("[runner] can't reach server (" + type(e).__name__ + "), retrying...", file=sys.stderr)
            time.sleep(min(backoff, 15)); backoff *= 2; continue

        cmds = r.get("commands", [])
        if not cmds:
            time.sleep(a.interval)
        for cmd in cmds:
            code = cmd.get("code", "")
            print("\n" + "-" * 60)
            print("the chat wants to run:\n")
            print("    " + code.replace("\n", "\n    "))
            print("-" * 60)
            approved = a.yolo
            if not a.yolo:
                try:
                    approved = input("run this here? [y/N] ").strip().lower() in ("y", "yes")
                except (EOFError, KeyboardInterrupt):
                    approved = False
            if not approved:
                print("declined.")
                _post(base + "/api/runner/result",
                      {"key": a.key, "id": cmd["id"],
                       "result": {"approved": False, "stdout": "", "stderr": "",
                                  "exit_code": None, "note": "user declined this command"}}, 15)
                continue
            print("running...")
            try:
                p = subprocess.run(code, shell=True, cwd=workdir, timeout=a.timeout,
                                   capture_output=True, text=True)
                out, err, rc, to = p.stdout, p.stderr, p.returncode, False
            except subprocess.TimeoutExpired as e:
                out, err, rc, to = (e.stdout or ""), (e.stderr or ""), None, True
            except Exception as e:
                out, err, rc, to = "", "runner error: " + str(e), None, False
            if isinstance(out, bytes): out = out.decode("utf-8", "replace")
            if isinstance(err, bytes): err = err.decode("utf-8", "replace")
            print("done (exit " + str(rc) + ("; TIMED OUT" if to else "") + ")")
            _post(base + "/api/runner/result",
                  {"key": a.key, "id": cmd["id"],
                   "result": {"approved": True, "stdout": out[:20000], "stderr": err[:20000],
                              "exit_code": rc, "timed_out": to}}, 20)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nstopped.")
'''
