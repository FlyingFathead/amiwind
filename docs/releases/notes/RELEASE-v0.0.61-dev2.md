# AmiWind v0.0.61-dev2 (in development)

_Last updated with AmiWind v0.0.61-dev2 (2026-11-06)._

Development snapshot, 6 November 2026, in development. Running on CHIM Engine v0.2.2. Previous snapshot:
[v0.0.61-dev1](RELEASE-v0.0.61-dev1.md). Previous release: [v0.0.60](RELEASE-v0.0.60.md).

The second snapshot of v0.0.61 and the first with game changes: player casting and the spell-effect system, weapons and
first-person stances, one set of stats for every being, an inventory without a fixed number of kinds, and carriable
lights that take their flame with them. Most of it was proven in game on the dev1 image with the new engine; the parts
that need an image built with them are listed under "Not yet seen in game" and are checked on this build. The game needs
32 MB of Fast RAM, and the emulator presets of this snapshot have it.

## New since v0.0.61-dev1

### Magic and casting

- **Casting.** `R` (or `dbg cast ready`) readies magic and the attack button casts the selected spell; the Magic
  window (`O`) selects it. The magicka is paid at the start and the cast is refused when it is short; the chance to
  succeed follows the original's rules; a failed roll keeps the magicka. Self, Touch (at blow reach) and Target spells
  (a bolt that lands on the actor aimed at, with areas) deliver their effects; a harmful spell starts the fight;
  powers work once a day; the school skill rises with use. In god mode a cast always succeeds and is free
  ([PLAYER-START-SPELLS-NOT-KNOWN-61](../../bugs/PLAYER-START-SPELLS-NOT-KNOWN-61.md) for what is still missing,
  [GODMODE-COMBAT-DAMAGE-61](../../bugs/GODMODE-COMBAT-DAMAGE-61.md)).
- **Spell effects.** Any of the 143 effects can be applied to any actor by reference (64 entries, 32 of them for the
  player), applied over time or once as the original does, with harmful ones told apart. Effects are kept in the save
  (a new block; older saves still load). The effects of non-player actors run while they are loaded and their damage
  feeds the fight. Light lights the player; Resist and Weakness to Normal Weapons are read by the combat code; Burden
  and Feather feed the carry weight. Creatures ignore skill effects.
- Checked in game on the dev1 image with the new engine at 32 MB Fast: a Self effect on the player, Absorb Health by
  touch on an NPC, a Fireball bolt on a guard (his health fell from 285 to 269 over a second and he fought back),
  failed rolls keeping the magicka, a short-magicka refusal; frames of 14 to 47 ms.

### Weapons and combat

- **Weapons and shields of every type** are drawn in their stance on the assembled body (one-handed, two-handed close
  and wide, swings, unequip), with a debug weapon menu (`dbg weapon`, 536 rows) and gear menu (`dbg gear`, 739 rows)
  that read in about 75 ms and hold about 133 KB while open; two-handed weapons take the shield off
  ([COMBAT.md](../../COMBAT.md)). The attachment of a held weapon follows the original; blades are at least one unit
  thick in the build (`HELD-BLADE-EDGE-ON-61`).
- **First-person bow, crossbow and thrown stances** are in the first-person table (196 frames); ranged weapons can be
  equipped, thrown weapons as their stack. The shot itself waits for ranged combat.
- **First-person weapon sway** has two styles: the AmiWind groove (default) and a stiff style with still hands, in
  Options, Controls, Weapon sway, and as `dbg camera sway 1|2|bench`
  ([FP-WEAPON-SWAY-60](../../bugs/FP-WEAPON-SWAY-60.md)).
- **Creatures that resist normal weapons** (ghosts and others) take no harm from ordinary weapons; silver and magical
  weapons still work
  (`RESIST-NORMAL-WEAPONS-61`,
  `COMBAT-PLAYGROUND-CREATURE-HUMANOID-61`).
- **God mode** takes no damage, knockdown, fatigue loss or wear, as in the original
  ([GODMODE-COMBAT-DAMAGE-61](../../bugs/GODMODE-COMBAT-DAMAGE-61.md)).
- **Cliff racers** that attack the player land their strikes: on dry land beside a racer in the open world it attacked
  on sight and hit 11 of 36 swings at its 31 percent chance. Its drawn size is not yet seen in a still.

### Every being's stats

- Every person and creature, and the player, carries the full set of the stats its record gives it, kept in one place
  that the game's systems read through one set of calls ([ACTOR_STATS](../../ACTOR_STATS.md),
  [ACTOR-STATS-SCATTERED-61](../../bugs/ACTOR-STATS-SCATTERED-61.md)). The live records are made when an area loads:
  seven of seven in Arrille's Tradehouse in 1.1 ms, the worst staggered outdoor frame 1.0 ms, the first outdoor load
  step 124 ms. All 3,437 records of the game data decode as their records, and nine beings (auto-calculated and stored
  NPCs and a mudcrab) matched their records stat for stat in game.
- Two reference pages describe the game data: [ACTOR_RECORDS](../../ACTOR_RECORDS.md) (every value a being, race,
  class and birthsign can carry) and [GAME_FORMULAS](../../GAME_FORMULAS.md) (about 90 calculations in words).
- Known gaps: the far-actor fallback and the widened greeting value are still to come
  (`ACTOR-STATS-FAR-FALLBACK-61`,
  `ACTOR-HELLO-CLAMPED-61`).

### Inventory and carry weight

- **No fixed number of kinds of item.** As in the original, only carry weight limits what the player holds. The item
  table grows in blocks of 32 rows (24 bytes a row; about 42 bytes a kind with its name; 400 kinds take about 17 KB). A
  refused pick-up names the reason. Saves with more than 32 kinds set a feature bit that older versions refuse rather
  than lose items; saves from the 128-kind table still load
  ([COLLECT-CAPACITY-REJECTED-60](../../bugs/COLLECT-CAPACITY-REJECTED-60.md),
  [INVENTORY](../../INVENTORY.md)).
- **Carry weight and burden** are shown and movement stops over the limit
  ([ENCUMBRANCE-INCOMPLETE-61](../../bugs/ENCUMBRANCE-INCOMPLETE-61.md)); after loading a save of another character the
  carried weight is worked out at the load instead of reading 0
  ([LOADED-ITEMS-NOT-WEIGHED-61](../../bugs/LOADED-ITEMS-NOT-WEIGHED-61.md)).
- **Many kinds, fast.** The carried items are read in one pass at each place load and the inventory window no longer
  re-reads the item file on every category change. With 400 kinds carried, earlier workers' engines took 19 to 59 s to
  load a place and 5 to 13 s to open the window
  ([CARRIED-RECORDS-SEARCH-PER-KIND-61](../../bugs/CARRIED-RECORDS-SEARCH-PER-KIND-61.md),
  [INVENTORY-OPEN-COST-MANY-KINDS-61](../../bugs/INVENTORY-OPEN-COST-MANY-KINDS-61.md)); the repaired path is checked
  on this build.

### Carriable lights

- **Taking a lit candle or lamp takes its flame and its light with it,** outdoors and indoors, and it stays gone after
  a save and load. The builder writes each exterior cell's effect links (which flame and night lamp belong to which
  placement) into the cell's own area record at image assembly: in the dev1 data 25 cells, 524 rows, median 112 bytes,
  the largest 1,660 bytes. A build check covers the whole world and a test plants a miss on each path
  (`TAKEN-LIGHT-FLAME-STAYS-60`,
  `TAKEN-LIGHT-OUTDOORS-NOT-TAKEN-61`,
  `TAKEN-LIGHT-OUTDOOR-EFFECTS-UNLINKED-61`).

### Fixes in the builder and the game

- A blank sheet of paper no longer offers Read; a book with no words is taken
  (`BLANK-PAPER-READ-60`).
- Inside ancestral tombs the tomb ambience plays instead of the exploration music, and battle music still starts when
  an enemy attacks. This is a deliberate difference from the original, which keeps the exploration music on
  (`TOMB-MUSIC-OVER-AMBIENT-60`).
- The death music no longer starts when an area changes: the player's health was read before it was restored
  (`MUSIC-DEATH-TRACK-RANDOM-60`).
- After character creation the inventory opens and the character is dressed as in the original; a trader's refusal of
  service is tested as the original tests it (refuse below the value), which let a trader at disposition 40 open
  Barter again
  (`CHARGEN-INVENTORY-LOCKED-60`,
  `CHARGEN-NO-STARTING-CLOTHES-60`,
  `SERVICE-REFUSAL-UNCLOTHED-60`).
- Tombs and caves get the creatures of their levelled lists in converted rooms; in Samarys Ancestral Tomb a level 1
  character met an ancestor ghost that attacked on sight and a skeleton, with 3 of 5 levelled references empty as the
  list rules give
  (`TOMB-NO-CREATURES-60`).
- The ground along the Balmora canal bank no longer dips below the original terrain: five ground points on the bank
  edge are set to the original height, each splitting only the two triangles it lies between, which adds 10 triangles
  to that one frame (8,678 to 8,688) and touches no other cell. Before, 34 points of the strip lay more than 4 units
  under the original surface, the deepest 19 under; now none do. A build check refuses the frame if the strip drifts
  more than 4 units from the original surface. Checked in game at both spots
  (`BALMORA-GROUND-DENTS-51`).

## Not yet seen in game

These are checked on this image:

- First-person bow, crossbow and thrown stances, and stills of all seven first-person stances.
- The thickened blades, the sway cost per frame (`dbg camera sway bench`) and stills of both sway styles.
- A ghost taking no harm from iron and harm from silver; a godmode hit.
- Taking an Ebonheart carriable lantern outdoors (model, flame and night light gone, also after a save and load) and the
  candle in Arrille's Tradehouse indoors.
- The Census and Excise Office step after character creation (papers, then `I` opens the inventory), equipping a robe
  with the inventory open (the preview may be drawn before the new parts are loaded), and the number of Arrille's
  disposition against the original's formula.
- The pick-up check of the many-kinds item table (`dbg give weapons`, loot a body, collect mushrooms), and the time to
  load a place and open the window with hundreds of kinds.
- A blank sheet of paper, the tomb ambience with battle music on a ghost attack, and no death music on any area
  crossing.
- The Magic window after character creation, and resting (Until Healed after damage, enemies near, a wilderness
  interruption).
- Frame times on the Raspberry Pi 4B and in the emulator against dev1, on the same routes.

## Known in this build

- The baked light of a room stays when a light in it is taken; only the carriable light's flame and lamp light go
  (`TAKEN-LIGHT-BAKED-LIGHT-61`).
- Seyda Neen's carriable lanterns are missing from the open world, so none can be taken there
  ([SEYDA-LANTERNS-MISSING-31](../../bugs/SEYDA-LANTERNS-MISSING-31.md)).
- A loop sound on an object a script disabled keeps playing
  (`SCRIPT-LOOP-SOUND-DISABLED-OBJECT-61`).
- A new character now gets the powers and abilities of its race and the spells of its birth sign, but not yet the
  starting spells the original works out from the class and skills
  ([PLAYER-START-SPELLS-NOT-KNOWN-61](../../bugs/PLAYER-START-SPELLS-NOT-KNOWN-61.md)); the hands'
  casting gesture, Cast When Used and Constant Effect items, and reflection are not in.
- The pit axe lying outside in Seyda Neen is drawn but shows no item box
  (`PLACED-PIT-AXE-NO-FOCUS-61`); the iron shardaxe is refused when
  equipped (`EQUIP-SHARDAXE-REFUSED-61`); the Census Office map has no cell
  id, so resting there is offered in a cell where it should not be
  (`REST-CENSUS-NO-CELL-ID-61`).
- The known problems of [v0.0.60](RELEASE-v0.0.60.md) that remain: the first frame in Seyda Neen takes about a second,
  the Vivec town's resident bake costs about three and a half times its earlier CPU
  ([PERF-GUARD-RESIDENT-BUSY-HOST-57](../../bugs/PERF-GUARD-RESIDENT-BUSY-HOST-57.md)), the trip from Seyda Neen to
  Balmora sometimes stalls on the loading screen in the emulator
  ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)) and some rooms still load in after
  you arrive ([CHIM-ROOM-POPIN-51](../../bugs/CHIM-ROOM-POPIN-51.md)).
