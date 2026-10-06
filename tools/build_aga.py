#!/usr/bin/env python3
"""Build the GPLv2 AGA runtime and an owner-only boot image.

CAPACITY FIRST: before starting the build, verify enough usable storage for ALL
required content, conversion intermediates, staging copies, temporary images,
readback verification and a margin. Include filesystem/quota limits and shared
RAM limits for memory-backed scratch. If capacity is insufficient, arrange it
before expensive work; never omit NPC models or the gallery to make a build fit.

All NPCs must be included and loadable by the engine for the game to be complete.
NPC gallery creation MUST NOT be skipped except for exceptional, explicitly
requested debugging purposes. Build time and disk usage are not reasons to omit it.

Normal builds and recovery MUST include the gallery; missing input/model/catalogue
content is an error, never an automatic opt-out. Only the owner's explicit
--no-npc-gallery permits debugging-only omission of inspection assets. It must
never remove required game NPC content or change the normal default.

Skipping NPC model creation together with the gallery is pointless and
counterproductive for a complete build: all character models are still required
in the final product. Exceptional debugging may temporarily isolate the gallery;
it cannot reduce the final game's required content.

BOTH GALLERIES REQUIRE OUTSIDE APPROVAL FOR EXCEPTIONS: the NPC gallery and
upcoming static-asset gallery, including their model generation, catalogues,
coverage, quality and validation, must not be disabled, reduced or bypassed
without a specific documented case/scenario and explicit approval from the
project owner. The builder or contributor cannot approve its own exception.
Time pressure, storage pressure and convenience are not approval. Existing
--no-npc-gallery support is only a mechanism for an owner-approved exceptional
debugging case; its availability does not grant permission to use it.

A complete game requires all of its NPC and other game assets intact, packaged
and loadable by the engine. Skipping model/asset creation with either gallery is
pointless and counterproductive: those assets are required in the final product
anyway. A debugging exception cannot redefine a complete build. Loadable does not
mean all assets must be resident in memory simultaneously. The static-asset
gallery remains planned; this contract does not claim it is implemented.
"""
import argparse
import hashlib
import json
import math
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
from build_host import executable_path, make_python_assignment

ROOT=Path(__file__).resolve().parents[1]
UPSTREAM_COMMIT='9c62d905151614af3e788ae3145a0d4ecc8a7bb8'
UPSTREAM_SHA256='43353034beb2a43b1af82c735f93c0a8bee8129c1b93d7ba152dd8e60ad3721c'
RUNTIME_SOURCE=ROOT/'engine/aga'
HEAP_LOADER_SOURCE_PATHS = (
    'Makefile',
    'src/model.c', 'src/model.h', 'src/zone.c', 'src/zone.h',
    'src/common.c', 'src/sys_amiga.c',
    'src/aw_guard_torch.c', 'src/aw_torch.c',
    'src/aw_harvest.c', 'src/aw_harvest.h', 'src/aw_harvest_runtime.c', 'src/aw_harvest_runtime.h',
    'src/aw_harvest_proxy.c', 'src/aw_harvest_proxy.h',
    'src/aw_scenery.c', 'src/pr_edict.c', 'src/aw_scene.c', 'src/aw_spawn.c', 'src/aw_console.c',
    'src/render.h', 'src/r_sprite.c', 'src/r_efrag.c', 'src/r_main.c',
    'src/cl_parse.c', 'src/cl_main.c', 'src/client.h', 'src/pr_cmds.c', 'src/protocol.h', 'qc/world.qc',
    'src/quakedef.h', 'src/server.h', 'src/net.h', 'src/host.c', 'src/net_main.c', 'src/net_loop.c',
)
RUNTIME_BUILD_DIR='runtime'
CC_FLAGS=' -std=gnu89 -Wno-implicit-function-declaration -Wno-int-conversion -Wno-incompatible-pointer-types'

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def run(args,cwd=None,env=None):subprocess.run(list(map(str,args)),cwd=cwd,env=env,check=True)
def heap_watcher_summary(report, report_path):
    """Expose estimated use and spare capacity; never invent target measurements."""
    budget = report['heap_budget_bytes']
    baseline = report['baseline_reserve_bytes']
    safety = report['safety_headroom_bytes']
    worst = next(row for row in report['maps'] if row['map'] == report['worst_map'])
    peak = worst['peak_loader_bytes']
    return {
        'schema_version': 1,
        'status': 'estimate_failed' if report['failing_maps'] else 'estimate_passed',
        'measurement_kind': 'target-ABI static estimate',
        'heap_budget_bytes': budget,
        'worst_map': worst['map'],
        'estimated_map_peak_used_bytes': peak,
        'estimated_free_before_reserves_bytes': budget - peak,
        'non_map_reserve_bytes': baseline,
        'required_safety_headroom_bytes': safety,
        'estimated_committed_with_reserves_bytes': peak + baseline + safety,
        'estimated_growth_margin_after_reserves_bytes': budget - peak - baseline - safety,
        'map_count': report['map_count'],
        'over_budget_maps': list(report['failing_maps']),
        'report': Path(report_path).name,
        'report_sha256': digest(report_path),
        'loader_source_sha256': report.get('loader_source_sha256', {}),
        'runtime_validation': 'pending',
        'runtime_measured_used_bytes': None,
        'runtime_measured_free_bytes': None,
        'runtime_log': 'heap-audit.log',
        'acceptance': report['acceptance'],
    }

def apply_map_budget_policy(report, policy='strict', receipt_path=None):
    """Opt in to modeled reserve warnings; never waive loader/allocation errors."""
    if policy not in ('strict', 'warning'):
        raise ValueError('Map budget policy must be strict or warning')
    ceiling = report['heap_budget_bytes']
    if ceiling <= 0 or report['baseline_reserve_bytes'] <= 0 or report['safety_headroom_bytes'] <= 0:
        raise ValueError('Invalid heap ceiling or reserve data')
    hard_failures = [row['map'] for row in report['maps'] if row['peak_loader_bytes'] >= ceiling]
    failures = list(report['failing_maps'])
    status = ('estimate_allocation_ceiling_failed' if hard_failures else
              'estimate_warning_needs_adjustment' if failures and policy == 'warning' else
              'estimate_failed' if failures else 'estimate_passed')
    decision = {'policy': policy, 'status': status,
                'modeled_allowance_passed': not failures,
                'private_assembly_allowed': not hard_failures and (not failures or policy == 'warning'),
                'production_memory_gate_passed': not failures and not hard_failures,
                'heap_budget_bytes': ceiling,
                'baseline_reserve_bytes': report['baseline_reserve_bytes'],
                'safety_headroom_bytes': report['safety_headroom_bytes'],
                'allowance_failures': failures, 'allocation_ceiling_failures': hard_failures,
                'runtime_validation': 'pending; runtime allocation errors remain fatal',
                'scope': 'modeled reserve allowance only; assets, geometry, collision and all other gates unchanged'}
    if receipt_path is not None:
        Path(receipt_path).write_text(json.dumps(decision, indent=2) + '\n', encoding='utf-8', newline='\n')
    if not decision['private_assembly_allowed']:
        raise ValueError('World-map heap clearance estimate failed: ' + status + '; ' + ', '.join(hard_failures or failures))
    return decision


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
            source.write_text(source.read_text().replace('progs/v_nord.mdl', 'progs/player.mdl'), newline='\n')
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

def verify_heap_loader_source_receipt(engine_record, source=None):
    """Bind the BSP estimate to the loader/heap source used by this engine."""
    source = Path(source or RUNTIME_SOURCE)
    recorded = engine_record.get('source_sha256')
    if not isinstance(recorded, dict):
        raise ValueError('Engine build receipt is missing runtime source hashes')
    current = {}
    stale = []
    for relative in HEAP_LOADER_SOURCE_PATHS:
        path = source / relative
        if not path.is_file():
            raise ValueError('Heap-critical runtime source is missing: ' + relative)
        actual = digest(path)
        current[relative] = actual
        if recorded.get(relative) != actual:
            stale.append(relative)
    if stale:
        raise ValueError('Engine build receipt is stale for heap-critical runtime sources: ' +
                         ', '.join(stale) + '; rebuild the engine before image assembly')
    return current

def audit_world_map_heap_with_receipt(engine_record, maps, sdk, out, source=None):
    """Run the map estimate only when it matches the engine's loader sources."""
    loader_hashes = verify_heap_loader_source_receipt(engine_record, source)
    from check_world_map_heap import audit_world_maps
    report = audit_world_maps(maps, sdk, out)
    report['loader_source_sha256'] = loader_hashes
    out = Path(out)
    out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
    return report

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
    run(['make','-B','--output-sync=target',f'-j{jobs}',('nofpu' if args.cpu=='68020' else 'fpu'),make_python_assignment(),'CC=m68k-amigaos-gcc'+CC_FLAGS+' -DAMIWIND_SPRITE_HANDS='+('1' if args.hands=='sprites' else '0'),'NDK_INC='+str(args.sdk.resolve()/'m68k-amigaos/ndk-include')],tree,env)
    binary=tree/('build/AmiQuakeGCC-NoFPU' if args.cpu=='68020' else 'build/AmiQuakeGCC')
    check_binary(binary.read_bytes())
    checker=tree/'build/AmiWindCheck'
    vasm=executable_path(args.vasm.resolve() if args.vasm else args.sdk.resolve()/'bin/vasmm68k_mot')
    run([vasm,'-m68000','-Fhunkexe','-kick1hunks','-nosym','-I',args.sdk.resolve()/'m68k-amigaos/ndk-include','-I',tree/'build/version','-o',checker,tree/'boot/bootcheck.asm'])
    check_binary(checker.read_bytes())
    (out/'engine-build.json').write_text(json.dumps({'version':VERSION,'hands':args.hands,'compiler_jobs':jobs,'source_kind':'repository engine/aga','source_sha256':source_hashes,'upstream_commit':UPSTREAM_COMMIT,'baseline_upstream_archive_sha256':UPSTREAM_SHA256,'binary':str(binary),'binary_sha256':digest(binary),'bootcheck_sha256':digest(checker)},indent=2)+'\n', newline='\n')
    print(binary)

def install_world_scenery(overlay, id1):
    """Validate a complete full-world overlay, then replace its terrain BSPs."""
    overlay, id1 = Path(overlay), Path(id1)
    receipt_path = overlay / 'world-scenery.json'
    if not receipt_path.is_file():
        raise ValueError('World scenery overlay receipt is required')
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    if receipt.get('format') != 'AmiWind world scenery overlay 1' or receipt.get('diagnostic_subset'):
        raise ValueError('A complete production world scenery overlay is required')
    region_dir = id1 / 'world/regions.awr'
    if not region_dir.is_file():
        raise ValueError('Complete terrain region directory is required before scenery installation')
    packet = region_dir.read_bytes()
    if len(packet) < 64 or packet[:4] != b'AWR2':
        raise ValueError('Invalid world terrain region directory')
    count = struct.unpack_from('<I', packet, 4)[0]
    if not count or count > 8192 or len(packet) != 64 + count * 52:
        raise ValueError('Invalid world terrain region directory size')
    expected_names = [f'vf{index:04d}' for index in range(count)]
    directory_names = [struct.unpack_from('<8s11f', packet, 64 + index * 52)[0].split(b'\0', 1)[0].decode('ascii')
                       for index in range(count)]
    if directory_names != expected_names:
        raise ValueError('World terrain region names differ from the expected runtime sequence')
    regions = receipt.get('regions')
    if not isinstance(regions, list) or [r.get('name') for r in regions] != expected_names:
        raise ValueError('World scenery overlay does not cover every terrain region in order')
    palette = id1 / 'gfx/palette.lmp'
    if not palette.is_file() or digest(palette) != receipt.get('palette_sha256'):
        raise ValueError('World scenery overlay palette differs from the boot scene')
    unique_references = set()
    replacements = []
    for region in regions:
        name = region['name']
        if not re.fullmatch(r'vf\d{4}', name):
            raise ValueError('Invalid world scenery region name')
        source = id1 / 'maps' / f'{name}.bsp'
        if not source.is_file() or digest(source) != region.get('original_terrain_sha256'):
            raise ValueError('World scenery overlay does not match retained terrain: ' + name)
        baked = overlay / name / 'scene.bsp'
        if not baked.is_file() or digest(baked) != region.get('sha256'):
            raise ValueError('World scenery BSP is missing or changed: ' + name)
        expected_bytes = region.get('bytes')
        # Legacy empty-region receipts omitted size; only unchanged terrain is
        # eligible. Both hashes were checked above; populated regions stay strict.
        if ('bytes' not in region and region.get('retained_terrain_only') is True
                and region.get('instances') == 0 and region.get('unique_models') == 0
                and region.get('source_references') == []
                and region.get('sha256') == region.get('original_terrain_sha256')):
            expected_bytes = source.stat().st_size
        if baked.stat().st_size != expected_bytes:
            raise ValueError('World scenery BSP size differs from receipt: ' + name)
        references = region.get('source_references')
        if not isinstance(references, list) or len(references) != region.get('instances'):
            raise ValueError('World scenery reference count differs from receipt: ' + name)
        local_references = set()
        for reference in references:
            if reference.get('kind') not in ('rock', 'giant_mushroom'):
                raise ValueError('Unexpected source placement in rc3 scenery overlay')
            identity = (json.dumps(reference.get('cell'), sort_keys=True, separators=(',', ':')),
                        reference.get('number'))
            if identity in local_references:
                raise ValueError('Duplicate source placement within overlay region: ' + name)
            local_references.add(identity)
            unique_references.add(identity)
        replacements.append((baked, source))
    if len(unique_references) != receipt.get('covered_source_references'):
        raise ValueError('World scenery coverage total differs from region references')
    for baked, destination in replacements:
        shutil.copyfile(baked, destination)
    result = {'status': 'passed', 'format': receipt['format'], 'regions': count,
              'covered_source_references': len(unique_references),
              'palette_sha256': receipt['palette_sha256'],
              'terrain_directory_sha256': receipt.get('terrain_directory_sha256'),
              'scenery_index_sha256': receipt.get('scenery_index_sha256'),
              'receipt_sha256': digest(receipt_path)}
    return result


def town_region_map_names(directory, prefix):
    """Fingerprint the actual native region table, including adaptive additions."""
    rows=Path(directory).read_text(encoding='ascii').splitlines()
    if not rows:raise ValueError('Missing town region header: '+str(directory))
    header=rows[0].split()
    try:
        count=int(header[1])
        values=list(map(float,header[2:]))
    except (ValueError,IndexError) as exc:
        raise ValueError('Invalid town region header: '+str(directory)) from exc
    if (len(header)!=12 or header[0]!='AWBR1' or not 1<=count<=64 or
        len(rows)!=count+1 or not all(math.isfinite(v) for v in values) or
        not 0<=values[0]<=128 or values[1]!=540):
        raise ValueError('Invalid town region header/count: '+str(directory))
    names=[]
    for index,line in enumerate(rows[1:]):
        parts=line.split()
        try:xy=list(map(float,parts[1:]))
        except ValueError as exc:raise ValueError('Invalid town region bounds') from exc
        name=f'{prefix}{index:03d}'
        if (len(parts)!=9 or parts[0]!=name or not all(math.isfinite(v) for v in xy) or
            any(not (xy[i]<xy[i+2] and xy[i+4]<=xy[i] and xy[i+6]>=xy[i+2] and
                     abs(xy[i+4])<32768 and abs(xy[i+6])<32768) for i in range(2))):
            raise ValueError('Invalid town region row: '+str(directory))
        names.append('maps/'+name+'.bsp')
    return names

def harvest_fingerprint_entries(id1):
    """Bind optional pickup contents to saves, preserving the legacy namespace.

    Check the bounded catalogue envelope here; the native parser and original
    source/placement admission still own semantic validation. Hash every byte.
    """
    root=Path(id1);result=[];catalogue_kind=None;global_index=None;model_files={}
    for path in sorted(root.glob('harvest-*.txt'),key=lambda item:item.name):
        match=re.fullmatch(r'harvest-([a-z0-9_]{1,24})\.txt',path.name)
        if not match or path.is_symlink() or not path.is_file():
            raise ValueError('Invalid harvest catalogue path: '+path.name)
        if not (root/'maps'/(match[1]+'.bsp')).is_file():
            raise ValueError('Harvest catalogue has no matching map: '+path.name)
        if not 0 < path.stat().st_size <= 65536:
            raise ValueError('Harvest catalogue exceeds runtime byte bound: '+path.name)
        raw=path.read_bytes()
        try:text=raw.decode('ascii')
        except UnicodeDecodeError:
            raise ValueError('Harvest catalogue is not ASCII: '+path.name) from None
        lines=text.splitlines()
        header=re.fullmatch(r'AWH([1234]) ([0-9]+) ([0-9]+) ([0-9]+)(?: ([0-9]+) ([0-9a-f]{64}))?(?: ([0-9]+))?',lines[0]) if lines else None
        if not header or any(ord(c)<32 and c not in '\r\n\t' for c in text):
            raise ValueError('Invalid harvest catalogue envelope: '+path.name)
        version,nodes,edges,plants,slots,identity,models=header.groups()
        indexed=version in ('3','4')
        if indexed != (slots is not None):
            raise ValueError('Invalid harvest catalogue envelope: '+path.name)
        counts=tuple(map(int,(nodes,edges,plants)))
        external=version=='4'
        if external != (models is not None):
            raise ValueError('Invalid external harvest catalogue envelope: '+path.name)
        models=int(models) if external else 0
        if (external and not 1<=models<=8) or any(n>limit for n,limit in zip(counts,(64,256,24))) or len(lines)!=1+sum(counts)+models:
            raise ValueError('Invalid harvest catalogue counts: '+path.name)
        if catalogue_kind is not None and catalogue_kind!=indexed:
            raise ValueError('Mixed legacy and indexed harvest catalogues: '+path.name)
        catalogue_kind=indexed
        if indexed:
            index=(int(slots),identity)
            if not 1<=index[0]<=4096 or identity=='0'*64:
                raise ValueError('Invalid harvest global index: '+path.name)
            if global_index is not None and global_index!=index:
                raise ValueError('Mismatched harvest global index: '+path.name)
            global_index=index
        result.append((path.name,hashlib.sha256(raw).hexdigest()))
        if external:
            from harvest_alias import model_entries
            for name,hash_value in model_entries(root,lines[1:1+models]):
                if name in model_files and model_files[name]!=hash_value:
                    raise ValueError('Conflicting external harvest model binding: '+name)
                model_files[name]=hash_value
    result.extend(sorted(model_files.items()))
    return result


def write_content_fingerprint(id1):
    fingerprint=hashlib.sha256()
    from area_config import SCENES
    town_maps=town_region_map_names(Path(id1)/'seyda-regions.txt','sn')+town_region_map_names(Path(id1)/'balmora-regions.txt','bm')
    for name in [*(f"maps/{s['map']}.bsp" for s in SCENES), 'maps/intro_docks.bsp', 'maps/sncourt.bsp', 'seyda-regions.txt', 'balmora-regions.txt', *town_maps, 'progs.dat', 'character/catalog.awc', 'world/map.awm', 'world/journal.awj', 'world/entries.dat', 'world/quests.awq', 'world/region-names.awn']:
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
    from prepare_guard_torches import fingerprint_entries
    def optional_asset(name):
        path=Path(id1)/name
        return path.read_bytes() if path.is_file() else None
    for name,hash_value in fingerprint_entries(optional_asset):
        fingerprint.update(name.encode('ascii')+b'\0'+bytes.fromhex(hash_value))
    for name,hash_value in harvest_fingerprint_entries(id1):
        fingerprint.update(name.encode('ascii')+b'\0'+bytes.fromhex(hash_value))
    (Path(id1)/'save-content.bin').write_bytes(fingerprint.digest())


def image(args):
    """Package the NPC gallery by default; fail if any required payload is absent.

    The sole opt-out is explicit --no-npc-gallery, recorded in build.json and
    the image itself. Asset-free boot-notice images use build_dry_run.py.
    """
    if getattr(args, 'allow_known_actor_ground_findings', None):
        from check_actor_ground import load_approved_report
        args.allow_known_actor_ground_findings = args.allow_known_actor_ground_findings.resolve()
        load_approved_report(args.allow_known_actor_ground_findings)
    if getattr(args, 'world_flora', None):
        for field in ('town_flora_source_index', 'town_flora_scene_report', 'balmora_cache'):
            value = getattr(args, field, None)
            if not value or not Path(value).exists():
                raise ValueError('Complete flora image requires --' + field.replace('_', '-'))
    check_binary(args.engine.read_bytes())
    checker=args.bootcheck or args.engine.parent/'AmiWindCheck'
    check_binary(checker.read_bytes())
    receipt=args.engine.parents[2]/'engine-build.json'
    if not receipt.is_file():raise ValueError('Engine build receipt is required')
    engine_record=json.loads(receipt.read_text())
    if engine_record.get('version')!=VERSION or engine_record.get('binary_sha256')!=digest(args.engine) or engine_record.get('bootcheck_sha256')!=digest(checker):
        raise ValueError('Engine/preflight does not match the current versioned build receipt')
    heap_loader_source_sha256=verify_heap_loader_source_receipt(engine_record)
    build_mode=engine_record.get('hands','3d')
    if build_mode!=args.hands:raise ValueError('Image hands choice must match engine build')
    scene=ensure_external(args.scene,'AGA scene');music=ensure_external(args.music,'converted music');out=new_output(args.out)
    boot=out/'boot';shutil.copytree(scene/'id1',boot/'id1');(boot/'S').mkdir()
    terrain = getattr(args, 'world_terrain', None)
    if terrain:
        from install_world_terrain import install as install_world_terrain
        terrain_acceptance = install_world_terrain(terrain, boot/'id1')
        (out/'world-terrain-staging.json').write_text(json.dumps(terrain_acceptance,indent=2)+'\n',encoding='utf-8',newline='\n')
    world_scenery_acceptance=install_world_scenery(args.world_scenery,boot/'id1')
    (out/'world-scenery-staging.json').write_text(json.dumps(world_scenery_acceptance,indent=2)+'\n',encoding='utf-8',newline='\n')
    flora = getattr(args, 'world_flora', None)
    if flora:
        from install_world_flora import install as install_world_flora
        flora_acceptance = install_world_flora(flora, boot/'id1', world_scenery_acceptance)
        (out/'world-flora-staging.json').write_text(json.dumps(flora_acceptance, indent=2)+'\n', encoding='utf-8', newline='\n')
    cfg=boot/'id1/default.cfg'
    cfg.write_text(startup_config(cfg.read_text()), newline='\n')
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
    if not args.data_files:raise ValueError('Owned data files are required to convert the original carried torch')
    from prepare_torch import prepare as prepare_torch
    print('Converting original torch and first-person holding animation...',flush=True)
    torch_report=prepare_torch(args.data_files,boot/'id1')
    from build_gallery import stage_required, omit_gallery
    if args.no_npc_gallery:
        gallery_report=omit_gallery(boot/'id1')
    else:
        gallery_report=stage_required(args.gallery,boot/'id1')
    (out/'npc-gallery-staging.json').write_text(json.dumps(gallery_report,indent=2)+'\n', newline='\n')
    (out/'torch-conversion.json').write_text(json.dumps(torch_report,indent=2)+'\n', newline='\n')
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
    (boot/'id1/quake.rc').write_text('exec default.cfg\nexec default-game.cfg\nexec config.cfg\nexec keymap.cfg\nexec keymaps.cfg\nexec autoexec.cfg\naw_controls_migrate\naw_gallery_migrate\naw_startup\n', newline='\n')
    print('Default start: logo fade then main menu; New Game plays the optional movie then ship + track 04.',flush=True)
    shutil.copyfile(args.engine,boot/'AmiWind')
    shutil.copyfile(checker,boot/'AmiWindCheck')
    (boot/'S/startup-sequence').write_text('FailAt 10\nSYS:AmiWindCheck\nStack 300000\nSYS:AmiWind\n', newline='\n')
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
    convert_seyda_regions(boot/'id1/maps/seyda.bsp',boot/'id1/maps',
                          source_map=out/'seyda.map',
                          palette=boot/'id1/gfx/palette.lmp',
                          ericw_bin=args.qbsp.parent,
                          threads=8, work_dir=out/'bounded-seyda')
    if getattr(args, 'balmora_cache', None):
        from repair_balmora_maps import repair as repair_balmora_maps
        print('Preparing measured bounded Balmora layout from complete source cache...', flush=True)
        repair_balmora_maps(boot/'id1/maps', cache=args.balmora_cache,
                           palette=boot/'id1/gfx/palette.lmp', ericw_bin=args.qbsp.parent,
                           work_dir=out/'bounded-balmora', threads=4)
    if flora:
        from install_town_flora import install as install_town_flora
        from prepare_quake import CENTRE
        from balmora_regions import config as balmora_config, regions as balmora_regions
        town_palette = args.scene/'id1/gfx/palette.lmp'
        seyda_origin = [CENTRE[0]*.25, CENTRE[1]*.25, 0.]
        actual = json.loads((boot/'id1/seyda-regions.json').read_text(encoding='utf-8'))
        seyda_entries = [{**entry, 'origin':seyda_origin} for entry in actual['regions']]
        towns = {'seyda':install_town_flora(boot, flora, town_palette,
            entries=seyda_entries, town_source_index=args.town_flora_source_index,
            town_scene_report=args.town_flora_scene_report, work_dir=out/'town-flora-seyda')}
        shutil.copyfile(boot/'id1/maps'/(actual['fallback_alias']+'.bsp'), boot/'id1/maps/seyda.bsp')
        settings = balmora_config()
        balmora_origin = [v*settings['scale'] for v in settings['centre']]+[0.]
        towns['balmora'] = install_town_flora(boot, flora, town_palette,
            entries=[{**entry, 'origin':balmora_origin} for entry in balmora_regions(settings)],
            town_source_index=args.balmora_cache/'scenery/scenery-index.json',
            work_dir=out/'town-flora-balmora')
        # Match the installed runtime directory's named fallback alias.
        rows=(boot/'id1/balmora-regions.txt').read_text(encoding='ascii').splitlines()
        point=tuple(map(float,rows[0].split()[4:6]))
        fallback=next(row.split()[0] for row in rows[1:] if
            float(row.split()[1]) <= point[0] < float(row.split()[3]) and
            float(row.split()[2]) <= point[1] < float(row.split()[4]))
        shutil.copyfile(boot/'id1/maps'/(fallback+'.bsp'), boot/'id1/maps/balmora.bsp')
        flora_acceptance['towns'] = {name:{k:v for k,v in result.items() if k!='maps'} for name,result in towns.items()}
        (out/'world-flora-staging.json').write_text(json.dumps(flora_acceptance,indent=2)+'\n',encoding='utf-8',newline='\n')
    qc=out/'qc';qc.mkdir()
    for name in ['defs.qc','world.qc']:shutil.copyfile(ROOT/'engine/aga/qc'/name,qc/name)
    if args.hands=='sprites':
        if not (scene/'id1/gfx/hands.aws').is_file():raise ValueError('Bake hand sprites first')
        q=qc/'world.qc';q.write_text(q.read_text().replace('progs/v_nord.mdl','progs/player.mdl'), newline='\n')
    (qc/'progs.src').write_text('../boot/id1/progs.dat\ndefs.qc\nworld.qc\n', newline='\n');run([args.qcc],qc)
    validate_quakec(boot/'id1/progs.dat')
    # Saved mutable state is only restored against this exact converted content.
    if args.data_files:
        from actor_grounding import annotate, bake_ground
        from mwad.paths import child_ci
        grounding=annotate(boot/'id1/maps',child_ci(args.data_files,'Morrowind.esm'))
        (out/'actor-grounding.json').write_text(json.dumps(grounding,indent=2)+'\n', newline='\n')
        (out/'actor-ground-support.json').write_text(json.dumps(bake_ground(boot/'id1/maps'),indent=2)+'\n', newline='\n')
    return finalize_image(args)


def staged_exterior_map_names(id1):
    """Explicit runtime directories identify exterior cells; sky is not a classifier."""
    id1 = Path(id1)
    names = {name for name in ('seyda', 'balmora', 'intro_docks', 'sncourt')
             if (id1 / 'maps' / (name + '.bsp')).is_file()}
    for table, prefix in (('seyda-regions.txt', 'sn'), ('balmora-regions.txt', 'bm')):
        directory = id1 / table
        if directory.is_file():
            names.update(Path(name).stem for name in town_region_map_names(directory, prefix))
    directory = id1 / 'world/regions.awr'
    if directory.is_file():
        raw = directory.read_bytes()
        if len(raw) < 64 or raw[:4] != b'AWR2':
            raise ValueError('Invalid world region directory for hidden-surface pass')
        count = struct.unpack_from('<I', raw, 4)[0]
        if len(raw) != 64 + count * 52:
            raise ValueError('World region count mismatch for hidden-surface pass')
        names.update(f'vf{index:04d}' for index in range(count))
    return names


def staged_interior_map_names(id1):
    """Only explicit authored scene catalogue interior classifications apply."""
    from area_config import SCENES
    id1 = Path(id1)
    return {scene["map"] for scene in SCENES if scene.get("interior") is True
            and (id1 / "maps" / (scene["map"] + ".bsp")).is_file()}


def require_complete_media_outputs(media_coverage):
    """Fail image creation when an available original has no validated output.

    Missing original sources remain separate coverage warnings; they are not
    treated as failed conversions.
    """
    categories = media_coverage.get('categories') if isinstance(media_coverage, dict) else None
    if not isinstance(categories, dict):
        raise ValueError('Media coverage report is missing category counts')
    expected_categories = ('videos', 'music', 'voices', 'effects')
    missing = {}
    for category in expected_categories:
        counts = categories.get(category)
        if not isinstance(counts, dict):
            raise ValueError('Media coverage report is missing counts for ' + category)
        count = counts.get('missing_output')
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise ValueError('Media coverage report has an invalid missing_output count for ' + category)
        if count:
            missing[category] = count
    if missing:
        details = ', '.join(f'{category}={count}' for category, count in missing.items())
        raise ValueError(
            'Available original media lacks validated converted output: ' + details +
            '. Missing original sources are warnings and are tracked separately; '
            'see media-coverage.json for the retained coverage counts.'
        )
    if media_coverage.get('status') != 'complete':
        raise ValueError('Media coverage status is not complete; see media-coverage.json')
    return True

def finalize_image(args):
    """Finalize an already prepared private image stage through every normal gate.

    This is the shared image tail, not a skip-validation/resume CLI. A separate
    controlled continuation must verify its frozen stage before invoking it.
    """
    out=ensure_external(args.out,'prepared AGA image')
    boot=out/'boot'
    music=ensure_external(args.music,'converted music')
    args.hands=getattr(args,'hands','3d')
    checker=getattr(args,'bootcheck',None) or args.engine.parent/'AmiWindCheck'
    check_binary(args.engine.read_bytes())
    check_binary(checker.read_bytes())
    receipt=args.engine.parents[2]/'engine-build.json'
    if not receipt.is_file():raise ValueError('Engine build receipt is required')
    engine_record=json.loads(receipt.read_text())
    if engine_record.get('version')!=VERSION or engine_record.get('binary_sha256')!=digest(args.engine) or engine_record.get('bootcheck_sha256')!=digest(checker):
        raise ValueError('Engine/preflight does not match the current versioned build receipt')
    if digest(boot/'AmiWind')!=engine_record['binary_sha256'] or digest(boot/'AmiWindCheck')!=engine_record['bootcheck_sha256']:
        raise ValueError('Staged engine/preflight differs from its verified build receipt')
    if engine_record.get('hands','3d')!=args.hands:
        raise ValueError('Image hands choice must match engine build')
    heap_loader_source_sha256=verify_heap_loader_source_receipt(engine_record)
    gallery_report=json.loads((out/'npc-gallery-staging.json').read_text())
    torch_report=json.loads((out/'torch-conversion.json').read_text())
    world_scenery_acceptance=json.loads((out/'world-scenery-staging.json').read_text())
    movie=boot/'id1/intro/mw_intro.awv'
    # Owned cloud conversion/palette reservation is source-reproducible and runs
    # before map/contact/heap gates and content fingerprints. Explicit shared
    # sources and local-skybox debug retain their caller-owned behavior.
    from prepare_shared_sky_assets import prepare_staged_sky
    sky_asset_preparation = prepare_staged_sky(boot / 'id1',
        getattr(args, 'data_files', None), out / 'sky-asset-preparation',
        shared_sky_source=getattr(args, 'shared_sky_source', None),
        local_skybox=getattr(args, 'local_skybox', 'false'))
    # The sky reservation remaps AWM1 pixels and rebinds their receipt. Check the
    # final palette contract, including reuse/custom-sky paths, before packaging.
    from prepare_world_ui import validate as validate_world_ui
    validate_world_ui(boot / 'id1')
    from prepare_guard_torches import prepare as prepare_guard_torches
    guard_torches = prepare_guard_torches(args.data_files, boot / 'id1')
    (out/'guard-torch-conversion.json').write_text(json.dumps(guard_torches,indent=2)+'\n', newline='\n')
    # Apply explicit sky policy after every mesh/overlay, before all final gates.
    from exterior_sky_build import configure_staged_maps
    exterior_sky_path = out / 'exterior-sky' / 'exterior-sky.json'
    exterior_sky = configure_staged_maps(boot / 'id1',
        exterior_maps=staged_exterior_map_names(boot / 'id1'),
        interior_maps=staged_interior_map_names(boot / 'id1'),
        local_skybox=getattr(args, 'local_skybox', 'false'),
        shared_sky_source=sky_asset_preparation['shared_sky_source'],
        work_dir=exterior_sky_path.parent)
    # Run after all meshes/overlays, before compaction, contact/heap and fingerprints.
    from hidden_surface_build import cull_staged_maps, enabled_value
    hidden_surface_path = out / 'hidden-surface-cull' / 'hidden-surfaces.json'
    hidden_surfaces = cull_staged_maps(boot / 'id1/maps', hidden_surface_path.parent,
        staged_exterior_map_names(boot / 'id1'),
        enabled=enabled_value(getattr(args, 'hidden_surface_cull', 'true')),
        jobs=getattr(args, 'optimizer_jobs', 6))
    # Regional map generation can replace a worldspawn after hands conversion.
    # Stamp all final maps from the same authored animation report before gates.
    from hand_metadata import stamp_staged_hands
    hand_source = json.loads((Path(args.scene)/'scene-ready.json').read_text())['hands']
    hand_metadata = stamp_staged_hands(boot/'id1', hand_source,
        staged_exterior_map_names(boot/'id1') | staged_interior_map_names(boot/'id1'))
    (out/'hand-metadata.json').write_text(json.dumps(hand_metadata,indent=2)+'\n', newline='\n')
    # Finish immutable BSP sharing before contact/heap gates and fingerprinting.
    # This step is interpreted Python only; it never creates a native helper.
    from optimize_world_maps import optimize_maps, verify_optimized_maps, bind_heap_report
    optimization_path = out/'optimize-world-maps.json'
    print('Verifying exact staged map geometry/light/PVS sharing...', flush=True)
    optimization = optimize_maps(boot/'id1/maps', optimization_path, jobs=getattr(args,'optimizer_jobs',6))
    # Placement correction is not its own proof: independently read the final
    # BSP/MDL payload, and stop before fingerprinting or HDF creation on failure.
    from check_actor_ground import require as require_actor_ground
    actor_report = require_actor_ground(boot/'id1/maps', out/'actor-initial-contact.json',
                                       getattr(args, 'allow_known_actor_ground_findings', None))
    actor_acceptance = actor_report['acceptance']
    (out/'actor-ground-acceptance.json').write_text(json.dumps(actor_acceptance, indent=2)+'\n', newline='\n')
    # Audit the final prepared payload after subdivision and actor annotation;
    # an earlier audit cannot authorize maps subsequently regenerated here.
    world_heap_path=out/'world-map-heap.json'
    verify_optimized_maps(boot/'id1/maps', optimization)
    world_heap=audit_world_map_heap_with_receipt(engine_record,boot/'id1/maps',args.sdk,world_heap_path)
    bind_heap_report(optimization, world_heap, world_heap_path, optimization_path)
    heap_watcher=heap_watcher_summary(world_heap,world_heap_path)
    (out/'heap-watcher.json').write_text(json.dumps(heap_watcher,indent=2)+'\n',encoding='utf-8',newline='\n')
    budget_policy_path = out / 'map-budget-policy.json'
    budget_decision = apply_map_budget_policy(world_heap,
        getattr(args, 'map_budget_policy', 'strict'), budget_policy_path)
    heap_watcher['status'] = budget_decision['status']
    heap_watcher['budget_policy'] = budget_decision
    (out/'heap-watcher.json').write_text(json.dumps(heap_watcher,indent=2)+'\n',encoding='utf-8',newline='\n')
    prefix = '[warning: needs adjustment]' if world_heap['failing_maps'] else 'World-map heap estimate passed:'
    print(f"{prefix} {world_heap['passing_maps']}/{world_heap['map_count']} maps clear the modeled allowance; "
          f"minimum clearance {world_heap['minimum_estimated_clearance_bytes']} bytes after unchanged baseline "
          f"and safety reserves. Policy={budget_decision['policy']}; runtime validation pending.",flush=True)
    verify_optimized_maps(boot/'id1/maps', optimization)
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
    from music_catalogue import write_catalogue
    music_catalogue = write_catalogue(target/'soundtrack.json', target/'catalogue.txt')
    (target/'playlist.txt').write_text('\n'.join(' '.join(map(str,[len(groups[g]),*groups[g]])) for g in ['explore','battle'])+'\n'+str(groups['title'])+'\n', newline='\n')
    # Reconcile source inventory with the bytes actually staged for the image.
    from prepare_media_assets import stage_catalogue
    intro_receipt_path = scene/'intro-conversion.json'
    intro_receipt = json.loads(intro_receipt_path.read_text()).get('movie') if intro_receipt_path.is_file() else None
    media_coverage = stage_catalogue(args.media, boot/'id1', manifest, intro_receipt)
    media_coverage_path = out/'media-coverage.json'
    media_coverage_path.write_text(json.dumps(media_coverage,indent=2)+'\n',encoding='utf-8',newline='\n')
    # Missing original inputs remain warnings, but every available source must
    # have a validated converted output before any image packing begins.
    require_complete_media_outputs(media_coverage)
    # Leave filesystem metadata and future saves room; retain legacy-safe sizes.
    verify_heap_loader_source_receipt(engine_record)
    from world_volumes import pack as pack_world_volumes
    world_images=pack_world_volumes(boot/'id1',out,VERSION,args.xdftool,args.rdbtool)
    check_payload_names(boot)
    payload_bytes=sum(p.stat().st_size for p in boot.rglob('*') if p.is_file())
    partition_mib=max(128,((payload_bytes*6//5 + 16*1024*1024 + 127*1024*1024)//(128*1024*1024))*128)
    if partition_mib>=2048:raise ValueError('Boot partition must remain below 2 GiB')
    suffix = '' if actor_acceptance['production_gate_passed'] and budget_decision['production_memory_gate_passed'] else '-private-test'
    part=out/'partition.hdf';hdf=out/f'AmiWind-v{VERSION}{suffix}.hdf'
    cmd=[args.xdftool,part,'create',f'size={partition_mib}Mi','+','format','AMIWIND','ffs','+','boot','install']
    for path in sorted((p for p in boot.rglob('*') if p.is_dir()),key=lambda p:len(p.parts)):
        cmd+=['+','makedir',path.relative_to(boot).as_posix()]
    for path in sorted(p for p in boot.rglob('*') if p.is_file()):cmd+=['+','write',path,path.relative_to(boot).as_posix()]
    if os.name == 'nt':
        from build_windows_xdftool import run as run_xdftool
        run_xdftool(cmd)
    else:
        run(cmd)
    root_check=check_image(part,normalize=True)
    from world_volumes import hardfile_groups, verify_combined
    drive_groups=hardfile_groups(part.stat().st_size,world_images)
    boot_files=[dict(path=p.relative_to(boot).as_posix(),bytes=p.stat().st_size,sha256=digest(p))
                for p in sorted(boot.rglob('*')) if p.is_file()]
    layout=[];drive_receipts=[]
    for index,volumes in enumerate(drive_groups):
        drive=hdf if index==0 else out/f'AmiWind-v{VERSION}{suffix}-world-{index:02d}.hdf'
        total_mib=(partition_mib if index==0 else 0)+sum(v['bytes']//(1024*1024) for v in volumes)
        if total_mib*1024*1024+32768>=4*1024**3:
            raise ValueError('Legacy hardfile must remain below 4 GiB')
        command=[args.rdbtool,drive,'create',f'chs={total_mib*32+1},1,64','+','init']
        partitions=[]
        if index==0:
            command+=['+','addimg',part,'name=DH0','bootable=1','pri=0']
            partitions.append(dict(partition='DH0',volume='AMIWIND',files=boot_files))
        for volume in volumes:
            command+=['+','addimg',out/volume['file'],'name='+volume['partition'],'bootable=0']
            partitions.append(volume)
        run(command)
        checked=verify_combined(drive,partitions)
        for receipt in checked:receipt['hdf_file']=drive.name
        layout.extend(checked)
        drive_receipts.append(dict(file=drive.name,bytes=drive.stat().st_size,sha256=digest(drive),
                                   bootable=index==0,partitions=[p['partition'] for p in checked],readback='passed'))
    for volume in world_images:(out/volume['file']).unlink()
    part.unlink()
    verify_heap_loader_source_receipt(engine_record)
    build_json={
        'version':VERSION,'hands':args.hands,'actor_ground_audit':actor_acceptance,
        'npc_gallery':gallery_report,'world_scenery':world_scenery_acceptance,
        'world_flora':json.loads((out/'world-flora-staging.json').read_text(encoding='utf-8')) if (out/'world-flora-staging.json').is_file() else {'status':'not_requested'},
        'sky_asset_preparation':sky_asset_preparation,
        'guard_torches':guard_torches,
        'hand_metadata':hand_metadata,
        'exterior_sky':{'local_skybox':exterior_sky['local_skybox'],
            'report':str(exterior_sky_path.relative_to(out)),
            'report_sha256':digest(exterior_sky_path),'status':exterior_sky['status'],
            'map_count':len(exterior_sky['maps']),
            'removed_sky_faces':exterior_sky['removed_sky_faces'],
            'unknown_maps_preserved':exterior_sky['unknown_maps_preserved'],
            'shared_resource_source':exterior_sky['shared_resource_source'],
            'shared_resource_sha256':exterior_sky['shared_resource_sha256']},
        'hidden_surface_cull':{'enabled':hidden_surfaces['enabled'],
            'report':str(hidden_surface_path.relative_to(out)),
            'report_sha256':digest(hidden_surface_path),'status':hidden_surfaces['status'],
            'removed_stored_faces':hidden_surfaces['removed_stored_faces'],
            'file_bytes_saved':hidden_surfaces['file_bytes_saved'],
            'acceptance':hidden_surfaces['acceptance']},
        'heap_watcher':heap_watcher,
        'world_map_optimization':{
            'report':optimization_path.name,'report_sha256':digest(optimization_path),
            'map_count':optimization['map_count'],'file_bytes_saved':optimization['file_bytes_saved'],
            'acceptance':optimization['acceptance']},
        'world_map_heap':{
            'status':budget_decision['status'],'budget_policy':budget_decision['policy'],
            'policy_receipt':budget_policy_path.name,'policy_receipt_sha256':digest(budget_policy_path),
            'production_memory_gate_passed':budget_decision['production_memory_gate_passed'],
            'runtime_validation':'pending','report':world_heap_path.name,
            'report_sha256':digest(world_heap_path),'map_count':world_heap['map_count'],
            'minimum_estimated_clearance_bytes':world_heap['minimum_estimated_clearance_bytes'],
            'baseline_reserve_bytes':world_heap['baseline_reserve_bytes'],
            'safety_headroom_bytes':world_heap['safety_headroom_bytes'],
            'loader_source_sha256':heap_loader_source_sha256,
            'acceptance':world_heap['acceptance']},
        'torch':torch_report,'hdf_file':hdf.name,'hdf_files':drive_receipts,
        'default_start':{'profile':'logo-fade-then-main-menu','movie':'intro/amiwind.awv',
            'music_track':groups['title'],'new_game_map':'prison',
            'new_game_movie':'intro/mw_intro.awv' if movie.exists() else None,
            'new_game_music_track':4,
            'new_game_music_source':opening_track['source'] if opening_track else None},
        'hdf_bytes':hdf.stat().st_size,'hdf_sha256':digest(hdf),
        'binary_sha256':digest(boot/'AmiWind'),'bootcheck_sha256':digest(checker),
        'payload_bytes':sum(p['payload_bytes'] for p in layout),'partitions':layout,
        'media_coverage':{'report':media_coverage_path.name,'sha256':digest(media_coverage_path),
            'categories':media_coverage['categories'],'payload_readback':'passed'},
        'music_tracks':len(manifest['tracks']),'music_catalogue':music_catalogue,'heap_reservation_bytes':world_heap['heap_budget_bytes'],
        'tested_minimum':False,'filesystem':'DOS1 FFS partitions in legacy-safe RDB HDF drives',
        'legacy_root_check':root_check}
    (out/'build.json').write_text(json.dumps(build_json,indent=2)+'\n', newline='\n')
    from emulator_configs import write_configs
    configs = write_configs(hdf, getattr(args, 'kickstart_file', None))
    build_record = json.loads((out/'build.json').read_text(encoding='utf-8'))
    build_record['emulator_configs'] = configs
    (out/'build.json').write_text(json.dumps(build_record,indent=2)+'\n',encoding='utf-8',newline='\n')
    if not actor_acceptance['production_gate_passed']:
        print('PRIVATE TEST image assembled. Production actor gate DID NOT PASS; see actor-ground-acceptance.json.', flush=True)
    from emulator_configs import print_outputs
    print_outputs(hdf)

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    e=sub.add_parser('engine');e.add_argument('--cpu',choices=['68020','68040'],default='68040');e.add_argument('--archive',type=Path,help='Optional legacy provenance check; source is always engine/aga in this repository');e.add_argument('--out',type=Path,required=True);e.add_argument('--sdk',type=Path,required=True);e.add_argument('--vasm',type=Path,help='68000 preflight assembler; defaults to the SDK vasm')
    add_jobs(e)
    i=sub.add_parser('image')
    from hidden_surface_build import add_options as add_hidden_surface_options
    add_hidden_surface_options(i)
    from exterior_sky_build import add_options as add_exterior_sky_options
    add_exterior_sky_options(i)
    i.add_argument('--kickstart-file',type=Path,help='Optional owned ROM for generated local emulator configurations; never bundled or downloaded')
    i.add_argument('--sdk',type=Path,required=True,help='AmigaPorts SDK used to compile the exact target ABI heap profile')
    i.add_argument('--map-budget-policy', choices=['strict', 'warning'], default='strict', help='Explicit private warning policy for modeled reserve allowance only; runtime allocation ceiling and all other gates stay unchanged')
    i.add_argument('--allow-known-actor-ground-findings', type=Path, help='PRIVATE TEST ONLY: accept an exact previously reviewed contact audit; strict production gate remains failed')
    i.add_argument('--data-files',type=Path,required=True,help='Owned original game assets')
    gallery_choice=i.add_mutually_exclusive_group(required=True)
    gallery_choice.add_argument('--gallery',type=Path,help='Verified NPC gallery from build_gallery.py; normal default')
    gallery_choice.add_argument('--no-npc-gallery',action='store_true',help='DEBUGGING ONLY: omit inspection gallery, never required game NPCs')
    i.add_argument('--intro-captions',type=Path,help='Private JSON title cards; first card becomes a switchable opening overlay')
    i.add_argument('--world-terrain',type=Path,help='Complete validated refined terrain receipt and runtime directory, staged before scenery')
    i.add_argument('--world-scenery',type=Path,required=True,help='Complete validated full-world rock and giant-mushroom overlay directory')
    i.add_argument('--world-flora',type=Path,help='Complete validated private world vegetation overlay; preserves rock/mushroom inputs')
    i.add_argument('--town-flora-source-index',type=Path,help='Exact original Seyda scenery reference bindings for flora installation')
    i.add_argument('--town-flora-scene-report',type=Path,help='Original alias conversion model mapping; required with --world-flora')
    i.add_argument('--balmora-cache',type=Path,help='Complete owned Balmora preparation cache for measured layout repair before final actor/heap audits')
    i.add_argument('--bootcheck',type=Path,help='Defaults to AmiWindCheck beside the engine binary')
    for name in ['scene','music','media','engine','out','qcc','qbsp','vis','light','xdftool','rdbtool']:i.add_argument('--'+name,type=Path,required=True)
    for parser in (e,i):parser.add_argument('--hands',choices=['3d','sprites'],default='3d',help='Compile-time first-person renderer; retain both conversion paths')
    args=p.parse_args()
    # Resolve executables before subprocess cwd changes.
    for name in ['qcc','qbsp','vis','light','xdftool','rdbtool','engine','bootcheck']:
        if getattr(args,name,None) is not None:setattr(args,name,getattr(args,name).resolve())
    try:(engine if args.action=='engine' else image)(args)
    except (OSError,ValueError,subprocess.CalledProcessError) as exc:p.exit(1,f'Error: {exc}\n')
if __name__=='__main__':main()
