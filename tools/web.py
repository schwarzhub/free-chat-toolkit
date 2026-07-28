"""web tools (schemas + callables). Part of the free-chat tool registry."""
from ._base import *  # noqa: F401,F403

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
    from .. import render
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

