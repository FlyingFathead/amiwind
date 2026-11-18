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


def _layer_names(table, text):
    """The expansion layers a layer-row table (build_cache.LAYER_ROW_TABLES) names, sorted; () for any other table."""
    from build_cache import LAYER_ROW_TABLES
    if LAYER_ROW_TABLES.get(name(_path(table))) is None:
        return ()
    try:
        layers = json.loads(text).get('layers')
    except ValueError:
        return ()
    return tuple(sorted(layers)) if isinstance(layers, dict) else ()


def _base_text(table, text, drop=None):
    """TEXT of a layer-row table (build_cache.LAYER_ROW_TABLES) without the rows of the expansion layers DROP (default:
    every layer it names): the table as it was before those rows (NPC-LIBRARY-NO-UNIT-CACHE-63); TEXT itself for any
    other table."""
    from build_cache import LAYER_ROW_TABLES, layer_table_view
    spec = LAYER_ROW_TABLES.get(name(_path(table)))
    if spec is None:
        return text
    layers = _layer_names(table, text)
    if not layers:
        return text
    return layer_table_view(text, set(layers) if drop is None else set(drop) & set(layers), *spec)


def _layer_subsets(table):
    """Every non-empty set of the table's expansion layers, the whole set first: the tables an entry may have been
    recorded on before some of today's layer rows were added (MESH-TABLE-SECOND-LAYER-REKEY-67: an entry recorded with
    the Bloodmoon rows read no Tribunal row added later)."""
    import itertools
    layers = _layer_names(table, _path(table).read_text(encoding='utf-8'))
    return [frozenset(c) for n in range(len(layers), 0, -1) for c in itertools.combinations(layers, n)]


def _views(table, base=False):
    """(format text, {mesh: decision}) of a table as it is on disk now (cached by its bytes' SHA-256); BASE: True for
    the table without its expansion layers' rows (_base_text), or a set of layer names for the table without the
    rows of those layers only."""
    raw = _path(table).read_bytes()
    if base:
        raw = _base_text(table, raw.decode('utf-8'), None if base is True else base).encode('utf-8')
    digest = hashlib.sha256(raw).hexdigest()
    known = _VIEWS.get((table, base))
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
    _VIEWS[(table, base)] = (digest, result)
    return result


def _decision(table, mesh, base=False):
    head, views = _views(table, base)
    if mesh == WHOLE:
        value = [head, sorted(views.items())]
    else:
        value = [head, views.get(mesh)]
    return hashlib.sha256(json.dumps(value).encode()).hexdigest()


def _recipe_rows_only(table, mesh, drop):
    """True when MESH's decision in the table without the layers DROP differs from today's by recipe rows only: the
    mesh is no row of those layers itself, the layers only list it for their own visual recipes (the table's
    "layer_recipes"). A unit in a cell of another recipe never read those rows; a cell of the layer's own recipe has
    that recipe in its key."""
    now = json.loads(_views(table)[1].get(mesh) or '{}')
    then = json.loads(_views(table, drop)[1].get(mesh) or '{}')
    now.pop('recipes', None)
    then.pop('recipes', None)
    return now == then


_SHORTER = {}


def _shorter_layer_decisions(table):
    """The whole-table decisions of the table as it was when its expansion layers were SHORTER: for each layer, only
    the first k rows of its list (k = 0: the layer and the recipe blocks it owns not there at all), in every
    combination over the layers. A layer's list is append-only, in the order the rows were added
    (MESH-TABLE-LAYER-GROWS-67), so one of these is the table an entry was recorded on before the rows added since;
    it read none of them. Cached by the table's bytes."""
    import itertools
    raw = _path(table).read_bytes()
    stamp = hashlib.sha256(raw).hexdigest()
    known = _SHORTER.get(table)
    if known is not None and known[0] == stamp:
        return known[1]
    data = json.loads(raw.decode('utf-8'))
    head, views = _views(table)
    layers = data.get('layers') if isinstance(data.get('layers'), dict) else {}
    owned = data.get('layer_recipes') if isinstance(data.get('layer_recipes'), dict) else {}
    parsed = {mesh: json.loads(view) for mesh, view in views.items()}
    found = set()
    names = sorted(layers)
    for lengths in itertools.product(*[range(len(layers[name]) + 1) for name in names]):
        if all(k == len(layers[name]) for k, name in zip(lengths, names)):
            continue                                    # the table as it is
        gone = {norm(mesh) for k, name in zip(lengths, names) for mesh in list(layers[name])[k:]}
        recipes = {str(r) for k, name in zip(lengths, names) if k == 0 for r in owned.get(name, ())}
        items = []
        for mesh, view in parsed.items():
            if mesh in gone or (recipes and 'recipes' in view):
                view = dict(view)
                if mesh in gone:
                    view.pop('listed', None)
                if recipes and 'recipes' in view:
                    kept = [r for r in view['recipes'] if r not in recipes]
                    if kept:
                        view['recipes'] = kept
                    else:
                        del view['recipes']
                if not view:
                    continue
                items.append((mesh, json.dumps(view, sort_keys=True)))
            else:
                items.append((mesh, views[mesh]))
        found.add(hashlib.sha256(json.dumps([head, sorted(items)]).encode()).hexdigest())
    _SHORTER[table] = (stamp, found)
    return found


def _shorter_layers_match(table, digest):
    """True when the whole-table DIGEST is the table's with shorter expansion layers (a layer-row table only)."""
    if not _layer_names(table, _path(table).read_text(encoding='utf-8')):
        return False
    return digest in _shorter_layer_decisions(table)


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
    """True when every decision RECORD (rows()) names is the same in the tables now. A whole-table row ('*') also
    matches the table without its expansion layers' rows (build_cache.LAYER_ROW_TABLES): an entry recorded before a
    layer's rows were added read only the base rows, and those are unchanged (NPC-LIBRARY-NO-UNIT-CACHE-63: the
    Bloodmoon rows of the hull-surface table missed all 418 NPC appearances and the creature models, whose bakes
    never read them). The same holds layer by layer: an entry recorded with one layer's rows matches the table
    without the rows of the layers added since (any set of the table's layers left out,
    MESH-TABLE-SECOND-LAYER-REKEY-67), and row by row within a layer: a layer's list is append-only, and an entry
    recorded when the layer was shorter matches the table without the rows appended since
    (_shorter_layer_decisions, MESH-TABLE-LAYER-GROWS-67: Solstheim's 71 rows under the Bloodmoon layer would have
    missed every NPC appearance and creature model recorded with its first 25). A base row changed still misses,
    and so does a layer row changed, removed or put anywhere but the end; a mesh row is compared as it is, except for the rows a layer lists for its own visual recipes
    only (_recipe_rows_only: a base game mesh that needs the rule in Mournhold's districts keeps every entry of the
    cells that place it elsewhere)."""
    if not record:
        return True
    try:
        for table, meshes in record.items():
            for mesh, digest in meshes.items():
                if digest is None:
                    return False
                if _decision(table, mesh) == digest:
                    continue
                if any(_decision(table, mesh, drop) == digest
                       and (mesh == WHOLE or _recipe_rows_only(table, mesh, drop))
                       for drop in _layer_subsets(table)):
                    continue
                if mesh != WHOLE or not _shorter_layers_match(table, digest):
                    return False
    except (OSError, ValueError, AttributeError, TypeError):
        return False
    return True


def note_record(record):
    """Note a hit entry's recorded rows into the recorders active around it."""
    for table, meshes in (record or {}).items():
        for mesh in meshes:
            note(table, mesh)
