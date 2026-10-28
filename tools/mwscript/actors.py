# SPDX-License-Identifier: GPL-3.0-only
"""The actor table: one compact record per NPC and creature record of the three masters (docs/ACTOR_STATE.md).

Built once from the game data by the mwscript stage, written as sections of id1/mwscript.awm that stay on disk
(the engine reads one row when an actor is first needed, aw_actorstate.c):

  ACTB  96 bytes an actor, sorted by its folded id (binary search by id):
          u16 id  u8 kind (0 NPC, 1 creature)  u8 flags (ACTOR_*)  u16 level
          u16 attributes[8]  u8 skills[27]  u8 hello fight flee alarm  u8 disposition  u8 reputation  i8 rank
          u16 health magicka fatigue  u16 race class faction (strings, 0xFFFF none)  u32 gold
          u16 first inventory entry, u16 entries  u16 first spell entry, u16 entries
          u8 weapon (its inventory entry, 0xFF none)  u8 creature type  u16 attack min/max x3 (creatures)  u16 soul
  AINV  6 bytes an inventory entry: u16 item (AITM row)  i16 count  u8 flags (INV_*)  u8 0
  AITM  28 bytes an item, shared by every actor that carries it and every script that names it:
          u16 id  u8 kind (ITEM_*)  u8 type (weapon or armour type)  u16 condition  u16 armour rating
          u8 damage[6] (chop, slash, thrust: min, max)  u16 flags (1 two-handed)  f32 weight  f32 speed  f32 reach
  ASPT  4 bytes a spell: u16 id  u8 type (0 spell, 1 ability, 2 blight, 3 disease, 4 curse, 5 power)  u8 0
  ASPL  2 bytes a spell entry: u16 spell (ASPT row)
  OACT  2 bytes per OBJS row: the actor its id names (ACTB row, 0xFFFF none); resident, for the scripts' targets

The stats are the record's own (NPDT); NPCs with autocalculated stats (12-byte NPDT) get them by the original
autocalculation as OpenMW documents it (rule from OpenMW apps/openmw/mwclass/npc.cpp autoCalculateAttributes,
autoCalculateSkills; the same code as the combat sheets, tools/prepare_combat.py autocalc). Creatures' 27 skills are
their combat, magic and stealth values by each skill's specialization (rule from OpenMW mwclass/creature.cpp
getSkill). Carried levelled lists are resolved as the combat sheets do (the highest entry at or below the level),
and the equipped weapon and armour are the combat sheets' (prepare_combat.equipment). Race powers are added to an
NPC's spells (OpenMW mwclass/npc.cpp). Nothing of the game is in the repo: everything is read at build time.
"""
import struct

ACTOR_FEMALE, ACTOR_ESSENTIAL, ACTOR_RESPAWN, ACTOR_AUTOCALC = 1, 2, 4, 8
ACTOR_WALKS, ACTOR_SWIMS, ACTOR_FLIES, ACTOR_BIPEDAL = 16, 32, 64, 128
INV_EQUIPPED, INV_LEVELLED, INV_RESTOCKS = 1, 2, 4
ITEM_UNKNOWN, ITEM_WEAPON, ITEM_ARMOR, ITEM_CLOTHING, ITEM_OTHER, ITEM_LEVELLED = 0, 1, 2, 3, 4, 5
OTHER_ITEMS = ('ALCH', 'APPA', 'BOOK', 'INGR', 'LIGH', 'LOCK', 'MISC', 'PROB', 'REPA')
ACTB_BYTES, AINV_BYTES, AITM_BYTES, ASPT_BYTES = 96, 6, 28, 4
NONE = 0xFFFF
TWO_HANDED = {2, 4, 5, 6, 8}
GOLD = 'Gold_001'
GOLD_ALIASES = ('gold_005', 'gold_010', 'gold_025', 'gold_100')


def item_id(ident):
    """The item a script's id means: the gold coins are one item (OpenMW containerextensions.cpp)."""
    return GOLD if ident.casefold() in GOLD_ALIASES else ident


def _first(fields, tag, default=b''):
    return next((v for k, v in fields if k == tag), default)


def _text(data):
    return data.split(b'\0', 1)[0].decode('cp1252', 'replace')


def _clamp(v, lo, hi, what, report):
    if v < lo or v > hi:
        report.setdefault('clamped', {}).setdefault(what, 0)
        report['clamped'][what] += 1
        return max(lo, min(hi, v))
    return v


class ActorTables:
    """The actor and item tables of the game data; strings interned through STRING (Program.string)."""

    def __init__(self, data, string):
        import prepare_combat   # the autocalculation and equipment rules of the combat sheets (one implementation)
        self.pc = prepare_combat
        self.data = data
        self.string = string
        self.records = data.records
        self.report = {}
        self.items = []            # AITM rows (dicts)
        self.item_index = {}
        self.spells = []           # ASPT rows
        self.spell_index = {}
        self.inventory = []        # AINV rows
        self.spell_list = []       # ASPL rows
        self.rows = []             # ACTB rows (dicts), sorted by id
        self.index = {}            # folded id -> ACTB row
        g = self.records['GMST']
        self.settings = {}
        for name in ('fNPCbaseMagickaMult', 'iBaseArmorSkill', 'fLightMaxMod', 'fMedMaxMod', 'iHelmWeight',
                     'iCuirassWeight', 'iPauldronWeight', 'iGreavesWeight', 'iBootsWeight', 'iGauntletWeight',
                     'iShieldWeight', 'fUnarmoredBase1', 'fUnarmoredBase2'):
            f = g.get(name.casefold())
            if f is None:
                continue
            raw = _first(f, 'FLTV') if name[0] == 'f' else _first(f, 'INTV')
            if len(raw) == 4:
                self.settings[name] = struct.unpack('<f' if name[0] == 'f' else '<i', raw)[0]
        # AITM row 0 is the gold item: an actor's gold (its record's gold value) counts as it (OpenMW: gold_005,
        # gold_010, gold_025 and gold_100 are gold_001 for the scripts' item calls, containerextensions.cpp)
        self.item(GOLD)
        self._build()

    # --- shared tables ---
    def item(self, ident):
        """AITM row of an item id (any carried record, a levelled list, or a name no record has)."""
        key = ident.casefold()
        if key in self.item_index:
            return self.item_index[key]
        row = {'id': self.string(ident), 'kind': ITEM_UNKNOWN, 'type': 0, 'health': 0, 'rating': 0,
               'damage': bytes(6), 'flags': 0, 'weight': 0.0, 'speed': 0.0, 'reach': 0.0}
        r = self.records
        if key in r['WEAP']:
            w = _first(r['WEAP'][key], 'WPDT')
            if len(w) >= 28:
                weight, _value, typ, health, speed, reach = struct.unpack_from('<fihhff', w, 0)[:6]
                row.update(kind=ITEM_WEAPON, type=typ & 255, health=max(0, health), damage=bytes(w[22:28]),
                           flags=1 if typ in TWO_HANDED else 0, weight=weight, speed=speed, reach=reach)
        elif key in r['ARMO']:
            a = _first(r['ARMO'][key], 'AODT')
            if len(a) >= 24:
                typ, weight, _value, health, _enchant, rating = struct.unpack_from('<ifiiii', a, 0)
                row.update(kind=ITEM_ARMOR, type=typ & 255, health=min(0xFFFF, max(0, health)),
                           rating=min(0xFFFF, max(0, rating)), weight=weight)
        elif key in r['CLOT']:
            c = _first(r['CLOT'][key], 'CTDT')
            row.update(kind=ITEM_CLOTHING, type=(struct.unpack_from('<i', c)[0] & 255) if len(c) >= 4 else 0,
                       weight=struct.unpack_from('<f', c, 4)[0] if len(c) >= 8 else 0.0)
        elif key in r['LEVI']:
            row['kind'] = ITEM_LEVELLED
        elif any(key in r[t] for t in OTHER_ITEMS):
            row['kind'] = ITEM_OTHER
        self.item_index[key] = len(self.items)
        self.items.append(row)
        return self.item_index[key]

    def spell(self, ident):
        key = ident.casefold()
        if key in self.spell_index:
            return self.spell_index[key]
        f = self.records['SPEL'].get(key)
        spdt = _first(f, 'SPDT') if f else b''
        self.spell_index[key] = len(self.spells)
        self.spells.append({'id': self.string(ident), 'type': struct.unpack_from('<i', spdt)[0] & 255
                            if len(spdt) >= 4 else 255})
        return self.spell_index[key]

    # --- one actor ---
    def _carried(self, fields, level):
        """[(item id, count, flags)] of NPCO entries; levelled lists resolved by the combat sheets' rule."""
        out = []
        for tag, d in fields:
            if tag != 'NPCO' or len(d) != 36:
                continue
            count = struct.unpack_from('<i', d)[0]
            if count == 0:
                continue
            name = _text(d[4:])
            flags = INV_RESTOCKS if count < 0 else 0
            if name.casefold() in self.records['LEVI']:
                picked = self.pc.resolve(self.records, name, level)
                if picked is None:
                    continue
                name, flags = picked, flags | INV_LEVELLED
            out.append((name, abs(count), flags))
        return out

    def _spells(self, fields):
        return [_text(d) for tag, d in fields if tag == 'NPCS']

    def _npc(self, key, fields):
        npdt = _first(fields, 'NPDT')
        flag = struct.unpack('<I', _first(fields, 'FLAG', b'\0\0\0\0')[:4])[0]
        level = struct.unpack_from('<h', npdt)[0] if len(npdt) >= 2 else 1
        row = {'kind': 0, 'flags': (ACTOR_FEMALE if flag & 1 else 0) | (ACTOR_ESSENTIAL if flag & 2 else 0) |
               (ACTOR_RESPAWN if flag & 4 else 0)}
        if len(npdt) == 52:
            attributes, skills = list(npdt[2:10]), list(npdt[10:37])
            health, magicka, fatigue = struct.unpack_from('<3H', npdt, 38)
            disposition, reputation, rank = npdt[44], npdt[45], struct.unpack_from('<b', npdt, 46)[0]
            gold = struct.unpack_from('<i', npdt, 48)[0]
        elif len(npdt) == 12:
            row['flags'] |= ACTOR_AUTOCALC
            race = _text(_first(fields, 'RNAM')).casefold()
            clas = _text(_first(fields, 'CNAM')).casefold()
            if race not in self.records['RACE'] or clas not in self.records['CLAS']:
                self.report.setdefault('autocalc_missing_race_or_class', []).append(key)
                return None
            attributes, skills, health = self.pc.autocalc(self.records, fields, level)
            # dynamic stats of an autocalculated NPC: fatigue Strength + Willpower + Agility + Endurance, magicka
            # Intelligence x fNPCbaseMagickaMult (OpenMW creaturestats.cpp, recalculateMagicka)
            fatigue = attributes[0] + attributes[2] + attributes[3] + attributes[5]
            magicka = int(attributes[1] * self.settings.get('fNPCbaseMagickaMult', 2.0))
            disposition, reputation, rank = npdt[2], npdt[3], struct.unpack_from('<b', npdt, 4)[0]
            gold = struct.unpack_from('<i', npdt, 8)[0]
        else:
            self.report.setdefault('malformed', []).append(key)
            return None
        aidt = _first(fields, 'AIDT')
        ai = (min(255, struct.unpack_from('<H', aidt)[0]), aidt[2], aidt[3], aidt[4]) if len(aidt) >= 5 else (0, 0, 0, 0)
        race = _text(_first(fields, 'RNAM'))
        spells = self._spells(fields)
        if race.casefold() in self.records['RACE']:
            spells += [_text(d) for t, d in self.records['RACE'][race.casefold()] if t == 'NPCS']
        row.update(level=level, attributes=[int(a) for a in attributes], skills=[int(s) for s in skills],
                   ai=ai, disposition=disposition, reputation=reputation, rank=rank,
                   dynamic=(int(health), int(magicka), int(fatigue)), race=race,
                   clas=_text(_first(fields, 'CNAM')), faction=_text(_first(fields, 'ANAM')), gold=gold,
                   carried=self._carried(fields, level), spells=spells, attack=(0,) * 6, soul=0, ctype=0)
        weapon, armor = self.pc.equipment(self.records, fields, level)
        row['equipped'] = {weapon[1]} if weapon else set()
        row['equipped'] |= {a for a, _ in armor.values()}
        row['weapon'] = weapon[1] if weapon else None
        return row

    def _creature(self, key, fields):
        d = _first(fields, 'NPDT')
        if len(d) != 96:
            self.report.setdefault('malformed', []).append(key)
            return None
        v = struct.unpack('<24i', d)
        ctype, level, attributes = v[0], v[1], list(v[2:10])
        health, magicka, fatigue, soul, combat, magic, stealth = v[10:17]
        attack, gold = v[17:23], v[23]
        flag = struct.unpack('<I', _first(fields, 'FLAG', b'\0\0\0\0')[:4])[0]
        skills = []
        for index in range(27):
            sk = _first(self.records['SKIL'].get(index, []), 'SKDT')
            spec = struct.unpack_from('<i', sk, 4)[0] if len(sk) >= 8 else 0
            skills.append((combat, magic, stealth)[spec] if 0 <= spec <= 2 else combat)
        aidt = _first(fields, 'AIDT')
        ai = (min(255, struct.unpack_from('<H', aidt)[0]), aidt[2], aidt[3], aidt[4]) if len(aidt) >= 5 else (0, 0, 0, 0)
        carried = self._carried(fields, level)
        return {'kind': 1, 'flags': (ACTOR_ESSENTIAL if flag & 0x80 else 0) | (ACTOR_RESPAWN if flag & 2 else 0) |
                (ACTOR_WALKS if flag & 0x40 else 0) | (ACTOR_SWIMS if flag & 0x10 else 0) |
                (ACTOR_FLIES if flag & 0x20 else 0) | (ACTOR_BIPEDAL if flag & 1 else 0),
                'level': level, 'attributes': attributes, 'skills': skills, 'ai': ai, 'disposition': 0,
                'reputation': 0, 'rank': -1, 'dynamic': (health, magicka, fatigue), 'race': '', 'clas': '',
                'faction': '', 'gold': gold, 'carried': carried, 'spells': self._spells(fields), 'attack': attack,
                'soul': soul, 'ctype': ctype, 'equipped': set(), 'weapon': None}

    def _build(self):
        rec = self.records
        rows = []
        for key, fields in rec['NPC_'].items():
            row = self._npc(key, fields)
            if row:
                rows.append((key, _text(_first(fields, 'NAME')), row))
        for key, fields in rec['CREA'].items():
            row = self._creature(key, fields)
            if row:
                rows.append((key, _text(_first(fields, 'NAME')), row))
        rows.sort(key=lambda r: r[0].encode('cp1252', 'replace'))
        r = self.report
        for key, name, row in rows:
            row['id'] = self.string(name)
            row['attributes'] = [_clamp(a, 0, 0xFFFF, 'attribute', r) for a in row['attributes']]
            row['skills'] = [_clamp(s, 0, 255, 'skill', r) for s in row['skills']]
            row['dynamic'] = [_clamp(x, 0, 0xFFFF, 'dynamic', r) for x in row['dynamic']]
            row['attack'] = [_clamp(x, 0, 0xFFFF, 'attack', r) for x in row['attack']]
            row['inv_first'] = len(self.inventory)
            weapon = 0xFF
            for name_, count, flags in row['carried']:
                if name_.casefold() in {e.casefold() for e in row['equipped']}:
                    flags |= INV_EQUIPPED
                    if row['weapon'] and name_.casefold() == row['weapon'].casefold() and weapon == 0xFF:
                        weapon = len(self.inventory) - row['inv_first']
                self.inventory.append((self.item(item_id(name_)),_clamp(count, 1, 32767, 'count', r), flags))
            row['inv_count'] = len(self.inventory) - row['inv_first']
            row['weapon_entry'] = weapon if weapon < 255 else 0xFF
            row['spell_first'] = len(self.spell_list)
            seen = set()
            for s in row['spells']:
                if s.casefold() not in seen:
                    seen.add(s.casefold())
                    self.spell_list.append(self.spell(s))
            row['spell_count'] = len(self.spell_list) - row['spell_first']
            self.index[key] = len(self.rows)
            self.rows.append(row)
        r['actors'] = len(self.rows)
        r['npcs'] = sum(1 for x in self.rows if x['kind'] == 0)
        r['creatures'] = len(self.rows) - r['npcs']
        r['autocalc'] = sum(1 for x in self.rows if x['flags'] & ACTOR_AUTOCALC)

    def actor(self, ident):
        """ACTB row of an actor id, or None."""
        return self.index.get(ident.casefold())

    def sections(self, objects):
        """{tag: (bytes, rows)} of the actor sections; OBJECTS: the program's object table rows (OACT)."""
        s = self.string
        actb = bytearray()
        for row in self.rows:
            actb += struct.pack('>HBBH8H27B4BBBbHHHHHHIHHHHBB6HH', row['id'], row['kind'], row['flags'],
                                max(0, min(0xFFFF, row['level'])), *row['attributes'], *row['skills'], *row['ai'],
                                row['disposition'], row['reputation'], max(-128, min(127, row['rank'])),
                                *row['dynamic'], s(row['race']) if row['race'] else NONE,
                                s(row['clas']) if row['clas'] else NONE, s(row['faction']) if row['faction'] else NONE,
                                max(0, min(0xFFFFFFFF, row['gold'])), row['inv_first'], row['inv_count'],
                                row['spell_first'], row['spell_count'], row['weapon_entry'], row['ctype'] & 255,
                                *row['attack'], max(0, min(0xFFFF, row['soul'])))
        ainv = b''.join(struct.pack('>HhBB', i, c, f, 0) for i, c, f in self.inventory)
        aitm = b''.join(struct.pack('>HBBHH6sHfff', r['id'], r['kind'], r['type'], r['health'], r['rating'],
                                    r['damage'], r['flags'], r['weight'], r['speed'], r['reach']) for r in self.items)
        aspt = b''.join(struct.pack('>HBB', r['id'], r['type'], 0) for r in self.spells)
        aspl = b''.join(struct.pack('>H', i) for i in self.spell_list)
        oact = b''.join(struct.pack('>H', NONE if self.actor(o['id']) is None else self.actor(o['id']))
                        for o in objects)
        if len(self.rows) > 0xFFFE or len(self.items) > 0xFFFE or len(self.inventory) > 0xFFFF \
                or len(self.spell_list) > 0xFFFF:
            raise ValueError('actor tables too large for 16-bit indexes')
        assert len(actb) == ACTB_BYTES * len(self.rows)
        return {'ACTB': (bytes(actb), len(self.rows)), 'AINV': (ainv, len(self.inventory)),
                'AITM': (aitm, len(self.items)), 'ASPT': (aspt, len(self.spells)), 'ASPL': (aspl, len(self.spell_list)),
                'OACT': (oact, len(objects))}


def read_actor(raw, index):
    """One ACTB row as a dict (tests, the measurement)."""
    v = struct.unpack_from('>HBBH8H27B4BBBbHHHHHHIHHHHBB6HH', raw, ACTB_BYTES * index)
    return {'id': v[0], 'kind': v[1], 'flags': v[2], 'level': v[3], 'attributes': list(v[4:12]),
            'skills': list(v[12:39]), 'hello': v[39], 'fight': v[40], 'flee': v[41], 'alarm': v[42],
            'disposition': v[43], 'reputation': v[44], 'rank': v[45], 'health': v[46], 'magicka': v[47],
            'fatigue': v[48], 'race': v[49], 'class': v[50], 'faction': v[51], 'gold': v[52], 'inv_first': v[53],
            'inv_count': v[54], 'spell_first': v[55], 'spell_count': v[56], 'weapon': v[57], 'type': v[58],
            'attack': list(v[59:65]), 'soul': v[65]}
