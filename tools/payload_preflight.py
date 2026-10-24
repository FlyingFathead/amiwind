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
- disk-layout: the layout plan (tools/layout_plan.py, the compact layout: the fewest partitions, each sized
  from its payload + headroom; written to the run as layout-plan.json, the image step follows it; the
  legacy layout: the world partition batches as world_volumes.pack makes them) and the planned drives
  (plan_drives: partitions below 2 GiB and starting below 2 GiB, files below the file limit, drives below
  4 GiB) for the planned payload, music, the media the image step adds and the CHIM volume included;
- music: every soundtrack file is there, decodes and matches its manifest hash;
- actor-frames: every placed actor model has a declared frame layout (an animation kit layout <model>.anm,
  or the previous 8 idle / 21 town actor layouts), every layout fits its model (and its mover), and every
  carried-item tag table has one row per model frame (tools/actor_frames.py, ANIMKIT-ACTOR-ABI-SITES-35);
- chim-native: each CHIM-native town (--chim-town output) takes its area from that output alone: no legacy-chain
  file of the town staged, no installed file staged with other bytes or from two outputs, the town an area of
  the CHIM world (chim_town.collisions, BUILD-IMAGE-CHIM-NATIVE-TOWN-36);
- guard-records: the guard torch records (guard source, model) of the staged maps and batch rooms fit the engine's
  guard torch table (tools/prepare_guard_torches.py MAX_RECORDS; a lower bound before the frame maps,
  GUARD-TORCH-TYPES-LIMIT-48);
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
    removed id1-relative files, towns not on CHIM). Empty without a CHIM world. The added frame maps
    are the towns' (and Seyda Neen's special maps) and the CHIM region frame maps, which keep their
    open-world map names (chim.frame_map.region_map_names, one per frame): the harvest step writes
    their catalogues (HARVEST-CHIM-REGION-LOSS-41), so they must count as maps of the payload."""
    if not chim_world:
        return [], set(), []
    from build_aga import chim_world_receipt, staged_extra_towns
    from chim.frame_map import SPECIALS, legacy_area_maps, map_name, region_map_names, town_files
    from town_config import runtime_towns
    _, areas = chim_world_receipt(chim_world)
    rows = {t['id']: t for t in runtime_towns()}
    added = [map_name(rows[area]['name']) for area in areas if area in rows]
    if 'seyda' in areas:
        added += [map_name(name) for name in SPECIALS]
    added += sorted(region_map_names(id1, chim_world, primary_only=True))
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
        from map_files import map_file
        if map_file(id1/'maps', map_name(row['name'])).is_file():
            continue
        if (id1/row['regions']).is_file():
            names = [name for name, _ in region_table(id1/row['regions'])[1]]
        elif pending.get(row['regions']) is not None:
            names = list(pending[row['regions']])
        else:
            missing.append(row['regions'])
            continue
        missing += ['maps/%s.bsp' % name for name in names if not staged('maps/%s.bsp' % name)]
    if 'seyda' in areas and 'seyda' not in chim_towns:   # a CHIM-native Seyda Neen's specials: from its output
        from map_files import map_file
        missing += ['maps/%s.bsp' % name for name in SPECIALS
                    if not map_file(id1/'maps', map_name(name)).is_file() and not staged('maps/%s.bsp' % name)]
    if missing:
        raise ValueError('CHIM frame map inputs are not staged: ' + ', '.join(missing[:12]) +
                         (' and %d more' % (len(missing) - 12) if len(missing) > 12 else ''))


def check_chim_native(id1, chim_world, town_dirs, installed=False):
    """The CHIM-native towns' collision check (chim_town.collisions, BUILD-IMAGE-CHIM-NATIVE-TOWN-36): for
    each --chim-town output, no legacy-chain file of its town is staged, no file it installs is staged with
    other bytes or comes from two outputs, and the town is an area of the CHIM world. installed: the image step
    already installed the outputs (OUT/chim-towns.json; its passes then rewrite models in place), so the staged
    bytes are not compared. Returns the town count."""
    from build_aga import chim_world_receipt
    from chim_town import collisions
    areas = chim_world_receipt(chim_world)[1] if chim_world else []
    found = collisions(id1, town_dirs, areas, installed=installed)
    if found:
        raise ValueError('CHIM-native towns collide with the legacy chain or each other (%d): %s'
                         % (len(found), '; '.join(found[:12]) + (' and %d more' % (len(found) - 12) if len(found) > 12 else '')))
    return len(town_dirs)


def planned_catalogues(id1, harvest, data_files, chim_world=None):
    """The harvest catalogues the image step will write (harvest_build.install: one per shipped exterior map
    with harvestable plants, before the heap admission drops some; with a CHIM world also one per CHIM region
    frame map with plants, HARVEST-CHIM-REGION-LOSS-41), read only. A superset: every map that can get a
    catalogue must be one the final image can bind it to."""
    from harvest_build import chim_regions, held_placements, map_selections
    _, _, refs = held_placements(harvest, data_files)
    regions = chim_regions(id1, chim_world)
    return sorted(map_selections(id1, refs, **({'regions': regions} if regions else {}))[1])


def check_harvest(id1, added, removed, harvest=None, data_files=None, chim_world=None):
    """harvest_fingerprint_entries on the planned final map set: maps after the frame maps are written
    and the removed files are gone, as empty placeholders; catalogues, region tables and harvest models
    copied (all small). Before the image step installs the catalogues (it does so late, after the BSP
    optimizer), the catalogues it will write are planned from the harvest source and checked as empty
    placeholders (BUILD-IMAGE-NO-RESUME-33: the check then runs in the image step's first minute, not
    after its passes). The temporary folder is always removed."""
    from build_aga import harvest_fingerprint_entries
    planned = []
    if not any(id1.glob('harvest-*.txt')) and harvest and data_files:
        planned = planned_catalogues(id1, harvest, data_files, chim_world)
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
        from map_files import frame_ext, map_files
        for path in map_files(id1/'maps'):
            if 'maps/' + path.name not in removed:
                (root/'maps'/path.name).touch()
        for name in added:
            (root/'maps'/(name+frame_ext())).touch()
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


def check_engine_map_limits(id1, removed, jobs=1):
    """map_engine_limits.check_maps on the staged maps the image keeps, on JOBS workers (BUILD-IMAGE-UNDERUSED-32);
    the number of maps checked."""
    from map_engine_limits import check_maps
    skip = {rel.split('/', 1)[1] for rel in removed if rel.startswith('maps/')}
    return check_maps(id1/'maps', skip=skip, jobs=jobs)['maps']


# A CHIM region frame map's size before the image step writes it (chim.frame_map._region_map_game_data): the empty
# world shell, the worldspawn and the player start, plus one entity row per recipe sprite. Recorded upper bound,
# measured on v0.0.43-dev2 (2026_10_18_v0.0.43-dev2_full-batch3_f29d984, 1,295 region frame maps): 808 to 9,996
# bytes; 812 bytes for 2 rows, at most 236 bytes per further row. The bound keeps about 2x headroom over both.
FRAME_MAP_BASE_BOUND = 1024
FRAME_MAP_ROW_BOUND = 512


def frame_map_bound(sprite_rows):
    """Recorded upper bound in bytes of one region frame map with SPRITE_ROWS recipe sprite rows."""
    return FRAME_MAP_BASE_BOUND + FRAME_MAP_ROW_BOUND * int(sprite_rows)


def planned_region_frame_maps(id1, chim_world):
    """({map name: PlannedMap}, {boot-relative file: bytes}) of the CHIM region frame maps the image step writes
    (chim.frame_map.build_regions), read only: one frame map per frame under its primary open-world name, sized by
    frame_map_bound from the frame's recipe sprite rows (chim-source.json); and the files that go with them into the
    boot partition, exact sizes from the CHIM world: each frame's far terrain sidecar (far/<cx>_<cy>.far ->
    maps/<name>.far, build_aga.chim_far_sidecar) and the recipe sprite assets (region_task). A frame map already on
    disk keeps its real size (the caller keeps its file)."""
    from chim.far import file_name, sidecar_name
    from chim import cuts
    from chim.frame_map import region_map_names, region_source_sections
    from map_files import frame_ext
    from world_volumes import PlannedMap
    names = region_map_names(id1, chim_world, primary_only=True)
    if not names:
        return {}, {}
    sections = region_source_sections(chim_world)
    planned, sidecars = {}, {}
    for name, cell in sorted(names.items()):
        section = sections.get(tuple(cell), {})
        map_name = name + frame_ext()
        planned[name] = PlannedMap(map_name, frame_map_bound(len(section.get('sprite_entities', []))), bound=True)
        far = Path(chim_world)/'far'/file_name(list(cell))
        if far.is_file():
            sidecars['id1/' + sidecar_name('maps/' + map_name)] = far.stat().st_size
        cut = Path(chim_world)/'cuts'/cuts.file_name(list(cell))
        if cut.is_file() and cuts.decode(cut.read_bytes())[0]['structures']:     # as build_aga.chim_cut_sidecar
            sidecars['id1/' + cuts.sidecar_name('maps/' + map_name)] = cut.stat().st_size
        for asset in section.get('sprite_assets', []):
            sidecars['id1/' + asset['path']] = int(asset['bytes'])
    return planned, sidecars


def actor_library_additions(library):
    """{boot-relative path: bytes} the image step's actor library install (tools/actor_library.py install) copies
    into id1 after the preflight: every file under the stage's id1/, at that path. {} without a library."""
    if not library:
        return {}
    root = Path(library)/'id1'
    if not root.is_dir():
        return {}
    return {'id1/' + p.relative_to(root).as_posix(): p.stat().st_size for p in sorted(root.rglob('*')) if p.is_file()}


def media_additions(media, files, catalogue=False):
    """{boot-relative path: bytes} the image step's media catalogue adds to the payload after the preflight
    (prepare_media_assets.stage_catalogue): every included converted sound and video not staged yet, and, only
    with CATALOGUE (build.py --media-catalogue on, debugging), the catalogue itself (written from the media
    coverage report, counted at that report's size + 1 %; off by default: IMAGE-MEDIA-CATALOGUE-ON-DISK-46)."""
    from prepare_media_assets import key
    media = Path(media)
    report_path = media/'media-coverage.json'
    if not report_path.is_file():
        return {}
    report = json.loads(report_path.read_text(encoding='utf-8'))
    out = {}
    for row in report.get('entries') or []:
        if row.get('status') == 'included' and row.get('path'):
            rel = 'id1/' + key(row['path'])    # the catalogue's own path rule
            if rel not in files:
                out[rel] = int(row.get('bytes') or 0)
    if catalogue:
        size = report_path.stat().st_size
        out['id1/media/catalogue.json'] = size + size // 100
    return out


def room_batch_additions(stage):
    """{boot-relative path: bytes} the image step's room batch install (tools/room_batches.py install) copies into
    id1 after the image step's first preflight: every file the batch stage's record lists. {} without a stage."""
    if not stage:
        return {}
    import room_batches
    path = Path(stage) / room_batches.RECORD
    if not path.is_file():
        return {}
    record = json.loads(path.read_text(encoding='utf-8'))
    return {'id1/' + rel: (Path(stage) / 'id1' / rel).stat().st_size for rel in record.get('files') or {}}


def entity_lump_bytes(path):
    """The entity lump's length of a BSP file (the header's first lump), or None when it is not readable."""
    import struct
    try:
        with open(path, 'rb') as stream:
            head = stream.read(12)
    except OSError:
        return None
    if len(head) < 12:
        return None
    return struct.unpack_from('<i', head, 8)[0]


ROOM_MAP_SHELL_BYTES = 4096   # a CHIM room map beside its entities: the six clip walls of its shell world, the header


def interior_additions(stage, files, boot, room_batches=None):
    """What the image step's CHIM rooms install (chim.interior.install, after finalize's preflight) does to the
    payload FILES {boot-relative path: bytes}: ({path: bytes} it adds, [paths] it removes). The interior store
    id1/chimi/ (without the records of rooms the payload does not hold) is added; every held room's map
    id1/maps/<room>.bsp becomes id1/maps/<room>.chim, counted at the .bsp's entity lump + ROOM_MAP_SHELL_BYTES (the
    room map keeps the entities in a shell world; measured: 43 Balmora rooms 472,720 bytes as .chim from 84,904,648
    bytes as .bsp). IMAGE-BOOT-PAYLOAD-OVER-2GIB-48: the store (321 MB in v0.0.48-dev2) was not in the plan."""
    if not stage:
        return {}, []
    from chim.interior import STORE
    from map_files import frame_map_path
    stage = Path(stage)
    receipt_path = stage / 'chim-rooms-receipt.json'
    if not receipt_path.is_file() or not (stage / STORE).is_dir():
        return {}, []
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    held, add, drop = set(), {}, []
    for row in receipt.get('rooms') or []:
        rel = 'id1/maps/%s.bsp' % row['room']
        if rel not in files:
            continue
        held.add(row['room'])
        source = Path(boot) / rel
        if not source.is_file() and room_batches:
            source = Path(room_batches) / rel
        lump = entity_lump_bytes(source)
        size = files[rel] if lump is None or lump < 0 else min(files[rel], lump + ROOM_MAP_SHELL_BYTES)
        drop.append(rel)
        # an installed room map is always .chim (chim.interior.install), whatever the frame map extension
        add['id1/' + frame_map_path('', row['room'], 'chim').as_posix()] = size
    root = stage / STORE
    for p in sorted(root.rglob('*')):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        if rel.startswith('rooms/') and rel.endswith('.crm') and rel[len('rooms/'):-len('.crm')] not in held:
            continue
        add['id1/%s/%s' % (STORE, rel)] = p.stat().st_size
    return add, drop


def check_disk_layout(boot, removed, music_files, chim_world, layout=None, media=None, media_catalogue=False,
                      actor_library=None, room_batches=None, chim_interiors=None):
    """The planned partitions and drives through the disk-layout gate, before anything is written. LAYOUT: the
    disk layout settings (tools/layout_plan.resolve); the compact layout (default) is planned by
    tools/layout_plan.py and returned as layout_plan (the image step follows it), counting the media the image
    step adds later (MEDIA, the converted media folder) and the actor library it installs later (ACTOR_LIBRARY,
    the actor library stage, only when the image step installs it: --chim-actor-table on); the legacy layout is
    planned as before."""
    import layout_plan
    layout = layout or layout_plan.resolve()
    from world_volumes import (RDB_BYTES, PlannedMap, map_bytes, partition_batches, plan_drives, plan_partitions,
                               partition_starts, planned_partition, require_partition_plans)
    id1 = boot/'id1'
    # every staged file's size, by the layout plan's walk (os.walk; the pathlib walk with AMIWIND_LAYOUT_WALK=pathlib):
    # the same sizes (every reader of FILES sorts it or looks paths up)
    files = dict(layout_plan.walk(boot))
    for rel in removed:
        files.pop('id1/' + rel, None)
    # The soundtrack is copied before world_volumes.pack measures the boot payload: count it first.
    for name, size in music_files:
        files['id1/music/' + name] = size
    # The actor library's models are copied into id1 by the image step after this plan (actor_library.install, at
    # the actor table): count them at their own size, over any staged file of the same name they replace
    # (IMAGE-LAYOUT-PLAN-ACTOR-LIBRARY-48: 148.8 MB left out of a MiniWind plan, +145 MB at the layout check).
    files.update(actor_library_additions(actor_library))
    # The room batches (copied in by the image step after its first preflight) and the CHIM rooms install (the
    # interior store id1/chimi/ and each held room's .bsp made its .chim, after finalize's preflight): counted
    # (IMAGE-BOOT-PAYLOAD-OVER-2GIB-48: 1.66 GB of batch room residents and the 321 MB store were not in the plan).
    files.update(room_batch_additions(room_batches))
    added_rooms, dropped_rooms = interior_additions(chim_interiors, files, boot, room_batches)
    for rel in dropped_rooms:
        files.pop(rel, None)
    files.update(added_rooms)
    worlds, frame_maps = [], []
    directory = id1/'world/regions.awr'
    if directory.exists():
        import struct
        raw = directory.read_bytes()
        if raw[:4] != b'AWR2' or len(raw) < 64:
            raise ValueError('Invalid region directory')
        count = struct.unpack_from('<I', raw, 4)[0]
        if not 1 <= count <= 8192 or len(raw) != 64 + count*52:
            raise ValueError('Invalid region directory count')
        from map_files import map_file
        paths = [map_file(id1/'maps', f'vf{i:04d}') for i in range(count)]
        paths = [p for p in paths if p.relative_to(id1).as_posix() not in removed]
        # a CHIM region cell's map is its frame map, written later in the image step: no legacy map is made for it
        # (docs/BUILD_MANIFEST.md step 2); any other missing map stays an error
        planned = {}
        if chim_world:
            from chim.frame_map import region_map_names
            from map_files import is_chim_frame
            owned = region_map_names(id1, chim_world)
            # ... but it IS a world map of the image: the frame maps join the partition plan by their planned size,
            # so the plan is the one world_volumes.pack makes after they are written (an all-CHIM world has no
            # legacy open-world map left: BUILD-IMAGE-ALL-CHIM-PREFLIGHT-43). A legacy map an earlier stage still
            # made for an owned cell leaves when its frame map is written (chim.frame_map.install_region): not counted.
            written = {p.stem for p in paths if p.stem in owned and p.is_file() and is_chim_frame(p)}
            for p in paths:
                if p.stem in owned and p.stem not in written and p.is_file():
                    files.pop(p.relative_to(boot).as_posix(), None)
            paths = [p for p in paths if p.stem not in owned or p.stem in written]
            planned, sidecars = planned_region_frame_maps(id1, chim_world)
            for rel, size in sidecars.items():
                files.setdefault(rel, size)
            paths += [m for name, m in sorted(planned.items()) if name not in written
                      and 'maps/' + m.name not in removed]
        if layout['mode'] == 'compact':
            return compact_disk_layout(boot, files, paths, chim_world, layout, media, media_catalogue)
        # the boot payload: every staged file but the world maps on disk (a planned map is not in FILES yet)
        terrain = sum(map_bytes(p) for p in paths if not isinstance(p, PlannedMap))
        kept, batches = partition_batches(paths, sum(files.values()) - terrain)
        for path in kept:          # a planned map the boot partition keeps is a boot file once written
            if isinstance(path, PlannedMap):
                files['id1/maps/' + path.name] = path.bytes
        worlds = plan_partitions(batches)
        require_partition_plans(worlds)
        for batch in batches:
            for path in batch:
                if not isinstance(path, PlannedMap):
                    files.pop(path.relative_to(boot).as_posix(), None)
        frame_maps = [m for m in kept + [m for batch in batches for m in batch] if isinstance(m, PlannedMap)]
    elif layout['mode'] == 'compact':
        return compact_disk_layout(boot, files, [], chim_world, layout, media, media_catalogue)
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
                bytes=sum(p['bytes'] for p in plans), rdb_bytes=RDB_BYTES,
                planned_frame_maps=dict(count=len(frame_maps), bytes=sum(m.bytes for m in frame_maps),
                                        bound=sum(1 for m in frame_maps if m.bound)),
                plan=[dict(drive=d['file'], bytes=d['bytes'],
                           partitions=[dict(partition=m['partition'], volume=m.get('volume'), bytes=m['bytes'],
                                            start=start, files=len(m.get('files', ())),
                                            payload=sum(f['bytes'] for f in m.get('files', ())),
                                            largest_file=max((f['bytes'] for f in m.get('files', ())), default=0))
                                       for m, start in zip(d['members'], partition_starts(RDB_BYTES, d['members']))])
                      for d in plans])


def compact_disk_layout(boot, files, paths, chim_world, layout, media=None, media_catalogue=False):
    """The compact layout plan (tools/layout_plan.py) of the payload: FILES {boot-relative path: bytes} with the
    world maps PATHS (files on disk or PlannedMap) among them or planned; the media the image step adds later
    counted. The plan passes the minimal-partitions check and the drive gate (plan_drives); returned with the
    drive summary as the layout_plan the image step follows."""
    import layout_plan
    from world_volumes import PlannedMap, map_bytes, partition_starts, plan_drives, RDB_BYTES
    files = dict(files)
    if media:
        for rel, size in media_additions(media, files, media_catalogue).items():
            files.setdefault(rel, size)
    maps = []
    for p in paths:
        rel = 'id1/maps/' + p.name
        files.pop(rel, None)
        maps.append((rel, map_bytes(p)))
    base = Path(chim_world)/'chim' if chim_world else None
    chim = layout_plan.walk(base) if base is not None and base.is_dir() else None
    plan = layout_plan.plan_compact(files, maps, chim, layout['headroom_mib'], layout['boot_headroom_mib'])
    layout_plan.require_minimal(plan)
    rows = plan['partitions']
    drives = plan_drives(dict(partition='DH0', volume='AMIWIND', bytes=rows[0]['bytes'], files=[]),
                         [dict(partition=r['partition'], volume=r['volume'], bytes=r['bytes'], files=[]) for r in rows[1:]])
    plan['drives'] = [dict(file=d['file'], bytes=d['bytes'], partitions=[m['partition'] for m in d['members']])
                      for d in drives]
    planned = [m for m in paths if isinstance(m, PlannedMap)]
    return dict(drives=len(drives), partitions=len(rows), bytes=sum(d['bytes'] for d in drives), rdb_bytes=RDB_BYTES,
                layout='compact', headroom_mib=plan['headroom_mib'], boot_headroom_mib=plan['boot_headroom_mib'],
                planned_frame_maps=dict(count=len(planned), bytes=sum(m.bytes for m in planned),
                                        bound=sum(1 for m in planned if m.bound)),
                lines=layout_plan.lines(plan),
                plan=[dict(drive=d['file'], bytes=d['bytes'],
                           partitions=[dict(partition=r['partition'], volume=r['volume'], role=r['role'],
                                            bytes=r['bytes'], start=start, files=r['files'], payload=r['payload'],
                                            free_bytes=r['free_bytes'], largest_file=r['largest_file'],
                                            maps=len(r['maps']))
                                       for r, start in zip([next(x for x in rows if x['partition'] == m['partition'])
                                                            for m in d['members']],
                                                           partition_starts(RDB_BYTES, d['members']))])
                      for d in drives],
                layout_plan=plan)


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


def check_guard_records(id1, removed, data_files, room_batches=None):
    """The guard torch records (guard source, model) of the staged maps the image keeps and of the batch rooms it
    installs, against the engine's table (tools/prepare_guard_torches.py MAX_RECORDS = AW_GUARD_TORCH_TYPES). The
    CHIM frame maps are not written yet, so this is a lower bound: an overflow by the rooms and interiors stops the
    build here in seconds instead of in the image step's guard torches (GUARD-TORCH-TYPES-LIMIT-48); the image
    step counts the final map set again. Returns the count."""
    from map_files import map_files
    from prepare_guard_torches import MAX_RECORDS, check_record_count, staged_guard_records
    if not data_files:
        return None
    skip = {rel.split('/', 1)[1] for rel in removed if rel.startswith('maps/')}
    every = map_files(Path(id1) / 'maps')
    if room_batches:
        staged = {p.name for p in every}
        every += [p for p in map_files(Path(room_batches) / 'id1' / 'maps') if p.name not in staged]
    # scene maps' NPCs get their source identity later in the image step: counted, not refused here (the image
    # step's guard torches refuse an NPC without one on the final maps; PREFLIGHT-GUARD-UNSTAMPED-NPCS-48)
    unstamped = []
    keys = staged_guard_records(every, data_files, unstamped)
    kept = staged_guard_records([p for p in every if p.name not in skip], data_files, []) if skip else keys
    if unstamped:
        print('guard torch records: %d staged NPC(s) not stamped with a source identity yet (%s); the image step '
              'checks them on the final maps' % (len(unstamped), ', '.join(sorted({m for m, _ in unstamped}))),
              flush=True)
    # The maps the image removes include the legacy town maps its CHIM town frame maps are written from: their
    # guards come back in the frame maps, so they are counted as a warning (they also hold maps that do not ship)
    if len(keys) > MAX_RECORDS >= len(kept):
        print('WARNING: guard torch records: %d with the maps the image removes (the CHIM towns are written from '
              'them), %d without; the engine holds %d' % (len(keys), len(kept), MAX_RECORDS), flush=True)
    check_record_count(len(kept), ' before the CHIM frame maps')
    return {'records_kept_maps': len(kept), 'records_with_removed_maps': len(keys)}


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


def layout_beside():
    """1 when the disk layout check runs beside the other checks and the Python-bound checks run in processes of
    their own (the default since v0.0.48, BUILD-IMAGE-UNDERUSED-32: on the threads of one process they shared one
    interpreter lock, 45 s at 1.6 cores in the dev2 try 9 build), 0 with AMIWIND_PREFLIGHT_METHOD=threads (every
    check on a thread, the layout after them: the method before). The same report either way."""
    import os
    return 0 if os.environ.get('AMIWIND_PREFLIGHT_METHOD', 'pool') == 'threads' else 1


# Checks that run Python over every staged file (names, formats, host paths, actor frame layouts): each in a process
# of its own beside the others (layout_beside), as build_parallel.Background
PROCESS_CHECKS = ('payload-names', 'file-formats', 'host-paths', 'actor-frames')


def run(out, *, chim_world=None, music=None, jobs=1, harvest=None, data_files=None, report_path=None,
        pending=None, chim_towns=(), chim_town_dirs=(), exterior_terrain=None, layout=None, media=None,
        layout_plan_path=None, media_catalogue=False, actor_library=None, room_batches=None, chim_interiors=None):
    """Run every check over the staged payload OUT (OUT/boot). Prints one summary line; raises
    ValueError listing every error together. Returns the report. pending: files the image step still
    writes before its frame maps (check_chim_inputs). layout: the disk layout settings (tools/layout_plan.py);
    the compact layout's plan is printed and written to LAYOUT_PLAN_PATH (the image step follows it)."""
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
        if exterior_terrain:
            from build_aga import chim_world_receipt
            from exterior_plan import omitted_paths
            owners = set(chim_world_receipt(chim_world)[1]) if chim_world else set()
            removed.update(omitted_paths(exterior_terrain, id1, planned_towns=owners))
    except (OSError, ValueError, KeyError) as exc:
        added, removed, not_on_chim = [], set(), []
        errors.append(('chim-receipt', exc))
    beside = layout_beside()
    calls = {'payload-names': (check_payload_names, boot), 'file-formats': (check_file_formats, id1),
             'host-paths': (check_payload_host_paths, boot, [out.resolve()]),
             'actor-frames': (check_actor_frames, id1, removed)}
    started_apart = {}
    if beside and int(jobs or 1) > 1:
        from build_parallel import Background
        started_apart = {name: Background(*calls[name], jobs=jobs) for name in PROCESS_CHECKS}

    def check(name):
        if name in started_apart:
            return started_apart[name].result
        return lambda: calls[name][0](*calls[name][1:])
    checks = [('payload-names', check('payload-names')),
              ('file-formats', check('file-formats')),
              ('host-paths', check('host-paths')),
              ('harvest-catalogues', lambda: check_harvest(id1, added, removed, harvest, data_files, chim_world)),
              ('interior-sections', lambda: check_interior_sections(id1, removed)),
              ('engine-map-limits', lambda: check_engine_map_limits(id1, removed, jobs)),
              ('actor-frames', check('actor-frames'))]
    if chim_world:
        checks.append(('chim-inputs', lambda: check_chim_inputs(id1, chim_world, pending, set(chim_towns))))
    if chim_town_dirs:
        checks.append(('chim-native', lambda: check_chim_native(id1, chim_world, list(chim_town_dirs),
                                                                 installed=(out/'chim-towns.json').is_file())))
    # the guard torch records against the engine's table (GUARD-TORCH-TYPES-LIMIT-48)
    checks.append(('guard-records', lambda: check_guard_records(id1, removed, data_files, room_batches)))
    music_result = {}
    if music:
        def music_check():
            music_result['files'] = check_music(Path(music))
            return len(music_result['files']) - 1
        checks.append(('music', music_check))
    def disk_layout():
        return check_disk_layout(boot, removed, music_result.get('files', []), chim_world, layout, media,
                                 media_catalogue, actor_library, room_batches, chim_interiors)
    layout_future = None
    with ThreadPoolExecutor(max_workers=max(1, min(int(jobs or 1), len(checks) + beside))) as pool:
        futures = [(name, pool.submit(fn)) for name, fn in checks]
        if beside:
            # The layout needs the music sizes only: it starts as soon as they are known, beside the other checks
            # (BUILD-IMAGE-UNDERUSED-32: it ran after all of them, 10.7 s on one core); its result and error keep
            # their place in the report
            music_future = dict(futures).get('music')
            if music_future is not None:
                try:
                    music_future.result()
                except (OSError, ValueError, KeyError):
                    pass
            if not music or 'files' in music_result:
                layout_future = pool.submit(disk_layout)
        for name, future in futures:
            try:
                results[name] = future.result()
            except (OSError, ValueError, KeyError) as exc:
                errors.append((name, exc))
    # The layout needs the music sizes; without layout_beside() it runs last (the method before v0.0.48).
    if layout_future is not None:
        try:
            results['disk-layout'] = layout_future.result()
        except (OSError, ValueError) as exc:
            errors.append(('disk-layout', exc))
    elif not beside and (not music or 'files' in music_result):
        try:
            results['disk-layout'] = disk_layout()
        except (OSError, ValueError) as exc:
            errors.append(('disk-layout', exc))
    planned = (results.get('disk-layout') or {}).pop('layout_plan', None)
    if planned is not None:
        lines = results['disk-layout'].pop('lines', [])
        if layout_plan_path is not None:           # an image run: the plan it will follow, printed and written
            for line in lines:
                print(line, flush=True)
        if layout_plan_path is not None and not errors:
            Path(layout_plan_path).write_text(json.dumps(planned, indent=1) + chr(10), encoding='utf-8',
                                              newline=chr(10))
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
