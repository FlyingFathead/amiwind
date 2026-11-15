# Magic effects

_Last updated with AmiWind v0.0.66-dev2 (14 November 2026)._

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
[roadmap](ROADMAP.md#near-term-magic-effects-as-sprites-and-bitmap-planes-25-october-2026). From v0.0.66 the game
turns it on by default (`aw_magic_fx 1` in the game's default settings; `dbg magicfx 0` turns it off; a settings file saved by an earlier version with the look off is switched on once at
the first start, and a later `dbg magicfx 0` stays). This page covers the look of spells (`dbg magicfx`) and, from v0.0.61, how the player casts
them, what the effects do and how enchanted items work, which are on by default and do not need the look.

## What it shows

- **The caster's animation**: a character with a shared animation table plays its own spellcast group (the
  target, touch or self variant), and the spell leaves its hands on the group's release key, as in OpenMW; a
  failed cast plays the animation too. From v0.0.66 the player does the same: readying magic (R) raises the open
  hands of the original's spell stance in first person (`idlespell`; the fists of hand-to-hand stay with F), and the
  attack button plays the cast of the selected spell's first range (`spellcast` self, touch or target) with the spell
  leaving on its release key; a failed cast plays it too. The arms from parts show what is worn (a robe's sleeves,
  gloves, bracers) in the stance and the cast, with all three ranges; the baked arms (`dbg camera hands off`) carry
  the target cast for every range. In third person the parts body plays the same groups. Readying magic shows the
  open hands whatever is equipped (decided for the project, 14 November 2026): a drawn weapon is put away, and a
  carried torch, a held candle or lantern and a shield are put away too while magic is ready (no light from them),
  as in the original, where the spell is a two-handed stance that hides what the left hand carries (OpenMW 0.51, its
  weapon types and `updateCarriedLeftVisible`). Readying the weapon or lowering the magic brings them back. Before,
  with a lit torch or a held light the readied-magic hands showed the fist of hand-to-hand beside it. Every image
  checks this on the data it ships (`tools/ready_hands.py`, run by the image step): the spell stances' open hands
  against the fists, on both first-person paths, and the image stops if the two do not differ.
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

With the setting off nothing is loaded, spawned or drawn. The setting's own value is 0; the game's default settings
set it to 1 (v0.0.66). A saved setting from an earlier version keeps its value.

### In step with the cast (v0.0.66)

A cast's look starts on the frame its cast animation starts: the hand glow, the cast sprites, the cast sound and the
orb or egg-shaped shell around the caster (seen from outside) begin together, for every kind of spell (self, touch,
target, summon), as OpenMW plays the casting effects when the spellcast group starts. The look then waits for the
spell itself: the bolt, the touch or the hit on the caster starts on the frame the spell leaves (the release key), and
a failed roll ends the look there with the school's failure sound. Casts without the hands' animation (an item used,
`dbg cast`) play their whole look at once, as before. `dbg cast` shows the shell shape (the egg is the default), the
count of such casts and the frame numbers of the last one: the animation, the look, the cast sound, the shell and the
release.

## Console

| Command | What it does |
|---|---|
| `dbg magicfx 0` / `1` / `2` | magic effects off / sprites and particles (the game's default, saved) / also their light |
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

- **Ready magic** (`R`, `dbg cast ready`): the hands come up open, whatever is equipped (the weapon, a torch or
  another light and a shield are put away while magic is ready); with magic ready the attack button casts the
  selected spell instead of striking, once per press.
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
- **The look** is this page's (with `dbg magicfx 1`, the default, or `2`): the cast, the bolt and the hit of the spell's first
  effect of that range (an effect without its own look takes the first of its school). The look's bolt is drawn
  apart from the spell's own; the failure sound plays only with the look on.

### Characters cast too (v0.0.66)

A character or creature that knows spells weighs them in a fight against its weapon about once a second, by OpenMW
0.51's combat rules (written independently): each spell's effects are rated by what they would do now (a harmful
effect on the player by its cost and the player's resistance, a summon when none stands by, a healing spell when it is
hurt, a bound weapon by its skill, Blind only on a player with a weapon ready, Silence and Sound only on one with magic
ready), times the game settings for spells (3, or 5 for Target effects) and the spell's chance to succeed. A melee
weapon is rated by its damage, the wielder's strength, its condition, the hit chance and its speed; fists and a
creature's own attacks rate nothing, so a creature or an unarmed caster casts whenever a spell is of use. The best
action wins. A spell is cast from its range (Touch within a blow's reach, the rest from up to 256 map units) with the
player in sight: the magicka is paid, the character's spellcast group plays (self, touch or target by the first
effect), the look starts with it as for the player, and on the release key the roll decides and the spell leaves as
the player's do: its Self effects on the caster, Touch on the player in reach, Target as a bolt from the caster's eye
that lands on the player. `dbg combat spells off` keeps fighters to their weapons (the earlier rule); `dbg combat`
shows the choices and casts. Also rated as OpenMW rates them: Burden on a player its magnitude would overburden (by
the player's load), Feather on an overburdened caster (only the Burden and Feather on it count as its load: a
character's carried weight is not summed in a fight), Dispel by the harmful spell effects it would lift from the
caster or the helpful ones it would strip from the player, Cure Poison and Cure Paralyzation by each such effect on the
caster (above everything else), Restore Magicka and Absorb Magicka by the caster's need (a spell it knows costs more
than its magicka now), the bound weapons one at a time by the caster's skill in that weapon; the bound longbow only
with arrows, which no fighter carries yet, so it is never cast. The disease cures are never cast, as in OpenMW. Fights
between two characters use their weapons only.

Cost: a fighter's spells are read from the actor table once, at its first choice in the fight (the list, then for each
spell its row, its effects, its flags and each effect's record: 1 + 3n + e reads for n spells with e effects); every later choice, once a second, reads nothing from disk and only rates
the kept spells. Each of the 4 fight slots keeps up to 32 spells and 48 effects, about 1.6 KB a slot, 6.4 KB in all,
part of the combat slots for the whole session (no allocation); a new fight reads its fighter again. `dbg combat` shows
the count ("spell reads"). Not measured on the Pi yet: the think's rating cost per choice.

The Magic window (O) selects the spell too: Up and Down move, Enter or a click selects (docs/INVENTORY.md).

A spell flagged as always succeeding in the game data always succeeds.

The cast plays on the player's hands in first person and on the parts body in third person (v0.0.66): the magicka is
paid, the roll made and the spell sent on the cast's release key, not at the press; the refusals (no spell, too
little magicka, a power used today) come at the press, with no gesture.

Not yet: resistances from abilities, reflection,
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
