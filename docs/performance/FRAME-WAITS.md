# Frame waits: disk, screen copy and buffer swap

_Last updated with AmiWind v0.0.59-dev6 (3 November 2026)._

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
