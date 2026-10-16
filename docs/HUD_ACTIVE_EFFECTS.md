# Active-effect HUD, icons and magic indicators

14 October 2026. Source findings and planned follow-up for v0.0.40. This document does not implement the effect grid, original icon conversion, selected-magic gameplay or the display diagnostic. The current HUD's interim artwork does not establish original visual parity. See the [HUD roadmap](ROADMAP_HISTORY.md#world-map-inventory-and-journal-todo-owner-request-1-october-2026) and [HUD-STATS-29](bugs/HUD-STATS-29.md).

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
