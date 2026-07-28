"""GitHub API client for community contributions — CREATE-ONLY.

By design this module implements ONLY the endpoints needed to OPEN an issue or a proposal pull
request on the public free-chat-tools repo. There is deliberately NO merge/close/accept/delete
call anywhere here: the chat can propose, never accept. A human maintainer reviews and merges
(also enforced by branch protection on the repo's main branch). The token is least-privilege and
lives only in the server env — never exposed to the model or the client.
"""
from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request

_API = "https://api.github.com"


def _req(method: str, path: str, token: str, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(_API + path, data=data, method=method, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "free-chat.ai",
        "X-GitHub-Api-Version": "2022-11-28"})
    try:
        r = urllib.request.urlopen(req, timeout=20)
        return json.loads(r.read() or "{}"), None
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read()).get("message") or f"HTTP {e.code}"
        except Exception:
            msg = f"HTTP {e.code}"
        return None, msg
    except Exception as e:
        return None, type(e).__name__


def create_issue(repo: str, token: str, title: str, body: str):
    d, err = _req("POST", f"/repos/{repo}/issues", token, {"title": title, "body": body})
    if err:
        return None, err
    return {"url": d.get("html_url"), "number": d.get("number")}, None


def create_proposal_pr(repo: str, token: str, title: str, body: str, slug: str, files: dict):
    """Open a PR from a fresh `proposal/<slug>` branch that adds `files` ({path: text}). Never merges."""
    d, err = _req("GET", f"/repos/{repo}/git/ref/heads/main", token)
    if err:
        return None, f"base ref: {err}"
    base_sha = (d.get("object") or {}).get("sha")
    if not base_sha:
        return None, "could not resolve base branch"
    branch = f"proposal/{slug}"
    _, err = _req("POST", f"/repos/{repo}/git/refs", token,
                  {"ref": f"refs/heads/{branch}", "sha": base_sha})
    if err and "already exists" not in err.lower():
        return None, f"branch: {err}"
    for path, text in files.items():
        content = base64.b64encode(text.encode("utf-8")).decode()
        _, err = _req("PUT", f"/repos/{repo}/contents/{path}", token,
                      {"message": f"proposal: {title[:60]}", "content": content, "branch": branch})
        if err:
            return None, f"file {path}: {err}"
    d, err = _req("POST", f"/repos/{repo}/pulls", token,
                  {"title": title, "head": branch, "base": "main", "body": body})
    if err:
        return None, f"pr: {err}"
    return {"url": d.get("html_url"), "number": d.get("number")}, None
