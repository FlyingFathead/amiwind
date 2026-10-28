#!/usr/bin/env python3
"""Humanoid animation coverage (ANIM-GROUPS-NOT-HOOKED-54, docs/ANIMKIT.md "Every group hooked up").

For every group of the humanoid animation tables a build writes (progs/humanoid.awsk, progs/humanoid_kna.awsk, the
female and own-file views inside them): is it in the table, and what in the game plays it. The "what" is the engine's
own catalogue (engine/aga/src/aw_animpick_catalogue.inc aw_pick_catalogue), whose "pick:" rows the gate proves reachable
through the engine's group choice (tests/aga_animpick_test.c); this tool reads both and reports, per group:

  group, the tables that hold it, hooked yes/no, by what, and the callers still to come (an entry point the engine
  has whose game-side caller lands with another work item).

A group in a table but not in the catalogue is never played: a finding (exit 1 with --check). A catalogue row no
table holds is listed as absent (a table built from other data, or a stale row).

  python3 tools/anim_coverage.py TABLE.awsk [TABLE.awsk ...] [--json OUT] [--markdown OUT] [--check]
  python3 tools/anim_coverage.py --catalogue        # the engine catalogue alone

Read only; no game data is written anywhere (the tables come from the user's own build)."""
import argparse
import json
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / 'engine/aga/src/aw_animpick_catalogue.inc'
HEADER = struct.Struct('>4sHHIffHH')        # engine aw_skel.h: "AWSK", version, bones, frames, rate, scale, groups, keys
GROUP = struct.Struct('>24sII')
KEY = struct.Struct('>32sHHI')
# Entry points the engine has whose game-side caller comes with another item (the coverage says so, never "done").
PENDING = {
    **{'idle%d' % n: 'AW_AnimPickIdleChances: the wander package chances (AI_W) from the ambient wander tables'
       for n in range(2, 10)},
    'spellcast': 'AW_AnimPickCast: an NPC casting (the spell effects work); readying and lowering already play on '
                 'combat start/end',
    'spellturnleft': 'the spell stance (an NPC casting, the spell effects work)',
    'spellturnright': 'the spell stance (an NPC casting, the spell effects work)',
    'idlespell': 'the spell stance (an NPC casting, the spell effects work)',
    'pickprobe': 'the player only (OpenMW: no NPC uses a lockpick or probe); AmiWind has no lockpicking yet',
    'inventoryhandtohand': 'the player only (the inventory picture, characterpreview.cpp); the preview does not pose yet',
    'inventoryweapononehand': 'the player only (the inventory picture); the preview does not pose yet',
    'inventoryweapontwohand': 'the player only (the inventory picture); the preview does not pose yet',
    'inventoryweapontwowide': 'the player only (the inventory picture); the preview does not pose yet',
}


def pending_for(name):
    """The caller still to come for a group, '' when the game already reaches it."""
    if name in PENDING:
        return PENDING[name]
    if name == 'idlesneak' or name.startswith('sneak'):
        return 'AW_AnimPickSneak: MWScript ForceSneak (the script host does not call it yet)'
    if name.startswith('jump'):
        return 'NPCs do not jump in AmiWind yet (OpenMW: an actor jumps over obstacles); the player body plays jump, jumphh'
    return ''


def catalogue(path=CATALOGUE):
    """[(group, hook)] from the engine source, in its order."""
    text = path.read_text(encoding='utf-8')
    body = text[text.index('aw_pick_catalogue[]={'):]
    body = body[:body.index('};')]
    rows = []
    for m in re.finditer(r'PICK\("([^"]+)","([^"]+)"\)|MOVE\("([^"]+)"\)|TURN\("([^"]+)"\)|\{"([^"]+)","([^"]+)"\}', body):
        if m.group(1):
            rows.append((m.group(1), 'pick: ' + m.group(2)))
        elif m.group(3):
            rows.append((m.group(3), 'pick: moving (refreshMovementAnims)'))
        elif m.group(4):
            rows.append((m.group(4), 'pick: turning on the spot (refreshMovementAnims)'))
        else:
            rows.append((m.group(5), m.group(6)))
    return rows


def table_groups(data):
    """The group names of an AWSK table (engine aw_skel.h), in order, and {group: [text keys]}."""
    magic, _version, bones, _frames, _rate, _scale, groups, keys = HEADER.unpack_from(data, 0)
    if magic != b'AWSK':
        raise ValueError('not an AWSK table')
    off = 24 + ((bones * 2 + 3) & ~3) + ((bones + 3) & ~3)
    names = []
    for _ in range(groups):
        name, _first, _last = GROUP.unpack_from(data, off)
        off += GROUP.size
        names.append(name.rstrip(b'\0').decode('latin-1'))
    texts = {}
    for _ in range(keys):
        text, group, _zero, _frame = KEY.unpack_from(data, off)
        off += KEY.size
        if group != 0xFFFF and group < len(names):
            texts.setdefault(names[group], []).append(text.rstrip(b'\0').decode('latin-1'))
    return names, texts


def report(tables):
    """tables: {label: AWSK bytes}. Returns the report dict."""
    rows = catalogue()
    hooks = dict(rows)
    holders = {}
    for label, data in tables.items():
        for name in table_groups(data)[0]:
            holders.setdefault(name, []).append(label)
    groups = []
    for name in list(dict.fromkeys([*holders, *hooks])):
        hook = hooks.get(name)
        groups.append({'group': name, 'tables': holders.get(name, []), 'hooked': bool(hook),
                       'by': hook or '', 'pending_caller': pending_for(name)})
    never = [g['group'] for g in groups if g['tables'] and not g['hooked']]
    absent = [g['group'] for g in groups if not g['tables']]
    return {'groups': groups, 'tables': sorted(tables), 'never_played': never, 'absent_from_tables': absent,
            'pending_callers': sorted(g['group'] for g in groups if g['pending_caller'] and g['tables']),
            'counts': {'groups': len(groups), 'in_tables': sum(1 for g in groups if g['tables']),
                       'hooked': sum(1 for g in groups if g['hooked'] and g['tables']), 'never_played': len(never)}}


def markdown(rep):
    lines = ['| Group | In table | Hooked by | Caller still to come |', '| --- | --- | --- | --- |']
    for g in rep['groups']:
        lines.append('| %s | %s | %s | %s |' % (g['group'], ', '.join(g['tables']) or 'no',
                                                g['by'] or '**NEVER PLAYED**', g['pending_caller'] or ''))
    c = rep['counts']
    lines.append('')
    lines.append('%d groups, %d in the tables, %d hooked, %d never played.' % (c['groups'], c['in_tables'], c['hooked'],
                                                                             c['never_played']))
    return '\n'.join(lines) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('tables', nargs='*', type=Path, help='AWSK tables (progs/humanoid.awsk ...) of a build')
    ap.add_argument('--json', type=Path)
    ap.add_argument('--markdown', type=Path)
    ap.add_argument('--catalogue', action='store_true', help='print the engine catalogue and stop')
    ap.add_argument('--check', action='store_true', help='exit 1 when a table holds a group nothing plays')
    args = ap.parse_args(argv)
    if args.catalogue:
        for name, hook in catalogue():
            print('%-24s %s' % (name, hook))
        return 0
    if not args.tables:
        ap.error('give at least one table (or --catalogue)')
    print('anim_coverage: reading %d table(s)' % len(args.tables), flush=True)
    rep = report({str(p): p.read_bytes() for p in args.tables})
    if args.json:
        args.json.write_text(json.dumps(rep, indent=1) + '\n', encoding='utf-8', newline='\n')
    if args.markdown:
        args.markdown.write_text(markdown(rep), encoding='utf-8', newline='\n')
    c = rep['counts']
    print('anim_coverage: %d groups in the tables, %d hooked, %d never played%s; %d with a caller still to come'
          % (c['in_tables'], c['hooked'], c['never_played'],
             (': ' + ' '.join(rep['never_played'])) if rep['never_played'] else '', len(rep['pending_callers'])))
    if rep['absent_from_tables']:
        print('anim_coverage: catalogue rows no table holds: %s' % ' '.join(rep['absent_from_tables']))
    return 1 if args.check and rep['never_played'] else 0


if __name__ == '__main__':
    sys.exit(main())
