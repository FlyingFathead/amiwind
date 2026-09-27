# Checkpoint-013: bounded collision and nearby greetings

Runtime **v0.0.12-dev2**, public pipeline **0.9.0.dev2**, 27 September 2026.
Created by FlyingFathead a.k.a. Horstator. Thanks to ChaosWhisperer.

## Delivered scope

- Expanded architectural collision pieces now include six axial support limits.
  This removes remote solid spikes produced by expanding only acute facet planes.
  Unexpanded point/visibility hulls retain the original planes and node count.
- `aw_blockers` reports eight nearby standing-hull sweeps with coordinates, hit
  model, fraction, contact normal and solid flags. `aw_npcs` reports positions,
  facing, greeting counters and rearm state. These are on-demand diagnostics.
- Fargoth and two guards turn toward the player for E/proximity Hello auditions.
  Distance/reset/duration settings come from the owned installation. Poll at
  4 Hz after cheap distance rejection; require two qualifying LOS checks.
  Do not repeat until the player leaves the reset radius. Shared automatic
  cooldown is eight seconds; manual cooldown is four seconds.
- E uses a paired button command. The previous compound binding replayed an
  impulse on key-up, including console typing, and could cause phantom greetings.
- Authored NPC ratings/packages are retained privately; Wander range, duration,
  time, idle weights and repeat are decoded. No walking routes are executed yet.
- Both packages include the owner FS-UAE guide and versioned FS-UAE/WinUAE presets
  under resources/emulators. Public presets contain placeholders only.

## Focused verification

**68 host tests pass**, including the actual patched client input handlers for
press/repeat/release/console sequences, an acute collision-piece regression,
legitimate hull contacts, ordered wander parsing and greeting-unit conversion.
Existing native-source standing/rotated hull, slope/stair, culling/depth and audio
fixtures still pass. No proprietary data appears in the public tests.

The host town grid found **246** old solid hits outside expanded model bounds;
the corrected final scene reports **zero** for the same grid. That scan bypasses
scene broadphase, so it is a diagnostic, not 246 proven in-game obstructions.
Native comparison separately reproduces a real defect at (0,136,90): dev1
refuses to disable noclip as 'inside solid'. The new image permits walking,
settles around (0,135,68), then crosses to approximately (93,135,66).
This does not prove that it is the exact location in the owner's screenshot.

`startup012-dev2-r2` validates final engine/scene geometry: initial WASD before
any recovery/noclip, square crossing, stationary support, stair ascent to about
(-147,319,99) and descent to (-55,319,75), recovery and clean exit. This candidate
still had the old E binding in generated config, so its greeting counters are
explicitly rejected as interaction evidence. Its native engine and scene are
byte-identical to the final image; the final image corrects the binding.

`startup012-dev2-r3` boots the final image and tests fresh WASD, E, console typing,
proximity greeting, lingering, leave/return rearming and normal exit. Fargoth
counters progress from automatic/manual 0/0 to 0/1, then 1/1 after 12 seconds
nearby, then 2/1 after leaving and returning. Typing console commands no longer
increments manual interactions. Facing changes to approximately yaw 270 when
the player stands to the east; the converted model's front axis is +Y. Native
captures inspect that orientation. NPCs remain nonblocking.

## Runtime and profiling context

FS-UAE **3.1.66**, A1200/AGA/PAL, **68040-NOMMU + internal FPU**, 2 MiB Chip,
16 MiB Z3 Fast, JIT on, maximum CPU speed, 24-bit addressing off, keyboard
joystick disabled, mechanical floppy sounds off. Resolved log:
`CPU=68040, FPU=68040, MMU=0, JIT=CPU/FPU=8192`. Kickstart 3.1 A1200 **40.68**,
524,288 bytes. No Workbench desktop. WinUAE preset is guidance, not a local
WinUAE execution result. No stock-A1200 performance claim.

Final greeting run: 2,246 frames / 122,966 ms;
world 104,416 ms, entities 2,304 ms,
C2P 291 ms. Zero surface/edge overflow and music read errors.
Late audio updates: **2**, including
1 warm-up update. This is not glitch-free audio.
The short final run did not reach a natural song transition; the unchanged
music implementation and earlier full-song evidence remain applicable.

Hunk use: **6,509,888 bytes** (dev1: 6,344,288). An initial
candidate needlessly added axial planes to point hulls and used 6,837,584 bytes;
keeping point hulls unchanged saves **327,696 hunk bytes** versus that candidate.
The final BSP adds 4,707 clipnodes (19,198 total) but keeps 11,343 drawing/point
nodes. BSP size is 2,834,616 bytes versus 2,745,100 previously. Visible geometry,
model count and actor meshes are unchanged. Hunk usage is not total memory:
alias caches and fixed reservations are separate. Exit free memory:
1,796,432 Chip and 6,082,328 Fast bytes.

World rendering still dominates. Routes and camera views differ across runs;
no comparative FPS speedup is claimed. Quake bob, grounded movement, stairs,
door-depth rendering, fog and music implementations are unchanged from dev1.

## Hashes and packaging

| Artifact | SHA-256 |
| --- | --- |
| Kickstart 3.1 A1200 40.68 | `6d43840d4099a74170ea0f0425b6257c3891ebcaa39c4d1840075a9ab22b5707` |
| FS-UAE executable | `b729fe233a6507daed7fea6fbe8cfc417da523239d4a43037dd57203858e4f37` |
| Pristine final HDF | `a1f2b07ccd1fec88de673e49e0b5b7e882e6a7f1318fb4ae27e741a9992da3d5` |
| AmiWind executable | `76f9bd69be7b3765b680dacebd3ae22fe478574b0fd2f71fe8a8c160689b0d6c` |
| Preflight executable | `b9a308ec391fe5b9b57c92ee9d607829ff44f8476959c2e94e056269eb1da07f` |

Engine: terriblefire/amiquake commit
`9c62d905151614af3e788ae3145a0d4ecc8a7bb8`, AmigaPorts GCC 16.2-rc11 bundle,
compiler 16.2.0b20260825082934, 68040/68881. Independent C2P and GPL C spans.
See LINUX_BUILD.md for qcc, ericw-tools v0.18.1 and image recipes.

HDF: 134,250,496 bytes, 128 MiB FFS partition in RDB, 18 converted music
tracks. Each payload was read back independently and root metadata verified.
Native tests use disposable writable copies. The public ZIP is source-only:
no ROM, executable, original/converted game assets or binary-recovered assembly.
Corresponding runtime source and build machinery accompany the host source.

## Remaining limits

Wandering, walk poses, ambient Idle speech, original awareness and full dialogue
conditions, quests, combat, Nord hands/punching, Balmora, interiors and saves are
future work. E is still a preselected generic Hello voice audition, not a dialogue
window or Fargoth's text-only ring quest. Imported character skins are coarse.
Collision remains approximate: axial bounds prevent remote spikes but do not
produce exact concave or bevel geometry. Other sticky corners may remain.
Music streams; world geometry is resident. See ROADMAP.md for the retained queue.
