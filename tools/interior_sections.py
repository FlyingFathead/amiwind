# SPDX-License-Identifier: GPL-3.0-only
"""Validate optional section content before incorporating it in save identity."""
import hashlib
import math
import re
from pathlib import Path

def decode(raw):
    lines=raw.decode('ascii').splitlines()
    h=lines[0].split() if lines else []
    if len(h)!=3 or h[0]!='AWIS1':raise ValueError('Invalid interior section header')
    count,links=map(int,h[1:])
    if not 2<=count<=8 or not 1<=links<=8 or len(lines)!=1+count+links:raise ValueError('Invalid section counts')
    sections={};portals=[]
    for line in lines[1:1+count]:
        v=line.split()
        if len(v)!=7 or not re.fullmatch('[a-z0-9]{1,15}',v[0]) or v[0] in sections:raise ValueError('Invalid section row')
        f=list(map(float,v[1:]));lo,hi=f[:3],f[3:]
        if not all(math.isfinite(x) and abs(x)<32768 for x in f) or any(lo[i]>=hi[i] for i in range(3)):raise ValueError('Invalid coverage')
        sections[v[0]]=(lo,hi)
    seen=set()
    for line in lines[1+count:]:
        v=line.split()
        if len(v)!=11 or v[0] not in sections or v[1] not in sections or v[0]==v[1]:raise ValueError('Invalid portal')
        key=tuple(sorted(v[:2]));axis=int(v[2]);f=list(map(float,v[3:]));split,margin=f[:2];lo,hi=f[2:5],f[5:]
        if key in seen or axis not in (0,1,2) or not all(math.isfinite(x) for x in f) or not 0<margin<=32:raise ValueError('Invalid portal limits')
        for name in v[:2]:
            a,b=sections[name]
            if any(not a[i]<=lo[i]<hi[i]<=b[i] for i in range(3)):raise ValueError('Portal lacks common coverage')
        if not lo[axis]<split-margin<split+margin<hi[axis]:raise ValueError('Hysteresis exceeds overlap')
        seen.add(key);portals.append(v)
    return sections,portals

def fingerprint_entries(id1):
    root=Path(id1);config=root/'interior-sections.txt'
    if not config.is_file():return []
    sections,_=decode(config.read_bytes())
    names={'interior-sections.txt'}
    for section in sections:
        names.update(('maps/'+section+'.bsp','doors-'+section+'.txt'))
    # External entry banks affect reachability and must enter the fingerprint
    # too. Existing banks are retained byte-for-byte by the merge step.
    names.update(p.relative_to(root).as_posix() for p in root.glob('doors-*.txt'))
    for name in sorted(names):
        path=root/name
        if path.is_symlink() or not path.is_file():raise ValueError('Missing section content: '+name)
        if name.startswith('maps/') and (path.stat().st_size<124 or path.read_bytes()[:4]!=b'\x1d\x00\x00\x00'):
            raise ValueError('Invalid section BSP: '+name)
        if name.startswith('doors-'):
            lines=path.read_text().splitlines()
            if name[6:-4] in sections and (not lines or lines[0]!='AWD3'):raise ValueError('Expected section AWD3 bank')
            if not lines or lines[0]!='AWD3':continue
            for row in lines[1:]:
                fields=row.split(maxsplit=13)
                if len(fields)!=14:raise ValueError('Malformed AWD3 section closure')
                if fields[0] in sections or fields[1] in sections:
                    for target in fields[:2]:
                        if not re.fullmatch('[a-z0-9]{1,15}',target) or not (root/'maps'/(target+'.bsp')).is_file():
                            raise ValueError('Missing directed section route map: '+target)
                        routed=root/'maps'/(target+'.bsp')
                        if routed.is_symlink() or routed.stat().st_size<124 or routed.read_bytes()[:4]!=b'\x1d\x00\x00\x00':
                            raise ValueError('Invalid directed section route BSP: '+target)
                        names.add('maps/'+target+'.bsp')
    return [(name,hashlib.sha256((root/name).read_bytes()).hexdigest()) for name in sorted(names)]
