# Checkpoint-016: first interior and repeatable conversion stages

Runtime **v0.0.15-dev1**, source **0.12.0.dev1**, 27 September 2026.
Created by FlyingFathead a.k.a. Horstator. Thanks to ChaosWhisperer.

## Delivered scope

The image starts in a separately loaded prison-ship interior, with offline dim
lightmaps, hollow shell collision and a bidirectional E hatch link to the deck.
One scene is resident. Music retains its track and play position across map
loads. This is not the opening quest: Jiub/guards, character creation, the Census
office, containers and persistent cell state remain future work.

Compact console text is the default; normal and retro fonts remain available.
Shift+physical grave / Shift+F10 toggles full/half console; PageUp/Down and
Shift+Up/Down scroll. `debug overlay off` and the other prefixes share the debug
master. XYZ now includes DEG heading and P pitch. Nord eye height is calibrated
from sampled camera/race data; collision width and Quake bob are preserved.

Default 3D hands draw after world fog with a brightness floor. A separate
compile-time sprite experiment preserves the 3D pipeline and original model.
Some sprite animation frames move offscreen and lighting is fixed: it is not
complete appearance coverage or a blanket hand-flicker fix.

## Host checks and source integrity

**92 host tests pass** against the final native source. New coverage includes
actual console-buffer reflow/partial lines/scroll anchoring; bounded scene links,
state restoration, safe arrivals and rejected use; bounded sprite input;
constant-UV lighting, hollow collision and software pose rasterization; and a
24,000-node hull chain using a 256 KiB host stack. Guided-build tests check that
interior output and the selected hand mode feed the image stage consistently.
Fixtures are synthetic and include no commercial data.

The new private build receipt records recipe/mode, stage commands/timing/logs,
input SHA-256 for installed files and tool/source fingerprints. It is not a
hermetic build environment. Current exterior/NPC stages are reused from the
preceding conversion; new hands/interior stages and both final native/image
builds were run for this checkpoint. A completely fresh full-install guided AGA
build was not repeated end to end. See CONVERSION_RECIPES.md.

## Failed trials and diagnosed limits

- `interior016-native-r1`: convex shell collision filled the room; movement was
  blocked. Later input automation also lost track of console state after map
  loads. A subsequent 80000025 failure has no isolated cause; this is not a pass.
- `interior016-native-r2`: hollow thin-prism collision exposed deep same-side
  hull recursion; the image failed at boot with 80000004. Iterative same-side
  descent boots the same geometry. Split-segment recursion remains bounded by
  input topology, not eliminated wholesale.
- `interior016-native-r3`: boot/walk worked, but console/map automation was invalid.
- `interior016-native-r4`: direct scene loads and music progression passed. E
  activation did not: the diagnostic camera stayed inside the hatch and noclip
  could not be disabled, so E meant vertical flight. Final routes correct this.
- A scene-use fixture caught null AngleVectors outputs; the inherited routine
  requires real output vectors. Final executables include the correction.

All failed runs remain labeled in private evidence. Later screenshots after a
failure are not counted as acceptance. No hidden specification or memory increase.

## Final native routes

Main **3D**: `interior016-native-r5`, engine build r6, image r4.
Experimental **sprites**: `interior016-native-r6`, engine r7, image r5.
Both: fresh boot, walking from spawn, hands visible, compact/full/normal console,
scrollback, overlay off/on, direct town/ship loads, E exit to deck, E re-entry,
eye-height readout, Escape menu and confirmed clean Exit to DOS/restart reminder.

Both E tests first place a controlled camera using noclip, then return to walking
before E. The arrival floor checks ground the player at approximately (695,-486,74)
outside and (18,27,48) inside. This isolates linked activation; it does not certify
the entire stairs/companion-guided opening route. The native fullscreen test uses
Shift+F10, not an actual Finnish host keyboard. No ERROR.TXT was produced in either
final run. The harmless existing `aw_hull is not a field` load warning remains.

Each final run records four scene leave/enter pairs with the same track ID and
strictly increasing played-frame position. Main map-ready durations were
275, 239, 277 and 228 ms on this accelerated host/emulator. These are not physical
drive timings. Neither short run reaches natural track completion; prior music
shuffle/full-song tests remain the evidence for that unchanged behavior.

| Counter | Default 3D | Experimental sprites |
| --- | ---: | ---: |
| Frames | 2528 | 2649 |
| Elapsed ms | 147086 | 147006 |
| Surface overflow frames | 0 | 0 |
| Edge overflow frames | 0 | 0 |
| Maximum surfaces | 6600 | 6600 |
| Maximum edges | 12422 | 12422 |
| Hunk bytes at exit | 7908112 | 7930528 |
| Free Chip bytes | 1796432 | 1796432 |
| Free Fast bytes | 5048544 | 5047584 |
| World ms | 89733 | 85118 |
| Entities ms | 204 | 238 |
| C2P ms | 327 | 348 |
| Hands ms | 940 | 55 |
| Audio late updates | 2 | 4 |
| Missed audio frames | 9325 | 8835 |
| Warmup missed frames | 2842 | 2966 |
| Worst frame us | 994598 | 1011058 |

Both music profiles: 804 read slices / 3,293,184 bytes; zero read errors. Audio
still misses deadlines. Do not infer glitch-free playback from successful reads.
Routes include console/hidden-hand time and nondeterministic host timing, so
hands_ms is diagnostic evidence, not a matched per-visible-frame FPS gain.
The sprite span allocation raises hunk use while avoiding the 3D hand cache
load; hunk alone is not total working-set cost. Heap reservation stays 9 MiB
within the same 16 MiB Fast configuration. World rendering still dominates.

## Exact environment

FS-UAE **3.1.66**, A1200/AGA/PAL, **68040-NOMMU**, internal 68040 FPU, JIT/max
(resolved cache 8192), 2 MiB Chip + 16 MiB Z3 Fast, 24-bit addressing disabled,
keyboard joystick off. No Workbench desktop. WinUAE preset is guidance, not a
local WinUAE test. No physical-Amiga or stock-A1200 performance claim.

ROM: Kickstart 3.1 A1200 **40.68**, 524,288 bytes, SHA-256:
`6d43840d4099a74170ea0f0425b6257c3891ebcaa39c4d1840075a9ab22b5707`.
FS-UAE executable SHA-256:
`b729fe233a6507daed7fea6fbe8cfc417da523239d4a43037dd57203858e4f37`.
AmigaPorts GCC 16.2-rc11 / 16.2.0b20260825082934, 68040/FPU.
AmiQuake commit `9c62d905151614af3e788ae3145a0d4ecc8a7bb8`;
archive SHA-256 `43353034beb2a43b1af82c735f93c0a8bee8129c1b93d7ba152dd8e60ad3721c`.

Both HDFs: 134,250,496 bytes, 128 MiB FFS partition in RDB, 18 music tracks.
Image construction read back every payload and checked FFS root metadata.

| Artifact | SHA-256 |
| --- | --- |
| Default HDF | `5c0af6b7b8de3c291f89c63b81c42faf338cb4e256278c74189f6dfd8b37e81d` |
| Default executable | `8685c463e2f1be63054101e7068f0313e5a8477c617c5bdf3203d523dd32dd7d` |
| Sprite HDF | `a7c26652619ecdac742d887bb85d49183332f1da5841fa6033cae3ec26d41235` |
| Sprite executable | `b92d3226ff352f577f0b7ee85613f648e025952915112b696f99c66f9ff3274b` |
| 68000 preflight | `072e0f766078ca91492efc58852b3aa27e6408bb39a563eb28a3057da0adfcab` |

## Still open

Exterior ship deck/bow gaps, detached rail details, the house near (-41,715,69)
and terrain/rock formation near (235,596,29) need source/topology/coverage checks.
No geometry fix for those reports is claimed here. Joined-plank pier and distant
building backdrops are planned A/B recipes. Census office, opening actors,
NPC collision/wandering, combat, inventory, dialogue and save/load remain upcoming.
Owner acceptance is pending. See PLAYTEST_STATUS.md and ROADMAP.md.
