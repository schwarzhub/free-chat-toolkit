# Contributing

Propose or change a **tool, skill, or MCP integration** (see the [concepts](README.md#concepts--breaking-the-jargon)
in the README, and the [out-of-bounds](README.md#out-of-bounds--for-this-stage-of-development) list — read it first).

## Via free-chat (in-chat)
Ask the assistant to file a complaint or propose a capability. It opens an **issue** here — it cannot
open PRs, merge, or accept anything (by design). If it drafts an implementation, the code is included
in the issue for a maintainer to review and turn into a change.

Every in-chat submission includes a **conversation reference hash** (see the README) — an opaque
fingerprint, no private content.

## Directly on GitHub
- Open an **issue** with your idea or bug, or
- Send a **pull request** (fork → branch → PR):
  - a **tool** → code under `tools/`, following the existing `{schema, callable(**args) -> str}` pattern;
  - a **skill** or **MCP integration**, or any longer write-up → a file under `proposals/`.

Keep contributions **bounded** (size/time/rate caps), **SSRF-safe**, and returning structured JSON or
artifact URLs over huge blobs. Nothing in the out-of-bounds list.

## Review
A maintainer triages issues/PRs and implements accepted capabilities in the free-chat app. Thanks for
contributing!
