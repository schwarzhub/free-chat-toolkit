"""Tool calling — a web_search tool backed by a self-hosted SearXNG instance, plus a small
stdlib scraping/utility kit.

SearXNG is a privacy-respecting metasearch engine: no API key, no tracking, self-hosted next to the
app (see deploy/). Tool-capable models get these functions; the model decides when to call them
(tool_choice="auto"), the provider runs the OpenAI tool-call loop, we execute here and feed results
back, and the model answers with sources.

The registry maps tool name -> callable(**args) -> str. Keeping it string-in/string-out means the
provider's tool loop stays provider-agnostic. Where structured data is useful to the model
(web_search, extract_metadata, extract_links) the string returned is compact JSON; where the model
mostly wants to *read* (fetch_url, rss_fetch) it's plain text with a one-line JSON metadata header.

Design notes:
- Results are size-capped (config.TOOL_RESULT_MAX_CHARS) so one call can't blow the context. When a
  cap forces a cut, we say so with a `truncated` flag instead of failing silently.
- Failures come back as data (`{"error": ...}` / `ok: false`) so the model can react, not guess.
"""
from __future__ import annotations

import ast
import base64
import codecs
import difflib
import hashlib
import html as _html
import io
import ipaddress
import json
import math
import operator as _op
import re
import secrets
import socket
import statistics
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from . import config

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


# ============================================================ web_search (SearXNG metasearch)
# The model can steer the SEARCH ENGINE POOL (`engines`) and the usual SearXNG filters, and pick
# which per-hit fields come back (`fields`) — so it can do source/engine-distribution analysis,
# prefer primary sources, or keep results lean. title/url/content/engine are always included.
_SEARCH_FIELDS = ["category", "score", "parsed_url", "published", "priority"]

WEB_SEARCH = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": (
            "Search the live web via a privacy metasearch engine (SearXNG) for current or factual "
            "information (news, prices, docs, events, anything after your training cutoff). Returns "
            "JSON: query metadata (number_of_results, engines_used) + a `results` list, each with "
            "title, url, content (snippet) and the `engine`(s) that surfaced it. Cite the URLs you "
            "use. You control the engine pool and filters via the parameters below, and can request "
            "extra per-hit fields (score, category, published date, parsed_url) via `fields`."),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query."},
                "engines": {
                    "type": "string",
                    "description": ("Comma-separated SearXNG engine pool to query, e.g. "
                                    "'google,bing,duckduckgo,brave,wikipedia,yandex'. Omit to use the "
                                    "instance default pool. Use this to prefer specific sources or "
                                    "widen/narrow coverage."),
                },
                "categories": {
                    "type": "string",
                    "description": ("Comma-separated SearXNG categories, e.g. 'general', 'news', "
                                    "'science', 'it', 'images'. Omit for 'general'."),
                },
                "language": {
                    "type": "string",
                    "description": "Result language, e.g. 'en', 'ru', or 'all'. Omit for the default.",
                },
                "time_range": {
                    "type": "string",
                    "enum": ["day", "week", "month", "year"],
                    "description": "Restrict to recent results. Omit for no time limit.",
                },
                "pageno": {
                    "type": "integer",
                    "description": "Result page number (1-based) for paging past the first set.",
                },
                "safesearch": {
                    "type": "integer",
                    "enum": [0, 1, 2],
                    "description": "0=off, 1=moderate (default), 2=strict.",
                },
                "max_results": {
                    "type": "integer",
                    "description": (f"How many results to return (default {config.SEARCH_MAX_RESULTS}, "
                                    f"max {config.SEARCH_RESULTS_HARD_MAX})."),
                },
                "fields": {
                    "type": "array",
                    "items": {"type": "string", "enum": _SEARCH_FIELDS},
                    "description": ("Extra per-hit fields to include beyond title/url/content/engine. "
                                    "`score`=engine relevance, `category`, `published`=publish date if "
                                    "known, `parsed_url`=[scheme,netloc,path,...], `priority`."),
                },
            },
            "required": ["query"],
        },
    },
}


def web_search(query: str = "", engines: str = "", categories: str = "", language: str = "",
               time_range: str = "", pageno: int = 1, safesearch: int = 1,
               max_results: int = 0, fields=None, **_) -> str:
    """Query SearXNG (JSON API) and return a compact, model-readable JSON result set."""
    q = (query or "").strip()
    if not q:
        return json.dumps({"error": "no query provided"})
    try:
        n = int(max_results) if max_results else config.SEARCH_MAX_RESULTS
    except (TypeError, ValueError):
        n = config.SEARCH_MAX_RESULTS
    n = max(1, min(n, config.SEARCH_RESULTS_HARD_MAX))
    want = set(f for f in (fields or []) if f in _SEARCH_FIELDS)

    params = {"q": q, "format": "json"}
    # Engine pool + filters: explicit call args win, else fall back to instance defaults in config.
    eng = (engines or config.SEARCH_ENGINES or "").strip()
    if eng:
        params["engines"] = eng
    if categories.strip():
        params["categories"] = categories.strip()
    lang = (language or config.SEARCH_LANGUAGE or "").strip()
    if lang:
        params["language"] = lang
    if time_range in ("day", "week", "month", "year"):
        params["time_range"] = time_range
    try:
        if int(pageno) > 1:
            params["pageno"] = int(pageno)
    except (TypeError, ValueError):
        pass
    try:
        params["safesearch"] = int(safesearch) if int(safesearch) in (0, 1, 2) else 1
    except (TypeError, ValueError):
        params["safesearch"] = 1

    url = config.SEARXNG_URL.rstrip("/") + "/search?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "free-chat.ai/1.0",
                                                   "Accept": "application/json"})
        data = json.loads(urllib.request.urlopen(req, timeout=15).read())
    except Exception as e:
        return json.dumps({"error": f"search failed: {type(e).__name__}"})

    raw = (data.get("results") or [])[:n]
    engines_used = set()
    results = []
    for r in raw:
        eng_single = r.get("engine")
        eng_list = r.get("engines") or ([eng_single] if eng_single else [])
        for e in eng_list:
            engines_used.add(e)
        hit = {
            "title": (r.get("title") or "").strip(),
            "url": (r.get("url") or "").strip(),
            "content": (r.get("content") or "").strip().replace("\n", " ")[:400],
            "engine": eng_single or (",".join(eng_list) if eng_list else None),
        }
        if len(eng_list) > 1:
            hit["engines"] = eng_list
        if "score" in want and r.get("score") is not None:
            hit["score"] = r.get("score")
        if "category" in want and r.get("category"):
            hit["category"] = r.get("category")
        if "published" in want:
            pub = r.get("publishedDate") or r.get("pubdate")
            if pub:
                hit["published"] = pub
        if "parsed_url" in want and r.get("parsed_url"):
            hit["parsed_url"] = r.get("parsed_url")
        if "priority" in want and r.get("priority") is not None:
            hit["priority"] = r.get("priority")
        results.append({k: v for k, v in hit.items() if v is not None})

    if not results:
        return json.dumps({"query": q, "number_of_results": 0, "results": [],
                           "note": f"no results for '{q}'"}, ensure_ascii=False)
    out = {
        "query": q,
        "number_of_results": data.get("number_of_results"),
        "engines_used": sorted(engines_used),
        "count": len(results),
        "results": results,
    }
    if eng:
        out["engines_requested"] = eng
    return _fit_json({k: v for k, v in out.items() if v is not None})


# ============================================================ fetch_url (read a web page)
FETCH_URL = {
    "type": "function",
    "function": {
        "name": "fetch_url",
        "description": ("Fetch a public web page and return its readable text (or raw HTML). Use "
                        "after web_search to read a specific result, or when the user gives a URL. "
                        "The first line is a JSON header (status, final_url, content_type, chars, "
                        "truncated); the page body follows after a blank line."),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Absolute http(s) URL to read."},
                "max_chars": {
                    "type": "integer",
                    "description": ("Max characters of body to return (default 6000, max 20000). "
                                    "Raise it for long docs/specs; the header's `truncated` flag "
                                    "tells you if there was more."),
                },
                "raw": {
                    "type": "boolean",
                    "description": ("Return raw HTML instead of extracted text — use when structure "
                                    "matters (tables, code, exact markup). Default false."),
                },
            },
            "required": ["url"],
        },
    },
}


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


def fetch_url(url: str = "", max_chars: int = 6000, raw: bool = False, **_) -> str:
    f = _fetch_raw((url or "").strip())
    if f["err"]:
        return json.dumps({"ok": False, "status": f["status"], "final_url": f["final"],
                           "error": f["err"]}, ensure_ascii=False)
    try:
        cap = max(200, min(int(max_chars) if max_chars else 6000, 20000))
    except (TypeError, ValueError):
        cap = 6000
    ctype = f["ctype"] or ""
    is_html = ("html" in ctype) or ("<html" in f["text"][:1000].lower())
    body = f["text"] if raw else (_html_to_text(f["text"]) if is_html else f["text"])
    body = body.strip()
    if not body:
        return json.dumps({"ok": False, "status": f["status"], "final_url": f["final"],
                           "error": "no readable text found"}, ensure_ascii=False)
    truncated = f["body_truncated"] or len(body) > cap
    header = {"ok": True, "status": f["status"], "final_url": f["final"],
              "content_type": ctype, "chars": min(len(body), cap), "truncated": truncated,
              "mode": "html" if raw else "text"}
    return json.dumps(header, ensure_ascii=False) + "\n\n" + body[:cap]


# ============================================================ extract_metadata
EXTRACT_METADATA = {
    "type": "function",
    "function": {
        "name": "extract_metadata",
        "description": ("Scrape a page's structured metadata for citation: title, description, "
                        "author, publish/modified date, site name, canonical URL, lead image, plus "
                        "a JSON-LD (schema.org) snapshot when present. Returns JSON; `ok:false` with "
                        "a reason when the page has little/no metadata (e.g. an SPA)."),
        "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
    },
}


def _meta_content(html_head: str, attr: str, val: str):
    for m in re.finditer(r"<meta\s[^>]*>", html_head, re.I):
        tag = m.group(0)
        if re.search(attr + r'\s*=\s*["\']' + re.escape(val) + r'["\']', tag, re.I):
            c = re.search(r'content\s*=\s*["\'](.*?)["\']', tag, re.I | re.S)
            if c:
                return _html.unescape(c.group(1).strip())
    return None


def _jsonld(html_doc: str) -> dict | None:
    """Pull the first Article-ish schema.org object out of any ld+json blocks."""
    for m in re.finditer(r'(?is)<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
                         html_doc):
        try:
            obj = json.loads(m.group(1).strip())
        except Exception:
            continue
        candidates = obj if isinstance(obj, list) else [obj]
        if isinstance(obj, dict) and isinstance(obj.get("@graph"), list):
            candidates = obj["@graph"]
        for node in candidates:
            if not isinstance(node, dict):
                continue
            t = node.get("@type") or ""
            t = " ".join(t) if isinstance(t, list) else str(t)
            if any(k in t for k in ("Article", "NewsArticle", "BlogPosting", "Report", "WebPage")):
                keep = ("headline", "datePublished", "dateModified", "author", "publisher",
                        "description", "articleSection", "@type")
                out = {k: node[k] for k in keep if node.get(k)}
                if out:
                    return out
    return None


def extract_metadata(url: str = "", **_) -> str:
    f = _fetch_raw((url or "").strip())
    if f["err"]:
        return json.dumps({"ok": False, "status": f["status"], "error": f["err"]}, ensure_ascii=False)
    head = f["text"][:200000]
    title = (_meta_content(head, "property", "og:title") or _meta_content(head, "name", "twitter:title"))
    if not title:
        m = re.search(r"<title[^>]*>(.*?)</title>", head, re.I | re.S)
        title = _html.unescape(m.group(1).strip()) if m else None
    canon = None
    lm = re.search(r'<link\s[^>]*rel=["\']canonical["\'][^>]*>', head, re.I)
    if lm:
        hm = re.search(r'href\s*=\s*["\'](.*?)["\']', lm.group(0), re.I)
        canon = hm.group(1).strip() if hm else None
    out = {
        "url": f["final"], "title": title,
        "description": _meta_content(head, "property", "og:description") or _meta_content(head, "name", "description"),
        "author": _meta_content(head, "name", "author") or _meta_content(head, "property", "article:author"),
        "published": _meta_content(head, "property", "article:published_time") or _meta_content(head, "name", "date"),
        "modified": _meta_content(head, "property", "article:modified_time") or _meta_content(head, "name", "last-modified"),
        "site_name": _meta_content(head, "property", "og:site_name"),
        "image": _meta_content(head, "property", "og:image"),
        "canonical": canon,
    }
    out = {k: v for k, v in out.items() if v}
    ld = _jsonld(f["text"])
    if ld:
        out["jsonld"] = ld
    # "url" alone isn't real metadata — if that's all we got, the page is metadata-sparse (SPA/minimal).
    if len(out) <= 1:
        return json.dumps({"ok": False, "url": f["final"], "status": f["status"],
                           "reason": "no article metadata found (SPA or minimal HTML)"},
                          ensure_ascii=False)
    out["ok"] = True
    return _fit_json(out, results_key="_none")


# ============================================================ extract_links
EXTRACT_LINKS = {
    "type": "function",
    "function": {
        "name": "extract_links",
        "description": ("List the outbound links on a page for crawling/discovery. Returns JSON: "
                        "each link has url, anchor text, rel, and same_site (same registered domain "
                        "as the page). Optionally filter to same-site only or a domain substring."),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "same_site": {"type": "boolean", "description": "Only links on the same site. Default false."},
                "domain": {"type": "string", "description": "Only links whose host contains this string."},
                "max": {"type": "integer", "description": "Max links to return (default 60, max 200)."},
            },
            "required": ["url"],
        },
    },
}


def extract_links(url: str = "", same_site: bool = False, domain: str = "", max: int = 60, **_) -> str:
    f = _fetch_raw((url or "").strip())
    if f["err"]:
        return json.dumps({"ok": False, "status": f["status"], "error": f["err"]}, ensure_ascii=False)
    try:
        cap = int(max) if max else 60
    except (TypeError, ValueError):
        cap = 60
    cap = min(cap, 200)
    page_host = (urllib.parse.urlparse(f["final"]).hostname or "").lower()
    dom = (domain or "").strip().lower()
    links, seen = [], set()
    for m in re.finditer(r"(?is)<a\b([^>]*)>(.*?)</a>", f["text"]):
        attrs, inner = m.group(1), m.group(2)
        hm = re.search(r'href\s*=\s*["\'](.*?)["\']', attrs, re.I)
        if not hm:
            continue
        href = hm.group(1).strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        absu = urllib.parse.urljoin(f["final"], href)
        if not absu.startswith(("http://", "https://")) or absu in seen:
            continue
        host = (urllib.parse.urlparse(absu).hostname or "").lower()
        same = bool(page_host) and (host == page_host or host.endswith("." + page_host)
                                    or page_host.endswith("." + host))
        if same_site and not same:
            continue
        if dom and dom not in host:
            continue
        seen.add(absu)
        text = re.sub(r"\s+", " ", _html.unescape(re.sub(r"(?s)<[^>]+>", " ", inner))).strip()[:120]
        rel = None
        rm = re.search(r'rel\s*=\s*["\'](.*?)["\']', attrs, re.I)
        if rm:
            rel = rm.group(1).strip()
        link = {"url": absu, "text": text or None, "same_site": same}
        if rel:
            link["rel"] = rel
        links.append({k: v for k, v in link.items() if v is not None})
        if len(links) >= cap:
            break
    return _fit_json({"url": f["final"], "count": len(links), "results": links})


# ============================================================ rss_fetch
RSS_FETCH = {
    "type": "function",
    "function": {
        "name": "rss_fetch",
        "description": ("Fetch and parse an RSS/Atom feed. First line is a JSON header (feed title, "
                        "item count); then one block per item (title, link, date, summary). Good for "
                        "news/changelogs without scraping HTML."),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "max_items": {"type": "integer", "description": "Max items to return (default 20, max 50)."},
            },
            "required": ["url"],
        },
    },
}


def rss_fetch(url: str = "", max_items: int = 20, **_) -> str:
    f = _fetch_raw((url or "").strip(), max_bytes=2_000_000)
    if f["err"]:
        return json.dumps({"ok": False, "status": f["status"], "error": f["err"]}, ensure_ascii=False)
    try:
        root = ET.fromstring(f["text"][f["text"].find("<"):].encode("utf-8", "replace"))
    except Exception:
        return json.dumps({"ok": False, "error": "not valid RSS/Atom XML"}, ensure_ascii=False)
    try:
        cap = min(max(int(max_items), 1), 50)
    except (TypeError, ValueError):
        cap = 20

    def field(el, names):
        for c in el:
            t = c.tag.split("}")[-1].lower()
            if t in names:
                return (c.text or c.get("href") or "").strip()
        return ""

    feed_title = ""
    for c in root.iter():
        if c.tag.split("}")[-1].lower() == "title":
            feed_title = (c.text or "").strip()
            break
    items = []
    for it in root.iter():
        if it.tag.split("}")[-1].lower() in ("item", "entry"):
            title = field(it, {"title"})
            link = field(it, {"link"})
            date = field(it, {"pubdate", "published", "updated", "date"})
            summ = re.sub(r"\s+", " ", _html.unescape(field(it, {"description", "summary", "content"})))[:280]
            items.append(f"- {title}\n  {link}\n  {date}  {summ}")
        if len(items) >= cap:
            break
    if not items:
        return json.dumps({"ok": False, "error": "no feed items found"}, ensure_ascii=False)
    header = json.dumps({"ok": True, "feed_title": feed_title, "count": len(items)}, ensure_ascii=False)
    return header + "\n\n" + "\n".join(items)


# ============================================================ calculator (safe AST eval)
CALCULATOR = {
    "type": "function",
    "function": {
        "name": "calculator",
        "description": ("Evaluate an arithmetic expression exactly. Operators + - * / ** % // and "
                        "parentheses; functions sqrt, abs, round, floor, ceil, min, max, log, log2, "
                        "log10, exp, factorial, gcd, hypot, and trig sin/cos/tan/asin/acos/atan/atan2/"
                        "radians/degrees; constants pi, e, tau. IEEE-754 double precision "
                        "(~15-17 significant digits)."),
        "parameters": {
            "type": "object",
            "properties": {"expression": {"type": "string", "description": "e.g. (1234*5.5)/3 or sqrt(2)*pi"}},
            "required": ["expression"],
        },
    },
}

_MATH_OPS = {ast.Add: _op.add, ast.Sub: _op.sub, ast.Mult: _op.mul, ast.Div: _op.truediv,
             ast.Pow: _op.pow, ast.Mod: _op.mod, ast.FloorDiv: _op.floordiv,
             ast.USub: _op.neg, ast.UAdd: _op.pos}
_MATH_FNS = {"sqrt": math.sqrt, "abs": abs, "round": round, "floor": math.floor, "ceil": math.ceil,
             "min": min, "max": max, "log": math.log, "log2": math.log2, "log10": math.log10,
             "exp": math.exp, "factorial": math.factorial, "gcd": math.gcd, "pow": pow,
             "hypot": math.hypot, "sin": math.sin, "cos": math.cos, "tan": math.tan,
             "asin": math.asin, "acos": math.acos, "atan": math.atan, "atan2": math.atan2,
             "radians": math.radians, "degrees": math.degrees}
_MATH_CONSTS = {"pi": math.pi, "e": math.e, "tau": math.tau}


def _eval_math(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.Name) and node.id in _MATH_CONSTS:
        return _MATH_CONSTS[node.id]
    if isinstance(node, ast.BinOp) and type(node.op) in _MATH_OPS:
        return _MATH_OPS[type(node.op)](_eval_math(node.left), _eval_math(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _MATH_OPS:
        return _MATH_OPS[type(node.op)](_eval_math(node.operand))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _MATH_FNS:
        if node.keywords:
            raise ValueError("no keyword args")
        return _MATH_FNS[node.func.id](*[_eval_math(a) for a in node.args])
    raise ValueError("unsupported")


def calculator(expression: str = "", **_) -> str:
    try:
        return str(_eval_math(ast.parse((expression or "").strip(), mode="eval").body))
    except Exception:
        return ("Could not evaluate that expression (allowed: + - * / ** % //, parentheses, and "
                "sqrt/abs/round/floor/ceil/min/max/log/log2/log10/exp/factorial/gcd, pi/e/tau).")


# ============================================================ current_datetime
CURRENT_DATETIME = {
    "type": "function",
    "function": {
        "name": "current_datetime",
        "description": ("Get the current date and time. Returns UTC always; pass an IANA `timezone` "
                        "(e.g. 'America/New_York', 'Europe/London') to also get the local time there "
                        "— useful for a user's local 'today'."),
        "parameters": {
            "type": "object",
            "properties": {
                "timezone": {"type": "string", "description": "IANA tz name, e.g. 'America/New_York'. Optional."},
            },
        },
    },
}


def current_datetime(timezone: str = "", **_) -> str:
    now = datetime.now(_UTC)
    out = {"utc": now.strftime("%Y-%m-%d %H:%M:%S UTC (%A)")}
    tz = (timezone or "").strip()
    if tz:
        try:
            from zoneinfo import ZoneInfo
            local = now.astimezone(ZoneInfo(tz))
            out["local"] = local.strftime("%Y-%m-%d %H:%M:%S %Z (%A)")
            out["timezone"] = tz
        except Exception:
            out["timezone_error"] = f"unknown timezone '{tz}'"
    return json.dumps(out, ensure_ascii=False)


# ============================================================ http_api (structured JSON API client)
# Grok's #3 preference: "stable JSON from APIs over more HTML scrapers." Same SSRF-guarded egress as
# fetch_url, but keeps the response STRUCTURED (parses JSON, exposes status/final_url/content_type
# for provenance) and supports GET/POST with a JSON body + headers — for weather/FX/GitHub/package
# registries and any public REST API. Not a general proxy: public http(s) only, no cookies/Host.
HTTP_API = {
    "type": "function",
    "function": {
        "name": "http_api",
        "description": ("Call a public REST/JSON API and get structured data back (prefer this over "
                        "fetch_url when a JSON API exists — weather, FX rates, GitHub, package "
                        "registries, etc.). Returns JSON: ok, status, final_url, content_type, and "
                        "either parsed `json` or raw `text`. Public http(s) only (SSRF-guarded)."),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Absolute public http(s) API URL (include query string)."},
                "method": {"type": "string", "enum": ["GET", "POST"], "description": "Default GET."},
                "json": {"type": "object", "description": "JSON request body for POST (sets Content-Type)."},
                "body": {"type": "string", "description": "Raw request body for POST (alternative to `json`)."},
                "headers": {"type": "object", "description": "Optional request headers (e.g. Accept). No cookies."},
            },
            "required": ["url"],
        },
    },
}


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


def http_api(url: str = "", method: str = "GET", body: str = "", headers=None, **kw) -> str:
    payload = kw.get("json")
    data, hdrs = None, dict(headers or {})
    if payload is not None:
        data = json.dumps(payload)
        hdrs.setdefault("Content-Type", "application/json")
    elif body:
        data = body
    r = _http_request((url or "").strip(), method=method, data=data, headers=hdrs)
    if r["err"] and r["status"] is None:
        return json.dumps({"ok": False, "final_url": r["final"], "error": r["err"]}, ensure_ascii=False)
    out = {"ok": (r["status"] or 0) // 100 == 2, "status": r["status"],
           "final_url": r["final"], "content_type": r["ctype"]}
    b = r.get("body") or ""
    parsed = None
    if b and (("json" in (r["ctype"] or "")) or b.lstrip()[:1] in "{["):
        try:
            parsed = json.loads(b)
        except Exception:
            parsed = None
    if parsed is not None:
        out["json"] = parsed
    else:
        out["text"] = b
    if r.get("trunc"):
        out["truncated"] = True
    cap = config.TOOL_RESULT_MAX_CHARS
    s = json.dumps(out, ensure_ascii=False)
    if len(s) > cap:                                             # too big -> collapse to a truncated text form (stays valid JSON)
        raw = json.dumps(out.get("json"), ensure_ascii=False) if "json" in out else out.get("text", "")
        out.pop("json", None)
        out["text"] = raw[:cap - 300]
        out["truncated"] = True
        s = json.dumps(out, ensure_ascii=False)
    return s


# ============================================================ unshorten_url (redirect tracer)
UNSHORTEN_URL = {
    "type": "function",
    "function": {
        "name": "unshorten_url",
        "description": ("Trace where a short/redirecting URL actually goes: follows the redirect "
                        "chain and returns every hop + the final destination. Use for safety and to "
                        "cite the real source behind a t.co/bit.ly-style link. Public http(s) only."),
        "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
    },
}


def unshorten_url(url: str = "", **_) -> str:
    cur, hops = (url or "").strip(), []
    for _ in range(15):
        if not _url_is_public(cur):
            return json.dumps({"ok": False, "error": "non-public URL in redirect chain",
                               "hops": hops, "final_url": cur}, ensure_ascii=False)
        req = urllib.request.Request(cur, headers={"User-Agent": "free-chat.ai/1.0 (+https://free-chat.ai)"})
        try:
            r = urllib.request.build_opener(_NoRedirect).open(req, timeout=10)
            hops.append({"url": cur, "status": getattr(r, "status", 200) or 200})
            try:
                r.close()
            except Exception:
                pass
            return json.dumps({"ok": True, "hops": hops, "final_url": cur,
                               "final_status": hops[-1]["status"], "redirects": len(hops) - 1}, ensure_ascii=False)
        except urllib.error.HTTPError as e:
            loc = e.headers.get("Location") if e.headers else None
            hops.append({"url": cur, "status": e.code})
            if e.code in (301, 302, 303, 307, 308) and loc:
                cur = urllib.parse.urljoin(cur, loc)
                continue
            return json.dumps({"ok": True, "hops": hops, "final_url": cur,
                               "final_status": e.code, "redirects": len(hops) - 1}, ensure_ascii=False)
        except Exception as e:
            hops.append({"url": cur, "error": type(e).__name__})
            return json.dumps({"ok": False, "error": type(e).__name__, "hops": hops, "final_url": cur}, ensure_ascii=False)
    return json.dumps({"ok": False, "error": "too many redirects", "hops": hops, "final_url": cur}, ensure_ascii=False)


# ============================================================ diff_text (unified diff)
DIFF_TEXT = {
    "type": "function",
    "function": {
        "name": "diff_text",
        "description": ("Compare two texts and return a unified diff (the +/- line format). Use to "
                        "show what changed between two versions of a file, config, or snippet."),
        "parameters": {
            "type": "object",
            "properties": {
                "a": {"type": "string", "description": "The 'before' / original text."},
                "b": {"type": "string", "description": "The 'after' / new text."},
                "label_a": {"type": "string", "description": "Name for the 'before' side (default a)."},
                "label_b": {"type": "string", "description": "Name for the 'after' side (default b)."},
                "context": {"type": "integer", "description": "Context lines around each change (default 3)."},
            },
            "required": ["a", "b"],
        },
    },
}


def diff_text(a: str = "", b: str = "", label_a: str = "a", label_b: str = "b", context: int = 3, **_) -> str:
    try:
        n = max(0, min(int(context), 10))
    except (TypeError, ValueError):
        n = 3
    d = list(difflib.unified_diff((a or "").splitlines(), (b or "").splitlines(),
                                  fromfile=label_a or "a", tofile=label_b or "b", lineterm="", n=n))
    return "\n".join(d)[:config.TOOL_RESULT_MAX_CHARS] if d else "No differences."


# ============================================================ list_models (capability discovery)
# Lets a model see what OTHER models are available and what they can do — so it can suggest a better
# model to the user ("this needs vision — try X"), or pick a delegate for ask_model.
_CAP_TAGS = ["chat", "vision", "tools", "reasoning", "image", "free", "all"]
LIST_MODELS = {
    "type": "function",
    "function": {
        "name": "list_models",
        "description": ("List the chat models available on this service, optionally filtered by "
                        "capability. Use to recommend the user switch to a better-suited model, or "
                        "to choose a `model` for ask_model. Returns id, name, capabilities, and "
                        "output price (cheapest first)."),
        "parameters": {
            "type": "object",
            "properties": {
                "capability": {"type": "string", "enum": _CAP_TAGS,
                               "description": "Filter by capability. 'vision'=can see images, 'tools'=tool-calling, "
                                              "'reasoning', 'image'=image generation, 'free'=$0 logged tier. Omit for all."},
                "query": {"type": "string", "description": "Optional substring to match in id/name (e.g. 'claude', 'qwen')."},
                "limit": {"type": "integer", "description": "Max models to return (default 12, max 30)."},
            },
        },
    },
}


def list_models(capability: str = "", query: str = "", limit: int = 12, **_) -> str:
    from . import models as _m
    cap = (capability or "").strip().lower()
    try:
        rows = _m.in_bucket(cap if cap and cap != "all" else None)
    except Exception as e:
        return json.dumps({"ok": False, "error": f"model catalog unavailable: {type(e).__name__}"})
    q = (query or "").strip().lower()
    if q:
        rows = [r for r in rows if q in (r.get("id") or "").lower() or q in (r.get("name") or "").lower()]
    rows = sorted(rows, key=lambda r: (r.get("out_price") if r.get("out_price") is not None else 1e9))
    try:
        n = max(1, min(int(limit) if limit else 12, 30))
    except (TypeError, ValueError):
        n = 12
    out = [{"id": r.get("id"), "name": r.get("name"), "capabilities": r.get("tags"),
            "price_out_per_m": r.get("out_price"), "free": r.get("free")} for r in rows[:n]]
    return json.dumps({"ok": True, "capability": cap or "all", "count": len(out), "models": out},
                      ensure_ascii=False)[:config.TOOL_RESULT_MAX_CHARS]


# ============================================================ ask_model (model-to-model delegation)
# The current model can hand a subtask it can't do itself to another model — the motivating case is
# VISION (pass image_url to a vision-capable model), but it works for any "use a stronger/cheaper/
# specialist model for this one step" need. The sub-call gets NO tools (no recursion) and a low token
# cap; cost is bounded by that + the outer tool-round limit + the spend-capped key.
ASK_MODEL = {
    "type": "function",
    "function": {
        "name": "ask_model",
        "description": ("Delegate a subtask to ANOTHER model and get its answer back — use when the "
                        "task needs a capability you lack (e.g. seeing an image: pass image_url to a "
                        "vision model) or a different model would do it better. Find a target with "
                        "list_models. The delegate answers in one shot (no tools, no follow-up)."),
        "parameters": {
            "type": "object",
            "properties": {
                "model": {"type": "string", "description": "The model id to delegate to (from list_models)."},
                "prompt": {"type": "string", "description": "The exact task/question for the delegate model."},
                "image_url": {"type": "string", "description": "Optional public http(s) image URL or data:image/ URL "
                                                              "to send to a vision model."},
                "system": {"type": "string", "description": "Optional system instruction for the delegate."},
            },
            "required": ["model", "prompt"],
        },
    },
}


def run_ask_model(model: str = "", prompt: str = "", image_url: str = "", system: str = ""):
    """Core delegation. Returns (result_json_str, usage_dict_or_None) so the caller can charge the
    delegated token cost to the session ledger. `usage` = {"input_tokens","output_tokens"}."""
    from . import providers
    m, q = (model or "").strip(), (prompt or "").strip()
    if not m or not q:
        return json.dumps({"ok": False, "error": "both 'model' and 'prompt' are required"}), None
    prov = providers.for_model(m)
    if not prov:
        return json.dumps({"ok": False, "error": f"model '{m}' is not available (try list_models)"}), None
    content = q
    if image_url:
        u = image_url.strip()
        if not (u.startswith("data:image/") or _url_is_public(u)):
            return json.dumps({"ok": False, "error": "image_url must be a public http(s) image URL or a data:image/ URL"}), None
        content = [{"type": "text", "text": q}, {"type": "image_url", "image_url": {"url": u}}]
    dc = "allow" if m.endswith(":free") else "deny"      # same privacy tiering as a normal turn
    parts, images, err, usage = [], [], None, None
    try:
        for ev in prov.stream(m, [{"role": "user", "content": content}], system=(system.strip() or None),
                              max_tokens=config.DELEGATE_MAX_TOKENS, tools=None, tool_registry=None,
                              data_collection=dc):
            t = ev.get("type")
            if t == "token":
                parts.append(ev["text"])
            elif t == "image" and ev.get("url"):
                images.append(ev["url"])                 # delegate generated an image — relay it
            elif t == "done":
                usage = ev.get("usage")
            elif t == "error":
                err = ev.get("message")
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
    answer = "".join(parts).strip()
    # Surface delegate images as markdown so they render in the tool result / parent answer. http(s)
    # urls inline directly; data: urls only if small enough to fit the context (else a note).
    img_md = []
    for u in images:
        if u.startswith("data:") and len(u) > 200000:
            img_md.append("_[delegate returned an image too large to inline]_")
        else:
            img_md.append(f"![generated image]({u})")
    if img_md:
        answer = (answer + "\n\n" + "\n\n".join(img_md)).strip()
    if not answer:
        return json.dumps({"ok": False, "model": m, "error": err or "the delegate returned nothing"}, ensure_ascii=False), usage
    out = {"ok": True, "model": m, "answer": answer}
    if images:
        out["image_count"] = len(images)
    if usage:
        out["usage"] = usage
    return json.dumps(out, ensure_ascii=False)[:config.TOOL_RESULT_MAX_CHARS], usage


def ask_model(model: str = "", prompt: str = "", image_url: str = "", system: str = "", **_) -> str:
    # Static registry entry (no ledger). The request path overrides this with a ledger-charging
    # closure (api.py _ask_model_fn) so delegated cost hits the session balance + ad pacing.
    return run_ask_model(model, prompt, image_url, system)[0]


# ============================================================ regex_test
REGEX_TEST = {
    "type": "function",
    "function": {
        "name": "regex_test",
        "description": ("Test a regular expression against sample text and get the ACTUAL matches "
                        "back (don't guess regex behavior — run it). Returns each match with its "
                        "span, numbered groups, and named groups. Python `re` syntax."),
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "The regex pattern (Python re syntax)."},
                "text": {"type": "string", "description": "The text to match against (max 5000 chars)."},
                "flags": {"type": "string", "description": "Optional flag letters: i (ignorecase), m "
                                                           "(multiline), s (dotall), x (verbose), a (ascii)."},
                "max_matches": {"type": "integer", "description": "Max matches to return (default 20, max 100)."},
            },
            "required": ["pattern", "text"],
        },
    },
}


def regex_test(pattern: str = "", text: str = "", flags: str = "", max_matches: int = 20, **_) -> str:
    p = pattern or ""
    if not p:
        return json.dumps({"ok": False, "error": "pattern is required"})
    if len(p) > 500:
        return json.dumps({"ok": False, "error": "pattern too long (max 500 chars)"})
    full = text or ""
    t = full[:5000]                       # cap input — bounds cost and pathological-regex runtime
    fl = 0
    for ch in (flags or ""):
        fl |= {"i": re.I, "m": re.M, "s": re.S, "x": re.X, "a": re.A}.get(ch.lower(), 0)
    try:
        rx = re.compile(p, fl)
    except re.error as e:
        return json.dumps({"ok": False, "error": f"invalid pattern: {e}"})
    try:
        n = max(1, min(int(max_matches), 100))
    except (TypeError, ValueError):
        n = 20
    matches = []
    for mm in rx.finditer(t):
        m = {"match": mm.group(0), "start": mm.start(), "end": mm.end()}
        if mm.groups():
            m["groups"] = list(mm.groups())
        if mm.groupdict():
            m["named"] = mm.groupdict()
        matches.append(m)
        if len(matches) >= n:
            break
    res = {"ok": True, "pattern": p, "flags": flags or "", "match_count": len(matches), "matches": matches}
    if len(full) > 5000:
        res["note"] = "text truncated to 5000 chars"
    return _fit_json(res, results_key="matches")


# ============================================================ wikipedia
WIKIPEDIA = {
    "type": "function",
    "function": {
        "name": "wikipedia",
        "description": ("Look up a topic on Wikipedia and get a clean summary + the article URL to "
                        "cite. Better than web_search for encyclopedic/definitional facts. Accepts a "
                        "title or search phrase; resolves the best-matching article."),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Article title or search phrase."},
                "lang": {"type": "string", "description": "Wikipedia language code (default 'en')."},
            },
            "required": ["query"],
        },
    },
}


def _wiki_summary(base: str, title: str):
    r = _http_request(base + "/api/rest_v1/page/summary/" + urllib.parse.quote(title.replace(" ", "_")))
    if r["err"] or not r.get("body"):
        return None
    try:
        d = json.loads(r["body"])
    except Exception:
        return None
    if d.get("type") == "disambiguation":
        return {"_disambig": True}
    return d if d.get("extract") else None


def wikipedia(query: str = "", lang: str = "en", **_) -> str:
    q = (query or "").strip()
    if not q:
        return json.dumps({"ok": False, "error": "query is required"})
    lang = re.sub(r"[^a-z]", "", (lang or "en").lower())[:12] or "en"
    base = f"https://{lang}.wikipedia.org"
    d = _wiki_summary(base, q)
    if not d or d.get("_disambig"):       # fall back to search to resolve the best title
        sr = _http_request(base + "/w/api.php?" + urllib.parse.urlencode(
            {"action": "query", "list": "search", "srsearch": q, "format": "json", "srlimit": 1}))
        try:
            hits = json.loads(sr["body"])["query"]["search"]
        except Exception:
            hits = []
        d = _wiki_summary(base, hits[0]["title"]) if hits else None
    if not d or not d.get("extract"):
        return json.dumps({"ok": False, "error": f"no Wikipedia article found for '{q}'"}, ensure_ascii=False)
    out = {"ok": True, "title": d.get("title"), "description": d.get("description"),
           "extract": d.get("extract"),
           "url": (d.get("content_urls") or {}).get("desktop", {}).get("page")}
    return json.dumps({k: v for k, v in out.items() if v is not None}, ensure_ascii=False)[:config.TOOL_RESULT_MAX_CHARS]


# ============================================================ geocode (OSM Nominatim)
GEOCODE = {
    "type": "function",
    "function": {
        "name": "geocode",
        "description": ("Convert a place/address to coordinates (forward), or coordinates to an "
                        "address (reverse), via OpenStreetMap. For distances/'what's near', geocode "
                        "the points and compute with calculator (haversine using sin/cos/atan2)."),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Place or address to geocode (forward)."},
                "lat": {"type": "number", "description": "Latitude for reverse geocoding."},
                "lon": {"type": "number", "description": "Longitude for reverse geocoding."},
                "limit": {"type": "integer", "description": "Max forward results (default 5, max 10)."},
            },
        },
    },
}


def geocode(query: str = "", lat=None, lon=None, limit: int = 5, **_) -> str:
    q = (query or "").strip()
    if not q and lat is not None and lon is not None:      # reverse
        try:
            la, lo = float(lat), float(lon)
        except (TypeError, ValueError):
            return json.dumps({"ok": False, "error": "reverse geocode needs numeric lat and lon"})
        r = _http_request("https://nominatim.openstreetmap.org/reverse?" + urllib.parse.urlencode(
            {"lat": la, "lon": lo, "format": "jsonv2"}))
        try:
            d = json.loads(r["body"])
        except Exception:
            return json.dumps({"ok": False, "error": "reverse geocode failed"})
        return json.dumps({"ok": True, "lat": la, "lon": lo, "display_name": d.get("display_name"),
                           "address": d.get("address")}, ensure_ascii=False)[:config.TOOL_RESULT_MAX_CHARS]
    if not q:
        return json.dumps({"ok": False, "error": "provide a `query` (forward) or lat+lon (reverse)"})
    try:
        n = max(1, min(int(limit), 10))
    except (TypeError, ValueError):
        n = 5
    r = _http_request("https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": q, "format": "jsonv2", "limit": n}))
    try:
        arr = json.loads(r["body"])
    except Exception:
        arr = []
    results = [{"display_name": x.get("display_name"), "lat": float(x["lat"]), "lon": float(x["lon"]),
                "type": x.get("type"), "class": x.get("class")} for x in arr if x.get("lat")]
    if not results:
        return json.dumps({"ok": False, "error": f"no location found for '{q}'"}, ensure_ascii=False)
    return _fit_json({"ok": True, "query": q, "count": len(results), "results": results})


# ============================================================ encode_decode (dev utility)
_ENC_OPS = ["base64_encode", "base64_decode", "base64url_encode", "base64url_decode",
            "url_encode", "url_decode", "hex_encode", "hex_decode", "rot13",
            "md5", "sha1", "sha256", "sha512", "jwt_decode"]
ENCODE_DECODE = {
    "type": "function",
    "function": {
        "name": "encode_decode",
        "description": ("Encode/decode or hash text without guessing. Ops: base64/base64url/url/hex "
                        "encode+decode, rot13, md5/sha1/sha256/sha512 hashes, and jwt_decode "
                        "(header+payload, NOT signature-verified)."),
        "parameters": {
            "type": "object",
            "properties": {
                "op": {"type": "string", "enum": _ENC_OPS, "description": "The operation to perform."},
                "text": {"type": "string", "description": "The input string."},
            },
            "required": ["op", "text"],
        },
    },
}


def encode_decode(op: str = "", text: str = "", **_) -> str:
    s = text or ""
    if len(s) > 100000:
        return json.dumps({"ok": False, "error": "input too long (max 100k chars)"})
    op = (op or "").strip().lower()

    def _b64u(p):
        return base64.urlsafe_b64decode(p + "=" * (-len(p) % 4)).decode("utf-8", "replace")
    try:
        if op == "base64_encode":
            r = base64.b64encode(s.encode()).decode()
        elif op == "base64_decode":
            r = base64.b64decode(s + "=" * (-len(s) % 4)).decode("utf-8", "replace")
        elif op == "base64url_encode":
            r = base64.urlsafe_b64encode(s.encode()).decode().rstrip("=")
        elif op == "base64url_decode":
            r = _b64u(s)
        elif op == "url_encode":
            r = urllib.parse.quote(s)
        elif op == "url_decode":
            r = urllib.parse.unquote(s)
        elif op == "hex_encode":
            r = s.encode().hex()
        elif op == "hex_decode":
            r = bytes.fromhex(s.strip()).decode("utf-8", "replace")
        elif op == "rot13":
            r = codecs.encode(s, "rot13")
        elif op in ("md5", "sha1", "sha256", "sha512"):
            r = hashlib.new(op, s.encode()).hexdigest()
        elif op == "jwt_decode":
            parts = s.split(".")
            if len(parts) < 2:
                return json.dumps({"ok": False, "error": "not a JWT (need header.payload.signature)"})
            return json.dumps({"ok": True, "op": op, "header": json.loads(_b64u(parts[0])),
                               "payload": json.loads(_b64u(parts[1]))}, ensure_ascii=False)[:config.TOOL_RESULT_MAX_CHARS]
        else:
            return json.dumps({"ok": False, "error": f"unknown op '{op}' (see the op enum)"})
    except Exception as e:
        return json.dumps({"ok": False, "op": op, "error": f"{type(e).__name__}: {e}"[:200]})
    return json.dumps({"ok": True, "op": op, "result": r}, ensure_ascii=False)[:config.TOOL_RESULT_MAX_CHARS]


# ============================================================ json_query (extract from JSON)
JSON_QUERY = {
    "type": "function",
    "function": {
        "name": "json_query",
        "description": ("Extract value(s) from a JSON string with a dotted path — great for pulling "
                        "specific fields out of an http_api/fetch_url response instead of eyeballing "
                        "big JSON. Path syntax: `a.b.c`, array index `items[0]`, wildcard `items[*].name` "
                        "(returns a list). Empty path returns the whole parsed value."),
        "parameters": {
            "type": "object",
            "properties": {
                "json": {"type": "string", "description": "The JSON text to query."},
                "path": {"type": "string", "description": "Dotted path, e.g. 'data.items[*].id'. Empty = whole value."},
            },
            "required": ["json"],
        },
    },
}


def json_query(path: str = "", **kw) -> str:
    raw = kw.get("json")
    if raw is None:
        raw = kw.get("data") or ""
    obj = raw if isinstance(raw, (dict, list)) else None
    if obj is None:
        try:
            obj = json.loads(raw)
        except Exception as e:
            return json.dumps({"ok": False, "error": f"input is not valid JSON: {e}"[:150]})
    p = (path or "").strip().lstrip("$").strip(".")
    if not p:
        return json.dumps({"ok": True, "path": path or "", "result": obj}, ensure_ascii=False)[:config.TOOL_RESULT_MAX_CHARS]
    toks = [t for t in re.sub(r"\[(\*|\d+)\]", r".\1", p).split(".") if t != ""]
    cur = [obj]
    for t in toks:
        nxt = []
        for o in cur:
            if t == "*":
                if isinstance(o, dict):
                    nxt.extend(o.values())
                elif isinstance(o, list):
                    nxt.extend(o)
            elif t.isdigit():
                if isinstance(o, list) and int(t) < len(o):
                    nxt.append(o[int(t)])
            elif isinstance(o, dict) and t in o:
                nxt.append(o[t])
        cur = nxt
    if not cur:
        return json.dumps({"ok": False, "path": path, "error": "no match for that path"}, ensure_ascii=False)
    result = cur if ("*" in toks or len(cur) > 1) else cur[0]
    return json.dumps({"ok": True, "path": path, "count": len(cur), "result": result},
                      ensure_ascii=False)[:config.TOOL_RESULT_MAX_CHARS]


# ============================================================ stats (exact descriptive statistics)
STATS = {
    "type": "function",
    "function": {
        "name": "stats",
        "description": ("Exact descriptive statistics for a list of numbers (count, sum, mean, "
                        "median, min, max, range, sample/population stdev + variance). Use instead "
                        "of estimating — don't do stats in your head."),
        "parameters": {
            "type": "object",
            "properties": {
                "numbers": {"type": "array", "items": {"type": "number"},
                            "description": "The numbers to summarize."},
            },
            "required": ["numbers"],
        },
    },
}


def stats(numbers=None, **_) -> str:
    nums = numbers
    if isinstance(nums, str):
        nums = re.findall(r"-?\d+(?:\.\d+)?", nums)
    if not isinstance(nums, list) or not nums:
        return json.dumps({"ok": False, "error": "provide a non-empty list of numbers"})
    try:
        vals = [float(x) for x in nums]
    except (TypeError, ValueError):
        return json.dumps({"ok": False, "error": "all items must be numbers"})
    out = {"count": len(vals), "sum": sum(vals), "mean": statistics.mean(vals),
           "median": statistics.median(vals), "min": min(vals), "max": max(vals),
           "range": max(vals) - min(vals)}
    if len(vals) >= 2:
        out["stdev_sample"] = statistics.stdev(vals)
        out["variance_sample"] = statistics.variance(vals)
        out["stdev_pop"] = statistics.pstdev(vals)
    return json.dumps({"ok": True, **{k: (round(v, 6) if isinstance(v, float) else v)
                                      for k, v in out.items()}}, ensure_ascii=False)


# ============================================================ random_gen (real randomness)
_RAND_OPS = ["uuid", "token", "int", "dice", "shuffle", "pick"]
RANDOM_GEN = {
    "type": "function",
    "function": {
        "name": "random_gen",
        "description": ("Generate real randomness (you can't — don't fake it). Ops: uuid, token "
                        "(url-safe, length n), int (in [low,high]), dice (n rolls of `high`-sided, "
                        "default 6), shuffle (a provided `items` list), pick (n random items from "
                        "`items`). Cryptographically-seeded."),
        "parameters": {
            "type": "object",
            "properties": {
                "op": {"type": "string", "enum": _RAND_OPS},
                "n": {"type": "integer", "description": "count/length (token length, dice count, picks)."},
                "low": {"type": "integer", "description": "int op: lower bound (default 0)."},
                "high": {"type": "integer", "description": "int op: upper bound (default 100); dice: sides."},
                "items": {"type": "array", "description": "list for shuffle/pick."},
            },
            "required": ["op"],
        },
    },
}


def random_gen(op: str = "uuid", n=None, low=None, high=None, items=None, **_) -> str:
    import uuid
    op = (op or "uuid").strip().lower()
    try:
        if op == "uuid":
            return json.dumps({"ok": True, "op": op, "result": str(uuid.uuid4())})
        if op == "token":
            length = max(4, min(int(n) if n else 24, 128))
            return json.dumps({"ok": True, "op": op, "result": secrets.token_urlsafe(length)[:length]})
        if op == "int":
            a = int(low) if low is not None else 0
            b = int(high) if high is not None else 100
            if a > b:
                a, b = b, a
            return json.dumps({"ok": True, "op": op, "result": secrets.randbelow(b - a + 1) + a, "range": [a, b]})
        if op == "dice":
            count = max(1, min(int(n) if n else 1, 100))
            sides = max(2, int(high) if high else 6)
            rolls = [secrets.randbelow(sides) + 1 for _ in range(count)]
            return json.dumps({"ok": True, "op": op, "sides": sides, "rolls": rolls, "total": sum(rolls)})
        if op in ("shuffle", "pick"):
            if not isinstance(items, list) or not items:
                return json.dumps({"ok": False, "error": "provide `items` (a non-empty list)"})
            arr = list(items)
            if op == "shuffle":
                for i in range(len(arr) - 1, 0, -1):
                    j = secrets.randbelow(i + 1)
                    arr[i], arr[j] = arr[j], arr[i]
                return json.dumps({"ok": True, "op": op, "result": arr}, ensure_ascii=False)[:config.TOOL_RESULT_MAX_CHARS]
            k = max(1, min(int(n) if n else 1, len(arr)))
            picks = [arr.pop(secrets.randbelow(len(arr))) for _ in range(k)]
            return json.dumps({"ok": True, "op": op, "result": picks}, ensure_ascii=False)[:config.TOOL_RESULT_MAX_CHARS]
        return json.dumps({"ok": False, "error": f"unknown op '{op}' (see the op enum)"})
    except Exception as e:
        return json.dumps({"ok": False, "op": op, "error": f"{type(e).__name__}: {e}"[:150]})


# ============================================================ cost_status (schema only)
# The CALLABLE is injected per-request in api.py, because it needs this turn's live ledger + model.
# Advertised only when that closure is wired in (a tool-capable turn). See api.py.
COST_STATUS = {
    "type": "function",
    "function": {
        "name": "cost_status",
        "description": ("Check the running cost of THIS chat and the current model's price, plus "
                        "remaining service credits. Use it to stay cost-aware: if this session is "
                        "in deficit or on a pricey model, prefer a cheaper/free model (see "
                        "list_models) or suggest the user switch, and be economical with tool calls."),
        "parameters": {"type": "object", "properties": {}},
    },
}


# ==================================================== scheduled follow-ups (schemas; callables in api.py)
# Callables need the current conversation + key + ledger, so they're injected per-request in api.py.
# Only advertised on keyed (persisted) conversations — a follow-up needs somewhere to land.
SCHEDULE_FOLLOWUP = {
    "type": "function",
    "function": {
        "name": "schedule_followup",
        "description": ("Schedule yourself to run a task LATER and post the result into THIS "
                        "conversation (an agent-style follow-up). Use for 'check back in an hour', "
                        "'remind me tomorrow', or work that should continue after this reply. "
                        "One-shot, or recurring with a repeat count. You'll run it autonomously with "
                        "your tools; the user sees the result when they reopen the chat."),
        "parameters": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "The instruction to carry out at run time "
                                                          "(self-contained; the conversation is context)."},
                "delay": {"type": "string", "description": "When the first run happens, as a duration: "
                                                           "e.g. '90s', '30m', '2h', '1d'."},
                "every": {"type": "string", "description": "Optional: repeat interval (same format) for a "
                                                           "recurring follow-up, e.g. '1h'. Omit for one-shot."},
                "count": {"type": "integer", "description": "Optional: total number of runs for a recurring "
                                                            "follow-up (bounded). Ignored if `every` is omitted."},
            },
            "required": ["task", "delay"],
        },
    },
}
LIST_SCHEDULED = {
    "type": "function",
    "function": {
        "name": "list_scheduled",
        "description": "List this conversation-owner's scheduled follow-ups (id, task, when, status).",
        "parameters": {"type": "object", "properties": {}},
    },
}
CANCEL_SCHEDULED = {
    "type": "function",
    "function": {
        "name": "cancel_scheduled",
        "description": "Cancel a pending scheduled follow-up by its id (from list_scheduled).",
        "parameters": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]},
    },
}


def parse_duration(s: str) -> int | None:
    """'90s'/'30m'/'2h'/'1d' (or a bare number = seconds) -> seconds. None if unparseable."""
    s = (s or "").strip().lower()
    if not s:
        return None
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([smhd]?)", s)
    if not m:
        return None
    n = float(m.group(1))
    return int(n * {"": 1, "s": 1, "m": 60, "h": 3600, "d": 86400}[m.group(2)])


# ============= submit_contribution (schema built in api.py — callable needs conv/ip/rate-limit/token) ===
def submit_contribution_schema(allow_pr: bool = False) -> dict:
    """The tool schema, shaped by whether the server's token can open PRs (else issue-only)."""
    types = ["issue", "pull_request"] if allow_pr else ["issue"]
    how = ("as an ISSUE (complaint/request) or a proposal PULL REQUEST" if allow_pr
           else "as an ISSUE (complaints, requests, or a proposed capability — include any code and "
                "it goes in the issue for a maintainer to turn into a PR)")
    return {
        "type": "function",
        "function": {
            "name": "submit_contribution",
            "description": (f"File a complaint, or propose building/changing a TOOL, SKILL, or MCP "
                            f"integration on the PUBLIC free-chat-toolkit repo, on the user's behalf "
                            f"— {how}. You can include proposed `code`. IMPORTANT: you can only OPEN "
                            f"submissions — you can NEVER merge or accept them; a human maintainer "
                            f"reviews. A conversation reference hash is attached automatically. Mind "
                            f"the repo's out-of-bounds rules (no code sandbox, no exploitable/heavy-"
                            f"binary tools like ffmpeg, no compute offload — security & privacy first). "
                            f"Confirm with the user before submitting."),
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": types,
                             "description": "'issue' for a complaint/request/proposal."
                                            + (" 'pull_request' to open a proposal PR." if allow_pr else "")},
                    "category": {"type": "string", "enum": ["tool", "skill", "mcp", "other"],
                                 "description": "What kind of capability this concerns (default 'tool')."},
                    "title": {"type": "string", "description": "Short title of the complaint/suggestion."},
                    "body": {"type": "string", "description": "Details: what's wrong or what the capability should do, and why."},
                    "code": {"type": "string", "description": "Optional: proposed implementation — included for the maintainer to review."},
                },
                "required": ["type", "title", "body"],
            },
        },
    }


# ============================================================ frames_to_gif (Pillow — no ffmpeg)
_GIF_MAX_FRAMES = 40
_GIF_FRAME_MAX_BYTES = 5_000_000
_GIF_OUT_MAX_BYTES = 8_000_000
_GIF_MAX_DIM = 720
FRAMES_TO_GIF = {
    "type": "function",
    "function": {
        "name": "frames_to_gif",
        "description": ("Assemble a list of images (frames) into an animated GIF and return a URL to "
                        "it — closes the loop between image-generating models and short animations. "
                        f"Frames are public http(s) image URLs or data:image URLs (2-{_GIF_MAX_FRAMES}). "
                        "Bounded: frames are downscaled and the output size is capped."),
        "parameters": {
            "type": "object",
            "properties": {
                "frames": {"type": "array", "items": {"type": "string"},
                           "description": "Ordered image URLs or data:image URLs (at least 2)."},
                "fps": {"type": "number", "description": "Frames per second (default 8, 1-30)."},
                "loop": {"type": "integer", "description": "0 = loop forever (default), else loop count."},
                "max_size": {"type": "integer", "description": f"Max frame dimension in px (default 480, max {_GIF_MAX_DIM})."},
            },
            "required": ["frames"],
        },
    },
}


def _fetch_image_bytes(src: str):
    """Load raw image bytes from a data:image URL or a public http(s) URL (SSRF-guarded, capped).
    Returns (bytes, error). Kept separate from _fetch_raw, which decodes as text (corrupts binary)."""
    src = (src or "").strip()
    if src.startswith("data:image/"):
        try:
            b64 = src.split(",", 1)[1]
            raw = base64.b64decode(b64 + "=" * (-len(b64) % 4))
        except Exception:
            return None, "invalid data: URL"
        return (raw, None) if len(raw) <= _GIF_FRAME_MAX_BYTES else (None, "image too large")
    for _ in range(4):
        if not _url_is_public(src):
            return None, "must be a public http(s) image URL or a data:image URL"
        req = urllib.request.Request(src, headers={"User-Agent": "free-chat.ai/1.0", "Accept": "image/*,*/*"})
        try:
            r = urllib.request.build_opener(_NoRedirect).open(req, timeout=12)
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 303, 307, 308) and e.headers.get("Location"):
                src = urllib.parse.urljoin(src, e.headers["Location"])
                continue
            return None, f"HTTP {e.code}"
        except Exception as e:
            return None, type(e).__name__
        blob = r.read(_GIF_FRAME_MAX_BYTES + 1)
        return (blob, None) if len(blob) <= _GIF_FRAME_MAX_BYTES else (None, "image too large")
    return None, "too many redirects"


def frames_to_gif(frames=None, fps=8, loop=0, max_size=480, **_) -> str:
    if not isinstance(frames, list) or len(frames) < 2:
        return json.dumps({"ok": False, "error": "provide `frames`: a list of at least 2 image URLs or data:image URLs"})
    if len(frames) > _GIF_MAX_FRAMES:
        return json.dumps({"ok": False, "error": f"too many frames ({len(frames)}); max {_GIF_MAX_FRAMES}"})
    try:
        from PIL import Image
    except Exception:
        return json.dumps({"ok": False, "error": "image assembly is unavailable on this server"})
    Image.MAX_IMAGE_PIXELS = 8_000_000        # decompression-bomb guard (stricter than default)
    try:
        ms = max(16, min(int(max_size) if max_size else 480, _GIF_MAX_DIM))
    except (TypeError, ValueError):
        ms = 480
    imgs = []
    for i, f in enumerate(frames):
        raw, err = _fetch_image_bytes(f)
        if err:
            return json.dumps({"ok": False, "error": f"frame {i + 1}: {err}"})
        try:
            im = Image.open(io.BytesIO(raw))
            im.load()
            im = im.convert("RGBA")
        except Exception:
            return json.dumps({"ok": False, "error": f"frame {i + 1}: not a readable image"})
        im.thumbnail((ms, ms))
        imgs.append(im)
    size = imgs[0].size                       # GIF needs a consistent canvas — use the first frame's
    prepped = []
    for im in imgs:
        if im.size != size:
            im = im.resize(size)
        bg = Image.new("RGBA", size, (255, 255, 255, 255))    # flatten alpha on white
        bg.alpha_composite(im)
        prepped.append(bg.convert("RGB").convert("P", palette=Image.ADAPTIVE))
    try:
        dur = int(1000 / max(1.0, min(float(fps or 8), 30.0)))
    except (TypeError, ValueError):
        dur = 125
    try:
        lp = max(0, int(loop)) if loop is not None else 0
    except (TypeError, ValueError):
        lp = 0
    buf = io.BytesIO()
    try:
        prepped[0].save(buf, format="GIF", save_all=True, append_images=prepped[1:],
                        duration=dur, loop=lp, disposal=2, optimize=True)
    except Exception as e:
        return json.dumps({"ok": False, "error": f"GIF assembly failed: {type(e).__name__}"})
    data = buf.getvalue()
    if len(data) > _GIF_OUT_MAX_BYTES:
        return json.dumps({"ok": False, "error": f"resulting GIF is too large ({len(data) // 1024} KB); "
                           "use fewer frames or a smaller max_size"})
    from . import artifacts
    url = "/g/" + artifacts.put(data, "image/gif")
    return json.dumps({"ok": True, "url": url, "markdown": f"![animation]({url})",
                       "frames": len(prepped), "size_px": list(size), "bytes": len(data),
                       "fps": round(1000 / dur, 1)}, ensure_ascii=False)


# ============================================================ fetch_rendered (camoufox headless)
FETCH_RENDERED = {
    "type": "function",
    "function": {
        "name": "fetch_rendered",
        "description": ("Fetch a page with a real headless browser that RUNS JavaScript, then return "
                        "its readable text. Use ONLY when fetch_url returns an empty shell / a JS-"
                        "gated SPA (fetch_url is much faster — try it first). Heavy and rate-limited: "
                        "one render at a time server-wide; may reply that the server is busy — if so, "
                        "retry shortly or fall back to fetch_url."),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Absolute public http(s) URL to render."},
                "max_chars": {"type": "integer", "description": f"Max characters of text to return "
                                                               f"(default {config.RENDER_MAX_CHARS}, max 40000)."},
            },
            "required": ["url"],
        },
    },
}


def fetch_rendered(url: str = "", max_chars: int = 0, **_) -> str:
    from . import render
    u = (url or "").strip()
    if not _url_is_public(u):
        return json.dumps({"ok": False, "error": "URL must be a public http(s) address"})
    if not render.available():
        return json.dumps({"ok": False, "error": "rendered fetch is not available on this server"})
    html, final, err = render.render(u)
    if err:
        return json.dumps({"ok": False, "final_url": final, "error": err}, ensure_ascii=False)
    text = _html_to_text(html) if html else ""
    if not text.strip():
        return json.dumps({"ok": False, "final_url": final, "error": "no readable text after rendering"},
                          ensure_ascii=False)
    try:
        cap = max(500, min(int(max_chars) if max_chars else config.RENDER_MAX_CHARS, 40000))
    except (TypeError, ValueError):
        cap = config.RENDER_MAX_CHARS
    header = {"ok": True, "final_url": final, "rendered": True,
              "chars": min(len(text), cap), "truncated": len(text) > cap}
    return json.dumps(header, ensure_ascii=False) + "\n\n" + text[:cap]


# ============================================================ registry
def available() -> bool:
    # The stdlib tools are always available; web_search additionally needs SearXNG. Tools are on
    # whenever any work — which is always true here.
    return True


def tools_for_model() -> list:
    """Advertise web_search only when SearXNG is configured; the rest are always available."""
    t = [FETCH_URL, HTTP_API, EXTRACT_METADATA, EXTRACT_LINKS, RSS_FETCH, UNSHORTEN_URL,
         WIKIPEDIA, GEOCODE, JSON_QUERY, DIFF_TEXT, REGEX_TEST, ENCODE_DECODE, STATS,
         RANDOM_GEN, FRAMES_TO_GIF, CALCULATOR, CURRENT_DATETIME, LIST_MODELS, ASK_MODEL]
    if config.SEARXNG_URL:
        t = [WEB_SEARCH] + t
    try:
        from . import render
        if render.available():                 # camoufox JS-rendered fetch — only when installed
            t.append(FETCH_RENDERED)
    except Exception:
        pass
    return t


TOOLS = [WEB_SEARCH, FETCH_URL, HTTP_API, EXTRACT_METADATA, EXTRACT_LINKS, RSS_FETCH,
         UNSHORTEN_URL, WIKIPEDIA, GEOCODE, JSON_QUERY, DIFF_TEXT, REGEX_TEST, ENCODE_DECODE,
         STATS, RANDOM_GEN, FRAMES_TO_GIF, CALCULATOR, CURRENT_DATETIME, LIST_MODELS, ASK_MODEL]
REGISTRY = {"web_search": web_search, "fetch_url": fetch_url, "http_api": http_api,
            "extract_metadata": extract_metadata, "extract_links": extract_links,
            "rss_fetch": rss_fetch, "unshorten_url": unshorten_url, "wikipedia": wikipedia,
            "geocode": geocode, "json_query": json_query, "diff_text": diff_text,
            "regex_test": regex_test, "encode_decode": encode_decode, "stats": stats,
            "random_gen": random_gen, "frames_to_gif": frames_to_gif, "fetch_rendered": fetch_rendered,
            "calculator": calculator, "current_datetime": current_datetime,
            "list_models": list_models, "ask_model": ask_model}
