#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The image step's sidecars of a CHIM frame map (moved out of tools/build_aga.py, which stood at the release text
size limit: BUILD-AGA-AT-TEXT-LIMIT-60; build_aga imports them under the same names)."""
import hashlib
from pathlib import Path


def chim_far_sidecar(chim_world, id1, record):
    """Copy the far terrain layer of a frame map's frame (CHIM output far/<cx>_<cy>.far) to
    id1/maps/<frame map>.far after checking it; None when the world has none (built without it)."""
    from chim.far import decode, file_name, sidecar_name
    if not record.get('frame') or not record.get('map'):
        return None
    source = Path(chim_world)/'far'/file_name(record['frame'])
    if not source.is_file():
        return None
    data = source.read_bytes()
    head = decode(data)[0]
    if list(head['cell']) != list(record['frame']):
        raise ValueError('Far terrain %s names frame %s, not %s' % (source.name, head['cell'], record['frame']))
    target = Path(id1)/sidecar_name(record['map'])
    if target.exists():
        raise ValueError('Far terrain already present: '+target.name)
    target.write_bytes(data)
    return {'file': sidecar_name(record['map']), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
            'size': list(head['size']), 'step': head['step']}


def chim_cut_sidecar(chim_world, id1, record):
    """Copy the whole-structure cut groups of a frame map's frame (CHIM output cuts/<cx>_<cy>.cut) to
    id1/maps/<frame map>.cut after checking it; None when the world has none (built before them, or a frame
    without structures: every placement then keeps its own cut)."""
    from chim.cuts import decode, file_name, sidecar_name
    if not record.get('frame') or not record.get('map'):
        return None
    source = Path(chim_world)/'cuts'/file_name(record['frame'])
    if not source.is_file():
        return None
    data = source.read_bytes()
    head = decode(data)[0]
    if list(head['cell']) != list(record['frame']):
        raise ValueError('Cut groups %s name frame %s, not %s' % (source.name, head['cell'], record['frame']))
    if not head['structures']:
        return None
    target = Path(id1)/sidecar_name(record['map'])
    if target.exists():
        raise ValueError('Cut groups already present: '+target.name)
    target.write_bytes(data)
    return {'file': sidecar_name(record['map']), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
            'structures': head['structures'], 'members': head['members']}
