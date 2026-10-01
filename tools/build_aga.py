#!/usr/bin/env python3
"""Build the separate GPLv2 AGA runtime and an owner-only boot image."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from mwad.paths import ensure_external
from prepare_music import playlists, unpack_stream
from check_aga_binary import check_binary
from amiga_fs import check_image, check_payload_names
from project_version import VERSION, check_native_versions
from build_jobs import add_jobs, resolve_jobs

ROOT=Path(__file__).resolve().parents[1]
UPSTREAM_COMMIT='9c62d905151614af3e788ae3145a0d4ecc8a7bb8'
UPSTREAM_SHA256='43353034beb2a43b1af82c735f93c0a8bee8129c1b93d7ba152dd8e60ad3721c'
RUNTIME_SOURCE=ROOT/'engine/aga'
RUNTIME_BUILD_DIR='runtime'
CC_FLAGS=' -std=gnu89 -Wno-implicit-function-declaration -Wno-int-conversion -Wno-incompatible-pointer-types'

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def run(args,cwd=None,env=None):subprocess.run(list(map(str,args)),cwd=cwd,env=env,check=True)
def new_output(path):
    path=ensure_external(path,'AGA build')
    path.mkdir(parents=True,exist_ok=False)
    return path

def startup_config(config):
    """Configure controls first; quake.rc selects the named start after autoexec."""
    config=re.sub(r'(?m)^r_max(?:surfs|edges) [^\n]*\n?', '', config)
    config=re.sub(r'(?m)^aw_drawdistance [^\n]*\n?', '', config)
    config=re.sub(r'(?m)^bind "?[123]"? "aw_drawdistance (?:450|540|700|1000)"\n?', "", config)
    config=config.replace('bind ESCAPE quit','bind ESCAPE togglemenu').replace('r_drawviewmodel 0','r_drawviewmodel 1')
    config,count=re.subn(r'(?m)^map (?:seyda|prison)\s*$',
        'r_maxsurfs 12288\nr_maxedges 24576\nshowram 0\nbind MOUSE1 +attack\nbind F10 toggleconsole\nbind e +aw_use\nbind f "impulse 202"\nbind q +movedown',config)
    if count!=1:raise ValueError('Expected exactly one startup map in the converted default.cfg')
    config=re.sub(r'(?m)^(?:bind |unbindall)[^\n]*\n?', '', config)
    return 'exec keymaps-default.cfg\naw_drawdistance 540\n'+config.rstrip()+'\n'

def validate_quakec(path):
    """Reject incompatible compiler output before it reaches an Amiga image."""
    raw = Path(path).read_bytes()
    if len(raw) < 60:
        raise ValueError('QuakeC compiler produced a truncated progs.dat')
    header = struct.unpack_from('<15i', raw)
    if header[:2] != (6, 5927):
        raise ValueError(f'QuakeC output version/CRC {header[:2]} does not match engine (6, 5927); use standard Quake 1 output')
    for index, width in ((2, 8), (4, 8), (6, 8), (8, 36), (10, 1), (12, 4)):
        offset, count = header[index:index+2]
        if offset < 60 or count <= 0 or offset + count * width > len(raw):
            raise ValueError('QuakeC output has invalid program section bounds')
    # The original VM supports opcodes 0..65; FTE-only extensions cannot run here.
    for offset in range(header[2], header[2] + header[3]*8, 8):
        if struct.unpack_from('<H', raw, offset)[0] > 65:
            raise ValueError('QuakeC output contains an unsupported VM opcode')

def check_quakec(compiler, hands='3d'):
    """Compile our source in isolation; no game input or retained build output."""
    compiler = str(Path(compiler).resolve())
    with tempfile.TemporaryDirectory(prefix='amiwind-qcc-') as temp:
        directory = Path(temp)
        qc = directory/'qc'; qc.mkdir()
        for name in ('defs.qc', 'world.qc', 'progs.src'):
            shutil.copyfile(ROOT/'engine/aga/qc'/name, qc/name)
        if hands == 'sprites':
            source = qc/'world.qc'
            source.write_text(source.read_text().replace('progs/v_nord.mdl', 'progs/player.mdl'))
        result = subprocess.run([compiler], cwd=qc, stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, errors='replace', timeout=30)
        if result.returncode or not (directory/'progs.dat').is_file():
            raise ValueError(f'Compiler failed (exit {result.returncode}):\n' + (result.stdout + result.stderr)[-4000:])
        validate_quakec(directory/'progs.dat')

def runtime_sources(source=None):
    """Use the checked-in runtime directly; ignore only local build products."""
    source=Path(source or RUNTIME_SOURCE)
    ignored={'build','obj','obj-nofpu','__pycache__','.git'}
    files={}
    for path in sorted(source.rglob('*')):
        rel=path.relative_to(source)
        if any(part in ignored for part in rel.parts):continue
        if path.is_symlink():raise ValueError('Runtime source symlink is not allowed: '+str(rel))
        if path.is_file():files[rel.as_posix()]=digest(path)
    for required in ('Makefile','COPYING','src/quakedef.h','src/aw_c2p.c','boot/bootcheck.asm','qc/world.qc'):
        if required not in files:raise ValueError('Bundled runtime source missing: '+required)
    return files

def stage_runtime(out, source=None):
    """Copy to a new external directory so compilation cannot dirty the repo."""
    source=Path(source or RUNTIME_SOURCE)
    hashes=runtime_sources(source)
    tree=out/RUNTIME_BUILD_DIR
    tree.mkdir(exist_ok=False)
    for name,expected in hashes.items():
        target=tree/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source/name,target)
        if digest(target)!=expected:raise ValueError('Runtime source changed during staging: '+name)
    shutil.copyfile(ROOT/'VERSION', tree/'VERSION')
    (tree/'tools').mkdir(exist_ok=True)
    shutil.copyfile(ROOT/'tools/project_version.py', tree/'tools/project_version.py')
    return tree,hashes

def engine(args):
    check_native_versions()
    # Optional legacy input only verifies provenance; it never replaces repo source.
    if args.archive and digest(args.archive)!=UPSTREAM_SHA256:raise ValueError('Upstream archive checksum mismatch')
    out=new_output(args.out)
    tree,source_hashes=stage_runtime(out)
    env=os.environ.copy();env['PATH']=str(args.sdk.resolve()/'bin')+os.pathsep+env.get('PATH','')
    jobs=resolve_jobs(args.jobs)
    print(f'Native compiler jobs: {jobs}',flush=True)
    run(['make','-B','--output-sync=target',f'-j{jobs}',('nofpu' if args.cpu=='68020' else 'fpu'),'CC=m68k-amigaos-gcc'+CC_FLAGS+' -DAMIWIND_SPRITE_HANDS='+('1' if args.hands=='sprites' else '0'),'NDK_INC='+str(args.sdk.resolve()/'m68k-amigaos/ndk-include')],tree,env)
    binary=tree/('build/AmiQuakeGCC-NoFPU' if args.cpu=='68020' else 'build/AmiQuakeGCC')
    check_binary(binary.read_bytes())
    checker=tree/'build/AmiWindCheck'
    vasm=args.vasm.resolve() if args.vasm else args.sdk.resolve()/'bin/vasmm68k_mot'
    run([vasm,'-m68000','-Fhunkexe','-kick1hunks','-nosym','-I',args.sdk.resolve()/'m68k-amigaos/ndk-include','-I',tree/'build/version','-o',checker,tree/'boot/bootcheck.asm'])
    check_binary(checker.read_bytes())
    (out/'engine-build.json').write_text(json.dumps({'version':VERSION,'hands':args.hands,'compiler_jobs':jobs,'source_kind':'repository engine/aga','source_sha256':source_hashes,'upstream_commit':UPSTREAM_COMMIT,'baseline_upstream_archive_sha256':UPSTREAM_SHA256,'binary':str(binary),'binary_sha256':digest(binary),'bootcheck_sha256':digest(checker)},indent=2)+'\n')
    print(binary)

def write_content_fingerprint(id1):
    from prepare_seyda_regions import regions as seyda_regions
    fingerprint=hashlib.sha256()
    from area_config import SCENES
    from balmora_regions import config as balmora_config, regions as balmora_regions
    for name in [*(f"maps/{s['map']}.bsp" for s in SCENES), 'maps/intro_docks.bsp', 'maps/sncourt.bsp', 'seyda-regions.txt', *(f"maps/{r['name']}.bsp" for r in seyda_regions()), 'balmora-regions.txt', *(f"maps/{r['name']}.bsp" for r in balmora_regions(balmora_config())), 'progs.dat', 'character/catalog.awc', 'world/map.awm', 'world/journal.awj', 'world/entries.dat', 'world/quests.awq']:
        asset=Path(id1)/name
        if not asset.is_file():raise ValueError('Required character-creation asset missing: '+name)
        fingerprint.update(name.encode('ascii')+b'\0'+bytes.fromhex(digest(asset)))
    directory=Path(id1)/'world/regions.awr'
    if directory.is_file():
        fingerprint.update(b'world/regions.awr\0'+bytes.fromhex(digest(directory)))
        raw=directory.read_bytes()
        if raw[:4]!=b'AWR2' or len(raw)!=64+struct.unpack_from('<I',raw,4)[0]*52:
            raise ValueError('Invalid world region directory')
        for index in range(struct.unpack_from('<I',raw,4)[0]):
            name=f'maps/vf{index:04d}.bsp'
            fingerprint.update(name.encode('ascii')+b'\0'+bytes.fromhex(digest(Path(id1)/name)))
    (Path(id1)/'save-content.bin').write_bytes(fingerprint.digest())


def image(args):
    check_binary(args.engine.read_bytes())
    checker=args.bootcheck or args.engine.parent/'AmiWindCheck'
    check_binary(checker.read_bytes())
    receipt=args.engine.parents[2]/'engine-build.json'
    if not receipt.is_file():raise ValueError('Engine build receipt is required')
    engine_record=json.loads(receipt.read_text())
    if engine_record.get('version')!=VERSION or engine_record.get('binary_sha256')!=digest(args.engine) or engine_record.get('bootcheck_sha256')!=digest(checker):
        raise ValueError('Engine/preflight does not match the current versioned build receipt')
    build_mode=engine_record.get('hands','3d')
    if build_mode!=args.hands:raise ValueError('Image hands choice must match engine build')
    scene=ensure_external(args.scene,'AGA scene');music=ensure_external(args.music,'converted music');out=new_output(args.out)
    boot=out/'boot';shutil.copytree(scene/'id1',boot/'id1');(boot/'S').mkdir()
    cfg=boot/'id1/default.cfg'
    cfg.write_text(startup_config(cfg.read_text()))
    shutil.copyfile(ROOT/'config/keymaps.cfg',boot/'id1/keymaps-default.cfg')
    shutil.copyfile(ROOT/'config/game.cfg',boot/'id1/default-game.cfg')
    if args.data_files:
        from prepare_ui import convert as convert_ui
        from ui_palette import reserve as reserve_ui_palette
        try:
            reserve_ui_palette(args.data_files,boot/'id1')
            convert_ui(args.data_files,boot/'id1/gfx/palette.lmp',boot/'id1/gfx')
        except FileNotFoundError:
            print('[warning] Original font inputs missing; readable UI fallback retained.',flush=True)
    from prepare_logo import prepare_logo,prepare_menu_logo
    # NPC skins can use the palette bank first introduced for status bars.
    # A copied old lighting table maps those colours back to grey sky pixels.
    from ui_palette import sync_lookups
    sync_lookups(boot/'id1',check=True)
    from prepare_world_ui import prepare as prepare_world_ui, validate as validate_world_ui
    if args.data_files:prepare_world_ui(args.data_files,None,boot)
    validate_world_ui(boot/'id1')
    logo=ROOT/'resources/media/AmiWind_wordmark.png'
    prepare_menu_logo(logo,boot/'id1/gfx/palette.lmp',boot/'id1/gfx/amiwind.awi')
    logo_stream=boot/'id1/intro/amiwind.awv'
    if logo_stream.exists():logo_stream.unlink()
    prepare_logo(logo,logo_stream,boot/'id1/gfx/magic16.awf')
    movie=boot/'id1/intro/mw_intro.awv'
    if movie.exists():
        from prepare_video import validate as validate_video
        movie_info=validate_video(movie)
        if getattr(args,'intro_captions',None):
            from prepare_logo import prepare_opening_card
            prepare_opening_card(args.intro_captions,boot/'id1/gfx/magic16.awf',
                                 boot/'id1/intro/opening.awt',movie_info['frames'])
    else:
        print('[warning] Video not found; will not be included: intro/mw_intro.awv',flush=True)
    (boot/'id1/quake.rc').write_text('exec default.cfg\nexec default-game.cfg\nexec config.cfg\nexec keymap.cfg\nexec keymaps.cfg\nexec autoexec.cfg\naw_controls_migrate\naw_gallery_migrate\naw_startup\n')
    print('Default start: logo fade then main menu; New Game plays the optional movie then ship + track 04.',flush=True)
    shutil.copyfile(args.engine,boot/'AmiWind')
    shutil.copyfile(checker,boot/'AmiWindCheck')
    (boot/'S/startup-sequence').write_text('FailAt 10\nSYS:AmiWindCheck\nStack 300000\nSYS:AmiWind\n')
    for name in ['seyda.map','town.wad']:shutil.copyfile(scene/name,out/name)
    if (scene/'scene-ready.json').is_file():
        ready=json.loads((scene/'scene-ready.json').read_text())
        if ready.get('format')!='AmiWind compiled mesh BSP29':raise ValueError('Unknown compiled scene format')
        from player_hull import PROFILE
        if ready.get('standing_hull_profile')!=PROFILE:raise ValueError('Rebuild the scene: standing collision hull does not match this runtime')
        if not ready.get('hands'):raise ValueError('Prepare first-person hands before building this runtime')
        shutil.copyfile(scene/'seyda.bsp',out/'seyda.bsp')
    else:
        raise ValueError('Prepare the matching mesh scene before building this runtime image')
    shutil.copyfile(out/'seyda.bsp',boot/'id1/maps/seyda.bsp')
    from prepare_seyda_regions import convert as convert_seyda_regions, regions as seyda_regions
    convert_seyda_regions(boot/'id1/maps/seyda.bsp',boot/'id1/maps')
    qc=out/'qc';qc.mkdir()
    for name in ['defs.qc','world.qc']:shutil.copyfile(ROOT/'engine/aga/qc'/name,qc/name)
    if args.hands=='sprites':
        if not (scene/'id1/gfx/hands.aws').is_file():raise ValueError('Bake hand sprites first')
        q=qc/'world.qc';q.write_text(q.read_text().replace('progs/v_nord.mdl','progs/player.mdl'))
    (qc/'progs.src').write_text('../boot/id1/progs.dat\ndefs.qc\nworld.qc\n');run([args.qcc],qc)
    validate_quakec(boot/'id1/progs.dat')
    # Saved mutable state is only restored against this exact converted content.
    if args.data_files:
        from actor_grounding import annotate, bake_ground
        from mwad.paths import child_ci
        grounding=annotate(boot/'id1/maps',child_ci(args.data_files,'Morrowind.esm'))
        (out/'actor-grounding.json').write_text(json.dumps(grounding,indent=2)+'\n')
        (out/'actor-ground-support.json').write_text(json.dumps(bake_ground(boot/'id1/maps'),indent=2)+'\n')
    # Placement correction is not its own proof: independently read the final
    # BSP/MDL payload, and stop before fingerprinting or HDF creation on failure.
    from check_actor_ground import require as require_actor_ground
    require_actor_ground(boot/'id1/maps',out/'actor-initial-contact.json')
    write_content_fingerprint(boot/'id1')
    manifest=json.loads((music/'soundtrack.json').read_text());groups=playlists(manifest['tracks'])
    opening_track=manifest['tracks'][4] if 4 in groups['explore'] else None
    if opening_track:
        print('Opening music track 04: '+opening_track['source'],flush=True)
    else:
        print('[warning] Track 04 is not available in the exploration playlist; runtime will use normal music selection.',flush=True)
    target=boot/'id1/music';target.mkdir()
    for track in manifest['tracks']:
        source=music/track['file'];unpack_stream(source.read_bytes())
        if digest(source)!=track['sha256']:raise ValueError('Music manifest mismatch')
        shutil.copyfile(source,target/track['file'])
    shutil.copyfile(music/'soundtrack.json',target/'soundtrack.json')
    (target/'playlist.txt').write_text('\n'.join(' '.join(map(str,[len(groups[g]),*groups[g]])) for g in ['explore','battle'])+'\n'+str(groups['title'])+'\n')
    # Leave filesystem metadata and future saves room; retain legacy-safe sizes.
    from world_volumes import pack as pack_world_volumes
    world_images=pack_world_volumes(boot/'id1',out,VERSION,args.xdftool,args.rdbtool)
    check_payload_names(boot)
    payload_bytes=sum(p.stat().st_size for p in boot.rglob('*') if p.is_file())
    partition_mib=max(128,((payload_bytes*6//5 + 16*1024*1024 + 127*1024*1024)//(128*1024*1024))*128)
    if partition_mib>=2048:raise ValueError('Boot partition must remain below 2 GiB')
    part=out/'partition.hdf';hdf=out/f'AmiWind-v{VERSION}.hdf'
    cmd=[args.xdftool,part,'create',f'size={partition_mib}Mi','+','format','AMIWIND','ffs','+','boot','install']
    for path in sorted((p for p in boot.rglob('*') if p.is_dir()),key=lambda p:len(p.parts)):
        cmd+=['+','makedir',path.relative_to(boot).as_posix()]
    for path in sorted(p for p in boot.rglob('*') if p.is_file()):cmd+=['+','write',path,path.relative_to(boot).as_posix()]
    run(cmd)
    root_check=check_image(part,normalize=True)
    total_mib=partition_mib+sum(p['bytes']//(1024*1024) for p in world_images)
    if total_mib*1024*1024+32768>=4*1024**3:
        raise ValueError('Combined legacy hardfile must remain below 4 GiB')
    command=[args.rdbtool,hdf,'create',f'chs={total_mib*32+1},1,64','+','init',
             '+','addimg',part,'name=DH0','bootable=1','pri=0']
    for volume in world_images:
        command+=['+','addimg',out/volume['file'],'name='+volume['partition'],'bootable=0']
    run(command)
    # Independently mount the finished RDB and hash every stored payload.
    from world_volumes import verify_combined
    boot_files=[dict(path=p.relative_to(boot).as_posix(),bytes=p.stat().st_size,sha256=digest(p))
                for p in sorted(boot.rglob('*')) if p.is_file()]
    layout=verify_combined(hdf,[dict(partition='DH0',volume='AMIWIND',files=boot_files),*world_images])
    for volume in world_images:(out/volume['file']).unlink()
    part.unlink()
    (out/'build.json').write_text(json.dumps({'version':VERSION,'hands':args.hands,'default_start':{'profile':'logo-fade-then-main-menu','movie':'intro/amiwind.awv','music_track':groups['title'],'new_game_map':'prison','new_game_movie':'intro/mw_intro.awv' if movie.exists() else None,'new_game_music_track':4,'new_game_music_source':opening_track['source'] if opening_track else None},'hdf_bytes':hdf.stat().st_size,'hdf_sha256':digest(hdf),'binary_sha256':digest(boot/'AmiWind'),'bootcheck_sha256':digest(boot/'AmiWindCheck'),'payload_bytes':sum(p['payload_bytes'] for p in layout),'partitions':layout,'music_tracks':len(manifest['tracks']),'heap_reservation_bytes':11*1024*1024,'tested_minimum':False,'filesystem':'DOS1 FFS partitions in one RDB HDF','legacy_root_check':root_check},indent=2)+'\n')
    print(hdf)

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    e=sub.add_parser('engine');e.add_argument('--cpu',choices=['68020','68040'],default='68040');e.add_argument('--archive',type=Path,help='Optional legacy provenance check; source is always engine/aga in this repository');e.add_argument('--out',type=Path,required=True);e.add_argument('--sdk',type=Path,required=True);e.add_argument('--vasm',type=Path,help='68000 preflight assembler; defaults to the SDK vasm')
    add_jobs(e)
    i=sub.add_parser('image')
    i.add_argument('--data-files',type=Path,help='Owned original font and UI assets; absent retains fallback')
    i.add_argument('--intro-captions',type=Path,help='Private JSON title cards; first card becomes a switchable opening overlay')
    i.add_argument('--bootcheck',type=Path,help='Defaults to AmiWindCheck beside the engine binary')
    for name in ['scene','music','engine','out','qcc','qbsp','vis','light','xdftool','rdbtool']:i.add_argument('--'+name,type=Path,required=True)
    for parser in (e,i):parser.add_argument('--hands',choices=['3d','sprites'],default='3d',help='Compile-time first-person renderer; retain both conversion paths')
    args=p.parse_args()
    # Resolve executables before subprocess cwd changes.
    for name in ['qcc','qbsp','vis','light','xdftool','rdbtool','engine','bootcheck']:
        if getattr(args,name,None) is not None:setattr(args,name,getattr(args,name).resolve())
    try:(engine if args.action=='engine' else image)(args)
    except (OSError,ValueError,subprocess.CalledProcessError) as exc:p.exit(1,f'Error: {exc}\n')
if __name__=='__main__':main()
