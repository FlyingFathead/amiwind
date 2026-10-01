# SPDX-License-Identifier: GPL-3.0-only
"""Use the scene's redundant sky entries for original status-bar colours.

Keep existing world pixels and their lighting unchanged. Rebuild the lookup
columns for the new colours: later NPC conversions may legitimately use them.
Refuse an unreserved scene that already uses those slots.
"""
import hashlib,io,json,struct
from pathlib import Path
from PIL import Image
from player_hull import lumps

RESERVED=set(range(225,254))

def lookup_columns(palette, name):
    """Exact nearest colours for the repurposed bank; no runtime work needed."""
    import numpy as np
    if len(palette)!=768:raise ValueError('Expected a 256-colour palette')
    colours=np.frombuffer(palette,dtype=np.uint8).reshape(256,3).astype(float)
    bank=colours[225:254]
    if name=='colormap.lmp':
        target=np.array([bank*max(.15,1-level/63) for level in range(64)])
    elif name=='fog.lmp':
        target=np.array([bank*(1-level/15)+colours[224]*(level/15) for level in range(16)])
    else:raise ValueError('Unknown palette lookup '+name)
    result=np.argmin(((target[:,:,None,:]-colours[None,None,:,:])**2).sum(3),axis=2).astype(np.uint8)
    # Preserve exact authored indices at full light / no fog, including duplicates.
    result[0]=np.arange(225,254,dtype=np.uint8)
    return result

def sync_lookups(game, check=False):
    """Repair or verify only the 29 changed columns in both offline tables."""
    game=Path(game);palette=(game/'gfx/palette.lmp').read_bytes();report={}
    for name,rows in (('colormap.lmp',64),('fog.lmp',16)):
        path=game/'gfx'/name;raw=path.read_bytes()
        if len(raw)!=rows*256:raise ValueError('Invalid palette lookup size: '+name)
        expected=bytearray(raw);columns=lookup_columns(palette,name)
        for row in range(rows):expected[row*256+225:row*256+254]=columns[row].tobytes()
        if check and raw!=expected:raise ValueError('Stale palette lookup: '+name)
        if raw!=expected:path.write_bytes(expected)
        report[name]=hashlib.sha256(expected).hexdigest()
    return report

def check_pixels(raw,label):
    if RESERVED.intersection(raw):raise ValueError('UI palette slots already used by '+label)

def check_scene(game):
    for path in game.glob('maps/*.bsp'):
        b=lumps(path.read_bytes())[2];n=struct.unpack_from('<i',b)[0]
        if not 0<=n<=65536 or 4+n*4>len(b):raise ValueError('Invalid texture table')
        for at in struct.unpack_from('<'+str(n)+'i',b,4):
            if at==-1:continue
            if at<0 or at+40>len(b):raise ValueError('Invalid mip texture')
            w,h,*offsets=struct.unpack_from('<6I',b,at+16)
            for level,offset in enumerate(offsets):
                if not offset:continue
                size=(w>>level)*(h>>level)
                if at+offset+size>len(b):raise ValueError('Truncated mip texture')
                check_pixels(b[at+offset:at+offset+size],str(path))
    for path in game.glob('progs/*.mdl'):
        b=path.read_bytes();h=struct.unpack_from('<4si3f3ff3f8if',b)
        if h[:2]!=(b'IDPO',6) or h[12]!=1 or struct.unpack_from('<i',b,84)[0]:raise ValueError('Unsupported palette audit model '+str(path))
        size=h[13]*h[14]
        if 88+size>len(b):raise ValueError('Truncated alias skin')
        check_pixels(b[88:88+size],str(path))
    for path in (game/'gfx').glob('*.lmp'):
        if path.name=='palette.lmp':continue
        raw=path.read_bytes()
        if path.name in ('conback.lmp','loading.lmp','pause.lmp'):raw=raw[8:]
        check_pixels(raw,str(path))
    path=game/'gfx.wad'
    if path.exists():
        raw=path.read_bytes();magic,n,at=struct.unpack_from('<4sii',raw)
        if magic!=b'WAD2' or n<0 or at<12 or at+n*32>len(raw):raise ValueError('Invalid UI WAD')
        for i in range(n):
            pos,size,usize,typ,compressed,pad,name=struct.unpack_from('<iiiBBH16s',raw,at+i*32)
            if compressed or pos<12 or size!=usize or pos+size>len(raw) or typ not in (64,66):raise ValueError('Unsupported WAD palette audit')
            check_pixels(raw[pos+(8 if typ==66 else 0):pos+size],str(path))
    path=game/'gfx/hands.aws'
    if path.exists():
        raw=path.read_bytes();magic,w,h,n,pad=struct.unpack_from('>4s4H',raw)
        if magic!=b'AWS1' or not 0<n<=32:raise ValueError('Unsupported hand spans')
        offsets=struct.unpack_from('>'+str(n+1)+'I',raw,12)
        for start,stop in zip(offsets,offsets[1:]):
            at=start
            for row in range(h):
                runs=struct.unpack_from('>H',raw,at)[0];at+=2
                for run in range(runs):
                    x,count=struct.unpack_from('>HH',raw,at);at+=4
                    if x+count>w or at+count>stop:raise ValueError('Invalid hand span')
                    check_pixels(raw[at:at+count],str(path));at+=count
            if at!=stop:raise ValueError('Invalid hand frame length')

def reserve(data,game):
    from mwad.audit import BSA
    from mwad.paths import child_ci,ensure_external
    from npc_geometry import Assets
    game=ensure_external(Path(game),'private palette');data=Path(data);path=game/'gfx/palette.lmp';old=path.read_bytes()
    marker=game/'gfx/ui-palette.json'
    if marker.exists():
        report=json.loads(marker.read_text())
        if hashlib.sha256(old).hexdigest()!=report['palette_sha256']:raise ValueError('UI palette receipt mismatch')
        report['lookup_sha256']=sync_lookups(game)
        marker.write_text(json.dumps(report,indent=2)+'\n')
        return report
    if len(old)!=768 or any(old[i*3:i*3+3]!=old[224*3:224*3+3] for i in RESERVED):raise ValueError('Scene has no redundant UI palette bank')
    check_scene(game)
    assets=Assets(data,BSA(child_ci(data,'Morrowind.bsa')));samples=Image.new('RGB',(48,16));sources={}
    for i,color in enumerate(('red','blue','green')):
        name='textures/menu_bar_'+color+'.dds';raw=assets.read(name);image=Image.open(io.BytesIO(raw)).convert('RGBA')
        if image.size!=(16,16):raise ValueError('Unexpected original status bar')
        samples.paste(image,(i*16,0),image);sources[name]=hashlib.sha256(raw).hexdigest()
    colors=bytes(samples.quantize(colors=29,dither=Image.Dither.NONE).getpalette()[:87])
    new=old[:225*3]+colors+old[254*3:];path.write_bytes(new)
    report={'format':'AmiWind reserved UI palette 1','indices':[225,253],
            'world_pixels_unchanged':True,'console_font_unchanged':True,'sources':sources,
            'previous_palette_sha256':hashlib.sha256(old).hexdigest(),'palette_sha256':hashlib.sha256(new).hexdigest()}
    report['lookup_sha256']=sync_lookups(game)
    marker.write_text(json.dumps(report,indent=2)+'\n');return report
