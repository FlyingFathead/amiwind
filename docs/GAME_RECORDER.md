# Gameplay recorder

_Last updated with AmiWind v0.0.67-dev1 (17 November 2026)._

<!-- contents start -->
## Contents

- [How to use it](#how-to-use-it)
- [What a recording holds](#what-a-recording-holds)
- [How a playback retraces the session](#how-a-playback-retraces-the-session)
- [Budget](#budget)
- [Checked in game](#checked-in-game)
- [Not yet covered](#not-yet-covered)
- [Recordings as benchmarks](#recordings-as-benchmarks)
- [Gameplay journeys](#gameplay-journeys)
  - [Playing a journey by hand](#playing-a-journey-by-hand)
  - [What it costs](#what-it-costs)
- [Gameplay smoke tests](#gameplay-smoke-tests)
- [Workflow](#workflow)

<!-- contents end -->

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

## Gameplay journeys

A journey is a fixed play route with checks that read the game's own state, never a picture: the inventory counts,
the journal index, the control switches, health, the actor list (who is alive, fighting or dead) and the script
globals, each through the console commands the game already has (`player->getitemcount`, `getjournalindex`,
`player->gethealth`, `chim actors list` and the `aw_mwscript_status call` reads). The standard journey is
`tests/sessions/journey_opening.txt`. It plays the opening the way a player does: the ship, the pier, the clerk's
registration, then the census office on foot (the papers taken off the table, the hall guard's door, the back room,
the courtyard, the captain's door), with the use key on what the view is aimed at and Sellus Gravius' topics chosen
by name (Morrowind, whose answer names his duties, then duties). Its nine steps:

1. The opening to the papers taken at the census office: fighting is switched off from the ship until the papers;
   after them the papers are carried and fighting and magic are on.
2. The hall guard's door and the back room: the door opens once the papers are carried, and the iron dagger on the
   back-room table (the one the clerk's tutorial box asks for) is taken. Then the crab meat (`ingred_crab_meat_01`) on
   the Silverware Plate (`misc_imp_silverware_plate_01`): the view is aimed at the crab meat, the game's focus row must
   name it and not the plate, the use key takes it, the crab meat is counted in the inventory and the plate is not
   (the theft ledger names none).
3. Out to the courtyard and back in through the other door: the dagger is not on the table again (the game's aim
   report lists its row switched off; the console cannot count an item no script names).
4. Fargoth's ring (the Engraved Ring of Healing, `ring_keley`) from the courtyard barrel, then Sellus Gravius: the papers are gone, the package and the directions
   are carried, 87 gold more, the journal of `A1_1_FindSpymaster` is at 1; asking again gives nothing a second time.
5. The release: the exit door lets the player out with the package, and the opening's state is over (`CharGenState`
   -1). The release's map change is the first after which the game may save, so the game's own autosave must be on
   disk a few seconds later: `dbg save status` (`aw_save_status`) answers `autosaves -> N` and must read at least 1;
   on a miss its answer says what held the autosave back and how the last save ended. Seyda Neen is outdoors, so its
   creatures are counted too: `chim actors creatures on` (the switch is on by default) must count at least one alive.
6. An actor killed, an interior entered (the captain's room by the street door), out by its courtyard door, in
   again and out by the exit door to the street: the actor is still listed dead, and both doors let the player out.
   The victim is named by reference (`chim actors kill 128960`, Erene Llenim, who stays by his shack on the west of
   the town): the nearest resident, which a plain `chim actors kill` takes, can be the guard standing by the street
   door, and his body there then takes the use key instead of the door (changed in v0.0.66-dev9; seen working in the
   v0.0.66-dev9 and v0.0.66-dev10 journeys).
   God mode is on for the kill only and off again right after it, since it blocks every kind of damage and would
   leave step 7's health readings all the same.
7. A spell cast (a Restore Health made for the test) and a fight: the health rises, the cast is counted as landed,
   and the fight takes health. The fighter is a copy of a resident put at the player's feet first: the nearest resident
   by itself can stand behind a wall, cannot reach the player and flees, and can be one who fights unarmed (Fargoth,
   `fargoth`: misses and fatigue damage only). The copy is of the Seyda Neen guard, who carries a weapon, named by
   reference (`chim actors summon 128967`; without a reference the command copies the nearest resident, and a
   reference of nobody living there copies nobody and says so; changed after v0.0.66-dev10, to be confirmed by a
   journey).
8. The game's own quicksave, then a new start of the engine and the load through the Load game window: the package,
   the gold, the ring, the journal, the dead actor and a script global are as they were saved.
9. Through a door with E: the next area loads and the game goes on with the loaded inventory. At the end, every map
   change since the release has written its autosave (the release's, the captain's room, the courtyard and back, and
   this door; the load of the quicksave is not a map change), and `dbg save status` says nothing holds the next one
   back.

A second journey, `tests/sessions/journey_tarhiel.txt`, checks the falling mage on the Bitter Coast near Seyda Neen.
Outside the trigger it checks that the mage is still held on his platform and that nothing has landed. After a walk
to within 2000 units of his journal it checks from `aw_mwscript_status` that he fell, landed and died.

A third, `tests/sessions/endgame_heart.txt`, plays the end of the main quest without the quest before it. A test
character (`dbg aw hors`, then `dbg maxstats`) is given Sunder (`sunder`), Keening (`keening`) and Wraithguard
(`wraithguard`), the quest `C3_DestroyDagoth` is set to 10 (Dagoth Ur defeated in the Facility Cavern) and
`dbg tp heartchamber` takes the character to Akulakhan's Chamber. Its nine steps:

1. The character: fighting allowed, every attribute and skill at 100.
2. The tools: all three carried. Wraithguard is worn, both by the original's console `Equip` and by the inventory's
   own route, and its global `wraithguardEquipped` is read after each. Sunder is in hand and does no harm for four
   seconds without god mode.
3. Dagoth Ur, Facility Cavern first, as the quest goes: Dagoth Ur's first form is defeated (by reference, as at stage
   10), and below stage 20 Azura's spirit and the Ring of Azura are hidden by their scripts. Then the chamber loads at
   32 MB Fast with the Heart of Lorkhan (`heart_akulakhan`) and Dagoth Ur (`dagoth_ur_2`) in it.
4. In front of the Heart: the Heart's script moves Dagoth Ur to his place and sets him on the player. His own script
   gives back the health a console blow takes and holds his first shield.
5. One strike with Sunder: the Heart's script takes it (its first local is 1, its `HitOnMe` matched once) and plays
   nothing yet.
6. Five strikes with Keening. After each one the Heart's script has taken one more blow and played one more
   animation (Idle2 to Idle5, then Death1), and Dagoth Ur's shield follows the count. The fifth sets `HeartDestroyed`.
7. The Heart destroyed: Dagoth Ur's health is capped at 200 (he can die now) and the three dreamer workers die.
8. Back at the entrance, within reach of the detector: the end script `EndGame` sets the quest to 20, ends the
   blight (`DestroyBlight` -1, two weather calls), kills Dagoth Ur, turns teleporting back on and gives 10
   reputation. The collapse of Akulakhan and the bridge is checked as a known gap
   ([ENDGAME-CHAMBER-COLLAPSE-63](BUGS.md)).
9. In Dagoth Ur, Facility Cavern, near Azura's spirit: the spirit is shown, takes the controls and plays the ending
   video, then the quest ends (`C3_DestroyDagoth` and `A1_SleepersAwake` at 50), the Ring of Azura is enabled, the
   controls are given back and the spirit goes.

Dagoth Ur is fought in god mode, not killed by reference: his script keeps him alive while the Heart lives, and that
is part of what is checked. The Heart is set on the player first (`chim actors fight`), as the first blow would do,
so a swing finds it by the original's hit cone over the fighters. The strikes are counted from the game's own state,
never from a picture: the Heart's `HitOnMe` calls that took a blow and its `PlayGroup` calls (`aw_mwscript_status`),
its first local (`aw_mwscript_status call getlocal 197602`) and Dagoth Ur's shields (`getspell`). After step 7's checks
the session sets `HeartDestroyed` from the console, which changes nothing when the fifth strike set it, so steps 8
and 9 are checked even when a strike did not register.

Some checks cannot pass today and are checked as known gaps, each with its register entry:

- Four console reads:
  - `player->getitemcount keening`: the console counts only the items of the actor table's list
    ([CONSOLE-GETITEMCOUNT-UNNAMED-ITEM-66](BUGS.md));
  - the original's `player->equip`: it wears the item without its script's OnPCEquip
    ([CONSOLE-EQUIP-SKIPS-ONPCEQUIP-66](BUGS.md));
  - `dagoth_ur_2->getpos` reads the console's own instance ([CONSOLE-GETPOS-SCRATCH-ORIGIN-66](BUGS.md));
  - `heart_akulakhan->sv` shows the console's own instance ([CONSOLE-SHOWVARS-SCRATCH-INSTANCE-66](BUGS.md)).
- Dagoth Ur's shield, which his script changes with the Heart's count: a read of another object's local gives 0
  today ([MWSCRIPT-MEMBER-READS-ID-AS-SCRIPT-66](BUGS.md)).
- The deaths of the dreamer workers and of Dagoth Ur: a script's `SetHealth 0` leaves an actor alive
  ([MWSCRIPT-SETHEALTH-ZERO-NO-DEATH-66](BUGS.md)). The workers' health set to 0 is a counted check.
- The collapse ([ENDGAME-CHAMBER-COLLAPSE-63](BUGS.md)).

Keening is checked from the grant's own answer, and Dagoth Ur's move from the script host's count of a
`PositionCell` carried out in the chamber.

Both runs so far used the v0.0.66-dev10 image.

- **The first run** stopped before the first strike, on an emulator disk stall in the test console's own state file
  ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](BUGS.md)). Before that, it passed steps 1 and 3: the chamber loaded at 32 MB Fast
  from Seyda Neen in 41 seconds.
- **The second run** played the whole session with the emulator option meant to keep the test console's folder from
  stalling (the comparison is still being measured).
  - Sunder registered, the five Keening strikes were taken and played on the Heart, and the Heart was destroyed.
  - Dagoth Ur's health was capped at 200.
  - The end script ended the blight, set the quest to 20, gave 10 reputation, changed the weather and turned
    teleporting back on.
  - It failed on the known gaps above, and in the Facility Cavern: that run came there first at stage 20. Azura's
    spirit had never been hidden, and its script shows it only when it was hidden, so the quest's end never started.
    The session now visits the cavern before the chamber.

Each part of a journey (`part A`, `part B`) runs as its own game: part B starts the engine again and loads the save
part A wrote. The journey file is the session-script language of `tools/engine_smoke.py` with four more words:
`step` (a numbered stage), `probe NAME COMMAND` (read one value), `pick NAME PROBE after|before TEXT` (the number
right after or before TEXT in an earlier probe's answer, such as one count of the long `aw_mwscript_status` answer)
and `expect` (a check on it, for example `expect gold_again == gold_sellus`, `expect dead victim in list_back`,
`expect fighting 262014 in list_near` with a reference number, or `expect lacks table_back reference 454283`).
`expect known REGISTER-ID CHECK` is a check for a step that cannot pass today: it is printed as `KNOWN` with its
register entry and is not counted in the result, and when it passes the result line says the gap closed.
`expect autosaves from step N` checks the game's autosave over the run's console: from step N on, every map load (a
streamed crossing and the load of a save are none) must be followed by a `Saved Autosave` line before the next map
load or the end of the part, and a failure names each map change without one. In a later part the count starts at
its `Game restored` line, since the start of a fresh engine is not a map change of the game.

Every session of a journey, like every smoke run, also fails on the engine's known failure lines anywhere in its
console (an entity update that overflowed the message, a frame update dropped or unreadable, any `Host_Error`) and
on a `dbg netstat` reading whose fullest frame wanted more than the game's own connection carries, or that counts a
frame update not sent (`tools/engine_smoke.py`; `--allow-engine-errors` only counts them, for a run that shows one on
purpose).

The walk itself never counts key presses blindly. Its steps wait for the game and stop the session at the first wrong
turn, naming where the player stands:

- `walkto X Y SECS`: walk to a point of the map until the engine says it is there; a message box on the way is
  answered with Enter;
- `waitfor KEY SECS TEXT`: wait until the game's state says so (the dialogue window is open, the census map runs);
- `boxes`: answer the message boxes that are showing;
- `face X Y Z` and `aimed REF`: turn the view to a point and check that the use key would go to that placed
  reference (the game's own focus or the crosshair's pick), nudging the aim a little around the point as a player
  does. Every aim is worked out from the eye as it is when it is made: `aimed` reads the eye again before each try and
  turns again when it has moved since `face`, and the nudges are centred on the aim from that eye. A point nearer than
  2 units on the floor plane, or needing more than 80 degrees down or 70 up, first has the player step back 12 units.
  A focus row on the reference counts only while the game's own use-key verdict names no actor: with a body or a
  person in front of a door the use key would search or talk instead, and the step fails naming them. A message box
  still showing is answered before the aim is checked, so the use key is never taken as its button;
- `lookat REF`: turn the view to a small placed item that the map does not draw itself (the town's items, not a
  room's own) with the game's own test aim at the nearest placed items;
- `topic NAME`: in the open dialogue window, type the topic's name into its search box and choose it;
- `mark` and `saw SECS TEXT`: a console line printed after the mark.

A part whose session stopped is reported with the step it stopped in and why, and every check it never reached says
so. `tools/journey_smoke.py`:

- `check JOURNEY`: the file is well formed and every check names values read before it;
- `scripts JOURNEY OUTDIR`: the session script of each part (`part-A.txt`, `part-B.txt`);
- `judge JOURNEY RUN-A RUN-B`: reads each session's `logs/steps.log` and `logs/console.log`, prints one line per
  check, `PASS` or `FAIL` with the value read and the value wanted, and a last line
  `JOURNEY RESULT PASS 42/42 checks, 9 steps` or `JOURNEY RESULT FAIL ... (steps 6)` (the counts are an example);
- `walkthrough JOURNEY`: the same journey as a checklist to play by hand.

A journey's checks read the game's state, so they also hold when its sessions run in the emulator's warp mode. Its
times never do: warp runs the emulated machine without frame pacing or sound, and every performance check and
benchmark runs without it (decided for the project, 17 November 2026; [FS-UAE-DEVELOPMENT.md](FS-UAE-DEVELOPMENT.md#engine-boot-and-map-load-smoke)).
The result line of a warp run ends with `[warp run: no timing verdict]`.

### Playing a journey by hand

`python3 tools/journey_smoke.py walkthrough tests/sessions/journey_opening.txt` prints, step by step, the console lines
to type and what each answer must show. Play the opening as usual; at each step open the console (the backquote key)
and type the lines, for example `player->getitemcount gold_001` before and after talking to Sellus Gravius, or
`chim actors kill` next to an actor, then `chim actors list` after a visit to a room (the actor's line must end in
`DEAD`). In step 8, quicksave; then quit the game, start it again and load that quicksave from Load game. Any answer
that differs from the checklist is a finding, with the step it belongs to.

### What it costs

Nothing in the game: the journey uses only existing console commands, and a probe is one console line and its answer.
A run is two emulator sessions (the opening walk takes most of the first).

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
