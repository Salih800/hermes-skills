# Reading dense pages (truncated text, many frames, SPA routes)

## When to use

Whenever you must **extract text** through screenshots and clicks: list/history pages, card grids,
detail panels, "list what I watched recently" style jobs that read many rows from one page. In short:
the text is cut with `…`, a deep route returns 404, or you need to read many frames in a row.
Clicking recipes live in SKILL.md; this file is about making reading cheap.

## 1. Text cut by CSS `ellipsis` is NOT in the pixels

For a label like `"S1 • B22 - The ..."` the missing part exists in the DOM/CSS, not in the pixels.
So none of these help: zooming with `shot --crop`, zooming out with `ctrl+-`, waiting for the column
to widen, or hoping for a hover tooltip. The moment you see an ellipsis the only exit is **open the
target**.

Screenshot zooming only helps with *small but complete* text (thin fonts, distant badges). Rule of
thumb: if the text ends with `…`, you need navigation, not magnification.

## 2. Read the full text in the detail view, do not lose the list

- Open the card with `click X Y --mods ctrl` → a background tab opens, the list tab stays put.
- In the new tab the title is usually complete in two places: the page `h1` and the right detail
  panel heading (`<show> / S2 • B11 - <episode name>`). If the panel exists, skip the `h1`; the panel
  is a smaller area to read.
- When done, return to the list by clicking its tab; navigating back with the browser button breaks
  the scroll position.
- Do not change anything lasting on the list page: sorting, filters or "watched" marks alter the
  user's view and undoing them costs an extra turn.

## 3. SPA route quirks: if a deep route 404s, try query params

In single-page apps a deep route like `/show/<slug>/seasons/2` may 404 while the same content opens
with `/show/<slug>?season=2`; episode details arrive as
`?view=episode&season=2&episode=5`. When a route 404s do not keep inventing addresses: go up one
level, find the working URL, and copy the query parameter it used (the address bar shows it).

By the same logic a "+8 more" style box may only reveal the first extra item. The reliable way to see
the whole list is opening items one by one, or horizontally scrolling the episode rail on the show page.

## 4. N frames → 1 vision call (composite crops)

One vision call per screenshot is the most expensive path. When you need the same region across N
frames:

```bash
S=~/.hermes/skills/bot-screen-control/scripts/screen.py
for id in 9 10 11 12 13; do
  python3 $S key "ctrl+l" >/dev/null
  python3 $S type "<url>&episode=$id" >/dev/null
  python3 $S key "Return" >/dev/null
  python3 $S wait-stable --quiet-for 1.5 >/dev/null
  python3 $S shot --out /tmp/ep$id.png >/dev/null
done
python3 ~/.hermes/skills/bot-screen-control/scripts/stack_crops.py \
  --box 940,160,1440,205 --scale 2 --out /tmp/titles.png /tmp/ep9.png /tmp/ep10.png /tmp/ep13.png
```

Then read `titles.png` in one go. The box `(x1,y1,x2,y2)` must land on the same place in every
frame: fine when the target is fixed (right panel heading, tab strip, table column).

Leave ~2+ s between frames; in a slow-loading frame the title may not be rendered yet, giving an
empty row in the composite (re-shoot that frame alone, not the whole series).

## 5. Verify the number of ctrl+clicks

Clicking the same coordinate with `--mods ctrl` repeatedly does not always open a new tab: if the
page scrolled or the click hit the same link again, the tabs do not multiply. After a click series
**screenshot the tab strip and count**; if you have fewer tabs than expected, open the missing items
one by one.

## 6. Reset the zoom

If you used `ctrl+-` / `ctrl+0` for reading, return to 100% with `key "ctrl+0"` when done; leaving the
user's window on a small font produces wrong coordinates on the next turn.

## 7. Sticky indicators swallow `Page_Down`

On pages with a sticky date/scroll indicator (scrubber), `key Page_Down` does not scroll — it sends
events to the indicator: the date jumps, a persistent panel stays open and `Escape`/`Home` will not
close it. Always scroll with `scroll down --amount N --at X,Y` (`--at` puts the pointer on the content
area, not on the indicator).

## 8. In-page PDF / document viewers: read the file, not the screen

Documents embedded in a page (guidelines, contracts, lecture notes, anything 10+ pages) usually open
at 40-50% zoom; reading dozens of pages with `shot` + vision is slow and error-prone. The right path
is downloading the document and reading its text locally:

1. Click the download/print icon in the viewer toolbar (usually the rightmost arrow or printer).
   Chrome's "Print" dialog opens with "Save as PDF" already selected; leave "Pages: All".
   → `Save`.
2. A filename dialog appears (folder `~/Downloads`). If a file with that name exists, rename it:
   click the name field, `key "ctrl+a"`, `type "NewName.pdf"`, then `Save`. Never overwrite — the old
   copy is a different document and cannot be recovered.
3. Verify with `ls -lt ~/Downloads | head -3`, then read it with `read_file`: if the PDF has a text
   layer it returns `extracted_document: true` and tables arrive as `|` rows; find the sentence you
   need with `search_files`.
4. The file lands in the user's `~/Downloads`: mention its name in your report, do not delete it on
   your own.

Why: this path reads every rule at once and lets you quote from text instead of guessing. Fall back to
reading the screen only when the viewer has no text layer (a scanned document) — then use page-by-page
`shot --crop` plus the composite method from §4.
