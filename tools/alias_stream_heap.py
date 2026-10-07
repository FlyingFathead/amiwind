# SPDX-License-Identifier: GPL-3.0-only
"""Source-bound simple-alias streaming allocation policy, never reserve credit."""
import hashlib
from pathlib import Path
import re
import struct

# Updated for aw_alias_single_pass (one read while decoding; same cache block, no staging).
STREAM_SHA256='17b39288303d1d762944dc278d193817fc7396b323735c7b08907379f9d0e36d'

def runtime_policy(source):
    source=Path(source)
    text=(source/'model.c').read_text()
    clean=re.sub(r'/\*.*?\*/|//[^\n]*','',text,flags=re.S)
    dispatch='if(Mod_TryStreamAlias(mod))return mod;'
    path=source/'model_alias_stream.inc'
    if dispatch not in clean and '#include "model_alias_stream.inc"' not in clean:
        return dict(alias_streaming=0,mode='legacy_staging')
    digest=hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    if (clean.count(dispatch)!=1 or '#include "model_alias_stream.inc"' not in clean or
        '#define AW_ALIAS_STAGING_LIMIT (512*1024)' not in clean or
        clean.index(dispatch)>clean.index('alias_file=AW_AliasFile(mod->name);') or digest!=STREAM_SHA256):
        raise ValueError('Unrecognized alias streaming allocation policy')
    return dict(alias_streaming=1,mode='bounded_single_skin_direct_cache',source_sha256=digest,
                payload_stack_chunk_bytes=4096,source_and_decoded_limit_bytes=524288,
                validation='Source policy only; real decoder/cache and target checks remain separate.')

def eligible(raw,decoded):
    if not 84<=len(raw)<=524288 or decoded>524288 or raw[:8]!=b'IDPO\x06\x00\x00\x00':return False
    skins,w,h,nv,nt,nf=struct.unpack_from('<6i',raw,48)
    if skins!=1 or w<=0 or w%4 or not 0<h<=480 or not 0<nv<=2000 or nt<=0 or nf<=0:return False
    at=88+w*h+nv*12+nt*16
    if at+nf*(28+nv*4)!=len(raw) or struct.unpack_from('<i',raw,84)[0]:return False
    triangles=88+w*h+nv*12
    for i in range(nt):
        if any(v<0 or v>=nv for v in struct.unpack_from('<3i',raw,triangles+i*16+4)):return False
    for i in range(nf):
        pos=at+i*(28+nv*4)
        if struct.unpack_from('<i',raw,pos)[0] or b'\0' not in raw[pos+12:pos+28]:return False
    return True

def apply(raw,sizes,row):
    streaming=sizes.get('alias_streaming')==1 and eligible(raw,row['decoded_hunk_bytes'])
    row['alias_loader_mode']='direct_cache_stream' if streaming else 'staged'
    row['loader_fallback_bytes']=0 if streaming else row['decoded_hunk_bytes']+row['source_file_hunk_fallback_bytes']
    if streaming:
        row['source_file_hunk_fallback_bytes']=0
        row['external_malloc_peak_bytes']=0
    return row

def fallback(row):
    return row.get('loader_fallback_bytes',row['decoded_hunk_bytes']+row['source_file_hunk_fallback_bytes'])
