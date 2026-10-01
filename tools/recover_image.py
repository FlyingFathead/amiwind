"""Bounded rc3 image recovery; retained conversions are read, never rewritten."""
import hashlib
import json
from pathlib import Path
import re

from mwad.paths import ensure_external


def digest(path):
    with Path(path).open('rb') as source:
        result = hashlib.sha256()
        for block in iter(lambda: source.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def inspect_run(args, root):
    old = ensure_external(args.recover_image_from, 'retained build').resolve()
    state_path = old / 'build-state.json'
    state = json.loads(state_path.read_text())
    if (state.get('schema'), state.get('runtime_version'), state.get('recipe'), state.get('status')) != (
            'amiwind-build-receipt-v1', '0.0.25-rc3', 'seyda-neen-prison-v1', 'failed'):
        raise ValueError('Recovery requires a failed rc3 full AGA run')
    expected = {'setup', 'terrain', 'scenery', 'scene', 'bsp', 'npcs', 'hands', 'interior',
                'dialogue-lookup', 'intro', 'census', 'area', 'balmora', 'balmora-interiors',
                'door-audio', 'character', 'reading', 'opening-references', 'world-survey',
                'world-terrain', 'music', 'engine'}
    steps = state.get('steps', [])
    if (len(steps) != len(expected) + 1 or
            {s['name'] for s in steps if s.get('status') == 'passed'} != expected or
            [(s['name'], s.get('status')) for s in steps if s.get('status') != 'passed'] != [('image', 'failed')]):
        raise ValueError('All 22 pre-image stages must have passed; no terrain conversion will be scheduled')
    if Path(state['data_files']).resolve() != args.data_files.resolve() or state['hands'] != args.hands:
        raise ValueError('Recovery must use the original game input directory and hands mode')
    if state.get('font_options', {}).get('bitmap_paper_ink') != args.font_options['bitmap_paper_ink']:
        raise ValueError('Recovery must preserve the original bitmap paper ink option')
    image_step = next(s for s in steps if s['name'] == 'image')
    if '--intro-captions' in image_step['command']:
        at = image_step['command'].index('--intro-captions')
        original = Path(image_step['command'][at + 1]).resolve()
        if args.intro_captions is None or args.intro_captions.resolve() != original:
            raise ValueError('Repeat the original --intro-captions option for recovery')
    elif args.intro_captions:
        raise ValueError('Recovery cannot add a different opening-caption input')
    # Bound this migration to the published rc3 source. Do not silently reuse
    # conversions from an unknown local generator patch or another release.
    base = json.loads((root / 'docs/PATCH-v0.0.25-rc6.json').read_text())['base_files']
    recorded = state.get('source_sha256', {})
    suffixes = {'.py', '.c', '.h', '.patch', '.qc', '.asm', '.sh', '.cfg'}
    required = {name for name in base if Path(name).suffix in suffixes or
                Path(name).name in {'Makefile', 'VERSION', 'pyproject.toml'}}
    if not required <= recorded.keys() or any(recorded[name] != base[name]['sha256'] for name in required):
        raise ValueError('Recorded rc3 source does not match the published baseline; inspect before reusing conversion')
    if not state.get('input_sha256'):
        raise ValueError('Original input checksums are required for recovery')
    scene = old / 'intro-scene'
    report_path = old / 'world-terrain/world-regions.json'
    report = json.loads(report_path.read_text())
    if report.get('format') != 'AmiWind playable terrain regions 1' or report.get('diagnostic_subset'):
        raise ValueError('Expected a complete terrain receipt, not a diagnostic subset')
    from prepare_world_regions import plan, region_directory
    survey, planned = plan(old / 'world-survey')
    entries = report['regions']
    if [e['name'] for e in entries] != [e['name'] for e in planned]:
        raise ValueError('Terrain receipt is missing planned regions')
    for key, path in [('survey_sha256', old/'world-survey/world-survey.json'),
                      ('terrain_sha256', old/'world-survey/terrain-source.npz')]:
        if report[key] != digest(path):
            raise ValueError('Retained survey hash mismatch: ' + path.name)
    if (scene/'id1/world/regions.awr').read_bytes() != region_directory(survey, entries):
        raise ValueError('Published world directory differs from the complete terrain receipt')
    for entry in entries:
        name = entry['name']
        if not re.fullmatch(r'vf\d{4}', name):
            raise ValueError('Invalid terrain region name')
        path = scene/'id1/maps'/(name+'.bsp')
        if path.stat().st_size != entry['converted']['bytes'] or digest(path) != entry['converted']['sha256']:
            raise ValueError('Retained terrain output hash mismatch: ' + name)
    return {'from_run': str(old), 'original_state_sha256': digest(state_path),
            'terrain_receipt_sha256': digest(report_path), 'verified_regions': len(entries),
            'scope': 'reuse completed rc3 conversion; rebuild versioned engine and image; preserve all image gates',
            'input_sha256': state['input_sha256']}


def recovery_commands(steps, old, run):
    """Use current known command construction; never execute commands from a receipt."""
    selected = []
    for name, original in steps:
        if name not in ('engine', 'image'):
            continue
        command = list(original)
        if name == 'image':
            for flag, path in [('--scene', old/'intro-scene'), ('--music', old/'music')]:
                command[command.index(flag)+1] = str(path)
        selected.append((name, command))
    if [name for name, _ in selected] != ['engine', 'image']:
        raise ValueError('Expected engine then image recovery commands')
    # The normal command builder must keep all new output paths in the new run.
    for _, command in selected:
        output = Path(command[command.index('--out')+1]).resolve()
        if run.resolve() not in output.parents or old.resolve() in output.parents:
            raise ValueError('Recovery output must be inside a new run')
    return selected
