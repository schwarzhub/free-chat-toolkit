---
title: "Retrieval-Augmented Generation: A Literature Review"
slug: rag
tier: B
status: published
reading_time: 25 min
prerequisites: [what-is-an-llm]
series: foundations-of-modern-ai
series_order: 3
papers_cited: 16
papers_verified: true
version: 1.0
source_issue: 83
connections:
  - to: automated-prompt-optimization
    relationship: "complementary — another way to improve an LLM system without retraining it"
  - to: reasoning-and-chain-of-thought
    relationship: "downstream — retrieved context is what the reasoning process operates over at inference"
  - to: from-retrieval-to-reasoning
    relationship: "this is one layer of that synthesis — retrieval as a component of a larger reasoning system"
---

## Abstract

A pre-trained language model stores what it knows in its weights: its knowledge is frozen at training
time, opaque to inspection, and expensive to update. Retrieval-Augmented Generation (RAG) breaks this
constraint by pairing the model with an external, searchable text store and conditioning generation on
passages fetched at inference time. This review traces the literature from its two roots — decades of
information-retrieval work on sparse lexical matching (TF-IDF, BM25) and the neural dense-retrieval turn
that followed (DPR; Karpukhin et al., 2020) — through the founding RAG formulations that coupled a
retriever to a generator end-to-end (REALM, Guu et al., 2020; RAG, Lewis et al., 2020; FiD, Izacard &
Grave, 2021; RETRO, Borgeaud et al., 2021; Atlas, Izacard et al., 2022). It then covers late-interaction
retrieval (ColBERT; Khattab & Zaharia, 2020), the adaptive and corrective systems that decide *when* and
*how* to retrieve (Self-RAG, Asai et al., 2023; CRAG, Yan et al., 2024; RAPTOR, Sarthi et al., 2024),
the evaluation infrastructure (KILT, Petroni et al., 2021; RAGAS, Es et al., 2023), and the vector-index
machinery that makes billion-scale search practical (FAISS, Johnson et al., 2017; HNSW, Malkov &
Yashunin, 2016). The takeaway: retrieval turns a static model into an updatable, auditable knowledge
system, but *good* retrieval is the hard part.

## Why it matters

An LLM answering from parametric memory alone has three structural problems. It cannot know anything that
happened after its training cut-off. It cannot see private or proprietary data it was never trained on.
And when it does not know an answer, it tends to produce a fluent, confident, wrong one — a
*hallucination*. None of these are fixed by making the model bigger; they are fixed by giving the model
somewhere to look.

RAG is that somewhere. Instead of asking the model to recall a fact, a RAG system retrieves the relevant
text from a corpus and asks the model to read it. This has three consequences that matter in production:

- **Updatability without retraining.** New knowledge enters the system by adding documents to the index,
  not by fine-tuning weights. Atlas demonstrated this directly — the document index can be swapped or
  extended and the model's answers change accordingly, with no gradient step (Izacard et al., 2022).
- **Provenance.** Because the answer is conditioned on specific retrieved passages, those passages can be
  surfaced as citations. The claim becomes auditable.
- **Smaller models, competitive accuracy.** A model that can look things up needs to memorize less. Atlas
  matched and beat a 540-billion-parameter model on Natural Questions using 50× fewer parameters
  (Izacard et al., 2022); RETRO matched GPT-3-scale performance with 25× fewer parameters by retrieving
  from a two-trillion-token store (Borgeaud et al., 2021).

In a deployed LLM application, RAG is typically the layer between the user's question and the model: it
sits in front of generation, decides what context the model sees, and largely determines whether the
answer is grounded or invented.

## Core concepts

**Parametric vs. non-parametric memory.** *Parametric* knowledge lives in the model's weights, learned
during training. *Non-parametric* memory is an external store — here, a corpus of text — queried at
inference time. RAG combines both: a parametric generator and a non-parametric index (Lewis et al.,
2020).

**Sparse vs. dense retrieval.** *Sparse* retrieval represents a query and a document as high-dimensional
vectors indexed by vocabulary terms; relevance is term overlap. TF-IDF and BM25 are the canonical sparse
methods. Their weakness is the *vocabulary-mismatch problem*: a query for "canine" does not match a
document about "dogs." *Dense* retrieval instead maps text to a low-dimensional continuous vector (an
*embedding*) where semantic similarity, not exact word overlap, drives the score.

**Dual-encoder (bi-encoder).** An architecture with two encoders — one for queries, one for passages —
each producing a single vector. Relevance is a cheap dot product or cosine between the two vectors.
Because passage vectors do not depend on the query, they can be computed once, offline, and indexed. This
is what makes dense retrieval fast at query time (Karpukhin et al., 2020).

**Late interaction.** A middle ground between the dual-encoder (one vector per text, cheap, less
expressive) and a *cross-encoder* (query and document read together by one transformer, expressive but
too slow to run over a whole corpus). Late interaction keeps a *per-token* vector for each document and
scores a query against a document by summing, over query tokens, the maximum similarity to any document
token (the *MaxSim* operator). Document token vectors are still precomputable (Khattab & Zaharia, 2020).

**Approximate nearest neighbor (ANN) search.** Given a query vector, find the closest vectors in the
index. Exact search is linear in corpus size; ANN methods trade a small amount of recall for
sub-linear query time, which is what makes retrieval over millions or billions of vectors feasible (see
FAISS, Johnson et al., 2017, and HNSW, Malkov & Yashunin, 2016).

**Chunking.** Documents are split into passages ("chunks"), commonly a few hundred tokens each, because
retrieval and the generator's context window both operate on passage-sized units. Chunk size is a design
knob: too large dilutes relevance, too small fragments meaning.

**Top-*k*.** The number of passages retrieved per query. The generator conditions on these *k* passages.

## The literature

### Retrieval foundations: from lexical match to learned embeddings

Modern RAG rests on information-retrieval work that predates deep learning. The probabilistic relevance
framework — of which **BM25** is the practical instantiation — scores a document against a query using
term frequency, inverse document frequency, and a document-length normalization, all with a principled
probabilistic justification (Robertson & Zaragoza, 2009). BM25 remains a strong, cheap, and
surprisingly hard-to-beat baseline; most production RAG systems still run it, often as one half of a
hybrid retriever.

The neural turn came with **Dense Passage Retrieval (DPR)** (Karpukhin et al., 2020). DPR trains a
dual-encoder on question–passage pairs with a contrastive objective — pulling a question's embedding
toward its answer passage and away from *in-batch negatives* (the other passages in the same training
batch, reused as cheap negatives). The headline result: on open-domain QA, DPR's learned dense retriever
beat a strong Lucene-BM25 system by **9–19% absolute** in top-20 passage retrieval accuracy, and this
retrieval gain translated into new state-of-the-art end-to-end QA numbers. DPR established the dual-
encoder as the default RAG retriever, and its training recipe (in-batch negatives, dot-product scoring)
is still the standard.

### Late interaction: keeping token-level detail

The dual-encoder compresses an entire passage into one vector, which loses fine-grained information. A
cross-encoder keeps that detail but is far too slow to score a full corpus. **ColBERT** (Khattab &
Zaharia, 2020) resolves the tension with *late interaction*: it encodes query and document independently
with BERT — so document representations are still precomputable — but retains a vector per token and
scores via MaxSim. This recovers most of the cross-encoder's expressiveness at a fraction of the cost.
The drawback is index size: one vector per token is far more storage than one per passage.
**ColBERTv2** (Santhanam et al., 2022) addresses exactly this, using residual compression and denoised
supervision to cut the space footprint of late-interaction indexes by **6–10×** while improving retrieval
quality across in-domain and zero-shot benchmarks.

### The founding RAG formulations

Four papers, all from 2020–2022, defined how a retriever and a generator are coupled.

**REALM** (Guu et al., 2020) was the first to learn retrieval *during pre-training*. It augments a masked
language-model objective with a latent *knowledge retriever* and backpropagates through the retrieval
step itself — the retriever is trained by the signal of whether the retrieved document helped predict
masked tokens. REALM showed that end-to-end training of retrieval and language modeling improves open-
domain question answering over closed-book and prior retrieve-and-read approaches.

**RAG** (Lewis et al., 2020) gave the paradigm its name and its cleanest formulation. It pairs a DPR-
style retriever over a dense Wikipedia index with a BART sequence-to-sequence generator, fine-tuned
jointly. The paper introduced two variants: **RAG-Sequence**, which conditions the entire generated
answer on one set of retrieved passages, and **RAG-Token**, which can attend to a different passage for
each generated token. RAG set state-of-the-art on three open-domain QA benchmarks and produced more
specific and factual text than a parametric-only baseline.

**Fusion-in-Decoder (FiD)** (Izacard & Grave, 2021) changed *how* the generator consumes many passages.
Rather than concatenating retrieved passages into one long input, FiD encodes each passage independently
with the encoder and lets the decoder attend across all of them via cross-attention — "fusing" the
evidence in the decoder. Because encoding cost is linear in the number of passages but the decoder sees
them jointly, FiD scales to far more passages than concatenation allows, and its accuracy on Natural
Questions and TriviaQA kept improving as the passage count grew into the hundreds.

**RETRO** (Borgeaud et al., 2021) pushed retrieval to extreme scale and interleaved it with generation.
Instead of a single retrieve-then-read step, RETRO retrieves nearest-neighbor chunks from a **two-
trillion-token** database throughout decoding via chunked cross-attention. The result: performance
comparable to GPT-3 and Jurassic-1 on the Pile with **25× fewer parameters**, evidence that a large
external store can substitute for a large fraction of parametric memory.

**Atlas** (Izacard et al., 2022) is the few-shot culmination of this line. It combines a Contriever-style
dense retriever with a FiD generator and studies how to train the whole system data-efficiently. Atlas
reached **over 42% accuracy on Natural Questions using only 64 training examples**, outperforming a 540-
billion-parameter model by 3 points despite having **50× fewer parameters** — and it makes the
updatability argument concrete, since editing the index changes the model's answers with no retraining.

### Adaptive and corrective RAG

The founding systems always retrieve, and always trust what they retrieve. The next wave made both
choices conditional.

**Self-RAG** (Asai et al., 2023) trains a single model to decide *on demand* whether to retrieve at all,
to generate using retrieved passages, and to critique its own output — all via special *reflection
tokens* the model emits (signalling, e.g., whether retrieval is needed and whether a passage supports the
generated claim). These tokens also make the behavior controllable at inference. Self-RAG (7B and 13B)
outperformed strong instruction-tuned LLMs and fixed-retrieval RAG baselines across open-domain QA,
reasoning, and long-form generation tasks.

**CRAG** (Corrective Retrieval-Augmented Generation; Yan et al., 2024) attacks the failure mode where
retrieval returns irrelevant or misleading passages. It adds a lightweight *retrieval evaluator* that
scores the confidence of retrieved documents and triggers one of three actions — use them, discard them
in favor of a large-scale web search, or a blend — followed by a decompose-then-recompose step that
strips irrelevant content from within a passage. CRAG is plug-and-play atop any RAG pipeline and improved
performance across four short- and long-form generation datasets.

**RAPTOR** (Sarthi et al., 2024) rethinks the index itself for questions that require integrating
information spread across a long document. It recursively embeds, clusters, and summarizes chunks bottom-
up, building a *tree* whose higher nodes hold progressively more abstract summaries. Retrieval draws from
multiple levels of this tree, letting the model pull both fine detail and high-level context. Coupled
with GPT-4, RAPTOR improved the best result on the QuALITY reading-comprehension benchmark by **20%
absolute accuracy**.

### Evaluation

RAG has two moving parts (retrieval and generation) and several ways to fail, so evaluation is its own
sub-literature. **KILT** (Petroni et al., 2021) unifies five categories of knowledge-intensive tasks —
open-domain QA, fact-checking, slot filling, entity linking, and dialogue — over a *single shared
Wikipedia snapshot*, so that provenance and downstream accuracy can be measured against a common
knowledge source and systems can be compared component-by-component. **RAGAS** (Es et al., 2023) targets
the practical problem that reference answers are expensive: it proposes *reference-free* metrics —
faithfulness (is the answer grounded in the retrieved context?), answer relevance, and context relevance
— computed without ground-truth labels, enabling fast automated evaluation of a RAG pipeline.

### The vector-index machinery

None of the above is deployable without fast nearest-neighbor search. **FAISS** (Johnson et al., 2017)
is the library that made billion-scale similarity search practical, contributing GPU-optimized k-
selection and index structures (flat, inverted-file, product-quantized) that trade memory and recall for
speed. **HNSW** (Malkov & Yashunin, 2016) is the graph-based ANN algorithm underlying much of modern
vector search: it builds a hierarchy of proximity graphs — a coarse top layer for long-range hops down to
a dense bottom layer — giving approximate search with roughly logarithmic scaling in the number of
vectors. In practice a RAG system chooses among a flat (exact) index for small corpora, an inverted-file
index that partitions the space, and an HNSW graph for large-scale sub-millisecond retrieval — most often
via FAISS or a vector database built on these primitives.

## Worked code

A RAG pipeline is, at its core, three steps: embed a corpus, search it with a query embedding, and
assemble the retrieved passages into a prompt. The snippet below implements all three. Retrieval uses
plain NumPy cosine similarity — the exact-search case, and the clearest way to see the mechanism. It has
no paid dependencies; the generator is left as a pluggable function so the retrieval half runs on its
own.

```python
# pip install sentence-transformers numpy   (both free, open-source)
import numpy as np
from sentence_transformers import SentenceTransformer

# ---- 1. Corpus + embedding (offline, done once) ----
CORPUS = [
    "The Eiffel Tower is located in Paris, France, and was completed in 1889.",
    "BM25 is a sparse lexical ranking function from the probabilistic relevance framework.",
    "Dense Passage Retrieval trains a dual-encoder with in-batch negatives.",
    "FAISS provides GPU-accelerated approximate nearest-neighbor search at billion scale.",
    "Photosynthesis converts light energy into chemical energy in plants.",
]

encoder = SentenceTransformer("all-MiniLM-L6-v2")  # 384-dim embeddings
# normalize so that a dot product equals cosine similarity
doc_emb = encoder.encode(CORPUS, normalize_embeddings=True)  # shape (N, 384)

# ---- 2. Retrieve: top-k by cosine similarity ----
def retrieve(query, k=2):
    q = encoder.encode([query], normalize_embeddings=True)[0]  # (384,)
    scores = doc_emb @ q                # cosine sim, since both are unit-norm
    top = np.argsort(-scores)[:k]       # indices of the k highest scores
    return [(CORPUS[i], float(scores[i])) for i in top]

# ---- 3. Assemble the prompt (retrieved context + question) ----
def build_prompt(query, passages):
    context = "\n".join(f"[{i+1}] {p}" for i, (p, _) in enumerate(passages))
    return (
        "Answer the question using ONLY the context below. "
        "If the context does not contain the answer, say you don't know.\n\n"
        f"Context:\n{context}\n\nQuestion: {query}\nAnswer:"
    )

# ---- 4. Generate (plug in any LLM; stubbed here) ----
def generate(prompt):
    # Replace with a call to any local or hosted model, e.g. a transformers
    # pipeline, llama.cpp, or an API. The RAG logic above is model-agnostic.
    return "<LLM output conditioned on the assembled prompt>"

query = "Where is the Eiffel Tower?"
hits = retrieve(query, k=2)
for text, score in hits:
    print(f"{score:.3f}  {text}")
print(generate(build_prompt(query, hits)))
```

The cosine search is `doc_emb @ q` — one matrix-vector product. That is exact and fine for thousands of
documents. At millions or billions, the exact product becomes the bottleneck and you swap in an ANN
index. The FAISS drop-in replacement for step 2 is small:

```python
# pip install faiss-cpu   (free, open-source)
import faiss

d = doc_emb.shape[1]                    # embedding dimension (384)
index = faiss.IndexFlatIP(d)            # exact inner-product index
index.add(doc_emb.astype("float32"))    # for approximate search at scale,
                                        # use faiss.IndexHNSWFlat(d, 32) instead

def retrieve_faiss(query, k=2):
    q = encoder.encode([query], normalize_embeddings=True).astype("float32")
    scores, idx = index.search(q, k)    # returns top-k per query
    return [(CORPUS[i], float(s)) for s, i in zip(scores[0], idx[0])]
```

`IndexFlatIP` is still exact search; switching the single line to `IndexHNSWFlat(d, 32)` turns it into an
HNSW graph index (Malkov & Yashunin, 2016) that scales to large corpora at the cost of a little recall.
The rest of the pipeline — embedding, prompt assembly, generation — is unchanged. That separability is
the point: retrieval quality (the index and encoder) and generation quality (the model and prompt) are
independent knobs you can tune and evaluate on their own.

## Open problems

**Multi-hop retrieval.** Questions whose answer requires chaining facts across documents are poorly
served by a single query embedding, because the passages needed for later hops are not similar to the
original question. Iterative and agentic retrieval help but add latency and failure modes; unifying multi-
step retrieval with reasoning remains open (and is the subject of the *from-retrieval-to-reasoning*
explainer).

**Conflicting and noisy sources.** When retrieved passages disagree, models often average, ignore, or
silently pick one — with no principled handling of contradiction or source reliability. CRAG's retrieval
evaluator (Yan et al., 2024) is a partial answer for *irrelevant* retrieval, but resolving *conflicting*
evidence and attributing claims correctly is unsettled.

**The latency–quality tradeoff.** ANN search with HNSW is fast but sacrifices some recall; a cross-
encoder reranker recovers quality but adds tens to hundreds of milliseconds per query. Where to sit on
this curve is application-specific and there is no free lunch.

**Evaluation validity.** Reference-free metrics such as RAGAS (Es et al., 2023) rely on an LLM to judge
faithfulness and relevance, which imports the judge model's own biases and blind spots; shared benchmarks
like KILT (Petroni et al., 2021) fix a knowledge snapshot but cannot cover domain-specific, multilingual,
or adversarial settings. No single benchmark captures all the ways a RAG system fails, and human
evaluation stays costly and hard to standardize.

**Chunking and indexing are still heuristic.** How to split documents, what granularity to embed, and how
to structure the index (flat passages vs. RAPTOR-style trees; Sarthi et al., 2024) are largely empirical
choices with no settled theory, yet they materially change retrieval quality.

## Connections & further reading

- **[Automated Prompt Optimization](automated-prompt-optimization.md)** — *complementary.* RAG improves
  an LLM system by changing what the model *reads*; prompt optimization improves it by changing how the
  model is *asked*. Neither retrains the base model.
- **[Reasoning & Chain-of-Thought](reasoning-and-chain-of-thought.md)** — *downstream.* Retrieved context
  is the material the reasoning process operates over; better retrieval gives reasoning better premises.
- **[From Retrieval to Reasoning](from-retrieval-to-reasoning.md)** — *synthesis.* This review covers
  retrieval as a component; that piece situates it inside a larger system that interleaves retrieval,
  reasoning, and self-improvement.

### References

1. **Robertson, S. & Zaragoza, H.** (2009). "The Probabilistic Relevance Framework: BM25 and Beyond."
   *Foundations and Trends in Information Retrieval*, 3(4), 333–389. DOI:10.1561/1500000019.
   https://doi.org/10.1561/1500000019
2. **Malkov, Yu. A. & Yashunin, D. A.** (2016). "Efficient and robust approximate nearest neighbor search
   using Hierarchical Navigable Small World graphs." arXiv:1603.09320. https://arxiv.org/abs/1603.09320
3. **Johnson, J., Douze, M. & Jégou, H.** (2017). "Billion-scale similarity search with GPUs."
   arXiv:1702.08734. https://arxiv.org/abs/1702.08734
4. **Guu, K., Lee, K., Tung, Z., Pasupat, P. & Chang, M.-W.** (2020). "REALM: Retrieval-Augmented Language
   Model Pre-Training." arXiv:2002.08909. https://arxiv.org/abs/2002.08909
5. **Karpukhin, V., Oğuz, B., Min, S., et al.** (2020). "Dense Passage Retrieval for Open-Domain Question
   Answering." *EMNLP 2020*. arXiv:2004.04906. https://arxiv.org/abs/2004.04906
6. **Khattab, O. & Zaharia, M.** (2020). "ColBERT: Efficient and Effective Passage Search via
   Contextualized Late Interaction over BERT." *SIGIR 2020*. arXiv:2004.12832.
   https://arxiv.org/abs/2004.12832
7. **Lewis, P., Perez, E., Piktus, A., et al.** (2020). "Retrieval-Augmented Generation for Knowledge-
   Intensive NLP Tasks." *NeurIPS 2020*. arXiv:2005.11401. https://arxiv.org/abs/2005.11401
8. **Izacard, G. & Grave, E.** (2021). "Leveraging Passage Retrieval with Generative Models for Open
   Domain Question Answering." *EACL 2021*. arXiv:2007.01282. https://arxiv.org/abs/2007.01282
9. **Petroni, F., Piktus, A., Fan, A., et al.** (2021). "KILT: a Benchmark for Knowledge Intensive
   Language Tasks." *NAACL 2021*. arXiv:2009.02252. https://arxiv.org/abs/2009.02252
10. **Borgeaud, S., Mensch, A., Hoffmann, J., et al.** (2021). "Improving Language Models by Retrieving
    from Trillions of Tokens." *ICML 2022*. arXiv:2112.04426. https://arxiv.org/abs/2112.04426
11. **Santhanam, K., Khattab, O., Saad-Falcon, J., Potts, C. & Zaharia, M.** (2022). "ColBERTv2:
    Effective and Efficient Retrieval via Lightweight Late Interaction." *NAACL 2022*. arXiv:2112.01488.
    https://arxiv.org/abs/2112.01488
12. **Izacard, G., Lewis, P., Lomeli, M., et al.** (2022). "Atlas: Few-shot Learning with Retrieval
    Augmented Language Models." arXiv:2208.03299. https://arxiv.org/abs/2208.03299
13. **Asai, A., Wu, Z., Wang, Y., Sil, A. & Hajishirzi, H.** (2023). "Self-RAG: Learning to Retrieve,
    Generate, and Critique through Self-Reflection." arXiv:2310.11511. https://arxiv.org/abs/2310.11511
14. **Es, S., James, J., Espinosa-Anke, L. & Schockaert, S.** (2023). "RAGAS: Automated Evaluation of
    Retrieval Augmented Generation." arXiv:2309.15217. https://arxiv.org/abs/2309.15217
15. **Yan, S.-Q., Gu, J.-C., Zhu, Y. & Ling, Z.-H.** (2024). "Corrective Retrieval Augmented Generation."
    arXiv:2401.15884. https://arxiv.org/abs/2401.15884
16. **Sarthi, P., Abdullah, S., Tuli, A., et al.** (2024). "RAPTOR: Recursive Abstractive Processing for
    Tree-Organized Retrieval." arXiv:2401.18059. https://arxiv.org/abs/2401.18059
```
