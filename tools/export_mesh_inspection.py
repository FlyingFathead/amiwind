#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Export locally owned BSP v29 geometry for the offline polycount inspector.

Indexed texture pixels are exported when embedded in the BSP. The resulting
scene contains derived game assets and must remain private for proprietary inputs.
"""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path
import re
import struct


def extract(raw, source):
    if len(raw) > 128 * 1024 * 1024:
        raise ValueError('BSP exceeds 128 MiB inspection limit')
    if len(raw) < 124 or struct.unpack_from('<i', raw)[0] != 29:
        raise ValueError('Expected BSP version 29')
    lumps = []
    for i in range(15):
        offset, size = struct.unpack_from('<ii', raw, 4 + i * 8)
        if offset < 124 or size < 0 or offset + size > len(raw):
            raise ValueError(f'Invalid lump {i}')
        lumps.append(raw[offset:offset + size])
    def records(i, fmt):
        if len(lumps[i]) % struct.calcsize(fmt):
            raise ValueError(f'Misaligned lump {i}')
        return list(struct.iter_unpack(fmt, lumps[i]))
    vertices = records(3, '<3f')
    if len(vertices) > 2_000_000:
        raise ValueError('BSP exceeds two million vertices')
    if any(not all(map(math.isfinite, vertex)) for vertex in vertices):
        raise ValueError('Non-finite BSP vertex')
    edges = records(12, '<HH')
    surfedges = [x[0] for x in records(13, '<i')]
    faces = records(7, '<HhihH4Bi')
    planes = records(1, '<4fi')
    models = records(14, '<9f7i')
    texinfos = records(6, '<8fii')
    if any(not all(map(math.isfinite, info[:8])) for info in texinfos):
        raise ValueError('Non-finite texinfo vectors')
    textures = extract_textures(lumps[2])
    entities = [dict(re.findall(r'"([^"\n]*)"\s*"([^"\n]*)"', block))
                for block in re.findall(r'\{([^{}]*)\}', lumps[0].decode('cp1252'))]
    result, total_vertices = [], 0
    def build(model_id, entity, entity_index=0, override=None):
        nonlocal total_vertices
        if len(result) >= 10_000:
            raise ValueError('Scene exceeds ten thousand placements')
        if not 0 <= model_id < len(models):
            raise ValueError('Model index outside table')
        first, count = models[model_id][14:16] if override is None else override
        if first < 0 or count < 0 or first + count > len(faces):
            raise ValueError('Invalid model face range')
        origin = list(map(float, entity.get('origin', '0 0 0').split()))
        angle = list(map(float, entity.get('angles', '0 ' + entity.get('angle', '0') + ' 0').split()))
        if len(origin) != 3 or len(angle) != 3 or not all(map(math.isfinite, origin + angle)):
            raise ValueError('Invalid placement transform')
        p, y, r = map(math.radians, angle)
        sp, cp, sy, cy, sr, cr = math.sin(p), math.cos(p), math.sin(y), math.cos(y), math.sin(r), math.cos(r)
        basis = ((cp*cy, cp*sy, -sp), (sr*sp*cy-cr*sy, sr*sp*sy+cr*cy, sr*cp),
                 (cr*sp*cy+sr*sy, cr*sp*sy-sr*cy, cr*cp))
        used, placed, lines, triangles, materials, polygons = {}, [], set(), [], set(), []
        def vertex(j):
            if not 0 <= j < len(vertices):
                raise ValueError('Vertex outside table')
            if j not in used:
                used[j] = len(placed)
                v = vertices[j]
                placed.append([origin[a] + sum(v[k] * basis[k][a] for k in range(3)) for a in range(3)])
            return used[j]
        for face in faces[first:first + count]:
            start, n, tex = face[2:5]
            if start < 0 or n < 3 or start + n > len(surfedges):
                raise ValueError('Invalid face edge range')
            materials.add(tex)
            poly = []
            for signed in surfedges[start:start + n]:
                if abs(signed) >= len(edges):
                    raise ValueError('Edge outside table')
                poly.append(vertex(edges[abs(signed)][0 if signed >= 0 else 1]))
            lines.update(tuple(sorted((poly[i], poly[(i + 1) % n]))) for i in range(n))
            triangles.extend((poly[0], poly[i], poly[i + 1]) for i in range(1, n - 1))
            polygon = dict(vertices=poly, texinfo=tex, lightmapped=face[-1] >= 0)
            if planes:
                if face[0] >= len(planes) or not all(map(math.isfinite, planes[face[0]][:4])):
                    raise ValueError('Invalid face plane')
                polygon['planeNormalZ'] = planes[face[0]][2] * (-1 if face[1] else 1)
            if texinfos:
                if not 0 <= tex < len(texinfos):
                    raise ValueError('Texinfo outside table')
                info = texinfos[tex]
                texture = info[8]
                if not 0 <= texture < len(textures):
                    raise ValueError('Texture index outside table')
                original = []
                for signed in surfedges[start:start+n]:
                    original.append(vertices[edges[abs(signed)][0 if signed >= 0 else 1]])
                polygon.update(texture=texture, uv=[[sum(v[a]*info[a] for a in range(3))+info[3],
                                                    sum(v[a]*info[4+a] for a in range(3))+info[7]] for v in original])
            polygons.append(polygon)
        if placed:
            total_vertices += len(placed)
            if total_vertices > 2_000_000:
                raise ValueError('Scene exceeds two million placed vertices')
            result.append(dict(name='World / terrain' if model_id == 0 else
                               entity.get('classname', 'inline') + ' · ref ' + entity.get('aw_ref', '?'),
                               model=model_id, entityIndex=entity_index,
                               entityClassname=entity.get('classname', 'worldspawn' if model_id == 0 else None),
                               terrainRole=('canonical_land' if override is None and
                                            entity.get('classname') == 'aw_render_diagnostic' and
                                            entity.get('aw_ref') == 'canonical_land_diagnostic' else
                                            'world_legacy' if model_id == 0 else 'none'),
                               inspectorOnlyDiagnostic=entity.get('classname') == 'aw_render_diagnostic',
                               renderPool=(dict(model=model_id, parent_model=int(entity['model'][1:]),
                                                relative_range=[first-pool[0], count]) if override is not None else None),
                               storedFaceRange=[first, count], reference=entity.get('aw_ref', ''), origin=origin,
                               angles=angle, faceCount=count, materialCount=len(materials),
                               vertices=placed, edges=sorted(lines), triangles=triangles, polygons=polygons))
    build(0, {})
    pool_text=entities[0].get('aw_render_pool') if entities else None
    pool=None
    if pool_text is not None:
        if not re.fullmatch(r'\*\d+',pool_text):raise ValueError('Invalid render pool model')
        pool_id=int(pool_text[1:])
        if not 0<=pool_id<len(models):raise ValueError('Render pool model outside table')
        pool=models[pool_id][14:16]
        if pool[0]<0 or pool[1]<0 or pool[0]+pool[1]>len(faces):raise ValueError('Invalid render pool face range')
    for entity_index, entity in enumerate(entities):
        if re.fullmatch(r'\*\d+', entity.get('model', '')):
            build(int(entity['model'][1:]), entity, entity_index)
            if 'aw_render_ranges' in entity:
                if pool is None:raise ValueError('Render ranges lack pool')
                for value in entity['aw_render_ranges'].split(','):
                    if not re.fullmatch(r'\d+:\d+',value):raise ValueError('Invalid auxiliary render range')
                    start,count=map(int,value.split(':'))
                    if count<1 or start+count>pool[1]:raise ValueError('Auxiliary render range outside pool')
                    build(pool_id,entity,entity_index,(pool[0]+start,count))
    return dict(format='amiwind-mesh-inspector-1', source=source, source_filename=source, loaded_filename=source,
                program={'name':'AmiWind Polycount inspector','version':'0.0.31'},
                coordinate_system='Compiled BSP/world XYZ units; +X east, +Y north; not original cell coordinates',
                source_sha256=hashlib.sha256(raw).hexdigest(),
                metric='Placed unique vertices per 3D bin; compiled BSP coordinates', objects=result, textures=textures)


def extract_textures(lump):
    """Validate all four mip ranges; export indexed base pixels only."""
    if not lump:
        return []
    if len(lump) < 4:
        raise ValueError('Truncated texture table')
    count = struct.unpack_from('<i', lump)[0]
    if count < 0 or count > 65536 or 4 + 4 * count > len(lump):
        raise ValueError('Invalid texture count')
    result, total = [], 0
    for offset in struct.unpack_from('<' + 'i'*count, lump, 4):
        if offset == -1:
            result.append(None)
            continue
        if offset < 4 + 4*count or offset + 40 > len(lump):
            raise ValueError('Texture header outside lump')
        name = lump[offset:offset+16].split(b'\0', 1)[0].decode('cp1252')
        width, height, *mips = struct.unpack_from('<6I', lump, offset+16)
        if not 1 <= width <= 4096 or not 1 <= height <= 4096:
            raise ValueError('Invalid texture dimensions')
        if all(mip == 0 for mip in mips):
            result.append(dict(name=name, width=width, height=height, missing=True))
            continue
        for level, mip in enumerate(mips):
            size = max(1, width >> level) * max(1, height >> level)
            if mip < 40 or offset+mip+size > len(lump):
                raise ValueError('Texture mip outside lump')
        total += width*height
        if total > 32*1024*1024:
            raise ValueError('Texture pixel budget exceeded')
        start = offset+mips[0]
        result.append(dict(name=name, width=width, height=height, pixels=list(lump[start:start+width*height])))
    return result


def script_safe_json(scene):
    """Prevent untrusted entity/source labels from closing an inline data script."""
    return json.dumps(scene, separators=(',', ':'), ensure_ascii=True, allow_nan=False).replace('<', '\\u003c')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bsp', type=Path)
    parser.add_argument('--out', required=True, type=Path, help='Fresh PRIVATE output directory')
    parser.add_argument('--viewer', type=Path, default=Path(__file__).resolve().parents[1] / 'amiwind-toolkit' / 'map-inspector.html')
    parser.add_argument('--palette', type=Path, help='Optional owner-supplied 768-byte palette; private export only')
    args = parser.parse_args()
    if args.out.exists():
        parser.error('Output exists: use a fresh numbered directory')
    if args.bsp.stat().st_size > 128 * 1024 * 1024:
        parser.error('BSP exceeds 128 MiB inspection limit')
    raw = args.bsp.read_bytes()
    scene = extract(raw, args.bsp.name)
    palette_hash = None
    if args.palette:
        if args.palette.stat().st_size != 768:
            parser.error('Palette must be exactly 768 bytes')
        palette = args.palette.read_bytes()
        if len(palette) != 768:
            parser.error('Palette must be exactly 768 bytes')
        scene['palette'] = list(palette)
        palette_hash = hashlib.sha256(palette).hexdigest()
    serialized = json.dumps(scene, separators=(',', ':'), ensure_ascii=True)
    html = args.viewer.read_text(encoding='utf-8')
    # The shared Toolkit header is inlined (the export is one standalone file); its logo is not available there, so it hides itself.
    header = args.viewer.with_name('header.js')
    if header.is_file():
        tag = re.search(r'<script src="header.js"([^>]*)></script>', html)
        if tag:
            html = html.replace(tag.group(0), '<script%s>%s</script>' % (tag.group(1), header.read_text(encoding='utf-8')), 1)
    # Escape '<' so any untrusted entity names cannot terminate the data script.
    embedded = '<script>window.AMIWIND_PRIVATE_SCENE=' + script_safe_json(scene) + ';</script>'
    html = html.replace('<script>\n', embedded + '\n<script>\n', 1)
    args.out.mkdir(parents=True)
    (args.out / 'PRIVATE-scene.json').write_text(serialized + '\n', encoding='utf-8', newline='\n')
    (args.out / 'PRIVATE-mesh-navigator.html').write_text(html, encoding='utf-8', newline='\n')
    unique = {face for o in scene['objects'] for face in range(o['storedFaceRange'][0], sum(o['storedFaceRange']))}
    receipt = dict(source=str(args.bsp.resolve()), source_sha256=scene['source_sha256'],
                   render_batches=len(scene['objects']),
                   geometry_entity_placements=len({o['entityIndex'] for o in scene['objects'] if o['model'] != 0}),
                   world_batches=sum(o['model'] == 0 for o in scene['objects']),
                   placed_faces=sum(o['faceCount'] for o in scene['objects']),
                   unique_referenced_stored_faces=len(unique),
                   placed_unique_vertices=sum(len(o['vertices']) for o in scene['objects']),
                   polygon_edges=sum(len(o['edges']) for o in scene['objects']),
                   fan_triangles=sum(len(o['triangles']) for o in scene['objects']),
                   textures=len(scene['textures']), embedded_base_textures=sum(bool(t and t.get('pixels')) for t in scene['textures']),
                   palette_sha256=palette_hash,
                   transform='Quake AngleVectors basis and entity origin; world once, referenced inline placements each once',
                   validation='Version, lump bounds/stride, model face ranges, edge/vertex indices, finite placement transforms',
                   privacy='PRIVATE derived geometry; do not include in public repository or release',
                   files={name: hashlib.sha256((args.out/name).read_bytes()).hexdigest() for name in
                          ('PRIVATE-scene.json', 'PRIVATE-mesh-navigator.html')})
    (args.out/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
