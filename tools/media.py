"""media tools (schemas + callables). Part of the free-chat tool registry."""
from ._base import *  # noqa: F401,F403

# ============================================================ frames_to_gif (Pillow — no ffmpeg)
_GIF_MAX_FRAMES = 40

_GIF_FRAME_MAX_BYTES = 5_000_000

_GIF_OUT_MAX_BYTES = 8_000_000

_GIF_MAX_DIM = 720

FRAMES_TO_GIF = {
    "type": "function",
    "function": {
        "name": "frames_to_gif",
        "description": ("Assemble a list of images (frames) into an animated GIF and return a URL to "
                        "it — closes the loop between image-generating models and short animations. "
                        f"Frames are public http(s) image URLs or data:image URLs (2-{_GIF_MAX_FRAMES}). "
                        "Bounded: frames are downscaled and the output size is capped."),
        "parameters": {
            "type": "object",
            "properties": {
                "frames": {"type": "array", "items": {"type": "string"},
                           "description": "Ordered image URLs or data:image URLs (at least 2)."},
                "fps": {"type": "number", "description": "Frames per second (default 8, 1-30)."},
                "loop": {"type": "integer", "description": "0 = loop forever (default), else loop count."},
                "max_size": {"type": "integer", "description": f"Max frame dimension in px (default 480, max {_GIF_MAX_DIM})."},
            },
            "required": ["frames"],
        },
    },
}

def _fetch_image_bytes(src: str):
    """Load raw image bytes from a data:image URL or a public http(s) URL (SSRF-guarded, capped).
    Returns (bytes, error). Kept separate from _fetch_raw, which decodes as text (corrupts binary)."""
    src = (src or "").strip()
    if src.startswith("data:image/"):
        try:
            b64 = src.split(",", 1)[1]
            raw = base64.b64decode(b64 + "=" * (-len(b64) % 4))
        except Exception:
            return None, "invalid data: URL"
        return (raw, None) if len(raw) <= _GIF_FRAME_MAX_BYTES else (None, "image too large")
    for _ in range(4):
        if not _url_is_public(src):
            return None, "must be a public http(s) image URL or a data:image URL"
        req = urllib.request.Request(src, headers={"User-Agent": "free-chat.ai/1.0", "Accept": "image/*,*/*"})
        try:
            r = urllib.request.build_opener(_NoRedirect).open(req, timeout=12)
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 303, 307, 308) and e.headers.get("Location"):
                src = urllib.parse.urljoin(src, e.headers["Location"])
                continue
            return None, f"HTTP {e.code}"
        except Exception as e:
            return None, type(e).__name__
        blob = r.read(_GIF_FRAME_MAX_BYTES + 1)
        return (blob, None) if len(blob) <= _GIF_FRAME_MAX_BYTES else (None, "image too large")
    return None, "too many redirects"

def frames_to_gif(frames=None, fps=8, loop=0, max_size=480, **_) -> str:
    if not isinstance(frames, list) or len(frames) < 2:
        return json.dumps({"ok": False, "error": "provide `frames`: a list of at least 2 image URLs or data:image URLs"})
    if len(frames) > _GIF_MAX_FRAMES:
        return json.dumps({"ok": False, "error": f"too many frames ({len(frames)}); max {_GIF_MAX_FRAMES}"})
    try:
        from PIL import Image
    except Exception:
        return json.dumps({"ok": False, "error": "image assembly is unavailable on this server"})
    Image.MAX_IMAGE_PIXELS = 8_000_000        # decompression-bomb guard (stricter than default)
    try:
        ms = max(16, min(int(max_size) if max_size else 480, _GIF_MAX_DIM))
    except (TypeError, ValueError):
        ms = 480
    imgs = []
    for i, f in enumerate(frames):
        raw, err = _fetch_image_bytes(f)
        if err:
            return json.dumps({"ok": False, "error": f"frame {i + 1}: {err}"})
        try:
            im = Image.open(io.BytesIO(raw))
            im.load()
            im = im.convert("RGBA")
        except Exception:
            return json.dumps({"ok": False, "error": f"frame {i + 1}: not a readable image"})
        im.thumbnail((ms, ms))
        imgs.append(im)
    size = imgs[0].size                       # GIF needs a consistent canvas — use the first frame's
    prepped = []
    for im in imgs:
        if im.size != size:
            im = im.resize(size)
        bg = Image.new("RGBA", size, (255, 255, 255, 255))    # flatten alpha on white
        bg.alpha_composite(im)
        prepped.append(bg.convert("RGB").convert("P", palette=Image.ADAPTIVE))
    try:
        dur = int(1000 / max(1.0, min(float(fps or 8), 30.0)))
    except (TypeError, ValueError):
        dur = 125
    try:
        lp = max(0, int(loop)) if loop is not None else 0
    except (TypeError, ValueError):
        lp = 0
    buf = io.BytesIO()
    try:
        prepped[0].save(buf, format="GIF", save_all=True, append_images=prepped[1:],
                        duration=dur, loop=lp, disposal=2, optimize=True)
    except Exception as e:
        return json.dumps({"ok": False, "error": f"GIF assembly failed: {type(e).__name__}"})
    data = buf.getvalue()
    if len(data) > _GIF_OUT_MAX_BYTES:
        return json.dumps({"ok": False, "error": f"resulting GIF is too large ({len(data) // 1024} KB); "
                           "use fewer frames or a smaller max_size"})
    from .. import artifacts
    url = "/g/" + artifacts.put(data, "image/gif")
    return json.dumps({"ok": True, "url": url, "markdown": f"![animation]({url})",
                       "frames": len(prepped), "size_px": list(size), "bytes": len(data),
                       "fps": round(1000 / dur, 1)}, ensure_ascii=False)

