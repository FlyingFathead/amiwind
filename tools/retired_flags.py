# SPDX-License-Identifier: GPL-3.0-only
"""Builder flags and values retired since CHIM v0.1.0 (BUILD-LEGACY-CHAIN-DEFAULT-36).

A retired flag selects an older method that is kept only for historical regression
tests (nothing is deleted: the method stays in the source and selectable). In
developer mode (tools/build.py --developer-mode, which every development, release
candidate and final build uses) a retired flag stops the build before any stage
unless it is named with --override NAME. Outside developer mode it is accepted with
a loud warning. Every use is recorded in build-state.json, build-summary.json, the
end-of-build summary and the image receipt (image/build.json retired_flags_used).

Light module: no third-party imports (the parser and the tests read it).
"""

RETIRED_SINCE = 'CHIM v0.1.0'
# The Vivec district areas (one CHIM frame per canton; the Arena-only frame of Vivec stage A): replaced by all of
# Vivec in one CHIM frame, vivec_city (project decision 2026-10-11 09:55 +0300). Kept selectable for A/B regression
# tests (DON'T DELETE ANY METHOD), refused like the other retired options.
VIVEC_DISTRICTS = ('vivec_arena', 'vivec_foreign', 'vivec_hlaalu', 'vivec_redoran', 'vivec_telvanni', 'vivec_temple',
                   'vivec_delyn', 'vivec_olms')
HELP_PREFIX = 'RETIRED - DO NOT USE except for antiquated regression testing'

# name (the --override value), the flag as written, the argparse dest, the value that is
# retired (None = any use), why, and the project decision it comes from.
RETIRED = (
    {'name': 'legacy-area', 'flag': '--legacy-area', 'dest': 'legacy_areas', 'value': None,
     'replacement': 'the CHIM-native town (default: --chim-native-towns on)',
     'why': 'builds a CHIM town through the legacy region-map chain (CHIM-LEGACY-CHAIN-33)',
     'source': 'project decision 2026-10-09 (legacy Balmora disabled from builds by default) and '
               '2026-10-10 (CHIM-native areas by default; retired flags stop developer-mode builds)'},
    {'name': 'chim-native-towns-off', 'flag': '--chim-native-towns off', 'dest': 'chim_native_towns', 'value': 'off',
     'replacement': '--chim-native-towns on (the default)',
     'why': 'prepares every CHIM town other than Seyda Neen through its legacy region-map chain',
     'source': 'project decision 2026-10-10 (CHIM-native areas by default; BUILD-LEGACY-CHAIN-DEFAULT-36)'},
    {'name': 'vivec-districts', 'flag': '--chim-area/--miniwind-town/--extra-town <Vivec district>',
     'dest': 'chim_areas', 'dests': ('chim_areas', 'miniwind_town', 'extra_town'), 'value': None,
     'contains': VIVEC_DISTRICTS,
     'replacement': 'vivec_city (all of Vivec in one CHIM frame, the default; --miniwind-preset vivec-city-chim)',
     'why': 'builds a Vivec district frame (the Arena-only frame of stage A or another canton) instead of the '
            'whole city in one frame',
     'source': 'project decision 2026-10-11 09:55 +0300 (whole-city Vivec replaces the district areas by default; '
               'everything else behind legacy/debug settings)'},
    {'name': 'seyda-recorded', 'flag': '--seyda-recorded', 'dest': 'seyda_recorded', 'value': None,
     'replacement': 'Seyda Neen converted from the game data (the default)',
     'why': 'ships the recorded v0.0.31 Seyda Neen region maps: a legacy town chain (NOT RECOMMENDED since v0.0.31)',
     'source': 'project decision 2026-10-10 (rules consolidation item 8: legacy only for A/B regression tests)'},
    {'name': 'seyda-scene-compiled', 'flag': '--seyda-scene-source compiled', 'dest': 'seyda_scene_source',
     'value': 'compiled',
     'replacement': 'the source-only Seyda Neen scene carrier (the default for a CHIM-native Seyda Neen)',
     'why': 'compiles the complete Seyda Neen town to BSP29 for a CHIM-native Seyda Neen, whose cell-aligned frame '
            'exceeds the BSP29 node limit (BUILD-SEYDA-HULL2-32)',
     'source': 'owner goal 2026-10-15 (the Seyda Neen frame stays cell-aligned; the whole area on CHIM without a '
               'BSP29 compile of the widened box)'},
)
NAMES = tuple(row['name'] for row in RETIRED)


def vivec_help():
    """The retired part of the help of --chim-area, --miniwind-town and --extra-town (the Vivec district areas)."""
    return (HELP_PREFIX + ': the Vivec district areas (' + ', '.join(VIVEC_DISTRICTS) + '); all of Vivec is one '
            'CHIM frame, vivec_city (--override vivec-districts)')


def help_text(text):
    """The --help text of a retired flag: always starts with HELP_PREFIX."""
    return HELP_PREFIX + ' (retired since ' + RETIRED_SINCE + '): ' + text


def used(args):
    """The retired rows this command line uses, each with the value given."""
    rows = []
    for row in RETIRED:
        for dest in row.get('dests', (row['dest'],)):
            value = getattr(args, dest, None)
            hit, shown = matches(row, value)
            if hit:
                rows.append(dict(row, given=shown))
                break
    return rows


def matches(row, value):
    """(hit, shown value) of one option value against a retired row: any use (value None), the retired value,
    or (contains) any of the retired values in a list or single value."""
    values = list(value) if isinstance(value, (list, tuple)) else ([value] if value else [])
    if row.get('contains'):
        hits = [v for v in values if v in row['contains']]
        return bool(hits), ', '.join(hits)
    if row['value'] is None:
        hit = bool(value)
    else:
        hit = value == row['value']
    return hit, ', '.join(value) if isinstance(value, (list, tuple)) else str(value)


def error_message(row):
    return ('ERROR: ' + row['flag'] + ' has been disabled since ' + RETIRED_SINCE + ' in development mode. '
            'Override only if sure / for historical regression tests: --override ' + row['name'])


def warning_message(row):
    return ('WARNING: DO NOT USE ' + row['flag'] + ' EXCEPT FOR ANTIQUATED REGRESSION PURPOSES '
            '(retired since ' + RETIRED_SINCE + ')')


def check(args):
    """(record, errors, warnings). record is the list stored in every receipt (empty when no
    retired flag is used); errors stop a developer-mode build before any stage."""
    developer = bool(getattr(args, 'developer_mode', False))
    overrides = list(getattr(args, 'override', None) or [])
    unknown = sorted(set(overrides) - set(NAMES))
    errors = ['ERROR: --override ' + name + ': not a retired flag (retired: ' + ', '.join(NAMES) + ')'
              for name in unknown]
    record, warnings = [], []
    for row in used(args):
        overridden = row['name'] in overrides
        record.append({'name': row['name'], 'flag': row['flag'], 'given': row['given'],
                       'retired_since': RETIRED_SINCE, 'developer_mode': developer,
                       'overridden': overridden, 'why': row['why'],
                       'warning': 'DO NOT USE EXCEPT FOR ANTIQUATED REGRESSION PURPOSES'})
        if developer and not overridden:
            errors.append(error_message(row))
        else:
            warnings.append(warning_message(row) + (' [--override ' + row['name'] + ']' if overridden else ''))
    return record, errors, warnings


def summary_line(record):
    """'RETIRED FLAGS USED: ...' for the start banner and the end-of-build summary, or None."""
    if not record:
        return None
    return ('RETIRED FLAGS USED: ' + '; '.join(
        row['flag'] + (' ' + row['given'] if row['given'] not in ('', 'True', row['flag'].split()[-1]) else '')
        + (' (overridden)' if row['overridden'] else '') for row in record)
        + ' - WARNING: DO NOT USE EXCEPT FOR ANTIQUATED REGRESSION PURPOSES')


def image_option(record):
    """The image step's --retired-flags-used value (recorded in image/build.json), or None."""
    line = summary_line(record)
    return line[len('RETIRED FLAGS USED: '):] if line else None
