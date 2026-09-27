#!/usr/bin/env python3
"""Build the separate GPLv2 AGA runtime and an owner-only boot image."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from mwad.paths import ensure_external
from prepare_music import playlists, unpack_stream
from check_aga_binary import check_binary
from amiga_fs import check_image
from project_version import VERSION, check_native_versions

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
    return tree,hashes

def engine(args):
    check_native_versions()
    # Optional legacy input only verifies provenance; it never replaces repo source.
    if args.archive and digest(args.archive)!=UPSTREAM_SHA256:raise ValueError('Upstream archive checksum mismatch')
    out=new_output(args.out)
    tree,source_hashes=stage_runtime(out)
    env=os.environ.copy();env['PATH']=str(args.sdk.resolve()/'bin')+os.pathsep+env.get('PATH','')
    run(['make','-B','-j4',('nofpu' if args.cpu=='68020' else 'fpu'),'CC=m68k-amigaos-gcc'+CC_FLAGS+' -DAMIWIND_SPRITE_HANDS='+('1' if args.hands=='sprites' else '0'),'NDK_INC='+str(args.sdk.resolve()/'m68k-amigaos/ndk-include')],tree,env)
    binary=tree/('build/AmiQuakeGCC-NoFPU' if args.cpu=='68020' else 'build/AmiQuakeGCC')
    check_binary(binary.read_bytes())
    checker=tree/'build/AmiWindCheck'
    vasm=args.vasm.resolve() if args.vasm else args.sdk.resolve()/'bin/vasmm68k_mot'
    run([vasm,'-m68000','-Fhunkexe','-kick1hunks','-nosym','-I',args.sdk.resolve()/'m68k-amigaos/ndk-include','-o',checker,tree/'boot/bootcheck.asm'])
    check_binary(checker.read_bytes())
    (out/'engine-build.json').write_text(json.dumps({'version':VERSION,'hands':args.hands,'source_kind':'repository engine/aga','source_sha256':source_hashes,'upstream_commit':UPSTREAM_COMMIT,'baseline_upstream_archive_sha256':UPSTREAM_SHA256,'binary':str(binary),'binary_sha256':digest(binary),'bootcheck_sha256':digest(checker)},indent=2)+'\n')
    print(binary)

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
    config=re.sub(r'(?m)^r_max(?:surfs|edges) [^\n]*\n?', '', cfg.read_text())
    config=re.sub(r'(?m)^aw_drawdistance [^\n]*\n?', '', config)
    config=config.replace('bind 2 "aw_drawdistance 700"','bind 2 "aw_drawdistance 540"')
    config='aw_drawdistance 540\n'+config
    cfg.write_text(config.replace('bind ESCAPE quit','bind ESCAPE togglemenu').replace('r_drawviewmodel 0','r_drawviewmodel 1').replace('map seyda',
        'r_maxsurfs 10240\nr_maxedges 20480\nshowram 0\nbind MOUSE1 +attack\nbind F10 toggleconsole\nbind e +aw_use\nbind f "impulse 202"\nbind q +movedown\nmap seyda'))
    if (scene/'id1/maps/prison.bsp').is_file():cfg.write_text(cfg.read_text().replace('map seyda','map prison'))
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
    qc=out/'qc';qc.mkdir()
    for name in ['defs.qc','world.qc']:shutil.copyfile(ROOT/'engine/aga/qc'/name,qc/name)
    if args.hands=='sprites':
        if not (scene/'id1/gfx/hands.aws').is_file():raise ValueError('Bake hand sprites first')
        q=qc/'world.qc';q.write_text(q.read_text().replace('progs/v_nord.mdl','progs/player.mdl'))
    (qc/'progs.src').write_text('../boot/id1/progs.dat\ndefs.qc\nworld.qc\n');run([args.qcc],qc)
    manifest=json.loads((music/'soundtrack.json').read_text());groups=playlists(manifest['tracks'])
    target=boot/'id1/music';target.mkdir()
    for track in manifest['tracks']:
        source=music/track['file'];unpack_stream(source.read_bytes())
        if digest(source)!=track['sha256']:raise ValueError('Music manifest mismatch')
        shutil.copyfile(source,target/track['file'])
    shutil.copyfile(music/'soundtrack.json',target/'soundtrack.json')
    (target/'playlist.txt').write_text('\n'.join(' '.join(map(str,[len(groups[g]),*groups[g]])) for g in ['explore','battle'])+'\n')
    # 128 MiB FFS partition, well below legacy size boundaries. No Workbench files.
    part=out/'partition.hdf';hdf=out/f'AmiWind-v{VERSION}.hdf'
    cmd=[args.xdftool,part,'create','size=128Mi','+','format','AMIWIND','ffs','+','boot','install']
    for path in sorted((p for p in boot.rglob('*') if p.is_dir()),key=lambda p:len(p.parts)):
        cmd+=['+','makedir',path.relative_to(boot).as_posix()]
    for path in sorted(p for p in boot.rglob('*') if p.is_file()):cmd+=['+','write',path,path.relative_to(boot).as_posix()]
    run(cmd)
    root_check=check_image(part,normalize=True)
    run([args.rdbtool,hdf,'create','chs=4097,1,64','+','init','+','addimg',part,'name=DH0','bootable=1','pri=0'])
    # Verify every payload via an independent read from the finished RDB image.
    check=out/'readback.tmp'
    for path in sorted(p for p in boot.rglob('*') if p.is_file()):
        run([args.xdftool,hdf,'open','part=DH0','+','read',path.relative_to(boot).as_posix(),check])
        if digest(check)!=digest(path):raise ValueError('HDF readback mismatch')
        check.unlink()
    check_image(hdf,partition="DH0")
    part.unlink()
    (out/'build.json').write_text(json.dumps({'version':VERSION,'hands':args.hands,'hdf_bytes':hdf.stat().st_size,'hdf_sha256':digest(hdf),'binary_sha256':digest(boot/'AmiWind'),'bootcheck_sha256':digest(boot/'AmiWindCheck'),'payload_bytes':sum(p.stat().st_size for p in boot.rglob('*') if p.is_file()),'music_tracks':len(manifest['tracks']),'heap_reservation_bytes':9*1024*1024,'tested_minimum':False,'filesystem':'FFS, 128 MiB partition in RDB','legacy_root_check':root_check},indent=2)+'\n')
    print(hdf)

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    e=sub.add_parser('engine');e.add_argument('--cpu',choices=['68020','68040'],default='68040');e.add_argument('--archive',type=Path,help='Optional legacy provenance check; source is always engine/aga in this repository');e.add_argument('--out',type=Path,required=True);e.add_argument('--sdk',type=Path,required=True);e.add_argument('--vasm',type=Path,help='68000 preflight assembler; defaults to the SDK vasm')
    i=sub.add_parser('image')
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
