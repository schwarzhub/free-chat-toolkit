---
name: research-paper-summary
description: Produce a rigorous, structured summary of a single research paper — foregrounding the claim, the research design, the identification strategy, and the threats to validity, not just the abstract.
when-to-use: The user gives you a paper (DOI, arXiv id, title, URL, or uploaded PDF) and wants to actually understand what it establishes — for a lit review, a reading group, a referee report, or their own work.
draws-on: fetch_url, read_document*, resolve_doi*, fetch_fulltext*, scholar_search*
status: authored
---

# Research Paper Summary

A good summary is not a shorter abstract. It reconstructs the paper's **argument** and states, plainly,
**what it does and does not establish** — with the research design and identification front and center.

## Get the paper (in order of preference)
1. If given a **DOI / arXiv id / title**, resolve it: `resolve_doi*` (metadata + abstract + references),
   then `fetch_fulltext*` for the open-access PDF/HTML. Fall back to `scholar_search*` to disambiguate a
   title, or `fetch_url` / `read_document*` for a URL or uploaded PDF.
2. Work from the **full text** whenever available — the abstract oversells and omits the caveats. If only
   the abstract is reachable, say so and mark the summary "abstract-only (design not verified)."
3. **Verify identity before summarizing.** Confirm the version (working paper vs published; arXiv v1 vs
   v3 — numbers change across versions), and check for a **retraction / correction / erratum**
   (`resolve_doi*` / Crossref flag these). Summarizing a retracted paper without flagging it is a failure.

## Read for structure, then write to this template
Extract these; if the paper doesn't answer one, write "not stated" (an informative absence).

- **Question & motivation** — the specific question, and the gap/puzzle it addresses.
- **Claim** — the central finding in one sentence, *with direction and magnitude* ("a 1 SD increase in X
  raises Y by ~3pp"), not "X affects Y." **Anchor the magnitude to a specific table/figure/line in the
  full text.** Abstract-only, or a number you can't point to → give the *direction* and write "magnitude
  not extracted." Never synthesize a plausible-looking coefficient — an unanchored number is the single
  likeliest place this skill fabricates.
- **Multi-study papers** (several experiments / many main tables): produce one *Design & Claim* block per
  study, then a synthesis — don't force the single-design template onto a multi-study paper.
- **Design & identification** — THE core of the summary. What kind of evidence is this
  (RCT / natural experiment / panel / cross-section / observational / simulation / theory)? What is the
  **identifying variation**, and what must be true for the estimate to be causal (the identifying
  assumptions)? Name the estimator (DiD, IV, RDD, matching, OLS, structural, …).
- **Data** — source, unit of analysis, N, time span, key measures and how they're operationalized.
- **Key results** — the 1–3 numbers that carry the paper, with uncertainty (CI/SE) and the main table/figure.
- **Robustness** — what alternative specifications, placebo/falsification tests, and sensitivity checks
  they run, and whether the result survives.
- **Threats to validity** — internal (confounding, selection, measurement, reverse causality), external
  (generalizability, sample), and statistical (power, multiple testing, p-hacking/forking-paths risk,
  fragile specifications). Be specific to *this* paper.
- **Contribution & scope** — what it adds vs. prior work, and the boundary of the claim.
- **Your verdict** — is the central claim well-supported by the evidence presented? Where is it strongest
  and weakest? What single additional test would most change your confidence?

## Output
Lead with a 2–3 sentence plain-language **bottom line** (claim + how convincing), then the template as a
tight bulleted brief. Include a one-line **citation** (resolve it — don't fabricate) and a link to the
source used. Keep it to ~1 page; a summary that can't be skimmed has failed.

## Guardrails
- **Never invent numbers, quotes, or citations.** If you couldn't read the full text, say what you're
  inferring vs. what you verified.
- Distinguish **what the authors claim** from **what the evidence shows** — the gap between them is often
  the most useful thing in the summary.
- Report the design honestly: correlational evidence described as causal is the most common failure, and
  the thing a careful reader most needs flagged.
