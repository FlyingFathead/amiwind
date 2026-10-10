# SPDX-License-Identifier: GPL-3.0-only
"""The MiniWind plan's stage table: what an AmiWind "MiniWind" Playtester Build leaves out.

Pure data, no imports: tools/miniwind.py re-exports every name, and the stage
scheduler (tools/build_parallel.py) imports this module instead of miniwind.py.
Stage code imports the scheduler, and the stage cache follows every import, so
importing miniwind.py there put the CHIM builder modules and the engine source
folder into every conversion stage's fingerprint (BUILD-MINIWIND-STAGE-CLOSURE-33).
"""
SCOPES = ('full', 'exterior')
DEFAULT_SCOPE = 'full'

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


def omitted(name, scope=DEFAULT_SCOPE):
    """The reason a MiniWind plan leaves this stage out, or None when it runs."""
    if scope not in SCOPES:
        raise ValueError('--miniwind-scope must be one of %s, not %r' % (', '.join(SCOPES), scope))
    if name.startswith('town-'):
        return EXTRA_TOWN_REASON
    return OMITTED.get(name) or SCOPE_OMITTED[scope].get(name)
