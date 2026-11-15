#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The actor record audit (NPC-CREATURE-COMBAT-STYLE-STATS-66, docs/ACTOR_RECORDS.md "Is it all there: the audit"):
one world-wide table of everything an NPC or creature record of the three masters carries, field by field, against
what a build's actor data holds, so a missing or changed value is a count, never an impression.

What is compared (the record side: Morrowind, Tribunal and Bloodmoon read together, the last record of an id winning,
a deleted record removing it; the build side: the image's id1/mwscript.awm actor table ACTB/AINV/AITM/ASPT/ASPL and
its script table SCRP, id1/npc-ambient.lut (the compiled Wander packages) and the focus stage's focus/actor-stats.awt,
the vocabulary every area's stats section is cut from):

  level, attributes, skills, health, magicka, fatigue   NPDT (stored NPCs and creatures; an auto-calculated NPC's
                                                        values are derived, so only its level, disposition,
                                                        reputation, rank and gold are its record's own)
  hello, fight, flee, alarm, services                   AIDT
  disposition, reputation, rank, gold                   NPDT
  race, class, faction                                  RNAM, CNAM, ANAM
  creature type, attacks, soul                          creature NPDT
  flags                                                 FLAG (female, essential, respawn, auto-calculate; creatures:
                                                        walks, swims, flies, bipedal, and "weapon and shield")
  blood                                                 FLAG >> 10, held in the stats vocabulary only
  spells                                                NPCS (every listed id among the actor's spell entries)
  inventory                                             NPCO (every entry: the item, its count and restock mark; a
                                                        levelled list resolved by the build is "different": the
                                                        original rolls it per spawn)
  weapon                                                the weapon the record's inventory gives it (melee and
                                                        ranged), against the actor table's equipped weapon entry
  armour                                                the armour pieces it gives, against the entries marked worn
  stats vocabulary                                      the raw NPDT FLAG AIDT NPCS RNAM CNAM ANAM bytes in
                                                        focus/actor-stats.awt
  wander / travel / follow / escort / activate          AI_W (npc-ambient.lut, by id hash) and the other packages
  script, script locals                                 SCRI against SCRP (compiled), its SCHD local counts
  scale                                                 XSCL (creatures)

Each field of each record is one of: carried (the build holds the record's value), missing (the record has it, the
build holds nothing), different (the build holds another value), and absent (the record has no such value). Each
count is given in records and in placed references (the cells' references of the three masters by id; levelled
creature references count under their lists, not under a creature).

Run in the shell container (nothing of the game is in the repo; outputs are private):
  python3 tools/actor_record_audit.py --data-files DIR --build RUN_DIR --out DIR [--public docs/actor-record-audit.json]
"""
import argparse
import json
import struct
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / 'tools', ROOT / 'src'):          # src first: tools/mwad.py is a command, src/mwad the package
    while str(_p) in sys.path:
        sys.path.remove(str(_p))
    sys.path.insert(0, str(_p))

MASTERS = ('Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm')
TAGS = ('NPC_', 'CREA', 'WEAP', 'ARMO', 'LEVI', 'LEVC', 'SCPT')
STATES = ('carried', 'missing', 'different', 'absent')
FIELDS = ('level', 'attributes', 'skills', 'health', 'magicka', 'fatigue', 'hello', 'fight', 'flee', 'alarm',
          'services', 'disposition', 'reputation', 'rank', 'gold', 'race', 'class', 'faction', 'creature type',
          'attacks', 'soul', 'flags', 'weapon and shield flag', 'blood', 'spells', 'inventory',
          'inventory levelled', 'weapon', 'ranged weapon', 'armour', 'stats vocabulary', 'wander', 'travel',
          'follow', 'escort', 'activate', 'script', 'script locals', 'scale')
# The animation groups (NPC-ATTACK-ANIMS-MISSING-65, docs/ACTOR_RECORDS.md "The animations"): per record, the groups the
# original's animation files give its skeleton (an NPC: xbase_anim.kf, the female and beast files, its own file; a
# creature: its own x<model>.kf, plus xbase_anim.kf when it is bipedal), sorted into these kinds, against what the
# build's model of that actor can play (its method: room or town resident, NPC library, the opening's standing model
# with its full kit, creature library 'kf' (six baked groups) or 'skeletal' (its whole table), a corpse).
ANIM_KINDS = ('idle', 'walk', 'run', 'attack', 'attack hand-to-hand', 'attack one-handed', 'attack two-handed',
              'attack two-wide', 'attack bow', 'attack crossbow', 'attack thrown', 'hit', 'knockdown', 'death',
              'spellcast', 'block', 'sneak', 'swim')
ANIM_FIELDS = tuple('anim ' + k for k in ANIM_KINDS)
FIELDS = FIELDS + ANIM_FIELDS
KF_GROUP_KINDS = {'idle': 'idle', 'walk': 'walk', 'run': 'run', 'attack': 'attack', 'hit': 'hit', 'death': 'death'}
RANGED = {9, 10, 11}         # WPDT type: marksman bow, crossbow, thrown (12, 13: arrows, bolts)
AMMO = {12, 13}
INV_EQUIPPED, INV_LEVELLED, INV_RESTOCKS = 1, 2, 4      # AINV flags (tools/mwscript/actors.py)
VOCAB_KEEP = {'NPC_': ('NPDT', 'FLAG', 'AIDT', 'NPCS', 'RNAM', 'CNAM', 'ANAM'), 'CREA': ('NPDT', 'FLAG', 'AIDT', 'NPCS')}


def text(d):
    return d.split(b'\0', 1)[0].decode('cp1252', 'replace')


def first(fields, tag, default=b''):
    for t, d in fields:
        if t == tag:
            return d
    return default


def phase(n, total, what):
    print('=== PHASE %d/%d: %s ===' % (n, total, what), flush=True)


# ------------------------------------------------------------------ the record side

def read_masters(data_files):
    """({tag: {folded id: fields}}, Counter of placed references by folded id) of the masters present."""
    from mwad.esm import records, subrecords
    from mwad.paths import child_ci, resolve_data_files
    try:
        data = resolve_data_files(Path(data_files))
    except ValueError:
        data = Path(data_files)
    out = {t: {} for t in TAGS}
    refs = Counter()
    refs.by_master = {}
    for name in MASTERS:
        mine = refs.by_master.setdefault(name, Counter())
        path = child_ci(data, name, required=False)
        if path is None:
            continue
        for tag, flags, payload in records(path.read_bytes()):
            if tag == 'CELL':
                in_ref = False
                for key, value in subrecords(payload):
                    if key == 'FRMR':
                        in_ref = True
                    elif key == 'NAME' and in_ref:
                        refs[text(value).casefold()] += 1
                        mine[text(value).casefold()] += 1
                        in_ref = False
                continue
            if tag not in out:
                continue
            parts = list(subrecords(payload))
            ident = text(first(parts, 'SCHD')[:32] if tag == 'SCPT' else first(parts, 'NAME')).casefold()
            if not ident:
                continue
            if flags & 0x20 or any(t == 'DELE' for t, _ in parts):
                out[tag].pop(ident, None)
            else:
                out[tag][ident] = parts
    return out, refs


def weapon_type(records, ident):
    w = first(records['WEAP'].get(ident.casefold(), []), 'WPDT')
    return struct.unpack_from('<h', w, 8)[0] if len(w) >= 10 else None


def levelled_items(records, ident, level=None, seen=None):
    """Every item a levelled item list (and its lists) can give to an actor of LEVEL (entries of a higher level are
    never picked: OpenMW 0.51 mwmechanics/levelledlist.hpp getLevelledItem, for an actor's
    inventory the level of the actor that carries it); LEVEL None: every entry."""
    seen = seen if seen is not None else set()
    key = ident.casefold()
    if key not in records['LEVI']:
        return {key}
    if key in seen:
        return set()
    seen.add(key)
    out, name = set(), None
    for t, d in records['LEVI'][key]:
        if t == 'INAM':
            name = text(d)
        elif t == 'INTV' and name is not None:
            if level is None or struct.unpack('<H', d[:2])[0] <= level:
                out |= levelled_items(records, name, level, seen)
            name = None
    return out


def expected(tag, fields, records):
    """{field: value or None (absent)} of one NPC_ or CREA record, in the actor table's terms."""
    e = dict.fromkeys(FIELDS)
    npdt = first(fields, 'NPDT')
    flag = struct.unpack('<I', first(fields, 'FLAG', b'\0\0\0\0')[:4].ljust(4, b'\0'))[0]
    e['blood'] = flag >> 10
    if tag == 'NPC_':
        e['flags'] = (1 if flag & 1 else 0) | (2 if flag & 2 else 0) | (4 if flag & 4 else 0) | \
                     (8 if len(npdt) == 12 else 0)
        if len(npdt) == 52:
            e['level'] = struct.unpack_from('<h', npdt)[0]
            e['attributes'] = list(npdt[2:10])
            e['skills'] = list(npdt[10:37])
            e['health'], e['magicka'], e['fatigue'] = struct.unpack_from('<3H', npdt, 38)
            e['disposition'], e['reputation'] = npdt[44], npdt[45]
            e['rank'] = struct.unpack_from('<b', npdt, 46)[0]
            e['gold'] = struct.unpack_from('<i', npdt, 48)[0]
        elif len(npdt) == 12:
            e['level'] = struct.unpack_from('<h', npdt)[0]
            e['disposition'], e['reputation'] = npdt[2], npdt[3]
            e['rank'] = struct.unpack_from('<b', npdt, 4)[0]
            e['gold'] = struct.unpack_from('<i', npdt, 8)[0]
        e['race'] = text(first(fields, 'RNAM')).casefold() or None
        e['class'] = text(first(fields, 'CNAM')).casefold() or None
        e['faction'] = text(first(fields, 'ANAM')).casefold() or None
    else:
        e['flags'] = (2 if flag & 0x80 else 0) | (4 if flag & 2 else 0) | (16 if flag & 0x40 else 0) | \
                     (32 if flag & 0x10 else 0) | (64 if flag & 0x20 else 0) | (128 if flag & 1 else 0)
        e['weapon and shield flag'] = 1 if flag & 4 else None
        if len(npdt) == 96:
            v = struct.unpack('<24i', npdt)
            e['creature type'], e['level'] = v[0], v[1]
            e['attributes'] = list(v[2:10])
            e['health'], e['magicka'], e['fatigue'], e['soul'] = v[10:14]
            e['attacks'] = list(v[17:23])
            e['gold'] = v[23]
        xscl = first(fields, 'XSCL')
        if len(xscl) == 4:
            scale = struct.unpack('<f', xscl)[0]
            e['scale'] = round(scale, 3) if abs(scale - 1.0) > 1e-4 else None
    aidt = first(fields, 'AIDT')
    if len(aidt) >= 5:
        e['hello'] = min(255, struct.unpack_from('<H', aidt)[0])
        e['fight'], e['flee'], e['alarm'] = aidt[2], aidt[3], aidt[4]
        services = struct.unpack_from('<I', aidt, 8)[0] if len(aidt) >= 12 else 0
        e['services'] = services or None
    spells = sorted({text(d).casefold() for t, d in fields if t == 'NPCS'})
    e['spells'] = spells or None
    inv, lev = [], []
    weapons, ranged, armour = set(), set(), set()
    for t, d in fields:
        if t != 'NPCO' or len(d) != 36:
            continue
        count = struct.unpack_from('<i', d)[0]
        name = text(d[4:]).casefold()
        if count == 0 or not name:
            continue
        if name in records['LEVI']:
            lev.append(name)
            can = levelled_items(records, name, e['level'] if e['level'] is not None else 1)
        else:
            inv.append((name, abs(count), count < 0))
            can = {name}
        for item in can:
            typ = weapon_type(records, item)
            if typ is not None:
                if typ in RANGED:
                    ranged.add(item)
                elif typ not in AMMO:
                    weapons.add(item)
            elif item in records['ARMO']:
                armour.add(item)
    e['inventory'] = sorted(inv) or None
    e['inventory levelled'] = sorted(lev) or None
    # a creature holds and wears what it carries only with the "weapon and shield" flag (OpenMW 0.51
    # mwclass/creature.cpp: an inventory store only for kWeapon); otherwise its items are loot
    wields = tag == 'NPC_' or bool(flag & 4)
    e['weapon'] = sorted(weapons) if weapons and wields else None
    e['ranged weapon'] = sorted(ranged) if ranged and wields else None
    e['armour'] = sorted(armour) if armour and wields else None
    e['stats vocabulary'] = [(t, d) for t, d in fields if t in VOCAB_KEEP[tag]]
    packages = Counter(t for t, _ in fields)
    for t, name in (('AI_W', 'wander'), ('AI_T', 'travel'), ('AI_F', 'follow'), ('AI_E', 'escort'),
                    ('AI_A', 'activate')):
        e[name] = packages[t] or None
    script = text(first(fields, 'SCRI')).casefold()
    if script:
        e['script'] = script
        schd = first(records['SCPT'].get(script, []), 'SCHD')
        e['script locals'] = sum(struct.unpack_from('<3I', schd, 32)) if len(schd) >= 44 else None
    return e


# ------------------------------------------------------------------ the animations, record side

def anim_kind(group):
    """The audit's kind of one original group name (lower case), or None for a group no kind covers (turns, the
    wander idles 2-9, jumps, the inventory poses ...)."""
    import re
    g = group.casefold()
    direct = {'idle': 'idle', 'walkforward': 'walk', 'runforward': 'run', 'handtohand': 'attack hand-to-hand',
              'weapononehand': 'attack one-handed', 'weapontwohand': 'attack two-handed',
              'weapontwowide': 'attack two-wide', 'bowandarrow': 'attack bow', 'crossbow': 'attack crossbow',
              'throwweapon': 'attack thrown', 'knockdown': 'knockdown', 'knockout': 'knockdown',
              'spellcast': 'spellcast', 'shield': 'block', 'sneakforward': 'sneak', 'idlesneak': 'sneak',
              'swimwalkforward': 'swim', 'swimrunforward': 'swim', 'swimforward': 'swim'}
    if g in direct:
        return direct[g]
    for pattern, kind in ((r'^attack\d+$', 'attack'), (r'^hit\d+$', 'hit'), (r'^death\d+$', 'death')):
        if re.match(pattern, g):
            return kind
    return None


def text_key_groups(raw):
    """The group names a NIF or KF file's text keys start ("Idle: Start", "SpellCast: Self Start", "WalkForward: Loop
    Start"), lower case: a byte scan of the text key strings, no NIF parse (the keys are plain length-prefixed text)."""
    import re
    out = set()
    for m in re.finditer(rb'(?<![A-Za-z0-9_])([A-Za-z][A-Za-z0-9_]*): [^\r\n\x00]{0,24}?[Ss]tart', raw):
        out.add(m.group(1).decode('latin-1').casefold())
    return out


HUMANOID_FILES = {'base': 'meshes/xbase_anim.kf', 'female': 'meshes/xbase_anim_female.kf',
                  'beast': 'meshes/xbase_animkna.kf'}
BEAST_RACES = {'argonian', 'khajiit'}


class OriginalGroups:
    """READ(name) -> bytes or raises: the game's files (loose files over the archives). Group names per file, read once."""

    def __init__(self, read):
        self.read, self.cache = read, {}

    def groups(self, name):
        key = name.casefold().replace('\\', '/')
        if key not in self.cache:
            try:
                self.cache[key] = text_key_groups(self.read(key))
            except Exception:  # noqa: BLE001 (no such file: no groups from it)
                self.cache[key] = None
        return self.cache[key] or set()

    def own(self, model):
        """The groups of an actor's own model: its x<model>.kf (OpenMW correctActorModelPath), else the model's own keys."""
        if not model:
            return set()
        mesh = model.casefold().replace('\\', '/')
        mesh = mesh if mesh.startswith('meshes/') else 'meshes/' + mesh
        cut = mesh.rfind('/') + 1
        kf = mesh[:cut] + 'x' + mesh[cut:-4] + '.kf' if mesh.endswith('.nif') else None
        got = self.groups(kf) if kf else set()
        return got or self.groups(mesh)


def expected_anim(tag, fields, original):
    """{'anim KIND': True or None} of one record from the original's files (ORIGINAL: OriginalGroups)."""
    groups = set()
    model = text(first(fields, 'MODL'))
    if tag == 'NPC_':
        race = text(first(fields, 'RNAM')).casefold()
        groups |= original.groups(HUMANOID_FILES['beast' if race in BEAST_RACES else 'base'])
        if model and 'base_anim' not in model.casefold():
            groups |= original.own(model)
    else:
        flag = struct.unpack('<I', first(fields, 'FLAG', b'\0\0\0\0')[:4].ljust(4, b'\0'))[0]
        groups |= original.own(model)
        if flag & 1:                    # bipedal: the shared humanoid file under its own (OpenMW creatureanimation)
            groups |= original.groups(HUMANOID_FILES['base'])
    kinds = {anim_kind(g) for g in groups} - {None}
    if tag == 'NPC_':
        kinds.discard('attack')         # an NPC attacks by its weapon's group, never attackN
    return {'anim ' + k: (True if k in kinds else None) for k in ANIM_KINDS}


def game_reader(data_files):
    """READ(name) over the data folder: a loose file first, else the masters' archives (later archive wins)."""
    from mwad.archives import layered_bsa
    from mwad.esm import read_bsa_asset
    from mwad.paths import child_ci
    from mwad.paths import resolve_data_files
    try:
        root = resolve_data_files(Path(data_files))
    except ValueError:
        root = Path(data_files)
    bsa = layered_bsa(root)

    def read(name):
        node = root
        for part in name.replace('\\', '/').split('/'):
            node = child_ci(node, part, required=False) if node is not None and node.is_dir() else None
        if node is not None and node.is_file():
            return node.read_bytes()
        return read_bsa_asset(bsa, name)
    return read


# ------------------------------------------------------------------ the animations, build side

def read_anim_build(run):
    """{folded id: (method, set of kinds the build's model can play)} of every actor model the build placed: the
    residents (rooms, towns), the NPC library, the opening's people and the creature library."""
    import glob
    sys.path.insert(0, str(ROOT / 'tools'))
    from anim_coverage import catalogue, table_groups
    run = Path(run)
    id1 = run / 'image/boot/id1'
    hooked = {g for g, how in catalogue() if how.startswith('pick:') or how.startswith('combat:')}
    tables = {}

    def table_kinds(path, engine_only):
        if path not in tables:
            p = id1 / path
            names = table_groups(p.read_bytes())[0] if p.is_file() else []
            tables[path] = names
        return {anim_kind(g) for g in tables[path] if not engine_only or g in hooked} - {None}

    def layout_kinds(model):
        """The kinds a model's layout plays (its engine groups), following a '>' full kit; ('none', set()) without
        a layout (an authored corpse's one pose, or a model the engine plays idle only)."""
        p = (id1 / model).with_suffix('.anm')
        if not p.is_file():
            return None
        text_ = p.read_text(encoding='latin-1')
        groups = {w.split(':')[0] for w in text_.split() if w[:1].isalpha()}
        kit = next((w[1:] for w in text_.split() if w.startswith('>')), None)
        if kit:
            more = layout_kinds(kit)
            groups |= more[1] if more else set()
        engine = {'idle': 'idle', 'walk': 'walk', 'run': 'run', 'attack': 'attack', 'hit': 'hit', 'knock': 'knockdown',
                  'death': 'death', 'block': 'block', 'swim': 'swim', 'cast': 'spellcast'}
        return kit, {engine.get(g, g) for g in groups}

    out = {}
    humanoid = {k: table_kinds('progs/%s.awsk' % k, True) for k in ('humanoid', 'humanoid_kna')}
    npc_attacks = {k for k in ANIM_KINDS if k.startswith('attack ')}

    def skeletal_npc(ident, appearance, model, method):
        if appearance.get('initially_dead'):
            out[ident] = ('corpse', {'death'})
            return
        lk = layout_kinds(model)
        if lk is None:
            out[ident] = (method + ' (no layout: idle only)', {'idle'})
            return
        beast = 'kna' in (appearance.get('skeleton') or '').casefold()
        kinds = set(humanoid['humanoid_kna' if beast else 'humanoid'])
        # the engine plays a skeletal NPC's table by state; its layout must hold the fight groups the state moves
        # into the table's groups (aw_anim.c, the attack row moved into the weapon's group)
        if 'attack' not in lk[1]:
            kinds -= npc_attacks
        out[ident] = (method, kinds)

    # every area stage's resident table (towns, room batches, the city and opening interiors): {'models': {id: {
    # 'appearance', 'model', ...}}}
    residents = sorted(set(glob.glob(str(run / '*/*.json')) + glob.glob(str(run / '*/scene/*.json'))))
    for path in residents:
        if '/actor-library/' in path.replace('\\', '/'):
            continue
        try:
            doc = json.loads(Path(path).read_text(encoding='utf-8'))
        except (ValueError, UnicodeDecodeError):
            continue
        models = doc.get('models') if isinstance(doc, dict) else None
        if not isinstance(models, dict) or not models or not all(
                isinstance(r, dict) and 'appearance' in r and 'model' in r for r in list(models.values())[:3]):
            continue
        method = 'town resident' if 'chim-town-' in path else 'room resident'
        for ident, rec in models.items():
            if isinstance(rec, dict) and rec.get('model') and ident.casefold() not in out:
                skeletal_npc(ident.casefold(), rec.get('appearance') or {}, rec['model'], method)
    lib = run / 'actor-library'
    if (lib / 'npc-library.json').is_file():
        npcs = json.loads((lib / 'npc-library.json').read_text(encoding='utf-8'))
        for ident, row in npcs.get('npcs', {}).items():
            model = (npcs['models'].get(row.get('key')) or {}).get('model')
            if model and ident.casefold() not in out:
                skeletal_npc(ident.casefold(), {'initially_dead': row.get('dead')}, model, 'NPC library')
    # the opening's people (census office, prison ship, dock): the image's coverage table names their record and
    # standing model (np_*.mdl, whose layout links the full kit worn in a fight)
    coverage = run / 'image/actor-anim-coverage.json'
    if coverage.is_file():
        for row in json.loads(coverage.read_text(encoding='utf-8')).get('rows', []):
            ident, model = (row.get('record') or '').casefold(), row.get('model')
            if ident and model and model.startswith('progs/np_'):
                skeletal_npc(ident, {}, model, 'opening standing model + full kit')
    if (lib / 'creature-library.json').is_file():
        crea = json.loads((lib / 'creature-library.json').read_text(encoding='utf-8'))
        for ident, base in crea.get('bases', {}).items():
            m = crea['models'].get(base.get('mesh'))
            if not m or ident.casefold() in out:
                continue
            if m.get('method') == 'skeletal' and m.get('table'):
                out[ident.casefold()] = ('creature library skeletal', table_kinds(m['table'], False))
            else:
                out[ident.casefold()] = ('creature library kf', {KF_GROUP_KINDS[g['name']] for g in m.get('groups', [])
                                                                  if g['name'] in KF_GROUP_KINDS})
    return out


# ------------------------------------------------------------------ the build side

def read_build(run):
    """The build's actor data: {'actors': {folded id: held dict}, 'scripts': {folded name: locals}, 'wander': set of
    id hashes, 'vocab': {id hash: fields}, 'files': {name: path or None}}."""
    from mwscript import awms
    from mwscript.actors import read_actor, INV_EQUIPPED
    from actor_stats import read_vocabulary, name_hash
    run = Path(run)
    awm = next((p for p in (run / 'image/boot/id1/mwscript.awm', run / 'mwscript/id1/mwscript.awm') if p.is_file()),
               None)
    lut = next((p for p in (run / 'image/boot/id1/npc-ambient.lut',) if p.is_file()), None)
    awt = next((p for p in (run / 'focus/actor-stats.awt',) if p.is_file()), None)
    out = {'actors': {}, 'scripts': {}, 'wander': set(), 'vocab': {}, 'hash': name_hash,
           'files': {'mwscript.awm': str(awm) if awm else None, 'npc-ambient.lut': str(lut) if lut else None,
                     'actor-stats.awt': str(awt) if awt else None}}
    if awm:
        f = awms.read(awm.read_bytes())
        names = awms.strings(f)
        items = []
        for i in range(f.get('AITM_rows', 0)):
            ident, kind, typ = struct.unpack_from('>HBB', f['AITM'], 32 * i)
            items.append((names[ident].casefold(), kind, typ))
        spells = [names[struct.unpack_from('>H', f['ASPT'], 4 * i)[0]].casefold() for i in range(f.get('ASPT_rows', 0))]
        aspl = [struct.unpack_from('>H', f['ASPL'], 2 * i)[0] for i in range(f.get('ASPL_rows', 0))]
        string = lambda s: None if s == 0xFFFF else names[s].casefold()  # noqa: E731
        for i in range(f.get('ACTB_rows', 0)):
            r = read_actor(f['ACTB'], i)
            inv = []
            for j in range(r['inv_count']):
                item, count, flags, _ = struct.unpack_from('>HhBB', f['AINV'], 6 * (r['inv_first'] + j))
                inv.append((items[item][0], count, flags, items[item][1], items[item][2]))
            weapon = inv[r['weapon']][0] if r['weapon'] != 0xFF and r['weapon'] < len(inv) else None
            held = {'kind': r['kind'], 'level': r['level'], 'attributes': r['attributes'], 'skills': r['skills'],
                    'health': r['health'], 'magicka': r['magicka'], 'fatigue': r['fatigue'], 'hello': r['hello'],
                    'fight': r['fight'], 'flee': r['flee'], 'alarm': r['alarm'], 'disposition': r['disposition'],
                    'reputation': r['reputation'], 'rank': r['rank'], 'gold': r['gold'], 'race': string(r['race']),
                    'class': string(r['class']), 'faction': string(r['faction']), 'creature type': r['type'],
                    'attacks': r['attack'], 'soul': r['soul'], 'flags': r['flags'],
                    'spells': {spells[aspl[r['spell_first'] + j]] for j in range(r['spell_count'])},
                    'inventory': inv, 'weapon': weapon,
                    'armour': {n for n, _c, fl, kind, _t in inv if fl & INV_EQUIPPED and kind == 2}}
            out['actors'][names[r['id']].casefold()] = held
        for row in awms.scripts(f):
            out['scripts'][names[row['name']].casefold()] = row['locals']
    if lut:
        raw = lut.read_bytes()
        rows, = struct.unpack_from('>I', raw, 8)
        for i in range(rows):
            out['wander'].add(struct.unpack_from('>I', raw, 32 + 28 * i + 4)[0])
    if awt:
        vocab = read_vocabulary(awt.read_bytes())
        out['vocab'] = {h: fields for h, (_tag, fields) in vocab['actors'].items()}
    return out


def fresh_actor_table(data_files, build):
    """BUILD with its actor rows replaced by the actor table this source tree's builder writes now (tools/mwscript/
    actors.py on the masters, no build): the check of a builder fix before any build runs."""
    from mwscript.gamedata import GameData
    from mwscript.actors import ActorTables, INV_EQUIPPED
    names, index = [], {}

    def string(s):
        if s not in index:
            index[s] = len(names)
            names.append(s)
        return index[s]
    t = ActorTables(GameData().load(Path(data_files)), string)
    if hasattr(t, '_build') and not t.rows:
        t._build()
    for row in t.rows:
        inv = []
        for item, count, flags in t.inventory[row['inv_first']:row['inv_first'] + row['inv_count']]:
            it = t.items[item]
            inv.append((names[it['id']].casefold(), count, flags, it['kind'], it['type']))
        weapon = inv[row['weapon_entry']][0] if row['weapon_entry'] != 0xFF else None
        held = build['actors'].setdefault(names[row['id']].casefold(), {})
        held.update(inventory=inv, weapon=weapon,
                    armour={n for n, _c, fl, kind, _t in inv if fl & INV_EQUIPPED and kind == 2})
    return build


def fnv_lower(ident):
    """npc-ambient.lut's id hash: FNV-1a of the lower-case id."""
    h = 2166136261
    for c in ident.casefold().encode('cp1252', 'replace'):
        h = ((h ^ c) * 16777619) & 0xFFFFFFFF
    return h


# ------------------------------------------------------------------ the comparison

def compare(ident, tag, e, build):
    """{field: state} of one record against the build."""
    held = build['actors'].get(ident)
    s = {}
    auto = tag == 'NPC_' and e['flags'] is not None and e['flags'] & 8
    for field in FIELDS:
        want = e[field]
        if want is None or (field == 'skills' and tag == 'CREA'):
            s[field] = 'absent'
            continue
        if field in ANIM_FIELDS:
            method, kinds = build.get('anim', {}).get(ident, (None, set()))
            if method == 'corpse' and field != 'anim death':
                s[field] = 'absent'          # an authored corpse never moves: its one death pose is all it shows
            else:
                s[field] = 'carried' if field[5:] in kinds else 'missing'
            continue
        if field == 'stats vocabulary':
            got = build['vocab'].get(build['hash'](ident))
            if got is None:
                s[field] = 'missing'
            else:
                s[field] = 'carried' if sorted(want) == sorted((t, d) for t, d in got if t in VOCAB_KEEP[tag]) \
                    else 'different'
            continue
        if field == 'wander':
            s[field] = 'carried' if fnv_lower(ident) in build['wander'] else 'missing'
            continue
        if field == 'weapon and shield flag':
            # held as its effect: the row equips the weapon and armour the inventory gives (nothing to equip: carried)
            gives = e['weapon'] or e['armour']
            s[field] = 'carried' if not gives or (held and (held.get('weapon') or held.get('armour'))) else 'missing'
            continue
        if field in ('travel', 'follow', 'escort', 'activate', 'scale', 'services'):
            # no per-actor table of the build holds these (services: only the dialogue table, not audited here)
            got = build['vocab'].get(build['hash'](ident)) if field == 'services' else None
            s[field] = 'carried' if got is not None and first(got, 'AIDT')[8:12] == struct.pack('<I', want) \
                else 'missing'
            continue
        if field == 'blood':
            got = build['vocab'].get(build['hash'](ident))
            s[field] = 'carried' if got is not None and (want == 0 or first(got, 'FLAG')) else 'missing'
            continue
        if field in ('script', 'script locals'):
            if e['script'] not in build['scripts']:
                s[field] = 'missing'
            elif field == 'script':
                s[field] = 'carried'
            else:
                s[field] = 'carried' if build['scripts'][e['script']] == want else 'different'
            continue
        if field in ('attributes', 'skills', 'health', 'magicka', 'fatigue') and auto:
            s[field] = 'absent'            # derived from race, class and level: not the record's own
            continue
        if held is None or {'inventory levelled': 'inventory', 'ranged weapon': 'weapon'}.get(field, field) not in held:
            s[field] = 'missing'
            continue
        if field == 'spells':
            s[field] = 'carried' if set(want) <= held['spells'] else 'different'
        elif field == 'inventory':
            have = {(n, abs(c), bool(fl & INV_RESTOCKS)) for n, c, fl, _k, _t in held['inventory']
                    if not fl & INV_LEVELLED}
            s[field] = 'carried' if all(x in have for x in want) else 'different'
        elif field == 'inventory levelled':
            n = sum(1 for _n, _c, fl, _k, _t in held['inventory'] if fl & INV_LEVELLED)
            s[field] = 'different' if n else 'missing'     # resolved once at build time: the original rolls per spawn
        elif field == 'weapon':
            # a bow, crossbow or thrown weapon held instead by the original's opening rating is carried too
            # (ACTOR-RANGED-COMBAT-MISSING-66; tools/prepare_combat.py equipment)
            s[field] = 'carried' if held['weapon'] in want or held['weapon'] in (e['ranged weapon'] or ()) else \
                'missing' if held['weapon'] is None else 'different'
        elif field == 'ranged weapon':
            # different: a melee weapon held, which the original's rating prefers at the opening, or no ammunition
            s[field] = 'carried' if held['weapon'] in want else 'missing' if held['weapon'] is None else 'different'
        elif field == 'armour':
            s[field] = 'carried' if held['armour'] & set(want) else 'missing'
        elif field == 'attributes':
            s[field] = 'carried' if [min(0xFFFF, max(0, a)) for a in want] == held[field] else 'different'
        elif field == 'flags':
            s[field] = 'carried' if (held['flags'] & 0xFF) == want else 'different'
        else:
            got = held[field]
            s[field] = 'carried' if got == want else 'different'
    return s


def audit(records, refs, build, examples=8, original=None):
    """ORIGINAL: OriginalGroups over the game's files (the animation kinds), None to leave them absent."""
    table, rows = {}, []
    mw = getattr(refs, 'by_master', {}).get('Morrowind.esm', refs)
    for tag in ('NPC_', 'CREA'):
        for ident in sorted(records[tag]):
            e = expected(tag, records[tag][ident], records)
            if original is not None:
                e.update(expected_anim(tag, records[tag][ident], original))
            st = compare(ident, tag, e, build)
            rows.append({'id': ident, 'kind': 'npc' if tag == 'NPC_' else 'creature', 'refs': refs.get(ident, 0),
                         'refs_mw': mw.get(ident, 0),
                         'states': st, 'weapon': e['weapon'], 'ranged': e['ranged weapon'],
                         'held_weapon': (build['actors'].get(ident) or {}).get('weapon'),
                         'anim_method': build.get('anim', {}).get(ident, ('not in this build',))[0]})
    for field in FIELDS:
        c = {k: {'records': 0, 'refs': 0, 'refs_mw': 0, 'examples': []} for k in STATES}
        for r in rows:
            k = r['states'][field]
            c[k]['records'] += 1
            c[k]['refs'] += r['refs']
            c[k]['refs_mw'] += r['refs_mw']
            if k in ('missing', 'different') and len(c[k]['examples']) < examples:
                c[k]['examples'].append(r['id'])
        table[field] = c
    worst = sorted(((v['missing']['refs'] + v['different']['refs'], f) for f, v in table.items()), reverse=True)
    methods = {}
    for r in rows:
        m = methods.setdefault(r['anim_method'], {'records': 0, 'refs': 0, 'refs_mw': 0})
        m['records'] += 1
        m['refs'] += r['refs']
        m['refs_mw'] += r['refs_mw']
    # the opening's people by name (census office, prison ship, dock): the first rows anyone asks about
    opening = {r['id']: {f[5:]: r['states'][f] for f in ANIM_FIELDS if r['states'][f] != 'absent'}
               for r in rows if r['id'].startswith('chargen')}
    return {'fields': table, 'worst': [f for n, f in worst if n], 'rows': rows, 'anim_methods': methods,
            'opening': opening,
            'records': {'npc': len(records['NPC_']), 'creature': len(records['CREA'])},
            'refs': sum(r['refs'] for r in rows)}


def public_summary(report, build_name):
    """The public counts (no game text beyond record ids): per field and state, records and references."""
    return {'build': build_name, 'records': report['records'], 'refs': report['refs'], 'worst': report['worst'],
            'anim_methods': report.get('anim_methods', {}), 'opening': report.get('opening', {}),
            'fields': {f: {k: {'records': v[k]['records'], 'refs': v[k]['refs'], 'refs_mw': v[k]['refs_mw']}
                           for k in STATES}
                       for f, v in report['fields'].items()}}


def markdown(report, build_name):
    lines = ['# Actor record audit: %s' % build_name, '',
             '%d NPC and %d creature records, %d placed references.' % (report['records']['npc'],
                                                                      report['records']['creature'], report['refs']),
             '', '| Field | carried | missing | different | absent | examples |', '| --- | ---: | ---: | ---: | ---: | --- |']
    order = report['worst'] + [f for f in FIELDS if f not in report['worst']]
    for f in order:
        v = report['fields'][f]
        cell = lambda k: '%d (%d refs, %d in Morrowind.esm)' % (v[k]['records'], v[k]['refs'], v[k]['refs_mw'])  # noqa: E731
        ex = ', '.join(v['missing']['examples'][:4] + v['different']['examples'][:4])
        lines.append('| %s | %s | %s | %s | %s | %s |' % (f, cell('carried'), cell('missing'), cell('different'),
                                                         cell('absent'), ex))
    if report.get('anim_methods'):
        lines += ['', '## Animation method per record', '', '| Method | records | refs | in Morrowind.esm |',
                  '| --- | ---: | ---: | ---: |']
        for m, v in sorted(report['anim_methods'].items(), key=lambda kv: -kv[1]['refs']):
            lines.append('| %s | %d | %d | %d |' % (m, v['records'], v['refs'], v['refs_mw']))
    if report.get('opening'):
        lines += ['', '## The opening\'s people', '']
        for ident, st in sorted(report['opening'].items()):
            miss = [k for k, v in st.items() if v != 'carried']
            lines.append('- %s: %d kinds carried%s' % (ident, len(st) - len(miss),
                                                       ', missing ' + ', '.join(miss) if miss else ''))
    return '\n'.join(lines) + '\n'


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    p.add_argument('--data-files', type=Path, required=True)
    p.add_argument('--build', type=Path, required=True, help='a build run folder (its image/boot/id1 and focus/)')
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--public', type=Path, help='write the public counts JSON here too')
    p.add_argument('--fresh-actor-table', action='store_true',
                   help="compare the actor table this source tree's builder would write now, not the build's")
    a = p.parse_args(argv)
    t0 = time.time()
    phase(1, 3, 'the masters')
    records, refs = read_masters(a.data_files)
    print('  %d NPC, %d creature records, %d references counted (%.1f s)' % (
        len(records['NPC_']), len(records['CREA']), sum(refs.values()), time.time() - t0), flush=True)
    phase(2, 3, 'the build ' + a.build.name)
    build = read_build(a.build)
    if a.fresh_actor_table:
        build = fresh_actor_table(a.data_files, build)
        print('  actor rows replaced by the fresh actor table of this source tree', flush=True)
    print('  %d actor rows, %d scripts, %d wander rows; files %s (%.1f s)' % (
        len(build['actors']), len(build['scripts']), len(build['wander']), build['files'], time.time() - t0), flush=True)
    build['anim'] = read_anim_build(a.build)
    print('  %d actor models with an animation method (%.1f s)' % (len(build['anim']), time.time() - t0), flush=True)
    phase(3, 3, 'the comparison')
    report = audit(records, refs, build, original=OriginalGroups(game_reader(a.data_files)))
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / 'actor-record-audit.json').write_text(json.dumps(report, indent=1, default=list), encoding='utf-8',
                                                   newline='\n')
    (a.out / 'actor-record-audit.md').write_text(markdown(report, a.build.name), encoding='utf-8', newline='\n')
    if a.public:
        a.public.write_text(json.dumps(public_summary(report, a.build.name), indent=1) + '\n', encoding='utf-8',
                            newline='\n')
    for f in report['worst'][:12]:
        v = report['fields'][f]
        print('  %-24s missing %5d (%5d refs, %5d MW)  different %5d (%5d refs, %5d MW)' % (
            f, v['missing']['records'], v['missing']['refs'], v['missing']['refs_mw'], v['different']['records'],
            v['different']['refs'], v['different']['refs_mw']))
    print('done in %.1f s; %s' % (time.time() - t0, a.out), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
