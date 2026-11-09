"""Per-model face overrides (NPC-BODY-REGRESSION-62, CREATURE-MESH-HOLES-62): the only way a baked actor model gets
more faces than its class budget gives it.

config/model-face-overrides.json, in the repo as the shipped default (the public builder builds what ships). Each
entry names one model and what it may add on top of today's total:

    {"model": "nels llendo", "kind": "npc", "extra_faces": 19, "reason": "...",
     "cost": {"before": 488, "added": 19, "total": 507}, "pi_check": "pending" | "passed <date> <bench>"}

model: the NPC record id (kind npc) or the creature's mesh path as the creature library keys it (kind creature,
e.g. r/duskyalit.nif). npc_geometry.bake and creature_library.checked_bake read extra_faces(model, kind) here and
nowhere else; tests/test_model_face_overrides.py keeps the file valid and checks that a bake without an entry never
grows past its total.
"""
import json
from pathlib import Path

OVERRIDES_PATH = Path(__file__).resolve().parents[1] / 'config/model-face-overrides.json'
KINDS = ('npc', 'creature')
_cache = {}


def load(path=None):
    """{(kind, model): entry} of the override file, validated (ValueError naming the entry)."""
    path = Path(path or OVERRIDES_PATH)
    key = str(path)
    if key in _cache:
        return _cache[key]
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('schema') != 1 or not isinstance(data.get('entries'), list):
        raise ValueError('model-face-overrides: schema 1 with an entries list expected')
    out = {}
    for entry in data['entries']:
        name = str(entry.get('model', '')).strip().lower()
        kind = entry.get('kind')
        extra = entry.get('extra_faces')
        cost = entry.get('cost') or {}
        if not name or kind not in KINDS:
            raise ValueError('model-face-overrides: entry without model or kind: %r' % entry)
        if type(extra) is not int or extra <= 0:
            raise ValueError('model-face-overrides: %s: extra_faces must be a positive integer' % name)
        if not str(entry.get('reason', '')).strip():
            raise ValueError('model-face-overrides: %s: a reason is required' % name)
        if not all(type(cost.get(k)) is int for k in ('before', 'added', 'total')) or \
                cost['before'] + cost['added'] != cost['total'] or cost['added'] > extra:
            raise ValueError('model-face-overrides: %s: cost must be before + added = total, added <= extra_faces' % name)
        if not str(entry.get('pi_check', '')).strip():
            raise ValueError('model-face-overrides: %s: pi_check (pending or the bench that passed) is required' % name)
        if (kind, name) in out:
            raise ValueError('model-face-overrides: %s listed twice' % name)
        out[(kind, name)] = entry
    _cache[key] = out
    return out


SEAM_BASELINE_PATH = Path(__file__).resolve().parents[1] / 'config/mesh-seam-baseline.json'


def load_seam_baseline(path=None):
    """{'npc:<record id>' | 'creature:<mesh>': {'uncovered', 'least_width', 'date'}} of config/mesh-seam-baseline.json:
    today's known seam failures (npc_geometry.seam_stop, the ratchet). A model listed here may fail as far as its
    line, never further; written by tools/mesh_seam_baseline.py from a sweep, never by hand. Missing file: {}."""
    path = Path(path or SEAM_BASELINE_PATH)
    key = 'baseline:' + str(path)
    if key in _cache:
        return _cache[key]
    out = {}
    if path.is_file():
        data = json.loads(path.read_text(encoding='utf-8'))
        if data.get('schema') != 1 or not isinstance(data.get('models'), dict) or not str(data.get('reason', '')).strip() \
                or not str(data.get('date', '')).strip():
            raise ValueError('mesh-seam-baseline: schema 1 with a date, a reason and a models map expected')
        for name, line in data['models'].items():
            if ':' not in name or type(line.get('uncovered')) is not int or line['uncovered'] < 0 or \
                    not isinstance(line.get('least_width', 1.0), (int, float)):
                raise ValueError('mesh-seam-baseline: %s: kind:model with uncovered (int) and least_width' % name)
            out[name.strip().lower()] = dict(line, date=line.get('date', data['date']))
    _cache[key] = out
    return out


HEAD_FLOORS_PATH =Path(__file__).resolve().parents[1] / 'config/model-head-floors.json'
HEAD_FLOOR_RANGE = (40, 119)     # a per-model floor is lower than the default 120 and keeps a head


def load_head_floors(path=None):
    """{model: entry} of config/model-head-floors.json, validated (ValueError naming the entry). A per-model head
    trim floor below the default (npc_geometry.HEAD_TRIM_FLOOR): the head may give faces down to it so the seams
    fit inside today's total with no added faces. An entry is data only when its measured bake passed: 0 uncovered
    openings and every limb at 0.5 or more; the bake's seam stop still judges every bake that reads it."""
    path = Path(path or HEAD_FLOORS_PATH)
    key = 'floors:' + str(path)
    if key in _cache:
        return _cache[key]
    out = {}
    if path.is_file():
        data = json.loads(path.read_text(encoding='utf-8'))
        if data.get('schema') != 1 or not isinstance(data.get('entries'), list):
            raise ValueError('model-head-floors: schema 1 with an entries list expected')
        for entry in data['entries']:
            name = str(entry.get('body', '')).strip().lower()
            floor = entry.get('head_floor')
            measured = entry.get('measured') or {}
            cost = entry.get('cost') or {}
            if not name or type(floor) is not int or not HEAD_FLOOR_RANGE[0] <= floor <= HEAD_FLOOR_RANGE[1]:
                raise ValueError('model-head-floors: %r: body (head part id|hair part id) and a head_floor of %d-%d required' % (
                    entry, *HEAD_FLOOR_RANGE))
            if not str(entry.get('reason', '')).strip():
                raise ValueError('model-head-floors: %s: a reason is required' % name)
            if measured.get('uncovered_openings') != 0 or not (measured.get('least_width', 0) >= 0.5):
                raise ValueError('model-head-floors: %s: only a bake measured with 0 uncovered openings and every '
                                 'limb at 0.5 or more may be listed' % name)
            if not all(type(cost.get(k)) is int for k in ('before', 'total')) or cost['total'] > cost['before']:
                raise ValueError('model-head-floors: %s: cost before / total, total at most before (no added faces)'
                                 % name)
            if name in out:
                raise ValueError('model-head-floors: %s listed twice' % name)
            out[name] = entry
    _cache[key] = out
    return out


def body_key(appearance):
    """The body appearance a head floor is keyed by: the head and the hair (or helmet-less hair) body part ids,
    'head|hair' (every NPC sharing that head and hair gets the entry), or None without a head part."""
    parts = {p.get('slot'): str(p.get('id', '')).strip().lower() for p in (appearance or {}).get('parts', [])}
    if not parts.get(0):
        return None
    return parts[0] + '|' + parts.get(1, '')


def head_floor(body, path=None):
    """The head trim floor of a BODY key (body_key) from config/model-head-floors.json, or None (the default)."""
    if not body:
        return None
    entry = load_head_floors(path).get(str(body).strip().lower())
    return int(entry['head_floor']) if entry else None


def extra_faces(model, kind='npc', path=None):
    """The faces MODEL may add over its total (0 without an entry)."""
    if not model:
        return 0
    entry = load(path).get((kind, str(model).strip().lower()))
    return int(entry['extra_faces']) if entry else 0
