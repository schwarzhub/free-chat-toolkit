# free-chat-toolkit

The **capability toolkit** for [free-chat.ai](https://free-chat.ai) — the **tools, skills, and MCP
integrations** its models can use, and the place to propose or improve them. The actual
implementations live in [`tools/`](tools).

Anyone — or any model, from within free-chat — can suggest **building or changing a tool, a skill, an
MCP integration, or a related capability**, as an issue or a pull request.

## Concepts — breaking the jargon

These words get used interchangeably; they're different things.

### Tool  *(a.k.a. function / tool call)*
A **function the model can call.** Two parts:
- a **schema** — a name, a plain-English description, and typed parameters (JSON Schema). This is all
  the model sees; it reads the descriptions and decides *when* to call and *with what arguments*.
- a **function** — the code that runs when the model calls it, returning a result that's fed back in.

The loop: the model emits a structured call like `web_search(query="…")` → the app runs the real
function → the result re-enters the model's context → the model answers. That's literally what
[`tools/tools.py`](tools/tools.py) is — `{schema, callable}` pairs. **A tool is the app *doing* something.**

### Skill
**Instructions, not code.** A skill is a packaged **description** (and sometimes example files) that
teaches the model *how* to approach a task using capabilities it already has — a reusable procedure or
playbook the model reads. Nothing new executes; there's no function call with typed arguments. **A skill
is the model *knowing how* to do something.**

### MCP  *(Model Context Protocol)*
**A standard for exposing tools and data to models — not a tool itself.** An MCP *server* wraps an
external system (an API, a database, a service) and advertises its capabilities as callable tools; an
MCP *client* (the app) discovers and calls them. **MCP is the plumbing that turns an external API into
tools.** Proposing an MCP means proposing to connect free-chat to such a server. *(Note: free-chat uses
its own tool registry today; first-class MCP-client support is a larger, forward-looking piece.)*

### In one line
- **Tool** = a function call — a schema + the code the app runs.
- **Skill** = instructions the model reads — no new code runs.
- **MCP** = a protocol for advertising an external API as callable tools.

*(Related terms: an **artifact** is a file the app produced and serves by URL; an **agent** is a model
given tools + a goal that runs a multi-step loop. Both build on tools.)*

## How to contribute

Propose or change a **tool, skill, or MCP integration**:

1. **From within free-chat** — ask the assistant to file it; it opens an **issue** here (and can include
   proposed code inline). It can only *open* issues — never merge or accept.
2. **Directly on GitHub** — open an **issue**, or send a **pull request** (code under [`tools/`](tools),
   or a written proposal under [`proposals/`](proposals)).

Every in-chat submission carries an opaque **conversation reference hash** — a `sha256` fingerprint of
the conversation that suggested it. No private conversation content is published; the hash only lets a
maintainer trace/deduplicate a submission.

## Out of bounds — for this stage of development

**Security and privacy come first.** free-chat is a public, account-less service on a small shared box,
so some capabilities are **explicitly off the table right now** (to be revisited as the infrastructure
matures):

- **No code-execution sandbox.** No running arbitrary user/model code (Python/JS/shell) on the box —
  too big and too risky at this stage. *(The safe future route is WASM/Pyodide or a separate isolated
  worker, not an on-box tool.)*
- **No exploitable / heavy-binary tools over untrusted input** — e.g. **ffmpeg** on arbitrary media.
  Large attack surface (CVEs, decompression/CPU bombs). Bounded **pure-library** operations only.
- **No compute offload or heavy background jobs** on the public box — no mining, no long-running or
  resource-hungry processing. Heavy work belongs **off-box** (a fleet worker), not here.
- **No paid dependencies.** A tool, API, or MCP that requires **direct payment** — a paid API key,
  metered/per-call billing, a paid MCP host — will almost certainly **not** be accepted: it would bill
  the operator per use and break the free, ad-funded model. **Free APIs are welcome** (like the free
  ones already wired in — OpenStreetMap, Wikipedia, …), and a clean **MCP that wraps a *free* API** to
  make it easier to use is a great contribution.
- **No silent access to third-party accounts**, no send-without-approval, no tracking/profiling, no
  scrapers-for-abuse, and no exploit/malware helpers.

Good contributions are **bounded** (size/time/rate caps), **SSRF-safe**, return **structured JSON** or
stable **artifact URLs** (not huge inline blobs), and never weaken the privacy promise. When in doubt,
the more contained / less-privileged option wins.

## How review works

The in-chat assistant can **only open issues** — it can **never merge, accept, or close** anything.
Every change is reviewed and merged by a **human maintainer** (enforced in the app with a create-only,
least-privilege token, and by branch protection on `main`).

## Layout

Contributions are organized by kind:

- [`tools/`](tools) — the actual **tool** implementations (schema + function), synced from the app.
- [`skills/`](skills) — **skills** (instructions/procedures the model reads). *None yet — propose one.*
- [`mcps/`](mcps) — **MCP integrations** (connecting an external server's tools). *None yet — propose one.*
- [`TOOLS.md`](TOOLS.md) — human-readable catalog of the tools live today.
- [`proposals/`](proposals) — longer written proposals for any of the above.

Licensed under [MIT](LICENSE).
