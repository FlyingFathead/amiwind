# Third person, vanity camera and the death scene

_Last updated with AmiWind v0.0.67-dev2 (18 November 2026)._

<!-- contents start -->
## Contents

- [Keys](#keys)
- [The death scene](#the-death-scene)
  - [While dead](#while-dead)
- [Sources](#sources)
- [The player's body](#the-players-body)
- [The assembled body](#the-assembled-body)
  - [The drawn weapon's stance (v0.0.61)](#the-drawn-weapons-stance-v0061)
  - [The inventory picture](#the-inventory-picture)
- [First-person arms](#first-person-arms)
  - [The first-person view](#the-first-person-view)
  - [What the hands hold in first person](#what-the-hands-hold-in-first-person)
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
| (no input for a while) | The vanity camera: after `fVanityDelay` seconds (the game's own setting, 30 in Morrowind) the camera turns slowly around the character, 3 degrees a second, until any key, mouse movement or movement. While it orbits, the view fills the whole screen with nothing over it: no stat bars, compass, names, prompts or subtitles, as the original hides its interface in the vanity camera. Any input ends the orbit and brings the interface and the normal view size back. `aw_vanity_fullview 0` (saved) keeps the orbit inside the normal interface. A turn the game makes while the orbit runs (a script turning the character, an arrival's facing, the check commands `aw_view` and `aw_aim`) is the character's new heading: the orbit ends there and the view keeps it, as OpenMW's camera takes the character's own rotation when it leaves an orbit (it went back to where the orbit began, VIEW-VANITY-UNDOES-SET-VIEW-67). |

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
death, the hand-to-hand ready sections and, since v0.0.61, swimming: the original's `idleswim` and
`swimwalkforward` from the same shared table), so a swimming player wears what is worn, not the baked swimmer's
starting clothes.

A changed outfit loads its parts over several frames; since v0.0.61-dev3 the inventory picture waits for them (at most
5 seconds) and is drawn once, so a cuirass, a robe or trousers put on or taken off show in the window and on the body
at once. A held candle, candlestick or lantern is drawn on the left hand with its own model and flames, and the left
arm takes the light's pose ([INVENTORY.md](INVENTORY.md), "World models"); the light is not in the inventory picture.

The baked body stays selectable (`aw_player_body_parts 0`, saved, or `dbg camera parts off`), and it is still the
body while a torch is carried (its own baked pose), and while swimming in an image whose layout has no swim groups.
Not yet on the assembled body: the
draw/lower and punch arm layers of the bare hands and the torch pose.

### The drawn weapon's stance (v0.0.61)

With a weapon drawn, the assembled body plays the original's groups for that kind of weapon from the shared table,
the same groups and the same choice the residents use (OpenMW 0.51 `character.cpp` and `weapontype.cpp`):

| What the player does | Group played |
| --- | --- |
| Draws the weapon | the weapon's group from `equip start` to `equip stop` |
| Puts it away | `unequip start` to `unequip stop` |
| Swings | the weapon's `chop`, `slash` or `thrust` from its start to its large follow-through (the same attack the strike uses: by the movement at the swing's start, or the best attack) |
| Stands, walks, runs (forward, back, left, right) | the stance's own set: `idle1h`, `walkforward2c`, `runleft2w` ... |
| Jumps | `jump1h`, `jump2c`, `jump2w` |

The weapon groups by type: short blades, one-handed long blades, blunt weapons and axes play the one-handed set
(`weapononehand`, `1h`); two-handed long blades, blunt weapons and axes the two-handed close set (`weapontwohand`,
`2c`); staffs, warhammers and spears the two-handed wide set (`weapontwowide`, `2w`). The draw, the swing and the
putting away follow the first-person hand clock, so both views and the strike's hit key stay together. A raised
shield still plays the shield's block, and swimming, a carried torch and the bare hands keep the body's own poses.

Nothing new is loaded for it: the groups are in the table the body already uses, and a group is looked up by name
only when what the player does changes. `aw_player_stances 0` (saved, or `dbg camera stances off`) gives the previous
way: the body's own poses with the weapon on the hand bone. `dbg camera` shows the group playing.

**The body is kept in memory** (`aw_player_cache 1`, the default, in the game's default settings). Its parts
load over several frames, at most 40 ms of loading in one frame, and then stay in memory: the model cache never
evicts them to make room. A change of what is worn loads only the changed part. The first-person arms' parts are
kept the same way. `aw_player_cache 0` gives the previous way (every part in the frame that first needs the body,
the parts free to be evicted) for a comparison on the same image. The console says what each assembly cost:
"Assembled player body: 21 parts, N file lookups, T ms over F frames (K KB kept)".

Measured on 3 November 2026 (v0.0.59-dev6 image, FS-UAE, JIT, 68040, 32 MB Fast RAM, Seyda Neen):

| | Previous way (dev5, dev6 engines) | Kept body |
|---|---|---|
| First frame after arriving | 12.2 to 15.3 s (the parts, the script file's journal names, the actor rows) | about 1.0 s |
| Body assembly | all 21 parts inside that frame | 1.6 s of loading spread over 21 frames |
| Reload of the parts later in play | one frame of 4.2 to 5.6 s | none |
| Wearing a cuirass | (not measured) | 1 part loaded, 50 ms over 2 frames |
| Memory kept | none | 281 KB (body and arms) |

### The inventory picture

Since v0.0.59 the character picture in the inventory window draws the same assembled body: the parts of what the
player wears (the same recipe and the same worn items as the third-person view, assembled again only when one of
them changes), posed at the start of the original's inventory pose for the weapon in the right hand (the
`inventory...` groups of the shared table: hand to hand, short blade, one- and two-handed, blunt, two-handed wide),
with the weapon and shield on the table's item bones. Equipping or taking off an item in the window redraws the
picture once; every other frame copies the kept picture, as before. A two-handed weapon hides the shield, as in the
original (OpenMW `characterpreview.cpp` `InventoryPreview::update` picks the pose; the rule is the one the baked
poses used).

The picture follows the body's switch: with `aw_player_body_parts 0` (or `dbg camera parts off`) it draws the
previous picture, the race's baked inventory companion (`progs/body/*_i.mdl`) in its own starting outfit. A carried
torch keeps its torch body in the picture in both. The baked companions therefore stay in the image: they are the
picture with the baked body, and whenever the parts cannot be assembled (an image without `view/parts.txt`, or a
table without the inventory groups).

## First-person arms

Since v0.0.59 the first-person arms are, by default, put together from the same kind of parts: the race's own hand,
wrist, forearm and upper-arm parts, and over them the parts the worn gloves, gauntlets, bracers, shirt sleeves and
cuirasses give those slots, by the same priority as the body. Where the game has a first-person version of a part (a
record of the same name ending in `.1st`: the race's hands, the gloves and most gauntlets), that version is used, as
the original does (the rule OpenMW follows in `npcanimation.cpp`). A robe shows its own first-person sleeves (its
`.1st` chest record) and covers the arms under them; a robe without one leaves the arms as they are. Changing gloves
or gauntlets in the inventory changes the hands at once. The drawn weapon is held in the same stances as before.

The whole player body, first and third person, per race and sex: [PLAYER_BODY.md](PLAYER_BODY.md).

**Every race and sex has its own first-person hands (v0.0.67).** Decided for the project on 18 November 2026, a
deliberate departure from the original's data, which OpenMW follows (it draws the mesh a record names as it is): four
of the game's first-person hand records (Morrowind.esm; Tribunal and Bloodmoon do not change them) name another race's
or sex's mesh, whose textures are that one's skin:

| Race and sex | Record | Mesh it names | Drawn instead (the game's own, used by no record) |
| --- | --- | --- | --- |
| Nord man | `b_n_nord_m_hands.1st` | `b\B_N_Imperial_M_Hands.1st.nif` (`TX_B_N_Imperial_M_Hfinger`, `_Hthumb`, `_Hpalm`) | `b\b_n_nord_m_hands.1st.nif` (`TX_B_N_Nord_M_Hfinger`, `_Hthumb`, `_Hpalm`) |
| Imperial woman | `b_n_imperial_f_hands.1st` | `b\B_N_Nord_F_Hands.1st.nif` (`TX_B_N_Nord_F_H...`) | `b\b_n_imperial_f_hands.1st.nif` (`TX_B_N_Imperial_F_H...`) |
| Dark Elf man | `b_n_dark elf_m_hand.1st` | `b\B_N_Dark Elf_F_Hands.1st.NIF` (`TX_B_N_Dark Elf_F_H...`) | `b\b_n_dark elf_m_hands.1st.nif` (`TX_B_N_Dark Elf_M_H...`) |
| Redguard man | `b_n_redguard_m_hands.1st` | `b\B_N_Redguard_F_Hands.1st.nif` (`TX_B_N_Redguard_F_H...`) | `b\b_n_redguard_m_hands.1st.nif` (`TX_B_N_Redguard_M_H...`) |

The own meshes have the same 580 triangles as the ones named. The rule is general (`tools/player_own_skin.py`
`own_hand_mesh`: a hand record whose mesh's file name says another race or sex takes the race's and sex's own
first-person hand mesh when the game has it) and on the game's data it changes exactly those four; every first-person
path takes it (the arms from parts, the baked hands, the carried torch's arms and the shield guard's arms). Every other
part is the race's own record by the original's order (the sex's first-person part, then its third-person one, then for
a woman the man's: the Argonian woman's forearm is the man's, the game has no other).

**No steep colour step at the seams of the arm.** In first person the hand meets the wrist part (slots 8 and 9) and
the wrist meets the forearm, and a part's colour where it meets the next is not its whole colour. Measured as drawn
(the skin texels of each part's triangles at its vertices within 0.75 units of the other part, on the game palette),
the step where the hand meets the wrist was up to 54.9 per channel on the v0.0.67-dev2 image (the Nord man), and the
game's own wrist and forearm parts step by up to 36.6 (the Khajiit man). The image step now tints, along each arm of
every race and sex, the wrist to the forearm at their seam and then the hand to the wrist as it now draws (a factor per
channel, measured, at most four bakes, the best kept), aiming within 8 (one step of the palette's skin colours), and
stops the image when a seam is left more than 16 off or a hand is another race's or sex's (`player-fp-parts.json`
"seam_gaps", "own_hand_meshes"). Every race's and sex's records, meshes, textures and measured seams:
[FP-HANDS-PER-RACE-67](bugs/FP-HANDS-PER-RACE-67.md). Tests: `tests/test_fp_hands_per_race.py`,
`tests/test_fp_bare_hand_skin.py`.

Switches (in the source, the shipped default first): `tools/player_own_skin.py` `OWN_HAND_MESHES` (True; False = the
records' meshes as the game names them); `tools/prepare_player_fp_parts.py` `SEAM_MATCH` ('seams'; 'forearm' = the
first v0.0.67 method, each hand tinted to its forearm's whole colour; 'off' = no tint, the seams only reported) and
`OWN_SKIN` (True: a hand of another race's or sex's textures takes the race's own). The original's look: `SEAM_MATCH`
'off', `OWN_SKIN` False and `OWN_HAND_MESHES` False.

**Part models are released when they leave.** On a race, sex or outfit change the part models the new body and arms
no longer draw are released at once (their slots in the engine's model table freed), and `dbg race` releases both sets
at the swap. Before, they were only unpinned and kept their slots; after a few race or outfit changes in one place the
first-person arm parts found no slot and the arms fell back to an old hand model without the held light
(FP-ARMS-NO-MODEL-SLOT-67). `dbg camera` prints the model table by number ("Model table: N slots in use of M known, P of
them player parts").

### The first-person view

Since v0.0.61 the arms, the drawn weapon, the torch, a held light and their flames are drawn as the original draws
its first-person model (OpenMW 0.51 `npcanimation.cpp`), `aw_fp_view 1` (the default, saved):

- with their own field of view, 60 degrees high (OpenMW's "first person field of view"; `OverrideFieldOfViewCallback`),
  whatever the world's: the world's fov 90 across a view 2.1 times as wide as high is only about 51 degrees high, and
  drawn with it the arms were larger and only the hands reached into the bottom edge. Only the projection's scale
  changes (one tangent a frame); the centre, the clipping and the depth stay the world's;
- turned by 0.75 of the view's pitch (OpenMW's first-person neck, `runAnimation`; the skeleton's Camera rides Bip01
  Head on Bip01 Neck, so seen from the eye the arms turn a quarter of the pitch the other way): looking down they rise
  into the view with the forearms and the sleeves, looking up they sink. The eye and the aim do not change.

`aw_fp_view 0` (or `dbg camera fpview off`) keeps the previous method: the world's projection and the arms following
the whole pitch. Reference frames of OpenMW 0.51 at the same poses (first person, shirt and robe, fists and a dagger,
level and 45 degrees down) were taken for the comparison. With the fists raised and the view looking down the forearms
show, and a worn shirt's or robe's sleeves cover them. A lantern hangs below the hand, so in first person only its
handle shows. Not yet seen in game: the glass lantern in first person, a still in the middle of a swing, and the frame
times of this view on the Raspberry Pi 4B. Register: FP-FOREARMS-BELOW-VIEW-61 ([BUGS.md](BUGS.md)).
Tests: `tests/aga_viewmodel_bob_test.c`.

### What the hands hold in first person

Since v0.0.67 every held item in first person has one placement, the original's: the item on its own hand's bone of
the first-person arms it is drawn with (the drawn weapon on the right hand's Weapon Bone, a carried light on the left
hand's Shield Bone, OpenMW 0.51 `npcanimation.cpp`), at the frame drawn, then the item's own carried place on the bone
(a light's turn and offset, the same numbers third person uses), and nothing else. The left arm holding a light plays
the original's first-person `torch` group (the raised arm and the fingers round the handle). From v0.0.61 to
v0.0.67-dev2 a carried light was also moved 4 units forward along the view, which the arms it rides were not: its grip
sat 4 units from the hand (on the v0.0.67-dev2 image the torch's nearest point 4.2 units from the hand, the glass
lantern's 3.2, a candle's 1.9; now 1.7, 0.1 and 0.1, as in third person). The drawn weapon's place is the same as
before (its earlier tags agree with its bone within 0.05 units). In the normal view the hand holding a light sits below
the screen's lower edge; it shows looking down. Register: FP-TORCH-OUT-OF-HAND-67 ([BUGS.md](BUGS.md)). Tests:
`tests/test_fp_held_item.py`, `tests/aga_held_item_test.c`.

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
while a torch is carried and while the shield is raised to guard (their own baked poses). While magic is ready the
torch, a held light and the shield are put away and both paths show the open hands of the spell stance, whatever is
equipped; the third-person body puts them away too (since v0.0.66-dev2; [MAGIC_EFFECTS.md](MAGIC_EFFECTS.md)).

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
| `dbg camera stances on/off` | The drawn weapon's stance on the assembled body (on, the default) or the body's own poses (off); `aw_player_stances`, saved. |
| `dbg camera fpview on/off` | The original's first-person view (on, the default: the arms, weapon and held light with their own 60-degree field of view, lagging the pitch) or the world's projection with the arms following the whole pitch (off, the previous method); `aw_fp_view`, saved. `dbg camera` shows it with the view's and the arms' pitch. |
| `dbg camera hands on/off` | The first-person arms assembled from what is worn (on, the default) or the baked arms (off); `aw_hand_parts`, saved. `dbg camera` lists the arms' parts, their frame and the last assembly's time. |
| `dbg camera motion restart on/off` | The restart of the body's animation on camera and control changes (on, the default); off is the earlier way, for a before/after comparison (not saved). |
| `dbg camera die` | Test the death scene: the player dies as from world damage (like lava). |

`dbg setpov`, the view locked for test pictures and checks:

| Command | What it does |
| --- | --- |
| `dbg setpov 1` (or `first`) | First person, locked. |
| `dbg setpov 2` (or `vanity`) | The vanity camera circling the player, locked. |
| `dbg setpov 3` (or `third`) | Third person, locked. |
| `dbg setpov off` | Unlocks it; the view rules apply again (the idle vanity camera after its delay, Toggle POV, the wheel). |
| `dbg setpov` | The current view by its number (1 first, 2 vanity, 3 third; 0 another, such as the death camera) and whether it is locked. |

Each setting says so on the screen and in the console ("POV locked: first person (setpov 1)", "POV unlocked: ...").
While the view is locked the idle vanity camera never starts, and Toggle POV, the wheel, `dbg camera first/third/
toggle` and `dbg camera vanity now` do not change it (the console says it is locked). Every test session and look book
page locks the view before its pictures and reads it back with `dbg setpov`. Tests: `tests/test_setpov.py`,
`tests/aga_view_lock_test.c`.

`dbg race`, the player's race and sex swapped in place, for checks of the body and the first-person arms of every race
(DBG-RACE-SWAP-67):

| Command | What it does |
| --- | --- |
| `dbg race` | The playable races with their numbers, and the current race and sex. |
| `dbg race 5` or `dbg race khajiit` | Swaps the race (by its number in the list or its name, `dark elf` or `darkelf`). |
| `dbg race f`, `dbg race nord m` | Swaps the sex, or both. |

Stats, class, birthsign, name and level stay; a valid head and hair are chosen. The game's rules for the new race apply
at once: what it cannot wear (a beast race: nothing over the head, nothing on the feet) goes back into the inventory,
one console line per item. The old race's body and first-person arm parts are released at once ("Player parts
released: model table N slots in use ... before, M after") and both are assembled again; one line reads the result back
("Player race: 5: Khajiit, sex f, a beast race ..."). It is a debug command: a save made after it keeps the swap.

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

The body's animation after a camera or control change (v0.0.67): the body's walk, run, jump and landing clocks, the
drawn weapon's stance and the turn on the spot start again whenever the view mode changes (first or third person,
the Toggle POV orbit, the vanity orbit in and out, the death camera), noclip goes on or off, the player goes into or
out of the water, a menu, the dialogue window or the console comes over play or goes, or the body starts or stops
being drawn, the same way a new map starts them. Before, after an idle vanity orbit the walk and run could stay
stuck in third person (the body glided in its standing pose) until the next map load. `dbg camera` shows the body's
motion: its speed, whether it stands on the ground, the jump or landing state, how often its move group and its air
state changed in the last second (walking, a few times at most; a group started again every frame shows as one
change a frame) and the restarts with the last one's cause.

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
