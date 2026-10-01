# Roadmap and implementation options

Current release: [v0.0.24 - Welcome to Balmora (and Vvardenfell!)](RELEASE-v0.0.24.md).
Next work: resolve the retained placement findings and convert the surveyed
base-game terrain into runtime areas, retaining original cells wherever measured
budgets permit. Solstheim/Bloodmoon and Tribunal are outside this island pass.
The [29 September plan](PLAN-2026-09-29.md) retains historical priorities.

## Balmora interiors and loading

- [x] Convert 43 original Balmora destination interiors, 93 NPC placements and
  80 living voice sets. Native checks cover all 70 exterior round trips and both
  same-room Fighters Guild links. Full services/quests/schedules remain future work.
- [x] Offer frozen-frame sub-cell loading with a small top Loading box; keep
  the existing black-screen method selectable. Implemented in dev3.
- [ ] Profile read/decode stalls and memory ownership before bounded prefetch
  or offloading. Preserve audio servicing and persistent state when releasing
  scene resources. Frozen-frame presentation does not remove synchronous pauses.

## Seyda Neen subdivision

Owner feedback: Balmora's dev3 subdivision works surprisingly well; its exterior
often feels faster than Seyda Neen. Use that successful approach from the first
ship-exit scene. Performance observations remain separate from measured claims.

- [x] Add 25 regular overlapping Seyda Neen regions, a dedicated compact pier
  (`intro_seyda_neen_subcell_pier`, file `intro_docks.bsp`) and ring courtyard.
  Retain complete intersecting objects, stable reference IDs and shared coordinates.
- [x] Keep the accepted frozen frame with a small top Loading... box; retain
  the black-screen choice. Physically remove unreferenced BSP data from files.
- [ ] Complete owner playtest of natural ship/plank/guard/office/courtyard flow,
  bidirectional seams, containment, save/restore and peripheral views.
- [ ] Profile matched views and transition stalls on the owner's weaker machine;
  investigate the view-dependent distance-1000 speed-up. Keep the prison ship's
  interior cost separate. Background loading/prefetch remains future work.

## Future world-coordinate HUD (investigate first; not v0.0.24 work)

- [x] Establish a reversible transform from each runtime scene's local XYZ to
  original Morrowind world coordinates and exterior cell/grid coordinates.
  Check quarter-scale conversion, each area's origin and axis conventions,
  negative-cell boundaries, sub-cell copies and interior identity. Interiors
  must not invent an exterior location when the source has none.
- [ ] After that investigation, add a small console-font XYZ display at the
  upper right, matching the current AmiWind/debug text size. Define what the
  proposed world-map "mini coords" represent before showing them.
- [ ] Support `dbg global coords on/off`, `true/false`, and `1/0`, with the same
  forms through `debug`. Store the setting in game configuration; once the
  feature is implemented it should default to visible within `dbg hud on`.
- [ ] Relate the display to the original exterior-cell grid and the whole-world
  topographic/coverage planning map. Keep this separate from changing gameplay
  coordinates or adding continuous world travel.

## World map, inventory and journal TODO (owner request, 1 October 2026)

The post-RC3 world/map/journal pass has started at the owner's request.
[Current implementation and limits](WORLD_MAP_AND_JOURNAL.md).

- [x] **M: basic full-screen Vvardenfell map.** Show Morrowind and the player's current
  position. Reuse the verified local-to-world transform described above; define
  how interior locations appear without inventing exterior coordinates. Provide
  a clear return to play, keyboard navigation and mouse pan/zoom where practical.
- [ ] **I: inventory.** Show the player character beside their items, with
  readable names, quantities, icons and equipment slots. Support mouse selection
  and equipping/unequipping, with a visible cursor and keyboard alternatives,
  following the original game's interaction style.
- [ ] Connect equipped items to the character preview and persistent player
  state. Verify slot compatibility, quantities and save/load before allowing
  equipment changes; opening either screen must capture input from the world.
- [ ] Measure the map, preview model, item icons and UI memory on the reference
  Amiga profile. Load their resources on demand and release them on close.
- [x] **J: basic dated progression journal and quest links.** Present an open book with a central
  fold and two facing pages, page turning, dated entries and clickable topic/quest
  links. Provide keyboard navigation and a visible pointer, with a route back
  from linked topics to the current spread. Preserve progression and entry order across save/load. Follow the original journal's book
  presentation; use scrollbars for indexes or long topic lists where appropriate.
  Implemented: two-page earned entries, quest filter links and AWS2 history.
  Pending: learned dialogue-topic links, saved reading position, larger quest
  capacity and full original-script progression. Source journal data is DIAL/INFO,
  not XML; the supplied master has no QSTN quest titles.


## Optional field-of-view control

- [ ] Consider an Options FOV slider, subject to measured performance acceptance.
  Keep the owner's preferred **90-degree horizontal Quake FOV as the default**.
  A narrower setting, including 75 degrees, would be an optional preference.
- [ ] Use the existing runtime projection setting; changing FOV does not require
  reconverting assets, rebaking collision or rebuilding maps. It does not change
  the player's dimensions relative to the world and is not a height correction.
- [ ] Benchmark fixed boat, Seyda Neen and Balmora views on the reference profile
  before adopting the slider. Compare frame times, surface/edge work and overflow
  at the proposed limits; wider views can expose more geometry. Proceed only
  without a measurable default-setting regression and with an acceptable cost
  across the supported range. Defer the feature if that condition cannot be met.

## Next implementation milestone agreed 28 September 2026

Maintenance v0.0.20 is retained. v0.0.21-dev1 implements the bounded opening,
character/save and UI prototype; the checkboxes below track full acceptance,
not merely source presence. See [checkpoint limits](RELEASE-v0.0.21-dev1.md).

- [ ] Dock guard route, original CharGenDock dialogue and race-menu speech gates.
- [ ] Race/sex/face/hair selector with rotating head preview and bounded resource use.
- [ ] Authored invisible chargen barriers and their completion-dependent removal.
  Preserve deck/plank/pier/courtyard containment and forward passage together;
  see the persistent state rule in CHARACTER_CREATION.md and journal J015.
- [ ] Census Office interior rooms, door links, Socucius Ergalla, hall guard and
  Sellus Gravius; class, birthsign, review, papers, ring and release logic.
- [ ] Versioned character/attribute state and compact, recoverable save/load;
  manageable named manual saves and player-adjustable autosave history of the
  last X snapshots (not character levels). Deliver save/load together with completed
  Census attributes as the next playable milestone. Compare semantics
  with original ESS/OpenMW, test corruption/interruption and repeated-save growth.
- [ ] Add the unimplemented Silt Strider and driver; keep that content work
  separate from diagnosing the malformed landing geometry at XYZ260/417/30.
- [ ] Keep both intermittent FS-UAE freezes open during the new work.
- [ ] Review compiler warnings on every build and reduce the remaining 93; follow
  the mandatory gate in DEVELOPMENT.md. Preserve full diagnostic evidence.

Source audit, order and acceptance: [CHARACTER_CREATION.md](CHARACTER_CREATION.md).
Save design and pending comparison gates: [SAVEGAME_PLAN.md](SAVEGAME_PLAN.md).

Core world/cell/chunk design: [WORLD_MAPPING_PLAN.md](WORLD_MAPPING_PLAN.md).

## Next world-mapping milestone: entire-world terrain inspection

**First world-expansion milestone after v0.0.24 (owner priority, 1 October):**
build the Vvardenfell main-island topographic map from terrain and its original
textures. Start with the source game's exterior cells and the existing loading
method, then fit Seyda Neen and Balmora into that common world space. This
terrain-first milestone does not imply that every settlement, interior or
gameplay system is complete.

- [x] Catalogue the source exterior-cell grid, bounds, terrain heights, texture
  assignments and water; document the actual cell layout before choosing
  runtime boundaries. Produce a coverage view with both converted towns marked.
- [x] Produce a matching **source polygon-density map ("polymapping")**: count source
  triangles per cell and smaller spatial tiles, including placed
  copies of buildings and other meshes. Show concentrated geometry as a heatmap
  alongside terrain and existing region boundaries. Use it to flag candidates
  for sub-cells, then confirm with visible geometry, collision cost, texture
  residency, peak heap use and transition measurements. Raw polygon count alone
  is a screening tool, not a sufficient runtime budget. Whole-island converted
  BSP costs remain pending; the first survey calibrates against the existing
  89 town regions. See [measurements and private outputs](WORLD_SURVEY.md).
- [ ] Convert and traverse terrain cell by cell, checking texture continuity,
  shared edges, player coordinates and return crossings. Reuse the current
  selectable loading methods and measure memory and stalls on the Amiga profile.
- [ ] Begin with source-cell-sized regions where they fit. Subdivide only after
  geometry, visibility, collision or memory measurements show the need. Reuse
  Balmora's overlap/ownership lessons and canonical actor placements.
- [ ] Investigate logical boundaries in dense settlements, including Vivec:
  bridges between city sections are candidate crossing points, subject to the
  actual source-cell layout, sightlines and measured region budgets.
- [ ] Integrate the existing Seyda Neen and Balmora regions without duplicate
  terrain, shifted origins or broken door/return links. Compare ground height,
  materials, water and collision along every join.
- [ ] Turn the Seyda Neen/Balmora dwelling workflow into reusable conversion
  stages: source-reference inventory, complete building/interior geometry,
  entrance and return links, resident/outfit mapping, canonical initial support,
  and independent packaged-data checks. Carry the documented distant-origin,
  opening, stair and overlap lessons forward. Emit per-cell exception reports
  for review instead of silently dropping troublesome dwellings or placements.

- [ ] Export a topomesh of the **entire map's terrain**, with original exterior
  terrain coverage, global coordinates, source-cell IDs and a missing-data report.
  Preserve the full-detail baseline before creating LODs.
- [ ] Extract and inspect original water levels, coverage and shorelines; do not
  derive the whole world from the current placeholder sea plane.
- [ ] Add a separate terrain-only observer scene/viewer: free camera, coordinate/
  cell readout, water toggle, optional wireframe/boundaries, fog/view distance and
  LOD controls. Exclude NPC/quest/intro activity so geometry can be studied calmly.
- [ ] Compare whole-world overview and detailed terrain patches for LOD error,
  seams, triangle counts, RAM, load time and frame time. Complete source coverage
  must not require complete full-detail native residency. Use findings to choose
  streaming, optional polygonal BSP regions and elevated-view handling.

See [terrain inspection plan](WORLD_MAPPING_PLAN.md#next-milestone-entire-world-terrain-topomesh).


## Recovered follow-up: FREQUENT FLYER BONUS / whole-world scaling harness

Recovered from the surviving conversation after the frozen v0.0.21-dev4
package; documentation/planning only.

- [ ] Add a terrain-only native observer command, proposed as `dbg fly 1`, with
  unrestricted noclip flight over the full Morrowind terrain coordinate space.
- [ ] Start with terrain topology plus ground colour/texture identity where
  practical and a sea-level plane; keep NPCs, quests and normal gameplay out of
  the first benchmark so geometry/residency costs are measurable in isolation.
- [ ] Keep fog active and couple it to actual work rejection/residency policy,
  not only presentation. Measure low and high-altitude flight paths at fixed
  viewpoints and speeds.
- [ ] Expose/select prebuilt terrain LODs and record triangle/edge work, visible
  surfaces, RAM, cache behaviour, loading/offloading stalls and audio deadlines.
  The experiment's central question is: **the mechanics work locally; can they
  scale to the whole world?**
- [ ] Investigate **something akin to Nanite, but on these old pieces of gear**:
  host-precomputed geometry hierarchies/clusters and cheap runtime selection of
  immutable representations. Possible criteria include projected size, distance,
  altitude and fog. No runtime mesh simplification is assumed. Adopt only if the
  total measured cost beats simpler AmiQuake/BSP/LOD handling.
- [ ] Preserve the open-world illusion as an acceptance criterion. Interiors may
  load separately as in Morrowind, but exterior traversal should not degrade into
  gratuitous loading screens merely to satisfy the partitioning strategy.

See [world-scale flight and precomputed geometry experiments](WORLD_MAPPING_PLAN.md#recovered-follow-up-world-scale-flight-and-precomputed-geometry-experiments).

## Fundamental mechanics before attribute effects

- [ ] **Tables, tables, we need more tables:** catalogue character attributes,
  modifiers, skills, quests, globals/script locals, containers/items, NPCs,
  dialogue, world references and persistence. Record sources, types, defaults,
  dependencies, read/write events and save/unload behavior, with unknowns marked.
  Use the shared catalogue to guide conversion/runtime/save schemas and bounded
  memory; see [development notes](DEVELOPMENT.md#tables-tables-we-need-more-tables).

Owner priority, 28 September 2026: establish persistent conditional game state,
reference enable/disable behavior, interaction and dialogue gates, NPC actions,
scene transitions and save/load before expanding what each attribute does in
combat, movement, skills and spell calculations. Keep the character fields and
starting-value work already present. Research later effects using UESP, original
data and OpenMW; record uncertainty and exceptions in the implementation journal.
See [research references](REFERENCES.md#game-mechanics-research).

## UI readability and text scaling

- [x] Add Options controls for existing 16, 14 and 12 px fonts plus the readable
  fallback; preserve every font and size. Start the next playtest at 14 px.
- [x] Move/size the main-menu panel with its font metrics so it clears the
  background title at every supported size. Verify keyboard and mouse hit boxes.
- [ ] Later separate menu, dialogue, journal and book size preferences, with
  measured reflow/pagination and preserved content at each size. Text-heavy scenes
  need readable wrapping and accessible controls rather than clipped paragraphs.
- [ ] Owned TTF inputs may be rasterized on the host into bounded AWF1 atlases.
  Preserve original bitmap-font conversion as well. Book pages and birthsign
  artwork belong in the reading/character UI, with private source assets.

- [ ] Explore the lower screen area for needed status icons and interaction/menu
  controls as those mechanics arrive. Measure against 320x200 output, selected
  font size, dialogue, resource bars and debug coordinates. Establish readable
  priority/reflow before committing to an icon count or permanent layout.

## Opening exterior residency and playtest blockers

- [ ] Close the new Census missing-room and pier-escape reports before treating
  the full opening as accepted; use BUGS.md fixed Y/N/version index.
- [ ] Build a separate opening exterior with configurable radius X around the
  boat/dock/Census route. Include intersecting bounds and complete assemblies,
  all required doors/NPCs/navigation/barriers and enough backdrop for visibility.
  Keep original world coordinates and stable reference IDs. Unload prison before
  this scene, unload it on office entry, load the full town after release; include
  courtyard round trips while still restricted. Preserve globals, script locals,
  actor state and save content identity across both exterior variants.
- [ ] Compare full/reduced scenes at identical cameras for frame time, polygon
  work, resident geometry/textures, peak transition memory and audio continuity.
  Existing radius selection is preprocessing only; the native BSP is resident.
  Avoid loading both exteriors at once. Choose X from coverage and measurements.
- [ ] Audit Census texture resolution and UV/material bindings; use bounded
  per-material quality where close wall art needs it, not universal reduction.
- [ ] Add generic interior hinged doors with source sound, pivot, motion and
  swept collision; retain locked and opening-script-specific gates.
- [ ] Add ambient NPC idle vocalizations/whistling later, with bounded polling,
  distance, cooldowns and priority below active dialogue/intro speech.

## Optional polygonal POI regions

Owner principle: **"the fog is our friend"** for both bounded rendering/loading
work and Morrowind's mystique. Preserve atmosphere when measuring view-distance
tradeoffs; merely fogging still-processed/resident geometry is not the goal.

Horstator's evening proposal, 28 September 2026: [full note](HORSTATORS_JOURNAL_2026-09-28.md#evening--polygonal-poi-regions-if-streaming-is-insufficient).
First use fog-limited visibility to support measured cell/chunk streaming and
offloading, allowing brief pauses at selected crossings. Only if no sane version
of that approach meets the target budgets are explicit region swaps a required
fallback experiment. Fog culling alone does not evict resources from RAM.

- [ ] Add an optional polygonal region recipe around POIs, starting with Seyda
  Neen; allow regions to span original cell boundaries. Keep the original cell
  approach and source mapping intact. Use compiled BSP regions with associated
  resource packs; the earlier "WAD region" shorthand does not prescribe the
  container. No region converter or loader is implemented yet.
- [ ] Plan crossings and inexpensive horizon/tree/canopy backdrops; show a short
  Loading indication during a level swap and restore the matching safe position
  and facing only after collision is ready. Outdoor cell crossings get only a
  minimal upper-center "Loading..." box, not a large overlay window. Preserve
  original-style loading screens for interior/exterior transitions that use them.
  Test both crossing directions.
- [ ] Keep stable reference ownership and persistent state across overlapping
  coverage. Preserve original cell-dependent rules independently of rendering
  regions; no duplicate loot, actors or script execution at seams.
- [ ] Compare memory, peak load scratch/overlap, load duration, frame time and
  audio continuity against the cell/chunk approach. Verify repeated travel,
  save/load, missing-pack recovery and a handoff that does not require two full
  regions in RAM. Adopt only on measured results; retain both recipes.

- [ ] Treat elevated viewpoints and continuous topomap coverage as a major
  acceptance risk for POI regions. Trial a broader/coarser terrain mode above
  configurable height X over local ground; define the actual up-axis, preserve
  world coordinates/state, and test adjacent-region views, descent, collision,
  memory and separate enter/exit thresholds. A height switch alone is not proof
  that hidden boundaries or missing terrain are solved.

## Graphics and performance: crate geometry options

Requested 28 September 2026; add containers using the normal method first.

- [ ] **Type 001 / normal:** preserve the source crate's shape and recognizable
  details through the normal conversion. This is the initial default when crates
  are added, pending measurement.
- [ ] **Type 002 / low polygon:** offer a simple rectangular box with the source
  texture patterns mapped onto its faces, reducing geometry. Retain both methods
  as selectable conversion options; do not silently replace the normal version.
- [ ] Compare matching scenes and camera positions for visual quality, polygon
  counts, memory use, frame time, collision and interaction. Decide whether type
  002 is needed from those results.
- [ ] Later evaluate a streaming/distance hybrid that uses detailed crates nearby
  and simple boxes farther away, with bounded residency and controlled switching.
  Keep container reference identity, inventory, ownership and saved state stable
  across geometry changes; do not duplicate or reset contents during a switch.

## Build parallelism, 29 September 2026

v0.0.23-dev1 implements default dependency scheduling and bounded process workers
for scenery decoding, alias/sprite previews, BSP model geometry/lightmaps, intro actors, character heads and soundtrack
conversion. It preserves single-writer scene assembly, live prefixed output,
per-stage logs, failure propagation and explicit serial mode. Native make and
VIS/LIGHT use the shared budget; Census no longer hard-codes two threads.
See [PARALLEL_BUILD.md](PARALLEL_BUILD.md) for boundaries and measured validation.

Remaining opportunities: individual actor/hand conversion internals, terrain
conversion, final assembly and safe incremental caches.
Measure them before adding workers or changing the conversion recipe.

Next gameplay checkpoints requested by the owner: restore audible intro sea
ambience, verify continuous gameplay music, and cover every Seyda Neen interior
with original door destinations and repeatable entry/exit. Do not mark these
complete from a successful host build.

## Next major milestone: the connected starting area

Owner priority, 27 September 2026: **Seyda Neen exteriors first, then interiors,
then a working local gameplay slice before expansion to other towns.** Complete
the port, lighthouse/islets, bridges, opposing shore, residential connections
and mainland/Silt Strider approach. The strider itself is a desired later visual
landmark; its travel service is a separate task. See the coverage and acceptance
routes in [SEYDA_NEEN_SCOPE.md](SEYDA_NEEN_SCOPE.md).

Inventory town containers alongside scenery now. First preserve their placement,
appearance and collision; then add activation, player/container item transfer and
per-reference state that survives area changes. Resolve ownership, locks, traps,
scripts and leveled contents explicitly instead of silently treating all storage
as free loot. See [CONTAINERS.md](CONTAINERS.md). This system is planned, not
implemented by the current mesh renderer.

Census and Excise is the first town interior **after exterior acceptance**;
the prison-ship interior establishes the opening before that handoff. Load each on
entry and release area-specific exterior resources, retaining compact world and
music state. Measure peak transition memory and repeat entry/exit before adding
more interiors. Host lookup preparation can proceed alongside exterior repairs.

Use the dim opening ship as the first low-light rendering acceptance scene:
test silhouettes, doors, actors, local light falloff, palette banding and readable
UI while measuring lighting/frame cost. Current bright exterior tests are not
evidence that low-light presentation works. See the
[Seyda Neen journal](journals/SEYDA_NEEN.md).

Add a day/night cycle later: persistent game time, exterior sky/fog/ambient
transitions, supported local lights and separate interior lighting. Start with
host-baked lighting/lookup candidates and measure memory traffic and update cost.
Time progression, waiting/saving and time-dependent NPC/quest conditions need
explicit behavior; changing screen brightness alone does not implement them.
Include dawn/day/evening/dusk/night debug presets, exact-hour and freeze controls.
Test locally converted night-sky textures as a low-cost backdrop, then moons/clouds
within measured budgets. Include a small precomputed gradient sun disc, following
audited original timing and correctly occluded by scenery. Add cheap warm
dawn/dusk horizon gradients centered on that same solar direction. This is an impression of lighting, not global illumination.
See [day/night and sky plan](DAY_NIGHT_AND_SKY.md); these commands are not implemented yet.

Record verified asset mappings, implementation ideas, rejected approaches and
symptom/cause/fix/version/regression checks in the
[implementation journal](IMPLEMENTATION_JOURNAL.md). Keep performance history
and local/user acceptance evidence linked rather than replacing their records.

Later combat presentation research: identify the owner's Nexus mod reference
that reportedly visualizes failed attack rolls as dodges/blocks. Preserve the
dice-roll rules and distinguish cosmetic responses from actual gameplay blocks.
Study its behavior, then implement independently without copying the mod's code
or assets. It remains unnamed/unverified; see [implementation ideas](IMPLEMENTATION_IDEAS.md).

## Checkpoint-014 delivered work and next acceptance routes

- Delivered Nord male first-person hands, draw/sheath with F and a visual punch
  on primary attack; preserve walking bob. Hit tests, stamina, damage and enemy
  reactions remain a separate combat milestone.
- Escape opens a pause menu with Return and confirmed Exit; New, Save, Load and
  Options are visible but disabled until implemented. Keep shell `amiwind`
  relaunch and the versioned loading message.
- `amiwind_show_debug` is the master for development overlays, with
  `amiwind_debug_all` as an alias. Accept case-insensitive on/off, true/false,
  and 1/0. Preserve individual selections while hidden. Coordinates have a
  reserved bottom-right strip outside the 3D view; `amiwind_debug_coords`
  toggles it. Keep `showram` off by default; `amiwind_debug_showram` is an alias.
  Crosshair, dialogue, menus and loading feedback are not debug overlays.
- Pier repair: unsigned BSP face-plane indices restore the missing dock faces;
  measured edge/surface overflow is removed by preallocating larger buffers.
  Tune the allocation against high-water marks and model-cache residency;
  an oversized buffer can evict models and create repeated disk reads.
  Reduce visible triangle/edge
  cost through material/UV-aware simplification and distance variants next;
  retain silhouette and doorway/platform collision. Avoid dropping random faces
  to satisfy a hard budget. Fixed-camera profiles must compare equivalent output,
  including restored geometry; smaller textures do not reduce edge counts.
- Continue investigating the owner's pier screenshots: suspended
  geometry, and roads/walkways ending abruptly. Separate source-conversion loss,
  renderer clipping and the fixed scene boundary. This is the Seyda Neen slice,
  not a complete town/world export. Audit selected/skipped references and record
  camera XYZ/yaw for native regression captures before expanding coverage.
- Temporary sea backdrop: expand the simple water/enclosure beyond the bounded
  terrain slice so the cutoff is less abrupt at the normal fog presets. This
  is a demo placeholder while the basic rendering, movement and interiors are
  established. It is not the real surrounding coastline, archipelago, infinite
  ocean or world streaming. Replace it with converted neighboring cells and
  proper streaming/coverage as the map grows; keep this limitation in code notes
  and checkpoint documentation. The land/object export remains bounded.
- Opening/arrival scene is the overall first playable milestone, rather than
  full-world expansion. The pier repair is included in checkpoint-014. Preserve
  the separate position-dependent shack-wall report until reproduced/fixed.
- After the connected exterior acceptance gate, begin the opening in the prison
  ship interior, then the Census and Excise office as the first town interior. Read
  the original DOOR destinations and interior CELL; E loads the separate space,
  returning through its linked exit with a safe position/orientation. Repeated
  trips must preserve music state, release old geometry and report load time.
- Host export now provides ordered INFO lookup tables for Hello/Idle and other voice categories,
  indexed by actor/race/sex/class/faction. Keep condition operands, response IDs,
  original sound paths, order and scripts. Static candidates are not yet eligible
  playback. Multiple appropriate greetings follow a supported condition evaluator;
  unsupported conditions must not turn into unconditional/random folder playback.
- Keep NPC wandering/pathgrids, Fargoth's ring dialogue, combat tests, Balmora
  recall travel, interiors, saves and equipment on the retained queue below.

## Priority debugging controls — checkpoint-014

Delivered and locally verified in checkpoint-014: noclip look-directed flight. W/S move along camera forward/back, including
pitch; A/D strafe; Shift boosts speed. Keep explicit E up / Q down, with immediate
stop on release and no gravity/slope drift. This is a navigation debug mode, not
combat invulnerability. Preserve safe collision re-entry and aw_recover.
Test looking up/down through terrain, steep pitch, diagonal speed limits,
console/menu transitions and restart so no held inputs remain latched. Add `amiwind_debug_reset_location 0` as the numbered recall entry point for
the validated town spawn. Reject unsupported IDs without moving the player;
future points need stable IDs, area identity and safe standing placement.
Keep E/Q vertical movement and aw_recover; the owner
reported that returning above terrain was not discoverable enough.

## Quick usability fixes

On normal exit, show `To restart AmiWind, type: amiwind` at the AmigaDOS prompt.
This launches the executable again; it does not depend on keeping the game in
RAM. Keep the message after shutdown and before returning to DOS.

## Dialogue presentation and font work

The Finnish keyboard's section-key position (left of 1) currently opens the
console smoothly. Reuse the *timing/presentation approach* for a dialogue panel
that slides upward from the bottom, then retracts downward. Keep it separate
from debug console routing/history. Activation faces the NPC, blocks gameplay
inputs appropriately, and restores input without stuck keys when dismissed.

Use a classic Morrowind-inspired black dialogue panel with a restrained warm
border, readable text and clearly distinct topic/choice links. Preserve that
visual character at Amiga resolution; do not reuse the debug console artwork.
Original interface art, if converted locally, remains outside public source.

Keep the current compact font for diagnostics. Dialogue needs a more readable
font at the actual 320 x 200 output size: test letter spacing, contrast, accented
characters, line wrapping, long topic/response text and scrollback. Investigate
locally converting the owner's Morrowind font files through the host pipeline;
converted glyph atlases/metrics remain private derived game data. Alternatively
use a suitable freely distributable font with its license. Do not claim either
approach accepted before native readability and memory measurements. Greyed menu
options must remain distinguishable with the selected palette.

## Checkpoint-013 collision bounds and NPC behavior

Owner confirmation (27 September 2026): the central town-square obstruction is
fixed in v0.0.12-dev2. Track per-iteration confirmations and open reports in
[PLAYTEST_STATUS.md](PLAYTEST_STATUS.md); keep this location as regression coverage.

Bound each architectural convex piece before player-hull expansion. Facet-only
expansion can create remote solid spikes around acute or thin pieces. Keep the
existing slope/stair fixes and walking bob. Use `aw_blockers`/`aw_pos` for exact
remaining town-square reports. This is still approximate collision, not a claim
that every doorway and ledge is solved.

NPCs now have independent idle-pose, facing and proximity-Hello timing, a shared
voice cooldown, and a distance reset. E remains a generic voice audition, not
an interactive dialogue window. Authored AIDT ratings and ordered AI packages
are retained privately by the converter; AI_W range, duration, time, idle weights
and repeat are decoded. No wander package is executed yet.

Next NPC work, before more townsfolk:

Add player/NPC and NPC/NPC collision after validating scaled actor bounds. The
current three actors are deliberately nonblocking. Test doorway and stair
approaches, overlaps at spawn, sliding past an idle actor and later wandering
without pushing the player or recreating stuck-spawn regressions. Keep noclip
and safe recall available during acceptance.

Create a complete private Seyda Neen actor registry: inventory exterior cells
covering the agreed town area plus named interiors. Record NPC base ID and each
placed reference ID, cell, position/rotation/scale, race/sex/body, normal initial
outfit/equipment, voice candidates and authored AI packages. Distinguish shared
base records from separate placements and preserve disabled/deleted/scripted
states; do not blindly spawn every record. Include missing/unsupported assets
and a deterministic fallback policy in the conversion report.

First inclusion target is each actor's recognizable initial appearance, even
before full AI or dialogue. Budget shared model/skin/voice allocations, active
actors and nearby resident actors separately. Cache shared appearances once;
load/sleep/unload by area and distance with stable reference IDs and saved state.
Audit actual actor counts and memory before choosing limits; the existing three
actors are an initial subset, not a complete Seyda Neen population.


1. Bake walk poses from the original skeleton, preserving shared topology and
   matching foot speed to movement. Do not slide an idle model around.
2. Read original pathgrids and choose collision-checked routes inside each
   authored wander radius. Respect stationary/zero-range packages, return after
   interruptions, and handle blocked steps without pushing the player.
3. Suspend locomotion while greeting/activating, turn smoothly, then resume.
   Nearby actors get bounded updates; distant actors should sleep or tick slowly.
4. Add separately filtered Idle speech with a time-based chance. Do not recycle
   Hello samples as idle chatter or fire a random MP3 by voice folder alone.
5. Add full Greeting/INFO selection and dialogue state, then ring quest, combat,
   inventory/equipment changes. Keep Nord first-person hands/punching queued.

Both public/private packages include `docs/FS-UAE-PLAYTESTING.md` and versioned
FS-UAE/WinUAE presets under `resources/emulators/`. Keep pristine images as
checkpoints; run writable copies.

## Checkpoint-012 actor and movement slice

Implemented: host-assembled dressed Fargoth and two Imperial guards, shared
8-pose idle models, nonblocking actors and an E-key generic voice audition.
Full dialogue filtering, quest state and combat remain open; checkpoint-013
adds bounded proximity polling. The player box now matches the scaled base humanoid collision dimensions;
native startup, idle and one stair route passed after ground-support and stair
repairs. Other reported tight spots still need route-specific checking. Keep the preferred Quake bob. See [movement](PLAYER_MOVEMENT.md)
and [checkpoint validation](CHECKPOINT_012_VALIDATION.md).

## Checkpoint-011 startup repair and NPC handoff

Dev4 addresses a reproduced blocked initial spawn. The next acceptance route
must walk immediately after boot, before noclip/recovery, then test recovery
separately. Preserve the owner's now-working door rendering and town details.
Approximate collision still needs ledge/approach tests; a safe start does not
certify the whole town.

Owner playtest after dev4: walking now works from the initial spawn, but movement
near the town centre feels sticky and constrained. This remains a distinct open
regression. Capture a repeatable route and split ground/slope response from
architecture-hull overlap before changing collision. First NPCs must not add
blocking volumes until placement is validated. Combat comes after basic actors.

NPC research has identified the initial actors, base body/outfit records,
leveled guard equipment and original skeleton/text-key animation ranges. Their
ring/voice records have been inspected; Fargoth's ring conversation is text,
not an assumed voice clip. Assembly/baking and native actors remain next work.
See [the research handoff](OPENMW_REF_NPCS_AND_DIALOGUE.md).

## Checkpoint-010 repair scope

The owner's filesystem requester, stuck/falling movement and disappearing door
panels take priority over adding another town. Dev3 corrects legacy image root
metadata, rotated collision and floor-trace merging, adds console/noclip/recovery,
and tests near-door depth ordering separately from distance/PVS culling.
A known camera route and floor sweeps are required alongside existing audio
and restart checks. Do not claim the approximate collision proxies are exact.

Next collision work: test low ledges and door approaches at multiple yaws,
refine conservative hulls only where measured traps remain, and compare standing
height to visible terrain during repeated movement. Next rendering work: keep
door panels with frames, preserve attachment ordering without drawing through
walls, and investigate remaining terrain/roof seams before increasing coverage.

## Player body and first-person hands

- Preserve the Quake walking bob (owner preference, 27 September 2026):
  `cl_bob 0.02`, `cl_bobcycle 0.6`, `cl_bobup 0.5`. Camera motion is separate
  from collision dimensions, grounded movement and stair handling.
- First visible player-body milestone: Nord bare hands in first person,
  assembled from the owner's body-part data with the appropriate first-person
  skeleton/animation. Bake a bounded punching animation on the host.
- Verify handedness, skin/UV seams, wrist cropping, camera-relative position,
  near clipping and animation timing. Test while standing and walking with bob.
- Then wire attack input, hit timing, reach/line-of-sight, damage and reactions
  into a small combat test. A visible punch alone is not working combat.
- Full third-person player model, configurable race/sex and clothing/equipment
  variants follow the shared NPC appearance pipeline. No converted hands,
  character meshes, textures or animations in public source packages.

## First NPC milestone after this repair

Start with Fargoth and two town guards using compact animated alias models.
The host assembles race/sex body parts, heads, hair, equipped clothing, armour
and weapons from the owner's data, then bakes a bounded set of idle/walk frames.
AmiQuake supplies model drawing, not Morrowind actor assembly or gameplay rules.
Start with their recognizable normal outfits and an original greeting from the
owner's files. Validate feet/ground contact, model bounds, palette, memory and
frame cost with one, then three visible actors before filling the town.

For later equipment removal/changes, swap cached complete appearance variants
initially; clothing often changes geometry, not only textures. A body/underwear
base and modular equipment are longer-term options. Do not promise arbitrary
wardrobes, full actor animation, combat AI or dialogue trees in the first NPC
checkpoint. Keep conversion reproducible and all derived character/voice data
outside the public package. Add attack/damage tests only after basic actor
rendering, movement and collision are stable.

## Checkpoint-009 progress

v0.0.11-dev2 replaces convex facade scenery with shared mesh surfaces, corrects
the native music filename fault, restores history controls and verifies shell
relaunch. Linux `build.sh`, public notices and versioned `resources/emulators/`
presets are present. See [validation](CHECKPOINT_009_VALIDATION.md).

The queue below is retained in full: terrain joins and remaining visual gaps,
audio deadlines, Balmora/recall travel, NPCs, dialogue, combat and interiors
still need acceptance. Fixing a renderer or loading a Quake model does not
implement those game systems.

## Current repair and expansion queue (27 September 2026)

1. Repair the v0.0.10 architecture bake: preserve door recesses, deck/support
   separation, full instance transforms, and terrain/structure joins. Diagnose
   the separately reported view-dependent foreground disappearance.
2. Restore OST behaviour and controls: title excluded from in-world playlists,
   shuffled exploration/battle bags, Shift+F5 Previous, Shift+F6 Next, bounded
   buffering and separate transition/underrun evidence. See
   [OPENMW_REF_MUSIC_AND_AUDIO.md](OPENMW_REF_MUSIC_AND_AUDIO.md).
3. Convert a bounded Balmora area using the same pipeline. Add a recall-style
   travel control using owner-supplied sound data, with repeated Seyda Neen /
   Balmora trips, safe spawn points, preserved music state, load timings and
   memory recovery checks. This tests area replacement, not continuous streaming.
4. Introduce recognizable Fargoth and guards: assembled appearance, idle poses,
   collision and one greeting. Then add a small movement/attack/damage exercise
   with explicit limits and profiling. Quake's model renderer does not supply
   Morrowind character assembly, AI or rules automatically.
5. Extract and map dialogue records/conditions, actor identity and quest state
   before claiming functional dialogue trees. Keep NPC/gameplay work separate
   from the image-correctness and audio repair acceptance gates.
6. Add interior cells through the area replacement path: door activation,
   destination cell/position, safe entry orientation, return-door linking and
   persistent state. Provide selectable original-style and modern control
   profiles; modern E activates/uses doors and Space jumps. Verify the original
   mapping against primary documentation before labelling it a faithful preset.
7. Verify clean quit and `amiwind` relaunch from the Amiga shell, including
   repeated sessions. Later add an Escape overlay for resume, restart and quit;
   save/load becomes available only after persistent gameplay state exists.
8. Provide a Linux `build.sh` entry point with a Python build coordinator,
   dependency checks, installed Data Files selection, external private workspace,
   staged conversion/build progress and actionable failure messages. Document
   install prerequisites and reproducible toolchain identities. Never bundle
   game data or ROMs in the public checkout or fetch them for the user.
9. Keep copyright/licence notices specific: original authors retain their
   copyrights; each reused component remains under its own licence; Bethesda
   assets and ROMs are not GPL. Fan-tribute wording is not a licence exemption.

Save a versioned public-source and private playable checkpoint at each usable
stage. Preserve the prior build and comparable performance evidence.

## Completed checkpoint history

- Pipeline 0.1.x: owner-supplied game folder, base terrain/placement audit,
  converted packets, portable C reader and checked source packaging.
- Demo v0.0.1: OpenMW-captured opening, stereo PCM clip, centred speech and boot.
- Demo v0.0.2 / checkpoint-001: native wireframe, WASD/Shift and mouse movement.
- Demo v0.0.3 / checkpoint-002: filled terrain, baked surface colours, dense fog,
  blitter spans, projection tables and frame counters. Owner tested locally.

- Demo v0.0.4 / checkpoint-003: complete installed OST, fixed-size stereo queue,
  original voice, track selection and sustained streaming baseline.
- Demo v0.0.5 / checkpoint-004: native profiler, measured async refill options,
  smaller OFS partitions inside one RDB HDF, damaged-file recovery tests.
- Demo v0.0.6 / checkpoint-005: AmiWind name/version banner, exploration/battle
  playlists without consecutive duplicate songs, original static scenery export
  and host turntables. Native scenery rendering remains pending.

- Demo v0.0.8 / checkpoint-006: native AGA textured town, bounded BSP buildings,
  tree sprites, palette fog, WASD/mouse, whole-song stereo playback and profiling.
  Emulator 040/FPU reference only; stock 020 target and NPCs remain open.

- Demo v0.0.9 / checkpoint-007: startup dependency hotfix and linked-binary gate;
  separate 3.1/3.1.4 smoke records; unchanged world/audio payloads.

- Demo v0.0.10 / checkpoint-008: 68000 hardware/RAM preflight, checked Fast-memory
  hunk allocation and current WinUAE profiles. Audio deadlines at reduced CPU
  speed remain a measured optimization target.

## Current work: automatic scenery conversion and measured rendering

- Shared BSP architectural meshes replace convex facade proxies in dev2. Refine
  terrain joins, source texture seams and multipart collision before expanding.
- Profile world surfaces, models/sprites, C2P, mixer work, memory and I/O separately.
- Bring up a 68020/no-FPU build without loading the Workbench desktop; distinguish
  OS library dependencies from desktop memory use.
- Keep JIT/maximum-speed emulation separate from stock-machine claims.
- Add one stationary NPC with interaction and an owned greeting before crowds,
  inventories, animation variants or quests.
- Move from a resident scene to measured chunk residency/prefetch only after the
  renderer and collision workload are bounded. Prebaking is host work; HDD storage
  does not execute animation, collision or gameplay logic for the Amiga.

## Previous scenery milestone

The full soundtrack, playlist fix and first static-model translation are complete.
See TRANSLATION_LAYER.md for the two runtime routes and SCENERY_FORMAT.md for
measured source-asset budgets. Keep
profiling as scene complexity grows, record frame pacing alongside averages,
and preserve each tested build. See PROFILING.md and ENGINE_STUDY.md for measured
results and the Doom/DoomAttack/AmiQuake source study.

## Storage and runtime options

| Option | What it buys | Decision gate |
| --- | --- | --- |
| AmigaDOS files on a modest OFS HDF | Simple 1.3 boot, inspectable files | Current baseline; measure filesystem/read CPU cost |
| Indexed asset file | Fewer names, batched sequential requests | Compare to individual files before adopting |
| Reserved raw asset partition | Potentially less filesystem overhead | Implement bounds/device discovery; prove improvement and clean exit |
| Large UAE image with 64-bit access | Room for extensive baked variants | Verify exact API/driver; label emulator-specific dependence |
| A1200 / Fast RAM / accelerator | Larger cache and more CPU capacity | Separate build/profile; preserve A500 baseline |
| Pre-rendered views or billboards | Recognizable scenery with less geometry work | Assess camera freedom, occlusion, scaling and storage demand |

See [storage profiles and limits](STORAGE.md). Below 4 GiB is not a universal
old-controller compatibility guarantee. 8/16/32 GiB images are candidate
configurations, not implemented support or assumed speed improvements.

## Next visual checkpoint

Refine terrain and structure joins, remaining roof gaps and pier traversal in
the current mesh scene. Trees/buildings are CELL placements separate from LAND
height samples; they are already visible in AGA. Then reuse a parameterized
scene pipeline for Balmora and measure area replacement. Keep correctness and
worst-frame timing gates before expanding the resident scene.

## Audio effects and world cache

Add movement effects beside music/dialogue, explicit channel ownership and
sample-position-preserving handoff. Cache likely effects/voice and nearby world
chunks. Test simultaneous audio reads, turns, cell boundaries and hilltop views.
No hardware unit performs MP3 decoding or general 3D transformation for free.

## Host character baker

Use OpenMW on the PC for actor assembly, equipment and animation where practical.
Bake a bounded set of body/appearance/pose/view combinations. Reusing OpenMW
source requires its applicable licence and notices; current native code is
independent and the repository bundles neither OpenMW nor Hunter code.

## Later interaction and compatibility

Collision, doors, NPC interaction, dialogue conditions, inventory, combat, quests
and scripts are separate milestones. A complete game port is not established by
terrain rendering or asset conversion. Every public release requires the user's
original game files; converted game assets and ROMs remain outside that release.

For the first Fargoth/guard milestone, see [NPC and greeting behaviour](OPENMW_REF_NPCS_AND_DIALOGUE.md), including the requested UESP voice reference and OpenMW selection/trigger paths.

## Waterline and topographic diagnostics

The temporary sea-height reference is visible by default; the console command
`amiwind_debug_sealevel on/off` hides/shows its surface without changing physics.
Its current Z=0 plane helps compare the pier and terrain heights. For a later
host topomap, draw source LAND contours and the selected waterline, mark the
converted-cell boundary, and leave unconverted areas clearly identified rather
than inventing elevations. Verify cell water metadata before generalizing the
datum to interiors or other regions. Replace the expanded sea placeholder as
proper surrounding map coverage becomes available.

## First complete vicinity

Use [SEYDA_NEEN_SCOPE.md](SEYDA_NEEN_SCOPE.md) and the owner's UESP map as the
coverage target: town/tradehouse, shacks, lighthouse peninsula, docks, Census
buildings, prison-ship arrival and Silt Strider approach. Audit neighboring source
cells before choosing smaller runtime streaming chunks. Fix origin-only object
selection and explicitly handle supported visible activators. Keep the prison
ship/hatch/gangplank and character-generation state coherent. Checkpoint-015
restores the static assembly; opening-state removal still needs implementation. Opening and office entry/exit remain
ahead of distant-region expansion.

## Open incomplete terrain/rock formation report

Reproduce the checkpoint-014 screenshot's incompletely drawn terrain/rock formation
beside the road. The owner clarified this is missing/malformed formation geometry.
Compare original LAND/placed rocks with conversion at the same XYZ/yaw. Diagnose
source topology, selected coverage and render visibility separately. Use the
new `dbg coords on` / `dbg pos` aliases to collect coordinates. This remains
open; see [playtest status](PLAYTEST_STATUS.md).

## Checkpoint-016 playtest steering (27 September 2026)

- Console: compact font by default; retain normal readable and retro fonts.
  Shift + physical key left of 1 (Finnish §), or Shift+F10, toggles full/half
  height. PageUp/Down and Shift+Up/Down scroll. `debug overlay off` aliases the
  existing debug-only master switch; accept on/off, true/false and 1/0.
- Coordinates: add heading and pitch so a reported disappearing surface has
  both position and camera orientation. Do not call a location-specific bug
  fixed without reproducing that view.
- Keep first-person 3D hands and their conversion path. Add a compile-time
  `--hands 3d|sprites` selection; bake sprites from the same owned poses.
  Compare idle/draw/punch/sheathe visibility, frame cost, RAM and loading cost.
  Owner reports flicker and weak/transparent-looking hands in checkpoint-015.
- Exterior ship gaps: deck `(804,-311,61)`, bow `(615,-548,74)`, detached edge
  views `(777,-373,61)` and `(790,-413,62)`. Preserve the current silhouette as
  reference; check source surfaces, winding, LOD and renderer before changing
  shape. Simpler straight bow sections are an experiment, not an assumed fix.
- Pier A/B: retain the current separate-plank conversion; add an optional
  joined, textured deck while preserving outline, supports and collision.
  Capture from `(630,-388,56)` and walking-height side views; measure surfaces,
  edges, frame stages and RAM. No universal flattening of source meshes.
- Distant-building A/B: keep current geometry as baseline. Try baked backdrops
  only beyond the interaction range. Check parallax, silhouettes and entrances.
  Open house-disappearance report at `(-41,715,69)` needs heading/pitch.
- Height audit: current collision dimensions come from base_anim's bounding
  box; eye height was a prototype 90%-of-height choice. Compare the first-person
  Camera bone and Nord scale separately. Preserve the successful width.

## Checkpoint-016 outcome and next priorities

Implemented: first dim prison interior, bidirectional hatch loads, compact/full
console and scrollback, overlay alias, DEG/pitch, calibrated Nord eye height,
compile-time hand sprite experiment with the 3D path preserved. Full verification
and exclusions: CHECKPOINT_016_VALIDATION.md.

Next: reproduce exterior ship deck/bow gaps and the terrain/rock formation using
XYZ/DEG/pitch; audit ordinary scenery bounds for the disappearing house near the
current coverage edge. These are OPEN, not closed by adding an interior. Then
complete the opening walk/actors and Census office with the same scene pipeline.

Keep the joined-plank textured-pier and distant-building-backdrop alternatives
as explicit A/B recipes. Require connected walkable outlines, interactive doors,
collision/occlusion parity, counts and fixed-camera performance evidence. Neither
experiment is implemented in this checkpoint. Lift scene choices into a validated
recipe schema after the two-scene pipeline stabilizes; preserve all source and
conversion reports so later areas inherit lessons rather than manual patches.

## Recovered owner list, 27 September 2026, 22:17 Helsinki

The complete active register is [SEYDA_NEEN_NEXT_STEPS.md](SEYDA_NEEN_NEXT_STEPS.md):
interior structural regression first; town-edge/Silt Strider audit; exterior and
interior actor rosters; authored activities and conditioned speech pools; container
placement/state/refresh; separate interiors and door lookup tables; opening and
hatch state; sky fallback, sun, night torches; audio deadlines; exterior method_001.
Do not drop these items when handling the immediate geometry regression.

### Water feedback and scene-picker follow-up

- [ ] Separate blueish underwater presentation from red damage feedback and
  mapped hurt audio; test harmless immersion, damage and surfacing.
- [ ] Track the owner's v0.0.15-dev1 slowdown against identical fixed-camera
  runs; new exterior report: XYZ 211 447 47, DEG 4, P 0.
- [x] Scene-picker command `dbg scene change` (also `debug` and `amiwind debug`);
  host/native acceptance passed in checkpoint-017. See SEYDA_NEEN_NEXT_STEPS.md.

### Opening-state residency

- [ ] Host audit of original opening scripts: stages, actor prerequisites,
  controls, dialogue waits, door/menu transitions and disabled references.
- [ ] Persist compact opening state across the already separate interior/exterior
  scenes; remove the disabled ship assembly on post-registration town loads.
- [ ] Compare baked dim lighting with bounded AmiQuake-style dynamic lights for
  torches; retain the static path and measure cache rebuild/audio costs.

### Adjustable visibility and appearance A/B

- [x] Live fog/draw-distance aliases and first Options → Graphics slider,
  default/Medium 700 local units; 10/1-unit normal/Shift steps. Native check passed.
- [x] At the slow camera (-44,259,75), yaw328/pitch-14, compare 700/400
  coupled fog/culling on the same machine: one short native sample gives
  11.46 vs17.21 FPS. More views and physical-machine validation remain.
- [ ] Preserve whole-exterior method_001; test separate texture/geometry candidates
  and reject missing-scene geometry as a false optimization.
- [ ] Bake a low-poly Silt Strider landmark candidate from the owned ACTI model.

- [x] Default-off `dbg fps` counter, roughly one-second average, respects debug master.

## Next milestone after checkpoint-017 and recovery backup

- [ ] Audit the original ship-waking sequence, script gates and voice-completion
  pacing; distinguish scripted waits from time taken by the player.
- [ ] Add an opt-in first intro sequence and dark bordered subtitle/message boxes.
- [ ] Evaluate original Fonts/*.fnt + *.tex conversion as a selectable UI font.
  Keep readable/retro atlases and all existing font selection paths.
- [ ] Preserve existing feature variants and immutable checkpoints; follow the
  non-destructive experiment rule in DEVELOPMENT.md.

Recovery snapshot work takes priority until all required owner data, source,
toolchain and handover files are durably saved. Intro implementation has not begun.

## Final recovery handover update, 27 September 23:32–23:35 Helsinki

The latest chosen NEXT-build fog/culling default is **540**, superseding the450
proposal above. Current frozen dev2 still starts at700; live command:
`dbg fog distance 540`. Update config/runtime/menu reset/tests/docs together in
the next build, preserving the old packages and selectable distances.

New persistent rock/Silt Strider-port report: XYZ337 643 34, DEG304, P-16,
v0.0.15-dev2, image(20260927-203433).png. Owner screenshot shows a projecting
terrain/rock section with missing-looking lower geometry; exact source identity
and cause still require comparison. HUD reads28.4FPS in that one screenshot,
not a benchmark. Do not conflate the already-known omitted Silt Strider ACTI
with proof of this formation's geometry cause. Backup first; keep this open.

## Persistent world and disk loading direction (v0.0.16 planning)

See [the proposed implementation approach](PERSISTENCE_AND_STREAMING.md) for
state ownership, stable IDs, cell loading, memory budgets and save recovery.

Keep converted cell data immutable and identify placed objects with stable source
reference IDs. Save deltas for doors, containers, removed items, NPC state and
quest variables separately. Global quest/time state must survive cell unloading.
On cell load, apply saved deltas to its base data. Begin with explicit cell/door
transitions and bounded resident memory; investigate adjacent-cell preloading
after measuring RAM, disk latency and audio deadlines. A larger HDF increases
storage capacity without making all content resident. This is a design direction,
not implemented save support or seamless streaming.


## Interaction and inventory follow-up, 28 September 2026

Default layout: [npc_interaction_layout_template_001](INTERACTION_LAYOUTS.md).

- [x] Small 12 px target hint, right-aligned immediately below the viewport:
  `Fargoth` in the small Morrowind font, then `(Talk: E)` on the next line in
  the current console font. Shared opening action query; range, visibility and current
  permissions determine the displayed action. No extra panel or debug dependency.
- [x] Menu/character choices accept arrows and WASD; preserve name-entry letters.
- [x] Separate the hall guard's fighting permission from the global opening
  enclosure. Do not enable every player action just because one gate ends.
- [ ] General action permissions combine script restrictions, UI capture and
  active effects. Model Paralyze and Silence separately: Silence affects casting,
  not ordinary punches. Verify effect rules and expiration/restoration against
  original records and OpenMW before implementing combat/magic.
- [ ] Import container inventory entries and leveled-item lists from owned data;
  preserve fixed items, quantities, list flags, level rules and chance-none.
  Verify resolution/respawn behavior against OpenMW before choosing roll timing.
- [ ] Item catalogue and icon conversion from original item records; bounded
  palette/size/cache budgets, icons plus readable names/counts in inventory and
  container UI. Do not replace missing icons with unrelated art.
- [ ] Persist each placed container's resolved contents and player removals;
  reopening or loading must not duplicate loot. Track respawn policy separately.
- [ ] Fargoth ring dialogue: keep/return choice, original conditions, journal and
  disposition/reward changes. The ring pickup exists; the return branch does not.
- [ ] Replace the temporary namespaced courtyard-container fact with generalized
  reference state when that store is introduced; migrate saves explicitly.
- [x] Offline standing-hull scan reports floor support, bounded step connectivity,
  reachable scan edges and potential fall edges. Visual completeness remains a
  separate check; no automatically fabricated floors or invisible walls.


### Runtime out-of-bounds safeguard (requested 28 September)

- [ ] Bounded, low-frequency diagnostics poller for non-finite coordinates,
  sustained embedding in solids and escape from converted playable cell volumes.
  Use source-derived room/region bounds and reachable collision surfaces, not a
  single guessed Z threshold; stairs, lower floors, swimming and scripted
  transitions must remain valid.
- [ ] Retain the last verified supported, non-embedded position per cell. Require
  repeated grounded samples and exclude noclip, teleports/loads in progress,
  menus and unsafe/water states. Reset or revalidate it when cell content changes.
- [ ] Record version/cell/XYZ, previous safe location, nearby source references,
  story state and collision reason before offering recovery. Rate-limit notices.
  Do not silently move the player or convert that result into bug closure.
- [ ] Verify the recovery sweep and floor support before returning the player;
  never create autosaves while the character is out of bounds or unsupported.
  Measure the poller's trace/time budget on the Amiga.


### High priority: graphics/culling, door and wall assemblies

Owner explicitly prioritizes this as a key culling/geometry issue. Keep this
reference case when designing broader architectural occlusion and simplification.

- [ ] Reproduce exterior Census door overlap at XYZ396,-171,39, yaw170,pitch-3
  (AW-20260928-21); identify source door/wall references and offending triangles.
- [ ] Planned host `door_priority` true/false recipe, default **true** once implemented and validated (false preserves the baseline): retain real door holes,
  simplify covered planar wall geometry and remove proven redundant overlaps.
  Keep frames, silhouette, visibility through open doors and correct collision.
  Restrict any base-colour/texture backing to the concealed patch beneath the
  door/frame, with a conservative hidden margin. Preserve visible wall texture,
  UVs and shape. Remove redundant faces from the converted runtime asset; merely
  repainting or hiding them does not remove their memory/rendering cost.
  Never use unconditional door draw-on-top as a substitute for correct geometry.
- [ ] Compare source/candidate mesh counts, renderer surfaces/edges and fixed-view
  frame times. Separate visible correctness from a measured performance gain.

- [ ] Automate an oriented doorway cut from the placed door aperture. The owner
  confirms intrusion at both Census exits viewed from outside. Make a door-shaped cut-out: clear obstructing wall geometry behind/through
  the door opening (bounded depth), preserve the surrounding
  frame/wall, interpolate cut-face UVs and rebuild matching collision. Scope edits
  to verified adjoining wall references; never flatten everything in a door AABB.
  Report changed references/faces and retain source/baseline geometry. Validate
  repeated instances, rotated doors, door motion and both sides of each opening.


The door-cut optimization is intended to remove unnecessary geometry before
runtime, so the Amiga does not transform/rasterize redundant faces. Hiding the
artifact with a rendering priority while retaining that work does not meet the
performance goal. Profile the resulting reduction rather than assuming a gain.


Owner refinement: the assisted doorway simplification should be enabled by
**default** in the future build configuration, with an explicit disable switch.
Keep a conservative cut/overlap margin hidden underneath the door frame so no
seam or missing wall leaks around the edge. Where a transition door never reveals
an opening, replace unnecessary covered depth with a simple wall-coloured planar
rectangle behind it. A real hinged/open-through door must retain its aperture;
a backing rectangle must not seal a visible passage or create blocking collision.
This describes the planned default; no such build switch is active yet.

## Next local-area checkpoints

- v0.0.23-dev2: source-driven cast and all 13 Seyda Neen interiors plus
  Addamasartus; original Silt Strider and Darvame Hleran placements; all NPCs
  block the player; new gameplay captures for the main README.
- Clock and calendar: persistent game time and dates, explicit time advancement
  while waiting, and a wait interface. Debug control:
  `dbg timeofday <0..24|morning|night|midday|day|evening|sunset|sunrise>`.
  Match sunrise/sunset direction to the world axes. Start with an inexpensive
  sun disc and colour gradients at dawn/dusk; evaluate a small original-owned
  Morrowind night-sky texture against the Amiga memory and frame-time budget.
  Keep the existing sky as a fallback (`dbg sky on/off`, also 1/0 or true/false).
  Night-time guard torches belong to this lighting checkpoint.
- Weather experiment: an explicitly selectable blight wind test after the clock
  and sky path is stable. Measure the cost of tinted fog, directional particles
  and original owned wind audio before enabling it during normal exploration.
- Continue the audio audit: intro sea splash audibility, continuous exploration
  music, and the reported occasional music clicks under WinUAE.

Delivery gate: check trailing whitespace in every changed source and in the
exact generated apply/publish script before packaging or posting commands.

### Transport and resident voices

After the interior inspection checkpoint, expose Darvame Hleran's source travel
routes in an interaction screen beside the Silt Strider. Show destination, fare
and current gold; check affordability before travel. An unconverted destination
must say "Location not available." and must never deduct gold. Load only the
selected destination scene and charge only after a successful transition.

Replace the prototype single greeting with the original eligible NPC voice
pools and cycling. Preserve speaker/race/sex/class and quest/location/time
conditions; do not play every extracted line indiscriminately. Avoid immediate
repeats, retain speech cooldowns and interruption rules, and distinguish casual
ambient lines from player-initiated greetings and service dialogue. Guard lines
need their own pools. Record skipped/unsupported conditions in the private
conversion audit rather than silently substituting unrelated dialogue.

## dev3 feedback follow-up — 29 September 2026

The reported Vodunius-house visibility holes and the misrotated port rock are
addressed; see [terrain findings and workflow](WHAT_ARE_ROCKS.md). Voice style 2
now defaults to aim-only identity, overriding voiced speaker headers.
NPC conversation-facing, deck/pier sideways containment and door squeaks remain
open in [the consolidated dev2 feedback](FEEDBACK-v0.0.23-dev2.md).

## 29 September 2026 / v0.0.23-dev4

Published base: dev3 / `7e36e9051da477147f78cf22236a0a4c0c7201ae`.
See the updated [dated plan](PLAN-2026-09-29.md) and
[dev3 feedback disposition](FEEDBACK-v0.0.23-dev3.md). This checkpoint corrects
content-sized dialogue, input/rotation glyphs, startup audio/timing, opening quote,
tree sprite depth and Darvame's floor placement. The owner accepts the dev3 rock
fix. Door sounds, containment, complete voice behaviour and sky remain pending.


## Next version: world geometry density analysis

**Future-version work, outside the current fixes, by owner request (30 September 2026).**
Analyze source map placements to identify high- and low-polygon concentrations.
Produce spatial density maps and ranked areas, counting placed instances as
well as unique meshes, textures and expected resident data. Compare source and
converted complexity with actual visible/frame-time cost. Use this evidence
to guide sub-cell boundaries, overlap and loading/offloading budgets.
Treat this as a general world-streaming rule: identify the expensive concentrations
and the inexpensive stretches before choosing boundaries. Keep larger, more
continuous resident areas where measured cost permits; use tighter sub-cells and
earlier offloading around demonstrated bottlenecks. Polygon count is an input,
not a substitute for frame-time, visibility, collision and resident-memory data.
Begin with Seyda Neen and Balmora, then expand coverage. This is a planning
item, not part of the current implementation or validation claim.


## FIXES NEEDED IN BALMORA

### Jagged doorway arches

Owner report, v0.0.24-dev3, 30 September 2026: many Balmora doorways have
strongly jagged upper arches. Reference cameras: XYZ1218,-792,120, yaw352,
pitch-7; XYZ1269,-788,133, yaw343, pitch-18; and XYZ-1012,-939,142,
yaw204, pitch-5. Screenshots show irregular
dark strips around the upper door arch.

- [ ] Inspect source arch geometry, wall/door overlap and converted polygons;
  distinguish conversion defects from low-resolution rasterization.
- [ ] Compare a corrected mesh with a baked flat surface, bitmap or sprite
  where appropriate, choosing the least expensive method that preserves the
  intended appearance from nearby and oblique views. Preserve interaction and
  collision; a world-aligned surface must not turn to face the camera.
- [ ] Measure rendering cost and memory before adopting it broadly. Link this
  investigation with J021's concealed door/wall geometry work.

This is a recorded polish/optimization task, not an implemented dev4 change.


### Recurring deformed and blocked stairs — reusable conversion fix

Owner report from v0.0.24-dev3: XYZ962,119,64, yaw18, pitch-8. The screenshot
shows jagged stair treads and the owner cannot traverse them. The camera lies
inside the bounds of `ex_hlaalu_b_15`, placed reference 41379. Together with
XYZ613,-125,59 and the earlier b17 opening, this makes stair conversion a
recurring city issue, with both visual and movement consequences.

- [ ] Audit affected source visual triangles and authored collision separately;
  inspect surface winding, merging, overlap and depth ordering before attributing
  the jagged appearance to one cause. Check shared meshes across all placements.
- [ ] Build a reusable stair-aware collision conversion/validation step. Preserve
  authored walkable ramp/step surfaces and side boundaries; reject convex volumes
  that fill stair openings. Where reconstruction is needed, use bounded convex
  pieces or surface shells, retaining open space and the original landing heights.
- [ ] Sweep the unchanged standing hull along ascent/descent paths and landings,
  checking clearance, floor support, step height and slope; flag failures with
  source mesh, placed reference and coordinates. Do not force a generic ramp
  through an obstruction or change global player dimensions to hide the defect.
- [ ] Compare native before/after views and traversal, and measure clipnode/RAM
  cost before applying any higher-detail collision method across the city.

The current b17 shell correction is a narrow verified fix. It is **not** a claim
that these newly reported b04/dsteps03 and b15 stairs are repaired. This algorithm
and the doorway arch cleanup remain open work beyond the current dev4 correction.


### Proposed module: Balmora stairway optimizer

Additional owner report, v0.0.24-dev3: XYZ-883,126,300, yaw346, pitch-14.
The narrow stairs cannot be climbed. The camera is within `ex_hlaalu_b_13`,
reference 24020. Add this case to the recurring **Stairway to Balmora** issue.

Plan a reusable **Balmora stairway optimizer** in the Morrowind translation
pipeline, initially validated on these city cases but useful for other locations.
Its acceptance matrix must cover ascent, descent, narrow width, headroom,
landings, source/converted visual fidelity and runtime geometry/memory cost.
Collision success and intact appearance are separate required outcomes. Keep
the unchanged player hull as the test fixture; do not hide defects by shrinking
the character or changing FOV. This is TODO/design, not delivered functionality.


### Missing street ground texture

Owner report, v0.0.24-dev3: XYZ455,-699,61, yaw3, pitch17. The supplied
screenshot has the same XYZ and HUD yaw1/pitch16; retain both as nearby views.
It shows a broad flat untextured street patch around the lightpost in front of
two doorways.

- [ ] Inspect the source ground placement/material and converted face/UV/texture
  references to distinguish missing geometry, missing texture and incorrect mapping.
- [ ] Restore a continuous patch of the surrounding usual paving where supported
  by the original layout, matching texture scale/orientation and edge seams.
  Verify floor collision and avoid extra overlapping surfaces.

Suggested owner treatment: continue the usual street texture across the patch.
Status: recorded TODO; cause and correction not yet verified.


Additional stair validation case: v0.0.24-dev3, XYZ1182,-141,119, yaw91,
pitch-12; the owner cannot enter the stairway. Nearby mapped placements are
`ex_hlaalu_dsteps_03` reference41134 and `ex_hlaalu_b_04` reference22539.
This is another instance of the same dsteps03/b04 asset combination seen at
XYZ613,-125,59, strengthening the case for a reusable per-mesh correction
validated across placed rotations. Add to the Balmora stairway optimizer suite;
currently open, not covered by the b17 correction.


### Hlaalu guard missing/transparent chest armor

Owner screenshot, v0.0.24-dev3, Balmora: XYZ862,-502,58, yaw290, pitch13.
The guard's chest plate/torso appears absent or transparent, with the background
visible between the shoulders and waist. Owner suspects material conversion.

- [ ] Trace the NPC's equipped cuirass and BODY/armor slot resolution into the
  assembled actor; verify that torso suppression is paired with replacement armor.
- [ ] Check source submeshes, triangle retention/winding and transforms, plus
  material/texture presence, alpha flags and transparency-index conversion.
- [ ] Compare the original equipped appearance with the converted actor in native
  front/side/back views and animation; test other users of the same armor mesh.

Status: visual defect confirmed from the screenshot; exact conversion cause
remains unverified. Record independently from static building/door/stair issues.

## Debug teleport expansion

`dbg tp` means **debug teleport**. Keep the current named points of interest.
Future work: support original Morrowind world/map coordinates and placenames,
including case-insensitive `seydaneen`, `"seyda neen"` and `seyda_neen` aliases.
Inspect original coordinate/cell conventions before implementing conversion;
distinguish runtime-local XYZ from original world XYZ and validate safe arrival.
The requested `dbg aw hors 0` preset is current dev5 work: Hors, male Nord,
Barbarian, The Steed, after Census in Seyda Neen's square. A Balmora teleport
creates that preset only when no character exists; it preserves existing ones.

Owner acceptance against dev4, 30 September: Shift+V works; Balmora temple
passage is accessible as a Nord. Additional public stair reports remain in the
dev5 investigation: (-323,226,138), yaw260/pitch0 and (-527,187,143), yaw274/pitch-3.

## dev5 follow-up status (30 September 2026)

The earlier Balmora jagged-arch, blocked-stair, missing-paving and guard-chest
reports now have inspected causes and implemented candidates in
`INVESTIGATION-v0.0.24-dev5.md`. Native walking passes the previously stubborn
b04 arches and the new b02 approach (549,-739,58), plus the bridge05/06 stairs.
Keep citywide route acceptance open; a handful of passing routes is not complete
coverage. The birthsign cursor-only regression remains unreproduced; normal
native key dispatch passes and raw-event tracing is available.
## Recurring conversion acceptance: stair ramps

Every new region/interior family must include an authored stair-ramp check.
The Balmora `0.69766` normal versus former `0.7` walkable cutoff is a reusable
failure mode across repeated meshes, not a one-location defect. Inspect slope
classification separately from player dimensions and arch clearance; validate
idle support, ascent, descent and rejection of steeper non-walkable surfaces.
Procedure and RC1 evidence: [Stair ramp walkability](STAIR_RAMP_WALKABILITY.md).

## Dialogue inspection and long menus

- Reuse a vertical scrollbar for long option, destination, topic and text panes;
  support keyboard paging and pointer/wheel interaction with visible selection.
- Extend the isolated [character gallery](CHARACTER_MODEL_GALLERY.md) from bounded
  greeting previews to one-NPC topic/condition/result-script tests. Declare the
  test state and restore the entry snapshot on return to the game.
- Friendly-name search is debug-only, read from disk on demand. No gallery
  catalogue work belongs in ordinary gameplay's frame loop.
