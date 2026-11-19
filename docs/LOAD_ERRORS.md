# When a place cannot be loaded

_Last updated with AmiWind v0.0.67-dev1 (17 November 2026)._

<!-- contents start -->
## Contents

- [What the box says](#what-the-box-says)
- [The codes](#the-codes)
- [The console](#the-console)
- [Before anything is left](#before-anything-is-left)
- [After the load has started](#after-the-load-has-started)
- [No error in play ends the game](#no-error-in-play-ends-the-game)
- [Every way into a place](#every-way-into-a-place)
- [Testing it](#testing-it)
- [Cost](#cost)

<!-- contents end -->

A destination that is missing or broken never ends the game, and neither does an error in play. Whatever way the
player takes into a place (a door, a load door, travel, a script that moves the player, a region crossing, a debug
teleport), a place that cannot be reached or loaded leaves the player where he was, or puts him back there, and the
game's own centred message box names the error with one button, **OK**. The game then runs on. When even the way back
fails, the last autosave is loaded, and then the previous map; only when all of them fail does the load menu open,
with the error on its notice line.

## What the box says

The box shows the error itself:

- `Map <name> was not found.` (the place's name beside the map's name when it is known)
- `Map <name> was found but could not be loaded.` with the reason on the next line:
  `Broken map file (bad header / short read / bad lump N).`, `Not enough memory (needs N KB, N KB free).`,
  `The map did not spawn.`, `The load did not finish.`, `A file it needs is missing (...).` or `Load error: ...`
- `No map holds the point <X> <Y>.` (a teleport to coordinates)
- when the way back failed too: `..., and the way back to <map> failed as well.`, then where the game went on
  (`The last autosave (Autosave 2) was loaded. You are in Seyda Neen.` or `The previous map, balmora, was loaded.`);
  only when nothing loaded, the load menu, whose notice line keeps the error in one short line
  (`LF4: map bmcaius did not load; no way back.`)

The code of the error follows on the last error line (`Code LF4.`), and the last line says where the player is now
(`You are in Seyda Neen.`). For example:

```text
Map bmcaius (Caius Cosades' House) was found but could not be loaded.
Broken map file (bad lump 7). Code LF4.
You are in Balmora.
```

## The codes

| Code | Kind | When |
| --- | --- | --- |
| LF1 | map not found | a name that is no map of the game (a typed `dbg tp` destination, a door table row) |
| LF2 | map not on this disk | a map of the game this build leaves out (a door whose room was not converted, a test build) |
| LF3 | no map holds the point | a teleport to original coordinates that no map of this disk covers |
| LF4 | broken map file | the map file's header does not read, the file ends before its lumps do (a short read), or a lump holds data that does not decode (bad lump N, Quake's lump numbers 0-14) |
| LF5 | not enough memory | the map's world does not fit the memory left for a map, or an allocation failed while it loaded |
| LF6 | the map did not spawn | the file loaded but the map could not start (too many models, a CHIM frame without its world) |
| LF7 | the load did not finish | the load made no progress for the time limit (120 seconds by default) |
| LF8 | a file the map needs is missing | a model or another file the map names is not on the disk |
| LF9 | load error | any other error while the map loaded, or an error in play |

## The console

Each failure writes one debug block to the console (F10) and to `DEBUG.TXT`, the console's copy on disk: the error's
code and kind with the box's text, the command as typed or the way the load started (`door 113893`, `travel`, `script
PositionCell`, `region crossing`), the map and its file (path and size), the error (the bad lump with its name and the
offset, and the loader's own message), the memory needed and free (and the machine's free Fast and Chip RAM), the
place left (map and position) and where the player is now. Each step of a recovery adds one line (`Recovery 1 of 3:
seyda again at 120 -45 77, the last good position.`, `Recovery 2 of 3: the last autosave (Autosave 2).`).

```text
Load error LF4 (broken map file): Map bmcaius ... Code LF4. You are in Balmora.
  command: dbg tp bmcaius
  map: bmcaius (Caius Cosades' House), file maps/bmcaius.bsp, 52344 bytes
  error: bad data in lump 7 (faces) at offset 31744: MOD_LoadBmodel: funny lump size in maps/bmcaius.bsp
  memory: Fast 8192 KB free, Chip 1024 KB free
  left: balmora at 120 -45 77
  now: going back to balmora
```

## Before anything is left

Some errors are found before the player moves at all, so nothing is left or loaded:

- a debug teleport to a name that is no map (LF1), to a map this disk does not hold (LF2), or to a point no map holds
  (LF3);
- a door whose room is not in this build (LF2);
- every scene load first reads the map file's 124-byte header: a header that does not read or lumps that run past the
  end of the file (a truncated file) are refused there (LF4), and so is a map whose world, decoded, would need more
  memory than this start keeps for a map (LF5). A travel service checks before the fare is paid. The cost is one file
  open and 124 bytes per load.

## After the load has started

Once the player has left, every error of the load ends that load instead of the game, and the way back to where the
load started runs (`engine/aga/src/aw_scene.c` `AW_SceneLoadFailed`):

- an allocation that fails while a map loads (the Hunk, the cache or the zone) ends the load (`engine/aga/src/zone.c`
  tells the game before it would stop it; the half-loaded map is dropped by the way back's own load);
- a map file the loader finds damaged ends the load: the fatal path's first step outside the platform code (the heap
  audit's fatal-exit phase, `engine/aga/src/zone.c`) tells the game, and `AW_MapFailure` in `engine/aga/src/model.c`
  names the map decode that stopped (the kind, the lump being decoded and where it starts, the loader's message),
  closes the file and drops the half-decoded map; the loader's own code and the platform code are unchanged, so the
  converted world's build keys do not move;
- a model or a sound the map needs that is missing ends the load (the client no longer stops half connected on the
  loading screen);
- a load that makes no progress within the time limit ends (`dbg loadfail timeout S`; 0 switches the limit off).

The design follows Quake III Arena's rule that a failed hunk allocation ends the level, not the program (the idea only;
no code is taken from it).

## No error in play ends the game

An error in play, when no load is running (an error of the engine, a server message the screen side cannot read, an
allocation that fails), and a load whose way back fails, go down one chain until the player is in play again; each
step runs only when the one before it failed:

1. the place loads again at the last good position (where he stood; for a failed load, where it started), and the box
   says "An error stopped the game in <map>; it was loaded again." with the error and the code LF9;
2. the last autosave of the character loads;
3. the previous map loads, at the last good position he had there;
4. only when all three fail, the load menu opens with the error on its notice line.

The same error again within a minute of a recovery in the same map starts at the next step, so a place that fails
every time is not loaded for good. A saved game that does not load is dropped, never applied to a later load. The
errors are counted in the state file the test sessions read (`errors`, and `errors_forced` for the test aids below):
a test run with an error that was not forced fails, so the cause is still found and fixed, while the player keeps his
game ([NET_MESSAGES.md](NET_MESSAGES.md)).

## Every way into a place

Every scene load passes `load_scene` in `engine/aga/src/aw_scene.c` (the check before leaving, the place left, the way
back), and every map load passes `Host_Map_f` (or `Host_Changelevel_f`) in `engine/aga/src/host_cmd.c`, which puts the
load in flight (`AW_SceneMapBegin`) so an error during it ends that load. `tests/test_load_fallbacks.py` keeps this
table complete: a new caller fails the test until it is listed here.

| Caller | Ways into a place |
| --- | --- |
| `use_link` | doors and load doors, entering and leaving every interior, a script's Activate of a load door |
| `AW_SceneTick` | a door after its opening sound, a region crossing |
| `travel_ride` | the travel services: silt strider, boat, guild guide |
| `AW_TravelKey` | the town table's silt strider ride |
| `map_teleport` | a script's Position and PositionCell outdoors (the propylon chambers' and other scripted moves), the jail, `dbg tp X Y [Z]`, the map marker, named outdoor places |
| `AW_SceneLoadRoom` | a script's PositionCell into a room, the `dbg tp` list's rooms |
| `scene_command` | `dbg tp NAME`, `dbg scene NAME` (towns, rooms, the ship, named places) |
| `roulette_command` | `dbg door roulette` |
| `AW_SceneShot` | `dbg cam recall` |
| `hors_command` | `dbg aw hors 0` |
| `hors_census` | `dbg aw hors` (the census office's exit door into Seyda Neen) |

Map loads that no scene load starts reach `Host_Map_f` directly: a saved game (`aw_save.c`), New Game and the opening
(`aw_intro.c`), a quick start and the way back itself (`aw_scene.c`), the gallery and arena test maps (`aw_gallery.c`),
a demo (`cl_demo.c`) and the game code's changelevel (`pr_cmds.c`). There is no place the load started from: in a game
in play the place the player was in loads again, then the chain above; with no game in play yet, the load menu opens
with the error.

Mark, Recall, Divine Intervention and Almsivi Intervention are not in the engine yet; when they come they move the
player through `map_teleport` or `AW_SceneLoadRoom` like the scripts do.

## Testing it

`dbg loadfail N [KIND]` makes the next N map loads fail on purpose: 1 shows the way back and the box, 2 a way back that
fails as well (then the last autosave), 3 the autosave's load too (then the previous map), 4 every step (the load
menu). The kind makes the load fail inside its real path: `error` (the default), `memory` (an allocation of the load
fails), `lump` (the map's first section read gets bad data, so the loader's own check refuses it in that lump),
`hang` (the load never finishes; with `dbg loadfail timeout 10` the limit comes after 10 seconds). `dbg hosterror
script`, `client` or `now` makes an error in play: inside the next frame's script step, in the screen side's read of
the next server message, or at once. A teleport to a name that does not exist (`dbg tp nowhere`) shows LF1. A
truncated file (a short read) and a bad header are tested on the host with real damaged files.

The host tests: `tests/aga_loaderr_test.c` (the codes, the box and notice texts, the console block, the header check),
`tests/aga_scene_test.c` (the refusals, a door's failed load and its way back, a way back that fails, a saved game's
failed load, a travel ride refused before the fare, and the chain: an error in play, again within a minute, the
autosave and the previous map), `tests/aga_heap_watcher_test.c` (the allocators), and
`tests/aga_bsp_slice_load_test.c` (a broken or truncated map file, another version, bad data from the read-ahead and a
section's memory not had, each named with its kind, its lump and where the lump starts). `tests/test_recover_in_play.py`
keeps the wiring the host tests leave out (the test aids, the save hooks, the counters and the engine smoke's check).

## Cost

Resident: two error records, the box's text and two positions, under 3 KB; per frame of play, the player's position
copied once. During a map load, a few comparisons a frame for the time limit. Per scene load: one file open and its
124-byte header for the check before leaving.
