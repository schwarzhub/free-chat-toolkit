# free-chat-tools

Community-contributed **tool ideas and improvements** for [free-chat.ai](https://free-chat.ai) — the
tools its models can call (web search, fetch, JSON APIs, geocoding, stats, and more). The actual
implementations live in [`tools/`](tools).

## What is a tool?

A **tool is a function the AI model can call.** Each tool is two things:

1. a **schema** — a name, a plain-English description, and typed parameters (JSON Schema). This is all
   the model sees. It reads the descriptions and decides *when* to use a tool and *with what arguments*.
2. a **function** — the code that runs when the model calls it. It takes the arguments, does the work
   (search the web, fetch a page, build a GIF…), and returns a result string that's fed back to the model.

So the loop is: the model emits a structured call like `web_search(query="…")` → the app runs the real
`web_search` function → the result goes back into the model's context → the model answers. In this repo
that's literally what [`tools/tools.py`](tools/tools.py) is — a set of `{schema, callable}` pairs.

**How that differs from nearby ideas:**

- A **skill** is *not* a function the model calls — it's **instructions**: a description (and sometimes
  example files) that teach the model *how* to approach a task using capabilities it already has. The
  model reads it; nothing new executes.
- **MCP** (Model Context Protocol) is *not* a tool itself — it's a **standard for exposing** an external
  system's tools and data to models. An MCP server essentially says "here is my API as a set of callable
  tools," and a model client can then discover and call them. MCP is the plumbing that *turns an API into
  tools*; a tool is the concrete function + schema on the other end.

In one line: **a tool is a function call (schema + code), a skill is a set of instructions, and MCP is a
protocol for advertising an API as callable tools.**

## How to contribute

1. **From within free-chat** — ask the assistant to file a complaint or suggest a tool/change, and it
   opens an **issue** here on your behalf. It can include a proposed implementation (code) right in the
   issue for a maintainer to turn into a change.
2. **Directly on GitHub** — open an **issue**, or send a **pull request** yourself.

## How review works (important)

The in-chat assistant can **only open issues** — it can **never merge, accept, close, or otherwise act
on anything.** Every change is reviewed and merged by a **human maintainer**. This is enforced in the
app (a create-only, issues-only, least-privilege token) and by branch protection on `main`.

## Conversation reference hash

In-chat submissions carry a **conversation reference hash** — an opaque `sha256` fingerprint of the
model conversation that suggested the change. **No private conversation content is published**; the
hash only lets a maintainer trace/verify/deduplicate a submission.

## Layout

- [`tools/`](tools) — the **actual tool implementations** (schema + function), synced from the app.
- [`TOOLS.md`](TOOLS.md) — human-readable catalog of the tools live on free-chat.ai today.
- [`proposals/`](proposals/) — a home for longer written proposals (used by direct contributors, and
  by in-chat pull requests if that path is ever enabled).

Licensed under [MIT](LICENSE).
