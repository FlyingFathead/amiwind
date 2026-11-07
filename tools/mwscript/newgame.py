# SPDX-License-Identifier: GPL-3.0-only
"""What a new game starts once, and the build check that keeps it (NPC-STORY-DISABLED-AT-START-42, v0.0.62).

The original: a new game sets CharGenState to 1 (OpenMW 0.51 apps/openmw/mwworld/worldimp.cpp startNewGame) and the
global script Main, which the game always runs (OpenMW apps/openmw/mwscript/globalscripts.cpp addStartup), starts
the scripts of its `if ( CharGenState == 1 )` block: Startup, the run-once script whose `ID->Disable` lines take the
twelve road and town Dreamers, the Dreamer Prophet, the falling mage near Seyda Neen and about sixty other story
characters, creatures and objects out of the world until a quest enables them, and VampireCheck. The engine never
ran Main (it is no start script record), so none of them was disabled.

The builder writes those scripts as the NEWG section of id1/mwscript.awm (awms.py); the engine starts each once when
a new game begins, by any opening (aw_mwhost.c AW_MwscriptNewGame). Startup then disables them through the object
state, which is kept in saved games; a disabled reference's own script keeps running, so a Dreamer's script enables
it when the main quest reaches its stage (OpenMW World::disable keeps the local script).

check() is the build check: the new game's scripts are in the file and runnable, and every reference their
unconditional Disable lines name resolves to its placed reference, so the engine can disable it."""
from .codegen import SCRIPT_BROKEN, SCRIPT_HANDWRITTEN, SCRIPT_INERT
from .gamedata import MAIN_SCRIPT, unconditional_disables

ACTOR_TYPES = ('NPC_', 'CREA')


def report(program, compiled):
    """{'main', 'scripts': [{name, runnable, why}], 'disabled': [{id, script, type, placed, reference, resolved}],
    'counts'} of what a new game starts once and what those scripts disable."""
    data = program.data
    scripts, disabled = [], []
    for name in getattr(data, 'new_game', []):
        index = program.scripts.index.get(name)
        c = compiled[index] if index is not None else None
        why = ('not in the game data' if c is None else 'did not compile: %s' % c.error if c.flags & SCRIPT_BROKEN
               else 'carried by hand (config/mwscript.json handwritten)' if c.flags & SCRIPT_HANDWRITTEN
               else 'inert: nothing it does is seen' if c.flags & SCRIPT_INERT else '')
        scripts.append({'name': name, 'runnable': not why, 'why': why or 'runs once at a new game'})
        if c is None or why:
            continue
        for ident in unconditional_disables(data.scripts[name].text):
            key = ident.casefold()
            refs = data.object_refs.get(key, [])
            row = program.objects.rows[program.objects.index[key]] if key in program.objects.index else None
            kind = (data.bases.get(key) or (None, ''))[0]
            disabled.append({'id': ident, 'script': name, 'type': kind, 'placed': len(refs),
                             'reference': row['reference'] if row else None,
                             'resolved': bool(row) and len(refs) == 1 and row['reference'] == refs[0]})
    actors = [d for d in disabled if d['type'] in ACTOR_TYPES]
    return {'main': MAIN_SCRIPT in data.scripts, 'scripts': scripts, 'disabled': disabled,
            'counts': {'scripts': len(scripts), 'runnable': sum(s['runnable'] for s in scripts),
                       'disabled': len(disabled), 'actors': len(actors),
                       'placed_once': sum(d['placed'] == 1 for d in disabled),
                       'resolved': sum(d['resolved'] for d in disabled),
                       'placed_more_than_once': sum(d['placed'] > 1 for d in disabled),
                       'not_placed': sum(d['placed'] == 0 for d in disabled)}}


def check(program, compiled):
    """The report; raises ValueError when a new game would not start the original's run-once scripts or one of
    their disables placed once in the world cannot reach its reference (the Dreamers would stand on the roads from
    the first minute again)."""
    r = report(program, compiled)
    problems = []
    if r['main'] and not r['scripts']:
        problems.append('Main starts nothing under CharGenState == 1: no NEWG rows')
    if r['scripts'] and not r['counts']['runnable']:
        problems.append('none of the new game scripts can run: %s' % '; '.join(
            '%s %s' % (s['name'], s['why']) for s in r['scripts']))
    lost = [d for d in r['disabled'] if d['placed'] == 1 and not d['resolved']]
    if lost:
        problems.append('%d references placed once are not bound for their Disable: %s' % (
            len(lost), ', '.join(d['id'] for d in lost[:12])))
    if problems:
        raise ValueError('New game check (NPC-STORY-DISABLED-AT-START-42): ' + ' | '.join(problems))
    return r
