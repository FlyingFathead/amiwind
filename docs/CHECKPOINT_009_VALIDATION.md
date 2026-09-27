# Checkpoint-009 — v0.0.11-dev2

Recorded 27 September 2026. Source package 0.8.3.dev2. This is a playable
**development checkpoint**, not a completed graphics repair or stock-A1200 port.
The private image contains owned/converted data; the public source contains none.

## What changed

- Shared static BSP mesh surfaces preserve original UVs and architectural gaps.
  The old convex facade bake remains as historical tooling. Separate multipart
  collision is approximate; only the standing player hull is represented.
- Scale and pitch/roll form shared model variants; placements retain yaw and
  position. Current scene: 136 placements, 52 variants, 14,588 faces, 13,051
  vertices, 11,087 nodes and 12,845 clipnodes; BSP size 2,661,820 bytes.
- Renderer pools are set before map loading: 8,192 surfaces / 16,384 edges.
  Also corrected big-endian paired depth writes, rotated submodel clipping
  bounds and zero-area texture extents. UV patches stay within cache limits.
- BSP input sections load individually: 15 reads, largest section 620,000
  bytes. Decoded geometry remains resident; this is not world-cell streaming.
- Native track filename construction no longer routes 32-bit IDs through the
  SDK's word-sized decimal formatting. That bug repeatedly opened track00
  despite apparently changing playlist IDs. Title duplicates are also excluded
  from exploration/battle groups. All 18 installed files remain on disk.
- Shift+F5 Previous / Shift+F6 Next use history and shuffled groups. Two 16 KiB
  input buffers refill in cooperative 4 KiB slices. Event logs record actual
  filename and exact played/total frames; writes flush on close.
- Audio shutdown now frees the 32 KiB Chip DMA allocation before clearing its
  descriptor. Preflight's contiguous Fast threshold matches the 8 MiB hunk
  plus alignment, avoiding a false failure after quitting.
- Added guided Linux build, restored README intro/credits/notices, and versioned
  public WinUAE presets under `resources/emulators/` with empty private paths.

## Exact final image and toolchain

| Artifact | Value |
| --- | --- |
| HDF | `AmiWind-v0.0.11-dev2.hdf`, 134,250,496 bytes; RDB + 128 MiB FFS partition |
| HDF SHA-256 | `8aa82a42afa8d55e61c1d5eb4973448dc9aff094c08b2ec44cd7a8e0d559b281` |
| Runtime SHA-256 | `9160b5e90ea63d039dd4bf651651e6f7145523e3f68c72dc7e8b01dd11cd6d79` |
| Preflight SHA-256 | `15e9d60ae8ee63a0e727dc8132b33ef8ea8322762353d60afa3b91a285dc1e34` |
| Payload | 60,304,497 bytes; 18 complete music streams |
| ROM | A1200 Kickstart 3.1, revision 40.68, 524,288 bytes |
| ROM SHA-256 | `6d43840d4099a74170ea0f0425b6257c3891ebcaa39c4d1840075a9ab22b5707` |
| Emulator | FS-UAE 3.1.66, Linux x86-64 |
| Emulator SHA-256 | `b729fe233a6507daed7fea6fbe8cfc417da523239d4a43037dd57203858e4f37` |
| Settings | A1200 model, 68040/internal FPU, AGA/PAL, 2 MiB Chip, 16 MiB Z3, no slow/Z2 RAM, JIT on, maximum CPU, 24-bit addressing off, UAE RDB hardfile, joystick port 1 disabled |
| Compiler | AmigaPorts SDK v16.2-rc11, GCC 16.2.0b20260825082934, GNU89, 68040/68881, `-O1`; vasm 2.0f |
| Map tools | ericw-tools 0.18.1; qcc from Quake-Tools revision c0d1b91; amitools 0.8.1 |
| Upstream | AmiQuake `9c62d905151614af3e788ae3145a0d4ecc8a7bb8` |
| Upstream archive SHA-256 | `43353034beb2a43b1af82c735f93c0a8bee8129c1b93d7ba152dd8e60ad3721c` |

The public WinUAE 6.0.3 preset is based on the owner's settings and has not been
executed locally in WinUAE. These JIT runs are correctness checks, **not a
physical Amiga or stock A1200 benchmark**. Host load was not controlled for a
matched speed comparison. Preflight still requires 12 MiB free Fast RAM; the
contiguous threshold is 8 MiB + 16 bytes. Use the 2/16 MiB reference setup.

## Host and native evidence

All **51 host tests passed**. Coverage includes original-format parsing, private
path boundaries, guided build failures, source packaging, geometry concavity,
disconnected collision pieces, UV patch limits and the actual C music player
with synthetic variable-length PCM, history/mode transitions and malformed input.
Synthetic tests include at least 18 natural completions; they are not full-OST
emulator listening tests. The native-specific filename fault requires native
acceptance as well as Linux C tests.

The guided eight-stage Linux build completed and the image builder independently
read every payload back. That run preceded the final preflight/initial audio-ring
priming changes. The final engine and HDF were rebuilt through the same lower-
level tools, passed payload readback and underwent the following native test.
No clean-distribution installation test is claimed.

Final candidate `r3`: cold boot, five turned views, all three draw distances,
W/S/A/D movement, Shift+F6/F5, F8 mode audition, Escape, hardware check, shell
`amiwind` restart, Escape and hardware check again. The working HDF copy added
only diagnostic key bindings and overflow reporting; the packaged HDF is clean.
Private evidence includes screenshots, CSVs, profiles and exact FS-UAE config.

| Counter | First session | Relaunched session |
| --- | ---: | ---: |
| Frames / elapsed milliseconds | 1,941 / 90,356 | 749 / 33,097 |
| Worst frame, microseconds | 1,006,791 | 87,633 |
| Surface / edge overflow frames | 0 / 0 | 0 / 0 |
| Maximum surfaces / edges used | 6,261 / 13,114 | 3,861 / 7,634 |
| Hunk usage, bytes (8 MiB reservation) | 6,199,424 | 6,199,424 |
| Free Chip bytes while running | 1,796,432 | 1,796,432 |
| Music read errors | 0 | 0 |
| Late audio updates / missed frames | 2 / 8,245 | 1 / 2,673 |
| Included initial warm-up update / frames | 1 / 2,753 | 1 / 2,673 |

The first session's remaining non-warm-up audio miss coincided with the
approximately one-second initial draw. A one-time ring prefill does **not**
eliminate it. Some turned views took 100–128 ms. The second session had no late
update beyond initial warm-up. These counters do not establish glitch-free
playback on a slower machine. Music IDs/files were 6, 5, 6, 11 for manual
Next/Previous/battle, with zero read errors. Replaying 6 via Previous is intended.

After each quit, preflight passed with 1,977 KiB Chip free (largest 1,913) and
15,971 KiB Fast free (largest 9,319). There was no repeated 32 KiB Chip loss.
This checks two sessions, not an unlimited leak/endurance guarantee.

## Full-song acceptance, before the final startup-only changes

The same dev2 player and geometry ran for 274,644 ms in candidate `r2`. Native
logs record track04 reaching **2,153,150 / 2,153,150 frames**, then opening track03
with 2,048,413 frames. Next/Previous/battle yielded IDs 4, 3, 2, 3, 10. Surface
and edge overflow counts were zero. Its earlier runtime hash was
`a07eeb356fcd58e6c48f924deb117d9e5bfdd50862a0fd304a750e5893fbdc12`;
this is supporting evidence, not the exact final binary's long-duration test.

An earlier native filename-fix test on the old geometry completed track02 at
**2,037,191 / 2,037,191 frames**, then track03 at **2,048,413 / 2,048,413**, before
opening track07. Thus distinct original songs really reached EOF. The final
short r3 test verifies startup, controls and relaunch; it does not claim another
full-song cycle. Event timing describes decoded frames, with DMA playback lag
from mix-ahead. No subjective whole-OST audio certification is claimed.

## Remaining work

Terrain is still coarse; roof gaps, terrain/structure joins and pier traversal
need further visual/collision work. Mesh fidelity costs more than the old filled
hulls: the world-render stage dominates these profiles. Memory fits the 8 MiB
hunk but target hardware still needs the larger total Fast allocation.

Balmora, recall travel/effect, guards/Fargoth, dialogue, fighting, interiors,
activation, saves and the Escape menu are **not implemented**. Actual battle
state is absent; F8 only auditions music mode. Continuous world streaming and
the 68020/no-FPU build remain future work. See ROADMAP.md and
OPTIMIZATION_HISTORY.md; do not treat this checkpoint as closing those items.
