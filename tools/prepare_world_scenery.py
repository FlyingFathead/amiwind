#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Append private textured scenery to validated terrain; never modify inputs."""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import shutil
import time

from build_jobs import add_jobs, resolve_jobs
from build_parallel import ordered_map
from world_scenery import region_references

_INDEX = None
_MODELS = {}


def visual_profiles(index):
    profiles = {}
    for model in index['models']:
        mushroom = 'flora_emp_parasol_' in model['source'] or 'flora_t_mushroom_' in model['source']
        target = 160 if mushroom else 64
        profiles[model['source']] = {'texture_size': 64, 'ratio': min(1., target / max(1, model['triangles'])),
                                     'visual_triangle_target': target, 'preserve_shared_seams': mushroom}
    return profiles


def convert_region(task):
    global _INDEX
    from prepare_mesh_bsp import append_meshes, _prepare_model
    terrain, scenery, palette, out, entry = task
    started = time.monotonic()
    if _INDEX is None:
        _INDEX = json.loads((scenery / 'scenery-index.json').read_text(encoding='utf-8'))
    selected = region_references(_INDEX, entry)
    local = out / entry['name']
    local.mkdir(exist_ok=False)
    source = terrain / entry['name'] / 'scene.bsp'
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    if source_hash != entry['converted']['sha256']:
        raise ValueError('Retained terrain hash mismatch: ' + entry['name'])
    if selected:
        packet = scenery / 'scenery.mwpak'
        try:
            os.link(packet, local / 'scenery.mwpak')
        except OSError:
            shutil.copyfile(packet, local / 'scenery.mwpak')
        profiles = visual_profiles(_INDEX)
        subset = {**_INDEX, 'references': selected,
                  'groups': {'world_scenery': {'references': [], 'visual_profiles': profiles}}}
        (local / 'scenery-index.json').write_text(json.dumps(subset) + '\n', encoding='utf-8')
        with (local / 'conversion.log').open('w', encoding='utf-8') as log, contextlib.redirect_stdout(log):
            for mi in {r['model_index'] for r in selected}:
                if mi not in _MODELS:
                    model = _INDEX['models'][mi]
                    _, prepared = _prepare_model((mi, model, profiles[model['source']], packet, _INDEX['textures']))
                    _MODELS[mi] = prepared
            def convert():
                return append_meshes(source, local / 'scene.bsp', local, palette,
                                     centre=[x / .25 for x in entry['origin'][:2]], jobs=1,
                                     references=[r['number'] for r in selected], prepared_models=_MODELS,
                                     retain_dressing=True, collision_bounds=entry['coverage'],
                                     map_identity=entry['name'],cell_identity=','.join(map(str,entry['cell'])) if entry.get('cell') else None,subcell_identity=entry['name'] if entry.get('subcell') is not None else None)
            report = convert()
            # routed hulls add a clipnode per cut: a region they push past its reserve keeps the chains
            # (BUILD-ROUTED-FLORA-RESERVE-33); the region's other budgets are checked as before
            from mesh_geometry_env import model_hull_mode, model_hull_override
            if report['clipnodes'] > 32767 and model_hull_mode() != 'chain' and report.get('model_hull', {}).get('routed'):
                routed = report['clipnodes']
                with model_hull_override('chain'):
                    report = convert()
                report['model_hull_fallback'] = {'from': 'routed', 'clipnodes_routed': routed,
                                                 'clipnodes_chain': report['clipnodes'], 'reserve': 32767}
        if report['instances'] != len(selected):
            raise ValueError('Scenery placement count mismatch: ' + entry['name'])
        if report['unique_models'] > 240 or report['instances'] > 550:
            raise ValueError('Scenery runtime model/entity reserve exceeded: ' + entry['name'])
        if report['faces'] > 30000 or report['clipnodes'] > 32767 or report['bytes'] > 4 * 1024 * 1024:
            raise ValueError('Scenery region storage/collision budget exceeded: ' + entry['name'])
    else:
        shutil.copyfile(source, local / 'scene.bsp')
        report = {'instances': 0, 'unique_models': 0, 'retained_terrain_only': True}
    if hashlib.sha256(source.read_bytes()).hexdigest() != source_hash:
        raise ValueError('Retained terrain changed during overlay: ' + entry['name'])
    # No wall time in the region receipt: a stage output is byte-reproducible (BUILD-OUTPUTS-NOT-REPRODUCIBLE-33).
    print(f"Region {entry['name']}: {time.monotonic() - started:.1f} s", flush=True)
    report.update(name=entry['name'],
                  bytes=(local / 'scene.bsp').stat().st_size,
                  original_terrain_sha256=source_hash,
                  sha256=hashlib.sha256((local / 'scene.bsp').read_bytes()).hexdigest(),
                  source_references=[{'cell': r['cell'], 'number': r['number'], 'kind': r['kind']} for r in selected])
    (local / 'conversion.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    # Per-region packet/index aliases are scratch; the shared owned export is retained.
    for name in ('scenery.mwpak', 'scenery-index.json'):
        path = local / name
        if path.exists():
            path.unlink()
    return report


def convert_region_cached(task):
    """Worker: a region from the unit cache when its inputs are unchanged (development builds, and
    release builds with --allow-release-reuse; tools/pass_cache.py UnitCache), else convert_region,
    then record it. A stage that failed late resumes from its finished regions (BUILD-IMAGE-NO-RESUME-33)."""
    terrain, scenery, palette, out, entry, cache, shared = task
    if cache is None:
        return convert_region((terrain, scenery, palette, out, entry))
    source = terrain / entry['name'] / 'scene.bsp'
    if hashlib.sha256(source.read_bytes()).hexdigest() != entry['converted']['sha256']:
        raise ValueError('Retained terrain hash mismatch: ' + entry['name'])
    inputs = {'entry': entry, 'shared': shared}
    row = cache.restore_unit(inputs, out / entry['name'])
    if row is not None:
        return row
    report = convert_region((terrain, scenery, palette, out, entry))
    cache.store_unit(inputs, json.loads(json.dumps(report)), out / entry['name'])
    return report


def unit_cache(scenery, palette):
    """(the region unit cache or None, the inputs every region shares, by content)."""
    from pass_cache import UnitCache
    cache = UnitCache.open('world-scenery-region', {}, __file__)
    if cache is None:
        return None, None
    from build_parallel import sha256_file
    names = {'scenery_index': scenery / 'scenery-index.json', 'scenery_packet': scenery / 'scenery.mwpak',
             'palette': palette}
    return cache, {key: sha256_file(path) if path.is_file() else None for key, path in names.items()}


def prepare(terrain, scenery, palette, out, jobs, only=None):
    from mwad.paths import ensure_external
    terrain, scenery, palette = terrain.resolve(), scenery.resolve(), palette.resolve()
    out = ensure_external(out, 'private world scenery overlay')
    out.mkdir(parents=True, exist_ok=False)
    baseline = json.loads((terrain / 'world-regions.json').read_text(encoding='utf-8'))
    index = json.loads((scenery / 'scenery-index.json').read_text(encoding='utf-8'))
    if index['errors']:
        raise ValueError('Scenery input has conversion errors')
    if index.get('master_sha256') and index['master_sha256'] != baseline['master_sha256']:
        raise ValueError('Scenery and terrain master inputs differ')
    entries = baseline['regions']
    if only:
        entries = [e for e in entries if e['name'] in only]
        if len(entries) != len(set(only)):
            raise ValueError('Unknown diagnostic region')
    started = time.monotonic()
    results = []
    cache, shared = unit_cache(scenery, palette)
    for result in ordered_map(convert_region_cached, [(terrain, scenery, palette, out, e, cache, shared)
                                                      for e in entries], jobs):
        results.append(result)
        print(f"REGION {len(results)}/{len(entries)} {result['name']} references={result['instances']}", flush=True)
    covered = {(tuple(r['cell']), r['number']) for result in results for r in result['source_references']}
    expected = {(tuple(r['cell']), r['number']) for r in index['references']}
    if not only and covered != expected:
        raise ValueError('Full-world overlay omitted source references')
    receipt = {'format': 'AmiWind world scenery overlay 1', 'diagnostic_subset': bool(only),
               'terrain_directory_sha256': hashlib.sha256((terrain / 'world-regions.json').read_bytes()).hexdigest(),
               'scenery_index_sha256': hashlib.sha256((scenery / 'scenery-index.json').read_bytes()).hexdigest(),
               'palette_sha256': hashlib.sha256(palette.read_bytes()).hexdigest(),
               'covered_source_references': len(covered),
               'scope': 'Retained terrain BSPs with original rock/giant-mushroom placements. Town handoff and emulator acceptance remain separate.',
               'regions': results}
    (out / 'world-scenery.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(f'World scenery: {time.monotonic() - started:.1f} s', flush=True)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('terrain', 'scenery', 'palette', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--only', nargs='+')
    add_jobs(parser)
    from scenery_reduce import add_options, apply_options
    add_options(parser)
    args = parser.parse_args()
    apply_options(args)
    import build_profile
    build_profile.instrument('world-scenery')
    result = prepare(args.terrain, args.scenery, args.palette, args.out, resolve_jobs(args.jobs), args.only)
    print('OVERLAY PASSED', len(result['regions']), 'regions;', result['covered_source_references'], 'source references', flush=True)


if __name__ == '__main__':
    main()
