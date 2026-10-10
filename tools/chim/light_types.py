# SPDX-License-Identifier: GPL-3.0-only
"""CHIM lighting types: the builder's --chim-lighting-type (docs/chim/LIGHTING.md, docs/chim/LIGHTING_ROADMAP.md).

Owner decision 2026-10-09: "hybrid" is the default. The types that need more memory than today's CHIM zone stay
reserved for an increased-memory version of the game and are refused with a message saying so. Nothing here
imports numpy (the builder reads it before its tools exist).
"""
import collections

DEFAULT = 'hybrid'
TYPES = collections.OrderedDict([
    ('none', 'no light sources: constant terrain light, models without lightmaps, no night lamps'),
    ('lamps', 'the v0.0.33 lighting: constant terrain light, models without lightmaps, the night lamp table '
              '(lamps, lanterns, torches, fires and candles as the nearest dynamic lights at night)'),
    ('hybrid', 'terrain lightmaps (sun and ambient in style 0, light sources in style 32, flicker and pulse in '
               '33-36, darkeners negative), one light level per placed model, the nearest light sources of every '
               'class as dynamic lights, per-plant glow'),
    ('baked-e', 'hybrid plus per-placement lightmaps for the placed models a light source reaches'),
    ('full', 'per-chunk terrain lightmaps and per-placement lightmaps for every placed model'),
])
IMPLEMENTED = ('none', 'lamps', 'hybrid')
RESERVED = {
    'baked-e': 'reserved for an increased-memory version of the game: per-placement lightmaps where a light reaches '
               'add 186-416 KB to a town ring (docs/chim/LIGHTING.md, "The options, measured")',
    'full': 'reserved for an increased-memory version of the game: per-placement lightmaps for every placed model '
            'add 0.3-0.6 MB to a town ring and 1.2-2.0 MB per frame on disk (docs/chim/LIGHTING.md)',
}
# What "hybrid" does today, part by part (docs/chim/LIGHTING_ROADMAP.md milestones). Builds record it.
HYBRID_PARTS = collections.OrderedDict([
    ('lightstyles', 'implemented'),            # sources in 32-36, generated flicker and pulse strings
    ('dynamic_every_class', 'implemented'),    # the night lamp table widened to every class that adds light
    ('terrain_lightmaps', 'planned'),
    ('placement_light_level', 'planned'),
    ('plant_glow', 'planned'),
])
assert set(IMPLEMENTED) | set(RESERVED) == set(TYPES)
# The label "hybrid" carries until its planned parts exist (receipts list them in 'parts').
PARTIAL_NOTE = (' (PARTIAL today: light styles and the night lamp table widened to every class; terrain lightmaps, '
                'model light levels and plant glow not yet)')


def check(kind):
    """The lighting type, or ValueError with a message that names the choices (reserved types say why)."""
    if kind in IMPLEMENTED:
        return kind
    if kind in RESERVED:
        raise ValueError('CHIM lighting type %r is not available yet: %s. Choose one of: %s (default %s).'
                         % (kind, RESERVED[kind], ', '.join(IMPLEMENTED), DEFAULT))
    raise ValueError('Unknown CHIM lighting type %r: choose one of %s (default %s); reserved for later: %s'
                     % (kind, ', '.join(IMPLEMENTED), DEFAULT, ', '.join(RESERVED)))


def lamp_classes(kind):
    """The light classes the engine's lamp table (dynamic lights) holds for a lighting type."""
    from light_sources import LAMP_CLASSES, LIGHT_CLASS_CODES
    check(kind)
    if kind == 'none':
        return ()
    if kind == 'lamps':
        return tuple(LAMP_CLASSES)
    return tuple(LIGHT_CLASS_CODES)


def help_text():
    """The --chim-lighting-type help: every type, the default and the reserved ones."""
    return ('CHIM lighting type (default %s; docs/chim/LIGHTING.md): ' % DEFAULT
            + '; '.join('%s = %s%s' % (k, v, ' (RESERVED: later, for an increased-memory version)' if k in RESERVED
                                       else PARTIAL_NOTE if k == 'hybrid' else '')
                        for k, v in TYPES.items()))


def record(kind):
    """The build receipt's lighting record."""
    out = {'type': check(kind), 'implemented': list(IMPLEMENTED), 'reserved': sorted(RESERVED)}
    if kind == 'hybrid':
        out['parts'] = dict(HYBRID_PARTS)
    return out
