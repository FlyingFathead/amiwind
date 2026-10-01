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

The terrain is a reduced, palette-matched overview. The 489 by 512 pixel packet
is **250,520 bytes**, including bounds, ocean colour and area transforms. It is
allocated/read only when opened and freed on close. Rendering the open map does
not read from disk. Ocean beyond the image has the same colour as the map's
water; panning has a bounded ocean margin. This does not add new walkable regions.

## J: earned journal entries in two facing pages

J, or `aw_journal`, opens the most recently earned entry in a two-page book.
Left/right, Page Up/Down, wheel and the bottom page links turn pages, continuing
to the previous/next earned entry at each entry boundary. Home/End selects the
first/last entry. Long entries continue onto additional spreads.

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
page/index navigation, panel exit, no draw-time disk reads, history ordering,
duplicates, capacity transactions, corruption and legacy decoding. Native checks
open the island map, pan/zoom/grid/player-centre, read the opening journal entry,
follow the quest index, return to play and quickload the earned entry.

This is a working UI and persistence foundation. It does not implement all
quests, dialogue trees, inventory/equipment, local maps or island-wide travel.
The existing final-placement gate remains independent and unchanged.
