# NPC appearance, greetings and dialogue study

Status: checkpoint-013 adds facing/proximity Hello to checkpoint-012
nonblocking idle actors. E remains a voice audition. Walking, full original
dialogue filtering and quests are not implemented.
The requested content includes Fargoth's missing-ring interaction and guard
move-along greetings. Resolve their actual record IDs and conditions from the
installation before implementation; do not assume a remembered phrase is a
voiced line or invent a sound mapping for a text-only response.

<!-- contents start -->
## Contents

- [References and observed behaviour](#references-and-observed-behaviour)
- [Proposed conversion contract](#proposed-conversion-contract)
- [Appearance and acceptance plan](#appearance-and-acceptance-plan)
- [27 September 2026 conversion research handoff](#27-september-2026-conversion-research-handoff)
- [Checkpoint-012 implemented subset](#checkpoint-012-implemented-subset)
- [Checkpoint-013: three distinct behavior paths](#checkpoint-013-three-distinct-behavior-paths)
- [Expanded host roster and activity work](#expanded-host-roster-and-activity-work)

<!-- contents end -->

## References and observed behaviour

- [UESP: Morrowind — Generic Dialogue Voiced](https://en.uesp.net/wiki/Morrowind:Generic_Dialogue_Voiced)
  is the owner's requested community reference for identifying voice lines.
  Its page returned HTTP 403 during this check; no recordings were downloaded.
  Keep the link for manual cross-checks against the owner's installed data.
- [OpenMW dialogue manager](https://github.com/OpenMW/openmw/blob/master/apps/openmw/mwdialogue/dialoguemanagerimp.cpp):
  `DialogueManager::say` rejects actors already speaking, submerged NPCs and
  knocked-down actors. It looks up a dialogue topic, applies `Filter::search`,
  then uses the selected response's sound path and optional subtitles/result
  script. This is different from shuffling every audio file associated with a
  voice. Interactive dialogue entry uses a separate greeting-record path.
- [OpenMW actor behaviour](https://github.com/OpenMW/openmw/blob/master/apps/openmw/mwmechanics/actors.cpp):
  `updateGreetingState` uses proximity, the Hello setting, visibility/awareness
  checks and a greeting state/timer; it requests the `hello` topic and resets
  after the player moves sufficiently far away. `playIdleDialogue` separately
  gates idle speech by actor state, distance, visibility and a time-scaled chance.
  Its comment explicitly distinguishes that timing from original frame-dependent
  behaviour. Do not poll once per rendered frame on an Amiga.

These two implementation files were inspected in the master view on
2026-09-27. Pin and record a specific revision when implementing the converter.
Further source-reading targets: `mwdialogue/filter.cpp`, `filter.hpp`, and
`components/esm3/loadinfo.*` / `loaddial.*`. The full filter source was not
retrieved in this check; record ordering and all condition semantics still need
verification. No OpenMW implementation code is copied into the GPLv2 runtime.

## Proposed conversion contract

Read the owner's NPC, inventory/body-part, dialogue and response records and
resolve voice paths through the installed game data. Preserve actor identity,
topic/response IDs, record order, eligibility conditions and result-script
references in the private intermediate. Report unsupported conditions or scripts
explicitly; do not silently turn them into unconditional greetings. Generic
responses can be shared across actors, so actor ID alone is not a voice mapping.

The first runtime subset should select an eligible greeting for the current
actor/state, avoid overlapping that actor's speech, play locally converted audio
and enforce a bounded trigger/reset policy. Preserve source settings where
supported and label any simplified behaviour. Full topics, journal progression,
choice handling and script execution are later work. Do not execute result
scripts partly and then claim quest compatibility.

## Appearance and acceptance plan

Assemble each initial outfit on the host and bake compact idle/walk frames for
AmiQuake's animated model path. Clothing/armour can replace geometry as well as
textures. Start with complete appearance variants; equipment removal and a base
body/underwear variant come after the normal outfits work. Keep all derived
models, textures, response text and audio outside the public repository.

Measure one actor, then three: frame time, visible triangles, model/skin cache,
voice buffer use and music deadlines. Use deterministic synthetic fixtures for
eligibility, missing audio, active speech, trigger reset and unsupported-condition
handling. Record actor/response IDs in private diagnostics to reproduce selections.
This provides a route to recognizable townsfolk without claiming that Quake's
renderer already implements Morrowind's actor system or dialogue rules.

## 27 September 2026 conversion research handoff

Work began on Fargoth and two exterior Imperial Guard references in the bounded
Seyda Neen scene. It paused for the reproduced dev3 startup collision regression;
checkpoint-011 contains that repair. No character model or greeting has yet
been integrated into the native scene. The private research checkpoint retains
ordered original subrecords, actor references, dialogue inspection and NIF probes.

Implementation references were retrieved from OpenMW revision
`46bd4599203ee52ffc0f3e8edb3fc159a0303a49`:
`apps/openmw/mwrender/npcanimation.cpp`, `components/sceneutil/attach.cpp`,
`apps/openmw/mwrender/animation.cpp`, `apps/openmw/mwdialogue/filter.cpp`,
and `components/esm3/loadbody.hpp`, `loadnpc.hpp`, `loadclot.hpp`, `loadarmo.hpp`,
`loadinfo.hpp`. These are behaviour/file-format study references, not bundled
implementation or a linked runtime dependency.

Findings from the owner's base-game records and PyFFI inspection:

- NPC inventory and outfit part records repeat tags; parsing into a simple
  dictionary loses inventory items and left/right part assignments. Retain order.
- Fargoth's normal shirt, trousers and shoes replace several body segments.
  Body, head and hair are distinct records. Guard equipment also references
  leveled lists; resolve those deterministically and record the chosen variant.
- Rigid parts attach to named skeleton nodes; left-side rigid meshes need
  mirroring and matching triangle winding. Skinned files can hold several body
  parts: select the matching shape names instead of duplicating the whole file.
- The original base animation NIF contains a skeleton, per-bone controllers and
  animation text keys. The inspected idle controllers mostly use linear keys;
  unsupported key types must be handled explicitly, not silently treated as
  linear. Skinned and rigid attachments need separate transform paths.
- Alias-model baking should simplify once and retain topology across frames.
  Use one bounded appearance variant first; budget texture atlas, triangles,
  vertices and frame cache before attempting equipment permutations.
- Eligible voiced Hello records include race/sex/class/disposition and other
  filters. Result scripts and unsupported conditions cannot simply be ignored.
  Preserve linked response order and distinguish comments from executable results.
- Fargoth's ring-topic and initial ring-related interactive greeting records
  inspected here have text and conditions/scripts but no associated SNAM voice.
  A generic voiced Hello can be added separately. Do not invent a voiced ring
  request or trigger quest/result scripts without the required state machinery.

Next concrete deliverable: host-only outfit assembly with visual checks,
compact idle-frame export, then one and three native actors with measured memory
and frame cost. The startup repair must remain green when adding their colliders.

## Checkpoint-012 implemented subset

`tools/prepare_npcs.py` reads the supplied installation locally. It assembles
male humanoid body/head/hair and normal clothes/armour, resolves the guard's
leveled clothing choice with a recorded deterministic seed, and samples eight
poses from the original base skeleton's Idle text-key interval. Weapons,
shields, female and beast skeletons, walking AI and outfit changes are outside
this slice. Some rigid parts are mirrored for the left side; skinned parts use
inverse binds and sampled bone transforms. Meshes share topology across frames.

The host simplifies each outfit to approximately 500 triangles, bakes small
per-face texture tiles into a 512 x 256 indexed skin, and emits Quake MDL v6.
The Amiga performs no skeletal skinning. Two shared appearances supply Fargoth
and two Imperial guards at original exterior references. Rendered details and
skin quality remain coarse. NPCs are deliberately nonblocking during testing.

E selects a nearby visible actor in the view direction. One locally converted
8-bit mono 11025 Hz greeting plays over the existing music, with a subtitle
and a four-second shared cooldown. This is a **voice audition**: the host picks
a generic Hello response using a fixed disposition fixture of 50 and supported
race/sex/identity/class fields. It rejects scripts, quest/location conditions,
faction and rank checks. It does not emulate full original INFO selection or
proximity greeting behaviour. Guard-special dialogue and Fargoth's text-only
ring quest remain on the roadmap. The private report records the exact selected
response IDs, paths, actor references and equipment choices.

Nord first-person bare hands and a baked punching animation are the next player
body milestone, followed separately by hit/damage tests. Preserve walking bob.

## Checkpoint-013: three distinct behavior paths

References inspected at OpenMW revision
`46bd4599203ee52ffc0f3e8edb3fc159a0303a49`:

- [actors.cpp](https://github.com/OpenMW/openmw/blob/46bd4599203ee52ffc0f3e8edb3fc159a0303a49/apps/openmw/mwmechanics/actors.cpp):
  nearby Hello checks at 0.25-second intervals; two qualifying checks before
  requesting speech. Distance uses actor Hello times iGreetDistanceMultiplier;
  fGreetDistanceReset rearms it. State, LOS and awareness gates apply. Greeting
  turns toward the player; movement is interrupted during the turn.
- The same file's Idle speech path is separate: eligible nearby visible actors,
  no current speech/combat/follow/escort/swimming, with a time-based probability.
  This explains occasional ambient remarks without player activation. It is
  not the same as the interactive Greeting dialogue selection.
- [aipackage.hpp](https://github.com/OpenMW/openmw/blob/46bd4599203ee52ffc0f3e8edb3fc159a0303a49/components/esm3/aipackage.hpp)
  and aipackage.cpp document ordered authored packages. Wander specifies range,
  duration, time of day, eight idle weights and repeat. AIDT Hello is uint16,
  not uint8. Runtime movement must also obey path/collision constraints.

The independent AmiWind converter records those packages and decodes Wander;
raw unsupported package fields remain in the private report. The current runtime
only uses original Hello distance/reset/duration settings (scaled once to scene
units), checks nearby LOS at 4 Hz, turns at 8 Hz and keeps idle poses separately.
Two qualifying polls request a Hello audition; it cannot retrigger until the
player leaves the reset radius. A shared eight-second automatic/four-second
manual cooldown bounds voice overlap. Nonwalking/dead/submerged players do not
trigger automatic speech. Distance rejection precedes LOS work.

This is a deliberately limited scene policy: it lacks original awareness,
combat/crime/disposition updates and complete INFO condition evaluation. E calls
the same preselected generic Hello sample; it does not yet open the original
Greeting dialogue. Idle speech and actual wandering are deferred until their
eligible lines, walk animation, route selection and interruption handling exist.
No OpenMW implementation is copied into the GPLv2-compatible runtime.

## Expanded host roster and activity work

`tools/audit_vicinity.py` now gathers all placed NPC identities within a bounded
source-cell audit plus directly linked interiors. It preserves ordered action
packages and indexes voice candidates using identity filters without requiring
a renderable male humanoid outfit. Interior actors remain a separate roster.
This does not add native NPCs or approve playback of every candidate.

Next native additions must keep placed IDs, disabled/dead/opening states and
scene residency separate from shared appearance/voice assets. Support missing
female/beast appearance paths before claiming full town coverage. Compile supported
conditions and time-based activity triggers on the host; report unsupported ones.
A dialogue pool is a set of eligible responses after state/order filtering, not
every MP3 for a race or a random selection from raw static candidates.
