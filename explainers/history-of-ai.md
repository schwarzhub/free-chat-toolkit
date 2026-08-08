---
title: "A History of AI in Three Eras: Symbolic, Neural, and Transformer"
slug: history-of-ai
tier: B
status: published
reading_time: 30 min
prerequisites: []
series: foundations-of-modern-ai
series_order: 2
papers_cited: 30
papers_verified: true
version: 1.0
source_issue: 87
connections:
  - to: rag
    relationship: "downstream — the retrieval era builds directly on the embedding lineage traced here"
  - to: reasoning-and-chain-of-thought
    relationship: "downstream — inference-time reasoning is the latest turn in the arc this history sets up"
  - to: from-retrieval-to-reasoning
    relationship: "synthesis — this history is the backstory that synthesis assumes"
---

# A History of AI in Three Eras: Symbolic, Neural, and Transformer

## Abstract

Modern language models did not appear without antecedents. They are the current endpoint of a seventy-year
argument about how to build intelligent behavior, an argument that swung twice between two opposed bets. The
first bet, **symbolic AI**, held that intelligence is the manipulation of discrete symbols by explicit rules;
it produced theorem provers, dialogue programs, and expert systems, and then stalled on the problem of
acquiring knowledge by hand. The second bet, **connectionism**, held that intelligence emerges from adjusting
the weights of a network of simple units trained on data; it was twice dismissed as a dead end and twice
revived, decisively so after 2012. The **Transformer** (Vaswani et al., 2017) fused the connectionist
substrate with an attention mechanism that scaled, and the subsequent discovery of predictable scaling laws
turned model-building into an engineering discipline. This review traces the primary literature of all three
eras, reports the benchmark deltas that ended each debate, and shows — in runnable code — the single result
that separates the symbolic and neural bets.

## Why it matters

An engineer who treats a large language model as a self-contained novelty will misread its failure modes. The
model's tokenizer, its next-token objective, its brittleness on tasks requiring exact symbolic manipulation,
and its appetite for data and compute are all inheritances. Retrieval augmentation exists because parametric
models forget and confabulate — a rediscovery of the symbolic era's insistence on explicit, inspectable
knowledge. Chain-of-thought prompting reintroduces the step-by-step search that the General Problem Solver
performed in 1959, now over a learned distribution rather than hand-written operators. Knowing which problems
each era solved, and which it merely deferred, tells you where a modern system's competence actually comes
from and where it is borrowed. This explainer is the historical spine for the rest of the series: the
retrieval, reasoning, and self-improvement explainers each pick up a thread that starts here.

## Core concepts

- **Symbolic AI (GOFAI, "Good Old-Fashioned AI").** The paradigm that represents knowledge as discrete
  symbols and produces behavior by applying explicit logical rules to them. Reasoning is search through a
  space of symbol structures.
- **Physical Symbol System Hypothesis.** The claim, stated formally by Newell and Simon, that a physical
  symbol system has the *necessary and sufficient* means for general intelligent action. This is the
  foundational commitment of the symbolic era.
- **Connectionism / neural network.** A model composed of many simple units ("neurons") whose weighted
  connections are adjusted by a learning algorithm. Knowledge lives in the weights, not in inspectable rules.
- **Perceptron.** The simplest neural unit: a weighted sum of inputs passed through a threshold. It can learn
  any **linearly separable** function — one whose positive and negative examples can be divided by a single
  hyperplane — and no others.
- **Backpropagation.** An algorithm that computes the gradient of a network's error with respect to every
  weight by applying the chain rule backward through the layers, enabling training of networks with hidden
  layers.
- **Expert system.** A symbolic program that encodes a human specialist's knowledge as if-then rules and
  applies them to a narrow domain (medical diagnosis, chemical analysis, hardware configuration).
- **AI winter.** A period of collapsed funding and interest following a gap between promised and delivered
  capability. Two are conventionally dated: mid-1970s and late-1980s to mid-1990s.
- **Attention.** A mechanism that lets a model compute, for each output position, a weighted combination of
  all input positions, where the weights are learned functions of the content. It replaces the fixed-length
  bottleneck of a recurrent encoder.
- **Scaling law.** An empirical power-law relationship between a model's loss and the resources spent on it
  (parameters, data, compute).

## The literature

### Era I — Symbolic AI (1956–1990s)

**The founding.** The field named itself at a 1956 summer workshop at Dartmouth College, proposed the year
before by John McCarthy, Marvin Minsky, Nathaniel Rochester, and Claude Shannon. Their proposal asserted that
"every aspect of learning or any other feature of intelligence can in principle be so precisely described
that a machine can be made to simulate it" (McCarthy et al., 1955; reprinted 2006). The confidence of that
sentence set the tone for the era.

Working programs arrived immediately. Newell and Simon's **Logic Theorist** — described in their 1956 paper
on "the logic theory machine" — proved theorems from Whitehead and Russell's *Principia Mathematica* by
heuristic search, and is often called the first AI program (Newell & Simon, 1956). Their **General Problem
Solver** generalized the idea: GPS separated task-independent problem-solving machinery from domain knowledge
and searched by **means-ends analysis**, repeatedly reducing the difference between the current state and the
goal (Newell, Shaw & Simon, 1959). Joseph Weizenbaum's **ELIZA** (1966) simulated a Rogerian psychotherapist
with pattern-matching scripts and no understanding whatever; Weizenbaum was disturbed by how readily users
attributed comprehension to it, and the paper is as much a caution as a demonstration (Weizenbaum, 1966).
Terry Winograd's **SHRDLU** (1972) went further, carrying on a dialogue about a simulated "blocks world" —
parsing instructions, resolving pronouns, and answering questions about its own actions — which for a time
looked like a path to genuine language understanding (Winograd, 1972).

**The intellectual commitment.** Newell and Simon crystallized the era's premise in their 1976 Turing Award
lecture: the **Physical Symbol System Hypothesis**, that "a physical symbol system has the necessary and
sufficient means for general intelligent action" (Newell & Simon, 1976). Intelligence, on this view, *is*
symbol manipulation; the research program is to find the right symbols and the right search.

**Expert systems and the knowledge bottleneck.** The 1970s and 1980s bet that intelligence would come from
*knowledge*, not just search. **DENDRAL**, begun at Stanford, inferred molecular structures from mass
spectrometry data using rules elicited from chemists — the first program to rival specialists in a scientific
task (Buchanan & Feigenbaum, 1978). **MYCIN** diagnosed bacterial infections and recommended antibiotics,
reasoning under uncertainty with hand-tuned "certainty factors" (Shortliffe & Buchanan, 1975). The commercial
proof came from Digital Equipment Corporation's **R1/XCON**, which configured VAX computer orders; McDermott
reported it applied roughly 800 rules and, by the company's accounting, saved DEC millions per year — the
result that launched the expert-systems industry (McDermott, 1982). But every one of these systems exposed
the same wall: the **knowledge-acquisition bottleneck**. Rules had to be extracted from experts by hand, they
did not generalize past their narrow domain, they grew brittle as rule bases interacted, and — crucially — the
systems could not *learn* from their own experience.

**The winters.** Funding twice collapsed when capability lagged the promises. In Britain, the **Lighthill
Report** (1973) told the Science Research Council that AI had failed to deliver on its grand claims and that
its methods would not scale past toy problems ("combinatorial explosion"), and UK academic AI funding was
gutted for a decade (Lighthill, 1973). A second winter followed the late-1980s collapse of the specialized
Lisp-machine market and disillusionment with expert systems. The underlying diagnosis was the same each time:
symbolic systems could not acquire common-sense knowledge at scale, and hand-authored rules do not survive
contact with the open world.

### Era II — The neural revolution (1958–2017)

**The first wave and the first refutation.** Frank Rosenblatt's **perceptron** (1958) was a trainable linear
classifier with a biologically inspired story and a convergence guarantee for linearly separable data
(Rosenblatt, 1958). Minsky and Papert's *Perceptrons* (1969) then proved the limit precisely: a single-layer
perceptron cannot represent functions that are not linearly separable — the exclusive-or (XOR) being the
canonical example (Minsky & Papert, 1969). Multi-layer networks could in principle represent XOR, but no one
had a practical way to train the hidden layers, and neural research went dormant.

**Backpropagation.** The revival's key algorithm was popularized by Rumelhart, Hinton, and Williams in a 1986
*Nature* paper: **backpropagation** computes the error gradient for every weight by the chain rule and lets
hidden layers learn useful internal representations (Rumelhart, Hinton & Williams, 1986). It made
multi-layer training routine and dissolved the XOR objection. LeCun and colleagues put it to work on a real
task, training a convolutional network to read handwritten ZIP-code digits directly from pixels (LeCun et al.,
1989); the mature version, **LeNet-5**, was described in the 1998 survey that also introduced the MNIST-style
document-recognition pipeline (LeCun et al., 1998). Hochreiter and Schmidhuber's **Long Short-Term Memory**
(1997) gave recurrent networks a gating mechanism that preserved gradients over long sequences, the workhorse
for sequential data for the next fifteen years (Hochreiter & Schmidhuber, 1997).

**The second winter and the 2006 revival.** Through the 1990s and early 2000s, deep networks were hard to
train and were routinely beaten by support-vector machines and other shallow methods; funding and attention
drifted away again. The thaw is conventionally dated to Hinton, Osindero, and Teh (2006), who showed that
**greedy layer-wise unsupervised pre-training** of a deep belief network gave a good initialization from which
gradient descent could then train deep models effectively (Hinton, Osindero & Teh, 2006). Two enabling
ingredients arrived alongside: the **ImageNet** dataset, over a million labeled images across a thousand
categories (Deng et al., 2009), and cheap GPU compute.

**AlexNet — the decisive result.** The debate ended in 2012. Krizhevsky, Sutskever, and Hinton trained a deep
convolutional network ("AlexNet") on ImageNet and won the ILSVRC-2012 competition with a top-5 error of
**15.3%**, against **26.2%** for the best non-neural entry — a gap wide enough that computer vision converted
to deep learning within a year (Krizhevsky, Sutskever & Hinton, 2012). ReLU activations, dropout
regularization, and GPU training were the load-bearing tricks.

**From vision to language.** The neural wave then reached NLP. Mikolov and colleagues' **word2vec** (2013)
learned dense word vectors — "embeddings" — in which semantic and syntactic relations appeared as linear
directions (the *king − man + woman ≈ queen* regularity), and did so cheaply enough to train on billions of
words (Mikolov et al., 2013). Sutskever, Vinyals, and Le's **sequence-to-sequence** model (2014) mapped a
variable-length input to a variable-length output with an encoder–decoder pair of LSTMs, reaching a BLEU
score of 34.8 on English-to-French translation and establishing the framing that machine translation, and
soon much else, was sequence transduction (Sutskever, Vinyals & Le, 2014). Its bottleneck — cramming the
whole source sentence into one fixed-length vector — was removed the same year by Bahdanau, Cho, and Bengio,
whose **attention** mechanism let the decoder attend to a learned, content-dependent mixture of source
positions at each step, sharply improving translation of long sentences (Bahdanau, Cho & Bengio, 2014). The
limits of recurrence remained: it processed tokens sequentially, so it was slow to train and still strained
on very long-range dependencies.

### Era III — The Transformer and scaling (2017–present)

**Attention is all you need.** Vaswani et al. (2017) removed recurrence entirely. The **Transformer** builds
its representations from stacked **self-attention** and feed-forward layers, with multi-head attention and
positional encodings supplying, respectively, multiple relational views and word-order information. Because
self-attention relates all positions in parallel, the architecture trains far more efficiently on modern
hardware; it set new machine-translation state of the art (28.4 BLEU on WMT-2014 English-to-German) at a
fraction of prior training cost (Vaswani et al., 2017). Parallelism, not raw accuracy, was the revolution:
the Transformer was the first language architecture built to scale.

**Pre-training and the scaling era.** Two 2018 papers established the now-standard recipe of pre-train then
adapt. OpenAI's **GPT** used a left-to-right Transformer decoder pre-trained to predict the next token, then
fine-tuned per task (Radford et al., 2018). Google's **BERT** pre-trained a Transformer *encoder*
bidirectionally with a masked-language-model objective and advanced eleven NLP benchmarks, including a GLUE
score of 80.5 (Devlin et al., 2018). Scale then became the story. **GPT-2** (2019) showed that a larger model
trained on more web text could perform many tasks with no task-specific training, and OpenAI staged its
release over concerns about misuse (Radford et al., 2019). **GPT-3**, at 175 billion parameters, made the
decisive observation: at sufficient scale a frozen model performs new tasks from a few examples in its prompt
— **in-context learning** — without any gradient updates (Brown et al., 2020).

**Turning scale into a science.** Kaplan et al. (2020) found that language-model loss falls as a smooth
**power law** in model size, dataset size, and compute, across seven orders of magnitude — meaning capability
gains from scaling were, to a first approximation, predictable (Kaplan et al., 2020). Hoffmann et al. (2022)
corrected the compute-optimal recipe: for a fixed compute budget, parameters and training tokens should scale
**in roughly equal proportion**, implying that models like GPT-3 were badly under-trained on data. Their
70-billion-parameter **Chinchilla**, trained on 4× more data under the same budget as the 280B Gopher,
outperformed it — reorienting the field from "bigger models" to "more, better-matched data" (Hoffmann et al.,
2022).

**Alignment.** A capable next-token predictor is not yet a helpful assistant. Ouyang et al. (2022) fine-tuned
GPT-3 with **reinforcement learning from human feedback (RLHF)**: collect human preference comparisons of model
outputs, train a reward model on them, and optimize the policy against that reward. Human raters preferred the
outputs of the resulting 1.3-billion-parameter **InstructGPT** over those of the 175-billion-parameter GPT-3 —
a 100× smaller model, preferred because it was aligned to intent (Ouyang et al., 2022). That technique, applied
at product scale, is what turned a raw language model into the conversational assistants that followed.

## Worked code

The single result that divides the symbolic and neural eras — Minsky and Papert's proof that a perceptron
cannot learn XOR — is short enough to reproduce from scratch. The code below implements Rosenblatt's
perceptron and its learning rule in NumPy, then shows it *converging* on a linearly separable function (logical
AND) and *failing to converge* on XOR. That failure is the wall that ended the first neural wave; hidden layers
trained by backpropagation (Rumelhart, Hinton & Williams, 1986) are what climbed over it.

```python
import numpy as np

def train_perceptron(X, y, lr=0.1, epochs=50, seed=0):
    """Rosenblatt's perceptron. Returns weights, bias, and epochs-to-converge
    (or None if it never reaches zero training errors)."""
    rng = np.random.default_rng(seed)
    w = rng.normal(scale=0.01, size=X.shape[1])
    b = 0.0
    for epoch in range(1, epochs + 1):
        errors = 0
        for xi, target in zip(X, y):
            pred = 1 if (np.dot(w, xi) + b) > 0 else 0   # threshold unit
            update = lr * (target - pred)                # perceptron rule
            w += update * xi
            b += update
            errors += int(update != 0.0)
        if errors == 0:
            return w, b, epoch
    return w, b, None

X = np.array([[0, 0], [0, 1], [1, 0], [1, 1]], dtype=float)

# AND is linearly separable -> the perceptron converges.
y_and = np.array([0, 0, 0, 1])
w, b, e = train_perceptron(X, y_and)
print(f"AND: converged in {e} epochs; predictions =",
      [(int(np.dot(w, xi) + b > 0)) for xi in X])

# XOR is NOT linearly separable -> no separating line exists, so it never converges.
y_xor = np.array([0, 1, 1, 0])
w, b, e = train_perceptron(X, y_xor)
print(f"XOR: converged = {e is not None}; predictions =",
      [(int(np.dot(w, xi) + b > 0)) for xi in X])
```

Expected output:

```
AND: converged in 9 epochs; predictions = [0, 0, 0, 1]
XOR: converged = False; predictions = [1, 1, 0, 0]
```

The perceptron nails AND in a handful of passes and never gets XOR right, no matter how long it trains,
because no single straight line separates the two XOR classes. The fix is not a better learning rate but a
different architecture — a hidden layer, which requires a way to assign credit to weights that do not touch
the output. Backpropagation is that credit-assignment algorithm, and the leap from this failing loop to a
trainable multi-layer network is the whole bridge from Era I's dead end to Era II's revival.

## Open problems

- **The symbolic bet was deferred, not disproven.** Neural models are strong at perception and pattern
  completion and weak at exact, compositional, multi-step reasoning — precisely the regime symbolic systems
  were built for. Whether reliable reasoning is best obtained by scaling neural models, by neuro-symbolic
  hybrids, or by external tools remains unsettled; the reasoning explainer in this series takes up the
  current evidence.
- **Knowledge acquisition, again.** The expert-systems bottleneck — getting correct, current knowledge into
  the system — reappears as hallucination and staleness in LLMs. Retrieval augmentation is the modern answer,
  and it is a partial one; see the RAG explainer.
- **Scaling's ceiling is unknown.** Power-law fits (Kaplan et al., 2020; Hoffmann et al., 2022) predict loss,
  not capability, and they are extrapolations. High-quality training data is finite, and whether the curves
  bend is an empirical question still being answered.
- **Alignment is unsolved in general.** RLHF (Ouyang et al., 2022) aligns models to *rated* preferences,
  which are a proxy for intent; reward hacking, sycophancy, and specification gaming persist. The
  self-improvement explainer treats the risks that compound when such systems optimize themselves.

## Connections & further reading

- **[Retrieval-Augmented Generation](rag.md)** *(downstream)* — the retrieval era builds directly on the
  embedding lineage (word2vec → sentence and passage encoders) traced in Era II.
- **[Reasoning & Chain-of-Thought](reasoning-and-chain-of-thought.md)** *(downstream)* — inference-time
  reasoning is the latest turn in this arc, and a partial return to Era I's explicit search.
- **[From Retrieval to Reasoning](from-retrieval-to-reasoning.md)** *(synthesis)* — the essay that unifies
  retrieval, reasoning, and self-improvement assumes exactly the backstory assembled here.

### References

1. McCarthy, J., Minsky, M., Rochester, N., & Shannon, C. (1955; reprinted 2006). *A Proposal for the
   Dartmouth Summer Research Project on Artificial Intelligence*. AI Magazine, 27(4).
   DOI: [10.1609/aimag.v27i4.1904](https://doi.org/10.1609/aimag.v27i4.1904)
2. Newell, A., & Simon, H. A. (1956). *The logic theory machine — A complex information processing system*.
   IRE Transactions on Information Theory, 2(3).
   DOI: [10.1109/TIT.1956.1056797](https://doi.org/10.1109/TIT.1956.1056797)
3. Newell, A., Shaw, J. C., & Simon, H. A. (1959). *Report on a general problem-solving program*. Proceedings
   of the International Conference on Information Processing (UNESCO), 256–264.
   [Semantic Scholar](https://www.semanticscholar.org/paper/Report-on-a-general-problem-solving-program-Newell-Shaw/97876c2195ad9c7a4be010d5cb4ba6af3547421c)
4. Weizenbaum, J. (1966). *ELIZA — a computer program for the study of natural language communication between
   man and machine*. Communications of the ACM, 9(1).
   DOI: [10.1145/365153.365168](https://doi.org/10.1145/365153.365168)
5. Winograd, T. (1972). *Understanding Natural Language*. Cognitive Psychology, 3(1).
   DOI: [10.1016/0010-0285(72)90002-3](https://doi.org/10.1016/0010-0285(72)90002-3)
6. Newell, A., & Simon, H. A. (1976). *Computer science as empirical inquiry: symbols and search*.
   Communications of the ACM, 19(3).
   DOI: [10.1145/360018.360022](https://doi.org/10.1145/360018.360022)
7. Buchanan, B. G., & Feigenbaum, E. A. (1978). *DENDRAL and Meta-DENDRAL: Their applications dimension*.
   Artificial Intelligence, 11(1–2).
   DOI: [10.1016/0004-3702(78)90010-3](https://doi.org/10.1016/0004-3702(78)90010-3)
8. Shortliffe, E. H., & Buchanan, B. G. (1975). *A model of inexact reasoning in medicine* (the MYCIN
   certainty-factor model). Mathematical Biosciences, 23(3–4).
   DOI: [10.1016/0025-5564(75)90047-4](https://doi.org/10.1016/0025-5564(75)90047-4)
9. McDermott, J. (1982). *R1: A rule-based configurer of computer systems* (XCON). Artificial Intelligence,
   19(1). DOI: [10.1016/0004-3702(82)90021-2](https://doi.org/10.1016/0004-3702(82)90021-2)
10. Lighthill, J. (1973). *Artificial Intelligence: A General Survey* (the Lighthill Report). In *Artificial
    Intelligence: a paper symposium*, Science Research Council.
    [Chilton Computing archive](https://www.chilton-computing.org.uk/inf/literature/reports/lighthill_report/p001.htm)
11. Rosenblatt, F. (1958). *The perceptron: a probabilistic model for information storage and organization in
    the brain*. Psychological Review, 65(6).
    DOI: [10.1037/h0042519](https://doi.org/10.1037/h0042519)
12. Minsky, M., & Papert, S. (1969). *Perceptrons: An Introduction to Computational Geometry*. MIT Press.
    [MIT Press](https://mitpress.mit.edu/9780262630221/perceptrons/)
13. Rumelhart, D. E., Hinton, G. E., & Williams, R. J. (1986). *Learning representations by back-propagating
    errors*. Nature, 323. DOI: [10.1038/323533a0](https://doi.org/10.1038/323533a0)
14. LeCun, Y., Boser, B., Denker, J. S., et al. (1989). *Backpropagation applied to handwritten zip code
    recognition*. Neural Computation, 1(4).
    DOI: [10.1162/neco.1989.1.4.541](https://doi.org/10.1162/neco.1989.1.4.541)
15. LeCun, Y., Bottou, L., Bengio, Y., & Haffner, P. (1998). *Gradient-based learning applied to document
    recognition* (LeNet-5). Proceedings of the IEEE, 86(11).
    DOI: [10.1109/5.726791](https://doi.org/10.1109/5.726791)
16. Hochreiter, S., & Schmidhuber, J. (1997). *Long Short-Term Memory*. Neural Computation, 9(8).
    DOI: [10.1162/neco.1997.9.8.1735](https://doi.org/10.1162/neco.1997.9.8.1735)
17. Hinton, G. E., Osindero, S., & Teh, Y.-W. (2006). *A fast learning algorithm for deep belief nets*.
    Neural Computation, 18(7).
    DOI: [10.1162/neco.2006.18.7.1527](https://doi.org/10.1162/neco.2006.18.7.1527)
18. Deng, J., Dong, W., Socher, R., Li, L.-J., Li, K., & Fei-Fei, L. (2009). *ImageNet: A large-scale
    hierarchical image database*. IEEE CVPR 2009.
    DOI: [10.1109/CVPR.2009.5206848](https://doi.org/10.1109/CVPR.2009.5206848)
19. Krizhevsky, A., Sutskever, I., & Hinton, G. E. (2012). *ImageNet classification with deep convolutional
    neural networks* (AlexNet). NeurIPS 2012; reprinted Communications of the ACM, 60(6), 2017.
    DOI: [10.1145/3065386](https://doi.org/10.1145/3065386)
20. Mikolov, T., Chen, K., Corrado, G., & Dean, J. (2013). *Efficient Estimation of Word Representations in
    Vector Space* (word2vec). arXiv:[1301.3781](https://arxiv.org/abs/1301.3781)
21. Sutskever, I., Vinyals, O., & Le, Q. V. (2014). *Sequence to Sequence Learning with Neural Networks*.
    arXiv:[1409.3215](https://arxiv.org/abs/1409.3215)
22. Bahdanau, D., Cho, K., & Bengio, Y. (2014). *Neural Machine Translation by Jointly Learning to Align and
    Translate*. arXiv:[1409.0473](https://arxiv.org/abs/1409.0473)
23. Vaswani, A., Shazeer, N., Parmar, N., et al. (2017). *Attention Is All You Need*.
    arXiv:[1706.03762](https://arxiv.org/abs/1706.03762)
24. Radford, A., Narasimhan, K., Salimans, T., & Sutskever, I. (2018). *Improving Language Understanding by
    Generative Pre-Training* (GPT). OpenAI technical report.
    [PDF](https://cdn.openai.com/research-covers/language-unsupervised/language_understanding_paper.pdf)
25. Devlin, J., Chang, M.-W., Lee, K., & Toutanova, K. (2018). *BERT: Pre-training of Deep Bidirectional
    Transformers for Language Understanding*. arXiv:[1810.04805](https://arxiv.org/abs/1810.04805)
26. Radford, A., Wu, J., Child, R., Luan, D., Amodei, D., & Sutskever, I. (2019). *Language Models are
    Unsupervised Multitask Learners* (GPT-2). OpenAI technical report.
    [PDF](https://cdn.openai.com/better-language-models/language_models_are_unsupervised_multitask_learners.pdf)
27. Brown, T. B., Mann, B., Ryder, N., et al. (2020). *Language Models are Few-Shot Learners* (GPT-3).
    arXiv:[2005.14165](https://arxiv.org/abs/2005.14165)
28. Kaplan, J., McCandlish, S., Henighan, T., et al. (2020). *Scaling Laws for Neural Language Models*.
    arXiv:[2001.08361](https://arxiv.org/abs/2001.08361)
29. Hoffmann, J., Borgeaud, S., Mensch, A., et al. (2022). *Training Compute-Optimal Large Language Models*
    (Chinchilla). arXiv:[2203.15556](https://arxiv.org/abs/2203.15556)
30. Ouyang, L., Wu, J., Jiang, X., et al. (2022). *Training language models to follow instructions with human
    feedback* (InstructGPT). arXiv:[2203.02155](https://arxiv.org/abs/2203.02155)
