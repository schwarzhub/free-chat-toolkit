---
title: "From Retrieval to Reasoning: The Unified Narrative"
slug: from-retrieval-to-reasoning
tier: C
status: published
reading_time: 22 min
prerequisites: [rag, automated-prompt-optimization, reasoning-and-chain-of-thought]
series: foundations-of-modern-ai
series_order: 7
papers_cited: 13
papers_verified: true
version: 1.0
source_issue: 82
connections:
  - to: rag
    relationship: "layer 1 — retrieval grounds generation in external facts"
  - to: automated-prompt-optimization
    relationship: "layer 2 — search over the instruction/demonstration interface"
  - to: reasoning-and-chain-of-thought
    relationship: "layer 3 — spend inference-time compute to structure the reasoning"
  - to: rsi
    relationship: "layer 4 — the outer loop that closes over layers 1–3 using the system's own feedback"
---

## Abstract

Four bodies of work — retrieval-augmented generation, automated prompt optimization,
inference-time reasoning, and self-improving agent loops — are usually taught as separate subfields,
each with its own benchmarks and tools. This explainer advances a single organizing argument: they are
four *layers* of one system that raises the capability of a fixed language model **without touching its
weights**. Layer 1 changes what the model sees (context); layer 2 changes how the task is posed
(the prompt); layer 3 changes how much computation the model spends per query (reasoning); layer 4 wraps
the first three in a feedback loop that edits their configuration from observed outcomes. The claim is not
that the fields were designed as a stack — they were not — but that reading them as one exposes a shared
mechanism (external search plus verification substituting for gradient descent) and clarifies where each
technique helps. The layering thesis is the author's synthesis; every empirical claim below is cited to a
verified primary source.

## Why it matters

Retraining or fine-tuning a frontier model is expensive, slow, and often impossible: the weights may be
closed, the compute unavailable, or the deployment continuous. Yet the systems built on top of these
models keep getting better between weight releases. That improvement comes from a stack of techniques that
operate *around* the frozen model. Practitioners who see these techniques as a menu of unrelated tricks
tend to reach for the wrong one — adding a reranker when the failure is a reasoning gap, or hand-tuning a
prompt when a search procedure would dominate the human. Seeing them as an ordered stack, each addressing
a failure the previous layer exposes, tells you *which* knob to turn. This explainer is the capstone of
the `foundations-of-modern-ai` series; it assumes the three component explainers (RAG, automated prompt
optimization, chain-of-thought reasoning) and argues the connective tissue between them.

## Core concepts

Define every term before use.

- **Frozen model / no-weight-update regime.** The setting where the language model's parameters are held
  fixed. All four layers operate here: they change inputs, computation, and control flow, never the
  weights.
- **Context.** The tokens placed in the model's input window at inference. Retrieval populates context
  with external documents; memory systems populate it with the agent's own past.
- **Retrieval-Augmented Generation (RAG).** A pattern that fetches relevant documents from an external
  corpus and prepends them to the prompt before generation, grounding output in retrieved facts rather
  than parametric memory (Lewis et al., 2020).
- **Prompt / interface.** The instruction and demonstrations that frame a task for the model. Automated
  prompt optimization treats this string (or structured program) as a search space rather than a fixed
  artifact.
- **Inference-time compute.** Computation spent per query at generation time — extra tokens, extra
  samples, or extra search — as opposed to training-time compute spent once on the weights. Chain-of-
  thought and its descendants trade inference-time compute for accuracy.
- **Chain-of-Thought (CoT).** Prompting the model to emit intermediate reasoning steps before its final
  answer (Wei et al., 2022).
- **Self-improving loop.** A control structure in which the system observes the outcome of its own
  outputs and edits some component (a prompt, a stored skill, a memory) in response — an outer loop over
  the inner layers. In this series we treat recursive self-improvement (RSI) as this outer loop.
- **Verifier / feedback signal.** Any procedure that scores an output: a unit test, a metric, a
  majority vote across samples, or the model's own critique. Every layer above raw generation depends on
  a signal to search against.

**The layering thesis (author's synthesis, not a cited claim).** The four layers form a stack because
each answers a limitation the layer below leaves open. RAG fixes *what the model knows* but not *how the
task is asked*; prompt optimization fixes the asking but not the *depth of reasoning per query*;
inference-time reasoning fixes the depth but is still statically configured; a self-improving loop makes
the configuration itself respond to feedback. Read this claim as an argument, not a result — the papers
below were not written as a coordinated program, and the boundaries between layers are porous (a reasoning
strategy is also a prompt; a memory is also a retrieval corpus). The value of the framing is diagnostic,
not historical.

## The literature

### Layer 1 — Retrieval: change what the model sees

The foundational move is to stop relying solely on parametric memory. **Lewis et al. (2020)** introduced
Retrieval-Augmented Generation, coupling a parametric seq2seq generator with a non-parametric dense
retriever over Wikipedia; the retriever pulls passages that are prepended to the generator's input
(arXiv:2005.11401, NeurIPS 2020). The paper's contribution is architectural: knowledge that would
otherwise have to be baked into weights is instead fetched at inference, so the knowledge store can be
edited or expanded without retraining. This is layer 1 in its purest form — the weights are fixed, and
capability rises because the *context* improves.

The pattern proliferated into a large design space — chunking, embedding choice, top-k selection,
reranking, query rewriting — surveyed comprehensively by **Gao et al. (2023)**, "Retrieval-Augmented
Generation for Large Language Models: A Survey" (arXiv:2312.10997). That survey is the canonical map of
the subfield and the reference point for the sibling `rag` explainer. Two limitations it documents are the
hinge to the next layer: retrieval quality is itself sensitive to configuration with no universal setting,
and retrieving the right documents does not guarantee the model *uses* them well. RAG solves access to
facts; it does not solve how the task is posed or how the model reasons over what it retrieves.

### Layer 2 — Optimization: search over the interface

If the prompt is the bottleneck, treat it as something to search rather than to hand-write. Three systems
established this.

**Zhou et al. (2022)**, "Large Language Models Are Human-Level Prompt Engineers" (APE; arXiv:2211.01910),
frame instruction-writing as program synthesis: an LLM proposes candidate instructions, each is scored on
held-out examples, and the best is selected. APE-generated instructions match or beat human-written ones
on 19 of 24 instruction-induction tasks — the first strong evidence that the model can engineer its own
prompt better than a person.

**Yang et al. (2023)**, "Large Language Models as Optimizers" (OPRO; arXiv:2309.03409), generalize the
idea into an optimization loop where the model, given a trajectory of past prompts and their scores,
proposes the next prompt. The optimized prompts improve accuracy by up to 8% on GSM8K and up to 50% on
Big-Bench Hard over human-designed baselines. Crucially, the optimizer and the optimized are the same
model — the first clear instance in this stack of a system improving its own inputs from feedback.

**Khattab et al. (2023)**, "DSPy: Compiling Declarative Language Model Calls into Self-Improving Pipelines"
(arXiv:2310.03714), reframe the whole pipeline as a declarative program: modules with typed signatures,
plus optimizers ("teleprompters") that compile the program by searching over prompts and few-shot
demonstrations against a metric. DSPy's contribution is to make the search space *structured* — you
optimize a multi-stage program, not a single string — which is what lets prompt optimization compose with
the reasoning structures of layer 3. What unifies APE, OPRO, and DSPy is a search-plus-verify loop over
the interface; the verifier is a task metric, and no weight ever moves.

### Layer 3 — Reasoning: spend compute at inference

Optimizing the interface still leaves the model answering in one forward pass. Layer 3 spends more
computation per query. **Wei et al. (2022)**, "Chain-of-Thought Prompting Elicits Reasoning in Large
Language Models" (arXiv:2201.11903), showed that eliciting intermediate steps — via a few exemplars —
sharply improves arithmetic, commonsense, and symbolic reasoning, and that the effect emerges only at
scale. This is the empirical basis for the claim that inference-time computation can substitute for
additional training.

The family grew by adding search and verification on top of CoT. **Wang et al. (2022)**, "Self-Consistency
Improves Chain of Thought Reasoning in Language Models" (arXiv:2203.11171), sample many reasoning paths and
take a majority vote over final answers, improving GSM8K by +17.9% over greedy CoT — a verifier
(agreement across samples) layered onto reasoning. **Yao et al. (2023)**, "Tree of Thoughts" (ToT;
arXiv:2305.10601), generalize the linear chain to a search tree with self-evaluation and backtracking,
raising GPT-4's Game of 24 solve rate from 4% to 74%. **Besta et al. (2023)**, "Graph of Thoughts" (GoT;
arXiv:2308.09687), generalize the tree to an arbitrary graph allowing merges and feedback edges, reporting
a 62% improvement in sorting quality over ToT while cutting cost by more than 31%. The trajectory within
this layer — chain → vote → tree → graph — is itself a story of adding structure and verification, and
each structure is a hyperparameter that layer 2 can optimize. That is the concrete seam between layers 2
and 3: a reasoning strategy is also part of the searchable interface.

### Layer 4 — Self-improvement: close the loop

The final layer wraps retrieval, optimized prompts, and structured reasoning in an outer loop that edits
its own components from observed feedback. Four papers mark the transition.

**Madaan et al. (2023)**, "Self-Refine: Iterative Refinement with Self-Feedback" (arXiv:2303.17651), is the
minimal instance: one model generates an output, critiques its own output in natural language, and revises
using that critique — iterated, with no training data or RL — for roughly 20% absolute average improvement
across seven tasks. Self-Refine is the loop in miniature and is exactly the refine pass in the worked code
below. (Note the fabrication tell flagged in this series: Self-Refine is *not* "Recursive Introspection";
they are distinct works.)

**Shinn et al. (2023)**, "Reflexion: Language Agents with Verbal Reinforcement Learning" (arXiv:2303.11366),
turn the critique into persistent memory: the agent reflects on task feedback in language, stores the
reflection episodically, and conditions later attempts on it, reaching 91% pass@1 on HumanEval versus a
reported 80% GPT-4 baseline. The stored reflection is retrieval (layer 1) applied to the agent's own past;
the loop is layer 4.

**Wang et al. (2023)**, "Voyager: An Open-Ended Embodied Agent with Large Language Models"
(arXiv:2305.16291), runs the loop over executable skills in Minecraft: an automatic curriculum proposes
goals, generated code is verified by the environment and, on success, stored in a growing skill library
that is retrieved later. Voyager obtains 3.3× more unique items and reaches key tech-tree milestones up to
15.3× faster than prior methods — with no gradient update. Here all four layers are visible at once:
retrieval (skill library), an interface that is optimized by environment feedback, iterative reasoning,
and the outer curriculum loop.

**Park et al. (2023)**, "Generative Agents: Interactive Simulacra of Human Behavior" (arXiv:2304.03442,
UIST 2023), embed an observe → retrieve → reflect → plan loop over a persistent memory stream, letting
twenty-five agents produce coherent emergent behavior (famously, autonomously coordinating a party). Its
memory-retrieval-plus-reflection architecture is the layer-1-inside-layer-4 pattern made explicit.

Across these four, the components are the same ones from layers 1–3; the novelty is that the loop now
operates on the agent's *own* behavior, using a verifier (a test, an environment, or a self-critique) in
place of a gradient. That substitution — search and verification standing in for weight updates — is the
mechanism the whole stack shares, and it is why the sibling `rsi` explainer sits at the top of this series.

## Worked code

A minimal, self-contained sketch composing the four layers on one query: **retrieve → assemble prompt →
reason with CoT → self-critique and refine**. The model and retriever are deliberately stubbed so the file
runs with no dependencies and no paid API. Replace `stub_llm` and the toy corpus with a real client and
vector store; the control flow is the point.

```python
"""Four layers on one query, with stubbed model + retrieval.
Layer 1: retrieve      Layer 2: assemble/parameterize the prompt
Layer 3: reason (CoT)  Layer 4: self-critique -> refine (Self-Refine style)
Runs standalone: `python four_layers.py`. No network, no paid deps.
"""

# ---- Layer 1: retrieval (stub) -------------------------------------------
CORPUS = {
    "aqueduct": "Roman aqueducts moved water by gravity; the gradient was ~1:4800.",
    "concrete": "Roman concrete used volcanic ash (pozzolana), gaining strength in seawater.",
    "roads":    "Roman roads were layered: statumen, rudus, nucleus, then paving stones.",
}

def retrieve(query, k=2):
    """Toy lexical retriever. Swap for an embedding / vector-store lookup."""
    scored = [(sum(w in doc.lower() for w in query.lower().split()), key, doc)
              for key, doc in CORPUS.items()]
    scored.sort(reverse=True)
    return [doc for _score, _key, doc in scored[:k]]

# ---- The frozen model (stub) ---------------------------------------------
def stub_llm(prompt):
    """Deterministic stand-in for a real LLM call. Replace with an API client.
    Returns a CoT answer, or a critique/refinement when asked to."""
    if "CRITIQUE" in prompt:
        # Layer 4a: the model judges its own draft against the context.
        if "gravity" in prompt and "pump" in prompt:
            return "ISSUE: draft claims pumps; context says gravity-driven. Fix."
        return "OK: draft is grounded in the retrieved context."
    if "REFINE" in prompt:
        # Layer 4b: revise using the critique.
        return ("Reasoning: the context states aqueducts moved water by gravity.\n"
                "Answer: Roman aqueducts relied on a continuous downhill gradient, "
                "not pumps.")
    # Layer 3: first pass, chain-of-thought. (Intentionally flawed to exercise L4.)
    return ("Reasoning: water needs to be lifted, so pumps were likely used.\n"
            "Answer: Roman aqueducts used pumps to move water uphill.")

# ---- Layer 2: assemble / parameterize the prompt -------------------------
def build_prompt(question, context, instruction="Think step by step, then answer."):
    """The 'interface'. In a real system an optimizer (APE/OPRO/DSPy) would
    search over `instruction` and few-shot demos against a metric."""
    ctx = "\n".join(f"- {c}" for c in context)
    return f"{instruction}\n\nContext:\n{ctx}\n\nQuestion: {question}\n"

# ---- Layer 4: the self-improving loop over 1-3 ---------------------------
def answer(question, max_refines=2):
    context = retrieve(question)                      # Layer 1
    prompt = build_prompt(question, context)          # Layer 2
    draft = stub_llm(prompt)                           # Layer 3 (CoT)
    for _ in range(max_refines):                       # Layer 4
        critique = stub_llm(f"CRITIQUE the draft against the context.\n"
                            f"Context:\n{context}\nDraft:\n{draft}")
        if critique.startswith("OK"):
            break
        draft = stub_llm(f"REFINE the draft given the critique.\n"
                        f"Critique: {critique}\nContext:\n{context}\n"
                        f"Draft:\n{draft}")
    return draft, context

if __name__ == "__main__":
    out, ctx = answer("How did Roman aqueducts move water?")
    print("Retrieved context:", ctx)
    print("\nFinal answer:\n", out)
```

Running it, the layer-3 first pass asserts (wrongly) that aqueducts used pumps; the layer-4 critique
catches the contradiction with the retrieved context and the refine pass corrects it to the gravity-driven
answer. Every improvement here came from control flow around a fixed model — no weights changed. Swapping
`stub_llm` for a real client and `retrieve` for a vector store turns this into a working, if minimal,
instance of the full stack; adding an optimizer over `build_prompt`'s `instruction` argument is where
layer 2 (APE/OPRO/DSPy) plugs in.

## Open problems

- **Verifier quality caps every layer.** Search-and-verify only works when the verifier is trustworthy.
  Self-critique can miss its own errors, and majority vote (Wang et al., 2022) rewards *consistency*, not
  *correctness* — a model confidently wrong in the same way across samples defeats it. The stack's
  ceiling is set by the weakest verifier in the loop.
- **Cost scaling of inference-time compute.** Layer 3 buys accuracy with tokens and samples; ToT and GoT
  add branching on top. GoT reports cost reductions over ToT (Besta et al., 2023), but the general trend
  is superlinear compute for marginal accuracy, and the compute-optimal allocation between layers is
  unsettled.
- **Do the loops actually compound, or just help once?** Reflexion and Voyager show gains from iteration
  in specific environments, but whether a self-improving loop yields sustained, open-ended improvement —
  versus plateauing after a few rounds — is not established in general. The RSI explainer treats this as
  the field's central open question.
- **Optimizing the outer loop.** Prompt optimization (layer 2) has been applied to prompts and
  demonstrations; applying it to the *reflection and control strategy* of layer 4 — optimizing the loop
  that optimizes — is largely unexplored and risks instability.
- **Attribution and interaction effects.** Because the layers interact (a better retriever can mask a
  reasoning weakness; a stronger reasoner can paper over poor retrieval), it is genuinely hard to
  attribute a system's performance to a single layer, which complicates both debugging and honest
  benchmarking.

## Implications

Because these four capabilities compose, a toolkit that offers retrieval, prompt/route control,
multi-step reasoning, and self-review can, in principle, deliver a self-improving pipeline without
retraining a model. This explainer deliberately does *not* claim any particular tool name in the
free-chat toolkit implements a given layer — capabilities, not specific tools, are what the framing is
about — and readers should map the layers onto whatever concrete tools exist rather than the reverse.

## Connections & further reading

- **[rag](./rag.md)** — *layer 1.* The retrieval substrate this stack sits on; read it for the chunking,
  embedding, and reranking design space summarized here.
- **[automated-prompt-optimization](./automated-prompt-optimization.md)** — *layer 2.* APE, OPRO, and DSPy
  in depth — how the interface becomes a search space.
- **[reasoning-and-chain-of-thought](./reasoning-and-chain-of-thought.md)** — *layer 3.* CoT, self-
  consistency, ToT, and GoT — spending inference-time compute.
- **[rsi](./rsi.md)** — *layer 4.* The outer loop (Self-Refine, Reflexion, Voyager, Generative Agents) and
  the open question of whether it compounds.

### References

1. Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H., Lewis, M.,
   Yih, W., Rocktäschel, T., Riedel, S., & Kiela, D. (2020). *Retrieval-Augmented Generation for
   Knowledge-Intensive NLP Tasks.* NeurIPS 2020. arXiv:2005.11401. https://arxiv.org/abs/2005.11401
2. Gao, Y., Xiong, Y., Gao, X., Jia, K., Pan, J., Bi, Y., Dai, Y., Sun, J., Wang, M., & Wang, H. (2023).
   *Retrieval-Augmented Generation for Large Language Models: A Survey.* arXiv:2312.10997.
   https://arxiv.org/abs/2312.10997
3. Zhou, Y., Muresanu, A. I., Han, Z., Paster, K., Pitis, S., Chan, H., & Ba, J. (2022). *Large Language
   Models Are Human-Level Prompt Engineers (APE).* arXiv:2211.01910. https://arxiv.org/abs/2211.01910
4. Yang, C., Wang, X., Lu, Y., Liu, H., Le, Q. V., Zhou, D., & Chen, X. (2023). *Large Language Models as
   Optimizers (OPRO).* arXiv:2309.03409. https://arxiv.org/abs/2309.03409
5. Khattab, O., Singhvi, A., Maheshwari, P., Zhang, Z., Santhanam, K., Vardhamanan, S., Haq, S., Sharma,
   A., Joshi, T. T., Moazam, H., Miller, H., Zaharia, M., & Potts, C. (2023). *DSPy: Compiling Declarative
   Language Model Calls into Self-Improving Pipelines.* arXiv:2310.03714. https://arxiv.org/abs/2310.03714
6. Wei, J., Wang, X., Schuurmans, D., Bosma, M., Ichter, B., Xia, F., Chi, E., Le, Q., & Zhou, D. (2022).
   *Chain-of-Thought Prompting Elicits Reasoning in Large Language Models.* NeurIPS 2022. arXiv:2201.11903.
   https://arxiv.org/abs/2201.11903
7. Wang, X., Wei, J., Schuurmans, D., Le, Q., Chi, E., Narang, S., Chowdhery, A., & Zhou, D. (2022).
   *Self-Consistency Improves Chain of Thought Reasoning in Language Models.* arXiv:2203.11171.
   https://arxiv.org/abs/2203.11171
8. Yao, S., Yu, D., Zhao, J., Shafran, I., Griffiths, T. L., Cao, Y., & Narasimhan, K. (2023). *Tree of
   Thoughts: Deliberate Problem Solving with Large Language Models.* arXiv:2305.10601.
   https://arxiv.org/abs/2305.10601
9. Besta, M., Blach, N., Kubicek, A., Gerstenberger, R., Podstawski, M., Gianinazzi, L., Gajda, J.,
   Lehmann, T., Niewiadomski, H., Nyczyk, P., & Hoefler, T. (2023). *Graph of Thoughts: Solving Elaborate
   Problems with Large Language Models.* arXiv:2308.09687. https://arxiv.org/abs/2308.09687
10. Madaan, A., Tandon, N., Gupta, P., Hallinan, S., Gao, L., Wiegreffe, S., Alon, U., Dziri, N.,
    Prabhumoye, S., Yang, Y., Gupta, S., Majumder, B. P., Hermann, K., Welleck, S., Yazdanbakhsh, A., &
    Clark, P. (2023). *Self-Refine: Iterative Refinement with Self-Feedback.* arXiv:2303.17651.
    https://arxiv.org/abs/2303.17651
11. Shinn, N., Cassano, F., Berman, E., Gopinath, A., Narasimhan, K., & Yao, S. (2023). *Reflexion:
    Language Agents with Verbal Reinforcement Learning.* arXiv:2303.11366. https://arxiv.org/abs/2303.11366
12. Wang, G., Xie, Y., Jiang, Y., Mandlekar, A., Xiao, C., Zhu, Y., Fan, L., & Anandkumar, A. (2023).
    *Voyager: An Open-Ended Embodied Agent with Large Language Models.* arXiv:2305.16291.
    https://arxiv.org/abs/2305.16291
13. Park, J. S., O'Brien, J. C., Cai, C. J., Morris, M. R., Liang, P., & Bernstein, M. S. (2023).
    *Generative Agents: Interactive Simulacra of Human Behavior.* UIST 2023. arXiv:2304.03442.
    https://arxiv.org/abs/2304.03442
