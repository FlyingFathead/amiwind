# SPDX-License-Identifier: GPL-3.0-only
"""--clean and --public-defaults: a build as a first-time public user makes it (docs/BUILD_CACHE.md).

--clean builds with nothing from earlier builds: no --reuse-from run, no prerendered store, no cache or
storage pool outside the workspace, and the workspace's own cache folder (WORKSPACE/cache: the unit, media,
image-pass, stair-walk, NPC gallery and parts caches and the storage pool) must be empty or absent when the
build starts. A workspace with a filled cache is refused, never emptied: nothing is deleted; give a new
--workspace. The caches fill during the build as they do for a first-time user. Environment variables that
point the builder at another cache are ignored and listed.

--public-defaults refuses what a public user would not have: --override, the retired flags, every
--allow-* and --accept-* waiver, a --chim-regions @FILE or --chim-regions-status FILE outside the source
tree, and every switch of docs/EXPERIMENTAL_FLAGS.md at a value other than the builder's default. Every
refusal is listed with its reason.

Together, --clean --public-defaults is the release's from-scratch check. Both are off by default and change
no stage command and no stage key; when given, the build receipt records them ("clean", "public_defaults").

Light module: no third-party imports (the parser and the tests read it).
"""
from pathlib import Path
import json
import os
import re

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTAL_DOC = ROOT / 'docs' / 'EXPERIMENTAL_FLAGS.md'
DEFAULTS_FILE = ROOT / 'config' / 'build-defaults.json'

# Options that bring in work of an earlier build or a cache outside the workspace: (dest, flag, why).
CLEAN_REFUSED = (
    ('reuse_from', '--reuse-from', 'takes the stages of an earlier run'),
    ('rebuild_stage', '--rebuild-stage', 'works only with --reuse-from'),
    ('rebuild_unit', '--rebuild-unit', 'reruns a unit an earlier build stored in the cache'),
    ('prerendered', '--prerendered', 'takes stage outputs an earlier build stored'),
    ('gallery_cache', '--gallery-cache', 'an NPC gallery cache outside the workspace'),
    ('gallery_seed_run', '--gallery-seed-run', 'seeds the NPC gallery from an earlier run'),
    ('parts_cache', '--parts-cache', 'an NPC parts cache outside the workspace'),
    ('storage_pool_dir', '--storage-pool-dir', 'a storage pool outside the workspace'),
    ('allow_release_reuse', '--allow-release-reuse', 'turns on the per-file caches of a release version'),
)
# Environment variables that point the builder at another cache, pool or record folder; --clean ignores them.
CLEAN_ENV = ('AMIWIND_PASS_CACHE', 'AMIWIND_CACHE_FALLBACK', 'AMIWIND_STORAGE_POOL', 'AMIWIND_COST_HISTORY',
             'AMIWIND_STAIR_RECORDS')
# What a clean build starts without (the receipt's list).
CLEAN_WITHOUT = ('--reuse-from run', 'prerendered store', 'per-map world terrain cache (empty)',
                 'CHIM unit cache (empty)', 'media cache and storage pool (empty)', 'image-pass and stair-walk '
                 'cache (empty)', 'NPC gallery and parts caches (empty)', 'cache and pool folders from the '
                 'environment or the build config')
# Experimental switches with their own public rule below (a public user selects cells with the shipped sets or a
# file in the source tree, docs/chim/CHIM_REGIONS.md).
OWN_RULE = frozenset({'chim_regions', 'chim_regions_status'})


class Refused(ValueError):
    """The build is refused before any stage; the message lists every refused option."""


def _entries(folder):
    try:
        return sorted(path.name for path in Path(folder).iterdir())
    except (FileNotFoundError, NotADirectoryError):
        return []


def configure_clean(args, environ=None, config_pool=None):
    """The record of a --clean build, or None without --clean. Refused (before any stage) for an option or a
    workspace that brings in earlier work. Removes CLEAN_ENV from ENVIRON (default os.environ) and lists them.
    CONFIG_POOL: the build config's storage_pool_dir (build_font_options.configured_storage_pool_dir)."""
    if not getattr(args, 'clean', False):
        return None
    environ = os.environ if environ is None else environ
    refused = ['%s: %s' % (flag, why) for dest, flag, why in CLEAN_REFUSED if getattr(args, dest, None)]
    if config_pool:
        refused.append('build config storage_pool_dir %s: a storage pool outside the workspace' % config_pool)
    cache = Path(args.workspace).expanduser().absolute() / 'cache'
    found = _entries(cache)
    if found:
        refused.append('the workspace cache %s holds %d entries (%s%s): a clean build starts with an empty '
                       'cache; give a new --workspace (nothing is deleted)'
                       % (cache, len(found), ', '.join(found[:6]), ', ...' if len(found) > 6 else ''))
    if refused:
        raise Refused('--clean refused before any stage:\n  ' + '\n  '.join(refused))
    ignored = sorted(name for name in CLEAN_ENV if environ.get(name))
    for name in ignored:
        environ.pop(name, None)
    return {'clean': True, 'workspace_cache': str(cache), 'workspace_cache_empty_at_start': True,
            'without': list(CLEAN_WITHOUT), 'environment_ignored': ignored,
            'stair_records': 'only the known-good records shipped with the source (config/stair-records)'}


def clean_line(record):
    return ('CLEAN BUILD (--clean): as a first-time user: empty cache %s, no earlier run, no prerendered store, no '
            'outside cache or pool%s' % (record['workspace_cache'], '; ignored from the environment: '
                                         + ', '.join(record['environment_ignored'])
                                         if record['environment_ignored'] else ''))


# --------------------------------------------------------------------------
# --public-defaults

def experimental_switches(text=None):
    """{flag: set of values named with it} of the switch column of docs/EXPERIMENTAL_FLAGS.md (the table above
    "Retired flags"); a value is a word after the flag in the same code span or a following bare code span."""
    text = EXPERIMENTAL_DOC.read_text(encoding='utf-8') if text is None else text
    text = text.split('\n## Retired flags', 1)[0]
    found = {}
    for line in text.splitlines():
        if not line.startswith('|') or line.startswith('| ---') or line.startswith('| Switch'):
            continue
        cell = line.split('|')[1]
        current = None
        for span in re.findall(r'`([^`]*)`', cell):
            words = span.split()
            if words and words[0].startswith('--'):
                current = words[0]
                found.setdefault(current, set()).update(words[1:2])
            elif current and len(words) == 1:
                found[current].add(words[0])
    return found


def _same(value, default):
    def norm(item):
        if isinstance(item, (list, tuple)):
            return [norm(part) for part in item]
        if isinstance(item, Path):
            return item.as_posix()
        return item
    return norm(value) == norm(default)


def _inside(path, root):
    try:
        Path(path).expanduser().resolve().relative_to(Path(root).resolve())
        return True
    except (ValueError, OSError):
        return False


def check_public_defaults(args, parser, build_defaults=None, experimental=None, root=ROOT):
    """The record of a --public-defaults build, or None without it. Refused with every refused option and its
    reason. ARGS are the effective options (a recipe already folded in)."""
    if not getattr(args, 'public_defaults', False):
        return None
    if build_defaults is None:
        build_defaults = json.loads(DEFAULTS_FILE.read_text(encoding='utf-8'))
    experimental = experimental_switches() if experimental is None else experimental
    flags = {}
    for action in parser._actions:
        for flag in action.option_strings:
            flags[flag] = action
    refused = []
    for name in getattr(args, 'override', None) or []:
        refused.append(('--override ' + name, 'lets a retired flag through; a public build has none'))
    for row in getattr(args, 'retired_flags_record', None) or []:
        refused.append((row['flag'], 'retired since %s: %s' % (row['retired_since'], row['why'])))
    for action in parser._actions:
        dest = action.dest
        if not action.option_strings or not dest.startswith(('allow_', 'accept_')):
            continue
        value = getattr(args, dest, None)
        if value and not _same(value, action.default):
            refused.append((action.option_strings[0], 'a waiver (--allow-* / --accept-*): a public build waives '
                                                      'nothing'))
    for item in getattr(args, 'chim_regions', None) or []:
        text = str(item)
        if text.startswith('@') and not _inside(text[1:], root):
            refused.append(('--chim-regions ' + text, 'a cell list outside the source tree, which a public user '
                                                      'does not have'))
    status = getattr(args, 'chim_regions_status', None)
    if status and not _inside(status, root):
        refused.append(('--chim-regions-status %s' % status, 'a tracker file outside the source tree (the public '
                                                              'one: docs/chim/cell-progress-reference.json)'))
    seen = set()
    for flag, values in sorted(experimental.items()):
        action = flags.get(flag)
        if action is None or action.dest in OWN_RULE or action.dest in seen:
            continue
        seen.add(action.dest)
        value = getattr(args, action.dest, None)
        if value in (None, [], '') or _same(value, action.default):
            continue
        if action.dest in build_defaults and _same(value, build_defaults[action.dest]):
            continue
        if action.default is None and action.dest not in build_defaults and values and str(value) not in values:
            continue  # the builder decides this default; only the documented experimental values are refused
        shown = flag if isinstance(value, bool) else '%s %s' % (flag, value)
        refused.append((shown,
                        'an experimental switch (docs/EXPERIMENTAL_FLAGS.md); a public build uses the default'))
    if refused:
        raise Refused('--public-defaults refused before any stage (%d):\n  ' % len(refused)
                      + '\n  '.join('%s: %s' % row for row in refused))
    return {'public_defaults': True, 'refused': [],
            'checked': ['--override', 'retired flags', '--allow-* and --accept-* waivers',
                        '--chim-regions @FILE and --chim-regions-status outside the source tree',
                        '%d experimental switches (docs/EXPERIMENTAL_FLAGS.md)' % len(seen)]}


def public_line(record):
    return 'PUBLIC DEFAULTS (--public-defaults): checked ' + '; '.join(record['checked']) + ': none given'
