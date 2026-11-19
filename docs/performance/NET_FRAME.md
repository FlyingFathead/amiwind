# The frame message: FULL against PACED

_Last updated with AmiWind v0.0.67-dev2 (18 November 2026)._

The frame message carries an update for everything in sight from the game's internal server to its screen side, every
frame ([NET_MESSAGES.md](../NET_MESSAGES.md)). Its room grows as needed, so how much of it to send each frame is a
choice between two methods, switched live from the console with `aw_net_method` and saved:

| Method | What goes each frame | Settings |
| --- | --- | --- |
| 1, FULL | every update in sight; the room grows when a frame wants more than three quarters of it | `aw_net_frame` 32768 (the room at the start), `aw_net_buffer` 65536, `aw_net_max` 262144 |
| 2, PACED | at most `aw_net_send` bytes of updates, the actors and the nearest first, the rest in the next frames | `aw_net_send` 4096 |

On the game's own connection nothing travels over a wire: the cost of a frame's message is building the updates (the
same in both methods: every update is measured), copying them, and the screen side reading them. PACED reads fewer
updates per frame in a crowded place; far things then move a frame or more late. The default is the method that
measures better below, by the rule in [How the default is chosen](#how-the-default-is-chosen).

## How it is measured

The session `tests/sessions/net_frame_methods.txt` stands still for 45 seconds per method at four places: Vivec, the
wilderness spot where v0.0.66 stopped (global -13677 -61720 604), Seyda Neen on the Bitter Coast, and the Vivec arena
pit (a quiet interior). Each window is framed by `chim spikes report` (the window's frames and their time, so the
average frame time; it also runs on engines without the methods, for a "before" line) and ends with `aw_netstat`,
the command behind `dbg netstat`, called by its own name so the session also runs on an image whose command catalogue
is older than its engine (the fullest frame and how close it came to the room, the waits, the frame time and the
screen side's reading time per frame). The order of the methods alternates by place. Every window's console must hold
none of "packet overflow", "SZ_GetSpace: overflow", "Message overflow caught", "Frame update dropped" or "Illegible
server message".

A run on real hardware (a PiStorm accelerator) is still to come; until then the numbers are the emulator's, to compare
with each other.

Each number of the tables below comes from one console line of its window:

| Column | Console line | Read |
| --- | --- | --- |
| Frames, average frame | the window's second `chim spikes report`: `waits in N frames (T ms)` | N; T / N in ms |
| Server frame | `aw_netstat`: `Frame time X ms average, Y ms longest` | X (Y) |
| Client read | `aw_netstat`: `the client reads X us a frame on average, Y us longest` | X (Y) in microseconds |
| Fullest frame | `aw_netstat`: `the fullest frame B bytes (P% of the room` | B (P %) |
| Waits | `aw_netstat`: `longest wait W frames, U updates waited A frames on average` | W; A |
| Room grew | `aw_netstat`'s first line: `grown G times`, and `Frame message: the room grows` lines | G |
| Actors | `dbg sweep actors` after the arrival: `actors: map M, live L` | L |
| Dropped | the window's console: "packet overflow", "SZ_GetSpace: overflow", "Message overflow caught", "Frame update dropped", "Illegible server message" | how many (must be 0) |

## How the default is chosen

For each place, the change is the difference of the average frame, PACED against FULL, in percent of FULL's
((PACED - FULL) / FULL); below 0 PACED is faster. The emulator's run of the session decides, in this order:

1. A method with a dropped line, or a window that ended outside play, is out at that place, and that is a finding for
   the register before anything else.
2. PACED becomes the default only when it is faster by 3 % or more (the change at most -3 %) in at least one of the
   three outdoor places (Vivec, the wilderness spot, Seyda Neen) and slower by no more than 3 % (the change at most
   +3 %) everywhere, the arena pit included. Otherwise FULL stays the default: every update goes every frame and nothing waits.
3. When PACED is slower than FULL by more than 3 % anywhere, its budget `aw_net_send` is halved (4096 to 2048) and the
   session runs again with the new budget for that method; the lower budget is kept only when it passes rule 2.
4. A FULL frame that wanted more than three quarters of the starting room (the room grew) is noted with its place: the
   starting room `aw_net_frame` is raised so a frame of that place fits whole from the first frame.
5. The real-hardware run of the same session, when it comes, decides over the emulator's when the two disagree.

The decision, the numbers it rests on and the commit that sets the default go into "The decision" below.

## Recorded measurements

### Before: AmiWind v0.0.67-dev1, 17 November 2026

- Setup: FS-UAE, A1200 AGA, 68040 with FPU, JIT, 32 MB Fast RAM, audio on, deterministic; the v0.0.67-dev1 image
  (run 2026_11_17_v0.0.67-dev1_full-v0.0.67-dev1_eb5f8d8) with its own engine (SHA-256
  cbbb43fb6f15407e9a24ec730ab4cde7c53ff6a3e1465a401cbd45fc03418560). Session `tests/sessions/net_overflow.txt`
  (Vivec, then the wilderness spot of the v0.0.66 stop): the engine of that build has neither the methods nor
  `dbg netstat`.
- Vivec: 4668 "packet overflow" console lines from the arrival on (the frame message ran past its buffer every
  frame); the sweep counted 143 live actors. The wilderness spot (the Seyda Neen map): none in this run, 69 live
  actors.
- The whole session's median frame in play: 13.9 ms.

### After the fix (8 KB on the game's own connection, nearest first), 17 November 2026

- The same image, session and setup with the engine of the v0.0.67 dev line's first fix (SHA-256
  ddc71afe265cfe842374b1834182cb7c3fed0645ddb613b367e96012c12e2268), before the room grew and the methods came.
- No "packet overflow", "Illegible server message" or "Frame update dropped" line anywhere; the same live actors
  (143 at Vivec, 69 at the wilderness spot); the sweeps found no failure; median frame in play 13.9 ms.

### FULL against PACED

- Setup: FS-UAE, A1200 AGA, 68040 with FPU, JIT, 32 MB Fast RAM, audio on, deterministic; the v0.0.67-dev1 image (run
  2026_11_17_v0.0.67-dev1_full-v0.0.67-dev1_eb5f8d8) with the engine of the v0.0.67 line's commit 6d1f09df (SHA-256
  358d53a2e748546f95c1b0d12d44561c7d5950e6379df3520c01fa61465bf262). Session `tests/sessions/net_frame_methods.txt`,
  45 seconds per method and place, the methods' order alternating by place. A dash is a number still to be measured.

| Place | Method | Frames | Average frame (ms) | Server frame (ms) | Client read (us) | Fullest frame (bytes, % of room) | Waits (longest; average, frames) | Room grew | Actors | Dropped |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Vivec | FULL | - | - | - | - | - | - | - | - | - |
| Vivec | PACED | - | - | - | - | - | - | - | - | - |
| Wilderness spot (-13677 -61720 604) | PACED | - | - | - | - | - | - | - | - | - |
| Wilderness spot (-13677 -61720 604) | FULL | - | - | - | - | - | - | - | - | - |
| Seyda Neen | FULL | - | - | - | - | - | - | - | - | - |
| Seyda Neen | PACED | - | - | - | - | - | - | - | - | - |
| Vivec arena pit | PACED | - | - | - | - | - | - | - | - | - |
| Vivec arena pit | FULL | - | - | - | - | - | - | - | - | - |

### Before: the same session on the v0.0.67-dev1 engine

The image's own engine (SHA-256 cbbb43fb6f15407e9a24ec730ab4cde7c53ff6a3e1465a401cbd45fc03418560) has neither the
methods nor `aw_netstat`; its two windows per place are the same engine twice.

| Place | Window | Frames | Average frame (ms) | "packet overflow" lines | Actors |
| --- | --- | --- | --- | --- | --- |
| Vivec | first | - | - | - | - |
| Vivec | second | - | - | - | - |
| Wilderness spot (-13677 -61720 604) | first | - | - | - | - |
| Wilderness spot (-13677 -61720 604) | second | - | - | - | - |
| Seyda Neen | first | - | - | - | - |
| Seyda Neen | second | - | - | - | - |
| Vivec arena pit | first | - | - | - | - |
| Vivec arena pit | second | - | - | - | - |

### The decision

| Place | Change, PACED against FULL | Faster | Note |
| --- | --- | --- | --- |
| Vivec | - | - | - |
| Wilderness spot | - | - | - |
| Seyda Neen | - | - | - |
| Vivec arena pit | - | - | - |

Default method: to be decided by the rule above from these numbers (FULL until then). Budget `aw_net_send`: 4096 until
then. Real hardware: still to come.
