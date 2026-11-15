# World map and progression journal

_Last updated with AmiWind v0.0.66-dev2 (14 November 2026)._

<!-- contents start -->
## Contents

- [Open map reports - 4 October 2026](#open-map-reports---4-october-2026)
- [M: Vvardenfell overview](#m-vvardenfell-overview)
  - [Place markers (since v0.0.66)](#place-markers-since-v0066)
  - [Explored land (since v0.0.66)](#explored-land-since-v0066)
  - [Your markers (since v0.0.66)](#your-markers-since-v0066)
  - [The hot marker and the compass (since v0.0.66)](#the-hot-marker-and-the-compass-since-v0066)
  - [Land colours (switch, since v0.0.66)](#land-colours-switch-since-v0066)
  - [Local map (since v0.0.66)](#local-map-since-v0066)
- [Map file formats: v1 and v2 (lava pools)](#map-file-formats-v1-and-v2-lava-pools)
- [Region name and debug teleport](#region-name-and-debug-teleport)
- [J: earned journal entries in two facing pages](#j-earned-journal-entries-in-two-facing-pages)
  - [Quests (since v0.0.59)](#quests-since-v0059)
- [Persistence and validation](#persistence-and-validation)
- [v0.0.27-rc4 selector regression and rc5 source correction](#v0027-rc4-selector-regression-and-rc5-source-correction)
- [v0.0.29 focus cancellation candidate](#v0029-focus-cancellation-candidate)
- [v0.0.29 lava and weather map study](#v0029-lava-and-weather-map-study)
- [v0.0.29 click marker and debug-HUD destination selection](#v0029-click-marker-and-debug-hud-destination-selection)

<!-- contents end -->

## Open map reports - 4 October 2026

The maintainer reports three post-release v0.0.28 map issues: both F10 command aliases
`dbg tp map` / `dbg map tp` failed (a later `dbg tp map` retry worked), the
IN-GAME MAP PROTOTYPE screen has many
white/yellow spots, and mouse clicks do not switch DEBUG / IN-GAME views.
The screenshot confirms the affected map screen but not the dots' meaning.
Source inspection has since found an incorrect visible-HUD gate and an omitted
AWM1 palette remap. The v0.0.29 candidates preserve checked teleport arrivals,
explicit map/story availability and map area metadata. Twenty-three focused
interpreted checks pass on Windows and Linux, with two actual C world-UI/console
fixtures passing on Linux. Fresh target map/click/teleport acceptance remains
pending; the published image has not changed. See
[MAP-TELEPORT-28](journals/BUG_JOURNAL-v0.0.29.md#map-teleport-28-map-teleport-commands-fail-from-f10-open)
and [MAP-SPOTS-28](journals/BUG_JOURNAL-v0.0.29.md#map-spots-28-whiteyellow-spots-on-the-default-map-open),
plus [MAP-VIEW-SWITCH-28](journals/BUG_JOURNAL-v0.0.29.md#map-view-switch-28-mouse-cannot-switch-map-views-open).

The post-RC3 development checkpoint adds two on-demand screens. They use the
normal single-player menu pause, leave music servicing active, capture mouse
movement and return to play without changing the player's location.

## M: Vvardenfell overview

M, or the bindable command `aw_worldmap`, opens the whole base-master island.
Drag or use arrows/WASD to pan; wheel or +/- to zoom. P centres the player, G
shows the original exterior-cell grid, and Home fits the island. M or Escape
closes it. A white cross is the player; labelled points mark current converted
areas. The position is derived from the current area's actual conversion origin
and scale. Inside an interior the screen explicitly has no exterior position
fix; it does not pretend interior coordinates are world coordinates.

In rc1 the cross reads the simulated player's current source XYZ on each draw,
using the same transform as the HUD. Zoom/pan survive closing and reopening the
map; P centres the current position. The header includes live source XYZ, since
ordinary walking may move less than one pixel at whole-island scale. The separate
mouse pointer is not the white player cross. The map pauses ordinary play.

**TODO, explicitly deferred:** original-game unexplored-map masking / discovery
occlusion. rc1 keeps the entire island overview visible.

The terrain is a reduced, palette-matched overview. The 489 by 512 pixel packet
is **250,520 bytes**, including bounds, ocean colour and area transforms. It is
allocated/read only when opened and freed on close. Map pixels stay in memory while open. The region-name lookup reads a small
record on first use or a changed exterior cell and caches that result. Ocean beyond the image has the same colour as the map's
water; panning has a bounded ocean margin. The separate
[terrain pass](WORLD_TERRAIN.md) supplies playable regions and their origins.

### Place markers (since v0.0.66)

The map shows the original game's place markers: a small square for every named exterior cell,
the way the original and OpenMW mark Vivec, the forts, camps, shrines and ruins. Cells that share
a name before the first comma ("Vivec, Arena", "Vivec, Foreign Quarter") are one marker, placed at
the average of their cells. Hovering the pointer over a square names the place in a box beside it.

- The in-game view shows the places the player knows: a place shows once its spot on the map is
  explored (below), and a script's `ShowMap` reveals the places whose names hold its text (the
  list `ShowMap` already kept, saved with the game and cleared by New Game).
- The debug view shows every place.
- No new image data: the names and cells come from `world/region-names.awn`, which the image
  already carries for the region line. The map reads it when it opens (66 bytes per named place
  for the moment of reading, then a 6 KB table of at most 128 markers while the map is open) and
  frees it on close. In play the only work is one region lookup when the player enters a new exterior
  cell.

Names appear only on mouse-over; in play the settlements are squares like the other places.

### Explored land (since v0.0.66)

In play the map hides the land the player has not explored. It opens around the player as
they walk, the way OpenMW's map fog clears: everything within 0.17 of a cell's width of the
player. A place square shows once its spot is explored, or once a script's `ShowMap` names it.
The debug view shows the whole island. The player's own markers and the hot marker are drawn
above the fog; hovering one shows its name.

- Resolution: each exterior cell is split into 8 by 8 squares (1024 units, about the width of a
  house). OpenMW splits a cell into 32 by 32 and the original game's saves into 16 by 16; 8 by 8
  keeps a whole explored island at about 17 KB.
- Memory: only cells the player has walked in hold a row, 12 bytes each, taken 64 rows (768
  bytes) at a time. A whole explored island (about 1,400 land cells) is about 17 KB; a fresh
  game a few hundred bytes. While the map is open, one bit per square over the map's bounds
  (about 3 KB) is built and freed on close. The map screen reads these rows, and every reveal
  changes them, so they stay in memory; the save is the copy on disk.
- In play: a reveal after every 128 units of walking, a few dozen bit tests.
- Saved with the game (block `AWFG`: 5 bytes for a fully explored cell, 13 for the others), read
  back when the game is loaded, and cleared by New Game. A save from before v0.0.66 starts with
  the map unexplored. It now has a section of its own in the save, as long as it needs (before,
  it shared the actor block, and a well explored map with a full block refused the whole save);
  the land is never cut. A well explored game, 1,752 cells and 300 rooms, takes 20,268 bytes.
  Saves made by the earlier v0.0.66 builds, with it in the actor block, still load.

### Your markers (since v0.0.66)

The player can set up to 256 named markers on the map by default (the setting `aw_map_markers_max`, 1 to
4,096, default 256, saved; lowering it keeps the markers already set and only stops new ones; since v0.0.66-dev3
the top is a guard, not the default, and a save with more markers than the allowance still loads them all).
The original game has no player markers; OpenMW keeps any number of notes per cell. Here:

- Right click on the map sets a marker at once, a cyan diamond named after the region there, or
  the nearest place when there is no region. In the debug view with the teleport pick, the
  middle button sets it (the right button picks the teleport target there).
- Left click on a marker opens its box: the name (up to 32 characters, typed in the console
  font), OK, Cancel and Delete; Enter is OK and Escape is Cancel. Left drag pans as before, so a
  pan never drops a marker. Hovering a marker shows its name.
- K, or the MARKERS button, opens the Markers menu: the list with each marker's name and region,
  sorted by name or by region (Tab, or a click on the header), a Find line that filters as you
  type, used and allowed counts. Enter or Centre shows the marker on the map; Rename opens its
  box; Follow makes it the hot marker; Delete (the button, the Delete key, Backspace on an empty
  Find line, or the row's Del) removes it; Remove all asks Yes or No first.
- The console: `marker find TEXT` lists the matches with their region, `marker show NAME` (or
  its number) opens the map on it, `marker add NAME` sets one at the player, `marker del NAME`
  removes one, `marker clear` opens the Yes/No box on the map, and `marker` alone lists them all.
  The same commands are `dbg map marker ...`.
- The old single marker of earlier versions becomes marker 1 the first time a game with it is
  loaded or the map opens.
- Saved with the game in its own block (`AWMK`): 8 bytes, then 9 bytes and the name for each
  marker, about 10 KB with all 256 set. The list is taken as markers are set, so an unused
  allowance costs nothing. New Game clears them. A save with markers is refused by builds from
  before this block, as every new save block is.

### The hot marker and the compass (since v0.0.66)

One more marker has no name and is never in the list: the hot marker, an orange diamond with a
filled centre. H on the map sets it at the pointer and H on it clears it; Follow in the Markers
menu puts it on a named marker; `marker hot` sets it at the player, `marker hot NAME` on a named
marker and `marker hot off` clears it. `dbg tp mark` goes to the hot marker, else to marker 1.

The compass is a thin strip at the top of the view (120 by 7 pixels), off by default
(`aw_compass 1`, saved): N where north is, an orange mark in the direction of the hot marker (at
the strip's end when it is behind), and "here", "near" (within 2 cells) or "far" beside it.
Indoors it shows north only. It costs one square root and one arc tangent a frame while on.

### Land colours (switch, since v0.0.66)

The builder can colour the world map the way OpenMW does: each cell's coarse heights (the 9 by 9
WNAM values of its land record) pick a colour from OpenMW's map colour table, water below sea
level, the shore band, then land darkening towards the peaks. The table's values come from OpenMW
(GPLv3) and live only in the builder. It is a switch: `AMIWIND_MAP_COLOURS=openmw` (or
`--map-colours openmw`); the default stays the terrain overview until a picture comparison of the
two is saved.

### Local map (since v0.0.66)

The in-game map has a World and a Local view, as OpenMW's map window has: the two buttons in the
header, or Tab.

- Outdoors, Local is the world map at the zoom where about the 3 by 3 cells around the player
  fill the window, centred on the player, with the doors of the loaded area as small marks on
  explored land. Hovering a door names where it leads. The map opens on the view last chosen
  outdoors.
- Inside, the map always opens on the room's own map: a top-down plan drawn when the map opens
  from the room's own faces (walls bright, floors dim, ceilings left out), with the player's arrow
  and the room's doors, each named on mouse-over after where it leads. World shows the island
  map as before. The plan has no pan, zoom or marker.
- Each room has its own fog: a 16 by 16 grid over the room's box, opened within 384 units of the
  player the same way the land opens, kept by the room's name, saved with the game inside the
  `AWFG` block (an `AWFI` part after the land: 2 bytes plus the name for a fully explored room,
  34 more otherwise) and cleared by New Game. A save without that part reads as before.
- Up to 2,048 rooms are kept (every room of the base game and both expansions, about 1,750); it
  was 256, and a room visited after the 256th never cleared, its doors hidden. A room is found by
  a small index of its name (the last one asked for at once), so the plan's 256 squares cost one
  lookup a frame.

Budget (counted, not yet measured on the emulator or the Pi):

| | Cost |
| --- | --- |
| RAM while the map is open inside | 48,048 bytes for the plan, freed on close |
| RAM in play | 52 bytes per room visited (48 for the room, 4 for its name index; blocks of 64 rooms), at most 2,048 rooms (106,496 bytes if every room is visited; 300 rooms: 17,408) |
| Disk | none: the plan comes from the loaded map, no new file |
| Save | 6 bytes plus 3 to 49 bytes per room |
| CPU on open | one pass over the room's faces and edges (the console line "Local map: ... ms" gives the time) |
| CPU in play | 256 square tests after every 32 units walked inside |
| CPU per frame while open | one copy of 312 x 154 pixels with a 16 by 16 fog table (the room found once), the doors |

Pictures made by the builder (a top-down picture per exterior cell and per room) would cost disk
and build time and are not built; they are worth adding behind a switch only if the plan's open
time measured on the Pi is too slow.

Not yet: the Detect and Mark spell dots.

## Map file formats: v1 and v2 (lava pools)

The builder writes `id1/world/map.awm` from your own game data at build time (nothing of it is in this
repository). Builder option `--world-map v1|v2` (config key `world_map`; recorded in the build receipt's
build settings and in `id1/world/conversion.json`) chooses the format; the default is **v2**.

- **v1 (`AWM1`):** the terrain overview above: header (size, source bounds, settlement count, ocean colour),
  60-byte settlement rows, then the palette pixels. `--world-map v1` writes it byte for byte as before.
- **v2 (`AWM2`):** the same bytes under the `AWM2` tag, followed by one `LAVA` section: the tag, the pool
  count, the outline point count and the lava colour (a palette index), then one 24-byte row per pool (its
  exterior cell, point count and bounds) and the outline points in original Morrowind world units, the same
  coordinates as the map's bounds. All little-endian.

The pools are the molten lava pools of the exterior cells found by the lava census rules
([Lava](LAVA.md#on-the-world-map)). The layer draws the **visible** lava (WORLDMAP-LAVA-MISMATCH-36): a pool is a
flat tile laid into the land, and where the land rises above its surface the lava is buried and the player sees
ground. The builder reads the land heights of the master (LAND records, bilinear between the 128-unit vertices)
and covers each pool with axis-aligned rectangles, one row per rectangle, on a 64-unit grid (finer for small pools
and ovals; 128 or 256 only when the rows would exceed the 8,192-row guard, five times the land cells of the base game and both expansions). A grid square is lava when at least
half of its sample points lie on land below the pool surface and its corners lie in the pool's footprint; a pool
the land buries completely has no row. The rows are rounded to whole units. Measured on the Game of the Year
masters: 349 pools in 27 cells (Molag Amur, Sheogorad, one at Red Mountain), 27 of them buried completely, 1,713
rectangles, 95,900 bytes of LAVA section (the earlier whole-outline layer, 1,412 points, was 19,688 bytes and
painted 54 % of the pool footprints over ground). The lava colour is the palette entry nearest a lava
orange that no terrain pixel and no ocean fill uses and that the sky palette step neither remaps nor remaps
onto, so on the map that colour means lava and nothing else (lava-named rock and ground textures are not
lava and are not painted). The earlier whole-footprint method stays in `lava_layer(pools)` without land.

The build checks the layer before it writes the file: every row belongs to a census pool in its cell and lies
inside that pool's footprint (within one unit), and `tools/lava_map.py` `audit` samples every pool at 16 units
against the land: a pool that paints more than 12 % of its footprint on buried land, leaves more than 20 % of it
visible and unpainted, or paints a point where the land is more than 96 units above the surface stops the step
with the cell named. On the real masters the layer paints 0.8 % of the footprints on buried land and leaves 0.7 %
unpainted, with the land at most 83 units above the surface under any painted sample. The receipt records pools,
covered, buried, rectangles and the audit areas. `python3 tools/lava_map.py --data-files DIR` prints the audit per
cell and a TOTALS row.

In the game both views (Debug and In-Game) draw the pools by default, with a "LAVA" legend in the map's
lower left corner. A pool's outline is filled where a screen pixel's centre lies inside it; a pool smaller
than a pixel marks the one pixel that holds its centre. The settings:

| Setting | Default | Meaning |
| --- | --- | --- |
| `aw_map_lava` (`dbg map lava`) | 1 | 0 hides the lava layer |
| `aw_map_format` (`dbg map format`) | 2 | 1 draws a v2 map as the v1 map (terrain and settlements only) |

A v1 file still loads and draws as before. The pools are read with the map when it opens and freed when it
closes; nothing is drawn or held while the map is closed. Cost while open: each pool is rejected by its
bounds before its outline is used; on the host the map draw took about 4 microseconds more per frame at the
whole-island view (349 pools, about 350 lava pixels) and no measurable extra when zoomed in. Not yet measured
on 68040 hardware.

## Region name and debug teleport

The regular map shows **REGION: <name>** at the bottom right beneath the map
viewport. It uses the player's original source coordinates, not the mouse,
view direction or panned map centre. The same name appears beside the optional
compass/heading HUD. Original exterior CELL coordinates select CELL.RGNN; that
identifier resolves through REGN.NAME to the original REGN.FNAM display name.
Negative coordinates use floor division by the game's 8192-unit cell size.
No region boundaries or names are invented. Missing data or interiors without
an exterior coordinate fix display `unavailable`.

`dbg tp map` (or `dbg map tp`) opens **DEBUG TELEPORT** with **CLICK ON TARGET TO TELEPORT**.
Click inside the map to select a destination and display a red crosshair. The
**TELEPORT** button appears at the bottom right; clicking it confirms travel.
Enter also confirms an existing selection; Escape cancels. Selection survives
zoom/pan without changing its world coordinates. Right-drag or arrows pan this
mode. The ordinary M map retains left-drag panning. Its v0.0.29 debug-HUD
mode also supports the explicitly confirmed right-click workflow below.

The target is resolved to existing detailed-town or world-terrain coverage.
Landing uses the actual standing collision hull, with a checked normal spawn
and an explanatory message if the selected column is blocked. Highest supported
surfaces can include roofs. Missing destinations fail without starting travel.
This is a single-player debug aid, not unlocked in-world fast travel, discovery
progression or a promise that every map pixel is a reachable destination.

## J: earned journal entries in two facing pages

J, or `aw_journal`, opens the journal as the original game does (JOURNAL-ORIGINAL-VIEW-59, since v0.0.59): two
facing pages of every earned entry, oldest to newest, each day under its date heading, opened at the newest
spread. The heading has the original's form, for example **16 Last Seed (Day 1)**: the day of the month, the
month's name and the days passed counted from 1. The month names and the word "Day" are the game data's own
settings (`sMonthMorningstar` to `sMonthEveningstar`, `sDay`); day 0 of the game clock is 16 Last Seed. Entries
of one day follow under one heading, a blank line apart; a heading never ends a page without its first line.

The button row has the original's buttons: **Prev**, **Topics**, **Quests**, **Close** and **Next**. Left/right,
Page Up/Down, Space and the wheel turn a spread; Home/End go to the first/last spread. **Topics** (or T) opens the
alphabetical topic index; a topic's page shows what was heard about it, with links to other topics. **Back** (or
Tab/T) returns to the dated journal. J/Escape closes. The mouse stays in the panel. F10 closes the panel and opens
the console. Startup restores J and M when an older saved configuration leaves them unassigned, while retaining
custom bindings.

**Quests** (or Q, or Tab) opens the view by subject: the quest index below. It plays the role of the later
expansion's Quests button and is an extra beside the original layout. Select with arrows, wheel, Page Up/Down, the
draggable scrollbar or mouse, then Enter/click to read that quest's entries one at a time (headings centred on the
left leaf, long titles wrapped, the date in the same form as above). Clicking the quest heading follows that
quest; **All entries** reads every entry this way. Tab returns to the index, Q or Backspace to the dated journal.

The dated journal is built when the book opens: each entry's text is read once, laid out with the book's font into
lines and pages, and freed when the book closes. It has no page or entry limit of its own. The dated history it
reads is the one described below; kept quest stages without a date (a quest past the history's 32 quests, or a
save's stages without their dates) come first, without a heading.

The supplied master contains 632 journal DIAL records, of which 629 have text:
**2,489 journal INFO entries**. They are typed binary DIAL/INFO records, not XML.
This master does not carry QSTN quest titles. Display labels are derived from
source identifiers, with explicit wording in `config/journal_titles.json` where
needed; identifiers remain authoritative for lookup and saves. These labels
must not be mistaken for authored quest-title metadata.

The source catalogue is private and stays on disk. Opening the journal loads
labels only into the bounded reader; a binary search fetches the selected entry's
text. The reader uses **28,188 bytes** while open and frees it on close. It never
reads all source quest text into the runtime heap. `%PCName`, `%PCRace` and
`%PCClass` expand for the current character within checked text bounds.

A script's or a conversation's `Journal` records a new earned stage with its date and time. Repeated grants
cannot duplicate it; `SetJournalIndex` changes a stage without writing history. Since v0.0.59 the dated history is
kept on the world change list with no quest or entry limit (JOURNAL-ORIGINAL-VIEW-59, AW-STATE-32-SLOTS-48): one
16-byte entry per earned stage (the quest's name hash, the stage, the day and the time of day), in the order earned,
saved only when it has an entry (save feature 128, `AWH1`, 16 bytes an entry). An older save's history (at most
256 entries of 32 quests) is taken over when it loads. The 32-slot copy is still written for older readers; it is not
a limit on play: when it is full, new entries still land in the dated history and are saved and loaded with it (kept
by a test since v0.0.66).
`dbg mwscript call journal QUEST N` records a stage as a script's `Journal` does; `dbg mwscript call setjournalindex
QUEST N` sets it without an entry; `dbg mwscript call getjournalindex QUEST` prints the index kept now. Since
v0.0.64 the console also takes the original's lines as typed: `Journal QUEST N`, `SetJournalIndex QUEST N` and
`GetJournalIndex QUEST` run the same three calls.

### Quests (since v0.0.59)

Every quest's stage is kept on the world change list by its quest id (the change list's quest table, saved with
the game), with no 32-quest limit. When the book opens it reads the stages the scripts hold at that moment and
lists every started quest from them (JOURNAL-BOOK-32-QUESTS-59):

- The quest index lists quest **names**, each name once even when several quest ids share it, sorted by name. A
  quest without a name is not listed; its entries still read under **All entries**. This is the rule OpenMW 0.51
  follows (`journalviewmodel.cpp`, `journalwindow.cpp`).
- By default the index shows the active quests. **Show all** (or the A key) adds the finished ones, drawn in the
  page ink instead of the link colour; **Show active** returns. A quest is finished when the journal entry of its
  kept stage finishes it (the entry's quest status in the game data; `world/journal.awj` carries it since the
  `AWJ2` form, which adds four bytes of status flags to each row; an `AWJ1` file still reads, with no quest
  finished).
- The entries: the dated entries first, in the order they were earned, then for every started quest whose kept stage
  has no dated entry (a quest past the dated history's 32 quests, or stages from a save without their dates) the
  entry of that stage, without a date, in quest order. Filtering by a name reads that name's entries.

The quest list lives only while the book is open: the catalogue rows of the started quests, one row per entry and
one per name (with 100 quests started, about 21 KB beside the reader), freed when the book closes. Opening the
book reads `world/quests.awq` once and, per started quest, one index lookup for its finished flag. `dbg mwscript call
journal QUEST N` sets a quest's stage for a test. The reader links quests; topics have their own pages (T from
the journal or the quest index).

## Persistence and validation

AWS2 appends explicit journal history to the existing save fields. Each entry
stores a quest slot, stage, elapsed day and milliseconds within the day. The
history adds 4,100 bytes to a full in-memory state. At most 4,100 bytes are added
to a save; actual saves store only earned entries. The 32 KiB save packet ceiling
is retained and tested with maximum actor and history counts. Old AWS1 decoding
retains indices but creates no invented entry dates or history. The independent
content-fingerprint check still governs whether an old save can be loaded.

Host tests cover negative-cell transforms, geometry conservation, full-object
overlap, malformed asset bounds, disk-member-relative offsets, missing files,
page/index navigation, panel exit, cached map pixels and journal text, history ordering,
duplicates, capacity transactions, corruption and legacy decoding. Native checks
open the island map, pan/zoom/grid/player-centre, read the opening journal entry,
follow the quest index, return to play and quickload the earned entry.

This is a working UI and persistence foundation. It does not implement all
quests, dialogue trees, inventory/equipment, local maps or island-wide travel.
The existing final-placement gate remains independent and unchanged.

## v0.0.27-rc4 selector regression and rc5 source correction

Maintainer playtesting of the rc4 prototype showed the In-Game Map Prototype title,
a Debug button, a pale active selector button with an unreadable light label,
and no Seyda Neen/Balmora settlement markers. The retained map payload includes
two town landmarks; rc4 rendering hid the landmark loop outside Debug mode. The
rc5 source now draws settlement landmarks in both modes and gives the selected
button a dark text interior and contrasting border.

The rc5 correction compiled in engine-002 and is included in stable v0.0.27;
the private HDF readbacks passed. The repaired Linux native world-UI fixture
also passed in the full 558-test Docker suite. Target confirmation remains pending. The
earlier rc4 HDF was not changed by the failed helper retries. This In-Game view
remains a terrain overview prototype, not the complete original-game world/local
map. Verify both button labels and selected states, retained markers in both
modes, player marker and heading, map scales and interaction. See the tracked
[selector regression](journals/BUG_JOURNAL-v0.0.29.md#map-reg-01-rc4-in-game-selector-hides-retained-settlement-markers-bug--regression).

Stable v0.0.27 also includes the archived aw_region_loading_delay setting from rc5:
two seconds by default, zero for immediate loading-screen presentation. It
applies to automatic crossings only; startup and explicit travel are immediate.
The delay begins at a safe checkpoint after blocking reads and is not a
performance fix. See the [cell-changing policy](CELL_CHANGING.md).

## v0.0.29 focus cancellation candidate

Losing window focus during map or journal dragging can lose the button-up event.
The candidate now cancels the held drag on focus loss and gain while preserving
the panel, cursor, map view and any selected teleport destination. Normal map
left-drag and teleport right/middle-drag retain their behavior.

The Linux source fixture reproduces four baseline lost-release failures and
passes all eleven candidate checks, including ordinary release, close/reopen,
selection preservation and discarded pending gameplay motion. Native focus and
capture transitions remain unverified. This is distinct from map-tab pointer
delivery and does not establish a fix for that report. See
[MAP-FOCUS-DRAG-29](journals/BUG_JOURNAL-v0.0.29.md#map-focus-drag-29-map-or-journal-keeps-dragging-after-focus-returns-open).

## v0.0.29 lava and weather map study

Survey source-authored lava references and transformed coverage before adding
a debug-world-map lava overlay. Do not confuse the unwanted palette dots with
POIs or lava. Expose missing/unresolved survey coverage. Ash/blight regions and
transition boundaries also require original CELL/REGN/script evidence, not a
guessed distance from Red Mountain. These are planned studies; see
[v0.0.29 work list](history/plans/PLAN-v0.0.29.md#weather-storms-and-lava-study).

v0.0.36: the lava part is done as the v2 map's lava layer
([Map file formats](#map-file-formats-v1-and-v2-lava-pools)): it is built from the source-authored pool
placements, never from palette colours, and the build checks its coverage. Weather regions remain a study.


## v0.0.29 click marker and debug-HUD destination selection

Opening M chooses Debug when the debug HUD is enabled and debug maps are
available; otherwise it chooses In-Game. The tabs remain selectable. The
independent `aw_map_debug_available` setting remains authoritative, and explicit
`dbg tp map` / `dbg map tp` commands continue to work with the HUD hidden.

In the ordinary M map, left click places or moves one cyan diamond marker.
Dragging beyond three virtual pixels pans instead of placing a marker; focus
loss cancels a pending click. The marker uses original world coordinates,
survives map reopening and normal save/load, and never moves the player.
Press C or click CLEAR to remove it. It occupies three bounded existing global
state entries; insufficient capacity refuses the whole update with a message.
(Since v0.0.66 this single marker is replaced by the named markers of
[Your markers](#your-markers-since-v0066): the right button sets them and the old
marker becomes marker 1.)

With the debug HUD enabled and the Debug tab selected, right click selects a
red destination crosshair. A TELEPORT button appears over the bottom-right map
area. Click that button or press Enter to confirm; selecting alone does not
travel. Switching tabs or closing the map cancels the pending destination.
This uses the same destination/placement checks as the explicit command.
The cyan user marker and red teleport selection are independent.

Focused source tests cover coordinate bounds, marker save/load, capacity refusal,
click versus drag, focus cancellation, mode selection and confirmation. Native
acceptance on the matching development build remains pending. With the default
`aw_modal_freeze 1`, these menu screens freeze world simulation and skip the
underlying 3D draw while UI input and soundtrack servicing continue.
