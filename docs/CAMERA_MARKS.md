# Camera marks

A camera mark is a named shot: the map (or the original Morrowind position), the position, heading and pitch, the
time of day, the headlamp and the fog distance. One console command saves the shot you are looking at, another
brings you back to exactly that shot, so speed measurements, bug reports and before/after screenshots can name a
mark instead of repeating coordinates.

The commands live under `dbg cam`, because Mark and Recall are spells of the game:

| Command | What it does |
| --- | --- |
| `dbg cam mark NAME` | saves the current shot as a private mark (replaces a private mark of that name) |
| `dbg cam recall NAME` | restores a public or a private mark |
| `dbg cam list` | lists the public marks, then the private ones |

`NAME` is 1 to 31 letters, digits, `_`, `-` or `.`; names are matched without regard to case. A private mark cannot
take the name of a public one.

## What a recall does

In this order, as the benchmark method does it by hand:

1. With a time in the mark: the day/night cycle is switched off (the clock is held) and the clock set to that time
   (`dbg daynightcycle off`, `dbg set time HHMM`).
2. The headlamp on or off (`dbg headlamp`), and the fog/draw distance (`dbg fog distance`), when the mark gives them.
3. The travel:
   - a mark in original Morrowind coordinates travels as `dbg tp X Y` (or `dbg tp X Y Z`) does: the same map
     choice, the same arrival placement on the ground, the same checks. The heading and pitch are applied once the
     map has loaded. Recalling it again while you are already there (on that map, within 48 units) only sets the
     view again, which is what `aw_aim` after the arrival did in the benchmark method;
   - a mark on a map places the camera exactly at that point in noclip: at once on the current map (nothing is
     touched: no door, trigger or pick-up fires), or after loading that map through the same map load as
     `dbg tp`.

A recall is a debug teleport, nothing more: it does not detach the player from the world. The planned camera modes
(docs/PLAN-v0.0.42.md 1.2c) add that (no enemy notices, no triggers) and will take marks by name.

## The marks files

| File | Who writes it | Holds |
| --- | --- | --- |
| `config/camera-marks.txt` in the repository, `camera-marks.txt` in the game data | the project | the ten emulator benchmark cameras (`bm1` to `bm5` in Balmora, `sn1` to `sn5` in Seyda Neen, as in [HARDWARE-BENCHMARK.md](HARDWARE-BENCHMARK.md#frame-time-in-the-game)) and bug-evidence spots (`vivec-palace`) |
| `saves/camera-marks.txt` in the game folder | `dbg cam mark` | your own marks |

The builder copies the public file onto the boot disk with the debug command catalogue and refuses a file that
does not pass the check below. Both files have the same format, plain ASCII with LF line ends, at most 16384 bytes:

```
AWCM1
# name|place|position|yaw pitch|time|headlamp|fog|note
bm1|global|-20088 -14638|113 -3|1200|off|540|Balmora 1 (benchmark camera)
vivec-palace|vpi015|0 -64.7 -83.9|90 0|1200|off|-|Palace of Vivec
```

- The first line is `AWCM1`; lines starting with `#` and empty lines are comments. At most 383 characters a line.
- `place`: `global` for original Morrowind coordinates, or a map name (lower-case letters, digits and `_`, at most
  15) for that map's local units.
- `position`: `X Y` or `X Y Z` for `global` (as `dbg tp`), `X Y Z` for a map; numbers with at most two decimals,
  separated by single spaces.
- `yaw pitch`: yaw 0 up to 360 (not included), pitch -80 to 80, as `aw_aim` and `aw_view` take them.
- `time`: `HHMM` (0000 to 2359), or `-` to leave the clock alone.
- `headlamp`: `on`, `off` or `-`.
- `fog`: the fog/draw distance 100 to 4096 local units, or `-`.
- `note`: free text without `|`, at most 159 characters.

`dbg cam mark` writes a map mark at the exact point (with the original Morrowind position in the note when the map
has one), the current time to the minute, the headlamp and the fog distance.

Check a file with `python3 tools/camera_marks.py check [FILE ...]` (default: the public file); `show NAME` prints
one mark. The engine reads the same format (`engine/aga/src/aw_cam_rules.c`), and the tests check that both accept
and refuse the same lines and that the benchmark marks match the benchmark table.

## In scripts

An exec file or a scripted headless run can replace the benchmark's coordinates with marks:

```
dbg cam recall bm3
```

then, once the map has loaded and settled, `dbg cam recall bm3` once more (the view only). The frames are the same
as with `dbg daynightcycle off`, `dbg set time 1200`, `dbg headlamp off`, `dbg tp -21800 -12300` and
`aw_aim 90 0`.

## Orbit

`dbg cam orbit` circles the camera around something, for inspection and short clips:

| Command | What it does |
| --- | --- |
| `dbg cam orbit` | orbits what is under the crosshair: a character or creature (followed as it moves, around the middle of its drawn pose), a placed model, or the point the view ray hits |
| `dbg cam orbit ref N` | orbits the entity with original reference number `N` on this map (`dbg ent` shows a target's reference) |
| `dbg cam orbit mark NAME` | recalls the mark first, then orbits what that shot shows once it has arrived |
| `dbg cam orbit photo ...` | the same without the HUD, full screen (as photo mode) |
| `dbg cam orbit speed DEG ...` | the speed in degrees a second (default 36: one orbit in 10 seconds; negative turns the other way); alone, while orbiting, it changes the speed |
| `dbg cam orbit off` | ends the orbit |

While it runs: `+` and `-` change the speed by 6 degrees a second, `0` holds the camera still, the mouse wheel
moves it closer or further, the mouse turns it around the target, and the right mouse button or Esc ends it. The
camera starts where the view is and keeps that distance; walls between the target and the camera pull it in, as
in third person.

The orbit is the game's own idle (vanity) camera turned on another centre: the same placement, the same pull-in in
front of walls, the same full view. While it runs the player is not there for the game: noclip and god mode, Quake's
notarget (fighting characters stop chasing and attacking, nobody starts an idle line), the player's body hidden, the
position held and every game key taken by the orbit, so no door, trigger, pick-up or dialogue starts. When it ends
the position, view, movement mode and the god and notarget switches are as they were before.
