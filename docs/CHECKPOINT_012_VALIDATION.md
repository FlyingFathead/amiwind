# Checkpoint-012: first actors and scaled movement

Runtime **v0.0.12-dev1**, public pipeline **0.9.0.dev1**, 27 September 2026.
Created by FlyingFathead a.k.a. Horstator. Thanks to ChaosWhisperer.

## Delivered scope

- Dressed Fargoth and two Imperial guards at original exterior references.
  Two shared MDL appearances, eight sampled idle frames each, no runtime bones.
- E auditions a generic original greeting with subtitle and a shared cooldown.
  This is not original proximity AI, full dialogue filtering or the ring quest.
  The actors are nonblocking and have no walking/combat AI.
- Player standing box 14.64 x 14.24 x 33.25 at the imported world scale, replacing
  Quake's oversized 32 x 32 x 56. Matching world and building hulls are rebuilt.
- Ground support prevents idle slope drift and follows mild slopes. Step-up
  is 8.5; descending support 8.75. Tilted risers can request stepping, and the
  step-down code restores grounding using the hit object's solidity.
- Quake camera bob is preserved; `view.c` is byte-identical to dev4. Music,
  Paula playback, fog and the repaired door-depth code are also byte-identical.
- Nord first-person bare hands and punching animation are on the roadmap.
  They are not included in this executable.

## Build and automated verification

64 tests passed with the actual patched runtime source available to the host
compiler. New checks cover support/idle drift, uphill speed, downward steps,
cliff departure, jumping/swimming, affine hull-plane limits, unchanged visual
BSP lumps, alias animation bounds and rejection of unsupported dialogue rules.
The ground-support fixture uses synthetic traces and a simple movement stub;
it does not replace native staircase testing. No original assets are in tests.

Engine: pinned terriblefire/amiquake commit
`9c62d905151614af3e788ae3145a0d4ecc8a7bb8`, AmigaPorts GCC 16.2-rc11 bundle,
compiler 16.2.0b20260825082934, 68040/68881, independent C2P and GPL C spans.
The qcc, ericw-tools v0.18.1 and image recipes are recorded in LINUX_BUILD.md.
The new host NPC stage is part of the guided AGA build and can run separately.

## Native acceptance

FS-UAE **3.1.66**, A1200 model, AGA/PAL, **68040 + internal FPU**, **2 MiB Chip
+ 16 MiB Z3 Fast**, JIT enabled, maximum CPU speed, 24-bit addressing off,
no keyboard joystick. Licensed A1200 Kickstart 3.1 **40.68**, 524,288 bytes.
No Workbench desktop. WinUAE was not executed locally; its supplied preset is
configuration guidance. This is not a stock-A1200 performance result.

The harness copies the pristine HDF before booting. Final run `startup012-dev1-r2`:

1. Untouched startup and WASD, before any recovery/noclip. Initial recorded
   position stayed exactly (-16,44,60) throughout the idle portion, then moved
   with all four directional inputs.
2. Noclip used only to place a repeatable test start near the staircase at
   (-109,321). It was disabled before walking. The player settled at
   (-62,320,75.12), walked up to (-157.62,320,99.37), remained stationary during
   the rest interval, then walked down to approximately (-68.37,319.37,74.87).
   Jump/landing and grounded recovery were also exercised.
3. Both guard greeting/subtitle triggers and Fargoth's trigger were observed.
   Native captures show assembled clothes/armour and idle models. Host previews
   inspect four sides of each appearance; native frames demonstrate the model
   path and frame changes. This is a coarse first bake, not final art quality.
4. Normal Escape exit completed with profile files and shell return. The pristine
   deliverable was not used as the writable test disk.

Final run: 3,350 frames / 142,918 ms, zero surface/edge overflow, zero music read
errors. Hunk use 6,344,288 bytes (dev4: 6,304,688, delta 39,600); alias model
caches are additional, so that delta is not total NPC memory. Free memory at exit:
1,796,432 Chip and 6,083,360 Fast bytes. Fargoth MDL 197,688 bytes / 448 triangles;
shared guard MDL 204,940 bytes / 497 triangles. Each has a 512 x 256 indexed skin.

Measured accumulated stages: world 124,641 ms, entities 2,253 ms, C2P 431 ms,
audio work 18 ms. Views differ from dev4, so these are not controlled comparative
FPS measurements. World rendering remains the dominant measured work.
Two late audio updates remain, one during warm-up. No claim of glitch-free
playback. This short run did not reach a natural song transition; unchanged
shuffle/history code and earlier full-song evidence remain the basis for that
feature. Greeting tests use the existing effect mixer over streamed music.

## Hashes

| Artifact | SHA-256 |
| --- | --- |
| Kickstart 3.1 A1200 40.68 | `6d43840d4099a74170ea0f0425b6257c3891ebcaa39c4d1840075a9ab22b5707` |
| FS-UAE executable | `b729fe233a6507daed7fea6fbe8cfc417da523239d4a43037dd57203858e4f37` |
| Pristine HDF | `fa416d4e533e90d03c46e96f83e05fa899aff096c45d66ceef3c7a0ddc67354a` |
| AmiWind executable | `3f69cf00abba1e36e3e98a453db31901560fa034c2d13ce3471d4b49a12bfbd1` |
| Preflight executable | `0f961598bd393fdc471bf1410a100539fe272ccdc49fae2a19e1005362757a73` |

The HDF is 134,250,496 bytes, with a 128 MiB FFS partition and 18 converted
installed music tracks. No ROM, executable, game assets or derived data are
included in the public source ZIP. Its corresponding runtime source is separate
from the GPLv3 host tools and retains upstream notices.

## Remaining limits

One tested staircase and a clear start do not certify every town collision proxy.
Architecture still uses approximate convex unions, including imperfect corners
and yaw-rotated expansions. Terrain/roof seams, coarse character skins, alias
lighting, unsupported outfits, resident world geometry and audio deadlines need
more work. NPC proximity polling, complete dialogue conditions, quests, combat,
Nord hands/punching, Balmora, interiors and saves remain on the roadmap.
