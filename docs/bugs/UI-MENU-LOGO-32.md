# UI-MENU-LOGO-32: The menu logo has a line above the name and reddish-pink letters instead of gold

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 8 October 2026, in v0.0.32-dev3 |
| Where | in-game menu logo (tools/prepare_logo.py, id1/gfx/amiwind.awi) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev3, v0.0.32 (last seen) |
| Severity | low: Cosmetic: the menu logo shows a rule above the name and reddish letters instead of gold. |
| Family | Menus, HUD, map screen and text (`ui-text`) |
| Playtest version | v0.0.32-dev3 |
| From commit | source and engine 91a7eeb |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Fixed in source on the post-v0.0.32 line (not shipped yet). Reported by the owner as a long-standing
issue in the Options and other menus. Measured on the v0.0.32-dev3 image (`gfx/amiwind.awi`).

## Symptom

The "AmiWind" logo at the top of the in-game menus (main menu, Options, Wait, key help):

- a horizontal line runs ABOVE the name;
- the letters are a reddish pink-tan instead of the gold of the project logo.

## Where

`tools/prepare_logo.py` `prepare_menu_logo()`, called by `tools/build_aga.py image`, writes the
200x40 indexed image `id1/gfx/amiwind.awi`; the engine copies its bytes to the screen unchanged
(`AW_UILogo`, `engine/aga/src/aw_ui.c`).

## How it happened

1. Source: the builder used `resources/media/AmiWind_wordmark.png`, which is the gold name with
   the gold rule above it (the startup screen's layout). Rows 9-10 of the 40-row menu image were
   that rule.
2. Colour: the image was quantised to the nearest colour of the whole 256-colour game palette.
   The game palette is built from Morrowind's textures and has no saturated bright gold; plain
   nearest-RGB matching of the logo's saturated yellow lands on salmon and pink tans
   (e.g. index 241 (203,129,101), 234 (214,154,123), 233 (215,168,136)) and on the deep reds
   249, 250 and 253 ((187,93,68), (179,76,56), (148,52,41)). Indices 233-253 belong to the
   reserved UI slots 225-253 that hold the original status-bar colours (red health bar).
   Of the 1,377 non-black pixels in the dev3 logo, 424 used reserved UI slots and the mean hue
   was 26 degrees (red-orange), not gold (about 45 degrees).
3. The sky colour bank (`tools/sky_palette_overlay.py` `BANK`) was not involved in dev3: the logo
   used none of its entries. Nothing prevented it from doing so in another palette, though.

## Why it was not caught

No test looked at the menu logo's pixels; tests only checked that the builder used the wordmark
file. The menu logo is small and was judged by eye on screenshots where the reddish tint reads as
"warm".

## Reproduction

Any image up to v0.0.32-dev3: open the main menu or Options and look at the logo. Offline:
read `id1/gfx/amiwind.awi` with the boot palette and list the indices used.

## Repair

- The menu logo is made from `resources/media/AmiWind_logo_name_only.png` (the name without the
  rule). An optional rule can only be drawn BELOW the name (`rule='below'`); the default is none.
- Colours come from the palette's own gold ramp: entries with a gold hue (30-60 degrees),
  saturation of at least 0.25 and not near black, and never a reserved UI slot (225-253), a sky
  bank entry (`BANK`) or the transparent index 255. Each pixel takes the ramp entry closest in
  brightness first and colour second, without dithering, so the letters stay crisp. Background is
  the palette's black.
- The previous method is kept and selectable: `build_aga.py image --menu-logo legacy` rebuilds the
  old wordmark with whole-palette nearest colours (DEBUGGING / comparison only).
- The startup screen (`prepare_logo`) is unchanged: it has its own 256-colour palette and keeps
  the wordmark's real gold.

## Verification

- `tests/test_menu_logo.py`: no rule above the letters (the top rows of the opaque area are letter
  pixels only), a rule if present is below the letters, mean hue of the opaque pixels between 35
  and 55 degrees, no reserved UI or sky bank index used, the image still fits 200x40, the builder
  uses the name-only source and the legacy method is still selectable.
- dev3 palette (offline): the legacy method reproduces the dev3 `amiwind.awi` byte for byte; the
  new logo uses only gold-ramp entries and black, no reserved UI slot or sky bank entry, mean hue
  38 degrees.
- In game (FS-UAE, fresh copies of the v0.0.32-dev3 image, only `gfx/amiwind.awi` replaced in the
  second): the Options menu shows the name without a line, in the same gold as the menu text, and
  inside the title box.

Remaining limit: the game palette's brightest gold is a pale gold (238,221,170); a deeper, more
saturated gold would need its own palette entries.

## Prevention

The menu logo's palette entries are now chosen by rule (gold ramp, no reserved or banked entries)
and tested, instead of by an unconstrained nearest match.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Menus, HUD, map screen and text (`ui-text`). Menus, HUD, map screen, fonts and messages. See [families](README.md#families).

- AW-20260928-09 (no report page): Papers unreadable
- AW-20260928-13 (no report page): New Game confirmation defaults to Cancel
- AW25-03 (no report page): Map marker reported stale; HUD lacked global/local positions
- CHAR-CONFIRM-BORDER-29 (no report page): Character Go back / Choose actions lack OK-style frames
- [FONT-BITMAP-INDEX-32](FONT-BITMAP-INDEX-32.md): Bitmap font path keeps the .fnt glyph order; the engine indexes by game byte (wrong characters)
- [FONT-TTF-COVERAGE-32](FONT-TTF-COVERAGE-32.md): Magic Cards TrueType font silently lacks many characters and replaces ASCII brackets with ornaments
- [HUD-ENEMY-BAR-COLOUR-33](HUD-ENEMY-BAR-COLOUR-33.md): The enemy health bar draws orange, not yellow
- [HUD-NOTIFY-OVERLAP-31](HUD-NOTIFY-OVERLAP-31.md): Console messages print over the location title
- HUD-STATS-29 (no report page): Health uses fixed 100; other bars hardcoded full
- MAP-FOCUS-DRAG-29 (no report page): Map or journal keeps dragging after window focus returns
- MAP-MARKER-29 (no report page): Requested: click to place a user map marker
- MAP-REG-01 (no report page): In-Game map mode hid settlement markers (regression)
- MAP-RIGHT-DRAG-29 (no report page): Advertised right-drag does not pan teleport map
- MAP-SPOTS-28 (no report page): In-game map screen has white/yellow spots
- [PHOTO-DEBUG-STRIP-33](PHOTO-DEBUG-STRIP-33.md): Photo mode with Ctrl+H: the coordinate strip blacks out only from x=88, leaving the bottom-left corner of the view
- [PHOTO-GALLERY-TEXT-33](PHOTO-GALLERY-TEXT-33.md): Photo mode leaves test-room and gallery instruction text over the view
- [PLACE-NAMES-INTERIOR-31](PLACE-NAMES-INTERIOR-31.md): Location label has no place name inside interiors
- UI-ACCEPT-29 (no report page): Character selection lacks a visible OK button
- UI-OPTIONS-WRAP-29 (no report page): Setup selection wraps despite a bounded scrollbar
- [WAIT-NOCLIP-MESSAGE-32](WAIT-NOCLIP-MESSAGE-32.md): Wait refusal names registration, dry ground and speech together instead of the reason that applied (noclip)

<!-- END GENERATED CATEGORY -->
