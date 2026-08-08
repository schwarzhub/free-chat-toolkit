---
name: web-development
description: Act as a front-end web-development co-pilot — generate, customize, and explain self-contained HTML/CSS/JS pages and components, returned as fenced code ready to preview in the sandboxed viewer.
when-to-use: The user wants a web UI built or explained — a landing page, dashboard, form, component, or a concept like CSS Grid/Flexbox/responsive design/accessibility — and wants runnable code they can see immediately, not a framework project.
draws-on: preview_web*, fetch_rendered*, the web-templates recipes (../../recipes/web-templates/)
status: authored
---

# Web Development Suite

Turn the assistant into a **front-end co-pilot**: generate, customize, and explain HTML/CSS/JavaScript on
demand. Everything is returned as a **single self-contained file** in a fenced ```html block so it can be
rendered instantly in the sandboxed viewer and adapted by the user.

Scope is deliberately front-end: static HTML/CSS/JS pages and components. **Out of scope:** server-side
code (Node/PHP/Python backends), databases, deployment/CI, and security-critical code (auth, tokens,
CORS) — say so and stop rather than emitting insecure boilerplate.

## Start from a proven template

Six validated, fully self-contained templates live in
[`recipes/web-templates/`](../../recipes/web-templates/) — reach for one as the base instead of writing
from a blank file:

| Need | Template |
|------|----------|
| Admin / metrics view | `dashboard.html` |
| Product / project front page | `landing-page.html` |
| Sign-in / sign-up | `login-form.html` |
| Help / FAQ | `faq-accordion.html` |
| Portfolio, catalog, gallery | `card-grid.html` |
| Roadmap, history, changelog | `timeline.html` |

Each defines its palette and spacing as `:root` custom properties at the top — the first customization
lever. When nothing fits, compose from these patterns; don't claim a template exists that doesn't.

## Workflow

1. **Clarify the target** — one concrete page/component, its purpose, and any brand/color/content
   constraints. Don't over-ask; pick sensible defaults and state them.
2. **Pick a base** — the closest template above, or a clean scaffold if none fits.
3. **Generate / customize** — return ONE self-contained `.html` file: inline `<style>` and `<script>`,
   no external CDN, no build step, no paid dependencies. Keep the markup plain and comment the parts the
   user will edit.
4. **Preview** — wrap it in a fenced ```html block (the viewer renders it); if a `preview_web*` /
   `fetch_rendered*` capability is available, use it to show the rendered result.
5. **Iterate** — on tweaks, regenerate while **preserving the user's prior customizations**; change only
   what was asked.
6. **Explain when teaching** — for concept questions (Grid vs Flexbox, media queries, ARIA), give a
   short explanation *plus* a minimal live example, not prose alone.

## Quality bar

- **Self-contained** — one file, everything inline (or `data:` URIs). This keeps it previewable and
  portable; it's also required if the output is served as an artifact (strict CSP blocks external hosts).
- **Responsive** — relative units, flex/grid with `gap`, `max-width:100%` on media; the body never
  scrolls sideways.
- **Accessible defaults** — semantic elements, labelled controls, visible focus states, sufficient
  contrast. Offer an accessibility pass on request.
- **Honest** — no dead links, no invented framework APIs, no "just add your backend here" hand-waving for
  something that needs real server logic.

## Example interactions

- *"A responsive navbar, logo left, three links right, vanilla CSS."* → a self-contained page with a
  mobile hamburger toggle (inline JS), previewed.
- *"Make this dashboard's accent teal and tighten the card spacing."* → regenerate `dashboard.html` with
  the `:root` tokens changed, nothing else touched.
- *"Explain CSS Grid vs Flexbox."* → a short explanation and a two-panel live example showing when each
  wins.
