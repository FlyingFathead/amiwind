# SPDX-License-Identifier: GPL-3.0-only
"""The legacy exterior stages of a CHIM build plan and why each still runs (light: no numpy).

A CHIM build (tools/build.py --builder chim) ships no legacy exterior map of a
CHIM area: the image step writes the frame maps, removes the town's legacy
maps (chim.frame_map.remove_legacy_areas) and then fails the build if any is
left in the image (chim.frame_map.require_no_legacy_areas). Some legacy
exterior stages still run in the plan because later stages read their
outputs; this module names them, what they make and who reads it, so every
CHIM build records the split (build-state.json "chim_plan") and a test pins
it. When a reader moves to another source, its row goes and the stage leaves
the CHIM plan (CHIM-LEGACY-CHAIN-33).
"""

# Stages that make legacy exterior maps or the open world, with what they make
# and which later step of a CHIM build still reads it. Stages not listed are
# shared converter stages (scene chain, interiors, actors, assets) or CHIM's own.
# Seyda Neen has no such stage: its region maps are made in the image step from
# the scene chain's seyda.map, or taken from the recorded v0.0.31 maps
# (--seyda-recorded), which a CHIM build with Seyda Neen requires.
LEGACY_EXTERIOR = {
    'balmora': ('Balmora region maps (bm###.bsp, balmora.bsp) and the Balmora layout cache',
                'the CHIM frame map balmora-chim.bsp copies its actors and player start from the final '
                'Balmora region maps; the town flora and night lighting tables read the cache'),
    'world-terrain': ('open-world terrain region maps (vf####.bsp)',
                      'the image step installs the open-world overlay; world flora places trees on it'),
    'world-scenery-assets': ('open-world rocks and giant mushrooms (source meshes)', 'world-scenery'),
    'world-scenery': ('open-world scenery overlay (vf####.bsp)',
                      'the image step requires the complete open-world overlay (--world-scenery)'),
    'world-flora': ('open-world flora overlay and the town flora the image installs',
                    'the image installs the Seyda Neen and Balmora town flora from it; the CHIM world adds '
                    'the same flora as meshes, and the frame maps check both sides hold it'),
}
TOWN_STAGE = 'town-'


def legacy_stages(stage_names, areas):
    """Rows for the legacy exterior stages in a CHIM plan: stage, area ('open world' or a town id),
    on_chim (the area is a CHIM area), makes, read_by."""
    areas = set(areas)
    rows = []
    for name in stage_names:
        if name.startswith(TOWN_STAGE):
            town = name[len(TOWN_STAGE):]
            rows.append({'stage': name, 'area': town, 'on_chim': town in areas,
                         'makes': 'the town\'s region maps and its interiors (import_town)',
                         'read_by': ('the town runs on CHIM: its frame maps copy their actors from them'
                                     if town in areas else
                                     'nothing that ships: a CHIM image leaves the town out (remove_towns_not_on_chim); '
                                     'the stage stays in the scene chain, which later stages copy')})
            continue
        if name not in LEGACY_EXTERIOR:
            continue
        makes, read_by = LEGACY_EXTERIOR[name]
        area = 'balmora' if name == 'balmora' else 'open world'
        rows.append({'stage': name, 'area': area, 'on_chim': area in areas, 'makes': makes, 'read_by': read_by})
    return rows


def record(stage_names, areas):
    """The build-state record of a CHIM plan's split (tools/build.py)."""
    rows = legacy_stages(stage_names, areas)
    return {'chim_areas': list(areas), 'legacy_exterior_stages': rows,
            'policy': 'no legacy exterior map of a CHIM area ships (image step: removed, then checked)'}
