# Frame waits: disk, screen copy and buffer swap

_Last updated with AmiWind v0.0.61 (6 November 2026)._

<!-- contents start -->
## Contents

- [The fields](#the-fields)
- [Where they appear](#where-they-appear)
- [Reading them](#reading-them)
- [Recorded measurements](#recorded-measurements)

<!-- contents end -->

A slow frame is either the processor working or the game waiting. The Amiga chipset has no counter a program can
read that says how long it waited for the disk or the display, so the engine times its own waits, every frame, and
prints them on its frame lines.

## The fields

| Field | What is timed |
| --- | --- |
| `disk` | Time inside file calls: every file lookup by name (the search paths' locks and the opens), and every open, read and seek the engine makes. A call made inside another one (a read inside a lookup) is counted once. |
| `c2p` | The chunky-to-planar copy of the drawn frame into the screen bitmap in Chip RAM. |
| `vbl` | The screen buffer swap. The engine does not wait for the vertical blank in play: it swaps to the next of three buffers, so this stays near zero. A large value here would mean the system blocked the swap. |

Everything else in the frame is the processor's own work (game logic, drawing, sound mixing).

## Where they appear

- **Spike lines** (`chim spikes MS`): after the CHIM counters, `| disk 12.3 ms, c2p 8.1 ms, vbl 0.0 ms`, then the
  frame's file lookups.
- **Long frame lines**: every frame of 2 seconds or more prints, even with spikes off, for example
  `Long frame 12750 ms f42 seyda (disk 9864.4 ms, c2p 0.4 ms, vbl 0.1 ms): files 89 (1 missed), ...`.
- **`chim spikes report`**: the longest frame since the last report with its waits, and
  `waits in N frames (T ms): disk ..., c2p ..., vbl ...; the rest R ms` over every frame since the last report.

## Reading them

- `disk` close to the frame time: the frame waited for files. Look at the file names on the same line and at the
  stage that ran (a stage with large time but few lookups is reading an already open file, for example a table
  searched record by record).
- `disk` small and the frame long: the processor was busy; the stage times on the spike line name the work.
- `c2p` is a fixed cost per drawn frame; it grows with the screen size, not with the scene.
- `vbl` above a few milliseconds: the display held the frame.

Cost: two reads of the system's E-clock timer per timed call (a few microseconds each on a 68040), three numbers
per frame, nothing allocated. In an emulator with JIT the times are the emulated machine's clock; compare them with
each other, not with real hardware.

## Recorded measurements

### AmiWind v0.0.59-dev (commit 4d2b2269), 3 November 2026

- Setup: FS-UAE 3.1.66, A1200 AGA, 68040 with FPU, JIT, 32 MB Fast RAM, audio on; the v0.0.59-dev6 image
  (run 2026_11_03_v0.0.59-dev6_full-v0.0.59-dev6_7973537) with the engine of commit 4d2b2269 in place of its own
  (SHA-256 3ba1ee03eb52bb6ccbd623f620c857ef43f5d4f63bb6b054bdcb77b52e87218c). Session: Seyda Neen arrival, about
  10 s standing, then a short walk (8 s forward, 3 s left, 8 s forward), `chim spikes 300`.
- Session script SHA-256 b4fe0073c5033d25fbded6076cb462fa98dd560bf0e69112e6065e62d4e9d60a.
- Previous recorded line: none (first measurement of these counters).

| Frame | Total | disk | c2p | vbl |
| --- | ---: | ---: | ---: | ---: |
| Arrival, first long frame (f41) | 4,573 ms | 4,408.7 ms | 0.0 ms | 0.0 ms |
| Arrival, longest frame (f42) | 12,750 ms | 9,864.4 ms | 0.4 ms | 0.1 ms |
| Arrival, third long frame (f45) | 2,774 ms | 2,707.9 ms | 0.1 ms | 0.0 ms |
| Standing, residents walking (typical spike) | 501 ms | 482.1 ms | 0.0 ms | 0.0 ms |
| Walking (typical spike) | 372 ms | 353.1 ms | 0.1 ms | 0.0 ms |

Sums: the first 46 frames (arrival and standing) 33,679 ms, of which disk 29,647.9 ms, c2p 3.2 ms, vbl 0.7 ms;
the next 209 frames (the walk) 19,957 ms, of which disk 16,549.1 ms, c2p 14.9 ms, vbl 2.4 ms.

What it shows: the arrival's long frames are mostly file waits, not processor work, and the residents' walking step
(the `ambwalk` stage) spends almost all of its 300 to 800 ms per spike frame inside file calls, with few new files
looked up: it reads from files that are already open. The screen copy and the buffer swap are negligible here.

### AmiWind v0.0.61-dev1 (source 374d59b), 5 November 2026: residents' tables per area, on and off

- Setup: FS-UAE 3.1.66, A1200 AGA, 68040 with FPU, JIT, 32 MB Fast RAM, audio on, hard disks on the IDE controller;
  the delivered v0.0.61-dev1 image (run 2026_11_05_v0.0.61-dev1_full-v0.0.61-dev1_374d59b) with its own engine
  (SHA-256 e06a3897925238e4f043c772e944a8185a8c9dff97cf6393f39327b301e2f76b). The host was busy with other builds
  and checks (76 to 100 % CPU), the same for both variants of a session.
- What is compared: `aw_ambient_areas 1` (the default since v0.0.60: each area's walking-resident table read once
  when the place changes and searched in memory) against `aw_ambient_areas 0` (the island-wide table searched by
  seek and read). Both variants do the same work: the same arrival (`dbg scene seyda`, 60 s), 10 s standing, the
  same walk (8 s forward, 3 s left, 8 s forward), `chim spikes 300`, a `chim spikes report` after each part. Both
  variants are second or later arrivals in their session; session A ran 0 then 1, session B ran 1 then 0.
- Session scripts SHA-256: A 96177910dfd9a2573b4ff88c756e72ba047f45b409804e8b904fabce1a77fefd, B
  1c352d2ce342f589c0548a973b6b33196794a7228e2b212b1a6922d80d588c01.
- Previous recorded line: v0.0.59-dev (commit 4d2b2269) above, before the tables per area.

| Part | Session | areas 0: frames, total, disk | areas 1: frames, total, disk |
| --- | --- | ---: | ---: |
| Arrival (60 s) | A | 2,077 frames, 61,006 ms, disk 13,888.6 ms | 2,830 frames, 60,779 ms, disk 10,976.7 ms |
| Arrival (60 s) | B | 2,599 frames, 61,265 ms, disk 9,145.3 ms | 3,073 frames, 61,093 ms, disk 8,501.8 ms |
| Standing (10 s) | A | 316 frames, 10,389 ms, disk 2,064.0 ms | 673 frames, 10,651 ms, disk 1,069.3 ms |
| Standing (10 s) | B | 438 frames, 10,882 ms, disk 1,946.8 ms | 471 frames, 10,230 ms, disk 1,075.7 ms |
| Walk (19 s) | A | 1,017 frames, 20,256 ms, disk 4,334.2 ms | 988 frames, 19,751 ms, disk 4,074.5 ms |
| Walk (19 s) | B | 832 frames, 20,471 ms, disk 4,919.7 ms | 1,137 frames, 20,151 ms, disk 3,731.1 ms |

| Residents' think (`chim actors ambient`) | areas 0 | areas 1 |
| --- | ---: | ---: |
| Cost per think, session A / B | 0.737 / 0.490 ms | 0.517 / 0.475 ms |
| Worst think frame, session A / B | 411.7 / 181.7 ms | 314.9 / 259.9 ms |

What it shows: standing in Seyda Neen, the frames wait about half as long for the disk with the tables per area
(1,069 and 1,076 ms in 10 s against 1,947 and 2,064 ms), and the walk waits 6 to 24 % less. The 300 to 800 ms
`ambwalk` spike frames of the earlier line are gone with both settings (the walking step is now 10 to 41 ms over all
spike frames of a part); the remaining long frames while walking are the harvest plants of the next cells being read
(482 to 823 ms), and the residents' longest frames are their choice of the next package (`ambchoose`, 111 to 401 ms
in spike frames), not their walking. The arrival's longest frame depends more on the order in the session than on
the setting (the later arrival of each session is shorter). The counter "scans on the island-wide file" counts only
the fallbacks with the setting on, so it reads 0 with the setting off too.

### AmiWind v0.0.61-dev2 (source afa644d4), 6 November 2026

- Setup: FS-UAE 3.1.66, A1200 AGA, 68040 with FPU, JIT, 32 MB Fast RAM, audio on, hard disks on the IDE controller;
  the delivered v0.0.61-dev2 image (run 2026_11_06_v0.0.61-dev2_full-v0.0.61-dev2_afa644d) with its own engine
  (SHA-256 6f2aa1d72af05959cc8cba739b604206954264d2ec9d1c9da14d365ca1c6df57), and the delivered v0.0.61-dev1 image
  (run 2026_11_05_v0.0.61-dev1_full-v0.0.61-dev1_374d59b, engine e06a3897925238e4f043c772e944a8185a8c9dff97cf6393f39327b301e2f76b),
  one session after the other with the same script. The build machine was lightly loaded for both sessions (4 to 15 %
  processor use); the dev1 line of 5 November above was taken under heavy load, so only the same-day dev1 session below
  is compared.
- Session script SHA-256: B 1c352d2ce342f589c0548a973b6b33196794a7228e2b212b1a6922d80d588c01 (the same script as in the
  dev1 section; `aw_ambient_areas 1` first, then 0). Only the `aw_ambient_areas 1` rows (the default) are compared in the
  table; the `aw_ambient_areas 0` rows follow.
- Previous recorded line: v0.0.61-dev1 (source 374d59b) above, and the dev1 session of the same day.

| Part | dev1: frames, total, disk | dev2: frames, total, disk | Total | Disk |
| --- | ---: | ---: | ---: | ---: |
| Arrival (60 s) | 3,442 frames, 60,458 ms, disk 9,180.8 ms | 3,651 frames, 60,436 ms, disk 6,317.3 ms | 0 % | -31 % |
| Standing (10 s) | 552 frames, 10,201 ms, disk 1,143.3 ms | 673 frames, 10,673 ms, disk 584.9 ms | +5 % | -49 % |
| Walk (19 s) | 1,193 frames, 20,209 ms, disk 3,590.4 ms | 1,157 frames, 19,615 ms, disk 2,432.1 ms | -3 % | -32 % |

With `aw_ambient_areas 0` (second half of the session): arrival disk 7,378.9 ms (dev1) against 6,471.5 ms (dev2), -12 %;
standing 2,073.2 against 483.7 ms, -77 %; walk 3,304.4 against 2,739.9 ms, -17 %; the totals are within 1 %.

| Residents' think (`chim actors ambient`) | dev1 | dev2 |
| --- | ---: | ---: |
| Cost per think, areas 1 / areas 0 | 0.673 / 0.658 ms | 0.205 / 0.168 ms |
| Worst think frame, areas 1 / areas 0 | 184.7 / 95.5 ms | 179.8 / 269.5 ms |

The totals of the parts are the length of the wait steps in the script, so they stay near the same value; the
frames and the disk time carry the difference. No part is more than 10 % slower in disk time, so there is no regression.
The worst single think frame of dev2 with the setting off (269.5 ms against 95.5 ms) is one frame and the
setting is not the default.

#### The standard benchmark (`aw bench halloween`)

| Build | Machine | Run 1 | Run 2 |
| --- | --- | --- | --- |
| v0.0.61-dev1 | FS-UAE, 32 MB Fast, 68040, JIT | avg 29.4 fps, min 0.9, 1 % low 1.9, 20.4 s | avg 28.3 fps, min 1.4, 1 % low 2.1, 21.2 s |
| v0.0.61-dev2 | FS-UAE, 32 MB Fast, 68040, JIT | avg 31.0 fps, min 1.2, 1 % low 2.3, 19.3 s | avg 33.4 fps, min 1.5, 1 % low 3.4, 18.0 s |
| v0.0.61-dev2 | Pi 4B, Amiberry, 128 MB Fast | avg 5.1 fps, 600 frames, 118.0 s (from the console still; the live scene was running, residents on) | none |

dev2 is 8 to 15 % faster than dev1 on the emulator (mean 32.2 against 28.9 fps). No dev1 line exists for the Pi, so
the Pi line is the first of this build; the Pi's frame-line numbers in the live Seyda Neen scene (`chim spikes 300`,
second arrival after the map was loaded, windows longer than the script's because the console was typed in by hand):
arrival 4,732 frames in 106,374 ms with disk 2,089.7 ms and the longest frame 740 ms; standing 225 frames in 25,418 ms
with disk 42.0 ms and the longest frame 145 ms; residents' think 0.356 ms, worst 109.1 ms.

#### Walking residents' stuck searches (AMBIENT-UNSTUCK-FLOOD-61), 6 November 2026

- Setup: FS-UAE 3.1.66, A1200 AGA, 68040 with FPU, JIT, 32 MB Fast RAM; the delivered v0.0.61-dev2 image (run
  2026_11_06_v0.0.61-dev2_full-v0.0.61-dev2_afa644d), first with its own engine, then with the engine of branch
  v0.0.61-unstuck (built from the worktree before the setting moved from a console variable to the console switch,
  the same behaviour; SHA-256
  a8215c9e4bab04687f44b7aa54f4d0df9d5c18ae3ee3633017bcd4a25a6cd8b9), developer messages on, the Seyda Neen start.
- What is counted: the searches for a clear spot that the residents' steps run (`chim actors ambient`, new in this
  engine), and the "Unstuck." lines (one per search) for the image's own engine. A search costs 12 to 30 position
  tests (each a box trace against the world and the bodies).
- Previous recorded line: none for this counter; the residents' think cost above (v0.0.61-dev2) is the line it sits beside.

From the arrival at the Seyda Neen start (`dbg tp seydaneen` reloads the map), about 85 s, the old way: 24 searches
with the image's engine (one resident, Indrele Rathryon, 20 of them) and 26 with the branch engine at
`chim actors ambient settle off` (an Imperial Guard 21, at the same steep face). In a run where no resident ended up inside the
face, 3 searches; eight further arrivals gave 1 to 4 searches each with either setting, none of them repeated: the case
depends on where the random routes end.

On purpose (session script SHA-256 8427c6edb6a0a56ca794e84a343fc6a061acfec63e935b1d3dd0878447e7134e): the two residents
put at the spots where they had started inside solid (`chim actors ambient put`) and walked on into the face, three
times each at three spots, 3 to 4 s per try:

| Setting | Searches per try | Settled | Position tests, all nine tries |
| --- | ---: | ---: | ---: |
| `chim actors ambient settle off` (old) | 1 to 26, mostly 10 (106 in nine tries) | none | 1,758 |
| `chim actors ambient settle on` (default) | 1, plus the settle's own search | 9 of 9 | 336 (-81 %) |

The residents' think cost per think moves with the town around them (0.09 to 1.4 ms in these short windows) and shows
no clear difference beyond the searches' own share. In Balmora, Vivec and Suran (45 s after each arrival, the default
setting) the residents' steps ran 2, 0 and 2 searches, none repeated.

### The Raspberry Pi 4B, the standard benchmark (6 November 2026)

The project's Pi 4B boot stick runs nothing but Amiberry and the game, so its line is the cleanest comparison between
builds; it is also the machine closest to a PiStorm ([REAL_HARDWARE.md](../REAL_HARDWARE.md)). Setup: Amiberry on the
Pi 4B at 2.0 GHz (not throttled), 68040 with FPU, JIT with a 16 MB cache and the FPU JIT on, CPU speed at maximum,
128 MB Fast RAM, PAL. Steps: `map seyda`, `dbg camera vanity off`, `chim actors ambient off`, then
`aw bench halloween` in Seyda Neen, the console closed with the backquote key before the 600 frames start. The scene is
a worst case on purpose: Seyda Neen is the heaviest place in the game so far, with about ten animated characters on
screen and Dagoth Ur, the most detailed model.

| Build | Setting | Average | Min | 1 % low | 600 frames in |
| --- | --- | ---: | ---: | ---: | ---: |
| v0.0.61-dev3 (the v0.0.61 game) | `cpu_threaded=false` | 5.4 fps | 1.0 | 2.0 | 110.3 s |

A 962 ms frame with 477 ms of disk wait was printed while the scene set up; the result line cannot yet show whether
any of the 600 frames waited on the disk, so the minimum and the 1 % low are rough until the benchmark reports drawing
and disk time apart (planned for v0.0.62).

Earlier Pi lines are not comparable and are not listed: the runs of v0.0.59 to v0.0.61-dev2 taken the same evening
closed the console with the Escape key, which opens the main menu, so they measured with the menu over the scene.
They will be taken again with the corrected steps.
