# AmiWind v0.0.68-dev8 (in development)

_Last updated with AmiWind v0.0.68-dev8 (22 November 2026)._

Development snapshot, 22 November 2026, in development. Running on CHIM Engine v0.2.2. Previous snapshot:
[v0.0.68-dev7](RELEASE-v0.0.68-dev7.md). Previous release: [v0.0.67: Tribunal Introduced](RELEASE-v0.0.67.md).

The eighth snapshot of v0.0.68. The version is titled **Solstheim Is Here**: the release for which Solstheim is to be
complete; the snapshots come before it. This one brings the Mortrag Glacier and the sea between the islands into the
build, makes fights ordered by scripts wait for their turn instead of being lost, lets the scripts that wait for the
player's blow see it, and otherwise is mostly the game's menus. The windows of a running game keep the
game's own colours after a start from the main menu by a console command, Escape in play opens the in-game menu, which
now has the original's rows and questions, and the map screen is the original's map in the menus' framed style. Beside
them: containers and bodies whose script takes their use give it to the script, scripts can start fights for sixteen
actors at once instead of four, the outdoor draw distance can differ by region, two debug camera moves film pans and
glides, and the rally-game trees and the see-through fix for outdoor models come in behind switches that are off. Its
emulator presets, `AmiWind-v0.0.68-dev8-FS-UAE.fs-uae` and `AmiWind-v0.0.68-dev8-WinUAE.uae`, both start with 32 MB of
Fast RAM, which the game needs.

How each change was checked is said on its line. Every change here is covered by tests and by the gate of its commits
(12521 for the glacier and the sea cells; 12541, 12542, 12544 and 12545 for the containers, the fights and OnPCHitMe;
12580 for the draw distance; 12620 for the camera moves; 12661 for the trees; 12680 and 12681 for the menus; 12702 and
12703 for the map). The menus' colours, the Escape menu and the map are seen on the PC emulator; the rest is not yet seen
in play. The bug
tracker entries are set fixed in source where the change mends a fault; they are closed when this snapshot is recorded.

## New since v0.0.68-dev7

### Menus and the interface

- **The windows of a running game are drawn in the game's colours after a start from the main menu by a console command.**
  After a game was started from the main menu by a console command (a debug character start, a typed map), the main
  menu's mark stayed set until Escape was pressed, and the inventory with its item icons, the map, the journal, and the
  stats and magic windows were drawn through the title art's palette, which shares only the interface's own colours with
  the game's; the icons, the character picture and the map took the art's orange-brown. The main menu is now the menu with
  no game behind it, so those windows always use the game's palette. The interface's own colour picks also skip the 16
  entries of the new ice ramp while the palette holds them, so white text keeps its cream and the windows keep the colours
  they had before the ramp; the ramp stays for the textures, and ice and snow keep their cool colours
  (MENU-PALETTE-RED-CAST-68). The look book has a new page for it
  ([menu colours in the game palette](../../lookbook/MENU-COLOURS-GAME-PALETTE.md)), which opens each window after such a
  start and reads the palette back. New readout: `dbg ui palette`. Covered by new tests of the menu and the interface's
  colour picks and the gate 12680; not yet seen in play.
- **Escape in play opens the in-game menu after such a start.** A game started from the main menu by a console command
  kept the main menu's mark, so Escape in play opened the main menu (New game, Load game, Options, Exit game) over the
  running game and Escape could not close it; to the player the game had gone back to the main menu. A menu opened while a
  game runs is now the in-game one (MENU-TITLE-AFTER-CONSOLE-START-68).
  Covered by a new test of the menu and the gate 12680; not yet seen in play.
- **The in-game menu follows the original.** The rows are Return To Game, New Game, Save Game, Load Game, Options Menu and
  Exit Game, each worded as the game's own settings word them (the original's English until the image carries them). While
  a game runs, Exit Game, New Game and loading a saved game ask the original's own questions with Yes and No before the
  current game is lost; No is the default, and Escape keeps the game too. Exit Game on Yes leaves for the main menu. The
  game stays frozen behind the menu, and the menu says **Paused** in the game's font; the original shows no such caption,
  so it can be switched off (`dbg ui paused 0`, saved as `aw_menu_paused_caption`), which draws the logo there instead.
  The main menu keeps its own rows and questions. The texts are read once a session, at the menu's first opening, never in a
  frame ([PAUSE-MENU-CONTINUE-CONFIRM-68](../../KEYMAPS.md)). Covered by new tests of the menu and of the game-text reader
  and the gate 12681; not yet seen in play.
- **Map version 2 is the default map screen.** M opens the original's map in the same golden frame as the attributes,
  inventory and magic windows: the window box and its title bar, the map in a box of its own and a footer box, with no
  debug buttons and no lava colour or legend. The map itself stays whole: explored land, place squares named on
  mouse-over, markers, the original's arrow, World and Local (Tab or the footer's tabs) and the markers. The title names
  the place the player is in as the game data names it: a room's own name, an outdoor cell's own name, else its region's
  name, else Wilderness. The footer names the zoom and pan keys (+/- and the wheel zoom; drag, the arrows or WASD pan; Home
  fits; P centres) and the key that closes the map. The title fits the game's font for every region, outdoor place and
  room name, measured on this snapshot's font (all 16 regions, 95 named outdoor cells and 1,328 rooms; none falls back to
  the console glyphs). The map before it is version 1, kept: `dbg maptype 1` and `dbg dbgmap` bring it back, and the
  debug teleport map keeps it
  ([MAP-VERSION-2-DEFAULT-68](../../WORLD_MAP_AND_JOURNAL.md)). Covered by new tests of the map screen, the title layout and
  the title bar, which draws the other windows' titles as before, and the gates 12702 and 12703; not yet seen in play. The
  tracker item is still open until it is.

### Scripts and combat

- **Containers and bodies whose script takes their use now give it to the script.** A container whose script reads
  OnActivate opened its strip at once, and the script's Activate did nothing on it: the Stalhrim deposits of Raven Rock
  gave their Stalhrim without the pick, and the summoning and cursed chests opened without their effect. A dead actor's
  body could be searched before its script allowed it (the Spriggans of Solstheim). The use key on a container or a body
  now asks the script first; the script's Activate is the object's own use (a container's lock, trap and strip, a body's
  search), and a living actor keeps its talk
  ([CONTAINER-SCRIPT-ACTIVATE-67](../../bugs/CONTAINER-SCRIPT-ACTIVATE-67.md)). Covered by tests and the gates 12541 and 12542;
  not yet seen in play. The [script tracker](../../MWSCRIPT_FEATURES.md) now says, for each of the 259 functions the
  game's scripts call, what the engine does in play (153 full, 100 in part with what is missing, 6 none), read from the
  source against the original's rules and kept by a test; this is not yet proven in play, and the page's OnActivate and
  Activate rows are full.
- **Fights started by scripts have sixteen slots instead of four.** The original has no limit on the actors fighting at
  once; the game's scripts start six actors at the player at once and fifteen against each other in the Skaal village
  attack. The fifth StartCombat of a tick was refused, a third pair set against each other never fought, and a dead
  actor's body could not be laid down while four fought. The slots are sixteen now (`dbg combat slots N` lowers them for a
  comparison, 4 being the earlier cap). A fifth armed fighter draws the items in its hands only while the map has room for
  them; otherwise it fights with nothing drawn and is counted, so no map's memory plan changes
  (MWSCRIPT-STARTCOMBAT-FOUR-FIGHTERS-68, in part). Covered by new tests
  that fail on the engine before at the fifth fighter, the third pair and the body, and the gate 12544.
- **A fight a script orders is kept until it can start.** A StartCombat is now an order kept on the actor's record: it
  starts at once when the actor is loaded and a slot is free, otherwise once a second when the actor and its target are
  loaded and alive near the player, nearest first. A kept fight between two actors starts again against that actor, not
  against the player ([COMBAT-RESUMED-FIGHT-TARGETS-PLAYER-68](../../bugs/COMBAT-RESUMED-FIGHT-TARGETS-PLAYER-68.md)), and
  `dbg combat calm` ends the orders and the hostile mark, so a calmed actor talks again
  ([DBG-COMBAT-CALM-LEAVES-HOSTILE-MARK-68](../../bugs/DBG-COMBAT-CALM-LEAVES-HOSTILE-MARK-68.md)). The record's save block
  gains four bytes only when an order names another actor; older saves load as before, and their actors that still carry
  the hostile mark now hold it as an order against the player, as the original does. A StartCombat no longer reads the
  fighter's sheet from disk before a slot is known
  ([STARTCOMBAT-SHEET-READ-BEFORE-SLOT-68](../../bugs/STARTCOMBAT-SHEET-READ-BEFORE-SLOT-68.md)). Covered by new tests that fail
  on the engine before, and the gate 12545.
- **Scripts that wait for the player's blow now see it.** Nothing set OnPCHitMe, so the 32 scripts of the three masters
  that test it (the guards, quest givers and others that answer a blow) never saw one. The player's blow in reach, hit or
  miss, and a harmful spell now set it on the actor's own script, as the original does
  ([MWSCRIPT-ONPCHITME-NEVER-SET-68](../../bugs/MWSCRIPT-ONPCHITME-NEVER-SET-68.md)). An actor whose script reads it and
  whose Fight is 0 still fights back when struck; filed. Covered by a new test and the gate 12545.

### Draw distance and the camera

- **The outdoor draw distance can differ by region.** One rule now writes the distance: with the new option **Fog distance
  auto** (Options, Video; on by default) each region's own default applies, 300 in every region without a row; with it off,
  the player's own value applies everywhere. The map's limit and the location fog only shorten it. The rule runs on events
  (a map arrival, a setting, a change of cell or fog), never per frame; a walk across a region border eases over about a
  second, an arrival applies at once, and nothing new is saved with a game. The option takes the place of the reset row, and
  a configuration saved before it keeps its own value with Auto off. Solstheim's six regions are listed at 540 as a trial
  that applies only with `dbg fog region trial` on (off by default) until the frame rate on real hardware is measured and
  the maintainer decides. New console words: `dbg fog distance auto`, `dbg fog auto`, `dbg fog region trial`; the image
  step writes the region table
  ([REGIONAL-DRAW-DISTANCE-68](../../KEYMAPS.md)). Covered by a new test of every order of six events and the gate 12580; the
  frame rate of the trial distance is not measured.
- **Two debug camera moves for video.** `dbg cam pan [DEGREES] [HOLD] [speed DEG] [photo]` (also `dbg pan cam`) pans from
  the view now, 360 degrees by default, with the first and last frame held and an eased start and stop; `dbg cam track
  [SPEED] forward N` or `to MARK [HOLD]` glides along the heading or to a camera mark on the map. Both end by themselves or
  on Escape or a right click, print nothing on the screen, and a shot started in third person keeps the body drawn
  ([DBG-CAM-PAN-TRACK-68](../../CAMERA_MARKS.md)). Debug tools; covered by new tests and the gate 12620.

### Solstheim: the glacier and the sea between the islands

- **The Mortrag Glacier is in the build.** Its nine cells were left out because their ice did not fit the 32 MB mark.
  The way of fitting it the maintainer chose (exact-footing collision on the shard and both icebergs, and the shard's
  drawn mesh simplified with its seams locked) is now the builder's default for those ice models, and all nine cells
  are built and fit: the fullest peaks at 13.2 of 13.6 MB in the active ring
  ([SOL-ICE-CELLS-RING-OVER-68](../../bugs/SOL-ICE-CELLS-RING-OVER-68.md),
  [COLLISION-ICEBERG-CLIPNODE-BUDGET-67](../../bugs/COLLISION-ICEBERG-CLIPNODE-BUDGET-67.md)). The way and its numbers are on
  the [glacier page](../../chim/SOLSTHEIM_GLACIER.md). Only Solstheim's stages are built again for it.
- **The sea between the islands.** Six empty seabed cells near Solstheim become seabed frames and one sea cell with its
  own record becomes an ocean frame, the same way the main island's sea cells are built; Solstheim now has 151 built
  cells instead of 135. Two more sea cells wait for a builder fix
  ([CHIM-SEA-BETWEEN-ISLANDS-64](../../bugs/CHIM-SEA-BETWEEN-ISLANDS-64.md),
  [TRACKER-OCEAN-CELL-ISLAND-BASE-ONLY-68](../../bugs/TRACKER-OCEAN-CELL-ISLAND-BASE-ONLY-68.md)). Covered by new tests and
  the gate 12521; not yet seen in play.

### Solstheim's trees

- **Rally-game trees, behind a switch.** The densest forest frame of Solstheim spent 41 to 60 percent of its renderer time on
  the spruces' faces. A test build can now make every tree of the island as a trunk in polygons and a crown of eight
  see-through panes whose outline is cut from a picture of the original crown (`--chim-sol-tree-copies rally`; `rally-switch`
  builds the original trees and the four methods side by side as alternatives). On the one built frame it was measured on,
  faces a spruce fall from 472 to 724 to 128 or 14, and faces per view from a median of 45,964 to 12,330 or 4,985. It is
  not in a normal build, and the pictures are not yet seen in play; the maintainer chooses which method stays
  ([SOLSTHEIM-TREES-THREE-LOD-68](../../WORLD_TREE_SPRITES.md), open).
- **See-through faces of outdoor models, behind a switch.** The see-through pass drew the see-through faces of placed models
  from the world's origin, so outdoors they were not drawn at all and every face past its list was drawn solid. The new
  switch `aw_seethrough_placed 1` draws them from each placement's own position, as the pass for the brush models does. It
  is off by default until the pictures are seen, and the rally panes need it on
  (FENCE-PLACED-ORIGIN-68, open).

## Builder and tools

- **The game's default settings always run.** With this snapshot's new settings the image's default settings file had
  grown past the engine's command buffer (8,511 bytes against 8,192), and a file that does not fit is dropped whole, so
  none of the defaults ran and no outdoor creatures appeared; the delivery check caught it before the snapshot went out.
  The buffer is now 32,768 bytes, and the image step refuses any start-up settings file at or over half of it
  (CFG-OVER-COMMAND-BUFFER-68). Covered by new tests of the check and the gate of the commit.
- **New in the tools:** `tools/region_draw.py` writes the region draw table, `tools/chim_tree_rally.py` makes the rally
  trees, and `tools/map_title_fit.py` measures every map title in the game's font. The scripts' effect-in-play file
  `config/mwscript-effects.json` is part of the release file list.
- **The scene palette change of dev7 is unchanged.** The interface's colour picks now skip the ramp's entries as said above;
  the ramp, and what it does for the ice and snow, stands.

## What the v0.0.68 line works on

- **Tribunal and Bloodmoon in the game**, in the order of [v0.0.67](RELEASE-v0.0.67.md#known-in-this-build)'s notes and
  [the roadmap](../../ROADMAP.md): Mournhold's quests and play, Solstheim built like the island (its first cells are in
  the build since dev3, its glacier since dev8), the expansions' remaining scripts and dialogue, the save with
  their counts and the playtests.
- **Solstheim's forests and distance:** the trees' method awaits the maintainer's choice from the pictures, and the region
  draw distance for Solstheim's six regions is a trial until the frame rate is measured on real hardware.
- **Audits of what the original has**, planned: every creature record checked field by field against its original, every
  lever, valve, button and crank listed with whether it works, and the progress summary showing cells converted but not
  yet in an image; see the roadmap.
- **The werewolf drawn as the werewolf, without gaps** (WEREWOLF-BODY-63): planned, not in this snapshot.

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

The [checklist of dev7](RELEASE-v0.0.68-dev7.md#in-game-checklist-for-this-snapshot) stands. In addition:

- **The menus.** Start a game from the main menu with a console command (a debug character start), open the inventory and the
  map: the icons, the character picture and the map keep the game's colours. Press Escape: the in-game menu opens with
  Return To Game, New Game, Save Game, Load Game, Options Menu and Exit Game and a Paused caption; Escape closes it. Pick
  Exit Game, New Game and Load Game in turn: each asks its question first, and No keeps the game. Say what looks or reads
  differently from the original.
- **The map.** Press M: the map is in the golden frame with the place's name in the title and the keys in the footer; Tab
  switches World and Local. Name a place whose title looks cut or wrong. `dbg maptype 1` brings the old map back.
- **Containers and bodies.** Take the Stalhrim from a deposit in Raven Rock, open a chest with a script, search a
  Spriggan: each should give its use through its script. Say what happens.
- **Draw distance.** In Options, Video, leave Fog distance auto on and walk across a region border outdoors; then switch it
  off and set a value. Say what you see.
- **The Mortrag Glacier.** Walk up onto the ice north of Solstheim: the shards and icebergs are there, you stand on the
  ice where it is drawn, and nothing gapes. Say where the ice looks or feels wrong.
- **Fights by scripts.** Visit the Skaal village during its attack, or let several actors turn on you at once: each should
  fight. Strike a guard or a quest giver once and say how they answer.

## Known in this build

The [MWScript tracker](../../MWSCRIPT_FEATURES.md) shows how many of the game's scripts run and what each function does in
play; the [CHIM progress tracker](../../chim/PROGRESS_TRACKER.md) shows how far each land and part has come.

- **Seen in play:** on the PC emulator with the gated engines, the menus' colours after a console start, the Escape menu
  with its questions, and the map screen (the maintainer approved its look). The other changes are covered by tests and
  the gates named above, not yet seen in play.
- **Fights:** combat state is not saved ([COMBAT-NOT-SAVED-33](../../bugs/COMBAT-NOT-SAVED-33.md), open); a cheaper
  thinking pass for many fighters is not done yet, and its cost is not measured
  (MWSCRIPT-STARTCOMBAT-FOUR-FIGHTERS-68, open).
- **Trees and distance:** the rally trees and the see-through fix are off by default and not seen in play.
- **The map inside rooms:** inside rooms on the shared room store the map opens on the World view instead of the room's
  plan ([MAP-LOCAL-ROOM-PLAN-CHIM-ROOMS-68](../../bugs/MAP-LOCAL-ROOM-PLAN-CHIM-ROOMS-68.md), open).
- **Menus:** the item icons and the map's sea keep the colours that the game palette gave them; they are not
  re-quantised.
- **The entrance to Stahlman's Gorge:** it lies under the water below the Mortrag Glacier, and the player reaches it by
  swimming under the ice, as in the original. The build's door check has no case for an entrance reached by swimming yet,
  so this one is on the check's known list (DOOR-CHECK-NO-SWIM-CASE-68, open); not yet seen in play.
- **The sea between the islands:** two open-sea cells near Solstheim, -29,23 and -28,24, are not built yet; they hold
  nothing but water and come in the next snapshot (TRACKER-OCEAN-CELL-ISLAND-BASE-ONLY-68, open).
- From [v0.0.68-dev7](RELEASE-v0.0.68-dev7.md#known-in-this-build),
  [v0.0.68-dev6](RELEASE-v0.0.68-dev6.md#known-in-this-build), [v0.0.68-dev5](RELEASE-v0.0.68-dev5.md#known-in-this-build),
  [v0.0.68-dev4](RELEASE-v0.0.68-dev4.md#known-in-this-build), [v0.0.68-dev3](RELEASE-v0.0.68-dev3.md#known-in-this-build),
  [v0.0.68-dev2](RELEASE-v0.0.68-dev2.md#known-in-this-build), [v0.0.68-dev1](RELEASE-v0.0.68-dev1.md#known-in-this-build)
  and [v0.0.67](RELEASE-v0.0.67.md#known-in-this-build) and its snapshots: their Known lists stand for what is not named
  here, among them the census courtyard re-entry stop, Mournhold's and Solstheim's unfinished play, the open builder
  entries and the look book's open entries. Every other open entry is in the [bug tracker](../../BUGS.md).
