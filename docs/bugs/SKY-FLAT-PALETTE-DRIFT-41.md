# SKY-FLAT-PALETTE-DRIFT-41: Exterior sky flat with no clouds: the sampled palette drifted and the shared cloud sky silently fell back to a one-colour placeholder

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 17 October 2026, in v0.0.41 |
| Where | prepare_quake.py palette sample; prepare_shared_sky_assets.py fallback; exterior_sky_build.py |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.41 (last seen) |
| Severity | high: Every exterior of v0.0.40 and v0.0.41 has a flat grey-blue sky without clouds; the build printed only a warning |
| Family | Content silently missing from a build (`build-content-missing`) |
| Playtest version | v0.0.41 release image 2026_10_16_v0.0.41_release_ce7ace6 |
| From commit | source ce7ace6, engine ce7ace6, CHIM world ce7ace6 |
| CHIM engine version | CHIM 0.2.1, engine ce7ace6, world format 0.5 |
| Platform or emulator | FS-UAE 3.1.66, JIT, A1200 68040 preset |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.45 (20 October 2026)._

<!-- contents start -->
## Contents

- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Symptom

On 17 October 2026 the maintainer asked where the clouds and the sun had gone: the camera benchmark frames of the
v0.0.41 release image at the Balmora benchmark cameras show a flat grey-blue sky with no clouds.

Checked in FS-UAE (JIT preset, a fresh play copy of the v0.0.41 release image, Balmora camera bm1, clock stopped
and set, headlamp off) at 08:00, 12:00, 18:00 and 22:00, looking level, pitched up 30 degrees and towards the
sun's path:

- No clouds at any hour: the whole sky above the horizon is one colour (palette index 224 under the day/night
  colour tables), at every pitch.
- The sun is there: at 08:00 looking east, 20 degrees up, the sun disc and its halo show. At noon it is near
  the zenith (about 76 degrees up by the engine's orbit), outside a level or 30-degree view, so a noon frame
  never shows it.
- The day/night colours work: grey-blue by day, brown at 18:00, near black at 22:00.

The engine's settings were the defaults: `aw_sky_type 3`, `aw_clouds 1`, `aw_cloud_type` classic,
`aw_day_clouds 100`, `aw_sun 1`, `aw_daynight 1`, `aw_skyline_fill 0`. The night sky loaded ("Owned night sky:
27648 bitmap bytes").

## Where

- `tools/prepare_quake.py` (the `scene` stage): the scene palette is sampled from the textures of the Seyda Neen
  scenery stage.
- `tools/prepare_shared_sky_assets.py` `prepare_staged_sky`: the owned cloud sky and its palette bank are only
  prepared for one approved palette (`sky_palette_overlay.approved`, a SHA-256 fingerprint); any other palette
  gives a `fallback_warning`.
- `tools/exterior_sky_build.py` `configure_staged_maps`: with no prepared sky it installs the converted maps'
  own reserved sky texture, a 256 x 128 placeholder of index 224 in both layers.

## How it happened

Commit 01bdf9f (15 October 2026, v0.0.40-dev2 line, "Align town ownership to original cells") widened the Seyda
Neen scenery scope to cover the cell-aligned town (`town_grid.scenery_radius`: radius 11,500 to 29,772, and the
larger area rectangle in `config/seyda_area.json`). The scenery stage then held 183 textures instead of 107. The
scene palette is a 224-colour quantisation of those textures, so it changed (221 of 256 colours). The changed
palette no longer matched the approved fingerprint, the shared sky preparation fell back with "Unsupported
original palette fingerprint; no reservation/reindex performed", and the image shipped the placeholder.

Measured on the build volume: every build up to v0.0.38 (13 October, c2c2050) has the cloud sky (SHA-256
92a874a1...) with status `prepared_owned_clouds`; the v0.0.41-dev5 regional build and the v0.0.41 release image
have the one-colour sky (30f78f90...), status `fallback_warning`, no `gfx/sky-palette-bank.json`. v0.0.40 contains
01bdf9f and is affected the same way (its image is no longer on the build volume).

## Why it was not caught

- The fallback was a warning line in the image log, not an error, although every real build has the maintainer's data
  files: nothing can legitimately fall back there.
- The palette is derived data: nothing tied it to the scenery scope, so a scope change for another reason (town
  ownership) moved every colour without any check noticing.
- The always-included check tests only that `gfx/aw_shared_sky.lmp` exists, not that it has clouds; the frame
  checks and benchmarks ran with the flat sky as their baseline.

## Reproduction

Any build from 01bdf9f on: the image log has "Shared sky vivid/cloud preparation unavailable: Unsupported
original palette fingerprint", and `image/sky-asset-preparation/fallback-warning.json` exists. In game every
exterior sky is flat.

## Repair

- `prepare_shared_sky_assets.prepare_staged_sky` converts the owned cloud sky for whatever palette the build has:
  a palette the sky colour bank was not made for gets the clouds by nearest colour against that palette
  (`prepared_owned_clouds_palette_matched`). No bank is reserved, so no other staged file changes: no texture or
  map is converted again. The bank method stays for the palette it was made for. Without the bank the twilight
  tones come from the nearest palette colours. Checked on the real v0.0.41 palette (SHA-256 e7ce2a84...): the
  converted sky (18debc84...) alone, put into the v0.0.41 release image, shows clouds at noon and red and gold
  clouds at dusk in FS-UAE; the maintainer judged the noon and dusk frames ("it looks good now").
- `build_aga` image step: a `fallback_warning` from the shared sky preparation with owned data files stops the
  build, naming the reason and the staged palette's SHA-256, instead of shipping a flat sky.
- Tests: `tests/test_prepare_shared_sky_assets.py` (another palette gets palette-matched clouds and nothing else
  changes), `tests/test_prepare_quake_palette.py` (the image step refuses the fallback).
- Tried first and taken out again: sampling the palette from the old Seyda Neen texture set (4b20d7c). It brought
  back the old texture sample, but the palette sample also holds the Seyda Neen ground textures, which the larger
  area changed as well: a MiniWind built with it got a third palette (1654dedf...), still not the one the bank
  was made for, and stopped in the image step on the refusal above. It would also have converted every texture
  again. The palette stays the v0.0.41 one.

## Verification

Pending: the dev1 build (image log "sky assets" with `prepared_owned_clouds_palette_matched`) and the same
FS-UAE frames with clouds.

## Prevention

- The image step refuses the fallback (above).
- Every stand-in asset, not only the sky, goes through one rule (`tools/placeholder_policy.py`): a stand-in
  shared sky, night sky, night-windows table, interface font, startup-screen font or intro video stops the image
  step, naming the unit, each input with its SHA-256 and the reason, instead of a warning line. A test build can
  let a named one through with `--allow-placeholder NAME` (refused for release candidates and finals, recorded in
  the image receipt as `placeholders_allowed`). A stand-in that every build ships today because of an open bug
  (the empty night-windows table, [NIGHT-WINDOWS-LOST-CHIM-36](NIGHT-WINDOWS-LOST-CHIM-36.md)) is printed and
  recorded with that bug instead of stopping the build; once the bug is fixed it stops the build again.
- The earlier proposal (check the palette right after the `census` stage) is no longer needed: since the
  palette-matched method every palette gets the cloud sky, so there is nothing left to catch early.

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
- [LAVA-NOT-IMPLEMENTED-33](LAVA-NOT-IMPLEMENTED-33.md): Lava is drawn as plain static meshes: no liquid surface, no damage, no view tint, never tracked
- [MINIWIND-PAYLOAD-NOT-SLIM-33](MINIWIND-PAYLOAD-NOT-SLIM-33.md): MiniWind #2 was built with the full movie and voice payload
- [NIGHT-WINDOWS-LOST-CHIM-36](NIGHT-WINDOWS-LOST-CHIM-36.md): Windows no longer glow at night: the night-windows table has been empty since the towns moved to CHIM
- [PLAYTEST-PAYLOAD-COVERAGE-32](PLAYTEST-PAYLOAD-COVERAGE-32.md): The v0.0.32-dev1 playtest has no first-person hands and no harvest
- [SEYDA-LANTERNS-MISSING-31](SEYDA-LANTERNS-MISSING-31.md): Seyda Neen lanterns light the night but are not in its maps
- TREE-SCALE-001 (no report page): Non-unit-scale tree sprites omitted; bounds too conservative

Related bugs in other categories:

- [BUILD-INVENTORY-PALETTE-41](BUILD-INVENTORY-PALETTE-41.md): Inventory icons and metadata stop the sky palette image pass
- [SKY-STAR-TWINKLE-LATE-42](SKY-STAR-TWINKLE-LATE-42.md): Star twinkle seen only late at night: before the midnight clearing the night clouds hide the few twinkling stars

<!-- END GENERATED CATEGORY -->
