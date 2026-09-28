# Horstator's babblings on the state of AmiWind's development

Captain's log, 28 September 2026, 05:10–05:24 Helsinki.

Owner's development direction, recorded before the captain gets some sleep.
This is a request/decision log. Completion belongs in checkpoint validation records.

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
