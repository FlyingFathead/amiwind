# SPDX-License-Identifier: GPL-3.0-only
"""The links in dialogue text (tools/dialogue_lut.py span_finder; DIALOGUE-LINKS-62).

The builder finds every topic name in a text by OpenMW 0.51's keyword search rule (keywordsearch.cpp
highlightKeywords): a name starts the text or follows a word separator, nothing is checked at its end, the longest of
overlapping names wins; ours adds that a name must also end the word (no letter or digit right after it except a plural "s", a deliberate
step beyond OpenMW, docs/DIALOGUE_DESIGN.md). The engine then shows and answers a span as a link only when its topic is in the current
topic list (the topics the player knows that this speaker answers; OpenMW DialogueWindow seeds its search with that
list), which is why a short topic the player does not know is never lit inside a longer word. Synthetic names always;
with the tester's own Morrowind (AMIWIND_TEST_MORROWIND = the Data Files folder) every dialogue text of
Morrowind.esm, Tribunal.esm and Bloodmoon.esm is searched and every span checked. Nothing of the game data is stored.
"""
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'src', ROOT / 'tools'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import dialogue_lut as D  # noqa: E402


def check_spans(test, display, shown, spans):
    """Every span names its topic, starts at a word start (OpenMW's separators) and does not overlap the last."""
    last = 0
    for offset, length, topic in spans:
        word = shown[offset:offset + length]
        test.assertIsNotNone(display[topic])
        test.assertEqual(D._lower(word), D._lower(display[topic]), (shown, word))
        test.assertTrue(offset == 0 or shown[offset - 1] in D.WORD_SEPARATORS or offset == last, (shown, word))
        test.assertFalse(D.ends_inside(shown, offset + length), (shown, word))
        test.assertGreaterEqual(offset, last, (shown, word))
        last = offset + length


class SyntheticLinkTests(unittest.TestCase):
    display = ['Plan', 'Plantation', 'House Hlaalu', 'Hlaalu', None, 'Suran']

    def spans(self, text):
        return D.span_finder(self.display)(text)

    def test_whole_words_only(self):
        shown, spans = self.spans('Plantations to the southwest include Dren Plantation, and a plan.')
        # OpenMW checks no end ("Plan" would light inside "Plantation"); ours needs the word's end too, a plural kept
        self.assertEqual([shown[o:o + n] for o, n, _ in spans], ['Plantation', 'Plantation', 'plan'])
        shown, spans = self.spans('A planned plant, planning.')
        self.assertEqual(spans, [])
        check_spans(self, self.display, shown, spans)

    def test_never_inside_a_word_start(self):
        shown, spans = self.spans('Explanation of Suran')
        self.assertEqual([shown[o:o + n] for o, n, _ in spans], ['Suran'])

    def test_longest_first(self):
        shown, spans = self.spans('House Hlaalu of Suran.')
        self.assertEqual([shown[o:o + n] for o, n, _ in spans], ['House Hlaalu', 'Suran'])


DATA = os.environ.get('AMIWIND_TEST_MORROWIND')


@unittest.skipUnless(DATA, "requires the tester's own Morrowind data")
class MasterLinkTests(unittest.TestCase):
    """Every INFO text of the three masters: each span is a topic name starting a word."""

    def test_all_dialogue_text(self):
        from mwad.esm import first, records, subrecords, text
        names, texts = {}, []
        for master in ('Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm'):
            path = Path(DATA) / master
            if not path.is_file():
                continue
            for tag, _flags, raw in records(path.read_bytes()):
                if tag == 'DIAL':
                    fields = list(subrecords(raw))
                    kind = first(fields, 'DATA')
                    if kind and kind[0] == D.KIND_TOPIC:
                        name = text(fields, 'NAME')
                        names.setdefault(name.casefold(), name)
                elif tag == 'INFO':
                    line = text(list(subrecords(raw)), 'NAME')
                    if line:
                        texts.append(line)
        self.assertGreater(len(texts), 1000)
        display = sorted(names.values(), key=str.casefold)
        find = D.span_finder(display)
        links = 0
        for line in texts:
            shown, spans = find(line)
            check_spans(self, display, shown, spans)
            links += len(spans)
        self.assertGreater(links, 1000)
        print('dialogue links: %d texts, %d topics, %d spans, each a whole-word topic name'
              % (len(texts), len(display), links))


if __name__ == '__main__':
    unittest.main()
