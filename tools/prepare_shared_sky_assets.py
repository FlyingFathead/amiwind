# SPDX-License-Identifier: GPL-3.0-only
"""Prepare owned cloud shapes and seven sky tones in a derived private stage."""
from pathlib import Path
import hashlib,io,json,os,shutil
from PIL import Image
import sky_palette_overlay as overlay
from build_shared_sky_clouds import build_cloud_sky,FORBIDDEN,SECONDARY_TONES
from build_night_sky import prepare_night_sky

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def owned_clouds(data_files):
    """Loose TGA first, then DDS/BSA; no downloads or replacement artwork."""
    data=Path(data_files);textures=data/'Textures'
    # Case-insensitive installations are common; do not depend on host case rules.
    entries={p.name.casefold():p for p in data.iterdir()}
    textures=entries.get('textures')
    loose={p.name.casefold():p for p in textures.iterdir() if p.is_file()} if textures and textures.is_dir() else {}
    archive=None;result=[]
    for stem in ('tx_sky_clear','tx_sky_cloudy'):
        raw=None;name=None
        for suffix in ('.tga','.dds'):
            p=loose.get(stem+suffix)
            if p:raw=p.read_bytes();name='textures/'+p.name;break
        if raw is None:
            from mwad.audit import BSA
            from npc_geometry import bsa_read
            if archive is None:
                path=entries.get('morrowind.bsa')
                if path is None:raise FileNotFoundError('Owned cloud textures or Morrowind.bsa required')
                archive=BSA(path)
            for suffix in ('.dds','.tga'):
                try:name='textures/'+stem+suffix;raw=bsa_read(archive,name);break
                except KeyError:pass
        if raw is None:raise FileNotFoundError('Missing owned cloud texture '+stem)
        with Image.open(io.BytesIO(raw)) as opened:
            if 'A' not in opened.getbands():raise ValueError('Owned cloud input needs explicit alpha: '+name)
            image=opened.convert('RGBA')
        result.append((image,{'name':name,'sha256':hashlib.sha256(raw).hexdigest(),'dimensions':list(image.size)}))
    return result

def validate_sky(raw):
    if len(raw)!=32768:raise ValueError('Shared cloud sky must be 32768 bytes')
    left=set(raw[y*256+x] for y in range(128) for x in range(128))
    right=set(raw[y*256+x+128] for y in range(128) for x in range(128))
    if (left-{0}) & FORBIDDEN or not right<=set((*SECONDARY_TONES,224)) or not left-{0}:
        raise ValueError('Shared cloud layer contract failed')

def prepare_staged_sky(id1,data_files,work_dir,*,shared_sky_source=None,local_skybox='false'):
    id1=Path(id1);work=Path(work_dir);marker=id1/'gfx/sky-palette-bank.json'
    def with_night(report):
        # Night artwork owns an independent validated marker. Reusing clouds,
        # custom cloud input or the local-sky debug path must not suppress it.
        report['night_sky']=prepare_night_sky(id1,data_files,work/'night-sky')
        return report
    if shared_sky_source is not None:return with_night({'status':'explicit_shared_source','shared_sky_source':str(shared_sky_source),'vivid_sky':'caller-owned; not asserted'})
    if str(local_skybox).casefold() in ('true','1','on','yes'):
        return with_night({'status':'local_skybox_debug','shared_sky_source':None,'vivid_sky':False})
    palette=id1/'gfx/palette.lmp';sky=id1/'gfx/aw_shared_sky.lmp'
    if marker.exists():
        record=json.loads(marker.read_text(encoding='utf-8'))
        if record.get('palette_sha256')!=digest(palette) or record.get('sky_sha256')!=digest(sky):raise ValueError('Stale sky-bank marker')
        for name in ('colormap.lmp','fog.lmp'):
            if record.get('lookup_sha256',{}).get(name)!=digest(id1/'gfx'/name):raise ValueError('Stale sky-bank lookup '+name)
        raw=palette.read_bytes()
        if any(tuple(raw[i*3:i*3+3])!=rgb for i,(_,rgb) in overlay.BANK.items()):raise ValueError('Sky-bank RGB contract changed')
        validate_sky(sky.read_bytes())
        return with_night({'status':'verified_reuse','shared_sky_source':str(sky),'vivid_sky':True,'palette_sha256':digest(palette),'sky_sha256':digest(sky),'lookup_sha256':record['lookup_sha256']})
    def fallback(reason):
        report={'status':'fallback_warning','warning':reason,'vivid_sky':False,'shared_sky_source':None}
        print('[warning] Shared sky vivid/cloud preparation unavailable: '+reason,flush=True)
        work.mkdir(parents=True,exist_ok=True)
        path=work/'fallback-warning.json'
        if path.exists():raise ValueError('Existing sky preparation warning: use a fresh build work directory')
        path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');return with_night(report)
    if digest(palette)!=overlay.EXPECTED_PALETTE:return fallback('Unsupported original palette fingerprint; no reservation/reindex performed')
    if not data_files:return fallback('No owned data files supplied; no cloud artwork or vivid palette asserted')
    try:clouds=owned_clouds(data_files)
    except (FileNotFoundError,KeyError,OSError,ValueError) as exc:return fallback(str(exc))
    if work.exists():raise ValueError('Sky preparation work directory exists; preserve it and use fresh output')
    # Hard format errors stop before any staged mutation. Overlay contains only
    # changed files; every original is backed up before installing a changed file.
    record=overlay.convert(id1,work/'changed-overlay',overlay.EXPECTED_PALETTE,changed_only=True)
    raw,new_report=build_cloud_sky(clouds[0][0],(work/'changed-overlay/gfx/palette.lmp').read_bytes(),secondary=clouds[1][0])
    validate_sky(raw)
    output=work/'owned-cloud-sky.lmp';output.write_bytes(raw)
    changes=[r for r in record['files'] if r['overlay_written']]
    for row in changes:
        original=id1/row['path'];backup=work/'before-originals'/row['path']
        if digest(original)!=row['input_sha256']:raise ValueError('Staged input changed before sky install: '+row['path'])
        backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(original,backup)
    if sky.exists():
        backup=work/'before-originals/gfx/aw_shared_sky.lmp';backup.parent.mkdir(parents=True,exist_ok=True)
        if not backup.exists():shutil.copy2(sky,backup)
    for row in changes:
        original=id1/row['path'];payload=(work/'changed-overlay'/row['path']).read_bytes()
        if hashlib.sha256(payload).hexdigest()!=row['output_sha256']:raise ValueError('Changed overlay hash mismatch')
        temp=original.with_name(original.name+'.sky-install-tmp')
        with temp.open('xb') as stream:stream.write(payload)
        os.replace(temp,original)
    report={'status':'prepared_owned_clouds','vivid_sky':True,'shared_sky_source':str(output),'palette_sha256':digest(palette),'sky_sha256':hashlib.sha256(raw).hexdigest(),'lookup_sha256':{name:digest(id1/'gfx'/name) for name in ('colormap.lmp','fog.lmp')},'sources':[r for _,r in clouds],'cloud_conversion':new_report,'changed_files':len(changes),'runtime_colour_mapping_required':True,'native_acceptance':False}
    report=with_night(report)
    # configure_staged_maps will install this exact sky immediately afterward.
    marker.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    (work/'sky-asset-preparation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report
