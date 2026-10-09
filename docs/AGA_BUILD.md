# AGA checkpoint build and controls

Published v0.0.27 includes detailed Seyda Neen and Balmora, the island's
2,526 terrain regions, 37,960 exterior rocks and 816 giant mushrooms. Other
settlements and wider gameplay remain incomplete. See [current scope and
validation limits](RELEASE-v0.0.27.md). The A500 runtime remains a separate
experiment; this accelerated AGA profile is not stock-A1200 performance proof.

<!-- contents start -->
## Contents

- [Reference configuration](#reference-configuration)
- [Controls](#controls)
- [Console and getting unstuck](#console-and-getting-unstuck)
- [Host conversion](#host-conversion)
- [Runtime build](#runtime-build)
- [Correctness regression checks](#correctness-regression-checks)
- [Checkpoint-016 interior and hand variants](#checkpoint-016-interior-and-hand-variants)

<!-- contents end -->

## Reference configuration

Tested with FS-UAE 3.1.66, A1200 model, 68040/FPU, 2 MiB Chip, 16 MiB 32-bit
Fast memory, Kickstart 3.1 A1200 revision 40.68,
JIT and maximum CPU speed.
JIT results describe this emulator setup only. The current executable requires
an FPU. A 68020/no-FPU trial exists but does not boot from our bare-ROM setup
without an additional math library; stock A1200 playability is unproven.

The small 68000 preflight checks the hardware and free memory before loading
the engine. It reports a clear failure and stops the startup script if unsuitable.
Use 2 MiB Chip and 16 MiB Fast; the 4 MiB Quickstart preset is too small.
See [WinUAE setup](WINUAE.md) for panel-by-panel instructions and
[FS-UAE playtesting](FS-UAE-PLAYTESTING.md) for the Linux recipe/preset.

The image boots through the versioned preflight into the logo and main menu.
It does not load the Workbench desktop or use icon tooltypes. The executable
no longer links `icon.library` or closes/reopens Workbench. It still uses AmigaOS libraries,
filesystem, devices and screen management. Skipping the desktop does not
remove those dependencies. This AGA executable does not support Kickstart 1.3.

Private playable builds can span multiple RDB HDFs. Use the generated
configuration and mount every disk listed in the build summary simultaneously,
with the boot disk first. WinUAE uses RDB hardfiles on the UAE controller with
their stored geometry. The dated [Windows tests](VALIDATION-WINDOWS-2026-10-02.md)
and [v0.0.27 record](RELEASE-v0.0.27.md) distinguish game-entry checks from later
build/readback results and still-pending target acceptance. Use working image
copies: exiting the game writes profiling files to their filesystems.

## Controls

| Input | Action |
| --- | --- |
| J / M | Journal / world map during unrestricted gameplay |
| W / A / S / D | Forward / strafe left / back / strafe right |
| Mouse | Look; click inside the emulator window to capture |
| Left / right arrow | Turn |
| Shift | Run |
| Space | Jump; upward swim input when submerged |
| Shift+V | Cycle requested draw distance: 450 / 540 / 1000; region exteriors cap at 540 |
| Shift+F5 / Shift+F6 | Previous / next song in playback history, then shuffled selection |
| F6 | Next song (legacy alias) |
| F8 | Audition battle/exploration music mode; not combat detection |
| F10 or physical key left of 1 | Open/close development console; usually § on a Finnish host layout |
| Shift+§ / Shift+F10 | Toggle full-height / half-height console |
| PageUp / PageDown | Console scrollback; Shift+Up/Down fallback |
| Escape | Close console if open; otherwise open/close the menu |
| F | Draw / sheath Nord unarmed hands |
| Mouse1 | Visual punch while hands are drawn; no damage yet |
| E, while walking | Use a nearby ship hatch, otherwise audition a visible NPC greeting |
| E / Q, in noclip | Move up / down |

Quake physics supplies walking, gravity and jump/water primitives. This is not
a conversion of Morrowind's movement or combat rules. Terrain and building
collision are approximate. Converted town NPCs have bounded idle/greeting and
dialogue behavior. They do not implement the complete original quest, combat or
AI systems. Converted town interiors use the documented door links. See
[player movement](PLAYER_MOVEMENT.md) and [current state](PROJECT_STATE.md).

To quit, open the Escape menu, choose Exit and confirm. Wait for the shell
prompt and filesystem writes to finish. Type
`amiwind` and press Enter to restart. Run `AmiWindCheck` separately to print the versioned hardware/memory
checks again. The menu supports New Game and character save/load; Options → Graphics is active.
See [hands/menu reference](OPENMW_REF_CONTROLS_MENU.md) and
[debug overlays](DEBUG_OVERLAYS.md).

## Console and getting unstuck

F10 is the fallback when the emulator or host keyboard layout does not deliver
the Amiga grave key (raw key 0). Type `dbg help`, then Enter, for available commands.
`dbg coords on` enables the live XYZ/DEG/pitch strip. The image starts inside the
ship; `dbg scene town` and `dbg scene ship` are direct diagnostic loads. `debug` and `amiwind debug`
are equivalent space-separated prefixes; old underscore commands still work.
`noclip` or the Morrowind-style alias `tcl` toggles collision. WASD/mouse moves;
E/Q rises/descends; W/S now follows camera pitch and Shift boosts flight speed.
`dbg reset location 0` recalls the validated town spawn. Leave solids before disabling noclip: the runtime rejects
that transition if the standing hull is obstructed. `aw_recover` returns to the
scene's spawn and restores walking; `aw_pos` prints coordinates.
`aw_npcs` prints positions, facing yaw, automatic/manual greeting counts and
rearm state. `aw_blockers` traces the standing hull in eight nearby directions
and prints the hit model, fraction, start-solid flags and contact normal. If a
spot remains sticky, record `aw_pos` and `aw_blockers` there. This diagnostic
does not run per frame and does not alter collision.

`aw_view x y z yaw pitch` places a reproducible diagnostic camera while noclip
is enabled. `aw_probe` runs 441 floor sweeps and writes `collision-probe.csv`.
The latter stalls the game and is not a normal performance workload. Use
`aw_cull 0/1` and `aw_fog 0/1` to isolate distance rejection from shading.
These are development tools, not save/load or final Morrowind controls.
**E** activates the targeted door or resident in the implemented interaction
slice; see [the maintained keymap](KEYMAPS.md). Full gameplay remains incomplete.

## Host conversion

Use the guided [Linux builder](LINUX_BUILD.md), which checks dependencies and
runs setup, terrain, scenery, mesh conversion, music, engine and image assembly.
Inputs and generated outputs must stay outside the public source checkout.
The manual chain below records the earlier bounded-scene experiment. Use the
guided full-content recipe above for a current complete build; these individual
commands are a reference for the conversion stages after setup and terrain:

```sh
python tools/prepare_scenery.py --workspace ../morrowind-amiga-workspace --out ../scenery
python tools/prepare_quake.py --workspace ../morrowind-amiga-workspace --scene ../scenery --out ../alias-scene
python tools/prepare_mesh_bsp.py --scene ../alias-scene --scenery ../scenery --out ../mesh-scene --qbsp /tools/qbsp --vis /tools/vis --light /tools/light
python tools/prepare_npcs.py --data-files '/owned/Morrowind/Data Files' --scene ../mesh-scene --out ../npc-scene
python tools/prepare_hands.py --data-files '/owned/Morrowind/Data Files' --scene ../npc-scene --out ../hands-scene
python tools/prepare_dialogue_lookup.py --data-files '/owned/Morrowind/Data Files' --out ../voice-lookup.json
python tools/prepare_music.py --data-files '/owned/Morrowind/Data Files' --out ../music
```

In that earlier bounded-scene recipe, the converter read base-game static NIF
assets using PyFFI and wrote
shared BSP submodels with 64-pixel material textures and original UV mappings,
plus separate approximate multipart collision. Variants bake scale and pitch/
roll; placements carried position and yaw. That experiment used foliage
sprites and reported 155 placements / 55 model variants, three NPCs and Nord
hands. These are historical example counts, not current world/gallery coverage.
The current planned foliage policy retains mesh foliage in detailed Balmora;
see the [roadmap](ROADMAP.md#follow-up-static-asset-gallery-and-remaining-scenery).
An OpenMW-based backend remains future work. The guided build also exports a
private ordered [voice lookup](DIALOGUE_LOOKUPS.md); it is not loaded by the runtime yet.

## Runtime build

The complete native source is `engine/aga/` within the single `amiwind/` checkout.
Its upstream baseline is AmiQuake revision
`9c62d905151614af3e788ae3145a0d4ecc8a7bb8`; no separate archive is needed to build.
Use AmigaPorts GCC 16.2-rc11 / compiler 16.2.0b20260825082934.

```sh
python tools/build_aga.py engine --sdk /external/m68k-amigaos-gcc-16.2 --out ../engine-build
python tools/build_aga.py image --scene ../hands-scene --music ../music --engine ../engine-build/runtime/build/AmiQuakeGCC --out ../image-build --qcc /tools/qcc-host --qbsp /tools/qbsp --vis /tools/vis --light /tools/light --xdftool /tools/xdftool --rdbtool /tools/rdbtool
```

The engine compiles without warnings, and the build enforces it: `build_aga.py
engine` fails if the compiler prints any warning. This covers the 68040 and
68020 builds, both hand renderers and builds without the brightness controls.
`--allow-compiler-warnings` turns the check off for local experiments only.
Do not add `-Wno-*` flags to hide a new warning; fix the cause.

The SDK vasm assembles the independent 68000 boot checker and the FPU support
library loader `AmiWindFPU`; the renderer uses no extracted assembly. An optional
`--bootcheck` image argument selects the checker's binary; otherwise the builder
expects `AmiWindCheck` (and `AmiWindFPU`) beside the engine.

`--amiga-libs DIR` (optional) copies your own `68040.library`/`68060.library`
from your Workbench or accelerator installation into `LIBS:` on the boot disk;
the startup sequence then opens it before the boot check. See
[FPU support library](FPU_SUPPORT_LIBRARY.md).

The runtime uses GPL C span drawing and an independent C2P routine. Assembly
identified upstream as extracted from a binary is excluded. Build outputs and
all game-derived results stay external. The image builder validates all music
streams and reads every payload back from the finished RDB image before success.
No ROM or Workbench disk files are copied by this builder, except the FPU
support library you select yourself with `--amiga-libs`.

The image builder also writes the night lighting tables (`id1/world/lamps.awl`,
`night-windows.txt`, `fog-locations.txt`); their scenery sources and receipt
are described in [night lighting tables](LINUX_BUILD.md#night-lighting-tables).

All 18 installed base-game music files are stored on the private image.
Exploration and battle use separate shuffled groups, excluding title duplicates.
The player uses two 16 KiB PCM buffers and cooperative 4 KiB read slices; each
individual disk read is still synchronous. Playback feeds a bounded stereo DMA
ring. Special-event tracks are stored but not triggered by gameplay yet.
See [music behaviour](OPENMW_REF_MUSIC_AND_AUDIO.md) and
[checkpoint-010 validation](CHECKPOINT_010_VALIDATION.md) for full-song evidence,
remaining startup/deadline limitations and exact binary/image hashes.

BSP input is loaded one section at a time to reduce temporary memory, but the
decoded world remains resident. This is not continuous world-cell streaming.

## Correctness regression checks

```sh
python3 -m unittest discover -s tests -v
```

The native-source fixtures compile the actual collision, surface ordering and
culling routines with a host C compiler and synthetic geometry. They use the bundled source by default; a missing host C compiler causes an
explicit skip. Set AMIWIND_RUNTIME_SOURCE only to compare another source tree. Filesystem fixtures need
no commercial data. HDF creation normalizes and checks the reserved legacy root
field; the emulator validation also forces bitmap revalidation. See
[the filesystem record](FILESYSTEM_REVALIDATION.md).

## Checkpoint-016 interior and hand variants

The guided build now runs `prepare_interior.py` after `prepare_hands.py`. Build
the HDF from the resulting `interior-scene` to include both maps and hatch links.
See [ship interior](SHIP_INTERIOR.md) for the bounded preview and
[conversion recipes](CONVERSION_RECIPES.md) for repeatability and provenance.

`build.sh --hands 3d` is the default. `--hands sprites` selects the experimental
Nord-unarmed span renderer at compile time and propagates that choice to image
creation. There is no runtime renderer switch; the original 3D converter and
model remain intact. See [first-person hands](FIRST_PERSON_HANDS.md).

Checkpoint-017 debugging: `dbg scene change` opens the scene picker. Escape →
Options → Graphics provides live exterior fog/draw distance; arrows step10,
Shift+arrows step1. `dbg fog distance 675` sets an exact value, `dbg fps on`
shows the once-per-second frame-rate estimate. Default is540; counter off.
