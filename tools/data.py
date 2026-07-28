"""data tools (schemas + callables). Part of the free-chat tool registry."""
from ._base import *  # noqa: F401,F403

# ============================================================ calculator (safe AST eval)
CALCULATOR = {
    "type": "function",
    "function": {
        "name": "calculator",
        "description": ("Evaluate an arithmetic expression exactly. Operators + - * / ** % // and "
                        "parentheses; functions sqrt, abs, round, floor, ceil, min, max, log, log2, "
                        "log10, exp, factorial, gcd, hypot, and trig sin/cos/tan/asin/acos/atan/atan2/"
                        "radians/degrees; constants pi, e, tau. IEEE-754 double precision "
                        "(~15-17 significant digits)."),
        "parameters": {
            "type": "object",
            "properties": {"expression": {"type": "string", "description": "e.g. (1234*5.5)/3 or sqrt(2)*pi"}},
            "required": ["expression"],
        },
    },
}

_MATH_OPS = {ast.Add: _op.add, ast.Sub: _op.sub, ast.Mult: _op.mul, ast.Div: _op.truediv,
             ast.Pow: _op.pow, ast.Mod: _op.mod, ast.FloorDiv: _op.floordiv,
             ast.USub: _op.neg, ast.UAdd: _op.pos}

_MATH_FNS = {"sqrt": math.sqrt, "abs": abs, "round": round, "floor": math.floor, "ceil": math.ceil,
             "min": min, "max": max, "log": math.log, "log2": math.log2, "log10": math.log10,
             "exp": math.exp, "factorial": math.factorial, "gcd": math.gcd, "pow": pow,
             "hypot": math.hypot, "sin": math.sin, "cos": math.cos, "tan": math.tan,
             "asin": math.asin, "acos": math.acos, "atan": math.atan, "atan2": math.atan2,
             "radians": math.radians, "degrees": math.degrees}

_MATH_CONSTS = {"pi": math.pi, "e": math.e, "tau": math.tau}

def _eval_math(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.Name) and node.id in _MATH_CONSTS:
        return _MATH_CONSTS[node.id]
    if isinstance(node, ast.BinOp) and type(node.op) in _MATH_OPS:
        return _MATH_OPS[type(node.op)](_eval_math(node.left), _eval_math(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _MATH_OPS:
        return _MATH_OPS[type(node.op)](_eval_math(node.operand))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _MATH_FNS:
        if node.keywords:
            raise ValueError("no keyword args")
        return _MATH_FNS[node.func.id](*[_eval_math(a) for a in node.args])
    raise ValueError("unsupported")

def calculator(expression: str = "", **_) -> str:
    try:
        return str(_eval_math(ast.parse((expression or "").strip(), mode="eval").body))
    except Exception:
        return ("Could not evaluate that expression (allowed: + - * / ** % //, parentheses, and "
                "sqrt/abs/round/floor/ceil/min/max/log/log2/log10/exp/factorial/gcd, pi/e/tau).")

# ============================================================ current_datetime
CURRENT_DATETIME = {
    "type": "function",
    "function": {
        "name": "current_datetime",
        "description": ("Get the current date and time. Returns UTC always; pass an IANA `timezone` "
                        "(e.g. 'America/New_York', 'Europe/London') to also get the local time there "
                        "— useful for a user's local 'today'."),
        "parameters": {
            "type": "object",
            "properties": {
                "timezone": {"type": "string", "description": "IANA tz name, e.g. 'America/New_York'. Optional."},
            },
        },
    },
}

def current_datetime(timezone: str = "", **_) -> str:
    now = datetime.now(_UTC)
    out = {"utc": now.strftime("%Y-%m-%d %H:%M:%S UTC (%A)")}
    tz = (timezone or "").strip()
    if tz:
        try:
            from zoneinfo import ZoneInfo
            local = now.astimezone(ZoneInfo(tz))
            out["local"] = local.strftime("%Y-%m-%d %H:%M:%S %Z (%A)")
            out["timezone"] = tz
        except Exception:
            out["timezone_error"] = f"unknown timezone '{tz}'"
    return json.dumps(out, ensure_ascii=False)

# ============================================================ diff_text (unified diff)
DIFF_TEXT = {
    "type": "function",
    "function": {
        "name": "diff_text",
        "description": ("Compare two texts and return a unified diff (the +/- line format). Use to "
                        "show what changed between two versions of a file, config, or snippet."),
        "parameters": {
            "type": "object",
            "properties": {
                "a": {"type": "string", "description": "The 'before' / original text."},
                "b": {"type": "string", "description": "The 'after' / new text."},
                "label_a": {"type": "string", "description": "Name for the 'before' side (default a)."},
                "label_b": {"type": "string", "description": "Name for the 'after' side (default b)."},
                "context": {"type": "integer", "description": "Context lines around each change (default 3)."},
            },
            "required": ["a", "b"],
        },
    },
}

def diff_text(a: str = "", b: str = "", label_a: str = "a", label_b: str = "b", context: int = 3, **_) -> str:
    try:
        n = max(0, min(int(context), 10))
    except (TypeError, ValueError):
        n = 3
    d = list(difflib.unified_diff((a or "").splitlines(), (b or "").splitlines(),
                                  fromfile=label_a or "a", tofile=label_b or "b", lineterm="", n=n))
    return "\n".join(d)[:config.TOOL_RESULT_MAX_CHARS] if d else "No differences."

# ============================================================ regex_test
REGEX_TEST = {
    "type": "function",
    "function": {
        "name": "regex_test",
        "description": ("Test a regular expression against sample text and get the ACTUAL matches "
                        "back (don't guess regex behavior — run it). Returns each match with its "
                        "span, numbered groups, and named groups. Python `re` syntax."),
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "The regex pattern (Python re syntax)."},
                "text": {"type": "string", "description": "The text to match against (max 5000 chars)."},
                "flags": {"type": "string", "description": "Optional flag letters: i (ignorecase), m "
                                                           "(multiline), s (dotall), x (verbose), a (ascii)."},
                "max_matches": {"type": "integer", "description": "Max matches to return (default 20, max 100)."},
            },
            "required": ["pattern", "text"],
        },
    },
}

def regex_test(pattern: str = "", text: str = "", flags: str = "", max_matches: int = 20, **_) -> str:
    p = pattern or ""
    if not p:
        return json.dumps({"ok": False, "error": "pattern is required"})
    if len(p) > 500:
        return json.dumps({"ok": False, "error": "pattern too long (max 500 chars)"})
    full = text or ""
    t = full[:5000]                       # cap input — bounds cost and pathological-regex runtime
    fl = 0
    for ch in (flags or ""):
        fl |= {"i": re.I, "m": re.M, "s": re.S, "x": re.X, "a": re.A}.get(ch.lower(), 0)
    try:
        rx = re.compile(p, fl)
    except re.error as e:
        return json.dumps({"ok": False, "error": f"invalid pattern: {e}"})
    try:
        n = max(1, min(int(max_matches), 100))
    except (TypeError, ValueError):
        n = 20
    matches = []
    for mm in rx.finditer(t):
        m = {"match": mm.group(0), "start": mm.start(), "end": mm.end()}
        if mm.groups():
            m["groups"] = list(mm.groups())
        if mm.groupdict():
            m["named"] = mm.groupdict()
        matches.append(m)
        if len(matches) >= n:
            break
    res = {"ok": True, "pattern": p, "flags": flags or "", "match_count": len(matches), "matches": matches}
    if len(full) > 5000:
        res["note"] = "text truncated to 5000 chars"
    return _fit_json(res, results_key="matches")

# ============================================================ encode_decode (dev utility)
_ENC_OPS = ["base64_encode", "base64_decode", "base64url_encode", "base64url_decode",
            "url_encode", "url_decode", "hex_encode", "hex_decode", "rot13",
            "md5", "sha1", "sha256", "sha512", "jwt_decode"]

ENCODE_DECODE = {
    "type": "function",
    "function": {
        "name": "encode_decode",
        "description": ("Encode/decode or hash text without guessing. Ops: base64/base64url/url/hex "
                        "encode+decode, rot13, md5/sha1/sha256/sha512 hashes, and jwt_decode "
                        "(header+payload, NOT signature-verified)."),
        "parameters": {
            "type": "object",
            "properties": {
                "op": {"type": "string", "enum": _ENC_OPS, "description": "The operation to perform."},
                "text": {"type": "string", "description": "The input string."},
            },
            "required": ["op", "text"],
        },
    },
}

def encode_decode(op: str = "", text: str = "", **_) -> str:
    s = text or ""
    if len(s) > 100000:
        return json.dumps({"ok": False, "error": "input too long (max 100k chars)"})
    op = (op or "").strip().lower()

    def _b64u(p):
        return base64.urlsafe_b64decode(p + "=" * (-len(p) % 4)).decode("utf-8", "replace")
    try:
        if op == "base64_encode":
            r = base64.b64encode(s.encode()).decode()
        elif op == "base64_decode":
            r = base64.b64decode(s + "=" * (-len(s) % 4)).decode("utf-8", "replace")
        elif op == "base64url_encode":
            r = base64.urlsafe_b64encode(s.encode()).decode().rstrip("=")
        elif op == "base64url_decode":
            r = _b64u(s)
        elif op == "url_encode":
            r = urllib.parse.quote(s)
        elif op == "url_decode":
            r = urllib.parse.unquote(s)
        elif op == "hex_encode":
            r = s.encode().hex()
        elif op == "hex_decode":
            r = bytes.fromhex(s.strip()).decode("utf-8", "replace")
        elif op == "rot13":
            r = codecs.encode(s, "rot13")
        elif op in ("md5", "sha1", "sha256", "sha512"):
            r = hashlib.new(op, s.encode()).hexdigest()
        elif op == "jwt_decode":
            parts = s.split(".")
            if len(parts) < 2:
                return json.dumps({"ok": False, "error": "not a JWT (need header.payload.signature)"})
            return json.dumps({"ok": True, "op": op, "header": json.loads(_b64u(parts[0])),
                               "payload": json.loads(_b64u(parts[1]))}, ensure_ascii=False)[:config.TOOL_RESULT_MAX_CHARS]
        else:
            return json.dumps({"ok": False, "error": f"unknown op '{op}' (see the op enum)"})
    except Exception as e:
        return json.dumps({"ok": False, "op": op, "error": f"{type(e).__name__}: {e}"[:200]})
    return json.dumps({"ok": True, "op": op, "result": r}, ensure_ascii=False)[:config.TOOL_RESULT_MAX_CHARS]

# ============================================================ json_query (extract from JSON)
JSON_QUERY = {
    "type": "function",
    "function": {
        "name": "json_query",
        "description": ("Extract value(s) from a JSON string with a dotted path — great for pulling "
                        "specific fields out of an http_api/fetch_url response instead of eyeballing "
                        "big JSON. Path syntax: `a.b.c`, array index `items[0]`, wildcard `items[*].name` "
                        "(returns a list). Empty path returns the whole parsed value."),
        "parameters": {
            "type": "object",
            "properties": {
                "json": {"type": "string", "description": "The JSON text to query."},
                "path": {"type": "string", "description": "Dotted path, e.g. 'data.items[*].id'. Empty = whole value."},
            },
            "required": ["json"],
        },
    },
}

def json_query(path: str = "", **kw) -> str:
    raw = kw.get("json")
    if raw is None:
        raw = kw.get("data") or ""
    obj = raw if isinstance(raw, (dict, list)) else None
    if obj is None:
        try:
            obj = json.loads(raw)
        except Exception as e:
            return json.dumps({"ok": False, "error": f"input is not valid JSON: {e}"[:150]})
    p = (path or "").strip().lstrip("$").strip(".")
    if not p:
        return json.dumps({"ok": True, "path": path or "", "result": obj}, ensure_ascii=False)[:config.TOOL_RESULT_MAX_CHARS]
    toks = [t for t in re.sub(r"\[(\*|\d+)\]", r".\1", p).split(".") if t != ""]
    cur = [obj]
    for t in toks:
        nxt = []
        for o in cur:
            if t == "*":
                if isinstance(o, dict):
                    nxt.extend(o.values())
                elif isinstance(o, list):
                    nxt.extend(o)
            elif t.isdigit():
                if isinstance(o, list) and int(t) < len(o):
                    nxt.append(o[int(t)])
            elif isinstance(o, dict) and t in o:
                nxt.append(o[t])
        cur = nxt
    if not cur:
        return json.dumps({"ok": False, "path": path, "error": "no match for that path"}, ensure_ascii=False)
    result = cur if ("*" in toks or len(cur) > 1) else cur[0]
    return json.dumps({"ok": True, "path": path, "count": len(cur), "result": result},
                      ensure_ascii=False)[:config.TOOL_RESULT_MAX_CHARS]

# ============================================================ stats (exact descriptive statistics)
STATS = {
    "type": "function",
    "function": {
        "name": "stats",
        "description": ("Exact descriptive statistics for a list of numbers (count, sum, mean, "
                        "median, min, max, range, sample/population stdev + variance). Use instead "
                        "of estimating — don't do stats in your head."),
        "parameters": {
            "type": "object",
            "properties": {
                "numbers": {"type": "array", "items": {"type": "number"},
                            "description": "The numbers to summarize."},
            },
            "required": ["numbers"],
        },
    },
}

def stats(numbers=None, **_) -> str:
    nums = numbers
    if isinstance(nums, str):
        nums = re.findall(r"-?\d+(?:\.\d+)?", nums)
    if not isinstance(nums, list) or not nums:
        return json.dumps({"ok": False, "error": "provide a non-empty list of numbers"})
    try:
        vals = [float(x) for x in nums]
    except (TypeError, ValueError):
        return json.dumps({"ok": False, "error": "all items must be numbers"})
    out = {"count": len(vals), "sum": sum(vals), "mean": statistics.mean(vals),
           "median": statistics.median(vals), "min": min(vals), "max": max(vals),
           "range": max(vals) - min(vals)}
    if len(vals) >= 2:
        out["stdev_sample"] = statistics.stdev(vals)
        out["variance_sample"] = statistics.variance(vals)
        out["stdev_pop"] = statistics.pstdev(vals)
    return json.dumps({"ok": True, **{k: (round(v, 6) if isinstance(v, float) else v)
                                      for k, v in out.items()}}, ensure_ascii=False)

# ============================================================ random_gen (real randomness)
_RAND_OPS = ["uuid", "token", "int", "dice", "shuffle", "pick"]

RANDOM_GEN = {
    "type": "function",
    "function": {
        "name": "random_gen",
        "description": ("Generate real randomness (you can't — don't fake it). Ops: uuid, token "
                        "(url-safe, length n), int (in [low,high]), dice (n rolls of `high`-sided, "
                        "default 6), shuffle (a provided `items` list), pick (n random items from "
                        "`items`). Cryptographically-seeded."),
        "parameters": {
            "type": "object",
            "properties": {
                "op": {"type": "string", "enum": _RAND_OPS},
                "n": {"type": "integer", "description": "count/length (token length, dice count, picks)."},
                "low": {"type": "integer", "description": "int op: lower bound (default 0)."},
                "high": {"type": "integer", "description": "int op: upper bound (default 100); dice: sides."},
                "items": {"type": "array", "description": "list for shuffle/pick."},
            },
            "required": ["op"],
        },
    },
}

def random_gen(op: str = "uuid", n=None, low=None, high=None, items=None, **_) -> str:
    import uuid
    op = (op or "uuid").strip().lower()
    try:
        if op == "uuid":
            return json.dumps({"ok": True, "op": op, "result": str(uuid.uuid4())})
        if op == "token":
            length = max(4, min(int(n) if n else 24, 128))
            return json.dumps({"ok": True, "op": op, "result": secrets.token_urlsafe(length)[:length]})
        if op == "int":
            a = int(low) if low is not None else 0
            b = int(high) if high is not None else 100
            if a > b:
                a, b = b, a
            return json.dumps({"ok": True, "op": op, "result": secrets.randbelow(b - a + 1) + a, "range": [a, b]})
        if op == "dice":
            count = max(1, min(int(n) if n else 1, 100))
            sides = max(2, int(high) if high else 6)
            rolls = [secrets.randbelow(sides) + 1 for _ in range(count)]
            return json.dumps({"ok": True, "op": op, "sides": sides, "rolls": rolls, "total": sum(rolls)})
        if op in ("shuffle", "pick"):
            if not isinstance(items, list) or not items:
                return json.dumps({"ok": False, "error": "provide `items` (a non-empty list)"})
            arr = list(items)
            if op == "shuffle":
                for i in range(len(arr) - 1, 0, -1):
                    j = secrets.randbelow(i + 1)
                    arr[i], arr[j] = arr[j], arr[i]
                return json.dumps({"ok": True, "op": op, "result": arr}, ensure_ascii=False)[:config.TOOL_RESULT_MAX_CHARS]
            k = max(1, min(int(n) if n else 1, len(arr)))
            picks = [arr.pop(secrets.randbelow(len(arr))) for _ in range(k)]
            return json.dumps({"ok": True, "op": op, "result": picks}, ensure_ascii=False)[:config.TOOL_RESULT_MAX_CHARS]
        return json.dumps({"ok": False, "error": f"unknown op '{op}' (see the op enum)"})
    except Exception as e:
        return json.dumps({"ok": False, "op": op, "error": f"{type(e).__name__}: {e}"[:150]})

