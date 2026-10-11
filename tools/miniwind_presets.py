# SPDX-License-Identifier: GPL-3.0-only
"""MiniWind test spots: build recipes in config/recipes/miniwind/, one file per spot (NAME.json).

tools/build.py --miniwind-preset NAME (and one generated alias per recipe, --miniwind-NAME) is a MiniWind
playtest build from the recipe config/recipes/miniwind/NAME.json: the same recipe format and the same path as
tools/build.py --recipe FILE (tools/build_recipe.py, docs/BUILD_RECIPES.md); options given on the command line
win, and --exclude adds to the recipe's exclusions. A preset recipe sets:

  miniwind                 true
  miniwind_scope           the MiniWind scope (tools/miniwind.py SCOPES: full, exterior)
  miniwind_description     the startup screen's "Scene:" line (tools/miniwind.py check_description)
  direct_to_game_map       a --direct-to-game-map start point (tools/direct_start.py); left out: the MiniWind
                           town's arrival
  exclude                  quick-test exclusion groups (tools/build_exclusions.py), one comma list
  exclude_unreferenced     --exclude-unreferenced groups ("all" or a comma list); left out: none
  quick_character          a --quick-character RACE,CLASS[,NAME]; left out: the Hors preset
  skip_census              true / false: --skip-census / --no-skip-census; left out: the builder's default
  miniwind_boot            dbg console commands run once on arrival, separated by ";"

The row view of a recipe (row_of: name, description, scope, start, exclude, unreferenced, character,
skip_census, boot_commands) is what build-state.json records as miniwind_preset, exactly as the earlier preset
table (config/miniwind-presets.json, format 1) did; check_row checks it with the options' own parsers and
apply_row is that table's method, kept (tests/test_build_recipe.py proves every preset recipe gives the options
its table row gave). `--miniwind-preset list` prints the presets. A preset whose start is not in the build stops
the build before any stage with the start point's own message (vivec-arena-pit starts inside the Pit, vai000,
which the Arena's chim-rooms stage makes; BUILD-MINIWIND-ARENA-PIT-REFUSED-36). Presets are -devN only, like every MiniWind build. Add a spot: add a recipe file.
"""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
TABLE = 'config/recipes/miniwind'
OPTION = '--miniwind-preset'
KEYS = ('name', 'description', 'scope', 'start', 'exclude', 'unreferenced', 'character', 'skip_census',
        'boot_commands')
# The recipe options a preset may set (row field -> recipe option).
FIELDS = {'scope': 'miniwind_scope', 'description': 'miniwind_description', 'start': 'direct_to_game_map',
          'exclude': 'exclude', 'unreferenced': 'exclude_unreferenced', 'character': 'quick_character',
          'skip_census': 'skip_census', 'boot_commands': 'miniwind_boot'}


def recipe_files(root=ROOT):
    return sorted((Path(root) / TABLE).glob('*.json'))


def row_of(document):
    """The preset row of a preset recipe (the earlier table's fields)."""
    options = document['options']
    unknown = sorted(set(options) - set(FIELDS.values()) - {'miniwind'})
    if options.get('miniwind') is not True or unknown:
        raise ValueError('%s: preset %s: a preset recipe sets miniwind true and only %s%s'
                         % (TABLE, document.get('name'), ', '.join(sorted(FIELDS.values())),
                            ' (not ' + ', '.join(unknown) + ')' if unknown else ''))
    exclude = [group for entry in options.get('exclude') or [] for group in str(entry).split(',') if group]
    boot = options.get('miniwind_boot')
    return {'name': document['name'], 'description': options.get('miniwind_description'),
            'scope': options.get('miniwind_scope'), 'start': options.get('direct_to_game_map'),
            'exclude': exclude, 'unreferenced': options.get('exclude_unreferenced'),
            'character': options.get('quick_character'), 'skip_census': options.get('skip_census'),
            'boot_commands': boot.split(';') if boot else []}


def recipe_of(row):
    """The preset recipe of a row of the earlier table (config/miniwind-presets.json, format 1)."""
    options = {'miniwind': True, 'miniwind_scope': row['scope'], 'miniwind_description': row['description']}
    if row['start'] is not None:
        options['direct_to_game_map'] = row['start']
    if row['exclude']:
        options['exclude'] = [','.join(row['exclude'])]
    for field in ('unreferenced', 'character', 'skip_census'):
        if row[field] is not None:
            options[FIELDS[field]] = row[field]
    if row['boot_commands']:
        options['miniwind_boot'] = ';'.join(row['boot_commands'])
    return {'schema': 'build-recipe-1', 'name': row['name'],
            'description': 'MiniWind preset --miniwind-%s: %s' % (row['name'], row['description']),
            'options': options, 'inputs': [], 'written_with': None, 'checked_with': None, 'status': 'unverified'}


def table(root=ROOT):
    """Every preset as a row, by name (read only, without the option checks: see presets())."""
    rows = []
    for path in recipe_files(root):
        document = json.loads(path.read_text(encoding='utf-8'))
        if path.stem != document.get('name'):
            raise ValueError('%s: the file name must be the recipe name (%s.json)' % (path, document.get('name')))
        rows.append(row_of(document))
    return rows


def check_row(row, root=ROOT):
    """A row, checked with the same parsers the options use; returns it."""
    import direct_start
    import miniwind
    from build_exclusions import parse as parse_exclusions
    from content_closure import parse_groups
    if sorted(row) != sorted(KEYS):
        raise ValueError('%s: preset %r needs exactly the keys %s' % (TABLE, row.get('name'), ', '.join(KEYS)))
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', row['name'] or '') or len(row['name']) > 32:
        raise ValueError('%s: preset name %r: lower case letters, digits and single hyphens' % (TABLE, row['name']))
    miniwind.check_description(row['description'])
    miniwind.check_scope(row['scope'])
    if row['start'] is not None:
        direct_start.parse(row['start'], root)
    groups = parse_exclusions(row['exclude'] or [])
    if 'unreferenced' in groups:
        raise ValueError('%s: preset %s: give the reference closure in "unreferenced", not in "exclude"'
                         % (TABLE, row['name']))
    if row['unreferenced'] is not None:
        parse_groups(row['unreferenced'])
    if row['character'] is not None:
        direct_start.parse_character(row['character'])
    if not isinstance(row['boot_commands'], list):
        raise ValueError('%s: preset %r: boot_commands must be a list' % (TABLE, row['name']))
    miniwind.boot_line(row['boot_commands'])
    if row['skip_census'] not in (True, False, None):
        raise ValueError('%s: preset %s: skip_census is true, false or null' % (TABLE, row['name']))
    return row


def presets(root=ROOT):
    import build_recipe
    rows = []
    for path in recipe_files(root):
        build_recipe.read(path)  # the recipe schema
        rows.append(check_row(row_of(json.loads(path.read_text(encoding='utf-8'))), root))
    names = [row['name'] for row in rows]
    if len(set(names)) != len(names):
        raise ValueError(TABLE + ': preset names must be unique')
    return rows


def find(name, root=ROOT):
    rows = {row['name']: row for row in presets(root)}
    if name not in rows:
        raise ValueError('%s %s: unknown preset; presets: %s (or %s list)'
                         % (OPTION, name, ', '.join(rows), OPTION))
    return rows[name]


def alias(name):
    return '--miniwind-' + name


def add_options(parser, root=ROOT):
    """--miniwind-preset NAME|list and one --miniwind-NAME per recipe (same destination)."""
    rows = table(root)
    parser.add_argument(OPTION, dest='miniwind_preset', metavar='NAME',
                        help='MiniWind test spot, the recipe ' + TABLE + '/NAME.json (implies --miniwind): '
                             + ', '.join(row['name'] for row in rows) + '; "list" prints them. '
                             'See docs/chim/build_guide/MINIWIND.md and docs/BUILD_RECIPES.md')
    for row in rows:
        parser.add_argument(alias(row['name']), dest='miniwind_preset', action='store_const', const=row['name'],
                            help='Same as %s %s: %s' % (OPTION, row['name'], row['description']))


def listing(root=ROOT):
    lines = []
    for row in presets(root):
        lines.append('%s (%s): %s' % (alias(row['name']), OPTION + ' ' + row['name'], row['description']))
        lines.append('  scope %s; start %s; exclude %s; unreferenced %s; character %s; quick character screen %s'
                     % (row['scope'], row['start'] or 'the MiniWind town', ', '.join(row['exclude']) or 'nothing',
                        row['unreferenced'] or 'none', row['character'] or 'Hors preset',
                        {True: 'on', False: 'off', None: 'default'}[row['skip_census']]))
        lines.append('  recipe %s/%s.json' % (TABLE, row['name']))
    return '\n'.join(lines)


def apply(args, argv=None, out=None):
    """Fold the preset into the options through its recipe (tools/build_recipe.py; options given on ARGV win;
    without ARGV, every option that differs from its default counts as given). Returns the row."""
    import io
    import build
    import build_recipe
    name = getattr(args, 'miniwind_preset', None)
    if name is None:
        return None
    explicit = None
    if argv is None:
        parser = build.parser()
        explicit = {dest: value for dest, value in vars(args).items()
                    if dest in build_recipe.actions_by_dest(parser) and value != parser.get_default(dest)}
    build_recipe.configure(build.parser, args, argv or [], None, out=out or io.StringIO(), explicit=explicit)
    return args.miniwind_preset_record


def apply_row(args, row):
    """The earlier table's method (format 1 rows): fold ROW into the options, explicit options win. Kept for
    format-1 rows and as the reference the preset recipes are tested against."""
    args.miniwind = True
    if getattr(args, 'miniwind_scope', None) is None:
        args.miniwind_scope = row['scope']
    if getattr(args, 'miniwind_description', None) is None:
        args.miniwind_description = row['description']
    if getattr(args, 'direct_to_game_map', None) is None and row['start'] is not None:
        args.direct_to_game_map = row['start']
    if row['exclude']:
        args.exclude = list(getattr(args, 'exclude', None) or []) + [','.join(row['exclude'])]
    if getattr(args, 'exclude_unreferenced', None) is None and row['unreferenced'] is not None:
        args.exclude_unreferenced = row['unreferenced']
    if getattr(args, 'quick_character', None) is None and row['character'] is not None:
        args.quick_character = row['character']
    if getattr(args, 'skip_census', None) is None and row['skip_census'] is not None:
        args.skip_census = row['skip_census']
    if getattr(args, 'miniwind_boot', None) is None and row['boot_commands']:
        args.miniwind_boot = ';'.join(row['boot_commands'])
    args.miniwind_preset_record = dict(row)
    return row
