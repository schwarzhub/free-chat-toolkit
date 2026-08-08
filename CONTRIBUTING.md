# Contributing

Propose or change a **tool, skill, or MCP integration** (see the [concepts](README.md#concepts--breaking-the-jargon)
in the README, and the [out-of-bounds](README.md#out-of-bounds--for-this-stage-of-development) list — read it first).

## Via free-chat (in-chat)
Ask the assistant to file a complaint or propose a capability. It opens an **issue** here — it cannot
open PRs, merge, or accept anything (by design). If it drafts an implementation, the code is included
in the issue for a maintainer to review and turn into a change.

Every in-chat submission includes a **conversation reference hash** (see the README) — an opaque
fingerprint, no private content.

### Recipe & file contributions must embed the source
Any submission that claims to contribute a **recipe, template, or file** (`submit_contribution` with
`category: recipe`, or any "here are N templates/scripts" issue) **must include the complete, runnable
source inline in the issue body** — one fenced code block per file, each labeled with its proposed path
(e.g. `recipes/web-templates/dashboard.html`). The assistant cannot push files or open PRs, so a
*description* of the deliverable is not the deliverable.

**Pre-submit self-check:** before filing, confirm every file named in the issue actually appears as a
code block in the body. If the code can't be included, say so plainly and don't claim to have
contributed it — description-only recipe/file issues are incomplete and may be closed by a maintainer
pointing back to this rule.

### Explainer contributions must pass the citation gate
An **explainer** (a `explainers/*.md` literature review) is only accepted when **every citation resolves
to a real source** (arXiv/DOI) and matches its claim — see
[`proposals/explainer-series-framework.md`](proposals/explainer-series-framework.md). No invented
author-year tags, method names, or arXiv IDs. Set `papers_verified: true` only after each reference has
been checked. Drafts with unverifiable citations are held, not published.

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
