# AmiWind v0.0.63-dev1 (in development)

_Last updated with AmiWind v0.0.63-dev1 (9 November 2026)._

Development snapshot, 9 November 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.62: Stick To The Script](RELEASE-v0.0.62.md).

The first snapshot of v0.0.63. It carries a builder that keeps every finished unit the moment it comes back, actor
models that share their repeated shape data in the image, more of the game's script functions (599 of the 1,207
scripts run, 588 in v0.0.62), and fixes for creatures, combat, breath under water, god mode and dropping items in
rooms. The game needs 32 MB of Fast RAM, and the emulator presets of this snapshot have it.

## Checked by tests, not yet in play

Every change below is checked by the test suite and the gate of this snapshot. None of it has been seen in play on a
build of this snapshot yet; the in-game checklist at the end lists what to look at.

## New since v0.0.62

### The builder

- **Every finished unit is kept at once.** The world (CHIM) units, the player's body parts and the first-person parts
  now go into the unit cache the moment each one comes back, in the order they finish, with one `[done/total]` line
  per unit. A build that stops part way keeps every unit finished before the stop, and the next build reuses them
  instead of baking the whole stage again ([UNIT-STORED-AT-MAP-END-62](../../bugs/UNIT-STORED-AT-MAP-END-62.md)).
  The new unit key re-keys the world stages once, in this snapshot's build.
- **The world stages rebuild only for their own engine inputs.** The world (CHIM) stages counted the whole engine model
  loader file in their keys, so any change to it, even a message, rebuilt the world and its interiors. They now count
  only the loader policies the memory audits read from it and the digest of the brush and edge-cache loaders
  (`BUILD-CHIM-HEAP-KEY-LOADER-63`). The shared shapes changed that loader without renewing the memory audit's pin of
  it, which would have stopped the world stage late in the build; the pin is renewed and a test now runs every
  memory-audit policy on the tree (`BUILD-EDGE-PIN-SHARED-SHAPES-63`).
- **Each stage keeps to its own outputs.** The room residents were baked in a folder of the shared scene while the
  Vivec town stage ran beside it, so a resumed build refused the town's outputs. Residents now bake in a folder of
  their own (`BUILD-STAGE-WRITES-OTHERS-OUTPUT-63`), with a `[done/total]` line per resident.
- **Honest progress estimates.** A stage's time estimate comes from builds of a comparable size, never from a
  one-frame test build scaled up to the whole island (the world stage was shown at 34 hours; it took about 48 minutes)
  (`BUILD-ETA-FRAME-SCALING-63`). The build monitor shows `[done/total]` beside each running stage, and its running maps
  and slowest units on hover; the Toolkit is version 0.1.24.
- **Shared actor shapes.** Actor models built on the same body repeated the same texture-coordinate and triangle
  blocks. The image now stores each repeated pair once, and each model keeps a 28-byte reference to it; the engine
  rebuilds the model byte for byte before it decodes it, so resident memory is unchanged. On the v0.0.62 release
  payload this stores 219 shape files for 2,588 actor models and saves 78,381,384 bytes. The builder option
  `--shared-shapes off` keeps the earlier method. Load time is not measured yet
  (`IMAGE-BIGGER-THAN-ORIGINAL-62`,
  [PAYLOAD_SHARING](../../PAYLOAD_SHARING.md)).
- The blight cloud at Dagoth Ur, an animated effect layer the world format would draw as a solid brown shape, is left
  out of the world; a moving storm effect is to replace it later (`CHIM-DAGOTH-UR-RUIN-CYLINDER-44`).

### Scripts

The game's script functions added in this snapshot, each following OpenMW:

- TurnMoonRed and TurnMoonWhite (Secunda is drawn red while the script holds it, kept in saves, cleared by New Game).
- HasItemEquipped, for the player and for other characters.
- ForceRun, ClearForceRun and GetForceRun, kept in saves.
- ExplodeSpell, GetAttacked and GetSpellEffects.
- BecomeWerewolf, UndoWerewolf, IsWerewolf, SetWerewolfAcrobatics and GetWerewolfKills: the werewolf's attributes and
  skills from the game settings, the player's own given back afterwards, kept in saves; a werewolf runs at the
  original's werewolf speed. The werewolf's body is not drawn yet.
- GetPCTraveling, and SetScale, ModScale and GetScale, which change an object's drawn size.
- GetWaterBreathing, SetWaterBreathing and ModWaterBreathing.

The [MWScript tracker](../../MWSCRIPT_FEATURES.md) now also counts the scripts that do not run by their reason, apart
for Vvardenfell and the add-on worlds. Count at this snapshot:

| State | Scripts |
| --- | ---: |
| Run | 599 of 1,207 (588 in v0.0.62) |
| Use a function the interpreter lacks | 39 |
| Attached, not run | 13 |
| Belong to an add-on world not in the image yet | 422 |
| Named by nothing (they never run in the original either) | 134 |

### Breath, drowning and god mode

- **Breath under water.** The player holds his breath for the original's time under water, a breath bar shows at the
  top of the view, and when it runs out he takes the original's drowning damage with the drowning sound. Water
  Breathing from race abilities, potions, spells and worn items lets him breathe. `dbg breath` shows the state
  (`UNDERWATER-BREATH-62`).
- **God mode holds back every damage**: lava, falls, scripts and spells; a heal still lands
  (`GODMODE-LAVA-DEATH-62`).

### Creatures

- **Creatures stand on the ground.** Walking creatures placed high above the land in the game data (942 of the 5,082
  outdoor levelled creature placements sit more than 128 units above it) are now set down onto what is under them, as
  OpenMW places actors; flying and swimming creatures keep their height
  (`CREATURE-FLOATING-62`).
- **Hostile creatures attack on their own** when the player comes in range, also those without a wander package,
  indoors and out. A fight the player walks out of through a load door is kept, and the creature fights again when
  he comes back, as in the original
  ([ACTOR-WANDER-AGGRO-52](../../bugs/ACTOR-WANDER-AGGRO-52.md)).

### Combat

- **Always use best attack** is a row in Options > Prefs, the same saved value as the console setting, and on by
  default (decided for the project, 7 November 2026; the original's default is off).
- **The chance to hit** follows the original's rule with the active effects: Fortify Attack, Blind, Sanctuary,
  Chameleon and Invisibility count before each swing
  (`COMBAT-HIT-CHANCE-EFFECTS-62`).
- **A blow reaches the nearest fighter in the original's hit cone** when the crosshair finds nobody, so a hovering
  cliff racer can be struck and the opponent's health bar shows
  (`COMBAT-HIT-CONTACT-CONE-62`,
  `ENEMY-HEALTH-BAR-62`).

### The world and the calendar

- **Scripts move the world objects they name.** The Ghostgate switch scripts raise their portcullis and set it back, as
  in the original; scripts that move placed activators, statics, doors and containers along the world (MoveWorld,
  Move, SetPos, SetAtStart) now find them (`WORLD-BUTTONS-62`).
- **Dates read as in the original:** the journal shows 18 Last Seed (Day 3), the rest and wait window adds the hour, a
  saved game shows 18 Last Seed 9 a.m., with the month names and the word Day from the game data; `dbg date` prints
  the lore form (18 Last Seed, 3E 427) and day/month/year (`LORE-DATE-FORMAT-62`).

### Fixes

- **Containers in rooms can be opened again.** An urn, chest or crate is aimed at by its placement box instead of a
  single point (`ROOM-OBJECTS-MISSING-62`).
- **Items can be dropped on uneven tomb and cave floors.** A dropped item lands on the ground under the drop point,
  and on the floor under the player when the spot ahead has no ground, as in the original
  (`DROP-ROOM-BRUSH-ENTITY-59`).
- The register was brought into step with the v0.0.62 release: the console history keys, the witnessed theft and the
  Balmora ground beside the canal are fixed in the v0.0.62 source and wait for the in-game check; the shoreline plan
  and its rebuild cost are written down ([INLAND-SHORE-29](../../bugs/INLAND-SHORE-29.md)).

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

- Swim under water until the breath bar runs out; drink a Water Breathing potion; play an Argonian.
- God mode in the lava near Dagoth Ur and in a long fall.
- Mudcrabs, scribs and guars on the ground outdoors; hostile creatures attacking on sight in a tomb and outdoors; leave
  a fight through a door and come back.
- Options > Prefs > Always use best attack; a cliff racer struck while it hovers, with its health bar.
- Drop an item in a tomb and a cave with an uneven floor.
- Dagoth Ur's surroundings without the brown shape.
- The Ghostgate buttons on both sides; the dates in the journal, the rest window and the save list.
- Load times of rooms and towns with the shared actor shapes, on the Raspberry Pi 4B and in the emulator.
- Carried over from v0.0.62: the console history keys, the witnessed theft in the census office, the Balmora canal
  ground.

## Known in this build

- A player who becomes a werewolf is not drawn as the werewolf
  (`WEREWOLF-BODY-NOT-DRAWN-63`).
- The shores and pond edges still run in saw-tooth steps; the fix needs a world rebuild
  ([INLAND-SHORE-29](../../bugs/INLAND-SHORE-29.md)).
- The game image is still larger than the original game data; the shared shapes are the first step
  (`IMAGE-BIGGER-THAN-ORIGINAL-62`).
- From [v0.0.62](RELEASE-v0.0.62.md): pickpocketing and owned locks are not done, 608 scripts do not run yet, and the
  Heart Chamber may not load at 32 MB Fast RAM.
