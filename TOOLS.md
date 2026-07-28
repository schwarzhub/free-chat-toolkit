# Tools live on free-chat.ai

Snapshot of the assistant's callable tools (see the app for exact schemas).

| Tool | What it does |
|------|--------------|
| web_search | Web search via self-hosted SearXNG (engine pool + filters + selectable fields) |
| fetch_url | Fetch a page as readable text or raw HTML (SSRF-guarded) |
| http_api | Call a public REST/JSON API and get structured data |
| extract_metadata | Article metadata + JSON-LD from a page |
| extract_links | Outbound links (text, rel, same-site) |
| rss_fetch | Parse RSS/Atom feeds |
| unshorten_url | Trace a short/redirecting URL's hop chain |
| wikipedia | Clean Wikipedia summary + citation |
| geocode | Place↔coordinates via OpenStreetMap |
| json_query | Extract value(s) from JSON by dotted path |
| diff_text | Unified diff between two texts |
| regex_test | Run a regex and return real matches/groups |
| encode_decode | base64/hex/url/rot13 + md5/sha* + jwt_decode |
| stats | Exact descriptive statistics for a number list |
| random_gen | Real randomness: uuid/token/int/dice/shuffle/pick |
| frames_to_gif | Assemble image frames into an animated GIF (Pillow; served at /g/<id>) |
| calculator | Exact arithmetic + trig/log/etc |
| current_datetime | Current date/time (UTC + optional IANA tz) |
| list_models | Discover available models by capability |
| ask_model | Delegate a subtask to another model (e.g. vision), relaying text + images |
| run_code | Run Python in an OFF-BOX sandbox (no-network GitHub Actions runner) — stdout/stderr/exit |
| fetch_rendered | JS-rendered fetch via a headless browser (SPAs); heavy, rate-limited |

### Context-dependent tools
Available in certain sessions:

| Tool | What it does |
|------|--------------|
| cost_status | The model's view of this chat's running cost + remaining service credits |
| schedule_followup / list_scheduled / cancel_scheduled | Schedule a follow-up task to run later (saved-key chats) |
| submit_contribution | File a complaint or tool suggestion as an issue on this repo, from the chat |
| run_local | Run a shell command on **your own machine** via a runner you start (`curl -s https://free-chat.ai/api/runner/script \| python3 - --key YOURKEY`). You approve each command in your terminal by default (`--yolo` to auto-run). Only appears while your runner is connected. |

Missing something? Suggest it — from within free-chat, or open an issue/PR here.
