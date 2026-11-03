# Inventory

_Last updated with AmiWind v0.0.59-dev6 (3 November 2026)._

<!-- contents start -->
## Contents

- [Items and actions](#items-and-actions)
  - [Weapon kit for testing (dbg give weapons)](#weapon-kit-for-testing-dbg-give-weapons)
- [World models](#world-models)
- [The container strip](#the-container-strip)
  - [Where container data comes from (AREA-TABLES-59)](#where-container-data-comes-from-area-tables-59)
- [Debug torch (test only)](#debug-torch-test-only)
- [Appearance and implementation boundary](#appearance-and-implementation-boundary)
- [Next inventory pass: v0.0.40-dev2, 14 October 2026](#next-inventory-pass-v0040-dev2-14-october-2026)
- [Validation, 14 October 2026](#validation-14-october-2026)
  - [Inventory scrollbar source follow-up, 14 October 2026](#inventory-scrollbar-source-follow-up-14-october-2026)
- [Dedicated pose source progress, 14 October 2026](#dedicated-pose-source-progress-14-october-2026)
- [Inventory native checkpoint, 14 October 2026](#inventory-native-checkpoint-14-october-2026)
- [Icons and the HUD boxes, 17 October 2026](#icons-and-the-hud-boxes-17-october-2026)
- [Stats and Magic windows, 23 October 2026](#stats-and-magic-windows-23-october-2026)

<!-- contents end -->

The v0.0.40-dev1 source candidate adds **I** as a full-screen inventory modal.
It captures gameplay input and freezes the world simulation and rendering while
UI and audio service continue. Escape or I closes it. It reuses the existing
map modal and the original-art UI frame, with a nearly full-height player body
on the left and carried items on the right.

## Items and actions

The existing state capacity is 32 distinct carried IDs and 32 persistent ground
stacks. A loaded level admits up to 64 distinct new item models for dropped items
(`AW_INVENTORY_MODELS`). Every map is built with room for 16 of them in its model
table (`AW_INVENTORY_MODELS_GUARANTEED`, counted by the map limits check); past
those a drop takes only slots the map leaves free, keeps one slot for the arena
opponent, and is refused with "World model table full; kept." when none is left.
Repeated models reuse their slot, and scene changes reset this runtime cache.
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

Worn armour (v0.0.54): every armour piece goes into its own slot (helmet, cuirass, each pauldron, greaves, boots,
each gauntlet or bracer, the shield in the left hand), as OpenMW 0.51 places it (`mwclass/armor.cpp`
getEquipmentSlots). Pieces with a script that still acts after registration, or with an enchantment, are not
equippable yet. The armour rating is the original weighting (`mwclass/npc.cpp` getArmorRating): cuirass 0.3;
shield, helmet, greaves, boots and each pauldron 0.1; each gauntlet 0.05; an empty slot counts the Unarmored skill.
A piece rates its armour times the skill of its class (light, medium or heavy, by its weight) over iBaseArmorSkill,
times its condition. Each worn piece also gives the hit sound of a blow landing on it ([COMBAT.md](COMBAT.md)
"Sounds"). Since v0.0.59 the third-person body shows what is worn, assembled from parts by slot
([THIRD_PERSON.md](THIRD_PERSON.md)); the first-person hands do not yet show gloves or bracers. A two-handed weapon
and a shield exclude each other: equipping one takes the other off and back to the pack (`actionequip.cpp`,
`weapon.cpp` and `armor.cpp` canBeEquipped). Not yet: the rule that beast races cannot wear helmets that cover the
head or boots (armor.cpp). The engine's call `AW_InventoryEquippedWeaponType()` gives the type of the weapon in the
right hand (-1: hand to hand) for the hands and the player body.

A drop transfers one actual item into a persistent world record with its source
ID, count, scene, placement, yaw and condition. The converted ground model must
load, an entity must satisfy the engine allocator reuse rule, and the complete
swept footprint must have clear space and dry solid support before ownership
changes. Drops work in plain BSP scenes, in rooms and, since v0.0.59-dev4, on the streamed CHIM towns (a drop was
refused on every streamed map before). Scenes that cannot take a drop refuse placement with
"Cannot place items in this area yet; kept." Full-game CHIM/scenery drop support
remains open under [UI-INVENTORY-INTEGRATION-40](bugs/UI-INVENTORY-INTEGRATION-40.md).
Refused placement retains the item, quantity and condition. Aim at the dropped item
and press E to pick it up. Full inventory or incompatible condition retains the
world item. Save/load and scene re-entry restore the records: drops are rows of the world change list
([PERSISTENCE_AND_STREAMING.md](PERSISTENCE_AND_STREAMING.md)), which holds across rooms, outdoor areas and saves; the
older table of 32 ground stacks stays selectable (`aw_placed ledger off`). Dropping every kind of item is not yet
checked in game on the dev4 image.

For explicit testing, use dbg inventory grant "steel longsword" 1 and
dbg inventory grant steel_shield 1 to grant actual catalogue items. These are
diagnostics, not starter inventory or accepted gameplay acquisition. Character
change and grants use the on-demand debug catalogue; the I action adds one
32-byte resident command record. The console line aw_inventory equip "steel longsword"
then equips a carried item by the same rules as E in the inventory window (used by
the scripted first- and third-person gear checks).

### Weapon kit for testing (dbg give weapons)

`dbg give weapons` gives one of the game's own weapons of every weapon type (short
blade, long blade one- and two-handed, blunt one- and two-handed, staff, spear, axe
one- and two-handed, bow, crossbow, thrown weapons, arrows and bolts) plus a light
and a heavy shield, all at once, and prints each one's stats on the console from
its record: chop, slash and thrust damage (for bows, crossbows, thrown weapons and
ammunition, their damage), speed, reach, weight, value, health, enchantment points,
and armour for the shields. `dbg give weapons stats` prints the table again without
giving anything. Each row ends with `equip "ID"` (equippable now, with
`aw_inventory equip "ID"` or the inventory window) or `carry "ID"` (bows, crossbows,
thrown weapons and ammunition are carried only until ranged combat exists). The
lines wrap to the console's width.

The items are chosen when the image is built, by a rule, not by a list
(`tools/prepare_weapon_kit.py`): per type, the plain items (no enchantment, no
script, a name, a world model and an icon), iron, steel or chitin first, then the
one the game's records name most often (placed references, NPC, creature and
container inventories, levelled lists), then the cheaper one. On the original game
data that gives, for example, the iron dagger, steel longsword, steel claymore,
chitin short bow, steel crossbow with steel bolts, the chitin shield and the steel
shield. The choice is written to `inventory/weapon-kit.txt` (about 1 KB) and named
in the build receipt (`inventory-data.json` "weapon_kit"); the engine reads it only
when the command runs. The kit is given whole or not at all: it needs up to 16
kinds of item of the inventory's 32, and a full inventory refuses it with the
numbers. The items are an ordinary grant, saved and loaded like any other.
Tests: `tests/test_weapon_kit.py` and `tests/aga_weapon_kit_test.c`.

## World models

Every item the catalogue holds has its own world model when it lies on the
ground. The build stage `item-models` (`tools/prepare_item_models.py`) converts
each distinct original mesh once, on every core, into one alias model under
`progs/items/`, and writes the table `progs/items/models.awt` (the mesh path and
its model, one line each). Every item naming the same mesh shares that one file;
the same table draws the items the game data places in rooms and outdoors (v0.0.59-dev4), which can be aimed at and
taken. Each model's skin is cut to
the part its texture coordinates reach, which takes the set from about 124 MB to
about 48 MB (880 models). Nothing of it is resident: the engine loads a model
from disk only when an item is dropped. Each mesh's result is cached on its own,
so a later build converts only what changed.

`tools/item_census.py` checks this per kind of item (weapons, armour, clothing,
potions, ingredients, books, misc items, gold, keys, carried lights, apparatus,
lockpicks, probes, repair tools): how many item records the game data holds, how
many have a catalogue row, a picture and a world model in the table, and, with
`--id1`, how many an image carries and draws. It exits with a failure when a
kind has items missing from the catalogue, a mesh without a model, or no model or
picture at all; `tests/test_item_census.py` keeps the rule. The spell-effect
pseudo weapons are not items. Measured on the game data of 1 November 2026: all
2,910 item records are catalogued and every one names a model that the table
holds; two records name no picture. A build made before the model table
converted only ten models.

The catalogue also holds apparatus, lockpicks, probes, repair tools (weight,
value, and the apparatus type) and every light that can be carried (weight,
value, burn time, radius and colour; equipped in the left hand like the torch).

## The container strip

Placed containers (baskets, crates, barrels, chests, urns, sacks, cupboards,
desks, closets, the corpse and mummy containers and the rest) can be opened. Aim
at one within the activation distance: the focus box names it and the line under
the view reads "E: Open", or "E: Steal" in red when it belongs to someone (opening
is free, taking from it is theft). A locked container reads "Locked", its box
shows "Lock Level: N" as the original's tooltip does, and E does not open it; the
lock level comes from the placement in the game data, and a script's Lock or
Unlock on the world change list overrides it. Organic containers (flora) are not
opened: E picks them as before.

E opens the strip: a box along the bottom of the screen, up to the view, with a
title row (the container's name, red when owned; the Inventory side; Take All;
Close), one row of cells with each item's picture and count, the selected item's
name, and the keys.

| Key | In the strip |
|---|---|
| A / D, Left / Right | select the previous / next item (Page Up / Down: a row of cells) |
| E, Enter | take one (on the Inventory side: put one in) |
| Q | take (or put) the whole stack |
| T | take everything |
| Tab, W / S, Up / Down, 1 / 2 | the container side or the Inventory side |
| Esc | close |

The mouse: a cell selects its item, the selected cell again takes (or puts) one;
the title row's side names, Take All and Close are buttons. Taking from an owned
container marks the items stolen from its owner (the world change list's stolen
pairs). Every take and put is a container delta on the world change list, so the
contents stay changed across maps and in saves. The console's `aw_placed container`
shows the aimed or nearest container's contents and lock; `aw_placed container open`
opens its strip as E would; `aw_placed container take ID [N]` and `put ID [N]` move
items the same way.

The strip is assembled when it opens and freed when it closes: nothing of it is
resident while it is closed, and it adds no console command or variable. The
container's contents and owner are read from the image's focus table once, when
the strip opens, and kept until it closes, so a take or a put reads nothing from
the disk again (CONTAINER-STRIP-TAKE-STALL-59); a take or put that still holds the
frame for 100 ms or more says so in the console. While the strip is open the
whole screen is copied out only for two frames after a change (a key, the mouse,
a take or a put), otherwise only the view (CONTAINER-STRIP-REDRAW-COST-59). E and
`aw_placed container REF open` open the strip the same way. Bodies of dead people
and creatures are not containers in this pass: their carried items are not in the
data the engine reads, so they cannot be opened yet. Tests:
`tests/aga_container_strip_test.c`, `tests/aga_container_strip_open_test.c` (the
real strip opened both ways) and `tests/test_focus_box.py`; in game:
`tests/sessions/container_strip_both_opens.txt`.

### Where container data comes from (AREA-TABLES-59)

The builder writes one small binary table per room and per exterior cell into
one pack, `id1/areas.awa` (`tools/prepare_area_tables.py`): the area's placed
rows, its containers (contents, owner, lock level, trap and refill flags), the
owners it names, the catalogue records of every item its containers hold, its
placed items and its keys, and those items' strip pictures. The pack's index sits
at its head and stays in memory, so an area costs one seek and one read; it is
loaded with its room, or outdoors with the player's cell and its eight
neighbours. Opening a container, a take or a put, the strip's names and
pictures, a placed item's take and its owner then read only memory. Areas the
player has left stay in a small cache (16 areas, at most 256 KiB) and come back
without a read; the cache is emptied first when memory is short. A lookup
outside the loaded areas (an item carried from elsewhere, a container a script
names) goes through a small directory held in memory (8 bytes per item) to the
one area that has it, never through the island-wide files. When the pack is
missing the engine searches `focus.awf` and `inventory/items.awi` as before and
counts each such search; `aw_placed areas` shows the loaded areas, their bytes
and load times, the cache and that count. Tests: `tests/aga_area_tables_test.c`.

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
constant effects, scripted equip/drop events, quantity dialogs and corpse looting
remain incomplete (containers: see the container strip above). Missing models, tags or metadata disable the
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

## Stats and Magic windows, 23 October 2026

**P** opens the original's Stats window (`aw_stats`) and **O** the Magic window (`aw_magicmenu`). Both use
the inventory's window: the same frame, the original title bar, the same fonts and colours, the same pause
and input handling. Escape, or the window's own key (P or O, or whatever key is bound to it), closes it.
Both keys can be changed in Options > Controls ([keymaps](KEYMAPS.md)).

The Stats window is titled with the character's name, as in the original. The left side shows the health,
magicka and fatigue bars with current and maximum, the level, race and class, the eight attributes and the
birthsign. The right side lists the 27 skills under Major Skills, Minor Skills and Misc Skills as the class
defines them; Up/Down, the wheel, Page Up/Down, Home/End or the scrollbar scroll it. Everything is read
from the character sheet every frame, so values change as they change in the game. An attribute
raised or lowered by a modifier shows in green. The layout follows the original window, read from OpenMW's
stats window for structure (`mwgui/statswindow.cpp` and its layout). Two differences: the birthsign
sits under the attributes instead of under the skills, and factions, reputation and bounty are not shown,
because the engine has no faction state yet.

The Magic window is a placeholder until spells exist. It shows the original's headings, Powers, Spells
and Magic Items, lists the character's race and birthsign spells by their names from the game data
(`character/spells.aws`, written by the image builder; powers under Powers, spells under Spells,
abilities left out), shows "None" under an empty heading, and says "(Not yet implemented)" at the bottom.
Its title is "Magic"; the original titles it with the selected spell. Starting spells the original picks
from the class and skills are not listed yet.
