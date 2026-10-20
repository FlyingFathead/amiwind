# Crossing baseline: the time a CHIM cell crossing costs

_Last updated with AmiWind v0.0.45 (20 October 2026)._

The A side of every crossing comparison in the [v0.0.45 plan](../PLAN-v0.0.45.md#1-cell-crossings) (step 1.1),
for [CHIM-CROSSING-SLUGGISH-43](../bugs/CHIM-CROSSING-SLUGGISH-43.md): walking from one CHIM cell into the next
pauses the game, worst at corners. This page says how a crossing is measured, on which route, and what the
v0.0.44 and v0.0.45 release images measure at 16 MB and at 128 MB of Fast RAM. Nothing here changes the game: the
numbers come from the engine's own counters and logs.

## The route

`tools/crossing_route.py` holds the route as data and drives it (`crossing_route.py route` prints it). Every leg is
a level flight (noclip, the engine's default speed, about 450 units a second, original Morrowind units) at a fixed
height above the highest ground of the leg, at 12:00 with the clock held and the headlamp off.

| Leg | Region | Kind | What it crosses |
| --- | --- | --- | --- |
| ai-c1 | Ascadian Isles | corner | corner 3,-6: cell 2,-7 to 3,-6 |
| ai-c2 | Ascadian Isles | corner | corner 4,-5: cell 3,-6 to 4,-5 |
| bc-c1 | Bitter Coast | corner | corner -3,-4: cell -4,-5 to -3,-4 |
| bm-c1 | Balmora | corner | corner -4,-3: cell -5,-4 into the Balmora frame |
| ai-l1 | Ascadian Isles | corner-loop | a square around corner 3,-6 (cells 2,-7 / 3,-7 / 3,-6 / 2,-6) |
| bm-l1 | Balmora | corner-loop | a square around corner -4,-3 (cells -5,-4 / -4,-4 / the Balmora frame / -5,-3) |
| ai-e1 | Ascadian Isles | edge | cell 2,-6 to 3,-6 |
| ai-e2 | Ascadian Isles | edge | cell 3,-6 to 3,-5 |
| bc-e1 | Bitter Coast | edge | cell -5,-5 to -4,-5 |
| bc-e2 | Bitter Coast | edge | cell -4,-5 to -4,-4 |
| bm-e1 | Balmora | edge | cell -5,-2 into the Balmora frame |
| bm-e2 | Balmora | edge | the Balmora frame out to cell -1,-2 |

Light legs cross between one-cell frames of the open world; the Balmora legs enter or leave the town frame (nine
cells, its residents and doors in one frame). A corner leg flies diagonally through the point where four frames meet;
a corner loop flies a square of 1,300 units around a corner, the way a player walking around a corner leaves and
enters frames in quick succession (four crossings in about 11 seconds).

## How it is measured

- One FS-UAE session per memory size and engine: A1200 with a 68040, the JIT preset, 2 MB Chip RAM and 16 MB or
  128 MB of Zorro III Fast RAM, on a fresh writable copy of the game image (never a sealed disk).
- Each leg: teleport to its start (640 units before the border or the corner), rise straight up to the leg's height,
  wait until the CHIM streamer is settled (two seconds in a row with no chunk read and no frame-world update), then
  fly across. Every leg is flown three times in a row. The last session of a series repeats the first one as the
  drift control.
- Per crossing, from the engine itself (no extra instrumentation):
  - **Ready**: from the crossing's start to the player standing on the new frame (`Scene ready: MAP, N ms`).
  - **Worst frame of the crossing**: the longest rendered frame in the three seconds from the switch (the renderer
    counter's per-second peak, `dbg rcount`; `frame-stalls.csv` lists every frame over 100 ms as a cross-check).
  - **Worst frame of the approach**: the longest rendered frame of the flight before the border.
  - **Sections** (`cell-load-profile.tsv`, `cell-visible-profile.tsv` and `chim_debug 1`): the map file read and
    parsed, the entity spawn, the rest of the server spawn, the CHIM ring loaded around the arrival point (`CHIM:
    primed`), the rest until the player stands, and from there to the first drawn frame.
  - **Counts**: map file bytes and reads, the bytes and reads of the CHIM ring, surface-cache texels drawn in the
    three seconds after.
- Emulator times are relative ([BENCH-JIT-PROFILE-32](../bugs/BENCH-JIT-PROFILE-32.md)): the bytes, reads and
  texels are the main currency; times are compared only inside one series on a quiet host.

Rerunning it: the session runs inside the FS-UAE container with the play copy, the Kickstart file and an output
folder (`crossing_route.py session --hdf PLAY.hdf --kickstart KICK.rom --fast-mb 16 --out DIR`), then
`crossing_route.py parse DIR --json RUN.json` and `crossing_route.py table RUN.json ...` give the tables below.
Where a leg's start has no standing surface, the session moves the start back along the leg 256 units at a time
(the same on every run); two legs (ai-e2, bm-e1) start this way today.

Limits of the route, plainly:

- The legs fly at a fixed height above the highest ground of the leg, and the fog hides most of the ground from
  there: the approach frames draw mostly sky and fog, so the worst frame of the approach (about 50 ms) is lighter
  than on foot. A walking route on the ground is still to come.
- The crossings are noclip flights, so no collision or actor work runs on the way.
- Repeats fly the same border again within a minute, so the second and third repeats find more of the world
  cached; the first repeat of each leg is kept apart in the run files. On the v0.0.44 image the repeats differ by a
  few percent; on v0.0.45 at 128 MB the first visit to Balmora is about twice the later ones.

## Results, 20 October 2026

The v0.0.44 release image (A) against the v0.0.45 release image (B, the read-ahead into spare Fast RAM and the heap
sized from the free RAM). FS-UAE JIT preset; one session per image and memory size, 42 crossings each (36 straight
legs, 3 of each, and 6 corner loops of 4); medians over all repeats, worst in brackets, in ms. Host load was
recorded every 30 seconds; the sessions in the table ran without other work on the host. The v0.0.44 128 MB session
was run again at the end as the drift control: 3 to 12 % faster than the first run, Balmora corner the same.

| Crossing | A, 16 MB | B, 16 MB | A, 128 MB | B, 128 MB |
| --- | --- | --- | --- | --- |
| Light area, edge: ready | 448 (535) | 422 (502) | 293 (337) | 123 (152) |
| Light area, edge: worst frame | 278 (295) | 238 (250) | 201 (252) | 67 (130) |
| Light area, corner: ready | 537 (668) | 515 (610) | 367 (395) | 123 (148) |
| Light area, corner: worst frame | 304 (412) | 277 (356) | 262 (277) | 66 (86) |
| Light area, corner loop: ready | 509 (525) | 473 (582) | 339 (346) | 117 (126) |
| Light area, corner loop: worst frame | 275 (293) | 242 (261) | 251 (260) | 62 (70) |
| Balmora, edge: ready | 665 (901) | 658 (946) | 650 (913) | 201 (224) |
| Balmora, edge: worst frame | 474 (753) | 480 (737) | 509 (815) | 134 (148) |
| Balmora, corner: ready | 879 (1,029) | 825 (1,006) | 822 (1,021) | 223 (469) |
| Balmora, corner: worst frame | 762 (906) | 709 (889) | 751 (930) | 154 (393) |
| Balmora, corner loop: ready | 563 (926) | 550 (864) | 378 (786) | 145 (239) |
| Balmora, corner loop: worst frame | 368 (759) | 349 (713) | 286 (707) | 76 (162) |
| Worst frame of the approach, all legs | 44 to 48 | 43 to 49 | 46 to 59 | 42 to 48 |
| Ring read at the arrival, light frame | 4.1 MB, 857 reads | 4.1 MB, 857 reads | 3.2 MB, 636 reads | 8 KB, 2 reads |

What the numbers say:

- **With 128 MB, v0.0.45 cuts a crossing to about a third**, more than the "about half" the v0.0.45 notes
  first claimed (corrected there on 20 October 2026): light-area crossings from 293 to 367 ms down to 117 to 123 ms, Balmora from 650 to 822 ms down to 201 to
  223 ms; the worst frame of a light crossing from about 200 to 260 ms down to about 65 ms. The ring and the world
  index come from RAM: about 8 KB read at a light arrival instead of 3.2 MB.
- **With 16 MB, v0.0.45 changes little**: 1 to 7 % faster (no spare RAM to read ahead into).
- **Corners:** on v0.0.44 a corner costs about a quarter more than an edge, on v0.0.45 the same. A diagonal corner
  crossing switches once, straight into the diagonal frame, not through the neighbours; a corner loop (four crossings
  in 11 seconds) costs per crossing about what an edge does.
- **The first entry into Balmora** in a v0.0.45 session at 128 MB took 469 ms, the later ones about 220 ms: the
  town's 4.7 MB frame map is read once and then kept in RAM.

Where the time goes, part by part, is in [Cell crossings](../chim/CELL_CROSSINGS.md#what-a-crossing-costs-today).

The first measurements (19 October 2026, the same image A, an earlier version of the route with longer flights and
one session per repeat) gave the same picture: 128 MB light edge 301 ms, light corner 360, Balmora edge 693,
Balmora corner 804; 16 MB 526, 619, 803, 841.
