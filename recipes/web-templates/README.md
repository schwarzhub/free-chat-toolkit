# recipes/web-templates/

Six production-ready, **fully self-contained** HTML/CSS/JS templates — each a single `.html` file with
all styles and scripts inline, no build step, no external CDN, no paid dependencies. Drop one in a
browser and it works; copy it as the starting point for a real page and adapt.

These are the concrete assets behind the [Web Development Suite skill](../../skills/web-development/SKILL.md):
the skill is the *playbook* for building web UIs; these are *proven starting points* it can reach for.

Source: contributed via free-chat (issue #75), which embedded the complete source for all six. Each was
structurally validated (balanced tags, `<!DOCTYPE>`…`</html>`, inline `:root` design tokens).

## The templates

| File | What it is | JS | When to reach for it |
|------|------------|----|----------------------|
| [`dashboard.html`](dashboard.html) | Admin/analytics dashboard shell — sidebar, stat cards, content grid | — | An internal tool or metrics view |
| [`landing-page.html`](landing-page.html) | Marketing landing page — hero, features, CTA | — | A product or project front page |
| [`login-form.html`](login-form.html) | Centered auth card with a show/hide password toggle | tiny inline `onclick` | Sign-in / sign-up screens |
| [`faq-accordion.html`](faq-accordion.html) | Expand/collapse FAQ | none (native `<details>`) | Help / FAQ sections |
| [`card-grid.html`](card-grid.html) | Filterable responsive card grid | ~25 lines (filter) | Portfolios, catalogs, galleries |
| [`timeline.html`](timeline.html) | Vertical timeline | — | Roadmaps, histories, changelogs |

## How to use

- **Adapt, don't treat as a black box.** Each file defines its palette and spacing as `:root` custom
  properties at the top — change those first. The markup is plain and commented where it matters.
- **Inputs:** none — they're static. Wire your own data/endpoints where the placeholder content sits.
- **Sandbox:** none needed. These are static files, not `run_code`/`run_collect` scripts; open them
  directly or serve them from any static host.

## Caveats

- Static templates, not a framework. No state management, routing, or accessibility audit beyond
  sensible defaults (semantic elements, focus states) — treat them as a scaffold to build on.
- Self-contained by design: keep new assets inline (or as `data:` URIs) if you need the single-file
  property; otherwise split them out as you grow the page.
- No paid deps, no external network calls — consistent with the toolkit's
  [norms](../../README.md#out-of-bounds--for-this-stage-of-development).
