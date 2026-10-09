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
import check_fpu_unimplemented
from amiga_fs import check_image, check_payload_names, check_payload_host_paths
from project_version import VERSION, check_native_versions, require_private_test_version
from build_jobs import add_jobs, resolve_jobs
from build_host import executable_path, make_python_assignment
from vis_options import add_vis_option
import fpu_support
import known_inputs
from fpu_support import LOADER as FPU_LOADER

ROOT=Path(__file__).resolve().parents[1]
UPSTREAM_COMMIT='9c62d905151614af3e788ae3145a0d4ecc8a7bb8'
UPSTREAM_SHA256='43353034beb2a43b1af82c735f93c0a8bee8129c1b93d7ba152dd8e60ad3721c'
RUNTIME_SOURCE=ROOT/'engine/aga'
HEAP_LOADER_SOURCE_PATHS = (
    'Makefile',
    'src/model.c', 'src/model_alias_stream.inc', 'src/model.h', 'src/zone.c', 'src/zone.h',
    'src/r_draw.c', 'src/asm_draw.h',
    'src/common.c', 'src/sys_amiga.c',
    'src/aw_guard_torch.c', 'src/aw_torch.c',
    'src/aw_harvest.c', 'src/aw_harvest.h', 'src/aw_harvest_runtime.c', 'src/aw_harvest_runtime.h',
    'src/aw_harvest_proxy.c', 'src/aw_harvest_proxy.h',
    'src/aw_section.c', 'src/aw_section.h', 'src/aw_maps.h', 'src/aw_region.c',
    'src/aw_town.h', 'src/aw_town_table.h',
    'src/aw_scenery.c', 'src/pr_edict.c', 'src/aw_scene.c', 'src/aw_spawn.c', 'src/aw_console.c',
    'src/render.h', 'src/r_sprite.c', 'src/r_efrag.c', 'src/r_main.c',
    'src/cl_parse.c', 'src/cl_main.c', 'src/client.h', 'src/pr_cmds.c', 'src/protocol.h', 'qc/world.qc',
    'src/quakedef.h', 'src/server.h', 'src/net.h', 'src/host.c', 'src/net_main.c', 'src/net_loop.c',
)
RUNTIME_BUILD_DIR='runtime'
# The engine compiles warning-free; the build fails on any compiler warning
# (see build_engine). Do not add -Wno-* flags to hide new ones.
CC_FLAGS=' -std=gnu89'

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def run(args,cwd=None,env=None,capture=False):
    if not capture:
        subprocess.run(list(map(str,args)),cwd=cwd,env=env,check=True);return None
    # Echo the combined output and return it for inspection (compiler warnings).
    result=subprocess.run(list(map(str,args)),cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                          text=True,errors='replace')
    print(result.stdout,end='',flush=True)
    if result.returncode:raise subprocess.CalledProcessError(result.returncode,str(args[0]))
    return result.stdout
def heap_watcher_summary(report, report_path):
    """Expose estimated use and spare capacity; never invent target measurements."""
    budget = report['heap_budget_bytes']
    baseline = report['baseline_reserve_bytes']
    safety = report['safety_headroom_bytes']
    worst = next(row for row in report['maps'] if row['map'] == report['worst_map'])
    peak = worst['peak_loader_bytes']
    static = worst.get('additional_static_allowance_bytes',0)
    external = worst.get('additional_external_allocation_allowance_bytes',0)
    committed = peak + baseline + safety + static + external
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
        'additional_static_allowance_bytes': static,
        'additional_external_allocation_allowance_bytes': external,
        'estimated_committed_with_reserves_bytes': committed,
        'estimated_growth_margin_after_reserves_bytes': budget - committed,
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

HEAP_BYPASS = ROOT/'config/heap-bypass.json'
BYPASS_STATUS = 'temporary pre-CHIM bypass'


def load_heap_bypass(path=HEAP_BYPASS):
    """{map file name: entry} of the temporary pre-CHIM heap bypass (repository file only)."""
    path = Path(path)
    if not path.is_file():
        return {}
    record = json.loads(path.read_text(encoding='utf-8'))
    if record.get('format') != 'AmiWind heap bypass 1':
        raise ValueError('Unknown heap bypass file: ' + str(path))
    entries = {}
    for row in record['temporary_pre_chim_heap_bypass']:
        if (not re.fullmatch(r'[a-z0-9_]+\.bsp', row.get('map', '')) or row['map'] in entries or
                not re.fullmatch(r'[0-9a-f]{64}', row.get('sha256', '')) or row.get('builder') != 'legacy' or
                not row.get('until') or not row.get('bug') or not row.get('decision')):
            raise ValueError('Invalid heap bypass entry: ' + str(row.get('map')))
        entries[row['map']] = row
    return entries


def heap_bypass(failures, hard_failures, maps_dir, entries, builder='legacy'):
    """(bypassed rows, refused rows) for allowance-only failures of listed maps.

    A listed map is bypassed only with the legacy builder, its exact recorded
    bytes (SHA-256) and no allocation-ceiling failure. Everything else stays a
    failure; refusals are recorded with their reason."""
    bypassed, refused = [], []
    for name in failures:
        entry = entries.get(name)
        if entry is None:
            continue
        row = {'map': name, 'sha256': entry['sha256'], 'until': entry['until'], 'bug': entry['bug']}
        actual = digest(Path(maps_dir)/name) if maps_dir is not None and (Path(maps_dir)/name).is_file() else None
        if builder != entry['builder']:
            refused.append({**row, 'reason': 'built by builder %s; the bypass ends with %s' % (builder, entry['until'])})
        elif name in hard_failures:
            refused.append({**row, 'reason': 'allocation ceiling failure; never bypassed'})
        elif actual != entry['sha256']:
            refused.append({**row, 'actual_sha256': actual, 'reason': 'map bytes differ from the listed recorded map'})
        else:
            bypassed.append({**row, 'status': BYPASS_STATUS, 'decision': entry['decision']})
    return bypassed, refused


def apply_map_budget_policy(report, policy='strict', receipt_path=None, maps_dir=None, bypass=None, builder='legacy'):
    """Opt in to modeled reserve warnings; never waive loader/allocation errors.

    The temporary pre-CHIM heap bypass (config/heap-bypass.json, owner
    decision, HEAP-SEYDA-OVERLAP-32) accepts allowance-only failures of the
    listed recorded maps with their exact bytes (maps_dir), legacy builder only;
    it is recorded and the production gate says so."""
    if policy not in ('strict', 'warning'):
        raise ValueError('Map budget policy must be strict or warning')
    ceiling = report['heap_budget_bytes']
    if ceiling <= 0 or report['baseline_reserve_bytes'] <= 0 or report['safety_headroom_bytes'] <= 0:
        raise ValueError('Invalid heap ceiling or reserve data')
    hard_failures = [row['map'] for row in report['maps'] if row['peak_loader_bytes'] >= ceiling]
    bypassed, refused = heap_bypass(list(report['failing_maps']), hard_failures, maps_dir,
                                    load_heap_bypass() if bypass is None else bypass, builder)
    clearance = {row['map']: row.get('estimated_clearance_bytes') for row in report['maps']}
    for row in bypassed:
        row['estimated_clearance_bytes'] = clearance.get(row['map'])
    failures = [name for name in report['failing_maps'] if name not in {row['map'] for row in bypassed}]
    status = ('estimate_allocation_ceiling_failed' if hard_failures else
              'estimate_warning_needs_adjustment' if failures and policy == 'warning' else
              'estimate_failed' if failures else
              'estimate_passed_with_temporary_pre_chim_bypass' if bypassed else 'estimate_passed')
    passed = not failures and not hard_failures
    decision = {'policy': policy, 'status': status,
                'modeled_allowance_passed': not failures and not bypassed,
                'private_assembly_allowed': not hard_failures and (not failures or policy == 'warning'),
                'production_memory_gate_passed': passed,
                'production_memory_gate': ('failed' if not passed else
                    'passed with %s: %s' % (BYPASS_STATUS, ', '.join(row['map'] for row in bypassed)) if bypassed
                    else 'passed'),
                'temporary_pre_chim_bypass': bypassed, 'bypass_refused': refused, 'builder': builder,
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

def combat_summary(report):
    """build.json's short record of the combat data (docs/COMBAT.md)."""
    if not report:
        return {'status': 'not_built'}
    return {'status': 'built', 'actors': report['actors'], 'sounds': sorted(report['sounds']),
            'fighters': {k: {'model': v['model'], 'bytes': v['bytes'], 'frames': v['frames']}
                         for k, v in report.get('fighters', {}).items()}}


def stage_debug_catalogues(id1, debug_luma=False):
    """Required on-disk metadata: fail the build instead of shipping broken dbg."""
    files = [('debug-commands.txt', b'AWDC1'), ('shroompicker.txt', b'AWSP1')]
    payloads = []
    for name, magic in files:
        raw = (ROOT/'config'/name).read_bytes()
        if not raw or len(raw) > (65536 if name == 'debug-commands.txt' else 4096):
            raise ValueError(f'Invalid debug catalogue size: {name}')
        if raw.splitlines()[0] != magic:
            raise ValueError(f'Invalid debug catalogue header: {name}')
        payloads.append((name, raw))
    for name, raw in payloads:
        (Path(id1)/name).write_bytes(raw)
    return {name: {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
            for name, raw in payloads}


LIVE_LOGS_LINE = b'aw_logs_live 1\n'


def stage_game_config(id1, debug_luma=False, live_logs=False):
    """Keep disabled compile-time controls out of the production startup file.

    live_logs (builder --live-logs, benchmark and diagnostic images): the engine writes its
    diagnostic logs as they happen (walk-profile.csv, frame-stalls.csv, heap-audit.log, ...),
    as every build did before BOOT-VOLUME-NOT-VALIDATED-33. Default: the logs stay in memory and
    are written at Exit game or with dbg savelogs."""
    raw = (ROOT/'config/game.cfg').read_bytes()
    if not debug_luma:
        raw = b''.join(line for line in raw.splitlines(keepends=True)
                       if not line.strip().startswith((b'aw_interiorluma ',b'aw_exteriorluma ')))
    raw = b''.join(line for line in raw.splitlines(keepends=True) if not line.strip().startswith(b'aw_logs_live '))
    if live_logs:
        if raw and not raw.endswith(b'\n'):
            raw += b'\n'
        raw += b'// Benchmark/diagnostic image (--live-logs): diagnostic logs written as they happen.\n' + LIVE_LOGS_LINE
    (Path(id1)/'default-game.cfg').write_bytes(raw)
    return {'diagnostic_logs': 'live' if live_logs else 'memory'}


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

def audit_world_map_heap_with_receipt(engine_record, maps, sdk, out, source=None, jobs=1):
    """Run the map estimate only when it matches the engine's loader sources."""
    loader_hashes = verify_heap_loader_source_receipt(engine_record, source)
    from check_world_map_heap import audit_world_maps
    # The gate measures against the heap this engine was built with (engine-build.json heap_mb), not the
    # source default; receipts older than --heap-mb have none and were built with the default.
    report = audit_world_maps(maps, sdk, out, jobs=jobs, heap_mb=engine_record.get('heap_mb'))
    report['loader_source_sha256'] = loader_hashes
    out = Path(out)
    text = json.dumps(report, indent=2) + '\n'
    out.write_text(text, encoding='utf-8', newline='\n')
    # Return exactly what the receipt holds (tuples become lists), so later gates bind to the saved file
    # (BUILD-HEAP-RECEIPT-TUPLES-32: dev2's image failed after 20 min on a tuple in the harvest profile).
    return json.loads(text)

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
    shutil.copyfile(ROOT/'CHIM_VERSION', tree/'CHIM_VERSION')
    (tree/'tools').mkdir(exist_ok=True)
    shutil.copyfile(ROOT/'tools/project_version.py', tree/'tools/project_version.py')
    return tree,hashes

def world_coverage_build(record, kind):
    """Bind evidence to the completed build receipt, excluding this footer.

    Adapters use the same canonical identity before supplying --world-coverage.
    Repeated footer generation cannot alter the build identity it describes.
    """
    from world_asset_coverage import digest as coverage_digest
    if kind not in ('engine','image'):
        raise ValueError('Unknown world coverage build kind')
    binding={key:value for key,value in record.items() if key!='world_coverage'}
    return dict(id='sha256:'+coverage_digest(dict(kind=kind,receipt=binding)),
                kind=kind,version=record['version'])


def write_world_coverage(out, kind, evidence_path=None):
    """Always save and print coverage; absent evidence means unknown."""
    from world_asset_coverage import report,terminal
    out=Path(out)
    receipt_path=out/('engine-build.json' if kind=='engine' else 'build.json')
    record=json.loads(receipt_path.read_text(encoding='utf-8'))
    build=world_coverage_build(record,kind)
    evidence_raw=Path(evidence_path).read_bytes() if evidence_path is not None else None
    evidence=json.loads(evidence_raw) if evidence_raw is not None else None
    result=report(evidence,build=build)
    report_path=out/'world-coverage.json'
    if evidence_path is not None and Path(evidence_path).resolve()==report_path.resolve():
        raise ValueError('Coverage input must differ from generated report')
    report_path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    record['world_coverage']=dict(report=report_path.name,sha256=digest(report_path),
        status=result['status'],build=build,
        evidence_sha256=hashlib.sha256(evidence_raw).hexdigest() if evidence_raw is not None else None)
    receipt_path.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(terminal(result),end='',flush=True)
    return result


def check_town_table():
    """The engine's town table must be generated from the current configs."""
    from town_table import check
    if not check():
        raise ValueError('engine/aga/src/aw_town_table.h differs from config/towns.json and the town configs; '
                         'run tools/town_table.py --write')


def check_engine_fpu(binary,map_path,sdk,out):
    """ENGINE-FPU-UNIMPL-31: fail when engine code can reach a 68040-unimplemented
    FPU instruction outside tools/fpu-unimplemented-allowlist.json; the full
    result goes to out/fpu-unimplemented.json, a summary into engine-build.json."""
    objdump=executable_path(Path(sdk).resolve()/'bin/m68k-amigaos-objdump')
    disassembly=subprocess.run([str(objdump),'-d','-r','-m','m68k:68040',str(binary)],check=True,capture_output=True,text=True).stdout
    result=check_fpu_unimplemented.check(disassembly,Path(map_path).read_text(encoding='utf-8',errors='replace'),
        json.loads(check_fpu_unimplemented.ALLOWLIST.read_text(encoding='utf-8')))
    (out/'fpu-unimplemented.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    if not result['passed']:
        raise SystemExit('Engine code reaches 68040-unimplemented FPU instructions: '+'; '.join(
            ' -> '.join(row['path']) for row in result['engine_failures'][:10])+' (see fpu-unimplemented.json)')
    return {'passed':True,'unimplemented_instructions_in_binary':result['unimplemented_instructions'],
            'library_functions':sorted(result['functions_with_unimplemented']),'allowlist_unused':result['allowlist_unused']}


def fpu_loader_path(engine_binary):
    return Path(engine_binary).parent/FPU_LOADER


def stage_fpu_support(args, engine_record, boot):
    """--amiga-libs: the user's own 68040/68060.library into LIBS: plus AmiWindFPU.

    ENGINE-FPSP-MISSING-31. Without the option or a library the build continues;
    the receipt and the build report say "no FPU support library"."""
    directory=getattr(args,'amiga_libs',None)
    loader=None
    if directory is not None and fpu_support.find(directory):
        loader=fpu_loader_path(args.engine)
        if not loader.is_file() or engine_record.get('fpu_loader_sha256')!=digest(loader):
            raise ValueError('AmiWindFPU does not match the engine build receipt; rebuild the engine')
        check_binary(loader.read_bytes())
    receipt=fpu_support.stage(directory,boot,loader,policy=getattr(args,'amiga_libs_policy',None) or 'warn')
    for line in fpu_support.summary_lines(receipt):print(line,flush=True)
    return receipt


def engine(args):
    check_native_versions()
    check_town_table()
    # Optional legacy input only verifies provenance; it never replaces repo source.
    if args.archive and digest(args.archive)!=UPSTREAM_SHA256:raise ValueError('Upstream archive checksum mismatch')
    out=new_output(args.out)
    tree,source_hashes=stage_runtime(out)
    env=os.environ.copy();env['PATH']=str(args.sdk.resolve()/'bin')+os.pathsep+env.get('PATH','')
    jobs=resolve_jobs(args.jobs)
    debug_luma=bool(getattr(args,'debug_luma',True))
    print(f'Native compiler jobs: {jobs}',flush=True)
    # The game heap: exactly what --heap-mb asked (like --jobs), else the engine source's default; above
    # the measured safe size one loud warning, recorded, and the build goes on (never refused).
    from project_version import heap_plan
    heap=heap_plan(getattr(args,'heap_mb',None))
    heap['selected_by']='--heap-mb' if getattr(args,'heap_mb',None) is not None else 'engine default'
    if heap['heap_warning']:
        print('='*72+'\nWARNING: '+heap['heap_warning']+'\n'+'='*72,flush=True)
    output=run(['make','-B','--output-sync=target',f'-j{jobs}',('nofpu' if args.cpu=='68020' else 'fpu'),make_python_assignment(),
                *([f'HEAP_MB={heap["heap_mb"]}'] if getattr(args,'heap_mb',None) is not None else []),'CC=m68k-amigaos-gcc'+CC_FLAGS+' -DAMIWIND_SPRITE_HANDS='+('1' if args.hands=='sprites' else '0')+(' -DAMIWIND_DEBUG_LUMA=1' if debug_luma else ''),'NDK_INC='+str(args.sdk.resolve()/'m68k-amigaos/ndk-include')],tree,env,capture=True)
    warnings=[line for line in str(output or '').splitlines() if ': warning: ' in line]
    if warnings and not getattr(args,'allow_compiler_warnings',False):
        raise SystemExit(f'Engine build produced {len(warnings)} compiler warning(s); it must be warning-free. '
                         'Fix them, or pass --allow-compiler-warnings for a local experiment only.')
    binary=tree/('build/AmiQuakeGCC-NoFPU' if args.cpu=='68020' else 'build/AmiQuakeGCC')
    check_binary(binary.read_bytes())
    fpu_check=check_engine_fpu(binary,tree/'build/AmiQuakeGCC.map',args.sdk,out) if args.cpu=='68040' else None
    # Asset-free hardware benchmark for owners (engine/aga/bench, docs/HARDWARE-BENCHMARK.md).
    bench_output=run(['make','-B','bench','CC=m68k-amigaos-gcc'+CC_FLAGS,'NDK_INC='+str(args.sdk.resolve()/'m68k-amigaos/ndk-include')],tree,env,capture=True)
    bench_warnings=[line for line in str(bench_output or '').splitlines() if ': warning: ' in line]
    if bench_warnings and not getattr(args,'allow_compiler_warnings',False):
        raise SystemExit(f'Benchmark build produced {len(bench_warnings)} compiler warning(s); it must be warning-free.')
    bench=tree/'build/awbench'
    check_binary(bench.read_bytes())
    shutil.copyfile(bench,out/'awbench')
    checker=tree/'build/AmiWindCheck'
    vasm=executable_path(args.vasm.resolve() if args.vasm else args.sdk.resolve()/'bin/vasmm68k_mot')
    ndk=args.sdk.resolve()/'m68k-amigaos/ndk-include'
    run([vasm,'-m68000','-Fhunkexe','-kick1hunks','-nosym','-I',ndk,'-I',tree/'build/version','-I',tree/'boot','-o',checker,tree/'boot/bootcheck.asm'])
    check_binary(checker.read_bytes())
    # AmiWindFPU opens the user's own FPU support library at boot (--amiga-libs).
    loader=tree/'build'/FPU_LOADER
    run([vasm,'-m68000','-Fhunkexe','-kick1hunks','-nosym','-I',ndk,'-I',tree/'boot','-o',loader,tree/'boot/fpulib.asm'])
    check_binary(loader.read_bytes())
    (out/'engine-build.json').write_text(json.dumps({'version':VERSION,'hands':args.hands,'debug_luma':debug_luma,'compiler_jobs':jobs,'source_kind':'repository engine/aga','source_sha256':source_hashes,'upstream_commit':UPSTREAM_COMMIT,'baseline_upstream_archive_sha256':UPSTREAM_SHA256,'binary':str(binary),'binary_sha256':digest(binary),'bootcheck_sha256':digest(checker),'fpu_loader_sha256':digest(loader),'hardware_benchmark_sha256':digest(out/'awbench'),'fpu_unimplemented_check':fpu_check,
        'heap_mb':heap['heap_mb'],'heap_mb_selected_by':heap['selected_by'],'heap_default_mb':heap['heap_default_mb'],
        'heap_safe_mb':heap['heap_safe_mb'],'heap_warning':heap['heap_warning']},indent=2)+'\n', newline='\n')
    print(binary)
    write_world_coverage(out,'engine',getattr(args,'world_coverage',None))

def install_world_scenery(overlay, id1, jobs=1):
    """Validate a complete full-world overlay, then replace its terrain BSPs.

    Hashing and the final copies run in up to `jobs` workers (shared pool)."""
    from build_parallel import copy_files, hash_existing
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
    retained = hash_existing([id1 / 'maps' / f'{name}.bsp' for name in expected_names], jobs)
    overlays = hash_existing([overlay / name / 'scene.bsp' for name in expected_names], jobs)
    for region, source_sha, baked_sha in zip(regions, retained, overlays):
        name = region['name']
        if not re.fullmatch(r'vf\d{4}', name):
            raise ValueError('Invalid world scenery region name')
        source = id1 / 'maps' / f'{name}.bsp'
        if source_sha is None or source_sha != region.get('original_terrain_sha256'):
            raise ValueError('World scenery overlay does not match retained terrain: ' + name)
        baked = overlay / name / 'scene.bsp'
        if baked_sha is None or baked_sha != region.get('sha256'):
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
    copy_files(replacements, jobs)
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

def retire_chim_special_catalogues(id1):
    """Harvest catalogues of special maps that run on CHIM in this image (maps/<name>-chim.bsp present,
    maps/<name>.bsp absent, <name> not a region of a CHIM town): the engine names a map's catalogue after
    the loaded map (harvest-<map>.txt), so the legacy catalogue would never load; it is left out of the
    image and the save fingerprint, and listed (CHIM-HARVEST-SPECIALS-33)."""
    root=Path(id1);regions=set()
    for table in sorted(root.glob('*-regions.txt')):
        regions.update(line.split()[0] for line in table.read_text(encoding='ascii').splitlines()[1:] if line.split())
    retired=[]
    for path in sorted(root.glob('harvest-*.txt')):
        name=path.name[len('harvest-'):-len('.txt')]
        if ((root/'maps'/(name+'-chim.bsp')).is_file() and not (root/'maps'/(name+'.bsp')).is_file()
                and name not in regions):
            path.unlink();retired.append(path.name)
    return retired

def harvest_fingerprint_entries(id1, *, plant_capacity=None, removed=()):
    """Bind optional pickup contents to saves, preserving the legacy namespace.

    removed: legacy town maps a pure CHIM image left out (id1-relative 'maps/x.bsp'). Their regions
    stay in the town's region table and the engine keeps their harvest catalogues per region on the
    CHIM frame map (CHIM-HARVEST-REMOVED-MAPS-33).

    Check the bounded catalogue envelope here; the native parser and original
    source/placement admission still own semantic validation. Hash every byte.
    """
    root=Path(id1);result=[];catalogue_kind=None;global_index=None;model_files={}
    if plant_capacity is None:
        source=(RUNTIME_SOURCE/'src/aw_harvest.h').read_text(encoding='utf-8')
        bound=re.search(r'^\s*#define\s+AW_HARVEST_PLANTS\s+(\d+)\s*$',source,re.M)
        if not bound:raise ValueError('Cannot identify runtime harvest placement bound')
        plant_capacity=int(bound[1])
    if type(plant_capacity) is not int or not 1<=plant_capacity<=4096:
        raise ValueError('Invalid runtime harvest placement bound')
    # Regions of towns that run on CHIM (maps/<town>-chim.bsp present): their region maps are gone from a
    # pure CHIM image, their catalogues stay and the engine loads them per region (CHIM-HARVEST-REMOVED-MAPS-33).
    chim_regions=set()
    for table in sorted(root.glob('*-regions.txt')):
        town=table.name[:-len('-regions.txt')]
        if (root/'maps'/(town+'-chim.bsp')).is_file():
            chim_regions.update(line.split()[0] for line in table.read_text(encoding='ascii').splitlines()[1:] if line.split())
    for path in sorted(root.glob('harvest-*.txt'),key=lambda item:item.name):
        match=re.fullmatch(r'harvest-([a-z0-9_]{1,24})\.txt',path.name)
        if not match or path.is_symlink() or not path.is_file():
            raise ValueError('Invalid harvest catalogue path: '+path.name)
        if (not (root/'maps'/(match[1]+'.bsp')).is_file() and 'maps/'+match[1]+'.bsp' not in removed
                and match[1] not in chim_regions):
            if (root/'maps'/(match[1]+'-chim.bsp')).is_file():
                # A special map on CHIM: the engine never loads this catalogue; every caller skips it and the
                # save fingerprint step leaves it out of the image (CHIM-HARVEST-SPECIALS-33).
                continue
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
        if (external and not 1<=models<=8) or any(n>limit for n,limit in zip(counts,(64,256,plant_capacity))) or len(lines)!=1+sum(counts)+models:
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


def staged_extra_towns(id1):
    """Towns after Seyda and Balmora (config/towns.json) whose directory is staged."""
    from town_config import FIXED_TOWNS, runtime_towns
    return [town for town in runtime_towns()[len(FIXED_TOWNS):] if (Path(id1)/town['regions']).is_file()]


def write_content_fingerprint(id1, jobs=1, partial=False, removed=(), excluded=()):
    """Hash every bound asset (up to `jobs` hashing workers); fold in fixed order.

    partial: a MiniWind partial-area image (tools/miniwind.py) binds the maps it
    ships; the Seyda Neen maps and region table it leaves out are not required.
    True or 'full' is the full MiniWind scope; 'exterior' leaves the Balmora
    interiors out as well.
    removed: legacy town maps a pure CHIM image left out (id1-relative 'maps/x.bsp'); they are not
    required, and the CHIM frame maps (maps/*-chim.bsp) are bound instead.
    excluded: quick-test groups; with 'interiors' the room maps the build left out
    (every interior except the prison ship and the Census office) are not required."""
    from build_parallel import hash_files
    fingerprint=hashlib.sha256()
    from area_config import SCENES
    seyda=Path(id1)/'seyda-regions.txt'
    town_maps=(town_region_map_names(seyda,'sn') if seyda.is_file() or not partial else [])+town_region_map_names(Path(id1)/'balmora-regions.txt','bm')
    scenes=[s for s in SCENES if not ('interiors' in excluded and s.get('interior') is True
            and s['map'] not in ('prison','census') and not (Path(id1)/'maps'/(s['map']+'.bsp')).is_file())]
    names=[*(f"maps/{s['map']}.bsp" for s in scenes), 'maps/intro_docks.bsp', 'maps/sncourt.bsp', 'seyda-regions.txt', 'balmora-regions.txt', *town_maps, 'progs.dat', 'character/catalog.awc', 'world/map.awm', 'world/journal.awj', 'world/entries.dat', 'world/quests.awq', 'world/region-names.awn']
    if partial:
        import miniwind
        kept,prefix=miniwind.kept_maps(scope=miniwind.DEFAULT_SCOPE if partial is True else partial)
        names=[name for name in names if name!='seyda-regions.txt' and
               not (name.startswith('maps/') and not miniwind.keep_map(name[5:-4],kept,prefix))]
    # Optional extra towns follow, so images without them keep their fingerprint.
    for town in staged_extra_towns(id1):
        names+=[town['regions'],'maps/'+town['name']+'.bsp',*town_region_map_names(Path(id1)/town['regions'],town['prefix'])]
    names+=['maps/'+name+'.bsp' for name in staged_town_interiors(id1)]
    if removed:
        removed=set(removed)
        names=[name for name in names if name not in removed]
        names+=sorted('maps/'+p.name for p in (Path(id1)/'maps').glob('*-chim.bsp'))
    for name in names:
        if not (Path(id1)/name).is_file():raise ValueError('Required character-creation asset missing: '+name)
    for name,value in zip(names,hash_files([Path(id1)/name for name in names],jobs)):
        fingerprint.update(name.encode('ascii')+b'\0'+bytes.fromhex(value))
    directory=Path(id1)/'world/regions.awr'
    if directory.is_file():
        fingerprint.update(b'world/regions.awr\0'+bytes.fromhex(digest(directory)))
        raw=directory.read_bytes()
        if raw[:4]!=b'AWR2' or len(raw)!=64+struct.unpack_from('<I',raw,4)[0]*52:
            raise ValueError('Invalid world region directory')
        world=[f'maps/vf{index:04d}.bsp' for index in range(struct.unpack_from('<I',raw,4)[0])]
        for name,value in zip(world,hash_files([Path(id1)/name for name in world],jobs)):
            fingerprint.update(name.encode('ascii')+b'\0'+bytes.fromhex(value))
    from prepare_guard_torches import fingerprint_entries
    def optional_asset(name):
        path=Path(id1)/name
        return path.read_bytes() if path.is_file() else None
    for name,hash_value in fingerprint_entries(optional_asset):
        fingerprint.update(name.encode('ascii')+b'\0'+bytes.fromhex(hash_value))
    from night_lighting import TABLES as night_lighting_tables
    for name in night_lighting_tables:  # absent from stages built before the tables
        if (Path(id1)/name).is_file():
            fingerprint.update(name.encode('ascii')+b'\0'+bytes.fromhex(digest(Path(id1)/name)))
    retired=retire_chim_special_catalogues(id1)
    if retired:
        print('Harvest catalogues of special maps on CHIM left out (no CHIM catalogue yet, CHIM-HARVEST-SPECIALS-33): '
              +', '.join(retired),flush=True)
    for name,hash_value in harvest_fingerprint_entries(id1,removed=set(removed or ())):
        fingerprint.update(name.encode('ascii')+b'\0'+bytes.fromhex(hash_value))
    from interior_sections import fingerprint_entries as section_fingerprint_entries
    for name,hash_value in section_fingerprint_entries(id1):
        fingerprint.update(name.encode('ascii')+b'\0'+bytes.fromhex(hash_value))
    (Path(id1)/'save-content.bin').write_bytes(fingerprint.digest())


def image_jobs(args):
    """The image step's worker count: an explicit --jobs N exactly, otherwise the
    scheduled stage budget (AMIWIND_BUILD_JOBS) or auto. Every per-map pass gets
    it explicitly; converters called with their default see it through the
    inherited budget. Steps run one after another, so N workers is the total."""
    jobs = resolve_jobs(getattr(args, 'jobs', None))
    os.environ['AMIWIND_BUILD_JOBS'] = str(jobs)
    return jobs


def image_waivers(args):
    """Waiver options in use for this image (private tests only)."""
    return [name for name, used in (
        ('--allow-known-actor-ground-findings', getattr(args, 'allow_known_actor_ground_findings', None)),
        ('--accept-known-stair-findings', getattr(args, 'accept_known_stair_findings', None)),
        ('--map-budget-policy warning', getattr(args, 'map_budget_policy', 'strict') == 'warning'),
        ('--exclude ' + ','.join(excluded_groups(args)), bool(excluded_groups(args)))) if used]


def excluded_groups(args):
    """Quick test build: the content groups this image leaves out (tools/build_exclusions.py)."""
    from build_exclusions import parse
    return parse([args.exclude] if getattr(args, 'exclude', None) else [])


def stage_excluded_content(boot, groups):
    """The quick-test markers: id1/excluded-content.txt (read by the engine,
    aw_excluded.c) and QUICK-TEST-BUILD.txt at the boot volume's root. A complete
    image carries neither (a stale one from the scene is removed)."""
    import build_exclusions
    marker = Path(boot)/'id1'/build_exclusions.MARKER
    root = Path(boot)/build_exclusions.ROOT_MARKER
    if not groups:
        marker.unlink(missing_ok=True)
        root.unlink(missing_ok=True)
        return build_exclusions.record([])
    marker.write_text(build_exclusions.marker_text(groups), encoding='ascii', newline='\n')
    lines = ['AmiWind v' + VERSION + ': ' + build_exclusions.summary(groups),
             'Built by the repository builder with --exclude; this image does not match a release.']
    lines += [f"{name}: {build_exclusions.GROUPS[name]['in_game']}" for name in groups]
    root.write_text('\n'.join(lines) + '\n', encoding='ascii', newline='\n')
    print('Quick test build: ' + build_exclusions.summary(groups) + ' (marker id1/' + build_exclusions.MARKER + ')', flush=True)
    return build_exclusions.record(groups)


def chim_world_receipt(chim_world):
    """Read and check a CHIM world's receipts (read only): its files are there, it passed validation
    against its source and names the chim builder. Returns (receipt, areas). Shared by chim_frame_maps
    and the payload preflight (tools/payload_preflight.py)."""
    chim_world = Path(chim_world)
    receipt_path, validate_path = chim_world/'chim-receipt.json', chim_world/'chim-validate.json'
    stats_path = chim_world/'chim-stats.json'
    for path in (chim_world/'chim/world.cwi', receipt_path, validate_path, stats_path):
        if not path.is_file():
            raise ValueError('CHIM world is incomplete: missing '+str(path))
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    report = json.loads(validate_path.read_text(encoding='utf-8'))
    if not report.get('ok') or not report.get('source_checked'):
        raise ValueError('CHIM world did not pass validation against its source: '+str(validate_path))
    if receipt.get('builder') != 'chim':
        raise ValueError('CHIM world receipt does not name the chim builder')
    areas = receipt.get('areas') or ([receipt['town']] if receipt.get('town') else [])
    return receipt, areas


def chim_frame_maps(chim_world, id1):
    """Check a CHIM world's receipts and write its frame maps into id1: maps/<town>-chim.bsp for each
    area (the engine loads it instead of the town's region maps when CHIM is on), and for Seyda Neen
    its special maps (format 0.5). Each is checked against the town's final legacy maps, which must
    still be in id1. Returns {'areas', 'receipt', 'frame_maps'}."""
    chim_world = Path(chim_world)
    receipt, areas = chim_world_receipt(chim_world)
    # Written before the partition, so a refused entity stops the image here.
    from chim.frame_map import SPECIALS, build as build_frame_map, build_docks
    frame_maps = [build_frame_map(id1, area, chim_world) for area in areas]
    # Seyda Neen's special maps (the intro docks, the Census courtyard) become further frame maps of
    # its frame (format 0.5): maps/intro_docks-chim.bsp, maps/sncourt-chim.bsp.
    if 'seyda' in areas:
        frame_maps += [build_docks(id1, chim_world, name=name) for name in SPECIALS]
    # Each frame map's far terrain (chim.far): maps/<frame map>.far beside it, like a Quake .lit file.
    for record in frame_maps:
        record['far_terrain'] = chim_far_sidecar(chim_world, id1, record)
    return {'areas': areas, 'receipt': receipt, 'frame_maps': frame_maps}


def chim_far_sidecar(chim_world, id1, record):
    """Copy the far terrain layer of a frame map's frame (CHIM output far/<cx>_<cy>.far) to
    id1/maps/<frame map>.far after checking it; None when the world has none (built without it)."""
    from chim.far import decode, file_name, sidecar_name
    if not record.get('frame') or not record.get('map'):
        return None
    source = Path(chim_world)/'far'/file_name(record['frame'])
    if not source.is_file():
        return None
    data = source.read_bytes()
    head = decode(data)[0]
    if list(head['cell']) != list(record['frame']):
        raise ValueError('Far terrain %s names frame %s, not %s' % (source.name, head['cell'], record['frame']))
    target = Path(id1)/sidecar_name(record['map'])
    if target.exists():
        raise ValueError('Far terrain already present: '+target.name)
    target.write_bytes(data)
    return {'file': sidecar_name(record['map']), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
            'size': list(head['size']), 'step': head['step']}


def add_chim_volume(chim_world, id1, out, index, xdftool, mib=None, frames=None):
    """The CHIM world as world volume AW_WORLD<index> (partition DW<index>, files under id1/chim/),
    written in pack order, read back and gated (tools/chim/disk.py); world/volumes.awv then counts it.
    frames: chim_frame_maps' result when the image wrote the frame maps earlier (pure CHIM); else
    they are written here. Returns (the volume entry for the hardfile, the build.json record)."""
    from chim.disk import IMAGE_BASE, pack_partition
    chim_world = Path(chim_world)
    if frames is None:
        frames = chim_frame_maps(chim_world, id1)
    receipt_path, validate_path = chim_world/'chim-receipt.json', chim_world/'chim-validate.json'
    stats_path = chim_world/'chim-stats.json'
    receipt, areas, frame_maps = frames['receipt'], frames['areas'], frames['frame_maps']
    if not 0 <= index < 8:
        raise ValueError('World payload exceeds the eight-volume runtime limit')
    volume = 'AW_WORLD%d' % index
    packed = pack_partition(chim_world/'chim', out/('world%d-partition.hdf' % index), volume, mib, xdftool, IMAGE_BASE)
    (id1/'world').mkdir(parents=True, exist_ok=True)
    (id1/'world/volumes.awv').write_bytes(b'AWV1'+bytes([index+1]))
    for path in (receipt_path, validate_path, stats_path):
        shutil.copyfile(path, out/path.name)
    entry = dict(file=packed['file'], volume=volume, partition='DW%d' % index, bytes=packed['bytes'],
                 sha256=packed['sha256'], files=packed['files'], readback=packed['readback'])
    record = {'status': 'packed', 'builder': receipt['builder'], 'chim_version': receipt.get('chim_version'),
              'world_format': receipt.get('world_format'), 'areas': areas,
              'volume': volume, 'partition': entry['partition'], 'path': IMAGE_BASE,
              'files': len(packed['files']), 'payload_bytes': sum(f['bytes'] for f in packed['files']),
              'partition_mib': packed['mib'], 'layout_gate': packed['layout'],
              'receipt_sha256': digest(receipt_path), 'validate_sha256': digest(validate_path),
              'stats_sha256': digest(stats_path), 'frame_maps': frame_maps}
    return entry, record


def miniwind_options(args):
    """None for a normal image; for --miniwind (tools/miniwind.py) the checked options:
    a private -devN version, the generated feature line and the optional description."""
    if not getattr(args, 'miniwind', False):
        if getattr(args, 'miniwind_features', None) or getattr(args, 'miniwind_description', None) or \
                getattr(args, 'miniwind_scope', None):
            raise ValueError('--miniwind-features/--miniwind-description/--miniwind-scope require --miniwind')
        if getattr(args, 'world_scenery', None) is None:
            raise ValueError('--world-scenery is required (a complete world scenery overlay)')
        return None
    import miniwind
    require_private_test_version(VERSION, [miniwind.OPTION])
    features = getattr(args, 'miniwind_features', None)
    if not features:
        raise ValueError('--miniwind needs --miniwind-features (tools/build.py generates it from its stage plan)')
    miniwind.data_file(features)
    for name in ('world_scenery', 'world_terrain', 'world_flora', 'seyda_recorded', 'gallery'):
        if getattr(args, name, None) is not None:
            raise ValueError('--miniwind builds Balmora only; drop --' + name.replace('_', '-'))
    scope = miniwind.check_scope(getattr(args, 'miniwind_scope', None) or miniwind.DEFAULT_SCOPE)
    if miniwind.label(scope) and not getattr(args, 'no_npc_gallery', False):
        raise ValueError(miniwind.SCOPE_OPTION + ' ' + scope + ' implies --no-npc-gallery')
    return {'features': features, 'scope': scope,
            'description': miniwind.check_description(getattr(args, 'miniwind_description', None))}


def startup_lines(mini, font_path, chim=False):
    """The startup screen's lines under the logo: the normal two lines of a
    legacy build, the one CHIM line of a CHIM build (chim=True: a CHIM world
    volume is packed), or for MiniWind its name, the version line from VERSION
    and CHIM_VERSION (its "CHIM v..." segment in the console font) and the
    optional "Scene:" line, wrapped with the game font (tools/miniwind.py).
    The engine draws MiniWind's "Press ENTER to start" under them."""
    from prepare_logo import (CHIM_STARTUP_LINES, STARTUP_LINES, TEXT_WIDTH, fallback_width, load_font,
                              text_width)
    if not mini:
        return CHIM_STARTUP_LINES if chim else STARTUP_LINES
    import miniwind
    from project_version import chim_version
    if font_path and Path(font_path).is_file():
        font = load_font(font_path)
        measure = lambda text: text_width(font, text)
    else:
        measure = fallback_width
    return tuple(miniwind.logo_lines(VERSION, chim_version(ROOT/'VERSION'), mini['description'],
                                     measure=measure, width=TEXT_WIDTH))


def image(args):
    """Package the NPC gallery by default; fail if any required payload is absent.

    The sole opt-out is explicit --no-npc-gallery, recorded in build.json and
    the image itself. Asset-free boot-notice images use build_dry_run.py.
    """
    if getattr(args, 'payload_preflight_only', False):
        # Read-only: the payload preflight alone on an existing run's staged payload (tools/build.py --check-payload).
        return payload_preflight(args, ensure_external(args.out, 'prepared AGA image'), excluded_groups(args),
                                 image_jobs(args))
    require_private_test_version(VERSION, image_waivers(args))
    mini = miniwind_options(args)
    jobs = image_jobs(args)
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
    excluded=excluded_groups(args)
    if 'music' not in excluded and not getattr(args,'music',None):
        raise ValueError('--music is required unless the quick test build leaves the music out (--exclude music)')
    scene=ensure_external(args.scene,'AGA scene');out=new_output(args.out)
    if 'music' not in excluded:ensure_external(args.music,'converted music')
    boot=out/'boot';shutil.copytree(scene/'id1',boot/'id1');(boot/'S').mkdir()
    if mini:
        # Balmora only: every other area's maps leave before any pass runs.
        import miniwind
        from chim.frame_map import remove_legacy_areas
        mini['prune']=miniwind.prune(boot/'id1',scope=mini['scope'],remove_legacy=remove_legacy_areas)
        (out/'miniwind-prune.json').write_text(json.dumps(mini['prune'],indent=2)+'\n',encoding='utf-8',newline='\n')
    excluded_content=stage_excluded_content(boot, excluded)
    (out/'excluded-content.json').write_text(json.dumps(excluded_content,indent=2)+'\n',encoding='utf-8',newline='\n')
    terrain = getattr(args, 'world_terrain', None)
    if terrain:
        from install_world_terrain import install as install_world_terrain
        terrain_acceptance = install_world_terrain(terrain, boot/'id1')
        (out/'world-terrain-staging.json').write_text(json.dumps(terrain_acceptance,indent=2)+'\n',encoding='utf-8',newline='\n')
    if mini:
        world_scenery_acceptance={'status':'not_built','reason':'--miniwind: no open world'}
    else:
        world_scenery_acceptance=install_world_scenery(args.world_scenery,boot/'id1',jobs=jobs)
    (out/'world-scenery-staging.json').write_text(json.dumps(world_scenery_acceptance,indent=2)+'\n',encoding='utf-8',newline='\n')
    flora = getattr(args, 'world_flora', None)
    if flora:
        from install_world_flora import install as install_world_flora
        flora_acceptance = install_world_flora(flora, boot/'id1', world_scenery_acceptance, jobs=jobs)
        (out/'world-flora-staging.json').write_text(json.dumps(flora_acceptance, indent=2)+'\n', encoding='utf-8', newline='\n')
    cfg=boot/'id1/default.cfg'
    cfg.write_text(startup_config(cfg.read_text()), newline='\n')
    shutil.copyfile(ROOT/'config/keymaps.cfg',boot/'id1/keymaps-default.cfg')
    logs_record=stage_game_config(boot/'id1', debug_luma=engine_record.get('debug_luma',False),
                                  live_logs=getattr(args,'live_logs',False))
    (out/'diagnostic-logs.json').write_text(json.dumps(logs_record,indent=2)+'\n', newline='\n')
    if logs_record['diagnostic_logs']=='live':
        print('[diagnostics] --live-logs: this image writes its diagnostic logs as they happen (benchmark/diagnostic image)',flush=True)
    stage_debug_catalogues(boot/'id1', debug_luma=engine_record.get('debug_luma',False))
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
    from build_torchtest import build as build_torchtest
    torchtest_report=build_torchtest(boot/'id1/gfx/palette.lmp',boot/'id1/maps/torchtest.bsp',
                                    out/'torchtest-build',args.qbsp,args.vis,args.light)
    (out/'torchtest-staging.json').write_text(json.dumps(torchtest_report,indent=2)+'\n', newline='\n')
    (out/'torch-conversion.json').write_text(json.dumps(torch_report,indent=2)+'\n', newline='\n')
    # Melee combat for every NPC and the Vivec Arena minigame (docs/COMBAT.md):
    # game settings, one combat sheet per NPC record, the hit/miss sounds and the
    # Arena fighters' combat-frame models, all from the owned master.
    from prepare_combat import prepare as prepare_combat
    print('Converting combat data (settings, NPC sheets, sounds, Arena fighters)...',flush=True)
    combat_report=prepare_combat(args.data_files,boot/'id1',jobs=jobs)
    (out/'combat-data.json').write_text(json.dumps(combat_report,indent=2)+'\n',encoding='utf-8',newline='\n')
    from prepare_world_ui import prepare as prepare_world_ui, validate as validate_world_ui
    if args.data_files:prepare_world_ui(args.data_files,None,boot)
    validate_world_ui(boot/'id1')
    logo=ROOT/'resources/media/AmiWind_wordmark.png'
    # Menu logo: the gold name without the rule, on the palette's gold ramp
    # (UI-MENU-LOGO-32); --menu-logo legacy keeps the old wordmark method.
    menu_logo_style=getattr(args,'menu_logo','gold') or 'gold'
    if menu_logo_style=='legacy':
        prepare_menu_logo(logo,boot/'id1/gfx/palette.lmp',boot/'id1/gfx/amiwind.awi',style='legacy')
    else:
        prepare_menu_logo(ROOT/'resources/media/AmiWind_logo_name_only.png',boot/'id1/gfx/palette.lmp',
                          boot/'id1/gfx/amiwind.awi')
    logo_stream=boot/'id1/intro/amiwind.awv'
    if logo_stream.exists():logo_stream.unlink()
    # MiniWind: the stream ends on the full screen, which the engine holds with its
    # "Press ENTER to start" line until Enter (aw_movie.c); normal builds fade out.
    prepare_logo(logo,logo_stream,boot/'id1/gfx/magic16.awf',lines=startup_lines(mini,boot/'id1/gfx/magic16.awf',chim=bool(getattr(args,'chim_world',None))),
                 **({'prompt_top':miniwind.PROMPT_Y} if mini else {}))
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
    (boot/'id1/quake.rc').write_text('exec default.cfg\nexec default-game.cfg\nexec config.cfg\nexec keymap.cfg\nexec keymaps.cfg\nexec autoexec.cfg\naw_controls_migrate\naw_gallery_migrate\naw_horizon_migrate\naw_startup\n', newline='\n')
    if mini:
        # The engine reads the notice and starts in the town (aw_miniwind.c, aw_scene.c aw_quick_start).
        (boot/'id1'/miniwind.DATA_FILE).write_bytes(miniwind.data_file(mini['features']))
        (boot/miniwind.MARKER_FILE).write_text(miniwind.marker_text(VERSION,mini['features'],mini['description'],
                                                                    scope=mini['scope']),newline='\n')
        print('Default start: logo fade, "'+miniwind.PROMPT+'", then '+miniwind.TOWN+' (Hors preset); New Game starts '
              'there again. '+miniwind.partial_area(mini['scope'])+'.',flush=True)
    else:
        print('Default start: logo fade then main menu; New Game plays the optional movie then ship + track 04.',flush=True)
    shutil.copyfile(args.engine,boot/'AmiWind')
    shutil.copyfile(checker,boot/'AmiWindCheck')
    fpu_receipt=stage_fpu_support(args,engine_record,boot)
    (out/'fpu-support.json').write_text(json.dumps(fpu_receipt,indent=2)+'\n',encoding='utf-8',newline='\n')
    (boot/'S/startup-sequence').write_text(fpu_support.startup_sequence(fpu_receipt), newline='\n')
    if not mini:
        for name in ['seyda.map','town.wad']:shutil.copyfile(scene/name,out/name)
    if (scene/'scene-ready.json').is_file():
        ready=json.loads((scene/'scene-ready.json').read_text())
        if ready.get('format')!='AmiWind compiled mesh BSP29':raise ValueError('Unknown compiled scene format')
        from player_hull import PROFILE
        if ready.get('standing_hull_profile')!=PROFILE:raise ValueError('Rebuild the scene: standing collision hull does not match this runtime')
        if not ready.get('hands'):raise ValueError('Prepare first-person hands before building this runtime')
        if not mini:shutil.copyfile(scene/'seyda.bsp',out/'seyda.bsp')
    else:
        raise ValueError('Prepare the matching mesh scene before building this runtime image')
    if not mini:
        shutil.copyfile(out/'seyda.bsp',boot/'id1/maps/seyda.bsp')
        from prepare_seyda_regions import convert_builder_scene
        convert_builder_scene(boot/'id1/maps', scene_map=out/'seyda.map',
                              palette=boot/'id1/gfx/palette.lmp', ericw_bin=args.qbsp.parent,
                              work_dir=out/'bounded-seyda', vis_mode=getattr(args,'vis_mode','fast'),
                              canonical_land_source=getattr(args,'canonical_land_source',None), jobs=jobs,
                              recorded=getattr(args,'seyda_recorded',None))
    # Recorded-stage exception (BUILD-SEYDA-REGEN-30): later passes keep these maps byte for byte.
    import recorded_stage
    frozen=recorded_stage.frozen_maps(out/'bounded-seyda')
    if getattr(args, 'balmora_cache', None):
        from repair_balmora_maps import repair as repair_balmora_maps
        print('Preparing measured bounded Balmora layout from complete source cache...', flush=True)
        repair_balmora_maps(boot/'id1/maps', cache=args.balmora_cache,
                           palette=boot/'id1/gfx/palette.lmp', ericw_bin=args.qbsp.parent,
                           work_dir=out/'bounded-balmora', threads=jobs, vis_mode=getattr(args,'vis_mode','fast'))
    if flora:
        from install_town_flora import install as install_town_flora
        from prepare_quake import CENTRE
        town_palette = args.scene/'id1/gfx/palette.lmp'
        seyda_origin = [CENTRE[0]*.25, CENTRE[1]*.25, 0.]
        actual = json.loads((boot/'id1/seyda-regions.json').read_text(encoding='utf-8'))
        seyda_entries = [{**entry, 'origin':seyda_origin} for entry in actual['regions']]
        if frozen:
            towns = {'seyda':recorded_stage.keep_town_flora(boot, flora, [e['name']+'.bsp' for e in seyda_entries])}
        else:
            towns = {'seyda':install_town_flora(boot, flora, town_palette,
                entries=seyda_entries, town_source_index=args.town_flora_source_index,
                town_scene_report=args.town_flora_scene_report, work_dir=out/'town-flora-seyda')}
            shutil.copyfile(boot/'id1/maps'/(actual['fallback_alias']+'.bsp'), boot/'id1/maps/seyda.bsp')
        from install_town_flora import town_entries
        towns['balmora'] = install_town_flora(boot, flora, town_palette,
            entries=town_entries('balmora'),
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
    if getattr(args,'harvest',None):
        # Harvestable mushrooms replace baked ones before the final map passes (BUILD-HARVEST-NOT-BUILT-32).
        from harvest_build import clear_baked
        clear_baked(args.harvest,boot/'id1',out/'harvest',data_files=args.data_files,jobs=jobs)
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
        grounding=annotate(boot/'id1/maps',child_ci(args.data_files,'Morrowind.esm'),jobs=jobs,exclude=frozen)
        (out/'actor-grounding.json').write_text(json.dumps(grounding,indent=2)+'\n', newline='\n')
        (out/'actor-ground-support.json').write_text(json.dumps(bake_ground(boot/'id1/maps',jobs=jobs,exclude=frozen),indent=2)+'\n', newline='\n')
    recorded_stage.check(boot/'id1',out/'bounded-seyda','image map passes (flora, harvest removal, actor grounding)',jobs=jobs)
    return finalize_image(args)


def miniwind_hdf_tag(args):
    """'' for a normal image; a MiniWind image's HDF tag (-MiniWind-PARTIAL-AREA, plus
    -quick-playtest-no-NPC-gallery for --miniwind-scope exterior)."""
    if not getattr(args, 'miniwind', False):
        return ''
    import miniwind
    return miniwind.hdf_tag(getattr(args, 'miniwind_scope', None) or miniwind.DEFAULT_SCOPE)


def miniwind_start():
    """build.json default_start of a MiniWind image (aw_movie.c, aw_scene.c aw_quick_start)."""
    import miniwind
    return {'profile': 'logo-fade-enter-then-quick-start', 'movie': 'intro/amiwind.awv', 'prompt': miniwind.PROMPT,
            'new_game_map': miniwind.TOWN,
            'character': 'Hors preset (Nord, Barbarian, The Steed)', 'notice_file': 'id1/' + miniwind.DATA_FILE}


def miniwind_receipt(args, out, boot):
    """build.json build_type of a MiniWind image: what it is, its notice, logo lines and pruning."""
    import miniwind
    prune = json.loads((out / 'miniwind-prune.json').read_text(encoding='utf-8'))
    notice = boot / 'id1' / miniwind.DATA_FILE
    logo = startup_lines(miniwind_options(args), boot / 'id1/gfx/magic16.awf')
    scope = miniwind.check_scope(getattr(args, 'miniwind_scope', None) or miniwind.DEFAULT_SCOPE)
    return {'name': miniwind.NAME, 'scope': scope, 'label': miniwind.label(scope),
            'partial_area': miniwind.partial_area(scope), 'town': miniwind.TOWN,
            'notice': [miniwind.NOTICE_TITLE, args.miniwind_features],
            'notice_file': 'id1/' + miniwind.DATA_FILE, 'notice_sha256': digest(notice),
            'marker_file': miniwind.MARKER_FILE, 'description': getattr(args, 'miniwind_description', None),
            'logo_lines': [miniwind.line_text(line) for line in logo],
            'logo_console_font': [text for line in logo if not isinstance(line, str)
                                  for text, font in line if font == miniwind.CONSOLE_FONT],
            'prompt': miniwind.PROMPT,
            'maps_removed': len(prune['maps_removed']),
            'bytes_removed': prune['bytes_removed'], 'maps_kept': len(prune['maps_kept']),
            'interiors_missing': prune['interiors_missing']}


def staged_exterior_map_names(id1):
    """Explicit runtime directories identify exterior cells; sky is not a classifier."""
    id1 = Path(id1)
    from town_config import runtime_towns
    towns = runtime_towns()
    names = {name for name in (*(town['name'] for town in towns), 'intro_docks', 'sncourt')
             if (id1 / 'maps' / (name + '.bsp')).is_file()}
    for town in towns:
        directory = id1 / town['regions']
        if directory.is_file():
            names.update(Path(name).stem for name in town_region_map_names(directory, town['prefix']))
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


def staged_town_interiors(id1):
    """Converted town interiors (config/towns.json town lists) present in the stage."""
    from town_config import town_interiors
    return [room['map'] for room in town_interiors() if (Path(id1) / 'maps' / (room['map'] + '.bsp')).is_file()]


def staged_interior_map_names(id1):
    """Only explicit authored scene catalogue interior classifications apply."""
    from area_config import SCENES
    id1 = Path(id1)
    return {scene["map"] for scene in SCENES if scene.get("interior") is True
            and (id1 / "maps" / (scene["map"] + ".bsp")).is_file()} | set(staged_town_interiors(id1))


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

def payload_preflight(args, out, excluded, jobs):
    """The image step's read-only payload checks over the staged payload, before it writes anything
    (tools/payload_preflight.py; CHIM-HARVEST-SPECIALS-33 stopped three image runs at their end)."""
    import payload_preflight as preflight
    return preflight.run(out, chim_world=getattr(args, 'chim_world', None),
                         music=None if 'music' in excluded else getattr(args, 'music', None), jobs=jobs)

def finalize_image(args):
    """Finalize an already prepared private image stage through every normal gate.

    This is the shared image tail, not a skip-validation/resume CLI. A separate
    controlled continuation must verify its frozen stage before invoking it.
    """
    out=ensure_external(args.out,'prepared AGA image')
    boot=out/'boot'
    excluded=excluded_groups(args)
    music=ensure_external(args.music,'converted music') if 'music' not in excluded else None
    args.hands=getattr(args,'hands','3d')
    # One worker budget for every per-map pass (--jobs; shared pool, tools/build_parallel.py).
    jobs=image_jobs(args)
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
    fpu_receipt=fpu_support.load_receipt(out/'fpu-support.json')
    if (boot/FPU_LOADER).is_file() and digest(boot/FPU_LOADER)!=engine_record.get('fpu_loader_sha256'):
        raise ValueError('Staged AmiWindFPU differs from its verified build receipt')
    if (boot/FPU_LOADER).is_file()!=(fpu_receipt['status']=='installed'):
        raise ValueError('Staged AmiWindFPU and the FPU support receipt disagree')
    if engine_record.get('hands','3d')!=args.hands:
        raise ValueError('Image hands choice must match engine build')
    heap_loader_source_sha256=verify_heap_loader_source_receipt(engine_record)
    # Every read-only payload check first, all errors together, before any write (tools/payload_preflight.py).
    payload_preflight(args, out, excluded, jobs)
    gallery_report=json.loads((out/'npc-gallery-staging.json').read_text())
    torch_report=json.loads((out/'torch-conversion.json').read_text())
    combat_data=json.loads((out/'combat-data.json').read_text()) if (out/'combat-data.json').is_file() else None
    torchtest_report=json.loads((out/'torchtest-staging.json').read_text())
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
    if getattr(args,'hand_catalog',None):
        # Per-race hands after the sky palette bank: converted against this final
        # palette, so no remap touches them (BUILD-HANDS-NOT-BUILT-32).
        from prepare_hand_catalog import install as install_hand_catalog
        if args.hands!='3d':raise ValueError('The per-race hand catalogue applies to 3D hands only')
        hand_catalog=install_hand_catalog(args.hand_catalog,boot/'id1')
        (out/'hand-catalog-staging.json').write_text(json.dumps(hand_catalog,indent=2)+'\n',encoding='utf-8',newline='\n')
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
        work_dir=exterior_sky_path.parent, jobs=jobs)
    from recorded_stage import check as check_recorded
    check_recorded(boot/'id1', out/'bounded-seyda', 'sky asset preparation and exterior sky', jobs=jobs)
    if excluded:
        # Quick test build: the shared assets maps and the engine find by name (the sky,
        # palette, fonts, menus) are kept by every exclusion (build_exclusions.ALWAYS_INCLUDED).
        from build_exclusions import check_always_included, worldspawn_sky_keys
        always_included=check_always_included(boot/'id1', exterior=bool(staged_exterior_map_names(boot/'id1')),
                                              maps=worldspawn_sky_keys(boot/'id1/maps'))
        (out/'always-included.json').write_text(json.dumps(always_included,indent=2)+'\n',encoding='utf-8',newline='\n')
    # Run after all meshes/overlays, before compaction, contact/heap and fingerprints.
    from hidden_surface_build import cull_staged_maps, enabled_value
    hidden_surface_path = out / 'hidden-surface-cull' / 'hidden-surfaces.json'
    hidden_surfaces = cull_staged_maps(boot / 'id1/maps', hidden_surface_path.parent,
        staged_exterior_map_names(boot / 'id1'),
        enabled=enabled_value(getattr(args, 'hidden_surface_cull', 'true')),
        jobs=jobs)
    check_recorded(boot/'id1', out/'bounded-seyda', 'hidden-surface cull', jobs=jobs)
    # Regional map generation can replace a worldspawn after hands conversion.
    # Stamp all final maps from the same authored animation report before gates.
    from hand_metadata import stamp_staged_hands
    hand_source = json.loads((Path(args.scene)/'scene-ready.json').read_text())['hands']
    hand_metadata = stamp_staged_hands(boot/'id1', hand_source,
        staged_exterior_map_names(boot/'id1') | staged_interior_map_names(boot/'id1'), jobs=jobs)
    (out/'hand-metadata.json').write_text(json.dumps(hand_metadata,indent=2)+'\n', newline='\n')
    check_recorded(boot/'id1', out/'bounded-seyda', 'first-person hand metadata', jobs=jobs)
    # Finish immutable BSP sharing before contact/heap gates and fingerprinting.
    # This step is interpreted Python only; it never creates a native helper.
    from optimize_world_maps import optimize_maps, verify_optimized_maps, bind_heap_report
    optimization_path = out/'optimize-world-maps.json'
    print('Verifying exact staged map geometry/light/PVS sharing...', flush=True)
    optimization = optimize_maps(boot/'id1/maps', optimization_path, jobs=jobs)
    check_recorded(boot/'id1', out/'bounded-seyda', 'world map optimisation', jobs=jobs)
    # Harvest catalogues for the final maps: geometry gate, heap admission (BUILD-HARVEST-NOT-BUILT-32).
    from harvest_build import image_step as harvest_image_step
    harvest = harvest_image_step(args, boot/'id1', out/'harvest', jobs=jobs)
    # Placement correction is not its own proof: independently read the final
    # BSP/MDL payload, and stop before fingerprinting or HDF creation on failure.
    from check_actor_ground import require as require_actor_ground
    actor_report = require_actor_ground(boot/'id1/maps', out/'actor-initial-contact.json',
                                       getattr(args, 'allow_known_actor_ground_findings', None),
                                       findings_only=True, jobs=jobs)
    actor_acceptance = actor_report['acceptance']
    (out/'actor-ground-acceptance.json').write_text(json.dumps(actor_acceptance, indent=2)+'\n', newline='\n')
    # Count original versus placed entities on the final maps; an unexplained
    # loss against the previous build stops here, before any disk is made.
    from entity_tracker import build_gate as entity_gate
    from mwad.paths import child_ci
    from prepare_mesh_bsp import DRESSING_EXCLUDED
    entity_tracker = entity_gate(out, boot/'id1/maps', child_ci(args.data_files,'Morrowind.esm'),
        getattr(args,'entity_baseline',None), getattr(args,'accept_entity_loss',None), jobs=jobs,
        dressing_terms=DRESSING_EXCLUDED)
    # World progress map data: topomap coverage plus entity and POI layers.
    from world_progress import build_step as world_progress_step
    if getattr(args, 'miniwind', False):
        world_progress = {'status': 'not_built', 'reason': '--miniwind: no open-world region directory'}
    else:
        world_progress = world_progress_step(out, boot/'id1/world/regions.awr', out/'entity-tracker.json',
            child_ci(args.data_files,'Morrowind.esm'), Path(__file__).resolve().parents[1]/'docs/trackers/checked.json')
    # Audit the final prepared payload after subdivision and actor annotation;
    # an earlier audit cannot authorize maps subsequently regenerated here.
    world_heap_path=out/'world-map-heap.json'
    verify_optimized_maps(boot/'id1/maps', optimization, jobs=jobs)
    # Every town arrival and return point is a standing spot on the final
    # collision, by the engine's own arrival search (VIVEC-ARENA-TP-ARRIVAL-32).
    from arrival_spot import require as require_arrivals
    require_arrivals(boot/'id1', out/'arrival-check.json')
    # Night lamp, glowing glass and location fog tables from the final maps (read only; before a pure CHIM image
    # removes the CHIM towns' legacy maps below).
    from night_lighting import stage as stage_night_lighting, image_sources
    night_lighting = stage_night_lighting(boot/'id1', master=child_ci(args.data_files,'Morrowind.esm'),
        maps=staged_exterior_map_names(boot/'id1'), sources=image_sources(args),
        palette=boot/'id1/gfx/palette.lmp', data_files=args.data_files, work_dir=out/'night-lighting')
    # Pure CHIM (--builder chim): each CHIM town's frame maps are written and checked against its
    # final legacy maps (statics both ways, origin, harvest representation), then those legacy maps
    # leave the image (chim.frame_map.remove_legacy_areas, recorded): the stair and heap gates below
    # see only what ships, and the CHIM world carries its own (tools/chim_build.py).
    chim_frames, removed_legacy, not_on_chim = None, [], []
    if getattr(args, 'chim_world', None):
        chim_frames = chim_frame_maps(args.chim_world, boot/'id1')
        from chim.frame_map import remove_legacy_areas, remove_towns_not_on_chim
        removed_legacy = remove_legacy_areas(boot/'id1', chim_frames['areas'], 'the town runs on CHIM')
        # Extra towns not on CHIM yet (the Vivec Arena) leave a CHIM image whole: exterior maps, region and
        # door tables, harvest catalogues; the engine then finds no such destination (CHIM-LEGACY-CHAIN-33).
        not_on_chim = [town['id'] for town in staged_extra_towns(boot/'id1') if town['id'] not in chim_frames['areas']]
        removed_legacy += remove_towns_not_on_chim(boot/'id1', not_on_chim)
        (out/'chim-removed-legacy.json').write_text(json.dumps(removed_legacy, indent=2)+'\n', encoding='utf-8',
                                                   newline='\n')
        # Each frame map's whole-map heap (CHIM-SEYDA-MEMORY-33): the zone the engine can take beside
        # the frame map's own Hunk, its rings with the streamed statics' models, on this build's heap.
        from chim.heap import require_frame_map_heap
        frame_heap = require_frame_map_heap(args.chim_world, boot/'id1', args.sdk, heap_mb=engine_record.get('heap_mb'),
                                            report_path=out/'chim-frame-heap.json')
        for name, m in sorted(frame_heap.get('maps', {}).items()):
            print(f"[chim] frame-map heap {name}: zone {m['zone_bytes']} B (after the map {m['after_zone_bytes']} B), "
                  f"active ring {m['peak_bytes']} / load ring {m['load_ring']['peak_bytes']} of {m['budget_bytes']} B, "
                  f"streamed models {m['streamed_bytes']} B, largest block {m['largest_block_bytes']} B", flush=True)
        # The optimizer receipt follows the new map set (frame maps in, removed maps out) before the gates.
        from optimize_world_maps import rebind_chim_maps
        optimization = rebind_chim_maps(boot/'id1/maps', optimization, optimization_path,
                                        [row['file'] for row in removed_legacy], jobs=jobs)
    # Every flight of stairs in every map can be walked up and down by the
    # standing box (COLLISION-STAIR-SLOPE-32); on with follow_original_stair_rules.
    # The recorded Seyda Neen stage (BUILD-SEYDA-REGEN-30) is reported, not gated.
    from mesh_geometry_env import stair_rules_enabled
    if stair_rules_enabled():
        from stair_walk import require as require_stairs
        from recorded_stage import frozen_maps
        from chim.known import known_stair_findings
        # Private -devN tests only (image_waivers above): known findings accepted by tracker ID.
        accepted = known_stair_findings(getattr(args, 'accept_known_stair_findings', None) or [])
        require_stairs(boot/'id1', out/'stair-walk.json', jobs=jobs,
                       exempt=[name[:-4] for name in frozen_maps(out/'bounded-seyda')], accepted=accepted)
    world_heap=audit_world_map_heap_with_receipt(engine_record,boot/'id1/maps',args.sdk,world_heap_path,jobs=jobs)
    bind_heap_report(optimization, world_heap, world_heap_path, optimization_path)
    heap_watcher=heap_watcher_summary(world_heap,world_heap_path)
    if (out/'dressing-track.json').is_file():
        # Dressing track: each map's placed dressing with its modelled heap (BUILD-DRESSING-EXCLUDED-32).
        from entity_tracker import add_heap
        add_heap(out/'dressing-track.json', world_heap)
    (out/'heap-watcher.json').write_text(json.dumps(heap_watcher,indent=2)+'\n',encoding='utf-8',newline='\n')
    budget_policy_path = out / 'map-budget-policy.json'
    budget_decision = apply_map_budget_policy(world_heap,
        getattr(args, 'map_budget_policy', 'strict'), budget_policy_path,
        maps_dir=boot/'id1/maps', builder=getattr(args, 'builder', 'legacy'))
    for row in budget_decision['temporary_pre_chim_bypass']:
        print(f"[heap] {row['map']}: {BYPASS_STATUS} ({row['bug']}; ends with {row['until']}); "
              f"modelled clearance {row['estimated_clearance_bytes']} bytes.", flush=True)
    for row in budget_decision['bypass_refused']:
        print(f"[heap] {row['map']}: {BYPASS_STATUS} refused: {row['reason']}.", flush=True)
    heap_watcher['status'] = budget_decision['status']
    heap_watcher['budget_policy'] = budget_decision
    (out/'heap-watcher.json').write_text(json.dumps(heap_watcher,indent=2)+'\n',encoding='utf-8',newline='\n')
    prefix = ('World-map heap estimate passed with a temporary pre-CHIM bypass:'
              if budget_decision['status'] == 'estimate_passed_with_temporary_pre_chim_bypass' else
              '[warning: needs adjustment]' if world_heap['failing_maps'] else 'World-map heap estimate passed:')
    print(f"{prefix} {world_heap['passing_maps']}/{world_heap['map_count']} maps clear the modeled allowance; "
          f"minimum clearance {world_heap['minimum_estimated_clearance_bytes']} bytes after unchanged baseline "
          f"and safety reserves. Policy={budget_decision['policy']}; runtime validation pending.",flush=True)
    verify_optimized_maps(boot/'id1/maps', optimization, jobs=jobs)
    # Every map write is above: the recorded maps ship exactly as recorded.
    removed_files = [row['file'] for row in removed_legacy]
    recorded_stage = check_recorded(boot/'id1', out/'bounded-seyda', 'final image payload', jobs=jobs,
                                    removed=removed_files)
    write_content_fingerprint(boot/'id1', jobs=jobs, partial=getattr(args, 'miniwind', False) and
                              (getattr(args, 'miniwind_scope', None) or True), removed=removed_files,
                              excluded=excluded)
    if 'music' in excluded:
        # Quick test build without music (--exclude music): no soundtrack, no playlist;
        # the game stays silent and says so once (aw_excluded.c).
        manifest={'tracks':[]};groups={'title':None,'explore':[],'battle':[]};opening_track=None;music_catalogue=None
        print('Quick test build: music left out (--exclude music).',flush=True)
    else:
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
    intro_receipt_path = Path(args.scene)/'intro-conversion.json'
    intro_receipt = json.loads(intro_receipt_path.read_text()).get('movie') if intro_receipt_path.is_file() else None
    media_coverage = stage_catalogue(args.media, boot/'id1', manifest, intro_receipt,
                                     excluded=['music'] if 'music' in excluded else [])
    media_coverage_path = out/'media-coverage.json'
    media_coverage_path.write_text(json.dumps(media_coverage,indent=2)+'\n',encoding='utf-8',newline='\n')
    # Missing original inputs remain warnings, but every available source must
    # have a validated converted output before any image packing begins.
    require_complete_media_outputs(media_coverage)
    # Leave filesystem metadata and future saves room; retain legacy-safe sizes.
    verify_heap_loader_source_receipt(engine_record)
    # Before the world volumes take their files: every shipped text file is checked once.
    check_payload_host_paths(boot, [out.resolve()])
    # Safety net of a CHIM build: no legacy exterior map of a CHIM area is packed (the removal above is the
    # step that guarantees it; anything found here, e.g. re-added by a later pass, stops the build).
    legacy_check = None
    if chim_frames is not None:
        from chim.frame_map import require_no_legacy_areas
        legacy_check = require_no_legacy_areas(boot/'id1', chim_frames['areas'], 'final image payload',
                                               not_on_chim=not_on_chim)
    from world_volumes import pack as pack_world_volumes
    world_images=pack_world_volumes(boot/'id1',out,VERSION,args.xdftool,args.rdbtool,jobs=jobs)
    chim_world={'status':'not_requested'}
    if getattr(args,'chim_world',None):
        volume,chim_world=add_chim_volume(args.chim_world,boot/'id1',out,len(world_images),args.xdftool,
                                          frames=chim_frames)
        chim_world['removed_legacy']=removed_legacy
        chim_world['legacy_check']=legacy_check
        chim_world['not_on_chim']=not_on_chim
        world_images.append(volume)
    check_payload_names(boot)
    from world_volumes import (assemble_drives, partition_mib as planned_mib, plan_drives, planned_partition,
                               write_boot_partition)
    payload_bytes=sum(p.stat().st_size for p in boot.rglob('*') if p.is_file())
    partition_mib=planned_mib(payload_bytes)
    suffix = '' if actor_acceptance['production_gate_passed'] and budget_decision['production_memory_gate_passed'] else '-private-test'
    if suffix:
        require_private_test_version(VERSION, ['a failed production gate'])
    # A MiniWind image says PARTIAL-AREA (and its scope's label) in its file names (tools/miniwind.py);
    # a quick test build (--exclude) says -quick-test.
    from build_exclusions import HDF_TAG
    tag = miniwind_hdf_tag(args) + (HDF_TAG if excluded else '')
    part=out/'partition.hdf';hdf=out/f'AmiWind-v{VERSION}{tag}{suffix}.hdf'
    boot_paths=[p for p in sorted(boot.rglob('*')) if p.is_file()]
    # The disk-layout gate on the PLAN, before the boot partition or any drive is written: every
    # partition starts below 2 GiB and is below 2 GiB, files well under 2 GiB, drives below 4 GiB
    # (BUILD-WORLD-PARTITION-MOUNT-33). hardfile_groups groups the partitions into drives.
    drive_plans=plan_drives(planned_partition('DH0',[dict(path=p.relative_to(boot).as_posix(),bytes=p.stat().st_size)
                                                     for p in boot_paths],'AMIWIND'),world_images,
                            name=lambda index:hdf.name if index==0 else f'AmiWind-v{VERSION}{tag}{suffix}-world-{index:02d}.hdf')
    root_check=write_boot_partition(args.xdftool,part,boot,partition_mib)
    from build_parallel import hash_files
    boot_files=[dict(path=p.relative_to(boot).as_posix(),bytes=p.stat().st_size,sha256=value)
                for p,value in zip(boot_paths,hash_files(boot_paths,jobs))]
    # Every planned drive written (rdbtool), read back and gated again as written: require_mountable and
    # require_disk_layout(drive.name, drive.stat().st_size, checked, partitions); the measured layout goes
    # into build.json.
    layout,drive_receipts,disk_layout=assemble_drives(args.rdbtool,drive_plans,out,part,boot_files,jobs=jobs,run=run)
    for volume in world_images:(out/volume['file']).unlink()
    part.unlink()
    verify_heap_loader_source_receipt(engine_record)
    build_json={
        'version':VERSION,'hands':args.hands,'debug_luma':engine_record.get('debug_luma',False),'actor_ground_audit':actor_acceptance,
        'npc_gallery':gallery_report,'torch_test':torchtest_report,'world_scenery':world_scenery_acceptance,
        'world_flora':json.loads((out/'world-flora-staging.json').read_text(encoding='utf-8')) if (out/'world-flora-staging.json').is_file() else {'status':'not_requested'},
        'sky_asset_preparation':sky_asset_preparation,
        'guard_torches':guard_torches,
        'night_lighting':night_lighting,
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
            'production_memory_gate':budget_decision['production_memory_gate'],
            'temporary_pre_chim_bypass':budget_decision['temporary_pre_chim_bypass'],
            'runtime_validation':'pending','report':world_heap_path.name,
            'report_sha256':digest(world_heap_path),'map_count':world_heap['map_count'],
            'minimum_estimated_clearance_bytes':world_heap['minimum_estimated_clearance_bytes'],
            'baseline_reserve_bytes':world_heap['baseline_reserve_bytes'],
            'safety_headroom_bytes':world_heap['safety_headroom_bytes'],
            'loader_source_sha256':heap_loader_source_sha256,
            'acceptance':world_heap['acceptance']},
        'torch':torch_report,'combat_data':combat_summary(combat_data),'hdf_file':hdf.name,'hdf_files':drive_receipts,'disk_layout':disk_layout,'chim_world':chim_world,
        'default_start':{'profile':'logo-fade-then-main-menu','movie':'intro/amiwind.awv',
            'music_track':groups['title'],'new_game_map':'prison',
            'new_game_movie':'intro/mw_intro.awv' if movie.exists() else None,
            'new_game_music_track':4,
            'new_game_music_source':opening_track['source'] if opening_track else None}
            if not getattr(args, 'miniwind', False) else miniwind_start(),
        'hdf_bytes':hdf.stat().st_size,'hdf_sha256':digest(hdf),
        'binary_sha256':digest(boot/'AmiWind'),'bootcheck_sha256':digest(checker),
        'fpu_support':fpu_receipt,
        'payload_bytes':sum(p['payload_bytes'] for p in layout),'partitions':layout,
        'media_coverage':{'report':media_coverage_path.name,'sha256':digest(media_coverage_path),
            'categories':media_coverage['categories'],'excluded':media_coverage.get('excluded',[]),
            'payload_readback':'passed'},
        'excluded_content':(json.loads((out/'excluded-content.json').read_text(encoding='utf-8'))
            if (out/'excluded-content.json').is_file() else stage_excluded_content(boot, excluded)),
        'music_tracks':len(manifest['tracks']),'music_catalogue':music_catalogue,'heap_reservation_bytes':world_heap['heap_budget_bytes'],
        'tested_minimum':False,'filesystem':'DOS1 FFS partitions in legacy-safe RDB HDF drives',
        'legacy_root_check':root_check}
    if getattr(args, 'miniwind', False):
        build_json['build_type'] = miniwind_receipt(args, out, boot)
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
    build_record = json.loads((out/'build.json').read_text(encoding='utf-8'))
    build_record['entity_tracker'] = entity_tracker
    build_record['world_progress'] = world_progress
    build_record['harvest'] = harvest
    build_record['recorded_stage'] = ({'exception':recorded_stage['exception'],'pin':recorded_stage['pin'],
        'pin_sha256':recorded_stage['pin_sha256'],'files':len(recorded_stage['files']),
        'checks':recorded_stage['checks']} if recorded_stage else {'status':'none'})
    (out/'build.json').write_text(json.dumps(build_record,indent=2)+'\n',encoding='utf-8',newline='\n')
    write_world_coverage(out,'image',getattr(args,'world_coverage',None))

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    e=sub.add_parser('engine');e.add_argument('--cpu',choices=['68020','68040'],default='68040');e.add_argument('--archive',type=Path,help='Optional legacy provenance check; source is always engine/aga in this repository');e.add_argument('--out',type=Path,required=True);e.add_argument('--sdk',type=Path,required=True);e.add_argument('--vasm',type=Path,help='68000 preflight assembler; defaults to the SDK vasm')
    add_jobs(e)
    e.add_argument('--allow-compiler-warnings',action='store_true',help='Local experiments only: do not fail the build on compiler warnings')
    e.add_argument('--heap-mb',type=int,metavar='N',help="Game heap (Quake's Hunk) in MiB, exactly as asked (default: the engine source's AMIWIND_HEAP_MB); above the measured safe size one warning, recorded in engine-build.json and printed by the boot check")
    luma=e.add_mutually_exclusive_group()
    luma.add_argument('--disallow-luma-controls','--no-luma-controls',dest='debug_luma',action='store_false',help='Compile out brightness settings, scaling and menu; retain explanatory console messages')
    luma.add_argument('--interior-brightness','--debug-luma',dest='debug_luma',action='store_true',help='Enable brightness controls (the default); legacy aliases retained')
    e.set_defaults(debug_luma=True)
    i=sub.add_parser('image')
    from hidden_surface_build import add_options as add_hidden_surface_options
    add_hidden_surface_options(i)
    from exterior_sky_build import add_options as add_exterior_sky_options
    add_exterior_sky_options(i)
    i.add_argument('--kickstart-file',type=Path,help='Optional owned ROM for generated local emulator configurations; never bundled or downloaded')
    i.add_argument('--sdk',type=Path,required=True,help='AmigaPorts SDK used to compile the exact target ABI heap profile')
    i.add_argument('--map-budget-policy', choices=['strict', 'warning'], default='strict', help='Explicit private warning policy for modeled reserve allowance only; runtime allocation ceiling and all other gates stay unchanged')
    i.add_argument('--allow-known-actor-ground-findings', type=Path, help='PRIVATE TEST ONLY: accept an exact previously reviewed contact audit; strict production gate remains failed')
    i.add_argument('--accept-known-stair-findings', action='append', default=[], metavar='ID', help='PRIVATE -devN TESTS ONLY: the stair gate records the failures of this known finding (tracker ID, config/known-stair-findings.json) as accepted; refused for rc and final')
    i.add_argument('--data-files',type=Path,required=True,help='Owned original game assets')
    gallery_choice=i.add_mutually_exclusive_group(required=True)
    gallery_choice.add_argument('--gallery',type=Path,help='Verified NPC gallery from build_gallery.py; normal default')
    gallery_choice.add_argument('--no-npc-gallery',action='store_true',help='DEBUGGING ONLY: omit inspection gallery, never required game NPCs; gallery commands in game (dbg npcgallery etc.) print a built-without-the-NPC-gallery notice')
    i.add_argument('--live-logs',action='store_true',help='BENCHMARK/DIAGNOSTIC IMAGES: write the engine diagnostic logs (walk-profile.csv, frame-stalls.csv, heap-audit.log, ...) as they happen (aw_logs_live 1), as before BOOT-VOLUME-NOT-VALIDATED-33; default keeps them in memory until Exit game or dbg savelogs')
    i.add_argument('--menu-logo',choices=['gold','legacy'],default='gold',help='Menu logo method: gold (default, name only on the palette gold ramp) or legacy (previous wordmark, whole-palette nearest colours; comparison only)')
    i.add_argument('--intro-captions',type=Path,help='Private JSON title cards; first card becomes a switchable opening overlay')
    i.add_argument('--seyda-recorded',type=Path,help='Recorded-stage exception BUILD-SEYDA-REGEN-30: owner-provided recorded Seyda Neen maps (tools/recorded_stage.py), kept byte for byte by every later pass')
    i.add_argument('--canonical-land-source',type=Path,help='World-survey terrain-source.npz (survey_vvardenfell.py); required while Seyda terrain culling is enabled')
    i.add_argument('--world-terrain',type=Path,help='Complete validated refined terrain receipt and runtime directory, staged before scenery')
    i.add_argument('--world-scenery',type=Path,help='Complete validated full-world rock and giant-mushroom overlay directory; required except with --miniwind')
    i.add_argument('--miniwind',action='store_true',help='AmiWind "MiniWind" Playtester Build (tools/miniwind.py; tools/build.py --miniwind): a PARTIAL-AREA test image of Balmora on CHIM; private -devN versions only')
    i.add_argument('--miniwind-features',help='With --miniwind: the boot notice feature line tools/build.py generated from its stage plan ("FEATURES ONLY: ...")')
    i.add_argument('--miniwind-description',help='With --miniwind: optional "Scene:" line of the startup screen')
    i.add_argument('--miniwind-scope',choices=('full','exterior'),help='With --miniwind: full (default; Balmora exterior and interiors) or exterior (the Balmora exterior only; implies --no-npc-gallery)')
    i.add_argument('--world-flora',type=Path,help='Complete validated private world vegetation overlay; preserves rock/mushroom inputs')
    i.add_argument('--harvest',type=Path,help='Harvest source from harvest_build.py prepare (builder step harvest); the builder default')
    i.add_argument('--hand-catalog',type=Path,help='Per-race first-person hand catalogue from prepare_hand_catalog.py --runtime-palette; the builder default')
    i.add_argument('--chim-world',type=Path,help='CHIM world (tools/chim_build.py output: chim/, chim-receipt.json, '
                   'chim-validate.json, chim-stats.json), added as one more world volume; tools/build.py --builder chim')
    i.add_argument('--town-flora-source-index',type=Path,help='Exact original Seyda scenery reference bindings for flora installation')
    i.add_argument('--town-flora-scene-report',type=Path,help='Original alias conversion model mapping; required with --world-flora')
    i.add_argument('--balmora-cache',type=Path,help='Complete owned Balmora preparation cache for measured layout repair before final actor/heap audits')
    i.add_argument('--town-scenery',type=Path,help='Seyda Neen scenery (prepare_scenery.py output) for the night window table; defaults to the directory of --town-flora-source-index')
    i.add_argument('--balmora-scenery',type=Path,help='Balmora scenery (the Balmora cache scenery/) for the night window table; defaults to --balmora-cache/scenery')
    add_vis_option(i)
    add_jobs(i)
    i.add_argument('--bootcheck',type=Path,help='Defaults to AmiWindCheck beside the engine binary')
    i.add_argument('--amiga-libs',type=Path,help='Optional folder from your own Workbench/accelerator installation; '
                   'its 68040.library/68060.library (in DIR or DIR/LIBS) go into LIBS: and are opened at boot. '
                   'See docs/FPU_SUPPORT_LIBRARY.md')
    i.add_argument('--amiga-libs-policy',choices=known_inputs.POLICIES,default='warn',
                   help='warn (default): unknown builds used with a warning, invalid files not used; '
                   'fail: an invalid file stops the build; require-known: only known builds (docs/KNOWN_INPUTS.md)')
    i.add_argument('--entity-baseline',type=Path,help="Previous build's entity-tracker.json; placements lost against it stop the build")
    i.add_argument('--accept-entity-loss',help='Recorded reason that makes an intended entity loss pass the --entity-baseline gate')
    for name in ['scene','media','engine','out','qcc','qbsp','vis','light','xdftool','rdbtool']:i.add_argument('--'+name,type=Path,required=True)
    i.add_argument('--music',type=Path,help='Converted soundtrack (prepare_music.py); required unless --exclude music')
    i.add_argument('--payload-preflight-only',action='store_true',help='Read only: run the payload preflight of the image step (tools/payload_preflight.py) on the already staged payload in --out and stop')
    i.add_argument('--exclude',metavar='GROUP[,GROUP...]',
                   help='DEBUGGING ONLY (quick test builds, -devN only): content groups the builder left out '
                        '(tools/build_exclusions.py); written to id1/excluded-content.txt for the game')
    for parser in (e,i):
        parser.add_argument('--hands',choices=['3d','sprites'],default='3d',help='Compile-time first-person renderer; retain both conversion paths')
        parser.add_argument('--world-coverage',type=Path,help='Optional normalized world coverage evidence bound to this exact build; absent evidence is reported as unknown')
    import world_estimate
    w=sub.add_parser('estimate',help='Estimate every world map from your own Morrowind files (docs/WORLD_ESTIMATE.md)')
    world_estimate.add_estimate_options(w)
    c=sub.add_parser('estimate-calibrate',help='Refit the world estimate from maps converted by estimate --sample-convert')
    world_estimate.add_calibrate_options(c)
    import asset_census
    a=sub.add_parser('census',help='Asset census for the world streamer from your own Morrowind files (docs/ASSET_CENSUS.md)')
    asset_census.add_census_options(a)
    args=p.parse_args()
    import build_profile;build_profile.instrument('build_aga '+args.action)  # sub-stage timers (docs/BUILD_PROFILE.md)
    if args.action=='census':
        if args.jobs==0:
            from build_jobs import resolve_jobs
            args.jobs=resolve_jobs(None)
        try:return asset_census.census(args)
        except (OSError,ValueError) as exc:p.exit(1,f'Error: {exc}\n')
    if args.action in ('estimate','estimate-calibrate'):
        args=world_estimate.resolve(args)
        try:return (world_estimate.estimate if args.action=='estimate' else world_estimate.calibrate)(args)
        except (OSError,ValueError,subprocess.CalledProcessError) as exc:p.exit(1,f'Error: {exc}\n')
    # Resolve executables before subprocess cwd changes.
    for name in ['qcc','qbsp','vis','light','xdftool','rdbtool','engine','bootcheck']:
        if getattr(args,name,None) is not None:setattr(args,name,getattr(args,name).resolve())
    try:(engine if args.action=='engine' else image)(args)
    except (OSError,ValueError,subprocess.CalledProcessError) as exc:p.exit(1,f'Error: {exc}\n')
if __name__=='__main__':raise SystemExit(main())
