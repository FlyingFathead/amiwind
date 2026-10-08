#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Convert owned Balmora terrain, scenery and residents into bounded sub-cells.

Thin wrapper: import_town.py --town balmora does the work. Same CLI and
outputs as before the town converter became generic.
"""
import json

from import_town import (write_json, source_receipt, ground_assets, terrain_sample, terrain_material,  # noqa: F401
                         terrain_at, terrain_map, travel_point, residents, resident_entities, publish,
                         entity, parser)
from import_town import prepare as prepare_town


def prepare(data_files, scene, out, qbsp, vis, light, ffmpeg='ffmpeg', jobs=None, collect_only=False,
            vis_mode='fast'):
    return prepare_town('balmora', data_files, scene, out, qbsp, vis, light, ffmpeg, jobs, collect_only, vis_mode)


if __name__ == '__main__':
    a = parser(__doc__, town=False).parse_args()
    print(json.dumps(prepare(a.data_files, a.scene, a.out, a.qbsp, a.vis, a.light, a.ffmpeg, a.jobs,
                             a.collect_only, a.vis_mode), indent=2))
