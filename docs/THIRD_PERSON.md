# Third person, vanity camera and the death scene

_Last updated with AmiWind v0.0.59-dev4 (2 November 2026)._

<!-- contents start -->
## Contents

- [Keys](#keys)
- [The death scene](#the-death-scene)
- [Sources](#sources)
- [The player's body](#the-players-body)
- [The assembled body](#the-assembled-body)
- [First-person arms](#first-person-arms)
- [Console](#console)
- [Build switches](#build-switches)

<!-- contents end -->

The player's view works as in the original game: first person at the start, a third-person view on the
Toggle POV key, a slow orbit around the character after a while without input (the vanity camera), and on
death the camera moves behind the falling body, the death music plays and the game asks whether to load the
most recent save. AmiWind adds one choice to that question: **Retry fight** after a lost fight.

## Keys

| Key | What it does |
| --- | --- |
| Tab (Toggle POV) | A short press switches between first and third person. Held longer than a quarter of a second, the mouse turns the camera around the character instead of turning the character; on release the character turns to face the camera's heading. In third person the orbit starts at once. A tap shorter than one frame (a quick press, or a slow frame on the Amiga) counts as a short press. |
| Mouse wheel | Third person: closer / further (2.5 units a click, between 7.5 and 200). Wheel in at the closest distance goes to first person; wheel out in first person goes to third person at the closest distance. |
| (no input for a while) | The vanity camera: after `fVanityDelay` seconds (the game's own setting, 30 in Morrowind) the camera turns slowly around the character, 3 degrees a second, until any key, mouse movement or movement. While it orbits, the view fills the whole screen with nothing over it: no stat bars, compass, names, prompts or subtitles, as the original hides its interface in the vanity camera. Any input ends the orbit and brings the interface and the normal view size back. `aw_vanity_fullview 0` (saved) keeps the orbit inside the normal interface. |

Tab, the wheel and the bindings are written into new and older key configurations (`aw_controls_migrate`
fills them only when the key is free).

## The death scene

1. The player dies (in a fight, in lava or any other way): talking, activating, attacking, waiting and moving
   stop at once; nobody can be talked to any more.
2. The camera moves behind the character (the original's death camera) and the body plays its death
   animation. The death music plays (the original's death track).
3. When the animation has finished, the original question appears: *"The most recent Save Game is '...'.
   Would you like to load it?"* **Yes** loads it, **No** goes to the main menu. The text and the button
   labels are the game's own settings (`sLoadLastSaveMsg`, `sYes`, `sNo`). With no save at all the original
   goes straight to the main menu.
4. AmiWind extension, on by default: after a lost fight a third button, **Retry fight**, puts everyone back
   where the fight began, with the health and fatigue they had then, and the fight goes on. With no save,
   the question is "Try the fight again?" (Yes: retry, No: main menu). In the Vivec Arena minigame its own
   rematch screen stays in charge.

### While dead

Dead is dead: nothing more is shown or done until a choice is made. One check in the engine (the player's health
is gone) is asked by every path that shows or starts an interaction:

| What | While dead |
| --- | --- |
| Names under the crosshair (people, the silt strider driver, plants) | not shown |
| Prompts ("E: Talk", "E: Pick", door names and "Enter: E", the opening's hints) | not shown |
| The use key (talk, doors, travel, picking), attack, jump, movement, waiting | do nothing |
| The crosshair (and the red companion-pick crosshair) | not shown |
| The enemy's health bar | not shown |
| Greetings and voice lines aimed at the player (with the speaker's name on screen) | none; the line on screen at the moment of death is cleared |
| The health, magicka and fatigue bars | stay (health shown empty), as in the original |

The original does the same for activation and greetings (OpenMW: `Player::activate` refuses a dead player,
`Actors` greets only a living one) and shows no crosshair in the third-person death view (`camera.lua`
`updateCrosshair`: first person only). No voice lines at all while dead (also fight and idle lines) is an AmiWind
rule. The crosshair is also hidden in third person in general, as in the original.

Keys on the question: Left/Right (or A/D, Tab) choose, Enter (or E, Space) accepts, Y and N answer directly.
Escape still opens the menu; the question comes back after it.

## Sources

Every rule comes from the original game as OpenMW 0.51 reproduces it, or from the game's own settings. All
lengths are scaled 0.25 to game units, as the whole world is.

| Rule | Value (original units) | Source |
| --- | --- | --- |
| Toggle POV default key | Tab | `apps/openmw/mwinput/bindingsmanager.cpp` (default key bindings) |
| Short press switches, longer hold orbits | 0.25 s | `files/data/scripts/omw/camera/camera.lua` `updatePOV` (switchLimit) |
| Third-person distance at the start | 192 | `scripts/omw/camera/third_person.lua` (baseDistance) |
| Zoom range | 30 to 800 | `camera.lua` (minDistance, maxDistance), `zoom` |
| Zoom step | 10 per wheel click | `scripts/omw/input/actionbindings.lua` (Zoom3rdPerson) |
| Camera height | 124 above the feet | `apps/openmw/mwrender/camera.cpp` (mHeight) |
| Camera in front of a wall | 5 | `camera.cpp` `updatePosition` (cameraObstacleLimit) |
| Vanity delay | game setting `fVanityDelay` (30) | `camera.lua` `updateVanity`; read from the owned master at build time |
| Vanity turn | 3 degrees a second | `camera.lua` `updateVanity` |
| Death: third-person camera and the body's death animation | | `apps/openmw/mwmechanics/character.cpp` `playRandomDeath` -> `World::useDeathCamera` |
| Death: the question after the animation; Yes loads, No opens the main menu; no save: main menu | | `apps/openmw/mwmechanics/actors.cpp` (`Result_DeathAnimJustFinished`), `apps/openmw/mwstate/statemanagerimp.cpp` `askLoadRecent`, `update` |
| Death question text and buttons | `sLoadLastSaveMsg`, `sYes`, `sNo` | the owned master's game settings |

AmiWind simplifications, labelled as such: the original turns the character towards the orbit camera's
heading gradually after an orbit (deferred rotation); AmiWind turns it at once. The original's
over-the-shoulder offset is an OpenMW option that is off by default; AmiWind keeps the centred camera. The death camera keeps the player's own pitch, as in the original.

## The player's body

The body is baked by the builder through the same pipeline as the town's NPCs, one model per playable race
and sex (20 models, about 0.5 MB each): the original's new-game player record (a common shirt, pants and
shoes) over the race's own skin, the race and sex's first head and hair, and the animation kit's groups from
the skeleton's own text keys (idle, walk, run, hit, death and the shield block; female humans take the female skeleton's walk,
beast races their own skeleton). The engine picks the model of the character's race and sex and plays walk
or run by the real speed, and death when the player dies. A candidate adds the
original jump takeoff/held-air and landing sections from ground and velocity
state. All twenty regenerated models/layouts passed RC1 readback; matched
original-game and broader native verification remain pending under
[PLAYER-JUMP-THIRDPERSON-38](bugs/PLAYER-JUMP-THIRDPERSON-38.md).

In the image step the 80 bakes (body, torch body, water body and inventory poses per race and sex) run in one
worker pool for the whole step, the longest first, and each is kept in the image unit cache
(`WORKSPACE/cache/image-passes/player-view`) by the SHA-256 of its inputs: the game data (the build's input lock),
the palette, race and sex, the body fields a torch or water body reads, the code and the settings it reads. A
build with the same inputs takes every model from there byte for byte (about 3 s instead of about a minute);
`player-view.json` counts the units reused and made, and `--rebuild-unit "player-view:body nord male"` makes one
again ([BUILD-PLAYER-VIEW-UNDERUSED-48](bugs/BUILD-PLAYER-VIEW-UNDERUSED-48.md)).

A source candidate also selects original `idlehh`, `walkforwardhh`,
`runforwardhh` and `jumphh` clips from the first-person rules' bare-hand ready
state. Their own movement speeds drive playback; female normal walking keeps
its override while missing female ready sections use the base skeleton. Changing
stance in the air preserves takeoff/landing progress. Swimming, torch carrying,
death and an old model without the ready groups retain their separate paths.
The RC1 source passed Amiga compilation on 13 October 2026. This does not
establish an accepted visual fix. All 20 actual RC1 body models/layouts passed readback within the existing
alias budgets. Loaded memory and matched original-game views still need
verification. Five extra layout groups model 3,900 bytes across the
64 model entries plus the player layout at 12 bytes/group; target layout size,
stack and frame costs still require target measurement.

Bare-hand draw/lower is connected in the source candidate through an offline
grid of original upper-body poses and independently advancing leg poses. It uses
the existing QuakeC hand-state clock, with no runtime skeletal blending. The
normal/ready gait fraction is retained across stance changes. Its body-only ANM
words are `$ACTION:MOTION_BASE:MOTION_COUNT:GRID_BASE:ARM_PHASES` (actions 1 draw,
4 lower); the loader requires both actions for all five movement groups, checks
frame bounds/overlap and binds each row to the normal animation layout. Old or
invalid layouts retain ordinary body playback. Requested/minimum frame counts
are 253/93; fitting retains arm endpoints within the unchanged alias budgets.
All twenty actual RC1 body models/layouts passed readback. Nord male
ready/lower, movement, jump and camera changes were inspected in one scene.
Other appearances, matched original-game motion, memory and performance
acceptance remain unverified.

This baked body is the previous method since v0.0.59: the default body is assembled from what is worn (below), with
the character's own head and hair. Not yet on either body (the next steps): punch transitions on the assembled body, armed-weapon and torch poses, verified equip/lower playback, other weapon-specific jump variants, and more walk/run frames (the 512 KB model budget is mostly the skin page, so the walk and run
cycles keep 3 to 5 frames).

## The assembled body

Since v0.0.59 the third-person body is, by default, put together from parts by what the player wears, as the
original does: the race's own skin parts per slot, the head and hair chosen at character creation, and over them the
body parts of the clothing and armour worn, slot by slot by the original's priority (armour over clothing, a robe or
skirt over what it covers, a helmet hiding the hair). Changing a shirt, boots, a cuirass or a helmet changes the body
at once. The equipped weapon shows in the right hand while it is drawn, and a shield on the left arm whenever one is
worn, except while a two-handed weapon is drawn (the rule OpenMW follows in `actoranimation.cpp`
`updateCarriedLeftVisible`; the original shows no weapon at the hip).

How it is built (`tools/prepare_player_parts.py`, in the image step beside the baked bodies):

- Every body part mesh of the playable races and of every clothing and armour piece becomes **one model in the
  shared model table** (`progs/parts/`), whoever wears it: a skeletal model of one rest pose on the shared humanoid
  animation table (`progs/humanoid.awsk`, the beast races `progs/humanoid_kna.awsk`), so skinned pieces such as
  cuirasses, shirts and gauntlets bend with the body as the rigid ones (helmets, boots) do. Each part is built at the
  unit size; the game scales the whole body by the race's weight and height after posing, as the original scales
  the actor.
- Each part has a triangle cap by its slot (head 96, chest 72, an upper leg 32, a wrist 12 and so on), so the body in
  the starting clothes stays near the baked body's cost; its skin is cut to the rows it uses.
- `view/parts.txt` (the recipe table) lists per race and sex its scale and skin parts, the heads and hairs it may
  choose, and per clothing or armour piece its parts per slot (male and female, human and beast).
- About 2,200 part models, about 42 MB on the disk; each is a unit of the image unit cache (`player-parts`), so a
  rebuild with the same inputs takes them from there.

In the game (`engine/aga/src/aw_player_parts.c`, `aw_view.c`): the recipe is read only when the race, sex, head,
hair or a worn item changes, and not kept in memory; the parts load as ordinary models (about 0.3 MB for a full
outfit). Every part draws at the body's frame of the shared table; the bones are posed once per frame for all of
them, the vertices per part. The body plays the same groups as the baked one (idle, walk, run, jump, the block,
death and the hand-to-hand ready sections).

The baked body stays selectable (`aw_player_body_parts 0`, saved, or `dbg camera parts off`), and it is still the
body while a torch is carried or while swimming (their own baked poses). Not yet on the assembled body: the
draw/lower and punch arm layers of the baked body, armed stances per weapon class and the torch pose.

## First-person arms

Since v0.0.59 the first-person arms are, by default, put together from the same kind of parts: the race's own hand,
wrist, forearm and upper-arm parts, and over them the parts the worn gloves, gauntlets, bracers, shirt sleeves and
cuirasses give those slots, by the same priority as the body. Where the game has a first-person version of a part (a
record of the same name ending in `.1st`: the race's hands, the gloves and most gauntlets), that version is used, as
the original does (the rule OpenMW follows in `npcanimation.cpp`). A robe shows its own first-person sleeves (its
`.1st` chest record) and covers the arms under them; a robe without one leaves the arms as they are. Changing gloves
or gauntlets in the inventory changes the hands at once. The drawn weapon is held in the same stances as before.

How it is built (`tools/prepare_player_fp_parts.py`, in the image step after the player view):

- The first-person skeleton (`meshes/base_anim.1st.nif`) becomes a small animation table of its two arms, every finger
  joint kept (`progs/humanoid_1st.awsk`, 42 bones, 112 frames, about 30 KB): 28 frames for each of the four stances
  (bare hands, one-handed, two-handed close, two-handed wide) in the same frame order the baked arms use. Its root
  carries the view (the camera of each stance turned to the view axes), so a posed part is already where the baked
  arms are drawn and the drawn weapon sits on the Weapon Bone as before.
- Every arm part mesh of the playable races and of every worn piece becomes one model in the shared model table
  (`progs/parts/`, separate from the body's). A part keeps its authored triangles and vertices, each vertex shared by
  the triangles that use it, as the baked arms do (the textures in one small atlas per part); a part that the shared
  form cannot take, or one with more than twice its slot's cap of triangles (a hand 320, a forearm 120, an upper arm
  80, a wrist 48), is reduced to that cap instead. A race's bare arms are 852 vertices on 1,172 triangles; the
  reduced form of the first version gave every triangle its own three vertices (2,988 on 996).
- `view/parts_1st.txt` (the recipe, the body's format) lists per race and sex its arm parts and per piece its parts.
- 456 part models (357 in the shared form), about 24 MB on the disk; each is a unit of the image unit cache
  (`player-fp-parts`).

In the game (`aw_view.c`, `aw_hand_models.c`, `r_main.c`): the recipe is read only when the race, sex or a worn item
changes, and not kept in memory. The first part is the view model at the hands' frame of the stance, the others are
drawn at the same frame and place; the bones are posed once per frame for all of them. Measured at 32 MB Fast on
FS-UAE with the JIT, the bare hands raised at the same pose and clothes in Seyda Neen, both in one session: the arms
take about 0.35 ms a frame from parts and about 0.35 ms baked (15-second samples: 0.34 to 0.38 ms from parts, 0.34 to
0.35 ms baked). The first version, with unshared vertices, took about 0.5 ms against 0.36 ms. Not measured yet on
the Pi 4B or a 68040.

The baked arms stay selectable (`aw_hand_parts 0`, saved, or `dbg camera hands off`), and they are still the arms
while a torch is carried and while the shield is raised to guard (their own baked poses).

## Console

`dbg camera` (aliases `dbg pov`, `dbg thirdperson`):

| Command | What it does |
| --- | --- |
| `dbg camera` | Status: mode, distance, vanity delay and idle time, death camera, retry, body model. |
| `dbg camera first` / `third` / `toggle` | Switch the view. |
| `dbg camera distance N` | Third-person distance (7.5 to 200 game units; saved as `aw_view_distance`). |
| `dbg camera vanity on/off/now` | The idle orbit on or off (saved), or start it now (the same as `dbg vanitycamera auto/off/on`). |
| `dbg camera death on/off` | The death camera; off keeps the first-person death view (the previous method). |
| `dbg camera retry on/off` | "Retry fight" after a lost fight (`aw_death_retry`). |
| `dbg camera body on/off` | Draw the body; off means first person only (`aw_player_body`). |
| `dbg camera parts on/off` | The body assembled from what is worn (on, the default) or the baked body (off); `aw_player_body_parts`, saved. `dbg camera` lists the assembled body's parts, its scale and the last assembly's time. |
| `dbg camera hands on/off` | The first-person arms assembled from what is worn (on, the default) or the baked arms (off); `aw_hand_parts`, saved. `dbg camera` lists the arms' parts, their frame and the last assembly's time. |
| `dbg camera die` | Test the death scene: the player dies as from world damage (like lava). |

`dbg vanitycamera` (alias `dbg vanitycam`), the vanity camera on its own:

| Command | What it does |
| --- | --- |
| `dbg vanitycamera` | State: auto or off, the delay, the turn rate, the idle seconds now, orbiting or not. |
| `dbg vanitycamera auto` | The original behaviour and the default: the orbit starts after the game's own setting `fVanityDelay` (30 s in Morrowind) without input and turns 3 degrees a second (`aw_view_vanity 1`). |
| `dbg vanitycamera off` | Never orbit (`aw_view_vanity 0`, saved); stops an orbit that is running. |
| `dbg vanitycamera on` (or `now`) | Orbit now, until any key, mouse movement or movement (also when the automatic orbit is off). |
| `dbg vanitycamera delay N` / `delay default` | For testing only: a delay of N seconds (not saved); `default` returns to the game's own setting. |
| `dbg vanitycamera fullview on/off` | The orbit full screen with no interface (on, the default) or inside the normal interface (off); `aw_vanity_fullview`, saved. |

Keys typed in the console (the command itself, closing the console) do not count as input, so an orbit started
from the console keeps running until the first key or mouse movement in the game.

Named shots for inspection and screenshots: `dbg cam mark NAME` saves where you stand and look (with the
time of day, headlamp and fog distance), `dbg cam recall NAME` brings that shot back, `dbg cam list` lists the
marks ([CAMERA_MARKS.md](CAMERA_MARKS.md)).

## Build switches

| Switch | Default | Meaning |
| --- | --- | --- |
| `--player-body on` | on | Bake the player's bodies (`id1/progs/body/`, `id1/view/bodies.txt`). |
| `--player-body off` | | No body: the game stays in first person (Tab says why). |
| `--death-retry on` | on | The death question offers "Retry fight" after a lost fight. |
| `--death-retry off` | | Only the original's choices (`aw_death_retry 0` in the game defaults). |

The camera settings (`id1/view/settings.txt`: `fVanityDelay`, `sLoadLastSaveMsg`, `sYes`, `sNo`) are
always written from the owned master.
