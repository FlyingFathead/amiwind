#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Export a private, north-oriented terrain-only PLY from full source heights."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
from PIL import Image
from mwad.paths import ensure_external


def export(survey,out,stride=4):
    if stride not in (1,2,4,8,16):raise ValueError('Stride must divide the original 64 terrain intervals')
    out=ensure_external(out,'world terrain mesh');out.mkdir(parents=True,exist_ok=True)
    with np.load(survey/'terrain-source.npz',allow_pickle=False) as data:
        cells=data['cells'];heights=data['heights'];water=data['water'];spacing=int(data['spacing'])
    if heights.shape!=(len(cells),65,65) or spacing!=128 or not np.isfinite(heights).all():raise ValueError('Invalid full-resolution source packet')
    report=json.loads((survey/'world-survey.json').read_text());bounds=report['terrain_bounds']
    image=np.asarray(Image.open(survey/'terrain.png').convert('RGB'))
    side=64//stride+1;nv=len(cells)*side*side;nf=len(cells)*(side-1)**2*2
    path=out/'Vvardenfell-terrain.ply'
    if path.exists():raise ValueError('Choose a fresh output directory')
    with path.open('wb') as f:
        f.write(('ply\nformat binary_little_endian 1.0\ncomment Source world XYZ; Y north, Z up. No scenery or actors.\n'
                 f'element vertex {nv}\nproperty float x\nproperty float y\nproperty float z\nproperty uchar red\nproperty uchar green\nproperty uchar blue\n'
                 f'element face {nf}\nproperty list uchar uint vertex_indices\nend_header\n').encode())
        for cell,h in zip(cells,heights):
            for y in range(0,65,stride):
                for x in range(0,65,stride):
                    ix=int((cell[0]-bounds[0])*32+min(x//2,31));iy=image.shape[0]-1-int((cell[1]-bounds[1])*32+min(y//2,31))
                    f.write(struct.pack('<3f3B',cell[0]*8192+x*128,cell[1]*8192+y*128,h[y,x],*image[iy,ix]))
        for i in range(len(cells)):
            base=i*side*side
            for y in range(side-1):
                for x in range(side-1):
                    a=base+y*side+x;b=a+1;c=a+side;d=c+1
                    f.write(struct.pack('<B3IB3I',3,a,b,d,3,a,d,c))
    receipt=dict(format='AmiWind whole-island terrain mesh 1',master_sha256=report['master_sha256'],
        source_packet_sha256=hashlib.file_digest((survey/'terrain-source.npz').open('rb'),'sha256').hexdigest(),
        mesh_sha256=hashlib.file_digest(path.open('rb'),'sha256').hexdigest(),terrain_cells=len(cells),vertices=nv,triangles=nf,
        source_spacing=128,export_spacing=128*stride,source_height_seams=len(report['terrain']['height_seams']),
        bounds=report['terrain_bounds'],limitations=['Terrain only; no playable BSP, collision, scenery, actors, or water surface.',
        'Colours are averaged terrain preview colours; submerged terrain is blue. No original UV textures.',
        'Full source heights remain in terrain-source.npz; shared edges are retained without modification.'])
    (out/'terrain-mesh.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--survey',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--stride',type=int,default=4);a=p.parse_args();print(json.dumps(export(a.survey,a.out,a.stride),indent=2))
