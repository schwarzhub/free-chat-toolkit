# skills/

A **skill** is *instructions, not code* — a `SKILL.md` playbook the model reads to approach a task
using capabilities it already has (see [what a skill is](../README.md#skill)). Nothing new executes;
a skill orchestrates existing **tools**. Skills that reference a tool not yet built mark it with `*`
and list it under "Specialized tools" so it becomes a concrete [proposal](../proposals).

## Layout

Each skill is a folder `skills/<name>/` with a `SKILL.md` (and optional example files). `SKILL.md`
front-matter: `name`, `description`, `when-to-use`, `draws-on` (tools; `*` = not yet built), `status`.

## The Research Suite

The first cluster is an **academic-research workflow suite** — from reading the literature, through
running your own analysis, to shipping a submission-ready paper and its derivatives. Skills compose:
`replicate-paper` feeds `replication-package`; `scoping-review` feeds `draft-paper`; `draft-paper` feeds
`adversarial-review` → `reviewer-response`. They lean on tools free-chat already has — `run_code` (now
with numpy/pandas/scipy/matplotlib/sympy), `web_search`, `fetch_url`, `ask_model` (multi-model panels) —
plus a small set of **free scholarly-API tools** to be built (see Specialized tools).

> **A user review panel (Kimi K3, GPT-5, Claude Opus) shaped this.** Their unanimous notes drove:
> `analyze-data` added (the daily "do the research" step was the biggest gap); `systematic-review`
> renamed to `scoping-review` with an integrity banner (the name was a citation footgun); re-implementation
> quarantined from reproduction verdicts in `replicate-paper`; grounding/anti-hallucination steps and a
> confidentiality warning in `adversarial-review`; and the magnitude-anchor + retraction checks in
> `research-paper-summary`. The through-line of their critique: **force every load-bearing number/citation
> to a fetched source or an executed run — guardrails that only exhort don't hold.**

### Roadmap (from the operator's wishlist)

| # | Skill | Does | Draws on |
|---|-------|------|----------|
| **Data & analysis** *(the daily work — runs on `run_code` today)* | | | |
| 0.1 | [`analyze-data`](analyze-data) ✅ | Raw data → defensible result: cleaning log, stated estimator/SE choices, **every number from an executed run**, robustness battery | `run_code`, `read_document*`, `fetch_url` |
| 0.2 | `statistical-review` ▫ | Stats sanity-check (SE/CI/p coherence, GRIM/Statcheck-style, clustering, multiple testing) on a paper or your own results | `run_code`, `read_document*` |
| 0.3 | `measurement-validity` ▫ | Construct/measurement-validity check for a variable or scale | `run_code`, `ask_model` |
| **Literature processing** | | | |
| 1.1 | [`research-paper-summary`](research-paper-summary) ✅ | Structured single-paper summary (claims, design, identification, data, caveats) | `fetch_url`, `scholar_search*`, `resolve_doi*`, `fetch_fulltext*`, `read_document*` |
| 1.2 | [`replicate-paper`](replicate-paper) ✅ | Reproduce a paper's results — pull its code+data repo, re-run, compare to reported | `run_code`, `fetch_url`, `find_paper_code*`, `fetch_repo*` |
| 1.3 | [`scoping-review`](scoping-review) ✅ | Rapid, transparent literature synthesis (search→screen→extract→synthesize + optional quant meta-layer). **Not a PRISMA systematic review** — honest labeling built in | `scholar_search*`, `fetch_fulltext*`, `ask_model`, `run_code` |
| 1.4 | `literature-inconsistency-probe` ▫ | Where the literature disagrees + why — **a mode of `scoping-review` §5**, kept as a pointer, not a separate skill | `scholar_search*`, `ask_model` |
| 1.5 | `cross-project-synthesis` ▫ | Synthesize findings across the user's own projects/notes into shared themes + gaps | `read_document*`, `memory_*` |
| **Paper writing** | | | |
| 2.1 | `draft-paper` ▫ | Standardized base paper from results + notes (IMRaD, journal-agnostic) | `ask_model`, `read_document*` |
| 2.2 | [`adversarial-review`](adversarial-review) ✅ | Simulated multi-reviewer panel (referee reports + meta-review + revise-or-reject) | `ask_model` |
| 2.3 | `reviewer-response` ▫ | Response letter + change-tracking + comment→change map | `diff_text`, `ask_model` |
| 2.4 | `replication-package` ▫ | Assemble/validate a reproducible package (code, data, README, seed, env, one-click run) | `run_code`, `fetch_repo*` |
| 2.5 | `bibliography-hygiene` ▫ | De-dupe, complete, and validate a bibliography; fix DOIs; enforce a style | `resolve_doi*`, `parse_bib*` |
| 2.6 | `submission-qa` ▫ | Journal-readiness gate: format, word/figure counts, statements, cover letter, suggested reviewers, package | `read_document*`, `web_search` (author guidelines) |
| 2.7 | `paper-derivatives` ▫ | Slides, lay/press summary, talk script, thread, poster, editorial from one paper | `ask_model`, `frames_to_gif` |
| **Non-article writing** | | | |
| 3.1 | `grant-proposal` ▫ | Draft a proposal to a funder's structure (aims, significance, approach, budget narrative) | `read_document*`, `ask_model` |
| 3.2 | `progress-report` ▫ | Grant/lab progress report from milestones + outputs | `read_document*` |
| 3.3 | `irb-application` ▫ | IRB/ethics application + consent-language scaffold | `read_document*` |
| 3.4 | `cv-biosketch` ▫ | Update CV / NIH-style biosketch / NSF bio from a publication + activity list | `resolve_doi*`, `scholar_search*` |
| 3.5 | `lab-handbook` ▫ | Onboarding docs / lab handbook scaffold | — |
| 3.6 | `preregistration` ▫ | Pre-registration + experimental design, with a **methods checklist** (power, multiple-testing, robustness menu, sensitivity) | `run_code`, `ask_model` |
| **Engineering** | | | |
| 4.1 | `context-management` ▫ | Meta-skill: instruction-following + long-context discipline (chunk, summarize, checkpoint, verify) | — |
| 4.2 | `code-review` ▫ | Structured automated review (correctness, security, tests, simplification) | `run_code`, `diff_text` |
| 4.3 | `scraper-engineering` ▫ | Reverse-engineer + accelerate a scraper, respecting robots/rate etiquette | `fetch_url`, `fetch_rendered`, `run_code` |
| 4.4 | `dataset-documentation` ▫ | Datasheet + data dictionary + versioning/changelog for a dataset | `run_code`, `read_document*` |

✅ authored · ▫ planned

## Specialized tools these draw on (to be built — see [`../proposals`](../proposals))

All **free / key-free or polite-pool** (no paid dependencies), reusing free-chat's SSRF-guarded fetcher:

- `scholar_search` — search the literature (OpenAlex / Semantic Scholar / arXiv) by query/author/field.
- `resolve_doi` — DOI or title → full metadata + abstract + references (Crossref / OpenAlex).
- `fetch_fulltext` — DOI → open-access fulltext or PDF link (Unpaywall / Europe PMC / OpenAlex).
- `find_paper_code` — paper → linked code + data repository (Papers With Code / repo links).
- `read_document` — extract text/tables from an uploaded/URL PDF (the standing #7 gap).
- `parse_bib` / `format_citations` — parse & normalize BibTeX/RIS; render a citation style.
- `fetch_repo` — read a public code/data repo's tree + files (GitHub/OSF/Zenodo; Dataverse/Dryad/ICPSR
  best-effort, read-only).
- `memory_set` / `memory_get` — a small keyed cross-conversation store (used by `cross-project-synthesis`).

*(The scholarly-API landscape + exact endpoints are being finalized into a proposal; these specs will
land in `proposals/research-tools.md`.)*
