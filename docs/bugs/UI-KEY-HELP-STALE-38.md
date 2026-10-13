# UI-KEY-HELP-STALE-38: Key help shows raw actions and wastes the available space

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 12 October 2026, in v0.0.38-dev2 |
| Where | Current keys help screen |
| Reproduction | unknown |
| Duplicate of | no |
| Persists in | v0.0.38-dev2 (last seen) |
| Severity | medium: Players see raw command labels and fragmented control information. |
| Family | Menus, HUD, map screen and text (`ui-text`) |
| Playtest version | v0.0.38-dev2 (surrounding playtest context) |
| From commit | source unknown, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM unknown, engine unknown, world format unknown |
| Unknown because | Menu-only screenshots do not identify exact binary; nearby gameplay screenshots identify dev2. |
| Platform or emulator | unknown (Owner did not name the emulator.) |

<!-- END GENERATED FACTS -->

## Symptom
The owner reports stale, sparse key help. A screenshot shows TAB as +aw_pov,
seven entries on page 1 of 5, and a separate F10 console footer. A second image
shows only the title and border; its transition and persistence are unknown.
The owner suggests two or three columns to use the available space better.

## Where
Current keys help screen. The surrounding playtest reports identify dev2;
the menu-only images do not independently display a build version.

## How it happened
Source inspection: aw_wait.c uses seven rows, scans raw binding order, and
falls back to command strings when its action-name table lacks a binding.
The table omits +aw_pov. keys.c explicitly handles grave and F10 before ordinary
bindings. F10 is already mentioned in the footer but must stay represented
correctly when the page layout changes. The blank-frame cause is unknown.

## Why it was not caught
No current help-page completeness and layout acceptance was attached to this
playtest. A list of bindings alone does not account for fixed key handlers.

## Reproduction
Open key help with current defaults and with rebound controls. Visit every
page, return to gameplay, and repeat. Inspect friendly action labels, fixed
console keys, paging, text clipping and any persistent blank page.

## Repair
Pending. Reuse AmiQuake Key_KeynumToString and the existing live keybindings
table plus explicit fixed-key handlers. Group readable actions and evaluate
two columns at the actual low-resolution font size before considering three.
Preserve rebinding and show the current controls, not a stale static key list.

## Verification
Owner screenshots and source diagnosis only. No repaired build or native
acceptance. The second image does not alone prove a persistent blank-page bug.

## Prevention
Check every supported action and fixed key against runtime handlers, including
F10 and grave console cycling. Capture each page at native resolution and with
rebinding; require legible labels and no clipped or unexpectedly empty pages.


## Owner evidence reconciliation, 13 October 2026

The following owner screenshot evidence was visually reviewed. Original images
remain in the private evidence archive; identifiers bind this report to those
originals. This records reported symptoms and comparison controls, not a repair
or runtime acceptance. Missing build or pose information remains unknown.

- `OWNER-20261012-170828`: SHA-256 `0517373897b2f1b94cc4ee70558d34b4d0f3a3e4855e7efd9e193b8e6efbf64a`. F10 is visible in footer; report concerns unclear/stale help, not absence of all F10 text.
- `OWNER-20261012-170836`: SHA-256 `0517373897b2f1b94cc4ee70558d34b4d0f3a3e4855e7efd9e193b8e6efbf64a`. F10 is visible in footer; report concerns unclear/stale help, not absence of all F10 text.

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
- [TOOLKIT-CELL-HIGHLIGHT-SCALE-38](TOOLKIT-CELL-HIGHLIGHT-SCALE-38.md): Selected-cell outline offset on scaled displays
- [TOOLKIT-INCLUSION-PACKAGE-38](TOOLKIT-INCLUSION-PACKAGE-38.md): CHIM inclusion metadata omitted from Toolkit packaging rules
- [TOOLKIT-TEXT-ENCODING-38](TOOLKIT-TEXT-ENCODING-38.md): Toolkit labels contain corrupted Unicode characters
- UI-ACCEPT-29 (no report page): Character selection lacks a visible OK button
- [UI-MENU-LOGO-32](UI-MENU-LOGO-32.md): The menu logo has a line above the name and reddish-pink letters instead of gold
- UI-OPTIONS-WRAP-29 (no report page): Setup selection wraps despite a bounded scrollbar
- [WAIT-NOCLIP-MESSAGE-32](WAIT-NOCLIP-MESSAGE-32.md): Wait refusal names registration, dry ground and speech together instead of the reason that applied (noclip)
- [WORLDMAP-LAVA-MISMATCH-36](WORLDMAP-LAVA-MISMATCH-36.md): The in-game map shows a lava band in Molag Amar where the world has grass and no lava

<!-- END GENERATED CATEGORY -->
