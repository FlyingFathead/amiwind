# Bug journal

## HEAP-SEYDA-OVERLAP-32: temporary pre-CHIM heap bypass for three Seyda Neen maps, 8 October 2026

The from-scratch build dev3-r2 stopped at the strict heap gate on the recorded maps sn019, sn026
and sn035 (modelled reserve allowance only, worst -238,180 bytes). Owner decision A: v0.0.32 ships
them through a temporary pre-CHIM bypass, `config/heap-bypass.json` (name and SHA-256, legacy
builder only), recorded in the heap receipts and `build.json`; a temporary bypass for the legacy
builder, removed when Seyda Neen moves to CHIM (M2). Everything else stays strict.
[Report](bugs/HEAP-SEYDA-OVERLAP-32.md).

## Morrowind collision census, 8 October 2026

Where Morrowind keeps its collision and how the converter uses it:
[COLLISION_MESHES.md](COLLISION_MESHES.md). 2,680 of the base game's 5,798 NIFs carry an authored
`RootCollisionNode`; the authored collision of every measured stair is a ramp of at most 45
degrees. New: [COLLISION-RCN-SCOPE-32](bugs/COLLISION-RCN-SCOPE-32.md) (the Seyda Neen exterior
and every non-`i/` model in converted rooms collide with their visual mesh, not the authored
collision) and [COLLISION-NC-FLAGS-32](bugs/COLLISION-NC-FLAGS-32.md) (NC, NCC, MRK and AvoidNode
flags are ignored, so banners, tapestries, rugs and similar props are solid).

## First FS-UAE session of Balmora under CHIM, 8 October 2026

On the five benchmark cameras CHIM draws far fewer world faces and clip nodes than the legacy maps
and roughly halves the frame time (JIT, busy host, relative), and doors work both ways
([CHIM-VIEW-FACES-33](bugs/CHIM-VIEW-FACES-33.md)). New:
[CHIM-TEXTURE-SPECKS-33](bugs/CHIM-TEXTURE-SPECKS-33.md) (bright single-texel specks in CHIM
textures), [CHIM-ZONE-RING-THRASH-33](bugs/CHIM-ZONE-RING-THRASH-33.md) (the ring does not fit
the 6 MiB zone; 64 failed frame-world rebuilds).

## Vivec Arena arrival and owner dev1 reports, 8 October 2026

[VIVEC-ARENA-TP-ARRIVAL-32](bugs/VIVEC-ARENA-TP-ARRIVAL-32.md): cause found and fixed in source
(branch v0.0.32-vivec-arrival). The Arena arrival starts inside the Waistworks entrance top; in
dev1 the canton's convex fill blocked every nearby spot, and Quake's stuck recovery then moved the
player to the stale `oldorigin` 0 0 0, the frame origin under the sea. Arrivals are now stored as
the engine search's standing spot on the converted collision (every town), the engine falls back
to the scene spawn point and never to water, `dbg unstuck` finds the nearest clear spot, and the
image step checks every town arrival on the final maps. The owner's other dev1 Arena reports
(floating outflow, missing exterior, stairs, stuck walkway, noclip refused, hanging pieces,
St. Delyn without walls) are the two causes of
[VIVEC-ARENA-ACTORS-32](bugs/VIVEC-ARENA-ACTORS-32.md), already fixed in source; no mirrored
placement is involved. New: [VIVEC-ARENA-FRAME-EDGE-32](bugs/VIVEC-ARENA-FRAME-EDGE-32.md)
(neighbouring canton bodies end at the frame edge, in view).

## TEST-PROFILE-SECTION-CPU-32, 8 October 2026

The full gate failed one build profile test on a loaded host: two 0.05 s section calls read
0.08 s because `os.times()` counts whole clock ticks. The test now allows for the tick
resolution. [Report](bugs/TEST-PROFILE-SECTION-CPU-32.md).

## BUILD-EXTRA-TOWN-OPTIN-32: the Vivec Arena preview leaves the default build, 8 October 2026

Found by the CHIM builder's payload measurement of v0.0.32-dev1: the Arena that v0.0.32 ships
was built only with `--extra-town vivec_arena`, and the payload check found 19 Arena files no
release feature explains. Fixed in source: towns marked `shipped_since` in `config/towns.json`
are built by default (`--no-extra-town` / `--only-core-towns` debugging opt-outs), a release
feature `extra-towns` follows the town table, and the v0.0.32 classes are recorded.
[Report](bugs/BUILD-EXTRA-TOWN-OPTIN-32.md).

## KEYS-AMIGA-EDIT-32: Del arrived as F11, FS-UAE Home/End as keypad ( and Help, 8 October 2026

Found while adding terminal editing to the console. The raw-key table read the Amiga Del key as
F11, so the documented "Delete clears a control" never worked; FS-UAE sends a PC keyboard's Home
and End as keypad `(` and Help, and Insert as the key left of Return (read as Enter). Fixed in
source: Del is Delete, and the FS-UAE presets send Home/End as unused keys 0x6A/0x6C that the game
reads as Home/End. Insert unchanged and documented. [Report](bugs/KEYS-AMIGA-EDIT-32.md).

## BUILD-DRESSING-EXCLUDED-32: Census office lantern hook, silent converter drops, 8 October 2026

The one entity v0.0.32-dev1's Census office lacks against v0.0.31 is a lantern hook (reference
321381). The mesh converter skips lantern hooks, ropes and similar dressing unless the caller retains
dressing, without listing them in the receipt; v0.0.31's census was not builder-made. The entity
tracker did not fail: the guided build passed no baseline and its gate tolerated small losses.
Prevention in source: every omission receipted; per-cell placement digests; the v0.0.31 release
baseline is compared by default. Owner decision A: the Seyda Neen interiors keep their dressing
(six pieces back: two lantern hooks, two ferns, two grass tufts), `--skip-dressing` keeps the
earlier rule, and `dressing-track.json` lists every placed piece per map with its heap estimate.
[Report](bugs/BUILD-DRESSING-EXCLUDED-32.md).

## AW-20260928-01: ship-to-deck transition sluggish again, 8 October 2026

Owner report on dev1/dev2 (FS-UAE 3.1.66, Ubuntu 24.04): "scene clearing from prison ship to the
deck; sometimes on FS-UAE seems absolutely sluggish". Same transition as the September hatch
freeze; cause unknown. Next: measure the "Scene ready" time and bytes read, cold and warm, on dev3.
[Report](bugs/AW-20260928-01.md).

## CONSOLE-HISTORY-ARROWS-32: owner trace shows the arrows arriving, 8 October 2026

The owner's `aw_input_trace 1` on dev1: Up and Down reach the game as raw 76 and 77 with qualifier
32768 (mouse grabbed). The same keys, order and qualifier in FS-UAE on dev1 recall history, and a
native replay passes, so neither the qualifier nor the emulator is the cause on his machine. Most
likely the empty-line state of CONSOLE-HISTORY-EMPTY-32 (fixed in source); to be checked on the
next build. A keyboard joystick on port 1 would swallow the arrows (no trace line); all shipped
presets set `joystick_port_1 = none`. [Report](bugs/CONSOLE-HISTORY-ARROWS-32.md).

## FLAME-RANGE-NEAREST-32: Census office hearth fire only up close, 8 October 2026

Owner report on dev1: the Census and Excise Office fireplace shows no fire until the player is right
next to it. The static flame budget (12 flames within 640 units) took the nearest flames in any
direction; 14 candles, 10 of them behind the camera, were nearer than the hearth. Same in v0.0.31
(identical flames and code). Repaired in the engine: flames on screen, ranked by drawn size over
distance; the earlier rule stays as `aw_static_flames_nearest 1`.
[Report](bugs/FLAME-RANGE-NEAREST-32.md).

## CHIM parity and terrain hull fixes; test import path, 8 October 2026

Fixed in source on the CHIM branch, not merged:
[CHIM-PAYLOAD-PARITY-33](bugs/CHIM-PAYLOAD-PARITY-33.md) (Balmora 1,473 statics, two-way frame-map
gate passes; two open requirements: frame origin and harvest representation) and
[CHIM-TERRAIN-HULL-BEVELS-33](bugs/CHIM-TERRAIN-HULL-BEVELS-33.md) (exact standing hull, tighter
seam check, format stays 0.4). [TEST-WORKER-SYSPATH-32](bugs/TEST-WORKER-SYSPATH-32.md): a second
case in the test process itself makes `test_actor_ground` fail to import after modules that put
`tools/` before `src/`.

## Vivec dev1 owner evidence and CHIM terrain edges, 8 October 2026

Owner evidence from real play of dev1: a Vivec canton sewer outflow floats without its canton
(the frame-by-origin bug, fixed in source by the footprint rule:
[VIVEC-ARENA-ACTORS-32](bugs/VIVEC-ARENA-ACTORS-32.md)), and `dbg tp vivec_arena` always lands at
the frame origin under the water, a v0.0.32 blocker
([VIVEC-ARENA-TP-ARRIVAL-32](bugs/VIVEC-ARENA-TP-ARRIVAL-32.md)). New:
[CHIM-TERRAIN-HULL-BEVELS-33](bugs/CHIM-TERRAIN-HULL-BEVELS-33.md) (a standing box rests up to 8
units above convex CHIM terrain edges). Feature in progress, not a bug: `dbg daynight off`/`on`
to freeze the time at midday (owner request).

## CHIM harvest and payload parity findings, 8 October 2026

The CHIM Balmora statics match the pre-image region maps, but the image step later removes 20
harvest mushroom statics and adds 5 town flora references that the CHIM world does not see; a
per-area parity gate is in progress. A town-wide CHIM harvest catalogue would break the name and
size limits, so CHIM keeps the per-region catalogues. Frame maps carry only worldspawn, the
`aw_npc` entities and one `info_player_start`. New:
[CHIM-PAYLOAD-PARITY-33](bugs/CHIM-PAYLOAD-PARITY-33.md),
[CHIM-HARVEST-NAMING-33](bugs/CHIM-HARVEST-NAMING-33.md). Updated:
[CHIM-FRAME-WORLD-BOUNDS-33](bugs/CHIM-FRAME-WORLD-BOUNDS-33.md).

## BUILD-SEYDA-RECORDED-REWRITTEN-32: traced and repaired in source, 8 October 2026

The dev1 rewrites of the recorded Seyda Neen maps were the actor ground bake (one placement,
reference 128961, re-fitted by 0.0067 units in 64 region maps) and the builder's fallback-alias copy
over `seyda.bsp`; the sky and hidden-surface passes left them unchanged. The exception is now the
builder option `--seyda-recorded` (`tools/recorded_stage.py`, pinned by
`config/seyda-recorded-v0.0.31.json`): later passes skip the recorded maps and a check after every
map pass stops the build on any difference. `seyda.bsp` ships as the sn029 alias, the one named
difference (owner option A: the complete town fails the release actor gate).
[Report](bugs/BUILD-SEYDA-RECORDED-REWRITTEN-32.md).

## HORIZON-FLORA-SPRITES-32: cause measured, land-outline horizon default, 8 October 2026

The Seyda Neen castle and wall are the skyline fill (`aw_skyline_fill`, added in v0.0.31-dev5,
shipped on in v0.0.31): sky below far fogged scenery takes the fog colour. The v0.0.31 engine draws
the same at both owner poses on the same data; `aw_skyline_fill 0` removes the columns. The game
config now selects 0, `aw_horizon_migrate` resets saved configs once, and the silhouetting stays
selectable: experimental and buggy (sprites need their shapes from the alpha channel), tested but
subpar results, kept for future improvement. [Report](bugs/HORIZON-FLORA-SPRITES-32.md).

## FOG-TOWN-HEAVY-32: fog settings identical to v0.0.31, 8 October 2026

`fog-locations.txt`, the game configs, palette, fog and sky lookups and the 540 town fog distance
equal v0.0.31; location fog is off by default. The Seyda Neen silhouettes are the skyline fill
(HORIZON-FLORA-SPRITES-32). The Arena canton is larger than the 540 fog band (HORIZON-HOLES-31); a
longer Arena distance is an owner decision. [Report](bugs/FOG-TOWN-HEAVY-32.md).

## HORIZON-FLORA-SPRITES-32: owner decisions and planned improvements, 8 October 2026

The v0.0.31 horizon system is the default again; the silhouetting stays as an alternative mode,
documented as "tested but subpar results", and is not removed (the owner sees potential in it).
Planned: the skyline fill must not let the topography show through, and sprites become
silhouettes of their actual form (alpha honoured) instead of solid blocks or columns.
[Report](bugs/HORIZON-FLORA-SPRITES-32.md).

## CONSOLE-HISTORY-ARROWS-32: console arrows recall nothing on the owner's FS-UAE, 8 October 2026

Owner report on dev1, FS-UAE on Ubuntu 24.04: Up and Down do nothing in the console; keypad 8 and
2 type digits (expected: the Amiga keypad has no cursor keys). Not reproduced: the dev1 image in
FS-UAE 3.1.66 on Linux with the shipped preset recalls history in the menu console, the ship and
Vivec Arena, and the dev2 smoke test recalls it too. The key path and the FS-UAE preset are
unchanged since v0.0.31. Next: `aw_input_trace 1` on the owner's machine shows whether the arrows
reach the game. [Report](bugs/CONSOLE-HISTORY-ARROWS-32.md).

## CONSOLE-HISTORY-EMPTY-32: Up past the oldest command sticks on an empty line, 8 October 2026

Found during CONSOLE-HISTORY-ARROWS-32, inherited from Quake's `Key_Console`: Up past the oldest
command jumped to an empty slot and stayed there until Down, and the history position survived
closing and reopening the console. Fixed in source: Up keeps the oldest command and each open or
close starts from the newest. Native raw-key test; fails on the old code; not yet packaged.
[Report](bugs/CONSOLE-HISTORY-EMPTY-32.md).

## HORIZON-FLORA-SPRITES-32: horizon silhouetting, not yet perfect, 8 October 2026

Owner report on dev1: the horizon is meant to follow the highest topography, and the sprite trees
break it (partly the owner's own call; not a v0.0.32 blocker). Two owner screenshots near Seyda
Neen show a canopy-like fog-coloured silhouette behind the town and a fog-coloured wall of spikes,
both gone up close. Working hypothesis: fully fogged flora sprites drawn beyond the solid-fog
distance. A selectable return of the previous behaviour is in preparation; no method is removed.
Linked from [FOG-TOWN-HEAVY-32](bugs/FOG-TOWN-HEAVY-32.md).
[Report](bugs/HORIZON-FLORA-SPRITES-32.md).

## BUILD-HEAP-RECEIPT-TUPLES-32: dev2 image step refused its final heap receipt, 8 October 2026

After about 20 minutes the dev2 image step stopped: the heap audit's harvest fingerprint entries
were tuples in memory and lists in the saved receipt (389 differences on the dev2 maps). Fixed in
source (2ca08b5) with a round-trip test. GATE-SHARED-SOURCE-32 updated: concurrent gates verified,
temporary space and engine build folder follow-ups fixed.
[Report](bugs/BUILD-HEAP-RECEIPT-TUPLES-32.md).

## Vivec Arena residents, 8 October 2026

[VIVEC-ARENA-ACTORS-32](bugs/VIVEC-ARENA-ACTORS-32.md): cause found and fixed in source (branch
v0.0.32-arena-actors). Three residents stood on neighbouring canton walkways the frame dropped
because their origin lies outside it; two stood on the Arena canton's lower walkway, buried under
convex collision. The frame now keeps objects whose footprint reaches in, and exterior
architecture keeps its authored collision surfaces when the convex proxy closes more than a step.
The actor gate passes without the waiver; Balmora maps and every non-Arena audit row are
unchanged. New: [COLLISION-CONVEX-LOSS-32](bugs/COLLISION-CONVEX-LOSS-32.md) (convex proxies lose
surfaces up to 107 units and close space elsewhere). Updated:
[CONVERT-COLLISION-FALLBACK-32](bugs/CONVERT-COLLISION-FALLBACK-32.md) (Vivec canton shells fall
back too), [VIVEC-ARENA-TP-ARRIVAL-32](bugs/VIVEC-ARENA-TP-ARRIVAL-32.md) (the arrival point
starts inside the standing hull of the Waistworks entrance top).

## GATE-SHARED-SOURCE-32: local gate tested the main checkout, 8 October 2026

The local integration gate staged the main checkout into one shared folder whatever branch it was
asked to gate, and concurrent gates collided there (one engine step failed with `FileExistsError`).
Fixed in the local gate runner: a repository selector, per-gate staged sources and temporary
folders, no reused gate numbers, and a report header naming the repository and commit. Branch
gates reported earlier that day from worktrees may have tested the main line; merges were gated
again on the merged main line. Follow-up: the per-gate temporary folders are never removed and
filled the build container's temporary space, so later gates failed with empty logs.
[Report](bugs/GATE-SHARED-SOURCE-32.md).

## Image-parallel follow-ups merged, 8 October 2026

Fixed in source on the v0.0.32 development line, not yet shipped (state stays open):
[BUILD-LIGHT-THREADS-32](bugs/BUILD-LIGHT-THREADS-32.md) (one light thread for every map through
one helper; maps lit with several threads before now differ from earlier builds, expected in
from-scratch comparisons), [BUILD-HAND-CATALOG-SERIAL-32](bugs/BUILD-HAND-CATALOG-SERIAL-32.md),
[ACTOR-AUDIT-ORDER-32](bugs/ACTOR-AUDIT-ORDER-32.md). Partly:
[BUILD-IMAGE-UNDERUSED-32](bugs/BUILD-IMAGE-UNDERUSED-32.md) (cull 186.5 s to 83.1 s, parallel
readback; guard torches still serial). The build profiler records host load per stage
([BENCH-SESSION-DRIFT-32](bugs/BENCH-SESSION-DRIFT-32.md)).

## v0.0.32-dev1 delivery and smoke test findings, 8 October 2026

The recorded Seyda Neen maps are rewritten by later image passes (high priority for v0.0.32 final),
the Arena and Balmora are heavily fogged, the world disk image is just over 2 GiB and the static
emulator templates lack the world disk. New:
[BUILD-SEYDA-RECORDED-REWRITTEN-32](bugs/BUILD-SEYDA-RECORDED-REWRITTEN-32.md),
[FOG-TOWN-HEAVY-32](bugs/FOG-TOWN-HEAVY-32.md),
[WORLD-HDF-OVER-2GIB-32](bugs/WORLD-HDF-OVER-2GIB-32.md),
[EMULATOR-TEMPLATES-WORLD-32](bugs/EMULATOR-TEMPLATES-WORLD-32.md). Updated:
[BUILD-SEYDA-REGEN-30](bugs/BUILD-SEYDA-REGEN-30.md) (report page written; the exception must be
honoured byte for byte), [WORLD-THIRD-PARTITION-32](bugs/WORLD-THIRD-PARTITION-32.md) (WinUAE DW2
untested), [HORIZON-HOLES-31](bugs/HORIZON-HOLES-31.md) (Arena),
[CONVERT-DEGENERATE-FACES-32](bugs/CONVERT-DEGENERATE-FACES-32.md) (non-convex faces in Balmora
collision unions). From the CHIM format 0.3 statistics:
[CHIM-VIEW-FACES-33](bugs/CHIM-VIEW-FACES-33.md) (heavy models) and
[CHIM-LEAF-SPAN-33](bugs/CHIM-LEAF-SPAN-33.md) (160 placements always sent).

## v0.0.32-dev1 playtest findings, 8 October 2026

The dev1 playtest payload lacks the hands and harvest of v0.0.31 (built from a snapshot before
those builder steps; no packaging coverage gate), the first Arena teleport of a session can fail
its arrival, and parallel jobs grew the container disk image on the system drive.
[PLAYTEST-PAYLOAD-COVERAGE-32](bugs/PLAYTEST-PAYLOAD-COVERAGE-32.md),
[VIVEC-ARENA-TP-ARRIVAL-32](bugs/VIVEC-ARENA-TP-ARRIVAL-32.md),
[BUILD-SCRATCH-DISK-GROWTH-32](bugs/BUILD-SCRATCH-DISK-GROWTH-32.md).

## ENTITY-TRACKER-HARVEST-32: register state corrected, 8 October 2026

Set back to open: it had been marked fixed in "v0.0.32-dev", a development line, not a shipped build.
The status keeps "fixed in source"; release preparation marks it fixed. `tools/bug_register.py` and
`tests/test_bug_tracker.py` now refuse a development line as `fixed_in` or `owner_accepted`.
[Report](bugs/ENTITY-TRACKER-HARVEST-32.md).

## Builder harvest step findings, 8 October 2026

Found while moving harvest into the builder (0331f76). New:
[HARVEST-SEYDA-HEAP-REFUSED-32](bugs/HARVEST-SEYDA-HEAP-REFUSED-32.md) (six Seyda Neen sub-cells lose
the harvest they had in v0.0.31),
[ENTITY-TRACKER-HARVEST-32](bugs/ENTITY-TRACKER-HARVEST-32.md) (fixed in source),
[HARVEST-EXTRA-TOWNS-32](bugs/HARVEST-EXTRA-TOWNS-32.md). Updated:
[BUILD-HARVEST-NOT-BUILT-32](bugs/BUILD-HARVEST-NOT-BUILT-32.md) (Balmora's baked mushrooms were
removed by hand in v0.0.29), [HARVEST-PILOT-SHIPPING-32](bugs/HARVEST-PILOT-SHIPPING-32.md) (8-model
cap per run), [HEAP-SEYDA-OVERLAP-32](bugs/HEAP-SEYDA-OVERLAP-32.md).

## CHIM world-format follow-up findings, 8 October 2026

FFS sweep, walk replay and per-placement visibility (branch v0.0.33-chim-format). The 36 ms random
seek was mostly the hard file's place on the PC; emulated disk time drifts between sessions and
cannot price bytes. New: [BENCH-HOST-STORAGE-32](bugs/BENCH-HOST-STORAGE-32.md),
[BENCH-SESSION-DRIFT-32](bugs/BENCH-SESSION-DRIFT-32.md),
[BENCH-DISK-BYTES-32](bugs/BENCH-DISK-BYTES-32.md),
[BUILD-HDF-BUFFERS-32](bugs/BUILD-HDF-BUFFERS-32.md),
[BENCH-FSUAE-PLAIN-HDF-32](bugs/BENCH-FSUAE-PLAIN-HDF-32.md),
[BENCH-AWBENCH-BUFFERS-32](bugs/BENCH-AWBENCH-BUFFERS-32.md) (fixed on the CHIM branch, not merged),
[BENCH-FSUAE-JIT-HANG-32](bugs/BENCH-FSUAE-JIT-HANG-32.md),
[CHIM-VALIDATOR-ORDER-33](bugs/CHIM-VALIDATOR-ORDER-33.md) (fixed on the CHIM branch, not merged).
Updated: [STREAM-FFS-SEEK-32](bugs/STREAM-FFS-SEEK-32.md),
[FFS-DIRECTORY-HASH-32](bugs/FFS-DIRECTORY-HASH-32.md) (first measurement),
[CHIM-PVS-HOLLOW-33](bugs/CHIM-PVS-HOLLOW-33.md) (per-placement lists),
[CHIM-READ-RUNS-33](bugs/CHIM-READ-RUNS-33.md), [SEYDA-READ-SLOW-31](bugs/SEYDA-READ-SLOW-31.md)
(timings on Windows-folder hard files).

## Image-parallel follow-up findings, 8 October 2026

Found while making the image step parallel. New:
[BUILD-LIGHT-THREADS-32](bugs/BUILD-LIGHT-THREADS-32.md),
[BUILD-HAND-CATALOG-SERIAL-32](bugs/BUILD-HAND-CATALOG-SERIAL-32.md),
[BUILD-IMAGE-UNDERUSED-32](bugs/BUILD-IMAGE-UNDERUSED-32.md),
[TEST-WORKER-SYSPATH-32](bugs/TEST-WORKER-SYSPATH-32.md),
[ACTOR-AUDIT-ORDER-32](bugs/ACTOR-AUDIT-ORDER-32.md).
Updated: [BUILD-SCHEDULER-JOBSHARE-32](bugs/BUILD-SCHEDULER-JOBSHARE-32.md) (map tool threads keep
their start share), [BUILD-PALETTE-RACE-32](bugs/BUILD-PALETTE-RACE-32.md) (expected flora
difference in from-scratch comparisons).

## BUILD-HARVEST-NOT-BUILT-32: harvest built by default, 8 October 2026

Owner decision: a default builder step for every map family, Seyda Neen regenerated too. The
`harvest` step converts the shared models and placements from the player's data; the image step
removes Balmora's baked mushrooms, writes the catalogues for the final maps, runs the geometry gate
and admits maps by the heap check. Owned dev1 maps: 381 of 388 admitted; world, Balmora and docks
catalogues byte-identical to v0.0.31. Not shipped.
[Report](bugs/BUILD-HARVEST-NOT-BUILT-32.md),
[HARVEST-SEYDA-STALE-32](bugs/HARVEST-SEYDA-STALE-32.md),
[HARVEST-PILOT-SHIPPING-32](bugs/HARVEST-PILOT-SHIPPING-32.md),
[HARVEST-GEOMETRY-GATE-32](bugs/HARVEST-GEOMETRY-GATE-32.md).

## BUILD-IMAGE-SERIAL-32: cause and repair, 8 October 2026

Cause: the image stage never received `--jobs`, so the scheduler ran it as a one-worker stage;
its per-map passes were serial or fixed at six workers. Repair (not shipped): `--jobs N` reaches
every image pass through the shared pool with byte-identical results, ericw light stays at one
thread per map (multi-threaded light output is not reproducible), and the early actor audit
approves the image in one pass. [Report](bugs/BUILD-IMAGE-SERIAL-32.md).

## dev1 image build findings, 8 October 2026

The dev1 image passed the xdftool step and then stopped on an undefined report in its last step (fixed).
[AUDIO-MISSING-SOURCES-32](bugs/AUDIO-MISSING-SOURCES-32.md),
[BUILD-FINALIZE-TORCHTEST-32](bugs/BUILD-FINALIZE-TORCHTEST-32.md),
[WORLD-THIRD-PARTITION-32](bugs/WORLD-THIRD-PARTITION-32.md).

## Parallel test runner findings, 8 October 2026

The suite now runs in parallel (same test IDs and results as serial). Found on the way: [BUILD-JOBS-RESOLVE-PER-STAGE-32](bugs/BUILD-JOBS-RESOLVE-PER-STAGE-32.md),
[TEST-NATIVE-TMPDIR-32](bugs/TEST-NATIVE-TMPDIR-32.md).

## Second CHIM engine slice, 8 October 2026

Chunk terrain is now grafted into the world tree (vis, lighting, water and traces through Quake's own
code); actors outside the ring are frozen; visible-entity drops are counted (also on v0.0.32-dev).
New: [CHIM-BORDER-COLLISION-33](bugs/CHIM-BORDER-COLLISION-33.md),
[CHIM-FRAME-WORLD-BOUNDS-33](bugs/CHIM-FRAME-WORLD-BOUNDS-33.md),
[CHIM-FROZEN-ACTORS-33](bugs/CHIM-FROZEN-ACTORS-33.md),
[CHIM-HULL2-33](bugs/CHIM-HULL2-33.md),
[CHIM-REBUILD-COST-33](bugs/CHIM-REBUILD-COST-33.md).

## Build profiler findings, 8 October 2026

The new build profiler found a possible palette race and a scheduler that keeps a stage at one worker.
[BUILD-PALETTE-RACE-32](bugs/BUILD-PALETTE-RACE-32.md),
[BUILD-SCHEDULER-JOBSHARE-32](bugs/BUILD-SCHEDULER-JOBSHARE-32.md).

## BUILD-XDFTOOL-ARGMAX-32, 8 October 2026

With trees and grass the boot payload has 15,747 files, and the single xdftool call exceeds the Linux
argument limit at the very end of the image step. [Report](bugs/BUILD-XDFTOOL-ARGMAX-32.md).

## First CHIM engine slice, 8 October 2026

Model zone, shared model library, placements through efrags and collision work in host tests. Open:
[CHIM-ACTORS-OUTSIDE-RING-33](bugs/CHIM-ACTORS-OUTSIDE-RING-33.md),
[CHIM-ANIM-TEXTURES-33](bugs/CHIM-ANIM-TEXTURES-33.md),
[CHIM-HEAP-CHECK-33](bugs/CHIM-HEAP-CHECK-33.md),
[CHIM-LIGHT-CONTENTS-33](bugs/CHIM-LIGHT-CONTENTS-33.md),
[CHIM-PACK-DIRS-33](bugs/CHIM-PACK-DIRS-33.md),
[CHIM-READ-BUDGET-33](bugs/CHIM-READ-BUDGET-33.md),
[CHIM-TERRAIN-GRAFT-33](bugs/CHIM-TERRAIN-GRAFT-33.md),
[RENDER-VISEDICTS-OVERFLOW-32](bugs/RENDER-VISEDICTS-OVERFLOW-32.md).

## Harvest data audit and builder message, 8 October 2026

The v0.0.31 harvest files were never rebuilt with their maps: stale Seyda catalogues, a pilot
catalogue still shipping, the geometry gate not re-run. Also a mojibake builder message.
[BUILD-MOJIBAKE-32](bugs/BUILD-MOJIBAKE-32.md),
[HARVEST-GEOMETRY-GATE-32](bugs/HARVEST-GEOMETRY-GATE-32.md),
[HARVEST-PILOT-SHIPPING-32](bugs/HARVEST-PILOT-SHIPPING-32.md),
[HARVEST-SEYDA-STALE-32](bugs/HARVEST-SEYDA-STALE-32.md).

## First CHIM world-format build of Balmora, 8 October 2026

Balmora in CHIM format 0.1: 17.4 MB instead of 162 MB, crossings read 277 KB instead of 4.4 MB, but
in many separate runs; visibility culls little; model faces still dominate. New: [CHIM-LEAF-SPAN-33](bugs/CHIM-LEAF-SPAN-33.md),
[CHIM-PVS-HOLLOW-33](bugs/CHIM-PVS-HOLLOW-33.md),
[CHIM-READ-RUNS-33](bugs/CHIM-READ-RUNS-33.md),
[CHIM-VIEW-FACES-33](bugs/CHIM-VIEW-FACES-33.md),
[CONVERT-COLLISION-FALLBACK-32](bugs/CONVERT-COLLISION-FALLBACK-32.md),
[GATE-SUITE-WRITABLE-32](bugs/GATE-SUITE-WRITABLE-32.md).

## NET-UDP-INIT-CRASH-32, 8 October 2026

The UDP start-up inherited from AmiQuake can end the game at boot when bsdsocket.library opens
(unchecked lookup, `Sys_Error`); untested so far. [Report](bugs/NET-UDP-INIT-CRASH-32.md).

## Release coverage test; per-race hands built by default, 8 October 2026

BUILD-HANDS-NOT-BUILT-32 fixed in source: a default `hand-catalog` builder stage, installed by the
image step after the sky palette bank; on owned data its command reproduces all 42 v0.0.31 files
byte for byte. [Report](bugs/BUILD-HANDS-NOT-BUILT-32.md). BUILD-STANDALONE-STAGES-32 closed:
neither tool's output is in v0.0.31. [Report](bugs/BUILD-STANDALONE-STAGES-32.md).
BUILD-HARVEST-NOT-BUILT-32: the harvest plan is traced and the builder step waits for an owner
decision. [Report](bugs/BUILD-HARVEST-NOT-BUILT-32.md). New `config/release-features.json`,
`tests/test_release_coverage.py` and `tools/payload_coverage.py`: every file class a release
ships has a feature and a default builder step.

## Builder defaults audit: stages missing from the builder, 8 October 2026

Trees and grass and the Balmora layout repair are now default. The audit found two shipped features
no builder step makes (per-race hands, mushroom harvest) and two standalone tools to check.
[BUILD-HANDS-NOT-BUILT-32](bugs/BUILD-HANDS-NOT-BUILT-32.md),
[BUILD-HARVEST-NOT-BUILT-32](bugs/BUILD-HARVEST-NOT-BUILT-32.md),
[BUILD-STANDALONE-STAGES-32](bugs/BUILD-STANDALONE-STAGES-32.md).

## BUILD-IMAGE-SERIAL-32, 8 October 2026

The image step uses one core of 24 for about 23 minutes per pass, and a private-test waiver needs two
passes. [Report](bugs/BUILD-IMAGE-SERIAL-32.md).

## BUILD-FLORA-OPTIN-32 fixed in source, 8 October 2026

World flora (trees and grass) is built by default; `--no-tree-sprites` is a debugging-only
opt-out and `--tree-sprites` a no-op alias. The Balmora layout repair no longer rides on the flora
option, and the image step names missing flora as the cause. Regression tests in
`tests/test_build_defaults.py`. [Report](bugs/BUILD-FLORA-OPTIN-32.md).

## BUILD-FLORA-OPTIN-32; world layout verified, 8 October 2026

The dev1 image stopped on a missing flora sprite: trees and grass need `--tree-sprites`, which the
from-scratch recipe left out. [Report](bugs/BUILD-FLORA-OPTIN-32.md). The rebuilt world region
directory is byte-identical to v0.0.31 ([BUILD-WORLD-LAYOUT-DRIFT-32](bugs/BUILD-WORLD-LAYOUT-DRIFT-32.md)).

## DEBUG-TP-TOWN-NAMES-32, 8 October 2026

`dbg tp vivec_arena` works, but the help line omits the new towns and short names such as
`vivec` are not accepted. [Report](bugs/DEBUG-TP-TOWN-NAMES-32.md).

## Renderer counters and benchmark findings, 8 October 2026

Renderer counters show brush models cost time through deep world-BSP walks, not fragments
(RENDER-BMODEL-FRAGMENTS-32). New: [BENCH-FSUAE-FREQ-32](bugs/BENCH-FSUAE-FREQ-32.md),
[BUILD-NO-OVERLAY-32](bugs/BUILD-NO-OVERLAY-32.md),
[ENGINE-ARGS-32](bugs/ENGINE-ARGS-32.md),
[RENDER-EDGECACHE-SEYDA-32](bugs/RENDER-EDGECACHE-SEYDA-32.md),
[RENDER-SURFCACHE-THRASH-32](bugs/RENDER-SURFCACHE-THRASH-32.md),
[STREAM-FFS-SEEK-32](bugs/STREAM-FFS-SEEK-32.md).

## GOG/Steam loose-file A/B findings, 8 October 2026

The original game data is the same in both editions; AmiWind's builder still makes edition-dependent
sky outputs and plugin sounds, and its asset readers ignore the expansion archives.
[ASSETS-ARCHIVE-ORDER-32](bugs/ASSETS-ARCHIVE-ORDER-32.md),
[BUILD-EDITION-SKY-32](bugs/BUILD-EDITION-SKY-32.md),
[BUILD-PLUGIN-SOUNDS-32](bugs/BUILD-PLUGIN-SOUNDS-32.md).

## BUILD-WORLD-LAYOUT-DRIFT-32; dev1 actor waiver tracked, 8 October 2026

The from-scratch dev1 build stops at world-terrain: the world survey takes its geometry
ceiling from the largest town region, which moved from 140,801 to 115,288 source triangles, so
the world would be laid out in 4,623 regions instead of the shipped 2,526.
[Report](bugs/BUILD-WORLD-LAYOUT-DRIFT-32.md). The owner-accepted private-test waiver for the five
Arena residents is now tracked on [VIVEC-ARENA-ACTORS-32](bugs/VIVEC-ARENA-ACTORS-32.md).

## Known-inputs check merged; BUILD-INPUTCHECK-SLOW-32, 8 October 2026

Every input is identified against a known-versions table with an inputs lock. The old
reference check spends over 12 minutes walking parent folders per file.
[Report](bugs/BUILD-INPUTCHECK-SLOW-32.md).

## Vivec cantons import and loader rework findings, 8 October 2026

Four cantons convert within all limits; the Temple, St. Delyn and St. Olms still exceed the
heap; the loader no longer stages lumps (smaller saving than estimated). New: NPC bake budget,
Arena handoff overlap, unreachable rooms, unbuilt neighbours, door bank limit (fixed), a
single loader stall, Seyda heap allowance, model slots, stale estimate coefficients.
[ESTIMATE-HEAP-STALE-32](bugs/ESTIMATE-HEAP-STALE-32.md),
[HEAP-SEYDA-OVERLAP-32](bugs/HEAP-SEYDA-OVERLAP-32.md),
[IMPORT-DOORBANK-LIMIT-32](bugs/IMPORT-DOORBANK-LIMIT-32.md),
[LOADER-STALL-32](bugs/LOADER-STALL-32.md),
[MODEL-SLOTS-256-32](bugs/MODEL-SLOTS-256-32.md),
[NPC-BAKE-VERTEX-32](bugs/NPC-BAKE-VERTEX-32.md),
[TOWN-EDGE-UNBUILT-32](bugs/TOWN-EDGE-UNBUILT-32.md),
[VIVEC-ARENA-HANDOFF-32](bugs/VIVEC-ARENA-HANDOFF-32.md),
[VIVEC-ROOMS-UNREACHABLE-32](bugs/VIVEC-ROOMS-UNREACHABLE-32.md).

## Font A/B: both font paths show wrong characters, 8 October 2026

The bitmap path keeps the .fnt glyph order while the engine indexes by game byte;
Magic Cards.ttf lacks many characters and draws ornaments for brackets.
[FONT-BITMAP-INDEX-32](bugs/FONT-BITMAP-INDEX-32.md),
[FONT-TTF-COVERAGE-32](bugs/FONT-TTF-COVERAGE-32.md).

## Builder breaks fixed; next stop in Seyda Neen culling, 8 October 2026

BUILD-SEYDA-HULL2-32 and BUILD-ACTOR-CONTACT-CALL-32 fixed in source; the from-scratch build
now stops in Seyda Neen terrain culling (covered by the recorded exception); shipped maps
carry unused hull 2 data. [BUILD-SEYDA-CULL-STABLE-32](bugs/BUILD-SEYDA-CULL-STABLE-32.md),
[MAP-UNUSED-HULL2-32](bugs/MAP-UNUSED-HULL2-32.md).

## BUILD-EDITION-DIFFERENCES-32: GOG and Steam builds differ, 8 October 2026

Same masters, different builds: Steam lacks the BookArt TrueType fonts, and
GOG loose files override archive copies in several steps.
[Report](bugs/BUILD-EDITION-DIFFERENCES-32.md).

## BUILD-INPUTS-UNVERIFIED-32: user inputs not checked against known versions, 8 October 2026

The builder records but never identifies the Morrowind files and Amiga
libraries it is given. [Report](bugs/BUILD-INPUTS-UNVERIFIED-32.md).

## BUILD-NOT-FROM-SCRATCH-32: releases without a from-scratch build, 8 October 2026

Images since v0.0.28 were older images with overlays; the builder's broken
stages never re-ran and CI builds only the asset-free dry run.
[Report](bugs/BUILD-NOT-FROM-SCRATCH-32.md).

## First from-scratch build with the repository builder, 8 October 2026

The public builder has not built the game from scratch since v0.0.28 (Seyda Neen
full-town hull 2 over the clipnode limit) and its actor stage fails since v0.0.27;
five Vivec Arena residents fail placement; the importer converts no interiors.
[BUILD-ACTOR-CONTACT-CALL-32](bugs/BUILD-ACTOR-CONTACT-CALL-32.md),
[BUILD-SEYDA-HULL2-32](bugs/BUILD-SEYDA-HULL2-32.md),
[IMPORT-TOWN-NO-INTERIORS-32](bugs/IMPORT-TOWN-NO-INTERIORS-32.md),
[PKG-STALE-RUNTIME-32](bugs/PKG-STALE-RUNTIME-32.md),
[VIVEC-ARENA-ACTORS-32](bugs/VIVEC-ARENA-ACTORS-32.md).

## FPU support library findings, 8 October 2026

A 68060 on Kickstart 3.1 without its library fails the boot check's FPU line;
boot lines wrap at 64 columns; dry-run text ignores user libraries.
[BOOT-68060-FPU-FAIL-32](bugs/BOOT-68060-FPU-FAIL-32.md),
[BOOT-CONSOLE-WIDTH-32](bugs/BOOT-CONSOLE-WIDTH-32.md),
[DRYRUN-LIBS-LABEL-32](bugs/DRYRUN-LIBS-LABEL-32.md).

## Asset census findings, 8 October 2026

Interior hulls outweigh interior geometry; open-world maps spend a fifth of
their bytes on visibility; terrain and some interior bakes are nearly
uniform; a flat mesh breaks collision building; tilt drives model variants.
[CONVERT-QHULL-FLAT-32](bugs/CONVERT-QHULL-FLAT-32.md),
[INTERIOR-BAKE-UNIFORM-32](bugs/INTERIOR-BAKE-UNIFORM-32.md),
[INTERIOR-HULLS-HEAVY-32](bugs/INTERIOR-HULLS-HEAVY-32.md),
[TERRAIN-LIGHT-UNIFORM-32](bugs/TERRAIN-LIGHT-UNIFORM-32.md),
[VF-VIS-LUMP-32](bugs/VF-VIS-LUMP-32.md).

## Face validator over the shipped v0.0.31 image, 8 October 2026

21.8 million faces in 2,724 maps checked. The v0.0.32 extent rule breaks the
lightmaps of all 58 old interiors (release blocker unless reconverted); 42
non-planar and 41 tilted faces; 6 wrongly wound; degenerate faces.
[CONVERT-DEGENERATE-FACES-32](bugs/CONVERT-DEGENERATE-FACES-32.md),
[CONVERT-FACE-WINDING-32](bugs/CONVERT-FACE-WINDING-32.md),
[EXTENTS-RULE-OLD-INTERIORS-32](bugs/EXTENTS-RULE-OLD-INTERIORS-32.md).

## ENGINE-FPU-UNIMPL-31, NPC-TARGET-REDUNDANT-31, ENGINE-BUILD-REPRO-31, ENGINE-FPSP-MISSING-31, REMOTE-STATE-WIDTH-31: FPU fixes measured, 8 October 2026

Per-frame counters (`dbg fpucount`) on the v0.0.31 image: 3,547 `cexp` calls per
frame at Balmora before, none after (brush rotation fast paths and cache, table
sine/cosine, NPC targeting once per frame, flame constants, no library
trigonometry linked). The engine build now fails if engine code reaches a
68040-unimplemented FPU instruction outside a justified allowlist. Two fresh
engine builds are byte-identical. In the emulator's strict FPU mode the engine
now runs past start-up but still stops at the first scene load (text-to-float
parsing). A formatting slip in the new state-file code was caught and fixed
before release. [ENGINE-FPU-UNIMPL-31](bugs/ENGINE-FPU-UNIMPL-31.md),
[NPC-TARGET-REDUNDANT-31](bugs/NPC-TARGET-REDUNDANT-31.md),
[ENGINE-BUILD-REPRO-31](bugs/ENGINE-BUILD-REPRO-31.md),
[ENGINE-FPSP-MISSING-31](bugs/ENGINE-FPSP-MISSING-31.md),
[REMOTE-STATE-WIDTH-31](bugs/REMOTE-STATE-WIDTH-31.md).

## REMOTE-CONSOLE-APPEND-31: remote console log overwrites itself, 8 October 2026

Every console message was written over the start of `AWCTL:console.log`; the
C library ignores `O_APPEND`. Fixed in source with a seek to the end.
[Report](bugs/REMOTE-CONSOLE-APPEND-31.md).

## TEST-FPU-STRICT-JIT-31: strict FPU emulation needs the JIT off, 8 October 2026

The emulator's "no unimplemented FPU instructions" option is ignored while the
JIT is on; a probe program shows the F-line traps only with the JIT off.
[Report](bugs/TEST-FPU-STRICT-JIT-31.md).

## Converter face findings from the texture snapping test, 8 October 2026

Merged faces take their plane from the first three vertices (29 degrees off in
two Khuul faces), can bend slightly, and texture coordinates are not range-checked.
[CONVERT-FACE-PLANE-32](bugs/CONVERT-FACE-PLANE-32.md),
[CONVERT-MERGE-NONPLANAR-32](bugs/CONVERT-MERGE-NONPLANAR-32.md),
[CONVERT-TEXCOORD-RANGE-32](bugs/CONVERT-TEXCOORD-RANGE-32.md).

## TOWN-FRAME-CEILING-32: high ground leaks town frames, 8 October 2026

Frames are sealed at 2,048 units; 320 regions have higher ground and leak.
ESTIMATE-EVR-BELOW-CUR-31 cause found and fixed in the public estimator.
[Report](bugs/TOWN-FRAME-CEILING-32.md).

## Independent review of the open-world plan, 8 October 2026

All performance figures were taken with the emulator at host speed; flat
directories are slow on real FFS; brush models may fragment down the terrain
BSP; the loader stages lumps before decoding. Notes added to
ENGINE-FPSP-MISSING-31 (denormals), INTERIOR-INLINE-LIMIT-31 (cause of the cap)
and CONVERT-VARIANTS-32 (scale). [BENCH-JIT-PROFILE-32](bugs/BENCH-JIT-PROFILE-32.md),
[FFS-DIRECTORY-HASH-32](bugs/FFS-DIRECTORY-HASH-32.md),
[LOADER-STAGING-PEAK-32](bugs/LOADER-STAGING-PEAK-32.md),
[RENDER-BMODEL-FRAGMENTS-32](bugs/RENDER-BMODEL-FRAGMENTS-32.md).

## World streamer measurement findings, 8 October 2026

Model variants per mesh, textures copied into every map, shared node subtrees,
placements stored differently per region, and a heap estimate that ignores
sharing inside a map. [BSP-SHARED-SUBTREES-32](bugs/BSP-SHARED-SUBTREES-32.md),
[CONVERT-VARIANTS-32](bugs/CONVERT-VARIANTS-32.md),
[HEAP-MODEL-SUM-32](bugs/HEAP-MODEL-SUM-32.md),
[MAP-TEXTURE-COPIES-32](bugs/MAP-TEXTURE-COPIES-32.md),
[REGION-PLACEMENT-FORMS-32](bugs/REGION-PLACEMENT-FORMS-32.md).

## ENGINE-SUBMODEL-LIMIT-32, TOOL-SIMPLIFY-MANIFOLD-32, SHELL-TEXTURE-VOTE-32: distant shell prototype, 8 October 2026

Map loading does not check the submodel count; mesh reduction can open closed
meshes; the shell texture vote picks door textures for walls.
[ENGINE-SUBMODEL-LIMIT-32](bugs/ENGINE-SUBMODEL-LIMIT-32.md),
[SHELL-TEXTURE-VOTE-32](bugs/SHELL-TEXTURE-VOTE-32.md),
[TOOL-SIMPLIFY-MANIFOLD-32](bugs/TOOL-SIMPLIFY-MANIFOLD-32.md).

## Vivec limits repaired in source; ERICW-TEXINFO-SIGNED-31, EXTENTS-FPU-RULE-31, VIVEC-HEAP-31 found, 8 October 2026

VIVEC-TEXINFO-31 and MODEL-MARKSURF-SIGNED-31: the engine reads face texinfo
indices, marksurface entries and leaf mark ranges unsigned, bounds-checked
before any pointer; the converter allows 65,535 mappings. MESH-EXTENT-GRID-31:
1/16-texel guard in the face split and a three-rule extent check.
LIGHTMAP-TAIL-31: caused by LIGHTMAP-GRID-31 (lightmaps sized from unstored
coordinates); the converter now sizes them from the stored values. Found on
the way: ericw vis crashes and light skips faces above texinfo 32,767
(ERICW-TEXINFO-SIGNED-31); surface extents followed a different rounding rule
on the 68040, the emulator, ericw light and the converter, now one double-
precision rule (EXTENTS-FPU-RULE-31). Rerun of the Vivec dry run: interiors
117 to 134 of 146 passing, exterior regions 160 to 174 of 192; the next limit
is the loader heap (VIVEC-HEAP-31). Source only, not shipped.
[MODEL-MARKSURF-SIGNED-31](bugs/MODEL-MARKSURF-SIGNED-31.md),
[VIVEC-TEXINFO-31](bugs/VIVEC-TEXINFO-31.md),
[MESH-EXTENT-GRID-31](bugs/MESH-EXTENT-GRID-31.md),
[LIGHTMAP-TAIL-31](bugs/LIGHTMAP-TAIL-31.md),
[LIGHTMAP-GRID-31](bugs/LIGHTMAP-GRID-31.md),
[ERICW-TEXINFO-SIGNED-31](bugs/ERICW-TEXINFO-SIGNED-31.md),
[EXTENTS-FPU-RULE-31](bugs/EXTENTS-FPU-RULE-31.md),
[VIVEC-HEAP-31](bugs/VIVEC-HEAP-31.md).

## ESTIMATE-EVR-BELOW-CUR-31 and TOOLING-HEADLESS-BROWSER-31: map metrics layer, 8 October 2026

The world estimate puts "everything" slightly below "current content" in 894
regions; no Docker image can render Toolkit screenshots.
[Report](bugs/ESTIMATE-EVR-BELOW-CUR-31.md), [report](bugs/TOOLING-HEADLESS-BROWSER-31.md).

## WORLD-REGION-DUPLICATION-31: exterior objects stored about ten times, 8 October 2026

Overlapping self-contained region maps store each exterior object about 9.8
times; most of the 4.8 GB of game files and the ~20 GB whole-island estimate
is repeated geometry. [Report](bugs/WORLD-REGION-DUPLICATION-31.md).

## Whole-world measurement findings, 8 October 2026

Estimating every map of the world with every object placed found silent
drops (night lamps in Vivec, static flames), the 220-object interior ceiling,
out-of-range interior coordinates, unsupported expansions and developer test
cells; MESH-EXTENT-GRID-31, LIGHTMAP-TAIL-31 and VIVEC-TEXINFO-31 reach beyond Vivec.
[LAMPS-CACHE-31](bugs/LAMPS-CACHE-31.md),
[INTERIOR-INLINE-LIMIT-31](bugs/INTERIOR-INLINE-LIMIT-31.md),
[FLAMES-CAP-31](bugs/FLAMES-CAP-31.md),
[INTERIOR-COORDS-31](bugs/INTERIOR-COORDS-31.md),
[BUILD-EXPANSIONS-31](bugs/BUILD-EXPANSIONS-31.md),
[IMPORT-TEST-CELLS-31](bugs/IMPORT-TEST-CELLS-31.md).

## MODEL-MARKSURF-SIGNED-31 and TOWN-VIS-OCCLUSION-31: visibility prototype, 8 October 2026

Occluders and building faces in the world model were measured not to help
open towns. The leaf face list loader reads face indices signed (latent bad
pointer above 32,767). [Report](bugs/MODEL-MARKSURF-SIGNED-31.md),
[report](bugs/TOWN-VIS-OCCLUSION-31.md).

## ENGINE-FPU-UNIMPL-31, ENGINE-FPSP-MISSING-31, NPC-TARGET-REDUNDANT-31, CI-ERICW-SKIP-31, CI-SKIPS-UNGUARDED-31: FPU audit and gate skips, 8 October 2026

The engine's sin+cos pairs become `cexp` calls that execute 68040-unimplemented
instructions every frame, the boot disk loads no FPU support library, and the
emulator hides both. NPC targeting runs several times per frame. Two CI test
gaps found while itemising skips. ENGINE-BUILD-REPRO-31: cause is the compile-time stamps.
[ENGINE-FPU-UNIMPL-31](bugs/ENGINE-FPU-UNIMPL-31.md),
[ENGINE-FPSP-MISSING-31](bugs/ENGINE-FPSP-MISSING-31.md),
[NPC-TARGET-REDUNDANT-31](bugs/NPC-TARGET-REDUNDANT-31.md),
[CI-ERICW-SKIP-31](bugs/CI-ERICW-SKIP-31.md),
[CI-SKIPS-UNGUARDED-31](bugs/CI-SKIPS-UNGUARDED-31.md).

## GATE-NODE-MISSING-31 and TOOLKIT-TEST-POINTERLOCK-31: inspector tests, 8 October 2026

The local gate never runs the inspector JavaScript tests (no Node.js in the
images); one of those tests left pointer lock set (fixed in source).
[Report](bugs/GATE-NODE-MISSING-31.md), [report](bugs/TOOLKIT-TEST-POINTERLOCK-31.md).

## ENGINE-BUILD-REPRO-31 and VIVEC-TEXINFO-31: from tonight's reports, 8 October 2026

Two engine builds from the same source gave different binaries; and 52 dense
Vivec exterior regions stop on the 32,767 texture-mapping limit (unsigned
texinfo planned). [Report](bugs/ENGINE-BUILD-REPRO-31.md),
[report](bugs/VIVEC-TEXINFO-31.md).

## MESH-EXTENT-GRID-31 and LIGHTMAP-TAIL-31: Vivec dry run, 8 October 2026

A sewer corridor face sitting exactly on the texture grid passes the converter's
extent check but exceeds 256 texels with the 68040's rounding, stopping 13 Vivec
maps; a 1/16-texel guard fixes it on a copy. Some interiors also write a last
lightmap past the end of the lighting lump.
[Report](bugs/MESH-EXTENT-GRID-31.md), [report](bugs/LIGHTMAP-TAIL-31.md).

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
