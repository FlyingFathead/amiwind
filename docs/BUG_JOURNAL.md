# Bug journal

## BUILD-SEYDA-PRIVATE-STAGES-31: duplicate of BUILD-SEYDA-REGEN-30, 8 October 2026

Recorded again while preparing v0.0.31 and closed as a duplicate of
BUILD-SEYDA-REGEN-30; its detail (the three private Seyda stages, the image path not run
end to end since v0.0.29-dev4) is now on that record.
[Report](bugs/BUILD-SEYDA-PRIVATE-STAGES-31.md).

## BUILD-NIGHT-TABLES-31: night lighting tables only on hand-made disks, 8 October 2026

The night lamp, glowing glass and location fog tables reached the playtest
disks by hand; the image builder never wrote them, so repository builds have
dark lamps and no glowing glass. Repaired in source: the image builder writes
and checks all three and records them in its receipt; the window table matches
the private dev5 table byte for byte on the same inputs.
[Report](bugs/BUILD-NIGHT-TABLES-31.md).

## BUILD-FINALIZE-SCENE-31: undefined name in image finalisation, 8 October 2026

Found reading `finalize_image`: since v0.0.29-dev4 the media step uses
`scene`, which only `image()` defines, so the image build would stop with a
`NameError` before media staging. Repaired in source (one line); a full image
build is pending. [Report](bugs/BUILD-FINALIZE-SCENE-31.md).

## DBG-TOGGLE-WORDS-31: on/off words for settings, 8 October 2026

`dbg fog on` turned the fog off: settings read "on" as 0. Toggle words now
become 1/0 for settings. [Report](bugs/DBG-TOGGLE-WORDS-31.md).

## TOWN-VIS-OCCLUSION-31: buildings do not block visibility, 7 October 2026

Measured from the dev5 maps: 94 % of Balmora's faces are in `func_wall`
building models, which Quake's `vis` ignores, so 84-89 % of a Balmora map is
potentially visible from an average spot (Seyda Neen 73 %). Occluder blocks
are planned. [Report](bugs/TOWN-VIS-OCCLUSION-31.md),
[performance page](performance/TOWN-VISIBILITY.md).

## LAMPS-FLICKER-31 and SEYDA-LANTERNS-MISSING-31: dev5 night walk, 7 October 2026

Owner, dev5: lamp light keeps switching on and off while turning or walking
(our dev5 front priority; repaired in source with lamp stickiness and fade-out),
and Seyda Neen walls are lit by lanterns that are not in its maps.
[Report](bugs/LAMPS-FLICKER-31.md), [report](bugs/SEYDA-LANTERNS-MISSING-31.md).

## BUILD-WINDOWS-DOCKER-SLOW-31: Docker disk steps on Windows, 7 October 2026

Measured 225 MB/s from a container into a Windows folder against about
1.9 GB/s for a native Windows copy; playtest builds move several 5.6 GB disk
images that way. Large copies move to the host and container scratch to a
Docker volume. [Report](bugs/BUILD-WINDOWS-DOCKER-SLOW-31.md).

## NIGHT-0400-DARK-31: sudden darkness near 04:00, 7 October 2026

Owner, dev4 in Balmora: the exterior turns much darker at about 04:00. Cause
unknown; a 03:30-04:30 time sweep is being measured.
[Report](bugs/NIGHT-0400-DARK-31.md).

## GUARD-TORCH-BRIGHT-31 and LAMPS-RANGE-31: Balmora at night, 7 October 2026

Owner, dev4: guard torches outshine the lamps, and lamps switch on and off like
motion detectors while walking. Guard torches now light half as far. Lamps ahead
of the view now win the few light slots, and newly chosen lamps fade in. The
repair is baking the lamps into the maps on a night lightstyle.
[Report](bugs/GUARD-TORCH-BRIGHT-31.md), [report](bugs/LAMPS-RANGE-31.md).

## LAMPS-RANGE-31: only the nearest lamps light up, 7 October 2026

Owner, dev4 in Balmora: distant lamps stay dark until approached. The night
lamps light only the nearest two. [Report](bugs/LAMPS-RANGE-31.md).

## SEYDA-BLOCK-31 and PLACE-NAMES-INTERIOR-31: dev3 playtest, 7 October 2026

Owner: an invisible obstacle on a Seyda Neen slope stops the walk toward an NPC;
interiors show no town or building name. The autosave message also covers the
title (HUD-NOTIFY-OVERLAP-31). [SEYDA-BLOCK-31](bugs/SEYDA-BLOCK-31.md),
[PLACE-NAMES-INTERIOR-31](bugs/PLACE-NAMES-INTERIOR-31.md).

## DLIGHT-WALLS-31: cause is the night remap, 7 October 2026

Walls do receive torch light (native run on the shipped map); the outdoor night
remap darkened it with everything else. Light-space night becomes the default in
dev4. [Report](bugs/DLIGHT-WALLS-31.md).

## MUSIC-OPENING-CLIP-31: title clip during the opening load, 7 October 2026

Owner, dev3: a clip of another track plays while the ship loads. The map load
resumes the paused title stream during the new opening hold. Repaired in source.
[Report](bugs/MUSIC-OPENING-CLIP-31.md).

## MUSIC-STARTUP-TRACK-31: random track under the startup logo, 7 October 2026

Owner, dev3 in WinUAE: a random soundtrack piece plays during the logo. My
AUDIO-LOGO-31 change removed the switch to the title that had hidden the random
start-up track. Repaired in source. [Report](bugs/MUSIC-STARTUP-TRACK-31.md).

## DLIGHT-WALLS-31: torches light the ground but not town walls, 7 October 2026

Owner report; the headlamp barely changes Balmora wall views (0.1-1.9 luma)
while it lights the ship. Investigating. [Report](bugs/DLIGHT-WALLS-31.md).

## OPENING-BRIGHT-31: ship hold brighter than the original, 7 October 2026

Owner: the opening is too bright. Measured against OpenMW at the same poses:
AmiWind 1.2 to 2.5 times brighter. [Report](bugs/OPENING-BRIGHT-31.md).

## HORIZON-HOLES-31: distant Balmora breaks up against the sky, 7 October 2026

Owner screenshots: far buildings are a fogged silhouette with holes. Far culling
drops parts of buildings; the distant fill draws only land. Needs work.
[Report](bugs/HORIZON-HOLES-31.md).

## HUD-NOTIFY-OVERLAP-31: console line over the title, 7 October 2026

Owner screenshot: the heap audit message printed over the debug title.
[Report](bugs/HUD-NOTIFY-OVERLAP-31.md).

## LIGHT-OFF-31: Off-by-default lights would bake as lit, 7 October 2026

Checking whether any original light follows a time of day (none does), found
the Off-by-default flag unread by the bake. No shipped map affected; repaired
in source with unit tests. [Report](bugs/LIGHT-OFF-31.md).

## LIGHT-FALLOFF-31 correction; LIGHTMAP-GRID-31, 7 October 2026

My measuring script read placed objects in model-local coordinates, so the
claim that the opening lantern bakes no light was wrong: the map is lit around
it. The falloff difference stands. Found instead: some baked lightmaps are one
sample row or column off the engine grid (double vs single precision).
[LIGHT-FALLOFF-31](bugs/LIGHT-FALLOFF-31.md), [LIGHTMAP-GRID-31](bugs/LIGHTMAP-GRID-31.md).

## LIGHT-FALLOFF-31 and BALMORA-LAMPS-DIM-31: OpenMW reference, 7 October 2026

OpenMW at the owner poses: the ship lantern in view is light_com_lantern_02_200_Boat
(the _64 one is on the deck above); the original hold is very dark (luma 11-16).
Balmora: the original street lantern glows and lights the wall below it. Owner:
Seyda Neen also has no lamp light at night; exteriors carry no lamp light at all.
[LIGHT-FALLOFF-31](bugs/LIGHT-FALLOFF-31.md), [BALMORA-LAMPS-DIM-31](bugs/BALMORA-LAMPS-DIM-31.md).

## SEYDA-WALL-SHAPE-31: likely a tree card drawn through a wall, 7 October 2026

Ray-cast of the reported pose: the dark shape matches the trunk base of a
camera-facing tree card standing 230 units behind the wall, depth-tested at
the tree's centre. Same in v0.0.30; in-game capture pending.
[Report](bugs/SEYDA-WALL-SHAPE-31.md).

## BALMORA-LAMPS-DIM-31, NIGHT-RUST-31, EMISSIVE-UNSHIPPED-31: causes measured, 7 October 2026

Balmora lamps: exterior lamps are never baked into light, the lamp glass is not
emissive in the shipped maps (only bmtemple has an emissive texture), and the
night remap darkens the finished frame including any light. The rust speckle is
the night remap rounding near-black colours to a rust palette entry.
[BALMORA-LAMPS-DIM-31](bugs/BALMORA-LAMPS-DIM-31.md), [NIGHT-RUST-31](bugs/NIGHT-RUST-31.md),
[EMISSIVE-UNSHIPPED-31](bugs/EMISSIVE-UNSHIPPED-31.md).

## LIGHT-NEGATIVE-31: negative lights bake as white, 7 October 2026

Identifying the Census office fireplace: the original darkens its left corner
with dark_128 (Negative flag); the bake ignores flags and adds it as white.
[Report](bugs/LIGHT-NEGATIVE-31.md).

## BALMORA-LAMPS-DIM-31: Balmora lamps nearly black at night, 7 October 2026

Owner, dev2 playtest at 22:21: a Balmora street lamp and its surroundings are
almost black. Cause unknown; investigating.
[Report](bugs/BALMORA-LAMPS-DIM-31.md).

## SEYDA-WALL-SHAPE-31: shape in a Seyda Neen wall, 7 October 2026

Owner, dev2 playtest: a dark shape pokes out of a stone wall near the shore at
global -10474 -73437 135; not seen before. Cause unknown; investigating.
[Report](bugs/SEYDA-WALL-SHAPE-31.md).

## LIGHT-FALLOFF-31: the opening lantern bakes no light, 7 October 2026

Owner, dev2 opening scene: the lantern hanging above the start gives no light.
Measured: it is the original `light_com_lantern_02_64` (radius 16 local units);
the nearest surface is 27 units away and the bake stops every light at its
radius, where the original falls off as radius/(3d). All samples near it are
the cell ambient (64). Open; OpenMW A/B in progress.
[Report](bugs/LIGHT-FALLOFF-31.md).

## SEYDA-READ-SLOW-31: owner playtest of dev2, 7 October 2026

Owner, playing v0.0.31-dev2: Seyda Neen is fast now. Owner-observed; acceptance
pending. [Report](bugs/SEYDA-READ-SLOW-31.md).

## AUDIO-03 and AUDIO-LOGO-31: music started under disk-heavy moments, 7 October 2026

Owner, WinUAE: the music still crackles right after the intro video, and also
while the startup logo plays. Both music starts coincided with heavy disk reads
(the ship map load; the streamed logo video). Repair in source: the ship scene
holds until loaded and settled, then the music starts; the title music starts
after the main menu appears. Not yet packaged or heard.
[AUDIO-03](bugs/AUDIO-03.md), [AUDIO-LOGO-31](bugs/AUDIO-LOGO-31.md).

## TRACKER-MAP-BLANK-31: world progress map went blank on hover, 7 October 2026

The owner saw the new map viewer draw and then go blank in Firefox: the hover
tooltip resized (and so cleared) the canvas on every mouse move. Fixed before
the viewer was committed; owner confirmed. [Report](bugs/TRACKER-MAP-BLANK-31.md).

## SEYDA-READ-SLOW-31: 16 KiB file buffer repairs and beats it, 7 October 2026

Narrowed to the build that added ember particles, but not to the embers
themselves: the slowdown sits in the C library's buffered reads. A 16 KiB
buffer when a game file is opened (default 1 KiB) halves map read time; dev1
Seyda crossings 0.70-0.91 s -> 0.39-0.48 s. In source; a 10-15 % gap stays
open. [Report](bugs/SEYDA-READ-SLOW-31.md),
[lessons](performance/LESSONS_LEARNED.md).

## SEYDA-READ-SLOW-31: dev1 crossings read slower than the test image, 7 October 2026

The dev1 boot check measured Seyda Neen crossings 0.10-0.21 s slower than the
earlier test image with the same maps, all of it in read time. Still faster
than v0.0.30. Cause unknown; engine and disk-layout A/B running.
[Report](bugs/SEYDA-READ-SLOW-31.md).

## GATE-EMBERS-31: ember commit failed the dev1 gates, 7 October 2026

The v0.0.31-dev1 gates found a blank line at the end of `d_iface.h` and three
native torch tests that no longer linked: the new ember calls had no test
stand-ins. Repaired in source before packaging.
[Report](bugs/GATE-EMBERS-31.md).

## SEYDA-LOAD-HANG-30: the hung read is the music stream, 7 October 2026

Disassembly of the matching unstripped build places the freeze's return
address directly after `fread` in the music stream reader (`refill`, called
from `CDAudio_Update`), not in the map loader. The earlier function name came
from a lookup that missed static functions and is withdrawn.
[Report](bugs/SEYDA-LOAD-HANG-30.md).

## CI-HOSTDEPS-30: host CI job failed on the first v0.0.30 push, 7 October 2026

The hosted `host-launcher-parity` job failed: flame extraction asked for the
NIF reader for a synthetic non-NIF test model, and that job installs only
numpy and Pillow. Not tagged or released. Repaired in source; the host tests
now also run in a reduced environment before every handoff.
[Report](bugs/CI-HOSTDEPS-30.md).

## v0.0.30-rc1 owner playtest summary, 7 October 2026

WinUAE playtest by the owner: Census office interiors work
(CENSUS-ENTITIES-30 accepted), mushroom picking on the road to Balmora works,
Balmora works and torches work. Open from the same playtest, all WinUAE music
crackles or pauses at transitions: AUDIO-NEWGAME-30, AUDIO-03,
AUDIO-ENTER-29, AUDIO-APPEARANCE-29, AUDIO-LOAD-29. Character attributes and
the papers reader (no disk loads) stay clean.

## CENSUS-ENTITIES-30: owner-accepted in v0.0.30-rc1, 7 October 2026

Owner WinUAE playtest of v0.0.30-rc1: the Census and Excise Office interiors
work. Same playtest: small music clicks on the pier at head selection and on
Choose/OK (AUDIO-APPEARANCE-29) and small crackles entering the Census office
(AUDIO-LOAD-29); both open.

## AUDIO-NEWGAME-30: rc1 playtest audio reports, 7 October 2026

v0.0.30-rc1 WinUAE playtest by the owner: music crackles when confirming New
Game (new, [report](bugs/AUDIO-NEWGAME-30.md)); crackles as the game fades in
after the intro (AUDIO-03); a split-second pause on Enter to follow the guard,
which worked in earlier versions (AUDIO-ENTER-29, regression); heavy crackling
from the ship's hull to the deck (AUDIO-LOAD-29). All open; tracked for after
v0.0.30.

## CENSUS-ENTITIES-30: misplaced objects in the Census and Excise Office, 7 October 2026

1. Symptom (v0.0.30-dev5 playtest): an upright rug on the upper floor whose
   lower half shows as a black hole in the ceiling below, and a tapestry
   inside a bookshelf. The fireplace and its flames are correct.
2. Cause: the dev5 lighting rebuild kept an older object list (v0.0.29) on
   top of geometry from the dev3 rebuild, which had added one object. Every
   later object pointed at its neighbour's model: 67 of 140.
3. Introduced in v0.0.30-dev5; dev4 was correct. Only the Census map; the
   rebuilt Temple's numbering matches.
4. Fix: the dev4 object list plus dev5's flames; all 140 objects point at the
   same models as in dev4, and the geometry is unchanged. The rebuild step now
   stops if any object's model number differs from the rebuilt geometry.
5. Shipped in v0.0.30-rc1. [Details](bugs/CENSUS-ENTITIES-30.md).

## SEYDA-LOAD-HANG-30: rare freeze during a Seyda Neen region load, 7 October 2026

1. Symptom: in about 5 of 70 automated FS-UAE runs of the Seyda Neen test
   route the game stopped during a region load; the screen froze and quit was
   ignored. Not yet reported in manual play.
2. Reproduction: scripted route seyda-east-y-300 under FS-UAE 3.1.66 with the
   console debugger; v0.0.30-dev4 and dev5 engines.
3. Evidence: every CPU sample was the idle loop. The game task waited on the
   DOS signal inside a read (`fread` -> dos.library `Read` -> exec `Wait`); its
   reply port was empty and the file-system handlers were idle.
4. Cause: open. A read request or its reply was lost below the engine (file
   system handler or emulator disk layer); not an engine loop.
5. Not tied to host disk load: 0 freezes in 12 runs with a 4 GB copy running.
6. Status: open, no fix. Next: name the calling engine function and check the
   emulator log at the moment of the freeze.
7. Shipped: present in v0.0.30 if it is a real game fault.

## BUILD-SEYDA-REGEN-30: public build cannot regenerate Seyda Neen, 7 October 2026

Reproduced 7 October 2026: running the partition on the original v0.0.29 inputs
stops with the message below. `build_aga.py image` calls the Seyda partition
without a canonical terrain source while `config/terrain-visual-cull.json`
enables culling by default, so the partition stops with "Enabled Seyda culling
requires --canonical-land-source". The shipped sub-cells were finished by
terrain steps outside the repository; v0.0.29 reused them unchanged. Next:
bring the missing steps into the public build.

## INTRO-ROLES-30: crash on a region change, 7 October 2026

`NUM_FOR_EDICT: bad pointer` on a Seyda Neen sub-cell load. The opening
sequence kept actor pointers across a map reload; one pointed past the new
entity list. Repaired by validating role pointers before use. Scripted route:
dev3 crashed 2/2, repaired engine 0/3. [Details](bugs/INTRO-ROLES-30.md).

## CONVERTER-ROOT-ROTATION-30: same cause in more maps, 7 October 2026

The root-rotation converter bug behind the Temple also turned Velothi kit walls
in Tharys Ancestral Tomb (see-through holes) and `in_nord_fireplace_01` in five
Seyda Neen interiors (fireplace facing away). All six maps are rebuilt; only
the root-rotated meshes changed. One Balmora exterior placement is pending.
[Details](bugs/CONVERTER-ROOT-ROTATION-30.md).

## BALMORA-TEMPLE-GEOMETRY-29: cause found, 7 October 2026

The Temple's missing and edge-on walls, see-through holes and floating objects
come from the scenery converter applying each mesh's NIF **root node rotation**.
Morrowind ignores that rotation (it keeps root translation and scale), and the
Velothi kit pieces carry a 90-degree root yaw, so they were turned a quarter
turn. Earlier audits compared geometry flattened by the same converter and
could not see it. Candidate repair: ignore the root rotation in
`model_geometry`; regression `tests/test_scenery_root_transform.py`. The
rebuilt Temple matches OpenMW at the reported views in FS-UAE; only the five
root-rotated models changed. Other converted maps with root-rotated meshes:
Tharys Ancestral Tomb and the fireplace interiors. Not shipped; first fixed
version pending. [Details](bugs/BALMORA-TEMPLE-GEOMETRY-29.md).

Entries before 7 October 2026 are in
[the v0.0.29 bug journal](journals/BUG_JOURNAL-v0.0.29.md).
