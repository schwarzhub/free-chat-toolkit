"""Shared helpers for the tool modules: SSRF-guarded fetchers, JSON size-capping, HTML->text.
Every tool module does `from ._base import *` to pull these plus the stdlib modules they use."""
from __future__ import annotations
import ast, base64, codecs, difflib, hashlib, io, ipaddress, json, math, re, secrets, socket, statistics
import html as _html
import operator as _op
import urllib.error, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from .. import config


_UTC = timezone.utc     # captured here because current_datetime's `timezone` arg shadows the import

def _clip(s: str, n: int) -> str:
    return s if len(s) <= n else s[:n]

def _fit_json(obj: dict, results_key: str = "results", cap: int | None = None) -> str:
    """Serialize `obj` to compact JSON within the tool-result char cap. If it's too big, drop
    trailing items from obj[results_key] and flag `truncated` rather than let the provider clip
    the JSON mid-token (which would make it unparseable)."""
    cap = cap or config.TOOL_RESULT_MAX_CHARS
    items = list(obj.get(results_key) or [])
    while True:
        s = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
        if len(s) <= cap or not items:
            return s
        items.pop()                                  # drop the lowest-ranked hit and retry
        obj[results_key] = items
        obj["truncated"] = True
        if "count" in obj:                            # keep count honest with what's returned
            obj["count"] = len(items)

def _url_is_public(url: str) -> bool:
    """SSRF guard: only allow http(s) to hosts that resolve to public IPs (blocks localhost,
    private ranges, link-local/metadata 169.254.x, etc.)."""
    try:
        p = urllib.parse.urlparse(url)
        if p.scheme not in ("http", "https") or not p.hostname:
            return False
        for info in socket.getaddrinfo(p.hostname, None):
            ip = ipaddress.ip_address(info[4][0])
            if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
                    or ip.is_multicast or ip.is_unspecified):
                return False
        return True
    except Exception:
        return False

def _html_to_text(doc: str) -> str:
    doc = re.sub(r"(?is)<(script|style|noscript|template|svg)[^>]*>.*?</\1>", " ", doc)
    doc = re.sub(r"(?is)<br\s*/?>", "\n", doc)
    doc = re.sub(r"(?is)</(p|div|h[1-6]|li|tr|section|article)>", "\n", doc)
    text = _html.unescape(re.sub(r"(?s)<[^>]+>", " ", doc))
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n\s*\n\s*", "\n\n", text).strip()

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a):        # re-validate each hop ourselves (SSRF via redirect)
        return None

def _fetch_raw(url: str, max_bytes: int = 1_500_000) -> dict:
    """Fetch a public URL (SSRF-guarded, redirects re-validated). Returns a dict with
    text/ctype/status/final/body_truncated/err — errors surfaced as data, not exceptions."""
    for _ in range(4):
        if not _url_is_public(url):
            return {"text": None, "ctype": None, "status": None, "final": url,
                    "body_truncated": False, "err": "URL must be a public http(s) address"}
        req = urllib.request.Request(url, headers={
            "User-Agent": "free-chat.ai/1.0 (+https://free-chat.ai)",
            "Accept": "text/html,application/xhtml+xml,application/xml,*/*"})
        try:
            r = urllib.request.build_opener(_NoRedirect).open(req, timeout=12)
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 303, 307, 308) and e.headers.get("Location"):
                url = urllib.parse.urljoin(url, e.headers["Location"])
                continue
            return {"text": None, "ctype": e.headers.get("Content-Type", "") if e.headers else "",
                    "status": e.code, "final": url, "body_truncated": False, "err": f"HTTP {e.code}"}
        except Exception as e:
            return {"text": None, "ctype": None, "status": None, "final": url,
                    "body_truncated": False, "err": type(e).__name__}
        blob = r.read(max_bytes + 1)                 # +1 byte to detect an over-cap body
        body_truncated = len(blob) > max_bytes
        text = blob[:max_bytes].decode("utf-8", "replace")
        return {"text": text, "ctype": r.headers.get("Content-Type", ""),
                "status": getattr(r, "status", 200) or 200, "final": url,
                "body_truncated": body_truncated, "err": None}
    return {"text": None, "ctype": None, "status": None, "final": url,
            "body_truncated": False, "err": "too many redirects"}

def _http_request(url: str, method: str = "GET", data=None, headers=None, max_bytes: int = 1_200_000) -> dict:
    """Like _fetch_raw but method/body/header-aware. GET follows (revalidated) redirects; POST does not."""
    method = (method or "GET").upper()
    for _ in range(5):
        if not _url_is_public(url):
            return {"status": None, "final": url, "ctype": None, "body": None, "err": "URL must be a public http(s) address"}
        h = {"User-Agent": "free-chat.ai/1.0 (+https://free-chat.ai)",
             "Accept": "application/json, text/*;q=0.9, */*;q=0.8"}
        for k, v in (headers or {}).items():                    # caller headers, minus dangerous ones
            if isinstance(k, str) and k.lower() not in ("host", "cookie", "content-length") and isinstance(v, (str, int, float)):
                h[k] = str(v)
        body = data.encode("utf-8") if isinstance(data, str) else data
        req = urllib.request.Request(url, data=body, headers=h, method=method)
        try:
            r = urllib.request.build_opener(_NoRedirect).open(req, timeout=15)
        except urllib.error.HTTPError as e:
            if method == "GET" and e.code in (301, 302, 303, 307, 308) and e.headers.get("Location"):
                url = urllib.parse.urljoin(url, e.headers["Location"])
                continue
            eb = ""
            try:
                eb = e.read(4000).decode("utf-8", "replace")     # small error body helps the model react
            except Exception:
                pass
            return {"status": e.code, "final": url, "body": eb,
                    "ctype": (e.headers.get("Content-Type", "") if e.headers else ""), "err": f"HTTP {e.code}"}
        except Exception as e:
            return {"status": None, "final": url, "ctype": None, "body": None, "err": type(e).__name__}
        blob = r.read(max_bytes + 1)
        return {"status": getattr(r, "status", 200) or 200, "final": url,
                "ctype": r.headers.get("Content-Type", ""), "body": blob[:max_bytes].decode("utf-8", "replace"),
                "trunc": len(blob) > max_bytes, "err": None}
    return {"status": None, "final": url, "ctype": None, "body": None, "err": "too many redirects"}


__all__ = ['ast', 'base64', 'codecs', 'difflib', 'hashlib', 'io', 'ipaddress', 'json', 'math', 're', 'secrets', 'socket', 'statistics', '_html', '_op', 'urllib', 'ET', 'datetime', 'timezone', 'config', '_UTC', '_clip', '_fit_json', '_url_is_public', '_html_to_text', '_NoRedirect', '_fetch_raw', '_http_request']
