"""knowledge tools (schemas + callables). Part of the free-chat tool registry."""
from ._base import *  # noqa: F401,F403

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

