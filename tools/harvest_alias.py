"""Bound external harvest model bytes to the gameplay save fingerprint."""
import hashlib
import math
import re
import struct
from pathlib import Path


def model_entries(root, lines):
    result=[]
    for line in lines:
        fields=line.split()
        if len(fields)!=8 or not re.fullmatch(r'progs/harvest/[a-z0-9_]{1,45}\.mdl',fields[0]) or not re.fullmatch('[0-9a-f]{64}',fields[1]):
            raise ValueError('Invalid external harvest model binding')
        try:bounds=[float(v) for v in fields[2:]]
        except ValueError:raise ValueError('Invalid external harvest bounds') from None
        if not all(math.isfinite(v) and abs(v)<=32768 for v in bounds) or any(bounds[i]>bounds[i+3] for i in range(3)):
            raise ValueError('Invalid external harvest bounds')
        name=fields[0];path=Path(root)/name
        if path.is_symlink() or not path.is_file() or not 84<=path.stat().st_size<=128*1024:
            raise ValueError('Missing or excessive external harvest model: '+name)
        raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest()
        if digest!=fields[1]:raise ValueError('External harvest model hash mismatch: '+name)
        if raw[:4]!=b'IDPO' or struct.unpack_from('<i',raw,4)[0]!=6:
            raise ValueError('External harvest model must be MDL version6')
        scale=struct.unpack_from('<3f',raw,8);origin=struct.unpack_from('<3f',raw,20)
        ns,w,h,nv,nt,nf=struct.unpack_from('<6i',raw,48)
        if ns!=1 or nf!=1 or not 0<w<=128 or w%4 or not 0<h<=128 or not 0<nv<=1999 or not 0<nt<=666:
            raise ValueError('External harvest alias envelope exceeded')
        frame=88+w*h+nv*12+nt*16
        if len(raw)!=frame+28+nv*4 or struct.unpack_from('<i',raw,84)[0] or struct.unpack_from('<i',raw,frame)[0]:
            raise ValueError('Invalid external harvest alias layout')
        if not all(math.isfinite(v) and v>0 for v in scale) or not all(math.isfinite(v) for v in origin):
            raise ValueError('Invalid external harvest alias transform')
        for i in range(3):
            if abs(origin[i]-bounds[i])>.0001 or abs(origin[i]+scale[i]*255-bounds[i+3])>.0001:
                raise ValueError('External harvest model bounds mismatch')
        for i in range(nv):
            seam,u,v=struct.unpack_from('<3i',raw,88+w*h+i*12)
            if seam or not 0<=u<w or not 0<=v<h or raw[frame+28+i*4+3]>=162:
                raise ValueError('Invalid external harvest alias UV/normal')
        for i in range(nt):
            front,a,b,c=struct.unpack_from('<4i',raw,88+w*h+nv*12+i*16)
            if front!=1 or any(j<0 or j>=nv for j in (a,b,c)):
                raise ValueError('Invalid external harvest alias face')
        result.append((name,digest))
    if len({name for name,_ in result})!=len(result):
        raise ValueError('Duplicate external harvest model binding')
    return result
