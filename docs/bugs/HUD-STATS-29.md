# HUD-STATS-29: Health uses fixed 100; other bars hardcoded full

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 5 times; something has to be done

- Reported with v0.0.40-dev1 at 2026-10-14 (time not recorded): Original HUD reference requires actual weapon/fists and selected spell/enchantment boxes with applicable condition/charge indicators; no off-hand guess.
- Reported with v0.0.40-dev1 at 2026-10-14 (time not recorded): Opening HUD timing queried. Source audit finds missing staged channel checks; actual weapon model is a separate gate. Native reproduction and repair pending.
- Reported with v0.0.40-dev2 at 2026-10-14 (time not recorded): Dev2 source restores staged HUD channels and paper-pickup fighting. Seven focused checks pass; full suite, target and native pending. Map/menu gates and inventory pose remain separate.
- Reported with v0.0.40-dev2 at 2026-10-14 (time not recorded): Original and candidate show paper pickup enabling fists before the hall guard; reading alone does not. Scoped HUD observations retained; failed exit gate and full-route checks remain separate.
- Reported with v0.0.42-dev1 at 2026-10-17 01:58 +0300: owner: the weapon and magic boxes at the bottom of the HUD are still placeholders (fist, dash) and look bad

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | unknown |
| First noticed | unknown, in v0.0.29-dev |
| Where | HUD resource bars and planned actual weapon/fists and selected spell/enchantment boxes |
| Reproduction | always |
| Duplicate of | no |
| Persists in | unknown |
| Severity | low: Bars show a healthy character as partly depleted; cosmetic. |
| Family | Menus, HUD, map screen and text (`ui-text`) |
| Waiting on | Lacks dependency: magic (spells, active effects, magic menu) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.42 (17 October 2026)._

<!-- contents start -->
## Contents

- [PERSISTING: reported 5 times; something has to be done](#persisting-reported-5-times-something-has-to-be-done)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Functional HUD placeholder candidate, 14 October 2026](#functional-hud-placeholder-candidate-14-october-2026)
- [Planned effect-display diagnostic, 14 October 2026](#planned-effect-display-diagnostic-14-october-2026)
- [Temporary centre Guard label removed in source, 14 October 2026](#temporary-centre-guard-label-removed-in-source-14-october-2026)
- [Later exact normal-HUD check, 14 October 2026](#later-exact-normal-hud-check-14-october-2026)
- [Opening HUD source audit, 14 October 2026](#opening-hud-source-audit-14-october-2026)
- [Opening HUD source repair, 14 October 2026](#opening-hud-source-repair-14-october-2026)
- [Scoped opening comparison, 14 October 2026](#scoped-opening-comparison-14-october-2026)
- [Original weapon and magic boxes, 17 October 2026](#original-weapon-and-magic-boxes-17-october-2026)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Symptom

The historical issue concerned resource bars showing an incorrect fraction:
health divided by a fixed 100, with the other bars treated as full. The newer
maintainer reference also identifies missing equipped-weapon or bare-fist and selected
spell/enchantment HUD boxes with their appropriate indicators. These are
separate presentation requirements; the old bar-arithmetic cause does not
explain missing item or magic icons.

## Where

The original-style lower-left HUD, engine/aga/src/aw_ui.c and the planned
HUD conversion/state bindings in the roadmap.

## How it happened

The initial HUD used placeholder resource fractions. Current source inspection
shows AW_UIHud reading separate current/maximum values for health, magicka and
fatigue, plus live single-player entity health; 55/55 is therefore full. The
older independent pixel checks remain historical source evidence, not complete
current native acceptance.

Before the functional placeholder candidate below, the HUD drew resource bars,
an optional enemy bar and Guard text, without item or magic boxes. The original
artwork and selected-magic game logic remain incomplete.

## Why it was not caught

Resource-fraction pixel checks can verify bar arithmetic without proving the
complete original HUD layout, item-selection state or icon assets. The maintainer's
new original-HUD reference makes that missing scope explicit.

## Reproduction

Inspect current AW_UIHud and compare the actual game HUD with the original:
health/magicka/fatigue bars, weapon or unarmed icon, selected spell or enchanted
item icon and the original condition/charge indicators where applicable.
Use actual equipped and selected state; empty/unsupported selections must be
represented honestly. Test changed resource maxima and damaged/charged items
separately from visual layout.

## Repair

Keep the current independent resource fractions. The planned HUD must reuse
AmiQuake's UI picture/bar machinery and bounded source-derived icon resources.
Bind the weapon/fists box to actual current combat/equipment state. Bind the
other box to the selected spell or enchantment, with actual condition/charge
where the original uses it. It is not a guessed off-hand equipment slot.
Selection/use/effect and persistence behavior still need implementation where
absent; decorative icons cannot stand in for those systems.

The planned O attributes/stats screen is documented with the existing world-map,
inventory and journal roadmap. It is not implemented by this report.

## Verification

Current resource binding is source-checked; older independent pixel checks are
preserved as historical evidence. The missing weapon/fists and selected-magic
presentation is a current source finding and maintainer-reference request.
Original reference images remain private and are not public source assets.
The later bounded placeholder implementation is described below. Native HUD
parity, packaging and maintainer acceptance remain pending. Keep this existing issue
open, with no first fixed version.

## Prevention

Test independent current/max fractions and actual equipment/magic selection
separately, including bare fists, an equipped weapon, selected spell, selected
enchanted item, depleted condition/charge and absent/unsupported selection.
Capture matched original/native HUD layout before claiming complete parity.

## Functional HUD placeholder candidate, 14 October 2026

The new source candidate adds two bounded gold-framed boxes beside the existing
resource bars. The primary placeholder changes between a clear fist and generic
weapon mark using the real admitted right-hand inventory item. It refreshes on
equip, unequip and ownership changes. An off-hand shield never supplies the
magic box. Since the runtime has no selected-spell/enchantment state yet, that
box is explicitly empty with a dash; no spell, charge or effect is invented.

These are authored interim marks, not converted original item artwork.
Health/magicka/fatigue fractions and rendering remain unchanged. Actual original
weapon/fist and selected-magic icons, condition/charge indicators, selected-magic
game logic and full original HUD parity remain open. Original UI textures must
come from locally supplied game data during conversion and stay out of public
source; fixed right-corner artwork mirrors the left pattern without movable
or resize controls.

The real UI framebuffer fixture links actual inventory metadata, state and
equip/unequip rules. It verifies fist/weapon transitions, ownership removal and
restoration, unchanged empty magic under off-hand equip, and 32 stable draws
without new malloc calls or catalogue opens. The preceding HUD fails the
transition assertion; the candidate passes. Five other affected UI callers pass.
No full target, native HUD capture, original-reference visual parity, measured
frame-time saving or maintainer acceptance is established.

## Planned effect-display diagnostic, 14 October 2026

Plan a bounded, clearly labelled dbg teststatuseffects preview for the icon
catalogue, stacked-source/duration labels and overflow. It must clear after a
short real-time interval independent of game pause, stay out of saves and never
alter actual effects, statistics or random-number state.
This display diagnostic is not implemented, and cannot prove real effect logic.

## Temporary centre Guard label removed in source, 14 October 2026

The maintainer rejects the inherited Guard text over the middle of the normal world
view. The new mutable candidate removes only that AW_UIHud text call. Actual
guard state, the existing callback, debug combat readout, ordinary target-name
locations, enemy bar and resource/equipment boxes remain.

A real framebuffer regression toggles the guard callback/state and requires
identical normal HUD pixels, an untouched centre, and working target-name
rendering at its original location. The previous runtime fails that assertion;
the new candidate passes under UBSan. Existing real combat controls still
exercise held/automatic blocks, no-shield refusal and attack masking.

The earlier pin808 native male-Nord view shows the sword placeholder and empty
magic dash, but also the now-rejected Guard label. It cannot validate the new
removal. The new source requires its own full gate, Amiga target and native HUD
check. Original artwork, selected magic and complete visual acceptance remain
open; placeholders are interim authored marks.

The detailed [active-effect HUD findings and plan](../HUD_ACTIVE_EFFECTS.md)
publish the inspected original-source limits and condition/charge distinctions.
The latest requested layout is a row above bars and beneath the viewport, tiled
when necessary; original icons, effect grid and diagnostic remain planned.

## Later exact normal-HUD check, 14 October 2026

The exact later target/FPU and full suite pass. Its native normal HUD has no
centre Guard label while the ordinary NPC target name remains at its existing
location. This is scoped confirmation of the removed temporary draw call;
guard mechanics remain active in a separate actual incoming-block control.

The authored weapon/fist and empty-magic placeholders remain interim. Original
icons, selected-magic logic, condition/charge, active-effect grid and complete
original visual parity are not accepted by this observation.


## Opening HUD source audit, 14 October 2026

Original character-generation scripts enable HUD/menu channels in stages.
Race selection at the pier restores movement without unlocking every channel.
After the Census review, the class conversation enables the stats menu; the
registration-paper script enables inventory, and taking the papers enables
fighting and magic. Ring pickup enables the magic menu; the courtyard barrel
unlocks the map menu. OpenMW ties HUD bar, weapon and magic visibility to their
corresponding allowed windows. The inspected OpenMW code is version 0.51;
this is source evidence, not a matched 0.48 native capture or original-game
sequence.

The audited dev1 `AW_UIHud` checks connection and the global HUD switch, then draws all
three bars and both item slots without equivalent per-channel opening gates.
That establishes a source parity gap. The weapon HUD slot is distinct from
actual first-person hands/weapons, which also depend on fighting permission
and ready state. Audit the papers-taken interval separately from the later hall
guard permission. Do not infer a visible weapon-model failure from a HUD rule.

The manual global toggle is separate from those script permissions. In the
inspected OpenMW 0.51 defaults, F11 toggles HUD visibility; console `ToggleMenus`
and `TM` use the same visibility flag without unlocking windows. This does not
establish the original Morrowind executable's default key. AmiWind's archived
`aw_ui_hud` setting accepts 0/1. `dbg hud` is a separate inspector which consumes
attack input while enabled; it is not the ordinary HUD visibility switch.

No opening behavior is repaired by this record. Reproduce new game, pier race
selection, Census review, paper activation/taking, ring pickup and courtyard
barrel in matched original and target sessions. Include save/load at transition
boundaries and preserve explicit debug-test exemptions. This remains open;
full native parity and any shipped fixed version are unestablished.

## Opening HUD source repair, 14 October 2026

The unreleased dev2 candidate separates stats, weapon and magic HUD channels.
Bars unlock when Census review completes; activating the papers unlocks the
weapon slot even if the reader is closed without taking them. Taking the papers
allows fighting before hall-guard acknowledgement. Ring pickup unlocks the
magic slot, and dropping or returning the ring does not revoke that permission.
The global HUD switch hides permitted channels without changing story state.
Explicit debug-test scenes retain their bypass. Door, jump and character-modal
restrictions remain separate.

The implementation reuses AmiQuake's existing bottom-HUD fill and box drawing,
AmiWind's story transitions, physical input gates and bounded persistent global
table. Paper activation records one global instead of changing the save layout.
If that table is full, activation refuses with a message and retains the papers;
it does not open the reader or silently advance the story. Older snapshots with
hall permission retain fighting and weapon-slot admission. Released saves retain
the new global through the existing encoder/decoder; this does not add support
for saving during registration, which the current save codec still refuses.

Seven focused executable fixtures pass: HUD pixels/global hiding, real paper
activation/refusal, physical input, character state/save, debug-scene restoration,
opening barriers and inventory save encoding. The three before-change controls
reproduce missing channel gating, missing paper activation permission and fighting
remaining locked until the hall guard. Sanitizer checks accompany the executions.
The existing full-table, drop, door and modal restrictions are assertions, not
native visual acceptance.

The exact implementation now completes 4,086 tests: 4,080 passes, three
Windows-only skips and three tracked expected failures, with no unexpected
failures or errors. The Amiga/FPU target also passes. The scoped original/target comparison below is complete; full-route
opening checks remain pending. Follow the complete new-game/pier/Census/papers/ring/barrel sequence,
including available save/load boundaries and debug controls. This change does
not add map/menu admission, selected-magic logic, original icon artwork or the
dedicated inventory pose. It does not establish that the reported third-person
punching, blocking or swimming defects are repaired. The broader issue remains
open and this candidate has not shipped.

## Scoped opening comparison, 14 October 2026

The current unreleased candidate shows no bars or item slots at the pier.
Completing Census character review reveals the status bars. Reading the papers
and leaving them on the table reveals the weapon slot, while physical F leaves
the hands stowed. Taking the papers enables physical F to raise visible fists
before the hall guard acknowledges them. Global HUD hiding does not change
that permission. Taking the courtyard ring reveals the magic slot.

The original Morrowind scripts running in OpenMW independently show the same
review and paper sequence: bars after review, weapon slot after reading, and
visible fists from physical F after taking the papers and dismissing the original
tutorial prompts. Paper possession was recorded in the original inventory.
Fighting stays locked when the papers are read and left behind. Retain this
original rule; the hall guard is not the fighting unlock point.

This comparison used diagnostic placement and different character appearances,
cameras and resolutions. The candidate bypassed the ship and travelled directly
between test maps; barrel placement used noclip before returning to normal
movement. It does not establish normal-route collision, save/load, complete
visual parity, attack damage, third-person animation, blocking or swimming.
The native diagnostic exit-validation gate failed. Its independent resource
readback passed, but does not turn the failed gate into a pass. These observations
are retained separately; this is not release acceptance or a new shipment.
The original reference exited normally. Full opening-route checks remain open.

## Original weapon and magic boxes, 17 October 2026

Reported again by the maintainer in v0.0.42-dev1: the boxes were placeholders, a
flat skin-coloured fist and a dash. That fist was not a converted picture at
all: it was an 8 x 8 bit pattern written into the source (`hud_equipment_boxes`
in aw_ui.c) and filled with one menu-gold colour, so no conversion or palette
setting could have made it look like the original.

Repair (v0.0.42-dev1, docs/HUD.md): one icon and HUD-art lookup table built at
image time from the user's own game data (tools/prepare_icons.py,
`gfx/icons.awl` + `gfx/icon/<sha>.awi`, each picture stored once by SHA-256):

* the weapon box shows the equipped weapon's own icon, or the original
  hand-to-hand icon when unarmed, over a thin condition bar (empty for fists);
* the magic box shows the selected magic item's icon on the original magic
  backdrop over its charge bar, and the empty box when nothing is selected;
* the box and bar frames are the original thin menu border, the bar fill the
  original grey bar tinted with Morrowind.ini's fill colours; sizes are the
  original's times 24/42 (our resource bars are 24 pixels tall, the
  original's 42): box 20 x 20, icon 18 x 18, bar 20 x 4.

New game state: the selected magic item and the current enchantment charge of
each owned item, saved (AWS4 feature bit 4); the maximum charge comes from the
ENCH, MGEF and GMST records; Cast When Used and Cast When Strikes items
recharge by fMagicItemRechargePerSecond (0.05 per second) of unpaused play and
of waited time. The original's magic menu does not exist yet, so the
selection is made with the console command `aw_magic select ID`; spells
cannot be selected because there is no spell list. Casting from an item is not
implemented, so charge is spent only by the diagnostic `aw_magic charge`.
`aw_hud_icons 0` brings back the interim marks.

Verification: synthetic-picture builder tests (tests/test_hud_icons.py),
native fixtures for the table, the boxes, single loading per change, the
magic rules, the catalogue bytes and the save round trip; on the maintainer's
data the conversion gives 15 table rows and 14 pictures (4,192 bytes) and the
item catalogue's first 496 bytes per row are unchanged. In FS-UAE (JIT preset,
v0.0.41 image with this engine and data): unarmed, steel longsword, the ring
selected at full and at partial charge, recharge observed (13 to 17.1 points),
switching recorded on video. Per-frame cost and the side-by-side with the
original HUD are recorded with the evidence. Native acceptance by the maintainer is
pending; the issue stays open (spells, active effects, the magic menu and the
inventory icons, UI-ICONS-INVENTORY-42, remain).

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Menus, HUD, map screen and text (`ui-text`). Menus, HUD, map screen, fonts and messages. See [families](README.md#families).

- AW-20260928-09 (no report page): Papers unreadable
- AW-20260928-13 (no report page): New Game confirmation defaults to Cancel
- AW25-03 (no report page): Map marker reported stale; HUD lacked global/local positions
- CHAR-CONFIRM-BORDER-29 (no report page): Character Go back / Choose actions lack OK-style frames
- [CHIM-REGION-DOORS-NO-PROMPT-42](CHIM-REGION-DOORS-NO-PROMPT-42.md): Doors in CHIM region cells show no entrance at all (no prompt, not even Interior unavailable), e.g. every door in Khuul
- EXTRAS-MENU-54 (no report page): Requested: an Extras choice on the main menu that opens what the game holds: the arena, the dance scenes, the in-game videos, later a library of every book
- [FONT-BITMAP-INDEX-32](FONT-BITMAP-INDEX-32.md): Bitmap font path keeps the .fnt glyph order; the engine indexes by game byte (wrong characters)
- [FONT-TTF-COVERAGE-32](FONT-TTF-COVERAGE-32.md): Magic Cards TrueType font silently lacks many characters and replaces ASCII brackets with ornaments
- [HUD-DEBUG-STRIP-OVER-BOXES-42](HUD-DEBUG-STRIP-OVER-BOXES-42.md): Debug coordinate strip's black fill and text cover the weapon and magic boxes
- [HUD-ENEMY-BAR-COLOUR-33](HUD-ENEMY-BAR-COLOUR-33.md): The enemy health bar draws orange, not yellow
- [HUD-NOTIFY-OVERLAP-31](HUD-NOTIFY-OVERLAP-31.md): Console messages print over the location title
- MAP-FOCUS-DRAG-29 (no report page): Map or journal keeps dragging after window focus returns
- MAP-MARKER-29 (no report page): Requested: click to place a user map marker
- MAP-REG-01 (no report page): In-Game map mode hid settlement markers (regression)
- MAP-RIGHT-DRAG-29 (no report page): Advertised right-drag does not pan teleport map
- MAP-SPOTS-28 (no report page): In-game map screen has white/yellow spots
- [NOCLIP-BOB-DEFAULT-42](NOCLIP-BOB-DEFAULT-42.md): Head bob still on in noclip mode by default, although the noclip bob was set to off by default
- [NPC-DREAMER-GREETING-DEFAULT-42](NPC-DREAMER-GREETING-DEFAULT-42.md): Dreamers (Sixth House sleepers) give a default greeting instead of their own Sixth House greeting
- OPTIONS-CROSSHAIR-STYLE-48 (no report page): Requested: crosshair colour and shape in Options, and Options in framed categories, full screen
- OPTIONS-MOUSE-SENSITIVITY-48 (no report page): Requested: mouse sensitivity in Options and the console (the default is too fast for some players)
- PHOTO-CROSSHAIR-51 (no report page): In photo mode the crosshair stays: crosshair off and dbg crosshair off do nothing, and photo mode does not hide it by itself
- [PHOTO-DEBUG-STRIP-33](PHOTO-DEBUG-STRIP-33.md): Photo mode with Ctrl+H: the coordinate strip blacks out only from x=88, leaving the bottom-left corner of the view
- [PHOTO-GALLERY-TEXT-33](PHOTO-GALLERY-TEXT-33.md): Photo mode leaves test-room and gallery instruction text over the view
- [PLACE-NAMES-INTERIOR-31](PLACE-NAMES-INTERIOR-31.md): Location label has no place name inside interiors
- RAM-WARNING-BOX-52 (no report page): Requested: under 32 MB of Fast RAM a WARNING message box for a few seconds before the AmiWind logo
- [TOOLKIT-CELL-HIGHLIGHT-SCALE-38](TOOLKIT-CELL-HIGHLIGHT-SCALE-38.md): Selected-cell outline offset on scaled displays
- [TOOLKIT-INCLUSION-PACKAGE-38](TOOLKIT-INCLUSION-PACKAGE-38.md): CHIM inclusion metadata omitted from Toolkit packaging rules
- [TOOLKIT-TEXT-ENCODING-38](TOOLKIT-TEXT-ENCODING-38.md): Toolkit labels contain corrupted Unicode characters
- UI-ACCEPT-29 (no report page): Character selection lacks a visible OK button
- [UI-DEATH-DAMAGE-TINT-38](UI-DEATH-DAMAGE-TINT-38.md): Lava damage tint also colours the death menu and selection
- [UI-ICONS-INVENTORY-42](UI-ICONS-INVENTORY-42.md): Inventory rows show icons only for the few staged items, squeezed 32 to 14 pixels; no magic or equipped backdrops
- [UI-INVENTORY-FONT-TABS-42](UI-INVENTORY-FONT-TABS-42.md): Inventory categories use the console font as plain text instead of the original Morrowind font on button tabs
- [UI-INVENTORY-HEADING-CENTRE-42](UI-INVENTORY-HEADING-CENTRE-42.md): The Inventory heading text is not vertically centred in its bar
- [UI-INVENTORY-LAYOUT-40](UI-INVENTORY-LAYOUT-40.md): Inventory text overlaps fields and footer; preview initially faces away
- [UI-INVENTORY-ORIGINAL-LAYOUT-42](UI-INVENTORY-ORIGINAL-LAYOUT-42.md): The inventory lacks the original encumbrance bar, armour rating and item icon grid
- [UI-INVENTORY-PREVIEW-GAP-41](UI-INVENTORY-PREVIEW-GAP-41.md): Inventory shows 'Character preview unavailable': a fixed 2 MiB memory guard refuses the 128 KB pose model in Seyda Neen
- [UI-INVENTORY-PREVIEW-STILL-42](UI-INVENTORY-PREVIEW-STILL-42.md): The inventory character is drawn live and turns instead of being a still picture
- [UI-KEY-HELP-STALE-38](UI-KEY-HELP-STALE-38.md): Key help exposes raw actions and uses a sparse outdated layout
- UI-MAP-PLAYER-ARROW-51 (no report page): Requested: the map shows the player as the original s arrow that turns with the player, not a crosshair
- [UI-MENU-LOGO-32](UI-MENU-LOGO-32.md): The menu logo has a line above the name and reddish-pink letters instead of gold
- UI-OPTIONS-WRAP-29 (no report page): Setup selection wraps despite a bounded scrollbar
- UI-PALETTE-NO-WHITE-48 (no report page): The game palette has no white: a White crosshair draws as the console ink cream (238,221,170)
- [UI-STATS-WINDOW-48](UI-STATS-WINDOW-48.md): No Stats window (attributes, skills, health/magicka/fatigue) and no Magic window: the original's P and O windows
- [UI-WINDOW-TITLE-BAR-42](UI-WINDOW-TITLE-BAR-42.md): Menu windows lack the original title bar (tiled frame with the window name on a dark plaque)
- [WAIT-NOCLIP-MESSAGE-32](WAIT-NOCLIP-MESSAGE-32.md): Wait refusal names registration, dry ground and speech together instead of the reason that applied (noclip)
- [WORLDMAP-LAVA-MISMATCH-36](WORLDMAP-LAVA-MISMATCH-36.md): The in-game map shows a lava band in Molag Amar where the world has grass and no lava

<!-- END GENERATED CATEGORY -->
