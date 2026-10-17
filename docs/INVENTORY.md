# Inventory

The v0.0.40-dev1 source candidate adds **I** as a full-screen inventory modal.
It captures gameplay input and freezes the world simulation and rendering while
UI and audio service continue. Escape or I closes it. It reuses the existing
map modal and the original-art UI frame, with a nearly full-height player body
on the left and carried items on the right.

<!-- contents start -->
## Contents

- [Items and actions](#items-and-actions)
- [Debug torch (test only)](#debug-torch-test-only)
- [Appearance and implementation boundary](#appearance-and-implementation-boundary)
- [Next inventory pass: v0.0.40-dev2, 14 October 2026](#next-inventory-pass-v0040-dev2-14-october-2026)
- [Validation, 14 October 2026](#validation-14-october-2026)
  - [Inventory scrollbar source follow-up, 14 October 2026](#inventory-scrollbar-source-follow-up-14-october-2026)
- [Dedicated pose source progress, 14 October 2026](#dedicated-pose-source-progress-14-october-2026)
- [Inventory native checkpoint, 14 October 2026](#inventory-native-checkpoint-14-october-2026)
- [Icons and the HUD boxes, 17 October 2026](#icons-and-the-hud-boxes-17-october-2026)

<!-- contents end -->

## Items and actions

The existing state capacity is 32 distinct carried IDs and 32 persistent ground
stacks. A loaded level admits at most 16 distinct new inventory model precaches;
repeated models reuse their slot, and scene changes reset this runtime cache.
These are separate capacities; no unsupported expansion is implied. The item list reads actual AW_ITEM ownership and source-derived identities,
names, categories, quantities, weights, values and converted icons. All, Weapons,
Armour, Clothing, Potions, Ingredients, Books and Misc tabs filter the list;
O cycles name/value/weight sorting. Up/down and wheel select, Tab changes category,
left/right rotates the body preview. Right-click opens only available actions.
E or Enter equips/unequips the selected supported item; D drops one.

The first supported equipment set is source-compatible rings/amulets without
constant effects or unsupported scripts, plus converted melee weapons and
shields. The original starter shirt, pants and shoes are initialized once from
the original player record. Earned items remain earned: opening inventory does
not grant gold, the healing ring, a sword or a shield. The healing ring is a
CastWhenUsed item; wearing it never heals the player.

Equipment changes update persistent slots and live combat gear fields while
preserving health, fatigue, knockdown and opponents. Actual source weapon damage,
reach, speed, weight and weapon/shield condition are used. Condition is captured
before saves and equipment changes, and is retained through drop/pickup rather
than repaired by re-equipping. A durable stack with differing individual
conditions is not supported; incompatible merges and durable stacked equips
are refused.

A drop transfers one actual item into a persistent world record with its source
ID, count, scene, placement, yaw and condition. The converted ground model must
load, an entity must satisfy the engine allocator reuse rule, and the complete
swept footprint must have clear space and dry solid support before ownership
changes. The current safe development boundary supports plain BSP placement.
Active CHIM, captured-scenery and restricted-story scenes refuse placement with
"Cannot place items in this area yet; kept." Full-game CHIM/scenery drop support
remains open under [UI-INVENTORY-INTEGRATION-40](bugs/UI-INVENTORY-INTEGRATION-40.md).
Refused placement retains the item, quantity and condition. Aim at the dropped item
and press E to pick it up. Full inventory or incompatible condition retains the
world item. Save/load and scene re-entry restore the records.

For explicit testing, use dbg inventory grant "steel longsword" 1 and
dbg inventory grant steel_shield 1 to grant actual catalogue items. These are
diagnostics, not starter inventory or accepted gameplay acquisition. Character
change and grants use the on-demand debug catalogue; the I action adds one
32-byte resident command record.

## Debug torch (test only)

While AmiWind is a preview, the player leaves the census office with a torch that never burns out: the
maintainer's request of 17 October 2026, so a tester gets a torch and uses it. It will not be in the final game.

- **What it is:** one catalogue row, `aw_debug_torch`, named "Debug torch (test only)", made by
  `tools/prepare_inventory.py` from the original torch (the LIGH record `torch`: its model, icon, weight, value,
  light radius and colour). Its burn time is -1, the value OpenMW treats as a light that never runs out
  (`apps/openmw/mwmechanics/actors.cpp`); the original record's own time (210 seconds) stays in the build report.
  No other light is an inventory item yet, and nothing burns down in AmiWind yet; the carried torch (V with hands
  raised) has never had a burn time.
- **When:** once, when the player goes through the census office's exit door to the courtyard (the point where
  the opening hands over control). A saved mark (`amiwind:debug_torch:granted`) keeps it from being given again:
  not on a reload, not when leaving the office again, not after it was dropped. A quick-start character
  (the New Game screen of a `--skip-census` build) skips the office and gets no torch.
- **Use:** Equip in the inventory puts it in the left hand and lights the carried torch (raise hands with F to
  see it); unequip puts it out. V still toggles the carried torch as before.
- **The switch:** `aw_debug_torch 1` in the game config the builder writes (`config/game.cfg`, staged as
  `default-game.cfg`), on for every build until the final game, which sets it to 0. It is not a saved setting,
  so the image decides. The build receipt says it (`build.json` "debug_torch") and the image step prints
  `[debug torch] ON`.
- **Tests:** `tests/aga_inventory_test.c` (given once, never when off or when the inventory is full, unlimited
  burn time, an ordinary light counts down), `tests/aga_inventory_metadata_test.c` (the catalogue row),
  `tests/test_inventory_assets.py` (the row from the original record), `tests/test_debug_torch.py` (the switch,
  the receipt, the census exit, the lit torch).

## Appearance and implementation boundary

The preview uses the same race/sex alias body as gameplay, with real per-frame
weapon/shield attachments and a shared depth buffer. It fits body and held
models inside the left panel without changing the world camera. Player tags
reuse the existing AW_Items format, bone conversion and pose transform, keeping
the body's selected frames unchanged. This adds no animation frame reduction.

The selected dev1 normal-body set contains nineteen current bodies and a retained
122-frame Argonian male/layout with matching 122-row item tags. The latter
preserves hit/death/jump sampling but its legacy held-block sample is about
67 ms early; native held/release and movement are scoped observations, while
closer pose, anatomy/quality, jump/death and complete acceptance remain open.
This exception must not be labelled twenty new exact-hit bodies. See
[body fitting](bugs/BUILD-PLAYER-BODY-BUDGET-FALLBACK-39.md).

The existing gameplay body still bakes the default head/hair and starter outfit.
Selected full-body head/hair and arbitrary clothing/armour composition remain
required work in the [equipment roadmap](CHARACTER_EQUIPMENT_ROADMAP.md).
Unsupported worn clothing cannot be removed through this modal while its baked
appearance would remain unchanged. Carried-light inventory ownership, arbitrary
item resource conversion, two-handed animation/presentation, enchanted item use,
constant effects, scripted equip/drop events, quantity dialogs, containers and
corpse looting remain incomplete. Missing models, tags or metadata disable the
corresponding action instead of substituting unrelated values or appearance.

The converter writes a bounded, sorted AWI2 catalogue and selected original
model/icon resources into the private game image. The runtime searches rows on
disk rather than retaining the whole catalogue. UI rows, icons and preview depth
are allocated on open and released on close. Equipment/drop state uses a new
optional AWS4 feature section; older save payloads remain readable. Older readers
reject that new feature instead of silently discarding inventory.

## Next inventory pass: v0.0.40-dev2, 14 October 2026

The unreleased source now reserves inset status/control rows and uses the
literal "Inventory" heading, with unchanged preview and glyph/icon sizes.
Executable layout/action and map/journal checks pass; native visual comparison
remains pending. The original inset plaque, artwork and dedicated pose below
remain planned. Delivered dev1 does not contain this follow-up.

Plan compact lookup tables for all original item identities, properties and
effects, with explicit support states and bounded on-demand resources. Preserve
original typed effect, enchantment/charge, equip/use and save semantics; do not
substitute default values for unsupported records. Current basic AWI2 rows and
ten selected asset pairs are incomplete: actual picked Luminous Russula resolves
name/count/weight/value but has no converted icon/model or admitted action.
Keep authoritative carried IDs, counts, condition and equipped state reliable.
Quest logic must query actual AW_ITEM inventory, not a hot-swap list or the UI's
visible rows. A bounded hotbar/equipped asset cache may stay resident for fast
use; other descriptors, icons and models load on demand. Full-catalogue lookup
coverage does not require full-catalogue residency. This is a cache plan, not
an implemented optimization or measured speed/memory saving.

Original UI textures must be derived from the locally supplied owned game
during conversion and excluded from public source. The fixed right-hand corner
must mirror the left border pattern, with no movable-window or resize control.
Interim authored placeholders do not establish original artwork parity.

Require original golden title/tab frames and font, with no movable-window
top-right corner decoration in the full-screen modal. Add actual carried-weight/
capacity and Armor-rating readouts from game state, plus a mouse-operable
vertical scrollbar on the right and keyboard navigation. These readouts and
visual refinements remain planned. The dev2 scrollbar source follow-up below
has focused automated checks; native acceptance remains pending.

Add a persistent View option for item list versus icon grid, reusing the same
actual carried selection, category/filter/sort, equip/use/drop admission and
keyboard/mouse actions. Persisting a view must not duplicate inventory state
or change item ownership. This list/grid option remains planned follow-up.

Plan E or a double-click on the actual selected carried item to open its
context actions: equip/unequip, consume/use and read books or papers as the item
supports. Share the existing action admission and authoritative ownership state;
unsupported effects or reading paths must be labelled unavailable rather than
simulated. These expanded shortcuts/use/read actions are planned, not dev1
implementation.

Equipped items also require a thin golden outline. Dedicated original inventory
poses, the original inset black name plaque and camera parity remain planned;
none of these additions is implemented by this roadmap update.


The inventory heading is literal "Inventory"; the separate planned O stats
modal has the player-name header. Inventory-modal O keeps its existing sort
cycle; gameplay O is a planned rebindable action, not implemented here.

These are dev2 requirements; the scrollbar source progress is recorded below.
Dev1's implemented subset, delivery records and remaining verification gates
stay separate. No CHIM conversion, native or packaged coverage changes.
Track this work with [UI-INVENTORY-INTEGRATION-40](bugs/UI-INVENTORY-INTEGRATION-40.md)
and the [equipment roadmap](CHARACTER_EQUIPMENT_ROADMAP.md).

The inventory character must match the actual player: selected race, sex, head,
hair, clothing, armour and equipped items. Composition and visibility must follow
the original body-part and equipment rules. The existing race/sex alias, default
head/hair and baked starter outfit leave full appearance matching pending.
Convert the full original item-icon catalogue from the maintainer's game data and
track missing, held and unsupported icons per item. Dev1's ten selected test
models/icons do not establish full icon or item coverage.

Research and implement the original equip, unequip, use and drop behavior using
owned records, OpenMW source and matched original-game interaction. Preserve
ownership, quantities, condition, stack compatibility, scripts, active effects,
scene changes and save/load. Enchanted item use and constant effects require
actual effect handling and their original eligibility and timing. Dragging an
owned item onto the character must invoke the supported equip or use action
through the same ownership and state checks as context actions and keyboard
controls. Cancellation, invalid targets, ineligible items and failed actions
must retain the original ownership, quantity, condition and equipment. The
drag interaction must not claim an unsupported use or effect occurred.

Keep the black full-screen backdrop, paused world, original golden borders and
tall character panel. Place the literal "Inventory" title in the original inset black
plaque within the golden top border. The planned separate stats screen uses
the actual player name in its header. The latest maintainer reference still rejects
the preview posture; both plaque and original-posture refinements are planned,
not implemented here. Provide readable item-hover details at AGA resolution,
including a variant in the readable F10 console-font style. Hover interaction
remains pending.
Keep category selection and add value, weight and relevant item-stat sorting
and filtering. Existing category tabs and O's name/value/weight sort cycle are
a partial implementation; verify mouse and keyboard behavior and legibility
against the original interaction and the target display.

Minimize resident item memory with compact lookup tables (LUTs), meaning the
compact tables and indexes used to find an item's metadata and resources. Retain
stable original IDs and the data needed for ownership, actions and effects.
Use on-demand disk access for icons and other item assets, with a bounded cache
for visible items. The existing sorted on-disk catalogue is the starting point;
measure table/index sizes, decoder work and cache limits before choosing further
compression. Memory reduction must preserve item identity, rules and save data.

The delivered dev1 preview uses the live body frame/ordinary idle; a camera half-turn
does not reproduce OpenMW's dedicated inventoryhandtohand or inventory-plus-
weapon pose fixed at time zero. The latest maintainer finds the listing readable,
but dedicated posture and original-reference parity remain pending.

Use the original inventory-specific posture for the still preview. Evaluate
a higher-detail head or body only for this single-frame render, measuring peak
memory and latency. Cache by appearance/equipment/pose/view/palette revision:
a quick reopen may reuse matching pixels, while equip, unequip, drop or character
changes invalidate them. Compare a bounded RAM cache with an optional disk cache;
do not save or trust a stale portrait as authoritative character state. The cache
tracks current carried/equipped item state and condition; ordinary movement
is not an inventory-state change.

Compare the existing live body preview with a cached bitmap refreshed when the
appearance, pose or equipment changes. Record any additional invalidation needed
for view or palette changes. The bitmap is an option to measure, not an
implemented optimization or a promised saving. Measure open/closed allocations,
peak RAM, icon/asset residency, frame cost and disk-load latency at the reference
machine budget. Pausing does not itself release world memory. Release transient
panel/preview resources on close; unloading world dependencies requires a safe
restoration contract.

Add an explicit inventory preparation phase to the master builder, with its own
inputs, outputs, dependency hashes and completion/failure receipt. Measure build
elapsed time, peak memory and asset/table sizes while this work is developed;
keep runtime open/close, scrolling and preview costs in the same performance
record. Keep the inventory producer, runtime format/consumer, documentation,
release allowlist and exported public source synchronized in each reviewed
change. Public source contains conversion code and permitted metadata, while
original game icons and models remain user-supplied inputs/private outputs.
This phase and its performance monitoring are planned work.

Plan a MiniWind `--inventory-test` entry that loads a controlled scene with
explicit, tracked test items. This flag is proposed, not available through this
roadmap entry. Record the selected original IDs, types, quantities, initial
ownership/equipment and expected actions; keep diagnostic grants distinct from
normal earned inventory. Track each item's source, metadata, model/icon,
action/effect support, conversion, native verification and exact package
readback. Exercise appearance changes, drag cancellation, equip/use/drop,
pickup, capacity/condition refusal, scene re-entry and save/load without losing
or duplicating items. Retain original-versus-native comparison and separate
maintainer acceptance; a controlled test scene does not establish full-game support.

Inventory state must persist through panel close/reopen, scene changes and
save/load: carried counts, quest items such as the starting ring, equipment
and condition share the authoritative game-state records. Existing harvest
and ring transitions are integration controls, not a separate UI inventory.
The compact LUT/catalogue supplies names and rules, not a second ownership
database. Keep UI fields, framing and text rendering modular and reusable;
layout options must not duplicate item or gameplay state. Establish and
review the intended visual layout before selecting pre-baked low-cost UI
backgrounds; dynamic data and reusable controls remain separate.

For the planned configurable layout, expose inventory font and item-icon frame
preferences in the normal saved configuration, with bounded drawing for each
font size. Default icon framing may be removed after a readability comparison.
Keep controls reusable across AmiWind menus. These switches are planned; the
current candidate uses the small bounded font. Friendly item names are read
from original data during private conversion and resolved through the catalogue.

## Validation, 14 October 2026

Focused host checks cover atomic ownership/equipment/drop/pickup, condition and
save roundtrips, malformed/nonfinite equipment metadata, real UI input and
context actions, preview pixel bounds/depth, and existing map/journal/UI
regressions. Source-derived selected asset readback verifies ten item models and
icons plus twenty unchanged-body tag tables. The original inventory was
inspected in OpenMW 0.51, including actual ring slot state; this guides the
adapted full-screen layout.

Thirty-nine additional integration checks pass, including actual runtime
placement/capacity/no-loss cases and map model/entity reservations. Six affected
C units compile. These checks do not resolve full-game drop support.

The earlier complete suite and Amiga target passed, then native testing exposed
catalogue and layout failures. Later exact diagnostics verify selected names/icons,
actual sword/shield equip and scoped male-Nord modal pause/input; the later full
suite and Amiga/FPU target pass. Physical third-person shield hold/release is
observed for male Nord, with incoming block evidence separately scoped to the
previous female-Nord run. The subsequent exact target/FPU and full suite pass; native centre Guard
removal and live no-dice readout controls are observed. These scoped results
do not establish complete inventory or selected-body acceptance. Matched original comparison, complete appearance/clothing,
full-game drop placement, scene/save/load and target memory/performance remain
separate pending checks. This is a source
candidate, not a shipped or maintainer-accepted feature. No CHIM cell coverage changes
are claimed. [Current roadmap](ROADMAP_HISTORY.md#world-map-inventory-and-journal-todo-maintainer-request-1-october-2026)
and [blocking issue](bugs/COMBAT-BLOCKING-36.md) retain their pending gates.

### Inventory scrollbar source follow-up, 14 October 2026

The unreleased dev2 source adds the shared journal scrollbar to inventory
lists longer than six rows, reserving the right rail without shrinking the
character preview. Selected items stay visible and actual ownership remains
unchanged. Mouse arrows/rail/drag, release, focus loss, category changes,
keyboard navigation and close/reopen have focused executable coverage, along
with real equip targeting, empty/six/twelve-item lists and map/journal controls.
The actual shared UI-helper test also passes. The full suite and Amiga/FPU
build subsequently passed with the counts in the dedicated-pose section below.
Original/native visual comparison and packaging remain required. The ordinary
standing preview is still reported in dev1; dedicated inventory poses are now
converted but await native review. Original artwork remains unfinished.
No CHIM coverage changes.
[Inventory layout](bugs/UI-INVENTORY-LAYOUT-40.md).

## Dedicated pose source progress, 14 October 2026

The unreleased source selects dedicated original START poses for unarmed and
melee-equipped inventory bodies, with matching attachment tags and two-handed
left hiding. Six converter checks and the before/after runtime regression pass;
original human/female/beast keys and matrices resolve. Gameplay frame counts and
animation clocks are unchanged. All twenty race/sex companions have converted
with ten frames each; independent binary/tag readback passes (8,286,220 bytes).
The exact implementation passes the Amiga/FPU build and the full 4,086-test suite:
4,080 passes, three Windows-only skips and three tracked expected failures.
Matched native visuals remain pending. Torch-specific posture, full chosen head/hair
and changing worn body parts are unfinished; starting clothing is still used.
The optional modal alias is released on close. No measured target cost or
complete appearance/visual acceptance is claimed. CHIM coverage is unchanged.
[Inventory layout](bugs/UI-INVENTORY-LAYOUT-40.md).

## Inventory native checkpoint, 14 October 2026

The corrected candidate shows the dedicated male Nord unarmed, steel longsword
and steel shield preview through physical inventory controls and close/reopen.
The initial missing-model-allowance refusal is preserved in the report. Original
OpenMW appearance/equipment match is scoped; full appearance, torch, all-race
visuals and remaining UI work are still open. No new shipment or CHIM coverage.
[UI-INVENTORY-LAYOUT-40](bugs/UI-INVENTORY-LAYOUT-40.md).

## Icons and the HUD boxes, 17 October 2026

The image step's inventory conversion also imports the item icons, the hand-to-hand icon and the HUD box
and bar art into one lookup table (`gfx/icons.awl`, pictures in the pack `gfx/icons.awp`, each stored once by SHA-256) and
writes each item's enchantment type and maximum charge into the catalogue (bytes 496..511, zero in older
catalogues). It prints one line with the rows, pictures and anything held back. The HUD weapon and magic boxes
draw from it, and so do the inventory rows: every ownable item's original icon (UI-ICONS-INVENTORY-42). Details: [the HUD](HUD.md).
