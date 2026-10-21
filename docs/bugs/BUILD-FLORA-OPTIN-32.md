# BUILD-FLORA-OPTIN-32: a from-scratch build without --tree-sprites leaves out the trees and grass every release ships

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 8 October 2026, in v0.0.32-dev1 |
| Where | tools/build.py, world flora stages |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.32 |
| Severity | high: A default build left out the trees and grass every release ships; the image step failed late. |
| Family | Content silently missing from a build (`build-content-missing`) |
| Playtest version | v0.0.32-dev1 |
| From commit | source and engine 978475d |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.42-dev1 (17 October 2026)._

## Status: 8 October 2026

Fixed in source on v0.0.32-dev (not shipped at the time of writing; a from-scratch build with the default options
is still to confirm it). Found by the from-scratch v0.0.32-dev1 build: its image step stopped
after 23 minutes.

## Symptom

The image step stops with "Missing/unsafe sprite asset: progs/aw_flora/f_18299fefe9e2791c.spr".
The Seyda Neen maps reused under the recorded exception (BUILD-SEYDA-REGEN-30) reference flora
sprites, and v0.0.31 ships 76 of them, but a build without `--tree-sprites` never makes them.

## Where

`tools/build.py`: world flora (`world-flora-assets`, `world-flora`) is opt-in through
`--tree-sprites`; the from-scratch recipe used for dev1 did not pass it.

## How it happened

Trees and grass arrived in v0.0.28 as an opt-in builder option and stayed opt-in although every
release since ships them. Release images were built by patching earlier images, so the recipe
never had to carry the option (BUILD-NOT-FROM-SCRATCH-32).

## Why it was not caught

No from-scratch build ran between v0.0.28 and v0.0.32, and nothing records which builder options
a release needs; the missing sprites show only at the very end of the image step.

## Reproduction

From-scratch build at 5aacdc0 without `--tree-sprites`, with the recorded Seyda exception.

## Repair

- World flora is built by default in every real AGA build (`tools/build.py`,
  `world_flora_status`): the `world-flora-assets` and `world-flora` stages run and the image gets
  `--world-flora`, `--town-flora-source-index` and `--town-flora-scene-report`, the same pattern as
  the NPC gallery. `--no-tree-sprites` leaves flora out for debugging only and prints a warning;
  `--tree-sprites` is still accepted and has no effect; giving both is an error. Asset-free
  `--dry-run`, `--stage terrain` and the rc3 image recovery make no flora, as before.
- The measured Balmora layout repair (`--balmora-cache`, since v0.0.27) had been passed only
  together with `--tree-sprites`, so a build without it also skipped that repair. It is now passed
  in every AGA image build, with or without flora.
- `build-state.json` records `world_flora` (`requested`, `status`, `policy_sha256`), and the build
  summary footer and `build-summary.json` name the flora selection next to the NPC gallery
  selection.
- The image step's sprite check (`tools/sprite_heap.py`) now says "World flora was not built"
  when maps place `progs/aw_flora/*.spr` sprites that are missing, with the count, the first
  names and the cause (`--no-tree-sprites`, or a hand-run image step without `--world-flora`),
  instead of only "Missing/unsafe sprite asset".

## Verification

- `tests/test_build_defaults.py`: the default command list has every stage the release payload
  needs, including both flora stages; the image gets every shipped input (flora, Balmora cache,
  gallery, 3D hands, hidden-surface cull, shared sky, canonical land, night table sources) with
  the shipped values; `--tree-sprites` gives the same command list as the default;
  `--no-tree-sprites` removes only the flora stages and inputs; every `--no-*` option is
  "DEBUGGING ONLY"; every builder option is classified against what a release ships (a new
  option fails until classified); dry-run and terrain recipes stay flora-free; the receipt and
  summary record flora; the missing-flora message names the cause. Turning flora or the
  Balmora cache back into an opt-in fails these tests (checked by editing the builder in a
  scratch copy).
- Updated: `tests/test_world_flora_integration.py`, `tests/test_builder_stage_entries.py`
  (every stage parses the default and `--no-tree-sprites` command lines) and
  `tests/test_build_setup.py` (its receipt fixture now carries the flora policy).
- Full suite in Docker: 1,435 tests pass; the 3 skips are the Windows-only tests.
- Pending: a from-scratch default build (no flora option) compared file by file with the
  release payload.

## Prevention

The from-scratch check compares the payload with the last release file by file; a builder
config file states the release's options instead of a remembered command line.
`tests/test_build_defaults.py` fails when a shipped feature leaves the default build or a new
builder option is not classified against the release.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Content silently missing from a build (`build-content-missing`). Every omission is receipted; payload and entity counts are compared with the last release; shipped features are on by default. See [families](README.md#families).

- [ARENA-PIT-NO-INTERIOR-33](ARENA-PIT-NO-INTERIOR-33.md): The Vivec Arena minigame fights on the test floor: the Arena Pit interior is not in v0.0.33 builds
- [AUDIO-MISSING-SOURCES-32](AUDIO-MISSING-SOURCES-32.md): The image step reports missing sources for 7 voices and 2 effects
- [BUILD-CHIM-ROOMS-IMAGE-RACE-36](BUILD-CHIM-ROOMS-IMAGE-RACE-36.md): The image step ran beside a CHIM town's room stage and read its record before it existed
- [BUILD-CHIM-SANDBOX-NO-SHARED-SKY-36](BUILD-CHIM-SANDBOX-NO-SHARED-SKY-36.md): An area build of a CHIM town without exterior BSP maps ships no shared sky although its CHIM frame names it
- [BUILD-DRESSING-EXCLUDED-32](BUILD-DRESSING-EXCLUDED-32.md): The repository builder drops lantern hooks and other dressing in Seyda Neen maps without a receipt
- [BUILD-EXTRA-TOWN-OPTIN-32](BUILD-EXTRA-TOWN-OPTIN-32.md): A default build leaves out the Vivec Arena preview that v0.0.32 ships
- [BUILD-HANDS-NOT-BUILT-32](BUILD-HANDS-NOT-BUILT-32.md): Per-race first-person hands are not built by the builder
- [BUILD-HARVEST-NATIVE-TOWN-ORDER-36](BUILD-HARVEST-NATIVE-TOWN-ORDER-36.md): The image step's harvest check refused a CHIM-native town's catalogues before its frame map was written
- [BUILD-HARVEST-NOT-BUILT-32](BUILD-HARVEST-NOT-BUILT-32.md): Mushroom harvest data is not built by the builder
- [BUILD-IMAGE-NATIVE-BALMORA-CACHE-36](BUILD-IMAGE-NATIVE-BALMORA-CACHE-36.md): The image step asked for the legacy Balmora cache when Balmora is CHIM-native
- [BUILD-LAVA-COVERAGE-38](BUILD-LAVA-COVERAGE-38.md): Full dev2 world omits the reported lava cells
- [BUILD-LEGACY-TOWN-MAPS-SHIPPED-36](BUILD-LEGACY-TOWN-MAPS-SHIPPED-36.md): CHIM-native Seyda Neen is still built through the legacy chain: 65 sn maps are built and removed before packing (build time, not payload)
- [BUILD-MINIWIND-ARENA-PIT-REFUSED-36](BUILD-MINIWIND-ARENA-PIT-REFUSED-36.md): Regression against v0.0.35: the Vivec Arena Pit is in no CHIM build (no CHIM-native stage made the Arena's rooms), and its start was refused as not converted
- [BUILD-MINIWIND-BALMORA-ASSUMED-36](BUILD-MINIWIND-BALMORA-ASSUMED-36.md): A MiniWind image of another town fails its content fingerprint: the Balmora region table was always required
- [BUILD-MINIWIND-DIRECT-START-TOWN-36](BUILD-MINIWIND-DIRECT-START-TOWN-36.md): A MiniWind build of another town refuses its own direct start: the start check assumed Balmora
- [BUILD-NIGHT-TABLES-31](BUILD-NIGHT-TABLES-31.md): Repository image builds have no night lamp, glowing glass or location fog tables
- [BUILD-RUN-FOLDER-PRECREATED-36](BUILD-RUN-FOLDER-PRECREATED-36.md): Every real CHIM build is refused at its start: the plan writes the world map manifest into the run folder before the run makes it
- [BUILD-STANDALONE-STAGES-32](BUILD-STANDALONE-STAGES-32.md): Door overlay and interior section tools are outside the builder; their use in v0.0.31 is unverified
- [CHIM-CELL-FEATURE-LIST-INCOMPLETE-38](CHIM-CELL-FEATURE-LIST-INCOMPLETE-38.md): Cell feature list incomplete: original placements and gameplay support are not reconciled with packaged coverage
- [CHIM-COAST-OBJECTS-MISSING-36](CHIM-COAST-OBJECTS-MISSING-36.md): Objects including Dwemer ruins are reported missing from the CHIM coast
- [CHIM-LAVA-TERRAIN-SPIKES-38](CHIM-LAVA-TERRAIN-SPIKES-38.md): Angular terrain wedges cross a lava pool in the final-image inspection
- [CHIM-NATIVE-IMAGE-NO-SHARED-SKY-36](CHIM-NATIVE-IMAGE-NO-SHARED-SKY-36.md): CHIM-native images with no legacy exterior (MiniWinds of one town) ship without the shared sky their frame maps name
- [CHIM-TRACKER-APRON-40](CHIM-TRACKER-APRON-40.md): Tracker counts town apron dependencies as complete original cells
- [INTERIOR-PLACED-ITEMS-47](INTERIOR-PLACED-ITEMS-47.md): Placed items, ingredients included, are left out of converted interiors
- [LAVA-NOT-IMPLEMENTED-33](LAVA-NOT-IMPLEMENTED-33.md): Lava is drawn as plain static meshes: no liquid surface, no damage, no view tint, never tracked
- [MINIWIND-PAYLOAD-NOT-SLIM-33](MINIWIND-PAYLOAD-NOT-SLIM-33.md): MiniWind #2 was built with the full movie and voice payload
- [NIGHT-WINDOWS-LOST-CHIM-36](NIGHT-WINDOWS-LOST-CHIM-36.md): Windows no longer glow at night: the night-windows table has been empty since the towns moved to CHIM
- [PLAYTEST-PAYLOAD-COVERAGE-32](PLAYTEST-PAYLOAD-COVERAGE-32.md): The v0.0.32-dev1 playtest has no first-person hands and no harvest
- [SEYDA-LANTERNS-MISSING-31](SEYDA-LANTERNS-MISSING-31.md): Seyda Neen lanterns light the night but are not in its maps
- [SKY-FLAT-PALETTE-DRIFT-41](SKY-FLAT-PALETTE-DRIFT-41.md): Exterior sky flat with no clouds: the sampled palette drifted and the shared cloud sky silently fell back to a one-colour placeholder
- TREE-SCALE-001 (no report page): Non-unit-scale tree sprites omitted; bounds too conservative

Related bugs in other categories:

- [BUILD-ACTOR-CONTACT-CALL-32](BUILD-ACTOR-CONTACT-CALL-32.md): Builder actor-contact stage calls convert() with the wrong arguments since v0.0.27
- [BUILD-NOT-FROM-SCRATCH-32](BUILD-NOT-FROM-SCRATCH-32.md): Five releases shipped without the public builder being able to build them from scratch
- [BUILD-XDFTOOL-ARGMAX-32](BUILD-XDFTOOL-ARGMAX-32.md): The image step fails at the end: xdftool argument list too long

<!-- END GENERATED CATEGORY -->
