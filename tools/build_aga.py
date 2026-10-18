#!/usr/bin/env python3
"""Build the GPLv2 AGA runtime and a maintainer-only boot image.

CAPACITY FIRST: before starting the build, verify enough usable storage for ALL
required content, conversion intermediates, staging copies, temporary images,
readback verification and a margin. Include filesystem/quota limits and shared
RAM limits for memory-backed scratch. If capacity is insufficient, arrange it
before expensive work; never omit NPC models or the gallery to make a build fit.

All NPCs must be included and loadable by the engine for the game to be complete.
NPC gallery creation MUST NOT be skipped except for exceptional, explicitly
requested debugging purposes. Build time and disk usage are not reasons to omit it.

Normal builds and recovery MUST include the gallery; missing input/model/catalogue
content is an error, never an automatic opt-out. Only the maintainer's explicit
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
--no-npc-gallery support is only a mechanism for a maintainer-approved exceptional
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
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from mwad.paths import copy_tree, ensure_external
from prepare_music import playlists, unpack_stream
from check_aga_binary import check_binary
import check_fpu_unimplemented
from amiga_fs import check_image, check_payload_names, check_payload_host_paths
from project_version import VERSION, check_native_versions, require_private_test_version
from build_jobs import add_jobs, resolve_jobs
from build_host import executable_path, make_python_assignment
from vis_options import add_vis_option
import engine_profile
import fpu_support
import known_inputs
import camera_marks
from fpu_support import LOADER as FPU_LOADER, SELECTOR as CPU_SELECTOR, ENGINE_060

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
    'src/aw_mappath.c', 'src/aw_mappath.h',
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

    The temporary pre-CHIM heap bypass (config/heap-bypass.json, maintainer
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
    # camera-marks.txt: the public camera marks of dbg cam recall (docs/CAMERA_MARKS.md), checked as the engine reads them.
    files = [('debug-commands.txt', b'AWDC1'), ('shroompicker.txt', b'AWSP1'), ('camera-marks.txt', b'AWCM1')]
    limits = {'debug-commands.txt': 65536, 'camera-marks.txt': 16384}
    payloads = []
    for name, magic in files:
        raw = (ROOT/'config'/name).read_bytes()
        if not raw or len(raw) > limits.get(name, 4096):
            raise ValueError(f'Invalid debug catalogue size: {name}')
        if raw.splitlines()[0] != magic:
            raise ValueError(f'Invalid debug catalogue header: {name}')
        if name == 'camera-marks.txt':
            try:
                camera_marks.parse(raw, name)
            except camera_marks.MarkError as error:
                raise ValueError(f'Invalid camera marks: {error}') from None
        payloads.append((name, raw))
    for name, raw in payloads:
        (Path(id1)/name).write_bytes(raw)
    return {name: {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
            for name, raw in payloads}


LIVE_LOGS_LINE = b'aw_logs_live 1\n'
DEBUG_TORCH_NAME = 'Debug torch (test only)'


def debug_torch_record(id1):
    """The debug torch switch as staged (aw_debug_torch in default-game.cfg, config/game.cfg: 1 until the
    final game). The build receipt (build.json "debug_torch") and the image step's log say it."""
    value = None
    path = Path(id1)/'default-game.cfg'
    for line in (path.read_text(encoding='utf-8').splitlines() if path.is_file() else []):
        words = line.split('//')[0].split()
        if len(words) == 2 and words[0] == 'aw_debug_torch':
            value = words[1]
    on = value not in (None, '0')
    return {'on': on, 'item': DEBUG_TORCH_NAME, 'config': 'id1/default-game.cfg',
            'line': 'aw_debug_torch ' + (value or '0 (absent)'),
            'note': ('given once at the census exit, never burns out (test only, preview builds)' if on
                     else 'not given')}


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


def startup_config(config, draw_distance=540):
    """Configure controls first; quake.rc selects the named start after autoexec.
    draw_distance: the starting fog/draw distance (540; a DEBUG ONLY MiniWind image states a closer one)."""
    config=re.sub(r'(?m)^r_max(?:surfs|edges) [^\n]*\n?', '', config)
    config=re.sub(r'(?m)^aw_drawdistance [^\n]*\n?', '', config)
    config=re.sub(r'(?m)^bind "?[123]"? "aw_drawdistance (?:450|540|700|1000)"\n?', "", config)
    config=config.replace('bind ESCAPE quit','bind ESCAPE togglemenu').replace('r_drawviewmodel 0','r_drawviewmodel 1')
    config,count=re.subn(r'(?m)^map (?:seyda|prison)\s*$',
        'r_maxsurfs 12288\nr_maxedges 24576\nshowram 0\nbind MOUSE1 +attack\nbind F10 toggleconsole\nbind e +aw_use\nbind f "impulse 202"\nbind q +movedown',config)
    if count!=1:raise ValueError('Expected exactly one startup map in the converted default.cfg')
    config=re.sub(r'(?m)^(?:bind |unbindall)[^\n]*\n?', '', config)
    return 'exec keymaps-default.cfg\naw_drawdistance %d\n' % int(draw_distance)+config.rstrip()+'\n'

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


def check_engine_fpu(binary,map_path,sdk,out,engine_cpu='68040'):
    """ENGINE-FPU-UNIMPL-31: fail when engine code can reach an instruction its target CPU does not
    implement, outside that CPU's allowlist: the 68040's unimplemented FPU instructions
    (tools/fpu-unimplemented-allowlist.json), or for the 68060-targeted build (--engine-cpu 68060,
    docs/68060.md) the 68060's set (tools/fpu-unimplemented-allowlist-68060.json). The full result goes
    to out/fpu-unimplemented.json, a summary into engine-build.json. The 68040 build also records, as
    information, the 68060 traps it has (out/fpu-unimplemented-68060.json, ENGINE-060-FSCC-41)."""
    objdump=executable_path(Path(sdk).resolve()/'bin/m68k-amigaos-objdump')
    disassembly=subprocess.run([str(objdump),'-d','-r','-m','m68k:68040',str(binary)],check=True,capture_output=True,text=True).stdout
    map_text=Path(map_path).read_text(encoding='utf-8',errors='replace')
    allowlist=check_fpu_unimplemented.allowlist_path(engine_cpu)
    result=check_fpu_unimplemented.check(disassembly,map_text,json.loads(allowlist.read_text(encoding='utf-8')),engine_cpu)
    (out/'fpu-unimplemented.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    if not result['passed']:
        raise SystemExit(f'Engine code reaches {engine_cpu}-unimplemented instructions: '+'; '.join(
            ' -> '.join(row['path']) for row in result['engine_failures'][:10])+' (see fpu-unimplemented.json)')
    summary={'passed':True,'cpu':engine_cpu,'allowlist':allowlist.name,
             'unimplemented_instructions_in_binary':result['unimplemented_instructions'],
             'library_functions':sorted(result['functions_with_unimplemented']),'allowlist_unused':result['allowlist_unused']}
    if engine_cpu=='68060':
        summary['trap_kinds']=result['trap_kinds']
    else:
        info=check_fpu_unimplemented.check(disassembly,map_text,{'allowed':[]},'68060')
        (out/'fpu-unimplemented-68060.json').write_text(json.dumps(info,indent=2)+'\n',encoding='utf-8',newline='\n')
        summary['traps_on_68060']={'trap_kinds':info['trap_kinds'],
            'engine_functions':sum(1 for row in info['functions_by_kind'].values() if row['engine']),
            'report':'fpu-unimplemented-68060.json'}
    return summary


def engine_060_files(engine_binary,engine_record):
    """(AmiWind060, AmiWindCPU) beside the engine binary, checked against the engine receipt; None for an engine
    stage without them (older stages, the 68020 build, an --engine-cpu 68060 main build)."""
    row=engine_record.get('engine_68060')
    if not row:return None
    folder=Path(engine_binary).parent
    pair=(folder/ENGINE_060,folder/CPU_SELECTOR)
    if not all(path.is_file() for path in pair) or digest(pair[0])!=row['binary_sha256'] or digest(pair[1])!=row['selector_sha256']:
        raise ValueError('AmiWind060/AmiWindCPU do not match the engine build receipt; rebuild the engine')
    for path in pair:check_binary(path.read_bytes())
    return pair


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
    # Experimental engine switches (docs/EXPERIMENTAL_FLAGS.md), off by default: only an asked one changes the
    # make command line (EXTRA_DEFINES), so the default engine command and binary stay the same.
    experiments=sorted(set(getattr(args,'engine_experiment',None) or []))
    # The coordinate range (tools/coord_range.py): wide is the engine source's default, narrow adds its define.
    import coord_range
    coords=coord_range.current(getattr(args,'coord_range',None) or coord_range.DEFAULT)
    if coords=='narrow' and 'widecoord' in experiments:
        raise SystemExit('--coord-range narrow conflicts with --engine-experiment widecoord')
    defines=' '.join([ENGINE_EXPERIMENTS[name] for name in experiments]+
                     ([coord_range.RANGES[coords]['define']] if coord_range.RANGES[coords]['define'] else []))
    if experiments:
        print('EXPERIMENTAL engine switches: '+', '.join(experiments)+' ('+defines+')',flush=True)
    print(f"Coordinate range: {coords} (bound {coord_range.RANGES[coords]['bound']}, "
          f"{coord_range.RANGES[coords]['bytes']} bytes per coordinate, protocol {coord_range.RANGES[coords]['protocol']})",flush=True)
    # The engine profile (docs/ENGINE_PROFILES.md): c = the C paths at -O1, the make command unchanged.
    profile=engine_profile.from_args(args,args.cpu)
    print('Engine profile: '+engine_profile.short(profile),flush=True)
    binary,fpu_check=compile_engine(args,tree,env,jobs,heap,debug_luma,profile,out)
    profile_checks=(check_other_profiles(args,out,env,jobs,heap,debug_luma,profile,digest(binary))
                    if getattr(args,'check_profiles',False) else None)
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
    engine_profile.write_boot_include(tree/'build/version',profile)
    run([vasm,'-m68000','-Fhunkexe','-kick1hunks','-nosym','-I',ndk,'-I',tree/'build/version','-I',tree/'boot','-o',checker,tree/'boot/bootcheck.asm'])
    check_binary(checker.read_bytes())
    # AmiWindFPU opens the user's own FPU support library at boot (--amiga-libs).
    loader=tree/'build'/FPU_LOADER
    run([vasm,'-m68000','-Fhunkexe','-kick1hunks','-nosym','-I',ndk,'-I',tree/'boot','-o',loader,tree/'boot/fpulib.asm'])
    check_binary(loader.read_bytes())
    # The 68060 engine (docs/68060.md): the 68040 build stays the default and the baseline; the game disk also
    # carries AmiWind060 (the same source for the 68060) and AmiWindCPU, which picks it at boot on a 68060.
    engine060=None
    if args.cpu=='68040' and engine_profile.engine_cpu(profile)=='68040':
        selector=tree/'build'/CPU_SELECTOR
        run([vasm,'-m68000','-Fhunkexe','-kick1hunks','-nosym','-I',ndk,'-I',tree/'boot','-o',selector,tree/'boot/cpusel.asm'])
        check_binary(selector.read_bytes())
        engine060=build_engine_060(args,out,env,jobs,heap,debug_luma,profile,tree/'build'/ENGINE_060)
        engine060['selector_sha256']=digest(selector)
    (out/'engine-build.json').write_text(json.dumps({'version':VERSION,'hands':args.hands,'debug_luma':debug_luma,'compiler_jobs':jobs,'source_kind':'repository engine/aga','source_sha256':source_hashes,'upstream_commit':UPSTREAM_COMMIT,'baseline_upstream_archive_sha256':UPSTREAM_SHA256,'binary':str(binary),'binary_sha256':digest(binary),'bootcheck_sha256':digest(checker),'fpu_loader_sha256':digest(loader),'hardware_benchmark_sha256':digest(out/'awbench'),'fpu_unimplemented_check':fpu_check,
        'engine_profile':profile,'engine_profile_checks':profile_checks,'assembler':assembler_identity(vasm),
        **({'engine_68060':engine060} if engine060 else {}),
        'heap_mb':heap['heap_mb'],'heap_mb_selected_by':heap['selected_by'],'heap_default_mb':heap['heap_default_mb'],
        'heap_safe_mb':heap['heap_safe_mb'],'heap_warning':heap['heap_warning'],
        'coord_range':coords,'protocol':coord_range.RANGES[coords]['protocol'],
        **({'engine_experiments':experiments} if experiments else {})},indent=2)+'\n', newline='\n')
    print(binary)
    write_world_coverage(out,'engine',getattr(args,'world_coverage',None))

def assembler_identity(vasm):
    """The SDK's vasmm68k_mot (boot check, FPU loader and the upstream profile's assembly): its banner
    lines and SHA-256 for the engine receipt."""
    try:
        result=subprocess.run([str(vasm),'-v'],capture_output=True,text=True,errors='replace',timeout=30)
    except OSError as exc:
        return {'name':Path(vasm).name,'version':None,'sha256':None,'error':str(exc)}
    banner=[line.strip() for line in (result.stdout+result.stderr).splitlines() if line.strip().startswith('vasm')]
    return {'name':Path(vasm).name,'version':banner,'sha256':digest(vasm) if Path(vasm).is_file() else None}

def engine_experiment_variables(args):
    """make EXTRA_DEFINES for the asked --engine-experiment switches and the coordinate range (tools/coord_range.py:
    wide is the engine source's default, narrow adds -DAW_COORD_NARROW); none: the make command is unchanged."""
    import coord_range
    experiments=sorted(set(getattr(args,'engine_experiment',None) or []))
    narrow=coord_range.RANGES[coord_range.current(getattr(args,'coord_range',None) or coord_range.DEFAULT)]['define']
    defines=[ENGINE_EXPERIMENTS[name] for name in experiments]+([narrow] if narrow else [])
    return [f'EXTRA_DEFINES={" ".join(defines)}'] if defines else []

def _frame_heap_cache():
    """The image pass cache's folder for the CHIM frame-map heap reports (tools/pass_cache.py), or None when off."""
    from pass_cache import folder
    root = folder()
    return root / 'chim-frame-heap' if root else None

def compile_engine(args,tree,env,jobs,heap,debug_luma,profile,out,variables=None):
    """make the engine in TREE for the engine PROFILE: warning-free (compiler and assembler), binary
    structure, link map (exactly the selected assembly objects) and, for the 68040, the FPU check.
    VARIABLES replaces the profile's make variables (the c-explicit check)."""
    output=run(['make','-B','--output-sync=target',f'-j{jobs}',('nofpu' if args.cpu=='68020' else 'fpu'),make_python_assignment(),
                *([f'HEAP_MB={heap["heap_mb"]}'] if getattr(args,'heap_mb',None) is not None else []),'CC=m68k-amigaos-gcc'+CC_FLAGS+' -DAMIWIND_SPRITE_HANDS='+('1' if args.hands=='sprites' else '0')+(' -DAMIWIND_DEBUG_LUMA=1' if debug_luma else ''),'NDK_INC='+str(args.sdk.resolve()/'m68k-amigaos/ndk-include'),
                *(engine_profile.make_variables(profile) if variables is None else variables),
                *engine_experiment_variables(args)],tree,env,capture=True)
    # vasm reports "warning NNN in line ..." (the upstream assembly units): counted like compiler warnings.
    warnings=[line for line in str(output or '').splitlines() if ': warning: ' in line or re.match(r'\s*warning \d+',line)]
    if warnings and not getattr(args,'allow_compiler_warnings',False):
        raise SystemExit(f'Engine build ({engine_profile.short(profile)}) produced {len(warnings)} compiler warning(s); it must be warning-free. '
                         'Fix them, or pass --allow-compiler-warnings for a local experiment only.')
    binary=tree/('build/AmiQuakeGCC-NoFPU' if args.cpu=='68020' else 'build/AmiQuakeGCC')
    check_binary(binary.read_bytes())
    link_map=tree/'build/AmiQuakeGCC.map'
    if args.cpu=='68040' and link_map.is_file():  # a missing map fails check_engine_fpu below
        problems=engine_profile.check_link_map(link_map.read_text(encoding='utf-8',errors='replace'),profile)
        if problems:raise SystemExit('Engine link map does not match the engine profile: '+'; '.join(problems))
    fpu_check=(check_engine_fpu(binary,tree/'build/AmiQuakeGCC.map',args.sdk,out,engine_profile.engine_cpu(profile))
               if args.cpu=='68040' else None)
    return binary,fpu_check

def build_engine_060(args,out,env,jobs,heap,debug_luma,profile,target):
    """AmiWind060: the main build's profile compiled for the 68060 (--engine-cpu 68060: -m68060 -mhard-float,
    its own FPU check) in a separate tree; the binary is copied to TARGET. Returns its receipt."""
    record=engine_profile.resolve(profile['profile'],','.join(profile['asm']) or 'none',profile['opt'],args.cpu,'68060')
    sub=out/'engine-68060';sub.mkdir()
    sub_tree,_=stage_runtime(sub)
    tick=time.monotonic()
    print('Engine for the 68060 (AmiWind060): '+engine_profile.short(record),flush=True)
    binary,fpu_check=compile_engine(args,sub_tree,env,jobs,heap,debug_luma,record,sub)
    shutil.copyfile(binary,target)
    row={'file':target.name,'profile':engine_profile.short(record),'engine_profile':record,'binary_sha256':digest(target),
         'bytes':target.stat().st_size,'fpu_unimplemented_check':fpu_check,'seconds':round(time.monotonic()-tick,1)}
    print(f"Engine for the 68060: {row['bytes']:,} bytes, SHA-256 {row['binary_sha256']} ({row['seconds']} s)",flush=True)
    shutil.rmtree(sub/RUNTIME_BUILD_DIR,ignore_errors=True)
    return row


def check_other_profiles(args,out,env,jobs,heap,debug_luma,profile,binary_sha256):
    """--check-profiles (the gate's engine step): build every other engine profile and the -O2 experiment
    from the same source, each warning-free, link-map- and FPU-checked, so no path rots unnoticed. For a c build
    also c once more with its make variables spelled out (ENGINE_ASM empty, ENGINE_OPT=o1): it must
    give the same binary SHA-256 as the plain c build (the profile machinery adds nothing to c)."""
    variants=[(name,engine_profile.resolve(name,cpu=args.cpu,engine_cpu=engine_profile.engine_cpu(profile)),None)
              for name in engine_profile.PROFILES if name!=profile['label']]
    # and the -O2 experiment (upstream's assembly with every C file at -O2 except mathlib.c and in_amiga.c), so
    # an -O2-only warning or FPU instruction is found by the gate too
    variants.append(('upstream-o2',engine_profile.resolve('upstream',None,'o2',cpu=args.cpu,engine_cpu=engine_profile.engine_cpu(profile)),None))
    # (the 68060 engine of the same profile is built by every 68040 engine build: build_engine_060)
    if engine_profile.is_default(profile):
        variants.append(('c-explicit',profile,['ENGINE_ASM=','ENGINE_OPT=o1']))
    results=[]
    for name,record,variables in variants:
        sub=out/('profile-check-'+name);sub.mkdir()
        tree,_=stage_runtime(sub)
        tick=time.monotonic()
        binary,fpu_check=compile_engine(args,tree,env,jobs,heap,debug_luma,record,sub,variables)
        sha=digest(binary)
        row={'variant':name,'profile':engine_profile.short(record),'binary_sha256':sha,
             'seconds':round(time.monotonic()-tick,1),'warnings':0,'fpu_unimplemented_check':fpu_check}
        if name=='c-explicit':
            row['same_as_default_build']=sha==binary_sha256
            if sha!=binary_sha256:
                raise SystemExit('Engine profile c with ENGINE_ASM= ENGINE_OPT=o1 spelled out built a different binary '
                                 f'({sha}) than the plain c build ({binary_sha256}): the profile machinery changes the c build')
        print(f'Engine profile check {name}: {row["profile"]} SHA-256 {sha} ({row["seconds"]} s)',flush=True)
        results.append(row)
        shutil.rmtree(sub/RUNTIME_BUILD_DIR,ignore_errors=True)
    return results

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
    # CHIM region cells (docs/BUILD_MANIFEST.md step 2): no map was made for them; their rows carry no map
    chim = [r['name'] for r in regions if r.get('chim_region')]
    routing_only = [r['name'] for r in regions if r.get('routing_only')]
    not_made = set(chim + routing_only)
    for name in not_made:
        if (id1 / 'maps' / f'{name}.bsp').exists() or (overlay / name / 'scene.bsp').exists():
            raise ValueError('A legacy map of a CHIM region cell is staged: ' + name)
    made = [name for name in expected_names if name not in not_made]
    retained = hash_existing([id1 / 'maps' / f'{name}.bsp' for name in made], jobs)
    overlays = hash_existing([overlay / name / 'scene.bsp' for name in made], jobs)
    for region, source_sha, baked_sha in zip([r for r in regions if r['name'] not in not_made], retained, overlays):
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
              'chim_region_maps_not_made': chim,
              'routing_only_maps_not_made': routing_only,
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
    """Harvest catalogues of special maps that run on CHIM in this image (the frame map maps/<name>-chim.chim
    or .bsp present, maps/<name>.bsp absent, <name> not a region of a CHIM town): the engine names a map's catalogue after
    the loaded map (harvest-<map>.txt), so the legacy catalogue would never load; it is left out of the
    image and the save fingerprint, and listed (CHIM-HARVEST-SPECIALS-33)."""
    from map_files import map_file
    root=Path(id1);regions=set()
    for table in sorted(root.glob('*-regions.txt')):
        regions.update(line.split()[0] for line in table.read_text(encoding='ascii').splitlines()[1:] if line.split())
    retired=[]
    for path in sorted(root.glob('harvest-*.txt')):
        name=path.name[len('harvest-'):-len('.txt')]
        if (map_file(root/'maps',name+'-chim').is_file() and not (root/'maps'/(name+'.bsp')).is_file()
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
    # Regions of towns that run on CHIM (maps/<town>-chim.chim or .bsp present): their region maps are gone from a
    # pure CHIM image, their catalogues stay and the engine loads them per region (CHIM-HARVEST-REMOVED-MAPS-33).
    from map_files import map_file
    chim_regions=set()
    for table in sorted(root.glob('*-regions.txt')):
        town=table.name[:-len('-regions.txt')]
        if map_file(root/'maps',town+'-chim').is_file():
            chim_regions.update(line.split()[0] for line in table.read_text(encoding='ascii').splitlines()[1:] if line.split())
    for path in sorted(root.glob('harvest-*.txt'),key=lambda item:item.name):
        match=re.fullmatch(r'harvest-([a-z0-9_]{1,24})\.txt',path.name)
        if not match or path.is_symlink() or not path.is_file():
            raise ValueError('Invalid harvest catalogue path: '+path.name)
        if (not map_file(root/'maps',match[1]).is_file() and 'maps/'+match[1]+'.bsp' not in removed
                and match[1] not in chim_regions):
            if map_file(root/'maps',match[1]+'-chim').is_file():
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


def write_content_fingerprint(id1, jobs=1, partial=False, removed=(), excluded=(), kept_extra=()):
    """Hash every bound asset (up to `jobs` hashing workers); fold in fixed order.

    partial: a MiniWind partial-area image (tools/miniwind.py) binds the maps it
    ships; the Seyda Neen maps and region table it leaves out are not required.
    True or 'full' is the full MiniWind scope; 'exterior' leaves the Balmora
    interiors out as well.
    removed: legacy town maps a pure CHIM image left out (id1-relative 'maps/x.bsp'); they are not
    required, and the CHIM frame maps of towns and special maps are bound instead (found by their
    "_chim_frame" key, tools/map_files.py; region frames are bound with the open-world maps).
    excluded: quick-test groups; with 'interiors' the room maps the build left out
    (every interior except the prison ship and the Census office) are not required.
    kept_extra: maps a MiniWind image keeps for its direct start (tools/miniwind.py start_maps)."""
    from build_parallel import hash_files
    fingerprint=hashlib.sha256()
    from area_config import SCENES
    seyda=Path(id1)/'seyda-regions.txt'
    balmora=Path(id1)/'balmora-regions.txt'
    if partial:
        import miniwind
        scope,town=(partial if isinstance(partial,tuple) else
                    (miniwind.DEFAULT_SCOPE if partial is True else partial,miniwind.TOWN))
    # a MiniWind of another town (--miniwind-town) holds no Balmora region table (BUILD-MINIWIND-BALMORA-ASSUMED-36)
    with_balmora=not partial or town=='balmora' or balmora.is_file()
    town_maps=((town_region_map_names(seyda,'sn') if seyda.is_file() or not partial else [])
               +(town_region_map_names(balmora,'bm') if with_balmora else []))
    scenes=[s for s in SCENES if not ('interiors' in excluded and s.get('interior') is True
            and s['map'] not in ('prison','census') and not (Path(id1)/'maps'/(s['map']+'.bsp')).is_file())]
    names=[*(f"maps/{s['map']}.bsp" for s in scenes), 'maps/intro_docks.bsp', 'maps/sncourt.bsp', 'seyda-regions.txt', *(['balmora-regions.txt'] if with_balmora else []), *town_maps, 'progs.dat', 'character/catalog.awc', 'world/map.awm', 'world/journal.awj', 'world/entries.dat', 'world/quests.awq', 'world/region-names.awn']
    if partial:
        kept,prefix=miniwind.kept_maps(scope=scope,town=town,extra=kept_extra)
        names=[name for name in names if name!='seyda-regions.txt' and
               not (name.startswith('maps/') and not miniwind.keep_map(name[5:-4],kept,prefix))]
    # Optional extra towns follow, so images without them keep their fingerprint.
    for town in staged_extra_towns(id1):
        names+=[town['regions'],'maps/'+town['name']+'.bsp',*town_region_map_names(Path(id1)/town['regions'],town['prefix'])]
    names+=['maps/'+name+'.bsp' for name in staged_town_interiors(id1)]
    if removed:
        removed=set(removed)
        names=[name for name in names if name not in removed]
        from map_files import is_chim_frame, map_files
        names+=['maps/'+p.name for p in map_files(Path(id1)/'maps')
                if not re.fullmatch(r'vf[0-9]{4}', p.stem) and is_chim_frame(p)]
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
        from map_files import map_rel
        from chim.frame_map import alias_rows
        # a divided CHIM region cell's alias rows have no map (the directory bytes above bind them)
        aliases=alias_rows(raw)
        world=[map_rel(id1,f'vf{index:04d}') for index in range(struct.unpack_from('<I',raw,4)[0])
               if f'vf{index:04d}' not in aliases or (Path(id1)/map_rel(id1,f'vf{index:04d}')).is_file()]
        # Routing rows retain stable indices after a higher-priority town
        # replaces their entire core. Only explicitly retired payload paths
        # may be absent; an undeclared missing map must still fail this gate.
        world=[name for name in world if name not in removed]
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
        ('--exclude ' + ','.join(excluded_groups(args)), bool(excluded_groups(args))),
        ('--direct-start', getattr(args, 'direct_start', None)),
        ('--skip-census', getattr(args, 'skip_census', None)),
        ('--quick-character', getattr(args, 'quick_character', None))) if used]


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


def chim_native_towns(args):
    """The towns of --chim-town outputs (tools/chim_town.py): on CHIM with no legacy region maps."""
    towns=[]
    for path in getattr(args,'chim_town',None) or []:
        towns.append(json.loads((Path(path)/'entities.json').read_text(encoding='utf-8'))['town'])
    return towns


def flora_image_inputs(args):
    """The inputs a complete flora image needs. A CHIM-native Balmora holds its town flora in the CHIM world, so
    the legacy Balmora cache is not one of them (BUILD-IMAGE-NATIVE-BALMORA-CACHE-36)."""
    fields=['town_flora_source_index','town_flora_scene_report']
    if 'balmora' not in chim_native_towns(args):
        fields.append('balmora_cache')
    return fields


def chim_town_rows(args):
    """{town: frame-map entity rows} of the --chim-town outputs, with the shared exterior sky keys the
    sky pass gives every exterior map's worldspawn (exterior_sky_build.transform)."""
    from exterior_sky_build import SHARED_SKY_PATH
    rows={}
    for path in getattr(args,'chim_town',None) or []:
        record=json.loads((Path(path)/'entities.json').read_text(encoding='utf-8'))
        town=[dict(e) for e in record['rows']]
        town[0]['_aw_sky_mode']='exterior'
        town[0]['_aw_sky_asset']=SHARED_SKY_PATH
        rows[record['town']]=town
    return rows


def chim_town_specials(args):
    """({special map: frame-map entity rows}, {town or special map: activated object rows}) of the --chim-town
    outputs: a CHIM-native Seyda Neen's special frame maps (the intro docks, the Census courtyard) and the objects
    the engine activates as edicts, both made from the game data (tools/chim_town.py prepare_seyda); the specials'
    worldspawns get the shared exterior sky keys as the towns' (chim_town_rows)."""
    from exterior_sky_build import SHARED_SKY_PATH
    rows, activated = {}, {}
    for path in getattr(args,'chim_town',None) or []:
        record=json.loads((Path(path)/'entities.json').read_text(encoding='utf-8'))
        if record.get('activated') is not None:
            activated[record['town']]=record['activated']
        for name, special in (record.get('specials') or {}).items():
            special_rows=[dict(e) for e in special['rows']]
            special_rows[0]['_aw_sky_mode']='exterior'
            special_rows[0]['_aw_sky_asset']=SHARED_SKY_PATH
            rows[name]=special_rows
            activated[name]=special['activated']
    return rows, activated


def town_source_cell(town):
    """The game cell of a town's CHIM frame: its converter settings' source_cell, Seyda Neen's from chim.seyda."""
    if town == 'seyda':
        from chim.seyda import source_cell
        return tuple(source_cell())
    from town_config import load_settings
    return tuple(load_settings(town)['source_cell'])


def chim_town_grounding(args):
    """{town: the town stage's actor fit results on its CHIM frame} (entities.json 'grounding') of the
    --chim-town outputs, for the actor placement gate (BUILD-ACTOR-GATE-CHIM-FRAMES-36)."""
    out={}
    for path in getattr(args,'chim_town',None) or []:
        record=json.loads((Path(path)/'entities.json').read_text(encoding='utf-8'))
        out[record['town']]=list(record.get('grounding') or [])
    return out


def empty_miniwind_actor_evidence(args, maps):
    """Prove no resident contact is expected; retain deferred creature spawns as missing coverage."""
    if not getattr(args, 'miniwind', False) or getattr(args, 'miniwind_scope', None) != 'exterior':
        return None
    town = getattr(args, 'miniwind_town', None)
    frames = chim_town_grounding(args)
    if not town or set(frames) != {town} or frames[town]:
        return None
    if any(p.stem != 'torchtest' for p in Path(maps).glob('*.bsp')):
        return None
    from mwad.audit import load_esm
    from mwad.paths import child_ci
    from town_config import load_settings
    from import_town import in_frame
    master = child_ci(args.data_files, 'Morrowind.esm')
    original = load_esm(master)
    settings = load_settings(town)
    deferred_spawns = []
    # Scan every exterior cell: actor ownership is by origin, including cross-cell placements.
    for cell, record in original['cells'].items():
        for ref in record['refs']:
            if ref.get('deleted'):
                continue
            obj = original['objects'].get(ref['id'].casefold())
            placed = dict(ref, cell=list(cell))
            if in_frame(placed, settings):
                if obj is None or obj['type'] in ('NPC_', 'CREA'):
                    return None
                if obj['type'] == 'LEVC':
                    # import_town.split_references defers these markers: no creature is instantiated.
                    # This is missing gameplay coverage, not a supported or contact-tested actor.
                    deferred_spawns.append({'reference': ref['number'], 'id': ref['id'],
                                            'position': ref['position'], 'status': 'unconverted creature spawn'})
    return {'scope': 'MiniWind exterior without ground residents; creature spawns remain unconverted', 'town': town,
            'source_master_sha256': hashlib.sha256(master.read_bytes()).hexdigest(),
            'source_resident_count': 0, 'deferred_creature_spawns': deferred_spawns, 'bounds': settings['bounds']}


def chim_town_placements(args, id1, world=None):
    """{'<town>-chim': reference numbers} for each --chim-town town: its CHIM world placements, its frame
    actors and its region harvest catalogues (the entity tracker counts them as the legacy region maps
    would have). world: the CHIM world already read (chim_world_once); without it each town reads it again."""
    if not getattr(args,'chim_town',None):
        return {}
    from chim.frame_map import chim_placements
    from entity_tracker import harvest_refs
    from town_config import runtime_towns
    out={}
    for town, rows in chim_town_rows(args).items():
        refs={int(e['aw_ref']) for e in rows if str(e.get('aw_ref','')).isdigit()}
        refs|=set(chim_placements(args.chim_world, town_source_cell(town), world=world))
        row=next(t for t in runtime_towns() if t['id']==town)
        for name in town_region_map_names(Path(id1)/row['regions'], row['prefix']):
            catalogue=Path(id1)/('harvest-'+Path(name).stem+'.txt')
            if catalogue.is_file():
                refs|=harvest_refs(catalogue.read_bytes())
        out[town+'-chim']=refs
    return out


def chim_region_placements(args, id1, world=None):
    """{'vfNNNN': reference numbers} of each CHIM region cell whose legacy map no stage made (docs/BUILD_MANIFEST.md
    step 2): the CHIM world's placements of its frame and the plants of the catalogue the harvest step wrote for its
    frame map (harvest-vfNNNN.txt, HARVEST-CHIM-REGION-LOSS-41), which the entity tracker counts as the cell's map
    would have. world: the CHIM world already read (chim_world_once)."""
    if not getattr(args, 'chim_world', None):
        return {}
    from chim.frame_map import chim_placements, load, region_map_names
    # one name per cell (a divided cell's alias rows are not counted again: CHIM-REGION-DIVIDED-CELLS-36)
    owned = {name: cell for name, cell in region_map_names(id1, args.chim_world, primary_only=True).items()
             if not (Path(id1)/'maps'/(name+'.bsp')).is_file()}
    if not owned:
        return {}
    from entity_tracker import harvest_refs
    world = world if world is not None else load(args.chim_world)
    out = {}
    for name, cell in sorted(owned.items()):
        refs = set(chim_placements(args.chim_world, cell, world=world))
        catalogue = Path(id1)/('harvest-%s.txt' % name)
        if catalogue.is_file():
            refs |= harvest_refs(catalogue.read_bytes())
        out[name] = refs
    return out


def never_built_maps(id1, towns, world_terrain=None):
    """id1-relative legacy exterior maps of CHIM towns built without them (their region tables name them;
    Seyda Neen's special scenes too: the intro docks and the Census courtyard)."""
    from town_config import runtime_towns
    from chim.frame_map import SPECIALS
    names=[]
    for town in runtime_towns():
        if town['id'] in towns:
            names.append('maps/'+town['name']+'.bsp')
            if town['id']=='seyda':
                names+=['maps/'+name+'.bsp' for name in SPECIALS]
            table=Path(id1)/town['regions']
            if table.is_file():
                names+=town_region_map_names(table,town['prefix'])
    if world_terrain:
        from exterior_plan import omitted_paths
        names += omitted_paths(world_terrain, id1)
    return names


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
    # CHIM region frames (tools/chim/regions.py, --chim-regions) are no towns: chim_region_frames lists them
    regions = chim_region_table(chim_world)
    if regions:
        ids = {f['id'] for f in regions['frames']}
        areas = [a for a in areas if a not in ids]
    return receipt, areas


def image_content_fingerprint(args, id1, jobs, removed_files, excluded):
    """Bind content and return validated omissions for the disk packer."""
    omitted = removed_files + never_built_maps(
        id1, chim_native_towns(args), getattr(args, 'exterior_terrain', None)
        or getattr(args, 'world_terrain', None))
    write_content_fingerprint(id1, jobs=jobs, partial=getattr(args, 'miniwind', False) and
                              ((getattr(args, 'miniwind_scope', None) or 'full', args.miniwind_town)
                               if getattr(args, 'miniwind_town', None) else
                               (getattr(args, 'miniwind_scope', None) or True)), removed=omitted,
                              excluded=excluded, kept_extra=mini_start_maps(args))
    return omitted


def chim_region_table(chim_world):
    """The CHIM world's ownership table of CHIM region frames (chim-regions.json, tools/chim/regions.py), or None."""
    from chim.regions import TABLE_FILE, read_table
    return read_table(Path(chim_world)/TABLE_FILE) if chim_world else None


def chim_world_once(chim_world, held):
    """The CHIM world read and checked ONCE for the whole image step (chim.frame_map.load, a timed phase): the
    entity tracker's placements, the frame maps and the frame-map heap gate all take this one copy (read only by
    them). HELD: a dict the image step keeps ({} at first); the world is read the first time and held there. Each
    of them used to read the whole world again: six reads of about 30 s each on one core in the dev2 image step
    (BUILD-IMAGE-REGION-MAPS-SERIAL-43). None without a CHIM world."""
    if not chim_world:
        return None
    if 'world' not in held:
        import build_profile
        from chim.frame_map import load
        with build_profile.phase('Image: CHIM world read', detail=str(Path(chim_world).name)) as timer:
            held['world'] = load(chim_world)
            timer.done('Image: CHIM world read: %d frames, %d models (read once for the image step; serial: one '
                       'pass over the world files, checked and held in this process for its readers)'
                       % (len(held['world']['frames']), len(held['world']['models'])))
    return held['world']


def chim_frame_maps(chim_world, id1, town_rows=None, jobs=1, hand_fields=None, special_rows=None, activated=None,
                    keep_catalogues=None, world=None):
    """Check a CHIM world's receipts and write its frame maps into id1: maps/<town>-chim.chim for each
    area (.bsp with chim_frame_ext bsp; tools/map_files.py; the engine loads it instead of the town's
    region maps when CHIM is on), and for Seyda Neen its special maps (format 0.5). Each is checked against the town's final legacy maps, which must
    still be in id1. The CHIM world is read and checked once for all of them (chim.frame_map.load); the
    region frame maps are made on the shared worker pool (jobs) and taken from the image pass cache when
    unchanged (BUILD-IMAGE-CHIM-MAPS-SERIAL-36). Every part is a timed phase (build_profile.phase).
    hand_fields: the open-world maps' hand fields (hand_metadata), for region frame maps made from the game data
    (chim.frame_map region_rows_mode, docs/BUILD_MANIFEST.md step 2); without them the legacy method is used.
    special_rows / activated: a CHIM-native Seyda Neen's special frame rows and the activated objects of its maps
    (chim_town_specials): those frame maps take them instead of legacy maps.
    keep_catalogues: {map name: SHA-256} of the harvest step's catalogues for the region frame maps (they stay with
    their frame map: chim.frame_map.install_region, HARVEST-CHIM-REGION-LOSS-41).
    world: the CHIM world already read (chim_world_once); without it it is read here.
    Returns {'areas', 'receipt', 'frame_maps', 'region_maps', 'region_cache'}."""
    import build_profile
    import progress_line
    chim_world = Path(chim_world)
    receipt, areas = chim_world_receipt(chim_world)
    # Written before the partition, so a refused entity stops the image here.
    from chim.frame_map import SPECIALS
    world = chim_world_once(chim_world, {'world': world} if world is not None else {})
    town_rows = town_rows or {}
    special_rows, activated = special_rows or {}, activated or {}
    specials = list(SPECIALS) if 'seyda' in areas else []
    # Each area's frame map, and Seyda Neen's special maps (the intro docks, the Census courtyard: further frame maps
    # of its frame, format 0.5, maps/intro_docks-chim.chim, maps/sncourt-chim.chim), on the shared worker pool: each
    # unit gets only its frame's part of the world (chim.frame_map.frame_subworld) and writes only its own map;
    # results in this order, the same bytes with any worker count (BUILD-IMAGE-REGION-MAPS-SERIAL-43).
    from build_parallel import ordered_map
    from chim.frame_map import frame_subworld, town_cell, town_unit
    units = [('town', area, town_rows.get(area)) for area in areas] +             [('special', name, special_rows.get(name)) for name in specials]
    town_workers = max(1, min(resolve_jobs(jobs), len(units) or 1))
    with build_profile.phase('Image: CHIM town frame maps', detail='%s; %d workers (one per map)'
                             % (', '.join(list(areas) + specials), town_workers),
                             total=len(units), unit='maps') as timer:
        tasks = [(kind, str(id1), name, str(chim_world),
                  frame_subworld(world, town_cell(name) if kind == 'town' else town_cell('seyda')),
                  [dict(e) for e in rows] if rows is not None else None,
                  activated.get(name) if rows is not None else None)
                 for kind, name, rows in units]
        frame_maps = []
        for (kind, name, _), record in zip(units, ordered_map(town_unit, tasks, town_workers)):
            frame_maps.append(record)
            timer.step(label=name)
            build_profile.progress(progress_line.line('Image: CHIM town frame maps', name, record['map'][5:],
                                                      (timer.count, timer.total, 'maps')))
        timer.done('Image: CHIM town frame maps: %d written on %d workers' % (len(frame_maps), town_workers))
    # CHIM region frames (EXPERIMENTAL, --chim-regions): each cell's open-world map is replaced in place by
    # its frame map (chim.frame_map.build_regions; the legacy file is recorded in 'replaced').
    region_maps, region_cache = [], None
    table = chim_region_table(chim_world)
    if table:
        from chim.frame_map import build_regions, region_cache as open_region_cache, region_rows_mode
        cache = open_region_cache()
        rows = region_rows_mode() if hand_fields is not None else 'legacy'
        workers = max(1, min(resolve_jobs(jobs), len(table['frames'])))
        with build_profile.phase('Image: CHIM region frame maps', detail='%d frames, %d workers, pass cache %s, rows '
                                 'from %s' % (len(table['frames']), workers, 'on' if cache is not None else 'off', rows),
                                 total=len(table['frames']), unit='maps') as timer:
            def progress(record, reused):
                timer.step(label=record['map'][5:])
                build_profile.progress(progress_line.line('Image: CHIM region frame maps', record['map'][5:],
                                                          'reused' if reused else 'made',
                                                          (timer.count, timer.total, 'maps')))
            region_maps, reused = build_regions(id1, table['frames'], chim_world, world=world, jobs=workers,
                                                cache=cache, progress=progress, rows=rows, hand_fields=hand_fields,
                                                keep_catalogues=keep_catalogues)
            region_cache = dict(cache.summary() if cache is not None else {'status': 'off'}, reused=reused,
                                made=len(region_maps) - reused, rows=rows)
            timer.done('Image: CHIM region frame maps: %d written (%d from the pass cache, %d made)'
                       % (len(region_maps), reused, len(region_maps) - reused))
        frame_maps += region_maps
    # Each frame map's far terrain (chim.far): maps/<frame map>.far beside it, like a Quake .lit file.
    with build_profile.phase('Image: CHIM far terrain', total=len(frame_maps), unit='maps') as timer:
        for record in frame_maps:
            record['far_terrain'] = chim_far_sidecar(chim_world, id1, record)
            timer.step()
        timer.done('Image: CHIM far terrain: %d sidecars' % sum(1 for r in frame_maps if r['far_terrain']))
    return {'areas': areas, 'receipt': receipt, 'frame_maps': frame_maps, 'region_maps': region_maps,
            'region_cache': region_cache}


def legacy_maps_summary(id1, removed_legacy):
    """Legacy maps of CHIM cells in an image: the map files the CHIM step removed (built, never shipped), those
    still in the payload as legacy maps (must be none: a CHIM frame map written under the legacy name, chim_frame_ext
    bsp, is a frame map), and the payload's maps by kind (CHIM frame maps, far terrain, open-world legacy maps,
    interiors and other maps)."""
    from map_files import is_chim_frame, is_map_name, map_stem
    maps = Path(id1)/'maps'
    removed = [row for row in removed_legacy or [] if row['file'].startswith('maps/')]
    shipped = sorted(row['file'] for row in removed
                     if (Path(id1)/row['file']).is_file() and not is_chim_frame(Path(id1)/row['file']))
    kinds = {}
    for path in sorted(maps.iterdir()) if maps.is_dir() else []:
        if not path.is_file():
            continue
        if path.suffix == '.far':
            kind = 'far terrain'
        elif not is_map_name(path.name):
            kind = 'other files'
        elif is_chim_frame(path):                       # by its key, whatever its extension (tools/map_files.py)
            kind = 'CHIM frame maps'
        elif re.fullmatch(r'vf[0-9]{4}', map_stem(path.name)):
            kind = 'open-world legacy maps'
        else:
            kind = 'interiors and other maps'
        row = kinds.setdefault(kind, {'files': 0, 'bytes': 0})
        row['files'] += 1
        row['bytes'] += path.stat().st_size
    removed_bytes = sum(row['bytes'] for row in removed)
    line = ('legacy maps of CHIM cells: %d built / %d shipped (%d bytes kept out of the image)'
            % (len(removed), len(shipped), removed_bytes))
    return {'built': len(removed), 'shipped': shipped, 'removed_bytes': removed_bytes,
            'payload_by_kind': dict(sorted(kinds.items())), 'line': line}


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
    from map_files import frame_ext
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
              'stats_sha256': digest(stats_path), 'frame_maps': frame_maps,
              'frame_map_extension': frame_ext(), 'region_frame_cache': frames.get('region_cache')}
    return entry, record


def miniwind_options(args):
    """None for a normal image; for --miniwind (tools/miniwind.py) the checked options:
    a private -devN version, the generated feature line and the optional description."""
    if not getattr(args, 'miniwind', False):
        if getattr(args, 'miniwind_features', None) or getattr(args, 'miniwind_description', None) or \
                getattr(args, 'miniwind_scope', None) or getattr(args, 'miniwind_town', None) or \
                getattr(args, 'miniwind_debug', False) or getattr(args, 'miniwind_map_inspection', False) or getattr(args, 'default_draw_distance', None):
            raise ValueError('--miniwind-features/--miniwind-description/--miniwind-scope/--miniwind-town/'
                             '--miniwind-debug/--default-draw-distance require --miniwind')
        if getattr(args, 'world_scenery', None) is None:
            raise ValueError('--world-scenery is required (a complete world scenery overlay)')
        return None
    import miniwind
    require_private_test_version(VERSION, [miniwind.OPTION])
    features = getattr(args, 'miniwind_features', None)
    if not features:
        raise ValueError('--miniwind needs --miniwind-features (tools/build.py generates it from its stage plan)')
    town = miniwind.check_town(getattr(args, 'miniwind_town', None) or miniwind.TOWN)
    debug = bool(getattr(args, 'miniwind_debug', False))
    boot = miniwind.boot_line([c for c in (getattr(args, 'miniwind_boot', None) or '').split(';') if c.strip()])
    inspection = bool(getattr(args, 'miniwind_map_inspection', False))
    if inspection:
        boot = miniwind.inspection_boot(boot)
    miniwind.data_file(features, town, debug=debug, boot=boot)
    for name in ('world_scenery', 'world_terrain', 'world_flora', 'seyda_recorded', 'gallery'):
        if getattr(args, name, None) is not None:
            raise ValueError('--miniwind builds one town only; drop --' + name.replace('_', '-'))
    scope = miniwind.check_scope(getattr(args, 'miniwind_scope', None) or miniwind.DEFAULT_SCOPE)
    if miniwind.label(scope) and not getattr(args, 'no_npc_gallery', False):
        raise ValueError(miniwind.SCOPE_OPTION + ' ' + scope + ' implies --no-npc-gallery')
    draw = getattr(args, 'default_draw_distance', None)
    if draw is not None and (not debug or not 128 <= draw <= 540):
        raise ValueError('--default-draw-distance is DEBUG ONLY (--miniwind-debug) and 128..540')
    return {'features': features, 'scope': scope, 'town': town, 'debug': debug, 'draw_distance': draw or 540, 'boot': boot,
            'map_inspection': inspection,
            'description': miniwind.check_description(getattr(args, 'miniwind_description', None))}


_DIRECT_START = [None]


def direct_start_option(args=None):
    """The image's parsed --direct-start (tools/direct_start.py), or None."""
    if args is not None:
        text = getattr(args, 'direct_start', None)
        import direct_start
        _DIRECT_START[0] = direct_start.parse(text) if text else None
    return _DIRECT_START[0]


def direct_start_map(args):
    """The map of an interior direct start (the scene rows' cell ID), or None."""
    start = direct_start_option()
    if start is None or start.kind != 'interior':
        return None
    import direct_start
    scenes = {row['cell'].casefold(): row['map'] for row in direct_start.scene_rows() if row.get('cell')}
    return scenes.get(start.cell.casefold())


def mini_start_maps(args):
    """Maps outside Balmora a MiniWind image keeps for its direct start (the prison ship), else ()."""
    import miniwind
    return (miniwind.start_maps(direct_start_map(args), getattr(args, 'miniwind_scope', None) or miniwind.DEFAULT_SCOPE)
            if getattr(args, 'miniwind', False) else ())


def test_header(mini, start, font_path=None):
    """The title screen header of a test build (id1/miniwind.txt "header", aw_menu.c): MiniWind
    "MINIWIND TEST UNIT: <description>", another direct start "QUICK TEST BUILD: <scene>".
    Returns (text, record with the lines the game font wraps it to)."""
    import miniwind
    from prepare_logo import fallback_width, load_font, text_width
    if mini:
        text = miniwind.header_line(mini.get('description'))
    else:
        text = miniwind.header_line(start.describe() if start else None, prefix='QUICK TEST BUILD: ',
                                    fallback='direct start')
    if font_path and Path(font_path).is_file():
        font = load_font(font_path)
        measure = lambda line: text_width(font, line)
    else:
        measure = fallback_width
    lines, cut = miniwind.header_lines(text, measure)
    if cut:
        print('[warning] Title screen header cut to two lines: ' + ' / '.join(lines), flush=True)
    return text, {'text': text, 'lines': lines, 'cut': cut, 'width_px': miniwind.HEADER_WIDTH}


def stage_skip_census(args, id1):
    """--skip-census: aw_skip_census 1 at the end of the game's default settings (default-game.cfg), so
    New Game makes the character on the quick character screen (aw_quickchar.c). Returns the record."""
    if not getattr(args, 'skip_census', False):
        return {'on': False}
    path = Path(id1) / 'default-game.cfg'
    raw = path.read_bytes()
    if not raw.endswith(b'\n'):
        raw += b'\n'
    raw += SKIP_CENSUS_LINES
    path.write_bytes(raw)
    print('Quick character screen: New Game skips the ship and the census (aw_skip_census 1)', flush=True)
    return {'on': True, 'config': 'id1/default-game.cfg', 'line': 'aw_skip_census 1'}


def stage_world_bounds(args, id1):
    """--world-bounds (the builder's default, tools/world_bounds.py): aw_world_bounds 1 at the end of the
    game's default settings (default-game.cfg): the sea near the edge of the open world carries the player
    along it and back in (docs/WORLD_BOUNDS.md). Off: nothing is written (the game as before). Returns the
    record, or None when off."""
    if not getattr(args, 'world_bounds', False):
        return None
    path = Path(id1) / 'default-game.cfg'
    raw = path.read_bytes()
    if not raw.endswith(b'\n'):
        raw += b'\n'
    raw += WORLD_BOUNDS_LINES
    path.write_bytes(raw)
    print('World bounds: on (aw_world_bounds 1; --world-bounds off leaves it out)', flush=True)
    return {'on': True, 'config': 'id1/default-game.cfg', 'line': 'aw_world_bounds 1'}


WORLD_BOUNDS_LINES = (b'// World bounds (builder default, --world-bounds on|off): the sea near the edge of the open\n'
                      b'// world carries you along it and back in (an AmiWind extension; dbg worldbounds).\n'
                      b'aw_world_bounds 1\n')


SKIP_CENSUS_LINES = (b'// --skip-census (quick test build): New Game makes the character on the quick character\n'
                     b'// screen and goes straight to the scene, without the ship and the census office.\n'
                     b'aw_skip_census 1\n')


def stage_direct_start(args, boot, out, mini, excluded):
    """Resolve the direct start against the final maps and write the quick-start lines
    (id1/miniwind.txt, aw_miniwind.c): a MiniWind build adds them to its notice file; any other
    build gets the file with the quick-test title. Returns the build.json record, or None."""
    import direct_start, miniwind
    from town_config import runtime_towns
    start = direct_start_option()
    character = direct_start.parse_character(
        getattr(args, 'quick_character', None), getattr(args, 'data_files', None)) if getattr(args, 'quick_character', None) else None
    if start is None and character is None:
        return None
    id1 = Path(boot)/'id1'
    towns = direct_start.town_rows(runtime_towns())
    if start is not None:
        if start.kind == 'interior':
            scenes = {row['cell'].casefold(): row['map'] for row in direct_start.scene_rows() if row.get('cell')}
            start.map = scenes.get(start.cell.casefold())
            if start.map is None:
                raise ValueError('%s "%s": the interior "%s" is not in this build. %s.'
                                 % (direct_start.OPTION, start.text, start.cell, direct_start.interior_reason(start.cell)))
        if start.kind == 'area' and start.town not in {t['name'] for t in towns if (id1/t['regions']).is_file()}:
            raise ValueError('%s %s: %s is not in this image' % (direct_start.OPTION, start.text, start.title))
        if start.kind == 'area' and not any(t['name'] == start.town and 'teleport_arrival' in t['flags'] for t in towns):
            # A town without a teleport arrival (Seyda Neen): its region table's arrival point.
            from arrival_spot import read_directory
            table = read_directory(id1/next(t['regions'] for t in towns if t['name'] == start.town))
            line = 'map %s %s %s %s %s' % (start.town, *(direct_start._number(v) for v in (*table['arrival'], table['yaw'])))
            resolved = {'kind': 'map', 'map': start.town, 'arrival': list(table['arrival']), 'yaw': table['yaw'],
                        'from': 'the town region table arrival'}
        else:
            line, resolved = direct_start.resolve(start, id1, towns)
    else:
        line, resolved = None, None
    character_value = direct_start.character_line(character) if character else None
    path = id1/miniwind.DATA_FILE
    if mini:
        data = miniwind.data_file(mini['features'], mini.get('town', miniwind.TOWN), start=line, character=character_value,
                                  debug=mini.get('debug', False),
                                  header=test_header(mini, start, id1/'gfx/magic16.awf')[0], boot=mini.get('boot'))
    else:
        data = miniwind.data_file(direct_start.notice_features(start, excluded) if start else 'QUICK TEST BUILD',
                                  town=direct_start.town_of(start, resolved or {}) if start else 'seyda',
                                  start=line, character=character_value, title=direct_start.QUICK_TITLE,
                                  features_prefix=None, header=test_header(None, start, id1/'gfx/magic16.awf')[0])
    path.write_bytes(data)
    record = {'start': start.record() if start else None, 'summary': direct_start.summary(start) if start else None,
              'engine_line': line, 'resolved': resolved,
              'character': character or direct_start.parse_character(None), 'notice_file': 'id1/' + miniwind.DATA_FILE,
              'notice_sha256': digest(path)}
    (Path(out)/'direct-start.json').write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8', newline='\n')
    print('Direct start: ' + (record['summary'] or 'MiniWind town') + (' -> ' + line if line else '')
          + '; character ' + record['character']['race'] + ' ' + record['character']['class'] + ' ' + record['character']['name'],
          flush=True)
    return record


def image_start(args, boot, out, direct_start_record):
    """The start check of a partial-area build (MiniWind, direct start) on the final payload (tools/direct_start.py
    image_start_check); None for a full build (the new game)."""
    import direct_start, miniwind
    resolved = (direct_start_record or {}).get('resolved')
    if resolved:
        start = {'map': resolved.get('map') or resolved.get('town'), 'arrival': resolved.get('arrival'),
                 'source': 'direct start ' + ((direct_start_record.get('start') or {}).get('text') or '') + ' ('
                           + str(resolved.get('from') or 'town arrival') + ')'}
    elif getattr(args, 'miniwind', False):
        start = {'map': getattr(args, 'miniwind_town', None) or miniwind.TOWN, 'arrival': None,
                 'source': "the MiniWind town's arrival point (no explicit start)"}
    else:
        return None
    record = direct_start.image_start_check(Path(boot)/'id1', start, report=Path(out)/'start-check.json')
    print('Start check: %s (%s): %s' % (record['map'], record['map_file'], record['source']), flush=True)
    return record


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
        start = direct_start_option()
        if start is None:
            return CHIM_STARTUP_LINES if chim else STARTUP_LINES
        import direct_start
        from project_version import chim_version
        if font_path and Path(font_path).is_file():
            font = load_font(font_path)
            measure = lambda text: text_width(font, text)
        else:
            measure = fallback_width
        try:
            chim_ver = chim_version(ROOT/'VERSION') if (ROOT/'CHIM_VERSION').is_file() else None
        except (OSError, ValueError):
            chim_ver = None
        return tuple(direct_start.logo_lines(VERSION, chim_ver, start.describe(), measure=measure, width=TEXT_WIDTH))
    import miniwind
    from project_version import chim_version
    if font_path and Path(font_path).is_file():
        font = load_font(font_path)
        measure = lambda text: text_width(font, text)
    else:
        measure = fallback_width
    return tuple(miniwind.logo_lines(VERSION, chim_version(ROOT/'VERSION'), mini['description'],
                                     measure=measure, width=TEXT_WIDTH, debug=mini.get('debug', False)))


def image(args):
    """Package the NPC gallery by default; fail if any required payload is absent.

    The sole opt-out is explicit --no-npc-gallery, recorded in build.json and
    the image itself. Asset-free boot-notice images use build_dry_run.py.
    """
    if getattr(args, 'payload_preflight_only', False):
        # Read-only: the payload preflight alone on an existing run's staged payload (tools/build.py --check-payload).
        return payload_preflight(args, ensure_external(args.out, 'prepared AGA image'), excluded_groups(args),
                                 image_jobs(args), pending=seyda_pending(args, args.scene))
    require_private_test_version(VERSION, image_waivers(args))
    mini = miniwind_options(args)
    direct_start_option(args)
    jobs = image_jobs(args)
    if getattr(args, 'allow_known_actor_ground_findings', None):
        from check_actor_ground import load_approved_report
        args.allow_known_actor_ground_findings = args.allow_known_actor_ground_findings.resolve()
        approved, _ = load_approved_report(args.allow_known_actor_ground_findings)
        # the same maintainer-accepted findings reach the CHIM frame map writer's own actor check (private test only;
        # require_private_test_version above): exactly these references, nothing else
        import os
        from chim.frame_map import ACCEPTED_ACTORS_VARIABLE
        os.environ[ACCEPTED_ACTORS_VARIABLE] = ','.join(sorted({str(e['reference']) for e in approved['errors']
                                                               if str(e.get('reference', '')).isdigit()}))
    if getattr(args, 'world_flora', None):
        for field in flora_image_inputs(args):
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
    boot=out/'boot';copy_tree(scene/'id1',boot/'id1');(boot/'S').mkdir()
    seyda_native='seyda' in chim_native_towns(args)
    if seyda_native and (boot/'id1/maps/seyda.bsp').is_file():
        # The scene's complete converted town is the chim-town-seyda stage's source, no map of the game: a
        # CHIM-native Seyda Neen stages no legacy map at all (BUILD-LEGACY-TOWN-MAPS-SHIPPED-36).
        (boot/'id1/maps/seyda.bsp').unlink()
        print('Seyda Neen is CHIM-native: no Seyda Neen legacy map is staged or cut (frame maps from the '
              'chim-town-seyda stage)',flush=True)
    if mini:
        # Balmora only: every other area's maps leave before any pass runs.
        import miniwind
        from chim.frame_map import remove_legacy_areas
        mini['prune']=miniwind.prune(boot/'id1',scope=mini['scope'],remove_legacy=remove_legacy_areas,town=mini['town'],
                                     extra=mini_start_maps(args),census_files=bool(getattr(args,'skip_census',False)),
                                     chim_town=mini['town'] in chim_native_towns(args))
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
    # The payload preflight as soon as the payload it reads is staged (scene copy, world terrain, scenery and
    # flora installed): an error is reported in the image step's first minute instead of after its passes
    # (BUILD-IMAGE-NO-RESUME-33). finalize_image runs it again on what the steps in between added.
    # The Seyda Neen region maps this step converts (or installs, --seyda-recorded) further down are
    # checked as planned here and as written there (BUILD-SEYDA-CONVERTED-NOT-STAGED-35).
    payload_preflight(args, out, excluded, jobs, pending=None if mini else seyda_pending(args, scene))
    cfg=boot/'id1/default.cfg'
    cfg.write_text(startup_config(cfg.read_text(), mini['draw_distance'] if mini else 540), newline='\n')
    shutil.copyfile(ROOT/'config/keymaps.cfg',boot/'id1/keymaps-default.cfg')
    logs_record=stage_game_config(boot/'id1', debug_luma=engine_record.get('debug_luma',False),
                                  live_logs=getattr(args,'live_logs',False))
    skip_census_record=stage_skip_census(args, boot/'id1')
    args.image_skip_census_record=skip_census_record  # finalize_image writes it into build.json
    args.image_world_bounds_record=stage_world_bounds(args, boot/'id1')  # build.json, only when on
    # --death-retry off (tools/prepare_player_view.py): aw_death_retry 0 in the game defaults.
    from prepare_player_view import stage_death_retry
    args.image_death_retry_record=stage_death_retry(getattr(args,'no_death_retry',False), boot/'id1')
    (out/'diagnostic-logs.json').write_text(json.dumps(logs_record,indent=2)+'\n', encoding='utf-8', newline='\n')
    args.image_debug_torch_record=debug_torch_record(boot/'id1')  # build.json "debug_torch"
    print('[debug torch] %s: %s (%s)' % ('ON' if args.image_debug_torch_record['on'] else 'off',
          DEBUG_TORCH_NAME, args.image_debug_torch_record['note']), flush=True)
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
    # The player's view (docs/THIRD_PERSON.md): the camera and death-scene game settings, and the player's
    # body per playable race and sex for third person (--player-body on|off, tools/prepare_player_view.py).
    from prepare_player_view import prepare as prepare_player_view
    print('Converting the player view data (camera settings, player bodies)...',flush=True)
    view_report=prepare_player_view(args.data_files,boot/'id1',jobs=jobs,bodies=not getattr(args,'no_player_body',False))
    (out/'player-view.json').write_text(json.dumps(view_report,indent=2)+'\n',encoding='utf-8',newline='\n')
    from prepare_inventory import prepare as prepare_inventory
    print('Converting original inventory metadata and selected item resources...',flush=True)
    inventory_report=prepare_inventory(args.data_files,boot/'id1',jobs=jobs)
    (out/'inventory-data.json').write_text(json.dumps(inventory_report,indent=2)+'\n',encoding='utf-8',newline='\n')
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
                 **({'prompt_top':miniwind.PROMPT_Y} if mini or direct_start_option() else {}))
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
    if mini and mini.get('map_inspection'):
        mini['inspection_setup'] = miniwind.install_map_inspection(boot/'id1')
    if mini:
        # The engine reads the notice and starts in the town (aw_miniwind.c, aw_scene.c aw_quick_start).
        mini['header']=test_header(mini,None,boot/'id1/gfx/magic16.awf')[1]
        (boot/'id1'/miniwind.DATA_FILE).write_bytes(miniwind.data_file(mini['features'],mini['town'],debug=mini['debug'],
                                                                     header=mini['header']['text'],boot=mini.get('boot')))
        (boot/miniwind.MARKER_FILE).write_text(miniwind.marker_text(VERSION,mini['features'],mini['description'],
                                                                    scope=mini['scope'],town=mini['town'],
                                                                    debug=mini['debug']),newline='\n')
        print('Default start: logo fade, "'+miniwind.PROMPT+'", then '+mini['town']+' (Hors preset); New Game starts '
              'there again. '+('DEBUG ONLY, not a playtest. ' if mini['debug'] else '')
              +miniwind.partial_area(mini['scope'],mini['town'])+'.',flush=True)
    else:
        print('Default start: logo fade then main menu; New Game plays the optional movie then ship + track 04.',flush=True)
    shutil.copyfile(args.engine,boot/'AmiWind')
    shutil.copyfile(checker,boot/'AmiWindCheck')
    pair=engine_060_files(args.engine,engine_record)
    if pair:
        shutil.copyfile(pair[0],boot/ENGINE_060)
        shutil.copyfile(pair[1],boot/CPU_SELECTOR)
        print('Engines: AmiWind (68040 build, default) and AmiWind060 (68060 build); AmiWindCPU picks at boot',flush=True)
    fpu_receipt=stage_fpu_support(args,engine_record,boot)
    (out/'fpu-support.json').write_text(json.dumps(fpu_receipt,indent=2)+'\n',encoding='utf-8',newline='\n')
    (boot/'S/startup-sequence').write_text(fpu_support.startup_sequence(fpu_receipt,**fpu_support.engine_start(bool(pair))), newline='\n')
    if not mini:
        for name in ['seyda.map','town.wad']:shutil.copyfile(scene/name,out/name)
    if (scene/'scene-ready.json').is_file():
        ready=json.loads((scene/'scene-ready.json').read_text())
        from prepare_mesh_bsp import CARRIER_SCENE_FORMAT
        if ready.get('format')==CARRIER_SCENE_FORMAT:
            # The bsp stage's source-only carrier (--seyda-source carrier, BUILD-SEYDA-HULL2-32): entities and
            # model boxes, no geometry. Only a CHIM-native Seyda Neen takes it (chim_town.prepare_seyda); the
            # legacy chain cuts region maps from the compiled town and refuses it.
            if not seyda_native and not mini:
                raise ValueError('Scene %s is a Seyda Neen source carrier (no compiled town): it needs a CHIM-native '
                                 'Seyda Neen; build the scene with the bsp stage\'s --seyda-source compiled for the '
                                 'legacy chain'%scene)
        elif ready.get('format')!='AmiWind compiled mesh BSP29':raise ValueError('Unknown compiled scene format')
        from player_hull import PROFILE
        if ready.get('standing_hull_profile')!=PROFILE:raise ValueError('Rebuild the scene: standing collision hull does not match this runtime')
        if not ready.get('hands'):raise ValueError('Prepare first-person hands before building this runtime')
        if not mini and not seyda_native:shutil.copyfile(scene/'seyda.bsp',out/'seyda.bsp')
    else:
        raise ValueError('Prepare the matching mesh scene before building this runtime image')
    if not mini and not seyda_native:
        shutil.copyfile(out/'seyda.bsp',boot/'id1/maps/seyda.bsp')
        from prepare_seyda_regions import convert_builder_scene
        convert_builder_scene(boot/'id1/maps', scene_map=out/'seyda.map',
                              palette=boot/'id1/gfx/palette.lmp', ericw_bin=args.qbsp.parent,
                              work_dir=out/'bounded-seyda', vis_mode=getattr(args,'vis_mode','fast'),
                              canonical_land_source=getattr(args,'canonical_land_source',None), jobs=jobs,
                              recorded=getattr(args,'seyda_recorded',None),
                              terrain_cull=getattr(args,'seyda_terrain_cull','on')!='off')
    # Recorded-stage exception (BUILD-SEYDA-REGEN-30): later passes keep these maps byte for byte.
    import recorded_stage
    frozen=recorded_stage.frozen_maps(out/'bounded-seyda')
    native=chim_native_towns(args)
    if native:
        # A CHIM-native town's listed rooms first (tools/chim_rooms.py): their door bank links the doors into the rooms,
        # and chim_town.install keeps it instead of its own unlinked bank (BUILD-MINIWIND-ARENA-PIT-REFUSED-36).
        from chim_rooms import install as install_chim_rooms
        rooms=[install_chim_rooms(path,boot/'id1') for path in (getattr(args,'chim_rooms',None) or [])]
        if rooms:
            (out/'chim-rooms.json').write_text(json.dumps(rooms,indent=2)+'\n',encoding='utf-8',newline='\n')
            print('CHIM town rooms: '+'; '.join(r['town']+' '+', '.join(r['rooms']) for r in rooms),flush=True)
        from chim_town import install as install_chim_town
        installed=[install_chim_town(path,boot/'id1') for path in args.chim_town]
        (out/'chim-towns.json').write_text(json.dumps(installed,indent=2)+'\n',encoding='utf-8',newline='\n')
        print('CHIM towns from the game data (no legacy region maps): '+', '.join(native),flush=True)
    if getattr(args, 'balmora_cache', None):
        from repair_balmora_maps import repair as repair_balmora_maps
        print('Preparing measured bounded Balmora layout from complete source cache...', flush=True)
        repair_balmora_maps(boot/'id1/maps', cache=args.balmora_cache,
                           palette=boot/'id1/gfx/palette.lmp', ericw_bin=args.qbsp.parent,
                           work_dir=out/'bounded-balmora', threads=jobs, vis_mode=getattr(args,'vis_mode','fast'),
                           night_lamps=(__import__('mwad.paths',fromlist=['child_ci']).child_ci(args.data_files,'Morrowind.esm')
                                        if getattr(args,'night_lamp_lightmaps',False) else None))
    if flora:
        from install_town_flora import install as install_town_flora
        from prepare_quake import CENTRE
        town_palette = args.scene/'id1/gfx/palette.lmp'
        seyda_origin = [CENTRE[0]*.25, CENTRE[1]*.25, 0.]
        if 'seyda' in native:
            # The CHIM world holds Seyda Neen's town flora meshes and solid sprites' collision (chim.seyda), the
            # chim-town-seyda stage its flora sprites (the same rule, chim_town.seyda_flora); no legacy maps.
            towns = {'seyda': {'status': 'in the CHIM world and the chim-town-seyda frame rows (no legacy region maps)'}}
        elif frozen:
            actual = json.loads((boot/'id1/seyda-regions.json').read_text(encoding='utf-8'))
            towns = {'seyda':recorded_stage.keep_town_flora(boot, flora, [e['name']+'.bsp' for e in actual['regions']])}
        else:
            actual = json.loads((boot/'id1/seyda-regions.json').read_text(encoding='utf-8'))
            seyda_entries = [{**entry, 'origin':seyda_origin} for entry in actual['regions']]
            towns = {'seyda':install_town_flora(boot, flora, town_palette,
                entries=seyda_entries, town_source_index=args.town_flora_source_index,
                town_scene_report=args.town_flora_scene_report, work_dir=out/'town-flora-seyda')}
            shutil.copyfile(boot/'id1/maps'/(actual['fallback_alias']+'.bsp'), boot/'id1/maps/seyda.bsp')
        from install_town_flora import town_entries
        if 'balmora' in native:
            # The CHIM world holds Balmora's town flora as meshes (chim_build --flora); no legacy maps.
            towns['balmora'] = {'status': 'in the CHIM world (no legacy region maps)'}
        else:
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
        clear_baked(args.harvest,boot/'id1',out/'harvest',data_files=args.data_files,jobs=jobs,native=native,
                    chim_world=getattr(args,'chim_world',None))
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
    return miniwind.hdf_tag(getattr(args, 'miniwind_scope', None) or miniwind.DEFAULT_SCOPE,
                            getattr(args, 'miniwind_town', None) or miniwind.TOWN,
                            bool(getattr(args, 'miniwind_debug', False)))


def miniwind_start(town=None):
    """build.json default_start of a MiniWind image (aw_movie.c, aw_scene.c aw_quick_start)."""
    import miniwind
    return {'profile': 'logo-fade-enter-then-quick-start', 'movie': 'intro/amiwind.awv', 'prompt': miniwind.PROMPT,
            'new_game_map': town or miniwind.TOWN,
            'character': 'Hors preset (Nord, Barbarian, The Steed)', 'notice_file': 'id1/' + miniwind.DATA_FILE}


def miniwind_receipt(args, out, boot):
    """build.json build_type of a MiniWind image: what it is, its notice, logo lines and pruning."""
    import miniwind
    prune = json.loads((out / 'miniwind-prune.json').read_text(encoding='utf-8'))
    notice = boot / 'id1' / miniwind.DATA_FILE
    logo = startup_lines(miniwind_options(args), boot / 'id1/gfx/magic16.awf')
    scope = miniwind.check_scope(getattr(args, 'miniwind_scope', None) or miniwind.DEFAULT_SCOPE)
    town = getattr(args, 'miniwind_town', None) or miniwind.TOWN
    debug = bool(getattr(args, 'miniwind_debug', False))
    return {'name': miniwind.NAME, 'scope': scope, 'label': miniwind.label(scope),
            'partial_area': miniwind.partial_area(scope, town), 'town': town,
            'debug_only': debug, 'draw_distance': getattr(args, 'default_draw_distance', None) or 540,
            'notice': [miniwind.notice_title(debug), args.miniwind_features],
            'notice_file': 'id1/' + miniwind.DATA_FILE, 'notice_sha256': digest(notice),
            'marker_file': miniwind.MARKER_FILE, 'description': getattr(args, 'miniwind_description', None),
            'logo_lines': [miniwind.line_text(line) for line in logo],
            'logo_console_font': [text for line in logo if not isinstance(line, str)
                                  for text, font in line if font == miniwind.CONSOLE_FONT],
            'prompt': miniwind.PROMPT,
            'maps_removed': len(prune['maps_removed']),
            'bytes_removed': prune['bytes_removed'], 'maps_kept': len(prune['maps_kept']),
            'interiors_missing': prune['interiors_missing']}


def staged_exterior_map_names(id1, chim_world=None, exterior_terrain=None):
    """Explicit runtime directories identify exterior cells; sky is not a classifier. chim_world: the build's CHIM
    world; the open-world maps its region frames own have no legacy map (docs/BUILD_MANIFEST.md step 2) and are left
    out until their frame maps exist; any other missing map stays listed (and fails the passes)."""
    id1 = Path(id1)
    from town_config import runtime_towns
    towns = runtime_towns()
    names = {name for name in (*(town['name'] for town in towns), 'intro_docks', 'sncourt')
             if (id1 / 'maps' / (name + '.bsp')).is_file()}
    for town in towns:
        directory = id1 / town['regions']
        if directory.is_file():
            # A CHIM town built from the game data has a region table but no region maps.
            names.update(Path(name).stem for name in town_region_map_names(directory, town['prefix'])
                         if (id1 / name).is_file())
    directory = id1 / 'world/regions.awr'
    if directory.is_file():
        raw = directory.read_bytes()
        if len(raw) < 64 or raw[:4] != b'AWR2':
            raise ValueError('Invalid world region directory for hidden-surface pass')
        count = struct.unpack_from('<I', raw, 4)[0]
        if len(raw) != 64 + count * 52:
            raise ValueError('World region count mismatch for hidden-surface pass')
        owned = {}
        if chim_world:
            from chim.frame_map import region_map_names
            owned = region_map_names(id1, chim_world)
        names.update(name for name in (f'vf{index:04d}' for index in range(count))
                     if name not in owned or (id1 / 'maps' / (name + '.bsp')).is_file())
    if exterior_terrain:
        from exterior_plan import omitted_paths
        # These passes precede frame generation. Bind omissions to validated
        # town plans now; the final fingerprint requires actual owner frames.
        planned = set(chim_world_receipt(chim_world)[1]) if chim_world else None
        names.difference_update(Path(name).stem for name in
                                omitted_paths(exterior_terrain, id1, planned_towns=planned))
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

# The special scenes prepare_seyda_regions.convert writes after the regions (its `specials`).
SEYDA_SPECIAL_MAPS = ('intro_docks', 'sncourt')

def seyda_pending(args, scene):
    """The Seyda Neen files the image step writes itself before its CHIM frame maps, read only:
    {id1-relative file: the region names a table lists, or None}, or None when it writes none (MiniWind) or its inputs are not
    there (then the preflight reports them missing). Converted (the default): the region conversion's
    plan, from the scene's complete seyda.bsp and seyda.map; --seyda-recorded DIR: the pinned recorded
    set, after the same pin check the install makes (BUILD-SEYDA-CONVERTED-NOT-STAGED-35)."""
    if getattr(args, 'miniwind', False):
        return None
    if 'seyda' in chim_native_towns(args):
        return None   # CHIM-native: the image step writes no Seyda Neen map (chim-town-seyda gives the region table)
    recorded = getattr(args, 'seyda_recorded', None)
    if recorded is not None:
        # The same pin check install() makes (tools/recorded_stage.py), then its shipped set.
        import recorded_stage
        from chim.frame_map import region_table
        _, files, aliases = recorded_stage.check_source(recorded)
        plan = {}
        for name, source in recorded_stage.shipped(files, aliases).items():
            plan[name] = (tuple(n for n, _ in region_table(Path(recorded)/'id1'/source)[1])
                          if name.endswith('-regions.txt') else None)
        return plan
    if scene is None or not all((Path(scene)/name).is_file() for name in ('seyda.bsp', 'seyda.map')):
        return None
    # convert() (tools/prepare_seyda_regions.py): one map per layout region, the special scenes, the
    # fallback seyda.bsp, and the region table listing the regions in layout order.
    import prepare_seyda_regions as seyda_regions
    names = tuple(entry['name'] for entry in seyda_regions.regions())
    plan = {'seyda-regions.txt': names}
    for name in names + SEYDA_SPECIAL_MAPS + ('seyda',):
        plan['maps/'+name+'.bsp'] = None
    return plan

def payload_preflight(args, out, excluded, jobs, pending=None):
    """The image step's read-only payload checks over the staged payload, before it writes anything
    (tools/payload_preflight.py; CHIM-HARVEST-SPECIALS-33 stopped three image runs at their end).
    pending: files the image step still writes before its frame maps (seyda_pending); finalize_image
    passes none, so the written files are checked there."""
    import payload_preflight as preflight
    return preflight.run(out, chim_world=getattr(args, 'chim_world', None), pending=pending,
                         music=None if 'music' in excluded else getattr(args, 'music', None), jobs=jobs,
                         harvest=getattr(args, 'harvest', None), data_files=getattr(args, 'data_files', None),
                         report_path=None if getattr(args, 'payload_preflight_only', False) else out/'payload-preflight.json',
                         chim_towns=chim_native_towns(args), chim_town_dirs=getattr(args, 'chim_town', None) or (),
                         exterior_terrain=getattr(args, 'exterior_terrain', None) or getattr(args, 'world_terrain', None))

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
    row060=engine_record.get('engine_68060')
    if (boot/ENGINE_060).is_file()!=bool(row060) or (row060 and (digest(boot/ENGINE_060)!=row060['binary_sha256']
                                                                  or digest(boot/CPU_SELECTOR)!=row060['selector_sha256'])):
        raise ValueError('Staged AmiWind060/AmiWindCPU differ from the verified engine build receipt')
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
    # A fallback here leaves the converted maps' one-colour placeholder as the shared sky: every
    # exterior ships a flat sky with no clouds (SKY-FLAT-PALETTE-DRIFT-41, v0.0.40 to v0.0.41, only a
    # warning line then). With the maintainer's data files it is never acceptable: stop, naming why.
    if sky_asset_preparation.get('status')=='fallback_warning' and getattr(args, 'data_files', None):
        raise ValueError('Shared sky not prepared ({}): the image would ship a flat sky with no clouds '
                         '(SKY-FLAT-PALETTE-DRIFT-41); staged palette {} sha256 {}'.format(
                             sky_asset_preparation.get('warning'), boot / 'id1/gfx/palette.lmp',
                             hashlib.sha256((boot / 'id1/gfx/palette.lmp').read_bytes()).hexdigest()))
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
    # Original NPC heads take world, combat and guard models past 2,000 vertices:
    # each gets its byte-matching model-budgets.txt line (NPC-HEAD-DECIMATION-33).
    from audit_gallery_budgets import world_allowances
    world_budgets = world_allowances(boot / 'id1')
    (out/'world-model-budgets.json').write_text(json.dumps(world_budgets,indent=2)+'\n', newline='\n')
    print(f"World model allowances: {len(world_budgets['added'])} extended NPC models listed in model-budgets.txt.", flush=True)
    # Apply explicit sky policy after every mesh/overlay, before all final gates.
    from exterior_sky_build import configure_staged_maps
    exterior_sky_path = out / 'exterior-sky' / 'exterior-sky.json'
    exterior_sky = configure_staged_maps(boot / 'id1',
        exterior_maps=staged_exterior_map_names(boot / 'id1', getattr(args, 'chim_world', None), getattr(args, 'exterior_terrain', None)),
        interior_maps=staged_interior_map_names(boot / 'id1'),
        local_skybox=getattr(args, 'local_skybox', 'false'),
        shared_sky_source=sky_asset_preparation['shared_sky_source'],
        work_dir=exterior_sky_path.parent, jobs=jobs,
        # the CHIM frame maps (written later) name the shared sky too (CHIM-NATIVE-IMAGE-NO-SHARED-SKY-36)
        frame_exterior=bool(getattr(args, 'chim_world', None)))
    from recorded_stage import check as check_recorded
    check_recorded(boot/'id1', out/'bounded-seyda', 'sky asset preparation and exterior sky', jobs=jobs)
    if excluded:
        # Quick test build: the shared assets maps and the engine find by name (the sky,
        # palette, fonts, menus) are kept by every exclusion (build_exclusions.ALWAYS_INCLUDED).
        from build_exclusions import check_always_included, worldspawn_sky_keys
        always_included=check_always_included(boot/'id1', exterior=bool(staged_exterior_map_names(boot/'id1', getattr(args, 'chim_world', None), getattr(args, 'exterior_terrain', None)))
                                              or bool(getattr(args, 'chim_world', None)),
                                              maps=worldspawn_sky_keys(boot/'id1/maps'))
        (out/'always-included.json').write_text(json.dumps(always_included,indent=2)+'\n',encoding='utf-8',newline='\n')
    # Run after all meshes/overlays, before compaction, contact/heap and fingerprints.
    from hidden_surface_build import cull_staged_maps, enabled_value
    hidden_surface_path = out / 'hidden-surface-cull' / 'hidden-surfaces.json'
    hidden_surfaces = cull_staged_maps(boot / 'id1/maps', hidden_surface_path.parent,
        staged_exterior_map_names(boot / 'id1', getattr(args, 'chim_world', None), getattr(args, 'exterior_terrain', None)),
        enabled=enabled_value(getattr(args, 'hidden_surface_cull', 'true')),
        jobs=jobs)
    check_recorded(boot/'id1', out/'bounded-seyda', 'hidden-surface cull', jobs=jobs)
    # Regional map generation can replace a worldspawn after hands conversion.
    # Stamp all final maps from the same authored animation report before gates.
    from hand_metadata import stamp_staged_hands
    hand_source = json.loads((Path(args.scene)/'scene-ready.json').read_text())['hands']
    hand_metadata = stamp_staged_hands(boot/'id1', hand_source,
        staged_exterior_map_names(boot/'id1', getattr(args, 'chim_world', None), getattr(args, 'exterior_terrain', None)) | staged_interior_map_names(boot/'id1'), jobs=jobs)
    (out/'hand-metadata.json').write_text(json.dumps(hand_metadata,indent=2)+'\n', newline='\n')
    check_recorded(boot/'id1', out/'bounded-seyda', 'first-person hand metadata', jobs=jobs)
    # Stable interior cell numbers + full cell IDs for the debug HUD and `dbg cell`;
    # the lookup table goes into the build folder.
    from cell_numbers import stamp_staged_cells
    cell_numbers = stamp_staged_cells(boot/'id1', args.data_files, staged_interior_map_names(boot/'id1'),
                                      out/'cell-numbers.json', jobs=jobs)
    check_recorded(boot/'id1', out/'bounded-seyda', 'interior cell numbers', jobs=jobs)
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
    # residents of CHIM-native town frames: their town stage's fit on the frame collision, judged by the same gate
    actor_report = require_actor_ground(boot/'id1/maps', out/'actor-initial-contact.json',
                                       getattr(args, 'allow_known_actor_ground_findings', None),
                                       findings_only=True, jobs=jobs, chim_frames=chim_town_grounding(args),
                                       empty_scene=empty_miniwind_actor_evidence(args, boot/'id1/maps'))
    actor_acceptance = actor_report['acceptance']
    (out/'actor-ground-acceptance.json').write_text(json.dumps(actor_acceptance, indent=2)+'\n', newline='\n')
    # Count original versus placed entities on the final maps; an unexplained
    # loss against the previous build stops here, before any disk is made.
    from entity_tracker import build_gate as entity_gate
    from mwad.paths import child_ci
    from prepare_mesh_bsp import DRESSING_EXCLUDED
    # the CHIM world is read once here and held for the frame maps and their heap gate below
    chim_world_held = {}
    chim_world_data = chim_world_once(getattr(args, 'chim_world', None), chim_world_held)
    entity_tracker = entity_gate(out, boot/'id1/maps', child_ci(args.data_files,'Morrowind.esm'),
        getattr(args,'entity_baseline',None), getattr(args,'accept_entity_loss',None), jobs=jobs,
        dressing_terms=DRESSING_EXCLUDED, extra_maps={**chim_town_placements(args, boot/'id1', world=chim_world_data),
                                                     **chim_region_placements(args, boot/'id1', world=chim_world_data)})
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
    from town_config import runtime_towns
    require_arrivals(boot/'id1', out/'arrival-check.json',
                     towns=[t for t in runtime_towns() if t['id'] not in chim_native_towns(args)])
        # A direct start (tools/direct_start.py): resolved here, on the final maps, before a pure CHIM
    # image removes the legacy maps (the region maps hold the same collision as the CHIM chunks).
    direct_start_record=stage_direct_start(args, boot, out, miniwind_options(args), excluded)
    # Night lamp, glowing glass and location fog tables from the final maps (read only; before a pure CHIM image
    # removes the CHIM towns' legacy maps below).
    from night_lighting import stage as stage_night_lighting, image_sources
    night_lighting = stage_night_lighting(boot/'id1', master=child_ci(args.data_files,'Morrowind.esm'),
        maps=staged_exterior_map_names(boot/'id1', getattr(args, 'chim_world', None), getattr(args, 'exterior_terrain', None)), sources=image_sources(args),
        palette=boot/'id1/gfx/palette.lmp', data_files=args.data_files, work_dir=out/'night-lighting',
        lighting_type=getattr(args, 'chim_lighting_type', None))
    # Pure CHIM (--builder chim): each CHIM town's frame maps are written and checked against its
    # final legacy maps (statics both ways, origin, harvest representation), then those legacy maps
    # leave the image (chim.frame_map.remove_legacy_areas, recorded): the stair and heap gates below
    # see only what ships, and the CHIM world carries its own (tools/chim_build.py).
    chim_frames, removed_legacy, not_on_chim = None, [], []
    if getattr(args, 'chim_world', None):
        special_rows, activated_rows = chim_town_specials(args)
        # the harvest step's catalogues for the region frame maps stay with them (HARVEST-CHIM-REGION-LOSS-41)
        staging_path = out/'harvest'/'harvest-staging.json'
        keep_catalogues = ({n: r['sha256'] for n, r in json.loads(staging_path.read_text(encoding='utf-8'))
                            .get('chim_region_catalogues', {}).items()} if staging_path.is_file() else {})
        chim_frames = chim_frame_maps(args.chim_world, boot/'id1', town_rows=chim_town_rows(args), jobs=jobs,
                                      special_rows=special_rows, activated=activated_rows,
                                      hand_fields=hand_metadata['worldspawn_fields'], keep_catalogues=keep_catalogues,
                                      world=chim_world_data)
        from chim.frame_map import remove_legacy_areas, remove_towns_not_on_chim
        removed_legacy = remove_legacy_areas(boot/'id1', chim_frames['areas'], 'the town runs on CHIM')
        # Extra towns not on CHIM yet (the Vivec Arena) leave a CHIM image whole: exterior maps, region and
        # door tables, harvest catalogues; the engine then finds no such destination (CHIM-LEGACY-CHAIN-33).
        not_on_chim = [town['id'] for town in staged_extra_towns(boot/'id1') if town['id'] not in chim_frames['areas']]
        removed_legacy += remove_towns_not_on_chim(boot/'id1', not_on_chim)
        # CHIM region frames (EXPERIMENTAL): the open-world maps replaced in place (and their harvest catalogues)
        region_replaced = [row for record in chim_frames['region_maps'] for row in record['replaced']]
        removed_legacy += region_replaced
        # Town-first world routing can also make neighbouring legacy region
        # cores unreachable. Keep explicit payload dependencies and all partial
        # cores; record the remaining removals before image gates and packing.
        from world_payload import prune as prune_world_payload
        removed_legacy += prune_world_payload(boot/'id1', out/'world-payload-pruning.json')
        if getattr(args, 'harvest', None):
            # The final payload: every harvestable plant the CHIM world leaves out is in a shipped catalogue,
            # each CHIM region cell's in its own frame map's (HARVEST-CHIM-REGION-LOSS-41).
            from harvest_build import native_towns, require_chim_coverage
            coverage = require_chim_coverage(args.harvest, boot/'id1', out/'harvest', data_files=args.data_files,
                                             chim_world=args.chim_world, native=native_towns(args), frame_maps=True,
                                             report_name='harvest-chim-coverage-final.json')
            if coverage is not None:
                harvest['chim_coverage_final'] = dict(plants=coverage['plants'], placed=coverage['placed'],
                                                      missing=len(coverage['missing']),
                                                      region_frame_catalogues=coverage['region_frame_catalogues'])
        if chim_frames['region_maps']:
            print('[chim] CHIM region frames: %d open-world maps replaced in place by CHIM frame maps (%d legacy '
                  'bytes out, %d frame-map bytes in)' % (len(chim_frames['region_maps']),
                  sum(r['bytes'] for r in region_replaced if r['file'].startswith('maps/')),
                  sum(r['bytes'] for r in chim_frames['region_maps'])), flush=True)
        (out/'chim-removed-legacy.json').write_text(json.dumps(removed_legacy, indent=2)+'\n', encoding='utf-8',
                                                   newline='\n')
        # Each frame map's whole-map heap (CHIM-SEYDA-MEMORY-33): the zone the engine can take beside
        # the frame map's own Hunk, its rings with the streamed statics' models, on this build's heap.
        from chim.heap import require_frame_map_heap
        frame_heap = require_frame_map_heap(args.chim_world, boot/'id1', args.sdk, heap_mb=engine_record.get('heap_mb'),
                                            report_path=out/'chim-frame-heap.json',
                                            extra_maps=[r['map'][5:] for r in chim_frames['region_maps']],
                                            # all frames over the shared pool, unchanged frames from the image pass
                                            # cache by their SHA-256 content key (maintainer order 2026-10-11 10:08)
                                            jobs=resolve_jobs(args.jobs), cache_dir=_frame_heap_cache(),
                                            world=chim_world_data)
        for name, m in sorted(frame_heap.get('maps', {}).items()):
            print(f"[chim] frame-map heap {name}: zone {m['zone_bytes']} B (after the map {m['after_zone_bytes']} B), "
                  f"active ring {m['peak_bytes']} / load ring {m['load_ring']['peak_bytes']} of {m['budget_bytes']} B, "
                  f"streamed models {m['streamed_bytes']} B, largest block {m['largest_block_bytes']} B", flush=True)
        # the CHIM world read once for the image step is not needed after its last reader (the heap gate)
        chim_world_held.clear()
        chim_world_data = None
        # The optimizer receipt follows the new map set (frame maps in, removed maps out) before the gates.
        from optimize_world_maps import rebind_chim_maps
        optimization = rebind_chim_maps(boot/'id1/maps', optimization, optimization_path,
                                        [row['file'] for row in removed_legacy], jobs=jobs,
                                        replaced=[r['map'][5:] for r in chim_frames['region_maps'] if r['replaced']])
    # Every map that ships fits the engine's per-map tables: edicts, model and sound precaches, static
    # entities, the scenery catalogue (tools/map_engine_limits.py, BUILD-BUDGET-ENGINE-LIMITS-35); a map
    # over one stops the game at load ("no free edicts", precache overflow), so it never ships.
    from map_engine_limits import check_maps as check_engine_map_limits
    engine_map_limits = check_engine_map_limits(boot/'id1/maps', out/'engine-map-limits.json')
    print('Engine map limits passed: %d maps; tightest: %s.' % (engine_map_limits['maps'], ', '.join(
        '%s %s %d/%d' % (key, row['top'][0]['map'], row['top'][0]['value'], row['limit'])
        for key, row in engine_map_limits['worst'].items() if row['top'])), flush=True)
    # Every flight of stairs in every map can be walked up and down by the
    # standing box (COLLISION-STAIR-SLOPE-32); on with follow_original_stair_rules.
    # The recorded Seyda Neen stage (BUILD-SEYDA-REGEN-30) is reported, not gated.
    from mesh_geometry_env import stair_rules_enabled
    if stair_rules_enabled():
        from stair_parallel import require as require_stairs   # every core (BUILD-IMAGE-STAIR-WALK-SERIAL-36)
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
    # The player starts inside what a partial-area build holds (maintainer order 2026-10-11; BUILD-MINIWIND-DIRECT-START-
    # TOWN-36): the boot start's map is in the final payload and its spot stands on collision, in seconds, before packing.
    start_check=image_start(args, boot, out, direct_start_record)
    # Every map write is above: the recorded maps ship exactly as recorded.
    removed_files = [row['file'] for row in removed_legacy]
    recorded_stage = check_recorded(boot/'id1', out/'bounded-seyda', 'final image payload', jobs=jobs,
                                    removed=removed_files)
    omitted_maps = image_content_fingerprint(args, boot/'id1', jobs, removed_files, excluded)
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
                                     excluded=['music'] if 'music' in excluded else [], jobs=jobs)
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
    # Legacy maps of CHIM cells (docs/BUILD_MANIFEST.md): how many this build still made, how many ship (must be
    # 0) and the payload's maps by kind, printed and recorded (BUILD-LEGACY-TOWN-MAPS-SHIPPED-36).
    legacy_summary = legacy_maps_summary(boot/'id1', removed_legacy)
    (out/'legacy-maps-of-chim-cells.json').write_text(json.dumps(legacy_summary,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(legacy_summary['line'], flush=True)
    print('Payload maps by kind: ' + ', '.join('%s %d (%d bytes)' % (kind, row['files'], row['bytes'])
                                               for kind, row in legacy_summary['payload_by_kind'].items()), flush=True)
    if legacy_summary['shipped']:
        raise ValueError('Legacy maps of CHIM cells in the payload: ' + ', '.join(legacy_summary['shipped'][:8]))
    from world_volumes import pack as pack_world_volumes
    world_images=pack_world_volumes(boot/'id1',out,VERSION,args.xdftool,args.rdbtool,jobs=jobs,
                                   omitted=omitted_maps)
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
        'cell_numbers':{'report':'cell-numbers.json','interior_cells':cell_numbers['interior_cells'],
            'stamped_maps':len(cell_numbers['maps']),'masters_sha256':cell_numbers['masters_sha256']},
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
            if not getattr(args, 'miniwind', False) else miniwind_start(getattr(args, 'miniwind_town', None)),
        'hdf_bytes':hdf.stat().st_size,'hdf_sha256':digest(hdf),
        'binary_sha256':digest(boot/'AmiWind'),'bootcheck_sha256':digest(checker),
        'engine_profile':engine_record.get('engine_profile') or {'label':'c','note':'engine receipt predates engine profiles'},
        'fpu_support':fpu_receipt,
        'payload_bytes':sum(p['payload_bytes'] for p in layout),'partitions':layout,
        'media_coverage':{'report':media_coverage_path.name,'sha256':digest(media_coverage_path),
            'categories':media_coverage['categories'],'excluded':media_coverage.get('excluded',[]),
            'payload_readback':'passed'},
        'direct_start':direct_start_record,
        'start':start_check,
        'skip_census':getattr(args,'image_skip_census_record',None),
        'excluded_content':(json.loads((out/'excluded-content.json').read_text(encoding='utf-8'))
            if (out/'excluded-content.json').is_file() else stage_excluded_content(boot, excluded)),
        'music_tracks':len(manifest['tracks']),'music_catalogue':music_catalogue,'heap_reservation_bytes':world_heap['heap_budget_bytes'],
        'tested_minimum':False,'filesystem':'DOS1 FFS partitions in legacy-safe RDB HDF drives',
        'legacy_root_check':root_check}
    if getattr(args, 'retired_flags_used', None):
        # A flag retired since CHIM v0.1.0 (tools/retired_flags.py): the image receipt says so loudly.
        build_json['retired_flags_used'] = {'flags': args.retired_flags_used,
            'warning': 'WARNING: DO NOT USE EXCEPT FOR ANTIQUATED REGRESSION PURPOSES (retired since CHIM v0.1.0)'}
        print('RETIRED FLAGS USED: ' + args.retired_flags_used, flush=True)
    if getattr(args, 'image_world_bounds_record', None):
        build_json['world_bounds'] = args.image_world_bounds_record
    recipe_record = os.environ.get('AMIWIND_BUILD_RECIPE')
    if recipe_record:
        # The build's recipe (tools/build_recipe.py ENV, set by tools/build.py; never part of a stage key): a reused
        # image step keeps the record of the run that made it (its "run" names that run).
        build_json['build_recipe'] = json.loads(recipe_record)
    if getattr(args, 'image_debug_torch_record', None):
        build_json['debug_torch'] = args.image_debug_torch_record
    build_json['player_view'] = {'player_body': not getattr(args, 'no_player_body', False),
                                 'death_retry': not getattr(args, 'no_death_retry', False)}
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

# Experimental engine compile switches by name -> the define (engine/aga/Makefile EXTRA_DEFINES).
# widecoord: positions as 24 bits of 1/256 units, +/-32,768 (engine/aga/src/aw_coord.h, CHIM-FRAME-COORD-RANGE-33).
ENGINE_EXPERIMENTS={'widecoord':'-DAW_EXP_WIDECOORD'}

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    e=sub.add_parser('engine');e.add_argument('--cpu',choices=['68020','68040'],default='68040');e.add_argument('--archive',type=Path,help='Optional legacy provenance check; source is always engine/aga in this repository');e.add_argument('--out',type=Path,required=True);e.add_argument('--sdk',type=Path,required=True);e.add_argument('--vasm',type=Path,help='68000 preflight assembler; defaults to the SDK vasm')
    add_jobs(e)
    e.add_argument('--allow-compiler-warnings',action='store_true',help='Local experiments only: do not fail the build on compiler warnings')
    engine_profile.add_options(e)
    e.add_argument('--check-profiles',action='store_true',help='Gate check: also build every other engine profile (and c with its make variables spelled out) from the same source, each warning-free, link-map- and FPU-checked; recorded in engine-build.json')
    e.add_argument('--engine-experiment',action='append',choices=sorted(ENGINE_EXPERIMENTS),metavar='NAME',
                   help='EXPERIMENTAL engine compile switch, off by default (docs/EXPERIMENTAL_FLAGS.md): '
                        +', '.join('%s (%s)'%(k,v) for k,v in sorted(ENGINE_EXPERIMENTS.items())))
    e.add_argument('--coord-range',choices=('wide','narrow'),help="How the engine sends positions (tools/coord_range.py): wide (default, 24 bits of 1/256 units) or narrow (Quake's 1/8-unit shorts, -DAW_COORD_NARROW)")
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
    i.add_argument('--seyda-terrain-cull',choices=('on','off'),default='on',help='off: convert Seyda Neen without the terrain visual cull (a CHIM build: its Seyda Neen region maps are only a check reference for the frame maps and leave the image)')
    i.add_argument('--seyda-recorded',type=Path,help='Optional: user-provided recorded v0.0.31 Seyda Neen maps (tools/recorded_stage.py, BUILD-SEYDA-REGEN-30), kept byte for byte by every later pass; without it Seyda Neen is converted from the data files')
    i.add_argument('--canonical-land-source',type=Path,help='World-survey terrain-source.npz (survey_vvardenfell.py); required while Seyda terrain culling is enabled')
    i.add_argument('--world-terrain',type=Path,help='Complete validated refined terrain receipt and runtime directory, staged before scenery')
    i.add_argument('--exterior-terrain',type=Path,help='Prebuild ownership terrain receipt, required to bind never-compiled exterior maps at image finalization')
    i.add_argument('--world-scenery',type=Path,help='Complete validated full-world rock and giant-mushroom overlay directory; required except with --miniwind')
    i.add_argument('--miniwind',action='store_true',help='AmiWind "MiniWind" Playtester Build (tools/miniwind.py; tools/build.py --miniwind): a PARTIAL-AREA test image of Balmora on CHIM; private -devN versions only')
    i.add_argument('--miniwind-features',help='With --miniwind: the boot notice feature line tools/build.py generated from its stage plan ("FEATURES ONLY: ...")')
    i.add_argument('--miniwind-description',help='With --miniwind: optional "Scene:" line of the startup screen')
    i.add_argument('--miniwind-boot',metavar='CMD[;CMD]',help='With --miniwind: dbg commands run once on arrival')
    i.add_argument('--miniwind-town',help='With --miniwind: the town the image holds and boots into (default balmora)')
    i.add_argument('--miniwind-map-inspection',action='store_true',help='With --miniwind: direct inspection with god, noclip and debug HUD')
    i.add_argument('--miniwind-debug',action='store_true',help='With --miniwind: a DEBUG ONLY image, not a playtest')
    i.add_argument('--default-draw-distance',type=int,help='DEBUG ONLY (--miniwind-debug): the starting draw distance, '
                   '128..540 (default 540)')
    i.add_argument('--miniwind-scope',choices=('full','exterior','interior'),help='With --miniwind: full (default; Balmora exterior and interiors), exterior (the Balmora exterior only; implies --no-npc-gallery) or interior (the start room of an interior:<cell> start only)')
    i.add_argument('--world-flora',type=Path,help='Complete validated private world vegetation overlay; preserves rock/mushroom inputs')
    i.add_argument('--harvest',type=Path,help='Harvest source from harvest_build.py prepare (builder step harvest); the builder default')
    i.add_argument('--hand-catalog',type=Path,help='Per-race first-person hand catalogue from prepare_hand_catalog.py --runtime-palette; the builder default')
    i.add_argument('--chim-world',type=Path,help='CHIM world (tools/chim_build.py output: chim/, chim-receipt.json, '
                   'chim-validate.json, chim-stats.json), added as one more world volume; tools/build.py --builder chim')
    i.add_argument('--chim-lighting-type',default=None,help='With --chim-world: the CHIM lighting type (tools/chim/light_types.py); it selects the night lamp table classes (none: empty, lamps: the warm lamp classes, hybrid: every class that adds light); default: the legacy lamp table')
    i.add_argument('--town-flora-source-index',type=Path,help='Exact original Seyda scenery reference bindings for flora installation')
    i.add_argument('--town-flora-scene-report',type=Path,help='Original alias conversion model mapping; required with --world-flora')
    i.add_argument('--chim-rooms',dest='chim_rooms',type=Path,action='append',default=[],
                   help='The listed rooms of a CHIM-native town (tools/chim_rooms.py output), repeatable: their maps, '
                        'residents and room door banks, and the town door bank with the doors into them, installed '
                        'before the --chim-town outputs (BUILD-MINIWIND-ARENA-PIT-REFUSED-36)')
    i.add_argument('--chim-town',dest='chim_town',type=Path,action='append',default=[],
                   help='A CHIM town made from the game data (tools/chim_town.py output), repeatable: its residents, '
                        'region table and door bank are installed and its CHIM frame map takes its entities; the '
                        'town has no legacy region maps (CHIM-LEGACY-CHAIN-33)')
    i.add_argument('--retired-flags-used',metavar='TEXT',help='Set by tools/build.py when the build uses a flag retired '
                   'since CHIM v0.1.0 (tools/retired_flags.py): recorded in build.json retired_flags_used and printed loudly')
    i.add_argument('--night-lamp-lightmaps',action='store_true',help='EXPERIMENTAL (off by default): bake night-lamp '
                   'lightmaps (lightstyle 32) into the rebuilt Balmora cores (tools/lamp_lightmaps.py, prototype)')
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
    i.add_argument('--direct-start',metavar='START',
                   help='Quick test build (-devN only): boot straight into START (tools/direct_start.py forms); '
                        'resolved against the final maps and written to id1/miniwind.txt')
    i.add_argument('--quick-character',metavar='RACE,CLASS[,NAME]',
                   help='The ready-made character of the quick start (default: the Hors preset)')
    i.add_argument('--skip-census',action='store_true',
                   help='Quick test builds (-devN only): New Game makes the character on the quick character '
                        'screen, without the ship and the census (aw_skip_census 1 in default-game.cfg)')
    i.add_argument('--world-bounds',action='store_true',
                   help='The sea near the edge of the open world carries the player along it and back in '
                        '(aw_world_bounds 1 in default-game.cfg; tools/world_bounds.py, docs/WORLD_BOUNDS.md)')
    i.add_argument('--no-player-body',action='store_true',
                   help="No player body for the third-person view (tools/prepare_player_view.py; build.py --player-body off)")
    i.add_argument('--no-death-retry',action='store_true',
                   help='No quick retry after a lost fight (aw_death_retry 0 in default-game.cfg; build.py --death-retry off)')
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
