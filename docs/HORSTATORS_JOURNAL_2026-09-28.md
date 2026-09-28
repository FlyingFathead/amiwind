# Horstator's babblings on the state of AmiWind's development

Captain's log, 28 September 2026, 05:10–05:24 Helsinki.

Owner's development direction, recorded before the captain gets some sleep.
This is a request/decision log. Completion belongs in checkpoint validation records.

Later entry: [Evening — polygonal POI regions if streaming is insufficient](#evening--polygonal-poi-regions-if-streaming-is-insufficient).

## Starting point

- The owner's `amiwind-2026-09-28_045110.zip` is the latest working repository
  snapshot and takes precedence over older recovery packages and GitHub.
- The repository is now public: https://github.com/FlyingFathead/amiwind.
- Work incrementally through the todo list and roadmap. Save checkpoints after
  meaningful milestones: complete public source, separate private playable,
  incremental public source, and checksums. Preserve prior checkpoints.
- The owner handles Git publication. Keep original and converted game assets,
  voices, fonts and ROMs out of public source.

## UI and fonts

Use the original Morrowind visual language: black boxes, the original gold
border artwork, appropriate spacing, and original-colored health, magicka and
fatigue bars. The previous border color and blank lower area were placeholders.
The main UI should default to the converted proportional Magic Cards font.
The console must keep its present font. Preserve all older font implementations
as selectable fallbacks, including readable, retro and compact diagnostics.

The accepted font study selected 16px with three ink shades plus transparency;
14px is the compact alternative and 12px is for space-constrained cases.
Do not silently replace this with the rejected monochrome study.

Dialogue must start completely off-screen below the very bottom edge and slide
upward into the unused area BELOW the 3D viewport, temporarily using the bars'
space. It must not cover rendered world graphics. Long lines page or scroll in the lower
area. The console keeps opening from the top. Short subtitles, scripted messages
and full topic dialogue need distinct layouts and behavior. Match Morrowind's
boxes and dialogue conventions within the 320x200 target.

Place the three stat bars below the visible world. Consider an interactive
minimap and selected weapon/hotkey slots there if their measured cost permits.
A baked map with an inexpensive player marker is a candidate; it is not a
commitment to render the 3D world twice per frame. Do not display invented live
inventory/combat behavior behind decorative slots.

## Opening sequence and actors

The priority is the complete arrival: waking in the ship, Jiub's scripted lines,
name entry, the guard's approach and escort, the deck/dock actors, race and
character selection, Census Office registration and release.

Use the actual source scripts, dialogue and voice lines. Advance spoken beats
from sound completion, with authored pauses where appropriate. Begin mapping
NPC dialogue, ordered response conditions, actor identities and voice pools.
Guard voices are not one arbitrary unconditional sound.

The separate boat interior already exists. Hammocks are no longer obstructing
the route; do not re-open that resolved report as if no repair happened. Minor
hull glitches remain. Guard navigation needs actual collision-aware movement
and route checks, not teleporting actors presented as pathfinding.

Add Seyda Neen's separate interiors and their real door links. Keep the current
scene residency model and preserve player/quest state across transitions.

## Time and lighting

Implement a shared day/night clock for appearance, waiting and later schedules.
The requested intro atmosphere is dark with a few local lights; audit the source
clock and weather before claiming exact original timing. Study existing AmiQuake
lightmap/dynamic-light paths for affordable lamps and nighttime torches.

Add waiting for a chosen number of hours once the clock works. The owner recalls
waiting being restricted during character generation; confirm the exact source
gate. Waiting must not bypass the opening or silently reset state.

## Script translation and durable state

Consider a host-side translation layer from original scripts to a compact
platform-friendly representation. Lua is a possibility to investigate, not a
required new runtime dependency. The decision should account for memory,
execution cost and implementation complexity on the actual target.

Keep scene-local actors separate from durable player, clock, quest and object
state. Unsupported source commands must be identified, not silently accepted.
A specific translated opening is not a claim of general MWScript compatibility.

## Persistent geometry problems

- Add the omitted Silt Strider actor/model at its authored placement.
- Investigate the malformed port/rock formation at the recorded cameras,
  including XYZ 211 447 47 / DEG 4 / P 0 and XYZ 337 643 34 / DEG 304 / P -16.
- The missing ACTI conversion and malformed terrain may be separate issues.
  Compare actual source geometry before declaring one fix solves both.
- Preserve exterior ship method_001 and the working hull repair. Keep native
  clipping, geometry correctness and performance diagnoses distinguishable.

## Working while the captain sleeps

Proceed without expecting replies. Keep the project documentation current,
save concrete milestone packages, and state what was tested and what remains.
A checkpoint is a recoverable development state, not permission to call planned
features complete.

## Checklist annotation convention

Keep resolved older items visible as `- [x] ~~original item~~ Fixed`, followed by the
checkpoint or owner confirmation. Do not cross out a larger feature merely
because one part works; retain remaining defects explicitly.

- [x] ~~Hammocks obstructing the ship interior route.~~ Fixed. Owner confirmed.

## Further opening requests, 05:26–05:30

Audit the entire original opening, including initial position and movement,
control permissions, exact speech order, music policy and any intro video. The
Nerevarine movie is an optional future candidate if the owned input is present.
Jiub's speech must include mouth movement synchronized with dialogue. Facial
morphs are a top priority; inspect actual head targets and bake poses driven by
the converted audio playback position.
Record rejected attempts and working fixes in IMPLEMENTATION_JOURNAL.md.

## Character creation and introductory residency, 05:31–05:33

The lower ship deck should be dark with sparse local lighting. Consider a
bounded deck/dock/Census approach map during registration, loading the full town
when the opening releases the player. Reduced residency must retain the real
route, source guard behavior and accessible views; it must not invent invisible
walls or expose missing scenery.

Implement the linked creation screens: Jiub's name prompt, race/sex/face/hair
selection with a 3D face preview on the dock, class selection, birthsign, and
character-sheet review in the Census Office. Extract source lookup tables for
race attributes and skill bonuses, appearance parts, classes, birthsign powers,
skills and attributes; all screens must edit one persistent character state.

## Route constraints and ship ambience, 05:35–05:36

Audit the original movement/action restrictions and any physical or scripted
boundary on the deck/dock route before substituting a reduced introductory map.
Do not assume an invisible wall from memory. Preserve the progression gates
through registration, papers, the ring, Sellus Gravius and the release package.
Inspect ship creaks, water ambience, localized sound activators and script
triggers; reproduce their roles separately from speech and music.

## Main menu, 05:37

Use the original main-menu background from owned assets. Present New Game,
Load Game, Options and Exit; Load Game remains visibly disabled until saves
exist. New Game must enter the playable scripted opening once implemented.

## Reading, menus and town voices, 05:39–05:40

Match the original main-menu presentation and distinguish returning to the game
from exiting to the main menu. Confirm Escape behavior; no save capability is
implied by a displayed disabled entry. Add book and scroll views, needed for the
registration papers and subsequent reading. Use source text and layout metadata.
Town NPCs need varied periodic voice lines with original eligibility conditions,
individual/global cooldowns and overlap handling, not one repeated audition.

## Generic dialogue reference, 05:41

Owner supplied the UESP Generic Dialogue Voiced table to cross-check variation.
It explicitly flags missing entries and mixed expansion coverage. Use the owned
master's ordered INFO conditions and assets as the authority; distinguish Hello
from Idle, service, faction, weather, crime and combat responses. Do not import
expansion-only or player-state-dependent lines into an unconditional town pool.

## Actor collision, attack reactions and ambience, 05:58

- [ ] NPCs need physical collision: no walking through people. Retain movement
  around actors, doorway clearance and collision-aware escort behavior.
- [ ] Punches need hit detection, original hand-to-hand fatigue/health rules,
  aggression and combat reactions, nearby witness/guard responses and crime
  consequences. An animation alone is not a functioning attack.
- [ ] Reproduce environmental ambience separately from music and dialogue:
  localized ship creaks/water, interior loops, region/weather sounds and
  randomized intervals. Audit source scripts and sound records first.

## Checkpoint pace and camera review, 06:01–06:04

Keep the base version at 0.0.18 during these early milestones; increment only
the dev suffix. Mark actual completed items with their checkpoint, leaving
partial systems open. The owner reports that dev1 is heading in the right
direction, but requests distinct red/blue/green bars and an eye-height check.
The taller impression may have been one guard or fatigue; still verify it.

## Frame and dialogue feedback, 06:11–06:13

Try the original thick gold menu-border artwork around the whole game canvas,
keeping the lower dialogue band black. Preserve projection/actor scale while
comparing the frame. Physical emulator overscan is outside the game framebuffer.
Owner likes the original voice clips and dialogue panels rising from below;
retain this presentation and extend its line variation and synchronized faces.

## Outer-frame correction and journal name, 06:14–06:16

The outer gold frame is optional and OFF by default. Expose its toggle in
Options; dialogue boxes retain their existing original borders. Rename this
file to HORSTATORS_JOURNAL_2026-09-28.md, including the source allowlist.

## v0.0.18-dev2 implementation checkpoint

The filename correction and optional frame setting are applied. The first ship
script adapter now has Jiub, name entry, original voices, talking/blinking heads
and guard navigation. The dark hold uses its baked lamps plus original scripted
hull-water loops. Bars have the intended three colors. Full creation and story
release remain open; see RELEASE-v0.0.18-dev2.md for exact scope and evidence.

## v0.0.18-dev3 checkpoint

Original main-menu artwork is now converted and displayed, with separate New
Game/Load/Options/Exit choices and an explicit route back to the main menu. The
model-cache correction removes the observed repeated Jiub/guard loads without
shrinking actors or changing the viewport. Creation screens and the remaining
opening stages are still on the active checklist.

## 28 September, morning — dev3 playtest follow-up

- Start at the original-style main menu, with disabled Load until saving exists.
- Check the remembered ship/deck/Census music sequence. The original CharGen
  scripts do not request music changes; exact original engine cue timing remains
  unverified. Keep the deliberately chosen opening track clearly identified.
- The upper hatch is a teleport doorway, activated by the player. Audit original
  destination records so the same approach can cover other town entrances.
- Ship guards currently allow the player through while the escort can be blocked
  by the player. Make collision symmetric and distinguish waiting from failure.
- The stair approach and upper barrel views have severe local slowdown; Jiub's
  area is comparatively acceptable in the owner's setup. Measure fixed views;
  preserve the repaired structural hull. Exterior loads only on hatch activation.
- Hide the blinking top-right disk icon by default; retain a debugging switch.
- Loading credits: By FlyingFathead; project URL; Special thanks to:
  ChaosWhisperer, on three separate lines. Owner's joking role: “fart director”.

## 28 September, 11:26–11:32 Helsinki — prophecy movie

The owner requests the original skippable New Game prophecy video before Jiub.
The initial data ZIP has an empty Video directory; the owner is preparing the
missing video files. Convert on the desktop to a small indexed stream and PCM,
without a heavyweight decoder on the Amiga. Preserve narration and source aspect
ratio, support Esc, and start the selected ship music after the movie ends.
Native synthetic playback and both continuation paths pass; original footage
requires its own conversion and review.

## 28 September, 11:39–11:41 Helsinki — project logo

Use the supplied transparent AmiWind logo at the top of the README, retain its
original PNG in resources/media, fade it in from black during startup, and place
a scaled version in the upper main menu. Startup branding and the New Game
prophecy movie are separate sequences.

## Dev5 steering, 28 September 2026, Helsinki

- Original main-menu artwork without the added project logo. Put the version
  at bottom right. Keep the startup fade; simplify the Esc wordmark and rule.
- Sharper startup/logo/movie text, aligned menu rows and New Game confirmation.
- Debug overlay off; console hidden during transitions through a saved switch.
  Use the original Morrowind loading screens.
- Restore the deck guard's scripted greeting/reminder cycle.
- Default compilation to available CPU workers; provide ordinary jobs overrides.
- Show entrance destination names now. On attempted entry into missing content,
  display exactly “Interior not found.” and stay put. Keep the original interior
  layouts and door arrival references for the next conversion milestone.
- Research the original ship-to-Census escape restriction next. The recalled
  invisible barrier is a research lead, not yet a verified mechanism.
- Package dev5 as a complete public source snapshot plus dev4 incremental and
  private playable. Owner publishes the full accumulated change set to GitHub.

## Track-change overlay follow-up

- [x] ~~Track changes must stop flashing text at the top left when the debug
  layer is off.~~ Fixed in v0.0.19: routine notices obey the same switch.

## Evening — polygonal POI regions if streaming is insufficient

**Horstator's notes, 28 September 2026, 20:23 Helsinki.** Design proposal;
not implemented, benchmarked or selected as a replacement for cell streaming.

First try a sane way to use fog-limited visibility to load/offload exterior
objects fast enough, allowing brief pauses at selected crossings if needed.
Only if that approach cannot meet the Amiga's memory and frame-time budgets,
try polygonal BSP regions, using Doom/Quake-style bounded levels and explicit
transitions around points of interest. The owner's inspiration is a "John
Carmack approach":
prepare bounded levels for the engine rather than require the entire open world
to stream seamlessly. This is a **must-try fallback if streaming proves
insufficient**, not a reason to discard the streaming option now.

For example, Seyda Neen and its immediate surroundings could form one
"AmiWind cell area". Its polygonal footprint need not follow Morrowind's exterior
cell grid: a region may combine parts of several original cells, with coverage
overlap at the boundaries where needed. Divide the wider map by regions and POIs
that make sense for traversal, sightlines and measured resource budgets. Walking
out of one region would load the neighboring region, like changing levels.

Use inexpensive distant scenery, a false horizon, tree silhouettes, fog or a
canopy to conceal the changeover. At a controlled outdoor crossing, the viewport
may briefly freeze, then resume at the matching position and facing in the next
region. Show only an absolutely minimal "Loading..." box at the upper center of
the screen for such a new-cell crossing, with no large overlay window or modal
dialog. Preserve the original-Morrowind-style loading presentation for interior/
exterior transitions that already use it. A brief explicit load is an
acceptable experiment if it keeps the active world within memory. Backdrops
must agree with the destination view and must not pretend to be reachable,
interactive terrain; collision must be ready before movement resumes.

Terminology clarification, 20:29 Helsinki: Doom stores map data and other
resources in WAD archives. Quake uses compiled BSP levels, commonly packaged in
PAK archives; its WADs hold graphics resources. AmiWind currently loads loose
`seyda.bsp`, `prison.bsp` and `census.bsp` files from `id1/maps/` on the HDF,
with a separate `gfx.wad` for graphics. Call this proposal **polygonal BSP
regions with associated resource packs**. The polygon describes the region's
world footprint; the resource container remains a separate choice. This
corrects the original shorthand without changing the proposal. Owner clarification,
20:31 Helsinki: the intended term is **polygonal BSP regions**, akin to the
bounded levels of Doom and Quake. The footprint is the area being loaded, not
a claim that Doom and Quake use the same map-file format.

**Preserve both approaches.** Keep the original cell mapping, source assets and
existing conversion recipes. Add region partitioning as an optional conversion/
loading strategy, with a manifest connecting original cells and placed references
to each runtime region. Preserve world coordinates, player/quest/NPC state and
stable object identities across swaps. Overlapping coverage must not duplicate
actors, colliders, scripts, loot or reset taken items. Runtime region boundaries
must not redefine the original cell-dependent game rules.

Compare a Seyda Neen region prototype with the cell/chunk approach using the same
route: resident and peak transition RAM, load duration, frame time, audio
continuity, visual seams and repeated crossings. Test returning to a region,
save/load and failed-load recovery. A loading animation needs time to update;
do not claim responsive feedback while an unbroken synchronous load blocks it.
Do not assume two complete regions fit in memory during handoff. Choose the
approach from these measurements; no best method or speedup is established yet.

Follow-up: [world mapping options](WORLD_MAPPING_PLAN.md#optional-polygonal-poi-regions)
and [roadmap experiment](ROADMAP.md#optional-polygonal-poi-regions).

### 20:36 Helsinki — open-world/topographic-map limitation and elevated mode

The owner flags a major problem with this region approach: Morrowind's open-world
layout and topographic map do not stop at our selected POI boundaries. A high
viewpoint can expose region edges, false horizons and missing neighboring terrain.
Ground-level fog/backdrops alone do not establish that this design will work.

Proposed experiment: when the player is more than a configurable distance X
above the local ground, switch to a separate elevated terrain/view mode, perhaps
a broader, coarser topographic representation. The original "Y axis / Z-plane /
vector" wording expresses an altitude-triggered representation; define the
actual engine up-axis and terrain-height query before implementation. Measure
height above local terrain, not just height above sea level. This is a different
rendering/residency mode, not permission to change the player's world coordinates
or move gameplay onto a disconnected plane.

Check what remains visible and interactive from above, how neighboring regions
are represented, and how descent restores nearby detail/collision. Preserve one
world/topomap mapping and persistent state through both modes. Consider separate
enter/exit height thresholds to prevent rapid switching near X. Measure memory,
handoff stalls and visual continuity on hills and across region boundaries.
This is an unresolved architectural risk and an experimental mitigation, not
evidence that polygonal regions already preserve open-world traversal.

### The fog is our friend

28 September 2026, 20:37 Helsinki.

**The fog is our friend.** Even the elevated-mode experiment would be tricky.
Horstator points to Xbox-era Morrowind as the reference for using limited view
distance under constrained graphics resources. Keep fog central to AmiWind's
design: it gives us a bounded visible neighborhood for rendering and loading,
and it preserves the original world's mystique by leaving distant places unseen.
Maximum visibility is not automatically the better artistic result.

Use fog to support real distance culling and measured loading/offloading; simply
painting fog over geometry that stays resident and is still processed does not
deliver those savings. Keep enough collision/prefetch margin for movement and
turning, and check the atmosphere as well as frame time and RAM when tuning the
distance. Retain this principle whichever cell or polygonal-region strategy wins.

### 20:38–20:39 Helsinki — entire-world terrain topomesh and inspection scene

Near-term priority: build a topographic mesh of **the entire map's terrain**,
not just Seyda Neen or the opening area. Use the original exterior terrain data
in one consistent world-coordinate system, retain source-cell identity and
report missing coverage. Then inspect original water levels and shorelines.
Keep a full-detail terrain baseline before making reduced LOD variants.

Provide a separate terrain-only inspection scene or observer mode where the
world can be examined in peace, without the intro, quests or NPC simulation.
Use a free camera, world/cell coordinates, optional wireframe/cell boundaries,
water visibility, adjustable fog/view distance and selectable terrain LODs.
Inspect the full landmass, elevated views, slopes, coastlines and transitions;
show triangle/resource counts and measured runtime limits so we can determine
what is possible and how far each approach can go.

The full terrain dataset and host overview do not imply loading the entire
full-detail mesh into Amiga RAM. Keep the inspection path capable of bounded
regions or coarse overview LODs, preserve the original mesh and water metadata,
and compare visible error, seams, memory and frame time. This is the next
world-mapping experiment, not an implemented dev4 feature or a committed region
partition. Use its results to choose LOD, fog, streaming and POI boundaries.

### 20:40 Helsinki — a thought for Carmack

> Horstator has been greatly amused by the idea of John Carmack himself one day witnessing Morrowind on Amiga via the otherworldly 3D gimmicks he did back in the day for Quake and such.

### Tables, tables, we need more tables

28 September 2026, 20:41 Helsinki. Map out the parameters needed for the game as
a whole: character attributes and everything that affects them, skills, effects,
quest progression, globals, containers, items, NPC state, dialogue conditions,
world references and their relationships. Avoid building isolated next-scene
flags without understanding the wider conditional state model.

For each field/rule, record its source, identity, type/range, initial value,
readers, writers, dependencies and persistence requirements. Distinguish base
records from placed references, base values from modifiers/derived values, and
durable state from rebuildable caches. Keep verified source behavior separate
from proposals and unknowns. Use these tables to drive conversion, runtime
structures, save schemas and acceptance cases, with Amiga memory limits in view.
See [the development catalogue requirement](DEVELOPMENT.md#tables-tables-we-need-more-tables).
