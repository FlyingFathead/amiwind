# Initial NPC placement and ground-contact workflow

Ground residents must stand on the converted walkable surface, including stairs,
bridges, platforms and interior floors. Original placement Z is an input, not
proof of foot contact after geometry conversion.

<!-- contents start -->
## Contents

- [Classify the intended initial state first](#classify-the-intended-initial-state-first)
- [Main gate: host build, before packaging](#main-gate-host-build-before-packaging)
- [Runtime correction](#runtime-correction)
- [Native integration checks](#native-integration-checks)
- [Diagnostic RC2 exception](#diagnostic-rc2-exception)
- [rc3 retained contact findings and rc6 early checking](#rc3-retained-contact-findings-and-rc6-early-checking)
- [Source progression review, 1 October 2026](#source-progression-review-1-october-2026)
- [rc7 mesh-aware correction](#rc7-mesh-aware-correction)

<!-- contents end -->

## Classify the intended initial state first

The question is whether the actor is meant to have ground support at game/scene
initialization. It is not whether they are humanoid, tall, in a particular faction,
or capable of levitation later. The conversion writes original `aw_source_id` and
placed `aw_ref`. The versioned policy in `config/actor_grounding.json` explicitly
lists the ground residents currently converted and the other initial states.
An unclassified source ID stops conversion; it never silently defaults to ground.
Add classification during source/content intake, then automate the geometry work.

Ground classification describes the required support **when an actor is active**.
It is not an enabled-at-start flag, an AI schedule, or evidence that the actor
belongs in every quest state. A placed CELL reference supplies an authored
transform; local scripts, global startup scripts and dialogue results can change
its visibility, AI package or position. Preserve those decisions separately from
contact correction. A passing contact audit cannot certify quest-state fidelity.
See [character states](CHARACTER_STATES.md) for the Dreamer's later activation,
other confirmed lifecycle examples and the implementation requirements.

`aw_ground_mode=0` means an initially grounded resident. Mode 1 preserves a
documented flying, levitating, swimming, scripted airborne or authored dead state.
Tarhiel's original ID is `agronian guy`; the controller `fallingScript` enables him
in the sky and invokes Fall. Cliff racers and `vivec_god` are explicit airborne
examples. Do not classify all Telvanni as levitating. Keep source evidence and the
reason for every exception; none counts as a passed ground-contact test.

Authored corpses keep their death pose and placement. Their pose/contact checks,
swimming depth, flight clearance and later scripted movement are separate
contracts. A future placement-specific override must use the placed reference,
not change every instance of a source actor to hide one bad placement.

## Main gate: host build, before packaging

1. Finish visible geometry and collision, including stairs, platforms and floors.
   Resolve each resident in its owning sub-cell, with that scene's full support
   geometry. Use the bounded placement pass to fit the rendered initial idle soles. Preserve
   source reference, authored XYZ, support reference and every adjustment in evidence.
2. Write the canonical result into every overlap copy. Missing owners, inconsistent
   copies, unknown initial states and excessive or unsupported drops are errors.
   Do not repair a missing platform by snapping its occupant to terrain below.
3. Run the independent `tools/check_actor_ground.py` check on the final BSP and
   MDL files. It decodes actual quantized mesh vertices and samples the low mesh
   contact band across the declared initial idle poses, at the placed rotation.
   It measures support and gaps against packaged point collision. This catches a
   visually floating model even when its origin or collision box touches ground.
4. Stop image creation on every unresolved result. `build_aga.py image` writes the
   private `actor-initial-contact.json` receipt and requires a pass before creating
   the content fingerprint or HDF. The checker never edits placement.
5. Retain content hashes and exact scope/tolerances in that receipt. Re-run after
   geometry, hull, model, pose, scale, placement or classification changes. Validate
   the HDF read-back against the same payload hashes.

Manual invocation against an owned converted payload:

```sh
python3 tools/check_actor_ground.py /path/to/id1/maps --out /path/to/actor-initial-contact.json
```

The current geometric contract permits -0.5 to +1 converted unit at sampled low
mesh vertices; the contact band is the lowest 0.5 unit of each initial idle pose.
This is a finite, stated contract, not a claim of perfect foot IK or every future
animation. New stance/pose layouts must be declared. Semantic sole markers, swept
body clearance and moving-support attachment should extend this gate when those
features enter the runtime, rather than silently broadening its acceptance.

All mesh decoding, multi-point traces and reporting run on the build host. The
Amiga receives the final placement. There is no continuous multi-point grounding
scan and no need to keep the build reports or a second collision world in RAM.

## Runtime correction

rc7 preserves a host-certified initial point exactly when the current position
matches `aw_ground_baked` within 0.001 unit. Re-snapping only its origin would
undo mesh-aware correction. Moved/legacy residents still use the bounded origin
probe from 8 units above to 32 below, accepting walkable non-solid support with
a quarter-unit clearance. That fallback is not certification of arbitrary
movement, other poses or runtime support changes.

Balmora's distant render overlap contains some architecture with collision
intentionally removed. Conversion therefore measures each resident against its
owning sub-cell and writes that same resolved origin to all overlap copies,
retaining `aw_authored_z`. The same owning-core rule applies to Seyda Neen's
regular subdivisions. Runtime correction and ground acceptance for these towns
are restricted to that owning core. An audit row outside it says
`deferred-owner-core`, never `grounded`: visit the owner core and collect its
actual result. This prevents an overlap copy from being dropped through a visual
platform whose physical hull belongs to the neighbour. Interior scenes retain
their complete collision and are measured directly.

## Native integration checks

1. Use a fresh character and visit every converted map and relevant sub-cell.
   Let at least two simulation frames run after loading.
2. Run `dbg npcfloors`. It appends a read-only `npc-ground.tsv` report from live
   entities. Columns are map, placed reference, source ID, display name, status,
   X, Y, lowest model Z, support Z, and gap, in converted units.
3. Investigate every `floating`, `embedded`, `unsupported`, `blocked` or `steep`
   result. The default accepted foot gap is -0.5 through 1 unit, accommodating
   quantized model bounds, idle poses and the intentional clearance. `exempt`
   means a documented authored exception, not a pass.
4. Leave and return across sub-cell boundaries and doors; repeat the audit.
   Quicksave/quickload and repeat. A good initial spawn alone does not pass.
5. Inspect feet visually for every reported defect and representative races,
   footwear, slopes and platforms. Test the full idle cycle where feet move.
   Bounding-box contact alone cannot certify both feet on an uneven surface.
6. Keep the report and native captures in private release evidence. Summarize
   checked maps, remaining exceptions and owner acceptance in public notes.

The audit never moves actors. Automatic correction and independent measurement
are separate steps. Do not hide a failure by removing the NPC from the report or
marking it airborne without source evidence.

The guarantee is that every packaged, classified initial ground placement passes
the declared checks, or the build fails. It does not certify unknown scripts,
arbitrary later movement or future animation. Initialization, save restoration
and sub-cell copying must preserve the accepted placement; runtime movement
systems need their own support rules when implemented.

## Diagnostic RC2 exception

The owner requested an interim RC2 while placement and model-budget investigations
remain open. Its separate snapshot package retains the failed audit, exact payload
hashes and all 23 unresolved contacts. This is a diagnostic distribution exception,
not a successful placement gate. The normal `build_aga.py image` gate remains
unchanged and rejects this payload until those findings are resolved. The stated
all-placements guarantee applies to a passed production build, not this snapshot.


## rc3 retained contact findings and rc6 early checking

The retained payload audit reproduces 23 failing scene/actor cases covering 15
placed references. All require ground support when active. These are contact
defects in the converted idle placements, not evidence that every actor should
be active at the beginning of a new game. Some cases repeat across the regular
town, dock and courtyard scenes. They are not 23 different levitating characters.

| Scene | Placed actors |
| --- | --- |
| Addamasartus | Mulvisie Othril (282952), Melar Baram (282953), Banalz (365484), Baadargo (365485) |
| Balmora outdoors, owner bm015 | Dreamer (297839) |
| Hlaalu Council | Mervs Uvayn (67638) |
| Balmora Temple | Llarara Omayn (259838) |
| Seyda Neen | Dock guard (172852), Erene Llenim (128960), Indrele Rathryon (128961), Vodunius Nuccius (128962), Eldafire (128963), Fargoth (128964), Imperial Guards (128965 and 128966) |

The owner recalls earlier unintended floating NPCs outdoors in Balmora. The
outdoor Dreamer finding is relevant evidence, but there is not yet a verified
mapping from those earlier sightings to every current reference. The report
also includes penetration and unsupported/blocked samples, not only floating.
Three authored-dead placements were correctly reported separately as explicit
exceptions; they are not among these 23 failures.

The rc3/rc6 baker resolves support under the actor origin. The independent
audit checks low vertices of the quantized mesh across initial idle poses.
Those are different measurements: a supported origin does not prove supported
feet over uneven geometry. Proper repair must address actual mesh/placement
contact while preserving the strict checker, canonical overlap copies and
bounded support correction. Do not classify standing NPCs as flying to pass.

rc6 adds an actor-contact stage before world-terrain. It reproduces all 23 from
the retained rc3 scene without compiling world terrain. The final image audit
remains mandatory. An explicitly requested private-test baseline acceptance is
documented in [image recovery](IMAGE_RECOVERY.md). It does not mark the strict
gate passed, fix the placement defects or constitute production acceptance.

## Source progression review, 1 October 2026

The retained base master was inspected directly: NPC_ records, the 15 original
CELL reference numbers above, attached SCPT records, other scripts referring to
those actor IDs and matching dialogue-result scripts. Master SHA-256:
`5c3c8c2cbd20e25901b59b3ece33d36b7ef0e3d60ad8d11828bcc61a5ead1647`.
This review covers the base master, not expansion, mod or saved-game overrides.

| Actor | Original record/script evidence | Required distinction |
| --- | --- | --- |
| Dreamer, reference 297839 | `Startup` disables `Dreamer_Talker01`; its `dreamer_talkerEnable` script enables a disabled actor when `A2_2_6thHouse` is exactly 50. | The reference exists in the master but is not an unconditional new-game resident. Ground contact still matters when enabled. |
| Fargoth, reference 128964 | Attached `LocalState` holds a local variable. Separate `lookoutScript` uses `MS_Lookout`, time and proximity checks, then changes sneak/wander state and issues a sequence of travel commands. Dialogue results can terminate that sequence. | Reading only the attached script misses the quest route; the authored CELL position is not his permanent runtime position. |
| Dock guard, reference 172852 | `CharGenRaceNPC` sends him toward the plank and later the office door. `CharGenClassNPC` subsequently disables him with the boat objects. | Opening stages require different positions and eventual absence, not one permanently visible placement. |
| Vodunius Nuccius, reference 128962 | `voduniusScript` disables him on a cell change once `MS_Nuccius` is at least 100. | A grounded resident must still disappear when the original progression requires it. |
| Banalz and Baadargo, references 365484/365485 | Attached `slaveScript` distinguishes owned, for-sale, player-owned and freed states. It can issue follow/wander commands and disable a freed slave on cell change. | Preserve the source state transitions; this script capability alone does not establish that every branch is reachable for both individuals. |
| Other nine references | No attached script on their NPC_ records; authored AI_W packages exist. Mervs has zero wander distance; the other eight have nonzero distance. | They are not all stationary. Absence of a local script does not prove absence of external script or dialogue effects. |

The converted Dreamer is presently included as a resident, while the general
runtime has no implementation of `Startup`/`dreamer_talkerEnable`. That is a
separate visibility/progression gap. Do not describe grounding this actor as a
complete repair of its original behavior, or use later quest state to excuse
unsupported feet. The contact checker does not evaluate the quest state.

Required follow-up is to retain source activation and movement provenance by
placed reference, implement the relevant conditions using runtime quest/global
state, and test new-game, transition, scene re-entry and save/restore behavior.
Contact acceptance must remain separate and be rechecked for supported changes
of position or pose. Do not bake one quest's moved position into every state.

## rc7 mesh-aware correction

The fitter first retains a valid origin-grounded point, then tries vertical
adjustment. If needed it searches nearest-first over half-unit XY offsets within
32 native units. Candidate support must stay in the same owning core and within
16 units of the original supporting height; authored Z adjustment stays between
-32 and +8 units. A sampled approach path rejects unsupported gaps, walls and
steps over 4.5 units. Original coordinates remain in `aw_authored_origin` and
`aw_authored_z`; every overlap copy receives the same result.

Search uses conservative transformed model bounds to avoid tracing distant
brushes. The independent final checker still reads the entire unfiltered scene
and exactly the same mesh/tolerances. No actor is exempted or removed to pass.
Some repairs need a small horizontal relocation, not just lowering the origin;
those deltas are written to the private support report for inspection. These
constraints do not replace future swept-body or semantic foot-placement tests.

The current [validation receipt](validation/rc7-source.json) records measured
strict results and elapsed host-check time. The original 23 findings and their
source identities above remain historical evidence. Actual in-game positions,
scene return/save behavior and later actor progression still need playtesting.
