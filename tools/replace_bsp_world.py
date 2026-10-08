#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Replace a BSP29 world with a bounded world; preserve selected inline models.

Experimental offline composition, not automatic image acceptance. The caller
must establish identical world coordinates and complete terrain/water/barrier
coverage in the replacement. Palette and standing-hull markers are checked here.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
import struct

from compact_bsp import compact, entities
from player_hull import lumps, pack_lumps

FORMATS = {1: '<4fi', 3: '<3f', 5: '<i2h6h2H', 6: '<8f2i',
           7: '<HhihH4Bi', 9: '<iHH', 10: '<ii6h2H4B', 11: '<H',
           12: '<HH', 13: '<i', 14: '<9f7i'}


def rows(data):
    try:
        return {i: [list(row) for row in struct.iter_unpack(fmt, data[i])]
                for i, fmt in FORMATS.items()}
    except struct.error as exc:
        raise ValueError('Invalid BSP record size') from exc


def texture_blobs(data):
    if len(data) < 4:
        raise ValueError('Missing miptex directory')
    count = struct.unpack_from('<i', data)[0]
    if count < 0 or 4+4*count > len(data):
        raise ValueError('Invalid miptex count')
    result = []
    for index in range(count):
        offset = struct.unpack_from('<i', data, 4+4*index)[0]
        if offset == -1:
            result.append(None)
            continue
        if offset < 4+4*count or offset+40 > len(data):
            raise ValueError('Invalid miptex offset')
        width, height = struct.unpack_from('<II', data, offset+16)
        length = 40+width*height//64*85
        if not width or not height or width % 16 or height % 16 or offset+length > len(data):
            raise ValueError('Invalid miptex pixels')
        result.append(bytes(data[offset:offset+length]))
    return result


def merge_textures(base, source, *, allow_indexed_surface_aliases=False):
    blobs = []; lookup = {}; names = {}; mappings = []
    for data in (base, source):
        mapping = []
        for blob in texture_blobs(data):
            if blob is not None:
                name = blob[:16].split(b'\0', 1)[0]
                if name in names and names[name] != blob and not (allow_indexed_surface_aliases and re.fullmatch(rb'surface\d+', name)):
                    raise ValueError('Texture name has differing pixels: '+repr(name))
                names[name] = blob
            if blob not in lookup:
                lookup[blob] = len(blobs);blobs.append(blob)
            mapping.append(lookup[blob])
        mappings.append(mapping)
    if len(blobs) > 512:
        raise ValueError('Combined texture directory exceeds 512 entries')
    out = bytearray(struct.pack('<i',len(blobs))+bytes(4*len(blobs)))
    for i, blob in enumerate(blobs):
        struct.pack_into('<i',out,4+i*4,-1 if blob is None else len(out))
        if blob is not None:out.extend(blob)
    return out, mappings


def verify_collision(source, target, source_model, target_model, hull, parsed=None):
    """Check the complete paired trees, independent of numeric node/plane IDs."""
    a, b = parsed if parsed is not None else (rows(source), rows(target))
    index = 5 if hull == 0 else 9
    stack = [(a[14][source_model][9+hull], b[14][target_model][9+hull])]
    seen = set()
    def terminal(value, data):
        if index == 5:
            return data[10][-value-1][0] if value < 0 else None
        return value if value < 0 else value-65536 if value >= 65520 else None
    while stack:
        x,y = stack.pop()
        if (x,y) in seen:continue
        seen.add((x,y))
        tx,ty = terminal(x,a),terminal(y,b)
        if tx is not None or ty is not None:
            if tx != ty:raise ValueError('Inline collision contents changed')
            continue
        ra,rb = a[index][x],b[index][y]
        if bytes(source[1][ra[0]*20:(ra[0]+1)*20]) != bytes(target[1][rb[0]*20:(rb[0]+1)*20]):
            raise ValueError('Inline collision plane changed')
        stack.extend(zip(ra[1:3],rb[1:3]))


def verify_inline_rendering(source, target, retained_models, light_offset, parsed):
    a,b=parsed;at,bt=texture_blobs(source[2]),texture_blobs(target[2])
    def points(data,face):
        result=[]
        for (edge,) in data[13][face[2]:face[2]+face[3]]:
            vertex=data[12][abs(edge)][0 if edge>=0 else 1]
            result.append(data[3][vertex])
        return result
    checked=0
    for model,old in enumerate(retained_models[1:],1):
        am,bm=a[14][old],b[14][model]
        if am[:9]!=bm[:9] or am[15]!=bm[15]:
            raise ValueError('Inline model bounds/origin or face count changed')
        for af,bf in zip(a[7][am[14]:am[14]+am[15]],b[7][bm[14]:bm[14]+bm[15]]):
            ati,bti=a[6][af[4]],b[6][bf[4]]
            light=af[9]+light_offset if af[9]>=0 else af[9]
            if (points(a,af)!=points(b,bf) or a[1][af[0]]!=b[1][bf[0]] or
                af[1]!=bf[1] or ati[:8]!=bti[:8] or ati[9]!=bti[9] or
                at[ati[8]]!=bt[bti[8]] or af[5:9]!=bf[5:9] or bf[9]!=light):
                raise ValueError('Inline polygon, texture UV, material or lighting reference changed')
            checked+=1
    if bytes(target[8][light_offset:])!=bytes(source[8]):
        raise ValueError('Inline light samples changed')
    return checked


def replace_world(source_raw, base_raw, source_palette, base_palette, *, allow_indexed_surface_aliases=False):
    if len(source_palette) != 768 or source_palette != base_palette:
        raise ValueError('Source and replacement must use the same 768-byte palette')
    original = lumps(source_raw);source = lumps(source_raw);base = lumps(base_raw)
    sr,br = rows(source),rows(base)
    se,be = entities(source[0]),entities(base[0])
    if not se or not be or se[0].get('classname') != 'worldspawn' or be[0].get('classname') != 'worldspawn':
        raise ValueError('Missing first worldspawn entity')
    profile = se[0].get('aw_hull')
    if not profile or be[0].get('aw_hull') != profile:
        raise ValueError('Matching explicit standing-hull profile is required')
    if len(br[14]) != 1 or not br[5] or br[14][0][9] != 0:
        raise ValueError('Replacement must contain one world model rooted at node zero')
    if not br[10] or br[10][0][0] != -2:
        raise ValueError('Replacement leaf zero must be solid')
    if br[14][0][13] != len(br[10])-1:
        raise ValueError('Replacement visibility leaf count does not match world leaf table')
    seen_nodes=set();seen_leafs=set();stack=[0]
    while stack:
        node=stack.pop()
        if node < 0:
            leaf=-node-1
            if leaf>=len(br[10]) or (leaf and leaf in seen_leafs):
                raise ValueError('Replacement has invalid or shared non-solid world leaf')
            seen_leafs.add(leaf);continue
        if node>=len(br[5]) or node in seen_nodes:
            raise ValueError('Replacement world must be an acyclic tree with unique node parents')
        seen_nodes.add(node);stack.extend(br[5][node][1:3])
    # Remove source world roots/faces before compacting. Its leaf/PVS arrays are
    # only temporary lookup material for inline collision terminal contents.
    dummy=list(sr[14][0]);dummy[9:13]=[-1]*4;dummy[13:16]=[0,0,0]
    source[14][:64]=struct.pack(FORMATS[14],*dummy)
    inline_raw, reduction = compact(pack_lumps(source))
    inline=lumps(inline_raw);ir=rows(inline)
    textures, (base_tex, inline_tex) = merge_textures(base[2],inline[2], allow_indexed_surface_aliases=allow_indexed_surface_aliases)
    out=[bytearray(v) for v in base]
    out[0]=bytearray(inline[0]);out[2]=textures
    out[8]=base[8]+inline[8]
    offset={i:len(br[i]) for i in FORMATS}
    content_leaf={}
    for i,leaf in enumerate(br[10]):content_leaf.setdefault(leaf[0],i)
    def point_child(child):
        if child >= 0:return child+offset[5]
        contents=ir[10][-child-1][0]
        if contents not in content_leaf:
            raise ValueError('Replacement lacks inline terminal contents '+str(contents))
        return -content_leaf[contents]-1
    def clip_child(child):
        return child if child < 0 or child >= 65520 else child+offset[9]
    merged={i:[list(row) for row in br[i]] for i in FORMATS}
    # Reindex base texinfo too because duplicate slots may have been folded.
    for row in merged[6]:row[8]=base_tex[row[8]]
    merged[1].extend(ir[1]);merged[3].extend(ir[3])
    merged[12].extend([[v+offset[3] for v in row] for row in ir[12]])
    merged[13].extend([[(-1 if row[0]<0 else 1)*(abs(row[0])+offset[12])] for row in ir[13]])
    for row in ir[6]:
        row=list(row);row[8]=inline_tex[row[8]];merged[6].append(row)
    for row in ir[7]:
        row=list(row);row[0]+=offset[1];row[2]+=offset[13];row[4]+=offset[6]
        if row[9]>=0:row[9]+=len(base[8])
        merged[7].append(row)
    for row in ir[5]:
        row=list(row);row[0]+=offset[1];row[1:3]=[point_child(v) for v in row[1:3]];row[9]+=offset[7]
        merged[5].append(row)
    for row in ir[9]:
        merged[9].append([row[0]+offset[1],*[clip_child(v) for v in row[1:3]]])
    # Only the new base world owns the render leaves, marksurfaces and PVS.
    for row in ir[14][1:]:
        row=list(row);row[9]=point_child(row[9]);row[10:13]=[clip_child(v) for v in row[10:13]]
        row[14]+=offset[7];merged[14].append(row)
    if len(merged[5])>32767 or len(merged[9])>65520 or len(merged[1])>65536 or len(merged[3])>65536 or len(merged[6])>65536:
        raise ValueError('Combined BSP exceeds target index widths')
    try:
        for index, values in merged.items():
            out[index]=bytearray().join(struct.pack(FORMATS[index],*row) for row in values)
    except struct.error as exc:
        raise ValueError('Combined BSP field exceeds target index width') from exc
    result=pack_lumps(out)
    # Check all inline point and standing/default collision trees exactly.
    paired=(rows(original),merged)
    for model in range(1,len(ir[14])):
        old_model=reduction['retained_models'][model]
        for hull in range(4):verify_collision(original,out,old_model,model,hull,paired)
    checked_faces=verify_inline_rendering(original,out,reduction['retained_models'],len(base[8]),paired)
    if out[4]!=base[4] or out[10]!=base[10] or out[11]!=base[11]:
        raise ValueError('Replacement world visibility topology changed')
    report={'format':'AmiWind bounded world replacement 1','acceptance':'offline composition; target and world-coverage validation pending',
            'source_sha256':hashlib.sha256(source_raw).hexdigest(),'base_sha256':hashlib.sha256(base_raw).hexdigest(),
            'result_sha256':hashlib.sha256(result).hexdigest(),'palette_sha256':hashlib.sha256(source_palette).hexdigest(),
            'standing_hull_profile':profile,'inline_models':len(ir[14])-1,'source_leafs':len(sr[10]),
            'result_leafs':len(br[10]),'source_visibility_bytes':len(source[4]),'result_visibility_bytes':len(out[4]),
            'source_bytes':len(source_raw),'result_bytes':len(result),'checked_inline_faces':checked_faces,
            'inline_rendering':'polygon positions, planes, texture pixels, UVs, styles and light offsets checked',
            'inline_collision':'all four hull trees checked by paired traversal',
            'source_reduction':reduction}
    return result,report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','base','source-palette','base-palette','out','report'):
        p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args()
    inputs={p.resolve() for p in (args.source,args.base,args.source_palette,args.base_palette)}
    if args.out.resolve() in inputs or args.report.resolve() in inputs or args.out.resolve()==args.report.resolve():
        raise ValueError('Preserve source inputs; choose separate output and report paths')
    raw,report=replace_world(args.source.read_bytes(),args.base.read_bytes(),args.source_palette.read_bytes(),args.base_palette.read_bytes())
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_bytes(raw)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
