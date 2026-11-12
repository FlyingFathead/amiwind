"""The dialogue window opens in the opening from the papers' stage on (RC2-SELLUS-NO-TALK-65).

In the original and in OpenMW the use key on a person is "talk" (mwworld/actiontalk.cpp: the dialogue mode), never one of
the menus character creation keeps shut. AmiWind's dialogue window opened through the window gate of the map and the
inventory (aw_worldui.c AW_WorldUIOpenPanel), which refuses every window while the opening restricts the game, so no
person (Sellus Gravius, the clerk, the hall guard) could be talked to and Sellus could never take the papers. The window
now has its own opener: in play, and during the registration from the papers' stage on (the character sheet first,
the maintainer's order), with its refusal on the console.
"""
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'


def function_body(path, signature):
    text = (SRC / path).read_text(encoding='utf-8', errors='replace')
    start = text.index(signature)
    end = text.index('\n}\n', start)
    return text[start:end]


class DialogueWindowOpening(unittest.TestCase):
    def test_window_uses_its_own_opener(self):
        body = function_body('aw_dialwin.c', 'int AW_DialWindowOpen(')
        self.assertIn('AW_WorldUIOpenDialoguePanel(', body)
        self.assertNotIn('AW_WorldUIOpenPanel(', body, 'the window goes through the menus\' gate again')

    def test_opener_allows_the_registration_from_the_papers_on(self):
        body = function_body('aw_worldui.c', 'int AW_WorldUIOpenDialoguePanel(')
        self.assertIn('allowed_in_play()', body)
        self.assertNotIn('allowed()', body.replace('allowed_in_play()', ''), 'the menus\' rule shuts the window again')
        # the census office's one rule for takes and talk (the papers on the table unlock both)
        self.assertIn('aw_census_take_refused()', body, 'the talk is not unlocked with the takes')

    def test_refusal_is_said(self):
        body = function_body('aw_dialwin.c', 'int AW_DialWindowOpen(')
        tail = body[body.index('AW_WorldUIOpenDialoguePanel('):]
        self.assertIn('Con_Printf(', tail[:600])


if __name__ == '__main__':
    unittest.main()
