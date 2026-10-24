# Initial NPC placement and ground-contact workflow

_Last updated with AmiWind v0.0.48-rc1 (23 October 2026)._

<!-- contents start -->
## Contents

- [Classify the intended initial state first](#classify-the-intended-initial-state-first)
- [Actors start where the game puts them](#actors-start-where-the-game-puts-them)
- [Room residents by rule](#room-residents-by-rule)
  - [Where a CHIM room's residents are fitted (v0.0.48)](#where-a-chim-rooms-residents-are-fitted-v0048)
- [Interior creatures and the levitating class](#interior-creatures-and-the-levitating-class)
- [Actors the original disables at the start](#actors-the-original-disables-at-the-start)
- [Main gate: host build, before packaging](#main-gate-host-build-before-packaging)
- [Runtime correction](#runtime-correction)
- [Native integration checks](#native-integration-checks)
- [Diagnostic RC2 exception](#diagnostic-rc2-exception)
- [rc3 retained contact findings and rc6 early checking](#rc3-retained-contact-findings-and-rc6-early-checking)
- [Source progression review, 1 October 2026](#source-progression-review-1-october-2026)
- [rc7 mesh-aware correction](#rc7-mesh-aware-correction)

<!-- contents end -->

Ground residents must stand on the converted walkable surface, including stairs,
bridges, platforms and interior floors. Original placement Z is an input, not
proof of foot contact after geometry conversion. The design behind it (why the game data puts actors a little above
the floor, what OpenMW and Quake do, the build-time rule and the runtime safety net) is on
[Actor placement](ACTOR_PLACEMENT.md); this page is the workflow and the checks.

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

## Actors start where the game puts them

The maintainer's rule (22 October 2026): every NPC and creature starts at the position and rotation its reference
has in the game data. Nothing relocates an actor to a nicer spot. Some starts are odd on purpose: the wizard who
falls from the sky near Seyda Neen at the start of the game (Tarhiel) is placed high in the air, and his script
makes him fall. So the ground check never pulls an actor down that the game put up.

How the CHIM region frames apply it (experimental, `--chim-region-actors on`; the town frames place their
residents as before):

| The reference | What happens |
| --- | --- |
| stands within 32 Quake units (128 game units) of the ground, or of the water surface under it | the ordinary ground contact, x and y kept: the towns' contact rule sets the height where the actor's soles touch the frame's collision under it, and the frame map's contact check measures the result |
| stands higher than that above the ground or the water, swims well above the sea floor, or lies under the ground | the authored spot is kept (`aw_ground_mode 1`, so the engine's floor snap leaves it too) and the build receipt lists it as authored off the ground, with its height and its script when the record has one |
| is classified in `config/actor_grounding.json` as flying, levitating, swimming, scripted airborne or authored dead | the authored spot is kept, as in the towns |

32 units is also how far the engine's own floor snap reaches when an actor spawns (`AW_NPCFloor`), so the builder
and the engine draw the line in the same place. An NPC or creature the policy file does not list is classified
from the data this way and recorded per actor in the receipt (`image/chim-region-actors.json`), never silently.

Levelled creature lists are not placed in a frame map: the game rolls a list at the player's level when the cell
loads, and a frame map row holds one fixed creature, so the builder does not pick one. They are listed per frame as
deferred with that reason; the actor table rolls them when a cell joins the type 1 window.

The ordinary ground contact keeps the reference's x and y. The towns' sideways search, which may move a resident
up to 48 units to find a spot where every sole touches, is not used here: it would move the actor off the spot
the game gave it. An actor whose soles do not all touch at its own spot (a slope, a rock edge) stands on the
ground under its reference point, as the engine's own snap would put it, and the receipt records each sole's gap.

Measured on 22 October 2026 on the v0.0.47 release run's game data and CHIM world, read only (the region frames'
actor step run without a build):

- 999 of the 1,348 region frames have exterior actor references; 336 of them get actors. 781 actors are placed
  (468 NPCs, 313 creatures). 5 references are left to the town frame that places them and 9 have no model in the
  actor library; each is listed with its reason.
- 101 actors start more than 32 units above the ground or the water under them. 85 of them are creatures the
  grounding policy or their record keeps off the ground (slaughterfish and dreugh swimming, netch and cliff racers
  flying; one of them, a netch, has a breeding script). 16 others keep their authored spot and are listed: 8 have
  a script (Dreamer_Talker07, Fjol, golden saint_staada, lucan ostorius, m'aiq, paur maston, viatrix petilia,
  centurion_sphere_hts2), 8 have none (an Imperial Guard, four mudcrabs, a guar, a nix-hound, a shalk). Most of them
  stand 33 to 68 units up, which looks more like ground or a rock the conversion lost than an airborne start: each
  is a place to check in game.
- Tarhiel (`agronian guy`) is not a region frame actor: his cell belongs to Seyda Neen's town frame, which keeps
  him in the sky by the policy class `scripted_airborne`.
- 601 actors get the ordinary ground contact: 354 with every sole touching, 247 on the ground under their
  reference point with some soles off (94 of them within 2 units, 70 within 4, 83 more or over no support).
- 4,853 levelled creature references are deferred (in 982 frames).

## Room residents by rule

From v0.0.48 the rooms of the room list (`config/room-batches.json`, every interior of the base game) follow the same
rule, per reference, without a hand-made class per NPC (ROOM-BATCH-NPC-GROUNDING-48). Before, the room batches stage
refused a batch whose residents the policy did not name (Ald-ruhn's first batch: 62 NPCs in 22 rooms).

`tools/actor_grounding_census.py --rooms` reads every NPC and creature reference of every listed room from your game
data and compares its feet with the room's floor under them: the room's own placements (statics, activators, doors,
containers, lights) with their visible and collision triangles, placed as the scenery converter places them, which is
what the room's CHIM collision is made from. The tolerance is the exterior census's: the highest support at most 32
game units above the feet, at most 128 below them (32 Quake units: the support fitter's reach and the engine's floor
snap, `AW_NPCFloor`).

| Class | The reference | What happens |
| --- | --- | --- |
| `floor` | its feet within that band of the floor (or of a chair, bench or table it sits on) | the ordinary ground contact |
| `off_floor` | more than 128 game units above the floor under it | its authored spot is kept (`aw_ground_mode 1`) and it is listed with its script |
| `no_floor` | no floor under it in the room | kept and listed |
| `authored_dead` | the record is placed dead | its death pose at its authored spot |

`--write-rooms` writes the classes to `config/actor_grounding_rooms.json`: per room and class, the reference number
and the record ID (and the script of one kept off the floor), no positions or heights. `tools/actor_grounding.py`
reads it only for an actor `config/actor_grounding.json` does not name, and only by its reference number: an ID is
never classified everywhere by it, and a town resident keeps the policy's class. The room batches preflight, the
resident stage, the interior creatures and the contact check pass the reference. A levelled creature list is no actor
yet (the game rolls it when the cell loads) and is listed as deferred; nothing is dropped.

Measured on 23 October 2026 on the room list of 1,134 rooms (40 batches, every interior of the base game), read only,
in 100 s on 6 cores:

- 913 rooms have actors: 3,007 references (2,477 NPCs, 530 creatures). 2,819 stand on the floor, 143 are authored
  dead, 45 are kept off the floor, none has no floor under it. 1,270 levelled lists are deferred.
- The 45 kept off the floor: 43 creatures, nearly all slaughterfish and dreugh in the water rooms (they swim; up to
  about 1,076 units over the bottom) and two winged twilights in Maelkashishi; and two NPCs: Alvos Sadri in
  Kumarahaz (143 units up) and a Hlaalu guard in Caldera Mine (177 units up), whose record the policy already lists
  as ground, so the policy's class stands there. Both are places to check in the game.
- 667 references are of records the policy already names; the rest (2,340) take their class from the file.
- Of the references on the floor, 440 stand more than 32 game units above it and 90 more than 64: the game data puts
  many actors a little above their floor, as outdoors.

The file is made from the game data and lists only reference numbers and record IDs. Run the census again when the
room list changes (a new room makes the preflight name it and the command to run).

### Where a CHIM room's residents are fitted (v0.0.48)

A CHIM room has no classic floor until the image installs it. The town room stages convert their rooms as shells
(`--room-form shell`), and the batch rooms always were: a room map with its entities and no placed mesh and no
collision of its own, standing on the interior store's models once the image installs the CHIM rooms. So a shell
room's residents are fitted and measured in the image step, in this order:

1. The scene stage's early check (`tools/check_scene_actors.py`, before the image) classifies a shell room's
   residents (identity, support mode, death pose, transform, owner) and records them as `deferred-to-chim-room`
   (`defer_shells` in `tools/check_actor_ground.py`): there is no collision yet to measure. A shell still present at
   the image is measured as before and refused (CHIM-ROOM-SHELL-ACTORS-EARLY-48).
2. The image installs the CHIM rooms. A shell room's world declares the converted humanoid standing hull the check
   reads, as a room converted whole does (CHIM-ROOM-SHELL-NO-HULL-48).
3. The CHIM room actor bake (`tools/room_actor_bake.py`, `bake_room_ground`) fits every ground resident of every CHIM
   room on exactly the collision the check measures (the store models, each moved and turned by its record). The
   rule is the build-time one on [Actor placement](ACTOR_PLACEMENT.md#amiwinds-contract): the first walkable surface
   of the room under the resident within 8 units over and 32 under its recorded spot, the origin 0.25 over it, every
   idle sole within -0.5..1.0, else the nearest spot within 32 (then 48) units; a resident that fits nowhere is
   refused and reported. It writes the same fields as the map bake (`aw_ground_valid`, `aw_ground_baked`,
   `aw_authored_origin`). Before this bake the residents of batch rooms kept their game-data height, 1 to 15 units
   over the floor, and the check refused 1,662 of them
   ([ROOM-ACTORS-FLOATING-48](bugs/ROOM-ACTORS-FLOATING-48.md)).
4. A guard (`require_fitted`) stops the image step, naming the maps, if any ground resident of any map the check
   reads carries no mark of a ground bake.
5. The actor contact check (`tools/check_actor_ground.py`, without `defer_shells`) measures all of them.

Residents the bake cannot place are decided case by case in `config/actor_room_placements.json`: `authored` (kept
where the game data puts them, with the reason; the check reports each as an explicit exception) and `placements`
(an origin written as given, judged by the check). `AMIWIND_ROOM_ACTOR_BAKE=off` skips the bake (the method before it,
for comparison). The 110 pose exceptions (108 authored dead, one authored, `vivec_god` levitating) are never fitted.

Harvestable mushrooms are not residents and are not left in a room record: a plant exists once, as its harvest
entity, in a CHIM room as on the CHIM world outdoors
([CHIM-ROOM-HARVEST-DOUBLE-48](bugs/CHIM-ROOM-HARVEST-DOUBLE-48.md); [store details](chim/INTERIOR_STORE.md)).

## Interior creatures and the levitating class

From v0.0.42 the resident stage (`tools/prepare_area.py` populate, through `tools/creature_residents.py`)
also places creature records (CREA) in converted interiors (INTERIOR-CREATURES-MISSING-41). Before, it took
NPC records only and dropped every creature without a log line. `--interior-creatures` selects which:

| Mode | What is placed |
| --- | --- |
| `listed` (default) | the creatures in `config/interior_creatures.json`, each with a reason and a source: Vivec (`vivec_god`) in the Palace of Vivec |
| `all` (experimental) | every interior creature reference that `config/actor_grounding.json` classifies and whose model bakes |
| `off` | no creature: the method before v0.0.42 |

A creature's model is its own NIF posed on its own skeleton: 8 frames over one loop of its idle group (the
gallery profile's `pose_event` group in `config/gallery_model_quality.json`, else `idle`), at the original
scale and **not** moved to the floor, so the height the animation gives the body above the reference point is
kept. Vivec: the `idle2` loop (his AI_W idle chances give Idle2 60; his model has no `idle` group), the posed
body from 13.9 to 33.1 Quake units above his reference point. A placed creature is an idle `aw_npc` like the
placed NPCs: no greeting, dialogue or combat yet (nothing is invented).

The support state is the policy's class, never a rule for one ID in code. `levitating` (aw_ground_mode 1)
means the authored animation holds the body above the actor's reference point: the host contact fit and the
image-stage ground check skip the actor, and the engine's floor snap (`AW_NPCFloor`) leaves the origin where
the reference put it. Source for Vivec: the record has neither the Flies nor a Levitate effect, so the
original engine keeps his actor on the floor and the lift is the animation's; his reference point is
0.15 Quake units under the converted palace floor, so keeping it equals snapping it within that.

Every room reference the stage does not place is listed with its reason in the stage report
(`<town>-interiors.json` or `area-report.json`, `left_out`: map, reference, ID, type, reason): creatures not
listed, levelled creature lists (the pick is not resolved at build time), authored dead creatures (no
creature death pose bake yet), creatures the policy does not classify (`all`), instance scales other than 1,
models that do not bake (`all`) and NPCs excluded by the town settings. The report's `creatures` row gives the
mode and the number placed.

Island-wide, the base master places 530 creature references in interiors (178 records, 222 cells). With
`all`, Vivec is the only one classified today: 494 references have no grounding classification and 35 are
authored dead. Classifying them is source work (Flies flag, the Levitate effect, water level, measured
support), as for the NPCs; by their records 330 walk, 108 swim only, 1 flies and 91 have none of the three. From
v0.0.48 the creatures of the listed rooms take their class per reference from the room file
([room residents by rule](#room-residents-by-rule)); authored-dead creatures are still left out of the rooms (the
actor library's corpse model, its own death pose, is used outdoors only so far).

## Actors the original disables at the start

A new game in the original does not show every actor its cells list. The global script the game always
runs starts a run-once start script, and that script's `->Disable` lines take 78 references out of the
world before the player arrives (58 NPCs, 20 creatures; the twelve town Dreamers, the Dreamer Prophet and
characters of later quests). A disabled reference only leaves the scene: its own script keeps running, and a
Dreamer's script enables it when the main quest's journal `A2_2_6thHouse` reaches 50; others come back
through a quest script or a dialogue result ([NPC-STORY-DISABLED-AT-START-42](bugs/NPC-STORY-DISABLED-AT-START-42.md)).

From v0.0.47 the resident stages (`tools/import_town.py` residents for towns and CHIM towns,
`tools/prepare_area.py` populate for rooms and Seyda Neen) can read that list from the game data with
`tools/start_disabled.py`: the scripts the global script starts, their unconditional `->Disable` lines
(a line inside an `if` block is reported, not applied), and for each reference how it is enabled again.
`--start-disabled` selects what a build does with them:

| Mode | What is placed |
| --- | --- |
| `placed` (default) | every actor placed, as before |
| `original` (off by default, A/B) | the faithful start: the actors the start script disables are left out of a new game; each is listed with its enable rule (`residents.json` `start_disabled`, the area report's `left_out`) |

`original` stays off by default until the runtime enable exists: without it, an actor left out never comes
back (the Dreamer Prophet and the quest characters would be gone for good).

The enable rule is read, never guessed: a reference's own script counts as a journal condition only when it
is the simple template (a journal index read, a guard that returns, one `Enable` under one journal
comparison); every other script and dialogue result that names `ID->Enable` is listed by name; anything else
is recorded as unknown until the script compiler exists (docs/ROADMAP.md, game logic). AmiWind does not run
the main quest's journal stages yet, so nothing enables a held actor during play; the listed rules are the
input for the world state's "disabled at start" records, which are what lets `original` become the default. Objects the start script disables (scaffolding, notes,
keys) are listed in the table but not filtered.

## Main gate: host build, before packaging

1. Finish visible geometry and collision, including stairs, platforms and floors.
   Resolve each resident in its owning sub-cell, with that scene's full support
   geometry. Use the bounded placement pass to fit the rendered initial idle soles (for CHIM rooms, in the image step
   after the rooms install: [above](#where-a-chim-rooms-residents-are-fitted-v0048)). Preserve
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
matches `aw_ground_baked` within 0.001 unit. A resident spawns with movetype none (it never falls), and 0.1 s later
the engine's floor snap (`AW_NPCFloor`) keeps a baked resident exactly and sets it on the ground; the snap is a
safety net, and build and runtime agree (on a baked copy of all the CHIM rooms of dev2 try 11, all 2,341 fitted
residents were kept exactly). See [Actor placement](ACTOR_PLACEMENT.md#amiwinds-contract). Re-snapping only its origin would
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
   checked maps, remaining exceptions and maintainer acceptance in public notes.

The audit never moves actors. Automatic correction and independent measurement
are separate steps. Do not hide a failure by removing the NPC from the report or
marking it airborne without source evidence.

The guarantee is that every packaged, classified initial ground placement passes
the declared checks, or the build fails. It does not certify unknown scripts,
arbitrary later movement or future animation. Initialization, save restoration
and sub-cell copying must preserve the accepted placement; runtime movement
systems need their own support rules when implemented.

## Diagnostic RC2 exception

The maintainer requested an interim RC2 while placement and model-budget investigations
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

The maintainer recalls earlier unintended floating NPCs outdoors in Balmora. The
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
