# Gameplay recorder

_Last updated with AmiWind v0.0.62-dev1 (2026-11-07)._

**In development for v0.0.61** (register: GAME-RECORDER-MISSING-61). The first slice below is in v0.0.61-dev3 and
records and replays a session on the emulator; the hotkey for benchmark segments, the mouse in windows, replay on the Raspberry Pi 4B and the
gameplay smoke set are still planned.

A recorder for testing. It records what the player does in a session, keeps a save of the character and the world at
the start, and plays the session back in another game instance, so a route played once can be repeated exactly: to
reproduce a problem, to test the game's logic, and to measure frame times in the same places on every build.

## How to use it

- `dbg recorder` in the console arms the recorder. The version line at the top of the screen then reads
  `AmiWind v<version> - Ctrl+R: record`. Nothing is recorded yet. `dbg recorder off` disarms it.
- **Ctrl+R** starts a recording. The game takes a save of the character and the world as they are, loads that save at
  once (a short load), and records from the first frame in play after it. While recording, the version line reads
  `AmiWind v<version> (RECORDING)`. The key is live only after `dbg recorder`, so Ctrl and R keep their meaning in
  normal play (Ctrl is sneak); Alt is avoided because the emulator presets use Left Alt as their own modifier key.
- **Ctrl+R** again stops it, also with a window open (the dialogue, the inventory, the menu or the console): while the
  recorder is armed or running, Ctrl+R belongs to it everywhere and never reaches the window, so it is not typed into
  the dialogue's search field (register: GAME-RECORDER-HOTKEY-DIALOGUE-61). A
  recording starts only in play: with a window open, Ctrl+R says to close it first. The file is written once, at the
  stop, and the screen names it, for example `Saved recordings/001.awr` (the next free number in the `recordings`
  folder of the game folder).
- `dbg recorder play 001` (or `play 001.awr`) loads the recording's save and plays the session back. While it plays,
  the version line reads `AmiWind v<version> (PLAYBACK)`, the keyboard is taken by the playback (Ctrl+R stops it), and
  the console prints a line for every checkpoint. At the end one line sums it up:
  `RECORDER RESULT match 7/7 checkpoints, ...` or `RECORDER RESULT diverged at checkpoint 3 (0:15, in <place>) ...`,
  and the screen shows the same for 30 seconds.
- `dbg recorder start`, `dbg recorder stop` and `dbg recorder status` do the same from the console (for scripted test
  sessions).

## What a recording holds

One file (`.awr`) holds everything needed to repeat the session:

- the starting save: the character and its attributes, the inventory, the world change list, the journal, the time of
  day, and the random seed the game's rolls start from;
- every frame of the session, keyed to the game's frame number, never to the clock: the frame's length, the move
  (forward, side, up) and the view angles the game sent, every key pressed or released (movement, E, attack, menus,
  console typing) and the command lines of the remote test channel;
- checkpoints every 5 seconds of game time: the frame, the player's position, health, the place and a hash of the world
  change list.

Only what the player does is recorded. The game works out everything else again during playback, which is what makes
it a test of a build. This differs from the engine's demo recording (`record` / `playdemo`), which stores what the
server sent to the client: an exact replay to watch, not a run of the game's logic again.

## How a playback retraces the session

The recording starts from a fresh load of its own save, and so does the playback: both begin in the same state, at
the same first frame in play. Every random stream the game's logic draws from follows the recorded seed
(register: GAME-RECORDER-FIGHT-SEED-61):

- at that first frame the fights' dice, the script language's Random and the levelled container rolls are set from
  it. A fight that was on when the recording started (or began again in the load of the starting save) rolls the same
  dice in the recording and in its playback, and a fight that begins later takes its seed from the recording's own
  count of fights, not from how many fights the replaying game has seen;
- the general generator (monster moves, spells, persuasion, rests, harvest rolls, effects) is set again at the start
  of every frame from the seed and the frame's number, so a roll drawn on one frame in one run and not in the other
  cannot shift the rolls of the frames after it;
- the game no longer draws a roll per wall-clock frame while the recorder runs.

Each played frame uses the recorded length instead
of the measured one, so a slow machine and a fast one run the same frames. The recorded keys go through the game's
own key handling as if typed, and the recorded move and view replace the live ones. Autosaves are off while
recording and playing back (a save changes the world change list's tables, and nothing is written during play).

Matching checkpoints mean the route was retraced. The first mismatch is reported with its number, time and place: on
the same build it is a hole in the determinism to fix; on a new build it is a finding (a bug, or a real change of
behaviour).

## Budget

Measured or counted for this slice on FS-UAE at 32 MB of Fast RAM, 68040 with JIT:

- **Off:** one test per hook and frame (the frame, the input, each key, the move, the drawing); about 1.2 KB of
  static data; no allocation.
- **Per frame while recording:** 3 bytes (flags and length), 12 bytes for the move and view, 2 bytes per key event,
  and the length of a command line when there is one: 15 bytes in a frame without keys. At 10 frames a second, about
  9 KB a minute and about 0.5 MB an hour.
- **Memory:** the frames are kept in one buffer that starts at 32 KB and doubles up to 2 MB (about three hours at 10
  frames a second; when it is full the recording stops and is saved); the checkpoints take 48 bytes every 5 seconds;
  the starting save is held from the start to the stop (its size is that of an ordinary save). All of it is freed at
  the stop.
- **Processor:** a 15-byte copy and one reseed of the general generator (a few multiplies) per frame while recording
  or playing back; every 5 seconds a pass over the world change list for its hash.
- **Disk:** nothing during play. One write when recording stops, one read when a playback starts.
- **Drawing:** the version line (and, for a few seconds, the saved file's name or the playback result) at the top of
  the screen; a message wider than the screen goes on a second line instead of running past the edge.

## Checked in game

v0.0.61-dev2 recorder engine on the emulator, 32 MB of Fast RAM, 68040 with JIT: a recording that starts inside
Arrille's Tradehouse in Seyda Neen, walks to the door, opens it with E (the load out to the street) and walks on:
5,502 frames, 1 minute 20 seconds of game time, 82,667 bytes of frames (15.0 bytes a frame) and a 5,002-byte starting
save. Its playback matched all 18 checkpoints to 0.0 units and ended on the same spot. A test recording on the
dev3 engine, 3,797 frames (0:58 of game time), held 13 of 13 checkpoints in its replay. The engine's generated version
header is rewritten only when it changes, which stops an engine build from failing on a header that is briefly shorter
than expected ([BUILD-VERSION-HEADER-RACE-61](bugs/BUILD-VERSION-HEADER-RACE-61.md)).

## Not yet covered

- The mouse pointer in windows (inventory, dialogue) is not recorded yet: the view and the keys are, so a session
  that uses windows by keyboard replays, one that clicks in them may not.
- Segment marks, benchmark segments (planned: Ctrl+B) and frame times per segment in [docs/performance](performance/).
- Replay on the Raspberry Pi 4B.
- Anything that depends on loading speed or wall time rather than game frames (the streaming of the outdoor world,
  some timers) can still make a playback differ; the checkpoints show where.

## Recordings as benchmarks

Planned. A recording is also a frame-rate benchmark: playback measures frame times over the whole replay and per
marked segment, so the same places are measured on every build. The results are saved with the build and the commit,
in the same way as the other measurements in [docs/performance](performance/): measured once, compared later.

## Gameplay smoke tests

Planned. Today's boot smoke moves between places with the `dbg tp` console command. A recording walks the real paths
instead: doors opened with E, and the loads that follow. The planned starter set is a group of short recordings made
by the maintainer on the Raspberry Pi 4B, each with named checkpoints:

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
