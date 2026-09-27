# Optimization history

Preserve a measured baseline before changing the renderer, asset format, memory
layout or I/O scheduler. Keep rejected candidates: a failed experiment is useful
evidence. Never compare a maximum-speed JIT run to a stock-speed machine as if
they were the same hardware.

Verified asset mappings and symptom/cause/fix records are indexed in
[IMPLEMENTATION_JOURNAL.md](IMPLEMENTATION_JOURNAL.md); untried proposals are in
[IMPLEMENTATION_IDEAS.md](IMPLEMENTATION_IDEAS.md). Keep measured trials here.

## 2026-09-27: checkpoint-013 bounded hulls and greeting polling

Facet-only box expansion caused remote solids around acute architecture pieces.
Six axial support planes eliminate out-of-bounds solid hits in the same host
scan (246 to zero); native old/new comparison confirms one formerly blocked
square location is now walkable. Do not interpret the host count as 246 proven
runtime traps. Keep point hulls unchanged: the first candidate used 6,837,584
hunk bytes, final 6,509,888, saving 327,696 bytes. Final BSP
adds 89,516 bytes over dev1, with unchanged visible geometry/model counts.

NPC state rejection/distance checks precede LOS; greeting polls run at 4 Hz,
facing at 8 Hz, with independent idle poses. Authored wander packages are stored
for future routes, not simulated. Native counters caught a phantom-interaction
bug in the old compound E binding: console key releases issued the impulse.
A paired button and actual-client host test prevent that. The final HDF was
retested after replacing its generated binding.

Final greeting run: 2,246 frames / 122,966 ms,
world 104,416 ms, entities 2,304 ms,
C2P 291 ms; zero renderer overflow/read errors,
2 late audio updates. World work remains dominant.
Different routes prevent a controlled FPS comparison. See
[checkpoint-013 validation](CHECKPOINT_013_VALIDATION.md) for all evidence/limits.

## 2026-09-27: checkpoint-012 humanoid hull and first actors

Compared the base animation NIF's collision bounds with OpenMW's actor scaling.
The old Quake box was about 2.2 times too wide at our .25 world scale. Rebuild
standing world/architectural hulls together; do not change only the entity size.
Ground support removes idle slope drift in the acceptance route. Step-up now
uses 8.5 units, with tilted-riser handling and corrected post-step grounding.
The preferred Quake walking bob is unchanged. See [movement](PLAYER_MOVEMENT.md).

Three actors share two host-baked 8-pose MDLs (197,688 + 204,940 bytes on disk).
No Amiga skeletal animation is required. Final run: 3,350 frames / 142,918 ms;
world 124,641 ms, entities 2,253 ms, C2P 431 ms. Different camera routes prevent
an FPS comparison to dev4. Hunk use rose 39,600 bytes to 6,344,288; model caches
are separate. Zero render overflow and music read errors, two late audio updates
including warm-up. Preserve these limitations instead of hiding them behind JIT.
See [checkpoint-012 validation](CHECKPOINT_012_VALIDATION.md).

## 2026-09-27: dev4 fresh-boot movement regression

The dev3 acceptance route used recovery before testing walking. A new untouched
spawn test reproduced zero WASD/jump displacement at (16,44,74); noclip released
the player. Add a bounded startup-only standing-hull/ground/exit search and reuse
it for recovery. The repaired native run moves with all four WASD directions
before either command. Keep this ordering in every future scene acceptance gate.

The world and renderer are unchanged; hunk use remains 6,304,688 bytes. The new
run changes views and therefore is not a frame-rate comparison. It records zero
surface/edge overflow and zero music read errors, but two late audio updates
including warm-up. See [checkpoint-011](CHECKPOINT_011_VALIDATION.md). Do not fix
an invalid spawn by weakening the blocked-trace safeguard that prevents sinking.

## 2026-09-27: dev3 correctness before expansion

| Fault | Evidence | Change |
| --- | --- | --- |
| Legacy root contains DOS1 in reserved word -4 | Forced dev2 revalidation reproduces exact owner requester | Normalize known formatter mismatch and independently verify final root/payload |
| Rotated model collision not rotated | Actual C fixture misses a 90-degree platform before patch | Enable model-frame collision and conservative rotated broadphase bounds |
| Overlapping collider discards floor hit | Exit/start-overlap trace replaces nearer hit | Merge flags while retaining nearest blocking fraction |
| Fully blocked trace leaves requested end position | Step-down path copies that endpoint and can sink player | Return fraction zero and original start for blocked sweep |
| Door panel intermittently covered by wall | Identical cameras with old/new depth band, culling disabled | Tighten 1% band to 0.001%; no draw-last override |
| Fog and far culling use different distance definitions | Synthetic crossing-bound test | Cull by forward depth and retain intersecting bounds |

The native 441-point grid improved from 41 to zero below-world destinations;
40 final sweeps remain blocked and are reported as such. This is not a claim
that approximate collision proxies are exact or that every location is walkable.
The final mixed diagnostic run used 6,304,688 hunk bytes, about 105 KiB above dev2,
and peaked at 7,807 surfaces / 15,318 edges with no overflow. Windows account for
additional scene geometry. No speedup is claimed across different camera routes.

Three audio late updates remained in the diagnostic session; only the warm-up
miss occurred in its shorter restart. Keep that evidence and investigate scheduling
separately. The OST player itself was not changed. Native paired revalidation,
console recovery and shell restart now join the release acceptance gates.
Details and exact limits: [checkpoint-010](CHECKPOINT_010_VALIDATION.md).

## 2026-09-27: dev2 geometry, music and restart repair

See [checkpoint-009](CHECKPOINT_009_VALIDATION.md) for exact hashes and test
scope. Correctness came before expanding to another town.

| Candidate or fault | Observation | Result |
| --- | --- | --- |
| Old 800-surface renderer pool | Native `Short 35 surfaces`; foreground geometry could disappear | Set pools before map load; final walk/turn checks report zero overflow |
| Triangle prisms / multipart world brushes | BSP29 node/leaf or edge limits exceeded | Rejected; retain evidence privately |
| Non-instanced mesh BSP | About 4.7 MB input plus decoded geometry exceeded the 8 MiB hunk | Section-wise input loading alone was insufficient |
| Shared mesh variants | 136 placements reuse 52 variants; final BSP 2,661,820 bytes | Native hunk usage 6,199,424 bytes within the existing 8 MiB reservation |
| Mesh winding and texture extents | Invisible faces, then zero-sized cache allocation | Correct clockwise surface edges; split UV patches; clamp zero extents to 16 |
| Native numeric filename formatting | Playlist IDs changed, but all small IDs opened track00 | Construct digits directly; log filename and exact progress; distinct complete songs verified |
| Audio shutdown order | 32 KiB Chip lost on each quit/restart | Free DMA buffer before clearing descriptor; two final sessions recover equal Chip memory |
| Old preflight contiguous threshold | 9.1 MiB contiguous after quit could run the 8 MiB hunk but failed the 10 MiB gate | Keep 12 MiB total-free gate; require 8 MiB plus alignment contiguous |

The final first session recorded zero surface/edge overflow, 6,261/13,114 peak
surfaces/edges and zero music read errors. It still missed an audio deadline
around a one-second initial draw. One-time ring priming does not establish a
complete startup audio fix. Later turned views reached 100–128 ms; resident
world rendering dominates. The restarted session had only the initial audio
warm-up miss. Keep warm-up and subsequent misses separately visible.

This is a fidelity/memory improvement, **not a demonstrated speedup**. The old
convex scene reached the emulator's frame cap by drawing less faithful geometry.
Different views and shared host load prevent an isolated speed comparison here.
All runs use JIT/maximum-speed emulation, not a stock A1200. Next optimizations
must profile model/face culling and cache work while retaining the corrected
geometry, rather than silently restoring solid hulls for a higher FPS figure.

Two 16 KiB input buffers and 4 KiB disk slices bound music I/O. World geometry
is resident; section-wise BSP loading saves temporary startup memory and does
not implement gameplay cell streaming. HDD capacity is not a substitute for
rasterization time. Terrain refinement, remaining roof gaps and collision
acceptance precede generalizing the converter for Balmora.

## 2026-09-27: check hardware before loading the engine

The exact 80000027 requester was reproduced with the unchanged v0.0.9 image
and only 4 MiB Fast in FS-UAE. An 8 MiB game hunk plus code, BSS, stack and
other allocations cannot fit there. Disassembly of the linked C allocator has
a trap in an allocation-failure path; the WinUAE fault PC was not captured.

The v0.0.10 68000 preflight prints actual installed/free/contiguous memory and
returns 20 before loading the C runtime if the selected hardware is unsuitable.
It uses no heap, desktop or floating-point instructions. The engine's large
hunk now uses checked Exec Fast-memory allocation, with 15 bytes for alignment,
and frees the original pointer and size. Direct launch under 4 MiB also now
returns a readable allocation failure without entering engine shutdown.

An early checker incorrectly rejected AGA because bare-ROM graphics flags had
not been initialized. SetChipRev(SETCHIPREV_BEST), also used by the renderer,
corrected this before release. Native checks cover RAM, CPU, FPU, chipset and
KS1.3 rejection. Exact results and hashes are in CHECKPOINT_008_VALIDATION.md.

The owner later reported a WinUAE 6.0.3 boot after selecting the complete KS3.1
ROM with 16 MiB Z3 RAM. Severe audio breakup remained with cpu_speed=real.
The owner then selected maximum speed and reported that it ran OK. The
corrected profile preserves that setting. Playback shares the game loop, so late frames can repeat
stale DMA audio. Future work must measure and service that deadline, not infer
sufficient playback from zero file-read errors. The current host test suite and
previous timing baselines remain; no new renderer-speed improvement is claimed.

## 2026-09-27: static buildings belong in the wall renderer

Goal: a recognizable, walkable Seyda Neen scene. The first AGA conversion drew
buildings as reduced Quake alias models. Profiling identified model drawing as
the dominant measured stage; disk reads were not the dominant measured cost.

| Candidate | Observation | Decision |
| --- | --- | --- |
| A500 v0.0.7, eight-view scenery impostors | 38 frames / 1,411 PAL ticks = 1.35 fps; 0 reported audio starvation/read errors | Preserve as experiment; too slow for playable target |
| AGA alias buildings, run dev10 | 1,258 frames / 40.956 s = 30.72 fps; world 3,050 ms, entities 32,251 ms | Replace static alias buildings |
| One BSP brush per mesh triangle | 15,308 brushes; approximately 625,480 visibility leaves; standard BSP edge limit exceeded | Reject this conversion strategy |
| Unrestricted convex hulls | Hit compiler face limits on complex source geometry | Bound proxy complexity |
| Fourteen support directions, unsnapped hull vertices | Compiler rejected a nonconvex face caused by numerical precision | Quantize proxy vertices |
| Fourteen support directions, four-unit grid, baked facades | 128 convex brushes / 1,690 brush planes; BSP compiled and rendered | Historical checkpoint |
| AGA BSP buildings, run dev12 | 2,971 frames / 41.284 s = 71.96 fps; world 14,550 ms, entities 12 ms | Retain; reaches the engine's 72 fps cap in this JIT setup |
| 68020 soft-float, newlib and CLIB2 trials | Both stopped before renderer initialization: mathieeedoubbas.library unavailable in bare-ROM boot | Unresolved dependency; no stock-A1200 performance claim |

The AGA dev10/dev12 runs used FS-UAE 3.1.66, A1200 model, emulated 68040/FPU,
2 MiB Chip, 16 MiB Zorro III memory, JIT enabled and maximum CPU speed. This is
an emulator development configuration, **not a physical A1200 benchmark**.
The input route was a short stationary start followed by five seconds forward.
The rendering algorithm changed too: dev10 used the upstream assembly spans;
dev12 used GPL C spans. This is an architectural candidate comparison, not an
isolated microbenchmark of one function. Zorro III memory here is a UAE
convenience, not a stock A1200 RAM expansion specification.

The BSP test moved 128 static placements, using 44 shared source models, into
compiled world geometry. Thirteen foliage placements remained sprites. Facades
are 64 x 64 pixels, with four side projections and a top projection per model.
The compiled result has 6,753 faces, 3,439 leaves, 9,849 collision clipnodes and
1,210,524 bytes of mip textures. These are measured output counts, not budgets
for the whole game. Simplified convex collision closes some doorways and
undercuts; fidelity remains a separate acceptance criterion.

Run dev12 used 3,766,368 bytes of Quake hunk memory inside an 8 MiB reservation.
It read 917,504 music bytes with zero read errors, but reported one late mixer
update / 1,750 missed audio frames. **No read errors does not mean no underruns.**
The frame timings include the 72 fps limiter and uninstrumented work. Stage
totals are not a complete CPU utilization breakdown.

## Existing A500 baseline

The earlier streaming experiments remain in [PROFILING.md](PROFILING.md).
Blocking 16 KiB reads produced a 360 ms worst observed frame in the original
fixed-camera comparison; cooperative 4 KiB slices reduced that to 160 ms with
a small average-fps tradeoff. A longer movement test then exposed starvation,
so refill service was added inside terrain rendering. Keep both the short-test
result and its later correction; do not overwrite history with the better number.

## Regression procedure

1. Save source, converter settings, input identities, binary and image hashes.
2. Capture exact emulator version/hash, ROM hash, effective CPU/FPU/JIT/memory,
   display settings, storage path type, route and host class.
3. Check image correctness, collision and controls alongside speed. A missing
   building can make a bad change look fast.
4. Record frame average, sampled p95, worst frame, hunk usage, free Chip/Fast
   memory, stage totals, read failures, late mixer updates and song history.
5. Compare only matched runs; repeat a regression before drawing a conclusion.
   Keep a last-known-good checkpoint until the candidate passes.

`tools/profile_aga.py report RUN --context context.json` summarizes the native
`frame-profile.txt`, `music-profile.txt` and `walk-profile.csv`. The CSV samples
every tenth frame, so its p95 is explicitly a **sampled** percentile.
`tools/profile_aga.py compare baseline.json candidate.json` rejects mismatched
contexts and returns failure for >10% increases in sampled p95, worst frame or
hunk usage, increased audio/read failures, or adjacent repeated songs.
Context fields are listed in that tool's `MATCH_FIELDS`; effective machine and
view settings should be structured values, not vague names like "fast Amiga".

## Next bottlenecks to measure

- Run a deterministic camera route without the ordinary frame cap for renderer
  throughput, alongside a capped interactive run for pacing and audio.
- Separate world traversal, surface-cache work, fog and simulation timings.
- Resolve the 020 math-library dependency, then measure a fixed-speed no-JIT
  68020/Fast-RAM configuration. Do not optimize against JIT results alone.
- Introduce chunk residency with a fixed memory ceiling and bounded prefetch.
  The current BSP scene is loaded in full; only music streams during play.
- Add one NPC and one greeting before measuring actor populations. Share baked
  poses, palettes and equipment variants; retain only active actor working sets.

An HDD can supply precomputed data and cache misses. It does not perform the
Amiga's remaining projection, rasterization, collision or game logic. Lookup
tables trade arithmetic for memory traffic, so both sides need measurement.

## Packaged HDF baseline

The final checkpoint-006 sustained run and known stalls are recorded in
[CHECKPOINT_006_VALIDATION.md](CHECKPOINT_006_VALIDATION.md). Its exact
`context.json` and `profile.json` accompany the private image. Do not compare
its four-minute control/music route directly to the shorter dev10/dev12 runs.

## 2026-09-27: remove the desktop icon startup dependency

A user reported the LIBS/icon.library requester and return code 20 in WinUAE.
The old executable still referenced GetDiskObject/FindToolType for the unused
Workbench launch path. Its runtime library auto-opened icon.library before main,
so disabling Workbench desktop loading in startup-sequence was insufficient.
The explicit CLIB2 adapter also opened the library. Both paths were removed.

The failure was reproduced with the uploaded 3.1.4 A1200 ROM. The user also
reported it after selecting the supplied 3.1 ROM; the exact effective WinUAE
configuration for that attempt was not available. Do not present a ROM swap as
an established remedy for the user's setup.

The binary check rejects the old release and accepts the fixed executable.
This checks known desktop-library names in a linked Hunk file; it is not a full
proof that arbitrary future code cannot construct a library name dynamically.
Native ROM tests remain necessary. The filesystem payload audit permits only
`AmiWind` to differ. Recompiling the unchanged BSP produced different lighting
packing, so the hotfix reuses the exact previous compiled BSP. No geometry,
texture or audio conversion change is smuggled into the startup fix.

This removes an unnecessary requirement, not a claimed rendering speedup.
Optional network initialization is a candidate for a later startup audit;
required display, audio, input, timer and filesystem services still remain.
See CHECKPOINT_007_VALIDATION.md for hashes, counters and test scope.

## Owner confirmation — v0.0.12-dev2, 27 September 2026

The owner confirms that the central town-square obstruction is fixed. This
corroborates the bounded collision-hull work recorded in checkpoint-013; it
does not close the separate pier, scene-boundary or terrain rendering reports.
See [PLAYTEST_STATUS.md](PLAYTEST_STATUS.md) for per-version acceptance status.

## v0.0.13-dev1 / checkpoint-014 — correct geometry and bounded render buffers

The disappearing pier was a signed-short interpretation of BSP face plane
indices above 32767. The old scene has 34643 planes; all indices still fit
unsigned 16 bits. Fix decoding and validate the lump bound rather than widening
every face or introducing bank switching. Native same-camera views restore the
deck; a real loader fixture fails before and passes after the correction.

Correctly restored surfaces then exceeded the old 8192-surface/16384-edge
buffers at dock views. An oversized 16384/32768 trial eliminated overflow but
consumed 1 MiB more hunk space and provoked repeated actor/hand model loads.
Select 10240 surfaces / 20480 edges instead: 256 KiB extra, with 8587/17167
observed high-water marks and zero overflow on the final acceptance route.
Each actor/hand model loads once in that route. Total hunk use is 6935536 bytes;
new sea/world data also contributes. Keep monitoring other views/draw distances.

The coordinate strip initially drew into the chunky buffer but was omitted
from viewport-only screen updates. Explicitly include it in the transfer when
visible. Overlay-off restores the full viewport. The extended flat sea remains
a temporary coverage placeholder, not a world-streaming optimization.

World rendering accounts for 59320 ms of the mixed 69281 ms acceptance run;
entities 631 ms and C2P 189 ms. This does not establish a before/after FPS gain.
Do not celebrate a lower work count caused by missing geometry. Remaining work:
material/UV-aware geometry reduction, bounds-based coverage, chunks and bounded
prefetch, plus audio deadline servicing. See CHECKPOINT_014_VALIDATION.md.

## v0.0.14-dev1 / checkpoint-015 — ship conversion and cache budget

The full-detail ship trial produced 9976 BSP surfaces. Host material/component
reduction and 32-pixel material textures reduce that to 3931 (1954 triangles from
5908); separate authored collision reduces approximate convex pieces from 217
to 60. Whole-scene BSP drops from 4,130,044 to 3,382,832 bytes between these two
host trials. These counts do not establish an FPS speedup.

The 8 MiB native trial exhausted cache allocation space (253,632-byte request).
The final 9 MiB heap stays within the existing 16 MiB Fast preset; it passes the
ship/console/hands route with zero surface/edge overflow and one model open per
actor/hand asset. Hunk at exit: 7,674,432 bytes; free Fast: 5,054,552 bytes. Keep
this increase visible in the history: restoring coverage costs RAM. Residency
partitioning remains future work, not supplied by a larger HDD image.

Final route: 2184 frames / 97,615 ms, world 83,531 ms, entities 1434 ms, C2P
288 ms; maximum 7365 surfaces / 13,436 edges. It includes console/menu time and
different views from checkpoint-014, so do not derive a paired FPS improvement.
Audio: 2 late updates / 7114 missed frames plus startup warmup; no file read
errors. No claim of glitch-free audio or stock-A1200 speed. Full evidence and
rejected trial: [CHECKPOINT_015_VALIDATION.md](CHECKPOINT_015_VALIDATION.md).

Console background is an opaque row fill, with no alpha pass or extra buffer.
The readable/retro font switch keeps one 16 KiB active atlas and temporarily
reads 16 KiB on the stack; normal drawing has no per-frame font/background I/O.

## v0.0.15-dev1 / checkpoint-016 — interior policy and measured hand path

A hollow collision shell needs surface prisms rather than filled convex volumes.
The resulting 1,205-piece shell exposed task-stack pressure; iterative same-side
hull descent removed that dependency for long one-sided chains. Segment splits
still recurse. Preserve the synthetic long-chain test and native failed trial.

The interior shell reduces 32,297 triangles to 7,404 before UV/BSP subdivision;
the whole 98-instance scene has 26,073 faces and a 3,483,880-byte BSP. Offline
ambient/lamp sampling avoids per-frame lighting work, but unique lit instances
and collision consume memory. One resident scene and a 9 MiB heap remain the
current policy. This is not exterior cell streaming.

The 252,612-byte 3D hand model has an optional 22,426-byte opaque sprite-span
alternative. The native mixed routes recorded 940 ms hands time (3D) and 55 ms
(sprites), but differ in frame count/host timing and include hidden hands: no
matched FPS speedup is established. Sprite animation/lighting coverage is limited.
World cost (89,733 / 85,118 ms) dominates these roughly 147-second test routes.
Both recorded zero edge/surface overflow, but audio still missed deadlines.
All counters, hashes and failures: CHECKPOINT_016_VALIDATION.md.

The compact font adds 475 glyph bytes, uses the existing history ring and draws
without per-frame disk access. Fullscreen console/scrollback are debugging tools,
not gameplay performance optimizations. Future A/B runs need the same camera,
heading, pitch, overlay/viewport and scene state; see CONVERSION_RECIPES.md.

## 2026-09-27: checkpoint-017 structural interior correction

The 8%-ratio shell LOD flattened curved walls inward. Independent host full-source
vs reduced renders reproduced the same hammock intrusion as the native report.
Preserving structural shapes/UVs restores the native view without increasing the
preallocated heap or changing collision. Whole interior BSP rises from 26,073 to
26,572 faces (+499), 19,002 to 19,304 vertices, and 3,483,880 to 3,538,308 bytes
(+54,428, about 53.2 KiB). Nodes/clipnodes remain 14,566/23,487. Exterior BSP is
identical. These are storage/topology counts, not a measured FPS improvement.
Native report and fixed-view comparison are in CHECKPOINT_017_VALIDATION.md.

Checkpoint-017 live-control follow-up: replace the depth-LUT floating-point loop
with 15 integer threshold divisions plus fills in the same 32 KiB table. Host
oracle checks all depth values at five distances. No per-frame rebuild when the
setting is unchanged. Actual rebuild latency on physical hardware is unmeasured.
The town camera (-44,259,75), yaw328/pitch-14 improved from 11.46 to 17.21 FPS
in selected stationary windows at distance700 vs400 on the same FS-UAE JIT/max
run. This is a visibility/quality tradeoff, not a fix for the still-unisolated
regression. Details and limits: CHECKPOINT_017_VALIDATION.md.

Next bottleneck instrumentation: bounded per-brush-model render timing and
surface-cache miss/rebuild counts at the reported town/boat/overhang cameras.
Use sampled counters with a measured overhead budget; do not insert disk writes
inside per-surface work. Separate geometry count, clipping/overdraw, texture
cache behavior, collision and host output scaling before choosing the next LOD.

## Ship contribution diagnostic

`ship017-native-ab` uses the final engine with a separate private map candidate.
Only exterior hull submodel15's visible surface count changes from3931 to0.
Collision, existing arrays/texture allocation and separate ship attachments
remain. At the same town camera and fog700, selected stationary windows give
**10.52 FPS with hull surfaces vs 12.44 FPS suppressed**. No render overflow
or music read error; the on-screen town view is otherwise unchanged.
This suggests some hull rendering cost at that camera, but it does not explain
all of the low frame rate or establish the original regression's cause. It is
one short run, not a statistically controlled benchmark. Keep testing the
building/overhang and cache paths. The normal playable image retains the ship;
the suppression candidate is diagnostic evidence only, not a shipped gameplay
mode or a geometry optimization. It does not measure the potential memory
saving from removing the entire ship assembly after the opening.

## Building culling investigation 001 (after checkpoint-017)

Owner report at XYZ249 40 227 / DEG315 P25 linked roof-edge popping to culling
cost. Native fixed-camera A/B with `dbg cull 1` and0 reproduces the lines in both
states, also at XYZ288 42 171 / DEG332 P12. HUD-excluded scene crops are identical
(zero changed pixels of166352 at each pair). This rules out the added fog-distance
cutoff as the cause of the observed lines at those sampled poses; it does not
rule out frustum/backface/BSP clipping or depth-ordering defects. No new fix yet.
Buildings remain resident: this culling path performs no asset unload/reload.
Zero renderer edge/surface overflow in the completed run. Read-only BSP audit
found no broken edge loops, non-finite vertices/planes or reversed winding under
its checks. Next isolate native clipping/sorting and separately measure per-model
rendering/cache costs. Do not turn off useful culling globally or assume the
visual artifact proves the performance culprit. Details and private evidence:
AmiWind-building-culling-audit-001; this is not a new playable checkpoint.
