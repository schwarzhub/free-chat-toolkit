# recipes/

Reusable **working scripts** captured from real solved tasks — the toolkit's growing memory.

When a `run_code` or `run_collect` script solves something generally useful, the chat **saves it here
automatically** (via `submit_contribution`, `category: recipe`) — no prompting needed. It posts only the
**sanitized, generalized script** + what it does + when to use it; **never** the user's data, inputs,
prompt text, PII, or credentials. A maintainer reviews before it's integrated. The next time a similar
task comes up, the chat starts from a **proven recipe** instead of deriving it from scratch.
**Using the chat makes the chat better** — the flywheel:

```
task → run_code/run_collect solves it → offer to save → submit_contribution → review → merge
   ↑                                                                                      │
   └──────────────── next similar task reuses the recipe ─────────────────────────────────┘
```

## What a recipe is

A small, **self-contained** script plus a short header:

- **what** it does (one line) and **when** to reach for it
- **inputs / outputs** (what to adapt, what it prints)
- **which sandbox** it runs in — `run_code` (no network) or `run_collect` (curl_cffi/camoufox, network)
- any **caveats** (rate limits, sites that block, data licensing)

A recipe is a **starting point to adapt**, not a black box. A recipe that proves broadly useful and
stable **graduates** into a real [tool](../tools) (a parameterized `{schema, callable}`) or a
[skill](../skills) (a playbook). Recipes are the on-ramp; tools/skills are the destination.

## Norms

Same as the rest of the toolkit ([out-of-bounds](../README.md#out-of-bounds--for-this-stage-of-development)):
**no paid dependencies**; `run_collect` recipes must respect GitHub Actions' ToS and rate-limit
themselves (recipes that scrape abusively or risk an account ban are out). Auto-submitted recipes carry
**only the generalized script + description — no chat data or PII.** Community-submitted and **unverified**
until a maintainer reviews.

*None yet — the first one gets saved the first time a chat solves something worth keeping.*
