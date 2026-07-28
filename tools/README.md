# tools/ — the actual tool implementations

The real source behind [`../TOOLS.md`](../TOOLS.md), vendored from the live free-chat app. This is a
**synced snapshot** (the app is the source of truth); it lives here so you can read and propose changes
to real code. See [what a tool is](../README.md#what-is-a-tool) for the model.

- **`tools.py`** — the registry. Every tool is an OpenAI-style JSON **schema** + a
  `callable(**args) -> str`, collected into `TOOLS` / `REGISTRY` / `tools_for_model()`. Most tools are
  pure-stdlib or use one shared **SSRF-guarded** HTTP fetcher; results are string-in / string-out and
  size-capped.
- **`render.py`** — `fetch_rendered` (camoufox stealth headless Firefox), for JS-rendered SPAs. Heavy,
  so it's **box-contention-aware**: one render at a time box-wide, and it refuses under memory/load pressure.
- **`artifacts.py`** — the ephemeral in-memory artifact store (e.g. `frames_to_gif` output); FIFO +
  size cap + TTL, no disk, served same-origin at `/g/<id>`.
- **`github.py`** — the **create-only** GitHub client behind `submit_contribution` (opens issues; there
  is deliberately no merge/close endpoint).

## Notes for contributors

- These files import a few app internals (`from . import config`, `providers`, `models`, `artifacts`,
  `render`), so they don't run standalone here — treat this as the reference for review + PRs; a
  maintainer ports accepted changes into the app.
- **Context-bound tools** (`cost_status`, the ledger-charging `ask_model`, `schedule_followup` /
  `list_scheduled` / `cancel_scheduled`, `submit_contribution`) need the live conversation / key /
  ledger, so their **schemas** live in `tools.py` but their **callables** are injected per-request in the
  app's `api.py`.
- To propose a new tool: add a `{schema, callable(**args) -> str}` following the existing pattern —
  keep it string-in/string-out, **bounded** (size/time/rate), and **SSRF-safe**. Prefer structured JSON
  and stable artifact URLs over huge inline blobs.
