---
name: bot-screen-control
description: "Drive the bot screen GUI: real mouse/keyboard on X11."
version: 1.2.0
author: Hermes Agent + Salih
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [computer-use, desktop, x11, xdotool, screenshots, bot-screen, gui-automation]
---

# Bot Screen Control (X11, visual + coordinates)

Drive a headless Xfce desktop (Xvnc behind VNC) with **real pointer and keyboard events**.
No AT-SPI, no OCR, no MCP: look at a screenshot, click a coordinate, verify with another screenshot.

`scripts/screen.py` is a single file; every command prints one line of JSON (`--human` for text).

## When to use this

- `computer_use` cannot capture this screen (empty capture, or it returns an X11 image error). Retry
  the driver once it is fixed; use this skill when it is not.
- `browser_exec` answers "A human has taken over this desktop" (the user holds the screen) but a
  click is still needed: the lease only locks `browser_exec`/capture, `xdotool` keeps working.
- Page content is not reachable through the DOM (SPA, login wall) or a desktop app must be driven.

When the DOM is available, `browser_exec` is faster and sturdier. Prefer it.

Deeper material:

- `references/x11-desktop-tooling.md` — session env hygiene, the optional AT-SPI path, window work
  without wmctrl, recording + frame diffing, **proving which Chrome profile/session is open**, and
  trying a third-party stack without sudo.
- `references/reading-dense-web-pages.md` — reading truncated (ellipsis) text, downloading in-page
  documents, SPA route quirks, merging N frames into one vision call; `scripts/stack_crops.py`
  implements the composite method from that file.

## Working style (this user)

- **Use the screen like a person would.** Open the app from the top-left menu, click the bookmark,
  click the tab. Do not fall back to profile copies, separate `--user-data-dir` or DOM/API shortcuts
  unless the user asks; they produce a "guest/empty session" and waste the turn. When the user says
  "open it normally" or "open it from the menu", follow exactly that path.
- **Move the pointer before clicking.** No teleporting: 20-25 intermediate points, ~0.5 s,
  smoothstep, then ~250 ms hover, then click. `click` already does this; never hand-write
  `mousemove X Y` followed by an instant `click`.
- **"Only mouse + keyboard + screenshots"** means no other tool: no DOM/CDP, no AT-SPI, no MCP.
  If the user says "watch what I do on the screen", use `record` (one frame per second) and review
  the frames afterwards with `record-review`.
- **No MCP wrapper.** Keep the tool a CLI/script; sharing it with other agents can be a thin wrapper
  around the same script.
- **A third-party stack trial is temporary.** When the user says "let's try it and decide from the
  result", install it under scratch, test it on a real task, and when the decision is made remove it
  **completely**: install dir, binaries you unpacked instead of system packages, and any profile
  copies. Do not leave the experiment lying around like a real installation. Recipe:
  `references/x11-desktop-tooling.md` §7–8.
- **Profile copies carry the user's cookies.** If you copied a browser profile to try something,
  delete it when the work is done (it is often hundreds of MB); ask before deleting.
- **Stop when the flow confirms itself.** If the last step ends in a green "done/thank you" screen,
  a "This is correct" banner or a redirect to a dashboard, do not keep clicking through tabs to
  re-verify — the user is watching and that wandering looks like confusion. Take one final `shot`,
  summarize, and state any doubt in words instead.

## Quick start

```bash
S=~/.hermes/skills/bot-screen-control/scripts/screen.py

python3 $S check                    # READY/MISSING: tools + display + keyboard layout
python3 $S help                     # full command reference (also --help)
python3 $S info                     # display, layout, lease holder, window count
python3 $S shot --out /tmp/s.png    # screenshot (ffmpeg x11grab)
python3 $S shot --grid 50 --out /tmp/g.png    # + labeled coordinate grid & cursor crosshair
python3 $S click 390 415            # glide + 250 ms hover + click
python3 $S click 88 128 --mods ctrl # ctrl+click = open in a background tab
python3 $S click 390 415 --expect-change --timeout 10   # click, then report changed/ratio
python3 $S fill 390 415 "Merhaba dünya"   # click, select-all, clear, type (one call)
python3 $S type "Merhaba dünya"     # non-ASCII text is pasted through the clipboard
python3 $S key "ctrl+l"             # shortcut
python3 $S wait-change --timeout 20 # block until the screen changes
python3 $S wait-stable --quiet-for 2   # block until the screen stops changing
python3 $S record --seconds 10 --fps 1    # capture frames while a human works
python3 $S record-review --dir <dir>      # list the frames where the screen changed
python3 $S scroll down --amount 5 --at 800,600   # wheel; not Page_Down
python3 $S drag 300 400 900 400 --steps 30       # drag (smoothstep)
python3 $S diff /tmp/a.png /tmp/b.png            # changed-pixel ratio
python3 $S win list                 # window list (no wmctrl needed)
python3 $S log --tail 10            # action log
```

Global flags: `--human`, `--quiet`, `--crop x,y,w,h`, `--pixel-threshold N`, `--version`.
`help` lists every command; there is no per-command `--help`.

## Portability (other machines)

The script is machine-independent; resolution order:

1. **DISPLAY / XAUTHORITY**: environment → `$HERMES_HOME/bot-desktop/env` → `~/.hermes/bot-desktop/env` → `:0` + `~/.Xauthority`.
2. **ffmpeg**: `SCREEN_FFMPEG` → `PATH` → `$HERMES_HOME/tools/ffmpeg*/bin/ffmpeg` → `~/.hermes/tools/…`.
3. **Output paths**: `$HERMES_HOME/cache/screen-actions.jsonl`, `…/screen-shots/`, `…/screen-rec/` (per profile).
4. **Optional tools**: without `xclip` the clipboard path is disabled and `type` falls back to real key
   events; without `setxkbmap` layouts cannot be switched (ASCII still types). Required: `ffmpeg` + `xdotool`.
5. **Wayland**: XWayland windows work; native Wayland windows do not — use `wayland-desktop-control`.

On a new machine run `check` first. Screen-specific measurements live in `references/this-screen.md`
and must be re-measured when resolution, theme or window geometry changes.

## Environment facts (this machine)

- Display `:20`, 1440x900, X11 (Xvnc + Xfce). `XAUTHORITY=~/.hermes/bot-desktop/Xauthority`.
  The script reads both from `~/.hermes/bot-desktop/env`; no manual `export` needed.
- Screen coordinates equal image coordinates. No scaling (`scale=1.0`); do not compute a multiplier.
- `lease.json` → `holder: human` makes `browser_exec` refuse; `xdotool` is unaffected.
- Required: `ffmpeg` (under Hermes tools), `xdotool`. Useful: `xclip` (clipboard typing), PIL (diffs).
  `wmctrl`, `tesseract`, `numpy` and ImageMagick `import` are optional and **not needed**: window
  work is `xdotool`, diffing is `ImageChops`, capture is `ffmpeg`. Prove those three are insufficient
  before installing anything.
- The bot screen has **two separate Chrome profiles**:
  - `~/.hermes/bot-desktop/xdg/google-chrome` — Chrome opened from the menu or a terminal. The user's
    sessions (Trakt, Google) live here. **Treat this as the default.**
  - `~/.hermes/bot-desktop/browser-profile` — the agent's `browser_exec` profile; the dock's Browser
    icon opens this one. It is usually logged out.

## Recipes

**Open an app from the menu** (the natural path). Coordinates measured here; see `references/this-screen.md`:
```bash
python3 $S click 15 15     # top-left menu
python3 $S click 100 124   # "Internet Browser" (top of the menu) -> Chrome
python3 $S wait-stable --quiet-for 2
```
Menu order changes with the theme; verify with `shot` instead of trusting memorized coordinates.

**Open a link in a new tab:** if the bookmarks bar is hidden, `key "ctrl+shift+b"`, then
`click <x> 128 --mods ctrl`. The tab opens in the background and the strip shifts right — `shot`
before switching tabs.

**Typing text, including Turkish:** `type` pastes through the clipboard whenever the text contains
non-ASCII characters (`--method auto`), which is layout-proof. `--method keys` sends real key events:
it switches to the `tr` layout, types, then restores the previous layout. Both paths are verified.

**Form / survey / quiz pages:** these rarely fit one screen; every question may have its own
`Submit Answer` button and the `Continue` at the bottom stays disabled until all are submitted.
Order: click the radio/option → ~1 s → `Submit Answer` → `shot` and read the feedback (green
"This is correct" / red warning) → next question. `Attempts remaining: N` tells you the state:
0 = already submitted, >0 = still open. If `Continue` looks disabled there is an unsubmitted
question: `scroll down` through the whole page, finish the missing ones, then `Continue`.
Selecting and submitting are two separate steps; do not claim "answered" before seeing the banner.

**"It asks me to log in" / "it shows a guest session":** prove which profile is open instead of
guessing (`references/x11-desktop-tooling.md` §7). No `--user-data-dir` in `/proc/<pid>/cmdline`
means the window is the XDG profile; a cookie DB without the target domain means that jar never had
a login. Open the right window from the menu and log in there once — that is the persistent profile.

## Pitfalls (all of these happened on this machine)

1. **`pkill -f <pattern>` kills your own shell.** The pattern also matches the `bash -c` line that
   runs the command. Find the PID with `pgrep -af`, then `kill <pid>`.
2. **With the `us` layout, uppercase Turkish letters break:** `İstanbul` → `Istanbul`,
   `Çiçekler` → `çiçekler`. Lowercase (ü ş ğ ı ö ç) is fine. Fix: clipboard typing (default) or the
   `tr` layout.
3. **The first character can be lost right after a layout switch.** Wait ≥0.6 s after
   `setxkbmap tr` (the script does); if it still fails, fall back to the clipboard method.
4. **Sleeping instead of `wait-change`** is slow and fragile: waiting 8 s and screenshotting an empty
   page is worse than waiting for the change threshold. Use `wait-change` after an action and
   `wait-stable` after a navigation.
5. **The "Profile error" / "Chrome did not shut down correctly" bubbles** are not lost accounts:
   Chrome receives SIGTERM/SIGKILL when the screen stops. Persistent cookies survive.
6. **Zooming does not recover truncated card text.** The part cut by CSS `text-overflow: ellipsis`
   simply is not in the pixels: `shot --crop`, `ctrl+-` and hover tooltips all fail. Open the target
   (`--mods ctrl`) and read the detail heading instead (see `references/reading-dense-web-pages.md`).
   Prefer the DOM when it is available.
7. **Do not share a profile with `browser_exec`:** that tool opens its own profile
   (`browser-profile`); the window the user logged into is the `xdg` profile. Mixing them shows a
   "guest" view.
8. **`xdotool mousemove --sync` can hang:** if the pointer never arrives it waits forever and locks
   the agent turn. Use plain `mousemove` and wrap every `xdotool` call in a timeout (the script uses
   8 s). If a turn looks stuck, look for a hung `xdotool` call first.
9. **A "guest" view on the first try means the launch path was wrong, not the profile.** Retry the
   same tab in a Chrome opened from the menu; copying/moving profiles does not fix it.
10. **`key Page_Down` / `Page_Up` is not scrolling.** On pages with a sticky date/scroll indicator
    those keys go to the indicator: the date jumps, a panel stays open and `Escape`/`Home` will not
    close it. Always scroll with `scroll down --amount N --at X,Y`.
11. **Repeated `--mods ctrl` clicks on the same coordinate do not always open new tabs** (the page
    may have shifted or the click hit the same link). After a click series, `shot` the tab strip and
    count; open the missing ones one by one.
12. **`--mods ctrl` opens the new tab in the BACKGROUND and shifts the tab strip right.** The new tab
    sits right of the active one, at the end; the previous turn's tab x-coordinate now points at a
    different tab. `shot` and confirm before switching, otherwise you open the wrong tab (usually the
    document you just left) and waste the turn.
13. **The bot screen shuts itself down when idle** (`idle_stop_minutes`, default 30). Once it does,
    `bot-desktop/env` is removed, `xrandr` says "Can't open display" and the script falls back to
    `:0`. `check` reports this as `display_reachable:false` + `bot_desktop_env:false` + a hint.
    To start it again use the display pane in the desktop app, or:
    `cd ~/.hermes/hermes-agent && python3 -c "from tools.bot_desktop import runtime; print(runtime.start(wait_seconds=25))"`.
14. **Address bar coordinates move with the window geometry.** A maximized 1440x900 window puts the
    omnibox at y≈79; the same window at 1440x880+0+28 puts it at y≈91 and the tab strip at y≈50.
    Measure with `shot --grid` before `fill`, or use `key "ctrl+l"`, which needs no coordinate.

## Sharing / distribution

The skill is just a folder; distribution needs no special format:

```bash
# 1) copy to another machine (drop it into ~/.hermes/skills/ there)
scp -r ~/.hermes/skills/bot-screen-control other:/tmp/

# 2) GitHub repo + tap (repo layout: skills/<name>/SKILL.md)
hermes skills tap add <owner>/<repo>
hermes skills install <owner>/<repo>/bot-screen-control

# 3) install a single skill without a tap (any public repo works)
hermes skills install <owner>/<repo>/bot-screen-control

# 4) publish to a registry
hermes skills publish ~/.hermes/skills/bot-screen-control --to github --repo <owner>/<repo>
hermes skills publish ~/.hermes/skills/bot-screen-control --to clawhub
```

On the target machine run `check` first: missing `ffmpeg`/`xdotool` or an unreachable display shows
up there. Coordinates in `references/this-screen.md` do not travel — re-measure them.

## Verification principle

After every state-changing action take a `shot` and read it; "clicked" is not "happened".
`ok: true` in the JSON only means the event was sent, not that it had an effect.
