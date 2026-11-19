# SPDX-License-Identifier: GPL-3.0-only
"""The player's own skin parts: every race and sex draws its own hand (and its own skin part wherever a record names
another race's or sex's mesh), FP-HANDS-PER-RACE-67.

Decided for the project, 2026-11-18: every race and sex draws its own first-person hand. Four of the game's
first-person hand records (Morrowind.esm; Tribunal and Bloodmoon do not change them) name another race's or sex's mesh,
whose textures are that one's skin:
  b_n_nord_m_hands.1st      -> b\\B_N_Imperial_M_Hands.1st.nif   (the Nord man draws the Imperial man's hand)
  b_n_imperial_f_hands.1st  -> b\\B_N_Nord_F_Hands.1st.nif       (the Imperial woman the Nord woman's)
  b_n_dark elf_m_hand.1st   -> b\\B_N_Dark Elf_F_Hands.1st.NIF   (the Dark Elf man the woman's)
  b_n_redguard_m_hands.1st  -> b\\B_N_Redguard_F_Hands.1st.nif   (the Redguard man the woman's)
The game's archive holds each one's own first-person hand mesh, used by no record: b\\b_n_nord_m_hands.1st.nif,
b\\b_n_imperial_f_hands.1st.nif, b\\b_n_dark elf_m_hands.1st.nif, b\\b_n_redguard_m_hands.1st.nif (the same 580
triangles as the meshes named, the race's and sex's own TX_B_N_<Race>_<M|F>_Hfinger, _Hthumb and _Hpalm). OpenMW 0.51
draws the mesh a record names as it is (npcanimation.cpp), so the original's look is the other race's hand; this is a
deliberate departure from the original's data: a skin record whose mesh names another race or sex takes the race's
and sex's own mesh of the same part when the game has it. The rule is general; on the game's data it changes exactly
those four in first person and the High Elf man's upper legs in third person (b_n_high elf_m_upper leg names
b\\B_N_High Elf_F_Upper Leg.nif; tools/prepare_player_parts.py own_skin_mesh) (tests/test_fp_hands_per_race.py).
OWN_HAND_MESHES False = the records' meshes as the game names them.

Its own module, imported by the functions that use it (prepare_hands.appearance_parts, prepare_player_parts
own_skin_mesh / foreign_skin_parts / prepare, prepare_player_fp_parts check_own_hands / prepare), never at the top of
tools/prepare_hands.py: the NPC bakes import that module for its stance tables, so its import-time code is part of the
resident-bake, guard-torch-skip and player-view unit keys, and these lines there re-keyed all 2,323 stored residents
although no NPC runs them (UNIT-KEY-WHOLE-FILE-63, seen again 2026-11-18).
"""
import re

OWN_HAND_MESHES = True
# a first-person hand's mesh by the game's naming, b_n_<race>_<m|f>_hand(s).1st.nif
HAND_MESH_NAME = re.compile(r'^b_n_(?P<race>[a-z ]+?)_(?P<sex>[mf])_hands?\.1st\.nif$')
# any skin part's mesh by the game's naming, b_n_<race>_<m|f>_<part>.nif (the hands, wrists, forearms, upper arms)
SKIN_MESH_NAME = re.compile(r'^b_n_(?P<race>[a-z ]+?)_(?P<sex>[mf])_(?P<rest>[a-z0-9 .]+\.nif)$')
# BYDT (part, vampire, flags, type) as OpenMW reads it (components/esm3/loadbody.hpp): part 1 is a hair (MP_Hair), type
# 0 a skin part (MT_Skin; 1 clothing, 2 armour)
HAIR_PART = 1
SKIN_TYPE = 0


def race_key(race):
    """A race as the game's file names write it, read with or without its space: 'Dark Elf', 'dark elf' and the
    expansions' 'DarkElf' (Tribunal: b\\B_N_DarkElf_F_BarenziahH.NIF) are one race, 'darkelf'."""
    return str(race or '').replace(' ', '').casefold()


def rule_covers(bydt):
    """True for a body part record the rule covers (its BYDT): a race's skin part, not a vampire's, not a hair. A hair
    (and every clothing or armour part) stays as the game names it: a hair naming another race's hair or accessory art
    is the game's shared art, as decided (Tribunal's Barenziah and Helseth hairs write their race without its space),
    so it is neither replaced nor called another race's (PLAYER-PARTS-HAIR-FALSE-STOP-67)."""
    return bool(bydt) and len(bydt) >= 4 and bydt[3] == SKIN_TYPE and not bydt[1] and bydt[0] != HAIR_PART


def names_other(name, race, female):
    """True when NAME (a match of SKIN_MESH_NAME or HAND_MESH_NAME) says another race (race_key) or sex than RACE,
    FEMALE."""
    return (race_key(name.group('race')), name.group('sex')) != (race_key(race), 'f' if female else 'm')


def own_hand_mesh(mesh, race, female, assets):
    """The race's and sex's own mesh of the same part (b\\b_n_<race>_<m|f>_<part>.nif) in place of MESH, a skin record's
    mesh whose file name says another race or sex than the record's own (RACE, FEMALE: the record's; the race read
    with or without its space, race_key), when ASSETS (npc_geometry.Assets) has it; MESH otherwise (a name that says
    nothing, its own already, OWN_HAND_MESHES off or no ASSETS given). On the game's data it changes the four
    first-person hands named above. The caller decides which records it covers (rule_covers)."""
    if not OWN_HAND_MESHES or assets is None or not mesh:
        return mesh
    m = SKIN_MESH_NAME.match(str(mesh).replace('\\', '/').rsplit('/', 1)[-1].casefold())
    sex = 'f' if female else 'm'
    if not m or not names_other(m, race, female):
        return mesh
    own = 'b\\b_n_%s_%s_%s' % (race, sex, m.group('rest'))
    try:
        assets.read('meshes/' + own.replace('\\', '/'))
    except KeyError:
        return mesh
    return own
