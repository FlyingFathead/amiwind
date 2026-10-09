# NPC-BAKED-WHOLE-DUPLICATION-33: every NPC appearance is baked whole, so shared body parts are converted again for each actor

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 9 October 2026, in v0.0.32 |
| Where | NPC gallery and resident stages (tools/npc_geometry.py, prepare_gallery.py) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32 (last seen) |
| Severity | medium: Build speed and disk: 1,726 distinct parts are baked into 3,500 appearances (6.5 CPU hours); blocks equipment changes. |
| Family | Build speed (`build-speed`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine fec142b |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Open. Present in every build so far (measured on the v0.0.32 release build made from scratch).
Design and measurements: [MODULAR_NPCS.md](../MODULAR_NPCS.md). A host prototype (parts baked
once and concatenated) and regression tests are on the branch v0.0.33-modular-npc, not shipped at
the time of writing. It affects legacy and CHIM builds alike: CHIM frame maps carry the same
per-actor models.

## Symptom

Owner, 9 October 2026: the builder still wastes compute on NPCs, and the design has painted itself
into a corner, because humanoid NPCs share most of their body parts and because looting or changing
equipment must change an actor's appearance. Measured:

- The 2,675 humanoid records resolve to 3,500 appearances built from 68,001 part uses, but only
  1,726 distinct parts (942 mesh files). Each part is converted about 39 times.
- The gallery stage converts all 3,551 models from scratch in 2,034 s on 24 threads (23,388 CPU s,
  6.5 CPU hours), the longest stage of the build; whole-appearance baking processes 12.3 million
  source triangles where the distinct parts hold 0.40 million.
- Each placed actor ships its own complete model (about 200 KB, 66 % of it skin tiles); the whole
  game baked this way would need about 535 MB of actor models.
- A baked model cannot show an actor with one item removed: equipment changes are impossible.

## Where

`tools/npc_geometry.py` (`assemble`, `bake`), `tools/prepare_gallery.py` (gallery),
`tools/prepare_area.py` (`build_resident`, residents; also used by the town imports). The engine
side is unaffected: it draws whatever alias model a map names. Creatures (51 model specs) are not
part of this.

## How it happened

The first actor conversion produced one model per appearance because that is what the engine draws
(one Quake alias model per entity). The gallery and residents grew on that path; the model cache
(rc10) made repeated builds fast by reusing complete models, but every new appearance still
converts all of its parts. The baker's quota split (a part's triangle count depends on the whole
outfit) made a per-part cache look impossible.

## Why it was not caught

The duplication was measured earlier as catalogue counts (NPC_MODEL_CACHE.md "Next experiment:
component reuse") but never registered as a tracker item with a cost, so it stayed an experiment.
No build check compares conversion work with the number of distinct inputs.

## Reproduction

`tools/modular_npc_study.py census` on the owner's data: appearances, part uses, distinct parts
and source triangles; the gallery stage time is in any cold build's `build-profile.json`.

## Repair

Planned in stages (MODULAR_NPCS.md): a parts library and recipes on the host with the gallery
built from parts; residents from the same library; a composed-model loader in the engine (one
alias model per appearance, composed at load time); then per-actor equipment state. The
whole-appearance bake stays selectable as the reference. First step done: `bake` takes explicit
per-part quotas and a reference shell height (default path unchanged), and the study tool measures
the library and composes residents from parts.

## Verification

9 October 2026, host (Docker): parts baked with their outfit quotas at unit scale concatenate
to the whole model byte for byte (synthetic test). On the 13 NPCs of Balmora's exterior cells,
composition from parts gives 6,382 faces against 6,394 for the whole bake; 6 actors are
byte-identical, the others differ by the race scale applied after the part bake (at most 8 faces
and 0.14 units).
Nothing shipped yet.

## Prevention

`tests/test_modular_npc.py`: the explicit-quota path reproduces the default bake exactly, parts
baked once concatenate to the whole model, part keys separate slots, mirrored sides and skeletons.
When the parts library becomes the default, the gallery stage records distinct parts against
conversions, and a build that converts a part more than once per quota level fails.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Build speed (`build-speed`). Every stage on the shared worker pool; per-stage time and CPU in the build profile. See [families](README.md#families).

- [BUILD-CACHE-ABSOLUTE-PATHS-33](BUILD-CACHE-ABSOLUTE-PATHS-33.md): Stage fingerprints contain absolute paths, so a moved workspace or checkout reuses nothing
- [BUILD-CACHE-CHIM-UNITS-33](BUILD-CACHE-CHIM-UNITS-33.md): The chim stage's fingerprint changes whenever the CHIM unit cache gains units, so the stage is never reused
- [BUILD-CACHE-CLOSURE-WIDE-33](BUILD-CACHE-CLOSURE-WIDE-33.md): Stage fingerprints count every module any imported module could import, so unrelated edits rebuild most stages
- [BUILD-CACHE-NO-CUTOFF-33](BUILD-CACHE-NO-CUTOFF-33.md): A rebuilt stage whose outputs come out unchanged still rebuilds every stage after it
- [BUILD-CACHE-OVERBROAD-33](BUILD-CACHE-OVERBROAD-33.md): CHIM builds rerun the scene chain after merges that cannot change its outputs
- [BUILD-CACHE-TRACE-PYTHONPATH-33](BUILD-CACHE-TRACE-PYTHONPATH-33.md): The stage read trace refused reuse of a reused run when another checkout was on PYTHONPATH
- [BUILD-CHIM-UNIT-HULL-KEY-33](BUILD-CHIM-UNIT-HULL-KEY-33.md): CHIM unit cache ignores the standing-hull form: a --model-hull chain build reused routed-hull model units
- [BUILD-DOOR-REFERENCE-SERIAL-33](BUILD-DOOR-REFERENCE-SERIAL-33.md): The door step reads the whole master once per destination cell
- [BUILD-ENV-FINGERPRINT-GLOBAL-33](BUILD-ENV-FINGERPRINT-GLOBAL-33.md): The stair rule setting invalidates the reuse cache of every build stage, including stages that never read it
- [BUILD-EXCLUDE-STAGE-CLOSURE-33](BUILD-EXCLUDE-STAGE-CLOSURE-33.md): The quick test build table entered every conversion stage's fingerprint through the stage scheduler
- [BUILD-HAND-CATALOG-SERIAL-32](BUILD-HAND-CATALOG-SERIAL-32.md): The hand-catalog stage bakes every race and sex one after another
- [BUILD-IDLE-STAGES-33](BUILD-IDLE-STAGES-33.md): Scene-chain stages leave most of the workers they hold idle
- [BUILD-IMAGE-NOT-INCREMENTAL-33](BUILD-IMAGE-NOT-INCREMENTAL-33.md): The image step redoes every per-map pass and the whole pack on every build
- [BUILD-IMAGE-SERIAL-32](BUILD-IMAGE-SERIAL-32.md): The image step runs on one core for about 23 minutes per pass
- [BUILD-IMAGE-UNDERUSED-32](BUILD-IMAGE-UNDERUSED-32.md): Parts of the image step still run serially or leave most CPUs idle
- [BUILD-INPUTCHECK-SLOW-32](BUILD-INPUTCHECK-SLOW-32.md): The game data reference check takes over 12 minutes through Docker
- [BUILD-JOBS-RESOLVE-PER-STAGE-32](BUILD-JOBS-RESOLVE-PER-STAGE-32.md): With automatic jobs, stages of one build plan can get different worker counts
- [BUILD-MINIWIND-FINGERPRINT-ENGINE-33](BUILD-MINIWIND-FINGERPRINT-ENGINE-33.md): Every build stage's source fingerprint took in the engine sources through the MiniWind module
- [BUILD-NESTED-POOL-ALLOWANCE-33](BUILD-NESTED-POOL-ALLOWANCE-33.md): Pool workers open their own pools sized to the whole stage's allowance
- [BUILD-ORDERED-WINDOW-33](BUILD-ORDERED-WINDOW-33.md): The ordered worker pool idles behind one slow item, and hands long items out last
- [BUILD-PRERENDERED-PRUNE-ORDER-33](BUILD-PRERENDERED-PRUNE-ORDER-33.md): Prerendered store prune picks the superseded entry by folder name when two entries share a timestamp
- [BUILD-PROFILE-JOBS-START-ONLY-33](BUILD-PROFILE-JOBS-START-ONLY-33.md): The build profile compares a stage's cores with the workers it started with, not the ones it held
- [BUILD-REUSE-SCRATCH-UNDECLARED-33](BUILD-REUSE-SCRATCH-UNDECLARED-33.md): A rerun with --reuse-from reused 1 of 33 stages: the builder's scratch folder made the first stages non-reusable
- [BUILD-REUSE-TMP-UNDECLARED-33](BUILD-REUSE-TMP-UNDECLARED-33.md): A stage that runs while a reused stage is copied becomes non-reusable
- [BUILD-SCHEDULER-JOBSHARE-32](BUILD-SCHEDULER-JOBSHARE-32.md): The stage scheduler fixes a stage's worker share when it starts
- [BUILD-SCHEDULER-LOWBUDGET-33](BUILD-SCHEDULER-LOWBUDGET-33.md): With a small --jobs budget the stage scheduler starts nothing when more branches are ready than the budget (busy loop)
- [BUILD-STAGE-START-SHARE-33](BUILD-STAGE-START-SHARE-33.md): A pooled stage that starts while others run gets one worker as its start value
- [BUILD-SURVEY-NOT-REPRODUCIBLE-33](BUILD-SURVEY-NOT-REPRODUCIBLE-33.md): The world-survey stage writes its wall time into its outputs, so a rerun never has the same outputs
- [BUILD-WINDOWS-DOCKER-SLOW-31](BUILD-WINDOWS-DOCKER-SLOW-31.md): Docker builds and disk-image steps on Windows folders are slow
- [CHIM-LEGACY-CHAIN-33](CHIM-LEGACY-CHAIN-33.md): CHIM builds still run the legacy exterior chain: frame maps read the legacy region maps, and the open world is built
- [CHIM-PVS-SLOW-33](CHIM-PVS-SLOW-33.md): Seyda Neen's CHIM visibility rows take 5.5 minutes and are rebuilt whenever the worker count changes
- [CHIM-STAIRGATE-SLOW-33](CHIM-STAIRGATE-SLOW-33.md): The CHIM stair gate takes over 10 minutes on the Balmora and Vivec Arena world

Related bugs in other categories:

- [NPC-BAKE-VERTEX-32](NPC-BAKE-VERTEX-32.md): NPC model bake exceeds the alias vertex budget for two Telvanni residents
- [WORLD-REGION-DUPLICATION-31](WORLD-REGION-DUPLICATION-31.md): Every exterior object is stored about ten times (overlapping region maps)

<!-- END GENERATED CATEGORY -->
