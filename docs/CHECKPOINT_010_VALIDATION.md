# Checkpoint-010 — v0.0.11-dev3 / pipeline 0.8.3.dev3

Date: 27 September 2026. Repair checkpoint; no NPCs or second town yet.

## Final artifacts and configuration

| Item | Identity |
| --- | --- |
| Clean RDB HDF | 134,250,496 bytes; 128 MiB DOS1/FFS partition |
| HDF SHA-256 | `7b7ee9786db165849ee08e29997958132f7c8ceaf53d4f2b4521c1f1545f4a19` |
| Runtime SHA-256 | `0c198e04b396fd3873a1aa3abd8330a88e9a9e7f02a07014ca61df9cc7a8c419` |
| Boot checker SHA-256 | `a4cd33b2d555859ee46cb78946173b08985122fc975d70cb7499a573cd805c20` |
| Kickstart | A1200 3.1, revision 40.68, 524,288 bytes |
| ROM SHA-256 | `6d43840d4099a74170ea0f0425b6257c3891ebcaa39c4d1840075a9ab22b5707` |
| Emulator | FS-UAE 3.1.66 |
| Emulator binary SHA-256 | `b729fe233a6507daed7fea6fbe8cfc417da523239d4a43037dd57203858e4f37` |
| Machine | A1200 model, AGA/PAL, emulated 68040/internal FPU, 2 MiB Chip, 16 MiB Z3 |
| CPU/storage/input | JIT on, CPU maximum, 24-bit addressing off, UAE RDB hardfile, keyboard joystick disabled |
| Build tools | AmigaPorts GCC 16.2-rc11, compiler 16.2.0b20260825082934, vasm 2.0f, ericw 0.18.1, amitools 0.8.1 |

WinUAE 6.0.3 preset supplied under resources/emulators; local execution was
FS-UAE, not WinUAE or physical stock hardware. No Workbench desktop is loaded.
The engine still requires AmigaOS services and this executable's FPU target.

## Filesystem acceptance

The old dev2 image reproduced the owner's exact block-1146049281 requester when
only its bitmap flag was marked invalid. Correcting reserved root word -4 and
its checksum allowed native revalidation. The final dev3 test also began with
a deliberately invalid bitmap, revalidated, booted, wrote profiles/configuration,
quit and relaunched. After two clean quits its bitmap is valid and the reserved
word is zero. Full payload readback, root checks and general filesystem scans
passed on the clean release and post-test image. The original ZIPs are unchanged.
See [the diagnosis](FILESYSTEM_REVALIDATION.md), including the limits of repair.

## Collision and rendering acceptance

57 host tests passed with the optional geometry dependencies and a host compiler.
Actual patched C routines are exercised for rotation, fully blocked movement,
nearest-floor trace merging, nearby surface ordering and fog-plane culling.

| Native floor sweep, same 441-point grid | Below-world destinations | World floor misses |
| --- | ---: | ---: |
| First dev3 candidate, before trace merging | 41 | 0 |
| Preserve nearer hits, before blocked-end correction | 40 | 0 |
| Final candidate | 0 | 0 |

The final scan has 56 start-overlap flags and 40 fully blocked sweeps; those
return their starting positions. It does not establish 441 freely walkable
locations. Rotated collision now follows building yaw, the standing hull matches
its compiled width, and fully blocked step-down movement cannot copy an invalid
lower endpoint into the player. Conservative multipart proxies can still catch
players in tight spaces. Real playtesting is required beyond the sampled grid.

The reported cottage door was reproduced at fixed near/far/angled cameras with
fog and distance culling disabled. Quake's old 1% depth tie band allowed wall
surfaces to cover the panel. A 0.001% band restores its nearer surface. A separate
synthetic test checks both depth/insertion orders and slopes. The final binary
also renders that door correctly with normal fog/culling. This is not a draw-last
or through-wall override. An unrelated rectangular roof gap remains visible.

Window attachments are now included: 155 placements share 55 variants, with
14,941 faces in a 2,726,592-byte BSP. Far culling uses view depth consistent with
fog, preserves crossing bounds, and avoids rejecting truncated entity leaf lists.
Existing frustum/PVS/backface work remains. No new renderer overflow was observed.

## Controls and restart

Native checks exercised F10 and grave console toggles, Escape-to-close, help,
noclip on/off, E/Q ascent/descent, recovery, position reporting, WASD, turns and
1/2/3 distances. Mouse deltas are consumed while the console is open; event data
is copied before replying to its OS message. See [controls](AGA_BUILD.md).

`amiwind` successfully relaunched after quitting. Both post-quit preflight
screens show 1,977 KiB free Chip and 15,971 KiB free Fast; the largest blocks
are 1,913 and 15,931 KiB. This bounded test does not prove unlimited restart life.

## Performance and audio limits

The final mixed diagnostic session recorded 1,908 frames / 98,196 ms,
6,304,688 bytes used in the 8 MiB hunk, peak 7,807 surfaces / 15,318 edges,
and zero surface/edge overflow. The restarted session also had zero overflow.
These are different views/timings from dev2, not a controlled speed comparison.
World rendering remains the largest measured stage.

The first session recorded three late audio updates (12,106 missed frames,
including 2,956 during warm-up) and a worst frame around 1.01 seconds. It included
the heavy floor diagnostic. The second session recorded only its warm-up miss
(2,809 frames). Both reported zero music read errors. Audio is not declared
stutter-free. All 18 installed tracks remain on disk; playback code is unchanged.
The preceding door-test candidate completed a full song and advanced from track
6 to 5. The shorter final sessions did not complete a song. Earlier full-song
and history-control evidence remains in checkpoint-009; do not relabel it as a
fresh exhaustive soundtrack test of this binary.

## Evidence and remaining work

Private evidence includes engine/image logs, host tests, fixed-camera old/new
depth captures, final floor CSV, post-quit screens, root checks and the exact
paired bad/fixed revalidation experiment. Final engine build is r5, final image
r3; the preceding r4 engine / image r2 supplies the unchanged renderer comparison.
The distributed HDF is the clean build output, not an emulator-mutated test copy.

Roof/terrain seams, conservative collision and audio deadlines remain open.
This checkpoint does not implement Balmora, NPCs, dialogue, interiors, quests,
saves or world streaming. The next NPC plan starts with Fargoth and guards;
[dialogue references](OPENMW_REF_NPCS_AND_DIALOGUE.md) preserve the requested
ring interaction, guard greetings and UESP/OpenMW study paths.
