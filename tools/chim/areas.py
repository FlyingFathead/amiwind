# SPDX-License-Identifier: GPL-3.0-only
"""Which areas the CHIM builder can write (light: no numpy, used when the build is planned).

An area is a town id of config/towns.json whose converter settings carry a town
block (the import_town converter: Balmora, the Vivec districts), or Seyda Neen
(format 0.5: its frame comes from the legacy scene stage, chim.seyda). A row blocked
by a legacy region limit (VIVEC-HEAP-31) is accepted: CHIM removes that limit.
One world holds a frame per area; frames must not overlap (a placement or tile
would be stored twice).
"""


def area_problems(areas, root=None):
    """Messages for areas the CHIM builder cannot write; empty when all can be written."""
    from town_config import load_registry, load_settings
    problems = []
    from town_config import generated_areas
    known = {t['id'] for t in load_registry(root)['towns']} | set(generated_areas())
    if not areas:
        problems.append('No CHIM area given')
    boxes = {}
    for area in areas:
        if area not in known:
            problems.append('Unknown CHIM area %s: not a town of config/towns.json nor a CHIM region frame' % area)
            continue
        if area == 'seyda':
            from chim.seyda import owned_world_box
            boxes[area] = owned_world_box(root=root)
            continue
        try:
            settings = load_settings(area, root)
        except (KeyError, ValueError) as exc:
            problems.append('CHIM area %s has no town converter settings yet (%s)' % (area, exc))
            continue
        # the box the frame owns in Morrowind units (chim.world.frame_box): its bounds; terrain-only margins
        # may overlap (each frame stores its own margin terrain, no placements: CHIM region frames side by side)
        # a handoff frame's core must fit the build's coordinate range (CHIM-FRAME-COORD-RANGE-33): all of
        # Vivec in one frame needs wide coordinates (coord_range; tools/build.py --coord-range)
        from town_config import handoff_core, registry_row
        try:
            handoff_row = area in generated_areas() or registry_row(area, root).get('world_slot', -1) < 0
        except ValueError:
            handoff_row = False
        if handoff_row:
            from coord_range import core_problem
            problem = core_problem(handoff_core(settings))
            if problem:
                problems.append('CHIM area %s: %s' % (area, problem))
        (lx, ly), (hx, hy) = settings['bounds']
        c = settings['centre']
        boxes[area] = (c[0] + 4 * lx, c[1] + 4 * ly, c[0] + 4 * hx, c[1] + 4 * hy)
    names = sorted(boxes)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            p, q = boxes[a], boxes[b]
            if p[0] < q[2] and q[0] < p[2] and p[1] < q[3] and q[1] < p[3]:
                problems.append('CHIM areas %s and %s overlap: one world cannot hold both frames' % (a, b))
    return problems
