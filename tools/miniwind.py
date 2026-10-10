# SPDX-License-Identifier: GPL-3.0-only
"""AmiWind "MiniWind" Playtester Build: a quick partial-area test build of Balmora on CHIM.

tools/build.py --miniwind selects this build type (docs/MINIWIND_PLAYTESTER.md).
This module is the one place that says what the profile is: its scopes
(--miniwind-scope full: the Balmora exterior and interiors; exterior: the
Balmora exterior only), the stages each leaves out, the feature list it
generates from the stages it runs, the boot notice data file the engine reads
(miniwind.txt), the startup screen lines, the maps the image keeps and how the
image and receipts are marked.

A MiniWind build is a private -devN test only, never a release candidate or a
final: tools/build.py refuses it for any other VERSION
(project_version.require_private_test_version), and its image, receipts and
build summary say PARTIAL-AREA test.
"""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

NAME = 'AmiWind "MiniWind" Playtester Build'
PARTIAL_AREA = 'PARTIAL-AREA test build: Balmora only; not a release'
OPTION = '--miniwind'
DESCRIPTION_OPTION = '--miniwind-description'
# Scopes: full (the default, the locked spec: the Balmora exterior on CHIM and
# the Balmora interiors) and exterior (the leanest test build: the Balmora
# exterior on CHIM only; every door says "Area unavailable").
SCOPE_OPTION = '--miniwind-scope'
from miniwind_plan import SCOPES, DEFAULT_SCOPE  # noqa: E402
SCOPE_PARTIAL_AREA = {'full': PARTIAL_AREA,
                      'exterior': 'PARTIAL-AREA test build: Balmora exterior only; not a release'}
# The exterior scope's label: in the run folder and HDF names, the receipts, the
# build summary and the boot notice. Every scope leaves the NPC gallery out.
QUICK_LABEL = 'quick playtest, no NPC gallery'
QUICK_SLUG = 'quick-playtest-no-NPC-gallery'
SCOPE_LABEL = {'full': None, 'exterior': QUICK_LABEL}
# The town the build holds, its CHIM area and where a new game starts: Balmora by
# default; --miniwind-town picks another town table row (a sandbox of that town on
# CHIM: its exterior frame, its residents and interiors). Seyda Neen needs the
# recorded maps and is not a MiniWind town.
TOWN = 'balmora'
CHIM_AREAS = ('balmora',)
TOWN_OPTION = '--miniwind-town'
NOT_TOWNS = ('seyda',)
# DEBUG ONLY builds (--miniwind-debug): a private debugging sandbox, not a playtest.
# The notice, startup screen, marker, HDF and run names say so, and only such a build
# may carry debugging settings a playtest never has (a stated closer view).
DEBUG_OPTION = '--miniwind-debug'
DEBUG_TITLE = 'DEBUG ONLY: MINIWIND DEBUG BUILD, NOT A PLAYTEST'
DEBUG_LOGO_TITLE = 'MiniWind DEBUG ONLY'
DEBUG_SLUG = 'DEBUG-ONLY'

# Boot notice: the engine reads DATA_FILE (id1/miniwind.txt) and shows the two
# lines when the game starts. Normal builds have no such file and show nothing.
DATA_FILE = 'miniwind.txt'
DATA_MAGIC = 'AWMW1'
NOTICE_TITLE = 'ATTENTION: THIS IS A MINIWIND PLAYTEST BUILD'
FEATURES_PREFIX = 'FEATURES ONLY: '
# Engine buffers (engine/aga/src/aw_miniwind.h): one byte for the terminator.
TOWN_CHARS, TITLE_CHARS, FEATURES_CHARS = 15, 79, 511
# The optional quick-start lines of a direct start (aw_miniwind.h AW_MINIWIND_START/CHARACTER).
START_CHARS, CHARACTER_CHARS = 95, 127
# The optional main menu header line (aw_miniwind.h AW_MINIWIND_HEADER): "MINIWIND TEST UNIT: <description>"
# for MiniWind, "QUICK TEST BUILD: <scene>" for another direct start. The title screen wraps it to at most
# HEADER_LINES lines of HEADER_WIDTH pixels in the game font and ends a longer text with "..." (aw_menu.c).
HEADER_CHARS = 95
# Console commands a MiniWind sandbox runs once on arrival (miniwind.txt "boot"; aw_miniwind.c AW_MINIWIND_BOOT - 1):
# debug commands only (each starts with "dbg "), separated by ";".
BOOT_CHARS = 159


def boot_line(commands):
    """The boot line for a list of console commands, or None for none; ValueError for anything else."""
    commands = [" ".join(c.split()) for c in (commands or [])]
    if not commands:
        return None
    for c in commands:
        if not c.startswith("dbg ") or ";" in c or '"' in c or not printable(c):
            raise ValueError("MiniWind boot command must be a dbg command without ; or quotes: %r" % c)
    line = ";".join(commands)
    if len(line) > BOOT_CHARS:
        raise ValueError("MiniWind boot commands exceed %d characters" % BOOT_CHARS)
    return line
HEADER_PREFIX = 'MINIWIND TEST UNIT: '
HEADER_LINES, HEADER_WIDTH = 2, 300

# Startup screen lines under the AmiWind logo (tools/prepare_logo.py), in the
# game font. Under them the engine draws PROMPT in the console font at PROMPT_Y
# and waits for Enter (engine/aga/src/aw_movie.c, aw_miniwind.h).
LOGO_TITLE = 'MiniWind Playtest'
# The version line's "CHIM v<CHIM_VERSION>" is drawn in the console font (the
# prompt's font), the rest of the line in the game font: Magic Cards' capital H
# is an uncial h, so "CHIM" would read "ChIM" (owner decision). The font names
# are tools/prepare_logo.py's GAME_FONT and CONSOLE_FONT (not imported here: this
# module stays free of the image tools).
GAME_FONT, CONSOLE_FONT = 'game', 'console'
SCENE_PREFIX = 'Scene: '
DESCRIPTION_LINES = 2
# Early bound for --miniwind-description (with its prefix), checked before any
# stage runs; the image step wraps the text with the game font itself.
DESCRIPTION_CHARS = 72
PROMPT = 'Press ENTER to start'
PROMPT_Y = 184

# Image marking: a file at the boot volume's root and a tag in the HDF name.
MARKER_FILE = 'PARTIAL-AREA-TEST.txt'
HDF_TAG = '-MiniWind-PARTIAL-AREA'

# The stage table (what the plan leaves out, the dependency changes) lives in
# tools/miniwind_plan.py, which the stage scheduler imports (pure data); re-exported here.
from miniwind_plan import (OMITTED, EXTRA_TOWN_REASON, SCOPE_OMITTED,  # noqa: E402,F401
                           DEPENDENCY_OVERRIDES, IMAGE_AFTER)
# The reason recorded for every map the image step prunes (miniwind-prune.json).
NOT_BUILT = 'not built (MiniWind)'

# The feature list, in display order: each label comes from the stage that
# builds it, so the notice names only what the plan actually built.
FEATURES = (
    ('chim', 'Balmora exterior (CHIM)'),
    ('balmora-interiors', 'Balmora interiors'),
    ('balmora', 'Balmora residents'),
    ('harvest', 'harvestable plants'),
    ('hand-catalog', 'per-race hands'),
    ('door-audio', 'door sounds'),
    ('reading', 'books'),
    ('music', 'music'),
    ('media', 'sound effects and voices'),
)


def check_town(town, root=None):
    """The --miniwind-town value, checked: a town table row (config/towns.json) other than Seyda Neen."""
    from town_config import runtime_towns
    names = [t['name'] for t in runtime_towns(root)]
    if town not in names or town in NOT_TOWNS:
        raise ValueError('%s must be one of %s, not %r' % (
            TOWN_OPTION, ', '.join(n for n in names if n not in NOT_TOWNS), town))
    return town


def town_title(town, root=None):
    from town_config import runtime_towns
    return next(t['title'] for t in runtime_towns(root) if t['name'] == town)


def check_scope(scope):
    """The --miniwind-scope value, checked: one of SCOPES."""
    if scope not in SCOPES:
        raise ValueError('%s must be one of %s, not %r' % (SCOPE_OPTION, ', '.join(SCOPES), scope))
    return scope


def partial_area(scope=DEFAULT_SCOPE, town=TOWN):
    if town == TOWN:
        return SCOPE_PARTIAL_AREA[check_scope(scope)]
    return 'PARTIAL-AREA test build: %s%s only; not a release' % (
        town_title(town), ' exterior' if check_scope(scope) == 'exterior' else '')


def label(scope=DEFAULT_SCOPE):
    """The scope's label ("quick playtest, no NPC gallery"), or None."""
    return SCOPE_LABEL[check_scope(scope)]


def omitted(name, scope=DEFAULT_SCOPE, town=TOWN):
    """The reason a MiniWind plan leaves this stage out, or None when it runs. Another
    town than Balmora runs its own import (town-<town>); Balmora's scene stage still runs
    (the scene chain and the image's Balmora inputs), its interiors do not."""
    if name == 'town-' + town:
        return None
    if name.startswith('town-'):
        return EXTRA_TOWN_REASON if town == TOWN else 'extra town (not %s)' % town
    if town != TOWN and name in ('balmora', 'balmora-interiors'):
        # another town's sandbox holds no Balmora: its scene stage, interiors and their image inputs
        # (the layout repair, the night-window scenery) are left out with its maps
        return 'Balmora %s (%s %s)' % ('interiors' if name == 'balmora-interiors' else 'scene', TOWN_OPTION, town)
    return OMITTED.get(name) or SCOPE_OMITTED[check_scope(scope)].get(name)


def plan(steps, scope=DEFAULT_SCOPE, town=TOWN):
    """(the MiniWind stage plan, {left-out stage: reason}) from the normal plan's steps."""
    kept, left_out = [], {}
    for name, command in steps:
        reason = omitted(name, scope, town)
        if reason:
            left_out[name] = reason
        else:
            kept.append((name, command))
    return kept, left_out


# Stages that build the same feature another way: the legacy Balmora chain (--legacy-area balmora)
# makes the residents the chim-town stage makes by default (CHIM-LEGACY-CHAIN-33).
FEATURE_ALIASES = {'chim-town-balmora': 'balmora'}


def features(stage_names, town=TOWN, scope=DEFAULT_SCOPE):
    """The feature labels of the stages a plan runs, in display order. Another town than
    Balmora: its exterior on CHIM and its town stage (the chim-town stage: residents; the
    legacy import, --legacy-area: residents and, in the full scope, interiors) take
    Balmora's labels."""
    names = {FEATURE_ALIASES.get(name, name) for name in stage_names}
    if town == TOWN:
        return [label for stage, label in FEATURES if stage in names]
    title = town_title(town)
    table = [('chim', title + ' exterior (CHIM)'),
             ('chim-town-' + town, title + ' residents'),
             ('town-' + town, title + (' residents' if check_scope(scope) == 'exterior' else ' residents and interiors')),
             *((s, l) for s, l in FEATURES if s not in ('chim', 'balmora-interiors', 'balmora', 'chim-town-balmora'))]
    return [label for stage, label in table if stage in set(stage_names)]


def features_line(stage_names, scope=DEFAULT_SCOPE, town=TOWN):
    """The boot notice's second line: the generated feature list, then the scope's label."""
    tag = label(scope)
    return FEATURES_PREFIX + ', '.join(features(stage_names, town, scope)) + ('; ' + tag if tag else '')


def notice_title(debug=False):
    return DEBUG_TITLE if debug else NOTICE_TITLE


def printable(text):
    return all(' ' <= c <= '~' for c in text)


def check_description(text):
    """The --miniwind-description text, checked before any stage runs; None when not given.

    Printable ASCII only (characters the game font has), one line of input, at
    most DESCRIPTION_CHARS characters with its "Scene: " prefix (the image
    step wraps it to at most DESCRIPTION_LINES lines with the game font)."""
    if text is None:
        return None
    if not isinstance(text, str) or not text.strip():
        raise ValueError(DESCRIPTION_OPTION + ' is empty; leave it out to omit the "Scene:" line')
    bad = sorted({c for c in text if not (' ' <= c <= '~')})
    if bad:
        raise ValueError(DESCRIPTION_OPTION + ': only printable ASCII characters the game font has; refused: '
                         + ', '.join(repr(c) for c in bad))
    text = ' '.join(text.split())
    if len(SCENE_PREFIX + text) > DESCRIPTION_CHARS:
        raise ValueError('%s is too long: "%s%s" has %d characters; at most %d fit the startup screen in %d lines'
                         % (DESCRIPTION_OPTION, SCENE_PREFIX, text, len(SCENE_PREFIX + text),
                            DESCRIPTION_CHARS, DESCRIPTION_LINES))
    return text


def wrap(text, measure, width, lines=DESCRIPTION_LINES):
    """Word-wrap text into at most `lines` lines of `width` pixels by measure(line);
    refuses (ValueError) a text that does not fit."""
    out, line = [], ''
    for word in text.split():
        trial = (line + ' ' + word).strip()
        if line and measure(trial) > width:
            out.append(line)
            line = word
        else:
            line = trial
    if line:
        out.append(line)
    if len(out) > lines or any(measure(row) > width for row in out):
        raise ValueError('%s does not fit the startup screen: "%s" needs more than %d lines of %d pixels; '
                         'shorten it' % (DESCRIPTION_OPTION, text, lines, width))
    return out


def version_segments(version, chim_version):
    """Line 3 of the startup screen, from the VERSION and CHIM_VERSION files, as
    (text, font) segments: "AmiWind v<VERSION> / " in the game font and
    "CHIM v<CHIM_VERSION>" in the console font."""
    if not version or not chim_version:
        raise ValueError('The MiniWind version line needs VERSION and CHIM_VERSION')
    return (('AmiWind v%s / ' % version, GAME_FONT), ('CHIM v%s' % chim_version, CONSOLE_FONT))


def version_line(version, chim_version):
    """The plain text of the version line (receipts, docs)."""
    return line_text(version_segments(version, chim_version))


def line_text(line):
    """The plain text of a startup screen line: a string, or (text, font) segments."""
    return line if isinstance(line, str) else ''.join(text for text, _ in line)


def logo_lines(version, chim_version, description=None, measure=len, width=10 ** 9, debug=False):
    """The startup screen's lines under the logo: the build name (DEBUG_LOGO_TITLE for a
    debug build), the version line (segments: its CHIM part in the console font) and, only
    with a description, "Scene: ..." (1-2 lines). The engine draws PROMPT under them
    and waits for Enter."""
    lines = [DEBUG_LOGO_TITLE if debug else LOGO_TITLE, version_segments(version, chim_version)]
    if description:
        lines += wrap(SCENE_PREFIX + check_description(description), measure, width)
    return lines


def header_line(description, prefix=HEADER_PREFIX, fallback='Balmora'):
    """The main menu header of a test build: prefix + the description (or the fallback), cut to HEADER_CHARS."""
    text = prefix + ' '.join((description or fallback).split())
    return text if len(text) <= HEADER_CHARS else text[:HEADER_CHARS - 3].rstrip() + '...'


def header_lines(text, measure, width=HEADER_WIDTH):
    """The title screen's lines for the header, as the engine wraps them (aw_menu.c AW_MenuHeaderLines):
    words to `width` pixels by measure(), at most HEADER_LINES lines; the last line of a longer text keeps
    as many characters as fit with "...". Returns (lines, cut)."""
    lines, rest = [], text.strip()
    while rest and len(lines) < HEADER_LINES:
        if measure(rest) <= width:
            lines.append(rest)
            return lines, False
        if len(lines) == HEADER_LINES - 1:
            cut = len(rest)
            while cut > 0 and measure(rest[:cut] + '...') > width:
                cut -= 1
            lines.append(rest[:cut] + '...')
            return lines, True
        cut = len(rest)
        while cut > 0 and not ((cut == len(rest) or rest[cut] == ' ') and measure(rest[:cut]) <= width):
            cut -= 1
        if cut <= 0:
            cut = len(rest)
            while cut > 1 and measure(rest[:cut]) > width:
                cut -= 1
        lines.append(rest[:cut])
        rest = rest[cut:].lstrip(' ')
    return lines, bool(rest)


def data_file(feature_line, town=TOWN, start=None, character=None, title=None, features_prefix=FEATURES_PREFIX,
              debug=False, header=None, boot=None):
    """The boot notice data file (DATA_FILE), as the engine parses it (aw_miniwind.c).

    title: default the MiniWind notice title (notice_title(debug): DEBUG ONLY sandboxes say so).
    start / character: the optional quick-start lines of a direct start (tools/direct_start.py:
    "town NAME" or "map MAP X Y Z YAW"; "RACE|CLASS|BIRTHSIGN|m or f|NAME"). A direct start in a
    build that is not MiniWind writes the same file with its own title and features line
    (features_prefix None: no FEATURES ONLY prefix)."""
    title = notice_title(debug) if title is None else title
    rows = [('town', town, TOWN_CHARS), ('title', title, TITLE_CHARS), ('features', feature_line, FEATURES_CHARS)]
    if start is not None:
        rows.append(('start', start, START_CHARS))
    if character is not None:
        rows.append(('character', character, CHARACTER_CHARS))
    if header is not None:
        rows.append(('header', header, HEADER_CHARS))
    if boot is not None:
        rows.append(('boot', boot, BOOT_CHARS))
    for key, value, size in rows:
        if not value or len(value) > size or not printable(value):
            raise ValueError('MiniWind %s line must be 1-%d printable ASCII characters: %r' % (key, size, value))
    if not re.fullmatch(r'[a-z0-9_]+', town):
        raise ValueError('MiniWind start town must be a town table name: ' + town)
    if features_prefix and (not feature_line.startswith(features_prefix) or len(feature_line) == len(features_prefix)):
        raise ValueError('MiniWind features line must list what the build holds')
    return (DATA_MAGIC + '\n' + ''.join('%s %s\n' % (key, value) for key, value, _ in rows)).encode('ascii')


def kept_maps(root=None, scope=DEFAULT_SCOPE, town=TOWN, extra=()):
    """(names, region prefix): the maps a MiniWind image ships besides the
    image's own (the CHIM frame map, the torch test map): the town's map,
    its region maps (the CHIM frame map's source and the chim_towns 0 A/B) and,
    in the full scope, its interiors (Balmora: config/balmora_interiors.json;
    another town: its town table interiors)."""
    from town_config import runtime_towns, town_interiors
    root = Path(root) if root else ROOT
    row = next(t for t in runtime_towns(root) if t['name'] == town)
    if check_scope(scope) == 'exterior':
        return {town, *extra}, row['prefix']
    if town == TOWN:
        rooms = json.loads((root / 'config/balmora_interiors.json').read_text(encoding='utf-8'))['scenes']
    else:
        rooms = [r for r in town_interiors(root) if r['town'] == row['id']]
    return {town, *extra, *(room['map'] for room in rooms)}, row['prefix']

# Maps outside Balmora a MiniWind build can ship as its direct start (tools/direct_start.py): the prison
# ship, which the intro stage builds anyway (the opening-ship preset). The Census office never ships.
START_MAPS = ('prison',)


def start_maps(start_map):
    """The extra map a MiniWind image keeps for its direct start: (map,) or ()."""
    return (start_map,) if start_map in START_MAPS else ()


def keep_map(name, kept, prefix):
    return name in kept or bool(re.fullmatch(re.escape(prefix) + r'[0-9]{3}', name))


# The Census office's own files besides its map (tools/prepare_census.py: its actors' models and its
# door table). A MiniWind image never ships the Census map; with --skip-census these leave as well.
CENSUS_FILES = ('doors-census.txt', 'progs/np_census.mdl', 'progs/np_captain.mdl', 'progs/np_hall.mdl')
SKIP_CENSUS = 'census office (--skip-census: the quick character screen replaces it)'


def prune(id1, root=None, scope=DEFAULT_SCOPE, remove_legacy=None, town=TOWN, extra=(),
          census_files=False, chim_town=False):
    """Remove what the MiniWind image does not ship from a staged id1: every map
    outside kept_maps (Seyda Neen, the prison ship, Census, other towns and
    their rooms; in the exterior scope every Balmora interior too). The videos
    stay: the media stage ships all of them and the playvid command plays them.

    remove_legacy: chim.frame_map.remove_legacy_areas, passed by the image step:
    the other towns' legacy exterior maps then leave through the same mechanism
    and row format as a pure CHIM image's (reason NOT_BUILT); every other removed
    map gets a row of that format too (town None). Later, the pure CHIM image
    step removes Balmora's own legacy maps (build.json chim_world.removed_legacy);
    the region tables stay. This module never imports the CHIM tools itself:
    every build stage imports it (build_parallel), and their source fingerprints
    must not take in the engine sources the CHIM tools read (tests/test_build_cache.py).
    extra: maps kept for the direct start (start_maps). census_files: --skip-census also removes
    CENSUS_FILES (rows with reason SKIP_CENSUS).
    chim_town: Balmora is a CHIM town made from the game data (tools/chim_town.py), with no legacy
    town map to require (CHIM-LEGACY-CHAIN-33).
    Returns the receipt record."""
    import hashlib
    from town_config import runtime_towns
    id1 = Path(id1)
    kept, prefix = kept_maps(root, scope, town, extra)
    if not chim_town and not (id1 / 'maps' / (town + '.bsp')).is_file():
        raise ValueError('MiniWind image: the scene stage has no %s map (maps/%s.bsp)' % (town_title(town, root), town))
    rows = (remove_legacy(id1, [t['id'] for t in runtime_towns(root) if t['name'] != town], NOT_BUILT)
            if remove_legacy else [])
    for path in sorted((id1 / 'maps').glob('*.bsp')):
        if not keep_map(path.stem, kept, prefix):
            data = path.read_bytes()
            rows.append({'file': 'maps/' + path.name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                         'town': None, 'reason': NOT_BUILT})
            path.unlink()
    for name in (CENSUS_FILES if census_files else ()):
        path = id1 / name
        if path.is_file():
            data = path.read_bytes()
            rows.append({'file': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                         'town': None, 'reason': SKIP_CENSUS})
            path.unlink()
    rows.sort(key=lambda row: row['file'])
    shipped = sorted(p.name for p in (id1 / 'maps').glob('*.bsp'))
    missing = sorted(name for name in kept if name + '.bsp' not in shipped and not (chim_town and name == town))
    return {'scope': check_scope(scope), 'town': town,
            'maps_removed': [row['file'][5:] for row in rows if row['file'].startswith('maps/')],
            'census_files_removed': [row['file'] for row in rows if row['reason'] == SKIP_CENSUS],
            'bytes_removed': sum(row['bytes'] for row in rows), 'removed': rows,
            'maps_kept': shipped, 'interiors_missing': missing}


def marker_text(version, feature_line, description=None, scope=DEFAULT_SCOPE, town=TOWN, debug=False):
    """The PARTIAL-AREA marker at the boot volume's root."""
    lines = [NAME, 'AmiWind v' + version, partial_area(scope, town), notice_title(debug), feature_line]
    if label(scope):
        lines.append('Scope: %s (%s)' % (scope, label(scope)))
    if description:
        lines.append(SCENE_PREFIX + description)
    lines.append('Built by the repository builder with ' + OPTION + '; see docs/MINIWIND_PLAYTESTER.md.')
    return '\n'.join(lines) + '\n'


def town_slug(town=TOWN):
    """The town in names: nothing for Balmora (names stay as they were), '-<town>' otherwise."""
    return '' if town == TOWN else '-' + town.replace('_', '-')


def hdf_tag(scope=DEFAULT_SCOPE, town=TOWN, debug=False):
    """The tag in the image's HDF names: PARTIAL-AREA, the town (not Balmora), DEBUG-ONLY,
    then the scope's label."""
    return (HDF_TAG + town_slug(town) + ('-' + DEBUG_SLUG if debug else '')
            + ('-' + QUICK_SLUG if label(scope) else ''))


def hdf_name(version, suffix='', scope=DEFAULT_SCOPE, town=TOWN, debug=False):
    return 'AmiWind-v%s%s%s.hdf' % (version, hdf_tag(scope, town, debug), suffix)


def run_name(name, scope=DEFAULT_SCOPE, town=TOWN, debug=False):
    """The default run folder name with the town, DEBUG-ONLY and the scope's label (an explicit
    --name stays as given)."""
    return name + town_slug(town) + ('-' + DEBUG_SLUG if debug else '') + ('-' + QUICK_SLUG if label(scope) else '')


def record(stage_names, left_out, description=None, scope=DEFAULT_SCOPE, town=TOWN, debug=False,
           debug_settings=None):
    """The build_type block of the build receipts (build-state.json, build-summary.json)."""
    return {'name': NAME, 'option': OPTION, 'scope': check_scope(scope), 'label': label(scope),
            'partial_area': partial_area(scope, town), 'town': town,
            'chim_areas': [town], 'notice': [notice_title(debug), features_line(stage_names, scope, town)],
            'features': features(stage_names, town, scope), 'description': description,
            'debug_only': bool(debug), 'debug_settings': dict(debug_settings or {}) if debug else None,
            'stages': list(stage_names), 'left_out': dict(left_out)}
