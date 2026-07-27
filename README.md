# free-chat-tools

Community-contributed **tool ideas and improvements** for [free-chat.ai](https://free-chat.ai) — the
tools its models can call (web search, fetch, JSON APIs, geocoding, stats, and more).

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

- [`TOOLS.md`](TOOLS.md) — catalog of the tools live on free-chat.ai today.
- [`proposals/`](proposals/) — a home for longer written proposals (used by direct contributors, and
  by in-chat pull requests if that path is ever enabled).

Licensed under [MIT](LICENSE).
