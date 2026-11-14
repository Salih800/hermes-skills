# hermes-skills

A personal skill collection for [Hermes Agent](https://github.com/NousResearch/hermes-agent).
Every skill lives at `skills/<name>/SKILL.md`, so this repo works both as a **tap** (a skill source)
and for installing single skills.

## Contents

| Skill | What it does |
|---|---|
| [`bot-screen-control`](skills/bot-screen-control/SKILL.md) | Drives an X11 desktop with real pointer and keyboard events: screenshots, eased pointer glides, clicks, drags, scrolling, Unicode text entry, window handling, change detection and recording. No AT-SPI, OCR or MCP required. |

Skills in this repo are written in English (code, docs, output). Release notes: [CHANGELOG.md](CHANGELOG.md).

## Install

**As a tap (every skill in the repo becomes visible):**

```bash
hermes skills tap add Salih800/hermes-skills
hermes skills install Salih800/hermes-skills/bot-screen-control
```

**A single skill, without adding a tap:**

```bash
hermes skills install Salih800/hermes-skills/bot-screen-control
```

**By hand:** copy `skills/bot-screen-control/` into `~/.hermes/skills/`.

After installing, the first command should be the self-check:

```bash
python3 ~/.hermes/skills/bot-screen-control/scripts/screen.py check
```

## Requirements

- Linux with an **X11** session (XWayland windows work; native Wayland windows do not)
- `ffmpeg` and `xdotool` (required), `xclip` (recommended, clipboard-based typing),
  `setxkbmap` (needed to switch keyboard layouts)
- Python 3.10+ and PIL (frame diffing)

## Using this repo for your own skills

Add a folder under `skills/`, write its `SKILL.md`, commit and push. Machines that added the tap pick
up changes with `hermes skills check` / `hermes skills update`.

## Background

`bot-screen-control` grew out of driving a headless Xfce "bot desktop" (Xvnc) where the built-in
desktop driver could not capture the screen and the browser tool refused while a human held the
pointer. The design choice is deliberate: **screenshots plus coordinates only**, with a strict
verify-after-every-action loop, because that survives SPA login walls, canvas apps, native windows
and a broken accessibility stack alike.

## License

MIT — see [LICENSE](LICENSE).
