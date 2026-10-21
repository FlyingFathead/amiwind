# NIGHT-WINDOWS-LOST-CHIM-36: Windows no longer glow at night: the night-windows table has been empty since the towns moved to CHIM

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 17 October 2026, in v0.0.41 |
| Where | tools/night_lighting.py night_windows (legacy town maps only); CHIM frame maps get no rows |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.41 (last seen) |
| Severity | medium: Glowing window glass at night (shipped since v0.0.31) is gone in every exterior of v0.0.36 to v0.0.41; the build printed one warning line |
| Family | Content silently missing from a build (`build-content-missing`) |
| Playtest version | v0.0.41 release image 2026_10_16_v0.0.41_release_ce7ace6 |
| From commit | source ce7ace6, engine ce7ace6, CHIM world ce7ace6 |
| CHIM engine version | CHIM 0.2.1, engine ce7ace6, world format 0.5 |
| Platform or emulator | not in game (Measured on the shipped table world/night-windows.txt of each build on the build volume) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.42-dev1 (17 October 2026)._

## Symptom

At night the window glass of the towns no longer glows. Since v0.0.31 the engine lights the window-glass textures
listed in `world/night-windows.txt` (one line per map: the map name, then its glass textures; `aw_lamps.c`,
`aw_night_window_lights`). That table is empty in every image from v0.0.36 on:

| Build | Lines in `world/night-windows.txt` |
| --- | ---: |
| v0.0.35 release | 86 (Balmora, its region maps, Seyda Neen) |
| v0.0.36 release, every v0.0.36 to v0.0.38 MiniWind, v0.0.38, v0.0.41-dev5, v0.0.41 release | 0 |

The image log said only "[warning] Night windows: balmora scenery skipped (not supplied)."

## Where

`tools/night_lighting.py` `night_windows`: the table is classified from the legacy town maps and their scenery
sources only. Since v0.0.36 the towns are CHIM-native (`--chim-native-towns on`): their legacy town maps leave the
image, the scenery source of the old Balmora chain is no longer given, and the CHIM frame maps (`balmora-chim.chim`
and the others), which are what the engine loads, get no rows. The engine matches a row by the loaded map's name.

## How it happened

The move to CHIM-native towns replaced the maps the table was keyed by; the night lighting step was not extended to
the CHIM frames, and an empty table was accepted.

## Why it was not caught

The empty table was a warning line, not an error, and no check compared the table with the previous release.

## Reproduction

Any image from v0.0.36 on: `world/night-windows.txt` is empty; at night no window glows.

## Repair

Open. Needed: rows for the CHIM frame maps (the glass textures of the placed models each frame carries), from
the original game data as before (no new artwork). A builder rule that stops an image whose table is empty, unless
a test build allows it, is prepared for after v0.0.42-dev1 (with the other stand-in checks of
[SKY-FLAT-PALETTE-DRIFT-41](SKY-FLAT-PALETTE-DRIFT-41.md)).

## Verification

Pending: the table has rows for the CHIM frame maps and the windows glow at night in FS-UAE.

## Prevention

Planned: the image step refuses an empty table for a build that ships exteriors (above).

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Content silently missing from a build (`build-content-missing`). Every omission is receipted; payload and entity counts are compared with the last release; shipped features are on by default. See [families](README.md#families).

- [ARENA-PIT-NO-INTERIOR-33](ARENA-PIT-NO-INTERIOR-33.md): The Vivec Arena minigame fights on the test floor: the Arena Pit interior is not in v0.0.33 builds
- [AUDIO-MISSING-SOURCES-32](AUDIO-MISSING-SOURCES-32.md): The image step reports missing sources for 7 voices and 2 effects
- [BUILD-CHIM-ROOMS-IMAGE-RACE-36](BUILD-CHIM-ROOMS-IMAGE-RACE-36.md): The image step ran beside a CHIM town's room stage and read its record before it existed
- [BUILD-CHIM-SANDBOX-NO-SHARED-SKY-36](BUILD-CHIM-SANDBOX-NO-SHARED-SKY-36.md): An area build of a CHIM town without exterior BSP maps ships no shared sky although its CHIM frame names it
- [BUILD-DRESSING-EXCLUDED-32](BUILD-DRESSING-EXCLUDED-32.md): The repository builder drops lantern hooks and other dressing in Seyda Neen maps without a receipt
- [BUILD-EXTRA-TOWN-OPTIN-32](BUILD-EXTRA-TOWN-OPTIN-32.md): A default build leaves out the Vivec Arena preview that v0.0.32 ships
- [BUILD-FLORA-OPTIN-32](BUILD-FLORA-OPTIN-32.md): A from-scratch build without --tree-sprites leaves out the trees and grass every release ships
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
- [PLAYTEST-PAYLOAD-COVERAGE-32](PLAYTEST-PAYLOAD-COVERAGE-32.md): The v0.0.32-dev1 playtest has no first-person hands and no harvest
- [SEYDA-LANTERNS-MISSING-31](SEYDA-LANTERNS-MISSING-31.md): Seyda Neen lanterns light the night but are not in its maps
- [SKY-FLAT-PALETTE-DRIFT-41](SKY-FLAT-PALETTE-DRIFT-41.md): Exterior sky flat with no clouds: the sampled palette drifted and the shared cloud sky silently fell back to a one-colour placeholder
- TREE-SCALE-001 (no report page): Non-unit-scale tree sprites omitted; bounds too conservative

<!-- END GENERATED CATEGORY -->
