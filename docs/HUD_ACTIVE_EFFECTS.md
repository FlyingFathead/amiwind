# Active-effect HUD, icons and magic indicators

_Last updated with AmiWind v0.0.64-dev5 (11 November 2026)._

<!-- contents start -->
## Contents

- [How many small effect icons there are (11 November 2026)](#how-many-small-effect-icons-there-are-11-november-2026)
- [In the game (v0.0.64)](#in-the-game-v0064)
- [How many effects can be active?](#how-many-effects-can-be-active)
- [Instances, effect types and icons](#instances-effect-types-and-icons)
- [Planned AGA layout and overflow](#planned-aga-layout-and-overflow)
- [Original icons and build preparation](#original-icons-and-build-preparation)
- [Condition, charge, spell chance and Endurance](#condition-charge-spell-chance-and-endurance)
- [Bounded display diagnostic and acceptance](#bounded-display-diagnostic-and-acceptance)

<!-- contents end -->

## How many small effect icons there are (11 November 2026)

The small coloured icons the HUD shows while something is on the player (a disease, a shrine blessing, a race or
birthsign ability, a constant-effect ring, a potion or a spell) are the small icons of the magic effects, one per
effect type however many sources feed it. Counted in the game data:

| Source | Magic effect records | Distinct small icons |
| --- | --- | --- |
| Morrowind.esm | 137 | 135 |
| Tribunal.esm | +1 | +1 |
| Bloodmoon.esm | +4 | +4 |

The game files do not store which effects are instant; OpenMW keeps that in its own fixed table of 143 effect types
(components/esm3/loadmgef.cpp). By that table 13 effect types have no duration and never stay on as an icon (Open, Lock,
Dispel, Mark, Recall, the two Interventions and the Cures, among them), so **130 effect types can be active**; 111 of them
can be cast on oneself, the rest arrive from others, from diseases or from traps. The icons are the effect records'
small icon paths (for example `s\tx_s_ab_attrib.tga` under `icons\` in the game's archive; OpenMW loads the `.dds` file
the archive carries for it).

**How many show at once.** Neither OpenMW nor the game data caps it. OpenMW's effect box sits at the bottom right and
grows leftwards by one 16-pixel icon per active effect type, with no wrapping and no hidden count; at very large counts it
would run across the screen. In normal play a character carries a handful, at most a few dozen (abilities, constant
effects, a disease or two, a blessing, potions and spells running). Whether the original executable hides icons beyond
some number is not documented in the sources we hold; it is to be measured (an OpenMW and an original-engine session
with a stack of effects, screenshots, before the AmiWind grid is final).

**AmiWind's plan.** A row of small icons under the view, above the health, magicka and fatigue bars; when the row fills
it wraps into a second and a third row, and no further: beyond three rows the last place shows "+N" for the hidden ones
(they stay in the full, paused effects list), so the HUD never grows past three rows and no active effect is ever dropped
silently. The character's stats page shows the same icons and a key (for example V, "view active effects") that opens a
box you scroll up and down: every active effect with its icon, name, description, magnitude, its sources (spell, potion,
disease, blessing, ability, item) and the time left for timed ones. So a few always show on the HUD, and the whole list
is one key away in the stats view. How many icons fit in a row follows from the HUD width at the screen mode in use. The icons are converted from the player's own game data by the build (about 256 bytes each at 16 × 16
in 8 bits, about 36 KB for all of them); the repository holds the converter, never the pixels.

## In the game (v0.0.64)

**Under the view.** The icons stand right of the weapon and magic boxes and the sneak indicator, in the strip under the
view, one 12 × 12 icon per active effect type, in effect-number order as OpenMW orders them. The first row is the lowest
one; when it is full the icons go on in a second and a third row above it. When even three rows are full, the last
place shows "+N" for the effect types that do not fit. How many fit follows the screen width: 12 a row at 320 pixels
(36 in three rows), 37 a row at 640 (the picture cache caps the HUD at 48 places). With the debug HUD on (`dbg hud`)
the strip has no free rows beside the bars, so the icons get rows of their own under the name line and the view is
that much shorter while effects are active.

**The Stats window.** The same icons stand under the birthsign (one row, nine places, "+N" past them). V in the Stats
window opens the list of every active effect over the window: each effect's 16 × 16 icon and name, its description from
the game data, and one line per source: the attribute or skill it acts on, the magnitude in points (none for an effect
without a magnitude), the source's name (the spell, the worn item), what kind of source it is (spell, potion or item,
worn item, ability, disease, blight disease, curse) and the time left, or "permanent". Up and Down, the wheel, Page Up
and Page Down and the scroll bar move it; V or Escape go back to the Stats window; P closes both. The game is paused
while the window is open, as with every window. V outside the Stats window stays the torch.

**What counts as active.** Every effect in the player's active effect list (spells cast on the player, potions and
ingredients, used and striking items, the constant effects of worn items) and the effects of the spells in the
player's list that act always: race and birthsign abilities, diseases, blights and curses (OpenMW keeps those active
with no end). A script's resistance change (SetResistFire and the like) changes a magnitude but shows no icon.

**The switch.** `aw_hud_effects 1` (the default, in the game's default settings) shows the icons; `dbg hudeffects off`
hides them under the view and on the Stats window, and V still lists everything. The setting is saved. `dbg effects`
prints what is active, the pictures held and read, and the strip lines the debug HUD gives the icons.

**The pictures.** The build converts each magic effect record's small icon (its ITEX) from the player's own game data
into `gfx/effects.awe`, at 12 × 12 for the HUD and 16 × 16 for the list, together with the effect's description; one
row per effect number, so the game reads an effect's row directly. An effect whose icon the data does not have gets an
empty framed place, never drawn stand-in art. The repository holds the converter only.

### Cost

Measured numbers come from the in-game check (pending); the sizes below are the program's own.

| What | Bytes or work | When |
| --- | --- | --- |
| Effect file directory | 2,288 bytes resident | read on the first effect shown, kept |
| HUD picture cache | 48 icons, 7,296 bytes | allocated on the first effect shown, kept |
| Active list, icons, always-active entries | 4,096 bytes resident | static |
| The list behind V | about 52 KB | while it is open, freed on closing |
| Per frame | one pass over the 64-entry effect pool, a sort of at most 96 entries, 144 bytes copied per icon | while the HUD shows |
| Disk in play | one open of `gfx/effects.awe` for the icons new in that frame (144 bytes each); the always-active spells' effects read again only when the player's spell list changes | when an effect first shows |
| Disk on V | one open, the 16 × 16 icons (256 bytes each) and the descriptions of the effects listed | when the list opens |
| Image | `gfx/effects.awe`, about 80 KB (143 rows, two pictures and a description per effect) | build |

Nothing is drawn in the 3D view: no triangles, models or lights are added.

14 October 2026. Source findings and planned follow-up for v0.0.40. This document does not implement the effect grid, original icon conversion, selected-magic gameplay or the display diagnostic. The current HUD's interim artwork does not establish original visual parity. See the [HUD roadmap](ROADMAP_HISTORY.md#world-map-inventory-and-journal-todo-maintainer-request-1-october-2026) and [HUD-STATS-29](bugs/HUD-STATS-29.md).

## How many effects can be active?

The audited OpenMW 0.51 implementation does **not enforce a fixed global simultaneous-effect count** in its active-source storage or HUD loop. It uses a dynamic list of active sources, each with a vector of effects, plus a pending queue. This is resource-limited storage, not a claim of unlimited practical capacity. A numeric limit for the original closed-source Morrowind executable has not been verified.

**Eight is the creation editor's effects-per-spell/enchantment limit, not a limit of eight active effects on the player.** Multiple spells, potions, ingredients, abilities and enchanted items can contribute concurrently. Counting the magic-effect types in a catalogue does not establish a simultaneous-instance limit.

Source: [active-source storage, lines 34–43 and 93–124](https://github.com/OpenMW/openmw/blob/f4bec41444214a7903bebd178389ca22ca13f646/apps/openmw/mwmechanics/activespells.hpp#L34), [creation editor limit, lines 883–889](https://github.com/OpenMW/openmw/blob/f4bec41444214a7903bebd178389ca22ca13f646/apps/openmw/mwgui/spellcreationdialog.cpp#L883). These findings describe this inspected implementation; they are not an original-executable stress measurement.

## Instances, effect types and icons

OpenMW displays one 16 × 16 icon per active **effect ID**. Several sources and different target skills or attributes may share that icon. Its tooltip retains each contributing source name, target argument, magnitude and, when enabled, individual remaining duration. The HUD excludes unapplied effects and expired timed effects. Permanent effects have no invented countdown.

Gameplay aggregation is more specific than icon grouping: the effect key includes its skill or attribute argument. Applicable parameters accumulate under that key. Source replacement and stacking also depend on source, caster, item, flags and effect indices. Potions and ingredients explicitly allow stacking. Recasting a spell is not universally equivalent to adding another independent instance.

Source: [icon grouping, filtering and details, lines 88–168](https://github.com/OpenMW/openmw/blob/f4bec41444214a7903bebd178389ca22ca13f646/apps/openmw/mwgui/spellicons.cpp#L88), [gameplay key and addition](https://github.com/OpenMW/openmw/blob/f4bec41444214a7903bebd178389ca22ca13f646/apps/openmw/mwmechanics/magiceffects.cpp#L28), [source admission, lines 487–505](https://github.com/OpenMW/openmw/blob/f4bec41444214a7903bebd178389ca22ca13f646/apps/openmw/mwmechanics/activespells.cpp#L487), [potion and ingredient flags](https://github.com/OpenMW/openmw/blob/f4bec41444214a7903bebd178389ca22ca13f646/apps/openmw/mwmechanics/spellcasting.cpp#L370).

The inspected HUD expands a single row to approximately 16 × distinct-icon-count + 4 pixels and shifts its left edge to keep the right edge fixed. That loop has no explicit wrapping, paging or overflow counter. Rendering at extreme counts has not been verified here; this source finding does not establish an original visual capacity limit. Created widgets are retained and hidden when inactive, while active grouping and detail text are rebuilt. No exact memory or frame-time cost is established by this audit.

## Planned AGA layout and overflow

Place the active-effect row **above the resource bars, beneath the world viewport**. Tile into additional rows when needed, reserving space for health/magicka/fatigue, the weapon and selected-magic boxes, the selectable map/compass and debug text. This supersedes the earlier right-of-bars placement proposal. Derive the visible capacity from supported screen sizes and HUD scale; it is a display capacity, never a gameplay-effect cap.

Use a stable ordering and square icons. When groups exceed the available area, reserve an explicit **+N** entry for the hidden group count. Pointer and keyboard access must open a complete paused effects list. Show every contributing source, argument, magnitude and individual remaining duration there, including mixed permanent and timed contributions. A single combined timer must not imply that all sources expire together. If a compact next-expiry label is used, label that meaning clearly.

The reference image, active source state and HUD view are separate. Do not create an active icon merely because an enchanted item is equipped: cast-on-use effects must actually be applied, and constant effects must follow their real eligibility and removal rules. Simulation pause, expiry, dispel, cure, item removal and save/load must preserve the actual effect state.

## Original icons and build preparation

Convert the supplied game's original effect and item icons through the normal build pipeline. Resolve icons from source records and archive or loose-asset lookup, decode the original image, preserve its transparency, resize for the target and remap to the admitted AGA palette. Record source identity, dimensions, conversion settings and output hashes. Do not generate replacement artwork or guess an effect's identity from an ambiguous crop. Temporary authored placeholders remain explicitly interim.

Compare 16-pixel reference sizing with smaller candidates in the target HUD before choosing. The following are **calculated pixel payloads**, not measured assets, total allocations or savings:

| Square size | 8-bit pixels per icon | Pixels for 16 cached icons |
| --- | ---: | ---: |
| 8 × 8 | 64 B | 1,024 B |
| 12 × 12 | 144 B | 2,304 B |
| 16 × 16 | 256 B | 4,096 B |

A Quake picture adds its header; indexes, alignment, transparency handling, working buffers and disk reads add further cost. Original source dimensions, conversion output sizes and actual readability still need measured receipts. Compare source/converted byte counts and target captures, rather than claiming that fewer pixels automatically improve the result.

Reuse AmiQuake's indexed transparent picture drawing and existing HUD invalidation. [Draw_TransPic](../engine/aga/src/draw.c) requires valid screen bounds. Its global Draw_CachePic registry has 128 distinct-name slots and fails at exhaustion; that is an unrelated resource limit, **not** a magic-effect limit. Use a bounded reusable icon cache or reviewed atlas strategy rather than registering every encountered icon forever. Keep compact record IDs and offsets in lookups, load artwork on demand, and refresh membership on actual effect-state changes rather than player movement. Measure total RAM, worst-frame time and disk activity before performance claims.

Original game icons and derived image assets belong in private, game-data-generated builds. Public source contains the converter, schemas and findings, without proprietary pixels.

## Condition, charge, spell chance and Endurance

These are separate values, even when a HUD uses adjacent boxes:

| Value | Source and meaning | Required display behavior |
| --- | --- | --- |
| Weapon condition | Current item durability relative to its maximum | The weapon box represents condition, whether or not the weapon is enchanted. Bare fists have no item durability. |
| Enchantment charge | Current charge of the particular enchanted item relative to its enchantment capacity | The selected enchanted-item box represents charge; item details may also expose charge for a strike-enchanted weapon. It is not condition or a character attribute. |
| Normal spell success | The actual selected spell's casting success percentage | The selected-spell status is chance, not a charge reservoir. Eligibility, skills, cost, fatigue and effects require the original spell rules. |
| Endurance | A character attribute | It must not be labelled or interpreted as item condition or remaining charge. |
| No selected magic or no enchantment | No applicable selection or charge state | Show an explicit empty/not-applicable state; do not invent a full or depleted enchanted charge. |

The original HUD receives durability for the weapon box, success percentage for a normal spell and charge percentage for a selected enchanted item. Its magic list admits cast-on-use and cast-once items; constant effects and cast-on-strike items are not interchangeable selections. An unenchanted weapon can still have ordinary condition. An enchanted weapon can have both condition and charge, with different changes and persistence.

Source: [HUD setters, lines 332–444](https://github.com/OpenMW/openmw/blob/f4bec41444214a7903bebd178389ca22ca13f646/apps/openmw/mwgui/hud.cpp#L332), [selection and item condition, lines 1560–1584](https://github.com/OpenMW/openmw/blob/f4bec41444214a7903bebd178389ca22ca13f646/apps/openmw/mwgui/windowmanagerimp.cpp#L1560), [selectable enchantment types, lines 126–128](https://github.com/OpenMW/openmw/blob/f4bec41444214a7903bebd178389ca22ca13f646/apps/openmw/mwgui/spellmodel.cpp#L126).

The inspected charge normalization treats a stored −1 charge as full when a positive maximum applies; a zero maximum returns zero rather than dividing. That sentinel is not a depleted-item value. Capacity can be record-defined or calculated by enchantment type. The effective use cost also depends on Enchant skill, with a minimum cost of one in the inspected helper. Constant effects must not receive a fabricated draining countdown or reusable-use charge bar; cast-once consumption remains distinct from reusable charge. Actual charge use, recharge, depletion, item-instance persistence and source eligibility need their own checks.

Source: [charge normalization, lines 146–160](https://github.com/OpenMW/openmw/blob/f4bec41444214a7903bebd178389ca22ca13f646/apps/openmw/mwworld/cellref.cpp#L146), [cost and capacity, lines 96–149](https://github.com/OpenMW/openmw/blob/f4bec41444214a7903bebd178389ca22ca13f646/apps/openmw/mwmechanics/spellutil.cpp#L96), [normal spell success, lines 267–302](https://github.com/OpenMW/openmw/blob/f4bec41444214a7903bebd178389ca22ca13f646/apps/openmw/mwmechanics/spellutil.cpp#L267).

## Bounded display diagnostic and acceptance

The planned dbg teststatuseffects preview must be clearly labelled **DISPLAY TEST**. It should enumerate the finite icon catalogue in bounded pages and exercise empty, full, overflow, missing-icon, multiple-source, mixed-duration and permanent-effect views. Clear it automatically after a short bounded real-time interval, including while paused, and on exit/load/disconnect. Do not save it or alter real effects, stats, inventory, randomness, casting, charge or gameplay. Its display timer is independent of actual simulation-time effect durations.

Real acceptance separately checks stacking and recasts, different skill/attribute arguments, independent expiry, permanent-plus-timed sources, equipment removal, cast-on-use/strike/once behavior, dispel/cure, pause, charge/condition changes and save/load. Test layout at zero, one, capacity and capacity-plus-one groups, supported viewport sizes and complete overflow access. Use actual original icons and effects in matched original/native captures. Automated checks and payload arithmetic alone do not establish original parity, target resource fit or playable acceptance.
