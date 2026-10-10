#!/usr/bin/env python3
"""Payload preflight: the image step's read-only payload checks, run first.

The image step (build_aga.py finalize_image) takes 25-40 minutes on a full build and used to meet some
payload errors only at its end (CHIM-HARVEST-SPECIALS-33: three release-candidate image runs stopped on
the harvest catalogue check). This preflight calls the SAME check functions over the staged payload
before the image step writes anything, in parallel, and reports every error together.

It never changes the payload: checks that need the image's final map set (after the CHIM frame maps are
written and the legacy maps of CHIM towns leave the image) run on that planned set, laid out as empty
placeholder files in a scratch folder (tools/build_scratch.py) that is always removed. Checks:

- chim-receipt: the CHIM world's receipts (build_aga.chim_world_receipt, as chim_frame_maps reads them);
- chim-inputs: every legacy map a frame map is written from is staged, or planned by the image step's own
  Seyda Neen conversion / recorded install that runs before the frame maps (checked again once written);
- harvest-catalogues: build_aga.harvest_fingerprint_entries (the save fingerprint, the harvest and compact
  heap profiles and the interior sections all call it) on the planned final map set;
- interior-sections: interior_sections.fingerprint_entries (the save fingerprint reads it) on the staged
  payload, and none of the maps it binds is one the image removes (BUILD-IMAGE-NO-RESUME-33);
- payload-names: amiga_fs.check_payload_names (FFS names of at most 30 bytes, no case collisions);
- host-paths: amiga_fs.check_payload_host_paths (no build path in a shipped text file);
- disk-layout: the world partition batches (world_volumes.partition_batches, as pack makes them) and the
  planned drives (plan_drives: partitions below 2 GiB and starting below 2 GiB, files below the file
  limit, drives below 4 GiB) for the planned payload, music and CHIM volume included;
- music: every soundtrack file is there, decodes and matches its manifest hash;
- actor-frames: every placed actor model has a declared frame layout (an animation kit layout <model>.anm,
  or the previous 8 idle / 21 town actor layouts), every layout fits its model (and its mover), and every
  carried-item tag table has one row per model frame (tools/actor_frames.py, ANIMKIT-ACTOR-ABI-SITES-35);
- engine-map-limits: every staged map the image keeps fits the engine's per-map tables (edicts, model and
  sound precaches, static entities, the scenery catalogue; tools/map_engine_limits.py,
  BUILD-BUDGET-ENGINE-LIMITS-35). The image step checks the final map set again after the frame maps.

Later stages still run every check on what they write; this only moves the first failure from the end
of the image step to its first seconds. tools/build.py --check-payload RUN runs it alone on a run.
"""
import json
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def planned_maps(id1, chim_world):
    """The image's final exterior map changes on CHIM, read only: (added frame map names,
    removed id1-relative files, towns not on CHIM). Empty without a CHIM world."""
    if not chim_world:
        return [], set(), []
    from build_aga import chim_world_receipt, staged_extra_towns
    from chim.frame_map import SPECIALS, legacy_area_maps, map_name, town_files
    from town_config import runtime_towns
    _, areas = chim_world_receipt(chim_world)
    rows = {t['id']: t for t in runtime_towns()}
    added = [map_name(rows[area]['name']) for area in areas if area in rows]
    if 'seyda' in areas:
        added += [map_name(name) for name in SPECIALS]
    removed = {rel for area in areas for rel in legacy_area_maps(id1, area)}
    not_on_chim = [town['id'] for town in staged_extra_towns(id1) if town['id'] not in areas]
    removed |= {rel for town in not_on_chim for rel in town_files(id1, town)}
    return added, removed, not_on_chim


def check_chim_inputs(id1, chim_world, pending=None, chim_towns=()):
    """Every legacy map a frame map not yet written is made from (chim_frame_maps reads them).

    pending: {id1-relative file: region names for a table, else None} the image step itself still writes
    before the frame maps (the Seyda Neen region conversion or the recorded install, build_aga.seyda_pending):
    those count as staged; a pending region table's maps are its planned region names. Only the early preflight passes it;
    the image step's later preflight (finalize_image) checks the written files
    (BUILD-SEYDA-CONVERTED-NOT-STAGED-35).
    chim_towns: towns made from the game data by the chim-town stage (CHIM-LEGACY-CHAIN-33): their frame maps
    take the chim-town entities, no legacy map."""
    from build_aga import chim_world_receipt
    from chim.frame_map import SPECIALS, map_name, region_table
    from town_config import runtime_towns
    pending = pending or {}
    def staged(rel):
        return (id1/rel).is_file() or rel in pending
    _, areas = chim_world_receipt(chim_world)
    rows = {t['id']: t for t in runtime_towns()}
    missing = []
    for area in areas:
        if area not in rows:
            raise ValueError('Unknown town: ' + area)
        if area in chim_towns:
            continue
        row = rows[area]
        if (id1/'maps'/(map_name(row['name'])+'.bsp')).is_file():
            continue
        if (id1/row['regions']).is_file():
            names = [name for name, _ in region_table(id1/row['regions'])[1]]
        elif pending.get(row['regions']) is not None:
            names = list(pending[row['regions']])
        else:
            missing.append(row['regions'])
            continue
        missing += ['maps/%s.bsp' % name for name in names if not staged('maps/%s.bsp' % name)]
    if 'seyda' in areas:
        missing += ['maps/%s.bsp' % name for name in SPECIALS
                    if not (id1/'maps'/(map_name(name)+'.bsp')).is_file() and not staged('maps/%s.bsp' % name)]
    if missing:
        raise ValueError('CHIM frame map inputs are not staged: ' + ', '.join(missing[:12]) +
                         (' and %d more' % (len(missing) - 12) if len(missing) > 12 else ''))


def planned_catalogues(id1, harvest, data_files):
    """The harvest catalogues the image step will write (harvest_build.install: one per shipped exterior map
    with harvestable plants, before the heap admission drops some), read only. A superset: every map that
    can get a catalogue must be one the final image can bind it to."""
    from harvest_build import map_selections, source_placements
    _, _, refs = source_placements(harvest, data_files)
    return sorted(map_selections(id1, refs)[1])


def check_harvest(id1, added, removed, harvest=None, data_files=None):
    """harvest_fingerprint_entries on the planned final map set: maps after the frame maps are written
    and the removed files are gone, as empty placeholders; catalogues, region tables and harvest models
    copied (all small). Before the image step installs the catalogues (it does so late, after the BSP
    optimizer), the catalogues it will write are planned from the harvest source and checked as empty
    placeholders (BUILD-IMAGE-NO-RESUME-33: the check then runs in the image step's first minute, not
    after its passes). The temporary folder is always removed."""
    from build_aga import harvest_fingerprint_entries
    planned = []
    if not any(id1.glob('harvest-*.txt')) and harvest and data_files:
        planned = planned_catalogues(id1, harvest, data_files)
    if not any(id1.glob('harvest-*.txt')) and not planned:
        return 0
    from build_scratch import scratch_dir
    with scratch_dir(prefix='payload-preflight-', keep_on_failure=False) as tmp:
        root = tmp/'id1'
        (root/'maps').mkdir(parents=True)
        for path in list(id1.glob('harvest-*.txt')) + list(id1.glob('*-regions.txt')):
            if path.name not in removed:
                shutil.copyfile(path, root/path.name)
        if (id1/'progs/harvest').is_dir():
            from mwad.paths import copy_tree
            copy_tree(id1/'progs/harvest', root/'progs/harvest')
        for path in (id1/'maps').glob('*.bsp'):
            if 'maps/' + path.name not in removed:
                (root/'maps'/path.name).touch()
        for name in added:
            (root/'maps'/(name+'.bsp')).touch()
        for name in planned:
            (root/('harvest-'+name+'.txt')).write_bytes(b'AWH1 0 0 0\n')
        return len(harvest_fingerprint_entries(root))


def check_interior_sections(id1, removed):
    """interior_sections.fingerprint_entries (read only) on the staged payload; a bound file the image
    removes later would fail it at the end, so it fails here."""
    from interior_sections import fingerprint_entries
    entries = fingerprint_entries(id1)
    gone = sorted(name for name, _ in entries if name in removed)
    if gone:
        raise ValueError('Interior sections bind files the image removes: ' + ', '.join(gone[:12]))
    return len(entries)


def check_engine_map_limits(id1, removed):
    """map_engine_limits.check_maps on the staged maps the image keeps; the number of maps checked."""
    from map_engine_limits import check_maps
    skip = {rel.split('/', 1)[1] for rel in removed if rel.startswith('maps/')}
    return check_maps(id1/'maps', skip=skip)['maps']


def check_disk_layout(boot, removed, music_files, chim_world):
    """The planned partitions and drives through the disk-layout gate, before anything is written."""
    from world_volumes import (RDB_BYTES, partition_batches, plan_drives, plan_partitions, planned_partition,
                               require_partition_plans)
    id1 = boot/'id1'
    files = {p.relative_to(boot).as_posix(): p.stat().st_size for p in boot.rglob('*') if p.is_file()}
    for rel in removed:
        files.pop('id1/' + rel, None)
    # The soundtrack is copied before world_volumes.pack measures the boot payload: count it first.
    for name, size in music_files:
        files['id1/music/' + name] = size
    worlds = []
    directory = id1/'world/regions.awr'
    if directory.exists():
        import struct
        raw = directory.read_bytes()
        if raw[:4] != b'AWR2' or len(raw) < 64:
            raise ValueError('Invalid region directory')
        count = struct.unpack_from('<I', raw, 4)[0]
        if not 1 <= count <= 8192 or len(raw) != 64 + count*52:
            raise ValueError('Invalid region directory count')
        paths = [id1/'maps'/f'vf{i:04d}.bsp' for i in range(count)]
        terrain = sum(p.stat().st_size for p in paths)
        _, batches = partition_batches(paths, sum(files.values()) - terrain)
        worlds = plan_partitions(batches)
        require_partition_plans(worlds)
        for batch in batches:
            for path in batch:
                files.pop(path.relative_to(boot).as_posix(), None)
    if chim_world and (Path(chim_world)/'chim').is_dir():
        base = Path(chim_world)/'chim'
        chim = planned_partition('DW%d' % len(worlds), [dict(path=p.relative_to(base).as_posix(), bytes=p.stat().st_size)
                                                        for p in sorted(base.rglob('*')) if p.is_file()],
                                 'AW_WORLD%d' % len(worlds))
        require_partition_plans([chim])
        worlds.append(chim)
    boot_plan = planned_partition('DH0', [dict(path=k, bytes=v) for k, v in sorted(files.items())], 'AMIWIND')
    plans = plan_drives(boot_plan, worlds)
    return dict(drives=len(plans), partitions=1 + len(worlds),
                bytes=sum(p['bytes'] for p in plans), rdb_bytes=RDB_BYTES)


def check_file_formats(id1):
    """Every staged id1 file has a format the image step's palette overlay knows (sky_palette_overlay.spans):
    a new file type fails here in seconds, not after the image work (ANIMKIT-IMAGE-FORMATS-35)."""
    from sky_palette_overlay import unknown_formats
    id1 = Path(id1)
    rels = [p.relative_to(id1).as_posix() for p in sorted(id1.rglob('*')) if p.is_file()]
    bad = unknown_formats(rels)
    if bad:
        raise ValueError('%d staged files have a format the image step does not know (first: %s); declare the '
                         'format in tools/sky_palette_overlay.py' % (len(bad), ', '.join(bad[:5])))


def check_actor_frames(id1, removed):
    """Every placed actor model's frame layout, every animation kit layout and every item tag table
    (tools/actor_frames.py audit_payload): the guard torch companions, the ground check and the engine's
    item tags read them; a layout problem fails here in seconds (ANIMKIT-ACTOR-ABI-SITES-35)."""
    from actor_frames import audit_payload
    return audit_payload(id1, removed)


def check_music(music):
    """The soundtrack the image copies: every file there, decodable, matching its manifest hash."""
    import hashlib
    from prepare_music import unpack_stream
    manifest = json.loads((music/'soundtrack.json').read_text())
    sizes = []
    for track in manifest['tracks']:
        source = music/track['file']
        raw = source.read_bytes()
        unpack_stream(raw)
        if hashlib.sha256(raw).hexdigest() != track['sha256']:
            raise ValueError('Music manifest mismatch')
        sizes.append((track['file'], len(raw)))
    sizes.append(('soundtrack.json', (music/'soundtrack.json').stat().st_size))
    return sizes


def run(out, *, chim_world=None, music=None, jobs=1, harvest=None, data_files=None, report_path=None,
        pending=None, chim_towns=()):
    """Run every check over the staged payload OUT (OUT/boot). Prints one summary line; raises
    ValueError listing every error together. Returns the report. pending: files the image step still
    writes before its frame maps (check_chim_inputs)."""
    from amiga_fs import check_payload_host_paths, check_payload_names
    started = time.monotonic()
    out = Path(out)
    boot = out/'boot'
    id1 = boot/'id1'
    if not id1.is_dir():
        raise ValueError('Payload preflight: no staged payload at ' + str(id1))
    errors, results = [], {}
    try:
        added, removed, not_on_chim = planned_maps(id1, chim_world)
    except (OSError, ValueError, KeyError) as exc:
        added, removed, not_on_chim = [], set(), []
        errors.append(('chim-receipt', exc))
    checks = [('payload-names', lambda: check_payload_names(boot)),
              ('file-formats', lambda: check_file_formats(id1)),
              ('host-paths', lambda: check_payload_host_paths(boot, [out.resolve()])),
              ('harvest-catalogues', lambda: check_harvest(id1, added, removed, harvest, data_files)),
              ('interior-sections', lambda: check_interior_sections(id1, removed)),
              ('engine-map-limits', lambda: check_engine_map_limits(id1, removed)),
              ('actor-frames', lambda: check_actor_frames(id1, removed))]
    if chim_world:
        checks.append(('chim-inputs', lambda: check_chim_inputs(id1, chim_world, pending, set(chim_towns))))
    music_result = {}
    if music:
        def music_check():
            music_result['files'] = check_music(Path(music))
            return len(music_result['files']) - 1
        checks.append(('music', music_check))
    with ThreadPoolExecutor(max_workers=max(1, min(int(jobs or 1), len(checks)))) as pool:
        futures = [(name, pool.submit(fn)) for name, fn in checks]
        for name, future in futures:
            try:
                results[name] = future.result()
            except (OSError, ValueError, KeyError) as exc:
                errors.append((name, exc))
    # The layout needs the music sizes; it runs last (seconds: stat only).
    if not music or 'files' in music_result:
        try:
            results['disk-layout'] = check_disk_layout(boot, removed, music_result.get('files', []), chim_world)
        except (OSError, ValueError) as exc:
            errors.append(('disk-layout', exc))
    count = len(checks) + 1 + (1 if chim_world else 0)
    seconds = time.monotonic() - started
    report = dict(checks=count, errors=[dict(check=name, error=str(exc)) for name, exc in errors],
                  seconds=round(seconds, 1), frame_maps_planned=added, removed_planned=len(removed),
                  not_on_chim=not_on_chim, results={k: v for k, v in results.items() if v is not None})
    if pending:
        report['pending_from_image_step'] = len(pending)
    print(f'Payload preflight: {count} checks, {len(errors)} errors, {seconds:.1f} s', flush=True)
    if report_path is not None:  # for the end summary (tools/build_summary.py)
        Path(report_path).write_text(json.dumps(report, indent=1) + chr(10), encoding='utf-8', newline=chr(10))
    if errors:
        raise ValueError('Payload preflight found %d error(s) before the image step wrote anything:\n' % len(errors) +
                         '\n'.join('  %s: %s' % (name, exc) for name, exc in errors))
    return report
