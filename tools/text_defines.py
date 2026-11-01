# SPDX-License-Identifier: GPL-3.0-only
"""The game's text defines as the builder writes them (BOOK-TEXT-MACROS-58).

A define the engine's getter table knows (%PCName, %Cell, %ActionActivate ...) is written as two characters:
CODE (1) and 1 + its number in engine/aga/src/aw_textdef.c's table, so the engine fills it without a name search.
The match is the engine's own (OpenMW 0.51's rule): '%' or '^', then a define name as a prefix without case,
%PCCrimeLevel and the action bindings first, then the list in table order. Anything else (the game's globals such as
%GameHour, unknown names, a lone '%') stays as written; the engine fills globals at run time and prints the rest.
NAMES must equal the C table (tests/test_text_defines.py compares them)."""

CODE = '\x01'
NAMES = (
    'pccrimelevel', 'nextpcrank', 'pcnextrank', 'faction', 'pcclass', 'pcname', 'pcrace', 'pcrank', 'class', 'cell',
    'race', 'rank', 'name',
    'actionslideright', 'actionreadymagic', 'actionprevweapon', 'actionnextweapon', 'actiontogglerun',
    'actionslideleft', 'actionreadyitem', 'actionprevspell', 'actionnextspell', 'actionrestmenu', 'actionmenumode',
    'actionactivate', 'actionjournal', 'actionforward', 'actioncrouch', 'actionjump', 'actionback', 'actionuse',
    'actionrun',
)
ACTION_FIRST = 13
_ORDER = (0, *range(ACTION_FIRST, len(NAMES)), *range(1, ACTION_FIRST))


def match(text, at):
    """(number, length) of the define name at TEXT[AT:], or (-1, 0)."""
    low = text[at:at + 16].lower()
    for k in _ORDER:
        if low.startswith(NAMES[k]):
            return k, len(NAMES[k])
    return -1, 0


def encode(text):
    """TEXT with every known define written as its code; returns (text, count)."""
    out, at, count = [], 0, 0
    while at < len(text):
        c = text[at]
        if c in '%^':
            k, n = match(text, at + 1)
            if k >= 0:
                out.append(CODE + chr(k + 1))
                at += 1 + n
                count += 1
                continue
        out.append(c)
        at += 1
    return ''.join(out), count
