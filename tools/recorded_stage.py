#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Recorded-stage exception: ship owner-provided recorded maps byte for byte.

BUILD-SEYDA-REGEN-30: the repository builder cannot regenerate the shipped Seyda
Neen sub-cells, so v0.0.31 and v0.0.32 ship the recorded v0.0.31 maps (owner
decision). `--seyda-recorded DIR` (tools/build.py, build_aga.py image,
check_scene_actors.py) names a folder holding them as the owner's own input:

    DIR/id1/maps/sn000.bsp .. sn063.bsp, intro_docks.bsp, sncourt.bsp
    DIR/id1/seyda-regions.txt, DIR/id1/seyda-regions.json
    DIR/id1/maps/seyda.bsp (optional: recorded, but not shipped, see below)

copied from the owner's v0.0.31 image (boot partition, id1/). Every file must
match config/seyda-recorded-v0.0.31.json (names, sizes and SHA-256); the files
themselves are never part of the repository or a release source.

The exception is honoured byte for byte (BUILD-SEYDA-RECORDED-REWRITTEN-32):
the recorded set replaces the Seyda region conversion, every later pass that
would rewrite those maps skips them, and check() after each map pass stops the
build if any installed file differs from its recorded bytes.

The pin's `aliases` name the one intended difference (owner decision,
8 October 2026, documented on BUILD-SEYDA-REGEN-30): maps/seyda.bsp ships as a
copy of the fallback region (sn029), as the builder's own region conversion
writes it, instead of v0.0.31's complete town, whose actor copies the release
actor gate refuses. Any other change needs the same: named on
BUILD-SEYDA-REGEN-30 with the owner's reason.

    python3 tools/recorded_stage.py check DIR    # verify a folder against the pin
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIN = ROOT / 'config/seyda-recorded-v0.0.31.json'
RECEIPT_NAME = 'recorded-stage.json'
FORMAT = 'AmiWind recorded stage 1'
MAP_NAME = re.compile(r'(sn[0-9]{3}|intro_docks|sncourt|seyda)\.bsp')


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def _seyda_name(name):
    return name in ('seyda-regions.txt', 'seyda-regions.json') or (
        name.startswith('maps/') and MAP_NAME.fullmatch(name[5:]) is not None)


def load_pin(pin=PIN):
    """The pinned recorded set.

    Returns (record, files, aliases): files maps each recorded file (path under
    id1/) to (bytes, sha256); aliases maps a shipped file to the recorded file
    whose bytes it ships instead of its own.
    """
    record = json.loads(Path(pin).read_text(encoding='utf-8'))
    if record.get('format') != 'AmiWind recorded stage pin 1' or record.get('exception') != 'BUILD-SEYDA-REGEN-30':
        raise ValueError('Unknown recorded-stage pin: ' + str(pin))
    files = {}
    for row in record['files']:
        name = row['file']
        if not _seyda_name(name):
            raise ValueError('Recorded-stage pin names a file outside the Seyda Neen set: ' + name)
        if name in files or not re.fullmatch(r'[0-9a-f]{64}', row['sha256']) or row['bytes'] <= 0:
            raise ValueError('Invalid recorded-stage pin row: ' + name)
        files[name] = (row['bytes'], row['sha256'])
    aliases = {}
    for name, row in (record.get('aliases') or {}).items():
        source = row.get('source') if isinstance(row, dict) else None
        if not _seyda_name(name) or source not in files or source in aliases or not row.get('reason'):
            raise ValueError('Invalid recorded-stage alias: ' + name)
        aliases[name] = source
    if 'maps/seyda.bsp' not in files and 'maps/seyda.bsp' not in aliases:
        raise ValueError('Recorded-stage pin lacks maps/seyda.bsp')
    return record, files, aliases


def shipped(files, aliases):
    """{shipped file: recorded source file} in sorted order."""
    names = (set(files) - set(aliases)) | set(aliases)
    return {name: aliases.get(name, name) for name in sorted(names)}


def check_source(recorded, pin=PIN, jobs=None):
    """Verify DIR/id1 against the pin; return (record, files, aliases).

    Every recorded file a shipped file uses must be present; a recorded file
    replaced by an alias (v0.0.31's complete seyda.bsp) may be absent. Nothing
    else may be there, and every present file must have its pinned bytes.
    """
    record, files, aliases = load_pin(pin)
    id1 = Path(recorded) / 'id1'
    if not id1.is_dir():
        raise ValueError('Recorded Seyda Neen folder lacks id1/: ' + str(recorded))
    present = {p.relative_to(id1).as_posix() for p in id1.rglob('*') if p.is_file()}
    needed = set(shipped(files, aliases).values())
    missing, extra = sorted(needed - present), sorted(present - set(files))
    if missing or extra:
        raise ValueError('Recorded Seyda Neen folder does not match ' + Path(pin).name +
                         (': missing ' + ', '.join(missing[:8]) if missing else '') +
                         (': unexpected ' + ', '.join(extra[:8]) if extra else ''))
    from build_parallel import hash_files
    names = sorted(present)
    wrong = [name for name, value in zip(names, hash_files([id1 / n for n in names], jobs))
             if value != files[name][1] or (id1 / name).stat().st_size != files[name][0]]
    if wrong:
        raise ValueError('Recorded Seyda Neen files differ from ' + Path(pin).name + ': ' + ', '.join(wrong[:8]))
    return record, files, aliases


def receipt_path(work_dir):
    return Path(work_dir) / RECEIPT_NAME


def install(recorded, maps, *, work_dir, pin=PIN, jobs=None):
    """Install the recorded set in place of the Seyda region conversion.

    Same outputs as prepare_seyda_regions.convert: maps/<name>.bsp for every
    recorded map, maps/seyda.bsp (by its alias, the fallback region) and
    ../seyda-regions.txt/.json. Returns the recorded seyda-regions.json report,
    as convert() returns its own.
    """
    record, files, aliases = check_source(recorded, pin, jobs)
    recorded, maps, work = Path(recorded), Path(maps), Path(work_dir)
    id1 = maps.parent
    report = json.loads((recorded / 'id1/seyda-regions.json').read_text(encoding='utf-8'))
    if 'maps/seyda.bsp' in aliases and aliases['maps/seyda.bsp'] != 'maps/%s.bsp' % report.get('fallback_alias'):
        raise ValueError('seyda.bsp alias must be the recorded fallback region ' + str(report.get('fallback_alias')))
    work.mkdir(parents=True, exist_ok=False)
    rows = []
    for name, source in shipped(files, aliases).items():
        target = id1 / name
        replaced = sha256(target) if target.is_file() else None
        temporary = target.with_name(target.name + '.recorded-tmp')
        shutil.copyfile(recorded / 'id1' / source, temporary)
        os.replace(temporary, target)
        row = dict(file=name, bytes=files[source][0], sha256=files[source][1], replaced_sha256=replaced)
        if source != name:
            row.update(source=source, reason=record['aliases'][name]['reason'])
        rows.append(row)
    receipt = dict(format=FORMAT, exception='BUILD-SEYDA-REGEN-30', pin=PIN.name if Path(pin) == PIN else str(pin),
                   pin_sha256=sha256(pin), decision=record.get('decision'), source=str(recorded),
                   replaced_call='prepare_seyda_regions.convert', files=rows, checks=[])
    receipt_path(work).write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(f'[recorded-stage] BUILD-SEYDA-REGEN-30: installed {len(rows)} recorded Seyda Neen files '
          f'({Path(pin).name}, {len(aliases)} named alias); later passes keep them byte for byte.', flush=True)
    return report


def load_receipt(work_dir):
    """The install receipt, or None when the build has no recorded stage."""
    path = receipt_path(work_dir)
    return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else None


def frozen_maps(work_dir):
    """Map file names (e.g. sn029.bsp) under the recorded exception; empty without one."""
    receipt = load_receipt(work_dir)
    if receipt is None:
        return frozenset()
    return frozenset(row['file'][5:] for row in receipt['files'] if row['file'].startswith('maps/'))


def check(id1, work_dir, stage, jobs=None):
    """Stop the build when `stage` left any recorded file different from its recorded bytes.

    No-op without a recorded stage. Each passed check is appended to the receipt.
    """
    path = receipt_path(work_dir)
    receipt = load_receipt(work_dir)
    if receipt is None:
        return None
    from build_parallel import hash_existing
    id1 = Path(id1)
    rows = receipt['files']
    found = hash_existing([id1 / row['file'] for row in rows], jobs)
    changed = [row['file'] for row, value in zip(rows, found) if value != row['sha256']]
    if changed:
        raise ValueError(f'Recorded-stage exception BUILD-SEYDA-REGEN-30 broken by {stage}: {len(changed)} recorded '
                         'Seyda Neen file(s) differ from the recorded bytes (' + ', '.join(changed[:6]) +
                         '). A pass may change recorded maps only when the change is named on '
                         'BUILD-SEYDA-REGEN-30 (BUILD-SEYDA-RECORDED-REWRITTEN-32).')
    receipt['checks'].append(dict(stage=stage, files=len(rows), status='byte-identical'))
    path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8', newline='\n')
    return receipt


def keep_town_flora(scene, flora, maps):
    """Town flora for the recorded Seyda Neen maps: keep the maps as recorded.

    The recorded maps already carry their installed flora (aw_flora entities);
    reinstalling would rewrite them. Only the sprites they reference are copied
    from this build's flora bake, and must not conflict with installed sprites.
    """
    scene, flora = Path(scene), Path(flora)
    used, with_flora = set(), 0
    for name in maps:
        refs = set(re.findall(rb'progs/aw_flora/f_[0-9a-f]{16}\.spr', (scene / 'id1/maps' / name).read_bytes()))
        with_flora += bool(refs)
        used |= {ref.decode('ascii') for ref in refs}
    rows = []
    for name in sorted(used):
        source, target = flora / name, scene / 'id1' / name
        if not source.is_file():
            raise ValueError('Flora bake lacks a sprite the recorded Seyda Neen maps use: ' + name)
        if target.exists() and sha256(target) != sha256(source):
            raise ValueError('Flora sprite already installed with other content: ' + name)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        rows.append(dict(file=name, sha256=sha256(target)))
    print(f'[recorded-stage] Seyda Neen town flora kept from the recorded maps ({with_flora} of {len(maps)} '
          f'maps carry flora); {len(rows)} sprites from this bake.', flush=True)
    return dict(format='AmiWind bounded town flora staging 1', admission_profile='town',
                status='recorded maps kept (BUILD-SEYDA-REGEN-30)', maps=[], recorded_maps=len(maps),
                recorded_maps_with_flora=with_flora, sprites=rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    sub = parser.add_subparsers(dest='action', required=True)
    c = sub.add_parser('check', help='verify a recorded Seyda Neen folder against the pin')
    c.add_argument('recorded', type=Path)
    c.add_argument('--pin', type=Path, default=PIN)
    args = parser.parse_args(argv)
    try:
        _, files, aliases = check_source(args.recorded, args.pin)
    except (ValueError, OSError) as exc:
        parser.exit(1, f'Error: {exc}\n')
    print(f'{args.recorded}: recorded files match {args.pin.name} '
          f'({len(shipped(files, aliases))} shipped, {len(aliases)} by a named alias).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
