---
title: "Reasoning Models and Chain-of-Thought"
slug: reasoning-and-chain-of-thought
tier: C
status: published
reading_time: 17 min
prerequisites: [what-is-an-llm]
series: foundations-of-modern-ai
series_order: 5
papers_cited: 14
papers_verified: true
version: 1.0
source_issue: 86
connections:
  - to: automated-prompt-optimization
    relationship: "Prompt optimization can discover the reasoning formulations (exemplars, instructions) that this explainer applies by hand."
  - to: rag
    relationship: "Retrieved context becomes the working material that inference-time reasoning operates over."
  - to: rsi
    relationship: "Self-taught reasoning turns a model's own reasoning traces into training data, a concrete instance of recursive self-improvement."
---

## Abstract

An autoregressive language model commits to each token before it has computed the answer. This makes single-pass generation a poor fit for problems whose solution requires several dependent steps: the model must emit the final token of its answer having done all intermediate work implicitly, inside one forward pass. The literature reviewed here removes that constraint by spending computation at inference time rather than only at training time. Chain-of-thought prompting (Wei et al. 2022) lets the model externalize intermediate steps into the context window; zero-shot CoT (Kojima et al. 2022) shows a single instruction triggers the behavior. Self-consistency (Wang et al. 2022) samples many chains and votes. Decomposition methods (Zhou et al. 2022; Press et al. 2022) and the reason-act loop (Yao et al. 2022) restructure the problem. Search methods — Tree of Thoughts (Yao et al. 2023), Graph of Thoughts (Besta et al. 2024), RAP (Hao et al. 2023) — expand the chain into a searchable space. A parallel training thread — STaR (Zelikman et al. 2022), Quiet-STaR (Zelikman et al. 2024), process reward models (Lightman et al. 2023), ReST-MCTS* (Zhang et al. 2024) — turns reasoning traces into supervision. The takeaway: reasoning quality is bought with inference-time compute, and how that compute is spent matters more than how much.

## Why it matters

Reasoning techniques sit between a raw language model and any application that needs a correct multi-step answer — arithmetic, planning, tool orchestration, code synthesis, retrieval-augmented question answering. In a production stack, they are the layer you reach for when direct prompting returns confident wrong answers on problems a human would solve by "working it out." They matter for three practical reasons.

First, they are the cheapest lever available. Every method here works with an already-trained model; none requires new weights (though several can be distilled back into weights). You trade tokens for accuracy without retraining.

Second, the trade is steep and needs managing. Self-consistency multiplies token cost by the number of samples; tree and graph search can multiply it again. Snell et al. (2024) show the allocation is not monotone — spending compute the right way on the right problem beats spending more compute naively by over 4x, and can beat a 14x larger model. Knowing which technique fits which task is a budgeting decision, not an academic one.

Third, this layer is where the "reasoning models" of 2024–2025 came from. The commercial systems marketed as reasoning models are, in mechanism, the training-side descendants of the ideas below: generate reasoning traces, keep the ones that reach correct answers, reward good intermediate steps, and fine-tune on the result. Understanding the primitives explains the products.

## Core concepts

**Autoregressive generation.** The model produces text one token at a time, each conditioned on all previous tokens. There is no scratch space outside the token stream: any intermediate computation the model wants to reuse must be written into the visible sequence.

**Chain of thought (CoT).** A sequence of intermediate natural-language reasoning steps emitted before the final answer. Because each step becomes part of the context for subsequent steps, the chain acts as external working memory and lets the model condition its answer on its own prior deductions.

**Few-shot vs. zero-shot.** Few-shot prompting supplies worked examples (exemplars) in the prompt; zero-shot supplies none, relying on an instruction. Few-shot CoT includes exemplars whose answers show reasoning steps; zero-shot CoT uses a trigger phrase instead.

**Test-time (inference-time) compute.** Computation spent while answering, as opposed to during training. Sampling multiple chains, searching a tree of partial solutions, or running a verifier all spend test-time compute.

**Outcome reward vs. process reward.** An outcome reward model (ORM) scores only the final answer's correctness. A process reward model (PRM) scores each intermediate step. PRMs give denser feedback and can catch a correct answer reached by faulty reasoning.

**Faithfulness.** Whether a stated chain of thought reflects the computation that actually produced the answer, or is a post-hoc rationalization. An unfaithful chain can look valid while the answer depends on something the chain never mentions.

**Marginalization over reasoning paths.** Treating the reasoning chain as a latent variable and summing (voting) over many sampled chains that reach the same answer, rather than trusting a single chain.

## The literature

### The founding observation: externalized steps (2022)

Wei et al. (2022), *Chain-of-Thought Prompting Elicits Reasoning in Large Language Models* (arXiv:2201.11903), established the effect. Supplying few-shot exemplars whose answers spell out intermediate reasoning steps "significantly improves the ability of large language models to perform complex reasoning." The gain is strongly scale-dependent — it emerges only in sufficiently large models — and is largest on multi-step arithmetic, commonsense, and symbolic tasks. The mechanistic reading, developed across the follow-up literature, is that the chain lets the model store and reuse intermediate results in the token stream, effectively adding serial computation that a single forward pass cannot provide.

Kojima et al. (2022), *Large Language Models are Zero-Shot Reasoners* (arXiv:2205.11916), showed the exemplars are not strictly necessary. Prepending the single instruction **"Let's think step by step"** to the model's answer elicits step-by-step reasoning with no worked examples at all, turning CoT from a demonstration-heavy technique into a one-line intervention. This is the origin of the now-ubiquitous trigger phrase.

### Voting over chains: self-consistency (2022)

Wang et al. (2022), *Self-Consistency Improves Chain of Thought Reasoning in Language Models* (arXiv:2203.11171), attacked the brittleness of trusting one chain. Instead of greedy decoding, sample a diverse set of chains at nonzero temperature, then take the majority final answer — "marginalizing" over reasoning paths. A hard problem admits many valid routes to the same true answer but idiosyncratic routes to wrong ones, so agreement concentrates on truth. Reported absolute gains over CoT: **+17.9% on GSM8K, +11.0% on SVAMP, +12.2% on AQuA, +6.4% on StrategyQA, +3.9% on ARC-challenge.** Self-consistency is the simplest test-time-compute method: no verifier, no search, just sample-and-vote. Its cost scales linearly with the number of samples, which motivates the later question of how many samples are worth it.

### Restructuring the problem: decomposition and interleaving (2022)

Two 2022 lines changed the shape of the reasoning rather than just sampling more of it.

Zhou et al. (2022), *Least-to-Most Prompting Enables Complex Reasoning in Large Language Models* (arXiv:2205.10625), decomposes a hard problem into an ordered list of simpler subproblems, then solves them in sequence, feeding each answer forward. This targets *easy-to-hard generalization* — solving instances harder than any exemplar shown. On the SCAN compositional-generalization benchmark, least-to-most with code-davinci-002 reached **at least 99% accuracy from 14 exemplars, versus 16% for chain-of-thought**, surpassing specialized neuro-symbolic models trained on more than 15,000 examples.

Press et al. (2022), *Measuring and Narrowing the Compositionality Gap in Language Models* (arXiv:2210.03350), introduced **Self-Ask**, in which the model explicitly poses and answers follow-up sub-questions before the final answer. Making the decomposition explicit narrows the "compositionality gap" — the class of questions whose sub-facts the model knows but whose composition it fails — and the format's structured follow-ups plug cleanly into a search engine for the sub-questions.

Yao et al. (2022), *ReAct: Synergizing Reasoning and Acting in Language Models* (arXiv:2210.03629), interleaves reasoning traces with task actions: the model alternates *thought* steps with *act* steps (e.g., querying a tool or knowledge source) and *observation* steps that feed results back. Reasoning guides which action to take; observations ground subsequent reasoning, reducing the hallucination and error propagation seen in reasoning-only chains. ReAct is the direct ancestor of modern tool-using agents, and connects this explainer to retrieval-augmented systems.

### Searching a space of thoughts (2023–2024)

If a single chain is one path, the next step is to search over many.

Yao et al. (2023), *Tree of Thoughts: Deliberate Problem Solving with Large Language Models* (arXiv:2305.10601), generalizes the chain into a tree whose nodes are partial solutions ("thoughts"). The model generates candidate next thoughts, a heuristic evaluates partial states, and a search procedure (BFS or DFS) expands promising branches and prunes dead ends, with backtracking. On Game of 24, **GPT-4 with chain-of-thought solved 4% of tasks; Tree of Thoughts solved 74%.** ToT wins where the solution requires exploration, lookahead, or recovery from a bad early commitment — planning and constraint-heavy puzzles.

Besta et al. (2024), *Graph of Thoughts: Solving Elaborate Problems with Large Language Models* (arXiv:2308.09687; AAAI 2024), generalizes the tree to an arbitrary graph, so thoughts can be *merged* (combining partial results), aggregated, and refined in loops — not only branched. Modeling reasoning as a DAG of interdependent thoughts suits tasks with combinable sub-results such as sorting and document merging. Reported on a sorting task: **+62% quality over Tree of Thoughts while reducing cost by more than 31%**, by aggregating partial sorts rather than re-exploring.

Hao et al. (2023), *Reasoning with Language Model is Planning with World Model* (arXiv:2305.14992; EMNLP 2023), introduced **RAP** (Reasoning via Planning). It repurposes the LLM as both a *world model* (predicting the state resulting from a reasoning step) and a *reasoning agent*, and runs Monte Carlo Tree Search over the reasoning tree to balance exploration and exploitation under a reward signal. On plan generation, RAP with LLaMA-33B reported a **33% relative improvement over chain-of-thought on GPT-4.** RAP frames reasoning explicitly as planning — the framing that the later self-training methods exploit to *generate* good traces automatically.

> Scope note: the source issue attributed "CAST / ETO approaches" to Hao et al. This is incorrect and has been dropped. RAP uses MCTS over a world model; it does not propose ETO. "ETO" (Exploration-based Trajectory Optimization) is a separate 2024 agent-training method by Song et al., outside this explainer's inference-time scope, and "CAST" could not be verified as a reasoning method at all.

### Learning to reason: traces as supervision (2022–2024)

The methods above spend compute at inference. A parallel thread converts reasoning traces into training signal, folding the gains back into weights.

Zelikman et al. (2022), *STaR: Bootstrapping Reasoning With Reasoning* (arXiv:2203.14465), closes a self-improvement loop: prompt the model to generate rationales; keep those that reach the correct answer; for wrong ones, re-generate a rationale *given* the correct answer (rationalization); fine-tune on all rationales that yielded correct answers; repeat. STaR "performs comparably to fine-tuning a 30x larger" model on CommonsenseQA. Its limitation is exploratory: the loop reinforces reasoning styles the model already produces, so it can converge prematurely. This is the canonical link to recursive self-improvement — the model manufactures its own training data.

Zelikman et al. (2024), *Quiet-STaR: Language Models Can Teach Themselves to Think Before Speaking* (arXiv:2403.09629), generalizes STaR from task-specific rationales to token-level latent thoughts: the model learns, during continued pretraining, to generate internal rationales explaining arbitrary next text, rewarding thoughts that improve prediction. After this pretraining, zero-shot reasoning improved with no task-specific fine-tuning: **GSM8K 5.9% → 10.9%, CommonsenseQA 36.3% → 47.2%.**

Lightman et al. (2023), *Let's Verify Step by Step* (arXiv:2305.20050), addresses *which* traces to trust. Training a **process reward model** on step-level human labels beats outcome supervision: the process-supervised verifier "solves 78% of problems from a representative subset of the MATH test set" when used to rank solutions. The paper releases **PRM800K**, 800,000 step-level human feedback labels. The lesson — reward the reasoning, not only the answer — underlies both better verification-guided sampling and better self-training targets.

Zhang et al. (2024), *ReST-MCTS\*: LLM Self-Training via Process Reward Guided Tree Search* (arXiv:2406.03816; NeurIPS 2024), unifies the two threads. It runs MCTS guided by a process reward model to collect high-quality reasoning traces, then self-trains both the policy and the reward model on them, iterating. The search-guided traces let it exceed self-training baselines (ReST-EM, Self-Rewarding LM) and outperform Best-of-N and Tree-of-Thought under matched compute. ReST-MCTS* is the synthesis: search (ToT/RAP) + process reward (Lightman) + self-training (STaR) in one loop.

### How much compute, spent how (2024)

Snell et al. (2024), *Scaling LLM Test-Time Compute Optimally can be More Effective than Scaling Model Parameters* (arXiv:2408.03314), studies the budgeting question directly. The optimal way to spend a test-time budget depends on problem difficulty; a "compute-optimal" strategy that adapts allocation to difficulty improves efficiency by **more than 4x over best-of-N**, and on problems where a small base model has non-trivial success rates, test-time compute "can be used to outperform a 14x larger model" under a FLOPs-matched comparison. The result reframes reasoning methods as a compute-allocation problem rather than a fixed recipe.

## Worked code

A minimal self-consistency sampler: draw N chain-of-thought completions, parse each final answer, and take the majority vote. The model is stubbed so the file runs with no dependencies and no paid API — swap `stub_model` for a real client (returning completion strings) to use it for real. The mechanism, not the model, is the point.

```python
"""Self-consistency (Wang et al. 2022): sample N chains-of-thought,
parse each final answer, return the majority vote.

Runs with only the Python standard library. Replace `stub_model` with a
real LLM call (any function: prompt, temperature -> completion string).
"""
from __future__ import annotations
import random
import re
from collections import Counter

# --- 1. A stub "model": returns CoT-style text ending in "The answer is X."
# It usually reaches the right answer but sometimes takes a wrong path,
# so the vote has something to do. A real model replaces this entirely.
def stub_model(prompt: str, temperature: float, rng: random.Random) -> str:
    # Pretend the true answer to the prompt is 18.
    correct = 18
    # 70% of sampled chains land on the correct answer; the rest err.
    if rng.random() < 0.70:
        ans = correct
        work = "6 eggs a day, 3 eaten, 4 baked -> 6-3-4=... wait, sells 9 * $2 = 18"
    else:
        ans = rng.choice([16, 15, 12, 20])  # plausible-looking wrong paths
        work = f"miscount along the way, arriving at {ans}"
    return f"Let's think step by step. {work}. The answer is {ans}."

# --- 2. Parse the final answer out of a completion.
ANSWER_RE = re.compile(r"answer is\s*\$?(-?\d+(?:\.\d+)?)", re.IGNORECASE)

def parse_answer(completion: str) -> str | None:
    matches = ANSWER_RE.findall(completion)
    if not matches:
        return None
    return matches[-1]  # last match = the final stated answer

# --- 3. Self-consistency: sample N, parse, majority-vote.
def self_consistency(
    prompt: str,
    model=stub_model,
    n_samples: int = 20,
    temperature: float = 0.7,
    seed: int = 0,
):
    rng = random.Random(seed)
    answers: list[str] = []
    for _ in range(n_samples):
        completion = model(prompt, temperature, rng)
        ans = parse_answer(completion)
        if ans is not None:          # drop unparseable chains
            answers.append(ans)
    if not answers:
        return None, {}
    counts = Counter(answers)
    top_answer, top_count = counts.most_common(1)[0]
    confidence = top_count / len(answers)   # fraction agreeing = a cheap confidence signal
    return top_answer, {"votes": dict(counts), "confidence": round(confidence, 3),
                        "n_parsed": len(answers)}

if __name__ == "__main__":
    prompt = ("Janet's ducks lay 16 eggs/day; she eats 3 and bakes with 4, "
              "selling the rest at $2 each. How much does she make daily?")
    answer, meta = self_consistency(prompt, n_samples=20)
    print("self-consistent answer:", answer)   # -> 18 (majority)
    print("vote breakdown:", meta)
    # A single greedy sample could land on any wrong path above; voting
    # concentrates mass on the answer reached by the most chains.
```

Two design points carry over to real use. The vote fraction (`confidence`) is a usable signal for when to stop sampling or escalate to a harder method — the practical hook into Snell et al.'s compute-allocation question. And parsing is where self-consistency silently fails: if the answer-extraction regex is wrong, votes scatter across formatting variants rather than semantics. Normalize answers (strip units, canonicalize numbers) before counting.

## Open problems

**Faithfulness.** A stated chain need not be the computation that produced the answer. Models can output a valid-looking chain while the answer depends on a feature the chain never mentions — a "Clever Hans" pattern-match — and can produce the same answer after their own chain is perturbed. This undercuts using CoT as an explanation or a safety-audit surface. The founding papers (Wei et al. 2022; Kojima et al. 2022) demonstrate the accuracy effect but do not establish that the visible steps are causal; treating a chain as a faithful trace is an assumption, not a result.

**Cost escalation.** Every method here multiplies token usage — self-consistency by N, tree and graph search by more. The gains are real but bought, and on many deployments the budget, not the method, is the binding constraint. Snell et al. (2024) show the allocation can be optimized, but optimal allocation itself requires estimating problem difficulty, which is unsolved in general.

**Length exploitation.** When traces are scored or rewarded, models can learn that longer reasoning correlates with higher reward and inflate length without adding correctness — a reward-hacking failure that process reward models (Lightman et al. 2023) mitigate but do not eliminate, since step-level labels are expensive and themselves imperfect.

**Convergence and out-of-distribution reasoning.** Self-training loops reinforce reasoning the model already produces. STaR (Zelikman et al. 2022) notes the exploration limit directly; search-guided variants (Zhang et al. 2024) widen exploration but still bootstrap from the base model's distribution. Gains concentrate on problems near the training distribution and plateau on genuinely novel ones. Whether any of these methods produces reasoning that generalizes out of distribution, versus more thoroughly interpolating the training distribution, remains open.

**Verifier dependence.** Search and self-training lean on an evaluator — a heuristic (ToT), a world model (RAP), or a learned PRM (Lightman et al.; Zhang et al.). The reasoning is only as good as that signal, and a miscalibrated verifier steers search confidently wrong. Building verifiers that outrun the reasoners they supervise is the load-bearing open problem for the whole training-side thread.

## Connections & Further Reading

- **[Automated Prompt Optimization](automated-prompt-optimization.md)** — The CoT formulations applied by hand here (which exemplars, which trigger phrase, what decomposition) are exactly what prompt-optimization methods search for automatically. Reasoning gives APO its objective; APO gives reasoning its prompts.
- **[Retrieval-Augmented Generation](rag.md)** — ReAct (Yao et al. 2022) already interleaves reasoning with retrieval actions; retrieved passages are the working material inference-time reasoning operates over, and grounding reasoning in retrieved facts is a direct answer to the faithfulness and hallucination problems above.
- **[Recursive Self-Improvement](rsi.md)** — STaR, Quiet-STaR, and ReST-MCTS* are RSI made concrete: a model generates its own reasoning traces, filters them by correctness or process reward, and trains on the survivors. The verifier-dependence and convergence limits here are the RSI thread's central risks.

### References

1. Wei, J., Wang, X., Schuurmans, D., Bosma, M., Ichter, B., Xia, F., Chi, E., Le, Q., Zhou, D. (2022). *Chain-of-Thought Prompting Elicits Reasoning in Large Language Models.* arXiv:2201.11903. https://arxiv.org/abs/2201.11903
2. Kojima, T., Gu, S. S., Reid, M., Matsuo, Y., Iwasawa, Y. (2022). *Large Language Models are Zero-Shot Reasoners.* arXiv:2205.11916. https://arxiv.org/abs/2205.11916
3. Wang, X., Wei, J., Schuurmans, D., Le, Q., Chi, E., Narang, S., Chowdhery, A., Zhou, D. (2022). *Self-Consistency Improves Chain of Thought Reasoning in Language Models.* arXiv:2203.11171. https://arxiv.org/abs/2203.11171
4. Zhou, D., Schärli, N., Hou, L., Wei, J., Scales, N., Wang, X., Schuurmans, D., Cui, C., Bousquet, O., Le, Q., Chi, E. (2022). *Least-to-Most Prompting Enables Complex Reasoning in Large Language Models.* arXiv:2205.10625. https://arxiv.org/abs/2205.10625
5. Press, O., Zhang, M., Min, S., Schmidt, L., Smith, N. A., Lewis, M. (2022). *Measuring and Narrowing the Compositionality Gap in Language Models* (Self-Ask). arXiv:2210.03350. https://arxiv.org/abs/2210.03350
6. Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., Cao, Y. (2022). *ReAct: Synergizing Reasoning and Acting in Language Models.* arXiv:2210.03629. https://arxiv.org/abs/2210.03629
7. Yao, S., Yu, D., Zhao, J., Shafran, I., Griffiths, T. L., Cao, Y., Narasimhan, K. (2023). *Tree of Thoughts: Deliberate Problem Solving with Large Language Models.* arXiv:2305.10601. https://arxiv.org/abs/2305.10601
8. Besta, M., Blach, N., Kubicek, A., Gerstenberger, R., Podstawski, M., Gianinazzi, L., Gajda, J., Lehmann, T., Niewiadomski, H., Nyczyk, P., Hoefler, T. (2024). *Graph of Thoughts: Solving Elaborate Problems with Large Language Models.* arXiv:2308.09687 (AAAI 2024). https://arxiv.org/abs/2308.09687
9. Hao, S., Gu, Y., Ma, H., Hong, J. J., Wang, Z., Wang, D. Z., Hu, Z. (2023). *Reasoning with Language Model is Planning with World Model* (RAP). arXiv:2305.14992 (EMNLP 2023). https://arxiv.org/abs/2305.14992
10. Lightman, H., Kosaraju, V., Burda, Y., Edwards, H., Baker, B., Lee, T., Leike, J., Schulman, J., Sutskever, I., Cobbe, K. (2023). *Let's Verify Step by Step* (PRM800K). arXiv:2305.20050. https://arxiv.org/abs/2305.20050
11. Zelikman, E., Wu, Y., Mu, J., Goodman, N. D. (2022). *STaR: Bootstrapping Reasoning With Reasoning.* arXiv:2203.14465. https://arxiv.org/abs/2203.14465
12. Zelikman, E., Harik, G., Shao, Y., Jayasiri, V., Haber, N., Goodman, N. D. (2024). *Quiet-STaR: Language Models Can Teach Themselves to Think Before Speaking.* arXiv:2403.09629. https://arxiv.org/abs/2403.09629
13. Zhang, D., Zhoubian, S., Hu, Z., Yue, Y., Dong, Y., Tang, J. (2024). *ReST-MCTS\*: LLM Self-Training via Process Reward Guided Tree Search.* arXiv:2406.03816 (NeurIPS 2024). https://arxiv.org/abs/2406.03816
14. Snell, C., Lee, J., Xu, K., Kumar, A. (2024). *Scaling LLM Test-Time Compute Optimally can be More Effective than Scaling Model Parameters.* arXiv:2408.03314. https://arxiv.org/abs/2408.03314
