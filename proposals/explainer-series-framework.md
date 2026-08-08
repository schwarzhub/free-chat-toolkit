# Proposal: The Explainer Series — a literature-review corpus for humans and agents

**Status:** adopted (initial build-out in progress)
**Source issues:** #88 (framework), #80/#82/#83/#84/#85/#86/#87 (content)
**Relates to:** [`../explainers/`](../explainers/) (the corpus this governs), `research-tools.md`,
`explainer-automation-tooling.md` (the pipeline that will scale this)

## What this is

A curated series of **technical literature reviews** on the foundations of modern AI systems — how they
retrieve, reason, optimize, and improve themselves. Each entry is a standalone document that also links
into a larger narrative.

These are **not** the short, hype-driven "explainers" common on the web. The bar is an **academic
literature review with worked code examples**: precise, defines its terms, organizes the primary
literature chronologically and thematically, cites every claim to a **real, linkable source**, and is
honest about open problems. The audience is *both* humans learning the field *and* the free-chat agents
themselves — an explainer is **pre-assembled literature** an agent can retrieve instead of re-deriving a
survey from scratch. They are also **exemplars**: the reference quality bar that the downstream
authoring/verification tooling (see `explainer-automation-tooling.md`) is built to reproduce.

## Why in this repo

The toolkit is where free-chat's *capabilities* live. A retrievable, verified literature corpus is a
capability: it grounds the agent's answers, seeds `scoping-review` / `research-paper-summary` skills with
vetted starting points, and gives the RAG tools a high-quality internal collection to index. The corpus
will eventually surface on the website too, but the **canonical, version-controlled source lives here**.

## Non-negotiable: citation integrity

The motivating failure: several submitted drafts contained **fabricated citations** — a self-referential
"Reese et al. 2023" (Reese is the assistant), an invented "SAHOO" method, misattributions (Self-Refine
cited as "Recursive Introspection"), and invented tool names. Publishing those would be worse than
publishing nothing.

Therefore every explainer must pass a **citation gate** before it lands:

- Every claim about a paper carries a citation to a **real, resolvable source** — an arXiv ID, DOI, or
  stable publisher URL. No bare author-year tags without a link.
- Each citation is **verified to resolve** and to **match the claim** (right authors, right title, right
  finding). Verification is done against the source (arXiv/DOI/Semantic Scholar), not from memory.
- Frontmatter carries `papers_verified: true` **only after** every reference has been checked. A draft
  that hasn't been fully verified stays `papers_verified: false` and is not published to the index as
  ✅.
- When a fact cannot be sourced, it is cut or explicitly marked as the author's synthesis — never dressed
  up as a citation.

## Format

Each explainer is one Markdown file at `explainers/<slug>.md` (kebab-case). Multi-part topics stay a
single file with sections. The filename + frontmatter are the canonical identity (issue titles are
mutable).

### Frontmatter (YAML)

```yaml
---
title: "Retrieval-Augmented Generation: A Literature Review"
slug: rag
tier: B                      # A beginner · B intermediate · C advanced
status: published            # planned | drafting | in-review | published
reading_time: 25 min
prerequisites: [what-is-an-llm]     # slugs of explainers assumed
series: foundations-of-modern-ai
series_order: 3
papers_cited: 22
papers_verified: true        # true ONLY after every citation is checked to resolve + match
version: 1.0
source_issue: 83
connections:                 # relationship-labeled cross-links (the navigation backbone)
  - to: automated-prompt-optimization
    relationship: "complementary — another way to improve an LLM system without retraining"
  - to: reasoning-and-chain-of-thought
    relationship: "downstream — what the retrieved context feeds into at inference"
---
```

### Body — the seven sections

1. **Abstract / TL;DR** — a real abstract: the problem, the arc of the literature, the takeaway. ~150 words.
2. **Why it matters** — the motivation and where it sits in a real system.
3. **Core concepts** — define every term on first use; the vocabulary the rest of the piece uses.
4. **The literature** — the heart. Primary sources organized chronologically and by theme, each with a
   verified citation. This should read like the related-work section of a good survey.
5. **Worked code** — minimal, runnable illustrations of the key methods (self-contained; no paid deps;
   inline any web assets per the artifact CSP). Code clarifies the mechanism the prose describes.
6. **Open problems** — honest limitations and unsettled questions, cited where possible.
7. **Connections & further reading** — the relationship-labeled links to sibling explainers, plus a
   curated **References** list (every cited work, with its arXiv/DOI link).

### Audience tiers

| Tier | Level | Assumes | Length |
|------|-------|---------|--------|
| **A** | Beginner | General technical literacy; no ML background | 1,500–2,500 words |
| **B** | Intermediate | Knows what a neural net / embedding is | 2,500–4,000 words |
| **C** | Advanced | Comfortable with transformers, gradients, RL | 3,000–5,000 words |

## Style

Academic register, active voice, no filler ("in recent years", "it's no secret that"). Define terms
before using them. Prefer concrete examples and numbers (report the actual benchmark deltas, with the
citation). State uncertainty plainly. Every figure/claim traceable to a source.

## The index

`explainers/README.md` is the living index and single source of truth for tiers, status, and the reading
paths. Adding an explainer means adding its row there.

## Downstream: automate it

Authoring one of these by hand is the exemplar; doing it at scale needs tooling. The companion proposal
[`explainer-automation-tooling.md`](explainer-automation-tooling.md) specifies the
draft → cite-extract → **verify-against-source** → revise pipeline (and the skills that drive it) so new
explainers can be produced to this bar semi-automatically, with the citation gate enforced by a tool
rather than by hand.
