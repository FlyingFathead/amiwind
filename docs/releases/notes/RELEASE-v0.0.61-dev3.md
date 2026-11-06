# AmiWind v0.0.61-dev3 (in development)

_Last updated with AmiWind v0.0.61-dev3 (2026-11-06)._

Development snapshot, 6 November 2026, in development. Running on CHIM Engine v0.2.2. Previous snapshot:
[v0.0.61-dev2](RELEASE-v0.0.61-dev2.md). Previous release: [v0.0.60](RELEASE-v0.0.60.md).

The third snapshot of v0.0.61. It carries the fixes from the in-game check of dev2 and the next pieces of the magic,
light, crime and dialogue work: items that cast, held lights drawn and lit as themselves, theft seen by a witness,
notices and keys in the dialogue window, a container strip that opens fast with hundreds of kinds carried, creatures
that keep their fighting frames, first-person arms in their own view, the armour rating, and the first slice of an
in-game recorder for testing. The coming release of this version is titled "Keep Your Lantern Lit". The game needs
32 MB of Fast RAM, and the emulator presets of this snapshot have it.

## New since v0.0.61-dev2

### Magic items and saves

- **Enchanted items cast.** Cast When Strikes weapons cast on a landed blow (a hit or a block; the charge is spent by
  the Enchant skill, also on a killing blow), Cast When Used items and scrolls cast when used with magic readied (no
  roll), and Constant Effect items act while worn: a ring of Fortify Agility 30 took Agility from 30 to 60 on and back
  to 30 off, and stayed through a quick save and load. The item table carries every enchantment (795 rows). Weapons and
  shields with a Cast When Strikes or Cast When Used enchantment can now be equipped; before, 191 strike weapons, 59
  use weapons and 20 use shields, the iron shardaxe among them, were refused (`WEAPON-STRIKE-ENCHANT-NOT-CAST-61`,
  `EQUIP-SHARDAXE-REFUSED-61`).
- **The class starting spells.** A new character gets the starting spells the original works out from its class and
  skills, besides the powers and abilities of its race and the spells of its birth sign: a Breton mage under the Mage
  sign has 10 spells, a warrior none. The list is 12 rows in the game data and about 6 KB only while a character is
  chosen ([PLAYER-START-SPELLS-NOT-KNOWN-61](../../bugs/PLAYER-START-SPELLS-NOT-KNOWN-61.md)).
- **Active effects survive a load.** In dev2 a save made with a spell effect active lost the effects, and the made
  spells, enchanted items, soul gems and the other blocks stored after them, when it was loaded: the block of effects
  was read at the wrong size. It is read at its real size now (`SAVE-EFFECTS-BLOCK-SIZE-61`).

### Lights

- **Held lights are drawn and lit as themselves.** A candle, a candlestick (three candles) and a lantern held in the
  hand show their own model and flames, in first person and on the third-person hand, and light by their own record:
  the candle reaches half as far as the torch, the candlesticks and lanterns as far as the torch, as in the original.
  The torch is unchanged ([HELD-LIGHT-ALWAYS-TORCH-61](../../bugs/HELD-LIGHT-ALWAYS-TORCH-61.md)).
- **Carriable lights outdoors in the towns keep their flame tied to them.** The flame links of 61 flame rows of 53
  carriable lights in the five town frame maps (Vivec 49, Seyda Neen 4, and two more town maps with 4 each) were
  looked up under the wrong map name, so a taken lantern left its flame floating. All 288 flame rows are found now,
  and the build check also refuses a flame link that names no frame map of the image
  ([TAKEN-LIGHT-OUTDOOR-EFFECTS-UNLINKED-61](../../bugs/TAKEN-LIGHT-OUTDOOR-EFFECTS-UNLINKED-61.md)).

### Crime

- **Witnessed theft.** Taking an owned item in view of its owner or another witness reports the crime: the game's own
  message "Your crime has been reported!", a bounty (0 to 100 for a brandy in Arrille's Tradehouse), the witnesses'
  Thief lines, and the attacks of those who see it. A theft out of every resident's sight has no consequence. The
  witnesses are looked for only at the moment of the take, never per frame: one walk over the 15 entities, seven
  residents tested with seven line-of-sight traces, 14 to 20 ms for the rules (an unseen take 14 ms); about 1 KB is kept
  (`STEAL-WITNESSED-NO-CRIME-60`, `NPC-VOICE-INTRUDER-THIEF-NO-EVENT-58`). Guards who pursue to arrest, pickpocketing, trespass, assault and murder are
  not in yet.

### Dialogue and loot windows

- **Item notices in a conversation.** An answer that gives or takes an item writes "... has been added to your
  inventory" or its removal line into the conversation, as the original does
  ([DIALOGUE-ITEM-NOTICE-MISSING-61](../../bugs/DIALOGUE-ITEM-NOTICE-MISSING-61.md)).
- **Notices and messages on top of the window,** and a plain black screen behind the dialogue window with no status
  bars (`DIALOGUE-MSGBOX-BEHIND-60`, `DIALOGUE-BACKDROP-HUD-60`).
- **A picked answer is shown as the player's line,** in the same heading style as a picked topic, and the disposition
  change of its result is shown at once (Fargoth's ring: 40 to 90, +50 as the original data gives)
  (`DIALOGUE-CHOICE-LINE-UNMARKED-60`, `DIALOGUE-RING-DISPOSITION-CHECK-60`).
- **Keys.** In the dialogue window Up and Down move the highlighted topic or answer, Enter picks it, and Tab switches
  to the conversation text, where Up and Down scroll it. Moving the mouse pointer with the arrows is not in
  (`DIALOGUE-ARROWS-MOVE-POINTER-60`).
- **The loot window** has room around its buttons, wraps item names in the console font, shows the whole key help line,
  and lists the selected item's type, weight, value and condition ("Axe  Weight 24  Value 60  Condition 1200")
  (`LOOT-WINDOW-LAYOUT-60`, `LOOT-WINDOW-ITEM-PROPERTIES-60`).

### Containers and bodies

- **The container strip opens fast with many kinds carried.** With 415 kinds in the inventory a body's strip took
  10.3 s to open; it opens in 82 ms now (65 ms again after Take All, takes 0 to 1 ms), because the strip names its rows
  in one pass over the item table instead of one file search per kind
  ([CONTAINER-STRIP-OPEN-MANY-KINDS-61](../../bugs/CONTAINER-STRIP-OPEN-MANY-KINDS-61.md)).

### Creatures and residents

- **Creatures keep their fighting frames.** A creature that started a fight while walking its route was handed its
  standing model, which has 16 frames, instead of the walking model with 38; the ancestor ghost in Samarys Ancestral
  Tomb filled the console with 2,827 "No such frame" lines. It now fights with its own run and attack poses and none
  of those lines appear. 39 of the 39 baked creature models with a walking model were exposed
  ([CREATURE-COMBAT-FRAMES-MISSING-61](../../bugs/CREATURE-COMBAT-FRAMES-MISSING-61.md)).
- **Seyda Neen residents no longer fall into the stuck-movement retry.** A step that fails from inside solid ground
  now settles once onto the clear spot; in a forced test 106 searches and 1,758 position tests fell to 9 and 336
  (minus 81 percent). The cause was a resident's standing box at the foot of a steep face; the face is unchanged
  ([AMBIENT-UNSTUCK-FLOOD-61](../../bugs/AMBIENT-UNSTUCK-FLOOD-61.md)).

### Inventory and the character picture

- **Worn clothes show at once in the inventory preview.** A changed outfit loads its parts over several frames; the
  picture waits for them (at most 5 s) and is drawn once, so a cuirass, a robe or trousers put on or taken off show in
  the window and on the third-person body (`INVENTORY-PREVIEW-STALE-61`).
- **The pit axe in Seyda Neen** shows its item box and can be taken, and **the Census and Excise Office** is read as a
  cell where resting is not allowed: the rest window there gives the game's line and offers Wait. The world-spawn
  reader stopped at the first value over 127 bytes, and the compiled rooms (the Census Office, the prison) carry a long
  light grid before their cell keys, so this applies to every compiled room with a light grid
  (`PLACED-PIT-AXE-NO-FOCUS-61`, `REST-CENSUS-NO-CELL-ID-61`).
- **The burden bar numbers** (carried and maximum weight) are legible and placed as in the original
  (`INVENTORY-BURDEN-TEXT-UNREADABLE-61`).
- **The armour rating** is shown as "Armor: N" under the character picture, worked out from the worn pieces, their
  condition and the skills as in the original (clothes 5, an ebony cuirass 10 for the tradehouse character)
  (`INVENTORY-NO-ARMOR-RATING-61`).

### First person and the third-person body

- **First-person arms in their own view.** The arms, the weapon and the held light are drawn with a 60 degree field of
  view of their own and turn with three quarters of the view's pitch, as in the original; with the fists raised and the
  view looking down the forearms show, and a worn shirt's or robe's sleeves cover them. The switch is `aw_fp_view`
  (default on, saved; `dbg camera fpview on|off`) (`FP-FOREARMS-BELOW-VIEW-61`).
- **Swimming keeps the worn clothes.** The assembled body now has swimming groups and stays on in the water, so the
  swimmer wears the player's own clothes instead of the default ones (`SWIM-BAKED-CLOTHES-60`).
- **Trees on slopes keep their trunks.** The wall depth push of the Seyda Neen wall fix was applied to the bottom of
  every tree card, so on a slope the ground covered the trunk and cut it flat above the ground. It is now kept only
  where a card's base meets a wall, building or rock: of 885 cards 124 keep it. No triangles are added
  (`BC-TREE-FLOATING-60`).

### In-game recorder, slice 1

- **Recording and replay.** `dbg recorder` arms; Ctrl+R saves the game, loads that save at once and records from the
  first frame in play, so the recording and its replay begin from the same fresh load; the version line at the top reads
  (RECORDING) and then (PLAYBACK) in a replay. Every frame keeps its length, movement, view and key events (15.0 bytes a
  frame, kept in memory and written once at the stop); a checkpoint every 5 seconds of game time compares the frame, the
  position, the health and a hash of the world's change list. A test recording of 3,797 frames (0:58 of game time) held
  13 of 13 checkpoints in its replay ([GAME_RECORDER](../../GAME_RECORDER.md),
  [GAME-RECORDER-MISSING-61](../../bugs/GAME-RECORDER-MISSING-61.md)).
- The engine's generated version header is rewritten only when it changes, which stops an engine build from failing on
  a header that is briefly shorter than expected
  ([BUILD-VERSION-HEADER-RACE-61](../../bugs/BUILD-VERSION-HEADER-RACE-61.md)).

## Not yet seen in game

These are checked on this image:

- The Ebonheart lantern taken outdoors with its flame gone after a save and load (the view after the load did not reach
  the spot in the dev2 check), and the candle in Arrille's Tradehouse taken indoors.
- A weapon that casts on strike used by an NPC against the player (the code path is the player's; 408 actors hold one).
- The shore wall pose in Seyda Neen after the tree card change, and a swimmer off the docks wearing a worn robe (the
  Seyda Neen test image has no sea).
- The glass lantern in first person, and a still in the middle of a swing with the new first-person view.
- Until Healed after damage and a wilderness rest interruption; the Magic window after the courtyard ring.
- The held lights' look against the original at the same poses, and the frame times of the new first-person view.
- Frame times on the Raspberry Pi 4B and in the emulator against dev2, on the same routes.

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
- Not in the recorder yet: the mouse pointer inside windows, segment marks, frame times per segment, replay on the
  Raspberry Pi 4B and the smoke suite made from recordings.
- The known problems of [v0.0.60](RELEASE-v0.0.60.md) that remain: the first frame in Seyda Neen takes about a second,
  the Vivec town's resident bake costs about three and a half times its earlier CPU
  ([PERF-GUARD-RESIDENT-BUSY-HOST-57](../../bugs/PERF-GUARD-RESIDENT-BUSY-HOST-57.md)), the trip from Seyda Neen to
  Balmora sometimes stalls on the loading screen in the emulator
  ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)) and some rooms still load in after
  you arrive ([CHIM-ROOM-POPIN-51](../../bugs/CHIM-ROOM-POPIN-51.md)).
