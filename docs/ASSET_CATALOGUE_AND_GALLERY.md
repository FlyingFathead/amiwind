# Asset catalogue, placement coverage and debug gallery

**Outside approval is required for any exception affecting either gallery.**
Neither the NPC gallery nor the upcoming static-asset gallery may be disabled,
reduced or bypassed, including model/asset generation, catalogue coverage,
quality and validation, without a specific documented case or scenario **and
explicit approval from the project owner**. A builder or contributor cannot
approve its own exception. Build time, disk pressure and convenience do not
supply that approval. An opt-out flag is a mechanism for an approved exceptional
debugging case, not permission to choose that exception independently.

<!-- contents start -->
## Contents

- [Default inclusion contract](#default-inclusion-contract)
- [Required target: static assets directly callable by the engine](#required-target-static-assets-directly-callable-by-the-engine)
- [First implementation step: account for source assets](#first-implementation-step-account-for-source-assets)
- [Confirmed omission: scaled Bitter Coast trees](#confirmed-omission-scaled-bitter-coast-trees)
- [Coverage is not the same as catalogue size](#coverage-is-not-the-same-as-catalogue-size)
- [Proposed command: `dbg assetgallery`](#proposed-command-dbg-assetgallery)
- [Proposed cell-by-cell scenery layer over existing terrain](#proposed-cell-by-cell-scenery-layer-over-existing-terrain)
- [Proposed regional scenery pass and loading order](#proposed-regional-scenery-pass-and-loading-order)
- [Checkpoints and acceptance](#checkpoints-and-acceptance)

<!-- contents end -->

All NPCs and other game assets must remain intact, packaged and loadable by the
engine for the complete game to function properly. Skipping their creation
alongside either gallery is pointless and counterproductive: the final product
requires those assets anyway. An exceptional debug build must be labelled
incomplete and cannot redefine the complete game's required content. Runtime
loading may be on demand; this does not require every asset to reside in RAM
simultaneously. The static-asset gallery is still planned, not implemented.

Status: **TODO SOON**, planned, 2 October 2026. The catalogue and `dbg assetgallery` command
described here are not implemented. This plan does not add scenery to a shipped
image or implement the static asset gallery in rc9. The existing NPC gallery is a
separate feature and belongs in normal builds by default.

## Default inclusion contract

The future static-asset gallery must be included in normal builds once it is
implemented, for debugging and regression inspection. Any future explicit opt-out
is for debugging builds only and must warn accordingly. All static assets required
by the game remain required regardless of gallery selection: omitting an
inspection catalogue/UI must never remove world placements or shared models,
textures, collision or other dependencies. No asset-gallery opt-out exists today.
The NPC gallery follows this same rule now; it is enabled by default.

## Required target: static assets directly callable by the engine

Original `STAT` objects must become converted, packaged assets that the engine
can request by original object ID. An inventory entry alone does not meet this
target. The host inventory is the first implementation step toward that result,
not a substitute for runtime availability. Count a static asset as ready only
after its payload and dependencies are packaged, the loader accepts it and an
engine inspection check succeeds. Preserve unsupported/error entries visibly.

Load shared prepared assets on demand. World placement then supplies the
original transform and reference identity independently of the asset handle.
Do not require an object to be baked into a particular `vfXXXX` map before it
can be selected in the gallery. Generalized reusable scenery loading still
needs implementation; existing brush, alias and sprite paths do not by
themselves provide this interface for every original NIF.

## First implementation step: account for source assets

Build a catalogue from the original game records and asset containers so an
object can be looked up by its original ID. Begin with the supported base master;
record the input hashes and scope. Expansion and mod load orders require their
own override/deletion semantics before claiming coverage of those inputs.

Keep three related records separate:

| Record | Identity and purpose |
| --- | --- |
| Object definition | Source master, record type, original object ID, display name, model and dependencies |
| Converted asset | Source content hashes, conversion settings, model variant, output format/path/hash, bounds and conversion status |
| Placed reference | Source cell, FRMR identity, object ID, source position/rotation/scale, activation state and runtime destinations |

Several objects can share a model, and one object can have many placements.
Stable catalogue identities must not depend on traversal order or a sequential
`mNNN` filename. Preserve original spelling for display and normalize only the
lookup key; detect ambiguous collisions. Source resolution must record whether
bytes came from a loose file or archive according to the supported input policy.

Inventory archive/loose-file assets as well as record-referenced dependencies.
An unreferenced texture is different from a broken model dependency. Models,
textures, icons, sound, music, fonts and videos need appropriate catalogue
categories; a missing model field does not make every non-model record an error.
Do not guess dependencies for unsupported record or NIF features: report the
unsupported feature and its source identity.

Proposed lookup behavior: requesting an original object ID returns a ready
asset handle or an explicit reason such as `not-converted`, `unsupported`,
`source-missing` or `conversion-failed`. Merely knowing its filename must not
imply that the Amiga can load or render it. Keep conversion on the build host;
load prepared assets on demand at runtime with a bounded resident set. Do not
put the whole catalogue's geometry or textures into RAM at once.

Generate these reports from the owner's installed game files. Public source
contains the tools, schemas and synthetic examples; generated asset payloads and
full game-derived catalogues stay with private build outputs.

## Confirmed omission: scaled Bitter Coast trees

Inspection of the retained rc3 Seyda Neen scenery index and regional BSPs, with
the scale-filter path still present in rc8, found:

| Check | Result |
| --- | ---: |
| Large `flora_bc_tree_*` placements in exterior cell `(-2, -9)` | 7 |
| Large `flora_bc_tree_*` placements in exterior cell `(-2, -10)` | 9 |
| Those placements present in the intermediate scenery index | 16 |
| Unit-scale placements found as sprites in retained regional maps | 5 |
| Non-unit-scale placements skipped by the placement pass | 11 |

Evidence master SHA-256:
`5c3c8c2cbd20e25901b59b3ece33d36b7ef0e3d60ad8d11828bcc61a5ead1647`.
This is a focused retained-output audit, not an inspection of every asset in the
owner's current HDF or an emulator rendering test.

`prepare_quake.py` generates the flora sprite files, then skips any placement
where `abs(scale - 1) > 0.02`. All sixteen calculated sprite origins fall inside
the current scene bounds. The eleven rejected scales range from approximately
1.18 to 2.0; their sprite files exist but their placements do not. The normal
Seyda brush pass excludes flora and preserves the surviving sprite entities,
so it does not replace these skipped placements with brush geometry.

The five surviving placements were matched by model and transformed origin,
deduplicating copies across overlapping maps. Existing sprite entities do not
carry FRMR provenance; the production audit should add explicit reference
identity instead of relying on coordinate matching. The earlier origin-only
`+/-736` explanation is not sufficient for this current failure.

The base master also defines `flora_emp_parasol_*`, but none are placed in these
two named cells. Fix the actual source placements rather than adding guessed
mushroom locations.

Repair work remains open: preserve original per-reference scale through baked
variants or a validated renderer scale implementation. Do not remove the scale
filter and silently draw every tree at scale 1. Recheck transformed bounds,
sprite offsets, rotation/tilt, collision policy and region overlap. The current
region selector uses an origin-centred 96-unit allowance for sprites; replace
that assumption with measured asset bounds for large scenery and test seams.

## Coverage is not the same as catalogue size

The retained world survey accounts for 134,865 measured visual placements and
1,405 unique meshes within its stated filters. Those are survey counts, not
proof of converted, packaged or rendered objects. The `vfXXXX` generator adds
terrain and water outside the detailed towns; it does not already contain all
the island's scenery waiting for a visibility switch.

For each in-scope placement, trace selection, conversion, packaging and runtime
registration. Assign a reason at the first failed or intentionally deferred
stage. Keep source-state exclusions, unsupported behavior, source absence,
conversion errors, scale omissions and region-bound omissions distinct.
Also distinguish a simplified sprite from faithful 3D geometry, and visuals
from collision or interactive behavior. A gallery preview is not evidence
that the object is placed in the world.

Count unique source references independently of their runtime copies. Shared
models and overlapping chunk copies must not inflate coverage. A supported
placement with no terminal result is an audit failure. Explicitly deferred
content remains visible in the report rather than being counted as success.
Publishing a report must not automatically suppress existing actor, collision
or filesystem gates.

## Proposed command: `dbg assetgallery`

Use the same browsing approach as `dbg npcgallery`, with a separate scenery
catalogue. Browse/search original object ID, type and model path. Load one
selected asset at a time in an isolated inspection scene, with a character
beside it for scale. Show:

- Original identity and conversion status, including errors and missing items.
- Native source scale, selected placement scale, dimensions and output format.
- Geometry/texture storage cost and triangle count where meaningful.
- Optional collision and bounds overlays, rotation and next/previous controls.

Use an actual character model or an explicitly labelled height reference. The
legacy `player.mdl` placeholder is not a reliable human-scale reference. Keep a
deduplicated base-model view and allow inspection of selected placement variants.
Unconverted records must remain searchable and visibly unavailable rather than
silently disappearing from the browser.

BSP brush models, alias models and sprites need format-specific loading and
inspection. Verify memory release, lighting, bounds, preview collision and
return-to-game state for each. Gallery selection must not spawn permanent world
objects, execute source scripts, enable quest actors or alter save state.

## Proposed cell-by-cell scenery layer over existing terrain

Near-term goal: retain existing `vfXXXX` topography and import rocks, trees,
plants and other static objects in a separate pass. Original Morrowind `CELL`
records define the work units; generated `vfXXXX` regions are runtime coverage
units and must not be treated as the original cell grid.

Convert a unique source model once, then emit original CELL/FRMR placements into
separate spatially indexed scenery files. A changed cell invalidates its scenery
and intersecting neighbor coverage, not unchanged terrain. If an asset changes,
invalidate all placements/variants that actually depend on it. Cache identities
must include input bytes, transforms/scale policy, converter/settings and format.
Check terrain hashes before and after a scenery-only rebuild to prove reuse.

The runtime needs to draw and unload these prepared layers alongside terrain,
with independent collision structures queried by player, NPC and projectile
traces. Decorative plants can follow an explicit non-colliding policy; rocks,
trees and buildings must not silently lose source-intended support/obstruction.
Do not promise zero rebuilds for geometry already baked into the combined BSP:
that existing path still needs the affected BSP products regenerated. Separate
scenery storage and runtime loading are proposed work, not a flag available today.

Acceptance checkpoint: add one audited source cell beside existing terrain,
retain original position/rotation/scale, test shared-boundary objects, town
ownership, standing contact, visibility, unload/reload and save/restore; compare
terrain hashes unchanged. Extend one cell at a time using coverage reports.

## Proposed regional scenery pass and loading order

Keep completed `vfXXXX` terrain as a reusable input and investigate a separately
generated scenery catalogue and per-region placement manifest. Reuse original
CELL/FRMR coordinates, rotation and scale. Select intersecting model bounds,
including overhanging objects across cell edges, instead of only their origins.
Share geometry by asset identity and deduplicate overlapping reference copies.
Town handoffs need explicit ownership so an existing detailed-town object is
not drawn twice when a surrounding world region becomes resident.

Start with a measured corridor beyond a detailed town. Expand content in these
passes: major landmarks/buildings/bridges; large rocks and trees/mushrooms;
smaller vegetation and static props. This is an implementation priority, not a
replacement for original placements or a mod load order. Source record types
and identities remain authoritative; an interactive door/container must not be
declared behavior-complete merely because its static appearance is present.

At runtime, admit collision and nearby walkable structures before allowing the
player into them; then prioritize large visible silhouettes and nearby smaller
objects within explicit memory and frame budgets. Loading must be bounded and
visibility/distance-aware, with hysteresis at transitions and measured I/O
costs. Do not silently move objects, shrink them, or ignore collisions to meet a
budget. Report deferred visual detail separately.

A separate pass is feasible as a design, but the current engine does not yet
load arbitrary scenery layers alongside terrain. Validate model ownership,
lighting/PVS behavior, traces, lifetime and scene transitions before relying on
that architecture. If a chosen implementation changes the world's combined
collision or visibility representation, rebuild those affected products and
verify them; unchanged terrain bytes alone are not proof of equivalent gameplay.

## Checkpoints and acceptance

1. Create the host catalogue and dependency/placement report, using synthetic
   fixtures for shared models, scales, negative cell coordinates, source
   collisions, deleted references and unsupported features. Inventory first;
   do not eagerly convert the entire game to establish the list.
2. Correct the confirmed eleven tree omissions and prove all sixteen source
   placements are represented with their intended transforms. Audit all affected
   flora, then check the detailed-town seams in the emulator.
3. Add the bounded runtime lookup and gallery. Confirm repeated selection and
   exit restore the original game state without memory growth.
4. Expand regional scenery in measured batches using the same catalogue and
   coverage receipts. Track payload bytes, partition capacity, resident memory,
   conversion time and frame cost before extending coverage island-wide.

Avoid rebuilding unrelated terrain for catalogue-only work. Scenery changes do
require their affected scene/chunk products to be regenerated; engine/image-only
recovery cannot insert placements into old BSPs. Dependency-based reuse remains
part of the [build toolkit roadmap](BUILD_TOOLKIT_ROADMAP.md).
