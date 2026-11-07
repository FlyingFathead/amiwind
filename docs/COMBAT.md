# Combat and the Vivec Arena minigame

_Last updated with AmiWind v0.0.61 (7 November 2026)._

<!-- contents start -->
## Contents

- [Playing the Vivec Arena (testing guide)](#playing-the-vivec-arena-testing-guide)
- [Combat playground](#combat-playground)
- [How combat works](#how-combat-works)
- [Blocking](#blocking)
- [Ordinary weapons and creatures that resist them (v0.0.61)](#ordinary-weapons-and-creatures-that-resist-them-v0061)
- [Weapons, stances and the debug menus (v0.0.61)](#weapons-stances-and-the-debug-menus-v0061)
- [Spells, enchanted weapons and theft in a fight (v0.0.61)](#spells-enchanted-weapons-and-theft-in-a-fight-v0061)
- [Two-handed weapons](#two-handed-weapons)
- [Cost on a 68040](#cost-on-a-68040)
- [Known limits](#known-limits)

<!-- contents end -->

Melee combat is one shared layer for every NPC. The Vivec Arena minigame in
the debugger is its test room: pick an opponent, fight, read the result,
rematch. Development builds only; nothing here changes saved games.

## Playing the Vivec Arena (testing guide)

Open the console (F10) and type:

```
dbgmode arenapit
```

The same mode answers to `dbg arenapit`, `dbg battlearena`, `dbg arenatest`,
`dbg arena`, `testarena` and `dbg combattest`. It captures the game you are
in and puts it back exactly when you leave.

1. A title card names the opponent and level ("VIVEC ARENA").
2. "FIGHT!" and the opponent attacks. Raise your hands with F and punch with
   the attack button. Stay in reach: about one step from the opponent.
3. The result: victory or defeat, the fight's time and seed, your hits and
   misses, damage dealt and taken (health / fatigue).
4. Enter rematches, S rematches with the same seed (the same rolls), N and B
   take the next or previous opponent, P lists opponents in the console, Esc
   or Ctrl+X leaves. F1 shows help at any time.

Choosing an opponent:

| Command | Opponent |
| --- | --- |
| `dbgmode arenapit` | the current opponent, at first the default (Mevil Molor) |
| `dbgmode arenapit list` | the Arena fighters, the gallery and how to pick |
| `dbgmode arenapit ultis salam` | a fighter by name or record ID |
| `dbgmode arenapit #12` or `12` | NPC number 12 of the NPC gallery |
| `dbgmode arenapit fargoth` | any NPC or creature record (the model the world draws it with, else a stand-in) |
| `dbgmode arenapit next` / `prev` | step through the fighters, then the gallery |

The Arena fighters (config/arena_fighters.json: Mevil Molor, Ultis Salam,
Farmin, Seanwen) are baked with 42 combat frames: idle, run, attack, hit,
knockdown and death (the alias writer limits frames by bytes, not count).
A knocked-out fighter stays on the ground until its fatigue returns. Gallery NPCs fight in their one gallery pose; any other
record borrows a resident's model. Statistics always come from the record
itself: level, attributes, skills, health, fatigue, best melee weapon, armour
and shield.

Where: `dbgmode arenapit pit` (the Vivec Arena Pit, when the build has it;
the default then), `floor` (the NPC gallery's floor) or `here` (the current
scene, the opponent appears ahead of you). Without the pit the gallery floor
is used, without that the current scene. Spectators leave; the two fighters
stand on the pit floor 300 units apart, facing each other, at full health and
fatigue.

You fight as the arena's set fighter, so fights test the rules with a capable character:
config/arena_player.json (default a level 9 Nord Monk: Hand-to-hand is a major skill, boiled netch
cuirass and helm, fists only). The builder computes its sheet with the original autocalculation and
writes arena/player.txt; `aw_arena_player 0` fights with your own character instead. Your character
comes back unchanged when you leave. The quick character screen will take this over when it lands.

Loadouts: `dbgmode arenapit loadout NAME` picks one of config/arena_player.json's
loadouts for the next fight: fists (default), sword_shield, mace_shield,
axe_shield, shortsword, spear, claymore. A shield needs a one-handed weapon.
`dbg combat loadout NAME` uses the same test sheet for fights in the world
(`dbg combat loadout off` ends it).

Other switches:

- `dbgmode arenapit seed N`: the next fights use seed N (0: a new seed each
  fight; this is the cvar `aw_combat_seed`).
- `dbg combat readout on/off`: one console line per swing with the hit
  chance, the roll, the outcome and the damage (cvar `aw_combat_readout`,
  default on).
- `dbg combat`: status, both sheets, thinks per second, trace counts and the
  bytes per NPC. `dbg combat calm` ends every fight; `dbg combat off` turns
  the layer off (`aw_combat`).
- `dbg combat music on/off`: the battle music switch (`aw_combat_music`).
- `dbgmode arenapit setup`: fighter setup before the title card arrives with
  the quick character screen; until then fighters use their own sheets.

Since v0.0.33 `dbg combattest` enters the arena. The previous empty-floor
test (current hands, punch on an empty gallery floor) is
`dbg combattest gallery` (or `dbg combattest floor`, `dbgmode combattest`),
with its actions `idle`, `draw`, `lower`, `punch`, `center`, `help` and
`exit` as before.

## Combat playground

The combat playground is the Vivec Arena's set of test modes. The MiniWind preset `--miniwind-combat-playground`
builds a small image that starts in the Arena Pit and lists the modes. Pick a mode in the console with
`dbg playground MODE` (or `dbgmode combat MODE`, `dbgmode arenapit MODE`). `dbg playground modes` lists them.
Development builds only; nothing is saved.

| Mode | What it shows |
| --- | --- |
| `duel [opponent]` | The Vivec Arena minigame above: one opponent fights you. |
| `anim [actor]` | One actor plays every combat group of its animation table in turn, over and over: idle, walk, run, the attack groups of each weapon class (hand to hand, one-handed, two-handed, two-handed wide, bow, crossbow, thrown), the shield block, hits, knockdown, knockout and deaths. The bottom of the screen names the group and, in an attack group, its phase (equip, chop, slash, thrust, shoot, unequip). A baked Arena fighter has no animation table, so its animations play on the model of a skeletal resident of the scene. A model without a table plays its own groups. |
| `aggro [id, id, ...]` | Up to four actors who are not fighting yet. Each one decides on its own whether to attack, by the Fight rule below, and runs away by the Flee rule. The screen shows each actor's Fight, distance, rating and state (calm, HOSTILE, FLEEING, down, dead). Without names it uses the default cast: four NPC records with Fight 100, 90, 85 and a Flee-100 pacifist (config/arena_fighters.json `playground_casts`). They stand in a row along the Pit at 600 to 1,920 original units from you. |
| `group [N] [id, id, ...]` | N fighters (1 to 4; without names, the Arena fighters) all attack you at once. The screen shows each fighter's health and the measured cost of their thinks: thinks a second, mean and longest think in milliseconds. |
| `sounds [creature]` | Every combat sound in turn, one every 1.6 seconds, named on screen with its event (see Sounds below), then the sound generators of a creature record (default `daedroth`): left and right foot, swimming, moan, roar, scream and land. |
| `loadout NAME` | Your weapon and shield for the next fight (config/arena_player.json). |
| `creatures` | Says what creature fights do and do not have yet (see Known limits). |

The rules the aggro mode runs, with the game settings read from your master file:

- Attack on sight (OpenMW 0.51 `mechanicsmanagerimp.cpp` isAggressive, `combat.cpp` getFightDistanceBias,
  `actors.cpp` engageCombat). The effective Fight is Fight + iFightDistanceBase - fFightDistanceMultiplier x
  distance + (50 - disposition) x fFightDispMult. The distance is in original units. The actor attacks when the
  effective Fight reaches 100 and it can see you. Each actor checks about once a second (1 s, give or take 0.25 s).
  A player who is not sneaking is always noticed. With the original settings (20, 0.005, 0.2), a Fight-90 actor
  attacks within 2,000 units and a Fight-85 actor within 1,000. A townsperson with Fight 30 never attacks on sight.
- Disposition: creatures use 50. NPCs also use 50 until the actor record carries their disposition, so the
  disposition term is 0 for now.
- Flee (OpenMW `aicombataction.cpp` vanillaRateFlee and makeFleeDecision, `weaponpriority.cpp`
  vanillaRateWeaponAndAmmo). An actor with Flee 100 or more rates its Flee value. Any other actor rates
  (1 - health / maximum) x fAIFleeHealthMult + Flee x fAIFleeFleeMult, plus the distance term when that is not 0.
  A rating under 100 counts as 0. The actor runs when its rating beats the rating of its best action. Hand to hand
  rates 0. A melee weapon rates armour rating x fAIMeleeArmorMult + the weapon's best maximum damage x skill / 100
  x fAIMeleeWeaponMult. The original settings (7, 0.3) mean that only actors with a very high Flee ever run.
  A fleeing actor runs for one second, then stands and watches. It runs again whenever you come within its reach.
  It decides again after three seconds (ActionFlee).
- The Flee rule is the switch `dbg combat flee on/off`. It is off by default, so fights in the
  world keep the earlier rule: a fighter flees only when it cannot reach you. The aggro and group modes switch it
  on for their session and restore it afterwards. The sounds rule (`dbg combat sounds on/off`, see Sounds) is on
  by default since v0.0.58; the aggro, group and sounds modes switch it on for their session too. Since v0.0.57 attack on sight also runs in the
  world for the creatures that wander (placed and levelled ones): the same rule, on the same one-second check, see
  [NPC pathfinding](NPC_PATHFINDING.md) "Aggro on sight"; `chim actors ambient aggro off` turns it off.

## How combat works

Every NPC the player hits starts fighting back; the Arena opponent is hostile
from the start. The same code runs for both. The rules are the original
game's, written independently; the OpenMW engine's source (0.51) is the
reference used to check them, and the numbers are the game settings read from
your own master file when the image is built.

- Hit chance: (weapon skill + Agility/5 + Luck/10) x fatigue term of the
  attacker, minus the defender's evasion (Agility/5 + Luck/10) x its fatigue
  term; no evasion while knocked down, unaware or below zero fatigue. A roll
  of 0..99 below it hits. Fatigue term = fFatigueBase - fFatigueMult x (1 -
  fatigue/maximum). Reference: OpenMW `combat.cpp` getHitChance,
  `creaturestats.cpp` getFatigueTerm and getEvasion.
- Weapons: short and long blades, blunt weapons, axes and spears, one- and
  two-handed, each with its own skill. Damage: minimum + (maximum - minimum)
  x swing strength for the attack type (chop, slash, thrust), times the
  weapon's condition (current / full) and fDamageStrengthBase + Strength x
  fDamageStrengthMult x 0.1. Every swing in reach wears the weapon by
  fWeaponDamageMult x damage (at least 1, a miss 1); at 0 it breaks and the
  fighter continues with fists. Reference: `npc.cpp` Npc::hit, `combat.cpp`
  adjustWeaponDamage and reduceWeaponCondition.
- Attack type: your movement when the swing starts picks it (forward or back:
  thrust; sideways: slash; standing or diagonal: chop), or the weapon's best
  attack (highest minimum + maximum) with `aw_combat_best_attack 1`, the
  original "always use best attack" option. NPCs pick an attack weighted by
  its average damage. Swing strength: yours is how long you hold the attack
  button until the strike (the punch plays at once, so the hold stands in for
  the original draw-back); an NPC's is random. Reference: `character.cpp`
  getMovementBasedAttackType and getBestAttack, `aicombat.cpp`
  chooseBestAttack.
- Hand to hand (the player's punch): Hand-to-hand skill x (fMinHandToHandMult
  + (fMaxHandToHandMult - fMinHandToHandMult) x swing). It drains fatigue;
  only a knocked-down victim loses health (x fHandtoHandHealthPer).
  Strength does not count (the original rule). Reference: `combat.cpp`
  getHandToHandDamage.
- Armour: health damage x max(damage / (damage + armour rating),
  fCombatArmorMinMult), at least 1. The rating weighs cuirass 0.3; shield,
  helm, greaves, boots and pauldrons 0.1; gauntlets 0.05; empty slots count
  the Unarmored skill. Reference: `combat/local.lua` adjustDamageForArmor and
  getArmorRating.
- Block: a shield with a one-handed weapon (fists and two-handed weapons
  cannot block), the attacker in front (fCombatBlockLeftAngle..
  fCombatBlockRightAngle), not swinging, staggered or down. Rolled only after a
  hit: (Block + Agility/5 + Luck/10) x (swing x fSwingBlockMult +
  fSwingBlockBase), x fBlockStillBonus when not moving forward, x the fatigue
  term, minus the attacker's (skill + Agility/5 + Luck/10) x fatigue term,
  clamped to iBlockMinChance..iBlockMaxChance. A block stops the damage, wears
  the shield by it (at 0 the shield is gone), costs the blocker
  fFatigueBlockBase + weapon weight x swing x fWeaponFatigueBlockMult fatigue,
  plays the shield's light, medium or heavy armour hit sound and the original
  block animation. Reference: `combat.cpp` blockMeleeAttack. "Not moving
  forward" is the forward key, as in the original (sideways or backwards still
  counts as standing).
- Critical strike x fCombatCriticalStrikeMult on a resident that was not yet
  fighting; x fCombatKODamageMult on a knocked-down victim.
- Every damaging hit staggers the victim briefly (no block meanwhile).
- Knockdown when health damage reaches Agility x fKnockDownMult and a roll
  passes the odds (iKnockDownOddsBase + Agility x iKnockDownOddsMult / 100;
  Agility 100 is immune). It lasts the original knockdown clip (2.7 s): no
  moving or acting, 50 % more damage taken, no evasion. Below zero fatigue a
  fighter is knocked out until fatigue returns (fFatigueReturnBase +
  fFatigueReturnMult x Endurance per second). You too: the view drops to the
  floor and your movement and attacks are locked (the console still works);
  you get up over the end of the clip, or shortly after a knockout. Reference:
  `npc.cpp` Npc::onHit, `character.cpp` hit states, `actors.cpp`
  calculateRestoration.
- An NPC that cannot reach you (no route found by the companion's navigation: stuck ping, then the
  step-cell search) never warps and never gives up: it flees, running straight away for one second,
  then stands and watches, and decides again every three seconds, so it comes back as soon as you
  are reachable. Reference: `aicombat.cpp` (no path: flee; flee cooldown 3 s; no combat timeout).
- Every swing costs fatigue: fFatigueAttackBase + weapon weight x swing x
  fWeaponFatigueMult. NPCs wait fCombatDelayNPC plus up to 0.9 s between
  swings.
- Rolls come from one seeded generator per fight (xorshift, 4 bytes), so a
  seed replays a fight swing for swing when both fighters act the same.
- Levelling: your stats in these rolls are your character's own (skills, attributes, level), so a skill or
  attribute raised by levelling changes your hit, block and damage chances from the next fight on. Your blows that
  land train their weapon's skill (Hand-to-hand for fists), a block trains Block, and a blow that hurts you trains
  the armour skill of the piece it lands on (Unarmored for an empty slot). Reference: `combat/local.lua`. The rules
  of the training and the level-up: [Levelling](CHARACTER_CREATION.md#levelling).

## Blocking

The original game has no block button: blocking is automatic whenever a shield
is equipped (the rule above). AmiWind adds a held block, an AmiWind extension
and the default (project decision, 11 October 2026):

- Blocking: Hold to block (default, `aw_combat_block 1`). Hold the right mouse
  button (the Block action in Options > Controls) to raise your shield. You
  block only while it is held, and each blow is still decided by the original
  formula and settings above (Block skill, Agility, Luck, swing, fatigue,
  facing, 10 to 50 % chance): the button decides when you block, your skill
  decides whether the block holds. While you guard you cannot swing: let go to
  attack. "Guard" shows under the crosshair. Without a shield (or with a
  two-handed weapon or fists) there is nothing to raise and the console says
  so. In third person your body raises the shield (the original block
  animation: it rises to the block's hit key and stays up while you hold, and
  plays out after a blocked blow). In first person a block gives the shield's
  sound and a kick of the view; a first-person shield model is a later step.
- Blocking: Automatic (`aw_combat_block 0`): the original rule, the shield
  blocks by itself and the button does nothing.

NPCs always block the original way (automatic, by their skill), with the
block animation of the animation kit and their shield's sound; only fighters
with a shield and a one-handed weapon can block, which is why most residents
never do. Your character from the character creation carries no shield yet;
the arena loadouts with a shield (for example `dbg combat loadout
sword_shield`) can block. Console: `dbg combat block hold|auto`; `dbg combat`
reports the mode and the blocks of the fight (yours and the NPCs').
References: UESP Block (automatic blocking), OpenMW `combat.cpp`
blockMeleeAttack and `character.cpp` (isReadyToBlock, the block hit state).

Two switches, both in Options > Controls and saved with the game settings:

- Combat style: AmiWind (default) or Original Morrowind (`aw_combat_miss` 1 or
  0). Original: a failed roll is a swing through the air with the miss sound.
  AmiWind (an AmiWind extension, not in the original): the defender visibly
  avoids the blow. With a shield and a plausible block (one-handed weapon,
  facing the attacker, not busy) it raises the shield (the original block
  animation and the shield's sound; no damage and no shield wear, since the
  roll missed); otherwise it dodges: the original game has no dodge
  animation, so the dodge is a quick step aside, a few frames of the side
  walk plus a real 10-unit move through the collision (no warp). Your own
  dodge slides the view aside the same way. The swing is resolved once, at
  its contact time; the reaction only presents that result (no second roll,
  no block skill or shield effects for a cosmetic block) and starts at the
  same moment, the block clip at its hit key so the shield is up on contact.
  A swing out of reach is just a swing (no reaction). A fighter that is
  mid-swing, staggered, down, fleeing or dead does not react. Behaviour
  reference (ideas only): the OpenMW mod "Can't Touch This - Combat Miss
  Feedback" (see docs/ROADMAP.md).
- Dice rolls: On (default, `aw_combat_dice 1`, the original rolls) or Off
  (`aw_combat_dice 0`, an AmiWind extension): every swing in reach hits,
  nothing is blocked, a knockdown happens whenever the damage reaches
  Agility x fKnockDownMult (no odds roll) and NPCs swing at half strength.
  Damage, armour, fatigue and condition work as with dice.

Battle music: while any NPC fights the player the battle playlist plays; when
the last one is down the explore playlist returns, each switch starting a new
track (OpenMW `scripts/omw/music/music.lua`: the battle playlist outranks
explore while an actor has combat targets). When the player dies the special
death track plays once; it plays only then (an area change is never read as a
death: the combat frame waits for the spawned player).

Tombs and caves (decided for the project, v0.0.61): while one of the original's
dungeon ambience markers loops (the ancestral tombs' haunted sound and spirit
voices, the caves' drip and wind) the explore playlist rests and only the
ambience is heard. The battle playlist still starts when an enemy attacks, and
after the fight the ambience alone returns. The original and OpenMW keep the
explore playlist on everywhere; this is an AmiWind choice.

The enemy's health bar: the original HUD's yellow bar of the health bar's
size, just above it, appears for fNPCHealthBarTime seconds (3) after each of
your attacks that reaches the enemy, hit or miss, and fades over the last
fNPCHealthBarFade seconds (0.5) (OpenMW `hud.cpp` setEnemy /
updateEnemyHealthBar, `openmw_hud.layout` EnemyHealth). On the 8-bit screen
the fade is a stipple.

Sounds: the original sound records, read from your master file and converted to 11 kHz. Which sound plays for what
follows OpenMW 0.51; the rule is the switch `dbg combat sounds on/off` (on by default since v0.0.58; off plays one
sound per outcome, as before). Your own footsteps are a separate setting, off by default (`dbg footsteps on/off`
and Options > Audio); NPC and creature footsteps play with the rule. With it on:

| Event | Sound record | Rule from |
| --- | --- | --- |
| Every melee swing, hit or miss | Weapon Swish | `character.cpp` prepareHit, playSwishSound |
| Your swing misses | miss (only for the player's swings) | `combat/local.lua` onHit |
| A blow is blocked | the shield's Light, Medium or Heavy Armor Hit | `combat.cpp` blockMeleeAttack |
| A punch tires (no health damage) | Hand To Hand Hit or Hand To Hand Hit 2 | `combat.cpp` getHandToHandDamage |
| A blow takes health | the armour piece struck: Light, Medium or Heavy Armor Hit (none for an empty slot), then Health Damage | `combat/local.lua` pickRandomArmor, applyArmor, onHit |
| A critical strike | critical damage | `npc.cpp` hit |
| Knocked down or killed | Body Fall Medium (the earlier sound; the original plays it from the animation) | `character.cpp` |
| NPC footsteps | FootBare, FootLight, FootMed or FootHeavy Left and Right by the boots worn; FootWater and Swim in water | `npc.cpp` getSoundIdFromSndGen ([ANIMATION.md](ANIMATION.md)) |

The piece struck is picked as OpenMW picks it: cuirass 30 %, helmet, greaves, boots and each pauldron 10 %, each
gauntlet 5 %, the shield 10 %. Each combat sheet carries the armour class of each of those slots.

Creatures: the builder writes every creature record's sound generators (combat/sndg.txt; the SNDG records) by
OpenMW's rule (`mwclass/creature.cpp` getSoundIdFromSndGen): the creature's own generators of each type, else
those of the first other creature with the same model, else the generic ones; one of a type's sounds is picked at
random. Types: left and right foot, swim left and right, moan, roar, scream and land. In Morrowind.esm: 260
creatures, 147 sounds. The combat playground's `sounds` mode plays them; creature fights (see Known limits) will
use the same table.

Voices: the layer calls one voice hook per event (the fight starts, the NPC swings, takes a hit, flees, dies);
the character animation kit plays the original combat lines through it (the "hit" voice when an NPC loses
health, OpenMW `npc.cpp` onHit).

Sound events: every voice and sound moment has one named engine hook (`aw_glut.c` AW_SoundEvent), which plays the
sound the voice table maps for it: the speaker's line of a Voice topic (picked by the original's filter), a named
sound, or a creature's sound generator moment. `dbg sound MOMENT [N]` plays any of them on the actor you aim at
(else on you); `dbg sound list` shows what each plays in this build. The combat work of v0.0.60 calls these hooks;
until then the moments it needs (ranged weapons, casting) are proven through `dbg sound`. The tracker page is
[VOICE_FEATURES.md](VOICE_FEATURES.md).

| Moment | Plays | N |
| --- | --- | --- |
| hello, idle, intruder, thief, hit, attack, flee, alarm | the speaker's line of that Voice topic | |
| taunt | the speaker's Attack line | |
| pain | your own Hit line, by your race and sex | |
| swish, miss, damage, critical | Weapon Swish, miss, Health Damage, critical damage | |
| armorhit, block | Light, Medium or Heavy Armor Hit (a block: the shield's) | 0 light, 1 medium, 2 heavy |
| punch, punch2 | Hand To Hand Hit, Hand To Hand Hit 2 | |
| bowdraw, bowshoot, crossbowdraw, crossbowshoot | bowPull, bowShoot, crossbowPull, crossbowShoot (`character.cpp`) | |
| throw | Weapon Swish (a thrown weapon's release, `character.cpp`) | |
| projectilehit | Health Damage (a projectile striking an actor takes the hit sounds, `projectile.cpp`) | |
| cast, spellhit, spellfail | the school's cast, hit and Spell Failure sound (`spellcasting.cpp`) | the school, 0 Alteration .. 5 Restoration (default 2, Destruction) |
| knockdown, death | Body Fall Small, Medium or Large | 0 small, 1 medium (default), 2 large |
| creatureattack, roar, moan, scream, land | the creature's sound generator (an attack plays its roar) | |

The Thief line is raised by a witnessed theft (v0.0.61-dev3); the Intruder line has its hook, but no game event raises
it yet, as there is no trespass detection. The data's one Alarm line has no NPC that can say it. Every build's report names what is not mapped
(the voice coverage line: NPCs and creatures without a sound, creature moments, named sounds and sound records).

The enemy's bar is yellow: the reserved UI palette bank (indices 225..253)
holds the yellow bar's colours since format 2 of the bank; the sky palette's
approval ignores the bank, so world colours and the sky are unchanged.

## Ordinary weapons and creatures that resist them (v0.0.61)

Ghosts and other creatures with Resist Normal Weapons are hurt less, or not at all, by an ordinary weapon, as in the
original (OpenMW 0.51 `combat.cpp` `resistNormalWeapon` and `isNormalWeapon`):

- A weapon is ordinary unless it is silver, magical (the record's flags) or enchanted. Hand to hand is never resisted.
- The blow's damage, right after the weapon's own damage and its wear, is multiplied by 1 - min(1, resistance -
  weakness), with both as fractions of 100 (Resist Normal Weapons and Weakness to Normal Weapons). A weakness makes the
  blow stronger.
- At 100 % or more the blow does nothing (no hit sound, no hit recovery, no skill use) and the player is shown the
  game's own message box, the setting `sMagicTargetResistsWeapons` ("Your weapon has no effect." in the original
  data), also on a miss, as OpenMW does.
- The same rule applies to the player when an NPC strikes with a weapon (an NPC's weapon counts as ordinary: the NPC
  sheets carry no weapon flags yet).

The resistance comes from the target's active effects (cast spells, worn items: the script host's effect list) and,
since v0.0.62, from the spells of its own list that act always: abilities, blights, diseases and curses (OpenMW 0.51
`activespells.cpp`: every spell of an actor's list that is neither a castable spell nor a power stays active). In the
game data that is the "immune to normal weapons" ability (100 %) of 68 creatures and one NPC (ancestor ghosts, the
atronachs, daedroths, dremora, golden saints, hungers, ogrims, scamps, bonelords and more), the vampires' 50 % and a
few named abilities (Almalexia's shield 30 %, the Hircine aspects and the frost giant 100 %). Before v0.0.62 only the
`dbg combat resistnormal` test value reached the rule, so a real ghost still took full damage. Cost: once per landed
swing; the list part reads the target's spells from the game's actor table on disk the first time and is then kept
(eight answers by actor, effect and list size, refreshed when a script changes the list or a game loads), so a fight
reads nothing after its first blow; `dbg mwscript stats ID` shows an actor's value and how many answers were read and
kept. The weapon's flags are byte 506 of its row in the item catalogue
(`inventory/items.awi`; 0 in older catalogues). `dbg combat resistnormal N` (test only, not saved) gives every target
of the player's swings N % until `dbg combat resistnormal off`, and says whether the effect list is connected and the
message text the image carries.

## Weapons, stances and the debug menus (v0.0.61)

- **Every weapon and shield type is drawn in its stance** on the player's assembled body (one-handed, two-handed close
  and wide, the swings, the unequip), and the held weapon is attached to the hand as in the original. A blade is at
  least one unit thick in the build, so its edge does not vanish when seen edge-on. The first-person view has the
  matching stances, bow, crossbow and thrown included (196 frames in the first-person table;
  [FIRST_PERSON_HANDS.md](FIRST_PERSON_HANDS.md)). Ranged weapons can be equipped and thrown weapons are equipped as
  their stack; the shot itself waits for ranged combat.
- **Two sway styles** for the first-person weapon: the AmiWind groove (default) and a stiff style with still hands, in
  Options, Controls, Weapon sway, or `dbg camera sway 1|2|bench` (the last one measures the cost per frame).
- **God mode** (`dbg god on`) takes no damage, knockdown, fatigue loss or wear, and every cast succeeds and is free.
- **Debug menus.** `dbg weapon` lists every weapon (536 rows) and `dbg gear` every piece of gear (739 rows); each reads
  in about 75 ms and holds about 133 KB only while open.
- **The armour rating** is shown in the inventory window as "Armor: N" under the character picture, worked out from the
  worn pieces, their condition and the skills by the rule above; a Shield effect is added to it there, but the blows
  that land do not yet use that part (`COMBAT-SHIELD-EFFECT-NO-ARMOR-61`).
- **Cliff racers** that attack the player land their strikes: on dry land beside a racer in the open world it attacked
  on sight and hit 11 of 36 swings at its 31 percent chance. Its drawn size, the fish and the pack behaviour are not
  yet seen in game.
- **Creatures keep their fighting frames.** A creature that starts a fight while walking its route used to be handed
  its standing model (16 frames) instead of the walking model (38); it now fights with its own run and attack poses.

## Spells, enchanted weapons and theft in a fight (v0.0.61)

- A harmful spell cast at an actor is an attack and starts the fight; its damage feeds the fight as a blow's does
  ([MAGIC_EFFECTS.md](MAGIC_EFFECTS.md), "Casting").
- A weapon with a Cast When Strikes enchantment casts on a landed blow, a hit or a block, and spends charge by the
  striker's Enchant skill, also on a killing blow. Weapons and shields with such enchantments can be equipped.
- Taking an owned item in view of its owner or another witness reports the crime ("Your crime has been reported!"),
  adds a bounty and the witnesses speak their Thief line and attack. Witnesses are looked for only at the moment of the
  take. Guards who pursue to arrest, pickpocketing, trespass, assault and murder are not in yet. Several witnesses
  that start fights in the same frame hold that frame for about 0.6 s, because each fight start reads its sheet from
  disk ([COMBAT-START-SHEET-READS-61](bugs/COMBAT-START-SHEET-READS-61.md)).

## Two-handed weapons

As in the original, the weapon's type decides: two-handed long blades, two-handed close and wide blunt weapons
(staffs, warhammers), spears and two-handed axes are two-handed, and bows and crossbows take both hands too. Such a
weapon plays the two-handed groups on the player's body and takes the shield off when it is equipped (a shield worn
again later takes the two-handed weapon off). The list below is made from the game data by
`tools/two_handed_weapons.py` (names and numbers only).

<!-- two-handed weapons: generated by tools/two_handed_weapons.py, do not edit by hand -->

| Type | Body group | Weapons | Chop | Slash | Thrust |
| --- | --- | --- | --- | --- | --- |
| Long blade, two-handed | `weapontwohand` | 35 | 1-70 | 1-60 | 1-40 |
| Blunt, two-handed close | `weapontwohand` | 21 | 1-70 | 1-60 | 1-4 |
| Blunt, two-handed wide (staffs, warhammers) | `weapontwowide` | 41 | 2-16 | 1-16 | 1-15 |
| Spear | `weapontwowide` | 48 | 1-18 | 1-15 | 5-60 |
| Axe, two-handed | `weapontwohand` | 18 | 1-80 | 1-60 | 0-16 |
| Bow | `bowandarrow` | 14 | 1-50 | - | - |
| Crossbow | `crossbow` | 2 | 20-30 | - | - |

Bows and crossbows: the Chop column is their damage. The names, by type:

- **Long blade, two-handed** (35): Chrysamere, Daedric Claymore, Daedric Crescent, Daedric Dai-katana, Dwarven Claymore, Foeburner, Fury, Glass Claymore, Ice Blade of the Monarch, Iron Claymore, Iron Flameslayer, Iron Shardslayer, Iron Sparkslayer, Iron Viperslayer, Magebane, Nordic Claymore, Silver Claymore, Silver Flameslayer, Silver Shardslayer, Silver Sparkslayer, Silver Viperslayer, Steel Claymore, Steel Claymore of Hewing, Steel Dai-katana, Steel Flamescythe, Steel Flameslayer, Steel Shardscythe, Steel Shardslayer, Steel Sparkscythe, Steel Sparkslayer, Steel Viperscythe, Steel Viperslayer, Sword of Agustas, Temreki, Shackler of Souls, Umbra Sword
- **Blunt, two-handed close** (21): * Sunder *, BanHammer, Daedric Warhammer, Dwarven Warhammer, Iron Flamemauler, Iron Shardmauler, Iron Sparkmauler, Iron Vipermauler, Iron Warhammer, Orc Warhammer, Shockbite Warhammer, Sixth House Bell Hammer, Steel Flamemauler, Steel Shardmauler, Steel Sparkmauler, Steel Vipermauler, Steel Warhammer, Steel Warhammer of Smiting, Veloth's Judgement, Volendrung, Warhammer of Wounds
- **Blunt, two-handed wide (staffs, warhammers)** (41): Ancestral Wisdom Staff, Boethiah's Walking Stick, Crosier of St. Llothis, Daedric Staff, Divine Judgement Silver Staff, Dreugh Staff, Ebony Staff, Felen's Ebony Staff, Glass Staff, Hellfire Staff, Herder's Crook, Light Staff, Maryon's Staff, Peacemaker, Silver Staff, Silver Staff, Silver Staff of Chastening, Silver Staff of Hunger, Silver Staff of Peace, Silver Staff of Reckoning, Silver Staff of Shaming, Silver Staff of War, Staff of Hasedoki, Staff of Llevule, Staff of Magnus, Staff of the Forefathers, Steel Staff, Steel Staff of Chastening, Steel Staff of Divine Judgement, Steel Staff of Peace, Steel Staff of Shaming, Steel Staff of the Ancestors, Steel Staff of War, Trebonius' Staff, Wizard's Staff, Wooden Staff, Wooden Staff of Chastening, Wooden Staff of Judgement, Wooden Staff of Peace, Wooden Staff of Shaming, Wooden Staff of War
- **Spear** (48): Airan-Ahhe's Spirit Spear, Bound Spear, Bthuangth's Harvester, Chitin Spear, Daedric Spear, Devil Spear, Dwarven Halberd, Dwarven Spear, Ebony Spear, Ebony Spear, Erud-Dan's Spear, Fiend Spear, Fiend Spear, Glass Halberd, Greed, Illkurok, Iron Flamecleaver, Iron Flameskewer, Iron Halberd, Iron Shardcleaver, Iron Shardskewer, Iron Sparkcleaver, Iron Sparkskewer, Iron Spear, Iron Spear, Iron Vipercleaver, Iron Viperskewer, Shockbite Halberd, Silver Flameskewer, Silver Flameskewer, Silver Sparkskewer, Silver Spear, Silver Viperskewer, Spear of Bitter Mercy, Spear of Light, Steel Flamecleaver, Steel Flameskewer, Steel Halberd, Steel Shardcleaver, Steel Shardskewer, Steel Sparkcleaver, Steel Sparkskewer, Steel Spear, Steel Spear of Impaling Thrust, Steel Vipercleaver, Steel Viperskewer, Stormforge, Water Spear
- **Axe, two-handed** (18): Battle Axe of Wounds, Bound Battle Axe, Cloudcleaver, Daedric Battle Axe, Dwarven Battle Axe, Dwemer Pneuma-Trap, Fiend Battle Axe, Iron Battle Axe, Iron Shardaxe, Last Rites, Miner's Pick, Nordic Battle Axe, Orcish Battle Axe, Shockbite Battle Axe, Steel Battle Axe, Stormkiss, Widowmaker, Wings of the Queen of Bats
- **Bow** (14): Auriel's Bow, Bonebiter Bow of Sul-Senipul, Bonemold Long Bow, Bound Longbow, Bow of Shadows, Chitin Short Bow, Daedric Long Bow, Demon Longbow, Devil Longbow, Fiend Longbow, Long Bow, Short Bow, Shortbow of Sanguine Sureflight, Steel Longbow
- **Crossbow** (2): Dwarven Crossbow, Steel Crossbow

<!-- two-handed weapons end -->

## Cost on a 68040

Per hostile NPC: one fixed slot of about 300 bytes (at most four), no allocation; one
think every 0.1 s using the companion's navigation (at most two search traces
plus the step's own moves) and per frame only the animation frame. Nothing
runs while nobody is hostile except the player's fatigue return; the punch is
followed only from the moment the attack button is pressed. `dbg combat`
prints the measured thinks, traces, time per think and bytes.

Disk: combat/actors.txt (about 490 KB, every NPC record, read one letter's
rows per lookup), combat/settings.txt, ten sounds (about 40 KB), the creatures'
sound generators (combat/sndg.txt, about 30 KB, and 147 sounds, about 1.7 MB) and
the four fighters (about 0.3 MB each).

## Known limits

- Combat state is not saved: after loading a game nobody is hostile, and an
  NPC killed in normal play stands again after loading (its health is saved).
- Fighters hold the weapon and shield the rules use. Arena fighters have them
  baked into their model (weapon on the weapon bone, shield on the shield
  bone). Town residents draw them only while fighting: each item is its own
  small model, stored once per mesh (items/), placed every frame on the hand
  bone's position from a tag table beside the resident's model (<model>.tag,
  tools/npc_items.py, engine/aga/src/aw_items.c). The item keeps its own size
  (the original also stretches it with the actor's race width and height).
- First-person weapon views: since v0.0.59 an equipped melee weapon is drawn in the hands in the original's three
  stances (one-handed, two-handed close, two-handed wide; see [FIRST_PERSON_HANDS.md](FIRST_PERSON_HANDS.md)), and
  v0.0.61-dev2 adds the bow, crossbow and thrown stances (not yet seen in game as stills). The shot of a ranged weapon
  waits for ranged combat. A weapon loadout (`dbgmode arenapit loadout sword_shield`, config/arena_player.json) fights
  with the weapon's rules.
- The world's NPCs do not yet start fights on their own, other than the witnesses of a theft (their disposition toward the player is not modelled);
  creatures that wander do since v0.0.57, at most four at once; in a larger pack the next one joins as soon as one
  falls (a fallen fighter's slot is reused and its death kept, COMBAT-PACK-SLOTS-57). Alarms are not in. Fleeing by the Flee rating is in, behind `dbg combat flee on` (off by default).
- Sounds play at the listener, not from the fighter's position. Creatures do not yet play their own sound
  generators from their animations' sound keys; the table is built and the `sounds` mode plays it.
- Creatures: combat/actors.txt holds NPC records only, so until v0.0.54 a creature had no sheet and a blow passed
  through it. A creature's sheet now comes from the actor record ([ACTOR_STATE.md](ACTOR_STATE.md)), by OpenMW's
  rules (`mwclass/creature.cpp` hit, getSkill, getArmorRating): its level, attributes, health, fatigue, Fight and
  Flee; its combat value in every combat skill; no armour; its own chop, slash and thrust attacks as health damage
  (minimum + (maximum - minimum) x swing, no Strength modifier, no condition); a bipedal creature punches hand to
  hand. Hit one in the world, or name its record ID in the arena (`dbgmode arenapit daedroth`). Since v0.0.62 the arena
  draws a creature named by its record ID with the model the outdoor world draws it with (its base in the actor table,
  `maps/chim-actors.cca`: the creature's own standing model with its mover for the run and attack frames), so the
  `group` and `aggro` modes show a cliff racer as a cliff racer; a record with no model in the build still gets a
  stand-in.
  Not yet: weapons a creature carries (it fights with its own attacks) and its sound generators from its animations.
  A creature that starts a fight while walking its route now fights with its own run and attack frames (v0.0.61-dev3).
