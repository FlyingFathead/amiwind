# Optional small mushrooms

The flora pipeline can include the original small Bitter Coast mushroom
placements with `prepare_tree_sprites.py --include-small-mushrooms`. Existing
flora selection remains the default. A custom world-flora policy can instead
add `small_mushroom` to `source_categories`; keep that policy separate so the
previous selection remains available.

Run conversion inside the development container with original inputs mounted
read-only and a new private output directory:

```sh
python3 tools/prepare_tree_sprites.py \
  --data-files /input/DataFiles --palette /work/palette.lmp \
  --out /work/small-mushrooms --include-small-mushrooms
```

This currently covers the numbered `flora_bc_mushroom_*.nif` family, separate
from giant static mushrooms. Each original master/cell/reference identity,
position, rotation and scale is retained. Container flags, items, weight and
script metadata remain attached to the placement receipt.

Container mushrooms use `mesh_pending_interaction` in
`prepare_world_flora.py`, with zero decorative sprites for those placements.
The regional overlay can append their visible geometry while retaining existing
LAND and scenery. Original no-collision markers and authored collision nodes
take precedence; otherwise small ground plants do not gain invented solid hulls.

**Harvesting is not implemented by this conversion.** Region receipts identify
`interaction_status: "not_implemented"` and list `unsupported_interactions`.
Metadata preservation is not runtime inventory or script execution. Packaging,
source identity/duplicate checks, memory/transport admission and native gameplay
acceptance remain necessary before enabling a new overlay in a playtest.

For a bounded diagnostic, supply a private original-reference census with
`diagnostic_subset: true` using `--census`. The diagnostic flag propagates to the
generated receipt, and the complete-world assembly rejects such a partial
input. A diagnostic sample is not a production whole-world conversion.

This optional content does not establish the cause of unrelated distorted rock
surfaces. Keep reference classification and camera-matched rendering evidence
separate when investigating those reports.


## Direct pickup in the dev4 source candidate

The first gameplay milestone is simple: **interact with a mushroom, receive its
original contents, then remove that mushroom from view**. This is the AmiWind
default where a validated harvest catalogue is installed. An optional collection
sound can follow; no sound has been selected or added. A classic container
interface is a later optional mode, not an implemented setting.

`aw_harvest_mode 1` enables direct pickup (the default); `aw_harvest_mode 0`
disables pickup. These console/config values do not resurrect a plant already
harvested. Mode 0 is not a classic container interface.

The source candidate has separate geometry and interaction preparation. After
the flora overlay has passed its existing checks, prepare the matching private
interaction catalogue:

```sh
PYTHONPATH=src:tools python3 tools/prepare_harvest.py \
  --master /input/DataFiles/Morrowind.esm \
  --region-report /work/flora/vf0000/report.json \
  --bsp /work/flora/vf0000/scene.bsp \
  --media-payload /work/complete-media/payload \
  --out /work/harvest-vf0000
```

Use the actual region report and map name. The output `harvest-<map>.txt`
belongs beside the other runtime data and is bound to that report's exact BSP
hash. Its private JSON receipt keeps full master hash, exterior cell and FRMR
identity, original inventory and source flags. The runtime matches the brush
model, reference and unquantized pose; these mushrooms remain dynamic entities
rather than being captured as immutable scenery. A missing or invalid catalogue
does not turn arbitrary containers into harvestable plants.

The selected pickup cue is the original `Sound/Fx/item/item.wav`. The optional
`--media-payload` argument reuses its complete-media conversion, checking the
exact source/category/path binding, output digest and bounded mono PCM format.
It stages the cue under `sound/pool/` beside the interaction catalogue. Missing
or invalid audio emits a warning and a `pickup_sound` receipt with
`status: missing_output`; verified staging still reports packaging and native
acceptance as unverified. The image assembler must carry this dependency into
its file manifest, category summary and hash readback. A staged receipt alone
does not establish that a playtest contains the cue.

Pickup plays the cue only after actual items are received and the plant
disappears. An empty original-content result is resolved before the first
render: that plant is absent from the map, with no highlight, interaction,
pickup sound or notification.
Capacity failures, rejected data and repeated use of an already harvested plant
produce no pickup cue. The runtime uses the existing local sound/cache helper;
it does not preload the full sound library. If the selected sound is absent,
pickup still works and reports the missing sound once per loaded map. Native
audible acceptance remains pending.

The initial scope is unscripted, unowned small mushroom containers with original
ingredient or leveled ingredient contents. Scripted records, ownership/locks,
restocking negative counts, plugins and unsupported inventory types are rejected.
Source identity is retained even when a placement has different model indices in
overlapping maps. A full SHA-256-derived save key prevents FRMR-only identity
collisions; the converter rejects duplicate keys/bindings.

Leveled contents preserve chance-none, eligible player levels, highest-level or
all-level selection, nested lists, and the top-level Each flag. Missing listed
records remain empty choices. The original roll seed and player level are saved
on first encounter, after saved-state restoration and before visibility. This
timing is an explicit bounded AmiWind policy; it does
not claim to reproduce every original container-initialization event. A failed
inventory insertion cannot reroll the contents, grant a partial stack or hide
the plant. Empty and picked facts are distinct: bit 31 records an empty
first-encounter result, bit 30 records a successful pickup, and level bits
20–29 remain unchanged. Both make the placement absent on return and save/load.
Classification never grants items. If saved-state capacity or data prevents
classification, the runtime logs that uncertainty and disables the prompt;
it does not pretend the placement was picked or silently grant inventory.

Successful pickup saves the inventory and harvested fact together using the
existing game-state codec. Normal cell/sub-cell travel and save/load retain the
fact; hiding is restored after saved state is restored. This first stage has
**no respawn**, including for containers whose original Respawn flag is set.
Those flags remain in the receipt. Source-compatible cell reset/respawn is a
separate milestone, rather than an automatic reset at a loading boundary.

Bounds are explicit: 24 catalogued placements per loaded map, 64 content nodes,
256 edges, 16 nested list levels and at most 64 items in an authored stack.
AWH3 now stores up to 4,096 catalogue-bound placement facts in a dedicated
saved table, independently of the 32-entry quest/global tables. Inventory still
holds 32 item types. See [harvest state](HARVEST-STATE.md) for identity, sparse
AWS3 saves and legacy-codec compatibility limits. Whole-world map admission is
still pending: the origin-only census reaches 75 plants in one coverage region,
above the current 24-per-map bound. Indexing those placements does not convert
or install them. Carrying-weight simulation remains outside this stage.

Validation includes original-data catalogue preparation for six source
placements, synthetic converter rejection cases, actual C transaction and scene
fixtures, AWS2 save roundtrips, existing scene/travel/scenery checks, and m68k
object compilation. **Native harvesting acceptance and playtest packaging are
still pending.** No new mushroom is implied to be in a sealed older playtest.

Source semantics were checked against OpenMW 0.48, pinned revision
`81ab0feb2ec2fda488eec043f6fa3d9b020f1521`:
[leveled selection](https://github.com/OpenMW/openmw/blob/81ab0feb2ec2fda488eec043f6fa3d9b020f1521/apps/openmw/mwmechanics/levelledlist.hpp),
[container contents](https://github.com/OpenMW/openmw/blob/81ab0feb2ec2fda488eec043f6fa3d9b020f1521/apps/openmw/mwworld/containerstore.cpp),
[container flags/reset](https://github.com/OpenMW/openmw/blob/81ab0feb2ec2fda488eec043f6fa3d9b020f1521/apps/openmw/mwclass/container.cpp),
and [cell reset timing](https://github.com/OpenMW/openmw/blob/81ab0feb2ec2fda488eec043f6fa3d9b020f1521/apps/openmw/mwworld/cellstore.cpp).
The reference uses a strict elapsed-time threshold of
`24 * 30 * iMonthsToRespawn` hours from the cell's last reset, not a reset on
ordinary traversal. A future respawn mode needs that cell-level policy and its
own persistence checks.

## Crosshair prompt and pickup notification

The original container FNAM appears with `(E: Pick)` in the same placement and
style as the existing Talk prompt. Eligibility uses the actual pickup ray: a
live, unharvested placement within reach, under the crosshair, with no blocking
world geometry or actor. Existing NPC Talk selection takes priority. The prompt
disappears immediately after a successful pickup and remains absent after
crossings and saved-state restoration. Each exact original master/cell/FRMR
identity owns its present/harvested bit; one mushroom does not hide another.

AWH2 and AWH3 catalogues retain original ingredient FNAMs separately from
container names and internal IDs. AWH1 remains readable for compatibility, but
has no original item-name field. The converter requires actual supported FNAMs;
it does not substitute internal IDs for missing names. Actual inventory deltas
produce a brief rectangular message such as `Picked up 2 Luminous Russula.`
Once-per-success summaries can contain several original items; empty successes
never appear as selectable mushrooms. No pickup animation is added to the player model.

`aw_animate_item_pickups 1` (default, archived config/console variable) reuses the
existing notification slide. `aw_animate_item_pickups 0` shows/hides the pickup
box immediately. This switch does not alter ordinary dialogue animation, pause
the world or allocate memory per frame. The shared text buffer is 4 KiB so up to
32 distinct received item names/quantities are not truncated. A pickup notice
may replace currently displayed subtitle text; it does not stop voices or music.

The source-derived static mushroom preview was accepted on 5 October 2026.
That confirms the preview appearance only: live placement, prompt, pickup,
notification, sound, persistence and target performance still require native
acceptance in a new image. The existing sealed playtest is unchanged.

The hidden inventory uses the existing saved `AW_ITEM` table. The diagnostic
console command `dbg shroomtracker` (direct command `aw_shroomtracker`, no
arguments) reports how many distinct mushroom placements have been picked.
It is read-only and offers no reset operation. The
picked-placement count reads valid persisted DONE facts only: received item
quantities, EMPTY facts, repeat visits and repeat key presses do not add picked
mushrooms. It shares the existing 32-entry global-fact capacity; it is not an
unbounded whole-world counter or a visible inventory interface.

Optional `harvest-<map>.txt` catalogues are included in the gameplay save-content
fingerprint in sorted filename order, using each relative path and complete
file digest. Changing, adding or removing a catalogue intentionally changes save
compatibility: old pickup facts must not silently apply to different contents.
Builds with no harvest catalogues retain their previous fingerprint. The build
checks map association and the bounded ASCII AWH1/AWH2 envelope; original source
binding and native catalogue parsing remain separate required gates.

## Dev4 pickup confirmation and repeatable release checkpoint

Playtesting on 6 October 2026 confirms that mushroom picking works at the Seyda
Neen Luminous Russula pilot near original global XY **-10920, -75120**. The shipped
dev4 scope remains six original placements; this does not establish worldwide
coverage or acceptance of every pilot placement.

The upcoming More Mushrooms! release must include `dbg shroompicker` so the same
location can be checked quickly without resetting collected state. See the
[pickup checkpoint instructions](DEBUG_OVERLAYS.md#mushroom-pickup-checkpoint-next-v0029-build).
The command and post-load view setup need source/target checks and native
acceptance before the final release is marked ready.
