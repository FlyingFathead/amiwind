#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Independent, fail-closed check of packaged initial actor support.

Runs on the host after placement baking. Reads actual BSPs and quantized MDLs;
does not move actors. Only explicitly ground-classified initial states are held
to standing contact. Authored airborne/dead states are reported separately.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from actor_grounding import initial_state
from audit_walkability import Scene, axes
from player_hull import lumps
from actor_frames import MAX_FRAMES


def entities(raw):
    return [dict(re.findall(r'"([^"\n]+)"\s+"([^"\n]*)"', block))
            for block in re.findall(r'\{[^{}]*\}', lumps(raw)[0].decode('cp1252'))]


def model_frames(raw):
    """Decode final quantized alias positions; reject unsupported grouped poses."""
    if len(raw)<84:raise ValueError('Truncated actor model')
    h=struct.unpack_from('<4si3f3ff3f8if',raw)
    ns,w,height,nv,nt,nf=h[12:18]
    if h[:2]!=(b'IDPO',6) or not 0<nv<=1999 or not 0<nf<=MAX_FRAMES or not 0<ns<=32:
        raise ValueError('Unsupported actor model')
    if not 0<w<=4096 or not 0<height<=480 or not 0<nt<=4096:
        raise ValueError('Invalid actor model counts')
    if not all(math.isfinite(v) for v in h[2:8]) or min(h[2:5])<=0:
        raise ValueError('Invalid actor model transform')
    at=84
    for _ in range(ns):
        if struct.unpack_from('<i',raw,at)[0]:raise ValueError('Grouped skin needs a support decoder')
        at+=4+w*height
    at+=nv*12+nt*16;frames=[]
    for _ in range(nf):
        if struct.unpack_from('<i',raw,at)[0]:raise ValueError('Grouped frame needs a support decoder')
        at+=28;points=[]
        for i in range(nv):
            xyz=struct.unpack_from('<3B',raw,at+i*4)
            points.append(tuple(xyz[k]*h[2+k]+h[5+k] for k in range(3)))
        at+=nv*4;frames.append(points)
    if at!=len(raw):raise ValueError('Actor model length mismatch')
    return frames


def owner(maps, name, point):
    from town_config import runtime_towns
    for town in runtime_towns():
        area,prefix=town['name'],town['prefix']
        if name==area or re.fullmatch(prefix+r'\d{3}',name):
            directory=maps.parent/town['regions']
            if not directory.is_file():raise ValueError('Missing owner directory: '+area)
            for line in directory.read_text().splitlines()[1:]:
                v=line.split();x0,y0,x1,y1=map(float,v[1:5])
                if x0<=point[0]<x1 and y0<=point[1]<y1:
                    if not (maps/(v[0]+'.bsp')).is_file():raise ValueError('Missing owner BSP: '+v[0])
                    return v[0]
            raise ValueError('No owning core for actor in '+name)
    return name


def layout_idle(text):
    """(base, count) of the idle group in an animation kit layout (<model>.anm), or None when the layout
    has no idle group (ANIMKIT-GROUND-CHECK-LAYOUT-35). The layout is read by tools/actor_frames.py."""
    from actor_frames import parse
    return parse(text)[0].get('idle')


def resident_frames(raw, layout=None, intro=False):
    """A resident model's standing poses to check for ground contact: its idle group, as the model's
    frame layout declares it (tools/actor_frames.py: an animation kit layout <model>.anm beside the model,
    else the previous 8-frame idle or 21-frame town actor layout; anything else is refused)."""
    from actor_frames import of_model
    frames = model_frames(raw)
    return [frames[i] for i in of_model(len(frames), layout, intro).idle_range()]


def layout_of(model_path):
    """The animation kit layout beside a model (<model>.anm), or None."""
    from actor_frames import layout_text
    return layout_text(model_path)


def contact_samples(frames, angles, intro=False, layout=None):
    """Every distinct low rendered vertex in the supported initial idle poses.

    frames: a whole model's poses; its idle group comes from its frame layout (tools/actor_frames.py:
    the kit layout given as `layout`, else the previous 8 idle / 21 town actor layouts; the intro has
    eight idle poses followed by talk/walk poses). An undeclared layout is refused, never skipped.
    This tests low mesh contact, not semantic left/right foot IK or all animation.
    """
    from actor_frames import of_model
    frames=[frames[i] for i in of_model(len(frames), layout, intro).idle_range()]
    basis=axes(angles);samples={}
    for fi,points in enumerate(frames):
        low=min(p[2] for p in points)
        # A half-unit band includes the quantized soles without using the
        # collision-box minimum or mistaking a lowered origin for visible feet.
        for p in points:
            if p[2]>low+.5:continue
            world=tuple(sum(p[j]*basis[j][i] for j in range(3)) for i in range(3))
            key=tuple(round(v,5) for v in world)
            samples.setdefault(key,[]).append(fi)
    return samples


ACTOR_CLASSES = ('aw_npc', 'aw_corpse')
CONTACT_ERRORS = (ValueError, KeyError, OSError, struct.error)


def _scan_map(path):
    """Worker: one map's payload hash and its actor entities, in file order."""
    raw = Path(path).read_bytes()
    actors = [e for e in entities(raw) if e.get('classname') in ACTOR_CLASSES]
    return Path(path).name, hashlib.sha256(raw).hexdigest(), actors


def _measure_target(task):
    """Worker: every contact measurement whose canonical owner is one map.

    Returns per request ('ok', measured, failures) or ('error', message): the
    same values and messages the serial audit produced row by row.
    """
    path, requests = task
    scene = None
    results = []
    for point, samples in requests:
        try:
            measured = []
            failures = []
            for local, frames in samples:
                foot = tuple(point[k]+local[k] for k in range(3))
                if scene is None:  # built at the first sample, as the serial audit did
                    scene = Scene(Path(path).read_bytes(), hull=0)
                hit = scene.floor((foot[0], foot[1], foot[2]+2), 6)
                sample = dict(foot=foot, frames=sorted(set(frames)), support_status=hit['status'])
                if hit['status'] == 'supported':
                    sample.update(gap=foot[2]-hit['height'], support_reference=hit['reference'])
                    if sample['gap'] < -.5 or sample['gap'] > 1.0:
                        failures.append(sample)
                else:
                    failures.append(sample)
                measured.append(sample)
            results.append(('ok', measured, failures))
        except CONTACT_ERRORS as exc:
            results.append(('error', str(exc)))
    return results


def audit(maps, jobs=1):
    """Audit every packaged actor; jobs > 1 reads maps and measures in workers.

    Map reading/parsing and contact measurement are independent per map and run
    in the shared pool (tools/build_parallel.py). Canonical-owner selection,
    overlap-copy comparison, model hashing and row/error order stay serial in
    sorted map order: the first copy of a placement is the canonical one, and
    the receipt's key order is part of its bytes. Output equals jobs=1.
    """
    from build_parallel import ordered_map
    maps = Path(maps)
    paths = sorted(maps.glob('*.bsp'))
    rows = []; placements = {}; hashes = {}; copies = 0; owner_seen = set()
    model_cache = {}
    pending = {}

    def poses(name):
        p = Path(name)
        if p.is_absolute() or '..' in p.parts:
            raise ValueError('Unsafe actor model path')
        if name not in model_cache:
            raw = (maps.parent/p).read_bytes()
            hashes[name] = hashlib.sha256(raw).hexdigest()
            model_cache[name] = (model_frames(raw), layout_of(maps.parent/p))
        return model_cache[name]
    for name, sha, actors in ordered_map(_scan_map, paths, max(1, min(jobs, len(paths)))):
        stem = name[:-4]
        map_seen = set()
        hashes['maps/'+name] = sha
        for e in actors:
            copies += 1
            row = dict(map=stem, reference=e.get('aw_ref'), source_id=e.get('aw_source_id'),
                       name=e.get('netname'), model=e.get('model'))
            try:
                if not row['source_id']: raise ValueError('Missing original actor identity')
                state = initial_state(row['source_id']); row['initial_state'] = state
                if int(e.get('aw_ground_mode', -1)) != int(state != 'ground'):
                    raise ValueError('Entity support mode disagrees with classified source')
                if (e['classname'] == 'aw_corpse') != (state == 'authored_dead'):
                    raise ValueError('Death pose/classification mismatch')
                point = tuple(map(float, e['origin'].split())); angles = tuple(map(float, e.get('angles', '0 0 0').split()))
                if len(point) != 3 or len(angles) != 3 or not all(map(math.isfinite, point+angles)):
                    raise ValueError('Invalid actor transform')
                target = owner(maps, stem, point); row['owner'] = target
                identity = e.get('aw_ref') or ('intro:'+e.get('aw_intro_role', ''))
                key = (target, identity)
                if identity in map_seen: raise ValueError('Duplicate placed reference inside one scene')
                map_seen.add(identity)
                if stem == target: owner_seen.add(key)
                signature = (row['source_id'], row['model'], point, angles, state)
                if key in placements:
                    if signature != placements[key]: raise ValueError('Overlap copy differs from canonical placement')
                    continue
                placements[key] = signature; row['position'] = point
                if state != 'ground':
                    row['status'] = 'explicit-exception'; rows.append(row); continue
                frames, layout = poses(row['model'])
                samples = contact_samples(frames, angles, bool(float(e.get('aw_intro_role', 0))), layout)
                requests = pending.setdefault(target, [])
                row['_pending'] = (target, len(requests))
                requests.append((point, list(samples.items())))
            except CONTACT_ERRORS as exc:
                row.update(status='invalid', error=str(exc))
            rows.append(row)
    targets = sorted(pending)
    tasks = [(maps/(target+'.bsp'), pending[target]) for target in targets]
    measured = dict(zip(targets, ordered_map(_measure_target, tasks, max(1, min(jobs, len(tasks))))))
    errors = []
    for row in rows:
        if '_pending' in row:
            target, index = row.pop('_pending')
            result = measured[target][index]
            if result[0] == 'error':
                row.update(status='invalid', error=result[1])
            else:
                _, samples, failures = result
                gaps = [m['gap'] for m in samples if 'gap' in m]
                row.update(status='failed-contact' if failures else 'grounded', sample_count=len(samples),
                           minimum_gap=min(gaps) if gaps else None, maximum_gap=max(gaps) if gaps else None,
                           failures=failures)
                if failures:
                    errors.append(dict(**{k: row[k] for k in ('map', 'reference', 'source_id')},
                                       error='Initial mesh contact outside support tolerance'))
                continue
        if row.get('status') == 'invalid':
            errors.append(row.copy())
    if not copies: errors.append(dict(error='No actor placements found'))
    for key in sorted(placements.keys()-owner_seen):  # set order varies between runs
        errors.append(dict(owner=key[0], reference=key[1], error='Canonical owner omits its actor placement'))
    return dict(format=1, status='failed' if errors else 'passed', placement_copies=copies,
                distinct_placements=len(placements), summary=dict(Counter(r['status'] for r in rows)),
                tolerance={'minimum_gap': -.5, 'maximum_gap': 1.0, 'sole_band': .5},
                scope='Initial ground-resident idle poses, packaged point collision, explicit source classification; no moving platforms, footsteps, IK or future animation proof.',
                rows=rows, errors=errors, payload_sha256=hashes)


def load_approved_report(path):
    """Read an explicit owner baseline; only ordinary contact findings qualify."""
    raw = Path(path).read_bytes()
    report = json.loads(raw)
    if (report.get('format') != 1 or report.get('status') != 'failed'
            or not report.get('errors') or not report.get('payload_sha256')
            or report.get('tolerance') != {'minimum_gap': -.5, 'maximum_gap': 1.0, 'sole_band': .5}
            or any(row.get('status') == 'invalid' for row in report.get('rows', []))
            or any(error.get('error') != 'Initial mesh contact outside support tolerance'
                   for error in report['errors'])):
        raise ValueError('Approved report must contain only unresolved mesh-contact findings')
    return report, hashlib.sha256(raw).hexdigest()


FINDINGS_SCOPE = ('actor findings: every row (map, reference, pose samples, gaps, support), every '
                  'error and the counts equal the approved audit; payload hashes not compared '
                  '(image assembly rewrites map and model bytes; world maps were never approved findings)')


def evidence(report, before_world=False, findings_only=False):
    # The early check has no vf terrain yet; it compares every other payload hash.
    # findings_only (image step, private test): the owner approved the findings,
    # not the bytes of maps that image assembly rewrites. Every row and error is
    # still compared exactly; never reduce the comparison to a count.
    view = dict(report)
    if findings_only:
        view.pop('payload_sha256', None)
    elif before_world:
        view['payload_sha256'] = {name: value for name, value in report['payload_sha256'].items()
                                 if not re.fullmatch(r'maps/vf[0-9]{4}\.bsp', name)}
    return json.dumps(view, sort_keys=True, separators=(',', ':'), allow_nan=False)


def require(maps, output, allow_known=None, before_world=False, findings_only=False, jobs=1):
    approved = None
    if before_world and findings_only:
        raise ValueError('Choose one actor comparison scope')
    if allow_known:
        if Path(allow_known).resolve() == Path(output).resolve():
            raise ValueError('Approved actor report must be separate from the new audit output')
        approved, approved_hash = load_approved_report(allow_known)
    report = audit(maps, jobs=jobs)
    raw = json.dumps(report, indent=2) + '\n'
    Path(output).write_bytes(raw.encode('utf-8'))
    acceptance = {'status': 'passed', 'unresolved': len(report['errors']),
                  'production_gate_passed': report['status'] == 'passed',
                  'report_sha256': hashlib.sha256(raw.encode('utf-8')).hexdigest(),
                  'comparison_scope': ('before-world; vf payload not yet present' if before_world else
                                       FINDINGS_SCOPE if findings_only else 'complete packaged BSP/actor payload')}
    if report['status'] != 'passed':
        if approved is None:
            raise ValueError(f"Actor placement gate failed: {len(report['errors'])} unresolved cases; see {output}")
        if evidence(report, before_world, findings_only) != evidence(approved, before_world, findings_only):
            raise ValueError(f'Actor report differs from approved baseline; refusing private-test waiver; see {output}')
        acceptance.update(status='owner-accepted-known-findings', approved_report_sha256=approved_hash)
        print(f"WARNING: PRIVATE TEST ONLY: {len(report['errors'])} unchanged actor-contact findings accepted explicitly. Production actor gate DID NOT PASS.", flush=True)
    # Keep the on-disk audit unmodified and failed. Acceptance is separate evidence.
    report['acceptance'] = acceptance
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('maps',type=Path);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();require(a.maps,a.out)


if __name__=='__main__':main()
