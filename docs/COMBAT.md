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
Farmin, Seanwen) are baked with combat frames: idle, run, attack, hit,
knockdown and death. Gallery NPCs fight in their one gallery pose; any other
record borrows a resident's model. Statistics always come from the record
itself: level, attributes, skills, health, fatigue, best melee weapon, armour
and shield.

Where: `dbgmode arenapit pit` (the Vivec Arena Pit, when the build has it;
the default then), `floor` (the NPC gallery's floor) or `here` (the current
scene, the opponent appears ahead of you). Without the pit the gallery floor
is used, without that the current scene. Spectators leave; the two fighters
stand on the pit floor 300 units apart, facing each other, at full health and
fatigue.

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
- Weapon damage: minimum + (maximum - minimum) x swing strength for the
  attack (chop, slash, thrust), times fDamageStrengthBase + Strength x
  fDamageStrengthMult x 0.1. NPCs pick the attack weighted by its average
  damage. Reference: `npc.cpp` Npc::hit, `combat.cpp` adjustWeaponDamage,
  `aicombat.cpp` chooseBestAttack.
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
- Block: a shield, the attacker in front (fCombatBlockLeftAngle..
  fCombatBlockRightAngle), not swinging or down; chance from Block skill,
  Agility and Luck against the attacker's skill, clamped to
  iBlockMinChance..iBlockMaxChance. Reference: `combat.cpp` blockMeleeAttack.
- Critical strike x fCombatCriticalStrikeMult on a resident that was not yet
  fighting; x fCombatKODamageMult on a knocked-down victim.
- Knockdown when health damage reaches Agility x fKnockDownMult and a roll
  passes the odds (iKnockDownOddsBase + Agility x iKnockDownOddsMult / 100).
  Below zero fatigue a fighter is knocked out until fatigue returns
  (fFatigueReturnBase + fFatigueReturnMult x Endurance per second). Reference:
  `npc.cpp` Npc::onHit, `actors.cpp` calculateRestoration.
- An NPC that cannot reach you (no route found by the companion's navigation: stuck ping, then the
  step-cell search) never warps and never gives up: it flees, running straight away for one second,
  then stands and watches, and decides again every three seconds, so it comes back as soon as you
  are reachable. Reference: `aicombat.cpp` (no path: flee; flee cooldown 3 s; no combat timeout).
- Every swing costs fatigue: fFatigueAttackBase + weapon weight x swing x
  fWeaponFatigueMult. NPCs wait fCombatDelayNPC plus up to 0.9 s between
  swings.
- Rolls come from one seeded generator per fight (xorshift, 4 bytes), so a
  seed replays a fight swing for swing when both fighters act the same.

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
sounds play (converted to 11 kHz).

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
- NPCs carry no visible weapons or shields yet (weapon and shield meshes are
  not attached to the hand bones); the rules use them.
- The player fights with fists: there are no first-person weapon views. They
  need the weapon mesh on the first-person hands' weapon bone and the
  original first-person weapon groups (idle, equip and the three attacks per
  one-handed, two-handed and two-handed-wide class); about 48 frames, above
  the 32-frame alias limit of the current writer.
- NPCs do not yet start fights on their own (Fight rating, alarms), and do not flee when hurt (only
  the Flee rating's rule for an unreachable player is in).
- The player's knockdown is in the rules only (no fall and stand-up view).
- Creatures (Dagoth Ur, the Arena's beasts) are not converted for maps yet.
