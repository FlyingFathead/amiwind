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
}
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


def _window(skeleton, group):
    start, stop, _, _ = GROUPS[group]
    ev = skeleton.events
    if start in ev and stop in ev and ev[stop] > ev[start]:
        return ev[start], ev[stop]
    return None


def plan(base, profile, female=None, weight=1.0):
    """Sample plan for one skeleton and profile.

    base: npc_geometry.Skeleton of the actor's skeleton file; female: the female
    override Skeleton or None. Returns (KitSkeleton, groups) where groups is a
    list of dicts: name, base frame, count, step, speed (Quake units/s, moving
    loops), hit (attack), events [(offset, event)], source ('base'|'female'|
    'idle' when the skeleton lacks the group and idle frames stand in)."""
    idle = _window(base, 'idle')
    if idle is None:
        raise ValueError('Skeleton has no idle group')
    root_xy = base.local(ROOT_BONE, idle[0])[3, :2].copy() if ROOT_BONE in base.nodes else None
    samples, groups = [], []
    for name, count in profile:
        count = int(count)
        kind, moves = GROUPS[name][2], GROUPS[name][3]
        skeleton, source = base, 'base'
        if female is not None and _window(female, name) is not None:
            skeleton, source = female, 'female'
        window = _window(skeleton, name)
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
                hit = skeleton.events.get(ATTACK_HIT if name == 'attack' else BLOCK_HIT)
                entry['hit'] = (hit - a) / (b - a) if hit is not None and a <= hit <= b else .5
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
        n = dict(g, base=len(index), count=k, step=g['step'] * c / k)
        n['events'] = [(min(k - 1, int(off * k // c)), e) for off, e in g['events']]
        index.extend(g['base'] + p for p in picks)
        out.append(n)
    return out, index


def fit(groups, vertices, triangles, skin_width, skin_height, budget=ALIAS_BYTE_BUDGET):
    """Fewer frames until the model fits the byte budget: idle stays whole; the largest other group loses a
    frame first (loops keep 2, others 1). Returns (groups, frame indices) as select()."""
    keep = {g['name']: g['count'] for g in groups}
    floor = {g['name']: (g['count'] if g['name'] == 'idle' else 2 if g['kind'] == 'loop' else 1) for g in groups}
    while alias_bytes(sum(keep.values()), vertices, triangles, skin_width, skin_height) > budget:
        name = max((n for n in keep if keep[n] > floor[n]), key=lambda n: (keep[n], n), default=None)
        if name is None:
            raise ValueError('Alias byte budget exceeded even at the smallest frame counts')
        keep[name] -= 1
    return select(groups, keep)


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
