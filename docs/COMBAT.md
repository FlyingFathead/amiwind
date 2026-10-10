# Combat and the Vivec Arena minigame

Melee combat is one shared layer for every NPC. The Vivec Arena minigame in
the debugger is its test room: pick an opponent, fight, read the result,
rematch. Development builds only; nothing here changes saved games.

<!-- contents start -->
## Contents

- [Playing the Vivec Arena (testing guide)](#playing-the-vivec-arena-testing-guide)
- [How combat works](#how-combat-works)
- [Cost on a 68040](#cost-on-a-68040)
- [Known limits](#known-limits)

<!-- contents end -->

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
  block animation. Reference: `combat.cpp` blockMeleeAttack.
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

Sounds: the original hit, miss, punch, armour, swish, critical and body-fall
sounds play (converted to 11 kHz). Voices: the layer calls one voice hook per
event (the fight starts, the NPC swings, takes a hit, flees, dies); the
character animation kit plays the original combat lines through it.

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

Disk: combat/actors.txt (about 480 KB, every NPC record, read one letter's
rows per lookup), combat/settings.txt, nine sounds (about 40 KB) and the four
fighters (about 0.3 MB each).

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
- NPCs do not yet start fights on their own (Fight rating, alarms), and do not flee when hurt (only
  the Flee rating's rule for an unreachable player is in).
- Creatures (Dagoth Ur, the Arena's beasts) are not converted for maps yet.
