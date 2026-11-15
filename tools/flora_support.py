# SPDX-License-Identifier: GPL-3.0-only
"""The plants that grow on another object and the builder's two answers for them (config/flora-support.json,
docs/HARVEST.md "Plants on trees"):

- seats: a bracket fungus whose tree the builder draws with fewer faces than the original (the reduced trunk lies
  inside the original one) is moved by a measured shift (original units) onto the drawn trunk, so it touches it;
- mesh_hosts: a tree that carries a bracket fungus is drawn as a mesh, never as a flat sprite (a sprite has no trunk
  surface for the fungus to sit on).

Both lists are measured by tools/chim/flora_support_audit.py on a build (--write-config) and checked by it on every
build (FLORA-FLOATING-DEV1-66, HARVEST-HYPHA-FACIA-FLOATING-65, FUNGI-FLOATING-62)."""
import json
from functools import lru_cache
from pathlib import Path

CONFIG = Path(__file__).resolve().parents[1] / 'config' / 'flora-support.json'


@lru_cache(maxsize=None)
def _load(path=str(CONFIG)):
    p = Path(path)
    if not p.is_file():
        return {}, frozenset(), {}
    data = json.loads(p.read_text(encoding='utf-8'))
    if data.get('format') != 'AmiWind flora support 1':
        raise ValueError('Unrecognised flora support table: ' + str(p))
    seats = {}
    for row in data.get('seats', ()):
        shift = [float(v) for v in row['shift']]
        if len(shift) != 3 or max(abs(v) for v in shift) > 256:
            raise ValueError('Flora seat out of range for reference %s' % row.get('reference'))
        seats[int(row['reference'])] = tuple(shift)
    hosts = frozenset(int(row['reference']) for row in data.get('mesh_hosts', ()))
    known = {}
    for row in data.get('known_floating', ()):
        if not str(row.get('reason', '')).strip():
            raise ValueError('A known floating plant needs its reason: %s' % row.get('reference'))
        known[int(row['reference'])] = row['reason']
    return seats, hosts, known


def seats():
    """{original reference number: (dx, dy, dz) in original units} of the seated plants."""
    return dict(_load()[0])


def seat(number):
    return _load()[0].get(int(number))


def mesh_hosts():
    """Original reference numbers of the trees drawn as a mesh because a plant grows on them."""
    return _load()[1]


def known_floating():
    """{original reference number: reason} of plants the check reports but does not fail on (each with its reason)."""
    return dict(_load()[2])
