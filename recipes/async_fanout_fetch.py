#!/usr/bin/env python3
"""
recipe: async_fanout_fetch — fetch many URLs concurrently in the run_collect sandbox

what:    Given a list of URLs, fetch them ALL IN PARALLEL (browser-TLS-impersonated) with bounded
         concurrency, a per-request timeout, and retry + exponential backoff — then print one
         structured JSON blob. The canonical "collect N things at once" fan-out step.
when:    An agentic task needs to gather many pages/APIs before it can reason over them (search
         results, a list of docs, price checks across sites). Parallel is far faster than
         sequential, and the heavy, flaky I/O runs OFF the server on a disposable GitHub Actions
         runner — the async-style request pattern this repo is built around.
sandbox: run_collect  (network; curl_cffi + camoufox preinstalled; ~8 min wall-clock; no secrets).
inputs:  edit URLS, and the knobs (CONCURRENCY / TIMEOUT / RETRIES / IMPERSONATE / HEAD_CHARS).
outputs: JSON -> {ok, n, ok_count, elapsed_s, results:[{url,status,ok,ms,bytes,error,text_head}]}
caveats: respect target sites AND GitHub Actions' ToS — keep CONCURRENCY modest and don't hammer one
         host; this returns only a text_head preview per URL (raise HEAD_CHARS for more). No auth.
"""
import asyncio, json, time
from curl_cffi.requests import AsyncSession   # async, browser-TLS-impersonating HTTP

# ---- adapt these -----------------------------------------------------------
URLS = [
    "https://example.com",
    "https://httpbin.org/get",
    "https://httpbin.org/delay/2",
    # ... your targets
]
CONCURRENCY = 6          # max simultaneous requests (be polite: modest, and spread across hosts)
TIMEOUT     = 20         # seconds per request
RETRIES     = 2          # extra attempts after the first, with exponential backoff
IMPERSONATE = "chrome"   # curl_cffi TLS/JA3 profile ("chrome","safari","edge",...) to look like a browser
HEAD_CHARS  = 500        # chars of body kept per result (previews; raise if you need the full text)
# ---------------------------------------------------------------------------

async def fetch(session, sem, url):
    t0 = time.perf_counter()
    last = None
    async with sem:                              # the semaphore is what bounds concurrency
        for attempt in range(RETRIES + 1):
            try:
                r = await session.get(url, timeout=TIMEOUT, impersonate=IMPERSONATE)
                return {"url": url, "status": r.status_code, "ok": r.ok,
                        "ms": round((time.perf_counter() - t0) * 1000),
                        "bytes": len(r.content or b""),
                        "text_head": (r.text or "")[:HEAD_CHARS], "error": None}
            except Exception as e:               # timeout, DNS, TLS, connection reset, ...
                last = f"{type(e).__name__}: {e}"
                if attempt < RETRIES:
                    await asyncio.sleep(0.5 * (2 ** attempt))   # 0.5s, 1s, 2s, ...
    return {"url": url, "status": None, "ok": False,
            "ms": round((time.perf_counter() - t0) * 1000),
            "bytes": 0, "text_head": "", "error": last}

async def main():
    t0 = time.perf_counter()
    sem = asyncio.Semaphore(CONCURRENCY)
    async with AsyncSession() as session:
        results = await asyncio.gather(*(fetch(session, sem, u) for u in URLS))
    print(json.dumps({
        "ok": True,
        "n": len(results),
        "ok_count": sum(1 for r in results if r["ok"]),
        "elapsed_s": round(time.perf_counter() - t0, 2),
        "results": results,
    }, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())
