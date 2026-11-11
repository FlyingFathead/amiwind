# Magic effects

_Last updated with AmiWind v0.0.64-dev5 (11 November 2026)._

<!-- contents start -->
## Contents

- [What it shows](#what-it-shows)
- [How it is made](#how-it-is-made)
- [Console](#console)
- [Casting (v0.0.61)](#casting-v0061)

<!-- contents end -->

Morrowind draws its spells with a set of small effect meshes and textures of its own: a glow on the casting hands,
a burst at the caster, a bolt per school in flight, a burst where it hits and an orb where an area spell lands.
AmiWind shows them with Quake's own machinery, following the plan in the
[roadmap](ROADMAP.md#near-term-magic-effects-as-sprites-and-bitmap-planes-25-october-2026). It is an experimental
prototype, off by default. This page covers the look of spells (`dbg magicfx`) and, from v0.0.61, how the player casts
them, what the effects do and how enchanted items work, which are on by default and do not need the look.

## What it shows

- **The caster's animation**: a character with a shared animation table plays its own spellcast group (the
  target, touch or self variant), and the spell leaves its hands on the group's release key, as in OpenMW; a
  failed cast plays the animation too. Not yet: the first-person hands' cast animation.
- **The orb**: the translucent sphere in the spell's colour that wraps the caster while casting and the character
  a spell lands on, made from the effect's own shell texture with the effect's own hit model (a shield's body-shaped
  shell, levitation's rings) drawn into it from the front. On the character a spell lands on it follows them and,
  for the effects whose record keeps their hit visual for the whole duration (shields, levitation, light ...), stays
  for that duration (`dbg cast NAME dur SECONDS`; 8 seconds by default), as in OpenMW; seen from the player's own
  eyes it is a faint veil; `dbg cast orb 0|1|2|3` picks the type to compare: 0
  the first prototype (the cast glow), 1 the bubble, 2 the bubble with small sprites swirling on its radius (the
  default), 3 the swirling sprites only.
- **Hand glow**: a small cloud of sparks before the caster's hands, in the colours of the spell's particle texture.
- **Cast**: the school's cast effect around the caster: its particles rising from the feet and a glowing orb as tall
  as the caster (seen from outside), or the burst before the hands (first person), and a glow sprite on each hand.
- **Bolt**: a sprite flying along the view with its trail of particles; with the light setting, a moving light.
- **Hit**: a growing, fading sprite and a burst of particles on the actor the bolt strikes.
- **Area**: an orb where the bolt lands (a target spell always makes one; a larger area adds a ring of sprites
  spreading to its size).
- **Sounds**: the cast, the bolt (looping and following the bolt in flight, stopped where it lands), the hit, the
  area burst, and the failed cast (`dbg cast NAME fail`: only the failure sound, no effect).

### Which sound plays

Every magic effect record may name its own cast, bolt, hit and area sounds; when a field is empty the school's
sound plays instead (`<school> cast`, `bolt`, `hit`, `area`). A failed cast always plays the school's
`Spell Failure <School>`. In the game data most effects take their school's sounds; shock and frost have their
own, and a few effects borrow another school's (for example the calm effects use alteration's, the absorb
effects restoration's). The bolt's sound loops while the bolt flies. These rules follow OpenMW
(`mwworld/store.cpp`, `mwmechanics/spellcasting.cpp`, `mwworld/projectilemanager.cpp`). Spells, enchantments,
scrolls and the script commands that make someone cast all go through the same casting, so they play the same
sounds; a potion plays the drinking sound (its effects' own sounds are still to check). The image step converts the sounds the
chosen effects use and writes the whole table, every effect's sound per phase, into the build report
(`magic-effects.json`).

The magicka, the cast chance and the effects on actors are in since v0.0.61 (see "Casting" below). Not yet in the look:
the shields and auras on characters in every case, the lightning rods of shock and the spell icons in the magic menu.

### Shell shapes

Every effect's shell is built in two numbered shapes, both baked into sprites when the image is built (the engine
draws one sprite either way, at the same cost per pixel):

| Shape | Name | What it looks like |
|---|---|---|
| 0 | egg (the default) | the effect's own hit model seen from the front: for the shield an upright "cosmic egg" about one and a half times as tall as wide, reaching from the feet to above the head, as in the original |
| 1 | sphere | a round, dotted see-through bubble in the effect's colour, strongest at its rim, with the hit model's pattern laid in (the first shell of v0.0.54, kept as its own shape for spells and effects that want it) |

The shape is chosen with `dbg cast shell egg|sphere` (saved with the orb type) or for one cast with
`dbg cast NAME ... shape sphere`. Shells seen close (the player's own seen from behind, the first-person veil) use
a finer 64-pixel copy of the same shape.

## How it is made

Nothing is drawn by hand. The image step (`tools/prepare_magic.py`) reads the user's own game data: each chosen
magic effect's record (school, colour, particle texture, the cast, bolt, hit and area visuals and sounds) and the
effect meshes those name. From each mesh it takes the particle emitters (how many particles, their size, life,
speed, direction and spread, gravity, when they start and stop) and the texture each uses; from each texture a
Quake sprite (32 by 32 pixels, four fading frames, its glow kept as an ordered dither in the image palette) and a
ramp of eight colours for the particles. A phase without its own visual uses the game's default one, and an
effect's particle texture replaces a mesh's texture only where the mesh's root names that texture first, as in
OpenMW. Particle counts are capped for the 68040 (20 to 56 a phase, against up to several hundred in the original).

The engine (`aw_magic.c`) shows them with:

- Quake's particle pool (`r_part.c`): the emitters' particles, in the texture's colours;
- Quake sprites drawn as temporary entities (`cl_tent.c`, `r_sprite.c`): the hand glows, the bolt, the hit and the
  area burst, fullbright, with their fade frames and AmiWind's sprite scale;
- Quake's dynamic lights, only with `dbg magicfx 2`: the bolt's light and a short flash where it lands. A software
  dynamic light rebuilds every surface it touches, so it has its own setting.

With the setting off (the default) nothing is loaded, spawned or drawn.

## Console

| Command | What it does |
|---|---|
| `dbg magicfx 0` / `1` / `2` | magic effects off (default, saved) / sprites and particles / also their light |
| `dbg cast NAME` | cast NAME's look: hand glow, cast, a bolt along the view, its hit and area burst |
| `dbg cast NAME touch` / `self` | the hit within reach / on yourself instead of a bolt |
| `dbg cast NAME fail` | a failed cast: the school's failure sound only |
| `dbg cast NAME npc` | the actor most in front of you (within 600 units) casts NAME at you |
| `dbg cast orb 0` ... `3` | the orb type (see above; saved) |
| `dbg cast shell egg` / `sphere` | the shell shape of the effect set (see below; saved) |
| `dbg cast NAME ... shape egg` / `sphere` | the shell shape for this one cast |
| `dbg cast NAME ... dur SECONDS` | how long the hit shell stays on the character the spell lands on |
| `dbg cast NAME area FEET` | a larger area burst |
| `dbg cast NAME repeat` | cast again as each cast ends (for measurements), until `dbg cast stop` |
| `dbg cast list` | the effects in this image (fire, frost, shock, poison, drain, burden, levitate, shield, paralyze, light, dispel, heal, fortify, turnundead, summon) |
| `dbg cast` | the setting, the table and the particles and sprites of the last frame |

## Casting (v0.0.61)

The player casts the spells and powers he knows and the spells he made at a spellmaker. The rules follow OpenMW
0.51 (its spell utility, world and spell casting code), written independently.

- **Ready magic** (`R`, `dbg cast ready`): the hands come up; with magic ready the attack button casts the selected
  spell instead of striking, once per press.
- **The selected spell**: `dbg cast spell list` shows the known spells and powers (with their number, cost and the
  selection), `dbg cast spell N` selects spell N, `dbg cast spell mN` the made spell N, `dbg cast spell none` clears
  it.
- **The magicka** is paid when the cast starts; with too little the cast is refused ("You do not have enough
  Magicka to cast the spell."). A power costs nothing and works once a day (game hours).
- **The chance**: the effect with the lowest twice-the-school-skill minus its cost term gives the skill; the chance is
  that skill minus the spell's cost, plus a fifth of Willpower and a tenth of Luck, less the Sound effect's magnitude,
  times the fatigue term (1.25 minus 0.5 times the missing share of fatigue), from 0 to 100; Silence makes it 0. A
  roll from 0 to 99 below the chance succeeds; a failure keeps the magicka spent and says "You failed casting the
  spell.". A success gives the school's skill its use. In god mode (`dbg god on`) every cast succeeds and costs no
  magicka, as in OpenMW.
- **Delivery**: the Self effects land on the player; the Touch effects on the actor within a blow's reach in front;
  the Target effects fly as a bolt (the masters' bolt speed) and land on the actor in the line of the cast when the
  bolt reaches it (the fight's own aim test picks it at the cast; the world stops the bolt first if it is in the way)
  and, with an area, on every actor within the area's radius where it lands. A bolt carries its own spell: a later
  selection does not change it.
- **The effects** land through the active effects (each magnitude rolled once between its low and high, the
  duration on the game clock, kept in saved games; docs/MWSCRIPT_BYTECODE.md "Spell effects"). A harmful spell on an
  actor is an attack: it joins the fight, and its health falls with the damage until it dies as by a blow.
- **The effect system**: any of the 143 effects can be applied to any actor by reference (a table of 64 entries, 32 of
  them for the player), over time or once as the original does, with harmful effects told apart. The effects are kept
  in saved games (a block of their own; saves of before it still load, and since v0.0.61-dev3 the block is read at
  its real size, which dev2 got wrong and so lost the effects and the blocks stored after them on a load). The effects
  of non-player actors run while they are loaded and their damage feeds the fight. Creatures ignore skill effects.
  Light lights the player; Resist Normal Weapons and Weakness to Normal Weapons are read by the combat code; Burden
  and Feather feed the carry weight (docs/INVENTORY.md).
- **The look** is this page's (with `dbg magicfx 1` or `2`): the cast, the bolt and the hit of the spell's first
  effect of that range (an effect without its own look takes the first of its school). The look's bolt is drawn
  apart from the spell's own; the failure sound plays only with the look on.

The Magic window (O) selects the spell too: Up and Down move, Enter or a click selects (docs/INVENTORY.md).

A spell flagged as always succeeding in the game data always succeeds.

Not yet: the casting gesture of the first-person hands and of the parts body, resistances from abilities, reflection,
and the effects that need other systems to read their magnitude: Levitate and the other movement effects move nothing,
and a Shield effect on the player does not soften the blows that land on it (the inventory window adds it to the armour
rating; `COMBAT-SHIELD-EFFECT-NO-ARMOR-61`). When a Fortify Attribute effect on the player ends, the stat sheet keeps
it as a raised modifier plus a drop counted as damage (`PLAYER-FORTIFY-END-AS-DAMAGE-61`). Light lights the player with
Quake's own entity light while it lasts.

### Magic items (v0.0.61)

The game's enchanted items work by their enchantment's kind, by OpenMW 0.51's rules (its spell casting, combat and
active spells code), written independently. The builder writes every enchantment of the masters into the actor table
(its kind, its cast cost before the user's Enchant skill, its full charge and its effects; docs/ACTOR_STATE.md); the
engine reads an item's enchantment by its id when the item is used, strikes or is put on, and keeps the last two.

- **Cast When Strikes**: a weapon blow that hits, or is blocked, casts the weapon's enchantment: its Touch and Target
  effects land on the one struck, its Self effects on the striker. Each strike takes charge: the enchantment's cost
  less one percent for each point of the striker's Enchant skill over 10, at least 1. With too little charge left
  nothing is cast and the player is told "Item does not have enough charge.". The player's strikes give Enchant its
  use; an NPC's or a creature's weapon works the same way on the player (its spent charge is kept for the session; this
path has not yet been seen in game, although 408 actors hold such a weapon). Weapons and shields with a Cast When
Strikes or Cast When Used enchantment can be equipped (before dev3, 191 strike weapons, 59 use weapons and 20 use
shields, the iron shardaxe among them, were refused); Constant Effect items are worn as before.
- **Cast When Used** and **Cast Once** (scrolls): select the item (in the Magic window's Magic Items since v0.0.64,
  or `aw_magic select ID` in the console; a scroll needs no charge to be selected), ready magic and press the
  attack button (or `dbg cast now`): it is cast without a success roll, paying its charge as above (a Cast Once item
  is used up instead); Self effects on the player, Touch on the actor in reach, Target as a bolt. A selected item and
  a selected spell exclude each other, as in the original.
- **Constant Effect**: a worn item's effects are active while it is worn and end when it comes off (each magnitude
  rolled once when it is put on): a ring of Fortify Agility 30 takes Agility from 30 to 60 on and back to 30 off. They
  are kept in saved games and set again from what is worn after a load. The worn Constant Effect items of non-player
  characters are not applied yet, and the item table holds the base game's items only (Tribunal and Bloodmoon items
  are not in it).
- **Charge**: the player's items keep their charge in saved games and recharge over time
  (`fMagicItemRechargePerSecond`); the HUD's magic box shows the selected item's charge. God mode spends none.

`dbg cast spell list` also shows the selected item's charge and how many items were used, refused for lack of
charge, how many strikes cast, and how many worn effects are active.

### Summoning (v0.0.62)

A summoning effect (Summon Scamp to Summon Storm Atronach, Summon Centurion Sphere) calls up the creature the
effect's game setting names (sMagicScampID and the others), by OpenMW 0.51's rules (its summoning and actors code),
written independently. It works from a spell, a scroll or an enchanted item alike, since it is an effect like any
other.

- The creature appears 120 game units in front of the caster, facing as the caster faces (where that spot is
  blocked, beside or behind), with a short flash, and stays while the effect lasts on the game clock.
- It follows the player, comes back beside the player after a door or a loaded game while the effect lasts, and
  goes with the same flash when the effect ends.
- When it dies the effect ends at once and its body goes a few seconds later.
- The creatures are the game's own records (the summoned scamp, clannfear, daedroth, dremora, golden saint, hunger,
  winged twilight, the flame, frost and storm atronachs, the ancestor ghost, the skeletal minion, the bonewalker and
  the greater bonewalker, the bonelord and the centurion sphere), drawn with the creature library's models of the
  same kind: the builder gives each a base in the actor table and writes the effects' creatures into
  `maps/chim-summons.txt`.

What it costs: one creature model while it stands (445 to 589 triangles; its model file 183 to 316 KB, the walking
model 358 to 472 KB when the same kind of creature is not already loaded nearby), about 2 KB of the engine's own
memory, and a look over the 64 active effect entries each frame while any effect is active.

Not yet: the creature does not fight for the player (`COMBAT-SUMMON-ALLY-62`), its record's script is not attached
(the bonewalkers' disease script), the original's summon start and end effect meshes are not converted (a Quake
teleport flash stands in), and a summoning effect cast by an NPC calls up nothing (NPCs do not cast yet).
`aw_mwscript_status` counts the summons; `aw_mwscript_status summon EFFECT SECONDS` lands a summoning effect on the
player for SECONDS (a test route, as a cast's Self effect lands).

### Starting spells (v0.0.61)

A new character starts with the spells of the race and the birthsign and, as in the original, with the starting
spells the class and skills give: among the game's spells flagged as starting spells (in the masters' order), each
one the race does not give already, whose cost the character's magicka (Intelligence times fPCbaseMagickaMult) can
pay, whose chance (twice the weakest school's skill, less the cost, plus a fifth of Willpower and a tenth of Luck) is
at least fAutoPCSpellChance, and whose named attribute or skill is at least iAutoSpellAttSkillMin (OpenMW 0.51
autocalcspell.cpp). They are chosen from the character as character creation builds it, so they change with the
race, class and birthsign there and never later. `dbg cast start` lists them.

| Command | What it does |
|---|---|
| `dbg cast casting off` / `on` | casting off / on (default; not saved) |
| `dbg cast ready` (`R`) | ready or lower the magic |
| `dbg cast spell list` / `N` / `mN` / `none` | the spells and the selection |
| `dbg cast spell grant N` | for tests: give the player spell N (the actor table's spell row) and select it |
| `dbg cast now` | cast the selected spell, or use the selected magic item, now (as the attack button with magic ready) |
| `dbg cast start` | the starting spells the class and the skills gave the character made in this session |
| `dbg cast strike` | for tests: the held weapon's Cast When Strikes as if its blow landed on the actor in reach |

These words live under the magic effects' own command (`aw_magicfx`), so casting adds no console command or setting
to the engine's resident registries. Burden and Feather on the player go to the encumbrance once the inventory's
encumbrance call is in the build.
