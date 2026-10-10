# Character animation

The build switch (`--anim-kit`), the `dbg animkit` console commands, the group table and the walk/run rules with their sources: [ANIMKIT.md](ANIMKIT.md).

<!-- contents start -->
## Contents

- [Quake mechanism](#quake-mechanism)
- [The original animation data](#the-original-animation-data)
- [Builder: the animation kit](#builder-the-animation-kit)
- [Engine](#engine)
- [Voices](#voices)
- [Memory](#memory)
- [Visibility](#visibility)
- [Not done yet](#not-done-yet)
- [Tests](#tests)

<!-- contents end -->

How AmiWind animates its people: which of the original animation groups a
character model carries, how the builder samples them, and how the engine plays
them with their sounds. Tracked as
[NPC-ANIM-IDLE-ONLY-33](bugs/NPC-ANIM-IDLE-ONLY-33.md).

## Quake mechanism

A character is a Quake alias model with vertex frames, exactly like Quake's
monsters; animating it means changing the entity's frame, as Quake's QuakeC
does with `$walk1` to `$walk8`. Sounds go through `SV_StartSound` on the
entity's body channel, with their names precached by the spawn function. The
kit adds no renderer feature.

## The original animation data

Morrowind keeps all humanoid animation on one timeline per skeleton file, with
text keys marking each group: `WalkForward: Loop Start`, `WalkForward: Loop Stop`,
`Death1: Start`, `HandToHand: Chop Hit` and so on, plus sound keys
(`SoundGen: Left`, `SoundGen: Right`, `Sound: <id>`).

| Character | Skeleton | Groups from |
| --- | --- | --- |
| Men (human, elf, orc) | `base_anim.nif` | the shared keyframes |
| Women (not beast) | `base_anim_female.nif` | the shared keyframes, with Idle4, Idle5 and WalkForward from the female file |
| Khajiit, Argonians | `base_animkna.nif` | their own file (Argonians add their own swim groups) |
| Creatures | their model | their own keyframes (bipedal creatures also the shared ones) |

The original engine moves a walking character by the root bone's (Bip01)
forward motion in the group, and plays the group at the actor's speed divided
by that motion's speed. Measured root speeds (Quake units per second): walk 38.5
(women 31.5, beast races 24.6), run 55.7, swim 26.3.

## Builder: the animation kit

`tools/npc_anim.py`, used by every resident path (`tools/prepare_area.py`,
`tools/import_town.py`) and by the Arena fighters' run frames
(`tools/prepare_combat.py`). Option: `build.py --npc-anim PROFILE`, recorded in
`build.json` (`npc_anim`).

### Profiles

`config/npc-anim-kit.json`. Every profile starts with the 8 idle frames, so
anything that only knows the idle (QuakeC's idle cycle, older tools) keeps
working.

| Profile | Groups (frames) | Frames |
| --- | --- | --- |
| `idle` (default) | idle 8: the previous method, byte-identical models | 8 |
| `react` | idle 8, hit 3, death 5 | 16 |
| `move` | idle 8, walk 8, run 6, hit 3, death 5 | 30 |
| `full` | idle 8, walk 8, run 6, swim 6, swimidle 4, hit 3, knock 4, death 6, attack 8, block 5, dodgel 3, dodger 3 | 64 |
| `react+full` | standing model `react` (idle 8, hit 3, death 6) plus a mover model `full` | 17 + 64 |

Owner decision (9 October 2026), for the release after v0.0.33: standing
residents ship `react`; an actor that moves (the companion, followers,
fighters) wears its `full` model only while it moves: `react+full`. `idle`
stays the builder default until that release
([NPC-ANIM-MEMORY-33](bugs/NPC-ANIM-MEMORY-33.md)).

With `react+full` one bake gives both models: the standing model is a subset of
the mover's frames (same faces and skin), written as `<model>.mdl`, the mover as
`<model>_m.mdl`; the standing layout names its mover (`>PATH`).

**Byte budget.** Frames are limited by bytes, not by count
([TOOL-ALIAS-FRAMES-33](bugs/TOOL-ALIAS-FRAMES-33.md)): the alias writer's frame
budget (`npc_geometry.animated_mdl`, at most 256 frames), and the kit keeps every
model within the alias stream loader's 512 KiB staging buffer
(`npc_anim.fit`): idle stays whole, the largest other group loses a frame first
(loops keep two, others one), steps grow so each group keeps its duration. On
Balmora four heavy-armour movers drop from 64 to 43 to 49 frames.

### Sampling

- Each group is sampled on the shared skeleton timeline between its keys (loop
  keys for cyclic groups); every part of an actor is posed at the same samples,
  so frames are shared by construction ([modular NPCs](MODULAR_NPCS.md)).
- Moving loops (walk, run, swim) are sampled in place: the root keeps its idle
  x and y. The removed motion is written as the group's own speed.
- Death keeps its root motion (the body falls back) and ends on the final pose.
- A group the skeleton lacks repeats the idle start (the original falls back too).
- Frames are named by group (`walk03`); the face reduction is the idle model's
  (`reference_frames=8`), so the idle frames keep their topology.

### Block and dodge

- **Block** is the original shield group (`shield: block start` to `block stop`,
  1.33 s; X = the `block hit` fraction). OpenMW plays it when a block succeeds
  (CharacterController, hit recoil animations).
- **Dodge** is an AmiWind extension: Morrowind has no dodge group (none of the
  142 groups of base_anim is a dodge, evade or parry). `dodgel` and `dodger` are
  3 in-place frames of `walkleft` and `walkright` (about 16 to 22 KB a model);
  the combat code moves the actor sideways through collision. Inspiration for
  showing misses: see [implementation ideas](IMPLEMENTATION_IDEAS.md) "Combat:
  make dice-roll outcomes visible".

### Footstep sounds

As in the original: footsteps depend on water and boots only (no ground
surface). Barefoot or non-armour boots: `FootBareLeft`/`Right`; armour boots by
weight class against the `iBootsWeight`, `fLightMaxMod` and `fMedMaxMod` game
settings: light, medium or heavy; beast races are barefoot. Standing in water:
`FootWaterLeft`/`Right`; swimming: `Swim Left`/`Right`. NPCs ignore the land,
moan, roar and scream keys (creatures use their sound generator records). The
sound records are read from the master file and converted to 11,025 Hz 8-bit
mono under `sound/aw/fx/`.

### The layout file

Written beside each model as `<model>.anm` (one line):

    NAME:BASE:COUNT:STEP[:X]   a group: first frame, frames, seconds per frame; X = own speed
                               (units/s) for walk, run and swim, hit fraction for attack
    @NAME:OFFSET:EVENT         a footstep (left, right) on a group frame
    ~EVENT:DRY:WADE:SWIM       its sound files (relative to sound/)
    >PATH                      the mover model, worn only while the actor moves
    !TOPIC:HEX16[:KOPV[:KOPV]] a voice line (attack, hit, flee, idle): sound/pool/aHEX16.wav;
                               conditions K h|p|r (speaker health %, player health %,
                               Random100), OP = ! > g < l

Readers skip words they do not know, so the combat layout reader and the kit
reader share the format.

## Engine

`engine/aga/src/aw_anim.c`. The resident spawn function calls builtin #81
`aw_animprep`, which loads the model's layout once per model and precaches its
sounds (spawn time only). A model without a layout keeps the previous frames
(idle 0 to 7; the 21-frame intro actors walk on 13 to 20). Console:
`aw_npc_footsteps 0|1`, `aw_npc_footstep_volume` (default 0.6).

### Choosing a group

In water: swim (swimidle when still); otherwise idle below 1 unit per second,
else walk or run by the nearer own speed (the actors have no run flag), played
at the actor's speed over the group's own speed (clamped 0.25 to 4), so the feet
match the ground. Footsteps play when the frame carrying the event is entered;
the medium (dry, wading, swimming) is read at the actor's feet and chest. The
NPC companion test uses it.

### Mover models

A mover is registered at spawn by name only (the server's model list and the
client's, `Mod_FindName`: nothing is loaded). When the companion starts to follow
or a resident starts to fight, `AW_AnimMover` loads it into the Cache and the
actor wears it; when it stops (companion released, fight over, or a dead
fighter's death clip done) the actor goes back to its standing model and the
mover's Cache block is freed at once. Saves name the standing model. Console:
`aw_npc_movers 0|1`.

### Combat

The combat layer (`aw_combat.c`) takes a kit model's own groups for its idle,
run, attack, hit, knockdown and death (run falls back to walk, others to idle);
fighters with their own layout string are unchanged. A resident engaged without
a layout of its own wears its mover.

## Voices

The original's voice topics (dialogue type Voice: Hello, Idle, Attack, Hit,
Flee, Thief, Intruder), mapped onto the engine's moments with the rules of
OpenMW 0.51 and the game settings:

| Moment | Topic | Rule (source) |
| --- | --- | --- |
| A fight starts | Attack | always (MechanicsManager::startCombat) |
| Each new swing | Attack | 10 % (`iVoiceAttackOdds`; AiCombat startAttackIfReady) |
| Hit, losing health | Hit | 30 % (`iVoiceHitOdds`; Npc::onHit) |
| Flight starts | Flee | always (AiCombat) |
| Death | Hit | always (Actors::killDeadActors) |
| Standing near the player | Idle | `fVoiceIdleOdds` 10: 0.6 % a second, within 3,000 original units (750 here), in sight, not fighting (Actors::playIdleDialogue) |
| The player comes near | Hello | the greeting already in game |

- An actor already speaking says nothing new (DialogueManager::say); there is
  no global voice cooldown in the original.
- **Which line:** the first line whose conditions hold, in file order (OpenMW
  Filter::search); `aw_npc_voice_pick 1` picks at random among them instead (an
  AmiWind option). The builder keeps, per actor and topic, the lines the static
  filters allow (actor, race, class, faction, sex, disposition 50) and stops at
  the first line without a runtime condition (later ones are never said); at
  most 12. Runtime conditions: the speaker's health percent (Hit lines), the
  player's health percent and the global Random100, which the game's own Main
  script rolls every frame ("Set Random100 to Random, 101"): it is what varies
  the idle, attack and hit lines. Lines needing anything else (rank, the
  player's faction, cell, journal, other functions) are left out, never guessed.
- **Files:** the lines are the converted voice pool's files
  (`sound/pool/aHEX16.wav`, the same naming as the media stage); the reference
  closure already keeps every line an included actor can say, so they are in
  the build's referenced voice set. A line left out of a build is silent.
  Played through Quake's client sound system on the voice channel (2) at the
  actor, loaded into the Cache when first said. Console: `aw_npc_voices 0|1`.
- **Cost:** Balmora's dark elf men: 12 attack, 12 hit, 5 flee and 9 idle lines
  (about 2 s each, 22 KB as 11 kHz 8-bit); the layout adds about 1 KB of text per
  model; the engine keeps 672 bytes of line table per model in use.
- Creatures: their moan, roar and scream play only from their own animations'
  sound keys and sound generator records (not done yet).

## Memory

A frame costs 28 bytes plus 4 bytes per vertex; converted actors share no
vertices (three per face), so a frame is 5.4 to 7.3 KB. On Balmora's 15
exterior residents: `react` adds 45 KB per actor, `move` 125 KB, `full` 257 KB
(2.2 times the idle models). See [NPC-ANIM-MEMORY-33](bugs/NPC-ANIM-MEMORY-33.md).

Actor models live in Quake's Cache, not in the CHIM zone: the zone and the
Hunk are unchanged. Measured in FS-UAE (MiniWind, CHIM Balmora, `aw_heap_audit`):

| Build | Hunk low used | Zone largest free | Cache after load | Cache peak at load |
| --- | --- | --- | --- | --- |
| idle only | 9,428,752 | 29,792 | 1,997,344 | 3,274,048 |
| react + full | 9,428,752 | 29,760 | 2,012,368 | 3,574,512 |

Standing models (react, 17 frames) cost 4.00 MB on disk for the 15 actors instead
of 3.21 MB, the movers another 6.97 MB on disk (never all in memory); a worn mover is one more Cache block (the Hlaalu guard's: 522,292
bytes), freed when the actor stops (Cache measured 2,001,536 while following,
1,477,936 after the release). The CHIM frame-map heap gate reports the actors'
Cache demand per map (`actor_cache`: standing models plus two movers against the
Hunk gap); an overflow evicts least recently used models, so it is recorded, not
fatal.

## Visibility

No new entities: an animated actor is the same single entity, linked to the
leaves it touches and culled whole by the PVS and frustum as before. Frame
changes cost nothing in the visibility pass; the frame bounds grow with poses
that reach further (death lying down).

## Not done yet

- Back, left, right and sneak groups; turn in place; jump; random hit1 to hit5.
- Thief and Intruder voices (crime is not simulated yet).
- Weapon stances and weapon attacks (weapons are not drawn yet:
  [NPC-WEAPON-MESH-33](bugs/NPC-WEAPON-MESH-33.md)); random hit1 to hit5 and death1 to death5.
- Creatures (their own keyframes and sound generator records).
- Women on their own skeleton ([NPC-FEMALE-SKELETON-33](bugs/NPC-FEMALE-SKELETON-33.md)).
- Residents walking their own paths.

## Tests

`tests/test_npc_anim.py` (profiles, sampling on a synthetic skeleton, in-place
root, female layer, events, layout, footstep classes, named frames, builtin and
wiring contracts, mover models and the byte budget, block and dodge, voice line
selection, the actors' Cache figure) and `tests/aga_anim_test.c` (layout parsing,
group by speed, rate, stepping, events, mover token, voice picks).
