#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Every output map against the engine's per-map tables (BUILD-BUDGET-ENGINE-LIMITS-35).

A town config's "entity_budget" (1000) and "model_budget" (220) were checked per town region against
numbers the engine never had: the engine holds MAX_EDICTS edicts (quakedef.h; ED_Alloc stops the game
with "no free edicts" when the map spawns more), MAX_MODELS model precaches (the BSP's inline models,
the world itself and every .mdl/.spr/.bsp the QuakeC precaches: PF_precache_model overflow) and
MAX_SOUNDS sound precaches. This module counts a finished map the way the engine spawns it and
compares it with those defines (tools/engine_limits.py), so a map that cannot load never ships:

- edicts at the load peak: the world (edict 0), one client slot per player (single player: 1, as
  Host_FindMaxClients sets), every map entity whose spawn function keeps its edict, one slot for the
  entities that free theirs at once (makestatic/remove; ED_Alloc reuses the freed slot during the
  load), and the edicts engine code allocates later in the scene (runtime_edicts);
- model precaches: slot 0 (empty), the world, its inline models *1..*N, the models the worldspawn
  function precaches, every model a spawn function precaches through precache_model(self.model), and
  the model slot engine code may add at run time (RUNTIME_MODELS), and each actor model's carried items
  (<model>.tag) and animation sounds (<model>.anm), which builtin #81 precaches at spawn;
- sound precaches: slot 0 and every sound a spawn function precaches through precache_sound(self.<key>);
- leaves: the BSP's leaf count against MAX_MAP_LEAFS (bspfile.h; the PVS buffers are sized by it);
- static entities: every entity whose spawn function calls makestatic (cl_parse.c "Too many static
  entities");
- scenery: on a converted town's region maps (town table flag AW_TOWN_SCENERY, aw_town.h) the engine
  takes every func_wall into its scenery catalogue instead of an edict (aw_scenery.c AW_SceneryCapture),
  except the ones a harvest catalogue binds (they stay edicts). The catalogue holds
  AW_SCENERY_MAX_PLACEMENTS (a Host_Error above it) and is linked into cl_visedicts after the edicts in
  one go (AW_SceneryLink: a Host_Error when catalogue + edicts pass MAX_VISEDICTS).

The spawn functions and the fixed precaches are read from the QuakeC source (engine/aga/qc/world.qc),
never copied: a new spawn function or precache changes the count the day it is written. A config
budget may only tighten these limits (budget_room, check_config_budgets)."""
import json
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_limits  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
QC_SOURCE = ROOT / 'engine/aga/qc/world.qc'
CLIENT_SLOTS = 1            # host.c Host_FindMaxClients: single player has one client edict
# Edicts engine code allocates in a running scene, outside the map's entity list: the test companion
# (aw_companion.c spawn_test), the arena opponent (aw_arena.c AW_ArenaEntities) and the weapon and shield of
# every hostile NPC (aw_items.c AW_ItemsShow: aw_combat.c SLOTS hostiles x AW_ITEMS_KINDS items). The NPC
# gallery allocates its own on its own map and refuses gracefully. tests/test_map_engine_limits.py counts the
# ED_Alloc calls in the engine source and fails when a new one is not counted here.


def runtime_edicts(source=None):
    src = source or engine_limits.SOURCE
    return 2 + engine_limits.define('aw_combat.c', 'SLOTS', src) * engine_limits.define('aw_items.h', 'AW_ITEMS_KINDS', src)


# Model precache slots engine code may add at run time: the arena opponent's model (aw_arena.c; it
# reports "model table full" instead of failing, but the gate keeps its slot free).
RUNTIME_MODELS = 1
TOWN_TABLE = ROOT / 'engine/aga/src/aw_town_table.h'
ENTITY = re.compile(r'\{([^{}]*)\}')
FIELD = re.compile(r'"([^"\n]*)"\s+"([^"\n]*)"')


def _bodies(text):
    """{name: body} of every QuakeC function written as void() name = { ... };"""
    text = re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S)
    out = {}
    for match in re.finditer(r'void\s*\(\s*\)\s*(\w+)\s*=\s*\{', text):
        depth, i = 1, match.end()
        while depth and i < len(text):
            depth += {'{': 1, '}': -1}.get(text[i], 0)
            i += 1
        out[match.group(1)] = text[match.end():i - 1]
    return out


_CACHE = {}


def spawn_rules(qc_text=None):
    """What each spawn function does with its edict and precaches, read from the QuakeC:
    {'functions': {name: {'keeps_edict', 'static', 'model_from_self', 'sounds_from_self'}},
     'worldspawn_models': [...], 'worldspawn_sounds': [...]}"""
    if qc_text is None:
        if 'rules' not in _CACHE:
            _CACHE['rules'] = spawn_rules(QC_SOURCE.read_text(encoding='utf-8'))
        return _CACHE['rules']
    rules = {}
    for name, body in _bodies(qc_text).items():
        frees = bool(re.search(r'\b(makestatic|remove)\s*\(\s*self\s*\)', body))
        rules[name] = {'keeps_edict': not frees,
                       'static': bool(re.search(r'\bmakestatic\s*\(\s*self\s*\)', body)),
                       'model_from_self': bool(re.search(r'\bprecache_model\s*\(\s*self\.model\s*\)', body)),
                       'sounds_from_self': sorted(set(re.findall(r'\bprecache_sound\s*\(\s*self\.(\w+)\s*\)', body))),
                       # builtin #81: the model's <model>.anm sounds and <model>.tag items (aw_anim.c, aw_items.c)
                       'animprep': bool(re.search(r'\baw_animprep\s*\(\s*self\s*\)', body))}
    world = _bodies(qc_text).get('worldspawn', '')
    return {'functions': rules,
            'worldspawn_models': sorted(set(re.findall(r'precache_model\s*\(\s*"([^"]+)"\s*\)', world))),
            'worldspawn_sounds': sorted(set(re.findall(r'precache_sound\s*\(\s*"([^"]+)"\s*\)', world)))}


def scenery_towns(text=None):
    """{prefix: (town name, region cap)} of the towns whose region maps use the scenery catalogue, read
    from the engine's generated town table (aw_town_table.h AW_TOWN_ROWS, flag AW_TOWN_SCENERY)."""
    if text is None:
        if 'towns' not in _CACHE:
            _CACHE['towns'] = scenery_towns(TOWN_TABLE.read_text(encoding='utf-8'))
        return _CACHE['towns']
    row = re.compile(r'\{"([^"]*)","[^"]*","([^"]*)","[^"]*","[^"]*","[^"]*",(-?\d+),-?\d+,-?\d+,([A-Z_|0-9]+),')
    return {m.group(2): (m.group(1), int(m.group(3))) for m in row.finditer(text) if 'AW_TOWN_SCENERY' in m.group(4)}


def scenery_map(name, towns=None):
    """True when the engine captures NAME's func_walls (aw_scenery.c AW_SceneryMapEnabled: the town's
    own map name, or its prefix + 3 digits below the region cap)."""
    towns = scenery_towns() if towns is None else towns
    if any(name == town for town, _ in towns.values()):
        return True
    if len(name) == 5 and name[2:].isdigit() and name[:2] in towns:
        return int(name[2:]) < towns[name[:2]][1]
    return False


def harvest_plants(path):
    """The plant count of a harvest catalogue (AWH1-AWH4 header: nodes edges plants ...), 0 without one.
    Each bound plant keeps its func_wall as an edict (aw_harvest_runtime.c AW_HarvestProtect)."""
    try:
        header = Path(path).read_text(encoding='ascii', errors='replace').split(chr(10), 1)[0].split()
        return int(header[3]) if header and header[0].startswith('AWH') else 0
    except (OSError, IndexError, ValueError):
        return 0


def limits(source=None):
    """The engine's per-map tables and the room a map's own entities and models have in them."""
    src = source or engine_limits.SOURCE
    rules = spawn_rules()
    values = {'max_edicts': engine_limits.define('quakedef.h', 'MAX_EDICTS', src),
              'max_models': engine_limits.define('quakedef.h', 'MAX_MODELS', src),
              'max_sounds': engine_limits.define('quakedef.h', 'MAX_SOUNDS', src),
              'max_static_entities': engine_limits.define('client.h', 'MAX_STATIC_ENTITIES', src),
              'max_scenery': engine_limits.define('aw_town.h', 'AW_SCENERY_MAX_PLACEMENTS', src),
              'max_leafs': engine_limits.define('bspfile.h', 'MAX_MAP_LEAFS', src)}
    values['max_visedicts'] = values['max_edicts'] + values['max_static_entities']
    # world + client slots + one reused slot for freed entities + runtime edicts
    values['runtime_edicts'] = runtime_edicts(src)
    values['fixed_edicts'] = 1 + CLIENT_SLOTS + 1 + values['runtime_edicts']
    # slot 0 + the world + the worldspawn function's own precaches + runtime models
    values['fixed_models'] = 2 + len(rules['worldspawn_models']) + RUNTIME_MODELS
    values['entity_room'] = values['max_edicts'] - values['fixed_edicts']
    values['model_room'] = values['max_models'] - values['fixed_models']
    return values


def entities(data):
    """Entity dicts of a BSP29 map, in file order, and its model count."""
    return _entities(data)[:2]


def _entities(data):
    version, offset, size = struct.unpack_from('<iii', data, 0)
    if version != 29:
        raise ValueError('not a BSP29 map')
    leafs_offset, leafs_size = struct.unpack_from('<ii', data, 4 + 10 * 8)
    models_offset, models_size = struct.unpack_from('<ii', data, 4 + 14 * 8)
    if (models_size % 64 or leafs_size % 28 or models_offset + models_size > len(data) or offset + size > len(data)
            or leafs_offset + leafs_size > len(data)):
        raise ValueError('damaged BSP lumps')
    text = bytes(data[offset:offset + size]).decode('latin-1').split('\0', 1)[0]
    return [dict(FIELD.findall(block)) for block in ENTITY.findall(text)], models_size // 64, leafs_size // 28


def model_extras(id1, model, cache=None):
    """(sounds, item models) an actor model adds at spawn through aw_animprep (#81), read from the payload:
    the '~EVENT:DRY:WADE:SWIM' sound words of <model>.anm (aw_anim.c AW_AnimParse) and the weapon and shield
    lines of <model>.tag (aw_items.c AW_ItemsParse; '-' = none) and the '>PATH' mover model of the layout
    (aw_anim.c, registered by name at spawn) with its own layout's sounds. Empty without the files."""
    if id1 is None or not model.endswith('.mdl'):
        return set(), set()
    if cache is not None and model in cache:
        return cache[model]
    sounds, items = set(), set()
    base = Path(id1) / model[:-4]
    try:
        for word in base.with_suffix('.anm').read_text(encoding='latin-1').split():
            if word.startswith('~') and ':' in word:
                sounds |= {name for name in word.split(':')[1:4] if name}
            elif word.startswith('>') and word.endswith('.mdl') and len(word) > 5:
                # the mover model (aw_anim.c lazy_index): registered by name at spawn, its own layout's
                # sounds and its own item tags' models (aw_items.c AW_ItemsPrep) precached with it
                items.add(word[1:])
                if word[1:] != model:
                    mover_sounds, mover_items = model_extras(id1, word[1:])
                    sounds |= mover_sounds
                    items |= mover_items
    except OSError:
        pass
    try:
        lines = base.with_suffix('.tag').read_text(encoding='latin-1').splitlines()
        if lines and lines[0].startswith('AWTG1 '):
            for line in lines[1:3]:
                kind, _, path = line.rstrip('\r').partition(' ')
                if kind in ('weapon', 'shield') and path and path != '-':
                    items.add(path)
    except OSError:
        pass
    if cache is not None:
        cache[model] = (sounds, items)
    return sounds, items


def count(data, rules=None, scenery=False, plants=0, id1=None, extras_cache=None):
    """What one map uses of the engine's tables when it loads (see the module doc). scenery: the engine
    captures the map's func_walls (scenery_map); plants: its harvest catalogue's plant count; id1: the
    payload folder, for the actor models' animation sounds and carried items (model_extras)."""
    rules = rules or spawn_rules()
    rows, models, leafs = _entities(data)
    functions = rules['functions']
    kept = freed = statics = walls = 0
    model_names = {'*%d' % i for i in range(1, models)} | set(rules['worldspawn_models'])
    sound_names = set(rules['worldspawn_sounds'])
    unknown = {}
    for row in rows:
        name = row.get('classname', '')
        if name == 'worldspawn':
            continue
        rule = functions.get(name)
        if scenery and name == 'func_wall':
            walls += 1
            continue
        if rule is None:            # no spawn function: ED_LoadFromFile frees the edict
            freed += 1
            unknown[name] = unknown.get(name, 0) + 1
            continue
        if rule['keeps_edict']:
            kept += 1
        else:
            freed += 1
        statics += rule['static']
        if rule['model_from_self'] and row.get('model'):
            model_names.add(row['model'])
        if rule.get('animprep') and row.get('model'):
            extra_sounds, extra_models = model_extras(id1, row['model'], extras_cache)
            sound_names |= extra_sounds
            model_names |= extra_models
        for key in rule['sounds_from_self']:
            if row.get(key):
                sound_names.add(row[key])
    bound = min(walls, plants)          # harvest-bound func_walls stay edicts
    kept += bound
    edicts = 1 + CLIENT_SLOTS + kept + (1 if freed else 0) + runtime_edicts()
    return {'entities': len(rows) - 1 if rows else 0, 'edicts_kept': kept, 'edicts_freed': freed,
            'scenery': walls - bound, 'visedicts_at_scenery_link': walls - bound + edicts if walls else 0,
            'edicts_peak': edicts, 'models': 1 + 1 + len(model_names) + RUNTIME_MODELS,
            'inline_models': max(0, models - 1), 'leafs': leafs, 'sounds': 1 + len(sound_names), 'static_entities': statics,
            'no_spawn_function': dict(sorted(unknown.items()))}


def check(data, name='map', table=None, rules=None, scenery=None, plants=0, id1=None, extras_cache=None):
    """(refusals, counts) of one map: a refusal per engine table the map does not fit. scenery: None =
    from the map name and the engine's town table."""
    table = table or limits()
    counts = count(data, rules, scenery_map(name) if scenery is None else scenery, plants, id1, extras_cache)
    refused = []
    for key, limit, label in (('edicts_peak', table['max_edicts'], 'MAX_EDICTS'),
                              ('scenery', table['max_scenery'], 'AW_SCENERY_MAX_PLACEMENTS'),
                              ('visedicts_at_scenery_link', table['max_visedicts'], 'MAX_VISEDICTS'),
                              ('models', table['max_models'], 'MAX_MODELS'),
                              ('sounds', table['max_sounds'], 'MAX_SOUNDS'),
                              ('leafs', table['max_leafs'], 'MAX_MAP_LEAFS'),
                              ('static_entities', table['max_static_entities'], 'MAX_STATIC_ENTITIES')):
        if counts[key] > limit:
            refused.append('%s: %d %s, the engine holds %d (%s)' % (name, counts[key], key.replace('_', ' '),
                                                                    limit, label))
    return refused, counts


def audit_maps(maps_dir, skip=()):
    """The report of every map in MAPS_DIR (*.bsp, less the file names in SKIP) against the engine's
    tables, refusals listed."""
    table, rules, towns = limits(), spawn_rules(), scenery_towns()
    rows, refused, unreadable, extras = {}, [], {}, {}
    for path in sorted(Path(maps_dir).glob('*.bsp')):
        if path.name in skip:
            continue
        try:
            errors, counts = check(path.read_bytes(), path.stem, table, rules, scenery_map(path.stem, towns),
                                   harvest_plants(Path(maps_dir).parent / ('harvest-%s.txt' % path.stem)),
                                   Path(maps_dir).parent, extras)
        except (ValueError, struct.error) as exc:
            # Not a BSP29 map (a placeholder): the BSP gates (heap audit, optimizer) own the file's form.
            unreadable[path.stem] = str(exc)
            continue
        rows[path.stem] = counts
        refused += errors
    worst = {}
    for key, limit in (('edicts_peak', 'max_edicts'), ('models', 'max_models'), ('sounds', 'max_sounds'),
                       ('static_entities', 'max_static_entities'), ('scenery', 'max_scenery'), ('leafs', 'max_leafs'),
                       ('visedicts_at_scenery_link', 'max_visedicts')):
        ranked = sorted(((c[key], n) for n, c in rows.items() if key in c), reverse=True)[:5]
        worst[key] = {'limit': table[limit], 'top': [{'map': n, 'value': v, 'headroom': table[limit] - v}
                                                     for v, n in ranked]}
    return {'limits': table, 'maps': len(rows), 'refused': refused, 'worst': worst, 'unreadable': unreadable,
            'per_map': rows}


def check_maps(maps_dir, report_path=None, skip=()):
    """Every map in MAPS_DIR (*.bsp, less SKIP) against the engine's tables. Raises ValueError listing
    every map that does not fit; returns the report (worst headroom per table first)."""
    report = audit_maps(maps_dir, skip)
    refused = report['refused']
    if report_path is not None:
        Path(report_path).write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8', newline='\n')
    if refused:
        raise ValueError('%d map(s) do not fit the engine (BUILD-BUDGET-ENGINE-LIMITS-35):\n  ' % len(refused) +
                         '\n  '.join(refused[:20]) + ('\n  and %d more' % (len(refused) - 20) if len(refused) > 20 else ''))
    return report


def scenery_settings(settings):
    """True when a town config's region maps use the engine's scenery catalogue (its map prefix is a
    scenery town's in the engine's town table)."""
    town = settings.get('town') or {}
    return town.get('map_prefix') in scenery_towns()


def budget_room(settings, table=None, scenery=None):
    """(entity budget, model budget) a town region may use: the config's, which may only tighten the
    engine's room; ValueError when a config asks for more than the engine holds.
    Entities: a scenery town's placements go to the scenery catalogue (AW_SCENERY_MAX_PLACEMENTS); any
    other town's are edicts (MAX_EDICTS less the fixed edicts). Models: MAX_MODELS less the fixed
    precaches (the NPC models of a region are counted on the finished map by check/check_maps)."""
    table = table or limits()
    scenery = scenery_settings(settings) if scenery is None else scenery
    room, what = ((table['max_scenery'], 'the scenery catalogue AW_SCENERY_MAX_PLACEMENTS') if scenery else
                  (table['entity_room'], 'MAX_EDICTS %d less %d fixed edicts' % (table['max_edicts'],
                                                                                 table['fixed_edicts'])))
    problems = []
    if int(settings['entity_budget']) > room:
        problems.append('entity_budget %s exceeds the engine room %d (%s)' % (settings['entity_budget'], room, what))
    if int(settings['model_budget']) > table['model_room']:
        problems.append('model_budget %s exceeds the engine room %d (MAX_MODELS %d less %d fixed models)' % (
            settings['model_budget'], table['model_room'], table['max_models'], table['fixed_models']))
    if problems:
        raise ValueError('Town budget above the engine limits (BUILD-BUDGET-ENGINE-LIMITS-35): ' + '; '.join(problems))
    return int(settings['entity_budget']), int(settings['model_budget'])


def check_config_budgets(config_dir=ROOT / 'config'):
    """Every config/*.json that states an entity or model budget, through budget_room. Returns
    {file: (entity budget, model budget)}; ValueError names every file over the engine."""
    out, errors = {}, []
    for path in sorted(Path(config_dir).glob('*.json')):
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except ValueError:
            continue
        if not isinstance(data, dict) or not ({'entity_budget', 'model_budget'} & set(data)):
            continue
        try:
            out[path.name] = budget_room({'entity_budget': data.get('entity_budget', 0),
                                          'model_budget': data.get('model_budget', 0), 'town': data.get('town')})
        except ValueError as exc:
            errors.append('%s: %s' % (path.name, exc))
    if errors:
        raise ValueError('\n'.join(errors))
    return out


def main(argv=None):
    import argparse
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('maps', type=Path, help='a maps folder (or one .bsp)')
    p.add_argument('--report', type=Path)
    a = p.parse_args(argv)
    if a.maps.is_file():
        refused, counts = check(a.maps.read_bytes(), a.maps.stem,
                                plants=harvest_plants(a.maps.parent.parent / ('harvest-%s.txt' % a.maps.stem)),
                                id1=a.maps.parent.parent)
        print(json.dumps({'refused': refused, 'counts': counts}, indent=1))
        return 1 if refused else 0
    report = audit_maps(a.maps)
    if a.report:
        a.report.write_text(json.dumps(report, indent=1) + chr(10), encoding='utf-8', newline=chr(10))
    print(json.dumps({'limits': report['limits'], 'maps': report['maps'], 'worst': report['worst'],
                      'refused': report['refused']}, indent=1))
    return 1 if report['refused'] else 0


if __name__ == '__main__':
    sys.exit(main())
