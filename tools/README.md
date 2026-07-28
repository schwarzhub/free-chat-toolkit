# tools/ — the actual tool implementations

The real source behind [`../TOOLS.md`](../TOOLS.md), vendored from the live free-chat app (the app is
the source of truth; this is a synced snapshot for reading + PRs). See
[what a tool is](../README.md#tool--aka-function--tool-call).

Each tool is a JSON **schema** + a `callable(**args) -> str`. They're grouped into small modules so a
new tool lands as a clean, reviewable file — and so a **subset** can be advertised per turn instead of
every schema at once.

- **`__init__.py`** — assembles `TOOLS` / `REGISTRY` / `tools_for_model()` and the `GROUPS` map
  (web / knowledge / data / media / models) used to advertise a subset. Also handles gating
  (web_search needs SearXNG, fetch_rendered needs camoufox).
- **`_base.py`** — shared helpers every module imports: the **SSRF-guarded** HTTP fetcher, JSON
  size-capping (`_fit_json`), HTML→text, and the stdlib imports.
- **`web.py`** — web_search, fetch_url, http_api, extract_metadata/links, rss_fetch, unshorten_url, fetch_rendered.
- **`knowledge.py`** — wikipedia, geocode.
- **`data.py`** — json_query, diff_text, regex_test, encode_decode, stats, random_gen, calculator, current_datetime.
- **`media.py`** — frames_to_gif.
- **`modeltools.py`** — list_models, ask_model.
- **`schemas.py`** — schema-only for the **context-bound** tools (cost_status, schedule_*,
  submit_contribution) — their callables are injected per-request in the app's `api.py`.
- **`render.py`** — `fetch_rendered` (camoufox headless Firefox), box-contention-aware.
- **`artifacts.py`** — the ephemeral in-memory artifact store, served at `/g/<id>`.
- **`github.py`** — the **create-only** GitHub client behind `submit_contribution`.

## Notes for contributors

- These files import app internals (`from .. import config`, `providers`, `models`, …), so they don't
  run standalone here — treat this as the reference for review + PRs; a maintainer ports accepted
  changes into the app.
- To add a **tool**: drop a `{schema, callable(**args) -> str}` into the right module (or a new one)
  and register it in `__init__.py`. Keep it **string-in/string-out**, **bounded** (size/time/rate),
  **SSRF-safe**, and returning structured JSON / artifact URLs over huge blobs.
- Read the repo's [out-of-bounds](../README.md#out-of-bounds--for-this-stage-of-development) rules
  first — especially **no paid dependencies**.
