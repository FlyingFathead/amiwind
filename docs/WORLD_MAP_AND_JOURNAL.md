# World map and progression journal

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
mode. The ordinary M map retains normal drag behavior and never teleports.

The target is resolved to existing detailed-town or world-terrain coverage.
Landing uses the actual standing collision hull, with a checked normal spawn
and an explanatory message if the selected column is blocked. Highest supported
surfaces can include roofs. Missing destinations fail without starting travel.
This is a single-player debug aid, not unlocked in-world fast travel, discovery
progression or a promise that every map pixel is a reachable destination.

## J: earned journal entries in two facing pages

J, or `aw_journal`, opens the most recently earned entry in a two-page book.
Left/right, Page Up/Down, wheel and the bottom page links turn pages, continuing
to the previous/next earned entry at each entry boundary. Home/End selects the
first/last entry. Long entries continue onto additional spreads.

Headings are centred on the left leaf, never across the spine. Long titles wrap
fully and move that page's body text down; the right leaf keeps its normal text
area. Quest-index titles wrap too. Startup restores J and M when an older saved
configuration leaves them unassigned, while retaining custom bindings.

Tab or the **Quests** link opens the quest index. Select with arrows, wheel,
Page Up/Down, the draggable scrollbar or mouse, then Enter/click to filter entries for that quest. Clicking
the quest heading also follows that quest link. Backspace returns to all entries;
J/Escape closes. The mouse stays in the panel. F10 closes the panel and opens
the console. Gallery help/controls retain their separate context.

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

`AW_JournalAdd` records a new earned stage with its date/time. Repeated grants
cannot duplicate it. `AW_StateSet` may change an index without writing fictional
history. Capacity failure leaves the quest index and history unchanged; reward
transactions must propagate that failure. Current bounds are **32 quest IDs and
256 dated entries**, suitable for the present opening slice, not a claim that a
complete Morrowind playthrough fits. Expanding quest capacity and general script
execution are later milestones. The reader links quests; a complete dialogue
knowledge/topic-link system is still pending.

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

Owner playtesting of the rc4 prototype showed the In-Game Map Prototype title,
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
[selector regression](BUG_JOURNAL.md#map-reg-01-rc4-in-game-selector-hides-retained-settlement-markers-bug--regression).

Stable v0.0.27 also includes the archived aw_region_loading_delay setting from rc5:
two seconds by default, zero for immediate loading-screen presentation. It
applies to automatic crossings only; startup and explicit travel are immediate.
The delay begins at a safe checkpoint after blocking reads and is not a
performance fix. See the [cell-changing policy](CELL_CHANGING.md).
