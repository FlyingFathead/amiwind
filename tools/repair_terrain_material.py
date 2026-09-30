#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Apply one guarded terrain tile material repair to retained BSPs, no geometry edit."""
import argparse
import json
from pathlib import Path
import struct
from player_hull import lumps, pack_lumps


def repair(raw, bounds, source, target):
    data=lumps(raw);vertices=list(struct.iter_unpack('<3f',data[3]))
    edges=list(struct.iter_unpack('<2H',data[12]));surfedges=[v[0] for v in struct.iter_unpack('<i',data[13])]
    info=list(struct.iter_unpack('<8f2i',data[6]));faces=list(struct.iter_unpack('<Hhihh4Bi',data[7]))
    planes=list(struct.iter_unpack('<4fi',data[1]));textures={}
    for i in range(struct.unpack_from('<i',data[2])[0]):
        at=struct.unpack_from('<i',data[2],4+i*4)[0]
        if at>=0:textures[data[2][at:at+16].split(b'\0')[0].decode('ascii')]=i
    if source not in textures:return raw,0
    # Restrict to world faces and upward ground polygons within this exact tile.
    model=struct.unpack_from('<9f7i',data[14]);changed=0;copies={}
    for i in range(model[14],model[14]+model[15]):
        f=faces[i];tex=info[f[4]]
        if tex[8]!=textures[source] or planes[f[0]][2]*(1 if not f[1] else -1)<.5:continue
        ids=[surfedges[j] for j in range(f[2],f[2]+f[3])]
        points=[vertices[edges[abs(e)][0 if e>=0 else 1]] for e in ids]
        centre=[sum(v[k] for v in points)/len(points) for k in (0,1)]
        if not all(bounds[k]<=centre[k]<bounds[k+2] for k in (0,1)):continue
        if not all(bounds[k]-.01<=v[k]<=bounds[k+2]+.01 for v in points for k in (0,1)):
            raise ValueError('Merged terrain face extends outside guarded tile; rebuild terrain')
        if target not in textures:raise ValueError('Target terrain texture is not resident')
        if f[4] not in copies:
            copies[f[4]]=len(info);info.append((*tex[:8],textures[target],tex[9]))
        faces[i]=(*f[:4],copies[f[4]],*f[5:]);changed+=1
    if not changed:return raw,0
    data[6]=b''.join(struct.pack('<8f2i',*v) for v in info)
    data[7]=b''.join(struct.pack('<Hhihh4Bi',*v) for v in faces)
    return pack_lumps(data),changed


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('maps',type=Path)
    p.add_argument('--bounds',type=float,nargs=4,required=True);p.add_argument('--source',required=True);p.add_argument('--target',required=True)
    a=p.parse_args();report=[]
    # Read and validate every candidate before modifying any file.
    writes=[]
    for path in sorted(a.maps.glob('*.bsp')):
        if path.stem!='balmora' and not (path.stem.startswith('bm') and path.stem[2:].isdigit()):continue
        raw,n=repair(path.read_bytes(),a.bounds,a.source,a.target)
        if n:writes.append((path,raw));report.append(dict(map=path.stem,faces=n))
    for path,raw in writes:path.write_bytes(raw)
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
