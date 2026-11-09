#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The original game's console commands in AmiWind (MW-CONSOLE-COMMANDS-62): renders config/mwscript-console.json
into docs/CONSOLE_COMMANDS_MORROWIND.md, and gives the counts by state (the MWScript tracker reads them).

    python3 tools/mwscript_console.py render     write the page
    python3 tools/mwscript_console.py counts     print the counts by state
"""
import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'config/mwscript-console.json'
PAGE = ROOT / 'docs/CONSOLE_COMMANDS_MORROWIND.md'
HELP = ROOT / 'config/mwconsole-help.txt'   # staged as id1/mwconsole-help.txt (tools/build_aga.py)
STATES = ('alias', 'vm', 'collision', 'planned', 'not applicable')
WORDS = {'alias': 'works (AmiWind\'s own command)', 'vm': 'works (run as a script line)',
         'collision': 'AmiWind\'s own command of that name', 'planned': 'planned', 'not applicable': 'not applicable'}


def load():
    return json.loads(CONFIG.read_text(encoding='utf-8'))


def counts(data=None):
    data = data or load()
    c = Counter(r['state'] for r in data['commands'])
    return {s: c.get(s, 0) for s in STATES}


def sync(data):
    """The census follows the function table: a planned command the table carries becomes vm; every planned one
    gets the reason it stays planned ("why")."""
    sys.path.insert(0, str(ROOT / 'tools'))
    from mwscript import functions as F
    table = {r.split()[0]: r.split()[1] for r in function_rows()}
    for r in data['commands']:
        n = r['name']
        if r['state'] == 'planned' and n in table:
            r['state'] = 'vm'
            r['amiwind'] = ('the MWScript host by the compiler\'s function table (%s), on any reference by id-> or the '
                            'console target' % {'host': 'the host\'s call by number', 'actor': 'host_actor',
                                                'special': SPECIAL.get(n, '')}[table[n]])
        if r['state'] == 'planned':
            fn = F.FUNCTIONS.get(n)
            if n in COMPILED_ARGUMENTS:
                why = 'its arguments are worked out by the compiler (%s)' % COMPILED_ARGUMENTS[n]
            elif fn is None and n in NOT_YET:
                why = 'a console-only command with no AmiWind counterpart yet: ' + NOT_YET[n]
            elif fn is None:
                why = 'a console-only command with no AmiWind counterpart yet'
            elif not fn.run and n in NOT_YET:
                why = 'not carried out yet: ' + NOT_YET[n]
            elif not fn.run:
                why = 'not carried out by the interpreter yet (scripts too)'
            else:
                why = 'an interpreter opcode with compiled arguments (a sound, topic, script or message row)'
            r['why'] = why
        else:
            r.pop('why', None)
    CONFIG.write_text(json.dumps(data, indent=1, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')


def render(version):
    data = load()
    sync(data)
    c = counts(data)
    lines = ['# The original game\'s console commands in AmiWind', '',
             '_Last updated with AmiWind %s (%d %s)._' % (version, time.localtime().tm_mday, time.strftime('%B %Y')), '',
             'Debug steps written for the original game work in AmiWind\'s console as typed: an original console '
             'command that does not clash with one of AmiWind\'s runs AmiWind\'s own command for the same job, or '
             'runs through the game\'s script interpreter as a script line would. The names are matched without '
             'regard to case, the short and long forms alike (tgm and ToggleGodMode). A line may name its target '
             'first (player->SetStrength 50); arguments are separated by spaces or commas, and an id with spaces '
             'goes in quotes. These names are not listed in dbg help; dbg help mw (or dbg mw help) lists them page by '
             'page. A line without a target runs on the console target, chosen with dbg mw target from a list of '
             'the references on the map (typed to filter by name, id or kind, nearest first; the input line shows '
             'it), or on the player when none is chosen. Item and spell ids are found in the actor table (what an '
             'actor carries or a script names), so such a line may take a moment.', '',
             'With thanks to the UESP for its Morrowind:Console page (https://en.uesp.net/wiki/Morrowind:Console), '
             'which lists the original\'s commands; the list here is also checked against OpenMW 0.51.', '',
             '%d commands: %s.' % (sum(c.values()), ', '.join('%d %s' % (c[s], s) for s in STATES)), '',
             'Very high values of Speed or Acrobatics (SetSpeed, SetAcrobatics) make the player hard to control, '
             'as in the original.', '',
             '## Collisions', '',
             'These names are AmiWind\'s own commands; AmiWind\'s meaning is kept.', '',
             '| Command | AmiWind |', '|---|---|']
    for r in data['commands']:
        if r['state'] == 'collision':
            lines.append('| %s | %s |' % (r['name'], r['amiwind']))
    lines += ['', '## Every command', '', '| Command | Short | Group | State | In AmiWind |', '|---|---|---|---|---|']
    for r in data['commands']:
        lines.append('| %s | %s | %s | %s | %s |' % (r['name'], r.get('short', ''), r['group'], WORDS[r['state']],
                                                     r.get('amiwind', '') or r.get('why', '')))
    PAGE.write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
    HELP.write_text(help_text(data), encoding='ascii', newline='\n')
    FUNCTIONS_FILE.write_text('AWMF1\n' + '\n'.join(function_rows()) + '\n', encoding='ascii', newline='\n')
    return c


FUNCTIONS_FILE = ROOT / 'config/mwconsole-functions.txt'   # staged as id1/mwconsole-functions.txt
# The host calls whose arguments the compiler works out from the game data (a row, an index, a region): a console
# line cannot give them as typed, so they stay planned, each with the reason (codegen.py hostcall and call)
COMPILED_ARGUMENTS = {
    'cast': 'the spell\'s effect row', 'hasitemequipped': 'the item\'s row', 'getspelleffects': 'the spell\'s row',
    'becomewerewolf': 'the werewolf settings', 'setwerewolfacrobatics': 'the werewolf settings',
    'explodespell': 'the spell\'s row', 'removespelleffects': 'the spell\'s row', 'geteffect': 'the effect number', 'addtopic': 'the topic row',
    'changeweather': 'the region index', 'modregion': 'the region index', 'positioncell': 'the room and its move row',
    'placeatpc': 'the placing rows', 'placeatme': 'the placing rows', 'placeitem': 'the placing rows',
    'placeitemcell': 'the placing rows', 'drop': 'the item\'s row', 'aifollowcell': 'the room number',
    'aiescortcell': 'the room number', 'choice': 'a dialogue result only', 'goodbye': 'a dialogue result only',
    'clearinfoactor': 'a dialogue result only'}
# v0.0.63 (MWSCRIPT-GAPS-63): why each function still not carried out stays so (the console table and the tracker)
NOT_YET = {
    'setwaterlevel': 'a room\'s water is baked into its map; moving it needs moving water in the engine',
    'modwaterlevel': 'a room\'s water is baked into its map; moving it needs moving water in the engine',
    'getwindspeed': 'the weather has no wind speed yet',
    'equip': 'an NPC\'s worn and held entries come from its record; the actor table has no change of them yet '
             '(the player\'s Equip works as an alias)',
    'aiactivate': 'the ambient tables have no package that walks to an object and uses it',
    'hitattemptonme': 'the combat layer keeps only the blows that land (HitOnMe); a missed swing is not kept',
    'skipanim': 'the animation kit has no per-frame skip',
    'filljournal': 'a debug fill of every journal entry: the dated history keeps only what was earned',
    'fillmap': 'a debug fill of every map place: the revealed places come one by one from ShowMap',
    'getpcvisionbonus': 'the renderer has no player-side brightness term (Night Eye) yet; it needs an A/B on the Pi',
    'setpcvisionbonus': 'the renderer has no player-side brightness term (Night Eye) yet; it needs an A/B on the Pi',
    'modpcvisionbonus': 'the renderer has no player-side brightness term (Night Eye) yet; it needs an A/B on the Pi',
    'addtolevcreature': 'the levelled lists are read from the actor table on disk; an edit needs a saved change list',
    'removefromlevcreature': 'the levelled lists are read from the actor table on disk; an edit needs a saved change '
                             'list',
    'addtolevitem': 'the levelled lists are read from the actor table on disk; an edit needs a saved change list',
    'removefromlevitem': 'the levelled lists are read from the actor table on disk; an edit needs a saved change list',
    # the original's console-only toggles with no AmiWind switch: each is a new on-screen readout (a command or a
    # cvar of 32 to 56 bytes, plus its drawing and its data), none of them cheap enough to add as a stand-in
    'toggledialoguestats': 'a readout of the dialogue filter checks; the dialogue window has no such trace yet',
    'togglegrid': 'the exterior cell grid drawn over the world; the renderer has no such overlay yet',
    'togglekillstats': 'a count of the kills by kind; the change list keeps deaths per actor, no tally readout yet',
    'togglemagicstats': 'a readout of the active effects; dbg cast spell lists spells, not a live overlay',
    'toggleloadfade': 'AmiWind\'s loading screen has no fade to switch',
    # batch 3 (v0.0.63): the console group's drawing switches and cell tests left, each with what it lacks
    'togglesky': 'the sky is drawn as part of the world map\'s sky surfaces; the renderer has no switch to leave it out',
    'togglewater': 'a room\'s water is baked into its map as world surfaces; the renderer has no switch to leave it out',
    'toggleworld': 'the renderer has no switch to leave out the world map while drawing the objects',
    'togglepathgrid': 'the path grids are read per actor from the ambient table; nothing draws them yet',
    'togglecollisionboxes': 'the renderer has no overlay of the collision boxes yet',
    'togglecollisiongrid': 'the renderer has no overlay of the collision grid yet',
    'toggleborders': 'the renderer has no overlay of the cell borders yet',
    'togglefogofwar': 'the map screen reveals places one by one from ShowMap; it has no fog of war to switch off',
    'togglefullhelp': 'the aim box shows the name only; it has no extended reference readout to switch on',
    'testcells': 'loading every exterior cell in turn: a test of a desktop engine, far beyond a 32 MB machine',
    'testinteriorcells': 'loading every interior cell in turn: a test of a desktop engine, far beyond a 32 MB machine',
}
# the interpreter's own opcodes (functions.RUN) the console carries by name in aw_mwhost.c console_special, with the
# host function each one calls
SPECIAL = {'lock': 'host_object', 'unlock': 'host_object', 'getlocked': 'host_object', 'activate': 'host_object',
           'startcombat': 'host_combat', 'stopcombat': 'host_combat', 'getdeadcount': 'host_dead_count',
           'getcurrentaipackage': 'host_ai_package', 'getaipackagedone': 'host_ai_package', 'getspell': 'host_spell',
           'getcommondisease': 'host_spell', 'getblightdisease': 'host_spell', 'getdistance': 'host_distance'}

def function_rows():
    """The console's function table (AWMF1), from the compiler's own table (tools/mwscript/functions.py): per line
    the name, the kind (host: the host's call by NUMBER with the arguments typed by ARGS; actor: host_actor VERB STAT;
    special: aw_mwhost.c console_special), the number, the return letter and the argument letters."""
    sys.path.insert(0, str(ROOT / 'tools'))
    from mwscript import functions as F
    rows = []
    for name in sorted(F.FUNCTIONS):
        fn = F.FUNCTIONS[name]
        if name in F.ACTOR_CALLS:
            verb, stat = F.ACTOR_CALLS[name]
            rows.append('%s actor %d %d %s' % (name, verb, stat, fn.ret))
        elif name in F.HOST and name not in COMPILED_ARGUMENTS:
            rows.append('%s host %d %s %s' % (name, fn.number, fn.ret, fn.args or '-'))
        elif name in SPECIAL:
            rows.append('%s special %d %s %s' % (name, fn.number, fn.ret, fn.args or '-'))
    return rows


def help_text(data):
    """id1/mwconsole-help.txt: what dbg help mw pages from the disk (engine aw_console.c mwhelp_page), one line a
    command that works, then the collisions; AWMH1 first."""
    out = ['AWMH1', 'The original game\'s console commands in AmiWind (any case; target first: id->Command;',
           'without one: the dbg mw target, else the player). The table: docs/CONSOLE_COMMANDS_MORROWIND.md', '']
    for r in data['commands']:
        if r['state'] in ('alias', 'vm'):
            names = r['name'] + (' / ' + r['short'] if r.get('short') else '')
            out.append(' %s: %s' % (names, r['amiwind'].split(' (')[0] if r['state'] == 'alias' else 'runs'))
    out += ['', 'AmiWind\'s own command of the same name (kept):']
    out += [' %s' % r['name'] for r in data['commands'] if r['state'] == 'collision']
    return '\n'.join(out) + '\n'


def main(argv):
    if argv[:1] == ['render']:
        version = (ROOT / 'VERSION').read_text(encoding='utf-8').strip()
        print('wrote %s: %s' % (PAGE.relative_to(ROOT), render('v' + version.lstrip('v'))))
        return 0
    if argv[:1] == ['counts']:
        print(counts())
        return 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
