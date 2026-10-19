# CHIM-NATIVE-IMAGE-NO-SHARED-SKY-36: CHIM-native images with no legacy exterior (MiniWinds of one town) ship without the shared sky their frame maps name

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 11 October 2026, in v0.0.36-dev4 |
| Where | Image step exterior sky pass: shared sky installed only with legacy exteriors |
| Reproduction | unknown |
| Duplicate of | no |
| Persists in | v0.0.36-dev4 (last seen) |
| Severity | medium: the shared sky is missing in every image whose exteriors are only CHIM frame maps; no check required it |
| Family | Content silently missing from a build (`build-content-missing`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | MiniWind v0.0.36-dev4 seyda-chim |
| From commit | source 3a8eaec, engine 3a8eaec, CHIM world 3a8eaec |
| CHIM engine version | CHIM 0.1.0, engine 3a8eaec, world format 0.7 |
| Build note | run 2026_10_11_v0.0.36-dev4_miniwind-seyda-chim-seyda-chim-native_3a8eaec; also Arena 61a1ea0, Balmora 1b5e0aa MiniWinds |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.42-dev1 (17 October 2026)._

## Status: 11 October 2026

Open. Repaired in source on v0.0.36-seyda-chim, with a test. Not shipped at the time of writing; verification on the
next MiniWind of a CHIM-native town.

## Symptom

The Seyda Neen MiniWind (run `2026_10_11_v0.0.36-dev4_miniwind-seyda-chim-seyda-chim-native_3a8eaec`) stopped at the
end of the image step: `Always-included assets missing from this image: gfx/aw_shared_sky.lmp (named by 13 maps)`.
The earlier MiniWind images of the Vivec Arena (stage A, 61a1ea0) and of Balmora (mesh methods, 1b5e0aa) have no
`gfx/aw_shared_sky.lmp` either, although their CHIM frame maps name it; they passed because nothing required it.

## Where

`tools/exterior_sky_build.py`, `configure_staged_maps`, called by the image step (`tools/build_aga.py`).

## How it happened

The exterior sky pass installs the shared sky from the staged legacy exterior maps (or a given source) and only when
the image stages at least one legacy exterior map. A CHIM-native town has none: its frame maps are written later in
the image step, with the shared sky keys in their worldspawn (`chim_town_rows`). An image whose only exteriors are
CHIM frame maps (every MiniWind of a CHIM-native town) therefore had no shared sky.

## Why it was not caught

Full builds always stage legacy open-world maps, so the sky was installed there. The always-included check runs only
in quick test builds, and it counted only legacy exteriors as exteriors.

## Reproduction

Build a MiniWind of a CHIM-native town and list `boot/id1/gfx/` of its image.

## Repair

`configure_staged_maps(..., frame_exterior=True)` when the build has a CHIM world: with no legacy exterior staged, the
shared sky is installed from the prepared shared source (or the staged one), and the pass stops if there is none. The
always-included check counts the CHIM frame maps as exteriors.

## Verification

`tests/test_exterior_sky_build.py` (a frame-only image gets the sky; without CHIM frames nothing changes; no source
stops). To do: the next Seyda Neen MiniWind image holds `gfx/aw_shared_sky.lmp`.

## Prevention

The always-included check now treats a build with a CHIM world as one with an exterior.

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
- [CHIM-TRACKER-APRON-40](CHIM-TRACKER-APRON-40.md): Tracker counts town apron dependencies as complete original cells
- [LAVA-NOT-IMPLEMENTED-33](LAVA-NOT-IMPLEMENTED-33.md): Lava is drawn as plain static meshes: no liquid surface, no damage, no view tint, never tracked
- [MINIWIND-PAYLOAD-NOT-SLIM-33](MINIWIND-PAYLOAD-NOT-SLIM-33.md): MiniWind #2 was built with the full movie and voice payload
- [NIGHT-WINDOWS-LOST-CHIM-36](NIGHT-WINDOWS-LOST-CHIM-36.md): Windows no longer glow at night: the night-windows table has been empty since the towns moved to CHIM
- [PLAYTEST-PAYLOAD-COVERAGE-32](PLAYTEST-PAYLOAD-COVERAGE-32.md): The v0.0.32-dev1 playtest has no first-person hands and no harvest
- [SEYDA-LANTERNS-MISSING-31](SEYDA-LANTERNS-MISSING-31.md): Seyda Neen lanterns light the night but are not in its maps
- [SKY-FLAT-PALETTE-DRIFT-41](SKY-FLAT-PALETTE-DRIFT-41.md): Exterior sky flat with no clouds: the sampled palette drifted and the shared cloud sky silently fell back to a one-colour placeholder
- TREE-SCALE-001 (no report page): Non-unit-scale tree sprites omitted; bounds too conservative

<!-- END GENERATED CATEGORY -->
