# Gameplay recorder

_Last updated with AmiWind v0.0.61-dev1 (5 November 2026)._

**Planned for v0.0.61.** Nothing on this page exists in the game yet; it is the design the work starts from.

A recorder for testing. It records what the player does in a session, keeps a save of the character and the world at
the start, and plays the session back in another game instance, so a route played once can be repeated exactly: to
reproduce a problem, to test the game's logic, and to measure frame times in the same places on every build.

## How it works

- Planned: `dbg recorder` in the console arms the recorder. Nothing is recorded yet; the screen shows the key to press.
- Ctrl+R starts and stops a recording. While recording, a red dot is on the screen. The key is live only after
  `dbg recorder` (planned), so the normal play keys keep their meaning; Alt is avoided because the emulator presets use Left Alt
  as their own modifier key.
- When a recording stops, the screen shows where it was saved, for example `recordings/001.awr`.
- Planned: `dbg recorder play FILE` loads the recording's save and plays the inputs back. While playing back, a play icon is on
  the screen.

## What a recording holds

One file holds everything needed to repeat the session:

- the starting save: the character and its attributes, the inventory, the list of changes made to the world, and the
  random seed;
- the player's inputs, frame by frame: movement, view angles, buttons and keys, and the console lines typed. Inputs
  are keyed to the game's frame number, not to the clock, so a slow machine and a fast one replay the same session;
- checkpoints every few seconds: the player's position, health, cell and a hash of the list of world changes.

Only what the player does is recorded. The game works out everything else again during playback. This differs from the
engine's demo recording, which stores what the server sent to the client: that is an exact replay to watch, not a
re-run of the game's logic. The demo is recorded beside the input file, for watching.

## Budget

- Per frame: under 16 bytes (movement 3 x 2, view angles 3 x 2, buttons and keys 1 to 2, frame length 1); the budget is
  32 bytes with the frame number and the occasional console line.
- At about 10 frames per second on a 68040: about 19 KB a minute and about 1.1 MB an hour. Checkpoints add about
  30 bytes every 5 seconds, and the starting save is one ordinary save file.
- Memory: the recording is held in a RAM buffer (about 1 MB holds an hour).
- Disk: nothing is written during play. The file is written once, when recording stops.
- Processor: one copy of 16 to 32 bytes per frame while recording; one test per frame when the recorder is off.
- Drawing: only the red dot or the play icon.

## Playback and divergence

Playback loads the starting save and feeds the recorded inputs to the game frame by frame, on the emulator or on the
Raspberry Pi 4B. At each checkpoint it compares the position, health, cell and change-list hash with the recorded
values and reports where a playback first differs. A divergence on a new build is itself a finding. A divergence before a
benchmark segment makes that segment's numbers invalid.

## Recordings as benchmarks

A recording is also a frame-rate benchmark. Playback measures frame times over the whole replay and per marked segment.
A key pressed while recording (planned: Ctrl+B) marks the start or the end of a segment, so the same places are measured
on every build. The results are saved with the build and the commit, in the same way as the other measurements in
[docs/performance](performance/): measured once, compared later.

## Gameplay smoke tests

Planned for v0.0.61. Today's boot smoke moves between places with the `dbg tp` console command. A recording walks the
real paths instead: doors opened with E, and the loads that follow. The planned starter set is a group of short
recordings made by the maintainer on the Raspberry Pi 4B, each with named checkpoints:

1. Doors: the Seyda Neen street, into Arrille's Tradehouse, back out, then into the Census and Excise Office (exterior
   to interior and back, both ways).
2. A town walk: the streets of Balmora with their residents, into a shop and out again, with benchmark segments outside.
3. Travel: a silt strider ride and the load on arrival.
4. Containers and a body: open, take, leave, return, and the item is still taken.
5. A conversation and a purchase.
6. Resting, and the level-up box.
7. Saving, quitting to the menu, loading, and carrying on.

Each replays in the boot smoke and the delivery checks. A stall, a door that does not open or a divergence fails the
build and names the checkpoint; the marked segments give the frame-time line of the build.

## Workflow

1. The maintainer plays on the Raspberry Pi 4B and records.
2. The recording file is copied off the Pi's game disk.
3. It is replayed on the emulator and on the Pi, as gameplay tests (logic: checkpoints and divergence) and as
   benchmarks (frame times in the marked places).
4. A set of recordings becomes part of the boot smoke and the delivery checks: a divergence or a stall fails the check
   and names the checkpoint where it happened.
