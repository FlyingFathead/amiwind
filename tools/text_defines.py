# SPDX-License-Identifier: GPL-3.0-only
"""The game's text defines as the builder writes them (BOOK-TEXT-MACROS-58).

A define the engine's getter table knows (%PCName, %Cell, %ActionActivate ...) is written as two characters:
CODE (1) and 1 + its number in engine/aga/src/aw_textdef.c's table, so the engine fills it without a name search.
The match is the engine's own (OpenMW 0.51's rule): '%' or '^', then a define name as a prefix without case,
%PCCrimeLevel and the action bindings first, then the list in table order, then %GameHour (a global in OpenMW, the
engine's clock getter here; TEXT-MACROS-DIALOGUE-CODES-59). Anything else (the game's other globals, unknown names, a
lone '%') stays as written; the engine fills globals at run time and prints the rest. Books, journal entries, the
dialogue table's answers and the voice table's lines are written with these codes (prepare_books.py,
prepare_world_ui.py, dialogue_lut.py, greeting_lut.py).
NAMES must equal the C table (tests/test_text_defines.py compares them)."""

CODE = '\x01'
NAMES = (
    'pccrimelevel', 'nextpcrank', 'pcnextrank', 'faction', 'pcclass', 'pcname', 'pcrace', 'pcrank', 'class', 'cell',
    'race', 'rank', 'name',
    'actionslideright', 'actionreadymagic', 'actionprevweapon', 'actionnextweapon', 'actiontogglerun',
    'actionslideleft', 'actionreadyitem', 'actionprevspell', 'actionnextspell', 'actionrestmenu', 'actionmenumode',
    'actionactivate', 'actionjournal', 'actionforward', 'actioncrouch', 'actionjump', 'actionback', 'actionuse',
    'actionrun', 'gamehour',
)
ACTION_FIRST = 13
GAMEHOUR = len(NAMES) - 1     # a global in OpenMW, a getter of the game clock here: matched after the fixed list
_ORDER = (0, *range(ACTION_FIRST, GAMEHOUR), *range(1, ACTION_FIRST), GAMEHOUR)


def match(text, at):
    """(number, length) of the define name at TEXT[AT:], or (-1, 0)."""
    low = text[at:at + 16].lower()
    for k in _ORDER:
        if low.startswith(NAMES[k]):
            return k, len(NAMES[k])
    return -1, 0


def encode(text):
    """TEXT with every known define written as its code; returns (text, count)."""
    coded, _spans, count = encode_spans(text, ())
    return coded, count


def encode_spans(text, spans):
    """TEXT coded as encode() does, and SPANS [(offset, length, topic)] (the dialogue's links, offsets in TEXT's
    characters) moved onto the coded text; a define that a span starts or ends inside stays as written (the engine
    still fills it by name). Returns (text, spans, count)."""
    edges = {o for o, n, _t in spans} | {o + n for o, n, _t in spans}
    out, new_at, at, count = [], {}, 0, 0
    length = 0
    while at < len(text):
        new_at[at] = length
        c = text[at]
        if c in '%^':
            k, n = match(text, at + 1)
            if k >= 0 and not any(at < e < at + 1 + n for e in edges):
                out.append(CODE + chr(k + 1))
                length += 2
                at += 1 + n
                count += 1
                continue
        out.append(c)
        length += 1
        at += 1
    new_at[at] = length
    return ''.join(out), [(new_at[o], new_at[o + n] - new_at[o], t) for o, n, t in spans], count
