# Proposal: research tools (the scholarly-API tools behind the Research Suite skills)

Buildable spec for the specialized tools the [Research Suite skills](../skills) draw on. All reuse
free-chat's SSRF-guarded fetcher and `_fit_json` capping, like the existing `wikipedia` / `geocode`
tools. **API landscape verified 2026-08.**

## Norm compliance first (this shapes the design)

The hard rule is **no paid dependencies** — a tool that can bill the operator per call is out. That
verdict flips two "obvious" choices:

- **OpenAlex is no longer key-free.** As of ~Feb 2026 it requires a free key and is **usage-metered**
  ($1/day free ≈ unmetered single-DOI/ID lookups + ~1k searches/day, then **prepaid/paid**). The old
  `mailto` polite pool is gone. → **Do not make OpenAlex the search backbone.** Use it, if at all, only
  for its *unmetered single-DOI lookups*, or the CC0 bulk snapshot — and gate it behind a config key
  that's empty by default (like the other network keys), so a missing key simply disables it.
- **Papers With Code is dead** (shut down Jul 2025; API defunct). → `find_paper_code` must not depend on
  it; extract repo links from the paper itself + resolve data/software DOIs instead.

**Prefer this order of sources:** truly *key-free* → *polite* (send an identifying email/UA) → *free-key*
(only if the key is the operator's and clearly free-tier, config-gated, empty-default). Never a paid tier.

Auth of the sources we lean on: **KEY-FREE** — arXiv, Europe PMC, DataCite (reads), OpenCitations, DOAJ,
OSF/Zenodo/Dryad (public reads). **POLITE (email/UA)** — Crossref (`mailto`), Unpaywall (`email`
required), NCBI E-utilities. Config: a single `RESEARCH_CONTACT_EMAIL` (polite-pool identity) + optional
`RESEARCH_*_KEY` env vars, all empty-default; a source with no key/contact is simply skipped.

## Tools

| Tool | Purpose | Sources (auth) | In → Out |
|------|---------|----------------|----------|
| `scholar_search` | Search the literature | **arXiv** (key-free), **Crossref** (polite), **Europe PMC** (key-free, biomed), **Semantic Scholar** (unauth pool; TLDR/relevance, best-effort) | query/author/year/field → ranked hits {title, authors, year, venue, doi/arxiv_id, abstract/tldr, oa_url?} |
| `resolve_doi` | DOI **or title** → full metadata | **Crossref** `/works/{DOI}` (polite; articles), **DataCite** (key-free; dataset/software DOIs) | doi\|title → {title, authors(+ORCID), year, venue, type, abstract?, references[], funders, license, retracted?} |
| `fetch_fulltext` | DOI → open-access fulltext/PDF | **Unpaywall** (polite, email required) → **Europe PMC** `fullTextXML` (key-free) → **arXiv** PDF | doi → {is_oa, best_pdf_url, hosted_text?, license, version} |
| `find_paper_code` | Paper → code + data repos | repo-link extraction from paper text/metadata; **Zenodo** + **OSF** + **Dryad** DOIs (key-free reads); HF Paper Pages (best-effort) | doi\|arxiv_id\|url → {code_repos[], data_archives[{doi,host,files_url}], availability_statement?} |
| `citation_graph` | Who-cites-whom | **OpenCitations** v2 (key-free) or Crossref reference lists | doi, direction(cites\|cited-by) → edges[{doi, year}] + counts |
| `fetch_repo` | Read a public code/data repo | GitHub API / OSF / Zenodo (key-free reads; **set a real User-Agent** — Zenodo blocks default UAs) | repo_url\|doi → {tree, file(path)→text} (read-only, size-capped) |
| `read_document` | Extract text/tables from a PDF | local (pdfminer/pymupdf-class, **pure-python, no ffmpeg/binaries**) | pdf (upload\|url) → {text, tables[], page_map} — also closes the standing #7 gap |
| `parse_bib` / `format_citations` | Normalize + render references | local parse (BibTeX/RIS) + `resolve_doi` to complete/verify | entries → {normalized[], deduped, style_rendered(APA\|Chicago\|…)} |

## Per-tool notes

- **`scholar_search`** — federate: fire the key-free/polite sources, merge + de-dupe by DOI, rank by
  source relevance + citation count. Return a `sources_queried` list so coverage is honest (the skills
  require stating corpus boundaries). arXiv needs a **3s inter-call delay**; Semantic Scholar's anon pool
  is shared/unreliable → treat as best-effort, back off on 429.
- **`resolve_doi`** — Crossref is the registry of record for articles; DataCite for data/software DOIs.
  Crossref reference lists exist only where the publisher deposited them (note the gap). **Never fabricate
  a DOI or citation** — if unresolved, say so.
- **`fetch_fulltext`** — Unpaywall returns a *link + license*, not redistribution rights. Store the
  license; the caller may read/quote under fair use but must not blanket-republish. Europe PMC gives real
  OA XML bodies for its OA subset.
- **`find_paper_code`** — primary signal is the paper's own data/code-availability statement + inline repo
  URLs; then resolve Zenodo/OSF/Dryad DOIs for archived materials. **Dryad file downloads need a ~10h
  OAuth token** (metadata is free) — treat file pull as best-effort.
- **`read_document`** — pure-python only (no ffmpeg/heavy binaries over untrusted input — out-of-bounds).
  Bound pages/size. This is the highest-leverage missing tool: `research-paper-summary`, `submission-qa`,
  `cross-project-synthesis`, and `dataset-documentation` all need it.
- **`fetch_repo`** — read-only, public repos only, size-capped, SSRF-guarded; **create-only/no-write**
  (mirrors the `github.py` create-only norm). Set a custom User-Agent.

## Rollout order (highest leverage first)
1. **`read_document`** — unblocks the most skills and closes issue #7's PDF gap; no external key.
2. **`resolve_doi` + `scholar_search`** — the literature spine (Crossref polite + arXiv + Europe PMC, all
   key-free/polite). Powers `research-paper-summary`, `systematic-review`, `cv-biosketch`.
3. **`fetch_fulltext`** (Unpaywall) + **`find_paper_code`/`fetch_repo`** — turns summaries into full-text
   reads and powers `replicate-paper` / `replication-package`.
4. **`citation_graph`** (OpenCitations) + **`parse_bib`/`format_citations`** — `bibliography-hygiene`,
   `literature-inconsistency-probe`.

Sources: [OpenAlex pricing](https://blog.openalex.org/openalex-api-new-features-and-usage-based-pricing/) ·
[Crossref REST](https://www.crossref.org/documentation/retrieve-metadata/rest-api/) ·
[arXiv API](https://info.arxiv.org/help/api/user-manual.html) · [Unpaywall](https://unpaywall.org/products/api) ·
[Europe PMC](https://europepmc.org/RestfulWebService) · [OpenCitations v2](https://api.opencitations.net/index/v2) ·
[Zenodo](https://developers.zenodo.org/) · [OSF](https://developer.osf.io/) · [Semantic Scholar](https://api.semanticscholar.org/api-docs/) ·
PapersWithCode shut down Jul 2025 (use repo-link extraction instead).
