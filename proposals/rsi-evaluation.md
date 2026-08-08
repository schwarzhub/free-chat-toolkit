# Proposal: An evaluation harness for the RSI / prompt-optimization loop

**Status:** proposed
**Source issue:** #78 (originally mislabeled `[skill]` — it is an eval-harness spec, not a user playbook)
**Relates to:** [`../explainers/automated-prompt-optimization.md`](../explainers/automated-prompt-optimization.md)
(the literature), [`explainer-automation-tooling.md`](explainer-automation-tooling.md) (the citation gate
uses the same "measure, don't vibe" discipline), issue #77

## Why

free-chat's orchestrator participates in a self-improvement loop — it optimizes its own prompts, pipeline
structure, and tool-use patterns. **An RSI loop without a benchmark is just tweaking.** To claim an
optimized prompt is *better*, we need a measurable, repeatable evaluation with explicit accept/reject and
regression criteria. The prompt-optimization literature (OPRO, APE, DSPy — see the explainer) already
provides well-characterized protocols; this proposal curates them into a concrete harness scoped to the
toolkit's cost norms.

## Benchmark suite

A small, diverse suite chosen to catch cross-domain regressions, run cheaply, and give low-variance
signal:

| Benchmark | Measures | Metric | Role | Source (verify before wiring) |
|-----------|----------|--------|------|-------------------------------|
| **BIG-Bench Hard** (27 tasks) | reasoning/math/logic breadth | mean acc + worst-3-task acc | primary; regression net | OPRO arXiv:2309.03409, APE arXiv:2211.01910 |
| **Instruction Induction** (24 tasks) | meta-level: generating valid instructions | exact-match | fast per-iteration gate | APE arXiv:2211.01910 |
| **GSM8K** | chain-of-thought / phrasing sensitivity | accuracy | low-variance signal | OPRO arXiv:2309.03409 |
| **HotPotQA** (dev) | multi-hop retrieve+reason pipeline | EM / F1 + #LM-calls | pipeline & cost | DSPy arXiv:2310.03714 |

(Citations carried over from #78; per the toolkit's citation discipline, verify each resolves and matches
before this proposal is acted on.)

## Protocol

- **Tiered, cost-gated** so most iterations are cheap:
  1. *Smoke* — a rotating sample (e.g. 5 Instruction-Induction tasks, ~200 examples) every iteration.
     Gate: proceed only if ≥ a threshold (e.g. 75% EM).
  2. *Full* — the whole suite, only when the smoke tier passes.
- **Accept criterion:** a candidate prompt/pipeline is accepted only if the **mean improves AND no single
  task regresses beyond a margin** (e.g. >5 pp). This is the regression net — a gain on task A that
  silently breaks task B is rejected.
- **Report:** per-task deltas vs. the incumbent, the worst-N tasks, and **cost** (LM calls / tokens per
  item) — a cheaper prompt at equal quality is an improvement.
- **Rollback:** keep the incumbent's scores as the baseline of record; any deployed candidate that later
  underperforms it on a re-run is rolled back.

## Cost policy (toolkit norms)

The harness spends real tokens per iteration. It **must** run its model calls through the free/cheap-tier
policy — no paid models without sign-off — and cache/subsample aggressively (the tiered gate exists for
this). A full-suite run is the exception, not every iteration.

## Scope note

Much of this is free-chat **application** dev direction (it optimizes the running app's own prompts), not
a user-invokable toolkit capability. The reusable, in-charter pieces are: (a) the **benchmark loaders +
scorers** as bounded `tools/` or a `run_code` recipe, and (b) an `evaluate-prompt` **skill** that runs the
tiered protocol and reports the accept/reject decision. The app-side wiring (which meta-prompt is live,
deployment gating) belongs in the free-chat repo. A maintainer should split accordingly.
