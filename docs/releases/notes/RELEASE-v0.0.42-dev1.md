# AmiWind v0.0.42-dev1: the builder milestone (in development)

Development snapshot, 16 October 2026, in development. Running on CHIM Engine v0.2.1. Previous release:
[v0.0.41](RELEASE-v0.0.41.md). Working plan: [v0.0.42](../../history/plans/PLAN-v0.0.42.md).

The first v0.0.42 snapshot: faster and more precise build tools, before the work on Vivec's interiors and the next
CHIM cells.

## What changed since v0.0.41

- **The clouds are back.** v0.0.40 and v0.0.41 shipped a flat sky with no clouds (the sun and the day and night
  colours still worked): a wider Seyda Neen scenery area changed the textures the palette is picked from, the cloud
  sky conversion refused the new palette and the build used a flat stand-in with only a warning. The cloud sky is
  now converted for whatever palette the build has (colours and textures stay as in v0.0.41), and a stand-in sky
  now stops the build:
  [SKY-FLAT-PALETTE-DRIFT-41](../../bugs/SKY-FLAT-PALETTE-DRIFT-41.md).
- **The CHIM checks run on one worker pool** for the whole step, largest frame first, with one progress line per
  frame; on v0.0.41-dev5's world the checks went from 445 s to 269 s with identical reports.
- **Each stair flight is walked once**, in the frame that owns it; stair steps walked on the v0.0.41 world went from
  2,672,454 to 853,398, and a passed walk is kept and reused. The stair gate runs first among the CHIM checks.
- **The build's time estimate follows the work** (units still to do at the rate measured in this build), and every
  build starts with a list of what a final release would refuse, each with its tracker entry.
- **A size ledger** prints every build's size per folder in GiB against the previous release.
- **Interior creatures:** the builder can place listed creatures in interiors, Vivec in his palace first, classed as
  levitating; every creature it leaves out is listed with its reason.
- **Far detail: Strong is the new default.** Options > Far detail (or `dbg cull` in the console): Full, Light,
  Strong or Strong + small faces; distant models drop out sooner by size for a faster frame (Strong: 17-27 % less
  3D time in Balmora on a slow 68040). Saved with the settings. Existing saves keep Full; choose Strong in the menu.
  [The far test](../../performance/FAR-TEST.md).
- **Renderer counters** for the speed work (`dbg rcount 3` and `dbg rcount 4`), and the first measurements:
  [where a slow frame goes](../../performance/SLOW-FRAME-BREAKDOWN.md).
- **A 68060 engine on the game disk.** Beside the 68040 engine (still the default) the disk carries the same source
  built for the 68060, which the game picks at boot on a 68060; it avoids the instructions a 68060 leaves to its
  support library. On an emulated 68060 the 68040 engine traps 73,000 to 424,000 of them per frame at the benchmark
  places, the 68060 engine about 3. A 68060 without its `68060.library` gets a notice with a countdown first. New
  68060 emulator presets (FS-UAE, WinUAE, one like our tester's A4000) and two measurement presets:
  [AmiWind on the 68060](../../68060.md).
- **Camera marks:** `dbg cam mark NAME` saves the shot you are looking at (place, view, time of day, headlamp, fog
  distance) and `dbg cam recall NAME` brings it back; the ten benchmark cameras and the Palace of Vivec pose ship as
  public marks ([CAMERA_MARKS.md](../../CAMERA_MARKS.md)).
- **Orbit camera:** `dbg cam orbit` circles the camera around what is under the crosshair (or `ref N`, or what a
  mark shows), at a set speed, optionally without the HUD; the player is out of the game while it runs and is put
  back exactly as before ([CAMERA_MARKS.md](../../CAMERA_MARKS.md#orbit)).
- **Timedemo on CHIM maps:** Quake's `record` and `timedemo` now play the CHIM world (before, a demo of a CHIM
  map showed only the sky and the characters); each timedemo prints the renderer counters of the whole demo and adds
  them to `saves/timedemo-results.txt` ([HARDWARE-BENCHMARK.md](../../HARDWARE-BENCHMARK.md#timedemo)).
- **Documentation:** plain-English licence summary, README, FAQ and build guides; the FAQ and the real-hardware page
  are current again; [comparisons](../../COMPARISONS.md) with other PC games on the Amiga.
- **The bug register:** fixed and superseded entries closed with their evidence; 416 open entries, each still open.
- **The HUD's weapon and magic boxes use the original art**, converted from your own game data when the game is
  built: the equipped weapon's icon (or the hand-to-hand icon) with its condition bar, and the selected magic
  item's icon on the original magic backdrop with its charge bar. Magic items keep their charge in saves and
  recharge over time; until the magic menu exists, `aw_magic select ID` picks one. See [the HUD](../../HUD.md).

## Known in this build

- [INTERIOR-CREATURES-MISSING-41](../../bugs/INTERIOR-CREATURES-MISSING-41.md): only listed creatures are placed in
  interiors (Vivec first); the rest wait for their classification.
- [MESH-VIVEC-CAP-GAP-38](../../bugs/MESH-VIVEC-CAP-GAP-38.md): two banner-draped giant mushrooms at Vivec's entrance show
  open cap bands.

- [HUD-STATS-29](../../bugs/HUD-STATS-29.md): spells cannot be selected yet (no spell list), so the magic box shows magic
  items only; no casting from items yet.
- [UI-ICONS-INVENTORY-42](../../bugs/UI-ICONS-INVENTORY-42.md): the inventory shows icons only for a few items, resampled.
- [NIGHT-WINDOWS-LOST-CHIM-36](../../bugs/NIGHT-WINDOWS-LOST-CHIM-36.md): windows no longer glow at night (since
  v0.0.36): the towns moved to CHIM and their maps got no list of window glass.
- [VIVEC-ROOM-PRECACHE-LIMIT-42](../../bugs/VIVEC-ROOM-PRECACHE-LIMIT-42.md): Vivec, Telvanni Tower is left out again (as in
  v0.0.41): its map needs one model slot more than the engine has.

See the [bug register](../../BUGS.md) for everything else.
