# SPDX-License-Identifier: GPL-3.0-only
"""Actor model frame layouts: the one place that knows which frames an actor model has.

Every builder tool that needs "the idle frames", "the walk frames" or "how many frames" of an actor
model asks this module (ANIMKIT-ACTOR-ABI-SITES-35), instead of hard-coding a frame count:

* an animation kit model (tools/npc_anim.py) declares its groups in a layout beside it,
  <model>.anm: 'NAME:BASE:COUNT:STEP[:X] ... [>MOVER]' (docs/ANIMATION.md);
* without a layout, the two previous actor layouts, explicitly:
  8 frames = the idle cycle (residents, prepare_npcs.py);
  21 frames = the town actor: idle 0..7, talk 8..11, blink 12, walk 13..20 (npc_faces.actor_samples,
  prepare_intro.py);
  1 frame = an initially dead resident's death pose (aw_corpse);
* anything else is refused: a model with neither a layout nor a previous layout is an undeclared
  layout, never skipped.

The engine reads the same layout (engine/aga/src/aw_anim.c AW_AnimParse) and falls back to the same two
previous layouts (AW_AnimDefault).
"""
from pathlib import Path
import struct

IDLE_FRAMES = 8                     # the previous resident model: the idle cycle only
ACTOR_FRAMES = 21                   # the previous town actor
ACTOR_GROUPS = {'idle': (0, 8), 'talk': (8, 4), 'blink': (12, 1), 'walk': (13, 8)}
MAX_FRAMES = 64                     # npc_anim.profiles(): a kit profile has at most 64 frames
LEGACY_FRAME_COUNTS = (IDLE_FRAMES, ACTOR_FRAMES)
DEAD_FRAMES = 1                     # an initially dead resident (aw_corpse): its final death pose (prepare_area.py)


class UndeclaredLayout(ValueError):
    """A model with neither an animation kit layout nor one of the previous layouts."""


class Layout:
    """Frame groups of one actor model. kind: 'kit' (from <model>.anm), 'idle' (8 frames) or 'actor' (21)."""

    def __init__(self, kind, frames, groups, mover=None):
        self.kind, self.frames, self.groups, self.mover = kind, frames, dict(groups), mover

    def group(self, name):
        """(base, count) of a group, or None when the model does not carry it."""
        return self.groups.get(name)

    @property
    def idle(self):
        return self.groups['idle']

    def idle_range(self):
        base, count = self.idle
        return range(base, base + count)

    def __repr__(self):
        return 'Layout(%s, %d frames, %s)' % (self.kind, self.frames, self.groups)


def parse(text):
    """{group: (base, count)} and the mover model path ('>PATH') of a layout string. Event, sound and
    voice words (@event, ~sound, !voice) are not frame groups and are skipped, as the engine skips them."""
    groups, mover = {}, None
    for word in (text or '').split():
        if word.startswith('>'):
            mover = word[1:]
            continue
        if word[0] in '@~$!':
            continue
        parts = word.split(':')
        if len(parts) < 3:
            continue
        try:
            base, count = int(parts[1]), int(parts[2])
        except ValueError:
            continue
        if parts[0] in groups:
            raise ValueError('Animation kit layout repeats the group %s' % parts[0])
        groups[parts[0]] = (base, count)
    return groups, mover


def of_model(frames, layout=None, intro=False, dead=False):
    """The Layout of a model with FRAMES frames and its layout text (None: no <model>.anm).

    intro: the model stands in the opening scene; without a layout it must be the 21-frame town actor.
    dead: an aw_corpse; without a layout a 1-frame death pose is its layout too."""
    if not isinstance(frames, int) or not 1 <= frames <= MAX_FRAMES:
        raise ValueError('Actor model frame count outside 1..%d' % MAX_FRAMES)
    if layout is not None:
        groups, mover = parse(layout)
        if 'idle' not in groups:
            raise ValueError('Animation kit layout without an idle group')
        for name, (base, count) in groups.items():
            if base < 0 or count < 1 or base + count > frames:
                raise ValueError('Animation kit %s group outside the model frames' % name)
        return Layout('kit', frames, groups, mover)
    if dead and frames == DEAD_FRAMES:
        return Layout('dead', frames, {'idle': (0, DEAD_FRAMES)})
    if intro:
        if frames != ACTOR_FRAMES:
            raise UndeclaredLayout('Unexpected intro pose layout')
        return Layout('actor', frames, ACTOR_GROUPS)
    if frames == IDLE_FRAMES:
        return Layout('idle', frames, {'idle': (0, IDLE_FRAMES)})
    if frames == ACTOR_FRAMES:
        return Layout('actor', frames, ACTOR_GROUPS)
    raise UndeclaredLayout('Undeclared ground-resident pose layout')


def layout_path(model_path):
    return Path(model_path).with_suffix('.anm')


def layout_text(model_path):
    """The animation kit layout beside a model (<model>.anm), or None."""
    path = layout_path(model_path)
    return path.read_text(encoding='ascii') if path.is_file() else None


def numframes(raw):
    """Frame count of an alias model (its header)."""
    if len(raw) < 84 or raw[:4] != b'IDPO' or struct.unpack_from('<i', raw, 4)[0] != 6:
        raise ValueError('Invalid alias model header')
    return struct.unpack_from('<i', raw, 68)[0]


def of_file(model_path, intro=False):
    """The Layout of a staged model file (its frame count and the layout beside it)."""
    path = Path(model_path)
    return of_model(numframes(path.read_bytes()), layout_text(path), intro)


def tag_frames(text):
    """Rows of a carried-item tag table (<model>.tag, tools/npc_items.py 'AWTG1 FRAMES')."""
    words = (text or '').split(None, 2)
    if len(words) < 2 or words[0] != 'AWTG1':
        raise ValueError('Invalid item tag table')
    return int(words[1])


def _map_actors(path):
    """(model, intro, classname) of every actor entity (aw_npc, aw_corpse) in a staged BSP's entity lump."""
    import re
    with open(path, 'rb') as stream:
        header = stream.read(12)
        if len(header) != 12 or struct.unpack_from('<i', header)[0] != 29:
            return None  # not a Quake BSP 29 (the map checks own that); no entity lump to read here
        start, size = struct.unpack_from('<2i', header, 4)
        stream.seek(start)
        text = stream.read(size).decode('cp1252')
    out = []
    for block in re.findall(r'\{[^{}]*\}', text):
        if '"aw_npc"' not in block and '"aw_corpse"' not in block:
            continue
        ent = dict(re.findall(r'"([^"\n]+)"\s+"([^"\n]*)"', block))
        if ent.get('classname') in ('aw_npc', 'aw_corpse') and ent.get('model'):
            try:
                intro = bool(float(ent.get('aw_intro_role', 0) or 0))
            except ValueError:
                intro = False
            out.append((ent['model'], intro, ent['classname']))
    return out


def audit_payload(id1, removed_maps=()):
    """Every actor model frame layout in a staged payload, in seconds (the payload preflight's
    'actor-frames' check; ANIMKIT-ACTOR-ABI-SITES-35):

    * every actor model a kept map places resolves to a layout (kit layout, or the previous 8 idle /
      21 town actor layouts, or a corpse's 1-frame death pose; an intro actor without a layout must be the
      21-frame actor), and an aw_npc
      model's idle group is frames 0..7 (the QuakeC idle cycle and the guard torch companions);
    * every layout beside a model fits the model's frames and has an idle group; a mover it names
      exists and its own layout fits;
    * every carried-item tag table (<model>.tag) has one row per frame of the model beside it.
    Raises ValueError listing the problems; returns counts."""
    id1 = Path(id1)
    removed = set(removed_maps)
    errors, models, frames_of, other = [], {}, {}, 0

    def frames(rel):
        if rel not in frames_of:
            frames_of[rel] = numframes((id1 / rel).read_bytes())
        return frames_of[rel]

    for path in sorted((id1 / 'maps').glob('*.bsp')):
        if 'maps/' + path.name in removed or path.stem in removed:
            continue
        actors = _map_actors(path)
        if actors is None:
            other += 1
            continue
        for model, intro, classname in actors:
            models.setdefault(model, set()).add((intro, classname == 'aw_npc', classname == 'aw_corpse'))
    for model, intros in sorted(models.items()):
        p = Path(model)
        if p.is_absolute() or '..' in p.parts or not (id1 / p).is_file():
            errors.append('%s: placed actor model missing or unsafe' % model)
            continue
        for intro, idles, dead in sorted(intros):
            try:
                layout = of_model(frames(model), layout_text(id1 / p), intro, dead)
                if idles and layout.idle != (0, IDLE_FRAMES):
                    # the QuakeC idle cycle (world.qc aw_npc_idle) plays frames 0..7 of every aw_npc model, and
                    # the guard torch companions index the same frames (prepare_guard_torches.py)
                    raise ValueError('an aw_npc model needs its idle group at frames 0..7, not %d:%d' % layout.idle)
            except (OSError, ValueError, struct.error) as exc:
                errors.append('%s (%d frames%s): %s' % (model, frames_of.get(model, 0), ', intro' if intro else '', exc))
    layouts = 0
    for anm in sorted(id1.rglob('*.anm')):
        model = anm.with_suffix('.mdl')
        rel = model.relative_to(id1).as_posix()
        if not model.is_file():
            errors.append('%s: layout without a model' % anm.relative_to(id1).as_posix())
            continue
        layouts += 1
        try:
            layout = of_model(frames(rel), anm.read_text(encoding='ascii'))
            if layout.mover:
                mover = Path(layout.mover)
                if mover.is_absolute() or '..' in mover.parts or not (id1 / mover).is_file():
                    raise ValueError('mover %s missing' % layout.mover)
                if not layout_path(id1 / mover).is_file():
                    raise ValueError('mover %s has no layout' % layout.mover)
        except (OSError, ValueError, struct.error) as exc:
            errors.append('%s: %s' % (anm.relative_to(id1).as_posix(), exc))
    tags = 0
    for tag in sorted(id1.rglob('*.tag')):
        model = tag.with_suffix('.mdl')
        rel = model.relative_to(id1).as_posix()
        tags += 1
        try:
            rows = tag_frames(tag.read_text(encoding='ascii'))
            if not model.is_file():
                raise ValueError('item tags without a model')
            if rows != frames(rel):
                raise ValueError('item tags have %d rows for %d model frames' % (rows, frames(rel)))
        except (OSError, ValueError, struct.error) as exc:
            errors.append('%s: %s' % (tag.relative_to(id1).as_posix(), exc))
    if errors:
        raise ValueError('%d actor frame layout problem(s) (tools/actor_frames.py): %s' % (len(errors), '; '.join(errors[:8])))
    return {'actor_models': len(models), 'layouts': layouts, 'item_tags': tags, 'other_maps': other}
