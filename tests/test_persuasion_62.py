# SPDX-License-Identifier: GPL-3.0-only
"""Persuasion in the dialogue window (PERSUASION-BROKEN-62).

In v0.0.62-dev1 the persuasion rows shared their list codes (-10..-15) with the enchanting page's fixed rows, and the
window's click handler tested the enchanting codes first: Admire opened the enchanting item page (the list fell back
to the topics), Intimidate the soul gem page, Taunt changed an enchantment style (nothing seen), the bribes added,
removed or bought an effect. Checked here: every list code range of the window is apart from every other; a
persuasion row reaches the persuasion; the persuasion shows the action as a heading with the NPC's own
"<Kind> Success" / "<Kind> Fail" answer, trains Speechcraft and lets a taunted NPC attack; and the rule (OpenMW
MechanicsManager::getPersuasionDispositionChange, our own code, mirrored by tools/dialogue_lut.persuade and checked
against the engine's C in tests/test_dialogue_lut.py) with the game settings of Morrowind.esm and the record of
Tolvise Othralen (Seyda Neen: level 3, Fight 30, Flee 70, disposition 50)."""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src')]
import dialogue_lut as D  # noqa: E402

SRC = ROOT / 'engine' / 'aga' / 'src'
WIN = (SRC / 'aw_dialwin.c').read_text(encoding='utf-8')

# the persuasion settings of Morrowind.esm (GMST records, read from the master)
MASTER = {'fPersonalityMod': 5.0, 'fLuckMod': 10.0, 'fReputationMod': 1.0, 'fLevelMod': 5.0, 'fBribe10Mod': 35.0,
          'fBribe100Mod': 75.0, 'fBribe1000Mod': 150.0, 'iPerMinChance': 5, 'iPerMinChange': 10,
          'fPerDieRollMult': D._f32(0.3), 'fPerTempMult': 1.0, 'fFatigueBase': 1.25, 'fFatigueMult': 0.5}
TABLE = {'settings': MASTER}
# Tolvise Othralen: level 3 (the record), the rest a plain level-3 commoner's; a new player character
TOLVISE = {'personality': 40, 'luck': 40, 'reputation': 0, 'speechcraft': 10, 'mercantile': 10, 'level': 3,
           'fatigue': 1.0}
PLAYER = {'personality': 50, 'luck': 40, 'reputation': 0, 'speechcraft': 35, 'mercantile': 10, 'level': 1,
          'fatigue': 1.0}
TOLVISE_FIGHT, TOLVISE_FLEE = 30, 70
ADMIRE, INTIMIDATE, TAUNT, BRIBE10 = 0, 1, 2, 3


def body(text, start):
    i = text.index(start)
    return text[i:text.index('\n}', i) + 2]


def code_ranges():
    """{macro: (low, high)} of every CODE_* list code of the window, a range macro over its row count."""
    sizes = {'CODE_CHOICE': 10, 'CODE_SERVICE': 7, 'CODE_ACTION': 6, 'CODE_TRAIN': 3, 'CODE_WARE': 32,
             'CODE_SPELL': 24, 'CODE_SM_EFFECT': 8, 'CODE_SM_FIELD': 5, 'CODE_SM_PICK': 48, 'CODE_EN_EFFECT': 8,
             'CODE_EN_FIELD': 5, 'CODE_EN_PICKITEM': 24, 'CODE_EN_PICKGEM': 64, 'CODE_EN_PICK': 48}
    out = {}
    for name, value in re.findall(r'#define (CODE_\w+)\s+\((-\d+)\)', WIN):
        out[name] = (int(value), int(value))
    for name, base in re.findall(r'#define (CODE_\w+)\(k\)\s+\((-\d+)-\(k\)\)', WIN):
        out[name] = (int(base) - sizes[name] + 1, int(base))
    return out


class ListCodes(unittest.TestCase):
    def test_every_code_range_apart(self):
        ranges = code_ranges()
        self.assertIn('CODE_ACTION', ranges)
        self.assertIn('CODE_EN_ITEM', ranges)
        items = sorted(ranges.items(), key=lambda kv: kv[1])
        for (a, (lo_a, hi_a)), (b, (lo_b, _hi)) in zip(items, items[1:]):
            self.assertLess(hi_a, lo_b, '%s and %s share list codes' % (a, b))

    def test_persuasion_rows_reach_the_persuasion(self):
        ask = body(WIN, 'static void ask(int r){')
        self.assertIn('persuade(CODE_ACTION(0)-list[r]);', ask)


class Flow(unittest.TestCase):
    def setUp(self):
        self.p = body(WIN, 'static void persuade(int kind){')

    def test_heading_and_own_answer(self):
        # the action as a heading (like an asked topic), then the NPC's "<Kind> Success" / "<Kind> Fail" answer
        self.assertIn('answer_topic[kind],r.success?"success":"fail"', self.p)
        self.assertIn('answer_of(named_topic(name),T(AW_DIAL_TEXT_ADMIRE+kind,actions[kind]));', self.p)
        answer = body(WIN, 'static void answer_with(int topic,int answer,const char *heading,int journal){')
        self.assertIn('if(name[0])append(name,1);', answer)        # the heading bar
        self.assertIn('if(heading && *heading)append(heading,1);', answer)   # a missing answer keeps the heading
        self.assertEqual(re.findall(r'"(\w+)"', WIN[WIN.index('answer_topic[AW_PERSUADE_KINDS]'):][:120]),
                         ['admire', 'intimidate', 'taunt', 'bribe', 'bribe', 'bribe'])

    def test_disposition_speechcraft_and_fight(self):
        p = self.p
        self.assertIn('current_base+=r.temp;permanent_change+=r.perm;', p)
        self.assertIn('AW_LevelupUse(25,r.success?0:1,1);', p)           # Speechcraft (skill 25), success / fail use
        self.assertIn('AW_MwscriptSetSpeaker(speaker_record,speaker_reference,-1,r.fight,r.flee);', p)
        self.assertIn('if(AW_MwscriptSpeakerAggro(speaker,disposition)>0)fight_started=1;', p)
        self.assertLess(p.index('AW_MwscriptSetSpeaker('), p.index('AW_MwscriptSpeakerAggro('))

    def test_bribe_greyed_without_the_gold(self):
        self.assertIn('static int affordable(int kind){return !bribe_gold[kind] || AW_MwscriptPlayerGold(0)>=bribe_gold[kind];}',
                      WIN)
        self.assertIn('if(!affordable(kind))return;', self.p)


class Rule(unittest.TestCase):
    """Tolvise Othralen at disposition 50, the master's settings. Ratings (single precision):
    player r1 = (0 + 4 + 10 + 35) * 1.25 = 61.25, r2 = 61.25 + 5 = 66.25; Tolvise n1 = (0 + 4 + 8 + 10) * 1.25 = 27.5,
    n2 = (15 + 0 + 4 + 8 + 10) * 1.25 = 46.25. Chances: Admire / Taunt t1 = 61.25 - 27.5 + 50 = 83.75,
    Intimidate t2 = 66.25 - 46.25 + 50 = 70."""

    def run_(self, kind, roll, disposition=50):
        return D.persuade(TABLE, kind, PLAYER, TOLVISE, disposition, roll, TOLVISE_FIGHT, TOLVISE_FLEE)

    def test_admire(self):
        r = self.run_(ADMIRE, 20)               # 20 <= 83.75: success, floor(0.3 * 63.75) = 19
        self.assertEqual((r['success'], r['temp'], r['perm']), (True, 19, 19))
        r = self.run_(ADMIRE, 80)               # floor(0.3 * 3.75) = 1, below iPerMinChange 10: 10
        self.assertEqual((r['success'], r['temp']), (True, 10))
        r = self.run_(ADMIRE, 90)               # 90 > 83.75: fail, floor(0.3 * -6.25) = -2
        self.assertEqual((r['success'], r['temp'], r['perm']), (False, -2, -2))

    def test_intimidate(self):
        r = self.run_(INTIMIDATE, 40)           # success, r = 30: Flee +9 -> min change 10, Fight -10
        self.assertTrue(r['success'])
        self.assertEqual((r['fight'], r['flee']), (20, 80))
        self.assertEqual(r['temp'], 10)
        r = self.run_(INTIMIDATE, 95)           # fail: floor(-25 * 0.3) = -8
        self.assertEqual((r['success'], r['temp'], r['fight'], r['flee']), (False, -8, 30, 70))

    def test_taunt(self):
        r = self.run_(TAUNT, 10)                # success, c = 73: Fight + 21.9 -> 51, Flee - 21 -> 49, disposition -22
        self.assertTrue(r['success'])
        self.assertEqual((r['fight'], r['flee'], r['temp']), (51, 49, -22))
        r = self.run_(TAUNT, 99)                # fail: c = 15, floor(-4.5) = -5; Fight and Flee unchanged
        self.assertEqual((r['success'], r['temp'], r['fight'], r['flee']), (False, -5, 30, 70))

    def test_repeated_taunts_bring_fight_to_100(self):
        # OpenMW: taunting most people into attacking must be possible; each success raises Fight (to 100)
        fight, flee, disposition = TOLVISE_FIGHT, TOLVISE_FLEE, 50
        for _ in range(6):
            r = D.persuade(TABLE, TAUNT, PLAYER, TOLVISE, disposition, 0, fight, flee)
            self.assertTrue(r['success'])
            fight, flee, disposition = r['fight'], r['flee'], disposition + r['temp']
        self.assertEqual(fight, 100)

    def test_bribe(self):
        r = self.run_(BRIBE10, 50)              # t3 = (10 + 4 + 10) * 1.25 - (10 + 0 + 4 + 8) * 1.25 + 50 + 35 = 87.5
        self.assertEqual((r['success'], r['temp']), (True, 11))
        r = self.run_(BRIBE10, 99)
        self.assertFalse(r['success'])


if __name__ == '__main__':
    unittest.main()
