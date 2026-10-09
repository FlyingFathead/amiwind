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
    known = {t['id'] for t in load_registry(root)['towns']}
    if not areas:
        problems.append('No CHIM area given')
    boxes = {}
    for area in areas:
        if area not in known:
            problems.append('Unknown CHIM area %s: not a town of config/towns.json' % area)
            continue
        if area == 'seyda':
            from chim.seyda import world_box
            boxes[area] = world_box(root=root)
            continue
        try:
            settings = load_settings(area, root)
        except (KeyError, ValueError) as exc:
            problems.append('CHIM area %s has no town converter settings yet (%s)' % (area, exc))
            continue
        # the frame's ground box in Morrowind units (chim.world.frame_box)
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
