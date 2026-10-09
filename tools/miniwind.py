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
SCOPES = ('full', 'exterior')
DEFAULT_SCOPE = 'full'
SCOPE_PARTIAL_AREA = {'full': PARTIAL_AREA,
                      'exterior': 'PARTIAL-AREA test build: Balmora exterior only; not a release'}
# The exterior scope's label: in the run folder and HDF names, the receipts, the
# build summary and the boot notice. Every scope leaves the NPC gallery out.
QUICK_LABEL = 'quick playtest, no NPC gallery'
QUICK_SLUG = 'quick-playtest-no-NPC-gallery'
SCOPE_LABEL = {'full': None, 'exterior': QUICK_LABEL}
# The town the build holds, its CHIM area and where a new game starts.
TOWN = 'balmora'
CHIM_AREAS = ('balmora',)

# Boot notice: the engine reads DATA_FILE (id1/miniwind.txt) and shows the two
# lines when the game starts. Normal builds have no such file and show nothing.
DATA_FILE = 'miniwind.txt'
DATA_MAGIC = 'AWMW1'
NOTICE_TITLE = 'ATTENTION: THIS IS A MINIWIND PLAYTEST BUILD'
FEATURES_PREFIX = 'FEATURES ONLY: '
# Engine buffers (engine/aga/src/aw_miniwind.h): one byte for the terminator.
TOWN_CHARS, TITLE_CHARS, FEATURES_CHARS = 15, 79, 511

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

# Stages of the normal plan a MiniWind build leaves out, with the reason.
# Every extra town (town-<id>: the Vivec Arena and --extra-town towns) is left
# out as well. Every other stage of the plan runs unchanged.
OMITTED = {
    'area': 'Seyda Neen rooms and residents',
    'npc-gallery': 'NPC inspection gallery (a debugging browser, not game content)',
    'world-survey': 'open-world survey',
    'world-ui': 'open-world map tiles (the image writes the overview map from the game files)',
    'actor-contact': 'Seyda Neen scene actor audit (the image step keeps its final actor gate)',
    'world-terrain': 'open world: terrain regions',
    'world-scenery-assets': 'open world: rocks and giant mushrooms',
    'world-scenery': 'open world: rocks and giant mushrooms',
    'world-flora-assets': 'world flora (trees and grass need the open-world terrain)',
    'world-flora': 'world flora (trees and grass need the open-world terrain)',
}
EXTRA_TOWN_REASON = 'extra town (not Balmora)'
# The reason recorded for every map the image step prunes (miniwind-prune.json).
NOT_BUILT = 'not built (MiniWind)'
# Stages the exterior scope leaves out as well. The scene chain before Balmora
# (interior, intro, census) stays: the image's boot payload is its tree
# (intro-scene: palette, progs.dat, models, actor poses), census writes the
# palette every later stage reads, and the image step removes their maps.
SCOPE_OMITTED = {
    'full': {},
    'exterior': {
        'balmora-interiors': 'Balmora interiors (--miniwind-scope exterior; their doors say Area unavailable)',
        'door-audio': 'door sounds (--miniwind-scope exterior; every Balmora door leads to a left-out interior)',
    },
}
# Scene stages that change their predecessor's tree: without 'area', Balmora
# follows the census directly (tools/build_parallel.py).
DEPENDENCY_OVERRIDES = {'balmora': ('census',)}
# The image waits for the end of the scene chain: in the normal plan it does so
# through world-terrain (actor-contact, world-ui), which this build leaves out.
IMAGE_AFTER = ('opening-references',)

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


def check_scope(scope):
    """The --miniwind-scope value, checked: one of SCOPES."""
    if scope not in SCOPES:
        raise ValueError('%s must be one of %s, not %r' % (SCOPE_OPTION, ', '.join(SCOPES), scope))
    return scope


def partial_area(scope=DEFAULT_SCOPE):
    return SCOPE_PARTIAL_AREA[check_scope(scope)]


def label(scope=DEFAULT_SCOPE):
    """The scope's label ("quick playtest, no NPC gallery"), or None."""
    return SCOPE_LABEL[check_scope(scope)]


def omitted(name, scope=DEFAULT_SCOPE):
    """The reason a MiniWind plan leaves this stage out, or None when it runs."""
    if name.startswith('town-'):
        return EXTRA_TOWN_REASON
    return OMITTED.get(name) or SCOPE_OMITTED[check_scope(scope)].get(name)


def plan(steps, scope=DEFAULT_SCOPE):
    """(the MiniWind stage plan, {left-out stage: reason}) from the normal plan's steps."""
    kept, left_out = [], {}
    for name, command in steps:
        reason = omitted(name, scope)
        if reason:
            left_out[name] = reason
        else:
            kept.append((name, command))
    return kept, left_out


def features(stage_names):
    """The feature labels of the stages a plan runs, in display order."""
    names = set(stage_names)
    return [label for stage, label in FEATURES if stage in names]


def features_line(stage_names, scope=DEFAULT_SCOPE):
    """The boot notice's second line: the generated feature list, then the scope's label."""
    tag = label(scope)
    return FEATURES_PREFIX + ', '.join(features(stage_names)) + ('; ' + tag if tag else '')


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


def logo_lines(version, chim_version, description=None, measure=len, width=10 ** 9):
    """The startup screen's lines under the logo: the build name, the version
    line (segments: its CHIM part in the console font) and, only with a
    description, "Scene: ..." (1-2 lines). The engine draws PROMPT under them
    and waits for Enter."""
    lines = [LOGO_TITLE, version_segments(version, chim_version)]
    if description:
        lines += wrap(SCENE_PREFIX + check_description(description), measure, width)
    return lines


def data_file(feature_line, town=TOWN):
    """The boot notice data file (DATA_FILE), as the engine parses it (aw_miniwind.c)."""
    rows = (('town', town, TOWN_CHARS), ('title', NOTICE_TITLE, TITLE_CHARS),
            ('features', feature_line, FEATURES_CHARS))
    for key, value, size in rows:
        if not value or len(value) > size or not printable(value):
            raise ValueError('MiniWind %s line must be 1-%d printable ASCII characters: %r' % (key, size, value))
    if not re.fullmatch(r'[a-z0-9_]+', town):
        raise ValueError('MiniWind start town must be a town table name: ' + town)
    if not feature_line.startswith(FEATURES_PREFIX) or len(feature_line) == len(FEATURES_PREFIX):
        raise ValueError('MiniWind features line must list what the build holds')
    return (DATA_MAGIC + '\n' + ''.join('%s %s\n' % (key, value) for key, value, _ in rows)).encode('ascii')


def kept_maps(root=None, scope=DEFAULT_SCOPE):
    """(names, region prefix): the maps a MiniWind image ships besides the
    image's own (the CHIM frame map, the torch test map): Balmora's town map,
    its region maps (the CHIM frame map's source and the chim_towns 0 A/B) and,
    in the full scope, the Balmora interiors (config/balmora_interiors.json)."""
    from town_config import runtime_towns
    root = Path(root) if root else ROOT
    town = next(t for t in runtime_towns(root) if t['name'] == TOWN)
    if check_scope(scope) == 'exterior':
        return {TOWN}, town['prefix']
    rooms = json.loads((root / 'config/balmora_interiors.json').read_text(encoding='utf-8'))['scenes']
    return {TOWN, *(room['map'] for room in rooms)}, town['prefix']


def keep_map(name, kept, prefix):
    return name in kept or bool(re.fullmatch(re.escape(prefix) + r'[0-9]{3}', name))


def prune(id1, root=None, scope=DEFAULT_SCOPE, remove_legacy=None):
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
    Returns the receipt record."""
    import hashlib
    from town_config import runtime_towns
    id1 = Path(id1)
    kept, prefix = kept_maps(root, scope)
    if not (id1 / 'maps' / (TOWN + '.bsp')).is_file():
        raise ValueError('MiniWind image: the scene stage has no Balmora map (maps/%s.bsp)' % TOWN)
    rows = (remove_legacy(id1, [t['id'] for t in runtime_towns(root) if t['name'] != TOWN], NOT_BUILT)
            if remove_legacy else [])
    for path in sorted((id1 / 'maps').glob('*.bsp')):
        if not keep_map(path.stem, kept, prefix):
            data = path.read_bytes()
            rows.append({'file': 'maps/' + path.name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                         'town': None, 'reason': NOT_BUILT})
            path.unlink()
    rows.sort(key=lambda row: row['file'])
    shipped = sorted(p.name for p in (id1 / 'maps').glob('*.bsp'))
    missing = sorted(name for name in kept if name + '.bsp' not in shipped)
    return {'scope': check_scope(scope), 'maps_removed': [row['file'][5:] for row in rows],
            'bytes_removed': sum(row['bytes'] for row in rows), 'removed': rows,
            'maps_kept': shipped, 'interiors_missing': missing}


def marker_text(version, feature_line, description=None, scope=DEFAULT_SCOPE):
    """The PARTIAL-AREA marker at the boot volume's root."""
    lines = [NAME, 'AmiWind v' + version, partial_area(scope), NOTICE_TITLE, feature_line]
    if label(scope):
        lines.append('Scope: %s (%s)' % (scope, label(scope)))
    if description:
        lines.append(SCENE_PREFIX + description)
    lines.append('Built by the repository builder with ' + OPTION + '; see docs/MINIWIND_PLAYTESTER.md.')
    return '\n'.join(lines) + '\n'


def hdf_tag(scope=DEFAULT_SCOPE):
    """The tag in the image's HDF names: PARTIAL-AREA, then the scope's label."""
    return HDF_TAG + ('-' + QUICK_SLUG if label(scope) else '')


def hdf_name(version, suffix='', scope=DEFAULT_SCOPE):
    return 'AmiWind-v%s%s%s.hdf' % (version, hdf_tag(scope), suffix)


def run_name(name, scope=DEFAULT_SCOPE):
    """The default run folder name with the scope's label (an explicit --name stays as given)."""
    return name + ('-' + QUICK_SLUG if label(scope) else '')


def record(stage_names, left_out, description=None, scope=DEFAULT_SCOPE):
    """The build_type block of the build receipts (build-state.json, build-summary.json)."""
    return {'name': NAME, 'option': OPTION, 'scope': check_scope(scope), 'label': label(scope),
            'partial_area': partial_area(scope), 'town': TOWN,
            'chim_areas': list(CHIM_AREAS), 'notice': [NOTICE_TITLE, features_line(stage_names, scope)],
            'features': features(stage_names), 'description': description,
            'stages': list(stage_names), 'left_out': dict(left_out)}
