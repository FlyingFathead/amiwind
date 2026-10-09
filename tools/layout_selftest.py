#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Disk layout self-test: the image step's packing path refuses every Amiga disk limit.

Dummy payloads (sparse files: the size is set, nothing is written into them) go through the same
functions the image step uses: the world partition plan and its gate (world_volumes.write_partitions
runs require_partition_plans before its first write), the drive plan with hardfile_groups and the
disk-layout gate (plan_drives), and for the small wiring case the real writers (write_partitions,
write_boot_partition), rdbtool drive assembly, readback and the gate on the drives as written
(assemble_drives). Each case must end as expected:

  file-over-1gib       one 2.5 GB world map                      refused
  partition-over-2gib  a world partition of 2048 MiB             refused
  start-past-2gib      a partition starting at 2304 MiB          refused (grouping forced)
  drive-over-4gib      a drive of 4096 MiB + 32 KiB              refused (grouping forced)
  largest-legal        file 1 GiB - 1 byte, 1920 MiB partitions,
                       a partition starting at 1920 MiB + 32 KiB,
                       a 3840 MiB + 32 KiB drive                 passes (plan only)
  wiring               a tiny payload written end to end         passes, layout recorded

The grouping (hardfile_groups) never puts a partition past 2 GiB or a drive over 4 GiB; the two
"forced" cases replace its grouping to prove the gate itself refuses them, and check that the real
grouping keeps the same partitions legal. A refused plan stops before any image is written, so the
sparse dummies are never read or copied. Every dummy lives in one scratch folder that is removed
on success, on failure and on Ctrl-C.

Run: python3 tools/build.py --layout-selftest   (or python3 tools/layout_selftest.py --help)
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import world_volumes as wv  # noqa: E402

MIB = wv.MIB
GIB = 1024 * MIB


def case(name, expect, boot, worlds, groups=None, write=False, note=''):
    """BOOT: file sizes on DH0; WORLDS: one list of map sizes per world partition; GROUPS: forced
    drive grouping (world partition indexes per drive) or None for the real grouping; EXPECT: None
    (must pass) or a regular expression the refusal must match."""
    return dict(name=name, expect=expect, boot=boot, worlds=worlds, groups=groups, write=write, note=note)


CASES = (
    case('file-over-1gib', r'file id1/maps/vf0000\.bsp is 2500000000 bytes \(limit below %d, 1 GiB\)'
         % wv.FILE_SIZE_LIMIT,
         [1 * MIB], [[2500000000]], note='a single 2.5 GB file'),
    case('partition-over-2gib', r'DW0 is %d bytes \(limit below %d, 2 GiB\)' % (2048 * MIB, wv.PARTITION_SIZE_LIMIT),
         [1 * MIB], [[800 * MIB, 800 * MIB]], note='1600 MiB of maps make a 2048 MiB partition'),
    case('start-past-2gib', r'DW1 starts at %d \(limit below %d, 2 GiB' % (2304 * MIB + wv.RDB_BYTES,
                                                                          wv.PARTITION_START_LIMIT),
         [400 * MIB, 400 * MIB], [[500 * MIB, 500 * MIB], [50 * MIB]], groups=[[0, 1]],
         note='DH0 1024 MiB, DW0 1280 MiB, DW1 128 MiB in that order on one drive'),
    case('drive-over-4gib', r'drive selftest\.hdf \(planned\) is %d bytes \(limit below %d, 4 GiB\)'
         % (4096 * MIB + wv.RDB_BYTES, wv.DRIVE_SIZE_LIMIT),
         [750 * MIB, 750 * MIB], [[750 * MIB, 750 * MIB], [150 * MIB]], groups=[[0, 1]],
         note='DH0 1920 MiB, DW0 1920 MiB, DW1 256 MiB on one drive (a drive over 4 GiB always also '
              'has a partition starting past 2 GiB)'),
    case('largest-legal', None, [GIB - 1, 500 * MIB], [[GIB - 1, 500 * MIB]],
         note='just under every limit: the largest layout the packer makes (plan only: writing it would '
              'copy 3.8 GiB)'),
    case('wiring', None, [4096, 1000], [[70000, 3000, 5]], write=True,
         note='tiny payload through the writers, rdbtool, readback and the gate as written'),
)


def sparse(path, size):
    """A file of SIZE bytes with nothing written into it (a hole on file systems that support them)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'wb') as stream:
        stream.truncate(size)
    return path


def disk_bytes(root):
    """Bytes the files under ROOT really occupy (st_blocks); None where the host does not report it."""
    total = 0
    for path in Path(root).rglob('*'):
        st = path.lstat()
        if not hasattr(st, 'st_blocks'):
            return None
        total += st.st_blocks * 512
    return total


def tool(name):
    found = shutil.which(name)
    if found:
        return found
    beside = Path(sys.executable).parent / name
    return str(beside) if beside.is_file() else None


def run_case(spec, root, xdftool=None, rdbtool=None):
    """Plan (and for a write case, write) one dummy layout through the image step's functions.
    Returns the drive plans, or the assembled (layout, drives, disk_layout) for a write case."""
    boot, maps, out = root / 'boot', root / 'maps', root / 'out'
    boot_paths = [sparse(boot / 'id1' / f'pak{i}.pak', size) for i, size in enumerate(spec['boot'])]
    batches, n = [], 0
    for sizes in spec['worlds']:
        batch = []
        for size in sizes:
            batch.append(sparse(maps / f'vf{n:04d}.bsp', size))
            n += 1
        batches.append(batch)
    # The world partitions as the writer will make them, gated before any write (as in pack).
    planned = wv.plan_partitions(batches)
    wv.require_partition_plans(planned)
    boot_plan = wv.planned_partition('DH0', [dict(path=p.relative_to(boot).as_posix(), bytes=p.stat().st_size)
                                             for p in boot_paths], 'AMIWIND')
    name = lambda index: 'selftest.hdf' if index == 0 else 'selftest-world-%02d.hdf' % index  # noqa: E731
    if spec['groups'] is not None:
        # The real grouping keeps these partitions legal ...
        wv.plan_drives(boot_plan, planned, name=name)
        # ... forced into one drive, the gate must refuse them.
        forced = [[planned[i] for i in group] for group in spec['groups']]
        return wv.plan_drives(boot_plan, planned, name=name, groups=forced)
    plans = wv.plan_drives(boot_plan, planned, name=name)
    if not spec['write']:
        return plans
    if not (xdftool and rdbtool):
        raise FileNotFoundError('xdftool and rdbtool are needed for the wiring case (or use --no-write)')
    out.mkdir()
    images = wv.write_partitions(batches, out, xdftool)
    part = out / 'partition.hdf'
    wv.write_boot_partition(xdftool, part, boot, boot_plan['bytes'] // MIB)
    boot_files = [dict(path=p.relative_to(boot).as_posix(), bytes=p.stat().st_size, sha256=wv.digest(p))
                  for p in boot_paths]
    return wv.assemble_drives(rdbtool, plans, out, part, boot_files, images={i['partition']: i for i in images},
                              run=quiet)


def quiet(command):
    """rdbtool without its per-partition chatter (errors still raise)."""
    subprocess.run(list(map(str, command)), check=True, stdout=subprocess.DEVNULL)


def selftest(scratch=None, write=True, xdftool=None, rdbtool=None, cases=CASES, log=print):
    """Run every case in a scratch folder under SCRATCH (default: the system temp folder) that is
    always removed. Returns (ok, results); results list each case with its outcome, time and the
    apparent and real size of its dummies."""
    xdftool = xdftool or tool('xdftool')
    rdbtool = rdbtool or tool('rdbtool')
    folder = Path(tempfile.mkdtemp(prefix='layout-selftest-', dir=scratch))
    results, dummies = [], 0
    try:
        for spec in cases:
            if spec['write'] and not write:
                results.append(dict(case=spec['name'], outcome='skipped', ok=True, note='--no-write'))
                continue
            root = folder / spec['name']
            started = time.monotonic()
            outcome, message, detail = 'passed', '', None
            try:
                detail = run_case(spec, root, xdftool, rdbtool)
            except ValueError as exc:
                outcome, message = 'refused', str(exc)
            files = [p for p in (root / 'boot').rglob('*') if p.is_file()] + list((root / 'maps').glob('*'))
            dummies += len(files)
            used = disk_bytes(root)
            expect = spec['expect']
            if expect is None:
                ok = outcome == 'passed'
            else:
                ok = outcome == 'refused' and re.search(expect, message) is not None
            hdfs = sorted(p.name for p in root.rglob('*.hdf'))
            if expect is not None and hdfs:
                ok, message = False, message + ' [an image was written before the refusal: %s]' % ', '.join(hdfs)
            row = dict(case=spec['name'], outcome=outcome, ok=ok, seconds=round(time.monotonic() - started, 3),
                       dummy_files=len(files), apparent_bytes=sum(p.stat().st_size for p in files),
                       disk_bytes=used, note=spec['note'])
            if message:
                row['message'] = message
            if spec['write'] and outcome == 'passed':
                row['disk_layout'] = detail[2]
            elif outcome == 'passed':
                row['drives'] = [dict(file=p['file'], bytes=p['bytes'],
                                      starts=[r['start_bytes'] for r in p['layout']['partitions']],
                                      partitions=[r['bytes'] for r in p['layout']['partitions']]) for p in detail]
            results.append(row)
            log('  %-20s %-8s %s  (%.2f s, %d dummy files, %s apparent, %s on disk)' % (
                spec['name'], outcome, 'ok' if ok else 'UNEXPECTED', row['seconds'], len(files),
                human(row['apparent_bytes']), 'n/a' if used is None else human(used)))
            if not ok:
                log('    expected %s; got: %s' % ('a pass' if expect is None else 'a refusal matching ' + expect,
                                                  message or 'a pass'))
            shutil.rmtree(root, ignore_errors=True)
    finally:
        # A case that raised (or Ctrl-C) leaves its dummies behind until here: count and remove them too.
        dummies += sum(1 for part in ('boot', 'maps') for p in folder.glob('*/' + part + '/**/*') if p.is_file())
        shutil.rmtree(folder, ignore_errors=True)
        log('Disk layout self-test: cleaned %d dummy files' % dummies)
    return all(r['ok'] for r in results) and len(results) == len(cases), results


def human(n):
    for unit, size in (('GiB', GIB), ('MiB', MIB), ('KiB', 1024)):
        if n >= size:
            return '%.1f %s' % (n / size, unit)
    return '%d B' % n


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--scratch', type=Path,
                   help='Parent folder of the (always removed) scratch folder; default: system temp')
    p.add_argument('--no-write', action='store_true',
                   help='Skip the wiring case (needs xdftool and rdbtool, ~256 MiB for a few seconds)')
    p.add_argument('--xdftool', help='xdftool executable (default: on PATH or beside this Python)')
    p.add_argument('--rdbtool', help='rdbtool executable (default: on PATH or beside this Python)')
    p.add_argument('--json', type=Path, help='Write the results as JSON here')
    args = p.parse_args(argv)
    print('Disk layout self-test (Amiga limits: partition start and size below 2 GiB, files below 1 GiB, '
          'drives below 4 GiB)', flush=True)
    started = time.monotonic()
    try:
        ok, results = selftest(args.scratch, not args.no_write, args.xdftool, args.rdbtool)
    except FileNotFoundError as exc:
        p.exit(2, 'Error: %s\n' % exc)
    if args.json:
        args.json.write_text(json.dumps(dict(ok=ok, results=results), indent=2) + '\n', encoding='utf-8',
                             newline='\n')
    print('Disk layout self-test: %s in %.1f s' % ('passed' if ok else 'FAILED', time.monotonic() - started),
          flush=True)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
