# Combat and the Vivec Arena minigame

_Last updated with AmiWind v0.0.57-dev1 (30 October 2026)._

<!-- contents start -->
## Contents

- [Playing the Vivec Arena (testing guide)](#playing-the-vivec-arena-testing-guide)
- [Combat playground](#combat-playground)
- [How combat works](#how-combat-works)
- [Blocking](#blocking)
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
| `dbgmode arenapit fargoth` | any NPC record (a stand-in model) |
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
  on for their session and restore it afterwards. The same goes for the sounds rule (`dbg combat sounds on/off`,
  see Sounds), which the aggro, group and sounds modes switch on. Since v0.0.57 attack on sight also runs in the
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
death track plays once.

The enemy's health bar: the original HUD's yellow bar of the health bar's
size, just above it, appears for fNPCHealthBarTime seconds (3) after each of
your attacks that reaches the enemy, hit or miss, and fades over the last
fNPCHealthBarFade seconds (0.5) (OpenMW `hud.cpp` setEnemy /
updateEnemyHealthBar, `openmw_hud.layout` EnemyHealth). On the 8-bit screen
the fade is a stipple.

Sounds: the original sound records, read from your master file and converted to 11 kHz. Which sound plays for what
follows OpenMW 0.51; the rule is the switch `dbg combat sounds on/off` (off by default: then each outcome plays one
sound, as before). With it on:

| Event | Sound record | Rule from |
| --- | --- | --- |
| Every melee swing, hit or miss | Weapon Swish | `character.cpp` prepareHit, playSwishSound |
| Your swing misses | miss (only for the player's swings) | `combat/local.lua` onHit |
| A blow is blocked | the shield's Light, Medium or Heavy Armor Hit | `combat.cpp` blockMeleeAttack |
| A punch tires (no health damage) | Hand To Hand Hit or Hand To Hand Hit 2 | `combat.cpp` getHandToHandDamage |
| A blow takes health | the armour piece struck: Light, Medium or Heavy Armor Hit (none for an empty slot), then Health Damage | `combat/local.lua` pickRandomArmor, applyArmor, onHit |
| A critical strike | critical damage | `npc.cpp` hit |
| Knocked down or killed | Body Fall Medium (the earlier sound; the original plays it from the animation) | |
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

The enemy's bar is yellow: the reserved UI palette bank (indices 225..253)
holds the yellow bar's colours since format 2 of the bank; the sky palette's
approval ignores the bank, so world colours and the sky are unchanged.

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
- There are no first-person weapon or shield views yet: a weapon loadout
  (`dbgmode arenapit loadout sword_shield`, config/arena_player.json) fights
  with the weapon's rules while the view shows the hands. The views need the
  weapon mesh on the first-person weapon bone and the original first-person
  weapon groups (idle, equip and the three attacks per one-handed,
  two-handed and two-handed-wide class).
- The world's NPCs do not yet start fights on their own (their disposition toward the player is not modelled);
  creatures that wander do since v0.0.57, at most four at once; in a larger pack the next one joins as soon as one
  falls (a fallen fighter's slot is reused and its death kept, COMBAT-PACK-SLOTS-57). Alarms are not in. Fleeing by the Flee rating is in, behind `dbg combat flee on` (off by default).
- Sounds play at the listener, not from the fighter's position. Creatures do not yet play their own sound
  generators from their animations' sound keys; the table is built and the `sounds` mode plays it.
- Creatures: combat/actors.txt holds NPC records only, so until v0.0.54 a creature had no sheet and a blow passed
  through it. A creature's sheet now comes from the actor record ([ACTOR_STATE.md](ACTOR_STATE.md)), by OpenMW's
  rules (`mwclass/creature.cpp` hit, getSkill, getArmorRating): its level, attributes, health, fatigue, Fight and
  Flee; its combat value in every combat skill; no armour; its own chop, slash and thrust attacks as health damage
  (minimum + (maximum - minimum) x swing, no Strength modifier, no condition); a bipedal creature punches hand to
  hand. Hit one in the world, or name its record ID in the arena (`dbgmode arenapit daedroth`, a stand-in model).
  Not yet: weapons a creature carries (it fights with its own attacks), its own animation groups in a fight and its
  sound generators from its animations.
