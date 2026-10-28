# Magic effects

_Last updated with AmiWind v0.0.54-dev1 (27 October 2026)._

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
| `dbg cast orb 0` ... `3` | the orb type (see above; not saved) |
| `dbg cast NAME ... dur SECONDS` | how long the hit shell stays on the character the spell lands on |
| `dbg cast NAME area FEET` | a larger area burst |
| `dbg cast NAME repeat` | cast again as each cast ends (for measurements), until `dbg cast stop` |
| `dbg cast list` | the effects in this image (fire, frost, shock, poison, drain, burden, levitate, shield, paralyze, light, dispel, heal, fortify, turnundead, summon) |
| `dbg cast` | the setting, the table and the particles and sprites of the last frame |
