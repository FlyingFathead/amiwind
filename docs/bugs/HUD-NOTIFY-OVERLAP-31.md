# HUD-NOTIFY-OVERLAP-31: console messages print over the location title

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 7 October 2026, in an unknown version |
| Where | Top of screen: console notify lines over the debug title |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.31-dev3 (last seen) |
| Severity | low: Console messages print over the location title, making both unreadable for seconds. |
| Family | Menus, HUD, map screen and text (`ui-text`) |

<!-- END GENERATED FACTS -->

## Status: 7 October 2026

Open. Cause read in source; no repair yet.

## Symptom

With the debug overlay on, a console message such as the heap audit line
("Heap maps/bm026.bsp first-presented: ...") appears at the top of the screen
on top of the "AmiWind v... Vvardenfell / ..." title; both become unreadable
for a few seconds (owner screenshot, Balmora, 17:15).

Seen again in v0.0.31-dev3 with the autosave message ("Saved Autosave 2 ...")
over the title in Seyda Neen.

## Where

Quake's console notify lines (recent `Con_Printf` output shown at the top of the
view for a few seconds) and the AmiWind debug title (`aw_hud.c`, drawn at the
top-left). The heap audit message comes from `aw_stream.c` on the first frame
of a new map.

## How it happened

Both draw in the same rows at the top of the screen; neither knows about the
other.

## Why it was not caught

The heap audit message appears only on the first frame of a map, and captures
are usually taken later.

## Reproduction

Debug overlay on; cross into a new region map and look at the top of the screen.

## Repair

Not done: move the notify lines below the title while the overlay is on, or
send debug-only messages to the console without the on-screen notify.

## Verification

Pending.

## Prevention

Pending.

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
- [UI-MENU-LOGO-32](UI-MENU-LOGO-32.md): The menu logo has a line above the name and reddish-pink letters instead of gold
- UI-OPTIONS-WRAP-29 (no report page): Setup selection wraps despite a bounded scrollbar
- [WAIT-NOCLIP-MESSAGE-32](WAIT-NOCLIP-MESSAGE-32.md): Wait refusal names registration, dry ground and speech together instead of the reason that applied (noclip)

<!-- END GENERATED CATEGORY -->
