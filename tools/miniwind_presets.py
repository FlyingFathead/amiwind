# SPDX-License-Identifier: GPL-3.0-only
"""MiniWind test spots: config/miniwind-presets.json, one row per spot.

tools/build.py --miniwind-preset NAME (and one generated alias per row,
--miniwind-NAME) is a MiniWind playtest build with the row's settings:

  name          the preset's name (lower case, digits, hyphens): the alias --miniwind-NAME
  description   the startup screen's "Scene:" line (tools/miniwind.py check_description)
  scope         the MiniWind scope (tools/miniwind.py SCOPES: full, exterior)
  start         a --direct-to-game-map start point (tools/direct_start.py), or null for the
                MiniWind town's arrival
  exclude       quick-test exclusion groups (tools/build_exclusions.py)
  unreferenced  --exclude-unreferenced groups ("all", a comma list, or null for none)
  character     a --quick-character RACE,CLASS[,NAME], or null for the Hors preset
  skip_census   true / false: --skip-census / --no-skip-census (the quick character screen on
                arrival); null: the builder's default (on, unless a character is given)

`--miniwind-preset list` prints the table. A preset whose start is not in the
build (the Vivec Arena interiors are not converted yet) stops the build before
any stage with the start point's own message. Presets are -devN only, like
every MiniWind build. Add a spot: add a row; tests/test_miniwind_presets.py
checks every row parses.
"""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
TABLE = 'config/miniwind-presets.json'
OPTION = '--miniwind-preset'
KEYS = ('name', 'description', 'scope', 'start', 'exclude', 'unreferenced', 'character', 'skip_census',
        'boot_commands')


def table(root=ROOT):
    data = json.loads((Path(root) / TABLE).read_text(encoding='utf-8'))
    if data.get('format') != 1:
        raise ValueError(TABLE + ': unknown format')
    return data['presets']


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
    import miniwind
    if not isinstance(row['boot_commands'], list):
        raise ValueError('%s: preset %r: boot_commands must be a list' % (TABLE, row['name']))
    miniwind.boot_line(row['boot_commands'])
    if row['skip_census'] not in (True, False, None):
        raise ValueError('%s: preset %s: skip_census is true, false or null' % (TABLE, row['name']))
    return row


def presets(root=ROOT):
    rows = [check_row(row, root) for row in table(root)]
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
    """--miniwind-preset NAME|list and one --miniwind-NAME per row (same destination)."""
    rows = table(root)
    parser.add_argument(OPTION, dest='miniwind_preset', metavar='NAME',
                        help='MiniWind test spot from ' + TABLE + ' (implies --miniwind): '
                             + ', '.join(row['name'] for row in rows) + '; "list" prints the table. '
                             'See docs/chim/build_guide/MINIWIND.md')
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
    return '\n'.join(lines)


def apply(args, root=ROOT):
    """Fold the preset into the options (explicit options win where both are given). Returns the row."""
    name = getattr(args, 'miniwind_preset', None)
    if name is None:
        return None
    row = find(name, root)
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
