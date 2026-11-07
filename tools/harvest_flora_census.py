#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Every harvestable plant of the game's masters against what this build makes harvestable (FLORA-FAUNA-COVERAGE-62).

Reads the masters the player owns (never written anywhere public; the census itself only counts), lists every
organic container record (FLAG bit 1: the plants, fungi, egg sacks, shells and ore the original lets the player
harvest) and its placements per region, and classifies each record by config/harvest-flora.json:

- harvestable: its kind is a harvest kind (prepare_harvest.HARVEST_KINDS). Every placement of it in the base master
  must be a placement of the harvest source or be listed by the source with the reason it stays scenery;
- pending: not harvestable yet, with the register entry that tracks it;
- not_flora: an ordinary container that carries the organic flag, tracked elsewhere.

check() names every organic record that no group covers, every harvestable placement the harvest source neither
places nor lists, and every master read that the config does not name: the build stops on any of them, so no kind of
plant is ever left out silently. The harvest builder step runs it (harvest_build.prepare) and keeps the census
beside its receipt; `--data-files DIR [--json OUT]` prints it for an audit.
"""
import argparse
from collections import Counter
import fnmatch
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

CONFIG = ROOT / 'config/harvest-flora.json'
FORMAT = 'AmiWind harvest flora census 1'
STATUSES = ('harvestable', 'pending', 'not_flora')


def load_config(path=None):
    config = json.loads(Path(path or CONFIG).read_text(encoding='utf-8'))
    if config.get('format') != 1:
        raise ValueError('Unsupported harvest flora config')
    from prepare_harvest import HARVEST_KINDS
    names, kinds = set(), set()
    for group in config['groups']:
        if group['name'] in names or group.get('status') not in STATUSES:
            raise ValueError('Harvest flora group duplicate or with an unknown status: ' + group['name'])
        names.add(group['name'])
        if group['status'] == 'harvestable':
            if group.get('kind') not in HARVEST_KINDS or group.get('ids'):
                raise ValueError('A harvestable group names one harvest kind and no ids: ' + group['name'])
            kinds.add(group['kind'])
        elif not group.get('ids') or not group.get('register'):
            raise ValueError('A pending or not_flora group names its ids and its register entry: ' + group['name'])
    if kinds != set(HARVEST_KINDS):
        raise ValueError('Every harvest kind has its harvestable group: ' + ', '.join(sorted(set(HARVEST_KINDS) - kinds)))
    masters = [m['name'] for m in config['masters']]
    if not masters or masters[0] != 'Morrowind.esm' or config['masters'][0].get('status') != 'read' or \
            any(m.get('status') != 'pending' or not m.get('register') for m in config['masters'][1:]):
        raise ValueError('The base master is read; every other master is pending with its register entry')
    return config


def record_kind(model):
    from world_flora import flora_kind, harvest_only_kind
    from prepare_harvest import HARVEST_KINDS
    kind = flora_kind(model) or harvest_only_kind(model)
    return kind if kind in HARVEST_KINDS else None


def classify(config, record_id, model):
    """The group of one organic record: a harvest kind's group by its model, else the first group whose id patterns
    match (case-folded); None for none."""
    kind = record_kind(model)
    for group in config['groups']:
        if kind is not None and group.get('kind') == kind:
            return group
        if kind is None and any(fnmatch.fnmatchcase(record_id, pattern.casefold()) for pattern in group.get('ids', ())):
            return group
    return None


def master_census(raw, known=None):
    """({record id: {model, name, flags}} of the organic containers this master defines (with `known`: those of the
    masters read before it, which its cells may place), [placements]): each placement is (record id, region or
    'interior', cell, reference number)."""
    from mwad.audit import cell_data, normpath, records, string, subrecords
    organic = dict(known or {})
    cells = []
    for tag, flags, payload in records(raw):
        if tag == 'CELL':
            if not flags & 0x20:
                cells.append(cell_data(list(subrecords(payload))))
        elif tag == 'CONT':
            fields = dict(subrecords(payload))
            if 'NAME' not in fields:
                continue
            record_id = string(fields['NAME']).casefold()
            flag = struct.unpack('<I', fields['FLAG'])[0] if len(fields.get('FLAG', b'')) == 4 else 0
            if 'DELE' in fields or flags & 0x20 or not flag & 1:
                organic.pop(record_id, None)
                continue
            organic[record_id] = dict(model=normpath(string(fields.get('MODL', b''))),
                                      name=string(fields.get('FNAM', b'')), flags=flag)
    placements = []
    for cell in cells:
        inside = bool(cell['flags'] & 1)
        for ref in cell['refs']:
            record_id = ref.get('id', '').casefold()
            if record_id in organic and not ref.get('deleted'):
                placements.append((record_id, 'interior' if inside else (cell.get('region') or 'no region'),
                                   cell['name'] if inside else [cell['x'], cell['y']], ref['number']))
    return organic, placements


def census(masters, config=None, harvest=None):
    """The census of `masters` ([(name, raw bytes)], the base master first). harvest: None, or the harvest source's
    {'numbers': set of placed reference numbers, 'refused': {reference number: reason}} of the base master, to check
    that every placement of a harvestable group is placed or listed."""
    config = config or load_config()
    statuses = {m['name']: m for m in config['masters']}
    groups = {g['name']: dict(name=g['name'], status=g['status'], register=g.get('register'), kind=g.get('kind'),
                              records=[], placements=0, exterior=0, interior=0, regions=Counter(), masters=Counter())
              for g in config['groups']}
    unmatched, unnamed, not_placed = [], [], []
    known = {}
    for index, (name, raw) in enumerate(masters):
        if name not in statuses:
            unnamed.append(name)
            continue
        organic, placements = master_census(raw, known)
        defined = {k: v for k, v in organic.items() if known.get(k) != v}
        known = organic
        by_id = Counter(p[0] for p in placements)
        for record_id, row in sorted(organic.items()):
            group = classify(config, record_id, row['model'])
            if group is None:
                if by_id[record_id] or record_id in defined:
                    unmatched.append(dict(master=name, id=record_id, model=row['model'], name=row['name'],
                                          placements=by_id[record_id]))
                continue
            entry = groups[group['name']]
            if record_id in defined and record_id not in {r['id'] for r in entry['records']}:
                entry['records'].append(dict(id=record_id, name=row['name'], model=row['model'], master=name))
        for record_id, region, cell, number in placements:
            group = classify(config, record_id, organic[record_id]['model'])
            if group is None:
                continue
            entry = groups[group['name']]
            entry['placements'] += 1
            entry['interior' if region == 'interior' else 'exterior'] += 1
            entry['regions'][region] += 1
            entry['masters'][name] += 1
            if index == 0 and group['status'] == 'harvestable' and harvest is not None and \
                    number not in harvest['numbers'] and number not in harvest['refused']:
                not_placed.append(dict(id=record_id, cell=cell, number=number, region=region))
    out = []
    for entry in groups.values():
        harvestable = entry['status'] == 'harvestable'
        base = entry['masters'].get(masters[0][0], 0) if masters else 0
        out.append(dict(entry, regions=dict(sorted(entry['regions'].items(), key=lambda kv: (-kv[1], kv[0]))),
                        masters=dict(entry['masters']), records=sorted(entry['records'], key=lambda r: r['id']),
                        harvestable_placements=base if harvestable else 0,
                        expansion_placements=entry['placements'] - base))
    refused = sorted(harvest['refused'].items()) if harvest else []
    return dict(format=FORMAT, masters=[dict(name=n, **{k: v for k, v in statuses.get(n, {}).items() if k != 'name'})
                                        for n, _ in masters],
                groups=out, unmatched=unmatched, masters_not_in_config=unnamed, not_placed=not_placed,
                refused=[dict(number=n, reason=r) for n, r in refused],
                totals=dict(records=sum(len(g['records']) for g in out), placements=sum(g['placements'] for g in out),
                            harvestable=sum(g['harvestable_placements'] for g in out),
                            pending=sum(g['placements'] for g in out if g['status'] == 'pending'),
                            not_flora=sum(g['placements'] for g in out if g['status'] == 'not_flora'),
                            expansion_harvest_kind=sum(g['expansion_placements'] for g in out
                                                       if g['status'] == 'harvestable')),
                rule='every organic container record of the masters is in a group of config/harvest-flora.json; every '
                     'base-master placement of a harvestable group is placed by the harvest source or listed with '
                     'its reason')


def check(report):
    """Problems of a census (empty: passed)."""
    problems = ['organic container %s (%s, %s, %d placements in %s) is in no group of config/harvest-flora.json: '
                'register it and add it' % (u['id'], u['name'] or '-', u['model'], u['placements'], u['master'])
                for u in report['unmatched']]
    problems += ['master %s is read but not named in config/harvest-flora.json' % n
                 for n in report['masters_not_in_config']]
    problems += ['harvestable %s (reference %s in %s) is neither placed by the harvest source nor listed with a reason'
                 % (p['id'], p['number'], p['cell']) for p in report['not_placed']]
    return problems


def read_masters(data_files, config=None):
    """[(name, raw)] of the config's masters that the data files hold, the base master first (required)."""
    from mwad.paths import child_ci, resolve_data_files
    config = config or load_config()
    data = resolve_data_files(data_files)
    out = []
    for index, row in enumerate(config['masters']):
        try:
            path = child_ci(data, row['name'])
        except (FileNotFoundError, OSError, ValueError):
            if index == 0:
                raise
            continue
        if path.is_file():
            out.append((row['name'], path.read_bytes()))
        elif index == 0:
            raise ValueError('The base master is missing: ' + row['name'])
    return out


def summary(report):
    lines = ['Harvest flora census: %d organic container records, %d placements: %d harvestable in this build, '
             '%d pending, %d ordinary containers; %d placements of harvest kinds in expansion masters (pending).'
             % (report['totals']['records'], report['totals']['placements'], report['totals']['harvestable'],
                report['totals']['pending'], report['totals']['not_flora'], report['totals']['expansion_harvest_kind'])]
    for g in report['groups']:
        top = ', '.join('%s %d' % kv for kv in list(g['regions'].items())[:4])
        lines.append('  %-40s %-11s %5d placements (%d outdoors, %d indoors)%s%s' % (
            g['name'], g['status'], g['placements'], g['exterior'], g['interior'],
            ' [' + g['register'] + ']' if g['register'] else '', ': ' + top if top else ''))
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--data-files', type=Path, required=True)
    parser.add_argument('--json', type=Path, help='write the census here (private: it names record ids and cells)')
    args = parser.parse_args(argv)
    config = load_config()
    report = census(read_masters(args.data_files, config), config)
    for line in summary(report):
        print(line, flush=True)
    if args.json:
        args.json.write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8', newline='\n')
    problems = check(report)
    for problem in problems:
        print('[census] ' + problem, flush=True)
    return 1 if problems else 0


if __name__ == '__main__':
    raise SystemExit(main())
