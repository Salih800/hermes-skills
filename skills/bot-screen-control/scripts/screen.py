#!/usr/bin/env python3
"""bot-screen: drive an X11 desktop with real pointer and keyboard events.

Design principle: pure visual + coordinates. No AT-SPI, no OCR, no MCP.
Every command prints a single line of JSON (use --human for readable text).

Commands:
  help                          this text
  check                         dependency + session self-check (run this first)
  info                          session summary (display, layout, lease, windows)
  shot   [--out P] [--crop x,y,w,h] [--scale S] [--grid N]
  move   X Y [--steps N] [--dur S]
  click  X Y [--button 1|2|3] [--count N] [--mods ctrl,shift] [--settle S]
                                [--expect-change [--timeout S] [--ratio R]]
  fill   X Y "text" [--no-clear] [--method auto|keys|paste]
  drag   X1 Y1 X2 Y2 [--steps N]
  scroll up|down [--amount N] [--at X,Y]
  type   "text" [--delay MS] [--method auto|keys|paste] [--layout tr] [--keep-layout]
  key    "ctrl+l" [--repeat N]
  win    list | focus <title> | move <title> X Y | resize <title> W H
  wait-change [--timeout S] [--interval S] [--ratio R] [--crop ...]
  wait-stable [--timeout S] [--quiet-for S] [--ratio R] [--interval S]
  record  [--fps N] [--seconds S] [--dir D]
  record-review --dir D [--ratio R]
  diff   A.png B.png [--pixel-threshold T]
  log    [--tail N]

Notes:
  * DISPLAY / XAUTHORITY: environment first, then <HERMES_HOME>/bot-desktop/env,
    then ~/.hermes/bot-desktop/env, then ":0" + ~/.Xauthority.
  * Screen coordinates equal image coordinates (no scaling) on a 1:1 display.
  * Every action is appended to <HERMES_HOME>/cache/screen-actions.jsonl.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

VERSION = "1.2.0"

HOME = Path.home()
HERMES_HOME = Path(os.environ.get("HERMES_HOME") or (HOME / ".hermes"))
FFMPEG = HOME / ".hermes" / "tools" / "ffmpeg-9.0.1-linux-x64" / "bin" / "ffmpeg"
SHOT_DIR = HERMES_HOME / "cache" / "screen-shots"
ACTION_LOG = HERMES_HOME / "cache" / "screen-actions.jsonl"


def _env_file_candidates() -> list[Path]:
    """Bot-desktop env file: this profile first, then the default profile."""
    out = [HERMES_HOME / "bot-desktop" / "env", HOME / ".hermes" / "bot-desktop" / "env"]
    return [p for p in dict.fromkeys(out)]


# ---------------------------------------------------------------- environment
def _bootstrap_env() -> dict:
    """Resolve DISPLAY/XAUTHORITY: environment wins, then bot-desktop/env, then a sane default."""
    env = dict(os.environ)
    if not env.get("DISPLAY") or not env.get("XAUTHORITY"):
        for cand in _env_file_candidates():
            if not cand.exists():
                continue
            for line in cand.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                env.setdefault(k, v)
            break
    env.setdefault("DISPLAY", ":0")
    if not env.get("XAUTHORITY"):
        xauth = HOME / ".Xauthority"
        env["XAUTHORITY"] = str(xauth if xauth.exists() else "")
    return env


ENV = _bootstrap_env()


def run(cmd: list[str], timeout: float = 20, check: bool = False) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, env=ENV, capture_output=True, text=True,
                              timeout=timeout, check=check)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, 124, "", "timeout")


def xdo(*args: str) -> str:
    return run(["xdotool", *args]).stdout.strip()


def ffmpeg_bin() -> str:
    """SCREEN_FFMPEG, then PATH, then the ffmpeg builds Hermes ships under tools/."""
    explicit = os.environ.get("SCREEN_FFMPEG")
    if explicit and Path(explicit).exists():
        return explicit
    found = shutil.which("ffmpeg")
    if found:
        return found
    for base in (HERMES_HOME, HOME / ".hermes"):
        for cand in sorted((base / "tools").glob("ffmpeg*/bin/ffmpeg")) if (base / "tools").exists() else []:
            if cand.exists():
                return str(cand)
    if FFMPEG.exists():
        return str(FFMPEG)
    return "ffmpeg"


# ---------------------------------------------------------------- output
HUMAN = False
QUIET = False


def emit(payload: dict, human: str = "") -> None:
    _log_action(payload)
    if QUIET:
        return
    if HUMAN and human:
        print(human)
    else:
        print(json.dumps(payload, ensure_ascii=False))


def _log_action(payload: dict) -> None:
    try:
        ACTION_LOG.parent.mkdir(parents=True, exist_ok=True)
        rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), **payload}
        with ACTION_LOG.open("a") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


def fail(msg: str, **extra) -> None:
    emit({"ok": False, "error": msg, **extra})
    sys.exit(1)


HELP = """bot-screen __VERSION__ - X11 desktop control with real pointer/keyboard events
(pure visual + coordinates: no AT-SPI, no OCR, no MCP)

  check                        Dependency and session self-check. Run this first.
  info                         Display, keyboard layout, lease holder, window count.
  shot [--out P] [--crop x,y,w,h] [--scale S] [--grid N]
                               Screenshot. --grid N overlays a labeled coordinate grid
                               (absolute screen coordinates) plus the current cursor.
  move X Y [--steps N] [--dur S]      Glide the pointer (eased, default 24 steps / 0.55 s).
  click X Y [--button N] [--count N] [--mods ctrl,shift] [--settle S]
        [--expect-change [--timeout S] [--ratio R]]
                               Glide, hover ~250 ms, click. --mods ctrl opens links in a
                               background tab. --expect-change waits for the screen to
                               change and reports changed/ratio/waited.
  fill X Y "text" [--no-clear] [--method auto|keys|paste]
                               Click a field, select-all, clear, then type (one call).
  drag X1 Y1 X2 Y2 [--steps N]        Drag with intermediate motion.
  scroll up|down [--amount N] [--at X,Y]
                               Wheel scroll (buttons 4/5), pointer moved first if --at.
  type "text" [--method auto|keys|paste] [--delay MS] [--layout L] [--keep-layout]
                               Type text. "auto" pastes through the clipboard when the
                               text has non-ASCII characters (layout-proof), otherwise
                               sends real key events. "keys" forces key events and
                               switches XKB layout when needed.
  key "ctrl+l" [--repeat N]     Keyboard shortcut.
  win list | focus <title> | move <title> X Y | resize <title> W H
                               Window handling through xdotool (no wmctrl needed).
  wait-change [--timeout S] [--interval S] [--ratio R] [--crop ...]
                               Block until the screen changes (page loaded, menu opened).
  wait-stable [--timeout S] [--quiet-for S] [--ratio R] [--interval S] [--crop ...]
                               Block until the screen stops changing (render finished).
  record [--fps N] [--seconds S] [--dir D]
                               Capture one frame per tick as PNG (default 1 fps, 5 s).
  record-review --dir D [--ratio R]
                               List the frames where the screen changed (scene cuts).
  diff A.png B.png [--pixel-threshold T]     Changed-pixel ratio between two images.
  log [--tail N]               Recent action log lines.

Global flags: --human (readable text), --quiet (no output), --crop x,y,w,h.
Exit code 1 and {"ok": false, ...} on failure; every action is logged to
<HERMES_HOME>/cache/screen-actions.jsonl."""


# ---------------------------------------------------------------- image
def capture(out: Path, crop: str | None = None, scale: float | None = None) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    vf = []
    if crop:
        x, y, w, h = [int(v) for v in crop.split(",")]
        vf.append(f"crop={w}:{h}:{x}:{y}")
    if scale:
        vf.append(f"scale=iw*{scale}:ih*{scale}:flags=lanczos")
    cmd = [ffmpeg_bin(), "-loglevel", "error", "-f", "x11grab",
           "-video_size", screen_size(), "-i", ENV["DISPLAY"], "-frames:v", "1", "-y"]
    if vf:
        cmd += ["-vf", ",".join(vf)]
    cmd.append(str(out))
    res = run(cmd, timeout=25)
    if not out.exists():
        fail("screen capture failed", stderr=res.stderr[-300:])
    return out


def add_grid(path: Path, step: int, crop: str | None = None) -> dict:
    """Overlay a labeled grid + cursor crosshair so coordinates can be read off the image."""
    from PIL import Image, ImageDraw
    img = Image.open(path).convert("RGB")
    ox, oy = (0, 0)
    if crop:
        cx, cy, _, _ = [int(v) for v in crop.split(",")]
        ox, oy = cx, cy
    draw = ImageDraw.Draw(img)
    line = (255, 0, 160)
    w, h = img.size
    def label(xy, text):
        bbox = draw.textbbox(xy, text)
        draw.rectangle([bbox[0] - 1, bbox[1] - 1, bbox[2] + 1, bbox[3] + 1], fill=(0, 0, 0))
        draw.text(xy, text, fill=line)

    for x in range(0, w, step):
        draw.line([(x, 0), (x, h)], fill=line, width=1)
        label((x + 2, 2), str(ox + x))
    for y in range(step, h, step):
        draw.line([(0, y), (w, y)], fill=line, width=1)
        label((2, y + 1), str(oy + y))
    px, py = mouse_pos()
    rx, ry = px - ox, py - oy
    if 0 <= rx < w and 0 <= ry < h:
        draw.line([(rx - 12, ry), (rx + 12, ry)], fill=(0, 255, 255), width=1)
        draw.line([(rx, ry - 12), (rx, ry + 12)], fill=(0, 255, 255), width=1)
        draw.text((min(rx + 8, w - 60), max(ry - 14, 0)), f"{px},{py}", fill=(0, 255, 255))
    img.save(path)
    return {"grid": step, "origin": [ox, oy], "cursor": [px, py]}


_SIZE_CACHE: list[str] = []


def probe_screen() -> tuple[str | None, str | None]:
    """(size, error). Non-fatal: `check` uses it to diagnose a dead display."""
    out = run(["xrandr"]).stdout
    m = re.search(r"current (\d+) x (\d+)", out)
    if m:
        return f"{m.group(1)}x{m.group(2)}", None
    err = (run(["xrandr"]).stderr or "").strip().splitlines()
    return None, (err[0] if err else "could not parse xrandr output")


def screen_size() -> str:
    if _SIZE_CACHE:
        return _SIZE_CACHE[0]
    size, err = probe_screen()
    if not size:
        fail("could not read screen size (display may be down)",
             display=ENV.get("DISPLAY"), hint=err,
             bot_desktop_env=(HERMES_HOME / "bot-desktop" / "env").exists())
    _SIZE_CACHE.append(size)
    return size


def size_tuple() -> tuple[int, int]:
    w, h = screen_size().split("x")
    return int(w), int(h)


def load_rgb(path: Path):
    from PIL import Image
    return Image.open(path).convert("RGB")


def diff_ratio(a: Path, b: Path, pixel_threshold: int = 12) -> float:
    """Fraction of changed pixels (0..1). PIL only, no numpy."""
    from PIL import ImageChops
    ia, ib = load_rgb(a), load_rgb(b)
    if ia.size != ib.size:
        ib = ib.resize(ia.size)
    d = ImageChops.difference(ia, ib).convert("L")
    hist = d.histogram()
    changed = sum(hist[pixel_threshold:])
    total = ia.size[0] * ia.size[1]
    return changed / total if total else 0.0


# ---------------------------------------------------------------- pointer
def mouse_pos() -> tuple[int, int]:
    out = xdo("getmouselocation", "--shell")
    vals = dict(line.split("=", 1) for line in out.splitlines() if "=" in line)
    return int(vals.get("X", 0)), int(vals.get("Y", 0))


def glide(x: int, y: int, steps: int = 24, dur: float = 0.55) -> None:
    x0, y0 = mouse_pos()
    steps = max(2, steps)
    for i in range(1, steps + 1):
        t = i / steps
        e = t * t * (3 - 2 * t)  # smoothstep
        cx, cy = x0 + (x - x0) * e, y0 + (y - y0) * e
        xdo("mousemove", str(round(cx)), str(round(cy)))
        time.sleep(dur / steps)


def click(x: int, y: int, button: int = 1, count: int = 1,
          mods: list[str] | None = None, settle: float = 0.25,
          steps: int = 24, dur: float = 0.55) -> dict:
    w, h = size_tuple()
    if not (0 <= x < w and 0 <= y < h):
        fail("click target is outside the screen", x=x, y=y, screen=f"{w}x{h}")
    glide(x, y, steps, dur)
    time.sleep(settle)
    mods = mods or []
    for m in mods:
        xdo("keydown", m)
    for _ in range(max(1, count)):
        xdo("click", str(button))
        time.sleep(0.05)
    for m in reversed(mods):
        xdo("keyup", m)
    return {"ok": True, "action": "click", "x": x, "y": y, "button": button,
            "count": count, "mods": mods}


def drag(x1: int, y1: int, x2: int, y2: int, steps: int = 24) -> dict:
    glide(x1, y1)
    xdo("mousedown", "1")
    time.sleep(0.1)
    x0, y0 = x1, y1
    for i in range(1, steps + 1):
        t = i / steps
        e = t * t * (3 - 2 * t)
        xdo("mousemove", str(round(x0 + (x2 - x0) * e)), str(round(y0 + (y2 - y0) * e)))
        time.sleep(0.55 / steps)
    time.sleep(0.1)
    xdo("mouseup", "1")
    return {"ok": True, "action": "drag", "from": [x1, y1], "to": [x2, y2]}


def scroll(direction: str, amount: int = 3, at: tuple[int, int] | None = None) -> dict:
    if at:
        glide(*at)
    button = "4" if direction == "up" else "5"
    for _ in range(max(1, amount)):
        xdo("click", button)
        time.sleep(0.06)
    return {"ok": True, "action": "scroll", "direction": direction, "amount": amount}


# ---------------------------------------------------------------- keyboard
TR_CHARS = set("çÇğĞıİöÖşŞüÜ")
LAYOUT_RE = re.compile(r"layout:\s+(\S+)")


def current_layout() -> str:
    out = run(["setxkbmap", "-query"]).stdout
    m = LAYOUT_RE.search(out)
    return (m.group(1).split(",")[0] if m else "unknown")


def set_layout(layout: str) -> bool:
    return run(["setxkbmap", layout]).returncode == 0


def _clipboard_get() -> str | None:
    r = run(["xclip", "-selection", "clipboard", "-o"], timeout=5)
    return r.stdout if r.returncode == 0 else None


def _clipboard_set(text: str) -> bool:
    try:
        p = subprocess.run(["xclip", "-selection", "clipboard"], input=text, text=True,
                           env=ENV, timeout=10)
        return p.returncode == 0
    except Exception:
        return False


def _paste(text: str) -> bool:
    """Paste through the clipboard: sidesteps every non-US layout problem."""
    previous = _clipboard_get()
    if not _clipboard_set(text):
        return False
    time.sleep(0.15)
    xdo("key", "--clearmodifiers", "ctrl+v")
    time.sleep(0.3)
    if previous is not None:
        _clipboard_set(previous)
    return True


def type_text(text: str, delay: int = 45, want_layout: str | None = None,
              keep_layout: bool = False, method: str = "auto") -> dict:
    """method: auto (clipboard when non-ASCII) | keys (real key events) | paste."""
    use_paste = method == "paste" or (method == "auto" and any(ord(c) > 127 for c in text))
    if use_paste and _paste(text):
        return {"ok": True, "action": "type", "chars": len(text), "method": "paste",
                "turkish_chars": sorted(TR_CHARS & set(text))}

    original = current_layout()
    switched = False
    needs_tr = bool(TR_CHARS & set(text))
    target = want_layout or ("tr" if needs_tr else None)
    if target and target not in original:
        if not set_layout(target):
            fail("could not switch keyboard layout", wanted=target, current=original)
        switched = True
        time.sleep(0.6)  # let the XKB change reach the application
    run(["xdotool", "type", "--clearmodifiers", "--delay", str(delay), text], timeout=120)
    if switched and not keep_layout:
        set_layout(original)
    return {"ok": True, "action": "type", "chars": len(text), "method": "keys",
            "layout_before": original, "layout_used": target or original,
            "layout_restored": bool(switched and not keep_layout),
            "turkish_chars": sorted(TR_CHARS & set(text))}


def press_key(combo: str, repeat: int = 1) -> dict:
    for _ in range(max(1, repeat)):
        xdo("key", combo)
        time.sleep(0.05)
    return {"ok": True, "action": "key", "keys": combo, "repeat": repeat}


# ---------------------------------------------------------------- windows
def list_windows() -> list[dict]:
    ids = [w for w in xdo("search", "--onlyvisible", "--name", "").splitlines() if w.strip()]
    seen, out = set(), []
    for wid in ids:
        if wid in seen:
            continue
        seen.add(wid)
        name = run(["xdotool", "getwindowname", wid]).stdout.strip()
        geo = run(["xdotool", "getwindowgeometry", "--shell", wid]).stdout
        vals = dict(l.split("=", 1) for l in geo.splitlines() if "=" in l)
        if not name:
            continue
        out.append({"id": wid, "title": name,
                    "x": int(vals.get("X", 0)), "y": int(vals.get("Y", 0)),
                    "w": int(vals.get("WIDTH", 0)), "h": int(vals.get("HEIGHT", 0))})
    return out


def find_window(match: str) -> str:
    for w in list_windows():
        if match.lower() in w["title"].lower():
            return w["id"]
    fail("no window matched", match=match, windows=[w["title"] for w in list_windows()])


# ---------------------------------------------------------------- change detection
def _tmp_shot(tag: str, crop: str | None) -> Path:
    p = Path("/tmp") / f"bs-{tag}-{os.getpid()}.png"
    return capture(p, crop)


def wait_change(timeout: float = 15, interval: float = 0.4, ratio_thr: float = 0.002,
                pixel_thr: int = 12, crop: str | None = None) -> dict:
    base, nxt = _tmp_shot("wc-base", crop), _tmp_shot("wc-next", crop)
    start = time.time()
    while time.time() - start < timeout:
        time.sleep(interval)
        capture(nxt, crop)
        r = diff_ratio(base, nxt, pixel_thr)
        if r >= ratio_thr:
            return {"ok": True, "changed": True, "ratio": round(r, 5),
                    "waited": round(time.time() - start, 2)}
        base, nxt = nxt, base
    return {"ok": True, "changed": False, "ratio": 0.0, "waited": round(time.time() - start, 2)}


def changed_since(reference: Path, timeout: float = 12, interval: float = 0.4,
                  ratio_thr: float = 0.002, pixel_thr: int = 12,
                  crop: str | None = None) -> dict:
    """Wait until the screen differs from a previously captured reference frame."""
    start = time.time()
    cur = _tmp_shot("cs-cur", crop)
    while time.time() - start < timeout:
        time.sleep(interval)
        capture(cur, crop)
        r = diff_ratio(reference, cur, pixel_thr)
        if r >= ratio_thr:
            return {"changed": True, "ratio": round(r, 5), "waited": round(time.time() - start, 2)}
    return {"changed": False, "ratio": 0.0, "waited": round(time.time() - start, 2)}


def wait_stable(timeout: float = 20, interval: float = 0.4, quiet_for: float = 1.5,
                ratio_thr: float = 0.002, pixel_thr: int = 12, crop: str | None = None) -> dict:
    """Block until nothing has changed for `quiet_for` seconds (render finished)."""
    prev = _tmp_shot("ws-prev", crop)
    start = last_change = time.time()
    while time.time() - start < timeout:
        time.sleep(interval)
        cur = _tmp_shot("ws-cur", crop)
        r = diff_ratio(prev, cur, pixel_thr)
        if r >= ratio_thr:
            last_change = time.time()
        elif time.time() - last_change >= quiet_for:
            return {"ok": True, "stable": True, "quiet_for": quiet_for,
                    "waited": round(time.time() - start, 2)}
        prev = cur
    return {"ok": True, "stable": False, "quiet_for": quiet_for,
            "waited": round(time.time() - start, 2)}


# ---------------------------------------------------------------- recording
def record(fps: float = 1.0, seconds: float = 5.0, outdir: Path | None = None) -> dict:
    fps = max(0.2, min(fps, 10.0))
    seconds = max(1.0, min(seconds, 300.0))
    outdir = outdir or (HERMES_HOME / "cache" / "screen-rec" / time.strftime("%Y%m%d-%H%M%S"))
    outdir.mkdir(parents=True, exist_ok=True)
    for old in outdir.glob("f*.png"):
        old.unlink()
    cmd = [ffmpeg_bin(), "-loglevel", "error", "-f", "x11grab", "-framerate", str(fps),
           "-video_size", screen_size(), "-i", ENV["DISPLAY"], "-t", str(seconds),
           "-y", str(outdir / "f%04d.png")]
    started = time.time()
    run(cmd, timeout=seconds + 60)
    frames = sorted(outdir.glob("f*.png"))
    (outdir / "meta.json").write_text(json.dumps(
        {"started": started, "fps": fps, "seconds": seconds, "frames": len(frames),
         "display": ENV.get("DISPLAY"), "screen": screen_size()}, indent=1))
    return {"ok": True, "action": "record", "dir": str(outdir), "frames": len(frames),
            "fps": fps, "seconds": seconds, "duration": round(time.time() - started, 2)}


def record_review(outdir: Path, ratio_thr: float = 0.002, pixel_thr: int = 12) -> dict:
    frames = sorted(outdir.glob("f*.png"))
    if not frames:
        fail("no frames found", dir=str(outdir))
    scenes, prev = [], frames[0]
    for cur in frames[1:]:
        r = diff_ratio(prev, cur, pixel_thr)
        if r >= ratio_thr:
            scenes.append({"frame": cur.name, "ratio": round(r, 4)})
        prev = cur
    return {"ok": True, "action": "record-review", "dir": str(outdir),
            "frames": len(frames), "scenes": scenes, "scene_count": len(scenes)}


# ---------------------------------------------------------------- info commands
def cmd_check() -> None:
    """Dependency and session self-check for this machine."""
    tools = {name: shutil.which(name) for name in ("ffmpeg", "xdotool", "xclip", "setxkbmap", "xrandr")}
    ff = ffmpeg_bin()
    tools["ffmpeg"] = ff if Path(ff).exists() or shutil.which(ff) else None
    screen, screen_err = probe_screen()
    ok_display = screen is not None
    missing = [k for k, v in tools.items() if not v and k in ("ffmpeg", "xdotool")]
    payload = {
        "ok": ok_display and not missing, "version": VERSION,
        "display": ENV.get("DISPLAY"), "xauthority": ENV.get("XAUTHORITY") or None,
        "screen": screen, "display_reachable": ok_display, "display_error": screen_err,
        "bot_desktop_env": (HERMES_HOME / "bot-desktop" / "env").exists(),
        "keyboard_layout": current_layout(),
        "tools": tools, "missing_required": missing,
        "optional_missing": [k for k, v in tools.items() if not v and k not in ("ffmpeg", "xdotool")],
        "hermes_home": str(HERMES_HOME), "action_log": str(ACTION_LOG),
    }
    if not ok_display:
        payload["hint"] = ("Display unreachable: the bot desktop may be stopped (it shuts itself "
                           "down when idle and removes bot-desktop/env). Start it from the desktop "
                           "app, or pass the right DISPLAY/XAUTHORITY.")
    human = (f"{'READY' if payload['ok'] else 'MISSING'} - display {payload['display']} "
             f"({screen or 'unreachable'}) layout={payload['keyboard_layout']}\n  tools: " +
             ", ".join(f"{k}={'yes' if v else 'no'}" for k, v in tools.items()))
    emit(payload, human)


def cmd_info() -> None:
    lease = {}
    try:
        lease = json.loads((HERMES_HOME / "bot-desktop" / "lease.json").read_text())
    except Exception:
        pass
    chrome = [w["title"] for w in list_windows() if "chrome" in w["title"].lower()]
    payload = {"ok": True, "version": VERSION, "display": ENV.get("DISPLAY"),
               "screen": screen_size(), "xauthority": ENV.get("XAUTHORITY"),
               "keyboard_layout": current_layout(), "lease_holder": lease.get("holder"),
               "chrome_windows": chrome, "windows": len(list_windows())}
    human = (f"display {payload['display']} ({payload['screen']})  "
             f"layout={payload['keyboard_layout']}  lease={payload['lease_holder']}  "
             f"windows={payload['windows']}")
    emit(payload, human)


# ---------------------------------------------------------------- arguments
BOOL_FLAGS = {"human", "quiet", "json", "keep-layout", "no-clear", "expect-change", "version", "help"}


def parse(argv: list[str]) -> tuple[str, list[str], dict]:
    if not argv:
        print(HELP.replace('__VERSION__', VERSION))
        sys.exit(0)
    cmd, rest = argv[0], argv[1:]
    opts: dict = {}
    pos: list[str] = []
    i = 0
    while i < len(rest):
        a = rest[i]
        if a.startswith("--"):
            key = a[2:]
            if key in BOOL_FLAGS:
                opts[key] = True
                i += 1
                continue
            if i + 1 >= len(rest):
                fail(f"--{key} needs a value")
            opts[key] = rest[i + 1]
            i += 2
            continue
        pos.append(a)
        i += 1
    return cmd, pos, opts


def main() -> None:
    global HUMAN, QUIET
    raw = sys.argv[1:]
    if not raw or raw[0] in ("help", "-h", "--help"):
        print(HELP.replace('__VERSION__', VERSION))
        return
    cmd, pos, o = parse(raw)
    if o.get("help"):
        print(HELP.replace('__VERSION__', VERSION))
        return
    if o.get("version") or cmd == "version":
        print(json.dumps({"ok": True, "version": VERSION}))
        return
    HUMAN = bool(o.get("human"))
    QUIET = bool(o.get("quiet"))

    if cmd == "check":
        cmd_check()

    elif cmd == "info":
        cmd_info()

    elif cmd == "shot":
        out = Path(o.get("out") or (SHOT_DIR / f"shot-{time.strftime('%H%M%S')}.png"))
        crop = o.get("crop")
        scale = float(o["scale"]) if o.get("scale") else None
        p = capture(out, crop, scale)
        extra = add_grid(p, int(o["grid"]), crop) if o.get("grid") else {}
        w, h = size_tuple()
        payload = {"ok": True, "action": "shot", "path": str(p), "bytes": p.stat().st_size,
                   "screen": f"{w}x{h}", **extra}
        emit(payload, f"image: {p} ({p.stat().st_size} bytes)" +
             (f"  grid={o['grid']}px" if o.get("grid") else ""))

    elif cmd == "move":
        if len(pos) < 2:
            fail("move X Y")
        glide(int(pos[0]), int(pos[1]), int(o.get("steps", 24)), float(o.get("dur", 0.55)))
        emit({"ok": True, "action": "move", "x": int(pos[0]), "y": int(pos[1])},
             f"pointer {pos[0]},{pos[1]}")

    elif cmd == "click":
        if len(pos) < 2:
            fail("click X Y")
        mods = [m.strip() for m in (o.get("mods") or "").split(",") if m.strip()]
        expect = bool(o.get("expect-change"))
        before = _tmp_shot("click-before", o.get("crop")) if expect else None
        res = click(int(pos[0]), int(pos[1]), int(o.get("button", 1)), int(o.get("count", 1)),
                    mods, float(o.get("settle", 0.25)), int(o.get("steps", 24)),
                    float(o.get("dur", 0.55)))
        if expect:
            wc = changed_since(before, float(o.get("timeout", 12)), float(o.get("interval", 0.4)),
                               float(o.get("ratio", 0.002)), int(o.get("pixel-threshold", 12)),
                               o.get("crop")) if before else {"changed": None}
            res.update({"expect_change": True, "changed": wc.get("changed"),
                        "ratio": wc.get("ratio"), "waited": wc.get("waited")})
        emit(res, f"clicked {pos[0]},{pos[1]}" + (f" mods={mods}" if mods else "") +
             (f" changed={res.get('changed')} (ratio {res.get('ratio')})" if expect else ""))

    elif cmd == "fill":
        if len(pos) < 3:
            fail('fill X Y "text"')
        x, y, text = int(pos[0]), int(pos[1]), pos[2]
        res = click(x, y, 1, 1, [], float(o.get("settle", 0.25)), 24, 0.55)
        if not o.get("no-clear"):
            press_key("ctrl+a")
            press_key("BackSpace")
            time.sleep(0.2)
        typed = type_text(text, int(o.get("delay", 45)), o.get("layout"),
                          bool(o.get("keep-layout")), o.get("method", "auto"))
        res.update({"action": "fill", "chars": len(text), "method": typed.get("method"),
                    "cleared": not bool(o.get("no-clear"))})
        emit(res, f"filled {x},{y} with {len(text)} chars ({typed.get('method')})")

    elif cmd == "drag":
        if len(pos) < 4:
            fail("drag X1 Y1 X2 Y2")
        emit(drag(*[int(v) for v in pos[:4]], steps=int(o.get("steps", 24))),
             f"dragged {pos[0]},{pos[1]} -> {pos[2]},{pos[3]}")

    elif cmd == "scroll":
        if not pos:
            fail("scroll up|down")
        at = None
        if o.get("at"):
            ax, ay = [int(v) for v in o["at"].split(",")]
            at = (ax, ay)
        emit(scroll(pos[0], int(o.get("amount", 3)), at),
             f"scrolled {pos[0]} x{o.get('amount', 3)}")

    elif cmd == "type":
        if not pos:
            fail('type "text"')
        emit(type_text(pos[0], int(o.get("delay", 45)), o.get("layout"),
                       bool(o.get("keep-layout")), o.get("method", "auto")),
             f"typed {len(pos[0])} chars")

    elif cmd == "key":
        if not pos:
            fail('key "ctrl+l"')
        emit(press_key(pos[0], int(o.get("repeat", 1))), f"key {pos[0]}")

    elif cmd == "win":
        sub = pos[0] if pos else "list"
        if sub == "list":
            ws = list_windows()
            emit({"ok": True, "windows": ws},
                 "\n".join(f'{w["id"]}  {w["w"]}x{w["h"]}+{w["x"]}+{w["y"]}  {w["title"]}' for w in ws))
        elif sub == "focus":
            wid = find_window(pos[1])
            xdo("windowactivate", wid)
            emit({"ok": True, "focused": pos[1], "id": wid}, f"focused: {pos[1]}")
        elif sub == "move":
            wid = find_window(pos[1])
            xdo("windowmove", wid, pos[2], pos[3])
            emit({"ok": True, "moved": pos[1], "id": wid}, f"moved: {pos[1]}")
        elif sub == "resize":
            wid = find_window(pos[1])
            xdo("windowsize", wid, pos[2], pos[3])
            emit({"ok": True, "resized": pos[1], "id": wid}, f"resized: {pos[1]}")
        else:
            fail("win list|focus|move|resize")

    elif cmd == "wait-change":
        res = wait_change(float(o.get("timeout", 15)), float(o.get("interval", 0.4)),
                          float(o.get("ratio", 0.002)), int(o.get("pixel-threshold", 12)),
                          o.get("crop"))
        emit(res, (f"changed (ratio {res['ratio']}, {res['waited']}s)" if res["changed"]
                   else f"no change within {res['waited']}s"))

    elif cmd == "wait-stable":
        res = wait_stable(float(o.get("timeout", 20)), float(o.get("interval", 0.4)),
                          float(o.get("quiet-for", 1.5)), float(o.get("ratio", 0.002)),
                          int(o.get("pixel-threshold", 12)), o.get("crop"))
        emit(res, (f"stable (quiet {res['quiet_for']}s, {res['waited']}s)" if res["stable"]
                   else f"still changing after {res['waited']}s"))

    elif cmd == "record":
        res = record(float(o.get("fps", 1.0)), float(o.get("seconds", 5.0)),
                     Path(o["dir"]) if o.get("dir") else None)
        emit(res, f"recorded {res['frames']} frames -> {res['dir']}")

    elif cmd == "record-review":
        if not o.get("dir"):
            fail("record-review --dir D")
        res = record_review(Path(o["dir"]), float(o.get("ratio", 0.002)),
                            int(o.get("pixel-threshold", 12)))
        human = (f"{res['frames']} frames, {res['scene_count']} changes:\n" +
                 "\n".join(f"  {s['frame']}  ratio={s['ratio']}" for s in res["scenes"]))
        emit(res, human)

    elif cmd == "diff":
        if len(pos) < 2:
            fail("diff A.png B.png")
        r = diff_ratio(Path(pos[0]), Path(pos[1]), int(o.get("pixel-threshold", 12)))
        emit({"ok": True, "ratio": round(r, 5), "changed": r > 0.001},
             f"difference: {r * 100:.2f}%")

    elif cmd == "log":
        n = int(o.get("tail", 10))
        lines = ACTION_LOG.read_text().splitlines()[-n:] if ACTION_LOG.exists() else []
        print("\n".join(lines))

    else:
        fail(f"unknown command: {cmd}", hint="run: screen.py help")


if __name__ == "__main__":
    main()
