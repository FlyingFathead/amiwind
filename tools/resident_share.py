#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Shared resident files (ROOM-RESIDENT-MODELS-SIZE-48): residents whose baked files are the same are written once.

A room stage's residents (prepare_area.populate) are baked one per NPC or creature record, each under its own name
(progs/a_<12 hex of the id>.mdl, its layout .anm and item tag .tag beside it, its mover progs/a_<..>_m.mdl with its own
.anm and .tag, its greeting sound/npc/a_<..>.wav). Two records with the same look bake the same bytes, and most
greetings are the same few lines, so the same files were installed under many names. share() keeps the first
resident's files (in identifier order) for every resident whose whole set is the same, deletes the others' copies and
points their records at the kept paths; rewrite_maps() points the room maps' entities (model, aw_voice) at them.

What is the same:
  model set   the model, its .anm and .tag, the mover model and the mover's .anm and .tag, all byte for byte; the
              standing .anm names its own mover (">progs/a_x_m.mdl"), so that one reference is compared as ">@mover".
              The engine keeps a layout and an item tag per model (aw_anim.c prep_layout, aw_items.c), read from
              beside the model's path, so a resident can share a model only when every file beside it is the same.
  voice       the greeting sound, byte for byte (an entity names its own, aw_voice).

Left alone: a record with near/far level files (npc_lod: the level table is keyed by the model path it was baked as).

MODES: 'shared' (the default of the batch rooms stage) or 'per-resident' (the previous method: every resident keeps
its own files; tools/chim_room_batches.py --resident-files per-resident).
"""
import hashlib
import json
from pathlib import Path
import re

MODES = ('shared', 'per-resident')
DEFAULT_MODE = 'shared'
MOVER_TOKEN = b'>@mover'
FORMAT = 1


def _beside(path, suffix):
    return path[:-4] + suffix


def model_files(record):
    """The id1-relative paths of one resident record's model set, in a fixed order (missing files are allowed:
    a corpse has no layout, a creature no mover)."""
    model = record['model']
    paths = [model, _beside(model, '.anm'), _beside(model, '.tag')]
    mover = ((record.get('anim') or {}).get('mover') or {}).get('model')
    if mover:
        paths += [mover, _beside(mover, '.anm'), _beside(mover, '.tag')]
    return paths, mover


def model_key(id1, record):
    """(key, {path: bytes}) of one resident's model set: the SHA-256 of every file of the set in order ('-' for a
    missing one), the standing layout's own mover reference written as MOVER_TOKEN."""
    id1 = Path(id1)
    paths, mover = model_files(record)
    parts, present = [], {}
    for index, rel in enumerate(paths):
        path = id1 / rel
        if not path.is_file():
            parts.append('-')
            continue
        raw = path.read_bytes()
        present[rel] = raw
        if index == 1 and mover:
            raw = raw.replace(b'>' + mover.encode('ascii'), MOVER_TOKEN)
        parts.append(hashlib.sha256(raw).hexdigest())
    return '|'.join(parts), present


def share(id1, models, mode=DEFAULT_MODE):
    """Share identical resident files in ID1 between the records of MODELS ({identifier: record}, populate's), in
    identifier order. Changes the records in place (model, anim.mover.model, items, voice; 'shared_model' and
    'shared_voice' name the identifier whose files they now use) and deletes the duplicate files. Returns
    {'mode', 'paths': {old path: kept path}, 'models': {...counts}, 'voices': {...counts}}."""
    if mode not in MODES:
        raise ValueError('resident files mode must be one of %s' % ', '.join(MODES))
    id1 = Path(id1)
    record = {'format': FORMAT, 'mode': mode, 'paths': {},
              'models': {'residents': 0, 'sets': 0, 'shared': 0, 'files_removed': 0, 'bytes_removed': 0,
                         'left_alone': 0},
              'voices': {'residents': 0, 'kept': 0, 'shared': 0, 'files_removed': 0, 'bytes_removed': 0}}
    if mode != 'shared':
        return record
    kept_models, kept_voices, removed = {}, {}, []
    for identifier in sorted(models):
        resident = models[identifier]
        if not resident.get('model'):
            continue
        record['models']['residents'] += 1
        if resident.get('lod_levels') or resident.get('near_use') or resident.get('_levels'):
            record['models']['left_alone'] += 1
        else:
            key, present = model_key(id1, resident)
            owner = kept_models.get(key)
            if owner is None:
                kept_models[key] = identifier
            else:
                kept = models[owner]
                old_paths, old_mover = model_files(resident)
                new_paths, _ = model_files(kept)
                for old, new in zip(old_paths, new_paths):
                    if old in present:
                        record['paths'][old] = new
                        if old != new:
                            removed.append(old)
                            record['models']['files_removed'] += 1
                            record['models']['bytes_removed'] += len(present[old])
                resident['model'] = kept['model']
                if old_mover:
                    resident['anim']['mover']['model'] = kept['anim']['mover']['model']
                resident['shared_model'] = owner
                record['models']['shared'] += 1
        voice = resident.get('voice')
        if voice:
            record['voices']['residents'] += 1
            path = id1 / 'sound' / voice
            if path.is_file():
                raw = path.read_bytes()
                digest = hashlib.sha256(raw).hexdigest()
                owner = kept_voices.get(digest)
                if owner is None:
                    kept_voices[digest] = identifier
                else:
                    kept = models[owner]['voice']
                    record['paths']['sound/' + voice] = 'sound/' + kept
                    if kept != voice:
                        removed.append('sound/' + voice)
                        record['voices']['files_removed'] += 1
                        record['voices']['bytes_removed'] += len(raw)
                    resident['voice'] = kept
                    resident['shared_voice'] = owner
                    record['voices']['shared'] += 1
    record['models']['sets'] = len(kept_models)
    record['voices']['kept'] = len(kept_voices)
    for rel in sorted(set(removed)):
        (id1 / rel).unlink()
    return record


def _entity_paths(paths):
    """{(key, old value): new value} of the entity fields that name a resident's files: model, aw_voice."""
    out = {}
    for old, new in paths.items():
        if old == new:
            continue
        if old.startswith('sound/'):
            out[('aw_voice', old[len('sound/'):])] = new[len('sound/'):]
        elif old.endswith('.mdl'):
            out[('model', old)] = new
    return out


FIELD = re.compile(r'"(model|aw_voice)" "([^"]*)"')


def rewrite_entities(text, paths):
    """TEXT (an entity lump) with every model and aw_voice field that names a shared file pointed at the kept one.
    Returns (text, fields changed)."""
    table = _entity_paths(paths)
    changed = 0

    def point(match):
        nonlocal changed
        new = table.get((match.group(1), match.group(2)))
        if new is None:
            return match.group(0)
        changed += 1
        return '"%s" "%s"' % (match.group(1), new)
    return FIELD.sub(point, text), changed


def rewrite_maps(maps, names, paths):
    """Point the entities of the room maps MAPS/<name>.bsp (NAMES) at the kept files (share's 'paths'). Each map is
    replaced whole only when a field changed. Returns {map name: fields changed} for the maps that changed."""
    from player_hull import lumps, pack_lumps
    out = {}
    if not _entity_paths(paths):
        return out
    for name in names:
        path = Path(maps) / (name + '.bsp')
        if not path.is_file():
            continue
        raw = path.read_bytes()
        parts = lumps(raw)
        text = bytes(parts[0]).decode('cp1252')
        new, changed = rewrite_entities(text, paths)
        if changed:
            parts[0] = bytearray(new.encode('cp1252'))
            # replaced whole (a temporary file renamed over it), as mwad.paths.replace_bytes
            temporary = path.with_name(path.name + '.tmp')
            temporary.write_bytes(pack_lumps(parts))
            temporary.replace(path)
            out[name] = changed
    return out


def rewrite_report(path, report):
    """The residents report REPORT (populate's return, its models shared in place) written again to PATH, as
    populate writes it (report_name)."""
    Path(path).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
    return report
