# BUILD-CHIM-SANDBOX-NO-SHARED-SKY-36: An area build of a CHIM town without exterior BSP maps ships no shared sky although its CHIM frame names it

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 11 October 2026, in v0.0.36-dev3 |
| Where | tools/exterior_sky_build.py configure_staged_maps |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.36-dev3 (last seen) |
| Severity | medium: the Vivec stage A image (try4) had no gfx/aw_shared_sky.lmp while its frame named it; a room in such a build stops the image step |
| Family | Content silently missing from a build (`build-content-missing`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source 300e8dd, engine 300e8dd, CHIM world 300e8dd |
| CHIM engine version | CHIM 0.1.0, engine 300e8dd, world format 0.5 |
| Build note | MiniWind vivec-arena-pit 2026_10_11_v0.0.36-dev4_miniwind-vivec-arena-pit-arena-pit-rooms_300e8dd stopped in the image step; try4 (61a1ea0) shipped without the sky |

<!-- END GENERATED FACTS -->

## Status: 11 October 2026

Fixed in source with a regression test; verified by the MiniWind build of the Vivec Arena Pit at the time of writing
pending.

## Symptom

The first MiniWind build of `vivec-arena-pit` stopped in the image step: "Always-included assets missing from this
image: gfx/aw_shared_sky.lmp (named by 1 maps, e.g. vai000)". The Vivec stage A image (try4, 61a1ea0) had passed without
the shared sky at all, although its CHIM frame map names it in its worldspawn.

## Where

`tools/exterior_sky_build.py` `configure_staged_maps`: the shared sky was installed only when the build has an exterior
Quake map (a region map, a town map, an open-world map). An area build of a CHIM town (the MiniWind of the Vivec Arena)
has none: its exterior is a CHIM frame map, which the sky pass does not list. So nothing installed the sky the image step
had prepared from the owner's own cloud artwork (`prepare_shared_sky_assets.prepare_staged_sky`), although the frame map
(`chim_town_rows`) and every classified room (the sky pass tags interiors too) name it.

## How it happened

The shared sky came from the exterior maps of every build until CHIM area sandboxes of towns other than Balmora: a
Balmora MiniWind still builds Balmora's scene stage, and full builds hold the open world.

## Why it was not caught

The always-included check skips the sky when the build has no exterior Quake map, and the stage A build had no room
that named it. No test covered a build whose only exterior is a CHIM frame.

## Reproduction

A MiniWind build of `vivec-arena-pit` (or any CHIM town other than Balmora with a room) on a commit before the fix.

## Repair

`configure_staged_maps` installs the prepared shared sky (the explicit or owned-cloud source) when no exterior Quake map
provides one; its receipt says so.

## Verification

`tests/test_exterior_sky_build.py` `test_prepared_sky_is_installed_without_exterior_maps`: with no exterior map and a
prepared sky, the sky is installed and the room names it; with neither, nothing is installed. Pending: the MiniWind build
of `vivec-arena-pit`.

## Prevention

The sky follows the maps that name it, not the kind of map that used to bring it.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Content silently missing from a build (`build-content-missing`). Every omission is receipted; payload and entity counts are compared with the last release; shipped features are on by default. See [families](README.md#families).

- [ARENA-PIT-NO-INTERIOR-33](ARENA-PIT-NO-INTERIOR-33.md): The Vivec Arena minigame fights on the test floor: the Arena Pit interior is not in v0.0.33 builds
- [AUDIO-MISSING-SOURCES-32](AUDIO-MISSING-SOURCES-32.md): The image step reports missing sources for 7 voices and 2 effects
- [BUILD-CHIM-ROOMS-IMAGE-RACE-36](BUILD-CHIM-ROOMS-IMAGE-RACE-36.md): The image step ran beside a CHIM town's room stage and read its record before it existed
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
- [LAVA-NOT-IMPLEMENTED-33](LAVA-NOT-IMPLEMENTED-33.md): Lava is drawn as plain static meshes: no liquid surface, no damage, no view tint, never tracked
- [MINIWIND-PAYLOAD-NOT-SLIM-33](MINIWIND-PAYLOAD-NOT-SLIM-33.md): MiniWind #2 was built with the full movie and voice payload
- [PLAYTEST-PAYLOAD-COVERAGE-32](PLAYTEST-PAYLOAD-COVERAGE-32.md): The v0.0.32-dev1 playtest has no first-person hands and no harvest
- [SEYDA-LANTERNS-MISSING-31](SEYDA-LANTERNS-MISSING-31.md): Seyda Neen lanterns light the night but are not in its maps
- TREE-SCALE-001 (no report page): Non-unit-scale tree sprites omitted; bounds too conservative

<!-- END GENERATED CATEGORY -->
