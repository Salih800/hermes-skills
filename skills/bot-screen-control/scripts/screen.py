#!/usr/bin/env python3
"""bot-screen — gerçek fare/klavye olaylarıyla X11 masaüstü sürme.

Tasarım ilkesi: saf görsel + koordinat. AT-SPI, OCR, MCP yok.
Her komut tek satır JSON basar (--human ile okunur metin).

Komutlar:
  info                          oturum bilgisi (ekran, düzen, lease, chrome)
  shot   [--out P] [--crop x,y,w,h] [--scale S]
  move   X Y [--steps N] [--dur S]
  click  X Y [--button 1|2|3] [--count N] [--mods ctrl,shift] [--settle S]
  drag   X1 Y1 X2 Y2 [--steps N]
  scroll up|down [--amount N] [--at X Y]
  type   "METİN" [--delay MS] [--layout tr] [--keep-layout]
  key    "ctrl+l" [--repeat N]
  win    list | focus <ad> | move <ad> X Y | resize <ad> W H
  wait-change [--timeout S] [--interval S] [--ratio R] [--pixel-threshold T] [--crop ...]
  diff   A.png B.png [--pixel-threshold T]
  log    [--tail N]

Notlar:
  * DISPLAY/XAUTHORITY ~/.hermes/bot-desktop/env dosyasından okunur (yoksa ortam).
  * Ekran koordinatı == görüntü koordinatı (ölçekleme yok, 1440x900).
  * Her eylem ~/.hermes/cache/screen-actions.jsonl dosyasına yazılır.
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

HOME = Path.home()
HERMES_HOME = Path(os.environ.get("HERMES_HOME") or (HOME / ".hermes"))
FFMPEG = HOME / ".hermes" / "tools" / "ffmpeg-9.0.1-linux-x64" / "bin" / "ffmpeg"
SHOT_DIR = HERMES_HOME / "cache" / "screen-shots"
ACTION_LOG = HERMES_HOME / "cache" / "screen-actions.jsonl"


def _env_file_candidates() -> list[Path]:
    """Bot ekranı env dosyası: bu profilde, sonra varsayılan profilde."""
    out = [HERMES_HOME / "bot-desktop" / "env", HOME / ".hermes" / "bot-desktop" / "env"]
    return [p for p in dict.fromkeys(out)]


# ---------------------------------------------------------------- ortam
def _bootstrap_env() -> dict:
    """DISPLAY/XAUTHORITY: ortamda varsa ona güven, yoksa bot-desktop/env, yoksa makul varsayılan."""
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
    """SCREEN_FFMPEG → PATH → Hermes tools altındaki bilinen konumlar."""
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


# ---------------------------------------------------------------- çıktı
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


# ---------------------------------------------------------------- görüntü
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
        fail("ekran görüntüsü alınamadı", stderr=res.stderr[-300:])
    return out


_SIZE_CACHE: list[str] = []


def probe_screen() -> tuple[str | None, str | None]:
    """(boyut, hata) — ölümcül değil; `check` bunu kullanır."""
    out = run(["xrandr"]).stdout
    m = re.search(r"current (\d+) x (\d+)", out)
    if m:
        return f"{m.group(1)}x{m.group(2)}", None
    err = (run(["xrandr"]).stderr or "").strip().splitlines()
    return None, (err[0] if err else "xrandr çıktısı okunamadı")


def screen_size() -> str:
    if _SIZE_CACHE:
        return _SIZE_CACHE[0]
    size, err = probe_screen()
    if not size:
        fail("ekran boyutu okunamadı (ekran kapalı olabilir)", display=ENV.get("DISPLAY"),
             hint=err, bot_desktop_env=(HERMES_HOME / "bot-desktop" / "env").exists())
    _SIZE_CACHE.append(size)
    return size


def size_tuple() -> tuple[int, int]:
    w, h = screen_size().split("x")
    return int(w), int(h)


def load_rgb(path: Path):
    from PIL import Image
    return Image.open(path).convert("RGB")


def diff_ratio(a: Path, b: Path, pixel_threshold: int = 12) -> float:
    """Değişen piksel oranı (0..1). PIL yeterli, numpy yok."""
    from PIL import ImageChops
    ia, ib = load_rgb(a), load_rgb(b)
    if ia.size != ib.size:
        ib = ib.resize(ia.size)
    d = ImageChops.difference(ia, ib).convert("L")
    hist = d.histogram()
    changed = sum(hist[pixel_threshold:])
    total = ia.size[0] * ia.size[1]
    return changed / total if total else 0.0


# ---------------------------------------------------------------- fare
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
        fail("tıklama ekran dışında", x=x, y=y, screen=f"{w}x{h}")
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


# ---------------------------------------------------------------- klavye
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
    """Panoyla yapıştır: ASCII dışı karakterlerde düzen sorunlarını tamamen atlar."""
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
    """method: auto (ASCII dışı varsa pano) | keys (gerçek tuş basımı) | paste."""
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
            fail("klavye düzeni değiştirilemedi", wanted=target, current=original)
        switched = True
        time.sleep(0.6)          # XKB değişikliğinin uygulamaya ulaşması için
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


# ---------------------------------------------------------------- pencereler
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
    fail("pencere bulunamadı", match=match, windows=[w["title"] for w in list_windows()])


# ---------------------------------------------------------------- info
def cmd_check() -> None:
    """Bu makinede araç çalışır mı: bağımlılık + oturum öz-denetimi."""
    tools = {name: shutil.which(name) for name in ("ffmpeg", "xdotool", "xclip", "setxkbmap", "xrandr")}
    ff = ffmpeg_bin()
    tools["ffmpeg"] = ff if Path(ff).exists() or shutil.which(ff) else None
    screen, screen_err = probe_screen()
    ok_display = screen is not None
    missing = [k for k, v in tools.items() if not v and k in ("ffmpeg", "xdotool")]
    payload = {
        "ok": ok_display and not missing,
        "display": ENV.get("DISPLAY"), "xauthority": ENV.get("XAUTHORITY") or None,
        "screen": screen, "display_reachable": ok_display, "display_error": screen_err,
        "bot_desktop_env": (HERMES_HOME / "bot-desktop" / "env").exists(),
        "keyboard_layout": current_layout(),
        "tools": tools, "missing_required": missing,
        "optional_missing": [k for k, v in tools.items() if not v and k not in ("ffmpeg", "xdotool")],
        "hermes_home": str(HERMES_HOME), "action_log": str(ACTION_LOG),
    }
    if not ok_display:
        payload["hint"] = ("Ekran erişilemiyor: bot ekranı kapalı olabilir (boşta durunca kendini "
                           "kapatır ve bot-desktop/env silinir). Masaüstü uygulamasından ekranı "
                           "aç ya da doğru DISPLAY/XAUTHORITY ver.")
    human = (f"{'HAZIR' if payload['ok'] else 'EKSİK'} — ekran {payload['display']} ({screen or 'erişilemiyor'}) "
             f"düzen={payload['keyboard_layout']}\n  araçlar: " +
             ", ".join(f"{k}={'✓' if v else '✗'}" for k, v in tools.items()))
    emit(payload, human)


def cmd_info() -> None:
    lease = {}
    try:
        lease = json.loads((HERMES_HOME / "bot-desktop" / "lease.json").read_text())
    except Exception:
        pass
    chrome = [w["title"] for w in list_windows() if "chrome" in w["title"].lower()]
    payload = {"ok": True, "display": ENV.get("DISPLAY"), "screen": screen_size(),
               "xauthority": ENV.get("XAUTHORITY"), "keyboard_layout": current_layout(),
               "lease_holder": lease.get("holder"), "chrome_windows": chrome,
               "windows": len(list_windows())}
    human = (f"ekran {payload['display']} ({payload['screen']})  düzen={payload['keyboard_layout']}  "
             f"lease={payload['lease_holder']}  pencere={payload['windows']}")
    emit(payload, human)


# ---------------------------------------------------------------- argümanlar
def parse(argv: list[str]) -> tuple[str, list[str], dict]:
    if not argv:
        fail("komut gerekli: info|shot|move|click|drag|scroll|type|key|win|wait-change|diff|log")
    cmd, rest = argv[0], argv[1:]
    opts: dict = {}
    pos: list[str] = []
    i = 0
    while i < len(rest):
        a = rest[i]
        if a.startswith("--"):
            key = a[2:]
            if key in ("human", "quiet", "keep-layout", "json"):
                opts[key] = True
                i += 1
                continue
            if i + 1 >= len(rest):
                fail(f"--{key} için değer gerekli")
            opts[key] = rest[i + 1]
            i += 2
            continue
        pos.append(a)
        i += 1
    return cmd, pos, opts


def main() -> None:
    global HUMAN, QUIET
    cmd, pos, o = parse(sys.argv[1:])
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
        w, h = size_tuple()
        emit({"ok": True, "action": "shot", "path": str(p), "bytes": p.stat().st_size,
              "screen": f"{w}x{h}"}, f"görüntü: {p} ({p.stat().st_size} bayt)")

    elif cmd == "move":
        if len(pos) < 2:
            fail("move X Y")
        glide(int(pos[0]), int(pos[1]), int(o.get("steps", 24)), float(o.get("dur", 0.55)))
        emit({"ok": True, "action": "move", "x": int(pos[0]), "y": int(pos[1])},
             f"imleç {pos[0]},{pos[1]}")

    elif cmd == "click":
        if len(pos) < 2:
            fail("click X Y")
        mods = [m.strip() for m in (o.get("mods") or "").split(",") if m.strip()]
        emit(click(int(pos[0]), int(pos[1]), int(o.get("button", 1)), int(o.get("count", 1)),
                   mods, float(o.get("settle", 0.25)), int(o.get("steps", 24)),
                   float(o.get("dur", 0.55))),
             f"tıklandı {pos[0]},{pos[1]}" + (f" mods={mods}" if mods else ""))

    elif cmd == "drag":
        if len(pos) < 4:
            fail("drag X1 Y1 X2 Y2")
        emit(drag(*[int(v) for v in pos[:4]], steps=int(o.get("steps", 24))),
             f"sürüklendi {pos[0]},{pos[1]} -> {pos[2]},{pos[3]}")

    elif cmd == "scroll":
        if not pos:
            fail("scroll up|down")
        at = None
        if o.get("at"):
            ax, ay = [int(v) for v in o["at"].split(",")]
            at = (ax, ay)
        emit(scroll(pos[0], int(o.get("amount", 3)), at),
             f"kaydırma {pos[0]} x{o.get('amount', 3)}")

    elif cmd == "type":
        if not pos:
            fail("type \"metin\"")
        emit(type_text(pos[0], int(o.get("delay", 45)), o.get("layout"),
                       bool(o.get("keep-layout")), o.get("method", "auto")),
             f"yazıldı ({len(pos[0])} karakter)")

    elif cmd == "key":
        if not pos:
            fail("key \"ctrl+l\"")
        emit(press_key(pos[0], int(o.get("repeat", 1))), f"tuş {pos[0]}")

    elif cmd == "win":
        sub = pos[0] if pos else "list"
        if sub == "list":
            ws = list_windows()
            emit({"ok": True, "windows": ws},
                 "\n".join(f'{w["id"]}  {w["w"]}x{w["h"]}+{w["x"]}+{w["y"]}  {w["title"]}' for w in ws))
        elif sub == "focus":
            wid = find_window(pos[1])
            xdo("windowactivate", wid)
            emit({"ok": True, "focused": pos[1], "id": wid}, f"odak: {pos[1]}")
        elif sub == "move":
            wid = find_window(pos[1])
            xdo("windowmove", wid, pos[2], pos[3])
            emit({"ok": True, "moved": pos[1], "id": wid}, f"taşındı: {pos[1]}")
        elif sub == "resize":
            wid = find_window(pos[1])
            xdo("windowsize", wid, pos[2], pos[3])
            emit({"ok": True, "resized": pos[1], "id": wid}, f"boyutlandırıldı: {pos[1]}")
        else:
            fail("win list|focus|move|resize")

    elif cmd == "wait-change":
        timeout = float(o.get("timeout", 15))
        interval = float(o.get("interval", 0.4))
        ratio_thr = float(o.get("ratio", 0.002))
        pixel_thr = int(o.get("pixel-threshold", 12))
        base = Path("/tmp") / f"wc-base-{os.getpid()}.png"
        nxt = Path("/tmp") / f"wc-next-{os.getpid()}.png"
        capture(base, o.get("crop"))
        start = time.time()
        while time.time() - start < timeout:
            time.sleep(interval)
            capture(nxt, o.get("crop"))
            r = diff_ratio(base, nxt, pixel_thr)
            if r >= ratio_thr:
                emit({"ok": True, "changed": True, "ratio": round(r, 5),
                      "waited": round(time.time() - start, 2)},
                     f"değişti (oran {r:.4f}, {time.time() - start:.1f}s)")
                return
            base, nxt = nxt, base
        emit({"ok": True, "changed": False, "ratio": 0.0, "waited": round(time.time() - start, 2)},
             f"değişim yok ({timeout}s)")

    elif cmd == "diff":
        if len(pos) < 2:
            fail("diff A.png B.png")
        r = diff_ratio(Path(pos[0]), Path(pos[1]), int(o.get("pixel-threshold", 12)))
        emit({"ok": True, "ratio": round(r, 5), "changed": r > 0.001},
             f"fark: {r * 100:.2f}%")

    elif cmd == "log":
        n = int(o.get("tail", 10))
        lines = ACTION_LOG.read_text().splitlines()[-n:] if ACTION_LOG.exists() else []
        print("\n".join(lines))

    else:
        fail(f"bilinmeyen komut: {cmd}")


if __name__ == "__main__":
    main()
