# SPDX-License-Identifier: GPL-3.0-only
"""Procedural visual shells; materials come from the user's matched source asset."""
import numpy as np


def lantern_shell(settings):
    """Four-sided paper body, overhanging pyramid roof and tapered lower spike."""
    width = float(settings['half_width'])
    top, bottom = float(settings['top']), float(settings['bottom'])
    roof = top - width
    neck = float(settings['neck_half_width'])
    points = [(x, y, z) for z in (float(settings['body_bottom']), roof)
              for y in (-width, width) for x in (-width, width)]
    points.append((0, 0, top))
    points.extend((x, y, float(settings['neck_z'])) for y in (-neck, neck) for x in (-neck, neck))
    points.append((0, 0, bottom))
    eave = width * float(settings['roof_width_ratio'])
    points.extend((x, y, roof) for y in (-eave, eave) for x in (-eave, eave))
    # Six decimal places match the retained shell's authored export precision.
    points = np.round(np.asarray(points, dtype=float), 6)
    faces = [(0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5),
             (14, 15, 8), (15, 17, 8), (17, 16, 8), (16, 14, 8),
             (1, 0, 9, 10), (3, 1, 10, 12), (2, 3, 12, 11), (0, 2, 11, 9),
             (10, 9, 13), (12, 10, 13), (11, 12, 13), (9, 11, 13),
             (4, 5, 15, 14), (5, 7, 17, 15), (7, 6, 16, 17), (6, 4, 14, 16)]
    vertices, triangles = [], []
    for k, ids in enumerate(faces):
        q = points[list(ids)]
        normal = np.cross(q[1] - q[0], q[2] - q[0])
        axes = [a for a in range(3) if a != int(np.argmax(abs(normal)))]
        uv = q[:, axes]
        uv = (uv - uv.min(0)) / np.maximum(np.ptp(uv, axis=0), 1e-9)
        start = len(vertices)
        vertices.extend([*p, *t, 255, 255, 255, 255] for p, t in zip(q, uv))
        material = int(settings['paper_material'] if k < 4 else settings['frame_material'])
        triangles.extend([start, start + i, start + i + 1, material] for i in range(1, len(ids) - 1))
    return np.asarray(vertices), np.asarray(triangles, dtype=np.int64)


def make_visual(settings):
    if settings['kind'] == 'lantern_shell':
        return lantern_shell(settings)
    raise ValueError('Unknown visual primitive: ' + str(settings['kind']))
