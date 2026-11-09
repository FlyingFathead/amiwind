# SPDX-License-Identifier: GPL-3.0-only
"""The dialogue answers that start or change a fight (DIALOGUE-AGGRO-62): every StartCombat, SetFight and ModFight
call of a result script, with whom it acts on, and the engine path that carries it out. The scripting tracker
(tools/mwscript_features.py) measures them over the masters; tests/test_crime.py holds every one to a handled path.

The paths, as the engine carries a dialogue answer out (OpenMW 0.51 alike):
  speaker-startcombat  the speaker's StartCombat Player: host_combat finds the speaker by the answer's reference
  other-startcombat    another actor's "ref"->StartCombat Player: host_combat by that reference
  speaker-fight        the speaker's SetFight / ModFight: the talk's end weighs the Fight it has now
                       (AW_MwscriptSpeakerAggro)
  other-fight          another actor's SetFight / ModFight: the ambient aggression reads that actor's Fight now
                       (aw_ambient_fight_now) at its next check
  startcombat-actor    StartCombat against another actor (not the player): the combat layer fights the player only
  not-run              the answer does not run whole (a compile error, or a function not carried out yet)
"""
import re

CALL = re.compile(r'^\s*(?:"?(?P<ref>[^"\r\n]+?)"?\s*->\s*)?(?P<fn>startcombat|setfight|modfight)\b[\s,]*'
                  r'(?P<arg>"[^"]*"|[^\s;]+)?', re.I)
HANDLED = ('speaker-startcombat', 'other-startcombat', 'speaker-fight', 'other-fight')
UNHANDLED = ('startcombat-actor', 'not-run')


def calls(text):
    """The fight calls of a result's TEXT, in order: [function, who it acts on, target] with who 'speaker', 'player'
    or 'other' and target the StartCombat's opponent ('player' or 'actor') or the Fight value ('' when not a number)."""
    out = []
    for raw in text.splitlines():
        m = CALL.match(raw.split(';', 1)[0])
        if not m:
            continue
        fn = m.group('fn').lower()
        ref = (m.group('ref') or '').strip().strip('"').strip()
        arg = (m.group('arg') or '').strip().strip('"')
        who = 'speaker' if not ref else 'player' if ref.lower() == 'player' else 'other'
        if fn == 'startcombat':
            out.append([fn, who, 'player' if arg.lower() == 'player' else 'actor'])
        else:
            out.append([fn, who, arg if re.match(r'^-?\d+(\.\d+)?$', arg) else ''])
    return out


def path(fight_calls, runs=True):
    """The engine path of a result with these calls (see the module's text); None without a fight call."""
    if not fight_calls:
        return None
    if not runs:
        return 'not-run'
    starts = [c for c in fight_calls if c[0] == 'startcombat']
    if any(c[2] != 'player' or c[1] == 'player' for c in starts):
        return 'startcombat-actor'
    if starts:
        return 'speaker-startcombat' if all(c[1] == 'speaker' for c in starts) else 'other-startcombat'
    return 'speaker-fight' if all(c[1] == 'speaker' for c in fight_calls) else 'other-fight'
