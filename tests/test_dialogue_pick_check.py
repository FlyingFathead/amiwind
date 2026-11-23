# SPDX-License-Identifier: GPL-3.0-only
"""The dialogue's answer choice by number (tools/dialogue_pick_check.py, DIALOGUE-PICK-CHECK-67): the answer the
dialogue table gives every NPC equals the answer the original's rule gives (an independent reading of OpenMW 0.51's
mwdialogue/filter.cpp), for every topic of a synthetic master that exercises each rule: actor, race, class, faction and
rank (named, none, rank without a faction), sex, the player's faction, the cell, every condition kind, the
disposition with the Info Refusal fallback, and the greeting from Greeting 0..9. The check also catches a filter that
breaks the original's rule (the rank without a faction that gave Hul and Heddvild the faction members' line). The same
tool runs on Morrowind.esm in the shell container (its counts in docs/DIALOGUE_FEATURES.md). Synthetic records; seconds."""
import struct
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / 'tests', ROOT / 'tools', ROOT / 'src'):     # src first (TEST-WORKER-SYSPATH-32)
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import dialogue_lut as D  # noqa: E402
import dialogue_pick_check as P  # noqa: E402
import greeting_lut as G  # noqa: E402
from test_greeting_lut import f, info, npc  # noqa: E402
import test_dialogue_lut as TD  # noqa: E402

MEMBERS = 'I am %Name, %Class and %Rank of the %Faction.'
TOPICS = dict(TD.TOPICS)
TOPICS['background'] = [info('m0', MEMBERS, kind=0, rank=0, disp=30)] + TD.TOPICS['background']
TOPICS['little secret'] = [
    info('s0', 'Only for the guild\'s third rank.', kind=0, FNAM='Mages Guild', rank=3),
    info('s1', 'Not for the guild.', kind=0, FNAM='FFFF'),
    info('s2', 'For women only.', kind=0, gender=1),
    info('s3', 'The council club.', kind=0, ANAM='Balmora'),
    info('s4', 'Not in the club.', kind=0, scvr=[('0BLX0Balmora, Council Club', 0)]),
    info('s5', 'A guild member of the player.', kind=0, DNAM='Mages Guild'),
    info('s6', 'Not a mage.', kind=0, scvr=[('09CX0Mage', 0)]),
    info('s7', 'Rich enough.', kind=0, scvr=[('05IX3Gold_001', 50)]),
    info('s8', 'Nothing.', kind=0, disp=80)]
# read live since v0.0.67-dev3 (DIALOGUE-CONDITIONS-PARTIAL-67): the player's diseases, worn value, Corprus, vampirism
TOPICS['specific place'] = [
    info('p0', 'You are sick.', kind=0, scvr=[('01400', 1)]),             # PcCommonDisease == 1
    info('p1', 'The blight!', kind=0, scvr=[('01410', 1)]),               # PcBlightDisease == 1
    info('p2', 'Fine clothes.', kind=0, scvr=[('01422', 1000)]),          # PcClothingModifier > 1000
    info('p3', 'Corprus, keep away.', kind=0, scvr=[('01580', 1)]),       # PcCorprus == 1
    info('p4', 'A vampire!', kind=0, scvr=[('01600', 1)]),                # PcVampire == 1
    info('p6', 'You attacked me!', kind=0, scvr=[('01620', 1)]),          # Attacked == 1 (the speaker's)
    info('p5', 'Nowhere special.', kind=0)]
DIALS = dict(TD.DIALS, **{'little secret': ('little secret', 0), 'specific place': ('specific place', 0)})
WANTED = ('background', 'help', 'latest rumors', 'my ring', 'little secret', 'specific place')


def kinds():
    k = TD.kinds()
    k['DIAL'] = {t: kind for t, (_n, kind) in DIALS.items()}
    # a speaker in Balmora's council club (its home cell) and a woman of the guild below the third rank
    k['NPC_'] = dict(k['NPC_'], clubman=npc('clubman', 'Clubman', 'Dark Elf'),
                     adept=npc('adept', 'Adept', 'Breton', cls='Mage', faction='Mages Guild', female=True, rank=1))
    return k


HOMES = {'clubman': 'Balmora, Council Club', 'fargoth': 'Seyda Neen'}


def run(k=None):
    k = k or kinds()
    raw, report = D.build(k, TOPICS, DIALS, HOMES)
    order = [i for i in G.plan_npcs(k, HOMES)[0] if i not in report['left_out']]
    return P.check(k, TOPICS, DIALS, raw, order, HOMES, WANTED)


class AnswerChoice(unittest.TestCase):
    def test_the_table_picks_what_the_original_picks(self):
        result = run()
        self.assertEqual(result['checked'], 10 * (1 + len(WANTED)) * len(P.VARIANTS))
        self.assertEqual(result['mismatches'], 0, result['first'])

    def test_the_check_catches_the_rank_without_a_faction(self):
        # the builder's filter before DIALOGUE-RANK-WITHOUT-FACTION-67: the members' line for everyone without a faction
        with mock.patch.object(G, 'rank_without_faction', lambda npc, fields: False):
            result = run()
        self.assertGreater(result['by_topic'].get('background', 0), 0)
        wrong = [m for m in result['first'] if m['topic'] == 'background']
        self.assertIn('%rank of the %faction', wrong[0]['amiwind'])
        self.assertNotIn('%rank', wrong[0]['original'] or '')

    def test_the_check_catches_a_condition_read_at_its_start_value(self):
        # before v0.0.67-dev3 the engine read these six at their start-of-game value: in the states where the player
        # is sick, cursed or well dressed, or the speaker was attacked, the table gave another answer than the original
        now_live = ('PcCommonDisease', 'PcBlightDisease', 'PcClothingModifier', 'PcCorprus', 'PcVampire', 'Attacked')
        self.assertTrue(set(now_live) <= set(D.LIVE_FUNCTIONS))
        old = tuple(n for n in D.LIVE_FUNCTIONS if n not in now_live)
        with mock.patch.object(D, 'LIVE_FUNCTIONS', old):
            result = run()
        self.assertGreater(result['by_topic'].get('specific place', 0), 0)
        said = {(m['original'] or '').lower() for m in result['first'] if m['topic'] == 'specific place'}
        self.assertTrue(said & {'you are sick.', 'the blight!', 'fine clothes.'}, said)

    def test_the_reference_reads_the_original_rules(self):
        k = kinds()
        from mwad.dialogue import speaker
        member, adept, plain = speaker(k, 'mage'), speaker(k, 'adept'), speaker(k, 'dunmer_m')
        st = P.state(k, plain, None)
        third = TOPICS['little secret'][0]
        self.assertEqual(P.ref_passes(third, member, P.state(k, member, None), None), (False, False))   # rank 2 < 3
        factionless = TOPICS['little secret'][1]
        self.assertEqual(P.ref_passes(factionless, plain, st, None), (True, True))
        self.assertEqual(P.ref_passes(factionless, member, st, None), (False, False))
        women = TOPICS['little secret'][2]
        self.assertEqual(P.ref_passes(women, adept, P.state(k, adept, None), None), (True, True))
        self.assertEqual(P.ref_passes(women, plain, st, None), (False, False))
        self.assertEqual(P.ref_passes(TOPICS['background'][0], plain, st, None), (False, False))   # no faction: -1
        # a disposition test alone failing is a refusal (the Info Refusal fallback)
        self.assertEqual(P.ref_passes(TOPICS['little secret'][8], plain, st, None), (True, False))

    def test_creature_rows_are_skipped_and_every_npc_row_still_matches(self):
        # DIALOGUE-CREATURE-SPEAKERS-66: the table's rows include the creature speakers, sorted with the NPCs; this
        # check's reference is the NPC rule, so it skips a creature row and still compares each NPC with its own row
        from test_greeting_lut import creature_record
        k = kinds()
        k['CREA'] = {'mudcrab': creature_record('mudcrab', 'Mudcrab', level=1, services=0x2003)}
        topics = dict(TOPICS, background=TOPICS['background'] + [info('cb', 'I am a mudcrab.', kind=0, ONAM='mudcrab')])
        raw, report = D.build(k, topics, DIALS, HOMES)
        creatures = G.creature_speakers(k, topics)
        order = [i for i in G.plan_npcs(k, HOMES, creatures)[0] if i not in report['left_out']]
        self.assertEqual((creatures, len(D.read(raw)['rows'])), (['mudcrab'], len(order)))
        result = P.check(k, topics, DIALS, raw, order, HOMES, WANTED)
        self.assertEqual(result['creature_rows_skipped'], 1)
        self.assertEqual(result['checked'], 10 * (1 + len(WANTED)) * len(P.VARIANTS))
        self.assertEqual(result['mismatches'], 0, result['first'])


if __name__ == '__main__':
    unittest.main()
