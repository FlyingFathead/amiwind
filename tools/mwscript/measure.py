# SPDX-License-Identifier: GPL-3.0-only
"""How much MWScript there is and what it needs: the measurement behind docs/MWSCRIPT_BYTECODE.md.

  python3 -m mwscript.measure --data-files DIR [--catalogue media-coverage.json --soundtrack soundtrack.json]
                              [--private OUT_DIR] [--json SUMMARY.json] [--reference N ...]

Per master (its own SCPT records): scripts, source bytes, the original editor's compiled bytes, our bytecode
bytes, distinct functions, the top functions by use; the share of scripts that need only the interpreter, audio,
journal and globals; how many need AI packages, inventory, combat, spells or positioning; then the whole program (the
winning record of each id) as one file with its sections. --private writes the per-script table (names of the
game's scripts: private, never in the repo). --reference adds the script of a placed reference (e.g. 172860).
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mwscript.gamedata import GameData, MASTERS  # noqa: E402
from mwscript.compiler import compile_program, bindings, usage, groups_of  # noqa: E402
from mwscript.codegen import SCRIPT_VOLATILE, SCRIPT_NOTYET  # noqa: E402
from mwscript.functions import MISSING_GROUPS, lookup  # noqa: E402
from mwscript import awms  # noqa: E402

AUDIO_ONLY = {'core', 'audio', 'journal'}


def classify(c):
    groups = groups_of(c)
    return {'groups': sorted(groups), 'audio_journal_globals_only': groups <= AUDIO_ONLY and c.error is None,
            'touches_audio': 'audio' in groups,
            'missing': sorted(groups & set(MISSING_GROUPS)),
            'runs_whole': c.error is None and not c.flags & SCRIPT_NOTYET}


def blockers(compiled, top=40):
    """The not-yet functions ranked by how many scripts each one stops (v0.0.57, MWSCRIPT-MORE-57): 'scripts' uses
    it at all, 'last' it is the only not-yet function the script calls (carrying it out makes the script run whole),
    and a greedy order: each step the function that makes the most further scripts run whole."""
    sets = [set(c.notyet) for c in compiled if c.error is None and c.notyet]
    uses = Counter(n for s in sets for n in s)
    last = Counter(next(iter(s)) for s in sets if len(s) == 1)
    rows = [{'function': n, 'scripts': k, 'last': last.get(n, 0)} for n, k in uses.most_common()]
    rows.sort(key=lambda r: (-r['last'], -r['scripts'], r['function']))
    greedy, left, done = [], [set(s) for s in sets], set()
    for _ in range(top):
        gain = Counter()
        for s in left:
            rest = s - done
            if rest:
                for n in rest:
                    gain[n] += 1.0 / len(rest)    # a script shared by k missing functions gives each 1/k
        if not gain:
            break
        pick = max(gain, key=lambda n: (gain[n], uses[n], n))
        done.add(pick)
        greedy.append({'function': pick, 'scripts': uses[pick],
                       'runs_whole_after': sum(1 for s in left if not (s - done))})
    return {'blocked_scripts': len(sets), 'by_last': rows[:top], 'greedy': greedy}


def master_summary(master, compiled):
    uses = usage(compiled)
    rows = [classify(c) for c in compiled]
    n = len(compiled)
    need = {g: sum(1 for r in rows if g in r['missing']) for g in MISSING_GROUPS}
    return {
        'master': master, 'scripts': n,
        'source_bytes': sum(c.source_bytes for c in compiled),
        'original_compiled_bytes': sum(c.original_bytes for c in compiled),
        'bytecode_bytes': sum(len(c.code) for c in compiled),
        'not_compiled': sum(1 for c in compiled if c.error),
        'distinct_functions': len(uses), 'function_uses': sum(uses.values()),
        'top_functions': uses.most_common(40),
        'audio_journal_globals_only': sum(r['audio_journal_globals_only'] for r in rows),
        'touch_audio': sum(r['touches_audio'] for r in rows),
        'runs_whole_today': sum(r['runs_whole'] for r in rows),
        'need_missing': need,
        'need_any_missing': sum(1 for r in rows if r['missing']),
        'volatile': sum(1 for c in compiled if c.flags & SCRIPT_VOLATILE),
        'inert_today': sum(1 for c in compiled if c.flags & 64),
        'handwritten': sum(1 for c in compiled if c.flags & 32),
        'with_while': sum(1 for c in compiled if c.loops),
        'blockers': blockers(compiled),
    }


def run(args):
    data = GameData().load(args.data_files)
    media = None
    if args.catalogue:
        from mwscript.media import MediaMap
        media = MediaMap.from_files(data, args.catalogue, args.soundtrack)
    out = {'masters': [], 'master_sha256': data.master_sha256}
    for master in MASTERS:
        records = data.scripts_by_master.get(master) or []
        if not records:
            continue
        _, compiled = compile_program(data, None, records)
        out['masters'].append(master_summary(master, compiled))
    program, compiled = compile_program(data, media)
    all_binds = bindings(program)
    binds = bindings(program, compiled)
    raw, sizes = awms.write(program, compiled, binds)
    whole = master_summary('all (winning records)', compiled)
    whole['file_bytes'] = len(raw)
    whole['sections'] = sizes
    whole['bindings'] = len(binds)
    whole['bindings_all'] = len(all_binds)
    whole['binding_types_all'] = dict(Counter(b['type'] for b in all_binds))
    whole['binding_types'] = dict(Counter(b['type'] for b in binds))
    whole['binding_interior'] = sum(1 for b in binds if b['flags'] & 1)
    whole['bound_local_cells'] = sum(compiled[b['script']].nlocals for b in binds)
    whole['global_local_cells'] = sum(c.nlocals for c in compiled)
    whole['max_locals'] = max(c.nlocals for c in compiled)
    whole['max_stack'] = max(c.max_depth for c in compiled)
    whole['globals'] = len(program.globals)
    whole['journal_topics'] = len(program.journal)
    whole['strings'] = len(program.strings)
    whole['objects'] = len(program.objects)
    whole['start_scripts'] = len(data.start_scripts)
    whole['scripted_references_per_master'] = data.reference_counts
    ops = Counter(name for c in compiled for _, name in c.ops)
    whole['opcode_uses'] = ops.most_common()
    notyet_names = Counter(n for c in compiled for n in c.notyet)
    whole['notyet_functions'] = len(notyet_names)
    whole['notyet_top'] = notyet_names.most_common(40)
    whole['max_code_bytes'] = max(len(c.code) for c in compiled)
    # sounds, voices, music
    def media_counts(table, kind):
        rows = table.rows
        reasons = Counter(r.get('reason') for r in rows if not r.get('resolved'))
        notes = Counter(r.get('note') for r in rows if r.get('resolved') and r.get('note'))
        return {'names': len(rows), 'mapped': sum(1 for r in rows if r.get('resolved')),
                'unmapped': sum(1 for r in rows if not r.get('resolved')), 'unmapped_reasons': dict(reasons),
                'repaired': dict(notes)}
    whole['media'] = {'sounds': media_counts(program.sounds, 'sound'), 'voices': media_counts(program.voices, 'voice'),
                      'music': media_counts(program.music, 'music'),
                      'catalogue': bool(media)}
    out['program'] = whole
    # census door (and any other asked references)
    asked = []
    for number in args.reference or ():
        ref = next((r for r in data.references if r['reference'] == number), None)
        if ref is None:
            asked.append({'reference': number, 'found': False}); continue
        index = program.scripts.index.get(ref['script'])
        c = compiled[index] if index is not None else None
        asked.append({'reference': number, 'found': True, 'id': ref['id'], 'type': ref['type'], 'script': ref['script'],
                      'compiled': bool(c and not c.error), 'error': c.error if c else 'no script',
                      'functions': sorted(set(c.calls)) if c else [],
                      'not_yet': sorted(set(c.notyet)) if c else [],
                      'bytecode_bytes': len(c.code) if c else 0, 'source_bytes': c.source_bytes if c else 0,
                      'locals': c.nlocals if c else 0,
                      'disassembly': awms.disassemble(c.code, program.strings.rows) if c else '',
                      'text': program.scripts.rows[index]['script'].text if index is not None else ''})
    if args.private:
        priv = Path(args.private)
        priv.mkdir(parents=True, exist_ok=True)
        table = []
        for c in compiled:
            r = classify(c)
            table.append({'script': c.name, 'master': c.master, 'source_bytes': c.source_bytes,
                          'original_bytes': c.original_bytes, 'bytecode_bytes': len(c.code), 'locals': c.nlocals,
                          'flags': c.flags, 'error': c.error, 'warnings': c.warnings, 'groups': r['groups'],
                          'missing': r['missing'], 'runs_whole': r['runs_whole'],
                          'functions': dict(Counter(c.calls))})
        stem = args.stem
        (priv / (stem + '_SCRIPTS.json')).write_text(json.dumps(table, indent=1) + '\n', encoding='utf-8',
                                                     newline='\n')
        with (priv / (stem + '_SCRIPTS.tsv')).open('w', encoding='utf-8', newline='\n') as f:
            f.write('script\tmaster\tsource\toriginal\tbytecode\tlocals\tvolatile\truns_whole\tgroups\tmissing\terror\n')
            for t in table:
                f.write('%s\t%s\t%d\t%d\t%d\t%d\t%d\t%d\t%s\t%s\t%s\n' % (
                    t['script'], t['master'], t['source_bytes'], t['original_bytes'], t['bytecode_bytes'], t['locals'],
                    1 if t['flags'] & SCRIPT_VOLATILE else 0, 1 if t['runs_whole'] else 0, ','.join(t['groups']),
                    ','.join(t['missing']), t['error'] or ''))
        unresolved = [{'script': s, 'kind': k, 'name': n, 'reason': why} for s, k, n, why in program.unresolved]
        (priv / (stem + '_MEDIA_UNMAPPED.json')).write_text(json.dumps(
            {'unmapped': unresolved,
             'sounds': program.sounds.rows, 'voices': program.voices.rows, 'music': program.music.rows,
             'repaired': media.notes if media else []}, indent=1, default=str) + '\n', encoding='utf-8',
            newline='\n')
        (priv / (stem + '_REFERENCES.json')).write_text(json.dumps(asked, indent=1) + '\n', encoding='utf-8',
                                                        newline='\n')
    out['references'] = [{k: v for k, v in a.items() if k not in ('text', 'disassembly')} for a in asked]
    if args.marker_census:
        out['sound_markers'] = sound_markers(json.loads(Path(args.marker_census).read_text(encoding='utf-8')),
                                             program, compiled, binds, data)
    return out


def sound_markers(census, program, compiled, binds, data):
    """The original's sound markers (editor-marker placements whose script plays a sound: tools/editor_markers.py
    census, the same records the converters keep as invisible deferred placements) against the compiled file:
    how many are bound and play, per cell; and the other placements whose script plays a 3D sound."""
    from mwscript.codegen import SCRIPT_INERT, SCRIPT_HANDWRITTEN
    bound = {b['reference']: b for b in binds}
    rows = [r for r in census['emitter_table']['emitters'] if r['kind'] == 'sound emitter']
    per_cell = Counter()
    status = Counter()
    by_space = Counter()
    for r in rows:
        space = 'interior' if isinstance(r['cell'], str) else 'exterior'
        cell = r['cell'] if space == 'interior' else '%d,%d' % tuple(r['cell'])
        per_cell[(r['master'], space, cell)] += 1
        by_space[(r['master'], space)] += 1
        if r['master'] != 'Morrowind.esm':
            status['add-on master (not in the image yet)'] += 1
            continue
        key = (r.get('script') or '').casefold()
        index = program.scripts.index.get(key)
        if index is None:
            status['no script'] += 1
        elif compiled[index].flags & SCRIPT_HANDWRITTEN:
            status['hand-written list'] += 1
        elif compiled[index].flags & SCRIPT_INERT:
            status['inert'] += 1
        elif r['reference'] not in bound:
            status['not bound'] += 1
        else:
            sound = (r.get('sound') or '').casefold()
            row = program.sounds.rows[program.sounds.index[sound]] if sound in program.sounds.index else None
            status['bound, sound mapped' if row and row.get('resolved') else 'bound, sound not mapped'] += 1
    marker_refs = {r['reference'] for r in rows if r['master'] == 'Morrowind.esm'}
    three_d = {'PLAYSOUND3D', 'PLAYSOUND3DVP', 'PLAYLOOP3D', 'PLAYLOOP3DVP'}
    others = Counter(b['type'] for b in binds if b['reference'] not in marker_refs
                     and any(name in three_d for _, name in compiled[b['script']].ops))
    return {'sound_emitters': len(rows),
            'by_master_space': {'%s/%s' % k: n for k, n in sorted(by_space.items())},
            'cells': len(per_cell),
            'top_cells': [{'master': m, 'space': s, 'cell': c, 'markers': n} for (m, s, c), n in per_cell.most_common(25)],
            'morrowind_status': dict(status),
            'other_scripted_3d_sound_placements': dict(others)}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--data-files', required=True)
    p.add_argument('--catalogue')
    p.add_argument('--soundtrack')
    p.add_argument('--private')
    p.add_argument('--stem', default='mwscript')
    p.add_argument('--json')
    p.add_argument('--reference', type=int, action='append')
    p.add_argument('--marker-census', help='tools/editor_markers.py census JSON: the sound markers against the file')
    args = p.parse_args(argv)
    out = run(args)
    text = json.dumps(out, indent=1)
    if args.json:
        Path(args.json).write_text(text + '\n', encoding='utf-8', newline='\n')
    for m in out['masters'] + [out['program']]:
        print('%-22s scripts %4d  source %8d  original %8d  bytecode %8d  not compiled %d  functions %d  '
              'audio/journal/globals only %d  runs whole %d  need AI packages/inv/combat/spells/pos %s any %d' % (
                  m['master'], m['scripts'], m['source_bytes'], m['original_compiled_bytes'], m['bytecode_bytes'],
                  m['not_compiled'], m['distinct_functions'], m['audio_journal_globals_only'], m['runs_whole_today'],
                  m['need_missing'], m['need_any_missing']))
    print('file bytes', out['program']['file_bytes'], out['program']['sections'])
    print('media', json.dumps(out['program']['media']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
