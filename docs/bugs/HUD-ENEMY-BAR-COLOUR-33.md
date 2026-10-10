# HUD-ENEMY-BAR-COLOUR-33: The enemy health bar draws orange, not yellow

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | gfx/ui.awu yellow bar tile (tools/prepare_ui.py), quantized to the reserved UI palette |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | low: The bar reads as a second health bar; size, place and timing match the original. |
| Family | Menus, HUD, map screen and text (`ui-text`) |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Repaired in source on v0.0.33-arena-combat (owner decision: yellow in the reserved UI palette),
not yet in a build. Seen in the first Vivec Arena run in the emulator (docs/COMBAT.md).

## Symptom

The enemy's health bar appears above the player's health bar at the right size and time, but in an
orange close to the health bar's red instead of the original's yellow.

## Where

`tools/prepare_ui.py` builds the bar from the original grey bar tinted (1, 0.729, 0) into `gfx/ui.awu`
and quantizes it to the image palette; the reserved UI palette bank (`tools/ui_palette.py`) holds the
red, blue and green bar colours only.

## How it happened

The palette was kept unchanged on purpose: the reserved bank is shared with the hand catalogues,
which must match it byte for byte.

## Why it was not caught

The host tests check the bar's place and timing, not its colours after quantization.

## Reproduction

Always: `dbgmode arenapit`, punch at the opponent, look at the bar above the health bar.

## Repair

`tools/ui_palette.py`: the reserved bank (format 2) is quantized from the red, blue, green and the
yellow bar (`yellow_bar`, one implementation shared with the UI atlas in `tools/prepare_ui.py`); a scene
with a format 1 bank is upgraded in place. The hand catalogue follows the reserved palette as before
(`prepare_hand_catalog.runtime_palette`). The sky palette approval (`sky_palette_overlay.approved`) checks
the approved fingerprint with the format 1 bank put back (`ui_palette.legacy_bank`, from the owned bars),
so the sky bank and the world colours are unchanged; only indices 225..253 differ.

## Verification

`tests/test_ui_palette.py` EnemyBarYellow: the tint, the bank-independent sky approval (a change outside
the bank is refused) and the in-place upgrade. In the emulator (the Vivec Arena, private evidence image)
the bar shows amber-yellow after, orange before, at the same place.

## Prevention

UI colours added later get a palette check (distance of the quantized colour to the intended one).

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Menus, HUD, map screen and text (`ui-text`). Menus, HUD, map screen, fonts and messages. See [families](README.md#families).

- AW-20260928-09 (no report page): Papers unreadable
- AW-20260928-13 (no report page): New Game confirmation defaults to Cancel
- AW25-03 (no report page): Map marker reported stale; HUD lacked global/local positions
- CHAR-CONFIRM-BORDER-29 (no report page): Character Go back / Choose actions lack OK-style frames
- [FONT-BITMAP-INDEX-32](FONT-BITMAP-INDEX-32.md): Bitmap font path keeps the .fnt glyph order; the engine indexes by game byte (wrong characters)
- [FONT-TTF-COVERAGE-32](FONT-TTF-COVERAGE-32.md): Magic Cards TrueType font silently lacks many characters and replaces ASCII brackets with ornaments
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
- [UI-MENU-LOGO-32](UI-MENU-LOGO-32.md): The menu logo has a line above the name and reddish-pink letters instead of gold
- UI-OPTIONS-WRAP-29 (no report page): Setup selection wraps despite a bounded scrollbar
- [WAIT-NOCLIP-MESSAGE-32](WAIT-NOCLIP-MESSAGE-32.md): Wait refusal names registration, dry ground and speech together instead of the reason that applied (noclip)

<!-- END GENERATED CATEGORY -->
