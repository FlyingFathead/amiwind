# SPDX-License-Identifier: GPL-3.0-only
"""The state of a player who has walked out of the Census and Excise Office, read from the game's own scripts
(DBG-HORS-AFTER-CENSUS-67): the script AW_AfterCensus that the bare 'dbg aw hors' starts once.

config/after-census.json names the scripts of the one required path out of the office and the speaker whose dialogue
results run on it (Sellus Gravius). Everything the generated script does is read from those, by these rules:
- each placed object that carries a path script gets that script's locals at the last value the script sets them to
  (`set "<object>".<local> to <value>`), unless the config names the statement that gives the after value; the locals
  the engine itself sets (OnActivate, OnPCAdd, OnPCEquip) and those that end at 0 are left alone;
- every lasting switch (EnablePlayerControls, -Fighting, -Magic, -Jumping, -ViewSwitch, EnableVanityMode, the menus
  EnableStatsMenu, -InventoryMenu, -MagicMenu, -MapMenu, EnableRest) at its last Enable or Disable along the path; the
  registration's own windows (EnableClassMenu and the like) are left out, they open a window and keep nothing;
- every global at its last Set along the path (CharGenState -1 from the exit door's script), every StartScript,
  every Unlock, Disable and Enable of a named object, in path order;
- an item a path script belongs to and that lies placed in the world (the papers, the dagger) is taken: it goes into
  the player's inventory and its placement out (Disable); an item held in a container (Fargoth's ring in the courtyard
  barrel) is taken by the engine's own route for that container (aw_state.c AW_CourtyardTakeRing), never twice;
- the speaker's dialogue results run as he runs them, every effect line of each result except the functions the config
  skips (his ShowMap answer about Balmora); a Set of one of his own locals becomes a Set on him.

The script ends with StopScript, so it runs once. A script, a local, a statement or a speaker the config names that the
game data does not have stops the build (ValueError), naming it. compiler.compile_program compiles it like any script.
"""
import json
import re
from pathlib import Path

SCRIPT_ID = 'AW_AfterCensus'
CONFIG = Path(__file__).resolve().parents[2] / 'config' / 'after-census.json'
ENGINE_LOCALS = {'onactivate', 'onpcadd', 'onpcequip', 'onpcdrop', 'onpcsoulgemuse', 'onpcrepair', 'onknockout',
                 'onmurder', 'ondeath', 'pcskipequip'}
SWITCHES = {'playercontrols', 'playerfighting', 'playermagic', 'playerjumping', 'playerviewswitch', 'playerlooking',
            'vanitymode', 'statsmenu', 'inventorymenu', 'magicmenu', 'mapmenu', 'rest'}
ITEM_TYPES = {'BOOK', 'WEAP', 'CLOT', 'ARMO', 'MISC', 'INGR', 'ALCH', 'APPA', 'LOCK', 'PROB', 'REPA', 'LIGH'}
RESULT_FUNCTIONS = {'journal', 'additem', 'removeitem', 'addtopic', 'set', 'enable', 'disable', 'unlock', 'startscript'}
DECLARATION = re.compile(r'^(short|long|float)\s+(\w+)', re.I)
SET = re.compile(r'^set\s+(\w+)\s+to\s+(-?\d+(?:\.\d+)?)\s*$', re.I)
OBJECT_CALL = re.compile(r'^"?([^"]+?)"?\s*->\s*(\w+)\s*$')


def code_lines(text):
    """The statements of a script's text: comments and blank lines out, whitespace folded."""
    for raw in text.replace('\r\n', '\n').split('\n'):
        line = raw.split(';', 1)[0].strip()
        if line:
            yield ' '.join(line.split())


def first_word(line):
    return re.split(r'[\s,(]', line, 1)[0].casefold()


def load_config(path=None):
    return json.loads(Path(path or CONFIG).read_text(encoding='utf-8'))


def _placed_objects(data, script):
    """The record ids (as spelt in the game data) of the placed objects that carry SCRIPT (folded), with their types."""
    out = {}
    for r in data.references:
        if r['script'] == script:
            out.setdefault(r['id'], data.bases.get(r['id'].casefold(), ('', ''))[0])
    return sorted(out.items(), key=lambda kv: kv[0].casefold())


def _holder_of(data, item):
    """1 when a placed container of the game holds ITEM (folded) in its record."""
    for h in data.holder_refs:
        if h.get('type') == 'CONT' and item in data.holdings.get(h['id'], []):
            return True
    return False


def generate(data, config=None):
    """(script text, report) of AW_AfterCensus from DATA (mwscript.gamedata.GameData) and the path CONFIG."""
    cfg = config if config is not None else load_config()
    windows = {w.casefold() for w in cfg.get('window_openers', [])}
    skip = {f.casefold() for f in cfg.get('skip_functions', [])}
    overrides = {k.casefold(): v for k, v in cfg.get('local_values', {}).items()}
    sets, switches, calls, takes, sources = [], {}, [], [], []
    globals_final = {}
    used_overrides = set()
    for name in cfg['scripts']:
        script = data.scripts.get(name.casefold())
        if script is None:
            raise ValueError('after census: the path script %s is not in the game data' % name)
        lines = list(code_lines(script.text))
        locals_ = [m.group(2) for m in (DECLARATION.match(l) for l in lines) if m]
        last = {}
        for line in lines:
            m = SET.match(line)
            if m and m.group(1).casefold() in {v.casefold() for v in locals_}:
                last[m.group(1).casefold()] = m.group(2)
            elif m and m.group(1).casefold() in data.globals:
                globals_final[m.group(1).casefold()] = (data.globals[m.group(1).casefold()][2], m.group(2), name)
            word = first_word(line)
            if word in windows:
                continue
            sw = re.match(r'^(enable|disable)(\w+)$', word)
            if sw and sw.group(2) in SWITCHES:
                switches.pop(sw.group(2), None)          # the last call wins, in path order
                switches[sw.group(2)] = (line.split()[0], name)
            elif word == 'startscript':
                calls.append((line, name))
            o = OBJECT_CALL.match(line)
            if o and o.group(2).casefold() in ('unlock', 'disable', 'enable') and not o.group(1).casefold() == 'player':
                calls.append(('"%s"->%s' % (o.group(1), o.group(2)), name))
        for local in locals_:
            key = '%s.%s' % (name.casefold(), local.casefold())
            if local.casefold() in ENGINE_LOCALS:
                continue
            value = last.get(local.casefold())
            if key in overrides:
                m = SET.match(' '.join(overrides[key].split()))
                if not m or m.group(1).casefold() != local.casefold() or \
                        ' '.join(overrides[key].split()).casefold() not in {l.casefold() for l in lines}:
                    raise ValueError('after census: %s has no statement %r' % (name, overrides[key]))
                value = m.group(2)
                used_overrides.add(key)
            if value is None or float(value) == 0:
                continue
            for obj, kind in _placed_objects(data, name.casefold()):
                if kind in ITEM_TYPES:
                    continue                                   # a taken item's script: its copy goes with it
                sets.append(('set "%s".%s to %s' % (obj, local, value), name))
        record = [(rid, t) for rid, (t, s) in data.bases.items() if s == name.casefold() and t in ITEM_TYPES]
        for rid, kind in record:
            placed = _placed_objects(data, name.casefold())
            if placed:
                for obj, _ in placed:
                    takes.append(('player->AddItem "%s" 1' % obj, name))
                    takes.append(('"%s"->Disable' % obj, name))
            elif _holder_of(data, rid):
                sources.append({'script': name, 'item': rid, 'taken': 'by the engine\'s route for its container'})
    missing = set(overrides) - used_overrides
    if missing:
        raise ValueError('after census: local_values names what the path does not have: %s' % ', '.join(sorted(missing)))
    speaker = cfg['speaker'].casefold()
    results = [text for (who, text) in data.results if who == speaker]
    if not results:
        raise ValueError('after census: no dialogue results of %s' % cfg['speaker'])
    speaker_locals = set()
    for (rid, (t, s)) in data.bases.items():
        if rid == speaker and s in data.scripts:
            speaker_locals = {m.group(2).casefold() for m in (DECLARATION.match(l) for l in
                              code_lines(data.scripts[s].text)) if m}
    said = []
    for text in results:
        for line in code_lines(text):
            word = first_word(line.split('->', 1)[-1].strip()) if '->' in line else first_word(line)
            if word in skip or word not in RESULT_FUNCTIONS:
                continue
            m = SET.match(line)
            if m and m.group(1).casefold() in speaker_locals:
                line = 'set "%s".%s to %s' % (cfg['speaker'], m.group(1), m.group(2))
            said.append((line, 'the dialogue results of %s' % cfg['speaker']))
    # an item the path takes and the speaker takes back (the papers handed in): neither, so its pick-up script never
    # sees it arrive; its placement still goes out
    for line, _ in list(said):
        m = re.match(r'^player\s*->\s*removeitem\s*,?\s*"([^"]+)"\s*,?\s*1$', line, re.I)
        add = m and 'player->AddItem "%s" 1' % m.group(1)
        hit = next((t for t in takes if m and t[0].casefold() == add.casefold()), None)
        if hit:
            takes.remove(hit)
            said = [s for s in said if s[0] != line]
            sources.append({'item': m.group(1), 'taken': 'picked up and handed back on the path: placement out only'})
    body = []
    for _, (spelt, value, name) in sorted(globals_final.items()):
        body.append(('set %s to %s' % (spelt, value), name))
    body += sets
    body += [(word, name) for word, name in switches.values() if word.casefold().startswith('enable')]
    body += calls + takes + said
    lines = ['begin %s' % SCRIPT_ID,
             '; generated by tools/mwscript/aftercensus.py from the game\'s own scripts (config/after-census.json)']
    lines += [stmt for stmt, _ in body]
    lines += ['StopScript %s' % SCRIPT_ID, 'end %s' % SCRIPT_ID]
    report = {'script': SCRIPT_ID, 'statements': [{'line': s, 'from': n} for s, n in body],
              'switches_left_off': sorted(w for w, _ in switches.values() if w.casefold().startswith('disable')),
              'taken_elsewhere': sources}
    return '\n'.join(lines) + '\n', report


def inject(data, config=None):
    """Add AW_AfterCensus to DATA's scripts (compiled with the others); its report. None when the game data has none of
    the path (a test master without the opening): nothing added."""
    from .gamedata import Script
    cfg = config if config is not None else load_config()
    if not any(n.casefold() in data.scripts for n in cfg['scripts']):
        return None
    text, report = generate(data, cfg)
    raw = text.encode('cp1252', 'replace')
    data.scripts[SCRIPT_ID.casefold()] = Script(SCRIPT_ID, 'AmiWind', text, len(raw), 0, {}, [])
    return report
