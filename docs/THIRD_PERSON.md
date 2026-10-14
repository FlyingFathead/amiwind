# Third person, vanity camera and the death scene

The player's view works as in the original game: first person at the start, a third-person view on the
Toggle POV key, a slow orbit around the character after a while without input (the vanity camera), and on
death the camera moves behind the falling body, the death music plays and the game asks whether to load the
most recent save. AmiWind adds one choice to that question: **Retry fight** after a lost fight.

<!-- contents start -->
## Contents

- [Keys](#keys)
- [The death scene](#the-death-scene)
- [Sources](#sources)
- [The player's body](#the-players-body)
- [Console](#console)
- [Build switches](#build-switches)

<!-- contents end -->

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

Not yet (the next steps): the character's own chosen head and hair, the clothes and armour actually worn,
punch transitions, armed-weapon and torch poses, verified equip/lower playback, other weapon-specific jump variants, and more walk/run frames (the 512 KB model budget is mostly the skin page, so the walk and run
cycles keep 3 to 5 frames).

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

## Build switches

| Switch | Default | Meaning |
| --- | --- | --- |
| `--player-body on` | on | Bake the player's bodies (`id1/progs/body/`, `id1/view/bodies.txt`). |
| `--player-body off` | | No body: the game stays in first person (Tab says why). |
| `--death-retry on` | on | The death question offers "Retry fight" after a lost fight. |
| `--death-retry off` | | Only the original's choices (`aw_death_retry 0` in the game defaults). |

The camera settings (`id1/view/settings.txt`: `fVanityDelay`, `sLoadLastSaveMsg`, `sYes`, `sNo`) are
always written from the owned master.
