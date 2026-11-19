# The player's body: parts per race and sex, first and third person

_Last updated with AmiWind v0.0.67-dev2 (19 November 2026)._

The player character is put together from the game's own body parts, the same way the modular NPCs are
([MODULAR_NPCS.md](MODULAR_NPCS.md)): for each of the twenty choices of race and sex, each body slot takes that race's
and sex's own part, and what is worn (clothing, armour, gloves, a robe) puts its parts over the slots it covers. This
page says which parts are taken, where AmiWind departs from the original's data on purpose, what is loaded and when it
is let go, and the checks that keep it so.

## The parts

| View | Slots | Built by | Drawn by |
| --- | --- | --- | --- |
| Third person (and the inventory picture) | 21 body parts: head, hair, neck, chest, groin, hands, wrists, forearms, upper arms, upper legs, knees, ankles, feet, and the tail of a beast race | `tools/prepare_player_parts.py` (`view/parts.txt`) | `engine/aga/src/aw_view.c` `parts_ready` |
| First person | 8 slots: both hands, wrists, forearms and upper arms | `tools/prepare_player_fp_parts.py` (`view/parts_1st.txt`) | `aw_view.c` `hand_parts_ready` ([THIRD_PERSON.md](THIRD_PERSON.md#first-person-arms)) |

Which record a slot takes follows the original's rule, as OpenMW reads it (`npcanimation.cpp`): only the race's own
records (the record's race is the player's race, a skin part, not a vampire's); for a woman her own record, and the
man's where the game has none for her. In first person the record of the same name ending in `.1st` comes first (the
game has them for the hands only). The one fallback on the game's data is the Argonian woman's forearms, which are the
man's (`b_n_argonian_m_forearm`): the game has no other.

## Where the original's data is not followed

Decided for the project on 18 November 2026: every race and sex is drawn with its own parts. Five of the game's records
(Morrowind.esm; Tribunal and Bloodmoon do not change them) name another race's or sex's mesh, whose textures are that
one's skin. The original and OpenMW draw the mesh a record names as it is; AmiWind draws the race's and sex's own mesh
of the same part, which the game ships and no record uses:

| View | Race and sex | Record | Mesh it names | Drawn instead |
| --- | --- | --- | --- | --- |
| First person | Nord man | `b_n_nord_m_hands.1st` | `b\B_N_Imperial_M_Hands.1st.nif` | `b\b_n_nord_m_hands.1st.nif` |
| First person | Imperial woman | `b_n_imperial_f_hands.1st` | `b\B_N_Nord_F_Hands.1st.nif` | `b\b_n_imperial_f_hands.1st.nif` |
| First person | Dark Elf man | `b_n_dark elf_m_hand.1st` | `b\B_N_Dark Elf_F_Hands.1st.NIF` | `b\b_n_dark elf_m_hands.1st.nif` |
| First person | Redguard man | `b_n_redguard_m_hands.1st` | `b\B_N_Redguard_F_Hands.1st.nif` | `b\b_n_redguard_m_hands.1st.nif` |
| Third person | High Elf man | `b_n_high elf_m_upper leg` | `b\B_N_High Elf_F_Upper Leg.nif` | `b\b_n_high elf_m_upper leg.nif` |

The rule is general (`tools/player_own_skin.py` `own_hand_mesh`: a skin record whose mesh's file name says another
race or sex than the record's own takes the own mesh of the same part when the game has it), applied to every
first-person path and to the third-person body; on the game's data it changes exactly these five. Switch:
`OWN_HAND_MESHES` in `tools/player_own_skin.py` (True; False draws the records' meshes as the game names them). The
rule has a module of its own, imported only by the player's part code: the NPC bakes read `tools/prepare_hands.py` for
its stance tables, so the rule written at the top of that module made every stored NPC bake count as changed although
no NPC runs it (UNIT-KEY-WHOLE-FILE-63; `tests/test_fp_hands_per_race.py` checks the NPC bakes never reach it).
Hair records that name another race's hair or accessory textures (hairpins, hair wraps) are the game's shared art and
are left as they are: hairs are outside the rule and outside its check (`rule_covers`). A race is read in a file name
with or without its space (`race_key`): Tribunal names the Dark Elf hairs of Barenziah and Helseth
`b\B_N_DarkElf_F_BarenziahH.NIF` and `b\B_N_DarkElf_M_HelsethHair.NIF`, which are the Dark Elf's own
(PLAYER-PARTS-HAIR-FALSE-STOP-67). With Tribunal and Bloodmoon selected, the departures are still exactly these five.
Every race's and sex's records, meshes and textures: [FP-HANDS-PER-RACE-67](bugs/FP-HANDS-PER-RACE-67.md).

## The colour at the seams

A hand, its wrist and its forearm are three parts, and their skins do not always meet in the same colour (on the
v0.0.67-dev2 image the step where the hand meets the wrist was up to 54.9 per colour channel, and the game's own wrist
and forearm parts step by up to 36.6 for the Khajiit man). In first person, where they are seen close, the image step
tints, along each arm of every race and sex, the wrist to the forearm at their seam and then the hand to the wrist, by
a measured factor per channel, aiming within 8 (one step of the palette's skin colours). Switch: `SEAM_MATCH` in
`tools/prepare_player_fp_parts.py` ('seams', the default; 'forearm', the first v0.0.67 method; 'off'). All parts are
lit with one light value, so what is measured in the skins is what is seen.

## What loads and what is let go

- **Assigned, present, loaded when drawn.** Every slot of every race and sex has its part in the image; a part is
  loaded when the body or the arms first draw it and kept while worn.
- **A race or sex swap** (`dbg race`, `dbg set race`, `aw_quickchar_set`, the character menus, New Game, a load)
  releases the old race's and sex's body and arm parts at once, in one place every such path passes (the body and the
  arms see the change when they are next drawn); both sets are then assembled for the new race and sex.
- **An outfit change** releases the parts the new body and arms no longer draw at once; parts the new outfit keeps stay
  loaded. Before v0.0.67 the old parts were only unpinned and kept their places in the engine's model table, and after
  a few changes in one place the first-person arms found no place left (FP-ARMS-NO-MODEL-SLOT-67).
- **Planned:** equipping clothing, armour or a weapon frees the replaced item's own models too, unless something else
  on screen still uses them (MODEL-TABLE-GC-67).

## Debug commands

| Command | What it does |
| --- | --- |
| `dbg race [N / NAME] [m / f]` | Swaps the race (its number in the list or its name) and sex in place; no argument lists the races. Stats, class and level stay; what the new race cannot wear (a beast race: nothing over the head or on the feet) goes back into the inventory; the model table is read back. A save keeps the swap. |
| `dbg set race ID / NAME` | Swaps the race only (the older command). |
| `dbg quickchar` | The character menus over the current scene. |
| `dbg camera` | Prints the parts drawn now and the model table ("Model table: N slots in use of M known, P of them player parts"). |

All console commands: [AMIWIND_CONSOLE_COMMANDS.md](AMIWIND_CONSOLE_COMMANDS.md).

## Checks and tests

- The image step stops when a player part (first or third person) is another race's or sex's, or when a seam of the
  first-person arm steps by more than 16 (`check_own_hands`, `check_seams`, `foreign_skin_parts`;
  `player-fp-parts.json` "own_hand_meshes", "seam_gaps").
- `tests/test_fp_hands_per_race.py`: the five records, the rule, the seam measure, the chain match, the checks, the
  release of old parts and `dbg race`; `tests/test_fp_bare_hand_skin.py`.
- Planned: an image-step check that every part file the part tables name is in the image.

Related: [THIRD_PERSON.md](THIRD_PERSON.md), [CHARACTER_EQUIPMENT_ROADMAP.md](CHARACTER_EQUIPMENT_ROADMAP.md),
[MEMORY_ALLOCATION.md](MEMORY_ALLOCATION.md).
