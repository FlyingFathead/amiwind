# SPDX-License-Identifier: GPL-3.0-only
"""The per-mesh measured tables, keyed by the rows a cached result used (BUILD-KEY-MESH-TABLE-WHOLE-54).

config/collision-standing-room.json and config/collision-hull-surface.json each hold one decision per mesh. A pass or
unit cache that keyed them whole (pass_cache source digest: a data file its code names counts whole) was re-keyed for
every unit by one new row: the v0.0.54-dev2 rerun converted all 935 rooms again after one standing-room row. They are
left out of those keys (pass_cache.PASS_KEY_NEUTRAL) and each entry records the decisions it read instead:

- the table readers (mesh_geometry_env.standing_room_meshes, chim.build.hull_surface_table and its recipe and known
  tables) return TrackedSet sets: a membership test notes (table, mesh) into every recorder now active, any other use
  (iteration, length, set algebra) notes the whole table;
- a cache miss starts a recorder (begin), the store writes rows(used): {table: {mesh: decision digest}} ('*': the
  whole table's decisions), and a load takes an entry only while matches() finds every recorded decision unchanged.
  A hit also notes its recorded rows into the recorders active around it (a room unit that took a model from its own
  cache used that model's rows).

A mesh's decision is what the builder reads of it: standing room, whether the mesh is listed; hull surface, whether it
is listed, the visual recipes that list it and whether it is a known over-step mesh; plus the table's format. A reason
text edited, or a row added for another mesh, keeps every other entry. Lookups made in another process than the
recorder's (a pool the unit itself starts) are not seen: the units that key on these tables look up in their own
worker (prepare_area rooms build their meshes with one job).
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TABLES = ('config/collision-standing-room.json', 'config/collision-hull-surface.json')
WHOLE = '*'

_ACTIVE = []
_VIEWS = {}


def name(path):
    """The table's name in records: its repository path for the repository's tables, else the absolute path."""
    path = Path(path).resolve()
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _path(table):
    return ROOT / table if not Path(table).is_absolute() else Path(table)


def norm(mesh):
    return str(mesh).replace(chr(92), '/').casefold()


def note(table, mesh):
    for used in _ACTIVE:
        used.add((table, mesh))


def begin():
    """A new recorder: the (table, mesh) pairs read while it is active (end() stops it)."""
    used = set()
    _ACTIVE.append(used)
    return used


def end(used):
    for at, active in enumerate(_ACTIVE):
        if active is used:
            del _ACTIVE[at]
            return


class TrackedSet(set):
    """A table's meshes; a membership test notes (table, mesh), any other read the whole table."""

    def __init__(self, values=(), table=''):
        super().__init__(values)
        self.table = table

    def __contains__(self, mesh):
        note(self.table, norm(mesh))
        return super().__contains__(mesh)

    def _whole(self):
        note(self.table, WHOLE)

    def __iter__(self):
        self._whole()
        return super().__iter__()

    def __len__(self):
        self._whole()
        return super().__len__()

    def __reduce__(self):
        return (TrackedSet, (set(super().__iter__()), self.table))


def _whole_method(method):
    def wrapped(self, *args, **kwargs):
        self._whole()
        return getattr(set, method)(self, *args, **kwargs)
    wrapped.__name__ = method
    return wrapped


for _method in ('__and__', '__rand__', '__or__', '__ror__', '__sub__', '__rsub__', '__xor__', '__rxor__',
                '__eq__', '__ne__', '__le__', '__lt__', '__ge__', '__gt__', 'issubset', 'issuperset', 'isdisjoint',
                'intersection', 'union', 'difference', 'symmetric_difference', 'copy'):
    if hasattr(set, _method):
        setattr(TrackedSet, _method, _whole_method(_method))
TrackedSet.__hash__ = None


def tracked(values, path):
    return TrackedSet(values, name(path))


def _views(table):
    """(format text, {mesh: decision}) of a table as it is on disk now (cached by its bytes' SHA-256)."""
    raw = _path(table).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    known = _VIEWS.get(table)
    if known is not None and known[0] == digest:
        return known[1]
    data = json.loads(raw.decode('utf-8'))
    head = json.dumps([data.get('format'), data.get('schema')])
    views = {}

    def add(mesh, part, value):
        views.setdefault(norm(mesh), {}).setdefault(part, []).append(value)
    meshes = data.get('meshes')
    for mesh in (meshes or ()):
        add(mesh, 'listed', True)
    for recipe, listed in sorted((data.get('recipe_meshes') or {}).items()):
        for mesh in listed:
            add(mesh, 'recipes', recipe)
    for mesh in (data.get('known_over_step') or {}):
        add(mesh, 'known', True)
    result = (head, {mesh: json.dumps(view, sort_keys=True) for mesh, view in views.items()})
    _VIEWS[table] = (digest, result)
    return result


def _decision(table, mesh):
    head, views = _views(table)
    if mesh == WHOLE:
        value = [head, sorted(views.items())]
    else:
        value = [head, views.get(mesh)]
    return hashlib.sha256(json.dumps(value).encode()).hexdigest()


def rows(used):
    """{table: {mesh: decision SHA-256}} of the (table, mesh) pairs USED (a table read whole: its one row '*')."""
    out = {}
    for table, mesh in sorted(used):
        out.setdefault(table, set()).add(mesh)
    result = {}
    for table, meshes in out.items():
        try:
            result[table] = {mesh: _decision(table, mesh) for mesh in sorted({WHOLE} if WHOLE in meshes else meshes)}
        except (OSError, ValueError):
            result[table] = {WHOLE: None}       # unreadable: never matches
    return result


def whole_rows(tables=TABLES):
    """rows() of TABLES read whole (an entry found under a key that counted the tables whole)."""
    return rows({(table, WHOLE) for table in tables if _path(table).is_file()})


def matches(record):
    """True when every decision RECORD (rows()) names is the same in the tables now."""
    if not record:
        return True
    try:
        for table, meshes in record.items():
            for mesh, digest in meshes.items():
                if digest is None or _decision(table, mesh) != digest:
                    return False
    except (OSError, ValueError, AttributeError, TypeError):
        return False
    return True


def note_record(record):
    """Note a hit entry's recorded rows into the recorders active around it."""
    for table, meshes in (record or {}).items():
        for mesh in meshes:
            note(table, mesh)
