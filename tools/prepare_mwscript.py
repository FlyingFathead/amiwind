#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Builder stage mwscript: every script of the game data compiled into one file, id1/mwscript.awm.

Inputs: the masters (Morrowind, Tribunal, Bloodmoon), the media stage's catalogue (media-coverage.json: which
converted file each sound and voice became) and the soundtrack (music/soundtrack.json: each track's number),
and config/mwscript.json. Sounds, voices and music are referred to by index into the media catalogue's files
(sound/pool/a<hash>.wav, music/trackNN.mws): no audio is copied. One unit, keyed by the SHA-256 of all of
those and of the compiler's source: an unchanged key reuses the file from the pool (tools/file_cache.py).

  prepare_mwscript.py --data-files DIR --media RUN/media --music RUN/music --out RUN/mwscript
                      [--cache POOL --cache-report FILE]

Writes OUT/id1/mwscript.awm and OUT/mwscript-report.json (counts, sizes, every script sound that does not map
and why). The design and the format: docs/MWSCRIPT_BYTECODE.md.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tools'))

from mwscript.gamedata import GameData, MASTERS  # noqa: E402
from mwscript.compiler import compile_program, bindings  # noqa: E402
from mwscript.media import MediaMap  # noqa: E402
from mwscript import awms  # noqa: E402

CONFIG = ROOT / 'config' / 'mwscript.json'
NAME = 'mwscript.awm'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def compiler_identity():
    """SHA-256 over the compiler's source files (tools/mwscript/*.py, this stage, and tools/prepare_combat.py, whose
    autocalculation and equipment rules the actor table uses: tools/mwscript/actors.py; tools/room_batches.py and
    tools/town_interiors.py, whose door arrival rule the player's PositionCell uses: tools/mwscript/rooms.py)."""
    h = hashlib.sha256()
    for path in sorted((ROOT / 'tools' / 'mwscript').glob('*.py')) + [Path(__file__).resolve(),
                                                                        ROOT / 'tools' / 'prepare_combat.py',
                                                                        ROOT / 'tools' / 'room_batches.py',
                                                                        ROOT / 'tools' / 'town_interiors.py']:
        h.update(path.name.encode() + b'\0' + path.read_bytes())
    return h.hexdigest()


def unit_inputs(data_files, media, music, config, rooms=None):
    from mwad.paths import child_ci
    from mwscript.rooms import room_table, table_digest
    # the room maps the player's PositionCell loads (the repo's room lists): keyed by what the table holds
    inputs = {'compiler': compiler_identity(), 'config': sha(config),
              'rooms': table_digest(room_table() if rooms is None else rooms)}
    for name in MASTERS:
        path = child_ci(Path(data_files), name, required=False)
        inputs[name] = sha(path) if path else None
    inputs['media-coverage.json'] = sha(Path(media) / 'media-coverage.json')
    track = Path(music) / 'soundtrack.json' if music else None
    inputs['soundtrack.json'] = sha(track) if track and track.is_file() else None
    return inputs


def build(data_files, media, music, out, config=CONFIG):
    config_data = json.loads(Path(config).read_text(encoding='utf-8'))
    data = GameData().load(data_files)
    soundtrack = Path(music) / 'soundtrack.json' if music else None
    mapper = MediaMap.from_files(data, Path(media) / 'media-coverage.json',
                                 soundtrack if soundtrack and soundtrack.is_file() else None)
    program, compiled = compile_program(data, mapper, handwritten=config_data['handwritten']['patterns'])
    moves = {'rows': len(program.moves), 'rooms_known': len(program.rooms or {})}
    binds = bindings(program, compiled)
    conf = {'range_units': int(config_data['activation']['range_units']),
            'ops_per_frame': int(config_data['budget']['ops_per_frame']),
            'ops_per_run': int(config_data['budget']['ops_per_run'])}
    raw, sizes = awms.write(program, compiled, binds, conf)
    awms.read(raw)   # the output schema: the file reads back
    for row in awms.scripts(awms.read(raw)):
        awms.decode(row['code'])
    target = Path(out) / 'id1' / NAME
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)

    def media_rows(table):
        return {'names': len(table), 'mapped': sum(1 for r in table.rows if r.get('resolved')),
                'unmapped': [{'name': r.get('id') or r.get('path'), 'reason': r.get('reason')}
                             for r in table.rows if not r.get('resolved')],
                'repaired': [{'name': r.get('id') or r.get('path'), 'note': r['note']}
                             for r in table.rows if r.get('resolved') and r.get('note')]}
    report = {'format': 'AWMS1', 'file': 'id1/' + NAME, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
              'sections': sizes, 'scripts': len(compiled),
              'not_compiled': [c.name for c in compiled if c.error],
              'bindings': len(binds), 'globals': len(program.globals), 'journal_topics': len(program.journal),
              'player_moves': moves,
              'actors': dict(program.actors.report, items=len(program.actors.items),
                             spells=len(program.actors.spells), inventory_entries=len(program.actors.inventory),
                             spell_entries=len(program.actors.spell_list)),
              'media': {'sounds': media_rows(program.sounds), 'voices': media_rows(program.voices),
                        'music': media_rows(program.music)},
              'unmapped_uses': [{'script': s, 'kind': k, 'name': n, 'reason': why}
                                for s, k, n, why in program.unresolved]}
    (Path(out) / 'mwscript-report.json').write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8',
                                                   newline='\n')
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--data-files', type=Path, required=True)
    p.add_argument('--media', type=Path, required=True, help='the media stage output (media-coverage.json)')
    p.add_argument('--music', type=Path, help='the music stage output (soundtrack.json)')
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--config', type=Path, default=CONFIG)
    p.add_argument('--cache', type=Path, help='the shared pool (tools/file_cache.py): reuse an unchanged unit')
    p.add_argument('--cache-report', type=Path)
    args = p.parse_args(argv)
    started = time.time()
    print('[mwscript] start: one unit (the whole program), 1 worker: the compiler reads every script once; '
          'serial by design (member access needs every script), measured in seconds', flush=True)
    inputs = unit_inputs(args.data_files, args.media, args.music, args.config)
    key = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()
    target = args.out / 'id1' / NAME
    result = 'off'
    cache = None
    if args.cache:
        from file_cache import FileCache
        cache = FileCache(args.cache, 'mwscript', {'inputs': inputs})
        target.parent.mkdir(parents=True, exist_ok=True)
        facts = cache.fetch(cache.key(key, {}), target)
        result = 'hit' if facts and facts.get('report') else 'miss'
    if result == 'hit':
        report = facts['report']
        (args.out / 'mwscript-report.json').write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8',
                                                       newline='\n')
    else:
        report = build(args.data_files, args.media, args.music, args.out, args.config)
        if cache:
            cache.store(cache.key(key, {}), target, {'report': report})
    receipt = {'unit_key': key, 'inputs': inputs, 'cache': result, 'sha256': sha(target), 'bytes': target.stat().st_size}
    (args.out / 'mwscript-receipt.json').write_text(json.dumps(receipt, indent=1) + '\n', encoding='utf-8',
                                                    newline='\n')
    if args.cache_report:
        from file_cache import write_report
        write_report(args.cache_report, 'mwscript', {'units': {'hit': int(result == 'hit'), 'miss': int(result == 'miss'),
                                                               'enabled': bool(cache)}})
    m = report['media']
    print('[mwscript] %d scripts (%d not compiled), %d bytes (%s), %d placed scripted objects; sounds %d/%d mapped, '
          'voices %d/%d, music %d/%d; unit %s' % (
              report['scripts'], len(report['not_compiled']), report['bytes'], report['sha256'][:12],
              report['bindings'], m['sounds']['mapped'], m['sounds']['names'], m['voices']['mapped'],
              m['voices']['names'], m['music']['mapped'], m['music']['names'], result), flush=True)
    for kind in ('sounds', 'voices', 'music'):
        for row in m[kind]['unmapped']:
            print('[mwscript] [warning: unmapped %s] %s: %s' % (kind[:-1] if kind != 'music' else kind,
                                                                row['name'], row['reason']), flush=True)
    print('[mwscript] end: took %.1f s, 1 worker' % (time.time() - started), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
