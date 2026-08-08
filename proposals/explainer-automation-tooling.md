# Proposal: Tooling & skills to produce explainers at scale (with the citation gate enforced)

**Status:** proposed
**Relates to:** [`explainer-series-framework.md`](explainer-series-framework.md) (the quality bar this
automates), [`../explainers/`](../explainers/) (the corpus), `research-tools.md` (the retrieval tools
this reuses), issues #77, #78, #81 (tooling ideas distilled here)

## The problem

The [Explainer Series framework](explainer-series-framework.md) sets a high bar: each explainer is an
academic literature review with worked code, and **every citation must resolve to a real source and match
its claim**. The first batch was authored by a fan-out of agents followed by an independent
citation-verification pass — that worked, but it was hand-driven. The motivating failure is real: earlier
drafts shipped a self-referential "Reese et al." cite, an invented "SAHOO" method, and a Self-Refine →
"Recursive Introspection" misattribution. **The citation gate cannot depend on an author remembering to
be careful; it must be enforced by a tool.**

This proposal specifies the tools and skills to produce explainers semi-automatically at that bar. The
first batch is the **exemplar** the pipeline is built to reproduce.

## The pipeline

```
scope → draft → extract citations → VERIFY each against a real source → revise/cut → gate → publish
                                          │
                                          └── the enforced gate: unverified cite ⇒ not published
```

Every stage maps to a capability. The verify stage is the one that must be a tool, not a vibe.

## Tools to build (`tools/`, `{schema, callable(**args) -> str}`)

1. **`verify_citation`** — the keystone. Input: a citation (arXiv id / DOI / title+authors) and the claim
   it supports. Resolves it against arXiv, Crossref/DOI, and Semantic Scholar; returns `{resolves: bool,
   title, authors, year, url, claim_supported: "yes|unclear|no", notes}`. Flags the known fabrication
   tells (author-surname-equals-acronym; self-referential author names; arXiv id that 404s; title
   mismatch). Key-free, bounded, SSRF-safe. **Reuses `resolve_doi` / `scholar_search` / `fetch_fulltext`
   already planned in [`research-tools.md`](research-tools.md) — build once, don't duplicate.**
2. **`extract_citations`** — parse a Markdown draft's References + inline cites into a normalized list
   (author, year, title, arXiv/DOI, the sentence each supports) so `verify_citation` can be mapped over
   it. Pure-library, deterministic.
3. **`citation_report`** — run `extract_citations` → `verify_citation` over a whole file and emit a
   pass/fail table + the exact lines to fix. This is the CI-style gate: a draft is publishable only when
   the report is all-green (drives the `papers_verified` frontmatter flag).

`verify_citation` + `citation_report` generalize beyond explainers — they are the grounding gate for *any*
cited output the assistant produces (this is the same concern as the app-side grounding work).

## Skills to add (`skills/`, playbooks)

1. **`write-explainer`** — the authoring playbook: how to scope a topic to the framework, structure the
   seven sections, source the primary literature (via `scholar_search`/`fetch_fulltext`), write worked
   code, and — before claiming done — run `citation_report` and fix every flag. Encodes the standard so
   an agent produces a framework-conformant draft without re-reading the whole proposal.
2. **`verify-citations`** — a standalone review playbook: given any drafted document, extract and check
   every citation, and return a correction list. Composes with `adversarial-review`. Usable on its own
   whenever fabricated citations are a risk.

## How it runs (the exemplar, generalized)

The batch that seeded `explainers/` used exactly this shape and should be the template for a `run_collect`
recipe or an orchestrated agent flow:

1. **Fan-out author** — one agent per explainer, each handed the framework + a topic scope, each
   web-verifying its own citations as it writes.
2. **Independent verify** — a separate pass (agent or `citation_report` tool) re-checks every citation
   against the source — *not trusting the author's self-report*. Anything that doesn't resolve or match is
   cut or corrected before publish.
3. **Gate** — only all-green drafts flip to `papers_verified: true` and `status: published` in the index.

Automating steps 1–3 behind `write-explainer` + `citation_report` turns "a maintainer ran a fan-out by
hand" into "the assistant drafts a new explainer and self-gates it," with a human maintainer approving the
merge.

## Scope & norms

All key-free and bounded (toolkit norms: no paid deps, SSRF-safe, rate-limited). The verification tools
lean on free scholarly APIs (arXiv, Crossref polite pool, Semantic Scholar, Europe PMC) already scoped in
`research-tools.md`. Nothing here executes on the box beyond bounded library parsing; retrieval/verify
network calls follow the same rules as the other research tools.

## Open questions for the maintainer

- Build `verify_citation` as a **new tool** or extend the planned `resolve_doi`? (Recommend: one resolver
  core, `verify_citation` as the claim-matching layer on top.)
- Should `citation_report` be wired as a **PR check** on `explainers/*.md` (a GitHub Action) so the gate
  is enforced mechanically on every contribution, not just in-chat ones?
