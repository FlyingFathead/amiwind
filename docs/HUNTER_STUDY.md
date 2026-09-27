# Hunter as an optimization study

Inspiration suggested by the project owner:
[Timo Heimonen's Hunter 68060 Performance Patch](https://github.com/timoheimonen/amiga-hunter-performance-68060).
Reviewed its README, PATCH.md and changelog for version 1.1.0 on 27 September
2026. This project does not bundle Hunter code, game files or the patch.

The patch documents instruction-cache support, removal of self-modifying calls,
moving CPU data to Fast RAM, a terrain delta table, exact constant divisions,
perspective-result reuse, specialized polygon span loops and removal of per-row
calls in trapezoid fills. It also bounds terrain reads and object queues.

Its target is a 68060/Blizzard 1260 configuration with Kickstart 3.1, 2 MiB Chip
RAM and accelerator memory. Its cache/Fast RAM gains cannot be assumed on our
stock 68000 with 512 KiB Chip + 512 KiB slow RAM. The patch's own 1.1.0 notes say
no speed improvement was measured for that release; it is not evidence for a
particular A500 frame rate.

Useful experiments for this demo are reducing per-sample work, precomputing
bounded functions on the PC, reusing projection results, comparing CPU/blitter
span thresholds and measuring bounded visibility sets. Our height-projection
and row-offset tables follow these general optimization ideas, independently
implemented for the heightfield renderer. Always compare image correctness as
well as time; a faster incorrect fill is a regression.

Sources: [patch details](https://github.com/timoheimonen/amiga-hunter-performance-68060/blob/main/PATCH.md)
and [changelog](https://github.com/timoheimonen/amiga-hunter-performance-68060/blob/main/CHANGELOG.md).
