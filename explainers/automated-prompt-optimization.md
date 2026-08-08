---
title: "Automated Prompt Optimization: From APE to OPRO to DSPy"
slug: automated-prompt-optimization
tier: B
status: published
reading_time: 25 min
prerequisites: [what-is-an-llm]
series: foundations-of-modern-ai
series_order: 4
papers_cited: 11
papers_verified: true
version: 1.0
source_issue: 85
connections:
  - to: rag
    relationship: "complementary — another way to improve an LLM system without retraining"
  - to: reasoning-and-chain-of-thought
    relationship: "generative — prompt optimization can discover good reasoning formulations"
  - to: rsi
    relationship: "instance-of — a self-improvement loop that optimizes its own prompts"
---

## Abstract

A frozen language model's behavior is largely determined by its prompt, yet prompts are usually
written by hand through trial and error. Automated prompt optimization (APO) replaces that manual
search with an algorithm. This review organizes the literature along two axes: the *optimization
space* (discrete natural-language instructions vs. continuous embedding vectors vs. programmatic
pipelines) and the *search strategy* (LLM-as-optimizer, beam search over textual gradients, tree
search, or gradient descent). Discrete methods — APE (Zhou et al. 2022), APO/ProTeGi (Pryzant et al.
2023), OPRO (Yang et al. 2023), and PromptAgent (Wang et al. 2023) — search over human-readable
instructions and can outperform expert-written prompts on a majority of tasks. Continuous methods —
Prefix-Tuning (Li & Liang 2021), Prompt Tuning (Lester et al. 2021), and P-Tuning v2 (Liu et al.
2022) — tune vectors by backpropagation and match fine-tuning while touching a tiny fraction of
parameters, at the cost of interpretability and white-box access. DSPy (Khattab et al. 2023) and its
MIPRO optimizer (Opsahl-Ong et al. 2024) generalize the problem from single prompts to compound
pipelines. The recurring takeaway: automated search finds prompts that humans would not, and it does
so cheaply enough to be a standard engineering step.

## Why it matters

Every deployed LLM system rests on prompts. A retrieval-augmented pipeline needs an instruction that
tells the model how to use retrieved context; an agent needs a system prompt that shapes its tool
use; a classifier needs a template that maps free text onto labels. These prompts are brittle.
Rewording an instruction, reordering few-shot examples, or swapping a synonym can move accuracy by
several points, and the best wording is rarely the one a human would guess. Kojima et al. (2022)
showed the extreme case: appending the single phrase "Let's think step by step" to a prompt raised
zero-shot MultiArith accuracy from 17.7% to 78.7% [Kojima 2022]. If a five-word change is worth 60
points, the space of prompts is worth searching systematically rather than by hand.

Automated prompt optimization is one of three complementary ways to improve an LLM system *without
retraining the base model*. Retrieval (see the [RAG](rag.md) explainer) changes what the model sees;
prompt optimization changes how it is asked; and reasoning-time methods (see
[Reasoning & Chain-of-Thought](reasoning-and-chain-of-thought.md)) change how it computes an answer.
Prompt optimization is often the cheapest lever: it requires no gradient access for the discrete
methods, runs against a black-box API, and produces artifacts (instructions, exemplars) a human can
read and audit. When the optimizer improves *its own* prompt in a loop, the method becomes a concrete,
bounded instance of recursive self-improvement (see [RSI](rsi.md)).

## Core concepts

**Prompt.** The full text supplied to a language model before it generates: a task *instruction*, any
*few-shot exemplars* (input–output demonstrations), and the actual input. Optimization can target any
of these components.

**Discrete (hard) prompt.** A prompt expressed as ordinary tokens — words a person can read. Searching
over discrete prompts means searching over strings, a combinatorial, non-differentiable space.

**Continuous (soft) prompt.** A sequence of real-valued vectors prepended in the model's embedding
space. These "virtual tokens" need not correspond to any real word, so they can be optimized by
gradient descent, but only if you can backpropagate through the model (white-box access).

**Optimization space vs. search strategy.** The *space* is what you are searching over (instruction
strings, exemplar sets, embedding vectors, or whole pipelines). The *strategy* is how you move through
it (LLM-proposed edits, beam search, tree search, evolutionary resampling, gradient descent). This
review's taxonomy is the cross-product of the two.

**Meta-prompt / LLM-as-optimizer.** A prompt given to a language model whose job is to *propose better
prompts*. It typically contains a task description and a trajectory of previously tried prompts with
their scores, and asks the model to generate a new candidate. The optimizer LLM and the LLM being
optimized may be the same model.

**Scorer.** A function that assigns a numeric quality to a candidate prompt, usually accuracy on a
held-out set of labeled examples. The scorer defines the objective; everything else is search.

**Teleprompter / compiler (DSPy term).** An optimizer that takes a declarative program of LM calls and
a metric, then searches for the instructions and demonstrations that maximize the metric — compiling
a high-level specification into concrete, tuned prompts.

## The literature

### Discrete instruction search

The discrete methods share a loop — generate candidate instructions, score them, and use the scores
to propose better ones — and differ in the search strategy that closes the loop.

**APE (Zhou et al. 2022).** *Automatic Prompt Engineer* frames instruction selection as program
search: the instruction is the "program," and the LLM proposes candidates by inferring an instruction
from a handful of input–output demonstrations (forward or "reverse-mode" generation). Candidates are
scored by execution accuracy on a held set, and the best are optionally resampled into paraphrase
variants for a second round — a Monte-Carlo, propose-and-select strategy. On 24 instruction-induction
tasks plus BIG-Bench, APE-generated instructions matched or beat human-written ones on 19 of 24 tasks
[Zhou 2022]. Its most-cited result is a *discovered* reasoning trigger: applied to zero-shot
chain-of-thought, APE found "Let's work this out in a step by step way to be sure we have the right
answer," which raised text-davinci-002 accuracy from 78.7% to 82.0% on MultiArith and from 40.7% to
43.0% on GSM8K, improving on Kojima et al.'s hand-written "Let's think step by step" [Zhou 2022;
Kojima 2022]. The lesson that recurs throughout the field: the best instruction is often not the one a
person would write.

**APO / ProTeGi (Pryzant et al. 2023).** *Automatic Prompt Optimization with "Gradient Descent" and
Beam Search* borrows the *shape* of gradient descent for a non-differentiable space. For a minibatch
of examples on which the current prompt fails, the LLM writes a natural-language critique — a "textual
gradient" describing what is wrong. A second LLM step edits the prompt in the opposite direction of
that critique, and a beam search with bandit-based selection keeps the most promising edited prompts
across steps. The method (informally called ProTeGi, "Prompt Optimization with Textual Gradients")
improved starting prompts by up to 31% across NLP benchmarks and a jailbreak-detection task [Pryzant
2023]. It established the "textual gradient" idea that later compound-system optimizers reuse.

**OPRO (Yang et al. 2023).** *Large Language Models as Optimizers* pushes the LLM-as-optimizer idea to
its cleanest form. The optimizer LLM receives a *meta-prompt* containing the task description and a
trajectory of previously tried instructions sorted by their scores (worst to best), and is asked to
generate a new instruction that scores higher. Each new candidate is scored and appended, so the
trajectory itself carries the optimization history — no gradients, no fine-tuning, black-box
compatible. On GSM8K, optimized instructions beat human-designed prompts by up to roughly 8 percentage
points [Yang 2023]. The signature result: OPRO's highest-scoring instruction for the PaLM 2-L scorer,
discovered around step 107 of the search, was "Take a deep breath and work on this problem
step-by-step," reaching 80.2% training accuracy on GSM8K [Yang 2023]. The winning phrase is
model-specific — different scorers converge on different instructions — which is precisely why an
automated search beats a fixed human heuristic. OPRO's trajectory format maps directly onto a
self-improvement loop and is the basis for the worked code below.

**PromptAgent (Wang et al. 2023).** Where OPRO treats the trajectory as a flat list, *PromptAgent*
treats optimization as *strategic planning* and searches the prompt space with Monte Carlo Tree Search
(MCTS). Each node is an intermediate prompt (a state); an action is an error-feedback-driven revision;
simulated rewards let the search look ahead and prefer high-reward paths rather than greedily
following the last improvement. Across 12 tasks spanning BIG-Bench Hard, domain-specific, and general
NLP, PromptAgent produced expert-level, domain-insightful prompts that outperformed strong CoT and
prior prompt-optimization baselines [Wang 2023]. MCTS buys the ability to escape local optima that a
greedy hill-climb gets stuck in, at the cost of more LLM calls.

Across these four, the trend is toward more structured search: propose-and-select (APE) → directional
edits with beam search (APO) → sorted-trajectory hill-climbing (OPRO) → look-ahead tree search
(PromptAgent). All keep the prompt human-readable.

### Continuous / soft prompts

The continuous line predates the LLM-as-optimizer wave and answers a different question: if you *can*
backpropagate through the model, can you tune a few vectors instead of all the weights? These are
parameter-efficient fine-tuning methods, not natural-language search, but they optimize "prompts" in
the embedding sense and belong in the taxonomy.

**Prefix-Tuning (Li & Liang 2021).** Freezes the entire language model and prepends a short sequence of
trainable continuous vectors — a "prefix" of virtual tokens — that every layer can attend to. On
table-to-text generation (GPT-2) and summarization (BART), tuning only ~0.1% of parameters matched
full fine-tuning, and it generalized better to low-data and unseen-topic settings [Li & Liang 2021].
This is the founding result that a handful of continuous vectors can steer a frozen model.

**Prompt Tuning (Lester et al. 2021).** *The Power of Scale for Parameter-Efficient Prompt Tuning*
simplifies prefix-tuning to a single soft prompt at the input layer only, learned by backpropagation.
Its central finding is about *scale*: prompt tuning trails full fine-tuning for small models but closes
the gap as models grow into the billions of parameters, matching full model tuning at scale while
storing just one small prompt per task [Lester 2021]. This makes a single frozen model reusable across
many tasks — the efficiency argument for soft prompts.

**P-Tuning (Liu et al. 2021).** *GPT Understands, Too* introduces P-Tuning: trainable continuous prompt
embeddings interleaved with discrete tokens, which stabilized the notoriously brittle manual prompts on
LAMA and SuperGLUE [Liu 2021]. It showed that even GPT-style models benefit from learned prompts on
natural-language understanding tasks.

**P-Tuning v2 (Liu et al. 2022).** The key refinement is *depth*: instead of prepending soft prompts
only at the input, P-Tuning v2 applies independent trainable prompts at *every* transformer layer
(deep prompt tuning, the same structural idea as prefix-tuning applied to NLU). This closed the gap
that earlier prompt tuning left on hard sequence-labeling tasks and matched full fine-tuning
*universally* across model scales (from 300M to 10B) and task types, while tuning only 0.1%–3% of
parameters [Liu 2022]. The takeaway that separates it from Lester et al.: prompt *depth* matters more
than prompt *length*.

The continuous methods are strictly more grounded — they optimize against real gradients — but they
require white-box access and produce vectors no human can read, so they cannot be inspected, audited,
or transferred as text. That trade-off is why the discrete and programmatic lines dominate the
black-box-API era.

### Programmatic / compound pipelines

Real systems are rarely a single prompt. They chain retrieval, reasoning, and generation across
several LM calls. Optimizing each prompt in isolation ignores their interaction; the programmatic line
optimizes the whole pipeline.

**DSPy (Khattab et al. 2023).** DSPy is a programming model that expresses an LM pipeline as a graph of
declarative *modules*. Each module is defined by a *signature* — a typed input→output specification
such as `question -> answer` — that abstracts *what* the step does from *how* it is prompted. A
*teleprompter* (compiler) then searches for the concrete prompts and demonstrations that maximize a
user-supplied metric over the whole program. The flagship teleprompter, **BootstrapFewShot**, runs the
program on training inputs, keeps the traces that satisfy the metric, and uses those self-generated
traces as few-shot demonstrations for each module — the pipeline bootstraps its own examples.
Reported gains over hand-written prompt chains: more than 25% over standard few-shot on GPT-3.5 and
more than 65% on llama2-13b-chat, and 5–46% over expert-written demonstrations depending on the model
[Khattab 2023]. DSPy reframes prompt optimization as *compilation*: you write the program, the compiler
writes the prompts.

**MIPRO / MIPROv2 (Opsahl-Ong et al. 2024).** DSPy's more powerful optimizer, *Multi-prompt
Instruction PRoposal Optimizer*, jointly optimizes both the *instructions* and the *demonstrations* of
every module in a multi-stage program, with no per-module labels or gradients. It proposes candidate
instructions with a program-aware, data-aware LLM step, then uses Bayesian optimization over a
surrogate model to search the joint space of instruction and demonstration choices across all modules
at once. MIPRO outperformed baseline optimizers on five of seven multi-stage programs, by as much as
13% accuracy [Opsahl-Ong 2024]. This is the state of the art in the programmatic line: optimize the
compound system holistically rather than prompt by prompt. (MIPROv2 is the refined implementation
shipped in the DSPy library.)

### Reading the taxonomy

| Method | Space | Search strategy | Access | Reads as | Key number |
|---|---|---|---|---|---|
| APE (Zhou 2022) | Discrete instruction | Propose-and-select (MC) | Black-box | Text | Beat humans on 19/24 tasks |
| APO/ProTeGi (Pryzant 2023) | Discrete instruction | Textual gradient + beam | Black-box | Text | Up to +31% over start prompt |
| OPRO (Yang 2023) | Discrete instruction | Sorted-trajectory hill-climb | Black-box | Text | 80.2% GSM8K ("deep breath") |
| PromptAgent (Wang 2023) | Discrete instruction | Monte Carlo Tree Search | Black-box | Text | Beat CoT on 12 tasks |
| Prefix-Tuning (Li 2021) | Continuous prefix (all layers) | Gradient descent | White-box | Vectors | Match FT at ~0.1% params |
| Prompt Tuning (Lester 2021) | Continuous (input only) | Gradient descent | White-box | Vectors | Matches FT at scale |
| P-Tuning v2 (Liu 2022) | Continuous (deep) | Gradient descent | White-box | Vectors | Match FT, 0.1–3% params |
| DSPy/MIPRO (Khattab 2023; Opsahl-Ong 2024) | Pipeline (instructions + demos) | Bootstrap + Bayesian search | Black-box | Text | +25–65% over few-shot; +13% (MIPRO) |

## Worked code

The clearest mechanism to implement is OPRO's loop: build a meta-prompt from a sorted trajectory of
`(instruction, score)` pairs, ask an optimizer LLM for new candidates, score each by exact match on a
tiny task, append, and repeat. The code below is self-contained and has no paid dependencies. The
single LLM call is a clearly-marked stub — replace `call_llm` with any real client (a local model, a
free API, etc.) and the loop is a working OPRO optimizer.

```python
"""Minimal OPRO-style instruction optimizer (Yang et al. 2023, arXiv:2309.03409).

The optimizer LLM sees a trajectory of previously scored instructions (sorted
worst -> best) and proposes a better one. We score instructions by exact-match
accuracy on a tiny toy task. Swap `call_llm` for a real model to run for real.
"""
import re
from dataclasses import dataclass

# --- A tiny scored task: map a word to its number of letters. -----------------
# The "hard part" the instruction must convey is *what operation to perform*.
TASK = [
    ("apple", "5"), ("dog", "3"), ("banana", "6"),
    ("kiwi", "4"), ("strawberry", "10"), ("fig", "3"),
]

def run_instruction(instruction: str, word: str) -> str:
    """Ask the model to answer one item under the given instruction."""
    prompt = f"{instruction}\nWord: {word}\nAnswer:"
    return call_llm(prompt).strip()

def score(instruction: str) -> float:
    """Exact-match accuracy of an instruction over the whole task set."""
    correct = 0
    for word, gold in TASK:
        pred = run_instruction(instruction, word)
        # take the first integer the model emits, if any
        m = re.search(r"-?\d+", pred)
        if m and m.group() == gold:
            correct += 1
    return correct / len(TASK)

# --- The OPRO meta-prompt: sorted trajectory -> a new candidate. ---------------
@dataclass
class Trace:
    instruction: str
    score: float

def build_meta_prompt(history: list[Trace]) -> str:
    # Sort ascending so the *best* instruction sits last, nearest the ask.
    ranked = sorted(history, key=lambda t: t.score)
    lines = [
        "You optimize an INSTRUCTION for a text task.",
        "Below are past instructions with their scores (0-100). "
        "Higher is better.",
        "",
    ]
    for t in ranked:
        lines.append(f"[score {round(t.score * 100)}] {t.instruction}")
    lines += [
        "",
        "Write ONE new instruction, different from all above, that will "
        "score higher. Output only the instruction text.",
    ]
    return "\n".join(lines)

def optimize(seeds: list[str], steps: int = 8) -> Trace:
    history = [Trace(s, score(s)) for s in seeds]
    best = max(history, key=lambda t: t.score)
    for step in range(steps):
        meta = build_meta_prompt(history)
        candidate = call_llm(meta).strip()
        if any(candidate == t.instruction for t in history):
            continue  # skip duplicates the optimizer re-proposes
        cand = Trace(candidate, score(candidate))
        history.append(cand)
        if cand.score > best.score:
            best = cand
        print(f"step {step}: {round(cand.score*100)}%  {candidate!r}")
    return best

# --- Replace this stub with a real model call. --------------------------------
def call_llm(prompt: str) -> str:
    """PLACEHOLDER. Return the model's completion of `prompt` as a string.

    Wire this to any chat/completion client, e.g.:
        resp = client.chat(model="...", messages=[{"role": "user",
                                                    "content": prompt}])
        return resp.choices[0].message.content
    Left unimplemented so the file has no paid dependency.
    """
    raise NotImplementedError("Plug in an LLM client to run the optimizer.")

if __name__ == "__main__":
    seeds = [
        "Answer the question.",
        "Respond with a number.",
    ]
    winner = optimize(seeds, steps=8)
    print(f"\nBest instruction ({round(winner.score*100)}%): "
          f"{winner.instruction!r}")
```

Three design points carry the whole method. First, **the trajectory is the memory**: sorting past
attempts worst-to-best and placing the best nearest the ask lets the optimizer LLM infer the gradient
of improvement from examples, exactly as OPRO specifies — no numeric gradient is ever computed.
Second, **the scorer defines the objective**; here it is exact-match accuracy, but swapping in an
F1, a pass rate, or a preference model changes *what* the loop optimizes without touching the search.
Third, **it is black-box**: `call_llm` is the only model touchpoint, so the same loop optimizes a
prompt for an API you cannot see inside — the property that makes discrete APO practical.

To grow this toward DSPy, you would replace the single `run_instruction` call with a multi-module
program, replace exact-match `score` with a program-level metric, and let a teleprompter bootstrap
few-shot demonstrations from the traces where the metric passed — optimizing instructions *and*
exemplars jointly across the pipeline, which is what MIPRO does.

## Open problems

**Search cost.** Every candidate is scored by running the task, so each optimization step costs many
LLM calls; PromptAgent's tree search and MIPRO's joint search multiply this further. The literature
reports strong final prompts but the search budget is a real deployment cost, and cost-vs-accuracy
Pareto comparisons across methods on a common benchmark remain thin.

**Overfitting to the eval set.** An optimizer that maximizes accuracy on a small scoring set can find
instructions that exploit that set rather than the task. The discovered prompt may not transfer to new
inputs, distributions, or model versions. Robust APO needs held-out validation and, ideally,
distribution-shift testing that most papers report only lightly.

**Model- and seed-specificity.** OPRO's "take a deep breath" wins for PaLM 2-L but a different scorer
converges elsewhere [Yang 2023]; APE's best trigger is likewise model-specific [Zhou 2022]. Optimized
prompts are artifacts of a particular base model and search seed, so a result does not automatically
carry across models or even across runs. This limits reproducibility and means an optimized prompt can
silently decay when the underlying model is updated.

**Interpretability vs. groundedness trade-off.** Continuous methods optimize against true gradients but
yield unreadable vectors and need white-box access; discrete methods are readable and black-box but
search a rugged, non-differentiable space with no convergence guarantees. No method today gives both
grounded optimization and human-auditable, transferable prompts.

**Why do these phrases work?** The field can *find* effective instructions faster than it can *explain*
them. There is no predictive theory of which wordings help a given model on a given task, so
optimization remains empirical search rather than principled design.

## Connections & further reading

- **[Retrieval-Augmented Generation](rag.md)** — *complementary.* RAG improves an LLM system by changing
  what the model retrieves and sees; prompt optimization improves it by changing how the model is asked.
  Both improve behavior without retraining the base model, and they compose: DSPy is frequently used to
  optimize the prompts inside a RAG pipeline.
- **[Reasoning & Chain-of-Thought](reasoning-and-chain-of-thought.md)** — *generative.* Prompt optimization
  can *discover* good reasoning formulations: APE's "Let's work this out in a step by step way…" and
  OPRO's "Take a deep breath…" are automatically found chain-of-thought triggers, not hand-designed ones.
- **[Recursive Self-Improvement](rsi.md)** — *instance-of.* An optimizer that improves its own prompt from
  a trajectory of its own scored attempts is a concrete, bounded self-improvement loop. OPRO's
  meta-prompt is the cleanest example; DSPy's bootstrapping is a pipeline-level version.

### References

1. Zhou, Y., Muresanu, A. I., Han, Z., Paster, K., Pitis, S., Chan, H., & Ba, J. (2022). *Large Language
   Models Are Human-Level Prompt Engineers* (APE). ICLR 2023. arXiv:2211.01910.
   https://arxiv.org/abs/2211.01910
2. Yang, C., Wang, X., Lu, Y., Liu, H., Le, Q. V., Zhou, D., & Chen, X. (2023). *Large Language Models as
   Optimizers* (OPRO). ICLR 2024. arXiv:2309.03409. https://arxiv.org/abs/2309.03409
3. Pryzant, R., Iter, D., Li, J., Lee, Y. T., Zhu, C., & Zeng, M. (2023). *Automatic Prompt Optimization
   with "Gradient Descent" and Beam Search* (APO/ProTeGi). EMNLP 2023. arXiv:2305.03495.
   https://arxiv.org/abs/2305.03495
4. Wang, X., Li, C., Wang, Z., Bai, F., Luo, H., Zhang, J., Jojic, N., Xing, E. P., & Hu, Z. (2023).
   *PromptAgent: Strategic Planning with Language Models Enables Expert-level Prompt Optimization*.
   ICLR 2024. arXiv:2310.16427. https://arxiv.org/abs/2310.16427
5. Li, X. L., & Liang, P. (2021). *Prefix-Tuning: Optimizing Continuous Prompts for Generation*. ACL 2021.
   arXiv:2101.00190. https://arxiv.org/abs/2101.00190
6. Lester, B., Al-Rfou, R., & Constant, N. (2021). *The Power of Scale for Parameter-Efficient Prompt
   Tuning*. EMNLP 2021. arXiv:2104.08691. https://arxiv.org/abs/2104.08691
7. Liu, X., Zheng, Y., Du, Z., Ding, M., Qian, Y., Yang, Z., & Tang, J. (2021). *GPT Understands, Too*
   (P-Tuning). arXiv:2103.10385. https://arxiv.org/abs/2103.10385
8. Liu, X., Ji, K., Fu, Y., Tam, W. L., Du, Z., Yang, Z., & Tang, J. (2022). *P-Tuning v2: Prompt Tuning
   Can Be Comparable to Fine-tuning Universally Across Scales and Tasks*. ACL 2022. arXiv:2110.07602.
   https://arxiv.org/abs/2110.07602
9. Khattab, O., Singhvi, A., Maheshwari, P., Zhang, Z., Santhanam, K., Vardhamanan, S., Haq, S., Sharma,
   A., Joshi, T. T., Moazam, H., Miller, H., Zaharia, M., & Potts, C. (2023). *DSPy: Compiling Declarative
   Language Model Calls into Self-Improving Pipelines*. ICLR 2024. arXiv:2310.03714.
   https://arxiv.org/abs/2310.03714
10. Opsahl-Ong, K., Ryan, M. J., Purtell, J., Broman, D., Potts, C., Zaharia, M., & Khattab, O. (2024).
    *Optimizing Instructions and Demonstrations for Multi-Stage Language Model Programs* (MIPRO). EMNLP
    2024. arXiv:2406.11695. https://arxiv.org/abs/2406.11695
11. Kojima, T., Gu, S. S., Reid, M., Matsuo, Y., & Iwasawa, Y. (2022). *Large Language Models are
    Zero-Shot Reasoners*. NeurIPS 2022. arXiv:2205.11916. https://arxiv.org/abs/2205.11916
