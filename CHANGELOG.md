# Changelog

## 1.2.0 — 2026-11-14

New commands:

- `help` / `--help` / `-h`: full command reference (previously `--help` errored out).
- `version` / `--version`.
- `shot --grid N`: labeled coordinate grid overlay in absolute screen coordinates plus a cursor
  crosshair, so pointing at a target no longer needs eyeballed numbers.
- `click ... --expect-change [--timeout S] [--ratio R]`: performs the click and reports whether the
  screen actually changed (`changed`, `ratio`, `waited`) — one round-trip instead of click + wait.
- `fill X Y "text" [--no-clear]`: click, select-all, clear, type in a single call.
- `wait-stable [--quiet-for S]`: the inverse of `wait-change` — blocks until the screen stops
  changing (render finished), replacing fixed sleeps.
- `record [--fps N] [--seconds S] [--dir D]` and `record-review --dir D`: capture one frame per tick
  and list the frames where the screen changed.

Other changes:

- The whole repository is English (README, SKILL.md, references, script docstrings and output).
- `check` also reports the version and the bot-desktop env state.
- `references/this-screen.md` documents both address-bar geometries (maximized and windowed).

## 1.1.0

- Portability: DISPLAY/XAUTHORITY and ffmpeg resolution order, `$HERMES_HOME`-relative output paths,
  optional `xclip`/`setxkbmap`, `check` self-diagnosis for new machines.
- `type --method auto|keys|paste` with clipboard-first typing for non-ASCII text.
- Skill moved to a public repo and installable as a Hermes tap.

## 1.0.0

- Initial release: `check`, `info`, `shot`, `move`, `click`, `drag`, `scroll`, `type`, `key`, `win`,
  `wait-change`, `diff`, `log`.
