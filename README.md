<p align="center">
  <img src="resources/media/AmiWind_logo.png" width="900" alt="AmiWind: an open-source RPG engine for the Commodore Amiga">
</p>

# AmiWind

An unofficial, experimental RPG engine and enthusiast project bringing Morrowind
to the Commodore Amiga, featuring CHIM: an AmiQuake-based engine and an asset
conversion pipeline that builds the game from your own legally obtained copy of
Morrowind, and, in time, a base for your own Amiga RPG adventures.

Like community projects such as
[OpenMW](https://openmw.org), [MGE XE](https://github.com/Hrnchamd/MGE-XE) and
[MWSE](https://github.com/MWSE/MWSE), AmiWind ships with no game data or proprietary assets.

*Not affiliated with or endorsed by Bethesda Softworks or ZeniMax. Please support the original creators: buy Morrowind.*

AmiWind is a standalone extension of the GPL-licensed
[AmiQuake](https://github.com/terriblefire/amiquake) engine. It also converts
your own Morrowind installation into data for an experimental native Amiga
runtime. The [FAQ](docs/FAQ.md) covers the project's aims, the hardware it
needs and what it can do today. [Licensing and credits](docs/LICENSING_AND_CREDITS.md)
explains where the source comes from and what the public package contains.
The [gallery](docs/GALLERY.md) has in-game screenshots of every version, and
[Running AmiWind on real hardware](docs/REAL_HARDWARE.md) is for owners of a real Amiga.

<p align="center">
  <img src="docs/images/amiwind-v0.0.32-gallery.gif" width="800" alt="AmiWind v0.0.32 in Vivec: ten in-game screenshots in turn">
</p>

<p align="center">Not painted backdrops: every frame is rendered in real time by the engine.</p>

More in the [gallery](docs/GALLERY.md).

## v0.0.44: By Azura's Trees!

A patch release for v0.0.43. Its fix for the floating tree crowns on Azura's Coast made the Bitter Coast trees too
heavy for memory; they are 16 to 42 % lighter now, and every trunk keeps at least 90 % of its height. The player
body is built again for every race, and the roadmap describes the road after v0.0.44.

What went wrong while building v0.0.44, and how it was fixed:

- **Bitter Coast trees too heavy.** v0.0.43's fix for the floating tree crowns made the Bitter Coast trees about
  60 % larger; two Bitter Coast areas no longer fit in memory and the image could not be built. The trunk shape
  guard now tries lighter copies first: the trees are 16 to 42 % smaller and every trunk keeps at least 90 % of
  its height ([CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43](docs/bugs/CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43.md)).
- **Player bodies and guard torches could not be built.** The new NPC head reducer, which keeps every head's
  outline, left no fitting model for some player bodies and guard torch models. They fall back to the previous
  reducer, and a rebuilt guard model within one rounding step of the original is accepted
  ([NPC-HEAD-DECIMATION-33](docs/bugs/NPC-HEAD-DECIMATION-33.md)).
- **Interior plant sprites missing outside Vivec.** The plant sprites of converted interiors were installed only
  for the Vivec rooms; every room type installs them now
  ([INTERIOR-MORAG-TONG-FPS-43](docs/bugs/INTERIOR-MORAG-TONG-FPS-43.md)).

Running on CHIM Engine v0.2.1. See the [release notes](docs/RELEASE-v0.0.44.md) for what changed and what is
known in this build.

## v0.0.43: Let There Be CHIM: Vvardenfell's Outdoors, All of It

Every exterior cell of Vvardenfell is on CHIM now: no classic region maps are left outdoors. The region list holds
1,348 cells (1,132 land, 197 sea floor and 19 open sea), and 46 more are inside the town frames. The last cells
joined after the stair walk learned to replace collision that blocked visible steps, so Ald-ruhn, Maar Gan and
Suran are on CHIM too. The release also brings the fixes from the maintainer's playtest: Red Mountain's summit
without a solid sky, invisible editor markers, Azura's Coast plants on their trunks, interior plants as sprites and
NPC heads that keep their outline, the sea to the horizon at Vivec, and a builder that keeps its cores busy.

Running on CHIM Engine v0.2.1. See the [release notes](docs/RELEASE-v0.0.43.md) for what changed and what is
known in this build, and the [CHIM Progress Tracker](docs/chim/PROGRESS_TRACKER.md) for every cell.

<p align="center">
  <img src="docs/images/amiwind-v0.0.43-dev2-ghostgate.png" width="800" alt="Ghostgate in the fog seen from the valley below, in v0.0.43-dev2">
</p>

More in the [gallery](docs/GALLERY.md).

## v0.0.42: Things Are Starting To Look Pretty Khuul

More of the island on CHIM, the clouds back in the sky, and the first look of the original interface. 1,168 of
Vvardenfell's 1,395 exterior cells are on CHIM now (776 before), from Molag Mar and Pelagiad to Gnisis, Ghostgate
and the lava fields. The clouds are back after two releases with a flat sky, buildings no longer pop in and out
where memory runs full, and the game uses extra Fast RAM by itself. The HUD and the inventory start to take their
original shape: the original weapon and magic boxes, item icons from the game's own art, and the character as a
still picture in the original pose.

Running on CHIM Engine v0.2.1. See the [release notes](docs/RELEASE-v0.0.42.md) for what changed and what is
known in this build, and the [CHIM Progress Tracker](docs/chim/PROGRESS_TRACKER.md) for every cell.

| | |
| --- | --- |
| ![The Khuul docks, a ship at the pier, in v0.0.42-dev1](docs/images/amiwind-v0.0.42-dev1-khuul-2.png) | ![The Ebonheart bridge between two towers at dusk in v0.0.42-dev1](docs/images/amiwind-v0.0.42-dev1-ebonheart-dusk.png) |
| **The Khuul docks**, a ship at the pier. | **Ebonheart at dusk**, lanterns on the bridge. |
| ![A sunset tree near Khuul in v0.0.42-dev1](docs/images/amiwind-v0.0.42-dev1-khuul-3.png) | ![The sun beside a tower in v0.0.42-dev1](docs/images/amiwind-v0.0.42-dev1-sunset-tower.png) |
| **A tree against the sunset** near Khuul. | **The sun beside a tower.** |
| ![A dawn valley with dead trees in v0.0.42-dev1](docs/images/amiwind-v0.0.42-dev1-dawn-valley.png) | ![The same sunset under a clear blue sky in v0.0.42-dev1](docs/images/amiwind-v0.0.42-dev1-sunset-blue.png) |
| **A dawn valley.** | **A sunset under a clear sky.** |

More in the [gallery](docs/GALLERY.md#v0042-things-are-starting-to-look-pretty-khuul).

## v0.0.41: More Fixes, Fewer Planes (A Telvanni Root Story)

The first regional CHIM release. Rings 0 to 4 of Vvardenfell are on CHIM, and so are two whole Morrowind
regions, the Bitter Coast and Azura's Coast, with Seyda Neen, Balmora, the whole city of Vivec, Hla Oad,
Sadrith Mora and Vos: 723 cells, each converted from your own copy of Morrowind. The collision behind large
irregular meshes (Telvanni roots and towers, Daedric and Dwemer ruins) now compiles into compact hulls instead
of chains of thousands of planes, which is what lets the Telvanni towns fit the memory budget.

Running on CHIM Engine v0.2.1. See the [release notes](docs/RELEASE-v0.0.41.md) for what changed and what is
known in this build, and the [CHIM Progress Tracker](docs/chim/PROGRESS_TRACKER.md) for every cell.

<!-- v0.0.41 gallery: photo-mode captures from the release build go here -->

## v0.0.40: Rings 0, 1 and 2 of Vvardenfell in Full CHIM

The final release targets CHIM rings 0, 1 and 2 around Vvardenfell. Other
exterior areas keep their existing legacy representation, apart from named CHIM
towns; interiors remain separate. Complete candidate, native and package checks
are still required.

Running on CHIM Engine v0.2.0. The current candidate adds inventory layout and
preview corrections, original opening HUD activation, and an offline fix for
limb deformation during animation conversion. Rebuilt models pass serialized checks; package checks remain pending.
Original-spacing terrain diagonals and two local detail repairs are integrated
with source edge checks and a passing complete automated suite (explicit skips
and expected failures). Compiled/native seams and actor contact remain open. Combat, swimming, gait and appearance reports remain open.
See the [release preparation notes](docs/RELEASE-v0.0.40.md) and
[bug register](docs/BUGS.md#fix-index) for the exact scope and remaining gates.

### Along the coast: ring 2

| Grytewake, cell (-7,-6) | Shunned Shipwreck, cell (-10,1) |
| --- | --- |
| ![Grytewake ship exterior rendered by AmiWind v0.0.40-dev1 in ring 2](docs/images/amiwind-v0.0.40-dev1-grytewake.png) | ![Shunned Shipwreck exterior rendered by AmiWind v0.0.40-dev1 in ring 2](docs/images/amiwind-v0.0.40-dev1-shunned-shipwreck.png) |

Actual AmiWind **v0.0.40-dev1** captures, taken on 15 October 2026. These are
ship exteriors with cabin entrances in ring 2. Photo mode hides the HUD and
uses a free camera; the images preserve the rendered viewport pixels and
normal fog. They show the existing playtest, while the final release checks
above remain pending. Public gameplay screenshots show AmiWind itself.

## v0.0.39 - Cell By Cell, Piece By Piece

Running on CHIM Engine v0.2.0. This release brings together the RC1 changes
and RC2 repairs: safer teleport autosaves, an untinted death menu, third-person
ready/jump/punch and torch poses, swimming and diving, fuller movement pose
sampling, body budget checks, NPC animation registration and guard spear poses.
It also includes current keyboard help, sound cancellation and exterior
ownership checks that exclude redundant BSP conversion and packaging.

The RC2 source passed 4,043 automated tests (four skips and three expected
failures), Amiga compilation, full disk readback and package extraction. Scoped
emulator checks observed punch motion, a carried torch, stable water idle,
pitch-directed diving and visible first-person fists. These are RC2 observations;
they do not establish every appearance, physical LMB hit/damage, leg seams or
fast-gait quality. Memory/streaming warnings and broader gameplay gaps remain open.

CHIM content is unchanged from the inspected RC2: 360 whole regional cells,
with six partial town overlaps excluded from that count. Conversion and audit
progress are separate from packaged or fully playable coverage.

See the [release notes](docs/RELEASE-v0.0.39.md),
[changelog](docs/CHANGELOG.md) and [bug register](docs/BUGS.md#fix-index).
Unfinished work and new features continue in
[v0.0.40](docs/ROADMAP.md#v0040---unfinished-work-and-new-features).

<!-- v0.0.38 preview -->
## Previous public source release: v0.0.38 - Lava Is All You Need (And A Hint Of Tel Uvirith)

See the [v0.0.38 release notes](docs/RELEASE-v0.0.38.md) for changes and remaining verification limits.

Published v0.0.38 brings lava conversion repairs, new CHIM exterior areas,
reduced Tel Uvirith geometry, collision fixes and updated Toolkit inspection
controls. Scoped native checks verified lava contact damage and Tel Uvirith
arrival. Known issues remain in the [bug tracker](docs/BUGS.md); the
candidate source update above continues the repair and coverage work.

![Tel Uvirith lantern and arched walkway in the v0.0.38 development playtest](docs/images/amiwind-v0.0.38-molag-lantern-arch.png)

![Tel Uvirith elevated walkways in the v0.0.38 development playtest](docs/images/amiwind-v0.0.38-molag-walkways.png)

In-game development playtest screenshots, cropped to the rendered viewport.
The stronghold is Tel Uvirith, exterior cell (10,1), in Molag Amur.
Uvirith's Grave is the site on which the stronghold is built, not its alternative name.
This playtest uses the completed stronghold state (internal stage 6);
quest-driven construction transitions are not implemented. Earlier diagnostic
filenames used "Molag"; these screenshots do not show Molag Mar or its temple.

These views show the reduced Tel Uvirith scene; they do not establish full-world
or staircase traversal acceptance. See the [current CHIM cell tracker](docs/chim/CELL_TRACKER.md)
for conversion and audit progress; release plans remain separate from packaged coverage.
![Lava pool shoreline in the v0.0.38 full image](docs/images/amiwind-v0.0.38-lava-pool-clean.png)

![Lava below the surrounding terrain in the v0.0.38 full image](docs/images/amiwind-v0.0.38-lava-east-clean.png)

Original in-game captures with photo mode enabled and HUD/crosshair disabled.
A separate normal-movement test verified lava damage with god mode and noclip off.
These views do not establish sound or complete world-traversal acceptance.
<!-- /v0.0.38 preview -->

**v0.0.37 - Proofreading the Cantons:** a small fix release: the v0.0.36 release notes and this page now match the released code, and the logo images are fixed. Release notes: [docs/RELEASE-v0.0.37.md](docs/RELEASE-v0.0.37.md).

**v0.0.36, running on CHIM Engine v0.2.0:** introduced CHIM coverage along the coastline and the next ring inland, all of Vivec is one CHIM map with 130 of its rooms, Seyda Neen and Balmora are CHIM-native, terrain is stored once, and the engine gets wider coordinates, third person, blocking and a death scene. Release notes: [docs/RELEASE-v0.0.36.md](docs/RELEASE-v0.0.36.md).

### CHIM progress map

![CHIM conversion and audit snapshot: 1,275 of 1,292 Vvardenfell land and empty-sea cells reached an audit milestone; this is not packaged coverage](docs/images/amiwind-v0.0.40-rings-progress-map.png)

Snapshot: **15 October 2026, 10:50 UTC**, from the
[public cell reference](docs/chim/cell-progress-reference.json). Each square is
one exterior cell, north up. **Green** means a conversion/audit milestone;
lighting, actors and gameplay can still be deferred. **Red** means an audit
failure or an unfinished conversion. **Violet** is a hull-policy hold, **dark
grey** is not started, and **silver** is open ocean. This snapshot has no gold
release-plan overlay.

| Evidence | Recorded coverage |
| --- | --- |
| Converted cells | 1,191, including 15 with failed audits; 99 empty-sea cells are counted separately |
| Conversion/audit milestone | 1,275 of 1,292 land and empty-sea cells (98.7%); 15 failed and 2 not converted |
| Native-checked cells | No complete island-wide count established; scene checks remain scoped |
| Packaged region cells | 360 whole cells in the exact RC2 package, verified 14 October; six partial town overlaps remain outside this count |

The earlier combined v0.0.40 candidate passed conversion and structural, heap,
zone-walk and stair checks for all 369 frames. Subsequent boundary repairs now
produce zero full-static support-status disagreements across 2,816 samples
(5,632 queries) at southern Seyda; terrain and water controls agree. The corrected
Seyda frame passes structural, heap and zone-walk checks, but its full stair run
ended in memory exhaustion. The later combined attempt failed ownership before
packing because original kelp references were omitted by a legacy dressing filter.
A correction retains the three known original kelp meshes and passes 43 focused
source checks; its compiled, native and package gates remain pending. Other
541 original boundary segments remain unmeasured. Work continues on v0.0.40. See the
[static seam report](docs/bugs/CHIM-FRAME-STATIC-SEAM-40.md) and
[tracker guide](docs/chim/PROGRESS_TRACKER.md#current-mapping-evidence-15-october-2026).

The 865 open-ocean cells are outside the 1,292-cell denominator. Packaged
region coverage is not a total for named town frames or interiors, and green
cells do not establish actor presence or working gameplay. RC2's package
layer was verified on 14 October from full disk readback and independent
extraction. All 9,774 CHIM files retain the verified RC1 bytes; no new cells
were imported into RC2. The later v0.0.40-dev1 Pelagiad (0,-7) conversion passed
its measured offline audits and remains outside that package. Converted and packaged per-type actor/gameplay counts remain
unknown; original reference types are retained. Historical scoped Nord package diagnostics recorded punch, torch, swim and
dive behavior; those observations do not establish current gameplay acceptance.
Playtesting findings for [third-person punching](docs/bugs/PLAYER-PUNCH-THIRDPERSON-39.md), [movement with fists drawn](docs/bugs/PLAYER-READY-MOVEMENT-39.md), [blocking](docs/bugs/COMBAT-BLOCKING-36.md) and [swimming](docs/bugs/WATER-GAMEPLAY-PARITY-38.md) remain open.
RC2 inspection package and matching source artifacts finalized at
2026-10-13T22:15:44Z. Final v0.0.39 private playtest and matching public source
delivery finalized at 2026-10-14T07:15:35Z. Shipment does not close those
gameplay reports or establish gameplay acceptance; independent fresh-download
verification remains separate.

Historical RC1 package/source delivery finalized on 13 October at 18:06 UTC;
its 360 whole-cell check and six partial overlaps remain dated historical
evidence. Later RC1 regression reports stopped final preparation and led to
RC2. See the [cell tracker](docs/chim/CELL_TRACKER.md) and
[map guide](docs/chim/CHIM_PROGRESS_MAP.md) for separate evidence states.
The [11 October v0.0.36 map](docs/images/amiwind-v0.0.36-progress-map.png)
is retained as a historical snapshot.

**Earlier release, v0.0.35:** walk and run for NPCs, combat with weapons and shields, lava, Seyda Neen from your own data, about 30 engine crash fixes and a faster, resumable builder. Details: [docs/RELEASE-v0.0.35.md](docs/RELEASE-v0.0.35.md).

## v0.0.35 - CHIMporting It All: Gathering Up The Loose Branches From The Seashore

**AmiWind v0.0.35, running on CHIM Engine v0.1.0.**

A sync release: finished work that waited on side branches is gathered in. NPCs walk and run, fighters
use weapons and shields, lava glows and burns, Seyda Neen is built from your own game data, about 30
engine crash paths are closed and the builder resumes a failed build from where it stopped. Unfinished
work ships behind switches that are off by default.

- [Release notes](docs/RELEASE-v0.0.35.md)

## v0.0.34 - CHIM: Tightening the Bolts

**AmiWind v0.0.34, running on CHIM Engine v0.1.0.**

A fix release for v0.0.33: the silt strider's hull is closed again (its seams stay put when
the mesh is reduced, and it still fits Balmora's chunk memory), and every placed Bitter
Coast mushroom can be picked (invisible tree collision no longer blocks the pick). Both
fixes come with an island-wide check that runs in every build.

- [Release notes](docs/RELEASE-v0.0.34.md)

## v0.0.33 - Towards CHIM: Replacing the Engine Block

Introducing AmiWind's **CHIM** engine, a.k.a. **[C]hunks and [H]eaps [I]n [M]emory**.

**AmiWind v0.0.33, running on CHIM Engine v0.1.0.**

Balmora and Seyda Neen now run on pure CHIM: the world is cut into chunks, every
mesh, collision hull and texture is stored once and placed by reference instead of
being copied into overlapping region maps, and only the chunks around you are in
memory. It is still the AmiQuake engine underneath; what changed is how the world
reaches it. A far terrain layer draws the distance, and the CHIM builder is now the
default builder.

<!-- v0.0.33 photos -->
<!-- /v0.0.33 photos -->

### What is CHIM?

CHIM is AmiWind's overhauled engine: in many places a rewrite of the original
AmiWind engine, still built on id Software's Quake and the AmiQuake port. Its main
change is how the world is kept:

- **Store once.** Every mesh, collision hull and texture is stored once and placed
  by reference, the way Morrowind places its meshes, instead of being copied into
  every overlapping region map that can see it.
- **Stream chunks.** The land is cut into chunks; a ring of chunks around you is in
  memory and chunks join and leave a little at a time, so there is no "region
  loading" stop at a border.
- **Vis kept.** Chunks and placements are linked to the visibility leaves they
  touch, so Quake's visibility data still culls them.
- **Memory budgets.** The chunk ring lives in one fixed zone inside Quake's own
  heap, and the builder checks every CHIM area against the engine's numbers before
  it ships.

What it gained, measured (bytes and counts are exact; frame times are FS-UAE
emulator figures, relative until a real Amiga has been measured):

- **Disk:** Balmora's exterior 162.1 MB of legacy maps to 21.3 MB (7.6 times
  smaller); Seyda Neen with the intro docks 190.4 MB to 7.8 MB (24.3 times).
- **Loading:** the Balmora door walk reads 40.7 MB instead of 73.5 MB, in small
  steps instead of region loads.
- **Renderer work:** 46-114 brush models sent at the Balmora test cameras instead
  of 512-654, and 9-10 BSP nodes walked per clipped face instead of 27-52.
- **Frames (emulator, relative):** on a slow preset (a cycle-exact 68040 at about
  50 MHz) the median Balmora frame falls from 2.0-4.1 s to 1.1-1.6 s.

CHIM also has costs: it leaves less of the heap free at a town's load peak, spends
more time outside the 3D view and draws slightly more spans. The rest of the open
world is still on the legacy pipeline for now, and the Vivec Arena preview of
v0.0.32 is left out of this release; it comes back on CHIM.

Read more:

- [Release notes](docs/RELEASE-v0.0.33.md), with what is known in this build
- [CHIM engine](docs/chim/README.md)
- [CHIM file format](docs/CHIM_FILE_FORMAT.md): what CHIM stores and why, its files (`.chim` maps and the CHIM world), versions and roadmap
- [CHIM features](docs/chim/FEATURES.md): what is done, measured or still to do
- [Disk space](docs/chim/DISK_SPACE.md): Amiga disk limits and what CHIM saves
- [CHIM build guide](docs/chim/build_guide/README.md)

## v0.0.32 - Last Stop on the Old Line: Window-Shopping in Vivec

A first look at Vivec: the Arena canton as an outside-only preview, with stairs
you can climb and residents standing where Morrowind puts them. The last
release on the AmiQuake-based legacy engine.

<!-- v0.0.32 photos -->
| | |
| --- | --- |
| ![A lantern-lit bridge pillar against a blazing sunset in v0.0.32](docs/images/amiwind-v0.0.32-vivec-bridge-pillar.png) | ![A Vivec canal at night, lanterns on both sides, in v0.0.32](docs/images/amiwind-v0.0.32-vivec-canal-night.png) |
| **A lantern-lit bridge pillar** against a blazing sunset. | **A Vivec canal at night**, lanterns on both sides. |

More in the [gallery](docs/GALLERY.md).

<!-- /v0.0.32 photos -->

What's new:

- **Vivec Arena preview:** the Arena canton and the edges of its neighbours,
  outside only (doors say "Interior unavailable"); a separate area, reached with
  `dbg tp vivec_arena`.
- **Stairs and residents in Vivec:** the Arena stairs, bridges and walkways can
  be walked, and every resident stands on the original floor.
- **Horizon:** the default is the v0.0.30 look (`aw_skyline_fill 0`, Horstator
  approved); the skyline fill stays selectable as an experimental mode.
- **Fire:** the flames you can see win the flame budget, so hearths stay lit.
- **Console** edits like a terminal prompt, with history; `dbg daynight off`
  holds midday.
- **68040:** no library sine and cosine per frame; your own FPU support library
  can go on the boot disk (`--amiga-libs`).
- **Map loader** without temporary staging copies; renderer counters and the
  `awbench` hardware benchmark.
- **Builder:** builds the release from scratch from your own data, in parallel,
  with a build profiler and a known-inputs check.
- **New logo** and start-up lines.

Release notes, with what is known in this build:
[v0.0.32](docs/RELEASE-v0.0.32.md).

## v0.0.31 - Lamps, Lanterns and Loading

Balmora and Seyda Neen at night, lit by their own lamps and lanterns; much
faster loading; and the AmiWind Toolkit.

What's new:

- **Night in town:** the original street lamps, lanterns, wall torches and fires
  light Balmora and Seyda Neen at night with warm light; lantern and window
  glass glows; blue lanterns stay blue.
- **Light-space night:** night darkens the light, not the finished picture, so
  torches and glowing materials keep their light after dark.
- **Fire:** fireplaces and braziers burn with flames shaped like the original
  emitters, deep red to a near-white core, with rising embers; torches shed
  embers too. `dbg torchgallery` opens a dark room to look at them.
- **Guard torches** light half as far, so they no longer outshine the lamps.
- **Light hue:** torch, lamp and window light can be any colour
  (`dbg light hue R G B`, or the Hue row in `dbg lightgallery`).
- **Light gallery:** `dbg lightgallery` puts every night-lighting switch in a
  strip below the view, with a time preview.
- **Fog distance slider** (Options > Fog distance, 100-1500), **skyline fill**
  for short fog distances, and optional **location fog** per place.
- **Horizon veil** (`dbg horizon veil`) hazes gaps in distant silhouettes.
- **Faster loading** everywhere, and lighter Seyda Neen sub-cells.
- **Music and opening:** silent start-up until the title music, no stray clips
  while the ship loads, a shorter wait after the intro video, and the ship
  fades in from black.
- **Place names** in the location label, from the original cell names.
- **Time controls:** `dbg time`, `dbg time HHMM`, `dbg 24hrcycle`.
- **Debug headlamp:** `dbg headlamp on` lights dark places without a torch.
- **`dbg lamps`** shows which lamps are lit around you and why.
- **AmiWind Toolkit:** World / Local / 3D Inspector, multi-cell selection,
  scrollbars, keyboard panning.
- **Entity tracker:** the image build counts what the original game places
  against what AmiWind places, and stops if a category goes missing.
- **Builder:** writes the night lamp, glowing glass and location fog tables
  itself, and finishes its last step again.
- **Console:** every `dbg` command sorted and tested; on/off words work for
  every setting.
- **Docs:** a performance page with charts on what the engine is asked to draw,
  and the rule that the repository builds the whole game from scratch.

What we gained (measured):

- **Loading:** game files are read in 16 KiB pieces instead of 1 KiB (a 4.8 MB
  Seyda Neen map took over 4,700 separate disk reads). Seyda Neen region
  crossings: 0.54-0.71 s in v0.0.30, now 0.39-0.48 s on the test route.
- **Seyda Neen maps:** 247.5 MB down to 185.6 MB (-25 %); maps over the modeled
  memory reserve: 43 down to 6.
- **Lamps and lanterns at night:** 694 original street lamps, lanterns, wall
  torches and fires give a torch's worth of warm light from dusk to full day;
  lantern and window glass glows in 79 town maps.
- **Torch light at night:** torches and glowing materials keep their light after
  dark; walls lit by a torch measured about 2.5 times brighter than before.
- **Frame rate control:** Options > Fog distance is now a slider (100-1500); in
  Balmora a fog distance of 250 roughly doubles the frame rate, and the skyline
  stays fogged instead of cut out.
- **Music:** silent start-up until the title music, no stray clips while the
  opening loads, and the prison ship fades in from black.
- **Place names:** the location label reads "Vvardenfell / West Gash Region /
  Balmora" from the original game's cell names.
- **AmiWind Toolkit:** World, Local and 3D Inspector tabs for anyone working on
  AmiWind (below).
- **Console:** 116 `dbg` commands, sorted and tested so every one reaches its
  handler; `dbg time`, `dbg 24hrcycle`, `dbg lightgallery`, `dbg lamps`,
  `dbg headlamp`.
- **Bug tracking:** one register, 186 records, a report page for every bug found
  since v0.0.30.

| | |
| --- | --- |
| ![A Balmora street lamp lights the wall and street at 01:19](docs/images/amiwind-v0.0.31-balmora-night-street-lamp.png) | **01:19, a street lamp.** A torch's worth of warm light on the wall and the street; its glass glows. |
| ![A lamp-lit house in Balmora at 02:18 with a passer-by](docs/images/amiwind-v0.0.31-balmora-night-lamp-house.png) | **02:18, a lamp-lit house.** Pools of light with darker street between, the way a town at night should look. |
| ![The Odai river in Balmora glittering at 22:46](docs/images/amiwind-v0.0.31-balmora-night-river.png) | **22:46, the river.** The water glitters under the night sky. |
| ![A Balmora plaza at 21:38 with a Hlaalu guard carrying a torch](docs/images/amiwind-v0.0.31-balmora-night-plaza-guard.png) | **21:38, a plaza guard.** Guard torches light half as far as before, so they no longer outshine the lamps. |
| ![A Balmora house corner lit by its lamp at 22:36](docs/images/amiwind-v0.0.31-balmora-night-house-corner.png) | **22:36, a house corner.** Lamps stay lit while you turn and walk; a lamp that hands its light to a nearer one fades out instead of snapping off. |

Release notes: [v0.0.31](docs/RELEASE-v0.0.31.md) (with the dev1-dev6 notes linked
there) and the [bug register](docs/BUGS.md).

### Whoops! Actually...

Most of what AmiWind draws, Quake never got the chance to skip. Quake's `vis`
tool precomputes what can be seen from where, but only the world's own walls
count, and every converted building, room and rock went in as a `func_wall`
model, which `vis` ignores. Measured on the dev5 and dev6 maps:

| Map type | Visible from an average spot |
| --- | ---: |
| Interiors (Mages Guild, Temple, Census, prison ship) | 100 % |
| Balmora streets | 84-89 % |
| Open world with rocks and trees | 69-85 % |
| Seyda Neen | 59-76 % |

Inside the Mages Guild, all 40,488 faces were processed every frame wherever
you stood, and NPCs behind houses were drawn in full. The fix is the Quake way:
static building faces become part of the world, which Quake culls leaf by leaf,
and invisible solid blocks inside buildings and walls give `vis` the walls to
cut with. (Blocks alone were tried first: buildings left as separate models
stay visible as a whole.) Details: [Town visibility](docs/performance/TOWN-VISIBILITY.md) and
[TOWN-VIS-OCCLUSION-31](docs/bugs/TOWN-VIS-OCCLUSION-31.md).

### AmiWind Toolkit

The browser Toolkit inspects your own converted data: **World** shows cell
coverage and reference counts, **Local** shows a cell's maps, **3D Inspector**
opens BSP maps, CHIM maps and whole CHIM worlds, and **Monitor** follows builds.
It runs locally; game data and inspection exports are not uploaded.

The current [inspection controls](amiwind-toolkit/README.md#v0038-inspection-controls)
include remembered Names on/off, direct cell links with an optional highlighted
selection, per-panel Copy JSON, textures with a density heatmap, direct scene
and CHIM archive links, a collapsible sidebar and a placed-face budget display.
Stored, placed and preview counts remain distinct from native memory or speed.

World's **Included in build** view is separate from conversion colours and
release plans. It uses verified final-image readback; selected or planned cells
are not included cells. Inclusion alone does not verify lighting, actors,
interactions or traversal. See the [Toolkit guide](docs/AMIWIND_TOOLKIT.md) and
[CHIM coverage guide](docs/chim/CHIM_PROGRESS_MAP.md).

The guide retains historical v0.0.31 and v0.0.36 screenshots. Their headers,
controls and coverage totals describe those snapshots, not the current build.

## v0.0.30 - The Temple

The Balmora Temple is whole again. A scene-converter fault turned some meshes
around their own origin, leaving missing walls, see-through holes and floating
objects in the Temple's lower rooms; the same fix repairs Tharys Ancestral Tomb
and the Nord fireplaces of five Seyda Neen interiors.

| The Balmora Temple lower entrance in v0.0.30 | The Temple lower room: doorway and banner |
| --- | --- |
| ![The Balmora Temple lower entrance in v0.0.30 with the wall in place](docs/images/amiwind-v0.0.30-temple-after.png) | ![Balmora Temple lower room in v0.0.30: doorway and banner](docs/images/amiwind-v0.0.30-temple-banner.png) |
| ![Options > Controls page in v0.0.30](docs/images/amiwind-v0.0.30-controls.png) | |

Also new: misplaced Census office objects from dev5 fixed, a crash fix for
Seyda Neen region changes, an Options > Controls page for rebinding keys,
arrow keys that move like W/A/S/D, NPCs lit by the floor they stand on,
glowing lantern glass and flames on placed fires (rebuilt maps only so far),
about 15 % less reading on heavy Seyda Neen crossings, less music crackle in
WinUAE (still heard on some map changes), and an engine that builds without
compiler warnings. Every lighting and loading change has a console switch.

Still open: Seyda Neen crossing pauses (a lighter rebuild of its maps is under
way), a rare load freeze seen in automated runs, and the issues carried over
from v0.0.29. See the [release notes](docs/RELEASE-v0.0.30.md) and the
[tracker](docs/BUGS.md). Development builds:
[dev3](docs/RELEASE-v0.0.30-dev3.md), [dev4](docs/RELEASE-v0.0.30-dev4.md),
[dev5](docs/RELEASE-v0.0.30-dev5.md), [rc1](docs/RELEASE-v0.0.30-rc1.md).

## v0.0.29 - Let There Be (Just a Bit More) Light

Explore with adjustable interior brightness, clearer torchlight and improved
first-person hands. Graphics settings now provide independent saved interior
and exterior controls; the Census door guard and reported Seyda shack lighting
jump have positive RC2 playtest results. Confirmation dialogs use framed buttons.

This remains an experimental project with incomplete world and gameplay coverage.
Balmora Temple geometry holes and WinUAE music crackle/pauses remain known issues,
alongside the hand-animation transition and memory/performance limits. See the
[release notes](docs/RELEASE-v0.0.29.md) and [current tracker](docs/BUGS.md).

## Earlier v0.0.29-rc1 playtest - More Mushrooms! (...and fixes)

The **rc1 candidate is assembled** and has completed a bounded native FS-UAE
playtest: Audio controls, independent dialogue/effects levels and mushroom
pickup with save/reload were verified. Public source publication remains pending.
Final **More Mushrooms** still depends on the world-coverage and regression gates
in [the release plan](docs/PLAN-v0.0.29.md). The dev4 hotlist remains below.

- **Broader mushroom coverage:** the current memory model admits 347 of 390
  exterior maps. Forty-three maps and additional interior routes still need
  work. These are admission results, not a claim that all placements have passed
  in-game testing. See [asset coverage](docs/ASSET_COVERAGE.md).
- **Less temporary and resident RAM:** compact persistent harvest state,
  direct alias-model loading and exact edge/surface layouts preserve source
  geometry while reducing allocations. Native peaks and outdoor transition
  smoothness remain checks of their own.
- **Race-specific first-person hands:** the candidate includes a source-topology
  catalogue and corrected lighting normals, with legacy profiles retained. Bounded
  native motion comparisons show no newly detached skin triangle; the paw-like
  silhouette remains an appearance issue. Transparent sprite conversion is a
  [future investigation](docs/FIRST_PERSON_HANDS.md#investigation-first-person-hands-rendered-as-sprites).
- **Torch repairs:** nearby NPCs respond to local torchlight in bounded native
  off/on tests, and all three tested flame styles are visible. The rc1 run also
  captured held torchlight with a nearby NPC; broader actor coverage remains in
  the [tracker](docs/BUGS.md).
- **Audio work:** smaller, audio-serviced head-preview reads avoid a reproduced
  starvation case under injected disk delay. The rc1 WinUAE playtester reports
  no OST jump when entering appearance selection; a later RC2 WinUAE report
  reopens that issue. A separate
  Audio options screen with Master, Music, Effects and Dialogue sliders now has
  native arrow-key and saved-setting checks, plus independent dialogue/effects
  output checks. Broader listening and event coverage remain open.
- **Faster regression checks:** disk-backed debug help, `dbg shroompicker`
  locations and the `playvideo`, `videoplay`, `playvid` and `vidplay` aliases make
  the playtest easier to exercise.

### From the rc1 playtest

| Aim and pick | Pickup feedback |
| :---: | :---: |
| ![Luminous Russula with the E: Pick prompt in rc1](docs/images/amiwind-v0.0.29-rc1-mushroom-prompt.png) | ![Picked up one Luminous Russula in rc1](docs/images/amiwind-v0.0.29-rc1-mushroom-pickup.png) |

| Audio options | Torchlight at night |
| :---: | :---: |
| ![Master, Music, Effects and Dialogue sliders in rc1](docs/images/amiwind-v0.0.29-rc1-audio.png) | ![Nord hands, a held torch and a nearby NPC at night in rc1](docs/images/amiwind-v0.0.29-rc1-torch-night.png) |

![Actual rc1 mushroom pickup sequence](docs/images/amiwind-v0.0.29-rc1-mushroom-pick.gif)

These are actual frames and a six-second clip from the same rc1 run. A debug
destination placed the player by the mushroom; the pickup and save/reload used
ordinary controls. Two distinct plants were collected and remained picked after
reload. See [capture details and earlier galleries](docs/GAMEPLAY_MEDIA.md) for
the test scope and image processing. Broader audio and world checks remain open.

<p align="center">
  <img src="docs/images/amiwind-v0.0.29-rc1-high-elf-appearance.png" width="695" alt="High Elf male appearance selection in rc1, Face 1 of 6 and Hair 1 of 5">
</p>
<p align="center"><em>High Elf male appearance selection in WinUAE, v0.0.29-rc1.</em></p>

This separate playtester-supplied screenshot is unchanged. The playtester
confirms that entering appearance selection caused no OST jump in rc1; this
records that earlier result. The later RC2 WinUAE playtest reopens entry
audio continuity, so it remains in the current known issues.

## v0.0.29-dev4 — WIP: More Mushrooms! (...and fixes)

**More exciting features and bug fixes —** small mushrooms to pick, steadier
free-look, clearer nights and a growing list of repairs across Vvardenfell.
This is a development preview; **v0.0.28 remains the latest stable release**.

### The hotlist: changes since v0.0.28

- **Pick your first small mushrooms.** Six original Luminous Russula placements
  form the dev4 pilot. Aim for the name and **E: Pick**, collect the ingredient,
  and the mushroom disappears. Shared placement identity, hidden inventory and
  sparse saved state keep tested pickups from returning across map changes or
  save/load. `dbg shroomtracker` reports collected mushrooms.
- **Pickup feedback and joined mushroom meshes.** The original item sound and
  rectangular notification accompany successful collection; the notification
  animation is configurable. Conversion preserves shared mesh seams. This
  pilot is the starting point for worldwide picking.
- **Free-look stays where you put it.** Legacy automatic pitch centering while
  walking is disabled by default. `aw_auto_center 1` retains the old behavior;
  explicit centering remains available. Other reported orientation resets are
  still being investigated.
- **Lighter full-screen UI.** Head/race selection and blocking journal, map and
  reading overlays can freeze world work behind a black background while the
  soundtrack and interface keep running. The live background remains selectable;
  the original name-entry scene keeps its existing behavior.
- **Character-menu improvements.** UI mode 2 adds clickable, keyboard-focused
  **OK** buttons. Confirmation and travel choices gain matching framed buttons.
  `dbg tpscene headselection` skips directly to appearance selection for testing.
- **Map and HUD repairs.** Map palette fixes remove unwanted bright dots;
  debug-map selection, teleport aliases, secondary-button panning and tab/input
  handling have been revised. Health, magicka and fatigue use independent values,
  with heading and time available in the debug HUD. Broader mouse checks continue.
- **Hands and carried equipment.** The periodic unarmed idle blink has a corrected
  animation frame range, and repaired world-map metadata restores sampled F/V
  hand/torch controls. Transition view, equipment and voice continuity have new
  preservation paths. Quickload still puts equipment away in dev4; its separate
  save-format fix is coming next.
- **More useful torchlight.** Surface-light interpolation is repaired; player
  and admitted guard lights have a configurable radius, default 192 instead of 144.
  Optional bright-base and spark flame styles are available, and torch depth bob
  is disabled by default. Guard-light cache handling is improved; intermittent
  guard visibility and dim lighting remain on the investigation list.
- **A clearer midnight sky.** The new default clears clouds around 00:00–03:00
  and brings them back toward 04:00, revealing stars and both moons. Legacy cloud
  behavior stays selectable. The improved night appearance has playtest approval.
- **Scenery repairs.** Indrele Rathryon's shack walls are restored. Tree-root
  sampling and distant terrain presentation have improvements, with occasional
  horizon gaps and popping still being worked on. The experimental terrain
  horizon renderer remains opt-in.
- **Movies: 17/17 available source videos converted.** The builder includes the
  discovered movie catalogue. Dev4 retains its higher-resolution intro alongside
  the other new outputs; checking every in-game movie event and soundtrack is
  still in progress.
- **Music: 18/18 available tracks converted.** The complete inspected soundtrack
  set is included in the builder's media output.
- **Voices: 6,447/6,447 available files converted.** Seven additional referenced
  voice sources are missing from the inspected installation and reported as such.
- **Sound effects: 717/717 available files converted.** Two additional referenced
  effects are missing. All four categories have zero failed conversions for
  available inputs; event wiring, listening checks and crackling fixes continue.
  These counts describe conversion from a local game installation; the public
  source archive contains no original game media.
- **Better development tools.** New public guides cover headless FS-UAE and
  OpenMW reference runs in Docker, machine-state inspection and repeatable
  comparisons. Asset coverage, allocation checks and a documented cell-transition
  profiling investigation help track what is present and what still costs time.

### What's cooking next

- **More Mushrooms, worldwide:** compact original-placement data, shared models
  and persistent picking across exterior cells and mushroom-containing interiors.
  Interior rooms and connecting door routes still need integration.
- **More complete saves and hands:** restore equipment intent on quickload,
  improve hand mesh joins/detail and add race-specific first-person hands.
- **Smoother exploration:** measure and improve cell read-ahead/loading pauses,
  close remaining horizon gaps, and continue torch, audio and input fixes.
- **A clearer build report:** distinguish source assets, converted output,
  installed/reachable placements and missing or unsupported content at each build.
- **Later milestones:** Caius Cosades and the Dwemer puzzle box, richer interiors,
  and a combat-testing arena remain on the roadmap.

Dev4 is a **development prerelease**, with a small mushroom pilot rather than
worldwide coverage. See the [dev4 notes](docs/RELEASE-v0.0.29-dev4.md) for tests,
known issues and exact scope, plus the [active plan](docs/PLAN-v0.0.29.md).
There are no new dev4 pictures yet; the gallery below is from v0.0.28.

## v0.0.28 — Trees and Grass, Day and Night

Trees along the road, reeds by the water, grass around the rocks. Vvardenfell's
scenery is filling out beneath red-and-gold sunsets, purple twilight and a cool
blue hour. The new night layer brings back original stars, nebulae, Masser and
Secunda, while guards prepare their torches for the night watch. All of it works
through a shared indexed sky designed for the Amiga renderer.

**The v0.0.28 release build has passed its bounded independent WinUAE playtest.**
Fresh Windows and Linux builds produce the same Amiga executable. The release
adds foliage, a shared sky, tiny background stars, both moons and timed guard
torches. Explore the new skies below and see the
[release notes](docs/RELEASE-v0.0.28.md) for verified scope and known limitations.
Source publication is completed through the separately gated release workflow.

| Sunrise 06:30 | Red sunset 18:00 | Blue hour 20:15 |
| :---: | :---: | :---: |
| ![Sunrise 06:30 — Seyda Neen day gallery](docs/images/amiwind-v0.0.28-v3-sunrise.png) | ![Red sunset 18:00 — Seyda Neen day gallery](docs/images/amiwind-v0.0.28-v3-red-sunset.png) | ![Blue hour 20:15 — Seyda Neen day gallery](docs/images/amiwind-v0.0.28-v3-blue-hour.png) |

| Masser | Secunda | Balmora at 23:00 |
| :---: | :---: | :---: |
| ![Masser — Balmora night gallery, render time 23:00](docs/images/amiwind-v0.0.28-night-masser.png) | ![Secunda — Balmora night gallery, render time 23:00](docs/images/amiwind-v0.0.28-night-secunda.png) | ![Balmora at 23:00 — street sky](docs/images/amiwind-v0.0.28-balmora-street-sky.png) |

![From dawn to night: eight native V3 gallery stages](docs/images/amiwind-v0.0.28-day-gallery.gif)

*Real 320×200 Amiga frames captured in WinUAE. The GIF is an eight-stage
montage with edited timing; the screenshots retain their native pixels.
[All day and night stills, plus both GIFs](docs/GAMEPLAY_MEDIA.md#v0028--trees-and-grass-day-and-night).*

- **More of the original scenery.** The prepared world includes **19,984 unique
  foliage placements**: 19,787 sprite placements across 76 shared types and 197
  mesh placements, including 192 in Balmora. The landscape retains **37,960 rock
  placements** and **816 giant mushrooms**, with joined mushroom geometry.
  These count original source placements; neighboring map copies do not add
  unique instances.
- **One sky across exterior cells.** The default V3 presentation brings red and
  gold sunsets, purple twilight and a cool blue hour, with two scrolling cloud
  layers and a moving sun. Sky, distant fog and a subtle exterior world tone
  follow the persistent clock; interiors keep their own lighting.
- **Time you can control.** The cycle starts enabled. Press **T** to wait, use
  `dbg set time sunrise` or `dbg set time 1830` to choose a moment, and
  `dbg daynightcycle off` / `on` to pause or resume automatic time. The new
  `dbg daycycle gallery` tours eight sky stages; `dbg nightgallery` previews
  the night sky, Masser, Secunda and overhead stars. Both preserve player position
  and saved time, with `here` for a fixed view and `off` to return.
- **Torchlight for the night watch.** The new guard-torch runtime equips supported
  Imperial guards in Seyda Neen and Hlaalu guards in Balmora from their original
  equipment and poses. `guards_torch_cycle` follows the saved clock;
  `dbg guardtorch on/off/auto` provides an explicit override. Independent native
  checks confirm cold loading, dawn/dusk switching and subtle animated flame
  particles for both guard types. Heavy-scene memory reserves remain limited.
  [Source rules and current acceptance](docs/TORCH.md).
- **Better tools to see what costs memory.** The 3D Map Inspector and build
  comparisons expose stored geometry, placed geometry and per-map loading
  estimates. The Seyda Neen terrain winding repair restores the missing textured
  ground; broader world geometry and performance work remains ongoing.

Press **F10** for the console, or **Shift+F10** for fullscreen. The separate
`dbg sky off` / `on` control switches the sky/fog effect while time keeps passing.
`dbg sun off` / `on` and `dbg clouds off` / `on` control the two features
independently; both start enabled. These switches also accept `1/0` and
`true/false`. Saved settings can override the shipped defaults.

The pictures above come from the stable V3 default and native night layer.
Historical V1 prototype captures remain in the [capture record](docs/GAMEPLAY_MEDIA.md).
The local converter also converts the original star/nebula textures and both
moons into a compact night layer. Some bright stars twinkle gently in cool blue,
behind the moons and clouds. `dbg starsky` toggles stars/nebula and
`dbg nightsky` toggles that whole layer; both default on and accept the same
boolean forms. `dbg skyspeed` adjusts cloud motion, with a calmer
`0.00333333333` default. Original-source stars are tiny background points behind
the nebula, clouds, scenery and complete moon silhouettes.
The night gallery and Balmora night views have been checked in WinUAE. Regional
weather and full nearby-world lighting remain follow-up work. Read the
[sky and clock guide](docs/DAY_NIGHT_AND_SKY.md) for controls and current scope.

The shared-sky build comparison removed **301,751 local sky faces across
2,664 exterior maps**. Those compared maps plus one shared sky resource saved
**131.324 MiB of disk storage** against their untouched inputs. This measures
the sky conversion alone; subsequent terrain repairs and each loaded map have
separate storage, RAM and frame-cost checks.

![Build comparison: 301,751 local sky faces removed across 2,664 exterior maps; 131.324 MiB aggregate disk saving](docs/images/amiwind-shared-sky-build-comparison.svg)

*Project-authored build comparison. [Measurement scope](docs/DAY_NIGHT_AND_SKY.md).*

## AmiWind 3D Map Inspector

**Geometry analysis and optimization planning**

The standalone [AmiWind 3D Map Inspector](docs/POLYCOUNT_INSPECTOR.md) helps
inspect converted BSP geometry and plan optimization work. It is one component
in the aspirational **AmiWind Map Optimization Toolkit** direction, not a claim
that a complete automatic optimizer or runtime profiler is finished. The
bounded hidden-surface pass remains experimental, and verified house examples
currently produce no cuts. Read its [development roadmap](docs/BUILD_TOOLKIT_ROADMAP.md)
and [exterior hidden-surface status](docs/EXTERIOR_HIDDEN_SURFACES.md).
The [Map Optimization Toolkit overview](docs/AMIWIND_MAP_OPTIMIZATION_TOOLKIT.md)
and [measured findings](docs/MAP_OPTIMIZATION_FINDINGS_2026-10-04.md) distinguish
completed representation savings from open geometry and target gates.
See the [memory notes](docs/MEMORY_ALLOCATION.md),
[cell-changing checklist](docs/CELL_CHANGING.md),
[sky and background rendering](docs/DAY_NIGHT_AND_SKY.md#shared-exterior-background-sky-implementation-candidate),
[terrain-culling status](docs/TERRAIN_VISUAL_CULL.md),
[bug journal](docs/BUG_JOURNAL.md) and [roadmap](docs/ROADMAP.md) for the details.
Original-game assets, converted proprietary content and ROMs are not distributed
with AmiWind; you provide your own legally obtained files. Playable builds and
playtest packages containing those assets stay private.

### v0.0.27 — Rocks, Mushrooms, and Then Some: playtest screenshots

These Ascadian Isles screenshots were captured in WinUAE during the rc2
playtest: closed caps, joined rims and textured undersides. They show the mushroom
work that carries into the published v0.0.27 release.

| Closed cap and rim | Giant mushrooms on the hillside |
| --- | --- |
| ![Closed giant-mushroom cap in rc2](docs/images/amiwind-v0.0.27-rc2-mushroom-cap.png) | ![Ascadian Isles giant mushrooms in rc2](docs/images/amiwind-v0.0.27-rc2-ascadian-mushrooms.png) |

![Joined mushroom underside in rc2](docs/images/amiwind-v0.0.27-rc2-mushroom-underside.png)

### Explore the growing world

Walk the base-game island's terrain, head into the detailed streets of Seyda
Neen and Balmora, or take a detour through the character gallery. Rocks and
giant mushrooms join terrain and water across the wider world. This release
adds foliage; other settlement scenery and wider-world actors remain
incomplete. Bloodmoon and
Tribunal world content are outside the current playable scope.

Both towns use 64 exterior subdivision cores to keep individual maps bounded.
Balmora includes 43 destination interiors, including Tharys Ancestral Tomb;
Seyda Neen keeps its opening scenes and converted interiors. Aim at doors or
residents and press **E**. NPC interaction currently provides bounded authored
greetings. Full combat, quest simulation, services, schedules and inventory remain
unfinished. See [character-state limitations](docs/CHARACTER_STATES.md).

Character creation follows the opening registration sequence: name, race,
gender, head and hair, class, birthsign and a final review. The appearance
screen has a rotating head preview. Character choices and earned journal history
persist in saves. Start a fresh character when moving from older content.

**J** opens the two-page progression journal; **M** opens the island map. Older
saved configurations regain these keys when unassigned. Journal headings stay
centred on the left page and wrap onto multiple lines. The map marker follows
source coordinates and keeps its zoom on reopen. See
[map and journal](docs/WORLD_MAP_AND_JOURNAL.md).

**F**, then **V** equips a [torch converted from the original game](docs/TORCH.md),
with an animated grip and flame attached to its source emitter. The debug header
shows the region from the game's own records. The earlier torch-crash correction
is included; its target retest and the brief fist-visibility blink remain tracked
in the [bug journal](docs/BUG_JOURNAL.md).

`dbg gallery` opens the inspection plane for **2,935 original NPC/creature
records and all 3,551 converted model assets**. Search by friendly name or source
ID, inspect equipped/base-body variants, and return to the captured game state.
Dagoth Ur's protected mask geometry and original gold texture use an exact-model
allowance, enabled by default with `aw_allow_poly_budget_over true` and
`aw_poly_budget_over_cap auto`. Wheel cycles models; middle-click opens the
browser. [Gallery controls](docs/CHARACTER_MODEL_GALLERY.md).

### Earlier glimpses of Vvardenfell

| Welcome to Balmora | Dagoth Ur, in the character gallery |
| :---: | :---: |
| ![Balmora bridge in v0.0.24](docs/images/amiwind-v0.0.24-balmora-bridge.png) | ![Dagoth Ur's gold mask in the native gallery](docs/images/amiwind-v0.0.24-dagoth.png) |
| **Vvardenfell world map** | **Two-page progression journal** |
| ![Vvardenfell map with source coordinates](docs/images/amiwind-v0.0.25-rc1-map.png) | ![Dated progression journal](docs/images/amiwind-v0.0.25-dev1-journal.png) |

*Native FS-UAE captures at integer scale: map from v0.0.25-rc1, journal from
v0.0.25-dev1, town/gallery from v0.0.24. [Capture details](docs/GAMEPLAY_MEDIA.md).*

### Finding your way around

Shift+V cycles view distance. The optional compass is off by default;
`dbg compass on` enables it. GLOBAL/LOCAL XYZ aid navigation, and Ctrl debug
flight runs at twice Shift speed. M/N console typing is protected; debug Alt+M
exposes the desktop. Bindings have their own
[keymap file and reference](docs/KEYMAPS.md).

`dbg aw hors 0` creates the Nord / Barbarian / The Steed test character after
Census; `dbg tp balmora` travels to Balmora and supplies that character if absent.
`dbg tp vivec` (or `dbg tp vivec_arena`) does the same for the Vivec Arena preview,
outside only: its doors do not open yet. `dbg tp` opens the destination picker. `dbg map tp` and `dbg tp map` open the
world-map teleport picker. `dbg daynight off` holds the clock at 12:00 midday
(sky, light, lamps and windows as by day) until `dbg daynight on`. See
[debug controls](docs/DEBUG_OVERLAYS.md).
The animation kit (walk and run by speed, its build switch and `dbg animkit`):
[docs/ANIMKIT.md](docs/ANIMKIT.md).

Automatic cell changes preserve held input and gameplay state in the transition
checks; doors and explicit travel retain their own loading behavior. The default
loader replaces maps synchronously. At automatic crossings, Loading... waits
two seconds by default; startup and explicit travel remain immediate.
Experimental read-ahead does not establish seamless background
streaming. Exact crossing, collision and state checks remain on the
[target playtest checklist](docs/CELL_CHANGING.md).

### Making room for Morrowind

The current world is a baseline for measuring and optimizing content, memory,
loading time and frame cost. Town subdivisions remain necessary; their static
heap estimates do not certify runtime safety or FPS. Future changes must retain
closed mushroom seams, original placement and UVs, collision, and continuous
terrain handoffs. See the [optimization roadmap](docs/ROADMAP_HISTORY.md#assemble-first-then-optimize-the-measured-world).

Large outputs automatically split into simultaneously mounted HDFs, each below
4 GiB with filesystem partitions below 2 GiB. This is not disk swapping, and more
disk capacity does not add runtime memory. Generated emulator configurations
list every required disk; the paths are also recorded in the
[build output](docs/BUILD_OUTPUT.md).

Character conversion uses a [verified persistent host cache](docs/NPC_MODEL_CACHE.md).
The full NPC gallery remains enabled by default; reused models retain the same
Amiga format and quality. [Image recovery](docs/IMAGE_RECOVERY.md) can reuse
compatible, validated conversion output. General stage resume is not available.

The reference target is **A1200 / AGA / PAL, 68040 + FPU + JIT, 2 MiB Chip and
16 MiB Z3 RAM**. Stock A1200 and physical-hardware performance are unproven.
Linux remains the established build foundation. Native Windows is experimental,
with intermittent worker and cancellation failures recorded in the
[Windows guide](docs/WINDOWS_BUILD.md) and [bug journal](docs/BUG_JOURNAL.md).

The [Docker build helper](docs/DOCKER_BUILD.md) takes your own Morrowind
installation as private runtime input. Images contain source and tools; game
data, converted assets and ROMs stay outside image layers and public releases.
While it runs, the Toolkit's [Monitor](docs/DOCKER_BUILD.md#watch-a-build-in-the-monitor) follows it
in a browser: `python tools/toolkit_serve.py --monitor-docker amiwind-docker-builds --open`.
The [v0.0.27 release notes](docs/RELEASE-v0.0.27.md) record the first Docker-built
baseline's build and CI evidence. Earlier full-conversion and game-entry results remain in the dated
[Windows](docs/VALIDATION-WINDOWS-2026-10-02.md) and
[Docker](docs/VALIDATION-DOCKER-2026-10-02.md) records and
[v0.0.26 release notes](docs/RELEASE-v0.0.26.md).

See [world survey](docs/WORLD_SURVEY.md), [project state](docs/PROJECT_STATE.md),
[font options](docs/PAPER_FONT_OPTIONS.md) and
[conversion lessons](docs/BALMORA_CONVERSION_LESSONS.md) for more.

*For years, they thought the Nerevarine would never appear on the Commodore Amiga...*

*Well, those n'wahs were wrong! The prophecy said nothing about the frame rate.*

## About AmiWind

Created by **FlyingFathead a.k.a. Horstator**
Thanks to: **ChaosWhisperer**

> Massive thanks to everyone in the Amiga community who have been willing to
> share code and ideas to make this dream come true to a beloved platform.
> *May the wind be on your back!*

A fan-made tribute, free and open-source conversion tools, and an experimental
Amiga runtime. The growing playable world combines an island-wide terrain/scenery pass with
detailed starting towns, while much of Morrowind's gameplay remains unfinished. The A500 experiment
is preserved alongside the accelerated AGA development track.
**Official project repository:** [FlyingFathead/amiwind](https://github.com/FlyingFathead/amiwind).
**Repository root: `amiwind/`.** This directory contains the conversion tools,
complete native engine source, tests and documentation. `engine/aga/` is part of
this repository, not a second repository. See [repository layout](docs/REPOSITORY_LAYOUT.md).

**Original Morrowind game files are required. You must provide your own copy.**

> **AmiWind recommends the GOG GOTY edition of Morrowind.**
>
> AmiWind has been developed and tested primarily against the GOG Game of the Year
> release. The GOG installation includes additional loose TrueType (TTF) font assets
> that provide a better starting point for AmiWind's offline font conversion and
> rasterization.
>
> The Steam GOTY edition does not normally include these loose TTF font assets. When
> they are unavailable, AmiWind will fall back to Bethesda's original `.fnt` + `.tex`
> bitmap fonts and continue the build. This fallback is supported, but converted font
> quality and appearance may differ and may be inferior, particularly when fonts must
> be rendered at sizes different from the original bitmap assets.
>
> **For the best-tested and preferred AmiWind conversion path, use the GOG GOTY edition:**
>
> https://www.gog.com/en/game/the_elder_scrolls_iii_morrowind_goty_edition

The Steam GOTY edition remains a supported fallback input when its required game data
passes AmiWind's validation.

AmiWind runs on the CHIM engine, built on GPLv2 code from **id Software's
Quake** (John Carmack and the id team) and its Amiga port **AmiQuake** (Peter
McGavin, NovaCoder, Stephen Leary). The CHIM builder that converts your own
Morrowind files is GPLv3.

The Amiga runtime contains code from **id Software's Quake** and the
**AmiQuake** port, changed and extended for **AmiWind**. That code is
distributed under the **GNU GPL version 2**, with the original copyright and
licence notices kept in the files; files granted under "version 2 or later"
keep that grant. AmiWind's host tools and the original A500 runtime are a
separate program under **GPL-3.0-only**; see [LICENSE](LICENSE). OpenMW serves
as a reference for file formats and behaviour. The current converters are
standalone tools and include none of its code; earlier opening experiments used
OpenMW only to make external captures. [Licensing and credits](docs/LICENSING_AND_CREDITS.md)
has the details for each component.

Licensed Amiga ROMs are available from
[Cloanto / Amiga Forever](https://www.amigaforever.com/), which is worth
supporting. The public repository includes no Kickstart ROM, so you need a
suitable one of your own. Public test records identify the tested ROMs by
checksum.

Setup works much as it does in OpenMW: you point the tools at your installed
game folder. The conversion runs on your own machine and writes to a separate
workspace. AmiWind is an independent project, not an OpenMW release and not an
official Bethesda product.

> **Public source package: no commercial game data or ROMs.** The package
> includes no Quake or Morrowind game data, reusable game artwork, music,
> voices, game executables, Amiga Kickstart ROMs or Workbench files. It holds
> a selection of development screenshots and a short clip for the
> documentation, but no compiled AmiWind executable. The default engine build
> links no assembly recovered from a game binary (see
> [licensing and credits](docs/LICENSING_AND_CREDITS.md) for the upstream
> assembly used by an experimental profile). The GPL-licensed engine source is
> separate from the game assets. Converting the data needs your own Morrowind installation, and
> running the result in an emulator needs a suitable licensed Kickstart ROM.
> Compiling only the engine needs neither.

Copyrights stay with their holders, including the original code contributors,
and each component keeps its own licence. Morrowind, The Elder Scrolls, Quake,
Amiga and related names belong to their owners. AmiWind is an independent fan
tribute, not affiliated with or endorsed by Bethesda/ZeniMax, id Software,
Commodore, Cloanto or the OpenMW project. The GPL gives no right to share game
assets or ROMs. Game images you build yourself are private build outputs, not
public source releases.

## Building and playing

**Native Windows entry point (experimental):** `build.cmd` or `build.ps1`.
Start with `.\setup-windows.cmd -Plan`, then `.\setup-windows.cmd -Yes`, and follow the
[Windows setup guide](docs/WINDOWS_BUILD.md). Windows and Linux share the Python
build pipeline. Earlier native Windows full conversion and WinUAE game-entry
checks passed; experimental reliability limits remain. The published v0.0.27
passed Linux/Windows launcher CI, Docker builder CI and the source/asset-free
build job. See the [release notes](docs/RELEASE-v0.0.27.md) for the scope of each
check; these results do not certify a full v0.0.27 gameplay run on either host.

**Quickest way to compile on Ubuntu/Debian Linux (or Ubuntu under WSL):**

```sh
./build.sh --autoinstall
```

**Easiest way to build and run on Linux:** install [FS-UAE](https://fs-uae.net/),
then point the command at your own **A1200 Kickstart 3.1 ROM**:

```sh
./build.sh --autoinstall --autorun-fs-uae \
  --kickstart-file "/path/to/your/kickstart-3.1-a1200.rom"
```

Every finished build also writes, beside the HDF, `AmiWind-FS-UAE-launcher.py`
(run it: it asks for your ROM once and starts FS-UAE), `AmiWind-v<version>-FS-UAE.fs-uae`
and `AmiWind-v<version>-WinUAE.uae`. Without `--kickstart-file` the two configs carry a
placeholder ROM setting to fill in; see [WinUAE setup](docs/WINUAE.md) and the
[FS-UAE launcher](docs/FS-UAE-LAUNCHER.md).

The example ROM path stands for your own ROM file, or for a directory that
contains ROMs. The builder checks FS-UAE and the ROM before setup, fills in the
ROM and HDF paths of the [documented preset](docs/FS-UAE-PLAYTESTING.md), and
launches the finished image. Without `--kickstart-file`, it looks for
`~/.roms/kickstart-3.1-a1200.rom` in your home directory, and then for a file
directly in `~/.roms/` with the known SHA-256. If it still has no ROM, it
**asks for a file or directory**. In a directory it picks the file whose
checksum matches; a different ROM chosen by name is accepted with a warning
that compatibility is unverified. A run without a terminal stops with
instructions when no ROM is selected. ROMs are never downloaded or included.

Next, the tool asks for your Morrowind installation and shows the dependencies
it proposes to install. Once you confirm, it reuses what is already installed,
fetches the missing pinned SDK and map tools, builds the reference QuakeC
compiler if needed, sets up its own Python environment and carries on into the
build. APT may also ask for your sudo password and to confirm packages.
`--autoinstall --plan` shows the setup steps without installing anything.

Start with [Linux build instructions](docs/LINUX_BUILD.md) or
[Windows host options](docs/WINDOWS_BUILD.md). Native Windows/MSYS2 has completed a full
conversion and WinUAE game-entry smoke test; its reliability limits remain
[documented](docs/WINDOWS_BUILD_ROADMAP.md). The Linux Docker builder on WSL 2 has
also completed full conversion and verified HDF assembly. These are separate
host validation results; Linux remains the established build foundation.
The tool accepts your Morrowind installation root, checks required file sizes
and known SHA-256 hashes, and reports dependency versions. Build outputs default
to ignored `out/`.

```sh
./build.sh --install-dependencies --plan
./build.sh --versions
./build.sh --check
```

These commands preview setup and check prerequisites. Follow the linked build
guide to install the required tools and build the playable HDF.

**Build speed:** `--jobs N` sets the exact worker count. While a build runs,
`./build.sh status out/build/NAME` shows its progress, the cores in use and an
ETA; afterwards `./build.sh profile report|compare|optimize out/build/NAME`
shows where the time went and what to parallelize next. Development rebuilds can
reuse unchanged stages with `--reuse-from`. See
[performance options](docs/BUILD_PROFILE.md#performance-options). The numbers of
every build and gate can be kept in one database for comparisons across runs:
[perf database](docs/PERF_DATABASE.md).

A normal build includes everything the release ships; no extra option is
needed. From v0.0.33 the default builder is CHIM, with Balmora and Seyda Neen on
CHIM, both converted from your own data (from v0.0.35 the recorded v0.0.31
Seyda Neen maps, `--seyda-recorded DIR`, are optional and NOT RECOMMENDED since v0.0.31:
the default converts Seyda Neen from your data; which Seyda Neen an image holds:
[docs/LINUX_BUILD.md](docs/LINUX_BUILD.md#which-seyda-neen-is-in-my-build); what fills the disk images and
where their size is going: [docs/IMAGE_SIZE.md](docs/IMAGE_SIZE.md)), and `--builder legacy`
still builds the old way (see
[builder types](docs/chim/build_guide/BUILDER_TYPES.md)). The Vivec Arena preview
of v0.0.32 is withdrawn from v0.0.33 (`--extra-town vivec_arena` still builds it
for testing). Options that leave shipped content out are for debugging only and
say so; see [shipped towns](docs/LINUX_BUILD.md#shipped-towns-default).
For a quick Balmora-only playtest image (a private test, never a release), add
`--miniwind` or a ready-made sandbox such as `--miniwind-balmora-exterior`; see
[MiniWind: the test ground](docs/MINIWIND.md) and the
[build type reference](docs/MINIWIND_PLAYTESTER.md).
For quick test builds of one spot (fewer videos, voices, rooms or NPCs), see the
[CHIM build guide](docs/chim/build_guide/README.md).

**FPU support library (optional, your own copy):** a real 68040 or 68060 needs
`68040.library` or `68060.library` for the rare FPU cases its hardware does not
handle. Add `--amiga-libs DIR` with a folder from your own Workbench or
accelerator installation; the builder copies the library into `LIBS:` on the
boot disk and opens it at start-up. Without it the build continues and the boot
check shows a warning. AmiWind never includes the library; see
[FPU support library](docs/FPU_SUPPORT_LIBRARY.md).

### Run AmiWind in an emulator

Already have a playable HDF? Copy
[`AmiWind-FS-UAE-launcher.py`](tools/AmiWind-FS-UAE-launcher.py) beside it and run
`python3 AmiWind-FS-UAE-launcher.py`. It suggests the newest version, remembers
your ROM, checks its checksum and configures FS-UAE. Use `--yes` for immediate
subsequent launches. See the [launcher guide](docs/FS-UAE-LAUNCHER.md).

The FS-UAE autorun command above handles configuration and launch automatically.
For manual setup or WinUAE, use the guides and steps below.

| Emulator / official homepage | Host platforms | AmiWind setup | Historical v0.0.28-rc1 template |
| --- | --- | --- | --- |
| [FS-UAE](https://fs-uae.net/) | Linux, Windows, macOS | [FS-UAE guide](docs/FS-UAE-PLAYTESTING.md) | [Download/view `.fs-uae` preset](resources/emulators/AmiWind-v0.0.39-rc2-FS-UAE.fs-uae) |
| [WinUAE](https://www.winuae.net/) | Windows | [WinUAE guide](docs/WINUAE.md) | [Download/view `.uae` preset](resources/emulators/AmiWind-v0.0.39-rc2-WinUAE.uae) |

1. Build the current source from your own Morrowind installation using the guide
   above. Keep every HDF listed in the build summary together. The source ZIP
   contains tools and templates; playable images are private build outputs.
2. Install an emulator from its official homepage above. Prefer the matching
   configuration generated beside your HDFs: it lists every required disk. The
   historical rc1 templates above provide a starting point for manual setup.
3. Follow the matching setup guide to select your licensed **A1200 Kickstart
   3.1 ROM** and all the built HDFs. WinUAE uses RDB hardfiles on the UAE
   controller; FS-UAE uses the ROM and HDF paths in its configuration file.
4. Start emulation and click inside the window to capture the mouse. Use
   **WASD** to move and the mouse to look; see [controls and setup](docs/AGA_BUILD.md).

The presets use A1200/AGA, 68040 with FPU, 2 MiB Chip and 16 MiB Z3 Fast RAM,
with JIT and maximum CPU speed. The v0.0.16 playable image was tested with
FS-UAE 3.1.66 on Linux. The Windows checkpoint reached the game in WinUAE 6.0.3
using this hardware profile; see the [test scope](docs/VALIDATION-WINDOWS-2026-10-02.md).
The public [dry-run build](docs/CI_DRY_RUN.md) contains no game assets or ROMs
and boots to a test notice; it is not the playable demo.

## Development

The next work is the rest of the island on CHIM: the open world converted cell by
cell, Vivec back on CHIM and joined to the world, NPC animations and Arena combat.
Build-time profiling and [avoiding unnecessary recompilation](docs/BUILD_TOOLKIT_ROADMAP.md)
remain priorities alongside [the gameplay roadmap](docs/ROADMAP.md) and the
[CHIM features](docs/chim/FEATURES.md) page.

[FAQ](docs/FAQ.md) · [Gallery](docs/GALLERY.md) · [Project state](docs/PROJECT_STATE.md) · [Asset coverage](docs/ASSET_COVERAGE.md) ·
[Open bug reports](docs/BUGS.md) · [Roadmap](docs/ROADMAP.md) ·
[Repository layout](docs/REPOSITORY_LAYOUT.md) · [Release workflow](docs/RELEASE_WORKFLOW.md) ·
[Changelog](docs/CHANGELOG.md) · [Build dependencies](docs/BUILD_DEPENDENCIES.md) ·
[Build/compiler toolkit roadmap](docs/BUILD_TOOLKIT_ROADMAP.md) ·
[Licensing and credits](docs/LICENSING_AND_CREDITS.md)

Thanks to the Morrowind creators, the Amiga community, and the contributors whose
work made this experiment possible. The earlier A500 track, previous methods,
fonts and hand-rendering alternatives remain available in the source and history.

Development changes must follow the [project rules](docs/PROJECT_RULES.md), including required Linux and Windows compatibility.

### Inspect converted geometry locally

The development toolkit now includes a standalone
[Polycount Inspector](docs/POLYCOUNT_INSPECTOR.md). Open
[the local viewer](amiwind-toolkit/map-inspector.html) to explore polygon edges,
optional local base textures and spatial vertex-density hotspots. Isolate an
object, compare components, or inspect from above and export a private planning
polygon. The built-in synthetic scene demonstrates the tool without game assets.

Viewer counts and display filters help investigate geometry; they do not measure
Amiga memory, change the converter or establish a gameplay fix. Your converted
scenes, textures and captures remain private.

Read [Hidden in Dirt: Seyda Neen's graphics performance bottlenecks](docs/HIDDEN_IN_DIRT.md) for measured geometry experiments and the checks behind the next town optimization.

---

<p align="center"><i>AmiWind is brought to you by <a href="https://github.com/FlyingFathead/">FlyingFathead</a></i></p>

The 14 October 2026, 22:19 UTC tracker refresh records offline checks for five
ring-0 ocean frames. Their four original leveled-creature spawns remain deferred.
Runtime placement, native seams and package inclusion are pending, so the map
colours and milestone totals are unchanged.

The 14 October 2026, 23:45 UTC refresh records the expanded Vivec conversion
as 36 original core cells and 28 apron-only dependencies. It retains 6,039
owned references, 33 external dependencies and 297 deferred references.
Global converted and packaged counts are unchanged. Native seams and the
combined candidate remain pending.

The 15 October 2026 Seyda update records the completed offline conversion:
16 original core cells, 20 apron cells, 3,724 stair walks with zero blocking
failures and 532 advisory results. The earlier stair failures remain preserved.
The four Seyda and two Vivec ring-2 overlaps now have offline conversion evidence.
The corrected source carrier passes independent resident, voice and reference
checks. Expanded CHIM integration has two
[actor contact findings](docs/bugs/CHIM-SEYDA-ACTOR-CONTACT-33.md) that remain
after the final bounded refit. Original-height comparison identifies coarse
terrain distortion; repair and native checks remain open.
Runtime placement of the five ring-0 ocean frames, matched native seams and
complete package inclusion remain pending; dev2 has not shipped.
