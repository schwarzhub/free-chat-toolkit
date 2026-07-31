"""Tool registry — assembled from the category modules.

Split into modules (web / data / knowledge / media / modeltools / schemas + the shared `_base`) so
that (a) new tools land as clean, reviewable files, and (b) a **subset** can be advertised per turn
instead of paying context for every schema at once — see `GROUPS` and `tools_for_model(groups=...)`.

The context-bound tools (`cost_status`, the ledger-charging `ask_model`, `schedule_*`,
`submit_contribution`) keep their *schemas* here but are wired per-request in `api.py`.

Public interface used by the rest of the app: `TOOLS`, `REGISTRY`, `tools_for_model()`, `available()`,
plus `run_ask_model`, `parse_duration`, `submit_contribution_schema`, and the context-bound schema
constants (`COST_STATUS`, `SCHEDULE_FOLLOWUP`, `LIST_SCHEDULED`, `CANCEL_SCHEDULED`).
"""
from .. import config

from .web import (WEB_SEARCH, web_search, FETCH_URL, fetch_url, HTTP_API, http_api,
                  EXTRACT_METADATA, extract_metadata, EXTRACT_LINKS, extract_links,
                  RSS_FETCH, rss_fetch, UNSHORTEN_URL, unshorten_url,
                  FETCH_RENDERED, fetch_rendered)
from .knowledge import WIKIPEDIA, wikipedia, GEOCODE, geocode
from .data import (JSON_QUERY, json_query, DIFF_TEXT, diff_text, REGEX_TEST, regex_test,
                   ENCODE_DECODE, encode_decode, STATS, stats, RANDOM_GEN, random_gen,
                   CALCULATOR, calculator, CURRENT_DATETIME, current_datetime)
from .media import FRAMES_TO_GIF, frames_to_gif
from .modeltools import (LIST_MODELS, list_models, ASK_MODEL, ask_model, run_ask_model)
from .schemas import (COST_STATUS, SCHEDULE_FOLLOWUP, LIST_SCHEDULED, CANCEL_SCHEDULED,
                      submit_contribution_schema, parse_duration, RUN_CODE, RUN_LOCAL, LIST_TOOLS)

# Category groups → advertise a subset instead of everything. Keys are stable; values are the
# schemas that are always safe to show. Gated tools (web_search needs SearXNG, fetch_rendered needs
# camoufox) are added in tools_for_model(). This is the hook for a future per-turn tool selector.
GROUPS = {
    "web":       [FETCH_URL, HTTP_API, EXTRACT_METADATA, EXTRACT_LINKS, RSS_FETCH, UNSHORTEN_URL],
    "knowledge": [WIKIPEDIA, GEOCODE],
    "data":      [JSON_QUERY, DIFF_TEXT, REGEX_TEST, ENCODE_DECODE, STATS, RANDOM_GEN,
                  CALCULATOR, CURRENT_DATETIME],
    "media":     [FRAMES_TO_GIF],
    "models":    [LIST_MODELS, ASK_MODEL],
}


def available() -> bool:
    return True


def tools_for_model(groups=None) -> list:
    """Advertised tool schemas. Default (groups=None) = all base tools, gated by availability —
    identical to the pre-split behaviour. Pass a subset of GROUPS keys to advertise only some
    categories (the hook for not sending every schema every turn)."""
    keys = list(GROUPS) if groups is None else [g for g in groups if g in GROUPS]
    web_on = groups is None or "web" in keys
    t = []
    for k in keys:
        t.extend(GROUPS[k])
    if web_on and config.SEARXNG_URL:               # web_search only when SearXNG is configured
        t = [WEB_SEARCH] + t
    if web_on:                                       # fetch_rendered only when camoufox is installed
        try:
            from .. import render
            if render.available():
                t.append(FETCH_RENDERED)
        except Exception:
            pass
    return t


TOOLS = [WEB_SEARCH, FETCH_URL, HTTP_API, EXTRACT_METADATA, EXTRACT_LINKS, RSS_FETCH,
         UNSHORTEN_URL, WIKIPEDIA, GEOCODE, JSON_QUERY, DIFF_TEXT, REGEX_TEST, ENCODE_DECODE,
         STATS, RANDOM_GEN, FRAMES_TO_GIF, FETCH_RENDERED, CALCULATOR, CURRENT_DATETIME,
         LIST_MODELS, ASK_MODEL]

REGISTRY = {"web_search": web_search, "fetch_url": fetch_url, "http_api": http_api,
            "extract_metadata": extract_metadata, "extract_links": extract_links,
            "rss_fetch": rss_fetch, "unshorten_url": unshorten_url, "wikipedia": wikipedia,
            "geocode": geocode, "json_query": json_query, "diff_text": diff_text,
            "regex_test": regex_test, "encode_decode": encode_decode, "stats": stats,
            "random_gen": random_gen, "frames_to_gif": frames_to_gif, "fetch_rendered": fetch_rendered,
            "calculator": calculator, "current_datetime": current_datetime,
            "list_models": list_models, "ask_model": ask_model}
