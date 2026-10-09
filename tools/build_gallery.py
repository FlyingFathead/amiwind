#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Build and verify the complete owned NPC/creature inspection gallery.

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

Complete gallery outfits are inspection snapshots, not a permanent gameplay
equipment format. Partial corpse looting and equipment changes require mutable
per-actor inventory plus source-derived body/clothing composition. Caching these
snapshots must not replace that work or pre-bake every possible outfit combination.
See docs/CHARACTER_EQUIPMENT_ROADMAP.md.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from mwad.paths import ensure_external, child_ci
from build_jobs import add_jobs, resolve_jobs
from mwad.audit import normpath
from vis_options import light_args
from build_parallel import completed_map
from prepare_gallery import catalogue, convert_model, finish_catalogue, GALLERY_FACE_LIMIT
from audit_gallery_budgets import write_allowances
from stage_gallery import stage
from known_inputs import input_sha256

FORMAT = 'AmiWind required NPC gallery 1'


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def catalogue_files(path):
    lines = Path(path).read_text(encoding='ascii').splitlines()
    if not lines or not re.fullmatch(r'AWG1 [1-9][0-9]*', lines[0]):
        raise ValueError('Gallery catalogue missing or invalid')
    count = int(lines[0].split()[1])
    if len(lines) != count + 1:
        raise ValueError('Incomplete NPC gallery catalogue')
    files = {'gallery/catalog.txt', 'gallery/inspection.tsv', 'gallery/poses.txt',
             'model-budgets.txt', 'maps/charplane.bsp'}
    numbers, identities = set(), set()
    for row in lines[1:]:
        fields = row.split('\t')
        if len(fields) != 9 or fields[1] not in ('NPC_', 'CREA') or not fields[0].isdigit():
            raise ValueError('Invalid NPC gallery record')
        number = int(fields[0]); identity = (fields[1], fields[7].casefold())
        if number in numbers or identity in identities or not fields[7]:
            raise ValueError('Duplicate or empty NPC gallery identity')
        numbers.add(number); identities.add(identity)
        for key in fields[2:4]:
            if not re.fullmatch(r'm[0-9a-f]{16}', key):
                raise ValueError('Unresolved NPC gallery model: ' + fields[7])
            files.update(('gallery/' + key + '.mdl', 'gallery/f' + key[1:] + '.mdl'))
    if numbers != set(range(1, count + 1)):
        raise ValueError('Incomplete NPC gallery numbering')
    return count, files


def validate_payload(id1, receipt):
    """Check actual required files, not merely whatever happened to be staged."""
    if receipt.get('format') != FORMAT:
        raise ValueError('Missing current NPC gallery build receipt')
    if sha(id1/'gfx/palette.lmp') != receipt['palette_sha256']:
        raise ValueError('NPC gallery palette differs from image palette')
    count, files = catalogue_files(id1/'gallery/catalog.txt')
    if count != receipt['records'] or files != set(receipt['files']):
        raise ValueError('NPC gallery receipt omits required payload')
    from build_parallel import hash_existing  # every payload file, hashed in the worker pool
    names = sorted(files)
    for name, actual in zip(names, hash_existing([id1/name for name in names])):
        info = receipt['files'][name]; path = id1/name
        if actual is None or path.stat().st_size != info['bytes'] or actual != info['sha256']:
            raise ValueError('Missing or changed NPC gallery payload: ' + name)
    return {'status': 'passed', 'records': count, 'models': receipt['models'],
            'files': len(files), 'payload_bytes': sum(x['bytes'] for x in receipt['files'].values()),
            'visual_acceptance': 'requires target playtest'}


def stage_required(gallery, id1):
    gallery = ensure_external(Path(gallery), 'required gallery')
    id1 = ensure_external(Path(id1), 'game payload')
    receipt = json.loads((gallery/'gallery-build.json').read_text())
    # Validate the complete package before copying any model into the game tree.
    validate_payload(gallery, receipt)
    report = stage(gallery, id1)
    if report['unresolved']:
        raise ValueError('NPC gallery model budget audit failed')
    # Legacy receipts may describe CRLF; verify regenerated allowances before
    # preserving their authenticated source bytes for exact package validation.
    original = (gallery/'model-budgets.txt').read_bytes()
    generated = (id1/'model-budgets.txt').read_bytes()
    if original.replace(b'\r\n', b'\n') != generated.replace(b'\r\n', b'\n'):
        raise ValueError('NPC gallery regenerated model allowances differ')
    shutil.copyfile(gallery/'model-budgets.txt', id1/'model-budgets.txt')
    (id1/'maps').mkdir(exist_ok=True)
    shutil.copyfile(gallery/'maps/charplane.bsp', id1/'maps/charplane.bsp')
    (id1/DISABLED_MARKER).unlink(missing_ok=True)
    report.update(validate_payload(id1, receipt))
    report['receipt_sha256'] = sha(gallery/'gallery-build.json')
    print(f"NPC gallery verified: {report['records']} records, {report['models']} models, inspection map included.", flush=True)
    return report


# Marker written into a --no-npc-gallery image. When a gallery command
# (dbg gallery/npcgallery/modelgallery, aw charplane, dbg combattest, dbg
# torchtest npc) finds the gallery's own files missing, the engine looks for
# this file and prints a friendly "built without the NPC gallery" notice
# instead of a repair message (engine/aga/src/aw_gallery.c).
DISABLED_MARKER = 'npc-gallery-disabled.txt'


def omit_gallery(id1):
    """Omit inspection assets only for a documented, owner-approved debug case.

    The caller must have explicit outside approval from the project owner;
    this function and the opt-out flag do not authorize an exception. Preserve
    required world NPC assets. Never use this to meet time or space budgets.
    """
    id1 = ensure_external(Path(id1), 'new image payload')
    if (id1/'gallery').exists():shutil.rmtree(id1/'gallery')
    (id1/'maps/charplane.bsp').unlink(missing_ok=True)
    budgets=id1/'model-budgets.txt'
    if budgets.exists():
        budgets.write_text('\n'.join(line for line in budgets.read_text().splitlines()
                                    if not line.startswith('gallery/'))+'\n')
    (id1/DISABLED_MARKER).write_text('NPC gallery disabled by explicit --no-npc-gallery.\n')
    print('WARNING: NPC gallery disabled for debugging only. All NPC assets required by the game remain required; world NPCs are not omitted.', flush=True)
    return {'status': 'disabled', 'reason': 'explicit --no-npc-gallery',
            'marker': 'id1/' + DISABLED_MARKER, 'in_game_notice': 'gallery commands explain the omission'}


_DEPENDENCIES = {}


def _scan_dependencies(task):
    """Worker: one source mesh's dependency names and hashes, by the cache's own code."""
    from gallery_cache import Dependencies
    data, mesh = task
    if data not in _DEPENDENCIES:
        _DEPENDENCIES.clear()
        _DEPENDENCIES[data] = Dependencies(data)
    dependencies = _DEPENDENCIES[data]
    try:
        names = dependencies.mesh(mesh)
    except ValueError:
        return mesh, None, {}   # missing: the serial pass raises the same error
    return mesh, names, {name: dependencies.record(name) for name in names}


def spec_meshes(spec):
    """The source meshes Dependencies.for_spec reads for one gallery spec."""
    if spec['kind'] == 'NPC_':
        a = spec['appearance']
        return {normpath(a['skeleton'])} | {normpath('meshes/' + p['mesh']) for p in a['parts']}
    return {normpath('meshes/' + spec['mesh'])}


def prefetch_dependencies(dependencies, data, specs, jobs):
    """Parse every source mesh and hash its textures on the shared pool before the
    identities are built (the serial pass took about 125 s of the gallery's start,
    on the critical path; BUILD-IDLE-STAGES-33). Fills the same caches the serial
    Dependencies methods fill; identities, cache keys and outputs are unchanged."""
    from build_parallel import ordered_map
    meshes = sorted({mesh for spec in specs for mesh in spec_meshes(spec)} - set(dependencies.meshes))
    for mesh, names, hashes in ordered_map(_scan_dependencies, [(str(data), mesh) for mesh in meshes],
                                           max(1, min(jobs, len(meshes) or 1))):
        if names is None:
            continue
        dependencies.meshes[mesh] = names
        dependencies.hashes.update(hashes)


def gallery_filter(closure):
    """{casefolded record IDs} the gallery keeps for an area build's reference closure
    (the closure's 'npcs' group: its NPCs and creatures), or None for every record."""
    if not closure or 'npcs' not in (closure.get('groups') or ()):
        return None
    return set(closure.get('npcs', ())) | set(closure.get('creatures', ()))


def collect_models(tasks, jobs):
    """Collect independent models promptly; export in original catalogue order.

    Reused, converted and failed are disjoint completion counts, not a sample
    describing every 25th model. Failed models remain in the result and still
    fail the complete-gallery gate. No coverage, quality or cache policy changes.
    """
    from gallery_cache import convert_cached
    results = {}
    counts = {'reused': 0, 'converted': 0, 'failed': 0}
    worker_seconds = 0.
    started = time.monotonic()
    last_report = started

    def report(now):
        print(f"Gallery {len(results)}/{len(tasks)}: reused {counts['reused']}, "
              f"converted {counts['converted']}, failed {counts['failed']}, "
              f"remaining {len(tasks)-len(results)} | elapsed {now-started:.1f}s", flush=True)

    report(started)
    for result, action, seconds in completed_map(convert_cached, tasks, jobs):
        key = result['key']
        if key in results:
            raise ValueError('Duplicate completed gallery model: ' + key)
        results[key] = result
        worker_seconds += seconds
        failed = result['status'] != 'ready'
        if failed:
            counts['failed'] += 1
            print(f"Gallery model {key} failed: {result.get('error', 'unknown error')}", flush=True)
        elif action == 'hit':
            counts['reused'] += 1
        elif action == 'converted':
            counts['converted'] += 1
        else:
            raise ValueError('Unknown gallery cache action: ' + action)
        now = time.monotonic()
        if failed or len(results) % 25 == 0 or len(results) == len(tasks) or now-last_report >= 5:
            report(now)
            last_report = now
    # finish_catalogue serializes this mapping as well as using its model keys.
    # Restore the exact original spec order, not alphabetical/completion order.
    ordered = {task[2]: results[task[2]] for task in tasks}
    if len(ordered) != len(results):
        raise ValueError('Gallery results do not match requested model keys')
    return ordered, counts, worker_seconds


def prepare(data, palette_path, out, qbsp, vis, light, jobs, cache=None, seed_run=None, closure=None):
    """Convert the complete NPC/creature catalogue; unresolved models must fail.

    Do not reduce catalogue coverage or protected geometry to save build time.
    Any exception requires a specific case and explicit project-owner approval.
    All source records remain accounted for; normal game builds require this
    inspection gallery as well as every NPC asset required by the game.
    """
    data = Path(data); out = ensure_external(Path(out), 'NPC gallery output')
    # Fresh output, verified persistent cache: no blind adoption of old files.
    out.mkdir(parents=True, exist_ok=False)
    models = out/'gallery'; models.mkdir()
    (out/'gfx').mkdir(); palette = Path(palette_path).read_bytes()
    if len(palette) != 768:
        raise ValueError('Expected 256-colour palette')
    (out/'gfx/palette.lmp').write_bytes(palette)
    from gallery_cache import (Dependencies, converter_sources, environment, identity,
                               cache_location, import_rc9, preflight)
    started = time.monotonic()
    print("npc-gallery: pre-baking in-game character models...", flush=True)
    cache = cache_location(cache or out.parent/'gallery-cache-v1', data, out)
    # An area build (--exclude-unreferenced npcs): exactly the NPCs and creatures the area references.
    only = gallery_filter(closure)
    entries, specs = catalogue(data, only=only); results = {}
    if only is not None:
        print(f'NPC gallery: reference closure of {", ".join(closure.get("cells", [])[:4])}'
              f'{" ..." if len(closure.get("cells", [])) > 4 else ""}: {len(entries)} of the area\'s records.', flush=True)
    print(f'NPC gallery: {len(entries)} source records; {len(specs)} distinct models; {jobs} workers.', flush=True)
    print('Checking gallery source dependencies and persistent cache...', flush=True)
    dependencies = Dependencies(data); sources = converter_sources(); env = environment()
    prefetch_dependencies(dependencies, data, specs.values(), jobs)
    identities = {key: identity(spec, palette, dependencies.for_spec(spec), sources, env)
                  for key, spec in specs.items()}
    imported = import_rc9(seed_run, data, palette, specs, identities, cache, env) if seed_run else None
    capacity = preflight(cache, out, identities)
    print(f"Gallery cache: {capacity['verified_hits']} verified hits, {capacity['misses']} conversions required.", flush=True)
    if imported:print('Compatible rc9 pairs imported:', imported['imported'], flush=True)
    tasks = [(str(data), str(models), key, spec, palette, str(cache), identities[key]) for key, spec in specs.items()]
    print('Gallery scheduling: completion order; bounded queue; stable catalogue export.', flush=True)
    results, counts, worker_seconds = collect_models(tasks, jobs)
    dependencies.verify_unchanged()
    if sources != converter_sources() or env != environment():
        raise ValueError('Gallery converter environment changed during conversion')
    cache_report = {'format': 'AmiWind gallery reuse 1', 'hits': counts['reused'],
                    'converted': counts['converted'], 'failed': counts['failed'],
                    'completed': len(results), 'scheduler': 'bounded-completion-v1',
                    'imported_rc9': imported, 'capacity': capacity,
                    'dependency_and_model_seconds': round(time.monotonic()-started, 3),
                    'worker_seconds_sum': round(worker_seconds, 3),
                    'scope': 'host-only reuse; every model and catalogue entry remains required'}
    (out/'gallery-cache.json').write_text(json.dumps(cache_report, indent=2)+'\n')
    failed = finish_catalogue(entries, results, out, palette)
    budgets = write_allowances(models, results, entries, out/'model-budgets.txt')
    (out/'model-budget-audit.json').write_text(json.dumps(budgets, indent=2)+'\n')
    if failed or budgets['unresolved'] or any('-' in e['models'] for e in entries):
        raise ValueError('NPC gallery conversion incomplete; see gallery-audit.json and model-budget-audit.json')
    for command in ([str(Path(qbsp).resolve()), 'charplane.map'],
                    [str(Path(vis).resolve()), '-threads', str(jobs), 'charplane.bsp'],
                    [str(Path(light).resolve()), *light_args('charplane.bsp')]):
        subprocess.run(command, cwd=out, check=True)
    (out/'maps').mkdir(); shutil.move(out/'charplane.bsp', out/'maps/charplane.bsp')
    count, files = catalogue_files(models/'catalog.txt')
    receipt = {'format': FORMAT, 'records': count, 'models': len(results),
               'scope': ({'reference_closure': closure.get('cells', []), 'records': len(entries)}
                         if only is not None else 'every NPC and creature'),
               'master_sha256': input_sha256(child_ci(data, 'Morrowind.esm')),
               'palette_sha256': hashlib.sha256(palette).hexdigest(),
               'files': {name: {'bytes': (out/name).stat().st_size, 'sha256': sha(out/name)} for name in sorted(files)}}
    report = validate_payload(out, receipt)
    (out/'gallery-build.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(report, indent=2), flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('data-files', 'palette', 'out', 'qbsp', 'vis', 'light'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--cache', type=Path, help='Persistent verified model cache; defaults beside output')
    parser.add_argument('--seed-run', type=Path, help='Stopped rc9 build run with compatible input/source provenance')
    parser.add_argument('--reference-closure', type=Path,
                        help='Area build (--exclude-unreferenced npcs): only the NPCs and creatures this '
                             'reference closure lists')
    add_jobs(parser); args = parser.parse_args()
    closure = json.loads(args.reference_closure.read_text(encoding='utf-8')) if args.reference_closure else None
    try:
        prepare(args.data_files, args.palette, args.out, args.qbsp, args.vis, args.light, resolve_jobs(args.jobs),
                args.cache, args.seed_run, closure=closure)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f'Error: {exc}\n')


if __name__ == '__main__':
    main()
