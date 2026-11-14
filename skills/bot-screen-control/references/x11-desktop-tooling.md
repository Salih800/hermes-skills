# X11 desktop tooling — depth notes

Supporting detail for `bot-screen-control`. The default path is always visual + coordinates;
everything here applies when coordinates get fragile or a GUI tool must be aimed at this screen.

## 1. Session env hygiene (launching a GUI tool from Hermes)

The gateway runs inside the user's GNOME/Wayland session, so child processes inherit
`XDG_SESSION_TYPE=wayland` and `WAYLAND_DISPLAY=wayland-0`. The bot screen is X11 (`:20`, Xvnc).
Because of that mixture a tool concludes "Wayland session + DISPLAY=:20", disables its X11 backends
and reports "no keyboard input".

Before launching the tool:

```bash
set -a; . ~/.hermes/bot-desktop/env; set +a
unset WAYLAND_DISPLAY
export XDG_SESSION_TYPE=x11 XDG_CURRENT_DESKTOP=XFCE GDK_BACKEND=x11 QT_QPA_PLATFORM=xcb
```

Symptom: the tool sees `xdg_session_type=wayland` while `display=:20` — the env was not fixed.
`DBUS_SESSION_BUS_ADDRESS` must come from the bot env; connecting to the user's session bus drags
AT-SPI into a different desktop's tree.

## 2. Optional: reading page content semantically

Chrome exposes its page accessibility tree only with `--force-renderer-accessibility`. Without the
flag the AT-SPI tree holds just the window chrome (~3 nodes: application + frame). With it, the same
page splits into named nodes such as `combo box "Source text"`, `page tab "Turkish"`,
`button "Translate"` — which enables **clicking by name instead of by coordinate**.

- The flag is per launch, not a setting; it has no effect when Chrome starts from the menu.
- Re-read the tree after every navigation: snapshot indices go stale.
- Trees are large (hundreds of nodes) and often paginated; count "how many arrived vs the raw total"
  so you do not mistake a missing page for "not found".

Decision: if coordinates + `wait-change` are solid enough, skip this path entirely; when they break,
fall back to semantic reading temporarily with the flag above.

## 3. Window handling without wmctrl

```bash
xdotool search --onlyvisible --name ""          # id list (empty pattern = all)
xdotool getwindowname <id>
xdotool getwindowgeometry --shell <id>           # X/Y/WIDTH/HEIGHT
xdotool windowactivate <id>                      # focus
xdotool windowmove <id> X Y
xdotool windowsize <id> W H
```

These four cover list/focus/move/resize. wmctrl only adds workspaces, sticky/pin and EWMH metadata —
not needed for this work.

## 4. Screenshots without ImageMagick

```bash
ffmpeg -loglevel error -f x11grab -video_size 1440x900 -i :20 -frames:v 1 -y out.png
# crop / scale
-vf "crop=635:115:75:330"        # w:h:x:y
-vf "scale=iw*2:ih*2:flags=lanczos"
```

`XAUTHORITY` must be set. `import`, `scrot`, `gnome-screenshot` and `xwd` are not required.
Crop + 2x upscale makes small UI text readable and spends less context than a giant full-screen image.

## 5. Recording what the user does on screen

Prefer the built-in commands:

```bash
python3 screen.py record --seconds 600 --fps 1 --dir /tmp/watch
python3 screen.py record-review --dir /tmp/watch --ratio 0.002
```

`record` writes `f0001.png`, `f0002.png`, … plus `meta.json`; `record-review` lists the frames where
the screen changed (the interesting moments). Manual equivalent if you need a different pipeline:

```bash
ffmpeg -loglevel error -f x11grab -framerate 1 -video_size 1440x900 -i :20 -t 900 \
  -y ~/.hermes/cache/scratch/watch/f%04d.png
```

**Deduplicating frames by file hash misleads**: the clock, the cursor and animations change every
frame, so every frame looks "different". Downscale to `32x20` grayscale signatures and compare bytes;
threshold at a few times the mean difference. Then merge the 6-8 chosen frames into one image
(`xstack`) and read them in a single look.

## 6. Pointer/keyboard subtleties

- **ctrl+click (open in new tab):** `keydown ctrl` → `click 1` → `keyup ctrl`. Order matters; a
  `keyup` before the click makes it a normal click.
- **Wheel:** on X11 button 4 = up, 5 = down; each `click 4/5` is one notch.
- **Drag:** glide to the target → `mousedown 1` → move through intermediate points → `mouseup 1`;
  jumping in one step leaves no selection.
- **Focus:** clicking the target is usually enough; but before sending a shortcut (`ctrl+l`) activate
  the window first (`xdotool windowactivate`).
- **State after scrolling:** `Down`/`PageDown` can also move focus in a sticky date strip or list
  selection; prefer the wheel and verify the URL/title change.

## 7. Which Chrome profile/session is open? (prove it, do not guess)

"It asks me to log in again" has two causes: the wrong profile is open, or nobody ever logged in to
that profile. Both are measurable; do not jump to copying profiles.

```bash
# 1) the user-data-dir the window uses (no argument = XDG default)
for p in $(pgrep -f 'opt/google/chrome/chrome'); do
  c=$(tr '\0' ' ' </proc/$p/cmdline)
  case "$c" in *--type=*) continue;; esac
  echo "$p :: $(echo "$c" | cut -c1-140)"
done

# 2) does that profile's cookie DB know the target domain (copy it, never open the live DB)
cp ~/.hermes/bot-desktop/xdg/google-chrome/Default/Cookies /tmp/ck.db
python3 -c "import sqlite3;c=sqlite3.connect('/tmp/ck.db');print(c.execute('select host_key,name from cookies where host_key like \"%trakt%\"').fetchall())"

# 3) was the profile ever used: URL count in History + birth time
cp ~/.hermes/bot-desktop/xdg/google-chrome/Default/History /tmp/h.db
python3 -c "import sqlite3;print(sqlite3.connect('/tmp/h.db').execute('select count(*) from urls').fetchone())"
stat -c '%w' ~/.hermes/bot-desktop/xdg/google-chrome
```

Read it like this: no session cookie (`__Secure-…session_token`, `trakt-oidc-auth`, …) means that
profile has no login; `History` with 0 URLs means the window never navigated (so "I logged in before"
belongs to another profile). `bot-desktop/browser-profile` (agent/dock) and `xdg/google-chrome`
(menu) are separate jars — whichever one the user logged into is the persistent one.

## 8. Trying a third-party GUI stack without sudo or permanent traces

When the user says "let's try this ready-made skill/tool", test it without polluting the system:

```bash
mkdir -p ~/.hermes/cache/scratch/trial && cd ~/.hermes/cache/scratch/trial
npm install --prefix . --no-audit --no-fund <package>        # postinstall may be blocked
node node_modules/<package>/npm/install.js                   # fetch the binary by hand

# missing system binary (e.g. wmctrl): extract the .deb instead of using sudo
apt-get download wmctrl && dpkg-deb -x wmctrl*.deb ./root
export PATH=$PWD/root/usr/bin:$PATH
```

- In MCP-enabled tools `npm/bin/*.js` is a shim; call the real binary (e.g. `*-linux-x64`) directly,
  otherwise the stdio handshake times out.
- If the tool thinks it is on "Wayland", apply the §1 env fix; otherwise it reports window listing
  and keyboard input as unavailable (the culprit is the leaked env, not the tool).
- When the trial ends, delete the directory, the binaries you unpacked and any profile copies. The
  user makes the decision; you only produce the measurements and the cleanup.
