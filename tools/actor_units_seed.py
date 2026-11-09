# SPDX-License-Identifier: GPL-3.0-only
"""One-time import of a finished actor library stage's NPC appearances into the unit cache (NPC-LIBRARY-NO-UNIT-CACHE-63).

The actor library stage keeps every NPC appearance it bakes in the unit cache npc-appearance since v0.0.63
(tools/npc_library.py unit_cache). A build made before that kept none, so the first build with the unit cache would
bake all of them again. This tool stores the appearances of such a build's stage folder under exactly the key the stage
looks them up with, and only where that is safe:

- the bake code is the code that build ran: the bake-reach digest of npc_library.bake_standing in this checkout equals
  the one recorded for that build (SEED_REACH), else nothing is imported;
- the settings the bake reads are that build's: they are taken from the stage's recorded fingerprint
  (RUN/profile/fingerprints.json, the actor-library stage's environment), so a seeded unit is found only by a build
  with the same settings;
- each appearance is computed again from the game data and must give the same library key and the same first record
  id as that build's manifest, its model file must have the SHA-256 the manifest recorded, and the palette is that
  build's own (its SHA-256 is part of the key);
- a skeletal model (--npc-anim-type 2) carries its shared animation table, which the manifest names without a hash:
  the table is made again from the game data as the bake makes it and must equal the stage folder's file.
Run it as the user the builds run as (1000:1000): a unit cache folder made by root cannot be written by the builds.

Usage (inside the build container, with the workspace's input lock and unit cache):
  actor_units_seed.py --run RUN --data-files DATA --inputs-lock LOCK --cache CACHE [--lookup-only]
--lookup-only stores nothing and counts how many of the build's appearances the unit cache already finds.
"""
import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / 'tools', ROOT / 'src'):
    while str(_p) in sys.path:
        sys.path.remove(str(_p))
    sys.path.insert(0, str(_p))

# Bake-reach digest of npc_library.bake_standing (pass_cache.source_digest((npc_library.py, 'bake_standing'))) at the
# commit of a build whose stage folder may seed the unit cache: dc356e39, the v0.0.63-dev1 build. Measured in the
# container on a clean export of dc356e39 and on this branch (equal).
SEED_REACH = {'dc356e39': '15ee640c68d871fdabf1e3c55ce3c99c0495a08bf7552e03afcf6434219de557'}
STAGE = 'actor-library'


def sounds_of(layout):
    """The sound file names a standing layout names (its '~EVENT:DRY:WADE:SWIM' words, npc_anim.layout)."""
    names = set()
    for word in layout.split():
        if word.startswith('~'):
            names.update(part for part in word.split(':')[1:] if part)
    return sorted(names)


_TABLE_STATE = {}


def skeletal_table(data_files, appearance):
    """(table bytes, game path) of an appearance's shared animation table, as npc_library._skeletal_standing gets it."""
    import skeletal_actor
    from mwad.audit import BSA
    from mwad.paths import child_ci
    from npc_geometry import Assets, Skeleton
    data = Path(data_files)
    key = str(data.resolve())
    if key not in _TABLE_STATE:
        _TABLE_STATE[key] = (Assets(data, BSA(child_ci(data, 'Morrowind.bsa'))), {})
    assets, rigs = _TABLE_STATE[key]

    def rig_of(path):
        if path not in rigs:
            rigs[path] = Skeleton(assets, path)
        return rigs[path]
    table_bytes, _, _, table_path, _, _ = skeletal_actor.game_table(key, appearance, rig_of)
    return table_bytes, table_path


def stage_environment(run):
    """{AMIWIND_* setting: value or None} the actor library stage of RUN was keyed with."""
    record = json.loads((Path(run) / 'profile' / 'fingerprints.json').read_text(encoding='utf-8'))
    return dict(record[STAGE]['environment'])


def seed(run, data_files, lookup_only=False, log=print):
    """Import (or with LOOKUP_ONLY count) the appearances of RUN's actor library stage; returns the counts."""
    import pass_cache
    import npc_library as NL
    from mwad.npc import load_master
    from mwad.paths import child_ci
    run = Path(run)
    library = run / STAGE
    reach = pass_cache.source_digest((NL.__file__, 'bake_standing'))
    if reach not in SEED_REACH.values():
        raise ValueError('the bake code of this checkout (%s) is not the code any seed build ran (%s): nothing '
                         'imported' % (reach[:12], ', '.join('%s %s' % (c, (d or '')[:12])
                                                             for c, d in sorted(SEED_REACH.items()))))
    import actor_units
    cache = actor_units.open_cache(actor_units.NPC_CACHE, ((NL.__file__, 'bake_standing'),), reach,
                                   pass_cache.previous_digests((NL.__file__, 'bake_standing')),
                                   pass_cache.covered_lines((NL.__file__, 'bake_standing')))
    if cache is None:
        raise ValueError('no unit cache: set the cache folder and the input lock')
    manifest = json.loads((library / 'npc-library.json').read_text(encoding='utf-8'))
    if manifest.get('format') != NL.FORMAT:
        raise ValueError('not an NPC standing library manifest')
    profile = NL.standing_profile()
    if profile != manifest.get('profile'):
        raise ValueError('profile %s, the build baked %s' % (profile, manifest.get('profile')))
    palette = (run / 'intro-scene' / 'id1' / 'gfx' / 'palette.lmp').read_bytes()
    palette_sha256 = hashlib.sha256(palette).hexdigest()
    groups = {}
    for ident, row in manifest['npcs'].items():
        groups.setdefault(row['key'], []).append(ident)
    firsts = {key: sorted(idents)[0] for key, idents in groups.items()}
    kinds, _, _ = load_master(child_ci(Path(data_files), 'Morrowind.esm'))
    apps, _ = NL.appearances(kinds, sorted(firsts.values()))
    counts = {'appearances': len(manifest['models']), 'imported': 0, 'found': 0, 'skipped': {}}

    def skip(key, why):
        counts['skipped'][key] = why
    for done, key in enumerate(sorted(manifest['models']), 1):
        facts = dict(manifest['models'][key])
        model, seconds = facts.pop('model', None), facts.pop('seconds', 0.)
        if key not in firsts:
            skip(key, 'no record names it')
            continue
        app = apps.get(firsts[key])
        if app is None:
            skip(key, 'its first record has no appearance now')
            continue
        if NL.appearance_key(app, profile) != key:
            skip(key, 'the appearance gives another key now')
            continue
        inputs = actor_units.npc_inputs(app, key, profile, palette_sha256)
        if lookup_only:
            counts['found'] += cache.load_unit(inputs) is not None
            continue
        raw = (library / 'id1' / model).read_bytes()
        if hashlib.sha256(raw).hexdigest() != facts.get('sha256'):
            skip(key, 'its model file is not the one the manifest recorded')
            continue
        anm = (library / 'id1' / model).with_suffix('.anm')
        layout = anm.read_text(encoding='ascii')[:-1] if anm.is_file() else ''
        sounds = {}
        for name in sounds_of(layout):
            path = library / 'id1' / 'sound' / name
            if path.is_file():
                sounds[name] = path.read_bytes()
        if facts.get('type') == 2:
            # a skeletal model (--npc-anim-type 2): its shared animation table is part of the unit. The manifest names
            # the table's path but records no hash of it, so the table is made again here as the bake makes it
            # (skeletal_actor.game_table, from the game data; the skeletal-table unit cache keeps it cheap) and must
            # have that path and equal the run's file byte for byte
            try:
                table_bytes, table_path = skeletal_table(data_files, app)
            except (OSError, ValueError, KeyError) as error:
                skip(key, 'its animation table cannot be made: %s' % error)
                continue
            target = library / 'id1' / table_path
            if table_path != facts.get('table') or not target.is_file() or target.read_bytes() != table_bytes:
                skip(key, 'its animation table is not the one the bake makes')
                continue
            facts['_table'] = (table_path, table_bytes)
        packed = actor_units.pack_npc((raw, layout, sounds, facts), seconds)
        if packed is None:
            skip(key, 'not exact JSON')
            continue
        cache.store_files(inputs, *packed)
        # the store never raises (a cache problem never fails a build): read it back, so a folder this process cannot
        # write (made by another user) is a skip with its reason, never a silent 'imported'
        if cache.load_unit(inputs) is None:
            skip(key, 'stored but not found again (is the unit cache folder writable by this user?)')
            continue
        counts['imported'] += 1
        if done % 50 == 0:
            log('Seed: [%d/%d] appearances' % (done, counts['appearances']), flush=True)
    return counts


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--run', type=Path, required=True, help='the finished build run whose actor library seeds the cache')
    p.add_argument('--data-files', type=Path, required=True)
    p.add_argument('--inputs-lock', type=Path, required=True, help="the workspace's input lock (game data by SHA-256)")
    p.add_argument('--cache', type=Path, required=True, help='the unit cache folder (WORKSPACE/cache/image-passes)')
    p.add_argument('--lookup-only', action='store_true', help='store nothing; count what the unit cache finds')
    a = p.parse_args(argv)
    import pass_cache
    from known_inputs import LOCK_ENV
    for name, value in stage_environment(a.run).items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value
    os.environ[LOCK_ENV] = str(a.inputs_lock)
    os.environ[pass_cache.ENV] = str(a.cache)
    began = time.time()
    counts = seed(a.run, a.data_files, a.lookup_only)
    print('Seed: %d appearances in %s: %s, %d skipped (%.1f s)' % (
        counts['appearances'], a.run.name,
        ('%d found in the unit cache' % counts['found']) if a.lookup_only else ('%d imported' % counts['imported']),
        len(counts['skipped']), time.time() - began), flush=True)
    for key, why in sorted(counts['skipped'].items()):
        print('Seed: skipped %s: %s' % (key, why), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
