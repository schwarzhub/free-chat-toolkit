---
name: systematic-review
description: Build a review-article-style synthesis of a literature — a reproducible search, transparent screening, structured extraction, and an honest synthesis that foregrounds where the evidence converges and where it conflicts.
when-to-use: The user wants to understand the state of a literature ("what do we know about X?"), map it, or draft the related-work / review section — not just summarize one paper.
draws-on: scholar_search*, resolve_doi*, fetch_fulltext*, ask_model
status: authored
---

# Systematic Review

A defensible synthesis, not a vibes summary. Borrow the discipline of PRISMA even for a lightweight review:
make the **search reproducible**, the **inclusion criteria explicit**, and the **synthesis traceable to
sources**. State scope and limits honestly.

## 1. Scope & protocol (write this first)
- Frame the question precisely (population/context, intervention/variable, outcome, timeframe). A tight
  question is the difference between a review and a ramble.
- Fix **inclusion/exclusion criteria** up front (years, study types, methods, language, quality bar) so
  screening isn't post-hoc.

## 2. Reproducible search
- Run `scholar_search*` across sources (OpenAlex / Semantic Scholar / arXiv; add Europe PMC for biomed) with
  documented queries; snowball via `resolve_doi*` references + forward citations of key papers.
- **Log the search**: queries, sources, dates, hit counts. De-dupe by DOI. Report the funnel
  (found → after de-dup → screened → included) PRISMA-style so it's reproducible.

## 3. Screen
- Title/abstract screen against the criteria, then full-text screen the survivors (`fetch_fulltext*`).
  Record why excluded items were excluded. Note where you had to judge (borderline cases) — reviews live
  or die on screening transparency.

## 4. Structured extraction
- For each included paper, extract a **comparable row**: citation, question, design/identification, data
  (N, setting), key estimate (direction + magnitude + uncertainty), and a study-quality/credibility note.
  (`research-paper-summary` is the per-paper subroutine.) Build the evidence table — it is the backbone of
  the synthesis and makes conflicts visible.

## 5. Synthesize — and probe the inconsistencies
- **Where it converges**: findings that replicate across designs/settings, weighted by study quality (a
  result that holds in an RCT and a natural experiment is stronger than five correlational echoes).
- **Where it conflicts** (the most valuable part — the `literature-inconsistency-probe` mode): line up the
  disagreements (opposite signs, magnitude gaps, definitional splits) and **characterize *why*** —
  different populations, measures, identification, time periods, or specification choices; publication bias;
  or a genuine open question. Don't average away a real disagreement.
- **Gaps & frontier**: what hasn't been tested, what the field most needs next.
- Use `ask_model` to get a second model's independent synthesis of the same evidence table and reconcile —
  a cross-check against your own framing.

## Output
- A **narrative synthesis** organized by theme/finding (not paper-by-paper), each claim cited to the rows
  that support it. Lead with a bottom-line "state of the evidence."
- The **evidence table** (appendix) and the **search log / PRISMA funnel** so it's reproducible.
- An explicit **scope-and-limits** note: what was searched, what wasn't, and where coverage is thin.

## Guardrails
- **Every synthesized claim traces to sources** — cite the rows; never assert a field-level conclusion the
  table doesn't support, and never fabricate a citation.
- **Weight by credibility, don't vote-count** — five weak papers don't outweigh one clean design; say so.
- **Coverage honesty** — a key-free search never hits everything (paywalls, non-indexed work, languages).
  State the corpus's boundaries; an overstated "the literature shows…" from a partial search is the trap.
