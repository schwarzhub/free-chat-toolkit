---
name: scoping-review
description: A rapid, reproducible-as-far-as-possible synthesis of a literature (aka literature-synthesis) — documented search, transparent screening, structured extraction, and an honest synthesis that foregrounds where the evidence converges and where it conflicts. NOT a PRISMA systematic review.
when-to-use: The user wants to understand the state of a literature ("what do we know about X?"), map it, or draft the related-work / review section — quickly and transparently, not with the machinery of a publishable systematic review.
draws-on: scholar_search*, resolve_doi*, fetch_fulltext*, ask_model, run_code
status: authored
---

# Scoping Review (literature synthesis)

> **Integrity banner — say this to the user.** This produces a **rapid / scoping review over open,
> key-free sources**. It is **NOT a PRISMA-compliant systematic review** and must **not** be described as
> one in a manuscript. A real systematic review needs comprehensive database coverage (often incl. paid:
> Web of Science, Scopus, PsycINFO), **dual independent** screening, a registered protocol (PROSPERO),
> and validated risk-of-bias instruments — none of which a single AI over free indexes provides. Borrow
> PRISMA's *transparency* as an aspiration; don't claim its *status*.

A defensible synthesis, not a vibes summary: make the **search documented**, the **inclusion criteria
explicit**, and the **synthesis traceable to sources**. State scope and limits honestly.

## 1. Scope & protocol (write this first)
- Frame the question precisely (population/context, variable, outcome, timeframe). A tight question is the
  difference between a review and a ramble.
- Fix **inclusion/exclusion criteria** up front (years, study types, methods, language, quality bar) so
  screening isn't post-hoc.

## 2. Documented search
- Run `scholar_search*` across sources (arXiv / Crossref / Europe PMC; Semantic Scholar for relevance)
  with recorded queries; snowball via `resolve_doi*` references + forward citations of key papers.
- **Log the search**: queries, sources, dates, hit counts. De-dupe by DOI. Report the funnel
  (found → after de-dup → screened → included).

## 3. Screen — and be honest about scale
- Title/abstract screen against the criteria, then full-text screen the survivors (`fetch_fulltext*`).
  Record why excluded items were excluded.
- **Screening-cap rule (critical):** you cannot reliably screen thousands of abstracts in-context. If
  hits exceed what you can actually read (state the cap, e.g. N=~100–200 after relevance ranking), screen
  the **top N** and say so explicitly — "screened top N of M by relevance." **Never report a funnel whose
  "screened" count implies work you didn't do.** A fabricated funnel number is as bad as a fabricated
  citation.

## 4. Structured extraction
- For each included paper, extract a **comparable row**: citation, question, design/identification, data
  (N, setting), key estimate (direction + magnitude + uncertainty), and a credibility note.
  (`research-paper-summary` is the per-paper subroutine.) Build the evidence table — it is the backbone.

## 5. Synthesize — and probe the inconsistencies
- **Where it converges**: findings that replicate across designs/settings, **weighted by credibility, not
  vote-counted** (a result holding in an RCT *and* a natural experiment beats five correlational echoes).
- **Where it conflicts** (the most valuable part): line up disagreements (opposite signs, magnitude gaps,
  definitional splits) and **characterize *why*** — populations, measures, identification, time periods,
  specification choices, or publication bias vs. a genuine open question. Don't average away a real
  disagreement.
- **Gaps & frontier**: what hasn't been tested, what the field most needs next.
- Use `ask_model` for a second model's synthesis of the same evidence table — a cross-check on *framing*
  (not an independent check of search/screening).

## 6. Optional quantitative synthesis (`run_code`)
- If the evidence table has comparable estimates + standard errors, a light **meta-analytic** layer is a
  few lines of numpy/scipy: a random-effects pooled estimate, heterogeneity (I²/τ²), a forest plot, and a
  funnel/Egger check for small-study/publication bias. This turns "the literature disagrees" into a
  measured statement — but only when effects are genuinely commensurable; say so if they aren't.

## Output
- A **narrative synthesis** organized by theme/finding (not paper-by-paper), each claim cited to the rows
  that support it. Lead with a bottom-line "state of the evidence," under the integrity banner.
- The **evidence table** + the **search log / funnel** (with the screening cap stated) so it's auditable.
- An explicit **scope-and-limits** note: what was searched, what wasn't, where coverage is thin.

## Guardrails
- **Every synthesized claim traces to sources** — cite the rows; never assert a field-level conclusion the
  table doesn't support, and never fabricate a citation or a funnel count.
- **Weight by credibility, don't vote-count** — five weak papers don't outweigh one clean design.
- **Coverage honesty** — a key-free search never hits everything (paywalls, non-indexed work, languages).
  State the corpus's boundaries; an overstated "the literature shows…" from a partial search is the trap.
- **Never let the user call this a systematic review** in a paper — see the banner.
