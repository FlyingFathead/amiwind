# AmiWind v0.0.63-dev5 (in development)

_Last updated with AmiWind v0.0.63-dev5 (9 November 2026)._

Development snapshot, 9 November 2026, in development. Running on CHIM Engine v0.2.2. Previous snapshot:
[v0.0.63-dev4](RELEASE-v0.0.63-dev4.md); previous release: [v0.0.62: Stick To The Script](RELEASE-v0.0.62.md).

The fifth snapshot of v0.0.63. It changes how a spoken line is shown, so that the stats under the view stay visible,
and it makes the builder say plainly whether the files of the Tribunal and Bloodmoon expansions were found and what of
each is used. 605 of the 1,207 scripts run as scripts and 8 more are carried by the game's own code (the same as in
v0.0.63-dev4). The game needs 32 MB of Fast RAM, and the emulator presets of this snapshot have it.

## Checked by tests, not yet in play

Every change below is checked by the test suite and the gate of this snapshot. None of it has been seen in play on a
build of this snapshot yet; the in-game checklist at the end lists what to look at.

## New since v0.0.63-dev4

### The text box of a spoken line

- **Text box type 2 is the new default** (`SUBTITLE-BOX-HIDES-STATS-63`): the box of a spoken line (random and idle
  lines, greetings and notices) rose over the whole lower part of the screen and blackened it, so the health, magicka
  and fatigue bars under the view were hidden while a line showed. Type 2 draws the same box where it always was, at
  once and without the rising animation, and blackens nothing outside the box. Type 1, the old rising strip, stays as
  a choice: Options, Prefs, "Text box: type 1 / type 2" (saved), or `dbg ui textbox 1` and `dbg ui textbox 2` on the
  F10 debug console. The details are on the [dialogue and waiting](../../DIALOGUE_AND_WAIT.md) page.

### The builder

- **The builder states what it found of Tribunal and Bloodmoon**: after the game-file check, the build summary has a
  block for each expansion: found, partly found or not found (a warning line), the records of its master, the files of
  its archive, the scripts that run now and the scripts that wait for Mournhold or Solstheim (from the
  [MWScript tracker](../../MWSCRIPT_FEATURES.md) when it was measured on the same masters), and the creatures built.
  The same record is written to `build-state.json` and `build-summary.json`. It only reports: no build output and no
  stage key changes. It is also the place for the planned option to build without the expansions. See
  [known inputs](../../KNOWN_INPUTS.md), "Expansions: found or not".

### The game's scripts

The README's section "The game's scripts" gives the breakdown of the 1,207 script records of the three game files. The
numbers of this snapshot, measured on the same masters:

| State | Scripts |
| --- | ---: |
| Run as scripts | 605 of 1,207 (605 in v0.0.63-dev4) |
| Carried by the game's own code | 8 |
| Use a function the interpreter lacks | 28 |
| Belong to an add-on world not in the image yet | 432 |
| Named by nothing (they never run in the original either) | 134 |

Every script of Vvardenfell that the original runs also runs here. The 460 scripts of Mournhold and Solstheim (432
plus the 28 that also lack a function) wait for those worlds to be built; the 134 named by nothing never run in the
original either. The [MWScript tracker](../../MWSCRIPT_FEATURES.md) lists every script with its state.

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

- Text box type 2 in a conversation: a greeting and the topic lines show in a box drawn at once, in its usual place,
  and the health, magicka and fatigue bars under the view stay visible.
- Text box type 2 in passing: a random or idle line of a person you walk by, and a notice, show the same way.
- Text box type 1 is still selectable (Options, Prefs, "Text box", or `dbg ui textbox 1`): the old rising strip
  returns, and `dbg ui textbox 2` brings the new box back; the choice is kept after a restart.
- The expansions block in a build log: after the game-file check, the log names Tribunal and Bloodmoon as found,
  partly found or not found, with what of each is used.
- Everything on the [v0.0.63-dev4 checklist](RELEASE-v0.0.63-dev4.md#in-game-checklist-for-this-snapshot).

## Known in this build

- The box of type 1 still hides the stat bars while a line shows; type 2 is the default and is checked by tests, not
  yet in play (`SUBTITLE-BOX-HIDES-STATS-63`).
- The voice table's unit key is not stable from one run to the next, so a build bakes six of its seven units again
  (about 10 s a build; `BUILD-TABLE-UNITS-REBAKE-63`, reported twice).
- A player who becomes a werewolf is not drawn as the werewolf (`WEREWOLF-BODY-NOT-DRAWN-63`).
- Show and ShowVars name no script locals (`MWSCRIPT-CONSOLE-LOCAL-NAMES-63`).
- The shores and pond edges still run in saw-tooth steps; the fix needs a world rebuild
  ([INLAND-SHORE-29](../../bugs/INLAND-SHORE-29.md)).
- The game image is still larger than the original game data (`IMAGE-BIGGER-THAN-ORIGINAL-62`).
- Files that two build stages write each are listed and kept from growing; each is to be written by one stage only
  ([BUILD-SHARED-WRITES-UNATTRIBUTED-52](../../bugs/BUILD-SHARED-WRITES-UNATTRIBUTED-52.md)).
- The image step and the CHIM validation still run on few cores in a full world rebuild
  ([BUILD-IMAGE-UNDERUSED-32](../../bugs/BUILD-IMAGE-UNDERUSED-32.md),
  [BUILD-CHIM-STAGE-SERIAL-TAIL-36](../../bugs/BUILD-CHIM-STAGE-SERIAL-TAIL-36.md)).
- The new world key is checked by tests; a build that proves it is still to come (`BUILD-CHIM-HEAP-KEY-LOADER-63`).
- From [v0.0.62](RELEASE-v0.0.62.md): pickpocketing and owned locks are not done, and the Heart Chamber may not load at
  32 MB Fast RAM.
