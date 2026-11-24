# HUD-STATS-29: Health uses fixed 100; other bars hardcoded full

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 6 times; something has to be done

- Reported with v0.0.40-dev1 at 2026-10-14 (time not recorded): Original HUD reference requires actual weapon/fists and selected spell/enchantment boxes with applicable condition/charge indicators; no off-hand guess.
- Reported with v0.0.40-dev1 at 2026-10-14 (time not recorded): Opening HUD timing queried. Source audit finds missing staged channel checks; actual weapon model is a separate gate. Native reproduction and repair pending.
- Reported with v0.0.40-dev2 at 2026-10-14 (time not recorded): Dev2 source restores staged HUD channels and paper-pickup fighting. Seven focused checks pass; full suite, target and native pending. Map/menu gates and inventory pose remain separate.
- Reported with v0.0.40-dev2 at 2026-10-14 (time not recorded): Original and candidate show paper pickup enabling fists before the hall guard; reading alone does not. Scoped HUD observations retained; failed exit gate and full-route checks remain separate.
- Reported with v0.0.42-dev1 at 2026-10-17 01:58 +0300: owner: the weapon and magic boxes at the bottom of the HUD are still placeholders (fist, dash) and look bad
- Reported with v0.0.61 at 2026-11-07 03:39 +0200: Release image: in a game started from the map menu the player's sheet reads health 100 of a maximum of 55 (aw_magicfx spell list and the combat report "You: health 100/55"), in three sessions.

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

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-10-05: HUD-STATS-29: healthy character appears partly depleted (OPEN) (part 1 of 2): Source-candidate update: The source candidate now uses independent stat current/max values, with live single-player health authoritative where applicable and ...
- 2026-10-05: HUD-STATS-29: healthy character appears partly depleted (OPEN) (part 2 of 2): Cause: `AW_UIHud` divides live health by fixed 100 rather than the character's maximum.
- 2026-10-14: seen again in v0.0.40-dev1: Original HUD reference requires actual weapon/fists and selected spell/enchantment boxes with applicable condition/charge indicators; no off-hand guess.
- 2026-10-14: seen again in v0.0.40-dev1: Opening HUD timing queried.
- 2026-10-14: seen again in v0.0.40-dev2: Dev2 source restores staged HUD channels and paper-pickup fighting.
- 2026-10-14: seen again in v0.0.40-dev2: Original and candidate show paper pickup enabling fists before the hall guard; reading alone does not.
- 2026-10-14: UI-INVENTORY-INTEGRATION-40: scoped native equipment: UI-INVENTORY-INTEGRATION-40/INVENTORY-CATALOG-LOOKUP-40: actual names/icons, equip, modal pause and Russula persistence scoped; missing resources separate.
- 2026-10-17: HUD-STATS-29: original weapon and magic boxes: HUD-STATS-29, persisting (reported a fifth time by the maintainer: the boxes were placeholders).
- 2026-10-17 01:58 +0300: seen again in v0.0.42-dev1: owner: the weapon and magic boxes at the bottom of the HUD are still placeholders (fist, dash) and look bad
- 2026-11-07 03:39 +0200: seen again in v0.0.61: Release image: in a game started from the map menu the player's sheet reads health 100 of a maximum of 55 (aw_magicfx spell list and the combat report "You: health 100/55"), in three sessions.

<!-- END GENERATED TIMELINE -->

_Last updated with AmiWind v0.0.42 (17 October 2026)._

<!-- contents start -->
## Contents

- [PERSISTING: reported 6 times; something has to be done](#persisting-reported-6-times-something-has-to-be-done)
- [Timeline](#timeline)
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

- [ARRIVAL-LONG-FRAME-DEV6-59](ARRIVAL-LONG-FRAME-DEV6-59.md): Arriving in Seyda Neen, the first frame of play lasts about 13 to 15 seconds; v0.0.59-dev6 test sessions stopped on it as a stall
- [AW-20260928-09](AW-20260928-09.md): Papers unreadable
- [AW-20260928-13](AW-20260928-13.md): New Game confirmation defaults to Cancel
- [AW25-03](AW25-03.md): Map marker reported stale; HUD lacked global/local positions
- [BARTER-TRADE-WINDOW-MISSING-67](BARTER-TRADE-WINDOW-MISSING-67.md): Missing: the original trade window: an offer the player changes, a running total of both sides, the merchant gold limit and restocking, haggling
- [BLANK-PAPER-READ-60](BLANK-PAPER-READ-60.md): A blank sheet of paper offers Read although it has no text
- [BOOK-PICTURE-MARKER-SHOWN-67](BOOK-PICTURE-MARKER-SHOWN-67.md): A book shows a line with a literal picture marker where the original draws an image (seen in a book on the stars, page 3 of 15)
- BOOK-TEXT-MACROS-58 (no report page): A book read where it lies shows the text defines as written (Name: %PCName Race: %PCRace Class: %PCClass)
- CHAR-CONFIRM-BORDER-29 (no report page): Character Go back / Choose actions lack OK-style frames
- [CHARGEN-ABILITY-DESCRIPTIONS-65](CHARGEN-ABILITY-DESCRIPTIONS-65.md): The birthsign and race menus do not show what an ability or a special power does
- [CHIM-REGION-DOORS-NO-PROMPT-42](CHIM-REGION-DOORS-NO-PROMPT-42.md): Doors in CHIM region cells show no entrance at all (no prompt, not even Interior unavailable), e.g. every door in Khuul
- [CLASS-LIST-LAYOUT-62](CLASS-LIST-LAYOUT-62.md): The class choice window runs its lists together without separating lines
- [CONTAINER-OWNED-PROMPT-WORDING-67](CONTAINER-OWNED-PROMPT-WORDING-67.md): An owned container's aim hint reads "E: Steal" instead of "E: Open" in red, and the container window's "E: Steal" is not red
- CONTAINER-STRIP-REDRAW-COST-59 (no report page): The container strip redraws the whole screen every frame: about 17 fps while it is open
- [CONTAINER-STRIP-TAKE-STALL-59](CONTAINER-STRIP-TAKE-STALL-59.md): A take or put in the container strip can hold the game for seconds
- [CONTAINER-TAKE-NO-CONFIRM-62](CONTAINER-TAKE-NO-CONFIRM-62.md): Taking an item from a container shows only its name; nothing says it was taken
- [CRIME-RELEASE-LINE-CUT-62](CRIME-RELEASE-LINE-CUT-62.md): The release from jail shows only its first three lines: the skills that changed are cut off
- [DBG-HELP-PAGER-TITLE-SPLIT-67](DBG-HELP-PAGER-TITLE-SPLIT-67.md): The debug command list can end a page on a group's title, its separator line opening the next page
- [DBG-MWSCRIPT-SILENT-56](DBG-MWSCRIPT-SILENT-56.md): dbg mwscript on prints nothing: the switch gives no answer, so it looks as if it did nothing
- [DBG-TP-TYPED-PLACE-NOT-FOUND-67](DBG-TP-TYPED-PLACE-NOT-FOUND-67.md): dbg tp ghostgate says the place is not found and sends the player to Balmora; the list box reaches Ghostgate but also prints not found
- [DIALOGUE-ARROWS-MOVE-POINTER-60](DIALOGUE-ARROWS-MOVE-POINTER-60.md): In the dialogue window the Up and Down keys move the mouse pointer instead of the topic selection
- [DIALOGUE-BACKDROP-HUD-60](DIALOGUE-BACKDROP-HUD-60.md): The status bars stay visible behind the dialogue screen
- [DIALOGUE-CHOICE-LINE-UNMARKED-60](DIALOGUE-CHOICE-LINE-UNMARKED-60.md): An answer picked from a dialogue choice is printed like the NPC's text, not as the player's line
- [DIALOGUE-CLOSE-FRAME-FREEZE-59](DIALOGUE-CLOSE-FRAME-FREEZE-59.md): The talk window takes seconds to open
- [DIALOGUE-EXHAUSTED-TOPICS-NOT-SEEN-67](DIALOGUE-EXHAUSTED-TOPICS-NOT-SEEN-67.md): Incomplete: a topic whose answer is already in the journal is drawn greyed, but it has not been seen in a built game
- [DIALOGUE-GOODBYE-BLOCKED-HINT-67](DIALOGUE-GOODBYE-BLOCKED-HINT-67.md): While an answer waits for Continue, Goodbye does nothing and nothing shows why; requested: Goodbye and the topics greyed out, and a box "Continue the conversation first." when Goodbye is chosen
- [DIALOGUE-GOODBYE-ONLY-NOT-SEEN-67](DIALOGUE-GOODBYE-ONLY-NOT-SEEN-67.md): Incomplete: after a result script calls Goodbye only the Goodbye button is left in the window, not seen in a built game
- [DIALOGUE-ITEM-NOTICE-MISSING-61](DIALOGUE-ITEM-NOTICE-MISSING-61.md): An item a dialogue answer gives or takes shows no notice while talking
- DIALOGUE-LINK-MARK-AS-DEFINE-58 (no report page): Dialogue links lose their first two letters to a number, and the link itself, since the text defines table
- [DIALOGUE-LINKS-62](DIALOGUE-LINKS-62.md): The blue topic words in dialogue text cannot be clicked, a word is highlighted inside a longer word, and asking about a dead person gives "Who?"
- [DIALOGUE-MSGBOX-BEHIND-60](DIALOGUE-MSGBOX-BEHIND-60.md): Message boxes raised during a conversation open behind the dialogue window
- DIALOGUE-OPEN-STALL-58 (no report page): Opening a conversation hangs the game for many seconds
- [DIALOGUE-PADDING-UNEVEN-23](DIALOGUE-PADDING-UNEVEN-23.md): Two dialogue rows had uneven vertical spacing
- [EXTRAS-MENU-54](EXTRAS-MENU-54.md): Requested: an Extras choice on the main menu that opens what the game holds: the arena, the dance scenes, the in-game videos, later a library of every book
- [FOCUS-BOX-TWO-AT-ONCE-59](FOCUS-BOX-TWO-AT-ONCE-59.md): Two item boxes at once: the box of the item aimed at before stays while the next item's box is drawn below the view
- FOCUS-BOX-UNDRAWN-ITEMS-58 (no report page): The focus box showed for room items that the room does not draw, and the activate key then took nothing
- [FOCUS-NPC-OVERRIDES-ITEM-62](FOCUS-NPC-OVERRIDES-ITEM-62.md): Trying to take an item near a character talks to the character instead: the nearby character overrides the item under the crosshair
- [FOCUS-REACH-ITEM-ORIGIN-58](FOCUS-REACH-ITEM-ORIGIN-58.md): The focus box measures the reach to an item's origin, not to its nearer surface as the original does
- [FOCUS-ROWS-WINDOW-OVERFLOW-66](FOCUS-ROWS-WINDOW-OVERFLOW-66.md): In the busiest outdoor places some placed things have no focus row
- [FONT-BITMAP-INDEX-32](FONT-BITMAP-INDEX-32.md): Bitmap font path keeps the .fnt glyph order; the engine indexes by game byte (wrong characters)
- [FONT-TTF-COVERAGE-32](FONT-TTF-COVERAGE-32.md): Magic Cards TrueType font silently lacks many characters and replaces ASCII brackets with ornaments
- [HUD-DEBUG-STRIP-OVER-BOXES-42](HUD-DEBUG-STRIP-OVER-BOXES-42.md): Debug coordinate strip's black fill and text cover the weapon and magic boxes
- [HUD-ENEMY-BAR-COLOUR-33](HUD-ENEMY-BAR-COLOUR-33.md): The enemy health bar draws orange, not yellow
- [HUD-FPS-NEEDS-DBG-HUD-56](HUD-FPS-NEEDS-DBG-HUD-56.md): dbg fps shows nothing unless dbg hud is on; with it, the box sits over the view near the top left
- HUD-INTERIOR-CLOCK-CUT-54 (no report page): The dbg hud line GLOBAL XYZ: unavailable (interior) is so long that the clock is cut off
- [HUD-NOTIFY-OVERLAP-31](HUD-NOTIFY-OVERLAP-31.md): Console messages print over the location title
- [HUD-TEXTS-OVERLAP-67](HUD-TEXTS-OVERLAP-67.md): Two texts are drawn on top of each other in the HUD: the name of the aimed character and the place name
- HUD-WEAPON-BOX-EMPTY-59 (no report page): HUD weapon box stays empty after equipping a weapon from the console
- [INFO-BOX-TEXT-CUT-62](INFO-BOX-TEXT-CUT-62.md): The name of an aimed door or object is drawn in a box over the view that cuts its text; before, the name was shown only below the view
- [INVENTORY-ARROWS-SCROLL-62](INVENTORY-ARROWS-SCROLL-62.md): The arrow keys do not move through any list window: dialogue topics, bartering, the inventory, containers and spells
- [INVENTORY-BURDEN-TEXT-UNREADABLE-61](INVENTORY-BURDEN-TEXT-UNREADABLE-61.md): The carried and maximum weight on the inventory burden bar cannot be read
- [INVENTORY-EQUIPPED-LABEL-67](INVENTORY-EQUIPPED-LABEL-67.md): An item the player already wears or holds still shows "E/Enter equip" in the inventory, and nothing marks it as equipped
- [INVENTORY-ITEM-INFO-67](INVENTORY-ITEM-INFO-67.md): Requested: an item information button in the inventory that opens a box with the item's properties, where the game data has them
- [INVENTORY-NO-ARMOR-RATING-61](INVENTORY-NO-ARMOR-RATING-61.md): The inventory window shows no armour rating under the character picture
- [INVENTORY-OPEN-WINDOW-NO-REFRESH-61](INVENTORY-OPEN-WINDOW-NO-REFRESH-61.md): An item given and worn through the console while the inventory window is open does not show in that window until it is opened again
- [INVENTORY-PREVIEW-STALE-61](INVENTORY-PREVIEW-STALE-61.md): The inventory character preview does not change when equipment is put on or taken off in the window
- [ITEM-ICONS-MISSING-62](ITEM-ICONS-MISSING-62.md): The container window shows clothing, armour, books, scrolls and potions as text without a picture, and the pictures it does show are small and sit in the corner of the slot, on a brown background
- [ITEM-VIEW-ENTER-UNEQUIPS-67](ITEM-VIEW-ENTER-UNEQUIPS-67.md): In the inventory's item information view, Enter unequips the item being viewed instead of only closing the view
- [JOURNAL-HYPERLINKS-QUEST-ENTRIES-67](JOURNAL-HYPERLINKS-QUEST-ENTRIES-67.md): Incomplete: the journal hyperlinks work on topic pages only: the quest entries (the dated pages) carry no link spans
- [JOURNAL-NOTICE-EMPTY-ENTRY-67](JOURNAL-NOTICE-EMPTY-ENTRY-67.md): Incomplete: the journal updated notice is shown for a new entry with empty text, where OpenMW skips it
- [JOURNAL-QUEST-ENTRIES-NOT-SEEN-67](JOURNAL-QUEST-ENTRIES-NOT-SEEN-67.md): Incomplete: the quests and their finished and restart marks in the journal book are not seen in a built game
- [JOURNAL-TOPIC-LETTER-INDEX-68](JOURNAL-TOPIC-LETTER-INDEX-68.md): The journal's Topics view lists every topic in one scrolling list instead of the original's A to Z letter index
- [JOURNAL-TOPIC-PAGES-VALUES-AT-READ-67](JOURNAL-TOPIC-PAGES-VALUES-AT-READ-67.md): Incomplete: the journal topic pages fill the %-values of an entry when the page is read, not when it was said
- [LEVEL-UP-MISSING-57](LEVEL-UP-MISSING-57.md): Requested: levelling as in the original: skills rise with use, the level-up box with its text and sound, attributes raised, the new values used by every check
- [LOOT-WINDOW-ITEM-PROPERTIES-60](LOOT-WINDOW-ITEM-PROPERTIES-60.md): Loot window does not show the selected item's type, weight and value
- [LOOT-WINDOW-LAYOUT-60](LOOT-WINDOW-LAYOUT-60.md): Loot window: key help cut off, item names clipped, buttons crammed against the frame
- [LORE-DATE-FORMAT-62](LORE-DATE-FORMAT-62.md): Game dates are printed as 18/08/427 instead of the original's form: day, month name, era and year
- [MADE-ITEM-NO-PICTURE-62](MADE-ITEM-NO-PICTURE-62.md): A made potion or a made enchanted item shows an empty picture in the inventory list
- [MAP-FOCUS-DRAG-29](MAP-FOCUS-DRAG-29.md): Map or journal keeps dragging after window focus returns
- [MAP-LOCAL-ROOM-PLAN-CHIM-ROOMS-68](MAP-LOCAL-ROOM-PLAN-CHIM-ROOMS-68.md): Inside a room the map opens on the World view instead of the room's plan in rooms built on the shared room store
- [MAP-MARKER-29](MAP-MARKER-29.md): Requested: click to place a user map marker
- [MAP-ORIGINAL-FEATURES-66](MAP-ORIGINAL-FEATURES-66.md): The map window lacks the original's map: the explored fog, the local map, the interior map and the place markers
- MAP-REG-01 (no report page): In-Game map mode hid settlement markers (regression)
- [MAP-RIGHT-DRAG-29](MAP-RIGHT-DRAG-29.md): Advertised right-drag does not pan teleport map
- [MAP-SPOTS-28](MAP-SPOTS-28.md): In-game map screen has white/yellow spots
- [MAP-WORLD-TAB-BLANK-67](MAP-WORLD-TAB-BLANK-67.md): The World tab of the in-game map draws no land: only the player arrow and the place markers show on a blank background
- [MENU-PALETTE-RED-CAST-68](MENU-PALETTE-RED-CAST-68.md): The map screen, the inventory and the item icons have a red cast since the scene palette change for ice and snow
- [MSGBOX-NO-CURSOR-62](MSGBOX-NO-CURSOR-62.md): The death message box shows no mouse cursor
- [NAMED-ACTIVATOR-FOCUS-66](NAMED-ACTIVATOR-FOCUS-66.md): Named objects such as beds and shrines show no name when looked at
- [NOCLIP-BOB-DEFAULT-42](NOCLIP-BOB-DEFAULT-42.md): Head bob still on in noclip mode by default, although the noclip bob was set to off by default
- [NPC-DREAMER-GREETING-DEFAULT-42](NPC-DREAMER-GREETING-DEFAULT-42.md): Dreamers (Sixth House sleepers) give a default greeting instead of their own Sixth House greeting
- [OPENING-QUOTE-OVERLAY-23](OPENING-QUOTE-OVERLAY-23.md): The first prophecy quote of the intro showed unreadable burned-in lettering again
- [OPENING-SPEECH-LEADING-DOTS-65](OPENING-SPEECH-LEADING-DOTS-65.md): A speech line in the opening starts with a long row of dots before its text
- [OPENING-TUTORIAL-KEYS-65](OPENING-TUTORIAL-KEYS-65.md): The opening's tutorial boxes name the original game's controls (right click for the menus) instead of AmiWind's keys
- OPTIONS-CROSSHAIR-STYLE-48 (no report page): Requested: crosshair colour and shape in Options, and Options in framed categories, full screen
- OPTIONS-MOUSE-SENSITIVITY-48 (no report page): Requested: mouse sensitivity in Options and the console (the default is too fast for some players)
- [PHOTO-CROSSHAIR-51](PHOTO-CROSSHAIR-51.md): In photo mode the crosshair stays: crosshair off and dbg crosshair off do nothing, and photo mode does not hide it by itself
- [PHOTO-DEBUG-STRIP-33](PHOTO-DEBUG-STRIP-33.md): Photo mode with Ctrl+H: the coordinate strip blacks out only from x=88, leaving the bottom-left corner of the view
- [PHOTO-GALLERY-TEXT-33](PHOTO-GALLERY-TEXT-33.md): Photo mode leaves test-room and gallery instruction text over the view
- [PICKUP-NAME-ONLY-BOX-67](PICKUP-NAME-ONLY-BOX-67.md): Picking up an item shows only the item name in a box
- [PLACE-NAMES-INTERIOR-31](PLACE-NAMES-INTERIOR-31.md): Location label has no place name inside interiors
- QUICKSAVE-NO-PROFILE-SILENT-57 (no report page): Quicksave says nothing when no character profile is chosen (a game started from the console with map), while quickload says why
- [RACE-MENU-OK-HIGHLIGHT-65](RACE-MENU-OK-HIGHLIGHT-65.md): The OK box of the character windows shows no highlight when the keys reach it
- RAM-WARNING-BOX-52 (no report page): Requested: under 32 MB of Fast RAM a WARNING message box for a few seconds before the AmiWind logo
- [SIGNPOST-NAMES-MISSING-65](SIGNPOST-NAMES-MISSING-65.md): Signposts do not show what they read when the player looks at them
- [STATS-WINDOW-COLOURS-UNTIL-LOAD-67](STATS-WINDOW-COLOURS-UNTIL-LOAD-67.md): Stats window draws a raised attribute almost black and the birthsign icons brown until a saved game is loaded
- [SUBTITLE-BOX-HIDES-STATS-63](SUBTITLE-BOX-HIDES-STATS-63.md): The box of a spoken line rises over the whole lower part of the screen and hides the stat bar
- [TOOLKIT-CELL-HIGHLIGHT-SCALE-38](TOOLKIT-CELL-HIGHLIGHT-SCALE-38.md): Selected-cell outline offset on scaled displays
- [TOOLKIT-INCLUSION-PACKAGE-38](TOOLKIT-INCLUSION-PACKAGE-38.md): CHIM inclusion metadata omitted from Toolkit packaging rules
- [TOOLKIT-TEXT-ENCODING-38](TOOLKIT-TEXT-ENCODING-38.md): Toolkit labels contain corrupted Unicode characters
- [TOOLKIT-WORLD-FORMAT-STALE-64](TOOLKIT-WORLD-FORMAT-STALE-64.md): The 3D Map Inspector cannot open a current CHIM open world (format 0.11)
- [TRADEHOUSE-LONG-FRAME-59](TRADEHOUSE-LONG-FRAME-59.md): In Arrille's Tradehouse one frame can last about 10 seconds, with or without the container strip open
- [TUTORIAL-BOX-SHOWN-TWICE-65](TUTORIAL-BOX-SHOWN-TWICE-65.md): After the papers the same tutorial box is shown twice in a row
- [UI-ACCEPT-29](UI-ACCEPT-29.md): Character selection lacks a visible OK button
- [UI-CHARGEN-CLASS-FONT-67](UI-CHARGEN-CLASS-FONT-67.md): Requested: the Make your own class window uses the console font for the attribute and skill rows (as the race stats screen does), keeps the heading in the game font, and gives its hint row and Cancel and OK buttons the regular frame
- [UI-CONSOLE-FONT-SPECIAL-LETTERS-67](UI-CONSOLE-FONT-SPECIAL-LETTERS-67.md): Accented letters and curly quotes in game texts drawn in the console font show as other characters: an acute u as z, an acute e as i, a right single quote as a coloured digit
- [UI-DEATH-DAMAGE-TINT-38](UI-DEATH-DAMAGE-TINT-38.md): Lava damage tint also colours the death menu and selection
- [UI-ICONS-INVENTORY-42](UI-ICONS-INVENTORY-42.md): Inventory rows show icons only for the few staged items, squeezed 32 to 14 pixels; no magic or equipped backdrops
- [UI-INVENTORY-FONT-TABS-42](UI-INVENTORY-FONT-TABS-42.md): Inventory categories use the console font as plain text instead of the original Morrowind font on button tabs
- [UI-INVENTORY-HEADING-CENTRE-42](UI-INVENTORY-HEADING-CENTRE-42.md): The Inventory heading text is not vertically centred in its bar
- [UI-INVENTORY-LAYOUT-40](UI-INVENTORY-LAYOUT-40.md): Inventory text overlaps fields and footer; preview initially faces away
- [UI-INVENTORY-ORIGINAL-LAYOUT-42](UI-INVENTORY-ORIGINAL-LAYOUT-42.md): The inventory lacks the original encumbrance bar, armour rating and item icon grid
- [UI-INVENTORY-PREVIEW-GAP-41](UI-INVENTORY-PREVIEW-GAP-41.md): Inventory shows 'Character preview unavailable': a fixed 2 MiB memory guard refuses the 128 KB pose model in Seyda Neen
- [UI-INVENTORY-PREVIEW-STILL-42](UI-INVENTORY-PREVIEW-STILL-42.md): The inventory character is drawn live and turns instead of being a still picture
- [UI-JOURNAL-HINT-EMPTY-BOX-67](UI-JOURNAL-HINT-EMPTY-BOX-67.md): An empty box flashes after the first journal hint has gone: the frame stays on screen for a moment without its text
- [UI-KEY-HELP-STALE-38](UI-KEY-HELP-STALE-38.md): Key help exposes raw actions and uses a sparse outdated layout
- [UI-MAP-PLAYER-ARROW-51](UI-MAP-PLAYER-ARROW-51.md): Requested: the map shows the player as the original s arrow that turns with the player, not a crosshair
- [UI-MENU-LOGO-32](UI-MENU-LOGO-32.md): The menu logo has a line above the name and reddish-pink letters instead of gold
- [UI-NO-SHARED-LAYOUT-67](UI-NO-SHARED-LAYOUT-67.md): Menus place their boxes and buttons at fixed pixel positions of their own, so margins differ from screen to screen and buttons sit against the bottom edge of the box
- [UI-OK-BUTTON-THIN-FRAME-67](UI-OK-BUTTON-THIN-FRAME-67.md): The OK button in the menus has a thin outline instead of the regular button frame that View Stats has
- [UI-OPTIONS-WRAP-29](UI-OPTIONS-WRAP-29.md): Setup selection wraps despite a bounded scrollbar
- [UI-ORNAMENT-GLYPHS-23](UI-ORNAMENT-GLYPHS-23.md): The name-entry caret drew as a ball and the rotation hints as a skull and a tree (ornamental font glyphs)
- UI-PALETTE-NO-WHITE-48 (no report page): The game palette has no white: a White crosshair draws as the console ink cream (238,221,170)
- [UI-RACE-STATS-RETURN-SPACING-67](UI-RACE-STATS-RETURN-SPACING-67.md): Requested: the race stats screen gets a Return button under the attributes and space under the Attributes heading
- [UI-STATS-WINDOW-48](UI-STATS-WINDOW-48.md): No Stats window (attributes, skills, health/magicka/fatigue) and no Magic window: the original's P and O windows
- [UI-TEXT-BOX-CLEARANCE-64](UI-TEXT-BOX-CLEARANCE-64.md): Text boxes leave too little room above and below their text (the opening hint: the last line touches the bottom edge)
- [UI-WINDOW-TITLE-BAR-42](UI-WINDOW-TITLE-BAR-42.md): Menu windows lack the original title bar (tiled frame with the window name on a dark plaque)
- [WAIT-NOCLIP-MESSAGE-32](WAIT-NOCLIP-MESSAGE-32.md): Wait refusal names registration, dry ground and speech together instead of the reason that applied (noclip)
- [WORLDMAP-LAVA-MISMATCH-36](WORLDMAP-LAVA-MISMATCH-36.md): The in-game map shows a lava band in Molag Amar where the world has grass and no lava

<!-- END GENERATED CATEGORY -->
