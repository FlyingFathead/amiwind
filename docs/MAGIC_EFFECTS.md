# Magic effects

_Last updated with AmiWind v0.0.61-dev1 (5 November 2026)._

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
prototype, off by default.

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

Not yet: magicka, skills, cast chances and the effects on actors (they come with the game logic), the shields and
auras on characters, the lightning rods of shock, the spell icons in a magic menu.

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
- **The look** is this page's (with `dbg magicfx 1` or `2`): the cast, the bolt and the hit of the spell's first
  effect of that range (an effect without its own look takes the first of its school). The look's bolt is drawn
  apart from the spell's own; the failure sound plays only with the look on.

The Magic window (O) selects the spell too: Up and Down move, Enter or a click selects (docs/INVENTORY.md).

Not yet: the casting gesture of the first-person hands and of the parts body, the always-succeeds flag of a few spells,
resistances and reflection, Cast When Used and Constant Effect items, and most effects that need other systems to read
their magnitude (Levitate, Shield, Feather and the like are kept and ticked, but nothing moves or protects by them
yet). Light lights the player with Quake's own entity light while it lasts.

| Command | What it does |
|---|---|
| `dbg cast casting off` / `on` | casting off / on (default; not saved) |
| `dbg cast ready` (`R`) | ready or lower the magic |
| `dbg cast spell list` / `N` / `mN` / `none` | the spells and the selection |
| `dbg cast spell grant N` | for tests: give the player spell N (the actor table's spell row) and select it |
| `dbg cast now` | cast the selected spell now (as the attack button with magic ready) |

These words live under the magic effects' own command (`aw_magicfx`), so casting adds no console command or setting
to the engine's resident registries. Burden and Feather on the player go to the encumbrance once the inventory's
encumbrance call is in the build.
