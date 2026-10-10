#!/usr/bin/env python3
"""Build preflight: the checks that take seconds run before any stage (BUILD-CACHE-OWNER-FAILS-STAGE-34).

tools/build.py runs it for every real image build, right after the previous-release check and before setup:

- the workspace cache (WORKSPACE/cache: unit caches, pass caches, the storage pool) holds no folder this
  user cannot write and no entry owned by another user (a container that ran as root left such entries
  and a release build failed four minutes in);
- the workspace's file system has room for the build (AMIWIND_MIN_FREE_GIB, default 20; release candidates
  and finals stop, development builds warn);
- the game data folder exists and holds the master file;
- every town config's entity and model budget fits the engine's tables (tools/map_engine_limits.py
  budget_room: a config may only tighten the engine's limits, BUILD-BUDGET-ENGINE-LIMITS-35).

Every problem is listed at once, each with the command that fixes it. Run it alone with
`python3 tools/build_preflight.py --workspace DIR [--data-files DIR]`.
A cache entry that still cannot be read or written later never fails a stage: the unit is built locally and
the build reports "cache write refused".
"""
import argparse
import os
import shutil
import sys
from pathlib import Path

MIN_FREE_ENV = 'AMIWIND_MIN_FREE_GIB'
DEFAULT_MIN_FREE_GIB = 20
SHOWN = 5


def cache_problems(cache, uid=None):
    """[message] for folders under CACHE this user cannot write and entries another user owns."""
    cache = Path(cache)
    if not cache.is_dir():
        return []
    if uid is None:
        if not hasattr(os, 'geteuid'):
            return []  # no POSIX owners (Windows): only the write test below would apply
        uid = os.geteuid()
    if uid == 0:
        return []
    foreign, unwritable = [], []
    for folder, _, files in os.walk(cache):
        for path in [Path(folder), *(Path(folder) / name for name in files)]:
            try:
                info = os.lstat(path)
            except OSError:
                continue
            if info.st_uid != uid:
                foreign.append(path)
        if not os.access(folder, os.W_OK | os.X_OK):
            unwritable.append(Path(folder))
    problems = []
    gid = os.getegid() if hasattr(os, 'getegid') else uid
    if foreign or unwritable:
        listed = ', '.join(str(p) for p in (unwritable + foreign)[:SHOWN])
        problems.append(f'{len(foreign)} cache entries owned by another user and {len(unwritable)} folders this user '
                        f'cannot write under {cache} (first: {listed}); fix, as root where the cache lives: '
                        f'chown -R {uid}:{gid} {cache}')
    return problems


def free_space_problems(workspace, minimum_gib=None):
    if minimum_gib is None:
        try:
            minimum_gib = float(os.environ.get(MIN_FREE_ENV, DEFAULT_MIN_FREE_GIB))
        except ValueError:
            minimum_gib = DEFAULT_MIN_FREE_GIB
    existing = Path(workspace).absolute()
    while not existing.exists() and existing.parent != existing:
        existing = existing.parent
    try:
        free = shutil.disk_usage(existing).free / 2 ** 30
    except OSError:
        return []
    if free < minimum_gib:
        return [f'{free:.1f} GiB free where the workspace is ({existing}), {minimum_gib:g} GiB needed; fix: free space '
                f'there or build in another --workspace ({MIN_FREE_ENV} sets the minimum)']
    return []


def data_problems(data_files):
    if data_files is None:
        return []
    data = Path(data_files)
    if not data.is_dir():
        return [f'game data folder {data} does not exist; fix: --data-files <your Morrowind Data Files folder>']
    if not any(p.name.lower() == 'morrowind.esm' for p in data.iterdir()):
        return [f'game data folder {data} has no Morrowind.esm; fix: point --data-files at the Data Files folder']
    return []


def budget_problems(config_dir=None):
    """[problem] when a town config asks for more entities or models than the engine holds."""
    import map_engine_limits
    try:
        if config_dir is None:
            map_engine_limits.check_config_budgets()
        else:
            map_engine_limits.check_config_budgets(config_dir)
    except ValueError as exc:
        return [f'{exc}; fix: lower the budget in the named config']
    return []


def run(workspace, data_files=None, uid=None, minimum_gib=None, space=True):
    """[problem] of every check; empty when the build may start. tools/build.py checks the free space itself
    (space=False): release candidates and finals stop on it, development builds print a warning."""
    workspace = Path(workspace)
    return (cache_problems(workspace / 'cache', uid) + (free_space_problems(workspace, minimum_gib) if space else [])
            + data_problems(data_files) + budget_problems())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--workspace', type=Path, required=True)
    ap.add_argument('--data-files', type=Path)
    args = ap.parse_args(argv)
    problems = run(args.workspace, args.data_files)
    for problem in problems:
        print('Build preflight: ' + problem)
    print(f'Build preflight: {len(problems)} problems')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
