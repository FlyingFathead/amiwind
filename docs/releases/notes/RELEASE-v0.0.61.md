# AmiWind v0.0.61: Keep Your Lantern Lit

_Last updated with AmiWind v0.0.61 (6 November 2026)._

Release, 6 November 2026. Running on CHIM Engine v0.2.2. Previous release: [v0.0.60](RELEASE-v0.0.60.md).

v0.0.61, "Keep Your Lantern Lit", is the combat, magic and light release. Player casting with a spell-effect system,
weapons and shields of every type in their stances, enchanted items that cast, one set of stats for every person and
creature, an inventory with no fixed number of kinds, carriable lights that take their flame with them and held
candles and lanterns that light as themselves, theft that witnesses report, a fuller dialogue and loot window, and the
first slice of an in-game recorder for testing. It is also faster: the standard benchmark runs about 37 % more frames a
second in the emulator than the first snapshot of this version, and the places that waited for the disk wait about a
third to a half as long. The game needs 32 MB of Fast RAM, and the emulator presets of this release have it.

This release is the third development snapshot of v0.0.61 ([dev3](RELEASE-v0.0.61-dev3.md)) with its final version
number and the release documents; it contains no other game code. The in-game check of that snapshot and the rest of the
v0.0.61 list move, openly, to v0.0.62. The notes below cover the whole of v0.0.61 since v0.0.60, by area. The notes of
the snapshots are [dev1](RELEASE-v0.0.61-dev1.md), [dev2](RELEASE-v0.0.61-dev2.md) and
[dev3](RELEASE-v0.0.61-dev3.md).

## Checked in game

Much of the magic, weapon, stats, inventory and light work was checked in game on the first snapshot's image with the
new engine at 32 MB Fast RAM: a Self effect on the player, Absorb Health by touch on a person, a Fireball bolt on a
guard (his health fell from 285 to 269 over a second and he fought back), failed rolls keeping the magicka, a refusal
when the magicka is short, nine beings matched against their records stat for stat, a taken lantern's flame staying
gone after a save and load, and the Balmora canal bank at both spots. The pieces added in dev3 are checked by tests,
by the build and by recorded test sessions; their in-game check is listed under "Not yet seen in game".

## New since v0.0.60

### Magic and casting

- **Casting.** `R` (or `dbg cast ready`) readies magic and the attack button casts the selected spell; the Magic
  window (`O`) selects it. The magicka is paid at the start and the cast is refused when it is short; the chance to
  succeed follows the original's rules; a failed roll keeps the magicka. Self, Touch (at blow reach) and Target spells
  (a bolt that lands on the actor aimed at, with areas) deliver their effects; a harmful spell starts the fight;
  powers work once a day; the school skill rises with use. In god mode a cast always succeeds and is free
  ([GODMODE-COMBAT-DAMAGE-61](../../bugs/GODMODE-COMBAT-DAMAGE-61.md)).
- **Spell effects.** Any of the 143 effects can be applied to any actor by reference (64 entries, 32 of them for the
  player), applied over time or once as the original does, with harmful ones told apart. Effects are kept in the save
  (a new block; older saves still load) and survive a load at their real size
  (`SAVE-EFFECTS-BLOCK-SIZE-61`). The effects of non-player actors run while they are loaded and their damage feeds the
  fight. Light lights the player; Resist and Weakness to Normal Weapons are read by the combat code; Burden and Feather
  feed the carry weight. Creatures ignore skill effects.
- **Enchanted items cast.** Cast When Strikes weapons cast on a landed blow (a hit or a block; the charge is spent by
  the Enchant skill, also on a killing blow), Cast When Used items and scrolls cast when used with magic readied (no
  roll), and Constant Effect items act while worn: a ring of Fortify Agility 30 took Agility from 30 to 60 on and back
  to 30 off, and stayed through a quick save and load. The item table carries every enchantment (795 rows). Weapons and
  shields with a Cast When Strikes or Cast When Used enchantment can be equipped; before, 191 strike weapons, 59 use
  weapons and 20 use shields, the iron shardaxe among them, were refused (`WEAPON-STRIKE-ENCHANT-NOT-CAST-61`,
  `EQUIP-SHARDAXE-REFUSED-61`).
- **The class starting spells.** A new character gets the starting spells the original works out from its class and
  skills, besides the powers and abilities of its race and the spells of its birth sign: a Breton mage under the Mage
  sign has 10 spells, a warrior none ([PLAYER-START-SPELLS-NOT-KNOWN-61](../../bugs/PLAYER-START-SPELLS-NOT-KNOWN-61.md)).

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
  weapons still work (`RESIST-NORMAL-WEAPONS-61`, `COMBAT-PLAYGROUND-CREATURE-HUMANOID-61`).
- **God mode** takes no damage, knockdown, fatigue loss or wear, as in the original
  ([GODMODE-COMBAT-DAMAGE-61](../../bugs/GODMODE-COMBAT-DAMAGE-61.md)).
- **Cliff racers** that attack the player land their strikes: on dry land beside a racer in the open world it attacked
  on sight and hit 11 of 36 swings at its 31 percent chance. Its drawn size is not yet seen in a still.
- **Creatures keep their fighting frames.** A creature that started a fight while walking its route was handed its
  standing model, which has 16 frames, instead of the walking model with 38; the ancestor ghost in Samarys Ancestral
  Tomb filled the console with 2,827 "No such frame" lines. It now fights with its own run and attack poses. 39 of the
  39 baked creature models with a walking model were exposed
  ([CREATURE-COMBAT-FRAMES-MISSING-61](../../bugs/CREATURE-COMBAT-FRAMES-MISSING-61.md)).

### Every being's stats

- Every person and creature, and the player, carries the full set of the stats its record gives it, kept in one place
  that the game's systems read through one set of calls ([ACTOR_STATS](../../ACTOR_STATS.md),
  [ACTOR-STATS-SCATTERED-61](../../bugs/ACTOR-STATS-SCATTERED-61.md)). The live records are made when an area loads:
  seven of seven in Arrille's Tradehouse in 1.1 ms, the worst staggered outdoor frame 1.0 ms, the first outdoor load
  step 124 ms. All 3,437 records of the game data decode as their records.
- Two reference pages describe the game data: [ACTOR_RECORDS](../../ACTOR_RECORDS.md) and
  [GAME_FORMULAS](../../GAME_FORMULAS.md) (about 90 calculations in words).

### Crime

- **Witnessed theft.** Taking an owned item in view of its owner or another witness reports the crime: the game's own
  message "Your crime has been reported!", a bounty (0 to 100 for a brandy in Arrille's Tradehouse), the witnesses'
  Thief lines, and the attacks of those who see it. A theft out of every resident's sight has no consequence. The
  witnesses are looked for only at the moment of the take, never per frame: 14 to 20 ms for the rules, about 1 KB kept
  (`STEAL-WITNESSED-NO-CRIME-60`, `NPC-VOICE-INTRUDER-THIEF-NO-EVENT-58`). Guards who pursue to arrest, pickpocketing,
  trespass, assault and murder are not in yet.

### Inventory and carry weight

- **No fixed number of kinds of item.** As in the original, only carry weight limits what the player holds. The item
  table grows in blocks of 32 rows (about 42 bytes a kind with its name; 400 kinds take about 17 KB). A refused pick-up
  names the reason. Saves with more than 32 kinds set a feature bit that older versions refuse rather than lose items;
  saves from the 128-kind table still load
  ([COLLECT-CAPACITY-REJECTED-60](../../bugs/COLLECT-CAPACITY-REJECTED-60.md), [INVENTORY](../../INVENTORY.md)).
- **Carry weight and burden** are shown and movement stops over the limit
  ([ENCUMBRANCE-INCOMPLETE-61](../../bugs/ENCUMBRANCE-INCOMPLETE-61.md)); after loading a save of another character the
  carried weight is worked out at the load ([LOADED-ITEMS-NOT-WEIGHED-61](../../bugs/LOADED-ITEMS-NOT-WEIGHED-61.md)).
- **The character picture and the window.** Worn clothes show at once in the inventory preview (the picture waits, at
  most 5 s, for the parts of a changed outfit and is drawn once); the armour rating is shown as "Armor: N" under the
  picture, worked out from the worn pieces, their condition and the skills (clothes 5, an ebony cuirass 10 for the
  tradehouse character); the burden bar numbers are legible and placed as in the original
  (`INVENTORY-PREVIEW-STALE-61`, `INVENTORY-NO-ARMOR-RATING-61`, `INVENTORY-BURDEN-TEXT-UNREADABLE-61`).
- **The pit axe in Seyda Neen** shows its item box and can be taken, and **the Census and Excise Office** is read as a
  cell where resting is not allowed. The world-spawn reader stopped at the first value over 127 bytes, so this applies
  to every compiled room with a light grid (`PLACED-PIT-AXE-NO-FOCUS-61`, `REST-CENSUS-NO-CELL-ID-61`).

### Lights

- **Taking a lit candle or lamp takes its flame and its light with it,** outdoors and indoors, and it stays gone after
  a save and load. The builder writes each exterior cell's effect links into the cell's own area record at image
  assembly (25 cells, 524 rows, median 112 bytes, the largest 1,660 bytes). A build check covers the whole world
  (`TAKEN-LIGHT-FLAME-STAYS-60`, `TAKEN-LIGHT-OUTDOORS-NOT-TAKEN-61`, `TAKEN-LIGHT-OUTDOOR-EFFECTS-UNLINKED-61`).
- **Carriable lights in the towns keep their flame tied to them.** The flame links of 61 flame rows of 53 carriable
  lights in the five town frame maps were looked up under the wrong map name, so a taken lantern left its flame
  floating. All 288 flame rows are found now, and the build check also refuses a flame link that names no frame map of
  the image.
- **Held lights are drawn and lit as themselves.** A candle, a candlestick (three candles) and a lantern held in the
  hand show their own model and flames, in first person and on the third-person hand, and light by their own record:
  the candle reaches half as far as the torch, the candlesticks and lanterns as far as the torch, as in the original
  ([HELD-LIGHT-ALWAYS-TORCH-61](../../bugs/HELD-LIGHT-ALWAYS-TORCH-61.md)).

### Dialogue and loot windows

- **Item notices in a conversation:** an answer that gives or takes an item writes "... has been added to your
  inventory" or its removal line into the conversation, as the original does
  ([DIALOGUE-ITEM-NOTICE-MISSING-61](../../bugs/DIALOGUE-ITEM-NOTICE-MISSING-61.md)).
- **Notices and messages on top of the window,** and a plain black screen behind the dialogue window with no status
  bars (`DIALOGUE-MSGBOX-BEHIND-60`, `DIALOGUE-BACKDROP-HUD-60`).
- **A picked answer is shown as the player's line,** and the disposition change of its result is shown at once
  (Fargoth's ring: 40 to 90) (`DIALOGUE-CHOICE-LINE-UNMARKED-60`, `DIALOGUE-RING-DISPOSITION-CHECK-60`).
- **Keys.** Up and Down move the highlighted topic or answer, Enter picks it, Tab switches to the conversation text,
  where Up and Down scroll it (`DIALOGUE-ARROWS-MOVE-POINTER-60`).
- **The loot window** has room around its buttons, wraps item names, shows the whole key help line and lists the
  selected item's type, weight, value and condition (`LOOT-WINDOW-LAYOUT-60`, `LOOT-WINDOW-ITEM-PROPERTIES-60`).

### First person and the third-person body

- **First-person arms in their own view.** The arms, the weapon and the held light are drawn with a 60 degree field of
  view of their own and turn with three quarters of the view's pitch, as in the original; a worn shirt's or robe's
  sleeves cover the forearms. The switch is `aw_fp_view` (default on, saved; `dbg camera fpview on|off`)
  (`FP-FOREARMS-BELOW-VIEW-61`).
- **Swimming keeps the worn clothes** (`SWIM-BAKED-CLOTHES-60`).
- **Trees on slopes keep their trunks.** Of 885 tree cards 124 keep the wall depth push now; no triangles are added
  (`BC-TREE-FLOATING-60`).
- **The Balmora canal bank** no longer dips below the original terrain: five ground points set to the original height
  add 10 triangles to that one frame (8,678 to 8,688) and touch no other cell (`BALMORA-GROUND-DENTS-51`).

### Other fixes in the game and the builder

- A blank sheet of paper no longer offers Read (`BLANK-PAPER-READ-60`).
- Inside ancestral tombs the tomb ambience plays instead of the exploration music; battle music still starts when an
  enemy attacks. This is a deliberate difference from the original (`TOMB-MUSIC-OVER-AMBIENT-60`).
- The death music no longer starts when an area changes (`MUSIC-DEATH-TRACK-RANDOM-60`).
- After character creation the inventory opens and the character is dressed as in the original; a trader's refusal of
  service is tested as the original tests it (`CHARGEN-INVENTORY-LOCKED-60`, `CHARGEN-NO-STARTING-CLOTHES-60`,
  `SERVICE-REFUSAL-UNCLOTHED-60`).
- Tombs and caves get the creatures of their levelled lists in converted rooms (`TOMB-NO-CREATURES-60`).
- The engine's generated version header is rewritten only when it changes, which stops an engine build from failing on
  a header that is briefly shorter than expected
  ([BUILD-VERSION-HEADER-RACE-61](../../bugs/BUILD-VERSION-HEADER-RACE-61.md)).

### In-game recorder, slice 1

- **Recording and replay.** `dbg recorder` arms; Ctrl+R saves the game, loads that save at once and records from the
  first frame in play, so the recording and its replay begin from the same fresh load; the version line reads
  (RECORDING) and then (PLAYBACK) in a replay. Every frame keeps its length, movement, view and key events (15.0 bytes
  a frame, kept in memory and written once at the stop); a checkpoint every 5 seconds of game time compares the frame,
  the position, the health and a hash of the world's change list. A test recording of 3,797 frames (0:58 of game time)
  held 13 of 13 checkpoints in its replay ([GAME_RECORDER](../../GAME_RECORDER.md),
  [GAME-RECORDER-MISSING-61](../../bugs/GAME-RECORDER-MISSING-61.md)).

## How much faster

Every number below comes from a saved measurement, with its setup, in [docs/performance](../../performance/). The
standard benchmark is `aw bench halloween`; the emulator runs are FS-UAE with a 68040, FPU, JIT and 32 MB Fast RAM.

**The clearest results are the Raspberry Pi 4B's.** The project's Pi 4B boot stick (Amiberry, 2.0 GHz, 68040 with
FPU, JIT, 128 MB Fast RAM) runs nothing but the benchmark, the same 600 frames on the same machine for every version,
so its line is the one to trust. It is also the machine closest to a PiStorm (see
[REAL_HARDWARE.md](../../REAL_HARDWARE.md)). The benchmark is a deliberately heavy scene, well below the frame rate of
ordinary play (see [HALLOWEEN.md](../../HALLOWEEN.md)): Seyda Neen, the heaviest place so far, with about ten
animated characters on screen and Dagoth Ur. The v0.0.61 game runs it at **5.4 fps** on the Pi 4B (minimum 1.0, 1 %
low 2.0, 600 frames in 110.3 s), with the setup in [FRAME-WAITS](../../performance/FRAME-WAITS.md). Earlier versions are
not compared here: their Pi runs of the same evening were taken with the main menu over the scene and will be taken
again, and a benchmark result that keeps drawing time and disk time apart comes in v0.0.62.

**The benchmark in FS-UAE.** Over the three snapshots of this version the mean frame rate in FS-UAE went from 28.9 fps
(dev1) to 32.2 (dev2) to 39.6 (dev3), and the slowest 1 % of frames from 1.9 to 2.1 fps in dev1 to 4.6 fps in dev3.
These runs were taken on different days under conditions that were not kept the same, so they are not a clean
comparison: part of the difference may not come from the game. The
Pi 4B line above does not show the same rise. The dev1 and dev2 lines are in
[FRAME-WAITS](../../performance/FRAME-WAITS.md).

**Waiting for the disk, Seyda Neen (dev1 to dev2, same script, same day).** The arrival waits 31 % less for files
(9,181 to 6,317 ms in 60 s), standing waits 49 % less (1,143 to 585 ms in 10 s) and walking waits 32 % less (3,590 to
2,432 ms in 19 s). The residents' think costs 0.67 ms against 0.21 ms. The totals of the parts stay the same because
they are the length of the wait steps in the script; the frames and the disk time carry the difference.

**Many kinds of item.** With about 400 kinds carried, opening the inventory took 7 to 13 s and every category change
took as long again ([INVENTORY-OPEN-COST-MANY-KINDS-61](../../bugs/INVENTORY-OPEN-COST-MANY-KINDS-61.md)), and
loading a place took 19 to 59 s ([CARRIED-RECORDS-SEARCH-PER-KIND-61](../../bugs/CARRIED-RECORDS-SEARCH-PER-KIND-61.md)).
Both are much faster now: the carried items are read in one pass at each place load, and the window reads each page of
its list by row and changes category without reading the file. The register holds no measured time for the repaired
paths yet, so none is given here. A body's container strip with 415 kinds took 10.3 s and opens in 82 ms (65 ms again
after Take All), measured in the dev3 check
([CONTAINER-STRIP-OPEN-MANY-KINDS-61](../../bugs/CONTAINER-STRIP-OPEN-MANY-KINDS-61.md)).

**The stuck-movement retry.** A resident whose step fails from inside solid ground now settles once onto the clear
spot: in a forced test 106 searches and 1,758 position tests fell to 9 and 336 (minus 81 percent)
([AMBIENT-UNSTUCK-FLOOD-61](../../bugs/AMBIENT-UNSTUCK-FLOOD-61.md)).

**What did not get faster.** The first frame after arriving in Seyda Neen still takes about a second. The Vivec town's
resident bake in the builder still costs about three and a half times its earlier CPU per unit
([PERF-GUARD-RESIDENT-BUSY-HOST-57](../../bugs/PERF-GUARD-RESIDENT-BUSY-HOST-57.md)). The trip from Seyda Neen to
Balmora can still stall on the loading screen in the emulator, and some rooms still load in after you arrive. Held
lights, first-person arms in their own view and witnessed theft were added without a measured frame cost in the
benchmark scene; their frame times in play are checked on the next snapshot.

## Not yet seen in game

These are checked after the release, on the v0.0.62 builds:

- The Ebonheart lantern taken outdoors with its flame gone after a save and load, and the candle in Arrille's
  Tradehouse taken indoors.
- A weapon that casts on strike used by a non-player character against the player (408 actors hold one).
- The shore wall pose in Seyda Neen after the tree card change, and a swimmer off the docks wearing a worn robe.
- The glass lantern in first person, and a still in the middle of a swing with the first-person view.
- Until Healed after damage and a wilderness rest interruption; the Magic window after the courtyard ring.
- The held lights' look against the original at the same poses.
- The first-person bow, crossbow and thrown stances, stills of both sway styles and the thickened blades.
- A ghost taking no harm from iron and harm from silver, and a god mode hit.

The in-game check of the first-person bow, crossbow and thrown stances, the sway styles, the thickened blades, the
ghost against iron and silver and the god mode hit moves to v0.0.62.

## Known in this build

- A light that is dropped or put down again gets no flame and gives no light where it lies
  ([DROPPED-LIGHT-NO-EFFECTS-61](../../bugs/DROPPED-LIGHT-NO-EFFECTS-61.md)).
- A Shield effect on the player does not soften the blows that land on it, although the inventory window adds it to the
  armour rating (`COMBAT-SHIELD-EFFECT-NO-ARMOR-61`).
- When a Fortify Attribute effect on the player ends, the sheet keeps it as a raised modifier plus a drop counted as
  damage (`PLAYER-FORTIFY-END-AS-DAMAGE-61`).
- A theft seen by several witnesses that start fights in the same frame holds that frame for about 0.6 s, because four
  fight starts each read their sheet from disk
  ([COMBAT-START-SHEET-READS-61](../../bugs/COMBAT-START-SHEET-READS-61.md)).
- The worn Constant Effect items of non-player characters are not applied, and an NPC weapon's charge is kept for the
  session only. Tribunal and Bloodmoon items are not in the item table.
- Held lights: a lantern hangs below the hand, so in first person only its handle shows; the light's colour is one shade
  off the original; burn time is not counted; the light is not in the inventory picture.
- The baked light of a room stays when a light in it is taken
  (`TAKEN-LIGHT-BAKED-LIGHT-61`); Seyda Neen's carriable lanterns are missing from the open world
  ([SEYDA-LANTERNS-MISSING-31](../../bugs/SEYDA-LANTERNS-MISSING-31.md)).
- Not in the casting yet: the hands' casting gesture, reflection, the far-actor stats fallback and the widened greeting
  value (`ACTOR-STATS-FAR-FALLBACK-61`, `ACTOR-HELLO-CLAMPED-61`). A loop sound on an object a script disabled keeps
  playing (`SCRIPT-LOOP-SOUND-DISABLED-OBJECT-61`).
- Not in the recorder yet: the mouse pointer inside windows, segment marks, frame times per segment, replay on the
  Raspberry Pi 4B and the smoke suite made from recordings.
- The known problems of [v0.0.60](RELEASE-v0.0.60.md) that remain: the first frame in Seyda Neen takes about a second,
  the Vivec town's resident bake costs about three and a half times its earlier CPU, the trip from Seyda Neen to
  Balmora sometimes stalls on the loading screen in the emulator
  ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)) and some rooms still load in after
  you arrive ([CHIM-ROOM-POPIN-51](../../bugs/CHIM-ROOM-POPIN-51.md)).

## Moved to v0.0.62

The in-game check of the third snapshot and the fixes it brings, the full crime system (guards who arrest,
pickpocketing, trespass, assault, murder), alchemy, enchanting at an altar and spellmaking, per-area data tables for
containers, doors, items, activators and creatures, small-chunk game data per area, a build check on the size of every
lookup table, items lying outdoors that can be picked up, dropped lights with their flame, and the worn Constant Effect
items of non-player characters. The list is in the [roadmap](../../ROADMAP.md).
