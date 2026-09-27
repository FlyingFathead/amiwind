# Doom, DoomAttack and AmiQuake rendering study

Reviewed 27 September 2026. These are useful examples of software 3D on Amiga.
The goal is to adapt useful techniques to the 68000/OCS experiment and an
expanded 040/FPU/AGA renderer. The latter is an accepted option, not yet tested. No code or binaries from these projects are included here.
The existing [Hunter study](HUNTER_STUDY.md) remains relevant to simple geometry.

## Source observations and experiments

| Source inspected | What the code does | Experiment for this project |
| --- | --- | --- |
| Doom `r_bsp.c`: `R_RenderBSPNode`, `R_CheckBBox`, wall clipping | Visits the near subtree first and rejects hidden screen ranges before processing the far subtree | Bake small spatial groups on the host, reject groups outside fog/view bounds, then draw visible near objects |
| Doom `r_draw.c`: `R_DrawColumn` | Uses row-address tables, fixed-point texture stepping and a palette lookup inside a simple column loop | Compare a few baked texture-column variants against the current flat terrain spans |
| Doom `r_things.c`: `R_ProjectSprite`, `R_DrawMaskedColumn` | Projects sprites, selects a view, clips their opaque column runs | Bake tree/NPC sprites with transparent runs; combine them with terrain occlusion |
| Doom `r_plane.c`: `R_MapPlane` | Reuses row calculations for matching plane heights | Precompute repeated projection/scaling work on the host or once per view |
| DoomAttack 020/blitter C2P plugin | Separates CPU work from blitter-assisted chunky-to-planar conversion, with explicit synchronization and buffer constraints | Benchmark a small chunky viewport against our direct planar renderer; count the conversion cost separately |
| AmiQuake `d_surf.c`: `D_CacheSurface` | Reuses prepared surfaces when texture and lighting state still match; supports mip levels | Store prelit, reduced-resolution variants on disk and retain only nearby working sets in RAM |
| AmiQuake `d_scan.c` | Sets up gradients outside pixel loops and subdivides perspective work into spans | Use bounded fixed-point interpolation for a small number of near textured faces |
| AmiQuake `vid_amiga.c`, `c2p8.s`, `Makefile` | Has explicit display buffers/conversion and a 68040/FPU build path | Keep renderer, display conversion and presentation timings distinct; verify A1200 separately |

These are implementation ideas, not measured speedups for our demo. Doom's map
representation and Quake's geometry pipeline differ from Morrowind's exterior
heightfield and placed models. Their visibility structures cannot simply be
applied to an unconverted Morrowind cell. Our host pipeline can prepare a smaller
representation that preserves recognizable places.

The first practical visual experiment is one tree with a few prescaled sizes,
opaque-run metadata and a stable ground anchor. Occlusion must be evaluated at
the object's depth: the final terrain horizon alone can incorrectly hide objects
in front of distant hills. Use a terrain depth/coverage record or interleave
object columns with front-to-back terrain sampling. A blitter can copy/mask the
prepared pixels; it does not choose perspective, visibility or scale for us.

## Target and licensing boundaries

AmiQuake's examined Makefile uses `-m68040 -m68881`; its README targets 040/060
hardware. Its NoFPU build is not thereby a stock 68000 build. Its extracted C2P
routine uses later-CPU addressing and targets eight planes. Treat it as a study
reference: permission to redistribute that extracted routine has not been
established here. Review individual files and dependencies before any code reuse.
The same file-by-file review applies to DoomAttack plugins and historical Doom
source distributions. Study access is not a project-wide redistribution licence.

Our A500 path uses native 68000 instructions and three terrain planes. A1200 can
be a comparison build using the same scene, assets and visual settings first.
Test boot/exit, OCS-compatible display setup on AGA, timing, input, audio and disk
access before raising colours, geometry, resolution or draw distance. Added Fast
RAM and accelerators are separate measured profiles; the A500 baseline remains.

## Pinned references

- [Doom source](https://github.com/id-Software/DOOM/tree/a77dfb96cb91780ca334d0d4cfd86957558007e0/linuxdoom-1.10): the four renderer files above.
- [DoomAttack source](https://github.com/mheyer32/DoomAttack/tree/9b8e2e8e2ef9b8be84688103664485bc1d52a67a/gnudoom): `plugins/Chunky2Planar/020_Blitter/c2p_020_blitter.s`, the 020 optimized plugin and `plugins/Include/c2p.h`.
- [AmiQuake source](https://github.com/terriblefire/amiquake/tree/9c62d905151614af3e788ae3145a0d4ecc8a7bb8): the files named above, `d_init.c` and `r_main.c`.
- [ADoom author documentation on Aminet](https://aminet.net/package/game/shoot/ADoom-1.3): describes ECS/EHB and AGA C2P support. ADoom source was not inspected in this checkpoint.

The inspected reference files stay in the external research workspace. Public
packages contain these notes and links, not imported renderer code.

The current translation design and static-model export are documented in
TRANSLATION_LAYER.md and SCENERY_FORMAT.md. LICENSING_AND_CREDITS.md records
the GPL-version and extracted-C2P provenance review before any source reuse.
