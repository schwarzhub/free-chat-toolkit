"""modeltools tools (schemas + callables). Part of the free-chat tool registry."""
from ._base import *  # noqa: F401,F403

# ============================================================ list_models (capability discovery)
# Lets a model see what OTHER models are available and what they can do — so it can suggest a better
# model to the user ("this needs vision — try X"), or pick a delegate for ask_model.
_CAP_TAGS = ["chat", "vision", "tools", "reasoning", "image", "free", "all"]

LIST_MODELS = {
    "type": "function",
    "function": {
        "name": "list_models",
        "description": ("List the chat models available on this service, optionally filtered by "
                        "capability. Use to recommend the user switch to a better-suited model, or "
                        "to choose a `model` for ask_model. Returns id, name, capabilities, and "
                        "output price (cheapest first)."),
        "parameters": {
            "type": "object",
            "properties": {
                "capability": {"type": "string", "enum": _CAP_TAGS,
                               "description": "Filter by capability. 'vision'=can see images, 'tools'=tool-calling, "
                                              "'reasoning', 'image'=image generation, 'free'=$0 logged tier. Omit for all."},
                "query": {"type": "string", "description": "Optional substring to match in id/name (e.g. 'claude', 'qwen')."},
                "limit": {"type": "integer", "description": "Max models to return (default 12, max 30)."},
            },
        },
    },
}

def list_models(capability: str = "", query: str = "", limit: int = 12, **_) -> str:
    from .. import models as _m
    cap = (capability or "").strip().lower()
    try:
        rows = _m.in_bucket(cap if cap and cap != "all" else None)
    except Exception as e:
        return json.dumps({"ok": False, "error": f"model catalog unavailable: {type(e).__name__}"})
    q = (query or "").strip().lower()
    if q:
        rows = [r for r in rows if q in (r.get("id") or "").lower() or q in (r.get("name") or "").lower()]
    rows = sorted(rows, key=lambda r: (r.get("out_price") if r.get("out_price") is not None else 1e9))
    try:
        n = max(1, min(int(limit) if limit else 12, 30))
    except (TypeError, ValueError):
        n = 12
    out = [{"id": r.get("id"), "name": r.get("name"), "capabilities": r.get("tags"),
            "price_out_per_m": r.get("out_price"), "free": r.get("free")} for r in rows[:n]]
    return json.dumps({"ok": True, "capability": cap or "all", "count": len(out), "models": out},
                      ensure_ascii=False)[:config.TOOL_RESULT_MAX_CHARS]

# ============================================================ ask_model (model-to-model delegation)
# The current model can hand a subtask it can't do itself to another model — the motivating case is
# VISION (pass image_url to a vision-capable model), but it works for any "use a stronger/cheaper/
# specialist model for this one step" need. The sub-call gets NO tools (no recursion) and a low token
# cap; cost is bounded by that + the outer tool-round limit + the spend-capped key.
ASK_MODEL = {
    "type": "function",
    "function": {
        "name": "ask_model",
        "description": ("Delegate a subtask to ANOTHER model and get its answer back — use when the "
                        "task needs a capability you lack (e.g. seeing an image: pass image_url to a "
                        "vision model) or a different model would do it better. Find a target with "
                        "list_models. The delegate answers in one shot (no tools, no follow-up)."),
        "parameters": {
            "type": "object",
            "properties": {
                "model": {"type": "string", "description": "The model id to delegate to (from list_models)."},
                "prompt": {"type": "string", "description": "The exact task/question for the delegate model."},
                "image_url": {"type": "string", "description": "Optional public http(s) image URL or data:image/ URL "
                                                              "to send to a vision model."},
                "system": {"type": "string", "description": "Optional system instruction for the delegate."},
            },
            "required": ["model", "prompt"],
        },
    },
}

def run_ask_model(model: str = "", prompt: str = "", image_url: str = "", system: str = ""):
    """Core delegation. Returns (result_json_str, usage_dict_or_None) so the caller can charge the
    delegated token cost to the session ledger. `usage` = {"input_tokens","output_tokens"}."""
    from .. import providers
    m, q = (model or "").strip(), (prompt or "").strip()
    if not m or not q:
        return json.dumps({"ok": False, "error": "both 'model' and 'prompt' are required"}), None
    prov = providers.for_model(m)
    if not prov:
        return json.dumps({"ok": False, "error": f"model '{m}' is not available (try list_models)"}), None
    content = q
    if image_url:
        u = image_url.strip()
        if not (u.startswith("data:image/") or _url_is_public(u)):
            return json.dumps({"ok": False, "error": "image_url must be a public http(s) image URL or a data:image/ URL"}), None
        content = [{"type": "text", "text": q}, {"type": "image_url", "image_url": {"url": u}}]
    dc = "allow" if m.endswith(":free") else "deny"      # same privacy tiering as a normal turn
    parts, images, err, usage = [], [], None, None
    try:
        for ev in prov.stream(m, [{"role": "user", "content": content}], system=(system.strip() or None),
                              max_tokens=config.DELEGATE_MAX_TOKENS, tools=None, tool_registry=None,
                              data_collection=dc):
            t = ev.get("type")
            if t == "token":
                parts.append(ev["text"])
            elif t == "image" and ev.get("url"):
                images.append(ev["url"])                 # delegate generated an image — relay it
            elif t == "done":
                usage = ev.get("usage")
            elif t == "error":
                err = ev.get("message")
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
    answer = "".join(parts).strip()
    # Surface delegate images as markdown so they render in the tool result / parent answer. http(s)
    # urls inline directly; data: urls only if small enough to fit the context (else a note).
    img_md = []
    for u in images:
        if u.startswith("data:") and len(u) > 200000:
            img_md.append("_[delegate returned an image too large to inline]_")
        else:
            img_md.append(f"![generated image]({u})")
    if img_md:
        answer = (answer + "\n\n" + "\n\n".join(img_md)).strip()
    if not answer:
        return json.dumps({"ok": False, "model": m, "error": err or "the delegate returned nothing"}, ensure_ascii=False), usage
    out = {"ok": True, "model": m, "answer": answer}
    if images:
        out["image_count"] = len(images)
    if usage:
        out["usage"] = usage
    return json.dumps(out, ensure_ascii=False)[:config.TOOL_RESULT_MAX_CHARS], usage

def ask_model(model: str = "", prompt: str = "", image_url: str = "", system: str = "", **_) -> str:
    # Static registry entry (no ledger). The request path overrides this with a ledger-charging
    # closure (api.py _ask_model_fn) so delegated cost hits the session balance + ad pacing.
    return run_ask_model(model, prompt, image_url, system)[0]

