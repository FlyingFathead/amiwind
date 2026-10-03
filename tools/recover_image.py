"""Recover an rc3 image failure without rewriting retained conversions.

CAPACITY FIRST: before starting the build, verify enough usable storage for ALL
required content, conversion intermediates, staging copies, temporary images,
readback verification and a margin. Include filesystem/quota limits and shared
RAM limits for memory-backed scratch. If capacity is insufficient, arrange it
before expensive work; never omit NPC models or the gallery to make a build fit.

All NPCs must be included and loadable by the engine for the game to be complete.
NPC gallery creation MUST NOT be skipped except for exceptional, explicitly
requested debugging purposes. Build time and disk usage are not reasons to omit it.

Normal builds and recovery MUST include the gallery; missing input/model/catalogue
content is an error, never an automatic opt-out. Only the owner's explicit
--no-npc-gallery permits debugging-only omission of inspection assets. It must
never remove required game NPC content or change the normal default.

Skipping NPC model creation together with the gallery is pointless and
counterproductive for a complete build: all character models are still required
in the final product. Exceptional debugging may temporarily isolate the gallery;
it cannot reduce the final game's required content.

BOTH GALLERIES REQUIRE OUTSIDE APPROVAL FOR EXCEPTIONS: the NPC gallery and
upcoming static-asset gallery, including their model generation, catalogues,
coverage, quality and validation, must not be disabled, reduced or bypassed
without a specific documented case/scenario and explicit approval from the
project owner. The builder or contributor cannot approve its own exception.
Time pressure, storage pressure and convenience are not approval. Existing
--no-npc-gallery support is only a mechanism for an owner-approved exceptional
debugging case; its availability does not grant permission to use it.

A complete game requires all of its NPC and other game assets intact, packaged
and loadable by the engine. Skipping model/asset creation with either gallery is
pointless and counterproductive: those assets are required in the final product
anyway. A debugging exception cannot redefine a complete build. Loadable does not
mean all assets must be resident in memory simultaneously. The static-asset
gallery remains planned; this contract does not claim it is implemented.
"""
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
            'scope': 'reuse completed rc3 conversion; rebuild versioned engine, required NPC gallery and image; preserve all image gates',
            'input_sha256': state['input_sha256']}


def recovery_commands(steps, old, run):
    """Rebuild scenery overlays, the versioned engine, gallery, and image."""
    selected = []
    for name, original in steps:
        if name not in ('engine', 'npc-gallery', 'world-scenery-assets', 'world-scenery', 'image'):
            continue
        command = list(original)
        if name == 'npc-gallery':
            command[command.index('--palette')+1] = str(old/'intro-scene/id1/gfx/palette.lmp')
        if name == 'world-scenery':
            command[command.index('--terrain')+1] = str(old/'world-terrain')
            command[command.index('--palette')+1] = str(old/'intro-scene/id1/gfx/palette.lmp')
        if name == 'image':
            for flag, path in [('--scene', old/'intro-scene'), ('--music', old/'music')]:
                command[command.index(flag)+1] = str(path)
        selected.append((name, command))
    order = {'engine': 0, 'world-scenery-assets': 1, 'world-scenery': 2,
             'npc-gallery': 3, 'image': 4}
    selected.sort(key=lambda step: order[step[0]])
    image = next((command for name, command in selected if name == 'image'), [])
    expected = (['engine', 'world-scenery-assets', 'world-scenery', 'image']
                if '--no-npc-gallery' in image else
                ['engine', 'world-scenery-assets', 'world-scenery', 'npc-gallery', 'image'])
    if [name for name, _ in selected] != expected:
        raise ValueError('Expected engine, scenery source export and overlay, required NPC gallery, then image recovery commands')
    for _, command in selected:
        output = Path(command[command.index('--out')+1]).resolve()
        if run.resolve() not in output.parents or old.resolve() in output.parents:
            raise ValueError('Recovery output must be inside a new run')
    return selected
