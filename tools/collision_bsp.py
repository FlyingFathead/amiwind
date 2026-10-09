# SPDX-License-Identifier: GPL-3.0-only
"""Compile the union of expanded convex pieces to a compact native BSP tree."""
import hashlib
from itertools import product
import os
from pathlib import Path
import pickle
import struct
import subprocess
import tempfile
import numpy as np
from scipy.spatial import ConvexHull
from player_hull import MINS,MAXS,lumps


def compile_standing(pieces,qbsp,cache,grid=64):
    """grid: the expanded corners are merged on a 1/grid unit lattice (64, as for the models; a finer
    lattice leaves qbsp slivers, seam holes in the CHIM terrain hull: CHIM-SEYDA-MEMORY-33)."""
    corners=np.array(list(product(*zip(MINS,MAXS))))
    brushes=[]
    for points,hull,ids,error in pieces:
        expanded=(points[:,None,:]-corners[None,:,:]).reshape(-1,3)
        expanded=np.unique(np.round(expanded*grid)/grid,axis=0)
        convex=ConvexHull(expanded);seen=set();lines=['{']
        for equation in convex.equations:
            n=equation[:3];d=-equation[3]
            key=(*np.round(n,4),round(d,3))
            if key in seen:continue
            seen.add(key)
            axis=np.eye(3)[np.argmin(abs(n))];u=np.cross(n,axis);u/=np.linalg.norm(u);v=np.cross(n,u)
            centre=n*d
            points=(centre+u*256,centre,centre+v*256)
            lines.append(' '.join('( '+' '.join(f'{x:.8f}' for x in point)+' )' for point in points)+' stone 0 0 0 1 1')
        brushes.append('\n'.join(lines+['}']))
    source='{\n"classname" "worldspawn"\n'+'\n'.join(brushes)+'\n}\n'
    # Compiler identity and format are part of the cache key.
    compiler=Path(qbsp).resolve();key=hashlib.sha256(source.encode()+compiler.read_bytes()).hexdigest()
    cache=Path(cache);cache.mkdir(parents=True,exist_ok=True);path=cache/(key+'.pickle')
    if path.is_file():return pickle.loads(path.read_bytes())
    with tempfile.TemporaryDirectory(prefix='aw-collision-') as tmp:
        tmp=Path(tmp);(tmp/'collision.map').write_text(source)
        result=subprocess.run([str(compiler),'-noclip','-nofill','-nopercent','collision.map'],cwd=tmp,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        if result.returncode:raise ValueError('Collision compiler failed: '+result.stdout.decode(errors='replace')[-2000:])
        data=lumps((tmp/'collision.bsp').read_bytes())
    planes=list(struct.iter_unpack('<4fi',data[1]));nodes=list(struct.iter_unpack('<ihh6h2H',data[5]));leaves=list(struct.iter_unpack('<ii6h2H4B',data[10]))
    root=struct.unpack_from('<i',data[14],36)[0];found=set();order=[];stack=[root]
    while stack:
        n=stack.pop()
        if n<0 or n in found:continue
        found.add(n);order.append(n);stack.extend(nodes[n][1:3])
    remap={old:i for i,old in enumerate(order)}
    def child(n):
        if n>=0:return remap[n]
        contents=leaves[-n-1][0]
        if contents not in (-1,-2):raise ValueError('Unexpected collision contents')
        return contents
    packed=[(planes[nodes[n][0]][:4],child(nodes[n][1]),child(nodes[n][2])) for n in order]
    result=(packed,remap[root] if root>=0 else child(root))
    # Atomic: maps compiled side by side share this content-addressed cache.
    partial=path.with_name(path.name+'.'+str(os.getpid())+'.tmp');partial.write_bytes(pickle.dumps(result,protocol=4))
    os.replace(partial,path);return result
