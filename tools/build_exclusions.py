# SPDX-License-Identifier: GPL-3.0-only
"""Quick test builds: content groups a development build may leave out (--exclude).

This module is the one table of what each exclusion group does: the builder
stages it skips, the options it hands to the stages that still run, the labels
in receipts and in game, and what the game does without it. tools/build.py
reads it for the plan, tools/build_parallel.py for the stage order,
tools/build_cache.py for the stage fingerprints and tools/build_aga.py for the
image (the marker file the engine reads, the receipts and the media gates).

Every shipped feature stays in a default build: a build without --exclude
leaves nothing out. An exclusion is for quick -devN test builds only; release
candidates and finals refuse every one of them
(project_version.require_private_test_version).

Never an exclusion group (owner rule): dressing, clutter, props, flora or
anything else with collision that NPCs or the player walk into. NPCs can get
stuck on that content, so path and movement tests need it in every build.
REFUSED names those groups and the reason; tests/test_build_exclusions.py
checks that no group skips or reduces such content. --skip-dressing and
--no-tree-sprites stay separate DEBUGGING switches.

The image carries id1/excluded-content.txt (MARKER) when anything is left out:
"AWX1", then one line per group: its name and the words the game uses in its
notice ("This build was made without <notice> (quick test build).").
engine/aga/src/aw_excluded.c reads it once.
"""
from pathlib import Path
import re

OPTION = '--exclude'
MARKER = 'excluded-content.txt'
MARKER_MAGIC = 'AWX1'
# Boot volume root marker and HDF name tag of a quick test build.
ROOT_MARKER = 'QUICK-TEST-BUILD.txt'
HDF_TAG = '-quick-test'
LABEL = 'quick test build'
# Engine buffers (aw_excluded.c): group names and notice words, with the terminator.
NAME_CHARS, NOTICE_CHARS, MAX_GROUPS = 23, 63, 12

# One row per group. Keys:
#   label         receipts and summaries ("excluded: video, music")
#   notice        the game's words: "This build was made without <notice> (quick test build)."
#   alias         the readable command-line flag (same as --exclude NAME)
#   skip          builder stages that do not run
#   options       {stage: [extra options]} for stages that still run but leave the group out
#   legacy        the older DEBUGGING switch that means the same (kept working)
#   placements    True when placed entities disappear (the entity baseline then records the
#                 loss with the quick-test reason instead of stopping the image)
#   area_builds   True when the group only means something in an area build (MiniWind,
#                 a single area, a direct start); a full build refuses it
#   in_game       what the game does without it (docs and receipts)
#   saves         typical time saved (docs/chim/build_guide/QUICK_TEST_BUILDS.md has the measurements)
GROUPS = {
    'video': {
        'label': 'intro movies and videos',
        'notice': 'the intro movies',
        'alias': '--exclude-video',
        'skip': (),
        'options': {'media': ['--no-videos'], 'intro': ['--no-movie']},
        'placements': False,
        'in_game': 'New Game goes straight to the prison ship (no black wait); playvid says the build has no videos',
        'saves': 'the video part of the media stage and the intro movie conversion',
    },
    'music': {
        'label': 'music',
        'notice': 'the music',
        'alias': '--exclude-music',
        'skip': ('music',),
        'options': {},
        'placements': False,
        'in_game': 'silence where music would play; one console line at startup',
        'saves': 'the music stage and the soundtrack copy in the image step',
    },
    'voice': {
        'label': 'recorded dialogue voices',
        'notice': 'the recorded dialogue voices',
        'alias': '--exclude-voice',
        'skip': (),
        'options': {'media': ['--no-voices']},
        'placements': False,
        'in_game': 'the recorded dialogue library (Sound/Vo) is left out; NPC greetings and the ship '
                   'intro lines stay, so the opening runs; one console line at startup',
        'saves': 'the voice part of the media stage',
    },
    'npc-gallery': {
        'label': 'NPC gallery',
        'notice': 'the NPC gallery',
        'alias': '--exclude-npc-gallery',
        'skip': ('npc-gallery',),
        'options': {},
        'legacy': 'no_npc_gallery',
        'placements': False,
        'in_game': 'dbg npcgallery and the other gallery commands say the build has no gallery; '
                   'every NPC of the game is still built',
        'saves': 'the npc-gallery stage (the longest stage of a full build)',
    },
    'interiors': {
        'label': 'interiors',
        'notice': 'the interiors',
        'alias': '--exclude-interiors',
        'skip': (),
        # The rooms are not compiled; the stages still place the exterior residents
        # and write every door table, so doors say "Area unavailable".
        'options': {'area': ['--no-rooms'], 'balmora-interiors': ['--no-rooms']},
        'placements': True,
        'in_game': 'Seyda Neen and Balmora house doors say "Area unavailable"; the prison ship and the '
                   'Census and Excise Office stay, so a new game still starts normally',
        'saves': 'the Seyda Neen and Balmora room compiles',
    },
    'harvest': {
        'label': 'harvestable plants',
        'notice': 'the harvestable plants',
        'alias': '--exclude-harvest',
        'skip': ('harvest',),
        'options': {},
        'legacy': 'no_harvest',
        'placements': True,
        'in_game': 'mushrooms stay in the world as baked scenery (same shape and collision) but cannot be picked',
        'saves': 'the harvest stage and its image pass',
    },
    'unreferenced': {
        'label': 'content the selected area does not reference',
        'notice': 'content outside the selected area',
        # --exclude-unreferenced [GROUP,...]: the reference closure's groups
        # (tools/content_closure.py GROUPS: npcs, voice, sounds, models, textures; all
        # when none are named). Music is never trimmed by it.
        'alias': '--exclude-unreferenced',
        'skip': (),
        # A reference-closure stage runs first; these stages then read its list.
        'options': {},
        'closure_stages': ('npc-gallery', 'media'),
        'placements': False,
        'area_builds': True,
        'in_game': 'only what the built area references: its NPCs and creatures (the NPC gallery shows exactly '
                   'those), every line their dialogue pool can say, the sounds they use; music and every '
                   'placed object (dressing included) stay',
        'saves': 'gallery models and voice files of NPCs the area never shows',
    },
}
CLOSURE_STAGE = 'reference-closure'
CLOSURE_FILE = 'reference-closure.json'

# Never exclusion groups (owner rule, 2026-10-09): content with collision that NPCs
# or the player walk into. Each name maps to the reason the refusal prints.
REFUSED = {
    'dressing': 'dressing (hooks, ropes, ferns, lanterns) has collision NPCs get stuck on; path and movement '
                'tests need it. --skip-dressing stays a separate DEBUGGING switch',
    'clutter': 'clutter has collision NPCs get stuck on; it stays in every build',
    'props': 'props have collision NPCs get stuck on; they stay in every build',
    'flora': 'trees, grass and reeds have collision the player and NPCs walk into; they stay in every '
             'quick test build. --no-tree-sprites stays a separate DEBUGGING switch',
    'collision': 'collision content stays in every build',
    'scenery': 'scenery has collision the player and NPCs walk into; it stays in every build',
}
# Always included (owner rule, 2026-10-09): shared engine assets that maps and the
# engine find by name or by metadata, not by a placement, so a reference closure would
# miss them. No group and no --exclude-unreferenced closure may drop them; the image
# step of every quick test build checks them (check_always_included). id1-relative.
ALWAYS_INCLUDED = {
    'gfx/aw_shared_sky.lmp': 'the shared exterior sky (32,768 bytes; every exterior map names it in its '
                             'worldspawn keys _aw_sky_mode and _aw_sky_asset)',
    'gfx/palette.lmp': 'the palette',
    'gfx/colormap.lmp': 'the colour map',
    'gfx.wad': 'the status bar and menu graphics',
    'gfx/conback.lmp': 'the console background',
    'gfx/font-readable.lmp': 'the readable console font',
    'gfx/font-retro.lmp': 'the retro console font',
    'gfx/magic16.awf': 'the game font of the startup screen',
    'gfx/ui.awu': 'the user interface graphics',
    'gfx/menu.awb': 'the main menu background',
    'gfx/amiwind.awi': 'the menu logo',
    'intro/amiwind.awv': 'the startup logo',
    'progs.dat': 'the game code',
    'quake.rc': 'the start-up script',
    'default.cfg': 'the default settings',
}
# Needed only when the build has an exterior (an interior-only build has no sky).
EXTERIOR_ONLY = ('gfx/aw_shared_sky.lmp',)
SHARED_SKY = 'gfx/aw_shared_sky.lmp'
SHARED_SKY_BYTES = 32768
SKY_KEYS = ('_aw_sky_mode', '_aw_sky_asset')
# Stages whose outputs hold those assets: no group may skip them.
PROTECTED_STAGES = ('scene', 'intro', 'census', 'engine', 'image')
# Stages and stage options that remove or reduce content with collision; no group may
# skip or pass any of them (tests/test_build_exclusions.py).
COLLISION_STAGES = ('world-flora-assets', 'world-flora', 'world-scenery-assets', 'world-scenery',
                    'scenery', 'bsp', 'interior', 'census')
COLLISION_OPTIONS = ('--skip-dressing',)


def names():
    return tuple(GROUPS)


def alias_flags():
    """{flag: group} of the readable aliases."""
    return {row['alias']: name for name, row in GROUPS.items()}


def add_options(parser):
    """--exclude GROUP[,GROUP...] and one alias per group (same destination)."""
    parser.add_argument(OPTION, dest='exclude', action='append', metavar='GROUP[,GROUP...]',
                        help='DEBUGGING ONLY (quick test builds): leave content out of a -devN build; groups: '
                             + ', '.join(GROUPS) + '. Refused for release candidates and finals; the image, '
                             'receipts and console say "quick test build". See docs/chim/build_guide/QUICK_TEST_BUILDS.md')
    for name, row in GROUPS.items():
        if name == 'unreferenced':
            from content_closure import GROUPS as CLOSURE_GROUPS
            parser.add_argument(row['alias'], dest='exclude_unreferenced', nargs='?', const='all', default=None,
                                metavar='GROUP[,GROUP...]',
                                help='DEBUGGING ONLY (area builds): build only what the selected area references; '
                                     'groups ' + ', '.join(CLOSURE_GROUPS) + ' (default all). Music is never trimmed. '
                                     f'{OPTION} {name} means all groups')
            continue
        parser.add_argument(row['alias'], dest='exclude', action='append_const', const=name,
                            help=f'DEBUGGING ONLY: same as {OPTION} {name} ({row["label"]}; {row["in_game"]})')


def parse(values):
    """The requested groups, in table order, from --exclude values and aliases.

    Unknown names and refused groups raise ValueError with the reason."""
    requested = []
    for value in values or ():
        for part in str(value).split(','):
            name = part.strip().casefold()
            if not name:
                continue
            if name in REFUSED:
                raise ValueError(f'{OPTION} {name} is refused: {REFUSED[name]}')
            if name not in GROUPS:
                raise ValueError(f'{OPTION}: unknown group "{name}"; groups: ' + ', '.join(GROUPS))
            requested.append(name)
    return [name for name in GROUPS if name in requested]


def fold(args):
    """Fold --exclude, its aliases and the older switches into one group list on args.

    Sets args.exclude_groups (table order) and the older switches the rest of the
    builder reads (args.no_npc_gallery, args.no_harvest), so --exclude npc-gallery
    and --no-npc-gallery take the same path. Idempotent."""
    groups = parse(getattr(args, 'exclude', None))
    for name, row in GROUPS.items():
        legacy = row.get('legacy')
        if legacy and getattr(args, legacy, False) and name not in groups:
            groups.append(name)
    unreferenced = getattr(args, 'exclude_unreferenced', None)
    if unreferenced == 'none':
        unreferenced = None  # --exclude-unreferenced none: off (a MiniWind build's default is voice,npcs)
    if unreferenced is not None and 'unreferenced' not in groups:
        groups.append('unreferenced')
    groups = [name for name in GROUPS if name in groups]
    for name in groups:
        legacy = GROUPS[name].get('legacy')
        if legacy:
            setattr(args, legacy, True)
    args.exclude_groups = groups
    from content_closure import parse_groups
    args.unreferenced_groups = parse_groups(unreferenced) if 'unreferenced' in groups else []
    return groups


def resolve(args, version, area_build=False):
    """fold(), then the refusals: every exclusion for release candidates and finals
    (including the older switches), and area-only groups outside an area build."""
    groups = fold(args)
    if groups:
        from project_version import require_private_test_version
        require_private_test_version(version, [f'{OPTION} {", ".join(groups)}'])
    for name in groups:
        if GROUPS[name].get('area_builds') and not area_build:
            raise ValueError(f'{OPTION} {name} needs an area build (a single area, MiniWind or a direct start): '
                             'a full build references all of its content')
    return groups


# A MiniWind build (an area build) is a quick test build by default (owner decision,
# 2026-10-09: MiniWind #2 shipped with all 17 videos and 6,447 voices): no videos, and
# only the voices and NPC records Balmora references. Music stays; the shared sky and the
# other always-included assets stay; --with-video and --exclude-unreferenced none undo it.
MINIWIND_DEFAULT_EXCLUDE = ('video',)
MINIWIND_DEFAULT_UNREFERENCED = 'voice,npcs'


def miniwind_defaults(args):
    """Apply the MiniWind defaults to args before resolve(): adds 'video' unless --with-video,
    and --exclude-unreferenced voice,npcs unless that option was given. Returns what it added."""
    added = []
    if not getattr(args, 'miniwind', False):
        return added
    present = parse(getattr(args, 'exclude', None))
    for name in MINIWIND_DEFAULT_EXCLUDE:
        if name == 'video' and getattr(args, 'with_video', False):
            continue
        if name not in present:
            args.exclude = list(getattr(args, 'exclude', None) or []) + [name]
            added.append(name)
    if getattr(args, 'exclude_unreferenced', None) is None:
        args.exclude_unreferenced = MINIWIND_DEFAULT_UNREFERENCED
        added.append('unreferenced ' + MINIWIND_DEFAULT_UNREFERENCED)
    return added


def skipped_stages(groups):
    return {stage for name in groups for stage in GROUPS[name]['skip']}


def stage_groups(stage, groups):
    """The groups that change this stage (skip it, pass it options, or the image)."""
    return [name for name in groups if stage in ('image', CLOSURE_STAGE) or stage in GROUPS[name]['skip']
            or stage in GROUPS[name]['options'] or stage in GROUPS[name].get('closure_stages', ())]


def closure_step(run, data_files, cells, closure_groups, python=None):
    """The reference-closure stage of an area build (tools/content_closure.py)."""
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    command = [python or sys.executable, str(root / 'tools/content_closure.py'), '--data-files', str(data_files),
               '--out', str(Path(run) / CLOSURE_FILE), '--groups', ','.join(closure_groups)]
    for cell in cells:
        command += ['--cell', cell]
    return (CLOSURE_STAGE, command)


def apply(steps, groups, run=None, area_cells=None, data_files=None, closure_groups=None):
    """The plan with the groups left out: skipped stages removed, stage options added and
    the image told what is excluded (--exclude). No groups: the plan unchanged.

    'unreferenced' (area builds only) needs the area's cells: a reference-closure stage
    runs first and the gallery and media stages read its list (--reference-closure)."""
    if not groups:
        return list(steps)
    skipped = skipped_stages(groups)
    closure = None
    if 'unreferenced' in groups:
        if not area_cells or run is None or data_files is None:
            raise ValueError(OPTION + ' unreferenced needs an area build: the cells it builds decide what is referenced')
        from pathlib import Path
        closure = closure_step(run, data_files, area_cells, closure_groups or [])
        closure_file = str(Path(run) / CLOSURE_FILE)
    result = [closure] if closure else []
    for name, command in steps:
        if name in skipped:
            continue
        command = list(command)
        for group in groups:
            command += GROUPS[group]['options'].get(name, [])
            if closure and name in GROUPS[group].get('closure_stages', ()):
                command += ['--reference-closure', closure_file]
        if name == 'image':
            command += [OPTION, ','.join(groups)]
        result.append((name, command))
    return result


def from_command(command):
    """The groups an image (or any stage) command was given with --exclude."""
    command = [str(part) for part in command]
    if OPTION not in command:
        return []
    return parse([command[command.index(OPTION) + 1]])


def marker_text(groups):
    """id1/excluded-content.txt as the engine parses it (aw_excluded.c)."""
    if len(groups) > MAX_GROUPS:
        raise ValueError('Too many exclusion groups for the engine table')
    lines = [MARKER_MAGIC]
    for name in groups:
        notice = GROUPS[name]['notice']
        if not re.fullmatch(r'[a-z0-9-]{1,%d}' % NAME_CHARS, name):
            raise ValueError('Exclusion group name is not engine-safe: ' + name)
        if not (0 < len(notice) <= NOTICE_CHARS and all(' ' <= c <= '~' for c in notice)):
            raise ValueError('Exclusion notice is not engine-safe: ' + notice)
        lines.append(f'{name} {notice}')
    return '\n'.join(lines) + '\n'


def summary(groups):
    """'quick test build, excluded: video, music' (receipts, summaries, folder labels)."""
    return f'{LABEL}, excluded: ' + ', '.join(groups) if groups else 'complete (nothing excluded)'


def folder_tag(groups):
    """A short name part for run and playtest folder names: 'quick-test-video-music'."""
    return 'quick-test-' + '-'.join(groups) if groups else ''


def record(groups):
    """The excluded_content block of build-state.json, build-summary.json and build.json."""
    return {'groups': list(groups), 'summary': summary(groups),
            'label': LABEL if groups else None,
            # Read by the scheduler, the stage cache and the profiler (build_parallel.plan_skipped).
            'skipped_stages': sorted(skipped_stages(groups)),
            'marker': 'id1/' + MARKER if groups else None,
            'details': {name: {'label': GROUPS[name]['label'], 'in_game': GROUPS[name]['in_game'],
                               'skipped_stages': list(GROUPS[name]['skip']),
                               'stage_options': {k: list(v) for k, v in GROUPS[name]['options'].items()}}
                        for name in groups}}


def check_always_included(id1, exterior=True, maps=None):
    """The always-included assets of a staged id1 (ALWAYS_INCLUDED), raising ValueError with
    every missing one. exterior: the build has an exterior, so the shared sky is required (and
    must be SHARED_SKY_BYTES long); maps: {map name: worldspawn keys} of the staged maps, each
    sky asset a map names must exist. Returns the record for the receipts."""
    id1 = Path(id1)
    missing = []
    for name, what in ALWAYS_INCLUDED.items():
        if name in EXTERIOR_ONLY and not exterior:
            continue
        if not (id1 / name).is_file():
            missing.append('%s (%s)' % (name, what))
    sky = id1 / SHARED_SKY
    if exterior and sky.is_file() and sky.stat().st_size != SHARED_SKY_BYTES:
        missing.append('%s is %d bytes, not %d' % (SHARED_SKY, sky.stat().st_size, SHARED_SKY_BYTES))
    named = {}
    for name, keys in (maps or {}).items():
        asset = keys.get(SKY_KEYS[1])
        if asset:
            named.setdefault(asset, []).append(name)
    for asset, users in sorted(named.items()):
        if not (id1 / asset).is_file():
            missing.append('%s (named by %d maps, e.g. %s)' % (asset, len(users), sorted(users)[0]))
    if missing:
        raise ValueError('Always-included assets missing from this image (no exclusion may drop them): '
                         + '; '.join(missing))
    return {'checked': sorted(n for n in ALWAYS_INCLUDED if exterior or n not in EXTERIOR_ONLY),
            'sky_assets_named_by_maps': {asset: len(users) for asset, users in sorted(named.items())},
            'status': 'passed'}


def worldspawn_sky_keys(maps_dir):
    """{map name: {sky key: value}} of the staged BSP29 maps (their worldspawn)."""
    import struct
    found = {}
    for path in sorted(Path(maps_dir).glob('*.bsp')):
        with path.open('rb') as stream:
            head = stream.read(124)
            if len(head) < 124 or struct.unpack_from('<i', head)[0] != 29:
                continue
            offset, size = struct.unpack_from('<ii', head, 4)
            stream.seek(offset)
            text = stream.read(min(size, 1 << 20)).decode('cp1252', 'replace')
        first = text[:text.find('}') + 1]
        keys = dict(re.findall(r'"(_aw_sky_(?:mode|asset))"\s+"([^"]*)"', first))
        if keys:
            found[path.stem] = keys
    return found


def removes_placements(groups):
    return [name for name in groups if GROUPS[name]['placements']]
