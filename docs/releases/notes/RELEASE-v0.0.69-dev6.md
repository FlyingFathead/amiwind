# AmiWind v0.0.69-dev6 (in development)

_Last updated with AmiWind v0.0.69-dev6 (26 November 2026)._

Development snapshot, 26 November 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.68: Solstheim Is Here](RELEASE-v0.0.68.md). Previous snapshot: [v0.0.69-dev5](RELEASE-v0.0.69-dev5.md).

The sixth snapshot of v0.0.69, whose title is "Fix The World After You Put It Together". It answers the faults found in the latest play report: the
walking residents of Seyda Neen no longer snap back, armed characters hold their weapons in their hands, items can be
dropped in every room, the census office's platter can be taken, voiced characters move their mouths, the sneak key
toggles again, and the third-person body walks at the player's pace. Residents also walk their routes where the ground
has not loaded yet. Its emulator presets, `AmiWind-v0.0.69-dev6-FS-UAE.fs-uae` and `AmiWind-v0.0.69-dev6-WinUAE.uae`, both
start with 32 MB of Fast RAM, which the game needs. Every change below is covered by tests and the gate of its commit;
the ones marked as not yet seen in play are listed in the checklist.

## New since v0.0.69-dev5

### Fixed

- **Walking residents no longer stride ahead and snap back.** The female walk and the moving groups of every creature
  whose root bone is not named Bip01 are held in place in the shared animation table, so a walker is drawn at its
  position through the whole step cycle, as the original draws it; the part of the animation that carries the root is
  picked by its name, Bip01 first and the root bone otherwise
  ([NPC-WALK-RUBBERBAND-69](../../bugs/NPC-WALK-RUBBERBAND-69.md)). The fault was seen on the walking residents of Seyda
  Neen.
- **Armed people hold their weapons in their hands.** A held item now follows the frame its actor is sent with, so a battle
  axe or a knife stays in the hand through every attack, for every weapon type
  ([NPC-WEAPON-GRIP-WRONG-69](../../bugs/NPC-WEAPON-GRIP-WRONG-69.md)). The carried lights' posed frames are kept beside
  the carrier list in the same way.
- **The two Seyda Neen guards of the opening hold their spears.** The opening's people whose layout names a model of the
  shared people library had that model's weapon data refused at every load, so the guard on the boat and the guard on
  the dock fought empty-handed; the weapon data is now read with its own frame count, as for everyone else
  ([NPC-WEAPON-MESH-33](../../bugs/NPC-WEAPON-MESH-33.md)).
- **Items can be dropped in every room**, also during the opening. A drop ahead of the player that would pass through an
  invisible wall lands at the player's feet instead of being refused
  ([DROP-REFUSED-CENSUS-ROOM-67](../../bugs/DROP-REFUSED-CENSUS-ROOM-67.md)).
- **The census office's Limeware Platter (`misc_lw_platter`) can be taken.** The aim reaches an item that stands inside a
  shelf's collision, and the image step sweeps the opening rooms' items so the plate is an item and not part of the room
  ([CENSUS-SHELF-PLATE-BAKED-67](../../bugs/CENSUS-SHELF-PLATE-BAKED-67.md)).
- **Voiced characters move their mouths again.** Every voice line moves the speaker's mouth from its own loudness, also a
  line that has no lip file, so Socucius Ergalla's mouth moves in the Census and Excise Office
  ([NPC-TALK-MOUTH-STILL-69](../../bugs/NPC-TALK-MOUTH-STILL-69.md)). And every voiced character whose face is drawn
  now moves its mouth too, not only the opening's own actors: a new build stage bakes the original heads' talk shapes, and
  the engine opens the mouth by the loudness of each line, in conversation and in the world alike. Characters whose
  helmet replaces the head show no mouth, as in the original
  ([NPC-TALK-POSES-ONLY-OPENING-69](../../bugs/NPC-TALK-POSES-ONLY-OPENING-69.md)).
- **The journal's first-time hint leaves no empty box.** The hint shown the first time the journal is updated ended with
  an empty box under the dialogue window for its last second; blank rows at the edge of a page are now the gap to the
  next page and never a page of their own
  ([UI-JOURNAL-HINT-EMPTY-BOX-67](../../bugs/UI-JOURNAL-HINT-EMPTY-BOX-67.md)).
- **The sneak key toggles again.** One press keeps the player sneaking until the next press; Hold is an option. The
  crouched walk plays at the original's rate instead of gliding
  ([PLAYER-SNEAK-NOT-HELD-69](../../bugs/PLAYER-SNEAK-NOT-HELD-69.md)).
- **The third-person body keeps pace with the ground.** Its walk, run and sneak animations read the player's own speed
  (PLAYER-GAIT-RATE-VELOCITY-STEPS-69).
- **Residents walk their routes where the collision does not hold the ground.** A resident whose ground is not loaded
  walks its route and settles when the ground arrives, and an actor's step against a face that is too steep slides along
  it as the original's does ([AMBIENT-WALK-STUCK-COLLISION-54](../../bugs/AMBIENT-WALK-STUCK-COLLISION-54.md),
  [NPC-WANDER-NOT-EXECUTED-35](../../bugs/NPC-WANDER-NOT-EXECUTED-35.md), ACTOR-STEP-STEEP-CONTACT-REFUSED-69).

### The bug tracker

- Every register write now takes one lock and saves only if the file is unchanged since it was read, so two writers filing
  at once never lose each other's entries; the check refuses a report page that has no entry
  ([REGISTER-CONCURRENT-WRITE-LOST-67](../../bugs/REGISTER-CONCURRENT-WRITE-LOST-67.md)).
- Entries can be linked as probable variants of the same fault or as possibly related, also within one family, and the
  link shows on both pages (TRACK-POSSIBLY-RELATED-LINKS-69).

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

The [checklist of v0.0.69-dev5](RELEASE-v0.0.69-dev5.md#in-game-checklist-for-this-snapshot) stands. In addition, none
of the following has been seen in play yet:

- **Walking residents.** Watch the walking residents of Seyda Neen, among them Indrele Rathryon and Eldafire: they move
  steadily, with no stride ahead and jump back.
- **Weapons in hand.** Start a fight with an armed person, for example in the South Wall Cornerclub in Balmora: the weapon
  stays in the hand through every attack. A bow is still held in the right hand (see Known).
- **Drops.** Drop an item in a tomb, a house and in the first room of the Census and Excise Office, then leave and come
  back: it lies where it was dropped. Aim at a wall and drop: the item lands at the player's feet.
- **The platter.** In the Census and Excise Office aim at the Limeware Platter on the shelf: its name shows and it can be
  taken.
- **Mouths.** Talk to Socucius Ergalla and to other voiced characters: the mouth moves with each line.
- **Sneak.** Press the sneak key once: the player stays crouched until the next press, and the crouched walk looks like
  walking. In third person the walk, run and sneak animations keep pace with the ground.
- **Routes.** Watch residents walk their routes in the first towns, also right after arriving, and a step against a steep
  slope: the actor slides along it and does not stop.

## Known in this build

- **NPC weapon use does not follow the original yet** in its stance, attack types, speed, reach, blocking, bows and thrown
  weapons; the grip is fixed, the rest is planned as one item (NPC-WEAPON-USE-PARITY-69).
- **A bow is held in the right hand** where the original attaches it to the left hand's weapon bone
  ([NPC-BOW-RIGHT-HAND-69](../../bugs/NPC-BOW-RIGHT-HAND-69.md)).
- **A creature's carried weapon is not drawn in combat**
  ([CREATURE-COMBAT-WEAPON-54](../../bugs/CREATURE-COMBAT-WEAPON-54.md)), and the opening's people still differ from the
  rest of the world in some of the paths they use (OPENING-ONE-PATH-65).
- **A fast walker plays the run animation:** the walk or run animation is chosen by the speed, not by whether the
  character runs ([PLAYER-WALK-PLAYS-RUN-GROUP-69](../../bugs/PLAYER-WALK-PLAYS-RUN-GROUP-69.md)).
- **Sellus Gravius stands at a different spot** than before in the second Census and Excise Office building
  ([CENSUS-CAPTAIN-OUT-OF-PLACE-69](../../bugs/CENSUS-CAPTAIN-OUT-OF-PLACE-69.md)).
- **The build monitor's first minutes:** [TOOLKIT-MONITOR-BLIND-PHASES-36](../../bugs/TOOLKIT-MONITOR-BLIND-PHASES-36.md).
- **Water Walking is applied deep under the water too,** where the original refuses the spell
  ([WATER-WALKING-DEEP-CAST-NOT-REFUSED-68](../../bugs/WATER-WALKING-DEEP-CAST-NOT-REFUSED-68.md)).
- From [v0.0.69-dev5](RELEASE-v0.0.69-dev5.md#known-in-this-build) and the snapshots before it: their Known lists
  stand, among them the object in Solstheim's eastern waters
  ([SOL-SEA-INVISIBLE-BLOCKER-68](../../bugs/SOL-SEA-INVISIBLE-BLOCKER-68.md)). The next snapshots take these open items
  first, the small ones first. Every other open entry is in the [bug tracker](../../BUGS.md).
