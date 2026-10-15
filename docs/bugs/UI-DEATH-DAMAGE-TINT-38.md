# UI-DEATH-DAMAGE-TINT-38: Lava damage tint also colours the death menu and selection

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 13 October 2026, in v0.0.38 |
| Where | Owner v0.0.38 playtest: teleport, lava contact and death screen |
| Reproduction | unknown |
| Duplicate of | no |
| Persists in | v0.0.38 (last seen) |
| Severity | medium: Death-menu text and selection remain tinted by the gameplay damage effect. |
| Family | Menus, HUD, map screen and text (`ui-text`) |
| Playtest version | v0.0.38 |
| From commit | source unknown, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM unknown, engine unknown, world format unknown |
| Unknown because | Reported during the owner playtest; exact running image binding needs confirmation. |
| Platform or emulator | unknown (Earlier owner session was WinUAE; emulator not restated for this specific report.) |

<!-- END GENERATED FACTS -->

## Symptom

When the player dies in lava, the red damage overlay also tints the death-menu text and selected option. The owner clarified that the UI does not appear above the gameplay damage effect.

## Where

Owner-reported v0.0.38 gameplay on 13 October 2026. Exact map, pose and save identity remain to be recorded.

## How it happened

Cause unknown. Teleport saving, unsafe lava autosaves and death-menu tint are recorded independently so one repair cannot silently close another.

## Why it was not caught

No exact-package regression currently binds safe teleport arrival, hazardous autosave reload and readable death-menu composition together.

## Reproduction

Use a disposable gameplay copy. Record the source/image, destination, health, movement and water/lava state, save timestamp and menu state before and after the action. Repeat a normal safe arrival and ordinary death as controls. Preserve the original failing save privately.

## Repair

Inspect the existing AmiQuake palette/content-shift and menu drawing paths before choosing a fix. Render the death UI independently of gameplay damage tint. Owner suggestion: freeze the game view behind the death screen. Verify whether palette-based AGA rendering requires a separate untinted UI palette treatment; a changed draw order alone is not assumed sufficient.

## Verification

The original owner trigger still needs exact-image reproduction. Source
correction and compiled regression evidence are recorded below; these do not
establish native or owner acceptance. Compare original/OpenMW behavior and
verify the exact candidate on the target engine.

## Candidate diagnosis and verification, 13 October 2026

AmiQuake V_UpdatePalette applies contents/damage shifts to every indexed colour, including UI. The death prompt uses key_game and was outside the existing unshifted-menu palette path. The candidate reuses AW_UIMenuPalette with host_basepal and explicitly invalidates palette ownership even when its pointer is unchanged. It reuses AW_ModalWorldFrozen for the choice stage after the death animation, retaining the visible background and leaving input/audio services alive. The frozen background uses unshifted scene colours too; no second palette or framebuffer allocation is added. Compiled regressions verify tint restoration after UI closes, frozen server/client clocks, and ordinary modal controls. Target-native and matched original captures remain pending.

## Prevention

Add a regression for the demonstrated cause, then a target-native safe/unsafe transition check. Keep save integrity, game-state behavior and UI visibility as separate acceptance results.

## Exact RC1 evidence, 13 October 2026

The original exact-package death prompt showed beige/gold controls without lava red tint; snapshots four seconds apart were reviewed. The immediate key-selection frame was black, so highlight/selection acceptance is not claimed. Save/reload survival does not substitute for complete prompt interaction, viewport/font coverage or owner acceptance.

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
- [HUD-STATS-29](HUD-STATS-29.md): Health uses fixed 100; other bars hardcoded full
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
- [UI-INVENTORY-LAYOUT-40](UI-INVENTORY-LAYOUT-40.md): Inventory text overlaps fields and footer; preview initially faces away
- [UI-KEY-HELP-STALE-38](UI-KEY-HELP-STALE-38.md): Key help exposes raw actions and uses a sparse outdated layout
- [UI-MENU-LOGO-32](UI-MENU-LOGO-32.md): The menu logo has a line above the name and reddish-pink letters instead of gold
- UI-OPTIONS-WRAP-29 (no report page): Setup selection wraps despite a bounded scrollbar
- [WAIT-NOCLIP-MESSAGE-32](WAIT-NOCLIP-MESSAGE-32.md): Wait refusal names registration, dry ground and speech together instead of the reason that applied (noclip)
- [WORLDMAP-LAVA-MISMATCH-36](WORLDMAP-LAVA-MISMATCH-36.md): The in-game map shows a lava band in Molag Amar where the world has grass and no lava

<!-- END GENERATED CATEGORY -->
