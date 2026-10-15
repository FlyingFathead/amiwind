# SPDX-License-Identifier: GPL-3.0-only
"""Character animation kit: which original animation groups an actor model
carries, sampled once on the shared skeleton (docs/ANIMATION.md).

Quake mechanism: an alias model's vertex frames, played by changing
self.frame (QuakeC) or edict frame (C). The kit decides the frame list:

* groups come from the skeleton's text keys ('walkforward: loop start' ...);
  every part of an actor is posed at the same sample times, so frame i of
  every part is the same pose (docs/MODULAR_NPCS.md, frames shared by
  construction);
* moving loops are sampled in place: the accumulating root bone (Bip01) keeps
  its idle x, y, as the original engine removes the root's horizontal motion
  and moves the actor instead; the removed motion is the group's own speed,
  used by the engine to match the playback rate to the actor's real speed;
* female humans take the groups their own skeleton file overrides
  (base_anim_female.nif: walkforward) from that file, as the original layers it;
* 'soundgen: X' and 'sound: X' keys inside a group become frame events, and
  the actor's footstep sounds are resolved from its boots (armour weight class)
  and water, as the original resolves them.

Output per model: the times to pose (fed to npc_geometry.assemble), a layout
string (group frame ranges, steps, speeds, events, sounds; written beside the
model as <model>.anm) and the sound files it needs.

Profiles (config/npc-anim-kit.json): 'idle' is the previous method (8 idle
frames, byte-identical models); the others add groups. Selected by
AMIWIND_NPC_ANIM (build.py --npc-anim).
"""
import io
import json
import os
import struct
import wave
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'config/npc-anim-kit.json'
ENV = 'AMIWIND_NPC_ANIM'
SCALE = 0.25
ROOT_BONE = 'bip01'
FEMALE_SKELETON = 'meshes/base_anim_female.nif'

# Group -> (start key, stop key, kind, moves). kind: loop (cycles), once (plays
# and returns), hold (plays and holds its final pose: death).
GROUPS = {
    'idle': ('idle: start', 'idle: stop', 'loop', False),
    'walk': ('walkforward: loop start', 'walkforward: loop stop', 'loop', True),
    'run': ('runforward: loop start', 'runforward: loop stop', 'loop', True),
    'swim': ('swimwalkforward: loop start', 'swimwalkforward: loop stop', 'loop', True),
    'swimidle': ('idleswim: start', 'idleswim: stop', 'loop', False),
    'hit': ('hit1: start', 'hit1: stop', 'once', False),
    'knock': ('knockdown: start', 'knockdown: stop', 'once', False),
    'death': ('death1: start', 'death1: stop', 'hold', False),
    'attack': ('handtohand: chop start', 'handtohand: chop large follow stop', 'once', False),
    # Shield block (base_anim 'shield' group: block start, block hit, block stop; OpenMW plays it on a
    # successful block, CharacterController::refreshHitRecoilAnims). X = the 'block hit' fraction.
    'block': ('shield: block start', 'shield: block stop', 'once', False),
    # Dodge: an AmiWind extension (Morrowind has no dodge group): a quick sidestep, the walk-left and
    # walk-right loops sampled in place; the combat code moves the actor sideways through collision.
    'dodgel': ('walkleft: loop start', 'walkleft: loop stop', 'once', True),
    'dodger': ('walkright: loop start', 'walkright: loop stop', 'once', True),
    # Player jump sections. The owned human/beast loop markers coincide:
    # takeoff holds loop start until contact, then landing plays to stop.
    'jump': ('jump: start', 'jump: loop start', 'hold', False),
    'land': ('jump: loop stop', 'jump: stop', 'hold', False),
    # The player's hand-to-hand stance has its own authored locomotion. Keep
    # the complete moving pose; a standing upper-body pose cannot replace it.
    'ready': ('idlehh: start', 'idlehh: stop', 'loop', False),
    'readywalk': ('walkforwardhh: loop start', 'walkforwardhh: loop stop', 'loop', True),
    'readyrun': ('runforwardhh: loop start', 'runforwardhh: loop stop', 'loop', True),
    'readyjump': ('jumphh: start', 'jumphh: loop start', 'hold', False),
    'readyland': ('jumphh: loop stop', 'jumphh: stop', 'hold', False),
}
AIR_GROUPS = ('jump', 'land', 'readyjump', 'readyland')
ATTACK_HIT = 'handtohand: chop hit'
BLOCK_HIT = 'shield: block hit'
# Sound events an NPC uses (OpenMW Npc::getSoundIdFromSndGen: NPCs ignore
# land/moan/roar/scream text keys; creatures use SNDG records instead).
NPC_EVENTS = ('left', 'right')
FOOT = {'bare': 'FootBare', 'light': 'FootLight', 'medium': 'FootMed', 'heavy': 'FootHeavy'}
LAYOUT_VERSION = 1


def profiles():
    data = json.loads(CONFIG.read_text(encoding='utf-8'))
    if data.get('version') != LAYOUT_VERSION:
        raise ValueError('Unsupported animation kit config version')
    for name, groups in data['profiles'].items():
        if not groups or groups[0][0] != 'idle' or groups[0][1] != 8:
            raise ValueError(f'Animation profile {name}: the first group must be 8 idle frames')
        for group, count in groups:
            if group not in GROUPS or not 1 <= int(count) <= 16:
                raise ValueError(f'Animation profile {name}: bad group {group}:{count}')
        if sum(c for _, c in groups) > 64:
            raise ValueError(f'Animation profile {name}: more than 64 frames')
    return data['profiles']


def selected_profile(name=None):
    """(name, groups to sample) of AMIWIND_NPC_ANIM: a profile, or STANDING+MOVER ('react+full')."""
    name = name or os.environ.get('AMIWIND_NPC_ANIM', '').strip() or 'idle'
    return name, plan_profile(name)


class KitSkeleton:
    """Posing by sample index: sample i is (skeleton, time, fixed root x, y or None).

    npc_geometry.assemble only needs .N and .pose(t); passing the sample index
    as the time lets one model mix skeleton files and in-place loops."""

    def __init__(self, base, samples):
        self.N = base.N
        self.base = base
        self.samples = samples

    def pose(self, index):
        skeleton, time, fixed = self.samples[int(index)]
        matrices = {}

        def world(name):
            name = name.casefold()
            if name not in matrices:
                parent = skeleton.parents[name]
                local = skeleton.local(name, time)
                if fixed is not None and name == ROOT_BONE:
                    local = local.copy()
                    local[3, :2] = fixed
                matrices[name] = local @ (world(parent) if parent else np.eye(4))
            return matrices[name]
        return world


class BoneLayer:
    """Offline local-bone overlay, keeping the underlying pose outside a mask.

    This is the guard torch's left-clavicle method generalized to other masks
    (for example Bip01 Spine1 for equip/lower). It only bakes alias vertices;
    no skeletal evaluation is added to the engine. `normal` is a world-pose
    callable, so a female override's different file root remains untouched.
    """

    def __init__(self, skeleton, roots):
        self.skeleton = skeleton
        roots = frozenset(name.casefold() for name in roots)
        if not roots or not roots <= skeleton.nodes.keys():
            raise ValueError('Missing animation layer root')
        self.mask = {}
        active = set()

        def includes(name):
            if name not in self.mask:
                if name in active:
                    raise ValueError('Cyclic animation layer hierarchy')
                if name not in skeleton.parents:
                    raise ValueError('Missing animation layer parent: ' + name)
                active.add(name)
                parent = skeleton.parents[name]
                inherited = includes(parent) if parent else False
                self.mask[name] = name in roots or inherited
                active.remove(name)
            return self.mask[name]
        for name in skeleton.nodes:
            includes(name)

    def pose(self, normal, time):
        if not np.isfinite(time):
            raise ValueError('Non-finite animation layer time')
        matrices = {}

        def world(name):
            name = name.casefold()
            if name not in matrices:
                if self.mask.get(name, False):
                    parent = self.skeleton.parents[name]
                    matrices[name] = self.skeleton.local(name, time) @ (world(parent) if parent else np.eye(4))
                else:
                    # At the mask boundary retain the entire underlying world
                    # matrix, not the layer skeleton's file-root transform.
                    matrices[name] = normal(name)
            return matrices[name]
        return world


def _window(skeleton, group, attack_stance=None):
    start, stop, _, _ = GROUPS[group]
    if group == 'attack' and attack_stance:
        start = attack_stance + ': chop start'
        stop = attack_stance + ': chop large follow stop'
    ev = skeleton.events
    if start in ev and stop in ev and ev[stop] > ev[start]:
        return ev[start], ev[stop]
    return None


def plan(base, profile, female=None, weight=1.0, attack_stance=None, player_block_hit=False):
    """Sample plan for one skeleton and profile.

    base: npc_geometry.Skeleton of the actor's skeleton file; female: the female
    override Skeleton or None. Returns (KitSkeleton, groups) where groups is a
    list of dicts: name, base frame, count, step, speed (Quake units/s, moving
    loops), hit (attack), events [(offset, event)], source ('base'|'female'|
    'idle' when the skeleton lacks the group and idle frames stand in)."""
    idle = _window(base, 'idle')
    if attack_stance not in (None, 'weapontwowide'):
        raise ValueError('Unsupported resident attack stance')
    if idle is None:
        raise ValueError('Skeleton has no idle group')
    root_xy = base.local(ROOT_BONE, idle[0])[3, :2].copy() if ROOT_BONE in base.nodes else None
    samples, groups = [], []
    for name, count in profile:
        count = int(count)
        kind, moves = GROUPS[name][2], GROUPS[name][3]
        skeleton, source = base, 'base'
        if female is not None and _window(female, name, attack_stance) is not None:
            skeleton, source = female, 'female'
        window = _window(skeleton, name, attack_stance)
        if name == 'attack' and attack_stance and window is None:
            raise ValueError('Missing authored resident attack stance: ' + attack_stance)
        entry = {'name': name, 'base': len(samples), 'count': count, 'kind': kind, 'source': source, 'events': []}
        if window is None:
            # A missing group repeats the idle start (OpenMW falls back to idle).
            a, b = idle
            times = [a] * count
            entry.update(step=(b - a) / 8, source='idle')
        else:
            a, b = window
            if kind == 'hold':
                times = list(np.linspace(a, b, count - 1, endpoint=False)) + [b] if count > 1 else [b]
                step = (b - a) / max(1, count - 1)
            else:
                times = list(np.linspace(a, b, count, endpoint=False))
                step = (b - a) / count
            entry['step'] = step
            if moves and ROOT_BONE in skeleton.nodes:
                ya = skeleton.local(ROOT_BONE, a)[3, :2]
                yb = skeleton.local(ROOT_BONE, b)[3, :2]
                entry['speed'] = float(np.linalg.norm(yb - ya) / (b - a) * SCALE * weight)
            if name in ('attack', 'block'):
                hit = skeleton.events.get((attack_stance + ': chop hit' if attack_stance else ATTACK_HIT)
                                          if name == 'attack' else BLOCK_HIT)
                entry['hit'] = (hit - a) / (b - a) if hit is not None and a <= hit <= b else .5
                if name == 'block' and player_block_hit:
                    # The player fitter explicitly retains START and exact HIT.
                    # NPC plans keep their historical sampling unchanged.
                    if count != 5 or hit is None or not a < hit < b:
                        raise ValueError('Player block pair requires five source slots and an authored hit')
                    times[1] = hit
                    entry['player_block_hit_source'] = 1
                    entry['player_block_hit_time'] = float(hit)
            for t, line in skeleton.keys:
                if not a <= t < b + 1e-6:
                    continue
                if line.startswith('soundgen:'):
                    event = line.split(':', 1)[1].split()[0] if line.split(':', 1)[1].split() else ''
                elif line.startswith('sound:'):
                    event = 'sound:' + line.split(':', 1)[1].strip()
                else:
                    continue
                offset = int(np.floor((t - a) / step + .5)) if step > 0 else 0
                offset = offset % count if kind == 'loop' else min(offset, count - 1)
                entry['events'].append((offset, event))
        fixed = root_xy if (moves and source != 'idle') else None
        samples.extend((skeleton, float(t), fixed) for t in times)
        groups.append(entry)
    if groups[0]['name'] != 'idle':
        raise ValueError('Idle frames must come first')
    return KitSkeleton(base, samples), groups


def idle_compatible_times(groups):
    """Times for assemble(): sample indices."""
    return np.arange(sum(g['count'] for g in groups), dtype=float)


PLAYER_LAYER_MOTION = ('idle', 'walk', 'run', 'jump', 'land')
PLAYER_READY_MOTION = ('ready', 'readywalk', 'readyrun', 'readyjump', 'readyland')
PLAYER_LAYER_ACTIONS = ((1, 'draw', 'equip'), (4, 'lower', 'unequip'))
PLAYER_COMPACT_ACTIONS = ((1, 'draw', 'equip'), (4, 'lower', 'unequip'), (3, 'punch', 'chop'))


class PlayerLayerSkeleton:
    """Prebaked movement x arm-phase grid; the runtime still selects one alias frame."""
    def __init__(self, normal, samples):
        self.N = normal.N
        self.normal = normal
        self.samples = samples
        self.layer = BoneLayer(normal.base, ('bip01 spine1',))

    def pose(self, index):
        motion, time = self.samples[int(index)]
        normal = self.normal.pose(motion)
        return normal if time is None else self.layer.pose(normal, time)


def player_layers(normal, groups, phases=3, compact=False):
    """Append original bare-hand draw/lower over each normal movement pose.

    Both arm endpoints are retained. QuakeC owns the elapsed action fraction;
    movement uses its own advancing frame, including takeoff/landing. No root
    motion, legs, collision or first-person timing is replaced by the overlay.
    """
    if not 2 <= phases <= 8:
        raise ValueError('Player layer needs 2..8 arm phases')
    by_name = {g['name']: g for g in groups}
    required = PLAYER_LAYER_MOTION + (PLAYER_READY_MOTION if compact else ())
    if any(n not in by_name or by_name[n]['source'] == 'idle' for n in required):
        raise ValueError('Player layer missing original movement section')
    samples = [(i, None) for i in range(sum(g['count'] for g in groups))]
    out = list(groups)
    for action, name, section in (PLAYER_COMPACT_ACTIONS if compact else PLAYER_LAYER_ACTIONS):
        ev = normal.base.events
        stop = 'handtohand: chop large follow stop' if action == 3 else 'handtohand: ' + section + ' stop'
        a, b = ev.get('handtohand: ' + section + ' start'), ev.get(stop)
        if a is None or b is None or not np.isfinite((a, b)).all() or not 0 < b-a <= 60:
            raise ValueError('Missing or invalid original handtohand ' + section)
        hit = ev.get(ATTACK_HIT) if action == 3 else None
        if action == 3 and (hit is None or not a < hit < b):
            raise ValueError('Missing or invalid original handtohand chop hit')
        arm_times = (a, hit, b) if action == 3 else ((a, b) if compact else np.linspace(a, b, phases))
        for motion in (PLAYER_READY_MOTION if action == 3 else PLAYER_LAYER_MOTION):
            g = by_name[motion]
            motion_samples = (min(2, g['count']) if motion in ('walk', 'run', 'readywalk', 'readyrun') else 1) if compact else g['count']
            motion_indices = [i*g['count']//motion_samples for i in range(motion_samples)]
            out.append(dict(name=name+'_'+motion, base=len(samples), count=len(arm_times)*motion_samples,
                            kind='hold', step=(b-a)/(len(arm_times)-1), source='base-layer', events=[],
                            layer_action=action, motion_name=motion, motion_count=motion_samples,
                            phases=len(arm_times), compact_grid=compact,
                            hit_permille=round(1000*(hit-a)/(b-a)) if action == 3 else None))
            samples.extend((g['base']+i, float(t)) for t in arm_times for i in motion_indices)
    return PlayerLayerSkeleton(normal, samples), out


def player_layout(groups):
    """Normal ANM words plus body-only $action:motion_base:count:grid_base:phases."""
    base = [g for g in groups if 'layer_action' not in g]
    by_name = {g['name']: g for g in base}
    words = [layout(base).strip()]
    for g in groups:
        if 'layer_action' in g:
            motion = by_name[g['motion_name']]
            words.append('$%d:%d:%d:%d:%d%s%s' % (g['layer_action'], motion['base'],
                         motion['count'], g['base'], g['phases'],
                         ':' + str(g['motion_count']) if g.get('compact_grid') else '',
                         ':' + str(g['hit_permille']) if g.get('hit_permille') is not None else ''))
    return ' '.join(words)


def _gmst(kinds, name, default):
    fields = kinds.get('GMST', {}).get(name.casefold())
    if not fields:
        return default
    for tag, data in fields:
        if tag == 'FLTV' and len(data) == 4:
            return struct.unpack('<f', data)[0]
        if tag == 'INTV' and len(data) == 4:
            return struct.unpack('<i', data)[0]
    return default


def foot_class(kinds, appearance):
    """Boots -> footstep set (OpenMW Npc::getSoundIdFromSndGen): no boots or
    non-armour boots = bare; armour boots by weight class (Armor weight against
    iBootsWeight x fLightMaxMod / fMedMaxMod); beast races are always bare."""
    if appearance.get('skeleton', '').endswith('kna.nif'):
        return 'bare'
    boots = None
    for item in appearance.get('equipment', ()):
        if item.get('kind') != 'ARMO':
            continue
        fields = kinds['ARMO'].get(item['item'])
        aodt = next((d for t, d in fields if t == 'AODT'), b'') if fields else b''
        if len(aodt) >= 8 and struct.unpack_from('<i', aodt)[0] == 5:
            boots = struct.unpack_from('<f', aodt, 4)[0]
    if boots is None:
        return 'bare'
    reference = _gmst(kinds, 'iBootsWeight', 20)
    if boots <= reference * _gmst(kinds, 'fLightMaxMod', .6) + 5e-4:
        return 'light'
    if boots <= reference * _gmst(kinds, 'fMedMaxMod', .9) + 5e-4:
        return 'medium'
    return 'heavy'


def event_sounds(foot):
    """Footstep event -> (dry, wading, swimming) SOUN ids. OpenMW
    Npc::getSoundIdFromSndGen: swimming 'Swim Left/Right', standing in water
    'FootWaterLeft/Right', else by boots."""
    stem = FOOT[foot]
    return {'left': (stem + 'Left', 'FootWaterLeft', 'Swim Left'),
            'right': (stem + 'Right', 'FootWaterRight', 'Swim Right')}


def sound_file(soun_id):
    """Payload name of a converted SOUN record (sound/<name>, <= 30 characters)."""
    return 'aw/fx/' + ''.join(c for c in soun_id.casefold() if c.isalnum())[:20] + '.wav'


def layout(groups, foot=None):
    """The layout string (docs/ANIMATION.md):
    NAME:BASE:COUNT:STEP[:X]  X = own speed (moving loops) or hit fraction (attack)
    @NAME:OFFSET:EVENT        a text-key event on a group frame
    ~EVENT:DRY:WADE:SWIM      sound files (relative to sound/) for an event: on land,
                              standing in water, swimming
    """
    words, used = [], set()
    for g in groups:
        word = f"{g['name']}:{g['base']}:{g['count']}:{g['step']:.4f}"
        if 'speed' in g:
            word += f":{g['speed']:.2f}"
        elif 'hit' in g:
            word += f":{g['hit']:.3f}"
        words.append(word)
    for g in groups:
        for offset, event in g['events']:
            if event in NPC_EVENTS:
                words.append(f"@{g['name']}:{offset}:{event}")
                used.add(event)
    if foot:
        table = event_sounds(foot)
        for event in NPC_EVENTS:
            if event in used:
                words.append(f'~{event}:' + ':'.join(sound_file(s) for s in table[event]))
    return ' '.join(words)


def needed_sounds(groups, foot):
    used = {e for g in groups for _, e in g['events'] if e in NPC_EVENTS}
    table = event_sounds(foot)
    return sorted({s for e in used for s in table[e]})


def convert_wav(raw):
    """Original PCM WAV -> 11025 Hz 8-bit mono WAV bytes, linear resampling (deterministic)."""
    with wave.open(io.BytesIO(raw)) as w:
        channels, width, rate, frames = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        data = w.readframes(frames)
    if width == 1:
        samples = (np.frombuffer(data, np.uint8).astype(np.float64) - 128) / 128
    elif width == 2:
        samples = np.frombuffer(data, '<i2').astype(np.float64) / 32768
    else:
        raise ValueError('Unsupported WAV sample width')
    samples = samples.reshape(-1, channels).mean(axis=1)
    count = max(1, int(round(len(samples) * 11025 / rate)))
    resampled = np.interp(np.arange(count) * rate / 11025, np.arange(len(samples)), samples)
    pcm = np.clip(np.rint(resampled * 127 + 128), 0, 255).astype(np.uint8)
    out = io.BytesIO()
    with wave.open(out, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(1)
        w.setframerate(11025)
        w.writeframes(pcm.tobytes())
    return out.getvalue()


def soun_records(master):
    """SOUN id (casefolded) -> sound file under Data Files/Sound."""
    from mwad.audit import records, subrecords, string
    table = {}
    for tag, flags, raw in records(Path(master).read_bytes()):
        if tag != 'SOUN':
            continue
        fields = list(subrecords(raw))
        name = next((string(d) for t, d in fields if t == 'NAME'), '')
        path = next((string(d) for t, d in fields if t == 'FNAM'), '')
        if name and path:
            table[name.casefold()] = 'sound/' + path.replace('\\', '/')
    return table


def sound_payload(assets, soun, ids):
    """{payload name: converted bytes} for SOUN ids (missing records are skipped)."""
    out = {}
    for soun_id in ids:
        source = soun.get(soun_id.casefold())
        if source:
            out[sound_file(soun_id)] = convert_wav(assets.read(source))
    return out


def frame_bytes(vertices):
    """Alias frame cost: daliasframetype_t + daliasframe_t (24 B) + 4 B per vertex."""
    return 4 + 24 + 4 * vertices


def publish(id1, record):
    """Write a kit model's layout beside it (<model>.anm) and its sound files;
    the converted sound bytes leave the record (it is written as JSON)."""
    anim = record.get('anim')
    if not anim:
        return
    sounds = anim.pop('_sounds', {})
    mover = anim.pop('_mover', None)
    model = Path(id1) / record['model']
    text = anim['layout']
    if mover is not None:
        # the mover model beside the standing one; the standing layout names it (>PATH)
        path = mover_path(record['model'])
        (Path(id1) / path).write_bytes(mover)
        (Path(id1) / path).with_suffix('.anm').write_text(anim['mover']['layout'] + '\n', encoding='ascii', newline='\n')
        anim['mover']['model'] = path
        text += ' >' + path
    model.with_suffix('.anm').write_text(text + '\n', encoding='ascii', newline='\n')
    for name, raw in sorted(sounds.items()):
        target = Path(id1) / 'sound' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or target.read_bytes() != raw:
            target.write_bytes(raw)


def in_place(skeleton, entries):
    """KitSkeleton for (time, moving) samples on one skeleton: moving samples keep
    the root's idle x, y (the original removes the root's horizontal motion).
    For callers with their own group tables (tools/prepare_combat.py)."""
    idle = _window(skeleton, 'idle')
    root_xy = skeleton.local(ROOT_BONE, idle[0])[3, :2].copy() if idle and ROOT_BONE in skeleton.nodes else None
    return KitSkeleton(skeleton, [(skeleton, float(t), root_xy if moving else None) for t, moving in entries])


# ---- profile policies, byte budget and frame subsets (owner decision 2026-10-09: residents stand in
# 'react' and wear the 'full' model only while they move: companion, followers, fighters)

ALIAS_BYTE_BUDGET = 512 * 1024      # the engine's alias stream staging limit (model.c AW_ALIAS_STAGING_LIMIT)
MOVER_SUFFIX = '_m'


class AliasBudgetError(ValueError):
    """Even the minimum animation frames exceed the model byte budget."""


def split_profile(name):
    """'react+full' -> ('react', 'full'): standing model and mover model; 'react' -> ('react', None)."""
    standing, _, mover = name.partition('+')
    table = profiles()
    for part in (standing, mover):
        if part and part not in table:
            raise ValueError('Unknown animation profile %r (choices: %s)' % (part, ', '.join(table)))
    if mover:
        missing = {g for g, _ in table[standing]} - {g for g, _ in table[mover]}
        if missing:
            raise ValueError('Mover profile %s lacks the standing groups %s' % (mover, sorted(missing)))
    return standing, mover or None


def plan_profile(name):
    """The groups to sample: the mover's when there is one (the standing model is a subset of its frames)."""
    standing, mover = split_profile(name)
    return profiles()[mover or standing]


def alias_bytes(frames, vertices, triangles, skin_width, skin_height):
    """Bytes of an alias model written by npc_geometry.animated_mdl."""
    return 84 + 4 + skin_width * skin_height + 12 * vertices + 16 * triangles + frames * frame_bytes(vertices)


def select(groups, keep):
    """Frames of `groups` reduced to {group name: frames kept}: (new groups, source frame indices).
    Loops keep evenly spaced frames, 'hold' groups keep their final pose; steps grow so a group keeps its
    duration; events move to the kept frame they fall in."""
    out, index = [], []
    for g in groups:
        if g['name'] not in keep:
            continue
        c, k = g['count'], max(1, min(int(keep[g['name']]), g['count']))
        if k == c:
            picks = list(range(c))
        elif g['kind'] == 'hold':
            picks = sorted({int(round(x)) for x in np.linspace(0, c - 1, k)})
        else:
            picks = [int(i * c // k) for i in range(k)]
        k = len(picks)
        if 'player_block_hit_source' in g:
            if k < 2:
                raise ValueError('Player block requires START and HIT frames')
            hold = int(g['hit'] * (k - 1) + .5) if k > 2 else 1
            if hold < 1 or hold >= k:
                raise ValueError('Player block hit cannot be represented')
            picks[hold] = g['player_block_hit_source']
            if picks != sorted(set(picks)):
                raise ValueError('Player block hit selection is not ordered')
        n = dict(g, base=len(index), count=k, step=g['step'] * c / k)
        if g['name'] in AIR_GROUPS:
            # These endpoint-sampled sections retain their authored duration.
            # The existing death/other-group timing policy is unchanged.
            n['step'] = g['step'] * (c - 1) / max(1, k - 1)
        n['events'] = [(min(k - 1, int(off * k // c)), e) for off, e in g['events']]
        index.extend(g['base'] + p for p in picks)
        out.append(n)
    return out, index


def fit(groups, vertices, triangles, skin_width, skin_height, budget=ALIAS_BYTE_BUDGET):
    """Fewer frames until the model fits the byte budget: idle stays whole; the largest other group loses a
    frame first (loops keep 2, others 1). Returns (groups, frame indices) as select()."""
    if any('layer_action' in g for g in groups):
        return fit_player_layers(groups, vertices, triangles, skin_width, skin_height, budget)
    keep = {g['name']: g['count'] for g in groups}
    floor = {g['name']: (g['count'] if g['name'] == 'idle' else 2 if g['kind'] == 'loop' else 1) for g in groups}
    for name in AIR_GROUPS:
        if name in keep:
            floor[name] = min(2, keep[name])   # preserve takeoff/landing endpoints
    while alias_bytes(sum(keep.values()), vertices, triangles, skin_width, skin_height) > budget:
        name = max((n for n in keep if keep[n] > floor[n]), key=lambda n: (keep[n], n), default=None)
        if name is None:
            raise AliasBudgetError('Alias byte budget exceeded even at the smallest frame counts')
        keep[name] -= 1
    return select(groups, keep)


def fit_player_layers(groups, vertices, triangles, skin_width, skin_height, budget):
    """Reduce grid dimensions, never flatten/resample across movement/arm rows."""
    base = [g for g in groups if 'layer_action' not in g]
    overlays = [g for g in groups if 'layer_action' in g]
    by_name = {g['name']: g for g in base}
    if overlays and all(g.get('compact_grid') for g in overlays):
        keep = {g['name']: g['count'] for g in base}
        floor = {g['name']: g['count'] for g in base}
        for name, minimum in (('hit', 1), ('death', 2), ('block', 2), ('jump', 2),
                              ('land', 2), ('readyjump', 2), ('readyland', 2), ('ready', 6)):
            if name in floor:
                floor[name] = min(floor[name], minimum)
        # The ordinary and ready gait loops keep every authored sample. The
        # transient draw/lower/punch grids have their own small leg sample count.
        def count():
            return sum(keep.values()) + sum(g['count'] for g in overlays)
        def fits():
            nf = count()
            return (nf <= 256 and nf*frame_bytes(vertices) <= 64*(28+4*1999)
                    and alias_bytes(nf, vertices, triangles, skin_width, skin_height) <= budget)
        for name in ('hit', 'death', 'block', 'jump', 'land', 'readyjump', 'readyland', 'ready'):
            while not fits() and name in keep and keep[name] > floor[name]:
                keep[name] -= 1
        if not fits():
            raise AliasBudgetError('Player body exceeds alias budget with full normal and ready gait')
        fitted, index = select(base, keep)
        for g in overlays:
            fitted.append(dict(g, base=len(index)))
            index.extend(range(g['base'], g['base']+g['count']))
        return fitted, index
    keep = {g['name']: g['count'] for g in base}
    floor = {g['name']: (g['count'] if g['name'] == 'idle' else
                       min(2, g['count']) if g['kind'] == 'loop' or g['name'] in AIR_GROUPS else 1) for g in base}
    phases = {g['layer_action']: g['phases'] for g in overlays}
    def count():
        return sum(keep.values()) + sum(keep[g['motion_name']]*phases[g['layer_action']] for g in overlays)
    def fits():
        nf = count()
        return (nf <= 256 and nf*frame_bytes(vertices) <= 64*(28+4*1999)
                and alias_bytes(nf, vertices, triangles, skin_width, skin_height) <= budget)
    while not fits():
        # Choose the dimension that saves most frames. Preserve two arm
        # endpoints and each movement's normal floor; fail if those cannot fit.
        choices = [(1+sum(phases[g['layer_action']] for g in overlays if g['motion_name']==name),
                    'motion', name) for name in keep if keep[name] > floor[name]]
        choices += [(sum(keep[g['motion_name']] for g in overlays if g['layer_action']==action),
                     'arm', action) for action in phases if phases[action] > 2]
        if not choices:
            raise AliasBudgetError('Player layers exceed alias budget at minimum movement and arm phases')
        _, kind, name = max(choices, key=lambda x:(x[0], x[1], str(x[2])))
        (keep if kind == 'motion' else phases)[name] -= 1
    fitted, index = select(base, keep)
    motion_indices = {g['name']: [i-by_name[g['name']]['base'] for i in index[g['base']:g['base']+g['count']]]
                      for g in fitted}
    for g in overlays:
        steps = phases[g['layer_action']]
        arm_indices = sorted({int(round(x)) for x in np.linspace(0, g['phases']-1, steps)})
        picks = [g['base'] + arm*g['motion_count'] + motion for arm in arm_indices
                 for motion in motion_indices[g['motion_name']]]
        fitted.append(dict(g, base=len(index), count=len(picks), phases=steps,
                           motion_count=keep[g['motion_name']], step=g['step']*(g['phases']-1)/(steps-1)))
        index.extend(picks)
    return fitted, index


def mover_path(model):
    """progs/a_x.mdl -> progs/a_x_m.mdl"""
    return model[:-4] + MOVER_SUFFIX + '.mdl'


# ---- voice barks (docs/ANIMATION.md "Voices")

def voice_pool_name(sound):
    """A voice line's file in the converted voice pool, relative to sound/ (prepare_media_assets.sound_output
    of the record's source 'sound/<SNAM>', the same naming, so the closure-kept pool holds it)."""
    import hashlib
    source = 'sound/' + sound.replace(chr(92), '/').casefold()
    return 'pool/a' + hashlib.sha256(source.encode('utf-8')).hexdigest()[:16] + '.wav'


def voice_words(lines):
    """{topic: [(sound, conditions)]} -> layout words '!TOPIC:HEX16[:KOPVALUE[:KOPVALUE]]' (K h = speaker
    health percent, p = player health percent, r = Random100; OP one of = ! > g < l)."""
    words = []
    for topic in ('attack', 'hit', 'flee', 'idle'):
        for sound, condition in lines.get(topic, ()):
            hex16 = voice_pool_name(sound)[6:22]
            words.append('!%s:%s' % (topic, hex16) + ''.join(':%s%s%d' % tuple(c) for c in (condition or ())))
    return ' '.join(words)


def voices_of(topics, appearance):
    """{topic: [(sound, condition)]} for an actor (mwad.npc.voice_lines over the voice topics)."""
    from mwad.npc import voice_lines, VOICE_TOPICS
    return {t: voice_lines(topics, appearance, t) for t in VOICE_TOPICS}
