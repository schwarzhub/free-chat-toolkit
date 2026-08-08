# 📚 Explainer Series — Foundations of Modern AI

A curated set of **technical literature reviews** on how modern AI systems retrieve, reason, optimize,
and improve themselves. Each entry is a standalone document that also links into a larger narrative.

These are not short, hype-driven explainers. Each is closer to the **related-work section of a good
survey — with worked code** and a verified citation for every claim. They serve two audiences at once:

- **Humans** learning the field, from a curated, accurate starting point.
- **The free-chat agents themselves** — an explainer is *pre-assembled literature* an agent can retrieve
  and ground its answers on, instead of re-deriving a survey from scratch.

The governing standard (format, tiers, and the **citation-integrity gate**) is in
[`../proposals/explainer-series-framework.md`](../proposals/explainer-series-framework.md). The pipeline
to scale authoring is in
[`../proposals/explainer-automation-tooling.md`](../proposals/explainer-automation-tooling.md).

**New here? Begin with Tier A, then follow a "read next" path below.**

## How to read this series

Each explainer is tagged with an **audience tier**:

| Tier | Level | Assumes | Length |
|------|-------|---------|--------|
| **A** | Beginner | General technical literacy; no ML background | 1,500–2,500 words |
| **B** | Intermediate | Knows what a neural net / embedding is | 2,500–4,000 words |
| **C** | Advanced | Comfortable with transformers, gradients, RL | 3,000–5,000 words |

Every explainer opens with an abstract, defines its terms, cites every claim to a **real, resolvable
source** (arXiv/DOI), and closes with open problems, relationship-labeled connections, and a full
reference list.

## The explainers

| # | Tier | Explainer | ~Time | In one line | Status |
|---|------|-----------|-------|-------------|--------|
| 1 | A | What Is an LLM? | 15 min | Tokens, pretraining, and why next-token prediction is powerful | 🔜 planned |
| 2 | B | [A History of AI in 3 Eras](history-of-ai.md) | 30 min | Symbolic → neural → transformer, and why the lineage matters | ✅ published |
| 3 | B | [Retrieval-Augmented Generation](rag.md) | 25 min | Retrieval-augmented generation, end to end | ✅ published |
| 4 | B | [Automated Prompt Optimization](automated-prompt-optimization.md) | 25 min | APE → OPRO → DSPy: finding good prompts without hand-tuning | ✅ published |
| 5 | C | [Reasoning & Chain-of-Thought](reasoning-and-chain-of-thought.md) | 30 min | How LLMs "think" at inference: CoT, self-consistency, ToT/GoT | ✅ published |
| 6 | C | [Recursive Self-Improvement](rsi.md) | 30 min | Self-improving loops, mesa-optimization, and the risks | ✅ published |
| 7 | C | [From Retrieval to Reasoning](from-retrieval-to-reasoning.md) | 35 min | The synthesis that ties retrieval, reasoning, and RSI together | ✅ published |

*Status: ✅ published · ✍️ in-review · 🔜 planned. Every published entry has passed the citation gate
(`papers_verified: true`).*

## Recommended paths

**Fast Track (~2 hours)** — the working knowledge, in order:
RAG (B) → Automated Prompt Optimization (B) → Reasoning & Chain-of-Thought (C) →
From Retrieval to Reasoning (C)

**Deep Dive (~6 hours)** — the full story, in order:
A History of AI in 3 Eras (B) → RAG (B) → Automated Prompt Optimization (B) →
Reasoning & Chain-of-Thought (C) → Recursive Self-Improvement (C) → From Retrieval to Reasoning (C)

## How the pieces connect

- **RAG** and **Automated Prompt Optimization** are two complementary ways to improve an LLM system
  *without retraining* it.
- **Reasoning / Chain-of-Thought** is what those systems do at inference time; prompt optimization can
  *discover* good reasoning formulations.
- **Recursive Self-Improvement** generalizes the pattern: a system that optimizes its own prompts,
  retrieval, and reasoning is running a self-improvement loop — with the alignment risks that entails.
- **A History of AI** explains why this lineage exists; **From Retrieval to Reasoning** is the synthesis
  that unifies all of the above.

## Contributing an explainer

1. Read [`../proposals/explainer-series-framework.md`](../proposals/explainer-series-framework.md) first.
2. Copy the frontmatter template; fill in `tier`, `prerequisites`, `reading_time`, `papers_cited`,
   `papers_verified`, `version`, and `connections[]` (each with a *relationship* label).
3. Follow the seven-section skeleton (Abstract → Why It Matters → Core Concepts → The Literature →
   Worked Code → Open Problems → Connections & Further Reading).
4. **Citation gate:** every paper claim carries a real, resolvable citation (arXiv/DOI), *checked to
   resolve and match*. Set `papers_verified: true` only after checking each one. No invented author-year
   tags, ever.
5. Start at `version: 1.0`; use semantic versioning for later edits.
6. Add your row to the table above and to the reading paths.
