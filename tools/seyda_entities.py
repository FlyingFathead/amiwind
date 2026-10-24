# SPDX-License-Identifier: GPL-3.0-only
"""Seyda Neen's scene entity list (BUILD-SEYDA-ENTITY-BUS-48).

The scene chain (bsp -> npcs -> hands -> interior -> intro -> census -> area -> ... -> opening-references) adds
Seyda Neen's entities stage by stage, and chim-town-seyda (tools/chim_town.py prepare_seyda) reads the result.
Before, every stage took the entities out of the seyda.bsp carrier's entity lump and chim-town-seyda parsed the
whole .bsp. Now each stage that writes Seyda Neen's entities publishes them in SCENE/seyda-entities.json, and the
next stage and chim-town-seyda read them from there:

  format       FORMAT
  entities     the entity text, exactly (the bytes the map's entity lump holds, cp1252)
  models       the brush model boxes (BSP29 model rows: 9 floats, 7 ints), which the activated objects and the
               region cuts read
  lump_sizes   the byte size of each map lump (a source-only carrier has no geometry: lumps 3, 7 and 8 empty)
  bsp_sha256   the SHA-256 of the scene's seyda.bsp written beside it (the chim-town record names it)

The seyda.bsp file is still written beside the list (the legacy consumers: a non-CHIM-native image, the actor
check and the compiled scene source read it), but no stage reads Seyda Neen's entities out of it. A writer checks
that the list belongs to the map it rewrites (bsp_sha256), so the two never drift apart; the entity text it
starts from is the list's, byte for byte the lump's, so the outputs are those of the legacy path.

Modes (--seyda-entities, environment AMIWIND_SEYDA_ENTITIES; part of the scene stages' cache keys):
  list  (default) the stages read the entity list
  bsp   the legacy read path: the stages read the seyda.bsp entity lump, as before v0.0.48 (kept: the
        maintainer, "DON'T DELETE ANY METHOD"); the list is still written, so either mode feeds the other
"""
import hashlib
import json
import os
import struct
from pathlib import Path

FORMAT = 'AmiWind Seyda Neen scene entities 1'
NAME = 'seyda-entities.json'
ENV = 'AMIWIND_SEYDA_ENTITIES'
MODES = ('list', 'bsp')
DEFAULT_MODE = 'list'


def mode():
    value = os.environ.get(ENV, '').strip() or DEFAULT_MODE
    if value not in MODES:
        raise ValueError('%s takes %s, not %r' % (ENV, ', '.join(MODES), value))
    return value


def add_option(parser):
    parser.add_argument('--seyda-entities', choices=MODES, default=DEFAULT_MODE,
                        help='Where the scene stages read Seyda Neen\'s entities (BUILD-SEYDA-ENTITY-BUS-48): list '
                             '(default: the entity list SCENE/seyda-entities.json each writing stage publishes) or '
                             'bsp (the legacy read path: the seyda.bsp carrier\'s entity lump). The same bytes either '
                             'way. Part of the scene stages\' cache keys (AMIWIND_SEYDA_ENTITIES)')
    return parser


def export_mode(value):
    """Export the mode for every stage (the default removes the variable, so a default build's environment is as
    before)."""
    if value not in MODES:
        raise ValueError('seyda-entities must be one of %s, not %r' % (', '.join(MODES), value))
    if value == DEFAULT_MODE:
        os.environ.pop(ENV, None)
    else:
        os.environ[ENV] = value
    return value


def record_of(raw):
    """The entity list record of a seyda.bsp's bytes RAW."""
    from player_hull import lumps
    parts = lumps(raw)
    return {'format': FORMAT, 'map': 'seyda',
            'bsp_sha256': hashlib.sha256(raw).hexdigest(),
            'lump_sizes': [len(p) for p in parts],
            'models': [list(m) for m in struct.iter_unpack('<9f7i', parts[14])],
            'entities': bytes(parts[0]).decode('cp1252')}


def publish(scene, raw):
    """Write SCENE's entity list for the seyda.bsp bytes RAW the stage just wrote (replaced whole, never in place:
    an earlier stage's list may be a read-only link into the storage pool, BUILD-POOL-READONLY-SCENE-WRITE-35)."""
    from mwad.paths import replace_bytes
    text = json.dumps(record_of(raw), separators=(',', ':'), ensure_ascii=True) + '\n'
    replace_bytes(Path(scene) / NAME, text.encode('ascii'))


def read(scene):
    """SCENE's entity list record (checked format)."""
    path = Path(scene) / NAME
    if not path.is_file():
        raise ValueError('The scene %s has no Seyda Neen entity list (%s): rebuild it from the bsp stage, or read '
                         'the legacy seyda.bsp with --seyda-entities bsp (BUILD-SEYDA-ENTITY-BUS-48)' % (scene, NAME))
    record = json.loads(path.read_text(encoding='ascii'))
    if record.get('format') != FORMAT or record.get('map') != 'seyda' or len(record.get('lump_sizes', ())) != 15:
        raise ValueError('Not a Seyda Neen entity list: ' + str(path))
    return record


def entity_lump(record):
    """The entity lump bytes of an entity list record."""
    return record['entities'].encode('cp1252')


def models(record):
    """The brush model rows of an entity list record, as struct.iter_unpack gives them (tuples)."""
    return [tuple(m) for m in record['models']]


def writer_lump(scene, raw):
    """The entity lump a writing stage starts from, for the seyda.bsp bytes RAW it is about to rewrite: the list's
    (default; it must belong to RAW) or, in the legacy mode, RAW's own lump 0."""
    if mode() == 'bsp':
        from player_hull import lumps
        return lumps(raw)[0]
    record = read(scene)
    if record['bsp_sha256'] != hashlib.sha256(raw).hexdigest():
        raise ValueError('The Seyda Neen entity list of %s does not belong to its seyda.bsp (a stage rewrote the map '
                         'without publishing the list, BUILD-SEYDA-ENTITY-BUS-48)' % scene)
    return entity_lump(record)


def source(scene):
    """What chim-town-seyda reads: (entity lump bytes, model rows, lump sizes, seyda.bsp SHA-256), from the list
    (default) or, in the legacy mode, from SCENE/id1/maps/seyda.bsp."""
    if mode() == 'bsp':
        record = record_of((Path(scene) / 'id1/maps/seyda.bsp').read_bytes())
    else:
        record = read(scene)
    return entity_lump(record), models(record), list(record['lump_sizes']), record['bsp_sha256']
