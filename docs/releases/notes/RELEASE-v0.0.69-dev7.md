# AmiWind v0.0.69-dev7 (in development)

_Last updated with AmiWind v0.0.69-dev7 (27 November 2026)._

Development snapshot, 27 November 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.68: Solstheim Is Here](RELEASE-v0.0.68.md). Previous snapshot: [v0.0.69-dev6](RELEASE-v0.0.69-dev6.md).

The seventh snapshot of v0.0.69, whose title is "Fix The World After You Put It Together". It takes the world's items and
the way people and creatures fight a good step further. Plants, mushrooms and egg sacks are picked with one press again,
with the original's container window as an option; every armed person and 47 of the 58 armed creature records hold their own
weapon and shield; swings and shots last as long as the weapon's own animation and land on the shown blow; items without a
name can be taken, plants can be aimed at, and the census office's table models are drawn whole; and the open sea off
Solstheim has no invisible wall. Its emulator presets, `AmiWind-v0.0.69-dev7-FS-UAE.fs-uae` and
`AmiWind-v0.0.69-dev7-WinUAE.uae`, both start with 32 MB of Fast RAM, which the game needs. Every change below is covered
by tests and the gate of its commit; the ones marked as not yet seen in play are listed in the checklist.

## New since v0.0.69-dev6

### Items and plants

- **Plants, mushrooms, egg sacks, kollops, spore pods and ore rocks are picked with one press.** The pick sound plays and no
  window opens, as in the earlier builds. The setting **Plant and mushroom picking** in the options has two values:
  **AmiWind** (the default) and **Original**, which opens the original's container window for every plant. Stashes keep their
  window under both values; Fargoth's hollow treestump is one of them
  (PLANT-PICK-DIRECT-DEFAULT-69). Two parts of the plant pick are still to come, the
  outdoor plants shown as picked and the small mushrooms' window under Original (PLANT-PICK-COMPLETION-69, see Known).
- **Items without a name can be taken, as in OpenMW.** An item whose record has no name is aimed at and taken, and a carriable
  light gets its use row whatever its name, so the burned-out torches of the Temple Sewers can be picked up
  ([ITEM-NAMELESS-NOT-TAKEN-69](../../bugs/ITEM-NAMELESS-NOT-TAKEN-69.md)).
- **Plants have their measured aim boxes,** so a plant can be aimed at anywhere on it and not only at its centre point; what
  stands inside a plant's box is aimed first, and a nearer plant to pick takes the use
  ([PLANT-BOX-AIM-69](../../bugs/PLANT-BOX-AIM-69.md)).
- **Items outdoors are drawn once.** A takeable item that the scenery also places is no longer drawn twice at the same spot
  ([OUTDOOR-ITEM-CHIM-COPY-STAYS-69](../../bugs/OUTDOOR-ITEM-CHIM-COPY-STAYS-69.md)). The world's items are counted, and the
  organic containers that open are built for every land (WORLD-OBJECT-PLACEMENT-59,
  [CONTAINER-COUNT-LOOSE-ROOM-PATH-68](../../bugs/CONTAINER-COUNT-LOOSE-ROOM-PATH-68.md)).
- **Fargoth's stash in the stump can be opened.** The hollow treestump in Seyda Neen is a container with its contents
  ([FARGOTH-STASH-STUMP-69](../../bugs/FARGOTH-STASH-STUMP-69.md)).
- **The census office's table items are drawn whole.** The office keeps the small faces of the models its table names, so the
  Iron Dagger on the table shows its guard at its whole width and is easy to aim at
  ([ITEM-AIM-UNDER-OTHERS-69](../../bugs/ITEM-AIM-UNDER-OTHERS-69.md)).
- **The opening's item sweep reads the right room.** The sweep that makes the opening rooms' items real items reads the placed
  list under the room's own number, before the maps are stamped
  ([OPENING-SWEEP-BEFORE-STAMP-69](../../bugs/OPENING-SWEEP-BEFORE-STAMP-69.md)).

### Weapons and fighting

- **Each actor holds its own weapon and shield.** What an actor holds comes from its own record through its row in the actor
  table, and ranged fighters with a tag hold their bow, crossbow or thrown weapon
  ([ACTOR-HELD-ITEMS-NOT-LIVE-INVENTORY-69](../../bugs/ACTOR-HELD-ITEMS-NOT-LIVE-INVENTORY-69.md),
  [ACTOR-RANGED-WEAPON-NOT-HELD-69](../../bugs/ACTOR-RANGED-WEAPON-NOT-HELD-69.md)).
- **47 of the 58 armed creature records hold their weapon and shield.** The skeletons, dremora, golden saints, liches,
  goblins and Almalexia get a tag of bones and scale of their own. The rieklings and the lich king wait for the next
  rebuild of the world
  ([CREATURE-COMBAT-WEAPON-54](../../bugs/CREATURE-COMBAT-WEAPON-54.md),
  [CREATURE-OWN-TABLE-NO-ITEM-BONES-69](../../bugs/CREATURE-OWN-TABLE-NO-ITEM-BONES-69.md)).
- **Every armed person draws a weapon.** When the item tag tables are full, the next armed model takes the entry of a model no
  live actor uses, so armed people met late in a session still show their weapon, shield and torch
  ([HELD-ITEM-TABLE-FULL-69](../../bugs/HELD-ITEM-TABLE-FULL-69.md)).
- **Each swing and shot lasts as long as its weapon's own animation** and lands on the shown hit or release moment; the hit
  recovery lasts the shown hit animation. The AmiWind dodge and block on a miss stay as the default
  ([ACTOR-ATTACK-ONE-CLOCK-69](../../bugs/ACTOR-ATTACK-ONE-CLOCK-69.md)).
- **The weapon appears at the draw and the legs keep walking.** The weapon and shield appear at the draw's attach moment and go
  at the put-away's detach moment, no swing starts under the draw, and a draw while moving plays on the torso so the legs
  keep walking ([ACTOR-WEAPON-SHOWN-BEFORE-DRAW-69](../../bugs/ACTOR-WEAPON-SHOWN-BEFORE-DRAW-69.md),
  [ACTOR-DRAW-STOPS-LEGS-69](../../bugs/ACTOR-DRAW-STOPS-LEGS-69.md)).

### The opening and the world

- **The prison ship's dock-side guards and props go by the scripts' own Disable,** and the census office captain's dialogue
  values are kept between his lines
  ([CAPTAIN-SCRIPT-LOCALS-NOT-KEPT-69](../../bugs/CAPTAIN-SCRIPT-LOCALS-NOT-KEPT-69.md)). The rest of this work waits for the
  next rebuild of the world.
- **No invisible wall in the open sea off Solstheim.** A creature collides only up to its drawn height, so a horker resting
  under the water no longer stops a player walking on the water, and a step never lands on a body
  ([SOL-SEA-INVISIBLE-BLOCKER-68](../../bugs/SOL-SEA-INVISIBLE-BLOCKER-68.md),
  [ACTOR-CLIP-ABOVE-DRAWN-BODY-69](../../bugs/ACTOR-CLIP-ABOVE-DRAWN-BODY-69.md)). A gate test now checks the world's seams and
  store edges; the result shows that Vivec is left on every side as in the original
  ([VIVEC-CITY-FRAME-EDGE-WALLS-69](../../bugs/VIVEC-CITY-FRAME-EDGE-WALLS-69.md), not a fault).
- **The actor checks judge every placed actor** on the model it stands in, and a census of every placed actor runs in the
  image's actor check
  ([ACTOR-CHECKS-MISS-PLACED-MODELS-69](../../bugs/ACTOR-CHECKS-MISS-PLACED-MODELS-69.md)).
- **`dbg tp lordvivec`** takes the player to Lord Vivec in his palace
  (DBG-TP-LORDVIVEC-69).

### Scripts

- **The script feature page is measured again.** Every script function shows in-play and checked fields, a function is an
  AmiWind adaptation only when every step matches the original, 133 scripts the original does not use are confirmed, and the
  Toolkit shows script counts per land (MWSCRIPT-EFFECT-PARITY-69,
  [MWSCRIPT-TRACKER-ADDON-NO-FUNCTION-NOT-IN-IMAGE-69](../../bugs/MWSCRIPT-TRACKER-ADDON-NO-FUNCTION-NOT-IN-IMAGE-69.md)).
- **The werewolf's kill count starts again at zero** when the player changes into the werewolf
  ([WEREWOLF-KILLS-NOT-RESET-69](../../bugs/WEREWOLF-KILLS-NOT-RESET-69.md)).

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

The [checklist of v0.0.69-dev6](RELEASE-v0.0.69-dev6.md#in-game-checklist-for-this-snapshot) stands. In addition, none
of the following has been seen in play yet:

- **Picking plants.** Pick a comberry, a marshmerrow plant, a mushroom and an egg sack: one press takes the ingredient, the
  pick sound plays and no window opens. In the options set **Plant and mushroom picking** to **Original**: the plants
  open the container window. Open Fargoth's stump in Seyda Neen: its window opens under both values.
- **Nameless items.** In the Temple Sewers aim at a burned-out torch: it can be taken. Aim at a plant from its
  side, not only at its middle: it is aimed at.
- **Items outdoors.** Walk past items lying outdoors: each is drawn once, with no doubled look.
- **The census table.** In the Census and Excise Office aim at the Iron Dagger on the table: it shows with its guard, and
  its name shows.
- **Weapons.** Fight armed people in several towns and a skeleton, a dremora and a golden saint: each holds its own weapon
  and shield. Play a long session through many towns: armed people met late still draw their weapon.
- **Swings and draws.** Watch a fighter draw its weapon while walking: the weapon appears at the draw and the legs keep
  walking. Watch swings and shots: each lasts as long as the weapon's own animation and the blow lands when it is shown.
- **The sea off Solstheim.** Walk on the water with Water Walking west from Khuul: there is no wall in the open sea before
  Solstheim's coast.
- **The opening.** On the prison ship and the Seyda Neen dock the guards and props are where the scripts put them, and the
  census office captain answers as in the original.
- **The werewolf.** Change into the werewolf: the kill count starts at zero.

## Known in this build

- **NPC weapon use does not follow the original yet** in its stance, attack types, reach, blocking and bows; the grip, the
  held weapon and the swing's length are fixed, the rest is planned as one item (NPC-WEAPON-USE-PARITY-69).
- **The combat playground's bow, crossbow and thrown fighters have no ammunition** at their first shot, so they fall back to
  hand to hand ([ARENA-RANGED-NO-AMMO-69](../../bugs/ARENA-RANGED-NO-AMMO-69.md)).
- **The plant pick is not complete:** a plant outdoors is not shown picked, it stays drawn and is not aimed at again until it
  refills, and the small mushrooms and bracket fungi keep their one-press pick under Original too (PLANT-PICK-COMPLETION-69).
  Both need a rebuild of the world.
- **The rieklings and the lich king do not hold their weapon yet**
  ([CREATURE-OWN-TABLE-NO-ITEM-BONES-69](../../bugs/CREATURE-OWN-TABLE-NO-ITEM-BONES-69.md)), and a creature's carried weapon
  is not drawn in combat for those records ([CREATURE-COMBAT-WEAPON-54](../../bugs/CREATURE-COMBAT-WEAPON-54.md)). The opening's
  people still differ from the rest of the world in some of the paths they use (OPENING-ONE-PATH-65).
- **A bow is held in the right hand** where the original attaches it to the left hand's weapon bone
  ([NPC-BOW-RIGHT-HAND-69](../../bugs/NPC-BOW-RIGHT-HAND-69.md)).
- **A fast walker plays the run animation:** the walk or run animation is chosen by the speed, not by whether the
  character runs ([PLAYER-WALK-PLAYS-RUN-GROUP-69](../../bugs/PLAYER-WALK-PLAYS-RUN-GROUP-69.md)).
- **The open entries of v0.0.68's Known list stand:**
  [Water Walking is applied deep under the water](../../bugs/WATER-WALKING-DEEP-CAST-NOT-REFUSED-68.md),
  [the walk in storms is not slowed](../../bugs/STORM-WALK-NOT-SLOWED-68.md),
  [the werewolf's remaining fight rules](../../bugs/WEREWOLF-FIGHT-RULES-LEFT-68.md),
  [the skip flag of played videos](../../bugs/MWSCRIPT-PLAYBINK-SKIP-FLAG-68.md),
  [the Companion Share entry](../../bugs/DIALOGUE-COMPANION-SHARE-MISSING-68.md),
  [conversation with creatures](../../bugs/DIALOGUE-CREATURE-SPEAKERS-66.md),
  [the ice wall of Penumbra](../../bugs/PENUMBRA-ICE-WALL-NO-PASSAGE-68.md),
  [water ripples under actors](../../bugs/WATER-RIPPLES-UNDER-ACTORS-MISSING-68.md),
  [each weather's cloud picture](../../bugs/WEATHER-CLOUD-TEXTURES-68.md),
  [the journal's topic letter index](../../bugs/JOURNAL-TOPIC-LETTER-INDEX-68.md),
  [a box's destination map name](../../bugs/LF5-BOX-DESTINATION-MAP-NAME-68.md),
  [the districts' frame rate](../../bugs/DISTRICT-FRAME-RATE-LOW-67.md) and four builder items
  ([the Tribunal stage's cores](../../bugs/TRIBUNAL-STAGE-UNDERUSED-68.md),
  [the memory plan](../../bugs/BUILD-MEMPLAN-CHIM-5-OF-22-68.md),
  [cache key lookups](../../bugs/CACHE-KEY-LOOKUP-NO-USE-68.md),
  [the janitor](../../bugs/JANITOR-KEEPS-RUNS-OF-FINISHED-REQUESTS-68.md)). They are taken in that order, the game rules
  first.
- **The build monitor's first minutes:** [TOOLKIT-MONITOR-BLIND-PHASES-36](../../bugs/TOOLKIT-MONITOR-BLIND-PHASES-36.md).
- From [v0.0.69-dev6](RELEASE-v0.0.69-dev6.md#known-in-this-build) and the snapshots before it: their Known lists stand. The
  next snapshots take these open items first, the small ones first. Every other open entry is in the
  [bug tracker](../../BUGS.md).
