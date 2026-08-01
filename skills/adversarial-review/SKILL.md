---
name: adversarial-review
description: Run a paper (or draft) through a simulated peer-review panel — multiple distinct referees with different lenses, a meta-reviewer, and an accept/revise/reject decision — then turn it into an actionable revision plan.
when-to-use: Before submitting, the user wants a tough, realistic pre-review of their manuscript; or they want to pressure-test someone else's paper the way a journal would.
draws-on: ask_model, read_document*, diff_text
status: authored
---

# Adversarial Review

Simulate the review a strong journal would give — *diverse, skeptical, specific* — so weaknesses surface
before a real referee finds them. The value comes from **distinct perspectives**, not one model's opinion.

## 1. Intake
- Get the manuscript (`read_document*` / `fetch_url` / pasted text) and the target venue if any (it sets
  the bar and the criteria). Extract the claim, design, and contribution the way `research-paper-summary`
  does — a reviewer reads for the argument first.

## 2. Convene a panel (distinct referees, distinct lenses)
Use **`ask_model` to run each referee as a separate model/persona** so critiques are genuinely independent,
not one voice rephrased. Give each a lens and the standard referee brief (summary → strengths → major
concerns → minor concerns → recommendation). Suggested panel (pick 3–5 by field):
- **Methods/identification referee** — is the design sound? are the identifying assumptions credible and
  tested? are the stats right (power, multiple testing, spec fragility)?
- **Contribution/novelty referee** — what's actually new vs. prior work? is the framing honest?
- **Domain-expert referee** — does it get the substance, prior literature, and institutional facts right?
- **Reproducibility/data referee** — are data+code available and sufficient? could this be replicated?
  (pairs with `replicate-paper`).
- **Adversary / "reviewer 2"** — actively tries to reject: hunts the fatal flaw, the overclaim, the
  confound, the cherry-picked spec. Instructed to be harsh but fair.

Each returns a structured referee report and a recommendation (accept / minor / major / reject).

## 3. Meta-review
Synthesize the reports into a single **meta-review**: the consensus, the disagreements (and who's right),
the **major issues that must be fixed** vs. minor, and an overall editor-style decision with reasoning.
De-duplicate overlapping points; rank by how much each threatens the paper's central claim.

## 4. Revision plan (the deliverable)
Turn the meta-review into an actionable, prioritized plan:
- **Must-fix** (paper fails without it) → **Should-fix** → **Nice-to-have**, each with a concrete action
  and, where possible, the specific analysis/edit needed.
- Flag issues that need **new results** (a robustness check, a placebo test) vs. **new writing** (framing,
  clarity) — the former sets your timeline.
- Optionally iterate: after the user revises, re-run the panel and `diff_text` the critiques to show what
  was resolved (feeds `reviewer-response`).

## Guardrails
- **Distinct models/personas matter** — a single model wearing five hats converges to one view; spread
  referees across different models via `ask_model` so the criticism is real.
- **Calibrate to the venue** — a top-5 journal bar and a workshop bar are different reviews; don't apply
  crushing standards to a note, or a soft pass to a flagship submission.
- **Specific, not generic** — "add robustness checks" is useless; "the DiD needs a parallel-trends
  pre-period plot and a placebo on pre-treatment years" is a review. Reject generic feedback.
- This **simulates** review to improve the work; it is not, and must not be presented as, actual peer
  review or a substitute for it.
