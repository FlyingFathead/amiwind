#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""How many interiors a build includes (BUILD-SUMMARY-INTERIOR-COUNTS-48), read from a build run's own records:

  plan        the room list's rooms the build was asked for: chim-room-batches/room-batches.json (rooms the batch
              stage converted, rooms it left to another room stage by name, rooms it refused)
  chim        rooms made into CHIM rooms: chim-interiors/chim-rooms-receipt.json "rooms"
  classic     rooms that stay classic maps, each with its reason: the receipt's kept_room_maps and failed_rooms, the
              batch stage's refusals, and the classic maps the scene chain builds on purpose (the prison ship and the
              Census and Excise Office, while they are not CHIM rooms)
  fast_32mb   rooms the image marked as needing 32 MB of Fast RAM (worldspawn "_chim_room_fast_mb": image/
              chim-room-heap.json "marked_32mb"); None while the image has not reached its room heap gate
  residents   the rooms' residents by animation level, from every room stage's residents report: kit (the build's
              animation profile), standing or idle (a smaller level: the kit model over the alias byte budget,
              RESIDENT-ANIM-BYTE-BUDGET-48), corpse (an authored dead NPC: one pose) and creature; unique models and
              placements

Reads JSON only (well under a second); never writes. build_summary prints the lines at the end of every build and
chim_inclusion keeps the counts with the run's ledger entry.

    python3 tools/interior_counts.py RUN          (prints the lines; --json for the record)
"""
import argparse
import json
from pathlib import Path
import sys

FORMAT = 'AmiWind interior counts 1'
BATCH_RECORD = 'chim-room-batches/room-batches.json'      # tools/room_batches.py RECORD
RECEIPT = 'chim-interiors/chim-rooms-receipt.json'       # tools/chim/interior.py build
HEAP_REPORT = 'image/chim-room-heap.json'                # tools/chim/heap.py require_room_map_heap
INSTALL_RECORD = 'image/chim-interiors.json'             # tools/build_aga.py: chim.interior.install's record
# the room stages' residents reports (prepare_area.populate report_name), relative to the run; chim-rooms-<town> globbed
RESIDENT_REPORTS = ('intro-scene/area-report.json', 'intro-scene/balmora-interiors.json',
                    'chim-room-batches/scene/room-batches-residents.json')
# classic maps the scene chain makes on purpose, with the reason they are classic (stale .bsp audit 2026-10-23,
# the maintainer: prison stays a classic map for now; the census office becomes a CHIM room with object state later)
CLASSIC_BY_DESIGN = (('prison', 'intro-scene/id1/maps/prison.bsp',
                      'the prison ship (New Game): a classic map by decision for now'),
                     ('census', 'intro-scene/id1/maps/census.bsp',
                      'the Census and Excise Office: a classic map until it becomes a CHIM room with object state'))
LEVELS = ('kit', 'standing', 'idle', 'corpse', 'creature')


def _load(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def resident_level(record):
    """The animation level of one resident model record (prepare_area.populate's models)."""
    if 'appearance' not in record:
        return 'creature'
    fallback = record.get('anim_fallback')
    if fallback:
        return fallback.get('level') or 'idle'
    if 'anim' not in record:
        return 'corpse'          # an authored dead NPC (initially_dead): its death pose only
    return 'kit'


def residents(run):
    """{'reports': [paths], 'models': {level: n}, 'placed': {level: n}, 'profile': the build's profile or None} over
    the room stages' residents reports (the exterior's own residents, map 'seyda', left out), or None when none."""
    run = Path(run)
    paths = [run / p for p in RESIDENT_REPORTS] + sorted(run.glob('chim-rooms-*/scene/*-interiors.json'))
    models, placed, used, profile = {}, {}, [], None
    for path in paths:
        report = _load(path) if path.is_file() else None
        if not isinstance(report, dict) or not isinstance(report.get('models'), dict):
            continue
        used.append(path.relative_to(run).as_posix())
        levels = {}
        for identifier, record in report['models'].items():
            levels[identifier.casefold()] = resident_level(record)
            if profile is None and levels[identifier.casefold()] == 'kit':
                profile = (record.get('anim') or {}).get('profile')
        cast = [c for c in report.get('cast', []) if c.get('map') != 'seyda']
        ids = {c.get('id', '').casefold() for c in cast}
        for identifier, level in levels.items():
            if identifier in ids:
                models[level] = models.get(level, 0) + 1
        for c in cast:
            level = levels.get(c.get('id', '').casefold())
            if level is not None:
                placed[level] = placed.get(level, 0) + 1
    if not used:
        return None
    return {'reports': used, 'models': models, 'placed': placed, 'profile': profile}


def counts(run):
    """The interior counts of a build run (module docstring), or None when the run has neither the room batches
    record nor the CHIM interiors receipt (a build without interiors on CHIM)."""
    run = Path(run)
    batches, receipt = _load(run / BATCH_RECORD), _load(run / RECEIPT)
    if batches is None and receipt is None:
        return None
    out = {'format': FORMAT, 'sources': [p for p in (BATCH_RECORD, RECEIPT) if (run / p).is_file()]}
    if isinstance(batches, dict):
        held = batches.get('held') or {}
        by_stage = {'chim-room-batches': len(batches.get('rooms') or [])}
        for stage in held.values():
            by_stage[stage] = by_stage.get(stage, 0) + 1
        refused = batches.get('refused') or {}
        out['plan'] = {'rooms': len(batches.get('rooms') or []) + len(held) + len(refused),
                       'selection': batches.get('selection'), 'by_stage': dict(sorted(by_stage.items())),
                       'refused': len(refused)}
    classic = []
    if isinstance(receipt, dict):
        rooms = receipt.get('rooms') or []
        out['chim'] = {'rooms': len(rooms), 'placements': sum(int(r.get('placements') or 0) for r in rooms)}
        classic += [{'room': r['room'], 'reason': r.get('reason') or 'kept as a room map'}
                    for r in receipt.get('kept_room_maps') or []]
        classic += [{'room': r['room'], 'reason': 'CHIM room not made: %s' % (r.get('reason') or 'failed')}
                    for r in receipt.get('failed_rooms') or []]
    if isinstance(batches, dict):
        classic += [{'room': room, 'reason': 'refused by the room batches stage: %s' % reason}
                    for room, reason in sorted((batches.get('refused') or {}).items())]
    for name, path, reason in CLASSIC_BY_DESIGN:
        if (run / path).is_file():
            classic.append({'room': name, 'reason': reason})
    out['classic'] = classic
    install = _load(run / INSTALL_RECORD)
    if isinstance(install, dict):
        out['installed'] = {'rooms': len(install.get('rooms') or []),
                            'not_in_image': len(install.get('not_in_image') or []),
                            'shell_maps_removed': len(install.get('shell_maps_removed') or [])}
    heap = _load(run / HEAP_REPORT)
    out['fast_32mb'] = (sorted(heap.get('marked_32mb') or []) if isinstance(heap, dict) and 'marked_32mb' in heap
                        else None)
    out['residents'] = residents(run)
    return out


def ledger_record(record):
    """The compact form the CHIM inclusion ledger keeps with a build's entry (numbers, the classic rooms with their
    reasons; the 32 MB rooms as a count): the ledger is committed and capped (tools/release.py LARGE_TEXT)."""
    if not record:
        return None
    res = record.get('residents') or {}
    return {'plan': (record.get('plan') or {}).get('rooms'), 'chim': (record.get('chim') or {}).get('rooms'),
            'classic': record.get('classic') or [],
            'fast_32mb': None if record.get('fast_32mb') is None else len(record['fast_32mb']),
            'residents': {'models': res.get('models'), 'placed': res.get('placed'), 'profile': res.get('profile')}
            if res else None}


def _levels(table):
    return ', '.join('%s %d' % (level, table[level]) for level in LEVELS if table.get(level)) or 'none'


def summary_lines(record):
    """The build summary's lines for a counts record (counts())."""
    if not record:
        return []
    if record.get('format') == 'unreadable':
        return ['Interior counts: not made (%s)' % record.get('error')]
    lines = []
    plan = record.get('plan')
    if plan:
        lines.append('Interiors in the plan: %d rooms (selection %s; %s)' % (
            plan['rooms'], plan.get('selection') or 'n/a',
            ', '.join('%s %d' % (stage, n) for stage, n in plan['by_stage'].items())))
    else:
        lines.append('Interiors in the plan: not recorded (no room batches record)')
    chim = record.get('chim')
    if chim:
        line = 'Interiors converted to CHIM rooms: %d (%d placements)' % (chim['rooms'], chim['placements'])
        installed = record.get('installed')
        if installed:
            line += '; in the image: %d' % installed['rooms']
            if installed['not_in_image']:
                line += ', %d not in the image' % installed['not_in_image']
        lines.append(line)
    else:
        lines.append('Interiors converted to CHIM rooms: not recorded (no CHIM interiors receipt)')
    classic = record.get('classic') or []
    lines.append('Interiors kept as classic maps: %d%s' % (
        len(classic), (': ' + '; '.join('%s (%s)' % (c['room'], c['reason']) for c in classic[:12]) +
                       (' ...' if len(classic) > 12 else '')) if classic else ''))
    fast = record.get('fast_32mb')
    if fast is None:
        lines.append('Interiors that need 32 MB of Fast RAM: not recorded (the image has not reached its room heap gate)')
    else:
        lines.append('Interiors that need 32 MB of Fast RAM (_chim_room_fast_mb): %d%s' % (
            len(fast), (': ' + ', '.join(fast[:20]) + (' ...' if len(fast) > 20 else '')) if fast else ''))
    res = record.get('residents')
    if res:
        lines.append('Room residents by animation level (%s): models %s; placed %s' % (
            'kit = ' + res['profile'] if res.get('profile') else 'kit = the build\'s profile',
            _levels(res['models']), _levels(res['placed'])))
    else:
        lines.append('Room residents by animation level: not recorded (no room residents report)')
    return lines


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('run', type=Path, help='a build run folder')
    ap.add_argument('--json', action='store_true', help='print the record instead of the lines')
    a = ap.parse_args(argv)
    record = counts(a.run)
    if record is None:
        print('No interior records in %s (no room batches record, no CHIM interiors receipt)' % a.run)
        return 1
    print(json.dumps(record, indent=1) if a.json else '\n'.join(summary_lines(record)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
