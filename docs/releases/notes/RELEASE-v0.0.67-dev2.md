# AmiWind v0.0.67-dev2 (in development)

_Last updated with AmiWind v0.0.67-dev2 (18 November 2026)._

Development snapshot, 17 November 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.66: Forward It Is](RELEASE-v0.0.66.md). Previous snapshot: [v0.0.67-dev1](RELEASE-v0.0.67-dev1.md).

The second snapshot of v0.0.67. Its headline is three critical faults found in play on the v0.0.66 release, each fixed
in source and each checked in the emulator with its own engine: the game no longer stops on a loading screen in busy
places, autosaves are written again, and the wild has its creatures back. Besides them it carries the containers of
Seyda Neen and the opening's rule that nothing is taken before the census papers, the first Solstheim and Mournhold
steps of the expansions' work, the fallbacks for a place that cannot be loaded, the Toolkit's 3D views of rooms and
cells, and the builder's fail-fast work. Its emulator presets, `AmiWind-v0.0.67-dev2-FS-UAE.fs-uae` and
`AmiWind-v0.0.67-dev2-WinUAE.uae`, both start with 32 MB of Fast RAM, which the game needs. The changes below are
checked by the test suite and the gate of this snapshot; where a number comes from a session in the emulator, it says
so, and what has not been seen in play on a build of this snapshot says so as well.

## New since v0.0.67-dev1

### New

- **The `dbg netstat` console command** shows the last frame's update: how many things are in sight, the bytes their
  updates want against the room in the message, how many went and how many wait for the next frames, the fullest frame
  since the map started, and the models that took the most bytes. It is in the `dbg help` list and in the
  [console commands](../../AMIWIND_CONSOLE_COMMANDS.md) ([the frame message](../../NET_MESSAGES.md)).
- **Seyda Neen's crates, barrels, chests and sacks are drawn and open.** The town's frame places every container that
  opens in its cells: 19 containers, among them the 14 that were not drawn
  ([SEYDA-CONTAINERS-NOT-DRAWN-67](../../bugs/SEYDA-CONTAINERS-NOT-DRAWN-67.md)). The containers of the census office
  and of the prison ship are found by the view's aim again, where they are drawn as brushes of their own
  ([CONTAINER-BRUSH-ROWS-67](../../bugs/CONTAINER-BRUSH-ROWS-67.md)). The world-wide count of containers and the
  journey that proves the opening's are in the builder's tests.
- **A place that cannot be loaded names its error.** A door, travel, a spell, a script or a debug teleport to a place the
  build does not hold leaves the player where he was and shows the game's own box with the error and one button, **OK**;
  the game goes on. The load menu's error line fits its box, and the console says where the way back goes. A converted
  world's keys stay as they were. How it works: [when a place cannot be loaded](../../LOAD_ERRORS.md).
- **Units page.** [Morrowind units and AmiWind units](../../UNITS.md): the 0.25 world scale and where it matters (model
  export and import, gravity, the numbers in the docs).
- **The Toolkit opens every room tile in the 3D Inspector**, and a cell of the CHIM open world opens there too; the
  reader takes every world format from 0.5 to 0.12. The headline reads the expansions' rooms, and the rooms have a
  heatmap ([TOOLKIT-LOCAL-CHIM-CELL-NO-MAP-67](../../bugs/TOOLKIT-LOCAL-CHIM-CELL-NO-MAP-67.md)).

### Fixed

- **The game no longer stops on a loading screen in busy places** (the Bitter Coast, Vivec; register
  NET-VIVEC-ENTITY-PACKET-OVERFLOW-66, TODO LOAD-HANG-INVESTIGATE-66). Every frame the game's server writes the updates
  of everything in sight into one message of 1,024 bytes. An update has taken up to 22 bytes since the model numbers of
  v0.0.59-dev4, so a full frame ran past the end of the message and the screen side stopped reading it; the creatures
  and residents, which have the highest numbers, were also the first left out. Now each update is built whole and
  copied in only where it fits, the player, the actors and the nearest things first and the rest in the next frames; the
  game's own connection carries 8 KB; a message that cannot fit is caught whole, said once and dropped, never broken
  off in the middle; and the screen side drops a frame update it cannot read instead of ending the game. In the
  emulator, on the v0.0.67-dev1 image with the new engine, Vivec and the Bitter Coast spot where the game stopped loaded,
  the sweeps had no failures and no "packet overflow" line was printed; the same route with the engine of the previous
  snapshot printed 4,668 of them at Vivec. How the frame message is kept in its buffer: [the frame
  message](../../NET_MESSAGES.md).
- **Autosaves are written again** (register SAVE-AUTOSAVE-NOT-WRITTEN-67, TODO SAVE-AUTOSAVE-REGRESSED-67). Since the
  save became all-or-nothing in v0.0.66, one part that could not be kept refused the whole save, and a script error held
  every later save with it. A map change writes its autosave again, and the held save is let go. In the emulator, with
  the engine of the fix (session autosave-s3, TODO SAVE-AUTOSAVE-REGRESSED-67), a teleport to the census office wrote "Saved Autosave 1" and a teleport to Seyda Neen wrote
  "Saved Autosave 2", and nothing was held afterwards. A check now fails a build in which the autosaves stop.
- **Wild creatures are back outdoors** (register OUTDOOR-CREATURES-REGRESSION-66, OUTDOOR-CREATURES-HOME-CELL-67,
  ACTOR-QUEUE-OTHER-MAP-67, BUILD-ACTOR-SPEC-UNSPAWNABLE-67). Three causes met: the frame message above dropped the
  joined creatures first; the cell the player arrives in never joined its levelled creatures, about nine in ten of the
  wild's creatures; and the creatures still queued from the map before spawned in the next map at the old map's
  coordinates. Now the arrival cell gets its levelled creatures, a new map drops the old map's queue (its cells join
  again when that map is entered again), and the build's creature check counts only what the game can spawn and stops a
  build early when an outdoor creature has no model. In the emulator on the fixed engine (session proof2, TODO
  OUTDOOR-CREATURES-MISSING-66), 30 seconds after arriving, the Bitter Coast has 7 creatures alive against 1 before, Red
  Mountain 12, Pelagiad 21 and the Moonmoth Legion Fort 13. The history of the fault, version by version,
  is on its [report page](../../bugs/OUTDOOR-CREATURES-REGRESSION-66.md). The creatures now also come back when the same
  place is loaded again or a save made there is loaded (ACTOR-TABLE-SAME-MAP-RELOAD-67).
- **Nothing is taken, opened or harvested before the census papers allow the inventory**, as in the original, and a
  placed object shows no name or action line before then
  ([PRISON-SHIP-ITEMS-TAKEABLE-65](../../bugs/PRISON-SHIP-ITEMS-TAKEABLE-65.md)). Containers follow the original's
  inventory rule in their count and in the journey.
- **Solstheim's and Mournhold's models have their collision rows.** The collision surface table has the rows of
  Solstheim's exterior models, appended to the Bloodmoon layer, the rows of Mournhold's districts, and the banner hanger
  of the Royal Palace courtyard. A layer's rows are append-only, and a unit recorded with a shorter layer still matches,
  so a new row re-keys nothing (MESH-TABLE-LAYER-GROWS-67).

### Performance

- **A busy frame no longer costs a stop.** The frame message is built whole and paced across frames, nearest first (the
  numbers of the pacing against sending everything are being measured; the page will carry them).
- **A cell that cannot pass the collision check fails in seconds.** The CHIM areas' collision surface gate runs on the
  plain meshes before any stair collision unit is made, so a model the gate refuses no longer holds a core for tens of
  minutes first (one such unit of a Solstheim glacier cell took 19 minutes 33 seconds and the next 41 minutes 55 seconds
  before the gate stopped the cell: CHIM-MESH-STAIR-UNIT-SLOW-67).

### Builder and tools

- **A fault of the builder's own is told by name.** The hull chain audit names the models it fails on; the image's flora
  support check writes its measurements into the image's own folder, and the tracker data stage's diagnostic file no
  longer sits outside its declared outputs, so a later build reuses the stage
  (BUILD-CELL-PROGRESS-UNDECLARED-OUTPUT-67, fixed in source).
- **The early check `outdoor-creature-models`** stops a build in its first minutes when an outdoor creature or an outdoor
  levelled list of the base game has no model in the actor library.
- **The gate and delivery smoke now fail** on engine error lines, on a map change without an autosave, on no creatures at
  Seyda Neen (after its first load and after a reload of the same map) or at a wild stop, and on a frame update over the
  ceiling.
- **The expansions' ids are read by modules of their own**: the expansions' people outdoors are classed in a file of
  their own beside the policy, and the grounding reads the expansions' id file in a module of its own.
- **The Toolkit server reads the map heads of the cell table with the thread pool's default size**, with no worker count
  written in the tools.
- **The release file list and the docs index** carry the new pages and the frame message's rules include.
- **The bug register** has entries for the faults above, the CHIMport findings of Solstheim (cells only an expansion holds
  counted as empty, the glacier's stair unit, the two icebergs' collision) and the conversion's heavier models, each with
  its steps and, where there is one, its report page.

## What the v0.0.67 line works on

- **Tribunal and Bloodmoon in the game.** The order is the one of [v0.0.67-dev1](RELEASE-v0.0.67-dev1.md#what-the-v0067-line-works-on):
  the expansions' files checked; the changes they make to Vvardenfell; Solstheim built like the island; Mournhold's
  five districts as one exterior; scripts and dialogue; the save with their counts; the Toolkit's views; playtests.
  This snapshot adds the first of Solstheim's collision rows, Mournhold's district rows and the Toolkit's room views.
  The [roadmap](../../ROADMAP.md) holds the order.
- **The next snapshot**, v0.0.67-dev3, opens with the shared layout of every menu and message box and the crosshair's
  targeting.

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

- Walk the Bitter Coast and Vivec for a few minutes: the game keeps running and creatures are around you; `dbg netstat`
  shows each frame's update.
- Change maps (a door, a teleport) and look in Load game for the autosaves.
- Seyda Neen: open the crates, barrels and chests; in the opening, nothing is taken before the census papers.
- Try a teleport to a place the build does not hold: the box with the error, then the game goes on.
- The checklist of [v0.0.66](RELEASE-v0.0.66.md#what-to-check-in-play) stands for the rest.

## Known in this build

The [MWScript tracker](../../MWSCRIPT_FEATURES.md) shows how many of the game's scripts run: of the 1,074 scripts the
original uses, 611 run and 9 more are carried by AmiWind's own code; 433 belong to Mournhold and Solstheim and wait for
them. The [CHIM progress tracker](../../chim/PROGRESS_TRACKER.md) shows how far each land and part has come.

- **Mournhold and Solstheim are not playable yet.** Their rooms are in the image, but not their outdoors, the way there
  or their quests. Two of Solstheim's models, the icebergs of the Mortrag Glacier, cannot be converted yet: their
  collision is over the clipnode budget (COLLISION-ICEBERG-CLIPNODE-BUDGET-67). The Royal Palace's Reception Area runs
  at 3.0 to 5.7 frames a second on the Raspberry Pi 4B (INTERIOR-RECEPTION-AREA-FPS-67).
- **Fixed in source, still to be seen in play on a build of this snapshot:** the frame message, the arrival cell's
  creatures, the old map's queue, the autosaves' check, the load fallbacks' box and Seyda Neen's containers. Their
  register entries stay open until then.
- **Found in play on the v0.0.66 release, open in this build** (register entries, fixes under way for v0.0.67-dev3):
  - the World tab of the map draws no land on its first showing, until you switch to the Local tab and back
    (MAP-WORLD-TAB-BLANK-67), and the map shows places you have never visited, Pelagiad and the Moonmoth Legion Fort
    among them (MAP-PLACES-SHOWN-UNVISITED-67);
  - drawing the fists in first person shows a lump in the top left corner instead of the fists (FP-FISTS-LUMP-67);
  - the aimed character's name and the label of the door behind him are drawn on top of each other
    (HUD-TEXTS-OVERLAP-67), and an empty box flashes after the first journal hint (UI-JOURNAL-HINT-EMPTY-BOX-67);
  - menus place their boxes and buttons at positions of their own, so margins differ and buttons touch the bottom edge
    (UI-NO-SHARED-LAYOUT-67; [UI-TEXT-BOX-CLEARANCE-64](../../bugs/UI-TEXT-BOX-CLEARANCE-64.md)), and the class window's
    rows are hard to read (UI-CHARGEN-CLASS-FONT-67);
  - the birthsign and race windows: [CHARGEN-ABILITY-DESCRIPTIONS-65](../../bugs/CHARGEN-ABILITY-DESCRIPTIONS-65.md)
    (listing each ability's effects, awaiting confirmation in a numbered build); the magic menu's tutorial box is shown
    twice (TUTORIAL-BOX-SHOWN-TWICE-65);
  - a teleport to some Tribunal characters, such as Ten-Tongues Weerhat and the Assassin, drops the player through the
    floor (TP-BEING-TRIBUNAL-FALLS-THROUGH-67);
  - idle characters do not turn towards the player (NPC-IDLE-TRACK-PLAYER-67); the plate on the Census and Excise
    Office's shelf cannot be taken (CENSUS-SHELF-PLATE-BAKED-67); a Hypha Facia mushroom on a tree's side floats in the
    air ([HARVEST-HYPHA-FACIA-FLOATING-65](../../bugs/HARVEST-HYPHA-FACIA-FLOATING-65.md)).
- **Locked containers never open**: no key, lockpick or Open spell works on them
  ([LOCKED-CONTAINERS-NEVER-OPEN-67](../../bugs/LOCKED-CONTAINERS-NEVER-OPEN-67.md)); a container whose script takes
  the activation opens directly, without it
  ([CONTAINER-SCRIPT-ACTIVATE-67](../../bugs/CONTAINER-SCRIPT-ACTIVATE-67.md)).
- **The dead bodies the original places outdoors show only when the player arrives in their cell**, not when the cell
  joins around the player (OUTDOOR-CORPSE-NEIGHBOUR-JOIN-67).
- **A script that moves the player runs only after the console is closed**, when it was run from the console
  (MWSCRIPT-MOVE-WAITS-FOR-CONSOLE-67).
- **The conversion makes 556 models heavier than the original game** (512 in rooms, 44 outdoors;
  CONVERT-HEAVIER-THAN-ORIGINAL-67), and the per-model replacements reach the outdoor frames only
  ([VISUAL-EVERYWHERE-ROOMS-67](../../bugs/VISUAL-EVERYWHERE-ROOMS-67.md)).
- **The Heart Chamber's collapse is not animated, so the end of the main quest cannot play yet**
  (`ENDGAME-CHAMBER-COLLAPSE-63`).
- **A resident can still stand in front of a door**
  ([WANDER-DOOR-RULE-66](../../bugs/WANDER-DOOR-RULE-66.md), open).
- **Coming back out of a door onto a resident standing on its arrival point**
  ([DOOR-ARRIVAL-INSIDE-ACTOR-66](../../bugs/DOOR-ARRIVAL-INSIDE-ACTOR-66.md)): fixed in source and covered by tests, still
  to be seen in play.
- **One of the three dreamer workers stays alive after EndGame's `SetHealth 0`**
  ([MWSCRIPT-SETHEALTH-ZERO-NO-DEATH-66](../../bugs/MWSCRIPT-SETHEALTH-ZERO-NO-DEATH-66.md)).
- **Outdoor residents** ([CHIM-EXTERIOR-ACTORS-MISSING-46](../../bugs/CHIM-EXTERIOR-ACTORS-MISSING-46.md), open for a long
  time): the register's entry stays open until the wild's people and creatures are seen in play on a build of this line.
- **Buttons and levers that should act**: the Ghostgate switches have no in-game check on a v0.0.64 or later build
  (`WORLD-BUTTONS-62`, in the [bug tracker](../../BUGS.md)).
- **A load can stop in the emulator in test sessions**
  ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)): an interrupt request lost in the
  drive that serves the test sessions' remote-console folder; players have no such drive.
- **The save's whole round trip is not proven in play** (`SAVE-STATE-FIXED-CAPS-66`).
- **Bloodmoon's werewolves have no model yet** (`PLAYER-WEREWOLF-ROBE-NOT-BAKED-66`, `NPC-WEREWOLF-NO-MODEL-66`).
- **The shores and pond edges still run in saw-tooth steps**; the fix needs a world rebuild
  ([INLAND-SHORE-29](../../bugs/INLAND-SHORE-29.md)).
- **In the builder:** the image step's player view remakes all its player bodies in every build
  ([BUILD-PLAYER-VIEW-UNDERUSED-48](../../bugs/BUILD-PLAYER-VIEW-UNDERUSED-48.md)); the actor library's appearance bakes
  have no unit cache ([NPC-LIBRARY-NO-UNIT-CACHE-63](../../bugs/NPC-LIBRARY-NO-UNIT-CACHE-63.md)); the guard torch step
  bakes six models one at a time only to skip them
  ([GUARD-TORCH-SCRATCH-SERIAL-67](../../bugs/GUARD-TORCH-SCRATCH-SERIAL-67.md)); the frame memory report numbers its
  peak model lists differently from scratch and with reuse
  ([FRAME-HEAP-PEAK-MODELS-NUMBERING-67](../../bugs/FRAME-HEAP-PEAK-MODELS-NUMBERING-67.md)); one stair collision unit
  of a Solstheim glacier cell takes 19.5 minutes on one core (CHIM-MESH-STAIR-UNIT-SLOW-67); and the image and room batch
  stages use too few cores
  ([BUILD-IMAGE-UNDERUSED-32](../../bugs/BUILD-IMAGE-UNDERUSED-32.md),
  [BUILD-IMAGE-SCAN-GROUND-UNDERUSED-52](../../bugs/BUILD-IMAGE-SCAN-GROUND-UNDERUSED-52.md),
  [BUILD-ROOM-BATCHES-UNDERUSED-54](../../bugs/BUILD-ROOM-BATCHES-UNDERUSED-54.md)).
- From [v0.0.66](RELEASE-v0.0.66.md): its Known list stands. Every other open entry is in the
  [bug register](../../BUGS.md).
