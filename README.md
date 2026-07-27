# free-chat-tools

Community-contributed **tool ideas and improvements** for [free-chat.ai](https://free-chat.ai) — the
tools its models can call (web search, fetch, JSON APIs, geocoding, stats, and more).

## How to contribute

1. **From within free-chat** — ask the assistant to suggest a tool or improvement, and it can open an
   **issue** or a **proposal pull request** here on your behalf.
2. **Directly on GitHub** — open an issue, or a PR that adds a file under [`proposals/`](proposals/).

## How review works (important)

**Submissions are proposals only.** The chat can *open* issues and PRs — it can **never merge, accept,
close, or otherwise act on them.** Every change is reviewed and merged by a **human maintainer**. This
is enforced in the app (create-only, least-privilege token) and by branch protection on `main`.

## Conversation reference hash

In-chat submissions carry a **conversation reference hash** — an opaque `sha256` fingerprint of the
model conversation that suggested the change. **No private conversation content is published**; the
hash only lets a maintainer trace/verify/deduplicate a submission. In-chat PRs land as
`proposals/<hash>.md`.

## Layout

- [`proposals/`](proposals/) — in-chat proposal PRs land here, one file per submission.
- [`TOOLS.md`](TOOLS.md) — catalog of the tools live on free-chat.ai today.

Licensed under [MIT](LICENSE).
