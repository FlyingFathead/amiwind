# FP-HANDS-PER-RACE-67: In first person four races and sexes show another race's or sex's hand, and the skin steps at the wrist

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 18 November 2026, in v0.0.67-dev2 |
| Where | first-person view, the bare hands (no gloves worn): the four race and sex choices named, and the colour step where the hand meets the wrist for several more |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.67-dev2 (last seen) |
| Severity | high: the player's own hands look like another race's in every scene for four of the twenty race and sex choices, and a steep colour step shows at the wrist for several more |
| Family | First-person hands and torch (`torch-hands`) |
| Playtest version | v0.0.67-dev2 |
| From commit | source unknown, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM 0.2.2, engine unknown, world format 0.11 |
| Unknown because | the build receipt does not record source commit, engine commit, world commit |
| Platform or emulator | FS-UAE 3.1.66, JIT, A1200 68040, 32 MB Fast (the light test corridor sessions) |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Closure steps (how this bug was closed, [the schema](README.md#closure)):

| Stage | Who | Where | When | How | Why |
| --- | --- | --- | --- | --- | --- |
| fixed in source | a gated commit | v0.0.67-dev2 (f1a962c2) | 2026-11-18 | gate 11741 (8662 tests, smoke pass); tests/test_fp_hands_per_race.py | commit 8308ba5a on branch v0.0.67-fpfist: the four first-person hand records that name another race's or sex's mesh draw the race's own (b\b_n_nord_m_hands.1st.nif, b\b_n_imperial_f_hands.1st.nif, b\b_n_dark elf_m_hands.1st.nif, b\b_n_redguard_m_hands.1st.nif) and the High Elf man's upper legs his own (b\b_n_high elf_m_upper leg.nif), in every first-person path and in the third-person body; the image step stops on a part of another race or sex |

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-11-18: reported in v0.0.67-dev2
- 2026-11-18: fixed in source: a gated commit, v0.0.67-dev2 (f1a962c2); gate 11741 (8662 tests, smoke pass); tests/test_fp_hands_per_race.py: commit 8308ba5a on branch v0.0.67-fpfist: the four first-person hand records that name another race's or sex's mesh draw the race's own (b\b_n_nord_m_hands.1st.nif, b\b_n_imperial_f_hands.1st.nif, b\b_n_dark elf_m_hands.1st.nif ...
- 2026-11-18 22:15 +0200: v0.0.67-dev2: In third person, read over the whole body of every race and sex (668 parts, heads and hairs): the High Elf man's upper legs, record b_n_high elf_m_upper leg, name the woman's mesh b\B_N_High Elf_F_Upper Leg.nif (TX_B_N_High Elf_F_UL); the ...

<!-- END GENERATED TIMELINE -->

_Last updated with AmiWind v0.0.67-dev2 (18 November 2026)._

<!-- contents start -->
## Contents

- [Timeline](#timeline)
- [Status: 18 November 2026](#status-18-november-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 18 November 2026

Open. Present in v0.0.67-dev2 and every earlier image with first-person arms. Decided for the project on 18 November
2026: every race and sex draws its own first-person hand, assembled from its own parts through the existing
first-person parts pipeline (`tools/prepare_hands.py` `appearance_parts`, `tools/prepare_player_fp_parts.py`), and no
steep colour step shows at any seam of the arm, whatever the race. This is a deliberate departure from the original's
data, which OpenMW follows (see "How it happened").

## Symptom

In first person with bare hands (no gloves), the hand of the Nord man looks darker and of another tone than his
forearm, like a glove, with a sharp colour change at both wrists; the same with the starter shirt on or off (its
sleeves end above the elbow). Third person looks right. The same kind of step shows at the wrist for several other
races and sexes (the table below).

## Where

The first-person arms from parts: the race's hand, wrist, forearm and upper-arm skin parts (slots 6 and 7, 8 and 9,
11 and 12, 13 and 14) that the image step bakes into `progs/parts/` and lists in `view/parts_1st.txt`, drawn by
`engine/aga/src/aw_view.c` (`hand_parts_ready`, `hand_parts_apply`, `hand_part`). Not affected: gloves, gauntlets and
sleeves (their own parts); third person (its own part list, `view/parts.txt`, takes the race's third-person hand,
which names the race's own skin).

## How it happened

**The part each slot draws.** The first-person rule takes only the race's own records (the record's race is the
race, a skin part, not a vampire's): for each body part the sex's first-person (`.1st`) record, then its third-person
one, then for a woman the man's first-person and third-person ones. OpenMW 0.51 uses the same order
(`apps/openmw/mwrender/npcanimation.cpp`, the arm fallbacks in first person) and draws the mesh the record names as it
is. The game has first-person records only for hands, so the wrists, forearms and upper arms are the third-person
parts. The one fallback is the Argonian woman's forearm, the man's (`b_n_argonian_m_forearm`): the game has no other.

**Four hand records name another race's or sex's mesh.** Read from the game files (Morrowind.esm; Tribunal and
Bloodmoon do not change them):

| Race and sex | Record | Mesh it names | Textures that mesh names | The race's own mesh (in the game's archive, used by no record) | Its textures |
| --- | --- | --- | --- | --- | --- |
| Nord man | `b_n_nord_m_hands.1st` | `b\B_N_Imperial_M_Hands.1st.nif` | `TX_B_N_Imperial_M_Hfinger`, `_Hthumb`, `_Hpalm` (mean 145 96 76, 146 97 76, 151 100 78) | `b\b_n_nord_m_hands.1st.nif` | `TX_B_N_Nord_M_Hfinger`, `_Hthumb`, `_Hpalm` (199 149 125, 195 145 121, 206 156 132) |
| Imperial woman | `b_n_imperial_f_hands.1st` | `b\B_N_Nord_F_Hands.1st.nif` | `TX_B_N_Nord_F_Hfinger`, `_Hthumb`, `_Hpalm` (190 151 123, 185 146 118, 201 156 130) | `b\b_n_imperial_f_hands.1st.nif` | `TX_B_N_Imperial_F_Hfinger`, `_Hthumb`, `_Hpalm` (164 121 98, 157 117 95, 165 124 101) |
| Dark Elf man | `b_n_dark elf_m_hand.1st` | `b\B_N_Dark Elf_F_Hands.1st.NIF` | `TX_B_N_Dark Elf_F_Hfinger`, `_Hthumb`, `_Hpalm` (96 113 103, 99 116 107, 107 126 115) | `b\b_n_dark elf_m_hands.1st.nif` | `TX_B_N_Dark Elf_M_Hfinger`, `_Hthumb`, `_Hpalm` (77 84 70, 81 87 74, 96 103 88) |
| Redguard man | `b_n_redguard_m_hands.1st` | `b\B_N_Redguard_F_Hands.1st.nif` | `TX_B_N_Redguard_F_Hfinger`, `_Hthumb`, `_Hpalm` (79 46 24, 73 42 22, 82 49 27) | `b\b_n_redguard_m_hands.1st.nif` | `TX_B_N_Redguard_M_Hfinger`, `_Hthumb`, `_Hpalm` (54 30 17, 54 31 18, 60 34 21) |

Each own mesh has the same geometry as the one the record names (580 triangles, 434 vertices).

**In third person, one more.** Read the same way over the whole third-person body of every race and sex (668 parts,
heads and hairs): the High Elf man's upper legs, record `b_n_high elf_m_upper leg`, name the woman's mesh
`b\B_N_High Elf_F_Upper Leg.nif` (`TX_B_N_High Elf_F_UL`); the game ships his own `b\b_n_high elf_m_upper leg.nif`,
used by no record. Decided the same way (the race's own part). Hair records that name another race's hair or
accessory textures (`TX_B_N_Dark Elf_M_hairpin00`, `TX_B_N_High Elf_M_hairwrap01`, two Wood Elf woman hairs) are the
game's shared art and stay as they are; the Argonian woman's forearms stay the man's (the rule's fallback).

**The parts of every race and sex** (the hand's textures are `TX_B_N_<Race>_<M|F>_Hfinger`, `_Hthumb` and `_Hpalm`;
the wrist and forearm share `TX_B_N_<Race>_<M|F>_LA`, the upper arm `TX_B_N_<Race>_<M|F>_UA`, of the record's own race
and sex unless named):

| Race and sex | Hand record and mesh | Wrist | Forearm | Upper arm |
| --- | --- | --- | --- | --- |
| Argonian man | `b_n_argonian_m_hands.1st`, `b\b_n_argonian_m_hands.1st.nif` | `b_n_argonian_m_wrist` | `b_n_argonian_m_forearm` | `b_n_argonian_m_upper arm` |
| Argonian woman | `b_n_argonian_f_hands.1st`, `b\b_n_argonian_f_hands.1st.nif` | `b_n_argonian_f_wrist` | `b_n_argonian_m_forearm` (the man's: `TX_B_N_Argonian_M_LA`) | `b_n_argonian_f_upper arm` |
| Breton man | `b_n_breton_m_hand.1st`, `b\B_N_Breton_M_Hand.1st.NIF` | `b_n_breton_m_wrist` | `b_n_breton_m_forearm` | `b_n_breton_m_upper arm` |
| Breton woman | `b_n_breton_f_hands.1st`, `b\B_N_Breton_F_Hands.1st.nif` | `b_n_breton_f_wrist` | `b_n_breton_f_forearm` | `b_n_breton_f_upper arm` |
| Dark Elf man | `b_n_dark elf_m_hand.1st`, `b\B_N_Dark Elf_F_Hands.1st.NIF` (the woman's) | `b_n_dark elf_m_wrist` | `b_n_dark elf_m_forearm` | `b_n_dark elf_m_upper arm` |
| Dark Elf woman | `b_n_dark elf_f_hand.1st`, `b\B_N_Dark Elf_F_Hands.1st.NIF` | `b_n_dark elf_f_wrist` | `b_n_dark elf_f_forearm` | `b_n_dark elf_f_upper arm` |
| High Elf man | `b_n_high elf_m_hand.1st`, `b\B_N_High Elf_M_Hands.1st.nif` | `b_n_high elf_m_wrist` | `b_n_high elf_m_forearm` | `b_n_high elf_m_upper arm` |
| High Elf woman | `b_n_high elf_f_hands.1st`, `b\B_N_High Elf_F_Hands.1st.nif` | `b_n_high elf_f_wrist` | `b_n_high elf_f_forearm` | `b_n_high elf_f_upper arm` |
| Imperial man | `b_n_imperial_m_hands.1st`, `b\B_N_Imperial_M_Hands.1st.nif` | `b_n_imperial_m_wrist` | `b_n_imperial_m_forearm` | `b_n_imperial_m_upper arm` |
| Imperial woman | `b_n_imperial_f_hands.1st`, `b\B_N_Nord_F_Hands.1st.nif` (the Nord woman's) | `b_n_imperial_f_wrist` | `b_n_imperial_f_forearm` | `b_n_imperial_f_upper arm` |
| Khajiit man | `b_n_khajiit_m_hands.1st`, `b\b_n_khajiit_m_hands.1st.nif` | `b_n_khajiit_m_wrist` | `b_n_khajiit_m_forearm` | `b_n_khajiit_m_upper arm` |
| Khajiit woman | `b_n_khajiit_f_hands.1st`, `b\b_n_khajiit_f_hands.1st.nif` | `b_n_khajiit_f_wrist` | `b_n_khajiit_f_forearm` | `b_n_khajiit_f_upper arm` |
| Nord man | `b_n_nord_m_hands.1st`, `b\B_N_Imperial_M_Hands.1st.nif` (the Imperial man's) | `b_n_nord_m_wrist` | `b_n_nord_m_forearm` | `b_n_nord_m_upper arm` |
| Nord woman | `b_n_nord_f_hands.1st`, `b\B_N_Nord_F_Hands.1st.nif` | `b_n_nord_f_wrist` | `b_n_nord_f_forearm` | `b_n_nord_f_upper arm` |
| Orc man | `b_n_orc_m_hands.1st`, `b\B_N_Orc_M_Hands.1st.nif` | `b_n_orc_m_wrist` | `b_n_orc_m_forearm` | `b_n_orc_m_upper arm` |
| Orc woman | `b_n_orc_f_hands.1st`, `b\B_N_Orc_F_Hands.1st.nif` | `b_n_orc_f_wrist` | `b_n_orc_f_forearm` | `b_n_orc_f_upper arm` |
| Redguard man | `b_n_redguard_m_hands.1st`, `b\B_N_Redguard_F_Hands.1st.nif` (the woman's) | `b_n_redguard_m_wrist` | `b_n_redguard_m_forearm` | `b_n_redguard_m_upper arm` |
| Redguard woman | `b_n_redguard_f_hands.1st`, `b\B_N_Redguard_F_Hands.1st.nif` | `b_n_redguard_f_wrist` | `b_n_redguard_f_forearm` | `b_n_redguard_f_upper arm` |
| Wood Elf man | `b_n_wood elf_m_hands.1st`, `b\B_N_Wood Elf_M_Hands.1st.nif` | `b_n_wood elf_m_wrist` | `b_n_wood elf_m_forearm` | `b_n_wood elf_m_upper arm` |
| Wood Elf woman | `b_n_wood elf_f_hands.1st`, `b\B_N_Wood Elf_F_Hands.1st.nif` | `b_n_wood elf_f_wrist` | `b_n_wood elf_f_forearm` | `b_n_wood elf_f_upper arm` |

**The step at each seam.** The hand meets the wrist part, the wrist the forearm. Measured as drawn: the mean colour
of the texels of each part's triangles at its vertices within 0.75 units of the other part, on the game palette, in
the bare hands' pose; the step is the largest channel difference of the two (0..255). Lighting is not a cause: every
first-person arm part is drawn with one light value for all its vertices. The parts meet without a gap (hand to wrist
closest 0.06 to 0.14 units, wrist to forearm 0.01 to 0.03, forearm to upper arm 0.06 to 0.17).

| Race and sex | Hand to wrist, v0.0.67-dev2 image | Hand to wrist, own hand textures (c1a11300) | Hand to wrist, c1a11300 with its tint | Wrist to forearm |
| --- | --- | --- | --- | --- |
| Argonian man | 36.1 / 37.8 | 36.1 / 37.8 | 8.7 / 10.4 | 13.7 |
| Argonian woman | 19.9 / 20.0 | 19.9 / 20.0 | 19.9 / 20.0 | 13.7 |
| Breton man | 12.3 / 11.9 | 12.3 / 11.9 | 12.3 / 11.9 | 1.0 |
| Breton woman | 7.1 / 7.0 | 7.1 / 7.0 | 7.1 / 7.0 | 1.6 |
| Dark Elf man | 31.9 / 31.4 | 10.0 / 9.2 | 10.0 / 9.2 | 9.8 |
| Dark Elf woman | 7.5 / 7.5 | 7.5 / 7.5 | 7.5 / 7.5 | 4.2 |
| High Elf man | 5.5 / 5.5 | 5.5 / 5.5 | 5.5 / 5.5 | 19.5 |
| High Elf woman | 4.5 / 4.5 | 4.5 / 4.5 | 4.5 / 4.5 | 3.7 |
| Imperial man | 3.7 / 3.7 | 3.7 / 3.7 | 3.7 / 3.7 | 2.5 |
| Imperial woman | 26.7 / 26.7 | 8.3 / 8.3 | 8.3 / 8.3 | 3.5 |
| Khajiit man | 33.0 / 32.6 | 33.0 / 32.6 | 28.9 / 29.8 | 36.6 |
| Khajiit woman | 22.3 / 20.0 | 22.3 / 20.0 | 40.2 / 38.2 | 12.0 |
| Nord man | 54.9 / 54.9 | 9.5 / 9.5 | 9.5 / 9.5 | 1.2 |
| Nord woman | 5.0 / 5.0 | 5.0 / 5.0 | 5.0 / 5.0 | 1.7 |
| Orc man | 15.0 / 15.0 | 15.0 / 15.0 | 15.0 / 15.0 | 9.8 |
| Orc woman | 10.4 / 10.4 | 10.4 / 10.4 | 10.4 / 10.4 | 0.9 |
| Redguard man | 26.4 / 26.6 | 7.1 / 7.1 | 7.1 / 7.1 | 0.8 |
| Redguard woman | 4.3 / 4.3 | 4.3 / 4.3 | 4.3 / 4.3 | 5.1 |
| Wood Elf man | 13.9 / 13.9 | 13.9 / 13.9 | 13.9 / 13.9 | 2.4 |
| Wood Elf woman | 28.4 / 28.4 | 28.4 / 28.4 | 8.7 / 8.7 | 3.3 |

Right / left hand. The v0.0.67-dev2 column is the image's own part models; the other columns are the same parts
baked again with the builder of commit c1a11300 (own hand textures for the four records above, then a tint of the
hand towards the forearm's whole mean colour).

## Why it was not caught

The first-person arms showed only the hands until v0.0.61 (the forearms were below the view, FP-FOREARMS-BELOW-VIEW-61),
so the wrist was not seen. The image step's colour check added with c1a11300 compared each hand's whole mean colour
with its forearm's whole mean (worst 15.6, under its limit 16), while in first person the hand meets the wrist part,
and the colour at the seam differs from the part's whole mean. No check read the colour at the seam.

## Reproduction

Any race and sex in the table with a step over about 8 (one step of the palette's skin colours): bare hands, first
person, raise the fists and look down at the wrists (the light test corridor, `dbg lighttest`, and photo mode with the
hands drawn). By data: `view/parts_1st.txt` of the image names, for the Nord man's hand slots, the same part models
as for the Imperial man's.

## Repair

In source on branch v0.0.67-fpfist (commits 8308ba5a and f1a962c2, gate 11741), not shipped at the time of writing.
`tools/player_own_skin.py` `own_hand_mesh`: a skin record whose mesh names another race or sex than the record's own
takes the own mesh of the same part when the game has it, in every first-person path and in the third-person body
(`tools/prepare_player_parts.py` `own_skin_mesh`); on the game's data the four hands above and the High Elf man's upper
legs; switch `OWN_HAND_MESHES`. `tools/prepare_player_fp_parts.py` `match_seams`: along each arm the wrist tinted to the
forearm at their seam, then the hand to the wrist, aiming within 8; switch `SEAM_MATCH` ('seams'). The whole account:
[PLAYER_BODY.md](../PLAYER_BODY.md).

The rule was first written at the top of `tools/prepare_hands.py` (f1a962c2). The NPC bakes import that module for its
stance tables, so its import-time code is part of the resident, guard torch and player view unit keys, and the build
check of f1a962c2 counted all 2,323 stored residents, the 6 guard torch verdicts and the 100 player view bodies as
changed although no NPC runs the rule (UNIT-KEY-WHOLE-FILE-63, seen again). The rule now has its own module, imported
only by the functions that use it; the three keys are again those of the v0.0.67-dev3 line (a411ea0 and 723effc9),
and the parts each race and sex draws are those of f1a962c2 (all 2,162 third-person and 464 first-person part units
the same, the High Elf man's upper legs and the four hands their own meshes).

## Verification

In source: `tests/test_fp_hands_per_race.py` (the four records and the rule, the seam measure and the chain match, the
own-hand and seam checks, and that the NPC bakes never reach the rule), gate 11741. Not verified yet: the image step's
per-race seam check and the light test corridor's every-race clips on an image built with the repair.

## Prevention

The image step stops when a first-person hand's mesh or textures are another race's or sex's, a third-person body part
is another race's or sex's, or a first-person seam step is over 16, naming the race, sex and seam
(`check_own_hands`, `foreign_skin_parts`, `check_seams`); `tests/test_fp_hands_per_race.py`.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: First-person hands and torch (`torch-hands`). First-person hands, punches and the carried torch. See [families](README.md#families).

- [AW-20260928-18](AW-20260928-18.md): Punch blocked after Census office exit
- [DEBUG-GALLERY-TIMING-29](DEBUG-GALLERY-TIMING-29.md): Hands unavailable in the combat and torch test rooms
- [DEBUG-TORCH-64](DEBUG-TORCH-64.md): The debug torch no longer lights with V: the console says no light is equipped
- FIRST-PERSON-BLOCK-ITEM-TABLE-59 (no report page): The first-person shield block refuses a shield whose model comes from the shared item model table
- [FIRST-PERSON-WEAPON-SETS-MISSING-54](FIRST-PERSON-WEAPON-SETS-MISSING-54.md): First-person hands have only 4 of the 103 original animation groups: no weapon stance or attack, spellcast, hit, swim or storm
- [FP-ARMS-CUT-62](FP-ARMS-CUT-62.md): In first person, looking down shows the forearms ending in mid-air, with no upper arms or shoulders behind them
- [FP-ARMS-LANTERN-NOT-DRAWN-HANDSIMAGE-67](FP-ARMS-LANTERN-NOT-DRAWN-HANDSIMAGE-67.md): On a test build of the per-race first-person hands, the first-person arms, the held lantern and its light are not drawn at all, looking ahead or down; the same walk on the earlier build showed the arm, the lantern and its light
- [FP-ARMS-NO-MODEL-SLOT-67](FP-ARMS-NO-MODEL-SLOT-67.md): After the race or sex is changed several times in one place, the first-person arms turn into an old hand model with holes and the held lantern is not drawn
- [FP-BARE-HAND-OTHER-SKIN-67](FP-BARE-HAND-OTHER-SKIN-67.md): In first person the bare hand of some races has another race's skin and looks gloved, unlike the arm
- [FP-FISTS-LUMP-67](FP-FISTS-LUMP-67.md): Drawing the fists in first person shows a lump in the top left corner of the view instead of the fists
- [FP-FOREARMS-BELOW-VIEW-61](FP-FOREARMS-BELOW-VIEW-61.md): In first person only the hands show: the forearms and the sleeves worn on them stay below the view
- [FP-WEAPON-SWAY-60](FP-WEAPON-SWAY-60.md): The weapon in first-person view moves more while walking than in the original
- HAND-IDLE-BLINK-29 (no report page): Fists disappear once per idle breathing cycle
- HAND-PUNCH-COVERAGE-29 (no report page): Near-plane opening at maximum punch extension
- [HAND-PUNCH-TRANSITION-29](HAND-PUNCH-TRANSITION-29.md): Hands briefly disappear when changing into the punch animation
- [HELD-LIGHT-ALWAYS-TORCH-61](HELD-LIGHT-ALWAYS-TORCH-61.md): Any carried light held in the hand is drawn and lit as a torch
- [HELD-LIGHT-NOT-IN-HAND-65](HELD-LIGHT-NOT-IN-HAND-65.md): An equipped candlestick is not held in the hand; readying shows only the fists
- [PLAYER-3P-HELD-ITEM-STALE-65](PLAYER-3P-HELD-ITEM-STALE-65.md): After a new weapon is given and readied, the third-person body still holds the light that was equipped before
- [PLAYER-BODY-LEG-SHAPE-39](PLAYER-BODY-LEG-SHAPE-39.md): Nord player legs appear abnormally thin in RC1
- [PLAYER-EQUIPMENT-NOT-WORN-54](PLAYER-EQUIPMENT-NOT-WORN-54.md): The player body shows no chosen head or hair, no worn clothing or armour and no weapon: it is baked per race and sex with fixed new-game looks
- [PLAYER-MOVEMENT-FRAME-SKIP-39](PLAYER-MOVEMENT-FRAME-SKIP-39.md): Third-person Nord and Khajiit fast movement loses smooth foot animation
- [PLAYER-PARTS-BAKE-REFUSED-59](PLAYER-PARTS-BAKE-REFUSED-59.md): Two body part meshes are refused by the assembled player body's parts library
- [PLAYER-PARTS-HAIR-FALSE-STOP-67](PLAYER-PARTS-HAIR-FALSE-STOP-67.md): The player-view stage stops on two of Tribunal's own Dark Elf hairs, calling them another race's part: their mesh names write the race without its space
- [PLAYER-PUNCH-THIRDPERSON-39](PLAYER-PUNCH-THIRDPERSON-39.md): Third-person punches have no visible player-body attack animation
- [PLAYER-READY-THIRDPERSON-38](PLAYER-READY-THIRDPERSON-38.md): Third-person player lacks fists-up and weapon-draw animation
- [PLAYER-TORCH-THIRDPERSON-38](PLAYER-TORCH-THIRDPERSON-38.md): Player torch and holding pose disappear in third person while light remains
- [TORCH-ACTIVATE-CRASH-25](TORCH-ACTIVATE-CRASH-25.md): Raising the fists and pressing V crashed the game: a dynamic light was marked through a negative collision root
- [TORCH-FLAME-VISIBILITY-29](TORCH-FLAME-VISIBILITY-29.md): Torch flame not visible after changing styles
- [TORCH-FUEL-29](TORCH-FUEL-29.md): Torch never burns out; no unlit or fuel state
- [TORCH-HAND-NORD-29](TORCH-HAND-NORD-29.md): Detached-looking left grip fragment in dev4
- [TORCH-HAND-SEPARATION-29](TORCH-HAND-SEPARATION-29.md): Torch grip and hand appear to break during idle and running
- [TORCH-HAND-TO-HAND-64](TORCH-HAND-TO-HAND-64.md): With a torch equipped the fists cannot fight, raising them brings the torch back and V cannot put it away
- [TORCH-INPUT-29](TORCH-INPUT-29.md): F cannot raise hands; V only prints torch state
- [TORCH-INVENTORY-PICTURE-64](TORCH-INVENTORY-PICTURE-64.md): Unequipping the torch in the inventory still shows a torch in the hand

<!-- END GENERATED CATEGORY -->
