# CHIM-MOLAG-MEMORY-38

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 12 October 2026, in v0.0.38-dev3 |
| Where | Tel Uvirith, Molag Amur, exterior cell (10,1), CHIM frame x+10/y+01 |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.38 |
| Severity | high: Prevents complete Molag Mar exterior CHIM coverage under the unchanged memory budget. |
| Family | CHIM world streamer (`chim-streamer`) |
| CHIM | Performance ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | Molag Mar per-cell conversion |
| From commit | source 3fac049, engine 3fac049, CHIM world 3fac049 |
| CHIM engine version | CHIM 0.2.0, engine 3fac049, world format unknown |
| Unknown because | Exact serialized format revision must be read from the retained artifact; CHIM representation is confirmed. |

<!-- END GENERATED FACTS -->

15 October 2026 current checkpoint: 15 October 2026: the complete 369-frame successor passes structural, active-heap, scoped stair and exact 928 zone-recheck gates; 17 serialized actor contacts also pass their scoped check. Model measurements, 14 sprite provenance bindings and nine Vivec boundary findings remain under review. Native and package acceptance remain pending. See [CHIM-MODEL-ARENA-RESERVE-41](CHIM-MODEL-ARENA-RESERVE-41.md#zone-actor-and-model-checkpoint-15-october-2026).

<!-- contents start -->
## Contents

- [Symptom and location](#symptom-and-location)
- [How it happened and why it was not caught](#how-it-happened-and-why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Maintainer evidence reconciliation, 13 October 2026](#maintainer-evidence-reconciliation-13-october-2026)
- [Regular-builder integration, 13 October 2026](#regular-builder-integration-13-october-2026)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

15 October 2026: complete369-frame successor structural/source and active-heap checks pass after recipe and point-hull allocation repairs. Maximum active heap6,072,752 of6,242,304bytes. Scoped369-frame stair gate also passes with14,960advisory failures retained. Updated zone recheck, actor/seam/model/sprite equivalence, native and package gates remain pending. See [CHIM-MODEL-ARENA-RESERVE-41](CHIM-MODEL-ARENA-RESERVE-41.md#complete-suite-and-world-checkpoint-15-october-2026).

15 October 2026, v0.0.41 candidate: recipe repair converted all four affected frames with structural PASS. Three still failed the unchanged memory gate (peaks 6,957,632; 6,939,952; 6,644,768 bytes for (10,0), (10,1), (9,2)); (11,0) passed at 5,875,568 bytes. The separate placed-model reserve repair passes all four on identical world bytes. A complete successor world and recipe/model/sprite equivalence and native checks remain pending. See [CHIM-MODEL-ARENA-RESERVE-41](CHIM-MODEL-ARENA-RESERVE-41.md).

15 October 2026: 15 October 2026, v0.0.41 candidate: recipe repair converted all four affected frames with structural PASS. Three still failed the unchanged memory gate (peaks 6,957,632; 6,939,952; 6,644,768 bytes for (10,0), (10,1), (9,2)); (11,0) passed at 5,875,568 bytes. The separate placed-model reserve repair passes all four on identical world bytes. A complete successor world and recipe/model/sprite equivalence and native checks remain pending. See [CHIM-RECIPE-APRON-SCOPE-41](CHIM-RECIPE-APRON-SCOPE-41.md).

Location correction, 13 October 2026: the inspected cell (10,1) is Tel Uvirith
at Uvirith's Grave in Molag Amur, not Molag Mar. The established bug ID and
diagnostic filenames are retained for traceability. This correction does not
change the issue status or establish package/native acceptance.

## Symptom and location
Tel Uvirith exterior cell (10,1) converts to CHIM but fails the active-ring heap gate: 11,970,016 bytes against 6,242,304 bytes, a 5,727,712-byte shortfall. The sampled peak is frame-local (352,-352). The load-ring estimate is 12,262,160 bytes. No native crash is established.

## How it happened and why it was not caught
Whole-region conversion includes a dense set of Telvanni model variants. Earlier full-game selection did not establish playable CHIM acceptance for this cell. Modelled drawn geometry accounts for 9,812,312 bytes and model collision for 1,697,560 bytes at the peak. Largest individual blocks include tilted ex_t_root_xl_02 variants (676,496 and 676,320 bytes) and ex_t_slavemarket (616,240 bytes). Player-tower sprout variants are also present; their original script-controlled visibility is a separate unresolved feature-coverage question, not permission to omit them.

## Reproduction
At source 3fac049, convert original exterior cell (10,1) with the per-cell CHIM workflow, compiled terrain hulls, original terrain references and default memory settings. Inspect the heap report after format, hull and stair audits.

## Repair
The regular builder now carries the completed-stage selection, scoped mesh
recipes and sprite replacements described below. Full-world conversion at
source c2c2050 passes the unchanged active-ring heap gate for this cell; final
image and native acceptance remain pending. No memory-budget waiver or
omitted-cell workaround is used. AmiQuake zone.c Cache_Alloc uses aligned blocks
and LRU eviction; CHIM's map-start bank in chim_world.c fixes the available
working set. Eviction alone cannot fit simultaneously required models, so the
repair reduces the required resident geometry rather than relying on eviction.

## Verification
Full-world conversion at c2c2050 records 5,587,136 active-ring bytes and
5,758,640 load-ring bytes against a 6,242,304-byte budget for Tel Uvirith.
The full-world format validation and host zone-allocator walk pass. These are
offline checks, not final-image Hunk/sprite accounting or native acceptance.
The chronology below retains the earlier failed candidates and their limits.

Format, terrain/hull seams, sky-bank texels and hull policy pass. Stair audit: 1,319 tested, zero gating failures, 81 advisories. Memory fails at the values above. Native comparisons, script visibility, repaired frame validation and final-package presence are pending.

## Prevention
Gate every selected exterior frame against the unchanged target-ABI memory budget. Keep asset accounting, offline geometry checks, native evidence and packaged coverage separate.

12 October diagnostic follow-up: the existing 512-unit model-cut setting was tested with unchanged original references and memory budget. The shortfall increased from 5,727,712 to 6,397,552 bytes (669,840 bytes worse). Format, seams and stair checks still passed, but the memory gate failed. This setting is not adopted. All 123 original regional cells converted; 122 pass measured offline audits, with (10,1) remaining held. Exact original-reference reconciliation found 14,201 converted and 961 deferred references out of 15,162, with no missing IDs or transform/type discrepancies. Final package and native checks remain pending.

12 October script and topology investigation: original Stronghold scripts control 139 references in this cell. Their predicates enable respectively 0, 3, 9, 18, 53, 65 and 106 of these references at stages 0 through 6; the event-dependent foreman script is excluded from those counts. These are reference counts, not measured memory savings. Several heavy root and sprout models belong to mutually exclusive construction stages. The unchanged baseline still counts the resident models together. Its two largest root variants each contain 872 compiled faces and 2,600 BSP nodes, plus 13,654 and 13,655 clipnodes. This identifies both conditional-content and compiled-topology contributors; it does not establish a native fix. Effective initial runtime state, phase transitions, render/collision parity and matched OpenMW evidence remain pending. All original assets remain retained.

12 October stage-residency diagnostic: matched original-game views at requested Stronghold stages 0 and 6 show the structure absent and present respectively; logged camera position, yaw, base pitch and field of view agree. A hypothetical residency calculation retaining catalogue allocation and unchanged on-disk assets estimates active-ring peaks for stages 0-6 of 825,344; 1,376,976; 1,489,216; 5,307,184; 5,929,168; 7,141,088; and 7,638,112 bytes. The budget remains 6,242,304 bytes. Stages 5 and 6 still exceed it by 898,784 and 1,395,808 bytes. These are diagnostic estimates, not passing production audits: activation metadata, transition overlap, adjacent-frame demand and deferred actors remain unaccounted. Proposed repair needs both correct stage-aware drawing/collision/residency and further model-memory reduction for the later stages. Existing CHIM Hidden handles opening-story drawing/collision, while Need requests the chunk model list without that filter; hiding alone cannot establish the proposed saving. No engine change, native fix or packaged acceptance is claimed.

12 October representation follow-up: stage6 model allocation is led by planes (2,168,896 bytes), render nodes (1,171,232), surfaces (1,075,344), texture mappings (981,456), and standing clipnodes (961,664). Existing exact plane deduplication removes only two duplicate records, saving 48 target bytes; the stage6 diagnostic still exceeds the budget by 1,395,760 bytes. All stage6 planes are referenced, and there are no exact duplicate texture-mapping records. These routes cannot close the shortfall. Existing AmiQuake R_RotateBmodel caches full rotation bases, but CHIM placement records and traces presently carry yaw; sharing arbitrarily tilted/scaled visual variants would need explicit format, bounds and rendering work, with separate collision correctness and measured CPU acceptance. It is a candidate investigation, not an implemented optimization.

12 October render-geometry diagnostic from source 3fac049: baseline conversion has 56,830 placed
and 41,713 stored faces with an 11,970,016-byte modelled active-ring peak. A bounded
`meshopt+merge` override reaches 51,435 placed, 36,710 stored and 11,113,744 bytes. Applying
an opt-in terrain-aware cut after that reaches 49,925 placed, 35,466 stored and 10,964,336
bytes. The cut alone removes 1,510 placed and 1,244 stored faces, clips 918 stored crossing
faces and saves a modelled 149,408 bytes. It leaves 507 terrain faces and 169,776 collision
clipnodes at their previous counts. A resolved-graph comparison finds equal collision plane
tuples, clipnode children and hull 1–3 roots for all 88 models; native movement remains untested.
The cut uses exact ground triangles, a 0.5-unit contact overlap, and guarded treatment of
shared and lightmapped faces. Format, seams, six doors and 1,363 stair steps pass offline
(zero failures, 86 advisories); 13 existing terrain-cull tests pass. The resulting peak still
exceeds the 6,242,304-byte budget by 4,722,032 bytes. Model cutting has not been combined
with this trial. Matched FS-UAE/OpenMW images, native gameplay and wider conversion acceptance
are pending. The maintainer repeatedly points to lantern assemblies as density hotspots; one
original streetlight mesh has 149 faces and a separate curved support has 264, but their
relative memory cost is not established.

12 October combined stage-residency estimate for the optimized and clipped candidate:
stage 0–6 active-ring peaks are 1,115,744; 1,451,376; 1,541,344; 5,113,632;
5,721,376; 6,890,304; and 7,329,328 bytes. Stages 5 and 6 remain 648,000 and
1,087,024 bytes over budget. This is a hypothetical filter of original Stronghold
predicates, not implemented engine residency. Transition overlap, metadata,
neighboring frames and deferred actors are unaccounted, and native acceptance is pending.

12 October lantern and subdivision diagnostics: 18 placed streetlights share one
149-face, 26,592-byte resident model. Eighteen 264-face curved supports use three
37,920-byte variants (16, 1 and 1 placements). Together they contribute 7,434
placed faces and 140,352 bytes summed across distinct resident models, unchanged
by the optimizer and terrain cut. Textures and placement records are excluded;
this is not a stage-specific peak and does not close the memory gap. An opt-in
512-unit model tiling trial at 256-unit grain leaves 49,925 placed and 35,466
stored faces unchanged but raises model count 88 to 96, clipnodes 169,776 to
175,324 and the all-stage modelled peak 10,964,336 to 11,634,544 bytes
(+670,208). Hypothetical stage 6 rises from 7,329,328 to 7,999,536 bytes,
increasing its budget excess from 1,087,024 to 1,757,232 bytes. This setting
is not adopted; other subdivision methods remain untested.

12 October targeted tiling diagnostic: cutting root and slavemarket models at
128 units after optimization and terrain clipping leaves 49,925 placed and
35,466 stored faces, but increases models 88 to 174 and clipnodes 169,776 to
193,228. The modelled all-stage peak rises from 10,964,336 to 13,282,192 bytes
(+2,317,856) despite the largest block falling from 645,312 to 327,360 bytes.
Three hull-limit checks fail (maximum depth 3,081). This setting is rejected;
it says nothing about layout-sector division or every subdivision strategy.

12 October stronger all-mesh diagnostic: ratio cap 0.2 and meshoptimizer error
bound 0.01 of mesh diagonal (earlier 0.5 and 0.0025), with locked borders and
extent guard retained, were applied to all 44 nonterrain source meshes before
the terrain cut. Terrain meshes and LAND remain unchanged. The candidate has
30,985 placed and 21,087 stored faces, 507 terrain faces, 169,776 collision
clipnodes and a 9,045,776-byte modelled all-stage peak. That is 25,845 fewer
placed faces (45.48%) than the original and 18,940 fewer than the earlier
optimized-plus-clipped trial, but still 2,803,472 bytes over the budget.
All 88 resolved collision graphs match the earlier clipped candidate. Offline
format, terrain seams, hull policy, six doors and 699 stairs pass (zero stair
failures, 41 advisories); 16 mesh-method regressions pass. The stair sample
count differs from the earlier trial, and native movement and visual A/B are
pending. A hypothetical Stronghold residency filter puts stages 0–5 under
budget, stage 5 at 5,941,424 bytes (300,880 headroom), and stage 6 at
6,242,384 bytes at one position, **80 bytes over**. The engine does not yet
load by stage; transition overlap, neighbors, metadata and deferred actors
are unaccounted. This is not a memory-fit pass, native fix or deployable build.

12 October compiled lantern and fixed-stage follow-up: one lantern model shared
by 18 placements changes from 149 polygons / 166 fan triangles / 26,592 zone
bytes to 20 / 32 / 9,680. Each of three hook variants changes from 264 /
264 / 37,920 at baseline, through 158 / 158 / 23,504 in the stronger optimizer,
to 66 / 66 / 10,960 in the handcrafted trial. The compiled cell changes from
30,985 placed and 21,087 stored polygons to 27,007 and 20,682; active peak
falls 9,045,776 to 8,988,352 bytes, still 2,746,048 over budget. Model bytes
are shared by variant, not multiplied by placements. The 88 resolved standing
collision graphs match, but native movement and lantern appearance remain
unaccepted. The separate fixed-stage-6 build excludes 33 inactive construction
placements and has 120 placements, 59 models and 19,354 placed polygons. Active
peak 6,167,056 leaves 75,248 bytes under the old budget, while load peak
6,590,736 exceeds it by 348,432. Source-parity validation flags the omissions;
runtime stage transitions are not implemented. A door geometry-only sweep
reduces the original 822 triangles to the compiled 408 and trial 310, 282 or
260 triangles at higher error bounds. Those extra sweep variants were
geometry-only and were not credited with heap savings.

12 October ash-tree sprite trial on that fixed-stage candidate: five placements
from four source models held 2,632 render polygons / 2,744 fan triangles.
Replacing their visuals with four shared sprites changes the summed model
blocks from 397,488 to 34,672 bytes while retaining collision; all 59
resolved collision graphs match the preceding candidate. Active peak changes
6,167,056 to 6,032,032 bytes (210,272 under the old 6,242,304 budget), but
load peak changes 6,590,736 to 6,264,336 bytes, still 22,032 over. Sprite
files total 41,903 bytes; their separate Hunk allocation has not been charged
as runtime residency, so this is not a complete memory pass. A 31-second
native diagnostic loaded and ran with a visible tree sprite. Its capture is
poorly framed; matched original-game appearance and normal movement remain
pending. No public package or production fix is claimed.

12 October compiled door-panel candidate: two source types cover six placements
through four distinct transformed models. Each new double-sided panel has two
polygons / 24 fan triangles. Door 01 changes from 98 polygons / 134 triangles
and 15,232 resident bytes to 2 / 24 and 1,712 bytes. Three door 02 variants
change from 42 polygons / 70 triangles each and 7,552 / 7,392 / 7,552 bytes
to 2 / 24 each and 1,872 / 1,712 / 1,872 bytes. All 59 resolved collision
graphs match the preceding candidate. Modelled active peak changes from
6,032,032 to 6,008,192 bytes; load peak changes 6,264,336 to 6,240,496.
Against the old 6,242,304-byte room, load has only 1,808 bytes nominal
headroom. Separate sprite Hunk allocation has not been deducted, so this is
not a proven memory fit. Native door use, appearance and matched reference
views remain pending; no public release acceptance is claimed.

12 October door native diagnostic: the test map loaded and stayed running for
a 33-second scripted FS-UAE session, and both replacement panels were visible.
The first image is very close and pixelated; the second is an oblique view with
surrounding geometry gaps whose cause is unknown. Noclip was used to position
the camera. Better framed target captures, matched original-game comparison,
normal door interaction and movement/collision checks remain pending. This
load/run result does not accept the candidate as fixed or ready to ship.


## Maintainer evidence reconciliation, 13 October 2026

The following maintainer screenshot evidence was visually reviewed. Original images
remain in the private evidence archive; identifiers bind this report to those
originals. This records reported symptoms and comparison controls, not a repair
or runtime acceptance. Missing build or pose information remains unknown.

- `OWNER-20261012-201830`: SHA-256 `8203745ca13ce7a2cd83eec7b9feac8abb4b7496b7d9b4244037e2ce23d8df17`. Toolkit model-family chart, ex_t_root_xl_02 4.71 MiB; not a native heap measurement.

## Regular-builder integration, 13 October 2026

The first full-margin integration exceeded the active-ring budget by 226,192
bytes (6,468,496 against 6,242,304). Its recipe had inherited the ordinary
0.25% mesh simplification tolerance instead of the retained prototype's 1%
tolerance for remaining scenery. This restored thousands of render faces.
The exact prototype-to-integration allocation comparison isolated the mismatch;
checking only the eleven explicit mesh replacements had not covered that default.

The corrected Tel Uvirith recipe explicitly carries its 1% tolerance and 0.2
ratio cap. The ordinary converter default, terrain profiles and original
collision geometry remain unchanged. The regular full-margin conversion now
passes with active-ring peak 5,794,080 bytes and load-ring peak 6,108,240 bytes
against the unchanged 6,242,304-byte budget. Format, terrain seams, texture-bank,
hull-chain and stair audits pass; 361 stair/ramp walks have zero gating failures.
The original normal-walking access report still requires native reproduction.

An isolated production frame-map binding check carries five sprite placements
using four assets totaling 41,903 on-disk bytes, and records their Hunk reserve.
It projects the selected-cell directory rows; final-image routing and aggregate
memory still need validation. Stage 6 retains 120 converted references and
excludes 33 script-disabled construction references; five actors remain deferred.
No final-image, native traversal, delivery or maintainer acceptance is established.

Prevention: compare both named replacement profiles and recipe defaults against
the retained successful geometry; test full terrain margins before image assembly.

Final full-image verification, 13 October 2026: completed-stage Tel Uvirith and all four sprite assets passed HDF readback. Both teleport aliases reach its CHIM frame. Active-ring memory is 5,596,320 bytes and load-ring memory 5,767,824 bytes against 6,242,304 bytes. Arrival and scoped scene verified; normal staircase traversal and maintainer acceptance remain open.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: CHIM world streamer (`chim-streamer`). The CHIM streamer keeps Quake's visibility effective and its renderer counters must not get worse. See [families](README.md#families).

- [BUILD-CHIM-HEAP-GATE-LATE-36](BUILD-CHIM-HEAP-GATE-LATE-36.md): The CHIM heap gate runs after the stair walk: a ring over the zone is found 69 minutes late
- [BUILD-CHIM-STAIR-WALK-UNCACHED-36](BUILD-CHIM-STAIR-WALK-UNCACHED-36.md): CHIM frames are stair-walked again on every build: about 69 minutes for 270 frames
- [BUILD-CHIM-VALIDATE-LATE-36](BUILD-CHIM-VALIDATE-LATE-36.md): The CHIM world is validated only after the whole chim stage: a bad chunk is found 45 minutes in
- [BUILD-IMAGE-CHIM-NATIVE-TOWN-36](BUILD-IMAGE-CHIM-NATIVE-TOWN-36.md): The image step of a CHIM-native town read legacy region maps that are never built: the Bitter Coast test build failed at the end of its image step on maps/bc000.bsp
- [BUILD-LEGACY-CHAIN-DEFAULT-36](BUILD-LEGACY-CHAIN-DEFAULT-36.md): Builds still prepared CHIM towns through the legacy region-map chain by default, and a retired flag (--legacy-area) was accepted with only a warning
- [CHIM-ACTOR-RING-33](CHIM-ACTOR-RING-33.md): A scripted actor step could move the CHIM chunk ring to the actor
- [CHIM-ACTORS-OUTSIDE-RING-33](CHIM-ACTORS-OUTSIDE-RING-33.md): Actors outside the CHIM ring have no terrain collision
- [CHIM-ALIAS-STATIC-HUNK-35](CHIM-ALIAS-STATIC-HUNK-35.md): Streamed alias statics load into the cache mid-map without being counted in the map's Hunk rest
- [CHIM-ANIM-TEXTURES-33](CHIM-ANIM-TEXTURES-33.md): Animated shared textures in CHIM show only their first frame
- [CHIM-ARENA-MEMORY-33](CHIM-ARENA-MEMORY-33.md): The Vivec Arena does not fit the CHIM zone: canton bodies are single models of 1.4-2.5 MB
- [CHIM-BALMORA-LIGHT-ROOM-33](CHIM-BALMORA-LIGHT-ROOM-33.md): Balmora's CHIM active ring has 2,528 bytes of headroom: no stored lighting fits
- [CHIM-BORDER-COLLISION-33](CHIM-BORDER-COLLISION-33.md): Collision near CHIM chunk borders ignores the neighbour chunk's ground
- [CHIM-BRUSH-BAD-DATA-35](CHIM-BRUSH-BAD-DATA-35.md): A damaged or truncated CHIM model or terrain image ends the game (Sys_Error) instead of failing that load
- [CHIM-CHUNK-LOAD-FAIL-33](CHIM-CHUNK-LOAD-FAIL-33.md): Balmora chunks fail to load on CHIM, never recover, and leave holes without ground
- [CHIM-COMPILED-HULL-SHORT-36](CHIM-COMPILED-HULL-SHORT-36.md): Compiled standing hulls lose pieces: terrain up to 3 units below the ground, Hlaalu houses up to 139 units
- [CHIM-DETAIL-BUDGET-SEAM-UNAUDITED-36](CHIM-DETAIL-BUDGET-SEAM-UNAUDITED-36.md): The seam-tear audit does not measure the CHIM detail budgets: the Vivec statues at 900 of 5,451 triangles are not checked for opened seams
- [CHIM-DEV3-MAPLOAD-CRASH-36](CHIM-DEV3-MAPLOAD-CRASH-36.md): v0.0.36-dev3 image: the emulator exits about 2 s after a map load (JIT preset); the game stops advancing on the cycle-exact preset
- [CHIM-EFRAG-UNCAPPED-35](CHIM-EFRAG-UNCAPPED-35.md): CHIM placements link efrags without a cap: a large ring can reach the efrag pool limit and end the map (Host_Error)
- [CHIM-EMPTY-POINT-HULL-36](CHIM-EMPTY-POINT-HULL-36.md): A CHIM model without collision has no point-hull node: the engine reads it as solid, or refuses it on load
- [CHIM-FAR-BAND-GAP-36](CHIM-FAR-BAND-GAP-36.md): From a CHIM area's border the ground ends at the frame edge: up to 476 units with no land before the fog plane
- [CHIM-FAR-OBJECTS-33](CHIM-FAR-OBJECTS-33.md): Houses between the CHIM ring and the legacy overlap depth are missing from the fogged horizon
- [CHIM-FAR-TERRAIN-33](CHIM-FAR-TERRAIN-33.md): A CHIM frame has no distant ground: beyond the active ring the land is missing (empty valleys, Vivec not visible from the world)
- [CHIM-FERN-NCO-SOLID-38](CHIM-FERN-NCO-SOLID-38.md): Fire ferns marked NCO become solid in CHIM mesh conversion
- [CHIM-FRAME-COORD-RANGE-33](CHIM-FRAME-COORD-RANGE-33.md): One Vivec city frame does not fit Quake's coordinate range (network coordinates are 1/8-unit shorts)
- [CHIM-FRAME-EDGE-EFRAG-CRASH-36](CHIM-FRAME-EDGE-EFRAG-CRASH-36.md): R_StoreEfrags: Bad entity type 270440 ends the game: a leaf link to an entity whose model is NULL (normal play in Seyda Neen; noclip past the Vivec frame edge)
- [CHIM-FRAME-GROUND-TRACE-38](CHIM-FRAME-GROUND-TRACE-38.md): CHIM image assembly exceeds collision traversal guard in cell 6,-5
- [CHIM-FRAME-WORLD-BOUNDS-33](CHIM-FRAME-WORLD-BOUNDS-33.md): A CHIM frame map must carry an empty world whose bounds cover the frame
- [CHIM-FROZEN-ACTORS-33](CHIM-FROZEN-ACTORS-33.md): Frozen CHIM actors: projectiles stop mid-air and timers stop
- [CHIM-GRAFT-FAIL-NO-FLOOR-35](CHIM-GRAFT-FAIL-NO-FLOOR-35.md): A CHIM map whose frame world cannot start loses its far terrain too: the player may spawn over void
- [CHIM-GRAFT-REPACK-EMPTY-33](CHIM-GRAFT-REPACK-EMPTY-33.md): A frame world repack without room for the whole ring drops every chunk: the world vanishes and the player falls under Seyda Neen
- [CHIM-HANDOFF-POPIN-36](CHIM-HANDOFF-POPIN-36.md): Most of a CHIM area's objects are not drawn from the legacy side and appear at the handover (Gnaar Mok, a Dwemer ruin)
- [CHIM-HARVEST-NAMING-33](CHIM-HARVEST-NAMING-33.md): A town-wide CHIM harvest catalogue does not fit the name and size limits
- [CHIM-HARVEST-REMOVED-MAPS-33](CHIM-HARVEST-REMOVED-MAPS-33.md): A pure CHIM image stops at the save fingerprint: harvest catalogues of the removed town region maps have no matching map
- [CHIM-HEAP-INT-MATMUL-36](CHIM-HEAP-INT-MATMUL-36.md): The CHIM heap scan multiplies 0/1 tables as int32: numpy's plain loop, 6 of 24 cores, about 60 s per check
- [CHIM-HIDDEN-FACES-33](CHIM-HIDDEN-FACES-33.md): CHIM draws placed-model faces under the terrain that the recorded Seyda Neen region maps cull
- [CHIM-HULL-CHAIN-COST-33](CHIM-HULL-CHAIN-COST-33.md): Large placed models collide through one long chain of convex pieces: a trace near the Arena canton walks about 6,600 planes
- [CHIM-HULL2-33](CHIM-HULL2-33.md): CHIM terrain uses the player hull for large entities
- [CHIM-LAVA-RECOVER-38](CHIM-LAVA-RECOVER-38.md): Debug recovery fails to find a clear spawn after lava contact
- [CHIM-LAVA-TERRAIN-AUDIT-37](CHIM-LAVA-TERRAIN-AUDIT-37.md): Terrain validation omits lava beds, surfaces and contents
- [CHIM-LEAF-SPAN-33](CHIM-LEAF-SPAN-33.md): 160 of 1,488 Balmora placements span more than 16 leaves
- [CHIM-LIGHT-CONTENTS-33](CHIM-LIGHT-CONTENTS-33.md): Actor lighting and water contents ignore CHIM chunks
- [CHIM-MEASURE-EMPTY-FRAME-33](CHIM-MEASURE-EMPTY-FRAME-33.md): CHIM world measurement stops on a frame without models (every empty sea cell)
- [CHIM-MESH-PROFILE-SPLIT-36](CHIM-MESH-PROFILE-SPLIT-36.md): Seyda Neen converts the same meshes with other profiles than the other CHIM areas (texture size 64 against 32, no surface collision rule), so they are stored twice
- [CHIM-MIPTEX-OFFSET-UNCHECKED-35](CHIM-MIPTEX-OFFSET-UNCHECKED-35.md): CHIM texture mip offsets are taken from disk unchecked: a wrong offset makes the rasterizer read past its block
- [CHIM-MODEL-ARENA-RESERVE-41](CHIM-MODEL-ARENA-RESERVE-41.md): Placed CHIM models reserve renderer nodes that their point-hull loader never allocates
- [CHIM-PACK-DIRS-33](CHIM-PACK-DIRS-33.md): CHIM pack directories are fully resident and would grow to about 400 KB for the island
- [CHIM-PACK-LRU-STREAM-35](CHIM-PACK-LRU-STREAM-35.md): A streamed model keeps a sector file handle the four-file cache may close: the next stream step reads a closed file
- [CHIM-PAYLOAD-PARITY-33](CHIM-PAYLOAD-PARITY-33.md): The CHIM world misses the image step's edits to Balmora (harvest mushrooms, town flora)
- [CHIM-PREDICT-VIVEC-LOW-36](CHIM-PREDICT-VIVEC-LOW-36.md): The CHIM memory predictor under-predicts every Vivec district frame by 28-54 %: Vivec architecture decodes to 1.3-2.3 times the bytes per triangle it was fitted on
- [CHIM-PVS-HOLLOW-33](CHIM-PVS-HOLLOW-33.md): Chunk visibility culls almost nothing in Balmora: houses have hollow collision shells
- [CHIM-READ-BUDGET-33](CHIM-READ-BUDGET-33.md): CHIM per-frame read budget can be exceeded by a whole lump
- [CHIM-REBUILD-COST-33](CHIM-REBUILD-COST-33.md): Each CHIM crossing rebuilds the whole frame world; the cost is not measured
- [CHIM-RECEIPT-COMMIT-33](CHIM-RECEIPT-COMMIT-33.md): CHIM world receipts do not record the commit the world was built from
- [CHIM-RECIPE-APRON-SCOPE-41](CHIM-RECIPE-APRON-SCOPE-41.md): Regional aprons lose original-cell visual recipes and regress the memory gate
- [CHIM-REGION-DIVIDED-CELLS-36](CHIM-REGION-DIVIDED-CELLS-36.md): Most converted land cells cannot switch to CHIM inside the open world: the legacy builder split them over several maps and a region frame replaces exactly one
- [CHIM-REGION-MARGIN-STORAGE-36](CHIM-REGION-MARGIN-STORAGE-36.md): One-cell CHIM region frames store about 3.5 times their cell's terrain (the terrain-only margin)
- [CHIM-REGION-POCKET-TOWN-CELLS-42](CHIM-REGION-POCKET-TOWN-CELLS-42.md): The legacy-pocket rule counts cells wholly inside a town frame as legacy: CHIM region cells around a town are left out for nothing
- [CHIM-SEYDA-ACTOR-CONTACT-33](CHIM-SEYDA-ACTOR-CONTACT-33.md): rc1 image step refuses Seyda Neen's CHIM frame map: six actors stand 0.8-3.3 units off the CHIM ground
- [CHIM-STATIC-PLACE-HOST-ERROR-35](CHIM-STATIC-PLACE-HOST-ERROR-35.md): Bad flora data at CHIM chunk activation ended the session with zone locks held; the next map then stopped the program
- [CHIM-STATICS-FALLBACK-41](CHIM-STATICS-FALLBACK-41.md): A frame map with more than 512 streamed statics crashes when its CHIM world cannot load, instead of running without its chunks
- [CHIM-STITCH-SHORELINE-36](CHIM-STITCH-SHORELINE-36.md): A CHIM area in the legacy world has no shoreline refinement: steps of up to 28 units at its border
- [CHIM-TERRAIN-GRAFT-33](CHIM-TERRAIN-GRAFT-33.md): CHIM chunk terrain is a brush entity, not part of the world tree, so it does not occlude
- [CHIM-TERRAIN-HULL-BEVELS-33](CHIM-TERRAIN-HULL-BEVELS-33.md): A standing box rests above the ground at convex CHIM terrain edges
- [CHIM-TEXTURE-SPECKS-33](CHIM-TEXTURE-SPECKS-33.md): CHIM-drawn surfaces show bright single-texel specks that legacy frames do not
- [CHIM-TILT-VARIANTS-SPLIT-33](CHIM-TILT-VARIANTS-SPLIT-33.md): Tilted placements each get their own model variant: 39,103 extra model variants on the base island, breaking store-once
- [CHIM-TOWN-HEAP-ROUTED-HULL-36](CHIM-TOWN-HEAP-ROUTED-HULL-36.md): With the routed terrain hull for every chunk, Balmora and Seyda Neen rings no longer fit the CHIM zone
- [CHIM-UNIT-CACHE-RACE-33](CHIM-UNIT-CACHE-RACE-33.md): Two processes storing the same CHIM unit at once: the second rename fails
- [CHIM-UNIT-FP-SOURCE-LAYOUT-33](CHIM-UNIT-FP-SOURCE-LAYOUT-33.md): The same mesh is converted again for every source stage: CHIM mesh unit fingerprints include archive offsets and texture list positions
- [CHIM-VALIDATOR-ORDER-33](CHIM-VALIDATOR-ORDER-33.md): The CHIM validator walk depended on Python string hashing
- [CHIM-VARIANT-YAW-DUPLICATES-36](CHIM-VARIANT-YAW-DUPLICATES-36.md): One CHIM model variant is stored several times: each frame builds it at the yaw of its own first placement
- [CHIM-VIEW-FACES-33](CHIM-VIEW-FACES-33.md): Model faces dominate each Balmora view: the streamer alone does not fix frame rate
- [CHIM-VIEW-LEAF-NO-PVS-35](CHIM-VIEW-LEAF-NO-PVS-35.md): A view leaf without a visibility row draws everything, with no counter saying so
- [CHIM-WINDOW-MOUNT-CROSS-CELL-33](CHIM-WINDOW-MOUNT-CROSS-CELL-33.md): A one-cell CHIM frame stops when a window placed in it mounts on a facade placed in the next cell
- [CHIM-WORLD-AUDIT-SCALING-33](CHIM-WORLD-AUDIT-SCALING-33.md): The CHIM world audits grow much faster than the world: the heap gate took 3.6 s for 171 frames, 473 s for 331, and over an hour for 844
- [CHIM-WORLD-INDEX-FILE-LIMIT-36](CHIM-WORLD-INDEX-FILE-LIMIT-36.md): The engine refuses a CHIM world index with more than 4096 file rows; the dev3 coast world has 7,236, so every CHIM frame map fails
- [CHIM-ZONE-RELEASE-FLICKER-42](CHIM-ZONE-RELEASE-FLICKER-42.md): Full CHIM zone: distant buildings pop in and out while standing still, and the retry costs frames
- [CHIM-ZONE-RING-THRASH-33](CHIM-ZONE-RING-THRASH-33.md): Balmora's chunk ring does not fit the default 6 MiB CHIM zone, so the cache thrashes
- [CHIM-ZONE-TMP-NOEXEC-33](CHIM-ZONE-TMP-NOEXEC-33.md): The CHIM zone walk gate cannot load its host library when /tmp is mounted noexec
- [CHIM-ZONE-UNSATISFIABLE-EVICT-35](CHIM-ZONE-UNSATISFIABLE-EVICT-35.md): The CHIM zone evicts every unlocked block for a request no free run can hold
- [CHIMPORT-OCEAN-LAND-41](CHIMPORT-OCEAN-LAND-41.md): 98 seabed cells (land records entirely under water) are marked open ocean: CHIMport never plans them and the ocean admission refuses them
- [CHIMPORT-RETRY-LAVA-STALE-SOURCE-36](CHIMPORT-RETRY-LAVA-STALE-SOURCE-36.md): CHIMport --retry-failed cannot rerun a lava cell of the island run: its stored source stage predates the lava conversion
- [CHIMPORT-SEABED-NO-ISLAND-42](CHIMPORT-SEABED-NO-ISLAND-42.md): Seabed cells measured as empty sea lose their island in the tracker: they drop out of the published reference and the build calls them unknown

Related bugs in other categories:

- [CHIM-CELL-FEATURE-LIST-INCOMPLETE-38](CHIM-CELL-FEATURE-LIST-INCOMPLETE-38.md): Cell feature list incomplete: original placements and gameplay support are not reconciled with packaged coverage

<!-- END GENERATED CATEGORY -->
