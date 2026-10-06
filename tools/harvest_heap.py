# SPDX-License-Identifier: GPL-3.0-only
"""Target-ABI external harvest cache/loader cost and separate static allowance."""
import hashlib
from pathlib import Path
import struct
from alias_stream_heap import apply as alias_policy_apply, fallback as alias_fallback


def alias_cost(raw, sizes):
    """One-frame alias allocations after the shared MDL validator has passed."""
    skins, width, height, vertices, triangles, frames = struct.unpack_from('<6i', raw, 48)
    if skins != 1 or frames != 1:
        raise ValueError('Harvest heap expects a one-frame alias')
    align = lambda n: (n + 15) & ~15
    alloc = lambda n: sizes['hunk'] + align(n)
    header = alloc(sizes['aliashdr'] + sizes['mdl'] + vertices*sizes['stvert'] + triangles*sizes['mtriangle'])
    decoded = header + alloc(sizes['maliasskindesc']) + alloc(width*height) + alloc(vertices*sizes['trivertx'])
    return alias_policy_apply(raw,sizes,dict(file_bytes=len(raw), vertices=vertices, triangles=triangles,
                decoded_hunk_bytes=decoded, cache_bytes=align(decoded+sizes['cache_system']),
                source_file_hunk_fallback_bytes=alloc(len(raw)+1),
                external_malloc_peak_bytes=len(raw)+decoded))


def profile(id1, sizes):
    if sizes.get('harvest_storage_mode',0)==1:
        from compact_harvest_heap import profile as compact_profile
        return compact_profile(id1,sizes)
    root = Path(id1)
    static_keys = ('harvest_proxy_static', 'harvest_catalogue_extension')
    if any(key in sizes for key in static_keys):
        if any(type(sizes.get(key)) is not int or sizes[key] < 0 for key in static_keys):
            raise ValueError('Actual target harvest static ABI measurements are required')
        static = sum(sizes[key] for key in static_keys)
    else:
        static = 0
    catalogues = sorted(root.glob('harvest-*.txt'), key=lambda p: p.name)
    external = []
    for path in catalogues:
        if not 0 < path.stat().st_size <= 65536:
            raise ValueError('Harvest heap catalogue exceeds runtime byte bound')
        raw = path.read_bytes()
        try: header = raw.decode('ascii').splitlines()[0].split()
        except (UnicodeError, IndexError): raise ValueError('Invalid harvest heap catalogue') from None
        if not header or header[0] not in ('AWH1', 'AWH2', 'AWH3', 'AWH4'):
            raise ValueError('Unknown harvest heap catalogue representation')
        if header[0] == 'AWH4': external.append(path)
    if not external:
        if not static:
            return None
        return dict(catalogues=[], fingerprint_entries=[], models={}, unique_models=0,
                    global_warm_cache_ceiling_bytes=0, map_costs={},
                    proxy_static_bytes=sizes['harvest_proxy_static'],
                    catalogue_extension_static_bytes=sizes['harvest_catalogue_extension'],
                    additional_static_allowance_bytes=static, maximum_external_malloc_peak_bytes=0,
                    scope='Candidate engine static storage exists even with no AWH4 catalogues; no dynamic models admitted',
                    native_acceptance='not_measured')
    required = ('aliashdr', 'mdl', 'stvert', 'mtriangle', 'maliasskindesc',
                'trivertx', 'cache_system', 'hunk', 'harvest_proxy_static',
                'harvest_catalogue_extension', 'harvest_plant_capacity', 'harvest_model_capacity')
    if any(type(sizes.get(key)) is not int or sizes[key] <= 0 for key in required):
        raise ValueError('AWH4 requires actual target alias and harvest ABI measurements')
    # Reuse the exact package/save binding validator, including missing/modified
    # model bytes, bounded catalogues, matching BSPs and common global identity.
    from build_aga import harvest_fingerprint_entries
    entries = harvest_fingerprint_entries(root,plant_capacity=sizes['harvest_plant_capacity'])
    bindings = {name: sha for name, sha in entries if name.startswith('progs/harvest/')}
    if not bindings:
        raise ValueError('AWH4 model dependency closure is empty')
    records = []
    for path in external:
        raw = path.read_bytes(); header = raw.decode('ascii').splitlines()[0].split()
        if int(header[3]) > sizes['harvest_plant_capacity'] or int(header[6]) > sizes['harvest_model_capacity']:
            raise ValueError('Harvest catalogue exceeds measured target capacity')
        lines=raw.decode('ascii').splitlines()
        records.append(dict(path=path.name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                            plants=int(header[3]), models=int(header[6]),
                            model_paths=[line.split()[0] for line in lines[1:1+int(header[6])]]))
    models = {}
    for name, expected in sorted(bindings.items()):
        raw = (root/name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('Harvest model changed during heap inspection')
        models[name] = dict(alias_cost(raw, sizes), sha256=expected)
    cached = sum(m['cache_bytes'] for m in models.values())
    map_costs = {}
    for record in records:
        active = [models[name] for name in record['model_paths']]
        resident = sum(m['cache_bytes'] for m in active)
        fallback = max(alias_fallback(m) for m in active)
        map_costs[record['path'][8:-4]] = dict(active_model_union=record['model_paths'],
            warm_cache_bytes=resident, loader_fallback_bytes=fallback,
            conservative_game_heap_peak_bytes=resident+fallback,
            conservative_total_allowance_charge_bytes=resident+fallback+static)
    return dict(catalogues=records, fingerprint_entries=entries, models=models,
                unique_models=len(models), global_warm_cache_ceiling_bytes=cached,
                map_costs=map_costs,
                proxy_static_bytes=sizes['harvest_proxy_static'],
                catalogue_extension_static_bytes=sizes['harvest_catalogue_extension'],
                additional_static_allowance_bytes=static,
                maximum_external_malloc_peak_bytes=max(m['external_malloc_peak_bytes'] for m in models.values()),
                scope='Each AWH4 map charges its unique declared model union and worst loader fallback. Inactive prior-map aliases are evictable cache, as in guard admission. Candidate static BSS is debited on every map, even when no AWH4 exists; it is separate Fast RAM, not a Hunk allocation.',
                native_acceptance='not_measured')


def apply(report, prepared):
    report['additional_static_allowance_bytes'] = 0
    report['additional_external_allocation_allowance_bytes'] = 0
    report['harvest_external'] = None
    if prepared is None:
        return
    name=report['map'].removesuffix('.bsp')
    active=prepared['map_costs'].get(name,{})
    cache = active.get('warm_cache_bytes',0)
    fallback = active.get('loader_fallback_bytes',0)
    extra = cache + fallback
    report['harvest_external'] = dict(unique_models=len(active.get('active_model_union',[])), warm_cache_bytes=cache,
        loader_fallback_bytes=fallback, conservative_game_heap_peak_bytes=extra,
        static_allowance_bytes=prepared['additional_static_allowance_bytes'],
        catalogue_hashes={r['path']:r['sha256'] for r in prepared['catalogues']})
    report['peak_before_external_harvest_bytes'] = report['peak_loader_bytes']
    report['peak_loader_bytes'] += extra
    report['resident_loader_bytes'] += cache
    report['resident_bytes_at_peak'] += cache
    report['temporary_input_bytes_at_peak'] += fallback
    report['classifier_allocation_failure_fallback_peak_bytes'] += extra
    report['additional_static_allowance_bytes'] = prepared['additional_static_allowance_bytes']
    if prepared.get('storage_mode')=='compact_offsets':
        reserve=active.get('external_allocator_reservation_allowance_bytes',0)
        report['additional_external_allocation_allowance_bytes']=reserve
        report['harvest_external'].update(storage_mode='compact_offsets',
            catalogue_requested_bytes=active.get('catalogue_requested_bytes',0),
            all_available_binding_bytes=active.get('all_available_binding_bytes',0),
            external_malloc_requested_peak_bytes=active.get('external_malloc_requested_peak_bytes',0),
            external_malloc_rounded_blocks_peak_bytes=active.get('external_malloc_rounded_blocks_peak_bytes',0),
            external_allocator_reservation_allowance_bytes=reserve)
    if extra:
        report['peak_section'] = 'conservative external harvest cache/load overlap'
