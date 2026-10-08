#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Partition the existing Seyda Neen conversion; preserve its meshes and hulls."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import os
import shutil
from itertools import product
from audit_walkability import axes
from compact_bsp import compact, entities
from player_hull import lumps
from prepare_intro_docks import derive
from prepare_quake import GROUND_BOUNDS

CORE=768
OVERLAP=896
HYSTERESIS=96
DRAW_DISTANCE=540
# Include the existing world enclosure; partial edge cores remain explicit.
BOUNDS=((-2079,-2079),(2079,2079))
COURTYARD=(-128,-384,512,256)


LAYOUT = Path(__file__).resolve().parents[1]/'config/seyda-bounded-regions.json'


def validate_layout(settings):
    if settings.get('format') != 'AmiWind Seyda bounded layout 1':
        raise ValueError('Unknown bounded Seyda layout')
    if (settings.get('overlap'), settings.get('hysteresis'), settings.get('draw_distance')) != (OVERLAP,HYSTERESIS,DRAW_DISTANCE):
        raise ValueError('Seyda visibility/hysteresis policy changed')
    if settings.get('bounds') != [list(v) for v in BOUNDS]:
        raise ValueError('Seyda ownership bounds changed')
    entries = settings['regions']
    if not 1 <= len(entries) <= 64:
        raise ValueError('Invalid native Seyda region count')
    for index, entry in enumerate(entries):
        if entry['name'] != f'sn{index:03d}':
            raise ValueError('Region names must follow runtime directory order')
        core = entry['core']
        if len(core)!=2 or any(len(p)!=2 for p in core) or not all(math.isfinite(v) for p in core for v in p):
            raise ValueError('Invalid finite core coordinates')
        if any(not BOUNDS[0][i] <= core[0][i] < core[1][i] <= BOUNDS[1][i] for i in range(2)):
            raise ValueError('Core outside ownership bounds')
        coverage = [[min(core[0][i],max(GROUND_BOUNDS[0][i],core[0][i]-OVERLAP)) for i in range(2)],
                    [max(core[1][i],min(GROUND_BOUNDS[1][i],core[1][i]+OVERLAP)) for i in range(2)]]
        if entry['coverage'] != coverage:
            raise ValueError('Coverage differs from the required 896-unit apron')
    # Every rectangle tile induced by all cuts must have exactly one owner.
    cuts = [sorted({BOUNDS[0][i],BOUNDS[1][i]} | {e['core'][j][i] for e in entries for j in (0,1)}) for i in range(2)]
    for x0,x1 in zip(cuts[0],cuts[0][1:]):
        for y0,y1 in zip(cuts[1],cuts[1][1:]):
            point = ((x0+x1)/2,(y0+y1)/2)
            count = sum(all(e['core'][0][i] <= point[i] < e['core'][1][i] for i in range(2)) for e in entries)
            if count != 1:
                raise ValueError('Seyda ownership hole or overlapping cores')
    if OVERLAP < math.sqrt(2)*DRAW_DISTANCE+HYSTERESIS+32:
        raise ValueError('Insufficient visibility/hysteresis coverage')
    return entries


def regions():
    return validate_layout(json.loads(LAYOUT.read_text(encoding='utf-8')))


def default_region(entries):
    return next(e for e in entries if all(e['core'][0][i] <= 0 < e['core'][1][i] for i in range(2)))


def directory_text(entries):
    rows=['AWBR1 '+ ' '.join(map(str,[len(entries),HYSTERESIS,DRAW_DISTANCE,0,0,64,90,0,0,64,90]))]
    for entry in entries:
        rows.append(' '.join(map(str,[entry['name'],*entry['core'][0],*entry['core'][1],*entry['coverage'][0],*entry['coverage'][1]])))
    return '\n'.join(rows)+'\n'


def select(raw, bounds, polygon=None):
    data=lumps(raw);models=list(struct.iter_unpack('<9f7i',data[14]));kept=[]
    low,high=bounds
    for e in entities(data[0]):
        if e.get('classname') not in ('func_wall','aw_static'):
            # Stable NPC identities remain available for restoration; the runtime
            # discards actors whose restored positions lie outside this region.
            kept.append(e);continue
        origin=[float(v) for v in e.get('origin','0 0 0').split()]
        if len(origin)!=3 or not all(math.isfinite(v) for v in origin):raise ValueError('Invalid entity position')
        a=[v-96 for v in origin];b=[v+96 for v in origin]
        if e.get('model','').startswith('*'):
            m=models[int(e['model'][1:])];basis=axes(tuple(map(float,e.get('angles','0 0 0').split())))
            points=[[origin[i]+sum(v[j]*basis[j][i] for j in range(3)) for i in range(3)]
                    for v in product(*[(m[j],m[j+3]) for j in range(3)])]
            a=[min(v[i] for v in points) for i in range(3)];b=[max(v[i] for v in points) for i in range(3)]
        if not all(b[i]>=low[i] and a[i]<=high[i] for i in range(2)):continue
        if polygon:
            corners=list(product((a[0],b[0]),(a[1],b[1])))
            # CCW convex polygon: reject only when the whole placed AABB is
            # outside one boundary. Keep complete intersecting objects.
            if any(all((q[0]-p[0])*(v[1]-p[1])-(q[1]-p[1])*(v[0]-p[0])<0 for v in corners)
                   for p,q in zip(polygon,polygon[1:]+polygon[:1])):continue
        kept.append(e)
    return kept


def _build_region(task):
    """Worker: compile, verify and terrain-cull one bounded Seyda region.

    Reads the shared complete town (task['original']) and writes only its own
    work directory; returns (candidate path, receipt) as the serial loop did.
    """
    from prepare_bounded_world import build_candidate
    from terrain_visual_cull import resolve_policy
    from cull_bsp_terrain import cull_bsp
    from vis_options import vis_kwargs
    name, coverage, core = task['name'], task['coverage'], task['core']
    original, work = Path(task['original']), Path(task['work'])
    raw = original.read_bytes()
    result=build_candidate(Path(task['source_map']),original,original,Path(task['palette']),coverage,work/name,
                           Path(task['ericw_bin']),task['target_sizes'],core=core,threads=task['threads'],
                           **vis_kwargs(task['vis_mode']))
    output=Path(result['candidate_path'])
    if hashlib.sha256(output.read_bytes()).hexdigest()!=result['candidate_sha256']:
        raise ValueError('Bounded candidate receipt mismatch: '+name)
    policy=resolve_policy(task['terrain_cull_config'],map_identity=name,cell_identity='Seyda Neen',
                          subcell_identity=name if name.startswith('sn') and name[2:].isdigit() else None,
                          force=task['terrain_visual_cull'],overlap_force=task['terrain_cull_overlap'])
    culled,cull_receipt=cull_bsp(output.read_bytes(),policy,terrain_reference=raw,
        terrain_reference_metadata={'scope':'complete unculled town LAND; same compiled world coordinates',
            'path':str(original),'sha256':hashlib.sha256(raw).hexdigest()},
        canonical_land_source=task['canonical_land_source'],canonical_origin=task['canonical_origin'],
        require_canonical=True)
    original_output=output
    if not cull_receipt.get('unchanged'):
        output=work/name/'terrain-culled.bsp'
        if output.exists():raise ValueError('Terrain candidate output already exists')
        output.write_bytes(culled)
    (work/name/'terrain-cull.json').write_text(json.dumps(cull_receipt,indent=2)+'\n',encoding='utf-8')
    if cull_receipt.get('acceptance','').startswith('INCOMPLETE'):
        raise ValueError('Canonical cut diagnostic saved at '+str(output)+'; unresolved LAND render/physics alignment blocks region installation')
    result={**result,'pre_cull_candidate_path':str(original_output),
            'pre_cull_candidate_sha256':result['candidate_sha256'],
            'candidate_path':str(output),'candidate_sha256':hashlib.sha256(culled).hexdigest(),
            'terrain_visual_cull':cull_receipt,
            'validation_scope':'Bounded-builder metrics are before terrain culling; final candidate gates required'}
    return str(output),result


def convert(source, destination, *, source_map, palette, ericw_bin,
            target_sizes=None, threads=None, work_dir=None, terrain_visual_cull=None,
            terrain_cull_config=None, terrain_cull_overlap=None, canonical_land_source=None,
            vis_mode='fast', jobs=None):
    """Generate actual bounded terrain/PVS; never retain the full-town world.

    This normal build step invokes the configured terrain tools when called.
    Source-only/fixture checks must mock the builder, not launch those tools.
    All region generation finishes before the runtime map set is installed.
    """
    from terrain_visual_cull import resolve_policy
    if terrain_cull_config is None:
        config_path=Path(__file__).resolve().parents[1]/'config/terrain-visual-cull.json'
        terrain_cull_config=json.loads(config_path.read_text(encoding='utf-8'))
    identities=[e['name'] for e in regions()]+['intro_docks','sncourt']
    enabled=any(resolve_policy(terrain_cull_config,map_identity=name,cell_identity='Seyda Neen',
        subcell_identity=name if name.startswith('sn') and name[2:].isdigit() else None,
        force=terrain_visual_cull,overlap_force=terrain_cull_overlap)['enabled'] for name in identities)
    canonical_origin=None
    if enabled:
        if canonical_land_source is None:
            raise ValueError('Enabled Seyda culling requires --canonical-land-source; no local BSP fallback')
        area=json.loads((Path(__file__).resolve().parents[1]/'config/seyda_area.json').read_text(encoding='utf-8'))
        if area['scale']!=0.25:raise ValueError('Unsupported canonical source scale')
        canonical_origin=[float(v)*area['scale'] for v in area['centre']]+[0.0]
        from canonical_land_reference import CanonicalLand
        CanonicalLand(canonical_land_source,canonical_origin)  # validate before any build or write
    source=Path(source);destination=Path(destination)
    destination.mkdir(parents=True,exist_ok=True)
    entries=regions();raw=source.read_bytes()
    work=Path(work_dir) if work_dir else destination.parent/'seyda-bounded-work'
    work.mkdir(parents=True,exist_ok=False)
    # Keep the complete scene available throughout generation and outside maps/.
    original=work/'source-town.bsp';original.write_bytes(raw)
    palette=Path(palette);source_map=Path(source_map)
    reports=[];outputs={}
    # Every region compiles independently (own work directory, read-only shared
    # inputs): up to `jobs` regions at once in the shared pool, vis threads
    # sharing the budget, light single-threaded (reproducible). Results are
    # consumed in the serial order, so receipts and maps equal jobs=1.
    from build_parallel import ordered_map
    from build_jobs import resolve_jobs
    from vis_options import map_threads
    specials=[('intro_docks',(-240,-1100,1120,620)),('sncourt',COURTYARD)]
    jobs=resolve_jobs(jobs if jobs is not None else threads)
    plan=[(entry['name'],entry['coverage'],entry['core']) for entry in entries]+[
          (name,[list(bounds[:2]),list(bounds[2:])],None) for name,bounds in specials]
    concurrent=max(1,min(jobs,len(plan)))
    vis_threads=map_threads(jobs,concurrent)
    common=dict(source_map=str(source_map),original=str(original),palette=str(palette),work=str(work),
                ericw_bin=str(ericw_bin),target_sizes=target_sizes,threads=vis_threads,vis_mode=vis_mode,
                terrain_cull_config=terrain_cull_config,terrain_visual_cull=terrain_visual_cull,
                terrain_cull_overlap=terrain_cull_overlap,canonical_land_source=canonical_land_source,
                canonical_origin=canonical_origin)
    built=dict(zip([name for name,_,_ in plan],ordered_map(_build_region,
               [dict(common,name=name,coverage=coverage,core=core) for name,coverage,core in plan],concurrent)))
    def build(name, coverage, core=None):
        output,result=built[name]
        return Path(output),result
    for entry in entries:
        output,result=build(entry['name'],entry['coverage'],entry['core'])
        outputs[entry['name']]=output
        reports.append(dict(name=entry['name'],core=entry['core'],coverage=entry['coverage'],bounded=result))
    # Keep established special map names, route/courtyard selection, actor
    # pruning and standing-hull boundaries. Only their parent world is replaced
    # by a genuinely bounded terrain BSP before applying those existing masks.
    for name,bounds in specials:
        coverage=[list(bounds[:2]),list(bounds[2:])]
        output,result=build(name,coverage)
        masked,mask_report=derive(output.read_bytes(),bounds)
        polygon=[(440+680*math.cos(i*math.pi/4),-240+860*math.sin(i*math.pi/4)) for i in range(8)] if name=='intro_docks' else None
        converted,selection=compact(masked,select(masked,coverage,polygon),prune_world=True)
        final=work/name/'special.bsp';final.write_bytes(converted)
        outputs[name]=final
        reports.append(dict(name=name,coverage=coverage,bounded=result,mask=mask_report,selection=selection,
                            final_sha256=hashlib.sha256(converted).hexdigest()))
    fallback=default_region(entries)['name']
    outputs['seyda']=outputs[fallback]
    for name,output in outputs.items():
        temporary=destination/(name+'.bsp.staging')
        shutil.copyfile(output,temporary)
        os.replace(temporary,destination/(name+'.bsp'))
    (destination.parent/'seyda-regions.txt').write_text(directory_text(entries),encoding='ascii',newline='\n')
    report={'format':'AmiWind bounded Seyda regions 1','regular_regions':len(entries),
            'source_sha256':hashlib.sha256(raw).hexdigest(),
            'source_map_sha256':hashlib.sha256(source_map.read_bytes()).hexdigest(),
            'palette_sha256':hashlib.sha256(palette.read_bytes()).hexdigest(),
            'layout_sha256':hashlib.sha256(LAYOUT.read_bytes()).hexdigest(),
            'complete_source_preserved':str(original),'fallback_alias':fallback,
            'overlap':OVERLAP,'hysteresis':HYSTERESIS,'draw_distance':DRAW_DISTANCE,
            'world_terrain':'independently compiled bounded LAND/PVS with complete intersecting triangles',
            'special_routes':'existing names, selection masks and standing boundaries retained',
            'acceptance':'final actor/heap gates and target transition playtest required','regions':reports}
    (destination.parent/'seyda-regions.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


def convert_builder_scene(maps, *, scene_map, palette, ericw_bin, work_dir,
                          canonical_land_source=None, vis_mode='fast', jobs=None, recorded=None):
    """The builder's one Seyda region conversion (actor preflight and image).

    Replaces maps/seyda.bsp, the complete converted town, by the bounded
    regions. Both builder stages call this, so a convert() signature change
    reaches them together (BUILD-ACTOR-CONTACT-CALL-32). With `recorded`
    (--seyda-recorded), the recorded-stage exception BUILD-SEYDA-REGEN-30
    installs the owner's recorded maps instead (tools/recorded_stage.py).
    """
    maps=Path(maps)
    if recorded is not None:
        from recorded_stage import install
        return install(recorded,maps,work_dir=work_dir,jobs=jobs)
    return convert(maps/'seyda.bsp',maps,source_map=scene_map,palette=palette,ericw_bin=ericw_bin,
                   jobs=jobs,work_dir=work_dir,vis_mode=vis_mode,
                   canonical_land_source=canonical_land_source)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path);p.add_argument('destination',type=Path)
    p.add_argument('--source-map',type=Path,required=True)
    p.add_argument('--palette',type=Path,required=True)
    p.add_argument('--ericw-bin',type=Path,required=True)
    p.add_argument('--threads','--jobs',dest='threads',type=int,help='Worker budget (default: auto)')
    p.add_argument('--terrain-visual-cull',choices=('true','false'))
    p.add_argument('--terrain-cull-overlap',type=float)
    p.add_argument('--terrain-cull-config',type=Path)
    p.add_argument('--canonical-land-source',type=Path)
    from vis_options import add_vis_option
    add_vis_option(p)
    a=p.parse_args()
    r=convert(a.source,a.destination,source_map=a.source_map,palette=a.palette,
              ericw_bin=a.ericw_bin,threads=a.threads,
              terrain_visual_cull=None if a.terrain_visual_cull is None else a.terrain_visual_cull=='true',
              terrain_cull_overlap=a.terrain_cull_overlap,canonical_land_source=a.canonical_land_source,
              vis_mode=a.vis_mode,
              terrain_cull_config=json.loads(a.terrain_cull_config.read_text(encoding='utf-8')) if a.terrain_cull_config else None)
    print(f"Prepared {r['regular_regions']} bounded regions plus special scenes and fallback.")
