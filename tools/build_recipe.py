# SPDX-License-Identifier: GPL-3.0-only
"""Build recipes: a build's options as named fields, its inputs by SHA-256 and the build that checked it.

    tools/build.py --recipe FILE [options]         build from a recipe; command-line options win
    tools/build.py ... --save-recipe FILE          write the exact recipe of the build being run
    tools/build.py --miniwind-preset NAME          a MiniWind preset: the recipe config/recipes/miniwind/NAME.json

A recipe (schema build-recipe-1, config/schemas/build-recipe-1.json) holds:

  options       option name -> value, named by the builder's own option names (the argparse destination of
                every tools/build.py option: chim_terrain_hull for --chim-terrain-hull); null or left out =
                the builder's default. Options about this machine (paths of tools and workspaces, the run name,
                reuse, jobs, modes such as --plan) are never part of a recipe (NOT_IN_RECIPE), nor --override:
                a recipe cannot let a retired option through by itself.
  inputs        every file or folder an option names (a path option, a --chim-regions @FILE) with its role
                and SHA-256 (a folder: the SHA-256 of its sorted "sha256  path" list); a mismatch is refused.
  written_with  the builder that wrote it (AmiWind and CHIM version, commit, host time, run); null for the
                recipes kept with the source tree (config/recipes/), which follow that tree.
  checked_with  the passed build that verified it (run, host time, SHA-256 of its result record), filled in
                by the master builder (tools/aw.py) after success; null = unverified (a warning).

Versions: a recipe checked with (or written by) the same AmiWind version builds quietly; with an older one
the build warns and lists every option whose meaning or default changed since (config/option-changes.json);
a recipe from a NEWER version is refused, naming the options this builder does not know.

Standard library only; the builder's parser is handed in (tools/build.py parser), so tools/aw.py can use the
document checks without the builder. docs/BUILD_RECIPES.md.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'build-recipe-1'
SCHEMA_FILE = ROOT / 'config' / 'schemas' / 'build-recipe-1.json'
CHANGES_FILE = ROOT / 'config' / 'option-changes.json'
RECIPES = ROOT / 'config' / 'recipes'
PRESETS = RECIPES / 'miniwind'
DEFAULTS_FILE = ROOT / 'config' / 'build-defaults.json'
# The image step reads the recipe record from here (tools/build_aga.py); never part of a stage key
# (tools/build_cache.py IGNORED_ENV): a reused image keeps the record of the run that made it.
ENV = 'AMIWIND_BUILD_RECIPE'
VERSION_RE = re.compile(r'([0-9]+)\.([0-9]+)\.([0-9]+)(?:-(dev|rc)([0-9]+))?')

# Options a recipe never holds: where and how this machine builds (tool and workspace paths, the run name,
# reuse, caches, jobs), one-off modes (--check, --plan, setup, inventories) and the switches that must be
# given by hand on the command line (--override, the developer-mode waivers). Everything else is a recipe option.
NOT_IN_RECIPE = frozenset({
    'help', 'data_files', 'workspace', 'check', 'plan', 'install_dependencies', 'autoinstall', 'yes',
    'install_sdk', 'tools_dir', 'versions', 'host_plan', 'check_inputs', 'layout_selftest', 'dry_run',
    'recover_image_from', 'autorun_fs_uae', 'kickstart_file', 'name', 'any_run_name', 'developer_mode',
    'working_version', 'accept_version_mismatch', 'source_commit', 'sdk', 'vasm', 'upstream_archive',
    'quake_tools', 'qcc', 'ffmpeg', 'xdftool', 'rdbtool', 'gallery_cache', 'gallery_seed_run', 'parts_cache',
    'estimate_world', 'estimate_sample', 'jobs', 'serial_stages', 'no_profile', 'reuse_from', 'reuse_mode',
    'rebuild_stage', 'rebuild_unit', 'accept_rebuild', 'allow_release_reuse', 'prerendered',
    'prerendered_stages', 'storage_pool', 'storage_pool_dir', 'fingerprint_scope', 'live_tracker',
    'tracker_declined', 'keep_tracker', 'override', 'miniwind_preset', 'recipe', 'save_recipe',
    'recipe_inputs', 'perf_guard', 'perf_guard_baselines', 'size_guard', 'size_baseline', 'size_growth_margin',
    'size_growth_reason', 'clean', 'public_defaults',
    # the free space this machine must have (tools/disk_need.py)
    'min_free_gib', 'disk_margin_percent'})
# Repeatable options whose command-line values add to the recipe's instead of replacing them
# (exclusions add up, as they did with the MiniWind preset table).
ADDITIVE = frozenset({'exclude'})
# The role an input gets when --save-recipe finds it (an option not listed: its own name with hyphens).
INPUT_ROLES = {'chim_regions': 'chim-regions-cells', 'chim_regions_status': 'chim-regions-status',
               'intro_captions': 'intro-captions', 'amiga_libs': 'amiga-libs', 'seyda_recorded': 'seyda-recorded',
               'allow_known_actor_ground_findings': 'actor-ground-report', 'build_config': 'build-config',
               'fallback_font': 'fallback-font', 'shared_sky_source': 'shared-sky', 'npc_face_lod_list': 'face-lod-list'}
# --chim-regions values that name a file: @FILE (tools/chim/regions.py).
AT_FILE_OPTIONS = frozenset({'chim_regions'})


class RecipeError(ValueError):
    """A recipe the builder refuses (the build stops before any stage)."""


# --------------------------------------------------------------------------
# Small helpers

def stamp(moment=None):
    """Host time 'YYYY-MM-DD HH:MM:SS +ZZZZ'."""
    moment = datetime.datetime.now().astimezone() if moment is None else moment
    return moment.strftime('%Y-%m-%d %H:%M:%S %z')


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def folder_sha256(path):
    """SHA-256 of a folder: of its sorted 'sha256  relative/path' lines (every file, LF-joined)."""
    base = Path(path)
    lines = sorted('%s  %s' % (file_sha256(item), item.relative_to(base).as_posix())
                   for item in base.rglob('*') if item.is_file())
    return hashlib.sha256(('\n'.join(lines) + '\n').encode('utf-8')).hexdigest()


def content_sha256(path):
    """(sha256, kind) of a file or folder."""
    path = Path(path)
    if path.is_dir():
        return folder_sha256(path), 'folder'
    return file_sha256(path), 'file'


def canonical(document):
    return json.dumps(document, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def version_key(version):
    """Sort key of an AmiWind version: X.Y.Z-devN < X.Y.Z-rcN < X.Y.Z."""
    match = VERSION_RE.fullmatch(str(version).strip().lstrip('v'))
    if not match:
        raise RecipeError('not an AmiWind version (X.Y.Z, X.Y.Z-devN or X.Y.Z-rcN): %r' % (version,))
    major, minor, patch, stage, number = match.groups()
    return (int(major), int(minor), int(patch), {'dev': 0, 'rc': 1, None: 2}[stage], int(number or 0))


def compare_versions(first, second):
    """-1, 0 or 1."""
    a, b = version_key(first), version_key(second)
    return (a > b) - (a < b)


def jsonable(value):
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    return value


# --------------------------------------------------------------------------
# Documents

def schema():
    return json.loads(SCHEMA_FILE.read_text(encoding='utf-8'))


def document_errors(document):
    """Every reason DOCUMENT is not a well-formed recipe (schema and the rules between fields); no builder needed."""
    if str(ROOT / 'tools') not in sys.path:
        sys.path.insert(0, str(ROOT / 'tools'))
    from aw import validate
    if not isinstance(document, dict):
        return ['a recipe is a JSON object']
    errors = validate(document, schema())
    if errors:
        return errors
    options = document['options']
    for key in options:
        if not re.fullmatch(r'[a-z][a-z0-9_]*', key):
            errors.append('options: %r is not an option name (the builder\'s names: chim_terrain_hull for '
                          '--chim-terrain-hull)' % key)
        elif key in NOT_IN_RECIPE:
            errors.append('options: %s is not part of a recipe (it is about this machine or a one-off mode: give it '
                          'on the command line)' % key)
    if (document['checked_with'] is None) != (document['status'] == 'unverified'):
        errors.append('status: "verified" goes with a checked_with record, "unverified" with checked_with null')
    seen = set()
    for item in document['inputs']:
        if item['role'] in seen:
            errors.append('inputs: role %s appears twice' % item['role'])
        seen.add(item['role'])
        if item['option'] not in options:
            errors.append('inputs: %s (%s) names option %s, which the recipe does not set'
                          % (item['role'], item['path'], item['option']))
    return errors


def read(path):
    """(document, raw bytes) of a recipe file, checked; RecipeError otherwise."""
    path = Path(path)
    try:
        raw = path.read_bytes()
        document = json.loads(raw.decode('utf-8'))
    except (OSError, ValueError, UnicodeError) as exc:
        raise RecipeError('cannot read the recipe %s: %s' % (path, exc))
    errors = document_errors(document)
    if errors:
        raise RecipeError('recipe %s is not a %s document: %s' % (path, SCHEMA, '; '.join(errors[:6])))
    return document, raw


def write(path, document):
    errors = document_errors(document)
    if errors:
        raise RecipeError('refusing to write a malformed recipe: ' + '; '.join(errors[:6]))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp-%d' % os.getpid())
    temporary.write_text(json.dumps(document, indent=2, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')
    os.replace(temporary, path)
    return file_sha256(path)


# --------------------------------------------------------------------------
# The builder's options

def actions_by_dest(parser):
    """{dest: [actions]} of every option a recipe may hold."""
    found = {}
    for action in parser._actions:
        if not action.option_strings or action.dest in NOT_IN_RECIPE or action.dest == argparse.SUPPRESS:
            continue
        found.setdefault(action.dest, []).append(action)
    return found


def primary_flag(actions):
    for action in actions:
        if type(action).__name__ in ('_StoreAction', '_AppendAction', '_StoreTrueAction'):
            return action.option_strings[0]
    return actions[0].option_strings[0]


def tokens(actions, value, dest='option'):
    """The command-line words that give DEST the VALUE (RecipeError if no form of the option can)."""
    if value is None:
        return []
    kinds = {type(action).__name__: action for action in actions}
    if isinstance(value, bool):
        for action in actions:
            name = type(action).__name__
            if (name == '_StoreTrueAction' and value) or (name == '_StoreFalseAction' and not value) or \
                    (name == '_StoreConstAction' and action.const is value):
                return [action.option_strings[0]]
        if all(type(a).__name__ in ('_StoreTrueAction', '_StoreFalseAction') for a in actions) and \
                value == actions[0].default:
            return []
        raise RecipeError('option %s cannot be %s' % (dest, json.dumps(value)))
    if isinstance(value, list):
        if not value:
            return []
        if '_AppendAction' in kinds:
            flag = kinds['_AppendAction'].option_strings[0]
            return ['%s=%s' % (flag, jsonable(item)) for item in value]
        store = kinds.get('_StoreAction')
        if store is not None and store.nargs in ('+', '*'):
            return [store.option_strings[0], *[str(jsonable(item)) for item in value]]
        raise RecipeError('option %s takes one value, not a list' % dest)
    for action in actions:
        if type(action).__name__ in ('_StoreConstAction', '_AppendConstAction') and action.const == value:
            return [action.option_strings[0]]
    store = kinds.get('_StoreAction')
    if store is None or store.nargs not in (None, '?'):
        raise RecipeError('option %s cannot be %s' % (dest, json.dumps(value)))
    return ['%s=%s' % (store.option_strings[0], value)]


def shown(actions, value):
    """'--flag value' as a person would type it (for messages)."""
    try:
        words = tokens(actions, value)
    except RecipeError:
        words = []
    words = [word.replace('=', ' ', 1) if word.startswith('--') else word for word in words]
    return ' '.join(words) if words else 'the default (%s)' % json.dumps(jsonable(value))


def _raising(parser):
    def error(message):
        raise RecipeError(message)
    parser.error = error
    return parser


def suppressed(factory):
    """A fresh builder parser that leaves every option it is not given out of the result."""
    parser = _raising(factory())
    for action in parser._actions:
        if action.dest != 'help':
            action.default = argparse.SUPPRESS
    return parser


def given(factory, argv):
    """{dest: value} of exactly the options ARGV names."""
    return vars(suppressed(factory).parse_args(list(argv)))


def parsed_options(factory, options):
    """{dest: value} of a recipe's options, parsed by the builder's own parser (choices, types)."""
    actions = actions_by_dest(factory())
    words = []
    for dest, value in options.items():
        if dest in actions:
            words += tokens(actions[dest], value, dest)
    parser = suppressed(factory)
    try:
        values = vars(parser.parse_args(words))
    except RecipeError as exc:
        raise RecipeError('recipe options: ' + str(exc))
    return values


def file_values(dest, value, path_dests):
    """The paths a value names: a path option's value, or the @FILE entries of --chim-regions."""
    if value in (None, [], ''):
        return []
    items = value if isinstance(value, list) else [value]
    if dest in AT_FILE_OPTIONS:
        return [str(item)[1:] for item in items if str(item).startswith('@')]
    if dest in path_dests:
        return [str(jsonable(item)) for item in items]
    return []


def path_dests(parser):
    return {dest for dest, actions in actions_by_dest(parser).items() if any(a.type is Path for a in actions)}


# --------------------------------------------------------------------------
# Option changes (config/option-changes.json)

def load_changes(path=CHANGES_FILE):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if data.get('format') != 1:
        raise RecipeError('%s: unknown format' % path)
    return data


def changes_between(older, newer, changes=None):
    """Every recorded change with older < version <= newer, oldest first."""
    rows = (changes or load_changes())['changes']
    picked = [row for row in rows if compare_versions(older, row['version']) < 0 <= compare_versions(newer, row['version'])]
    return sorted(picked, key=lambda row: version_key(row['version']))


def change_line(row, recipe_options=None):
    what = {'added': 'new option, default %s' % json.dumps(row.get('to')),
            'default': 'default %s -> %s' % (json.dumps(row.get('from')), json.dumps(row.get('to'))),
            'meaning': 'meaning changed', 'retired': 'RETIRED (refused in developer mode without --override)',
            'removed': 'removed'}[row['change']]
    line = '%s (%s): %s in v%s' % (row.get('flag') or row['option'], row['option'], what, row['version'])
    if row.get('note'):
        line += ' - ' + row['note']
    if recipe_options is not None and row['option'] in recipe_options and recipe_options[row['option']] is not None:
        line += ' [this recipe sets it: %s]' % json.dumps(jsonable(recipe_options[row['option']]))
    return line


def snapshot(factory):
    """The defaults this builder has now: every recipe option's parser default and config/build-defaults.json.
    config/option-changes.json "current" must equal it (tests/test_build_recipe.py): a changed default or a new
    option is recorded there as a change first."""
    parser = factory()
    defaults = {dest: jsonable(parser.get_default(dest)) for dest in sorted(actions_by_dest(parser))}
    return {'options': defaults,
            'build_defaults': json.loads(DEFAULTS_FILE.read_text(encoding='utf-8'))}


# --------------------------------------------------------------------------
# Loading a recipe into the builder's options

def preset_path(name):
    return PRESETS / ('%s.json' % name)


def _note(out, text):
    print(text, file=out, flush=True)


def check_inputs(document, options, cli_dests, remap, base=None):
    """SHA-256 of every input; returns (records, the options with remapped paths). RecipeError on a mismatch."""
    records, problems = [], []
    options = dict(options)
    for item in document['inputs']:
        record = {'option': item['option'], 'role': item['role'], 'path': item['path'],
                  'sha256': item['sha256'], 'kind': item.get('kind', 'file')}
        if item['option'] in cli_dests:
            record.update(status='replaced by the command line')
            records.append(record)
            continue
        path = remap.get(item['role'], item['path'])
        if path != item['path']:
            value = options[item['option']]
            swap = (lambda v: '@' + path if v == '@' + item['path'] else path if v == item['path'] else v)
            options[item['option']] = [swap(v) for v in value] if isinstance(value, list) else swap(value)
            record['path'] = path
            record['recipe_path'] = item['path']
        found = Path(path) if Path(path).is_absolute() or base is None else Path(base) / path
        if not found.exists():
            problems.append('input %s: %s not found' % (item['role'], path))
            record['status'] = 'missing'
        else:
            actual, kind = content_sha256(found)
            record['actual_sha256'] = actual
            if actual != item['sha256']:
                problems.append('input %s (%s): SHA-256 %s is not the recipe\'s %s'
                                % (item['role'], path, actual, item['sha256']))
                record['status'] = 'mismatch'
            else:
                record['status'] = 'ok'
        records.append(record)
    if problems:
        raise RecipeError('recipe inputs refused: ' + '; '.join(problems))
    return records, options


def parse_remap(values):
    remap = {}
    for text in values or []:
        role, equal, path = text.partition('=')
        if not equal or not role or not path:
            raise RecipeError('--recipe-input takes ROLE=PATH, not %r' % text)
        remap[role] = path
    return remap


def configure(factory, args, argv, version, out=sys.stdout, check_files=True, explicit=None):
    """Fold the recipe of --recipe FILE or --miniwind-preset NAME into ARGS (the options ARGV names win; EXPLICIT
    replaces that list when given). Returns the record every receipt carries, or None without a recipe.
    RecipeError for a recipe the builder refuses. VERSION None: no version comparison (presets, tests)."""
    recipe_file = getattr(args, 'recipe', None)
    preset = getattr(args, 'miniwind_preset', None)
    remap = parse_remap(getattr(args, 'recipe_inputs', None))
    if recipe_file is None and preset is None:
        if remap:
            raise RecipeError('--recipe-input needs --recipe')
        return None
    if recipe_file is not None and preset is not None:
        raise RecipeError('give one recipe: --recipe %s or the MiniWind preset %s, not both' % (recipe_file, preset))
    if preset is not None:
        if version is not None:
            from project_version import require_private_test_version
            require_private_test_version(version, ['--miniwind-preset ' + preset])
        import miniwind_presets
        miniwind_presets.find(preset)  # unknown preset: refused with the list of presets
        recipe_file = preset_path(preset)
    document, raw = read(recipe_file)
    record = {'name': document['name'], 'file': Path(recipe_file).as_posix(),
              'sha256': hashlib.sha256(raw).hexdigest(), 'status': document['status'],
              'written_with': document['written_with'], 'checked_with': document['checked_with'],
              'preset': preset, 'builder_version': version, 'relation': None, 'changed_options': [],
              'overrides': [], 'added': [], 'inputs': []}
    parser = factory()
    actions = actions_by_dest(parser)
    options = document['options']
    unknown = sorted(dest for dest in options if dest not in actions)
    reference = document['checked_with'] or document['written_with']
    if reference is not None and version is not None:
        recipe_version = reference['amiwind_version']
        relation = compare_versions(recipe_version, version)
        if relation > 0:
            raise RecipeError('this recipe needs a newer builder (v%s); this builder is v%s%s' % (
                recipe_version, version, ': options it does not know: ' + ', '.join(unknown) if unknown else
                ' (every option name is known here, but their meaning may differ)'))
        if relation < 0:
            rows = changes_between(recipe_version, version)
            record['relation'] = 'newer-builder'
            record['changed_options'] = [dict(row) for row in rows]
            lines = ['=' * 72, 'WARNING: recipe %s %s v%s, this builder is v%s' % (
                document['name'], 'checked with' if document['checked_with'] else 'written by', recipe_version,
                version)]
            chim = reference.get('chim_version')
            if rows:
                lines.append('Options whose meaning or default changed since v%s (config/option-changes.json):'
                             % recipe_version)
                lines += ['  ' + change_line(row, options) for row in rows]
            else:
                lines.append('No option changed its meaning or default since v%s (config/option-changes.json).'
                             % recipe_version)
            if chim:
                lines.append('The recipe\'s CHIM version: %s.' % chim)
            lines.append('=' * 72)
            _note(out, '\n'.join(lines))
        else:
            record['relation'] = 'same'
    else:
        record['relation'] = 'in-tree'
    if unknown:
        raise RecipeError('recipe %s: options this builder does not know: %s (removed or misspelt; '
                          'tools/build.py --help lists the options as --names, a recipe names them with '
                          'underscores)' % (document['name'], ', '.join(unknown)))
    missing = []
    paths = path_dests(parser)
    pinned = {(item['option'], item['path']) for item in document['inputs']}
    for dest, value in options.items():
        for path in file_values(dest, value, paths):
            if (dest, path) not in pinned:
                missing.append('%s %s' % (dest, path))
    if missing:
        raise RecipeError('recipe %s: files with no SHA-256 in "inputs": %s (each needs {option, role, path, '
                          'sha256}; --save-recipe writes them)' % (document['name'], ', '.join(missing)))
    if explicit is None:
        explicit = given(factory, argv)
    if check_files:
        record['inputs'], options = check_inputs(document, options, set(explicit), remap, base=Path.cwd())
    values = parsed_options(factory, options)
    for dest, value in values.items():
        if dest in explicit:
            mine = explicit[dest]
            if dest in ADDITIVE and isinstance(value, list):
                setattr(args, dest, list(mine or []) + list(value))
                record['added'].append({'option': dest, 'recipe': jsonable(value), 'command_line': jsonable(mine)})
                _note(out, 'Recipe %s: %s; the command line adds %s' % (
                    document['name'], shown(actions[dest], value), shown(actions[dest], mine)))
            elif jsonable(mine) != jsonable(value):
                record['overrides'].append({'option': dest, 'flag': primary_flag(actions[dest]),
                                            'recipe': jsonable(value), 'command_line': jsonable(mine)})
                _note(out, 'recipe says %s, command line says %s' % (shown(actions[dest], value),
                                                                     shown(actions[dest], mine)))
        else:
            setattr(args, dest, value)
    if document['checked_with'] is None:
        _note(out, 'WARNING: recipe %s is unverified (checked_with: null): no passed build has checked it yet'
              % document['name'])
    _note(out, 'Recipe: %s (%s, SHA-256 %s)%s' % (
        document['name'], record['file'], record['sha256'],
        ', checked with v%s by %s' % (document['checked_with']['amiwind_version'], document['checked_with']['run'])
        if document['checked_with'] else ''))
    if preset is not None:
        import miniwind_presets
        args.miniwind_preset_record = miniwind_presets.row_of(document)
    return record


# --------------------------------------------------------------------------
# The recipe of the build being run

def effective_options(factory, args):
    """Every recipe option of ARGS as JSON values (null = the builder's default)."""
    return {dest: jsonable(getattr(args, dest, None)) for dest in sorted(actions_by_dest(factory()))}


def effective_inputs(factory, options, recipe_inputs=(), base=None):
    """Input records of the files OPTIONS names (role from the recipe where it pinned the same path)."""
    paths = path_dests(factory())
    roles = {(item['option'], item['path']): item for item in recipe_inputs or []}
    found = []
    for dest, value in sorted(options.items()):
        for path in file_values(dest, value, paths):
            item = roles.get((dest, path)) or {}
            role = item.get('role') or INPUT_ROLES.get(dest, dest.replace('_', '-'))
            if any(row['role'] == role for row in found):
                role = '%s-%d' % (role, sum(row['option'] == dest for row in found) + 1)
            target = Path(path) if Path(path).is_absolute() or base is None else Path(base) / path
            if not target.exists():
                raise RecipeError('cannot pin input %s (%s): not found' % (role, path))
            sha, kind = content_sha256(target)
            row = {'option': dest, 'role': role, 'path': path, 'sha256': sha, 'kind': kind}
            if item.get('how'):
                row['how'] = item['how']
            found.append(row)
    return found


def effective_sha256(options, inputs):
    """SHA-256 of what a build is made from: the options and the input hashes (not names, dates or checks)."""
    return hashlib.sha256(canonical({'options': options, 'inputs': [
        {'option': row['option'], 'sha256': row['sha256']} for row in inputs]}).encode('utf-8')).hexdigest()


def effective_document(factory, options, version, chim_version, commit, name=None, description=None, run=None,
                       result=None, recipe_inputs=(), base=None, inputs=None):
    """The recipe of a build: OPTIONS (effective_options, taken before the build-type rules fill in their own
    values), the input SHA-256s, and the builder that wrote it. Unverified until the master builder checks it in."""
    if inputs is None:
        inputs = effective_inputs(factory, options, recipe_inputs, base=base)
    return {'schema': SCHEMA,
            'name': name or 'build',
            'description': description or 'The options of one build, written by tools/build.py --save-recipe',
            'options': dict(options), 'inputs': [dict(row) for row in inputs],
            'written_with': {'amiwind_version': version, 'chim_version': chim_version,
                             'builder_commit': commit or 'nogit', 'date': stamp(), 'run': run, 'result': result},
            'checked_with': None, 'status': 'unverified'}


def mark_checked(document, version, chim_version, commit, run, result_sha256, date=None):
    """The recipe with checked_with filled in (the master builder, after a passed build)."""
    document = dict(document)
    document['checked_with'] = {'amiwind_version': version, 'chim_version': chim_version,
                                'builder_commit': commit, 'run': run, 'date': date or stamp(),
                                'result_sha256': result_sha256}
    document['status'] = 'verified'
    return document


def image_record(record, effective, run):
    """The compact record the image step writes into image/build.json (build_recipe)."""
    recipe = record or {}
    return {'name': recipe.get('name'), 'sha256': recipe.get('sha256'), 'status': recipe.get('status'),
            'checked_with': recipe.get('checked_with'), 'effective_sha256': effective, 'run': run,
            'overrides': len(recipe.get('overrides') or [])}


# --------------------------------------------------------------------------
# Command line: check recipes, write one from flags, show option changes

def _factory():
    sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
    import build
    return build.parser, build.VERSION


def main(argv=None):
    top = argparse.ArgumentParser(prog='build_recipe.py', description=__doc__.split('\n\n')[0])
    sub = top.add_subparsers(dest='command', required=True)
    check = sub.add_parser('check', help='check recipes against this builder (options, versions; --inputs: files)')
    check.add_argument('recipes', nargs='+', type=Path)
    check.add_argument('--inputs', action='store_true', help='also check every input file\'s SHA-256')
    flags = sub.add_parser('from-flags', help='print the recipe of a command line (tools/build.py options)')
    flags.add_argument('--name', default='build')
    flags.add_argument('--description')
    flags.add_argument('flags', nargs=argparse.REMAINDER, help='-- then the build options')
    changes = sub.add_parser('changes', help='options whose meaning or default changed')
    changes.add_argument('--since', help='an AmiWind version (default: every change)')
    sub.add_parser('snapshot', help='print the "current" block of config/option-changes.json for this builder')
    a = top.parse_args(argv)
    factory, version = _factory()
    if a.command == 'check':
        failed = 0
        for path in a.recipes:
            args = factory().parse_args(['--recipe', str(path)])
            try:
                record = configure(factory, args, ['--recipe', str(path)], version, check_files=a.inputs)
            except (RecipeError, ValueError) as exc:
                print('%s: REFUSED: %s' % (path, exc))
                failed += 1
                continue
            document = read(path)[0]
            print('%s: ok (%s, %d options, %d inputs)' % (path, record['relation'], len(document['options']),
                                                           len(document['inputs'])))
        return 1 if failed else 0
    if a.command == 'from-flags':
        words = a.flags[1:] if a.flags[:1] == ['--'] else a.flags
        args = factory().parse_args(words)
        import run_name
        commit, _ = run_name.source_commit(ROOT)
        from chim import CHIM_VERSION
        document = effective_document(factory, effective_options(factory, args), version, CHIM_VERSION, commit,
                                      a.name, a.description, base=Path.cwd())
        document['written_with']['result'] = None
        print(json.dumps(document, indent=2, ensure_ascii=False))
        return 0
    if a.command == 'changes':
        rows = load_changes()['changes']
        if a.since:
            rows = changes_between(a.since, version)
        for row in rows:
            print(change_line(row))
        return 0
    print(json.dumps(snapshot(factory), indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
