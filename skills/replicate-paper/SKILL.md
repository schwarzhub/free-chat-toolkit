---
name: replicate-paper
description: Attempt to computationally reproduce a paper's results — locate its code+data, re-run the analysis in the off-box sandbox, and compare what you get to what was reported, with an honest reproduction report.
when-to-use: The user wants to know whether a paper's headline results actually reproduce from its materials — for a replication study, a referee report, teaching, or before building on it.
draws-on: run_code, fetch_url, find_paper_code*, fetch_repo*, resolve_doi*
status: authored
---

# Replicate a Paper

Goal: go from a paper to a **reproduction report** — "given the authors' code and data, do the headline
numbers come out?" Be scrupulously honest; a failed or partial reproduction reported clearly is a success.

## 1. Locate the materials
- `find_paper_code*` (Papers With Code / repo links in the paper) and `resolve_doi*` to get the paper's
  data/code availability statement. Look for a code repo (GitHub/GitLab), a data archive (OSF, Zenodo,
  Dataverse, ICPSR), and a replication package DOI.
- If materials aren't linked, `web_search` the title + "replication data"/"code"; check the author site.
- **Record provenance**: exact repo URL + commit/tag, data DOI + version. Reproducibility starts with
  pinning what you ran.

## 2. Understand before running
- `fetch_repo*` the tree + the README/replication instructions. Identify: entry point (a `make`/`run.sh`/
  master script), the target result (which table/figure), language/deps, expected runtime, and the random
  seed. Map each headline number to the script + line that produces it.

## 3. Re-run in the sandbox
- Use `run_code` (off-box, no-network, preinstalled numpy/pandas/scipy/matplotlib/sympy). Fetch the needed
  code+data files via `fetch_repo*` and pass them into the run. **Constraints to respect:**
  - **No network inside the sandbox** — pre-fetch all inputs; a script that downloads at runtime must be
    adapted to read local files.
  - **Bounded compute** — the sandbox is time/memory-capped. If the full pipeline won't fit, reproduce the
    **specific headline result** (one table/figure) rather than the whole paper, and say so.
  - **Set the seed** the paper specifies; if none, report that non-determinism limits exact reproduction.
  - Non-Python (R/Stata) materials: translate the *specific* estimation you're checking into Python
    (pandas/statsmodels-style) and note it's a re-implementation, not a run of the original code.
- Capture: the numbers you got, runtime, and any deviations you had to make.

## 4. Compare and report
Produce a **reproduction report**:
- **Verdict per result**: Reproduced ✅ / Reproduced-with-deviations ◐ / Not reproduced ✗ / Not attempted ▫
  (with why), for each headline number.
- **Side-by-side**: reported value vs. your value (point + uncertainty), and the % / SE discrepancy.
- **Deviations**: every change you made (subset of the pipeline, re-implementation, seed, environment,
  data version) — these are the caveats a reader needs.
- **Diagnosis** if it didn't reproduce: data-version mismatch, undocumented preprocessing, seed, software
  version, or a genuine discrepancy. Don't assert fraud/error — describe what differs.
- **Provenance block**: repo+commit, data DOI+version, package versions, seed.

## Guardrails
- **Report exactly what happened** — partial coverage, deviations, and failures included. Never present a
  re-implementation as a run of the original code, or claim reproduction you didn't execute.
- **Respect licenses and access** — only fetch materials the authors made public; honor data-use terms;
  don't exfiltrate restricted data. Some data is legitimately unavailable — "materials not available" is a
  valid, important finding.
- Keep the human in the loop for anything ambiguous; a reproduction report's value is its honesty.
