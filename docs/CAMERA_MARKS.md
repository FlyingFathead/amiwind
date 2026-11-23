# Camera marks

_Last updated with AmiWind v0.0.68-dev7 (22 November 2026)._

<!-- contents start -->
## Contents

- [What a recall does](#what-a-recall-does)
- [The marks files](#the-marks-files)
- [In scripts](#in-scripts)
- [Orbit](#orbit)
- [Pan](#pan)
- [Track](#track)
- [Pan and track together](#pan-and-track-together)

<!-- contents end -->

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

The same command moves the camera for clips and demo reels: [`dbg cam orbit`](#orbit) circles something,
[`dbg cam pan`](#pan) turns the view through a smooth pan from where it is, and [`dbg cam track`](#track) glides it
along a line or to a mark. The game's own idle camera, the vanity camera (`dbg vanitycamera`, see
[THIRD_PERSON.md](THIRD_PERSON.md)), circles the player.

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
(docs/history/plans/PLAN-v0.0.42.md 1.2c) add that (no enemy notices, no triggers) and will take marks by name.

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
- `fog`: the fog/draw distance 100 to 4096 local units, or `-`. A number is set as your own fog distance (Fog
  distance auto goes off, as with `dbg fog distance N`); `-` leaves the setting alone.
- `note`: free text without `|`, at most 159 characters.

`dbg cam mark` writes a map mark at the exact point (with the original Morrowind position in the note when the map
has one), the current time to the minute, the headlamp and the fog distance: your own value when Fog distance auto is
off, `-` when it is on (the place's own default then makes the same picture).

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

## Pan

`dbg cam pan` (also `dbg pan cam`) is a pan as a film camera on a tripod makes it: the camera stays where the view
is and turns about its own point, level, at a steady speed, with a held frame at each end.

| Command | What it does |
| --- | --- |
| `dbg cam pan` | a 360-degree pan to the right from the view now, ending where it began |
| `dbg cam pan DEGREES` | a pan through `DEGREES` (up to 3600); a negative angle pans to the left |
| `dbg cam pan DEGREES HOLD` | the opening and the closing frame held `HOLD` seconds each (default 3, up to 60): `dbg cam pan 180 5` holds 5 s, pans 180 degrees, holds 5 s |
| `... speed DEG` | the speed in degrees a second (1 to 90) |
| `... photo` | the same without the HUD, full screen (as photo mode) |
| `dbg cam pan off` | ends the pan early (as Esc or the right mouse button) |

The shot, in order:

1. The opening frame, held for `HOLD` seconds.
2. The move: the speed rises smoothly over 1.25 s (the same easing curve as the Halloween scene's camera director),
   stays steady, and falls smoothly over the last 1.25 s, so it never starts or stops with a jerk. A pan too short for
   that eases over less time at each end.
3. The closing frame, held for `HOLD` seconds; then the shot ends and the view is the player's again.

The default speed follows film's rule of thumb for a pan that does not judder: anything in the picture should take
at least 5 to 7 seconds to cross the frame. The pan takes 6 seconds per frame width, the horizontal field of view
over 6 seconds: 15 degrees a second at the game's field of view of 90 degrees (the `fov` setting). So the default
360-degree pan lasts 3 + 25.25 + 3 = 31.25 seconds, and `dbg cam pan 180 5` lasts 5 + 13.25 + 5 = 23.25 seconds.

The pan starts from what is on the screen: in first person the camera turns at the player's eye; in third person
it turns at the third-person camera's own point, with the player's body standing in the picture. The pitch stays as
it was.

## Track

`dbg cam track` is a steadicam glide: the camera leaves the view's point and moves along a straight line, through
walls if need be (noclip for the camera only: the player stays where it was), with the same eased start and stop and
the same held frames as the pan.

| Command | What it does |
| --- | --- |
| `dbg cam track forward N` | glides `N` map units along the view's heading, level (the height and the pitch kept); a negative `N` moves back while looking ahead |
| `dbg cam track to MARK` | glides to a camera mark on this map (see the marks above), the view turning smoothly to the mark's own heading and pitch, the short way round; the mark's time, headlamp and fog are not applied (`dbg cam recall` does that) |
| `dbg cam track SPEED ...` or `... speed U` | the speed in map units a second (1 to 1024; default 32, a slow walk) |
| `... HOLD` after the target, or `... hold S` | the held frames at each end, seconds (default 3) |
| `... photo` | the same without the HUD, full screen |
| `dbg cam track off` | ends the glide early (as Esc or the right mouse button) |

A mark on another map is refused (`dbg cam recall` travels there). A mark in original coordinates without a height
ends at the floor `dbg tp X Y` would put the player on, at eye height. The game around the player is what is loaded
and sent to the screen: a long glide far away from the player, or into another room, can reach places whose
characters and objects the player's own place does not see.

## Pan and track together

Both run on the orbit's camera, one at a time (a new camera move replaces the running one), and both detach the
player as the orbit does (noclip, god mode, notarget, the position held, every game key taken; only Esc and the right
mouse button do something: they end the shot). The mouse does not move a shot. Nothing is printed on the screen while
a shot runs: its lines go to the console and the log only, so a recording shows the world alone; with photo mode
(`dbg photomode`, `dbg killhud`) the HUD is gone as well. The shot's clock runs while the game is played: typed in the
console, a shot starts when the console closes; from a session script (one command, no console) it starts at once.

Each shot prints, to the console and the log only:

```
Camera pan: 3.00 s held, 25.25 s moving, 3.00 s held: 31.25 s in all; Esc or right click ends it.
Camera pan: 360 degrees to the right at 15.0 degrees a second (field of view 90).
...
Camera pan ended: position, view, movement and flags restored.
```

A script can wait for the `Camera pan ended` (or `Camera track ended`) line; an early end says `stopped early`. In a
session script:

```
mark
rec seyda-pan
cmd dbg cam pan 360 3
saw 60 Camera pan ended
recstop
```

The shot is a function of its own clock: frame times that add up to the same time give the same frame, and a slow
frame moves further, never a fixed step per frame. A frame longer than a quarter of a second (a load) counts as a
quarter of a second, so a hitch never makes the camera jump.
