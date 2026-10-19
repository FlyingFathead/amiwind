#!/usr/bin/env python3
"""Editor markers at the builder input, and the island-wide audit (COLLISION-NC-FLAGS-32).

Decided for the project, 18 October 2026: Morrowind's editor markers are ignored by
default wherever they are placed, filtered out before any rendering. The rules are in
src/mwad/markers.py (learned from OpenMW 0.51, own implementation).

What this file does:

- EditorMarkers(data_files) classifies a placement: None (an ordinary model) or a
  marker kind. A hidden marker (northmarker, prisonmarker, divinemarker,
  templemarker) has no model in the game; an MRK model whose only drawn shape is
  the "Tri EditorMarker" is an invisible object (a sound or script activator, a
  particle effect, an invisible collision box).
- marker_status(ref, kind) is the deferred status a converter records for it: the
  placement leaves the drawn scenery but stays as an invisible record with its role
  (sound, effect, collision, script), for the stages that use those roles.
- `census` counts, per cell, the marker placements and the MRK models in the
  original data (every master and archive found).
- `check-built RUN` fails (exit 1) when a built world draws any marker: a CHIM
  frame or scenery index that places an MRK-only model or a hidden marker, or a
  converted model that still holds a "Tri EditorMarker" shape.
"""
import argparse
from collections import Counter, defaultdict
import io
import json
from pathlib import Path
import re
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from mwad.audit import BSA, cell_data, normpath, records, string, subrecords  # noqa: E402
from mwad.esm import GAME_ARCHIVES, GAME_MASTERS, is_deleted  # noqa: E402
from mwad.markers import (HIDDEN_MARKER_IDS, MARKER_KINDS, MARKER_SHAPE_PREFIX, is_hidden_marker,  # noqa: E402
                          is_marker_shape,
                          may_carry_marker, root_marked)
from mwad.paths import child_ci  # noqa: E402

PARTICLE_TYPES = ('NiParticles', 'NiAutoNormalParticles', 'NiRotatingParticles', 'NiParticleSystemController')
# A script that plays a sound makes its activator a sound emitter (PlayLoopSound3D / PlaySound3D and the VP forms).
SOUND_CALLS = ('playloopsound3d', 'playsound3d', 'playsound ', 'playloopsound')


def model_marker_info(raw, N=None):
    """What an MRK model draws and collides with once its marker shapes are gone.

    Returns None for a model that is not MRK-marked, else a dict: drawn_shapes (shapes
    still drawn), marker_shapes (names), marker_triangles, collision_shapes (RootCollisionNode
    shapes kept), particles (True when the model emits particles)."""
    if not may_carry_marker(raw):
        return None
    if N is None:
        from prepare_scenery import nif_reader
        N = nif_reader()
    data = N.Data()
    data.read(io.BytesIO(raw))
    if not root_marked(data.roots, N.NiStringExtraData):
        return None
    info = {'drawn_shapes': 0, 'marker_shapes': [], 'marker_triangles': 0, 'collision_shapes': 0,
            'particles': any(type(b).__name__ in PARTICLE_TYPES for b in data.get_global_iterator())}

    def walk(node, hidden, in_collision):
        if not isinstance(node, N.NiAVObject):
            return
        name = node.name.decode('cp1252')
        in_collision = in_collision or isinstance(node, N.RootCollisionNode) or name.casefold() == 'rootcollisionnode'
        hidden = hidden or bool(node.flags & 1)
        if isinstance(node, N.NiTriShape):
            tris = int(node.data.num_triangles) if node.data else 0
            if is_marker_shape(name, True):
                info['marker_shapes'].append(name)
                info['marker_triangles'] += tris
            elif in_collision:
                info['collision_shapes'] += bool(tris)
            elif not hidden and tris:
                info['drawn_shapes'] += 1
        for child in getattr(node, 'children', []):
            if child is not None:
                walk(child, hidden, in_collision)
    for root in data.roots:
        walk(root, False, False)
    return info


def marker_kind(object_id, record_type, info, script_text=''):
    """The marker kind of one placement, or None when it is drawn normally."""
    if is_hidden_marker(object_id):
        return 'hidden marker'
    if info is None or info['drawn_shapes']:
        return None
    if info['particles']:
        return 'effect emitter'
    if info['collision_shapes']:
        return 'collision marker'
    text = (script_text or '').casefold()
    if any(call in text for call in SOUND_CALLS):
        return 'sound emitter'
    return 'script marker' if record_type == 'ACTI' else 'marker object'


def marker_status(kind):
    """The deferred status a converter records for a marker placement."""
    return 'editor marker (not drawn): ' + kind


class EditorMarkers:
    """The placement classifier every converter path shares, cached per model.

    Models are read from the base archive first, as the scenery converter reads them
    (prepare_scenery.export_refs), then from the expansion archives."""

    def __init__(self, data_files, masters=GAME_MASTERS[:1]):
        """masters: the masters whose objects and scripts classify placements; the converters
        read the base master's placements (mwad.audit), the census passes every master."""
        # None: no game files (synthetic tests); only the id rule applies, models read as ordinary
        self.data = Path(data_files) if data_files is not None else None
        self.masters = tuple(masters)
        self._archives = None
        self._info = {}
        self._N = None

    def archives(self):
        if self._archives is None:
            self._archives = []
            if self.data is None:
                return self._archives
            for name in GAME_ARCHIVES:
                try:
                    path = child_ci(self.data, name)
                except (FileNotFoundError, ValueError):
                    continue
                if path.is_file():
                    self._archives.append(BSA(path))
        return self._archives

    def raw(self, model):
        name = normpath(model)
        if not name.startswith('meshes/'):
            name = 'meshes/' + name
        for bsa in self.archives():
            entry = bsa.entries.get(name)
            if entry:
                with bsa.path.open('rb') as stream:
                    stream.seek(entry['offset'])
                    return stream.read(entry['bytes'])
        loose = self.data / name if self.data is not None else None
        return loose.read_bytes() if loose is not None and loose.is_file() else None

    def info(self, model):
        key = normpath(model or '')
        if key not in self._info:
            raw = self.raw(key) if key else None
            if raw is None or not may_carry_marker(raw):
                self._info[key] = None
            else:
                if self._N is None:
                    from prepare_scenery import nif_reader
                    self._N = nif_reader()
                self._info[key] = model_marker_info(raw, self._N)
        return self._info[key]

    def records(self):
        """(objects, scripts, sounds) of the masters, read once per data folder (read_masters)."""
        _, objects, scripts, sounds, _ = read_masters(self.data, masters=self.masters)
        return objects, scripts, sounds

    def kind(self, ref):
        """Marker kind of a placement row (id, type, model as the audits write them), or None.

        A marker model's script decides between a sound emitter and a script marker; it is
        read from the masters only for such placements."""
        object_id = ref.get('id', '')
        if is_hidden_marker(object_id):
            return 'hidden marker'
        model = ref.get('model') or ''
        info = self.info(model) if model else None
        if info is None or info['drawn_shapes']:
            return None
        text = ref.get('script_text')
        if text is None:
            objects, scripts, _ = self.records() if self.data is not None else ({}, {}, {})
            script = (objects.get(object_id.casefold()) or {}).get('script', '')
            text = scripts.get(script, '') if script else ''
        return marker_kind(object_id, ref.get('type', ''), info, text)

    def emitter(self, ref, kind, cell=None, master=None):
        """The emitter-table row of a marker placement."""
        objects, scripts, sounds = self.records() if self.data is not None else ({}, {}, {})
        obj = objects.get(ref.get('id', '').casefold()) or {'type': ref.get('type'), 'model': ref.get('model', ''),
                                                            'script': ''}
        return emitter_row(ref, kind, obj, scripts, sounds, cell if cell is not None else ref.get('cell'), master)


def split_markers(references, markers):
    """(kept, deferred): marker placements leave the drawn list with their deferred status.

    The deferred rows keep the whole placement (position, object, role): only its marker
    shape and that shape's collision are gone."""
    kept, deferred = [], []
    for ref in references:
        kind = markers.kind(ref)
        if kind:
            deferred.append(dict(ref, status=marker_status(kind), editor_marker=kind))
        else:
            kept.append(ref)
    return kept, deferred


def area_emitters(deferred, markers, source):
    """The emitter table of an area's deferred marker placements (split_markers)."""
    rows = [markers.emitter(r, r['editor_marker']) for r in deferred if r.get('editor_marker')]
    rows.sort(key=lambda r: (str(r['cell']), r['reference']))
    return emitter_table(rows, source)


# ---------------------------------------------------------------- records

_RECORDS = {}

# Record types read for objects; the others carry no placed model, script or sound.
SKIPPED_TAGS = ('LAND', 'PGRD', 'DIAL', 'INFO', 'LTEX', 'REGN', 'SKIL', 'MGEF', 'GMST', 'GLOB', 'TES3',
                'CLAS', 'RACE', 'FACT', 'BSGN', 'SPEL', 'ENCH', 'SNDG')


def read_masters(data, with_cells=False, masters=GAME_MASTERS):
    """(masters, objects, scripts, sounds, cells) of every game master present, in load order.

    objects: id -> type, model, script; scripts: id -> text; sounds: id -> file, volume, ranges.
    Cells only with with_cells (the census); results are cached per data folder."""
    data = Path(data)
    key = (str(data.resolve()), with_cells, tuple(masters))
    if key in _RECORDS:
        return _RECORDS[key]
    wanted = tuple(masters)
    objects, scripts, sounds, cells, masters = {}, {}, {}, [], []
    for name in wanted:
        try:
            path = child_ci(data, name)
        except (FileNotFoundError, ValueError):
            continue
        if not path.is_file():
            continue
        masters.append(name)
        for tag, flags, payload in records(path.read_bytes()):
            if tag == 'CELL':
                if with_cells:
                    subs = list(subrecords(payload))
                    if not is_deleted(flags, subs, header_only=True):
                        cells.append((name, cell_data(subs)))
                continue
            if tag in SKIPPED_TAGS:
                continue
            fields = dict(subrecords(payload))
            if tag == 'SCPT':
                if 'SCHD' in fields:
                    scripts[string(fields['SCHD'][:32], errors='replace').casefold()] = string(
                        fields.get('SCTX', b''), errors='replace')
                continue
            if 'NAME' not in fields:
                continue
            key_id = string(fields['NAME'], errors='replace').casefold()
            if is_deleted(flags, fields):
                objects.pop(key_id, None)
                sounds.pop(key_id, None)
                continue
            if tag == 'SOUN':
                raw = fields.get('DATA', b'')
                volume, low, high = struct.unpack('<3B', raw[:3]) if len(raw) >= 3 else (255, 0, 255)
                sounds[key_id] = {'file': string(fields.get('FNAM', b''), errors='replace'),
                                  'volume': volume, 'min_range': low, 'max_range': high}
                continue
            objects[key_id] = {'type': tag, 'model': string(fields.get('MODL', b''), errors='replace'),
                               'script': string(fields.get('SCRI', b''), errors='replace').casefold()}
    result = (masters, objects, scripts, sounds, cells)
    _RECORDS[key] = result
    return result


SOUND_ARGUMENT = re.compile(r'play(?:loop)?sound3d(?:vp)?\s*,?\s*"([^"]+)"', re.I)


def script_sound(text):
    """The first sound a marker script plays (PlayLoopSound3D[VP] / PlaySound3D[VP] "<id>"), or None."""
    found = SOUND_ARGUMENT.search(text or '')
    return found.group(1) if found else None


# ---------------------------------------------------------------- emitter table

EMITTER_FORMAT = 'AmiWind marker emitters 1'
EMITTER_FIELDS = ('reference', 'master', 'cell', 'position', 'rotation', 'scale', 'kind', 'object', 'record_type',
                  'model', 'script', 'sound', 'sound_file', 'volume', 'min_range', 'max_range', 'effect_mesh')


def emitter_row(ref, kind, obj, scripts, sounds, cell, master=None):
    """One emitter-table row for a kept invisible marker placement (game data: build output only)."""
    obj = obj or {}
    script = obj.get('script', '')
    text = scripts.get(script, '') if script else ''
    sound_id = script_sound(text) if kind == 'sound emitter' else None
    sound = sounds.get(sound_id.casefold()) if sound_id else None
    model = normpath(obj.get('model', '')) or None
    return {'reference': ref.get('number'), 'master': master, 'cell': cell,
            'position': list(ref.get('position') or []), 'rotation': list(ref.get('rotation_radians') or []),
            'scale': ref.get('scale', 1.0), 'kind': kind, 'object': ref.get('id'), 'record_type': obj.get('type'),
            'model': model, 'script': script or None,
            'sound': sound_id, 'sound_file': sound['file'] if sound else None,
            'volume': sound['volume'] if sound else None,
            'min_range': sound['min_range'] if sound else None, 'max_range': sound['max_range'] if sound else None,
            'effect_mesh': model if kind == 'effect emitter' else None}


def emitter_table(rows, source):
    """The emitter table document, checked by validate_emitters."""
    doc = {'format': EMITTER_FORMAT, 'source': source,
           'note': 'Invisible editor-marker placements kept with their role (sound, effect, collision, script). '
                   'Units: original Morrowind world units; volume and ranges as the SOUN record stores them '
                   '(0-255). Not used by the engine yet.',
           'counts': dict(sorted(Counter(r['kind'] for r in rows).items())), 'emitters': rows}
    return validate_emitters(doc)


def validate_emitters(doc):
    """Schema check of an emitter table; raises ValueError naming the field and value."""
    if doc.get('format') != EMITTER_FORMAT:
        raise ValueError(f"emitters: format {doc.get('format')!r} != {EMITTER_FORMAT!r}")
    rows = doc.get('emitters')
    if not isinstance(rows, list):
        raise ValueError('emitters: emitters must be a list')
    for i, row in enumerate(rows):
        missing = [f for f in EMITTER_FIELDS if f not in row]
        if missing:
            raise ValueError(f'emitters[{i}]: missing fields {missing}')
        if row['kind'] not in MARKER_KINDS:
            raise ValueError(f"emitters[{i}].kind: {row['kind']!r}")
        if not isinstance(row['reference'], int) or isinstance(row['reference'], bool):
            raise ValueError(f"emitters[{i}].reference: {row['reference']!r}")
        if len(row['position']) != 3 or not all(isinstance(v, (int, float)) for v in row['position']):
            raise ValueError(f"emitters[{i}].position: {row['position']!r}")
        if row['kind'] == 'effect emitter' and not row['effect_mesh']:
            raise ValueError(f'emitters[{i}].effect_mesh: an effect emitter names its mesh')
        for f in ('volume', 'min_range', 'max_range'):
            if row[f] is not None and not (isinstance(row[f], int) and 0 <= row[f] <= 255):
                raise ValueError(f'emitters[{i}].{f}: {row[f]!r}')
        if row['sound_file'] is not None and not row['sound']:
            raise ValueError(f'emitters[{i}].sound: a sound file needs its sound id')
    if doc.get('counts') != dict(sorted(Counter(r['kind'] for r in rows).items())):
        raise ValueError(f"emitters: counts {doc.get('counts')!r} do not match the rows")
    return doc


def census(data):
    """Per-cell counts of marker placements in the original data, plus the MRK models."""
    data = Path(data)
    markers = EditorMarkers(data, masters=GAME_MASTERS)
    masters, objects, scripts, sounds, cells = read_masters(data, with_cells=True)
    # Only models some placement uses are read; MRK is found by bytes first, then parsed.
    per_cell = defaultdict(Counter)
    kinds = Counter()
    by_object = Counter()
    used_models = Counter()
    space = Counter()
    seen = {}
    by_master = Counter()
    emitters = []
    for master, cell in cells:
        interior = bool(cell['flags'] & 1)
        key = cell['name'] if interior else f"{cell['x']},{cell['y']}"
        for ref in cell['refs']:
            if ref.get('deleted'):
                continue
            obj = objects.get(ref.get('id', '').casefold())
            if obj is None:
                continue
            row = {'id': ref['id'], 'type': obj['type'], 'model': obj['model'],
                   'script_text': scripts.get(obj['script'], '')}
            kind = markers.kind(row)
            if not kind:
                continue
            ident = (master, 'interior' if interior else 'exterior', key, ref['number'])
            if ident in seen:
                continue
            seen[ident] = kind
            per_cell[('interior' if interior else 'exterior', key)][kind] += 1
            by_master[(master, kind)] += 1
            emitters.append(emitter_row(ref, kind, obj, scripts, sounds,
                                        key if interior else [cell['x'], cell['y']], master))
            kinds[kind] += 1
            space[('interior' if interior else 'exterior', kind)] += 1
            by_object[(ref['id'].casefold(), normpath(obj['model']), kind)] += 1
            if obj['model']:
                used_models[normpath(obj['model'])] += 1
    mrk_models = {}
    for bsa in markers.archives():
        for name, entry in bsa.entries.items():
            if not name.endswith('.nif'):
                continue
            with bsa.path.open('rb') as stream:
                stream.seek(entry['offset'])
                raw = stream.read(entry['bytes'])
            if not may_carry_marker(raw):
                continue
            info = model_marker_info(raw)
            if info is not None and name not in mrk_models:
                mrk_models[name] = dict(info, archive=bsa.path.name, placements=used_models.get(name[len('meshes/'):], 0))
    return {'format': 'AmiWind editor-marker census 1',
            'rules': 'src/mwad/markers.py (OpenMW 0.51 isHiddenMarker, nifloader MRK, bulletnifloader MRK)',
            'masters': masters, 'archives': [b.path.name for b in markers.archives()],
            'hidden_marker_ids': sorted(HIDDEN_MARKER_IDS),
            'placements': sum(kinds.values()), 'kinds': dict(kinds),
            'by_master': {f'{m}/{k}': n for (m, k), n in sorted(by_master.items())},
            'sound_emitters_without_sound': sum(1 for r in emitters if r['kind'] == 'sound emitter' and not r['sound_file']),
            'by_space': {f'{s}/{k}': n for (s, k), n in sorted(space.items())},
            'exterior_cells': sum(1 for s, _ in per_cell if s == 'exterior'),
            'interior_cells': sum(1 for s, _ in per_cell if s == 'interior'),
            'objects': [{'id': i, 'model': m, 'kind': k, 'placements': n}
                        for (i, m, k), n in by_object.most_common()],
            'mrk_models': mrk_models,
            'mesh_marker_nodes_in_drawn_models': sorted(n for n, i in mrk_models.items() if i['drawn_shapes']),
            'cells': {f'{s}:{c}': dict(v) for (s, c), v in sorted(per_cell.items(), key=lambda x: (x[0][0], str(x[0][1])))},
            'emitter_table': emitter_table(emitters, 'census of ' + ', '.join(masters))}


# ---------------------------------------------------------------- built-world check

def _models_of_index(index):
    return [normpath(m.get('source', '')) for m in index.get('models', [])]


def check_scenery_index(path, mrk_only):
    """Problems of one scenery-index.json: placed hidden markers / MRK-only models, kept marker shapes."""
    index = json.loads(Path(path).read_text(encoding='utf-8'))
    models = _models_of_index(index)
    problems = []
    for ref in index.get('references', []):
        model = models[ref['model_index']] if 0 <= ref.get('model_index', -1) < len(models) else ''
        if is_hidden_marker(ref.get('id')) or model in mrk_only:
            problems.append({'file': str(path), 'reference': ref.get('number'), 'id': ref.get('id'), 'model': model,
                             'cell': ref.get('cell'), 'check': 'editor marker placed in the drawn scenery'})
    for m in index.get('models', []):
        for mat in m.get('materials', []):
            if (mat.get('source_shape') or '').casefold().startswith(MARKER_SHAPE_PREFIX):
                problems.append({'file': str(path), 'model': m.get('source'), 'shape': mat.get('source_shape'),
                                 'check': 'Tri EditorMarker shape kept in a converted model'})
    return problems


def require_none_drawn(index, markers, where):
    """The builder check after a scenery export: no placement of the index is an editor marker and no
    converted model kept a marker shape; raises ValueError naming the unit, reference and check."""
    problems = []
    models = index.get('models', [])
    for ref in index.get('references', []):
        model = models[ref['model_index']]['source'] if 0 <= ref.get('model_index', -1) < len(models) else ''
        kind = markers.kind({'id': ref.get('id', ''), 'type': ref.get('type', ''), 'model': model})
        if kind:
            problems.append(f"reference {ref.get('number')} {ref.get('id')} ({kind}, {model})")
    for m in models:
        for mat in m.get('materials', []):
            if (mat.get('source_shape') or '').casefold().startswith(MARKER_SHAPE_PREFIX):
                problems.append(f"model {m.get('source')} kept shape {mat.get('source_shape')}")
    if problems:
        raise ValueError(f'{where}: editor markers would be drawn (COLLISION-NC-FLAGS-32): ' + '; '.join(problems[:20]))
    return len(index.get('references', []))


def check_built(run, census_doc=None, data=None):
    """Every scenery index of a run (towns, CHIM areas, rooms) checked; returns (files, problems)."""
    if census_doc is not None:
        mrk_only = {n for n, i in census_doc['mrk_models'].items() if not i['drawn_shapes']}
    elif data is not None:
        mrk_only = {n for n, i in census(data)['mrk_models'].items() if not i['drawn_shapes']}
    else:
        mrk_only = set()
    files, problems = 0, []
    for path in sorted(Path(run).rglob('scenery-index.json')):
        files += 1
        print(f'[editor-markers] checking {path}', flush=True)
        problems.extend(check_scenery_index(path, mrk_only))
    return files, problems


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = p.add_subparsers(dest='command', required=True)
    c = sub.add_parser('census', help='count marker placements and MRK models in the original data')
    c.add_argument('--data-files', type=Path, required=True)
    c.add_argument('--out', type=Path, help='write the census JSON here')
    c.add_argument('--emitters', type=Path, help='write the island-wide emitter table here (e.g. world/emitters.json)')
    b = sub.add_parser('check-built', help='fail when a built run draws an editor marker')
    b.add_argument('run', type=Path)
    b.add_argument('--census', type=Path, help='census JSON (else --data-files is read)')
    b.add_argument('--data-files', type=Path)
    a = p.parse_args(argv)
    if a.command == 'census':
        print('[editor-markers] census: reading masters and archives (one process; one pass over the data)', flush=True)
        doc = census(a.data_files)
        text = json.dumps(doc, indent=2) + '\n'
        if a.out:
            a.out.write_text(text, encoding='utf-8', newline='\n')
        if a.emitters:
            a.emitters.parent.mkdir(parents=True, exist_ok=True)
            a.emitters.write_text(json.dumps(doc['emitter_table'], indent=2) + '\n', encoding='utf-8', newline='\n')
        print(json.dumps({k: doc[k] for k in ('placements', 'kinds', 'by_space', 'by_master', 'exterior_cells',
                                             'interior_cells', 'sound_emitters_without_sound')}, indent=2))
        print('MRK models:', len(doc['mrk_models']), '; with other drawn shapes:', doc['mesh_marker_nodes_in_drawn_models'])
        return 0
    doc = json.loads(a.census.read_text(encoding='utf-8')) if a.census else None
    if doc is None and a.data_files is None:
        p.error('check-built needs --census or --data-files')
    files, problems = check_built(a.run, doc, a.data_files)
    print(json.dumps({'scenery_indexes': files, 'problems': len(problems)}, indent=2))
    for row in problems[:50]:
        print('[editor-markers] FAIL', json.dumps(row))
    return 1 if problems else 0


if __name__ == '__main__':
    raise SystemExit(main())
