# Example measurements (1440x900, Xfce) — re-measure on your machine

> This file is **a sample taken on one machine**, not a portable map. It goes stale when the theme,
> panel layout or resolution changes (the menu order changed while this file was being written).
> Re-measure with `check` + `shot --grid`.

Coordinates refer to the **screen**, not to a screenshot (scale 1:1). To re-measure: take a
`shot --grid 50`, read the image, and write down the center of the target.

## Panel / menu

| Target | Coordinate | Note |
|---|---|---|
| Application menu (top-left icon) | `15 15` | opens the category list |
| "Internet Browser" (top of the menu) | `100 124` | opens Chrome directly — **shortest path** |
| Menu: "Internet" category | `63 275` | submenu opens to the right (was `119` in the older theme) |
| Menu: "Accessories" | `63 197` | was "Utility" in the older theme |

> The menu order follows the theme; always confirm with `15 15` + `shot`.

## Chrome

| Target | Coordinate | Note |
|---|---|---|
| Bookmarks bar row | `y=128` | shown with `ctrl+shift+b` |
| "Translate" bookmark | `88 128` | ctrl+click = open in a new tab |
| Address bar, maximized 1440x900 window | `y=79` | prefer `ctrl+l` over a coordinate |
| Address bar, window at 1440x880+0+28 | `600 91` | the tab strip sits at `y≈50` in this geometry |
| Tab strip | `y≈34` | `ctrl+Tab` is safer than clicking a tab |

## Google Translate (translate.google.com.tr)

| Target | Coordinate | Note |
|---|---|---|
| Source text box | `390 415` | then `type` / `fill` |
| Source language chips | `y=337` | "Detect language" ~80, "Turkish" ~155 |
| Target language chips | `y=337` | "English" ~744, "Turkish" ~815 |

## Trakt (app.trakt.tv)

| Target | Coordinate | Note |
|---|---|---|
| Sidebar "History" | `100 735` | `app.trakt.tv/history` |
| Date strip | near the top, `y≈200` | `Down`/`Up` keys move focus here and add `?date=` to the URL |
