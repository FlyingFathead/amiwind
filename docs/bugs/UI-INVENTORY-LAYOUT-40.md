# UI-INVENTORY-LAYOUT-40: Inventory text overlaps fields and footer; preview initially faces away

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 3 times; something has to be done

- Reported with v0.0.40-dev1 at 2026-10-14 (time not recorded): Native first-open screenshot and two supplied crops show field/footer overlap; source repair awaits independent target/native verification.
- Reported with v0.0.40-dev1 at 2026-10-14 (time not recorded): Further playtest crop shows a rigid inventory standing pose. Dedicated original inventory posture remains open; scrollbar source checks do not verify posture.
- Reported with v0.0.40-dev2 at 2026-10-14 (time not recorded): Native preview first refused missing model allowances; corrected table restores male Nord unarmed/sword/shield previews and close/reopen. Broader visuals and appearance remain open.

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 14 October 2026, in v0.0.40-dev1 |
| Where | Full-screen inventory: item fields, details/footer, name header and character preview |
| Reproduction | once |
| Duplicate of | no |
| Persists in | v0.0.40-dev1 (last seen) |
| Severity | medium: Overlapping text obscures names and controls; the initial preview faces away. No item loss is established. |
| Family | Menus, HUD, map screen and text (`ui-text`) |
| Playtest version | v0.0.40-dev1 |
| From commit | source 7a783e0, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM 0.2.0, engine unknown, world format unknown |
| Unknown because | Native executable SHA-256 and screenshot binding are retained privately; engine commit and CHIM world identity are not separately established. |
| Build note | Native diagnostic inventory run; no package or acceptance claim. |
| Platform or emulator | FS-UAE native Amiga diagnostic |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.42 (17 October 2026)._

<!-- contents start -->
## Contents

- [PERSISTING: reported 3 times; something has to be done](#persisting-reported-3-times-something-has-to-be-done)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Latest original-reference requirements, 14 October 2026](#latest-original-reference-requirements-14-october-2026)
- [Title content and separate stats panel, 14 October 2026](#title-content-and-separate-stats-panel-14-october-2026)
- [Bottom control-hint margin follow-up, 14 October 2026](#bottom-control-hint-margin-follow-up-14-october-2026)
- [Inset control rows source follow-up, 14 October 2026](#inset-control-rows-source-follow-up-14-october-2026)
- [Right scrollbar source follow-up, 14 October 2026](#right-scrollbar-source-follow-up-14-october-2026)
- [Dedicated inventory pose source follow-up, 14 October 2026](#dedicated-inventory-pose-source-follow-up-14-october-2026)
- [Scoped native inventory observation, 14 October 2026](#scoped-native-inventory-observation-14-october-2026)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Symptom

Native playtesting shows item names painted across their list fields and icons,
while the details/status rows overlap the footer and its controls. The initial
character preview faces away from the viewer. The panel is difficult to read.
No inventory ownership loss is established by these screenshots.

The same run also shows unavailable catalogue details and raw record IDs. That
lookup failure is [INVENTORY-CATALOG-LOOKUP-40](INVENTORY-CATALOG-LOOKUP-40.md),
not proof that a layout repair restores item metadata or actions.

## Where

The full-screen inventory in the v0.0.40-dev1 native diagnostic, on first open:
item names, quantity/detail/status fields, footer, character-name header and
initial portrait orientation. Original native pixels and the two supplied crops
are retained privately; they are not public repository assets.

## How it happened

The existing AmiQuake-based UI helper `AW_UITextBox` centres text using its glyph
width and visible vertical bounds. Its rectangle is alignment geometry, not a
clip region. Inventory fields used it with strings wider or taller than their
available field. The catalogue failure exposes long record IDs, making the
overflow especially visible. Fixing lookup alone would not bound long valid
item names. The initial preview angle was zero, which presents the back of the
current body model in this camera setup.

## Why it was not caught

Earlier inventory checks exercised transactions, metadata and preview drawing,
but did not establish readable bounded fields in the exact native first-open
view. Source compilation and nonvisual checks did not prove that the chosen
font fit at 320x200 or that the initial preview faced the viewer.

## Reproduction

Open inventory with I in the v0.0.40-dev1 diagnostic. Inspect the first-open
portrait and the list containing long book/directions IDs. Check names against
icon and quantity columns, then inspect the details/status rows and footer.
The native screenshot and two playtest crops reproduce this layout failure.
Repeat with long valid names after catalogue lookup is repaired, a long player
name, each category, context actions, quantities and different font settings.
The latter checks remain required, not completed reproduction coverage.

## Repair

The proposed source change keeps the original-art frame and existing modal.
It uses console-derived 3x5 glyphs for bounded inventory fields, truncates long
strings with an ellipsis, gives the player name a full-width header and starts
the portrait at a half-turn. It reuses the engine's UI/text and existing alias
preview machinery rather than adding another rendering system.

This is a source candidate. It must not hide unsupported metadata/actions or
claim the separate catalogue lookup is fixed. Four affected checks pass; the full target build, new native
capture and original-reference comparison remain pending.

## Verification

The original native screenshot and supplied crops were visually inspected;
source inspection confirms that `AW_UITextBox` centres without clipping.
Private evidence binds the diagnostic source, executable and image hashes.
Integration reports four affected checks passing for the proposed source repair;
this is scoped automated evidence, not repaired native acceptance.
No repaired native image, package readback, full appearance coverage or gameplay
acceptance is established here. The issue remains open with no fixed version.
CHIM converted, audited, native-checked and packaged counts are unchanged.

## Prevention

Exercise field widths and vertical bounds with long actual names and IDs,
maximum quantities, unavailable metadata, context menus, a long player name and
each supported font. Check truncation, footer legibility and initial front view
at native 320x200. Retain a fresh actual-game screenshot of the repaired exact
build and a matched original comparison before claiming visual acceptance.

## Latest original-reference requirements, 14 October 2026

The subsequent exact native diagnostic now displays selected actual item names,
icons and equipped sword/shield appearance. This establishes that limited
catalogue/equipment observation, not complete layout or appearance acceptance.
The maintainer still finds the character-preview posture unlike the original.

Source comparison confirms the posture gap: OpenMW InventoryPreview::update
selects the dedicated inventoryhandtohand or inventory-plus-weapon long
animation group and fixes its pose time at zero. The current runtime
AW_ViewInventoryBody returns the live body frame or ordinary idle. Rotating that
body does not supply the original inventory pose. Dedicated original pose
references and drag-to-character requirements remain planned work; the latest
maintainer feedback finds the listing readable but still requires original
Morrowind/OpenMW comparison.

The original Steel Longsword preview uses inventoryweapononehand; original
preview setup forces weapon visibility and suppresses a left-hand item for
two-handed weapons. The current orthographic bounds-fit camera also differs
from the original preview camera; matched visual comparison remains required.
A persistent list-versus-icon-grid View option is also planned, sharing actual
selection and actions rather than copying inventory state.

Final UI artwork must be converted from locally supplied original game data
and stay outside public source. The fixed right corner mirrors the left border
pattern; no resize or movable-window corner control is wanted. This requirement
does not turn authored interim HUD placeholders into original-asset acceptance.

Further original-reference requirements are golden title/tab frames and font,
a full-screen frame without movable-window corner decoration, actual
encumbrance (carried weight/capacity) and Armor rating, and a right-side
mouse-operable vertical scrollbar with keyboard access. These are planned
improvements, not completed UI/game-logic coverage.

Equipped items additionally need the maintainer's requested thin golden outline.
That outline, the dedicated inventory pose and camera refinement remain
planned and unimplemented.

The next layout refinement must reproduce Morrowind's inset black character-name
plaque within the golden top border and use the original inventory-specific
preview posture. A full-width name label or a simple camera half-turn does not
establish those original details. These are planned improvements; this
documentation update implements neither the plaque nor a new posture.
Compare the actual original and candidate at matched appearance/pose and
AGA resolution before claiming visible parity or maintainer acceptance.

## Title content and separate stats panel, 14 October 2026

The latest requirement clarifies the inventory heading: the original inset
title plaque must read literal "Inventory". The planned separate attributes/
stats panel carries the actual player-name header. Do not replace the inventory
title with that name. The full-screen black/paused stats panel and rebindable
gameplay O action remain planned; current inventory-modal O sorting stays.
Installed OpenMW 0.51 and the current gameplay keymap leave O unassigned;
the original base-game manual default is unverified.

## Bottom control-hint margin follow-up, 14 October 2026

A further supplied inventory image shows the control hint crowded against the
bottom edge. The observation concerns spacing and readability; it does not
establish item loss, broken input or a diagnosed clipping cause. The exact
running executable cannot be identified from the image alone.

Reserve a readable hint/status area inside the bottom border with a visible
inset margin. Wrap or otherwise accommodate the controls without overlapping
item details or shrinking them below a readable native size. Check the final
layout at supported AGA resolutions with long names, categories and open
context actions, using actual unedited game views.

The previously requested original title/tab frames and font, dedicated preview
pose/camera, equipped-item outline, encumbrance/Armor readouts and right
scrollbar remain unfinished design work. Full icons and expanded interactions
remain separately tracked under
[UI-INVENTORY-INTEGRATION-40](UI-INVENTORY-INTEGRATION-40.md) and the
[inventory roadmap](../INVENTORY.md). This new observation completes none of
those features and does not change CHIM coverage or accept the layout.

## Inset control rows source follow-up, 14 October 2026

The unreleased follow-up uses the existing AmiQuake-derived modal, bounded
console glyphs and actual item actions. Six item rows share their draw and hit
geometry. Details, two status lines and two control lines occupy separate
regions; footer glyphs end at row 188 before the border begins at 192.
The 168-pixel character preview, 16-pixel icons and current glyph size remain.
Context actions stay above the controls. Clicking the navigation hint no longer
closes the modal; only the displayed close label does. The heading now reads
literal "Inventory"; the original inset plaque and artwork remain unfinished.

The executable host fixture rejects the old footer bounds and passes the new
bounds with long names, unavailable actions, a wrapped status, real context
selection/equip/drop and the close/navigation targets. The existing map/journal
fixture also passes. Status strings beyond the two-line capacity retain an
explicit ellipsis; arbitrary-length text is not claimed to fit. Ownership and
refused-drop checks remain intact. These are source/host checks, not an Amiga
build, matched OpenMW/FS-UAE observation or visual acceptance. The issue stays
open, delivered dev1 is unchanged, and CHIM coverage is unchanged.


## Right scrollbar source follow-up, 14 October 2026

The unreleased v0.0.40-dev2 source reuses AmiQuake-based `AW_UIScrollbar`
and `AW_UIScrollHit`, already used by the journal. Lists longer than six rows
reserve the right rail; shorter lists retain their original column width.
Arrow clicks step once and the inner rail supports dragging. A selected item
stays visible so Equip and Drop refer to the displayed list. Scrolling does
not change carried counts, equipment, condition or save state.

Mouse release, focus loss, category changes, keyboard actions and panel close
cancel dragging. Sanitized executable checks exercise those transitions,
empty/six/twelve-item lists, row bounds and real equip identity. The same
fixture rejects the previous source because it lacks the scrollbar. Existing
map/journal and actual shared UI-helper checks also pass. The full suite and
Amiga/FPU target subsequently passed; counts are recorded below. Matched
original/native comparison and packaging remain pending.
This does not accept the overall layout or mark a first fixed version.

Further dev1 playtesting supplied a crop with three equipped clothing rows,
no visible equipped weapon and a rigid standing inventory preview. It
reconfirms the dedicated-pose gap above; the crop alone does not establish the
race, exact binary or all equipped slots. Scrollbar and spacing changes do not
repair the preview pose. CHIM coverage is unchanged.

## Dedicated inventory pose source follow-up, 14 October 2026

The unreleased v0.0.40-dev2 source adds a separate ten-frame alias for each
race/sex body: unarmed plus the nine supported original melee weapon types.
The converter samples the original inventory animation START keys, preferring
the matching group and using the original one-/two-handed fallback when needed.
Human, female and beast animation data resolve all ten poses and their weapon
and shield matrices. All twenty race/sex bodies have now converted, each with
ten inventory frames. Independent readback checks model structure, exact hashes,
frame names, triangle indices and finite attachment rows. Together the models
and tags occupy 8,286,220 bytes. This is conversion evidence, not native visual
acceptance or a shipped asset set.

The modal selects that pose from actual right-hand equipment and hides the
left-hand attachment for two-handed weapons. It reuses AmiQuake's alias model
cache and existing frame/tag representation without advancing the gameplay
animation clock or replacing locomotion frames. One optional portrait model is
released on panel close. Existing alias-size and free-hunk admission limits
remain; missing, malformed or unsupported poses refuse the preview rather than
pretending ordinary idle is the original pose.

Six converter checks pass, including real ten-frame model/tag serialization.
The sanitized runtime fixture rejects the old live-frame behavior and passes
unarmed/melee selection, attachment alignment, two-handed left hiding, stable
world frame/clock, cache reload, close and missing/low-memory refusal cases.
The exact implementation completes the full suite: 4,086 tests, comprising
4,080 passes, three Windows-only skips and three expected failures tracked in
[TEST-CENSUS-CONTRACTS-40](TEST-CENSUS-CONTRACTS-40.md), with no unexpected
failures or errors. The Amiga/FPU build also passes. Matched OpenMW/FS-UAE
visuals remain pending. No target RAM, speed or image-quality improvement is
measured; test and conversion success do not establish those results.

Torch preview retains its existing live companion; its dedicated left-arm
layer is unfinished. Ranged equipment is outside the supported melee scope.
Bodies still use starting clothes and the first head/hair for the selected
race/sex; full selected appearance and changing worn body parts remain pending.
Original UI artwork, camera parity and the complete layout are not accepted.
This source follow-up remains OPEN, with no first fixed version or shipment.
Delivered dev1 and CHIM coverage are unchanged.

## Scoped native inventory observation, 14 October 2026

The first unreleased diagnostic omitted the matching model-budget entries for
the new inventory companions. The native loader correctly refused the oversized
model and the preview was unavailable. Regenerating the table with the normal
builder preserved existing allowances and added twenty byte-matching entries;
the engine and model bytes were unchanged.

On the corrected candidate, physical I opens the dedicated unarmed male Nord
preview. Tab and Enter equip the diagnostic steel longsword, changing the pose
and showing its attachment; equipping the steel shield shows it on the left arm.
Closing and reopening retains both. The original OpenMW reference matches the
baked race, sex, head/hair, starting clothes and equipment. Resolution, framing
and world camera differ. This is a scoped posture/attachment observation,
not universal image-quality or appearance acceptance.

The first refusal remains a failed observation. The corrected observation does
not verify all twenty appearances, torch posture, selected appearance, changing
clothes, pause, save reload, target memory or performance. Those checks and
remaining UI work stay open. Delivered dev1 and CHIM coverage are unchanged.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Menus, HUD, map screen and text (`ui-text`). Menus, HUD, map screen, fonts and messages. See [families](README.md#families).

- AW-20260928-09 (no report page): Papers unreadable
- AW-20260928-13 (no report page): New Game confirmation defaults to Cancel
- AW25-03 (no report page): Map marker reported stale; HUD lacked global/local positions
- CHAR-CONFIRM-BORDER-29 (no report page): Character Go back / Choose actions lack OK-style frames
- [CHIM-REGION-DOORS-NO-PROMPT-42](CHIM-REGION-DOORS-NO-PROMPT-42.md): Doors in CHIM region cells show no entrance at all (no prompt, not even Interior unavailable), e.g. every door in Khuul
- [FONT-BITMAP-INDEX-32](FONT-BITMAP-INDEX-32.md): Bitmap font path keeps the .fnt glyph order; the engine indexes by game byte (wrong characters)
- [FONT-TTF-COVERAGE-32](FONT-TTF-COVERAGE-32.md): Magic Cards TrueType font silently lacks many characters and replaces ASCII brackets with ornaments
- [HUD-DEBUG-STRIP-OVER-BOXES-42](HUD-DEBUG-STRIP-OVER-BOXES-42.md): Debug coordinate strip's black fill and text cover the weapon and magic boxes
- [HUD-ENEMY-BAR-COLOUR-33](HUD-ENEMY-BAR-COLOUR-33.md): The enemy health bar draws orange, not yellow
- [HUD-NOTIFY-OVERLAP-31](HUD-NOTIFY-OVERLAP-31.md): Console messages print over the location title
- [HUD-STATS-29](HUD-STATS-29.md): Health uses fixed 100; other bars hardcoded full
- MAP-FOCUS-DRAG-29 (no report page): Map or journal keeps dragging after window focus returns
- MAP-MARKER-29 (no report page): Requested: click to place a user map marker
- MAP-REG-01 (no report page): In-Game map mode hid settlement markers (regression)
- MAP-RIGHT-DRAG-29 (no report page): Advertised right-drag does not pan teleport map
- MAP-SPOTS-28 (no report page): In-game map screen has white/yellow spots
- [NOCLIP-BOB-DEFAULT-42](NOCLIP-BOB-DEFAULT-42.md): Head bob still on in noclip mode by default, although the noclip bob was set to off by default
- [NPC-DREAMER-GREETING-DEFAULT-42](NPC-DREAMER-GREETING-DEFAULT-42.md): Dreamers (Sixth House sleepers) give a default greeting instead of their own Sixth House greeting
- OPTIONS-CROSSHAIR-STYLE-48 (no report page): Requested: crosshair colour and shape in Options, and Options in framed categories, full screen
- OPTIONS-MOUSE-SENSITIVITY-48 (no report page): Requested: mouse sensitivity in Options and the console (the default is too fast for some players)
- [PHOTO-DEBUG-STRIP-33](PHOTO-DEBUG-STRIP-33.md): Photo mode with Ctrl+H: the coordinate strip blacks out only from x=88, leaving the bottom-left corner of the view
- [PHOTO-GALLERY-TEXT-33](PHOTO-GALLERY-TEXT-33.md): Photo mode leaves test-room and gallery instruction text over the view
- [PLACE-NAMES-INTERIOR-31](PLACE-NAMES-INTERIOR-31.md): Location label has no place name inside interiors
- [TOOLKIT-CELL-HIGHLIGHT-SCALE-38](TOOLKIT-CELL-HIGHLIGHT-SCALE-38.md): Selected-cell outline offset on scaled displays
- [TOOLKIT-INCLUSION-PACKAGE-38](TOOLKIT-INCLUSION-PACKAGE-38.md): CHIM inclusion metadata omitted from Toolkit packaging rules
- [TOOLKIT-TEXT-ENCODING-38](TOOLKIT-TEXT-ENCODING-38.md): Toolkit labels contain corrupted Unicode characters
- UI-ACCEPT-29 (no report page): Character selection lacks a visible OK button
- [UI-DEATH-DAMAGE-TINT-38](UI-DEATH-DAMAGE-TINT-38.md): Lava damage tint also colours the death menu and selection
- [UI-ICONS-INVENTORY-42](UI-ICONS-INVENTORY-42.md): Inventory rows show icons only for the few staged items, squeezed 32 to 14 pixels; no magic or equipped backdrops
- [UI-INVENTORY-FONT-TABS-42](UI-INVENTORY-FONT-TABS-42.md): Inventory categories use the console font as plain text instead of the original Morrowind font on button tabs
- [UI-INVENTORY-HEADING-CENTRE-42](UI-INVENTORY-HEADING-CENTRE-42.md): The Inventory heading text is not vertically centred in its bar
- [UI-INVENTORY-ORIGINAL-LAYOUT-42](UI-INVENTORY-ORIGINAL-LAYOUT-42.md): The inventory lacks the original encumbrance bar, armour rating and item icon grid
- [UI-INVENTORY-PREVIEW-GAP-41](UI-INVENTORY-PREVIEW-GAP-41.md): Inventory shows 'Character preview unavailable': a fixed 2 MiB memory guard refuses the 128 KB pose model in Seyda Neen
- [UI-INVENTORY-PREVIEW-STILL-42](UI-INVENTORY-PREVIEW-STILL-42.md): The inventory character is drawn live and turns instead of being a still picture
- [UI-KEY-HELP-STALE-38](UI-KEY-HELP-STALE-38.md): Key help exposes raw actions and uses a sparse outdated layout
- [UI-MENU-LOGO-32](UI-MENU-LOGO-32.md): The menu logo has a line above the name and reddish-pink letters instead of gold
- UI-OPTIONS-WRAP-29 (no report page): Setup selection wraps despite a bounded scrollbar
- UI-PALETTE-NO-WHITE-48 (no report page): The game palette has no white: a White crosshair draws as the console ink cream (238,221,170)
- [UI-STATS-WINDOW-48](UI-STATS-WINDOW-48.md): No Stats window (attributes, skills, health/magicka/fatigue) and no Magic window: the original's P and O windows
- [UI-WINDOW-TITLE-BAR-42](UI-WINDOW-TITLE-BAR-42.md): Menu windows lack the original title bar (tiled frame with the window name on a dark plaque)
- [WAIT-NOCLIP-MESSAGE-32](WAIT-NOCLIP-MESSAGE-32.md): Wait refusal names registration, dry ground and speech together instead of the reason that applied (noclip)
- [WORLDMAP-LAVA-MISMATCH-36](WORLDMAP-LAVA-MISMATCH-36.md): The in-game map shows a lava band in Molag Amar where the world has grass and no lava

Related bugs in other categories:

- [UI-INVENTORY-INTEGRATION-40](UI-INVENTORY-INTEGRATION-40.md): Inventory integration and safe world placement remain incomplete

<!-- END GENERATED CATEGORY -->
