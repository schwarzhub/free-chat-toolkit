"""schemas tools (schemas + callables). Part of the free-chat tool registry."""
from ._base import *  # noqa: F401,F403

# ============================================================ cost_status (schema only)
# The CALLABLE is injected per-request in api.py, because it needs this turn's live ledger + model.
# Advertised only when that closure is wired in (a tool-capable turn). See api.py.
COST_STATUS = {
    "type": "function",
    "function": {
        "name": "cost_status",
        "description": ("Check the running cost of THIS chat and the current model's price, plus "
                        "remaining service credits. Use it to stay cost-aware: if this session is "
                        "in deficit or on a pricey model, prefer a cheaper/free model (see "
                        "list_models) or suggest the user switch, and be economical with tool calls."),
        "parameters": {"type": "object", "properties": {}},
    },
}

# ==================================================== scheduled follow-ups (schemas; callables in api.py)
# Callables need the current conversation + key + ledger, so they're injected per-request in api.py.
# Only advertised on keyed (persisted) conversations — a follow-up needs somewhere to land.
SCHEDULE_FOLLOWUP = {
    "type": "function",
    "function": {
        "name": "schedule_followup",
        "description": ("Schedule yourself to run a task LATER and post the result into THIS "
                        "conversation (an agent-style follow-up). Use for 'check back in an hour', "
                        "'remind me tomorrow', or work that should continue after this reply. "
                        "One-shot, or recurring with a repeat count. You'll run it autonomously with "
                        "your tools; the user sees the result when they reopen the chat."),
        "parameters": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "The instruction to carry out at run time "
                                                          "(self-contained; the conversation is context)."},
                "delay": {"type": "string", "description": "When the first run happens, as a duration: "
                                                           "e.g. '90s', '30m', '2h', '1d'."},
                "every": {"type": "string", "description": "Optional: repeat interval (same format) for a "
                                                           "recurring follow-up, e.g. '1h'. Omit for one-shot."},
                "count": {"type": "integer", "description": "Optional: total number of runs for a recurring "
                                                            "follow-up (bounded). Ignored if `every` is omitted."},
            },
            "required": ["task", "delay"],
        },
    },
}

LIST_SCHEDULED = {
    "type": "function",
    "function": {
        "name": "list_scheduled",
        "description": "List this conversation-owner's scheduled follow-ups (id, task, when, status).",
        "parameters": {"type": "object", "properties": {}},
    },
}

CANCEL_SCHEDULED = {
    "type": "function",
    "function": {
        "name": "cancel_scheduled",
        "description": "Cancel a pending scheduled follow-up by its id (from list_scheduled).",
        "parameters": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]},
    },
}

def parse_duration(s: str) -> int | None:
    """'90s'/'30m'/'2h'/'1d' (or a bare number = seconds) -> seconds. None if unparseable."""
    s = (s or "").strip().lower()
    if not s:
        return None
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([smhd]?)", s)
    if not m:
        return None
    n = float(m.group(1))
    return int(n * {"": 1, "s": 1, "m": 60, "h": 3600, "d": 86400}[m.group(2)])

# ============= submit_contribution (schema built in api.py — callable needs conv/ip/rate-limit/token) ===
def submit_contribution_schema(allow_pr: bool = False) -> dict:
    """The tool schema, shaped by whether the server's token can open PRs (else issue-only)."""
    types = ["issue", "pull_request"] if allow_pr else ["issue"]
    how = ("as an ISSUE (complaint/request) or a proposal PULL REQUEST" if allow_pr
           else "as an ISSUE (complaints, requests, or a proposed capability — include any code and "
                "it goes in the issue for a maintainer to turn into a PR)")
    return {
        "type": "function",
        "function": {
            "name": "submit_contribution",
            "description": (f"File a complaint, or propose building/changing a TOOL, SKILL, or MCP "
                            f"integration on the PUBLIC free-chat-toolkit repo, on the user's behalf "
                            f"— {how}. You can include proposed `code`. IMPORTANT: you can only OPEN "
                            f"submissions — you can NEVER merge or accept them; a human maintainer "
                            f"reviews. A conversation reference hash is attached automatically. Mind "
                            f"the repo's out-of-bounds rules (no code sandbox, no exploitable/heavy-"
                            f"binary tools like ffmpeg, no compute offload — security & privacy first). "
                            f"Confirm with the user before submitting."),
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": types,
                             "description": "'issue' for a complaint/request/proposal."
                                            + (" 'pull_request' to open a proposal PR." if allow_pr else "")},
                    "category": {"type": "string", "enum": ["tool", "skill", "mcp", "other"],
                                 "description": "What kind of capability this concerns (default 'tool')."},
                    "title": {"type": "string", "description": "Short title of the complaint/suggestion."},
                    "body": {"type": "string", "description": "Details: what's wrong or what the capability should do, and why."},
                    "code": {"type": "string", "description": "Optional: proposed implementation — included for the maintainer to review."},
                },
                "required": ["type", "title", "body"],
            },
        },
    }



# run_code — off-box sandboxed execution (callable injected in api.py; needs the client IP for
# rate-limiting). Advertised only when a GitHub Actions token is configured. See runcode.py.
RUN_CODE = {
    "type": "function",
    "function": {
        "name": "run_code",
        "description": ("Run Python in a SANDBOX that is off this server (a fresh, no-network, "
                        "resource-capped environment) and get stdout / stderr / exit code back. Use "
                        "for real computation, data wrangling, quick simulations, or validating a "
                        "tool implementation — beyond what calculator/stats/regex_test cover. "
                        "Standard library ONLY: no network access, no pip installs. It spins up a "
                        "fresh runner, so it takes ~30-90s and the user waits; if it's still going "
                        "you'll get a run URL to check back. Keep code self-contained; print results."),
        "parameters": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "The self-contained Python 3 source to execute."},
            },
            "required": ["code"],
        },
    },
}
