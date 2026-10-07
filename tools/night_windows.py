#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Night window table: the BSP textures of each map that glow at night.

aw_night_window_lights makes window glass and lamp glass glow after dark (an
AmiWind extra; the original windows never glow). Converted maps name their
textures generically (surfaceN, emitN_N), so this tool traces each BSP
texture back to the original material:

  BSP func_wall entity "aw_ref" (original reference number) and "model" *N
  -> scenery index reference -> model -> its materials (texture source,
  diffuse, emissive) -> the BSP textures used by the faces of submodel N.

A texture's candidates are the material textures shared by every model whose
submodel uses it. Remaining ties are settled by comparing the BSP texture
pixels (through the palette) with each candidate texture from the scenery
archive. A texture glows only when every contributing original material is
window glass or lamp glass:

  window  the original texture is a window texture (name has "window", or
          starts "tx_win_"), or plain glass ("tx_glass_", not bottles,
          obsidian or the Sixth House glass) on an architecture model
          (ex_/in_ mesh, or a window mesh).
  lamp    a light-source model (LIGH placement) material whose original
          NiMaterial is emissive; when the scenery index predates the
          emissive field, --data-files reads it from your own Morrowind.bsa.

Output (--out, e.g. id1/world/night-windows.txt): one line per map with at
least one glowing texture: the map name (BSP file stem, lower case), then
its texture names, all separated by single spaces; maps and names sorted;
ASCII, LF line ends. A map without a line has no glowing textures.

Usage (reads your own converted maps and scenery caches; writes no game data):
  night_windows.py --maps DIR --scenery 'bm*=CACHE/scenery' \\
      --scenery 'sn*=OTHER/scenery' [--palette palette.lmp] \\
      [--data-files 'Data Files'] --out night-windows.txt [--report r.json]
Each --scenery PATTERN=DIR names a scenery-index.json (and optional
scenery.mwpak) a map set was converted from. A map uses every source whose
pattern matches its name, in the order given (town scenery first, then
overlays such as flora); maps that match none are skipped. --report lists per
map the window and lamp textures, their face counts, every unsettled texture
and any reference no source knows.
"""
import argparse, fnmatch, json, struct, sys
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

GLASS_EXCLUDED = ('bottle', 'obsidian', '6th')


def texture_stem(source):
    """'Tx_Glass_Amber_02.tga' or 'textures/tx_glass_amber_02.dds' -> 'tx_glass_amber_02'."""
    if not source: return ''
    return PurePosixPath(source.replace('\\', '/').lower()).stem


def model_stem(source):
    return PurePosixPath(source.replace('\\', '/').lower()).stem


def is_window_glass(texture_source, model_source):
    name = texture_stem(texture_source)
    if 'window' in name or name.startswith('tx_win_'):
        return True
    if not name.startswith('tx_glass_') or any(word in name for word in GLASS_EXCLUDED):
        return False
    model = model_stem(model_source)
    return model.startswith(('ex_', 'in_')) or 'window' in model or '_win_' in model


def material_kind(material, model, ref_types, emissive):
    """'window', 'lamp' or None for one original material of one model."""
    if is_window_glass(material.get('texture_source'), model['source']):
        return 'window'
    if 'LIGH' in ref_types and emissive:
        return 'lamp'
    return None


# --- BSP29 -----------------------------------------------------------------

def parse_entities(text):
    entities = []
    for block in text.split('{')[1:]:
        body = block.split('}')[0]; entity = {}
        for line in body.splitlines():
            parts = line.strip().split('"')
            if len(parts) >= 5: entity[parts[1]] = parts[3]
        entities.append(entity)
    return entities


def read_bsp(raw):
    """Texture names and pixels, face textures, submodel face ranges, entities."""
    if len(raw) < 124 or struct.unpack_from('<i', raw)[0] != 29:
        raise ValueError('Not a BSP29 map')
    lumps = []
    for k in range(15):
        offset, size = struct.unpack_from('<ii', raw, 4 + 8 * k)
        if offset < 0 or size < 0 or offset + size > len(raw): raise ValueError('BSP lump out of range')
        lumps.append(raw[offset:offset + size])
    tex = lumps[2]; textures = []
    count = struct.unpack_from('<i', tex)[0] if tex else 0
    for offset in struct.unpack_from('<%di' % count, tex, 4) if count else ():
        if offset < 0: textures.append({'name': None}); continue
        name, width, height, mip0 = struct.unpack_from('<16s3I', tex, offset)
        name = name.split(b'\0')[0].decode('ascii', 'replace')
        pixels = tex[offset + mip0:offset + mip0 + width * height] if mip0 else b''
        textures.append({'name': name, 'width': width, 'height': height, 'pixels': pixels})
    texinfo = [struct.unpack_from('<i', lumps[6], o + 32)[0] for o in range(0, len(lumps[6]) - 39, 40)]
    faces = [texinfo[struct.unpack_from('<H', lumps[7], o + 10)[0]] for o in range(0, len(lumps[7]) - 19, 20)]
    models = [struct.unpack_from('<2i', lumps[14], o + 56) for o in range(0, len(lumps[14]) - 63, 64)]
    text = lumps[0].split(b'\0')[0].decode('cp1252')
    return {'textures': textures, 'faces': faces, 'models': models, 'entities': parse_entities(text)}


# --- provenance ------------------------------------------------------------

def palette_rgb(palette):
    if len(palette) < 768: raise ValueError('Palette must hold 256 RGB entries')
    return [tuple(palette[i * 3:i * 3 + 3]) for i in range(256)]


def pixel_distance(texture, rgb, palette):
    """Mean absolute RGB difference between a BSP texture and a candidate."""
    import numpy as np
    from PIL import Image
    w, h = texture['width'], texture['height']
    have = np.array(palette, float)[np.frombuffer(texture['pixels'], np.uint8)].reshape(h, w, 3)
    want = np.asarray(Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).resize((w, h)), float)
    return float(np.abs(have - want).mean())


def classify_map(bsp, sources, palette=None):
    """Per BSP texture: original candidates, kind and face counts.

    sources: objects with .index (a scenery index), .texture_rgb(ti) and
    .emissive_of(model); a reference number resolves in the first source
    that lists it. Models and textures are keyed (source number, index).
    """
    refs = {}; ref_types = defaultdict(set)
    for s, source in enumerate(sources):
        own = defaultdict(set)
        for ref in source.index['references']:
            own[int(ref['number'])].add(ref['model_index'])
            ref_types[s, ref['model_index']].add(ref.get('type'))
        for number, models in own.items():
            refs.setdefault(number, {(s, mi) for mi in models})
    def model(key): return sources[key[0]].index['models'][key[1]]
    def texture_source(key):
        return '(untextured)' if key[1] is None else sources[key[0]].index['textures'][key[1]]['source']
    names = [t['name'] for t in bsp['textures']]
    model_faces = [Counter(bsp['faces'][first:first + count]) for first, count in bsp['models']]
    static_faces = Counter(bsp['faces'])
    users = defaultdict(set); drawn = Counter(); unresolved = []; untraced = set()
    for entity in bsp['entities']:
        if entity.get('classname') != 'func_wall' or 'aw_ref' not in entity: continue
        submodel = int(entity.get('model', '*0')[1:] or 0)
        models = refs.get(int(entity['aw_ref']), set())
        if len(models) != 1 or not 0 < submodel < len(model_faces):
            unresolved.append(entity['aw_ref'])
            if 0 < submodel < len(model_faces): untraced.update(model_faces[submodel])
            continue
        key = next(iter(models))
        for t, n in model_faces[submodel].items():
            users[t].add(key); drawn[t] += n
    def emissive(key, k, material):
        if 'emissive' in material: return int(material['emissive'])
        return sources[key[0]].emissive_of(model(key))[k]
    result = {}; emissive_unknown = set()
    for t, keys in sorted(users.items()):
        name = names[t]
        if not name or name.startswith('flat'): continue
        candidates = None
        for key in keys:
            slots = {(key[0], m.get('texture_index')) for m in model(key)['materials']}
            candidates = slots if candidates is None else candidates & slots
        scores = {}
        if candidates and len(candidates) > 1 and palette and bsp['textures'][t].get('pixels'):
            import numpy as np
            for tkey in candidates:
                rgb = sources[tkey[0]].texture_rgb(tkey[1]) if tkey[1] is not None else None
                if rgb is None: continue
                diffuses = {tuple(m.get('diffuse', (1., 1., 1.))) for key in keys
                            for m in model(key)['materials'] if (key[0], m.get('texture_index')) == tkey}
                scores[tkey] = min(pixel_distance(bsp['textures'][t], rgb * np.array(d), palette) for d in diffuses)
            if len(scores) == len(candidates):
                candidates = {min(scores, key=scores.get)}
        contributing = []; kinds = set()
        for key in sorted(keys):
            m = model(key)
            for k, material in enumerate(m['materials']):
                if (key[0], material.get('texture_index')) not in (candidates or ()): continue
                glow = emissive(key, k, material) if 'LIGH' in ref_types[key] else 0
                if glow is None: emissive_unknown.add(m['source'])
                kind = material_kind(material, m, ref_types[key], glow)
                kinds.add(kind)
                contributing.append({'model': m['source'], 'texture': texture_stem(material.get('texture_source')),
                                     'shape': material.get('source_shape'), 'emissive': glow, 'kind': kind})
        if not candidates: status = 'inconsistent'
        elif len(candidates) > 1: status = 'ambiguous'
        elif len(kinds) > 1: status = 'mixed'
        else: status = 'resolved'
        result[name] = {'kind': next(iter(kinds)) if status == 'resolved' else None, 'status': status,
                        'sources': sorted({texture_source(k) for k in candidates or ()}),
                        'faces': static_faces[t], 'drawn_faces': drawn[t],
                        'pixel_distance': {texture_source(k): round(v, 2) for k, v in scores.items()},
                        'contributing': contributing}
    # Textures seen only on references no index knows stay dark; list them so
    # a stale index never hides glass silently.
    return {'textures': result, 'unresolved_refs': sorted(set(unresolved)),
            'untraced_textures': sorted(names[t] for t in untraced - set(users)
                                        if names[t] and not names[t].startswith('flat')),
            'emissive_unknown': sorted(emissive_unknown)}


def glowing(classified):
    return sorted(name for name, info in classified['textures'].items() if info['kind'] in ('window', 'lamp'))


def table_text(rows):
    """rows: {map name: [texture names]} -> the night window table text."""
    lines = []
    for name in sorted(rows):
        textures = sorted(set(rows[name]))
        if not textures: continue
        for word in (name, *textures):
            if not word or any(c.isspace() for c in word) or not word.isascii(): raise ValueError('Bad table word: ' + repr(word))
        lines.append(' '.join([name.lower(), *textures]))
    return ''.join(line + '\n' for line in lines)


def parse_table(text):
    rows = {}
    for line in text.splitlines():
        words = line.split()
        if words: rows[words[0]] = words[1:]
    return rows


# --- original data ---------------------------------------------------------

class ScenerySource:
    """A scenery-index.json with its optional scenery.mwpak texture archive."""
    def __init__(self, directory, data_files=None):
        self.directory = Path(directory)
        self.index = json.loads((self.directory / 'scenery-index.json').read_text(encoding='utf-8'))
        self.archive = self.directory / 'scenery.mwpak'
        self.data_files = data_files; self._rgb = {}; self._emissive = {}; self._bsa = None

    def texture_rgb(self, ti):
        if not self.archive.is_file(): return None
        if ti not in self._rgb:
            import numpy as np
            from mwad.scene import read_asset
            with self.archive.open('rb') as f: raw = read_asset(f, self.index['textures'][ti])
            magic, w, h = struct.unpack_from('>4sHH', raw)
            if magic != b'MWT1': raise ValueError('Unknown scenery texture payload')
            self._rgb[ti] = np.frombuffer(raw[8:], np.uint8).reshape(h, w, 4)[:, :, :3].astype(float)
        return self._rgb[ti]

    def emissive_of(self, model):
        """Original NiMaterial emissive per material, read from your own BSA."""
        if self.data_files is None: return [None] * len(model['materials'])
        source = model['source']
        if source not in self._emissive:
            import hashlib
            from mwad.audit import BSA
            from mwad.paths import child_ci
            from prepare_scenery import nif_reader, model_geometry, bsa_read
            if self._bsa is None: self._bsa = BSA(child_ci(Path(self.data_files), 'Morrowind.bsa'))
            raw = bsa_read(self._bsa, source)
            if model.get('source_sha256') and hashlib.sha256(raw).hexdigest() != model['source_sha256']:
                raise ValueError('Model differs from the converted one: ' + source)
            materials = model_geometry(raw, nif_reader())[1]
            if [m['texture_source'] for m in materials] != [m['texture_source'] for m in model['materials']]:
                raise ValueError('Material order differs from the converted model: ' + source)
            self._emissive[source] = [int(m['emissive']) for m in materials]
        return self._emissive[source]


def build(maps, sources, palette=None):
    """maps: [(name, bsp bytes)]; sources: [(pattern, ScenerySource)].

    Every source whose pattern matches a map name is used for that map, in
    the order given (a reference resolves in the first source listing it).
    """
    rows = {}; report = {}
    for name, raw in maps:
        matching = [s for pattern, s in sources if fnmatch.fnmatch(name, pattern)]
        if not matching:
            report[name] = {'skipped': 'no scenery source pattern matches'}; continue
        classified = classify_map(read_bsp(raw), matching, palette)
        rows[name] = glowing(classified)
        info = classified['textures']
        def total(kind, key):
            return sum(v[key] for v in info.values() if v['kind'] == kind)
        report[name] = {'scenery': [str(s.directory) for s in matching], 'glowing': rows[name],
                        'window_textures': sorted(n for n, v in info.items() if v['kind'] == 'window'),
                        'lamp_textures': sorted(n for n, v in info.items() if v['kind'] == 'lamp'),
                        'window_faces': total('window', 'faces'), 'window_drawn_faces': total('window', 'drawn_faces'),
                        'lamp_faces': total('lamp', 'faces'), 'lamp_drawn_faces': total('lamp', 'drawn_faces'),
                        'unsettled': {n: v['status'] for n, v in info.items() if v['status'] != 'resolved'},
                        **{k: classified[k] for k in ('unresolved_refs', 'untraced_textures', 'emissive_unknown')},
                        'textures': info}
    return rows, report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--maps', type=Path, required=True, help='directory of converted .bsp maps')
    p.add_argument('--scenery', action='append', default=[], required=True, metavar='PATTERN=DIR')
    p.add_argument('--palette', type=Path, help='palette.lmp; settles ties by pixels')
    p.add_argument('--data-files', type=Path, help='your Morrowind Data Files, for lamp emissive')
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--report', type=Path)
    a = p.parse_args(argv)
    sources = []; loaded = {}
    for item in a.scenery:
        pattern, sep, directory = item.partition('=')
        if not sep or not pattern or not directory: p.error('--scenery takes PATTERN=DIR')
        if directory not in loaded: loaded[directory] = ScenerySource(directory, a.data_files)
        sources.append((pattern.lower(), loaded[directory]))
    palette = palette_rgb(a.palette.read_bytes()) if a.palette else None
    maps = [(f.stem.lower(), f.read_bytes()) for f in sorted(a.maps.glob('*.bsp'))]
    rows, report = build(maps, sources, palette)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_bytes(table_text(rows).encode('ascii'))
    if a.report:
        a.report.write_bytes((json.dumps(report, indent=1, sort_keys=True) + '\n').encode('utf-8'))
    for name in sorted(report):
        r = report[name]
        if 'skipped' in r: continue
        print('%-14s windows %d tex %d faces | lamps %d tex %d faces | unsettled %d | unresolved refs %d' % (
            name, len(r['window_textures']), r['window_faces'], len(r['lamp_textures']), r['lamp_faces'],
            len(r['unsettled']), len(r['unresolved_refs'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
