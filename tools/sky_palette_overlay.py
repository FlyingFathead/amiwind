# SPDX-License-Identifier: GPL-3.0-only
"""Format-aware derived-asset sky palette overlay; immutable input, Python only."""
from pathlib import Path
import argparse, hashlib, json, struct
from datetime import datetime
import numpy as np

BANK={222:(223,(100,69,138)),133:(113,(52,73,110)),95:(94,(210,50,34)),
      156:(158,(250,104,45)),140:(138,(255,174,66)),83:(82,(255,232,160)),221:(223,(153,38,79))}
# .anm: animation kit layouts beside actor models (tools/npc_anim.py); .tag: carried-item tags beside them
# (tools/npc_items.py): plain ASCII text, no pixels (ANIMKIT-IMAGE-FORMATS-35).
OPAQUE={'.cfg','.dat','.json','.lip','.rc','.tsv','.txt','.wav','.awc','.awj','.awn','.awq','.awr','.awt','.awg','.awl',
        '.anm','.tag'}
# Every extension spans() parses as indexed pixels or metadata (besides OPAQUE and the named files below).
PARSED={'.mdl','.spr','.bsp','.wad','.lmp','.awb','.awv','.awf','.mws','.awh','.awi','.awu','.awm','.aws'}
NAMED={'save-content.bin'}


def unknown_formats(paths):
    """The relative payload paths whose format spans() does not know (the image step's palette overlay would
    stop on them): checked by the payload preflight before any image work."""
    out=[]
    for rel in paths:
        rel=str(rel).replace('\\','/');ext=('.'+rel.rsplit('.',1)[1].lower()) if '.' in rel.rsplit('/',1)[-1] else ''
        if ext in OPAQUE or ext in PARSED or rel.lower() in NAMED:continue
        out.append(rel)
    return out
RAW_LMP={'font-readable.lmp':16384,'font-retro.lmp':16384}
QPIC_LMP={'conback.lmp','loading.lmp','pause.lmp'}
EXPECTED_PALETTE='a0f74c36edc83962b99cd254026659466b1932898636f8ccc1a814a06cb7986c'

def sha(b): return hashlib.sha256(b).hexdigest()
def approved(palette,legacy_bank=None):
    # The approved source palette, whatever the reserved UI bank (indices 225..253) now holds: the
    # fingerprint was taken with the format 1 bank, so the palette is checked with that bank put back
    # (ui_palette.legacy_bank). Since the enemy's yellow bar (format 2) the bank differs, the rest not.
    if sha(palette)==EXPECTED_PALETTE:return True
    return bool(legacy_bank) and len(palette)==768 and len(legacy_bank)==87 and \
        sha(bytes(palette[:225*3])+bytes(legacy_bank)+bytes(palette[254*3:]))==EXPECTED_PALETTE
def banked_palette(palette):
    """The palette with the sky colour bank; convert() and the hand catalogue share it."""
    new=bytearray(palette)
    for i,(_,rgb) in BANK.items():new[i*3:i*3+3]=bytes(rgb)
    return bytes(new)
def need(ok,msg):
    if not ok: raise ValueError(msg)

def bank_mapping():
    """The pixel translation of the sky bank: each banked index to its replacement index."""
    return bytes(BANK[i][0] if i in BANK else i for i in range(256))

def bank_safe(palette):
    """The overlay's guard: every banked index lies within two units per channel of its replacement,
    so translating pixels off the bank does not change a colour visibly."""
    return len(palette)>=768 and all(max(abs(palette[i*3+k]-palette[r*3+k]) for k in range(3))<=2
                                     for i,(r,_) in BANK.items())

def remap_miptex(mip):
    """A BSP miptex with its mip pixels translated off the sky bank, as convert() rewrites a map's
    textures (the same spans: four mip levels). Shared with the CHIM builder (CHIM-TEXTURE-SPECKS-33)."""
    w,h,*mips=struct.unpack_from('<6I',mip,16);mapping=bank_mapping();out=bytearray(mip)
    for level,p in enumerate(mips):
        if not p:continue
        size=(w>>level)*(h>>level);need(p>=40 and p+size<=len(mip),'Invalid mip pixels')
        out[p:p+size]=bytes(mip[p:p+size]).translate(mapping)
    return bytes(out)

def spans(raw,rel):
    """Return validated nonoverlapping indexed-byte spans, or an exclusion reason."""
    n=len(raw);ext=Path(rel).suffix.lower();name=Path(rel).name.lower();out=[]
    def get(fmt,at):
        need(0<=at and at+struct.calcsize(fmt)<=n,'Truncated header '+rel)
        return struct.unpack_from(fmt,raw,at)
    def add(at,size):
        need(size>0 and 0<=at and at+size<=n,'Invalid pixel span '+rel);out.append((at,size))
    def qpic(at,size):
        w,h=get('<2i',at);need(w>0 and h>0 and size==8+w*h,'Invalid qpic '+rel);add(at+8,w*h)
    if ext=='.bsp':
        need(n>=124 and get('<i',0)[0]==29,'Unsupported BSP version')
        off,length=get('<2i',20);need(off>=124 and length>=4 and off+length<=n,'Invalid texture lump')
        count=get('<i',off)[0];need(0<=count<=65536 and 4+4*count<=length,'Invalid texture table')
        for i in range(count):
            at=get('<i',off+4+4*i)[0]
            if at==-1:continue
            need(at>=4+4*count and at+40<=length,'Invalid miptex header')
            w,h,*mips=get('<6I',off+at+16);need(w>0 and h>0,'Invalid texture size')
            for level,p in enumerate(mips):
                if not p:continue
                size=(w>>level)*(h>>level);need(p>=40 and at+p+size<=length,'Invalid mip pixels');add(off+at+p,size)
    elif ext in ('.mdl','.spr'):
        if ext=='.mdl':
            need(raw[:4]==b'IDPO' and get('<i',4)[0]==6,'Unsupported MDL')
            count,w,h=get('<3i',48);need(count>0 and w>0 and h>0,'Invalid skins');at=84
        else:
            need(raw[:4]==b'IDSP' and get('<i',4)[0]==1,'Unsupported SPR');count=get('<i',24)[0];need(count>0,'Invalid frames');at=36
        for _ in range(count):
            kind=get('<i',at)[0];at+=4;need(kind in (0,1),'Unsupported image group');frames=1
            if kind:
                frames=get('<i',at)[0];need(0<frames<=65536,'Invalid group');at+=4+frames*4;need(at<=n,'Truncated group intervals')
            for _ in range(frames):
                if ext=='.spr':
                    _,_,w,h=get('<4i',at);at+=16;need(w>0 and h>0,'Invalid sprite frame')
                add(at,w*h);at+=w*h
        if ext=='.spr':need(at==n,'Trailing sprite bytes')
    elif ext=='.awm':
        # AWM1 terrain pixels and its ocean fill index share the global palette.
        # Town identities/transforms are metadata, not palette references.
        magic,w,h,x0,y0,x1,y1,count,ocean=get('<4sHH4iII',0)
        need(magic==b'AWM1' and 1<=w<=512 and 1<=h<=512 and count<=8,'Unsupported world map')
        need(-2000000<=x0<x1<=2000000 and -2000000<=y0<y1<=2000000,'Invalid world map bounds')
        start=32+60*count
        need(ocean<=255 and n==start+w*h,'Invalid world map pixel length/index')
        for i in range(count):
            at=32+60*i
            need(b'\0' in raw[at:at+16] and b'\0' in raw[at+16:at+48],'Invalid world map area name')
            x,y,scale=get('<3f',at+48)
            need(-2000000<=x<=2000000 and -2000000<=y<=2000000 and .0009765625<=scale<=100,'Invalid world map transform')
        add(28,1)  # Validated uint32 index: its other three bytes are zero.
        add(start,w*h)
    elif ext in ('.awi','.awu'):
        need(raw[:4]==(b'AWI1' if ext=='.awi' else b'AWU1'),'Unknown image version');w,h=get('<2H',4);need(n==8+w*h,'Image size mismatch');add(8,w*h)
    elif rel.lower()=='gfx/hand-models.awh':
        # AWH1 hand catalogue (prepare_hand_catalog.pack_catalog): race IDs and model paths, no pixels.
        need(raw[:4]==b'AWH1','Unknown hand catalogue');count,size=get('>HH',4)
        need(0<count<=32 and size==196 and n==8+count*size,'Invalid hand catalogue');return [],'hand model catalogue (paths only)'
    elif ext=='.awh':
        need(raw[:4]==b'AWH1','Unknown head preview');count=get('<H',4)[0];need(n==6+count*82,'Invalid head packet')
        for i in range(count):add(6+i*82+18,64)
    elif ext=='.aws':
        magic,w,h,count,pad=get('>4s4H',0);need(magic==b'AWS1' and w>0 and h>0 and 0<count<=32 and pad==0,'Unsupported spans')
        offsets=get('>'+str(count+1)+'I',12);need(offsets[0]>=12+4*(count+1) and offsets[-1]==n,'Invalid span offsets')
        for start,stop in zip(offsets,offsets[1:]):
            need(start<=stop,'Unordered span frames');at=start
            for _ in range(h):
                runs=get('>H',at)[0];at+=2
                for _ in range(runs):
                    x,size=get('>2H',at);at+=4;need(size>0 and x+size<=w and at+size<=stop,'Invalid span run');add(at,size);at+=size
            need(at==stop,'Span length mismatch')
    elif ext=='.wad':
        magic,count,at=get('<4sii',0);need(magic==b'WAD2' and count>=0 and at>=12 and at+count*32<=n,'Unsupported WAD')
        for i in range(count):
            pos,size,usize,typ,compressed,pad,_=get('<iiiBBH16s',at+i*32)
            need(pos>=12 and size==usize and not compressed and pos+size<=n,'Compressed/invalid WAD')
            if typ==64:add(pos,size)
            elif typ==66:qpic(pos,size)
            else:raise ValueError('Unknown indexed WAD lump type '+str(typ))
    elif ext=='.lmp':
        if name in ('palette.lmp','colormap.lmp','fog.lmp'):return [],'special palette/lookup'
        if name=='aw_shared_sky.lmp':need(n==32768,'Invalid sky');return [],'root replaces shared sky separately'
        if name in RAW_LMP:need(n==RAW_LMP[name],'Invalid font');add(0,n)
        elif name in QPIC_LMP:qpic(0,n)
        else:raise ValueError('Unknown indexed LMP '+rel)
    elif ext=='.awb':
        if raw[:4]==b'AWB1':
            count=get('<H',4)[0];need(0<count<=32 and n==6+60*count,'Invalid collision barriers');return [],'AWB1 collision metadata'
        need(raw[:4]==b'AWB2','Unknown menu image');w,h=get('<2H',4);need(n==8+768+w*h,'Invalid own-palette image');return [],'AWB2 own palette'
    elif ext=='.awv':
        if rel.lower()=='world/volumes.awv':need(raw[:4]==b'AWV1' and n==5,'Invalid volume manifest');return [],'volume metadata'
        magic,w,h,fps,rate,frames,samples=get('>4sHHHHII',0);need(magic==b'AWV1' and n==32+768+frames*w*h+samples,'Invalid own-palette video');return [],'AWV1 own palette'
    elif ext=='.awf':
        need(raw[:4]==b'AWF1','Unknown font version');return [],'two-bit glyph coverage'
    elif ext=='.mws':
        import re
        need(re.fullmatch(r'music/track\d{2}\.mws',rel.lower()) is not None,'Unknown music payload path')
        # Same header/length/padding contract as prepare_music.unpack_stream;
        # no PCM reconstruction is needed for an unchanged non-indexed payload.
        magic,rate,block,frames,count=get('>4sHHII',0)
        need(magic==b'MWA1' and rate==11015 and block==8192 and frames>0,'Unsupported music stream')
        need(count==(frames+block-1)//block and n==16+count*block*2,'Music length mismatch')
        used=frames-(count-1)*block;last=16+(count-1)*block*2
        need(not any(raw[last+used:last+block]) and not any(raw[last+block+used:]),'Nonzero music padding')
        return [],'MWA1 Paula audio; not indexed graphics'
    elif rel.lower()=='save-content.bin':
        need(n==32,'Invalid save-content SHA256 digest');return [],'32-byte content fingerprint'
    elif ext in OPAQUE:return [],'known non-indexed source format'
    else:raise ValueError('Unknown potentially indexed format '+rel)
    # Equal aliased spans are legal shared textures; partial overlaps are not.
    out=sorted(set(out))
    for (at,size),(next_at,_) in zip(out,out[1:]):need(at+size<=next_at,'Overlapping indexed spans')
    return out,'indexed pixels'

def lookup(raw,old,new,rows,name):
    need(len(raw)==rows*256,'Invalid lookup '+name)
    table=np.frombuffer(raw,np.uint8).reshape(rows,256);mapping=np.arange(256,dtype=np.uint8)
    for i,(target,_) in BANK.items():mapping[i]=target
    out=mapping[table].copy();colours=np.frombuffer(new,np.uint8).reshape(256,3).astype(float)
    for i in BANK:
        targets=np.array([colours[i]*max(.15,1-r/63) if rows==64 else colours[i]*(1-r/15)+colours[224]*(r/15) for r in range(rows)])
        # Do not emit transparent255 from light/fog quantization.
        out[:,i]=np.argmin(((targets[:,None,:]-colours[None,:255,:])**2).sum(2),axis=1)
    out[0]=np.arange(256,dtype=np.uint8)
    # Transparent input remains transparent, even though its RGB is black.
    out[:,255]=255
    return out.tobytes()

def convert(source,output,expected_palette=None,changed_only=False):
    source=Path(source).resolve();output=Path(output).resolve()
    need(source.is_dir() and not output.exists(),'Source required; output must not exist')
    need(source!=output and source not in output.parents and output not in source.parents,'Separate immutable input/output trees required')
    palette=(source/'gfx/palette.lmp').read_bytes();need(len(palette)==768,'Expected global palette')
    if expected_palette:need(sha(palette)==expected_palette,'Input palette fingerprint does not match approved source')
    need(bank_safe(palette),'Palette remap exceeds two units/channel guard')
    new=bytearray(banked_palette(palette));mapping=bank_mapping()
    rows=[];total=np.zeros(256,dtype=np.int64)
    # Complete preflight before creating output. Metadata-only manifest, no assets in workspace.
    for path in sorted(source.rglob('*')):
        need(not path.is_symlink(),'Symlinks are not supported')
        if not path.is_file():continue
        rel=path.relative_to(source).as_posix();raw=path.read_bytes()
        try:parts,reason=spans(raw,rel)
        except Exception as exc:raise ValueError(f'{rel} SHA256={sha(raw)}: {exc}') from exc
        counts=np.zeros(256,dtype=np.int64)
        for at,size in parts:counts+=np.bincount(np.frombuffer(raw[at:at+size],np.uint8),minlength=256)
        total+=counts;rows.append({'path':rel,'input_sha256':sha(raw),'bytes':len(raw),'spans':parts,'classification':reason,'pixels':int(counts.sum()),'remapped_pixels':int(sum(counts[i] for i in BANK))})
    # Validate the old world-map receipt before writing anything, then bind it
    # to the remapped map and palette. This never repairs an already-stale input.
    world_receipt=None
    if (source/'world/conversion.json').is_file():
        from prepare_world_ui import validate as validate_world_ui
        world_receipt=validate_world_ui(source)
        original=(source/'world/map.awm').read_bytes();remapped=bytearray(original)
        for at,size in spans(original,'world/map.awm')[0]:
            remapped[at:at+size]=original[at:at+size].translate(mapping)
        world_receipt['sky_overlay_source_palette_sha256']=sha(palette)
        world_receipt['palette_sha256']=sha(new)
        world_receipt['files']['map.awm']=sha(remapped)
    output.mkdir(parents=True)
    for row in rows:
        path=source/row['path'];raw=path.read_bytes();need(sha(raw)==row['input_sha256'],'Input changed after preflight')
        dest=bytearray(raw)
        for at,size in row['spans']:dest[at:at+size]=raw[at:at+size].translate(mapping)
        rel=row['path']
        if rel=='gfx/palette.lmp':dest=new
        elif rel in ('gfx/colormap.lmp','gfx/fog.lmp'):dest=lookup(raw,palette,new,64 if 'colormap' in rel else 16,rel)
        elif rel=='world/conversion.json' and world_receipt is not None:
            dest=(json.dumps(world_receipt,indent=2)+'\n').encode('utf-8')
        elif rel=='gfx/ui-palette.json':
            marker=json.loads(raw);need(marker['palette_sha256']==sha(palette),'Stale UI marker');marker['palette_sha256']=sha(new);marker['sky_overlay_source_palette_sha256']=sha(palette)
            marker['lookup_sha256']={name:sha(lookup((source/'gfx'/name).read_bytes(),palette,new,count,name)) for name,count in [('colormap.lmp',64),('fog.lmp',16)]}
            dest=(json.dumps(marker,indent=2)+'\n').encode()
        target=output/rel;row['output_sha256']=sha(dest);row['overlay_written']=not changed_only or dest!=raw
        if row['overlay_written']:
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(dest)
        need(sha(path.read_bytes())==row['input_sha256'],'Source mutation detected')
    oldcols=np.frombuffer(palette,np.uint8).reshape(256,3).astype(int)
    errors={str(i):{'old_rgb':oldcols[i].tolist(),'replacement':target,'replacement_rgb':oldcols[target].tolist(),'pixels':int(total[i]),'max_channel_error':int(abs(oldcols[i]-oldcols[target]).max()),'weighted_RGB_squared_error':int(total[i])*int(((oldcols[i]-oldcols[target])**2).sum()),'new_sky_rgb':rgb} for i,(target,rgb) in BANK.items()}
    receipt={'time':datetime.now().astimezone().isoformat(),'source':str(source),'output':str(output),'old_palette_sha256':sha(palette),'new_palette_sha256':sha(new),'bank':errors,'files':rows,'source_preserved':True,'native_runtime_colour_remap_required':True,'new_shared_sky_required':True,'not_native_acceptance':True,'lookup_policy':'Surviving input columns retain old curves with old-bank outputs translated. New sky columns quantized to new RGB excluding255. Row0 identity; transparent column255 preserved. Removed original colours are lossy, not exact-equivalent.'}
    (output/'sky-palette-overlay-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--output',required=True)
    p.add_argument('--expected-palette-sha256',default=EXPECTED_PALETTE);args=p.parse_args()
    try:
        report=convert(args.source,args.output,args.expected_palette_sha256);print(json.dumps({'files':len(report['files']),'output':report['output'],'bank':report['bank']},indent=2))
    except Exception as exc:
        failure=Path(args.output).with_name(Path(args.output).name+'.failed.json')
        if not failure.exists():
            failure.parent.mkdir(parents=True,exist_ok=True)
            failure.write_text(json.dumps({'time':datetime.now().astimezone().isoformat(),'source':args.source,'output':args.output,'status':'FAILED; never integrate','error_type':type(exc).__name__,'error':str(exc),'partial_output_may_exist':Path(args.output).exists()},indent=2)+'\n',encoding='utf-8')
        raise
