#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Build run names: date, version, purpose and source commit in every run folder name.

    YYYY_MM_DD_vX.Y.Z[-suffix]_<purpose>[-tryN]_<gitshort>
    e.g. 2026_10_10_v0.0.35-dev1_full_901f8e9

- the date is the host's local date when the build starts;
- the version (with its -devN/-rcN suffix) is the source's VERSION file;
- the purpose is "full" for a whole-game build, "miniwind-<town>[-debug][-quick]" for a MiniWind sandbox,
  "dry-run" for the asset-free test compile, or the stage name for a partial stage build;
- "-tryN" (N >= 2) is added when a run of the same name already exists (run folders are immutable);
- the commit is the source checkout's short git hash, or --source-commit / AMIWIND_SOURCE_COMMIT when the
  source is not a git checkout (an exported source tree), else "nogit".

An explicit --name must contain the source's version; --any-run-name allows any name, with a warning.
Every build records the parts in build-state.json ("run_name"). See docs/BUILD_CACHE.md "Run names".
"""
from datetime import datetime
import os
from pathlib import Path
import re

SCHEME = 'YYYY_MM_DD_vX.Y.Z[-suffix]_<purpose>[-tryN]_<gitshort>'
ENV = 'AMIWIND_SOURCE_COMMIT'
NAME = re.compile(r'[a-zA-Z0-9][a-zA-Z0-9._-]{0,99}')
COMMIT = re.compile(r'[0-9a-fA-F]{4,40}')


def source_version(root):
    return (Path(root) / 'VERSION').read_text(encoding='utf-8').strip()


def split_version(version):
    """('0.0.35', 'dev1') for 0.0.35-dev1; ('0.0.35', None) for a final version."""
    base, _, suffix = version.partition('-')
    return base, suffix or None


def git_head(root):
    """The checkout's HEAD commit read from its .git files (no git program, no subprocess), or None."""
    git = Path(root) / '.git'
    try:
        if git.is_file():  # a worktree: "gitdir: PATH"
            line = git.read_text(encoding='utf-8').strip()
            if not line.startswith('gitdir:'):
                return None
            git = (Path(root) / line[len('gitdir:'):].strip()).resolve()
        if not git.is_dir():
            return None
        common = git
        if (git / 'commondir').is_file():
            common = (git / (git / 'commondir').read_text(encoding='utf-8').strip()).resolve()
        head = (git / 'HEAD').read_text(encoding='utf-8').strip()
        if head.startswith('ref:'):
            ref = head[4:].strip()
            for folder in (git, common):
                if (folder / ref).is_file():
                    head = (folder / ref).read_text(encoding='utf-8').strip()
                    break
            else:
                packed = common / 'packed-refs'
                rows = packed.read_text(encoding='utf-8').splitlines() if packed.is_file() else []
                head = next((row.split()[0] for row in rows if row.endswith(' ' + ref)), '')
        return head.lower() if re.fullmatch(r'[0-9a-fA-F]{40}', head) else None
    except OSError:
        return None


def source_commit(root, explicit=None):
    """(short hash, where it came from): the checkout's git HEAD, else EXPLICIT or AMIWIND_SOURCE_COMMIT, else
    ('nogit', 'unknown')."""
    found = git_head(root)
    if found:
        return found[:7], 'git'
    for value, origin in ((explicit, '--source-commit'), (os.environ.get(ENV), ENV)):
        if value:
            if not COMMIT.fullmatch(value.strip()):
                raise ValueError(f'{origin} must be a git commit hash (4-40 hex digits), not {value!r}')
            return value.strip().lower()[:7], origin
    return 'nogit', 'unknown'


def purpose(stage='aga', dry_run=False, miniwind_label=None):
    if dry_run:
        return 'dry-run'
    if miniwind_label is not None:
        return 'miniwind' + miniwind_label
    return 'full' if stage == 'aga' else stage


def default_name(version, what, commit, exists=None, today=None):
    """The run name per SCHEME; EXISTS(name) -> True adds -try2, -try3, ..."""
    date = (today or datetime.now()).strftime('%Y_%m_%d')
    for attempt in range(1, 1000):
        name = f"{date}_v{version}_{what}{'' if attempt == 1 else f'-try{attempt}'}_{commit}"
        if exists is None or not exists(name):
            return name
    raise ValueError('More than 999 runs of the same name today; give --name')


def check_explicit(name, version, allow_any=False):
    """None, or the loud warning for an explicit name without the version (only with ALLOW_ANY); else refuse."""
    if version in name:
        return None
    if not allow_any:
        raise ValueError(f'--name {name!r} does not contain the source version {version} (run names: {SCHEME}, e.g. '
                         f'{default_name(version, "full", "901f8e9")}); leave --name out for the default name, or '
                         'pass --any-run-name')
    return (f'WARNING: run name {name!r} does not contain the source version {version} (--any-run-name); '
            f'the naming scheme is {SCHEME}.')


def record(name, version, commit, commit_origin, what, explicit):
    base, suffix = split_version(version)
    return {'name': name, 'scheme': SCHEME, 'version': version, 'base_version': base, 'suffix': suffix,
            'commit': commit, 'commit_from': commit_origin, 'purpose': what, 'explicit': bool(explicit)}
