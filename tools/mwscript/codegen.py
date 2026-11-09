# SPDX-License-Identifier: GPL-3.0-only
"""Typed stack bytecode from the parser's tree (opcodes.py), and the program's shared tables.

What the compiler does beyond a plain translation (docs/MWSCRIPT_BYTECODE.md "What the compiler squeezes"):
  - every value is typed at build time: whole-number and fraction opcodes, conversions only where the types meet;
  - constants are folded ("set x to 2 * 30" stores 60) and branches on a constant are dropped;
  - the smallest push for each constant (1, 3 or 5 bytes);
  - names become indexes: globals, journal topics, sounds, voices, music tracks, objects, scripts, strings;
  - each script is marked VOLATILE when it reads something outside the game state (time, distance, chance, a
    sound still playing, an engine query): only those must run every frame; the others run again only when the
    state they read has changed (engine/aga/src/aw_mwvm.c).
"""
import struct

from .opcodes import CODE, CMP_I, CMP_F, ARITH_I, ARITH_F, NONE, QUERIES, WHOLE_STATS, VERBS, CMP_CODES, SPELL_VERBS

# The squeeze switch: False builds the program without the compare-and-branch opcodes (the A/B reference run; the
# builder always squeezes).
SQUEEZE = True
from .functions import lookup, ACTOR_CALLS, HOST, HOST_EFFECT_NUMBERS, RESISTS

# A VISI row's room for an actor that may stand in any room: a follower of the player (AIFollow, AIFollowCell; v0.0.62)
VISI_ANY = 0xFFFFFFFF

# The magic effects in the game's numbering (the MGEF index; OpenMW components/esm3/loadmgef.cpp lists them in this
# order): GetEffect names one as "sEffect<Name>" (v0.0.57)
EFFECT_NAMES = (
    'WaterBreathing SwiftSwim WaterWalking Shield FireShield LightningShield FrostShield Burden Feather Jump Levitate '
    'SlowFall Lock Open FireDamage ShockDamage FrostDamage DrainAttribute DrainHealth DrainMagicka DrainFatigue '
    'DrainSkill DamageAttribute DamageHealth DamageMagicka DamageFatigue DamageSkill Poison WeaknessToFire '
    'WeaknessToFrost WeaknessToShock WeaknessToMagicka WeaknessToCommonDisease WeaknessToBlightDisease '
    'WeaknessToCorprusDisease WeaknessToPoison WeaknessToNormalWeapons DisintegrateWeapon DisintegrateArmor '
    'Invisibility Chameleon Light Sanctuary NightEye Charm Paralyze Silence Blind Sound CalmHumanoid CalmCreature '
    'FrenzyHumanoid FrenzyCreature DemoralizeHumanoid DemoralizeCreature RallyHumanoid RallyCreature Dispel Soultrap '
    'Telekinesis Mark Recall DivineIntervention AlmsiviIntervention DetectAnimal DetectEnchantment DetectKey '
    'SpellAbsorption Reflect CureCommonDisease CureBlightDisease CureCorprusDisease CurePoison CureParalyzation '
    'RestoreAttribute RestoreHealth RestoreMagicka RestoreFatigue RestoreSkill FortifyAttribute FortifyHealth '
    'FortifyMagicka FortifyFatigue FortifySkill').split()
# Spell effects of the first slice beyond Fortify/Drain/Damage/Restore (v0.0.57): the cures (effect number: the ASPT
# spell type they remove) and the effects that hurt health like Damage Health
CURE_EFFECTS = {69: 3, 70: 2, 72: 0}
HEALTH_DAMAGE_EFFECTS = (14, 15, 16, 27)
# v0.0.62 (MWSCRIPT-UNPLACED-ATTACH-62, the shrines' blessings): the effects with no attribute or skill that only stand
# on the actor for their duration with a magnitude (OpenMW 0.51 keeps them in the actor's active effects and the systems
# read their magnitude: MagicEffects): an SPFX effect of kind 5, the effect's number as its stat; the engine lands it
# with AW_EffectsLand. Water Breathing .. Slow Fall, the weaknesses, Invisibility .. Night Eye, the detections, Spell
# Absorption, Reflect, Fortify Maximum Magicka, the resistances and Fortify Attack. Actions (Lock, Open, Mark, Recall,
# the interventions, Dispel, the summons, the bound items, Calm, Frenzy, Command) are not among them: a spell with one
# stays "not yet".
PASSIVE_EFFECTS = frozenset(list(range(0, 12)) + list(range(28, 37)) + list(range(39, 44)) + [64, 65, 66, 67, 68, 84]
                            + list(range(90, 100)) + [117])
# Cast carried out (v0.0.57): the cures on the player (aw_mwhost.c AWF_CAST)
CURES = ('cure common disease', 'cure blight disease', 'cure poison')
# The placing family (v0.0.62, MWSCRIPT-PLACE-OBJECTS-62): the calls (their object id is always the first argument),
# the kinds of a PLAC row, the record types the inventory carries, and the most rows a placed actor's key can name
# (aw_mwhost.c placed_key: 0xF00000 | row << 12 | serial)
import re as _re
PLACE_CALL = _re.compile(r'(?i)\b(place(?:atpc|atme|itemcell|item)|drop)\b[\s,]+("[^"]+"|[^\s,"]+)')
PLACE_FUNCTIONS = ('placeatpc', 'placeatme', 'placeitem', 'placeitemcell')
PLACE_KINDS = {'actor': 0, 'item': 1, 'other': 2}
PLACE_ITEM_TAGS = ('WEAP', 'ARMO', 'CLOT', 'ALCH', 'APPA', 'BOOK', 'INGR', 'LIGH', 'LOCK', 'MISC', 'PROB', 'REPA')
PLACE_ROWS_MAX = 256
SCRIPT_VOLATILE = 1     # reads time, distance, chance, sound state or an engine query
SCRIPT_NOTYET = 2        # holds at least one NOTYET call
SCRIPT_START = 4         # a start script (runs from the beginning of the game)
SCRIPT_BROKEN = 8        # did not compile (an error in the original data); its code is END
SCRIPT_GLOBAL = 16       # started by StartScript somewhere (runs as a global script)
SCRIPT_HANDWRITTEN = 32  # the engine carries this behaviour by hand today (config/mwscript.json): not run
SCRIPT_INERT = 64        # nothing it can do today is seen outside its own values (no sound, global, journal, other
                         # object, script start or stop; only NOTYET calls): not attached until that changes
SCRIPT_ONACTIVATE = 128  # reads OnActivate: the player's use of its object goes to the script (the original's rule)
SCRIPT_ACTOR = 256       # reads the actor record (stats, items, spells, deaths): not VOLATILE; it wakes when the
                         # state generation moves, which a script's change or the engine's (a hit, a death) does
EFFECT_OPS = {'SETG', 'SETGS', 'SETM', 'SETMS', 'SETJ', 'JOURNAL', 'PLAYSOUND', 'PLAYSOUNDVP', 'PLAYSOUND3D',
              'PLAYSOUND3DVP', 'PLAYLOOP3D', 'PLAYLOOP3DVP', 'STOPSOUND', 'SAY', 'STREAMMUSIC', 'STARTSCRIPT',
              'STOPSCRIPT', 'ENABLE', 'DISABLE', 'LOCK', 'UNLOCK', 'ACTIVATE', 'COMBAT', 'AIWANDER', 'PLAYERMOVE',
              # MWSCRIPT-INERT-SEEN-62: a message box is seen; reading OnActivate takes the object's use over (the
              # door that stays shut, the item that cannot be taken: OpenMW 0.51 mwworld/action and the activation
              # rule of a script that tests OnActivate), so a script holding either is not inert
              'MESSAGEBOX', 'ONACTIVATE'}
# ACTOR, ITEM and SPELL are effects only when they change something (their verb): see effect_op()


def effect_op(name, args):
    """Whether one decoded opcode is seen outside the script's own values (the INERT rule)."""
    if name in EFFECT_OPS:
        return True
    if name == 'ACTOR':
        return args[0] in (VERBS['set'], VERBS['mod'], VERBS['modcurrent'])
    if name == 'ITEM':
        return args[0] != 0
    if name == 'SPELL':
        return args[0] in (SPELL_VERBS['add'], SPELL_VERBS['remove'])
    if name == 'NOTYET':
        # the import route's calls the engine carries out (functions.HOST) and that change something
        return args[0] in HOST_EFFECT_NUMBERS
    return False

# The opcodes whose answer changes without the state generation moving (a script that holds one runs every frame).
# Not among them: CELLCHANGED (true only when the script is woken anyway) and SOUNDPLAYING (the script's own
# sounds: it acted when it started one, and the host wakes it when one ends).
VOLATILE_OPS = {'SECONDS', 'RANDOM', 'MENUMODE', 'SAYDONE', 'DISTANCE', 'QUERY',
                'SCRIPTRUNNING', 'GETDISABLED', 'GETLOCKED', 'ONACTIVATE', 'GETPOS'}


class CompileError(ValueError):
    pass


class Table:
    """An interned list: key -> index, with the stored row for each index."""

    def __init__(self, limit=0xFFFE):
        self.index, self.rows, self.limit = {}, [], limit

    def get(self, key, row=None):
        if key in self.index:
            return self.index[key]
        if len(self.rows) >= self.limit:
            raise CompileError('table full')
        self.index[key] = len(self.rows)
        self.rows.append(row if row is not None else key)
        return self.index[key]

    def __len__(self):
        return len(self.rows)


SCRIPT_DIALOGUE = 512   # a dialogue result script (_dlg_N): run when its answer is shown, never attached or started


def fnv1a(raw):
    """32-bit FNV-1a of bytes (the DRSC key; aw_mwvm.c computes the same)."""
    h = 0x811C9DC5
    for b in raw:
        h = ((h ^ b) * 0x01000193) & 0xFFFFFFFF
    return h


def check_result_keys(results):
    """Stop the build when two different result texts share (hash, length): the engine tells result scripts apart by
    those two alone, so such a pair could run the wrong script. Names both texts."""
    seen = {}
    for r in results:
        key = (r['hash'], r['length'])
        other = seen.setdefault(key, r['text'])
        if other != r['text']:
            raise CompileError('two dialogue result texts share the hash %08x and the length %d: %r and %r'
                               % (key[0], key[1], other[:60], r['text'][:60]))


class Program:
    """The tables every script shares, filled while scripts compile.

    data: GameData. media: an object with sound(id) / voice(path) / music(path) -> row dict or None (media.py);
    None makes rows from the game data alone (the measurement before a catalogue exists)."""

    def __init__(self, data, media=None, scripts=None):
        self.data = data
        self.media = media
        self.strings = Table()
        self.globals = Table()
        self.journal = Table()
        self.sounds = Table()
        self.voices = Table()
        self.music = Table()
        self.objects = Table()
        self.scripts = Table()
        self.pccells = Table()    # GetPCCell names: the cells each one matches (the PCEL section)
        self.moves = Table()      # the player's PositionCell moves, worked out at build time (the PMOV section)
        # the actors a PositionCell may bring into a room (the VISI section): (room number, reference) -> the home
        # room map's name (a string index, NONE: outdoors or a room this build lacks)
        self.visitors = {}
        self._place_rows = None   # the objects the scripts' Place calls name (the PLAC section): place_rows()
        self.rooms = None        # {interior cell: room map and recentring} (rooms.room_table; compiler.py sets it)
        self.unresolved = []      # (script, kind, name, reason)
        for name, (kind, value, spelling) in data.globals.items():
            self.globals.get(name, {'name': spelling, 'type': kind, 'value': value})
        self.script_locals = {}   # folded script id -> {local: (type, slot)}
        for s in (data.scripts.values() if scripts is None else scripts):
            self.scripts.get(s.id.casefold(), {'name': s.id, 'script': s})
        self.results = []           # the dialogue's result scripts (the DRSC section): see dialogue_results()
        if scripts is None:
            self.dialogue_results()
        # the actor table (actors.py): every NPC and creature record, the items and spells they and the scripts name
        from .actors import ActorTables
        self.actors = ActorTables(data, self.string)

    def dialogue_results(self):
        """Every distinct (speaker, result text) of the dialogue becomes a script of its own (_dlg_N, flag
        SCRIPT_DIALOGUE), its body the text, declared with the speaker's own script's locals in slot order, so it
        runs on the speaker's instance and reads and sets the speaker's locals (as the original runs a result in the
        speaker's script context). A speaker with no script, or a line any speaker may say: no locals. The engine
        finds one by the text's FNV-1a hash, its length and the speaker's script (DRSC rows), so a collision never
        runs another text's script."""
        from .gamedata import Script
        from .parser import Parser
        globals_ = {k: v[0] for k, v in self.data.globals.items()}
        declared = {}
        for n, ((speaker, text), _) in enumerate(self.data.results.items()):
            script = self.data.bases.get(speaker, (None, ''))[1] if speaker else ''
            if script not in self.data.scripts:
                script = ''
            if script not in declared:
                lines = []
                if script:
                    p = Parser(self.data.scripts[script].text, globals_)
                    try:
                        p.script()
                    except Exception:   # noqa: BLE001 (a broken speaker script: its locals as far as read)
                        pass
                    word = {'s': 'short', 'l': 'long', 'f': 'float'}
                    lines = ['%s %s' % (word.get(letter, 'short'), name)
                             for name, (letter, slot) in sorted(p.locals.items(), key=lambda kv: kv[1][1])]
                declared[script] = '\n'.join(lines)
            ident = '_dlg_%d' % n
            body = 'Begin %s\n%s\n%s\nEnd %s\n' % (ident, declared[script], text, ident)
            s = Script(ident, 'dialogue', body, len(text), 0, (0, 0, 0, 0, 0), [])
            self.scripts.get(ident, {'name': ident, 'script': s, 'dialogue': True, 'speaker': speaker})
            raw = text.encode('cp1252', 'replace')
            self.results.append({'hash': fnv1a(raw), 'length': len(raw), 'speaker_script': script, 'script': ident,
                                 'text': raw})
        check_result_keys(self.results)

    def string(self, text):
        return self.strings.get(text)

    def topic(self, name):
        key = name.casefold()
        return self.journal.get(key, {'name': name})

    def sound(self, name, script):
        key = name.casefold()
        if key in self.sounds.index:
            return self.sounds.index[key]
        row = self.media.sound(name) if self.media else None
        if row is None:
            soun = self.data.sounds.get(key)
            row = {'id': name, 'resolved': False, 'reason': 'no SOUN record' if soun is None else 'not mapped',
                   'volume': soun['volume'] if soun else 255, 'min': soun['min'] if soun else 0,
                   'max': soun['max'] if soun else 0}
        if not row.get('resolved'):
            self.unresolved.append((script, 'sound', name, row.get('reason')))
        row.setdefault('name_string', self.string(name))
        return self.sounds.get(key, row)

    def voice(self, path, script):
        key = path.replace('\\', '/').casefold()
        if key in self.voices.index:
            return self.voices.index[key]
        row = self.media.voice(path) if self.media else None
        if row is None:
            row = {'path': path, 'resolved': False, 'reason': 'not mapped'}
        if not row.get('resolved'):
            self.unresolved.append((script, 'voice', path, row.get('reason')))
        row.setdefault('name_string', self.string(path))
        return self.voices.get(key, row)

    def track(self, path, script):
        key = path.replace('\\', '/').casefold()
        if key in self.music.index:
            return self.music.index[key]
        row = self.media.music(path) if self.media else None
        if row is None:
            row = {'path': path, 'resolved': False, 'reason': 'not mapped', 'track': 255}
        if not row.get('resolved'):
            self.unresolved.append((script, 'music', path, row.get('reason')))
        row.setdefault('name_string', self.string(path))
        return self.music.get(key, row)

    def object(self, name):
        """Object table index of an object id or a script name ('player' is NONE)."""
        key = name.casefold()
        if key == 'player':
            return NONE
        if key in self.objects.index:
            return self.objects.index[key]
        refs = self.data.object_refs.get(key, [])
        base = self.data.bases.get(key)
        row = {'id': name, 'reference': refs[0] if len(refs) == 1 else 0, 'placed': len(refs),
               'script': None, 'kind': 'object'}
        if base and base[1] and base[1] in self.scripts.index:
            row['script'] = self.scripts.index[base[1]]
        elif key in self.scripts.index and not base:
            row.update(kind='script', script=self.scripts.index[key])
        row['id_string'] = self.string(name)
        return self.objects.get(key, row)

    def pccell(self, name):
        """PCEL row of a GetPCCell name: every cell whose name starts with it, without case (rule from OpenMW
        apps/openmw/mwscript/cellextensions.cpp OpGetPCCell): rooms by their stable number (_aw_cell_int), outdoor
        cells by grid, an outdoor cell named by its own name, else its region's name, else the game setting
        sDefaultCellname (OpenMW's world getCellName). Made once here, so the engine compares numbers, never text."""
        key = name.casefold()
        if key in self.pccells.index:
            return self.pccells.index[key]
        d = self.data
        rooms = sorted(n for cell, n in d.interior_numbers.items() if cell.startswith(key))
        outside = sorted(xy for xy, (cell, region) in d.exteriors.items()
                         if (cell or d.regions.get(region) or d.default_cell_name).casefold().startswith(key))
        if any(n > 0xFFFF for n in rooms) or any(not (-128 <= v <= 127) for xy in outside for v in xy):
            raise CompileError('GetPCCell %r: a cell outside the table\'s ranges' % name)
        wild = d.default_cell_name.casefold().startswith(key)
        return self.pccells.get(key, {'name': name, 'rooms': rooms, 'outside': outside, 'wilderness': wild})

    def spell_effects(self, spell):
        """The SPFX row of a spell whose every effect is in the first slice of the spell effects (v0.0.57,
        SPELL-EFFECTS-57), else None. Each effect: (kind 0 drain 1 damage 2 restore 3 fortify, the actor record's stat
        number, duration seconds, magnitude low, high), from the SPEL record's ENAM (OpenMW's effect numbers: drain
        17-21, damage 22-26, restore 74-78, fortify 79-83; each block attribute, health, magicka, fatigue, skill)."""
        if not hasattr(self, 'spfx'):
            self.spfx = Table()
        key = spell.casefold()
        if key in self.spfx.index:
            return self.spfx.index[key]
        parts = getattr(self.data, 'records', {}).get('SPEL', {}).get(key)
        if not parts:
            return None
        effects = []
        for tag, data in parts:
            if tag != 'ENAM' or len(data) < 24:
                continue
            number, skill, attribute, _rng, _area, duration, low, high = struct.unpack_from('<hbbiiiii', data)
            if number in CURE_EFFECTS:
                # a cure (kind 4): the spell type it removes (3 common disease, 2 blight; 0 poison: no state yet)
                effects.append((4, CURE_EFFECTS[number], 0, 0, 0))
                continue
            if number in PASSIVE_EFFECTS:
                # kind 5: the effect by its number (no attribute or skill), for its duration
                effects.append((5, number, max(0, min(duration, 0xFFFF)), max(0, min(low, 0xFFFF)),
                                max(0, min(max(low, high), 0xFFFF))))
                continue
            if number in HEALTH_DAMAGE_EFFECTS:
                # Fire, Frost and Shock Damage and Poison hurt health like Damage Health (OpenMW spelleffects.cpp);
                # resistances do not exist here yet, so the full magnitude lands
                number = 23
            kind = next((k for k, b in enumerate((17, 22, 74, 79)) if b <= number <= b + 4), None)
            if kind is None:
                return None
            which = number - (17, 22, 74, 79)[kind]
            if which == 0:
                if not 0 <= attribute < 8:
                    return None
                stat = attribute
            elif which == 4:
                if not 0 <= skill < 27:
                    return None
                stat = 8 + skill
            else:
                stat = 34 + which            # 35 health, 36 magicka, 37 fatigue (docs/ACTOR_STATE.md)
            effects.append((kind, stat, max(0, min(duration, 0xFFFF)), max(0, min(low, 0xFFFF)),
                            max(0, min(max(low, high), 0xFFFF))))
        if not effects or len(effects) > 8:
            return None
        return self.spfx.get(key, {'name': spell, 'effects': effects})

    def topic_rows(self):
        """The game's dialogue topics, sorted by folded id: {folded id: TOPC row} (v0.0.57)."""
        if getattr(self, '_topic_rows', None) is None:
            self._topic_rows = {k: i for i, k in enumerate(sorted(getattr(self.data, 'topics', {})))}
        return self._topic_rows

    def player_move(self, args):
        """PMOV row of a PositionCell of the player, or None when it stays "not yet" (a number not constant, a room no
        repo list names). Rule from OpenMW apps/openmw/mwscript/transformationextensions.cpp OpPositionCell: a cell
        that is no interior moves the player outdoors to x, y (also an unknown name); the player's rotation is in
        degrees. Into a room: its map and the arrival as a door's (rooms.py)."""
        from .opcodes import PLAYERMOVE_KINDS
        numbers = [fold(a) for a in args if a[0] != 'str'][:4]
        cells = [a[1] for a in args if a[0] == 'str']
        if len(numbers) < 4 or not all(_const(n) for n in numbers) or not cells:
            return None
        x, y, z, rot = (float(n[1]) for n in numbers)
        key = cells[0].casefold()
        if key in self.data.interior_numbers:
            room = (self.rooms or {}).get(key)
            if room is None:
                return None
            from .rooms import arrival
            ax, ay, az, yaw = arrival((x, y, z), rot, room.get('offset'))
            row = {'kind': PLAYERMOVE_KINDS['room'], 'map': self.string(room['map']), 'at': (ax, ay, az), 'yaw': yaw}
        else:
            row = {'kind': PLAYERMOVE_KINDS['outdoors'], 'map': NONE, 'at': (x, y, z), 'yaw': rot}
        return self.moves.get((row['kind'], row['map'], row['at'], row['yaw']), row)

    def actor_move(self, args):
        """(kind, room number, x, y, z, yaw) of a PositionCell of anything but the player, 'unknown' for a cell the
        game has not (OpenMW does nothing then), or None when it stays "not yet" (a number not constant, no cell).
        Rules from OpenMW apps/openmw/mwscript/transformationextensions.cpp OpPositionCell: an interior cell by its
        name, else an exterior cell by its name (the reference goes to the exterior cell at x, y); the rotation of
        anything but the player is in minutes of arc (60 a degree). Into a room: x, y, z in that room map's own units
        (a quarter scale, a recentred room's offset first; tools/prepare_npcs.py places a resident so), the room's
        stable number; outdoors: the original's units. YAW is Quake's (an NPC's angles: minus the original's z)."""
        from .opcodes import PLAYERMOVE_KINDS
        numbers = [fold(a) for a in args if a[0] != 'str'][:4]
        cells = [a[1] for a in args if a[0] == 'str']
        if len(numbers) < 4 or not all(_const(n) for n in numbers) or not cells:
            return None
        x, y, z, rot = (float(n[1]) for n in numbers)
        yaw = round((-rot / 60.0) % 360.0, 5) % 360.0
        key = cells[0].casefold()
        if key in self.data.interior_numbers:
            room = (self.rooms or {}).get(key) or {}
            offset = room.get('offset') or (0.0, 0.0, 0.0)
            at = tuple(round((v - offset[k]) * 0.25, 5) for k, v in enumerate((x, y, z)))
            return (PLAYERMOVE_KINDS['room'], self.data.interior_numbers[key]) + at + (yaw,)
        if key in self.exterior_names():
            return (PLAYERMOVE_KINDS['outdoors'], 0, x, y, z, yaw)
        return 'unknown'

    def exterior_names(self):
        """The folded names of the exterior cells that have one (OpenMW's findCell finds an exterior by its name)."""
        if getattr(self, '_exterior_names', None) is None:
            self._exterior_names = {cell.casefold() for cell, _ in self.data.exteriors.values() if cell}
        return self._exterior_names

    def visitor(self, room_number, ref, ident):
        """Note the actors a PositionCell into room ROOM_NUMBER may bring there (the VISI rows): REF's placed
        references (Morrowind.esm, the world the image has), or with no reference the script's own bearers (the
        records that carry script IDENT; a dialogue result: its speaker). Each with its home room's map, from which
        the engine reads the actor's entity when it arrives while its home is not loaded."""
        d = self.data
        cells = getattr(d, 'actor_cells', {})
        if ref is not None:
            ids = [ref.casefold()]
        else:
            row = self.scripts.rows[self.scripts.index[ident.casefold()]] if ident.casefold() in self.scripts.index \
                else {}
            if row.get('dialogue'):
                ids = [row['speaker']] if row.get('speaker') else []
            else:
                ids = sorted(k for k, (_tag, script) in d.bases.items() if script == ident.casefold())
        for name in ids:
            for number in d.object_refs.get(name, []):
                if number not in cells:
                    continue                  # not an actor
                home = cells[number]
                room = (self.rooms or {}).get(home) if home else None
                key = (room_number, number & 0xFFFFFF)
                if key not in self.visitors:
                    self.visitors[key] = self.string(room['map']) if room else NONE

    def place_rows(self):
        """The PLAC rows (v0.0.62, MWSCRIPT-PLACE-OBJECTS-62): every object id a PlaceAtPC, PlaceAtMe, PlaceItem or
        PlaceItemCell call of the game names (the scripts and the dialogue results, read once from the text), sorted by
        folded id, so a row's number depends on the game data alone: the engine keys a placed actor by it (aw_mwhost.c
        placed_key). Each row: the id, its kind (PLACE_KINDS: an NPC or creature, a carried item, anything else), for
        an actor a template (a reference of that record placed in Morrowind.esm, a room's first when one has it, with
        that room's map name) and the record's own script, and whether the engine can make it (an actor needs a placed
        reference of its record, whose converted model the build has; an item the inventory catalogue's row)."""
        if self._place_rows is None:
            ids = set()
            texts = [s.text for s in self.data.scripts.values()] + [t for (_speaker, t) in self.data.results]
            for text in texts:
                for line in (text or '').splitlines():
                    for m in PLACE_CALL.finditer(line.split(';', 1)[0]):
                        ids.add(m.group(2).strip('"').casefold())
            self._place_rows = []
            self._place_index = {}
            for ident in sorted(ids):
                self._place_add(ident)
        return self._place_rows

    def _place_add(self, ident):
        d = self.data
        recs = getattr(d, 'records', {})
        if ident in recs.get('NPC_', {}) or ident in recs.get('CREA', {}):
            kind = 'actor'
        elif any(ident in recs.get(tag, {}) for tag in PLACE_ITEM_TAGS):
            kind = 'item'
        else:
            kind = 'other'
        template, home = 0, NONE
        refs = sorted(d.object_refs.get(ident, []))
        cells = d.actor_cells if kind == 'actor' else getattr(d, 'object_cells', {})
        if kind in ('actor', 'other') and refs:
            in_rooms = [(n, (self.rooms or {}).get(cells.get(n))) for n in refs if cells.get(n)]
            in_rooms = [(n, room) for n, room in in_rooms if room]
            if in_rooms:
                template, home = in_rooms[0][0] & 0xFFFFFF, self.string(in_rooms[0][1]['map'])
            else:
                template = refs[0] & 0xFFFFFF
        base = d.bases.get(ident)
        script = self.scripts.index.get(base[1], NONE) if base and base[1] else NONE
        # v0.0.62 (MWSCRIPT-GAP-FUNCTIONS-62): every NPC or creature record can be made (with no placed reference, from
        # the actor table's base the builder adds for each actor a script places: chim.actors script_placed_actors);
        # any other object from a placed reference of its record (its entity in a map, the template)
        carried = kind in ('item', 'actor') or (kind == 'other' and bool(refs))
        row = {'key': ident, 'id': self.string(ident), 'kind': PLACE_KINDS[kind], 'template': template,
               'home': home, 'script': script, 'carried': carried}
        self._place_index[ident] = len(self._place_rows)
        self._place_rows.append(row)
        return self._place_index[ident]

    def placed(self, ident):
        """The PLAC row number of object IDENT when the engine can make it, else None ("not yet")."""
        rows = self.place_rows()
        key = ident.casefold()
        k = self._place_index.get(key)
        if k is None:
            k = self._place_add(key)      # a call the text scan missed: after the sorted rows, still deterministic
        return k if rows[k]['carried'] and k < PLACE_ROWS_MAX else None

    def item(self, name):
        """AITM row of an item id a script names (the gold coins are one item)."""
        from .actors import item_id
        return self.actors.item(item_id(name))

    def spell(self, name):
        """ASPT row of a spell id a script names."""
        return self.actors.spell(name)

    def locals_of(self, name):
        """{local: (type, slot)} of the script an object id or script name runs, or None."""
        key = name.casefold()
        base = self.data.bases.get(key)
        script = base[1] if base and base[1] else (key if key in self.data.scripts else None)
        return self.script_locals.get(script) if script else None

    def equip_rows(self):
        """The EQUP rows (v0.0.62, MWSCRIPT-GAP-FUNCTIONS-62; OpenMW 0.51 mwgui/inventorywindow.cpp useItem): every
        carried item record whose script declares OnPCEquip or PCSkipEquip, sorted by folded id: (key, id string,
        script row, OnPCEquip's slot, PCSkipEquip's slot; 0xFF when the script has not that local). The engine sets
        OnPCEquip when the player equips the item and refuses the equipping while PCSkipEquip is 1."""
        rows = []
        recs = getattr(self.data, 'records', {})
        for tag in PLACE_ITEM_TAGS:
            for ident in recs.get(tag, {}):
                base = self.data.bases.get(ident)
                locs = self.script_locals.get(base[1]) if base and base[1] else None
                if not locs or base[1] not in self.scripts.index:
                    continue
                on, skip = locs.get('onpcequip'), locs.get('pcskipequip')
                if on is None and skip is None:
                    continue
                rows.append((ident, self.string(ident), self.scripts.index[base[1]],
                             on[1] if on is not None and on[1] < 0xFF else 0xFF,
                             skip[1] if skip is not None and skip[1] < 0xFF else 0xFF))
        return sorted(rows)


class Emitter:
    def __init__(self):
        self.code = bytearray()
        self.ops = []          # (offset, name) for the statistics
        self.depth = 0
        self.max_depth = 0

    def op(self, name, *operands, layout=None, pops=0, pushes=0):
        from .opcodes import LAYOUT
        code = CODE[name]
        self.ops.append((len(self.code), name))
        self.code.append(code)
        fmt = layout if layout is not None else LAYOUT[code]
        for letter, value in zip(fmt, operands):
            self.code += struct.pack({'b': '>b', 'B': '>B', 'h': '>h', 'H': '>H', 'i': '>i', 'f': '>f'}[letter],
                                     value)
        self.depth += pushes - pops
        self.max_depth = max(self.max_depth, self.depth)
        return len(self.code)

    def jump(self, name):
        """A jump with its offset to patch; returns the patch position."""
        pops = 1 if name == 'JZ' else 0
        self.op(name, 0, pops=pops)
        return len(self.code) - 2

    def patch(self, at, target=None):
        target = len(self.code) if target is None else target
        delta = target - (at + 2)
        if not -32768 <= delta <= 32767:
            raise CompileError('jump too far')
        self.code[at:at + 2] = struct.pack('>h', delta)


def _const(node):
    return node[0] in ('int', 'float')


def fold(node):
    """Constant folding on the tree (whole numbers stay whole, as the game computes them)."""
    kind = node[0]
    if kind == 'bin':
        a, b = fold(node[2]), fold(node[3])
        if _const(a) and _const(b):
            x, y = a[1], b[1]
            whole = a[0] == 'int' and b[0] == 'int'
            op = node[1]
            if op == '/' and y == 0:
                return ('bin', op, a, b)
            if op == '+':
                v = x + y
            elif op == '-':
                v = x - y
            elif op == '*':
                v = x * y
            else:
                v = int(x / y) if whole else x / y
            if whole and -2 ** 31 <= v < 2 ** 31:
                return ('int', v)
            if not whole:
                return ('float', float(struct.unpack('>f', struct.pack('>f', v))[0]))
        return ('bin', node[1], a, b)
    if kind == 'neg':
        a = fold(node[1])
        return (a[0], -a[1]) if _const(a) else ('neg', a)
    if kind == 'cmp':
        a, b = fold(node[2]), fold(node[3])
        if _const(a) and _const(b):
            x, y = a[1], b[1]
            v = {'==': x == y, '!=': x != y, '<': x < y, '<=': x <= y, '>': x > y, '>=': x >= y}[node[1]]
            return ('int', int(v))
        return ('cmp', node[1], a, b)
    return node


class ScriptCompiler:
    def __init__(self, program, ident, tree, local_types, warnings):
        self.p = program
        self.ident = ident
        self.tree = tree
        self.locals = local_types          # {name: (type letter, slot)}
        self.e = Emitter()
        self.warnings = warnings
        self.flags = 0
        self.calls = []                    # function names compiled (with repeats)
        self.notyet_names = []             # the calls compiled to NOTYET (with repeats)
        self.loops = 0

    # --- expressions: emit and return 'i' or 'f' ---
    def push_const(self, node):
        if node[0] == 'int':
            v = node[1]
            if -128 <= v <= 127:
                self.e.op('PUSHB', v, pushes=1)
            elif -32768 <= v <= 32767:
                self.e.op('PUSHW', v, pushes=1)
            else:
                self.e.op('PUSHL', max(-2 ** 31, min(2 ** 31 - 1, v)), pushes=1)
            return 'i'
        self.e.op('PUSHF', node[1], pushes=1)
        return 'f'

    def convert(self, have, want):
        if have == want:
            return
        if want == 'f':
            self.e.op('I2F')
        else:
            self.e.op('F2I')

    def expr(self, node):
        node = fold(node)
        kind = node[0]
        if kind in ('int', 'float'):
            return self.push_const(node)
        if kind == 'local':
            letter, slot = self.locals[node[1]]
            self.e.op('GETL', slot, pushes=1)
            return 'f' if letter == 'f' else 'i'
        if kind == 'global':
            index = self.p.globals.index[node[1]]
            self.e.op('GETG', index, pushes=1)
            return 'f' if self.p.globals.rows[index]['type'] == 'f' else 'i'
        if kind == 'member':
            target = self.member(node[1], node[2])
            if target is None:
                return self.push_const(('int', 0))
            obj, slot, letter = target
            self.e.op('GETM', obj, slot, pushes=1)
            return 'f' if letter == 'f' else 'i'
        if kind == 'neg':
            t = self.expr(node[1])
            self.e.op('NEGF' if t == 'f' else 'NEGI')
            return t
        if kind in ('bin', 'cmp'):
            # whole with whole stays whole; any fraction makes both sides fractions (the game's arithmetic)
            t = 'f' if 'f' in (self.typeof(node[2]), self.typeof(node[3])) else 'i'
            self.convert(self.expr(node[2]), t)
            self.convert(self.expr(node[3]), t)
            if kind == 'bin':
                self.e.op((ARITH_F if t == 'f' else ARITH_I)[node[1]], pops=2, pushes=1)
                return t
            self.e.op((CMP_F if t == 'f' else CMP_I)[node[1]], pops=2, pushes=1)
            return 'i'
        if kind == 'call':
            t = self.call(node, value=True)
            return t
        raise CompileError('unknown expression ' + kind)

    def typeof(self, node):
        """The type an expression has, without emitting it."""
        node = fold(node)
        kind = node[0]
        if kind == 'int':
            return 'i'
        if kind == 'float':
            return 'f'
        if kind == 'local':
            return 'f' if self.locals[node[1]][0] == 'f' else 'i'
        if kind == 'global':
            return 'f' if self.p.globals.rows[self.p.globals.index[node[1]]]['type'] == 'f' else 'i'
        if kind == 'member':
            table = self.p.locals_of(node[1])
            found = table.get(node[2].casefold()) if table else None
            return 'f' if found and found[0] == 'f' else 'i'
        if kind == 'neg':
            return self.typeof(node[1])
        if kind == 'bin':
            return 'f' if 'f' in (self.typeof(node[2]), self.typeof(node[3])) else 'i'
        if kind == 'cmp':
            return 'i'
        if kind == 'call':
            fn = lookup(node[2])
            if fn.name in ('getsoundplaying', 'saydone', 'getjournalindex', 'menumode', 'cellchanged',
                           'scriptrunning'):
                return 'i'
            if fn.name in ('getsecondspassed', 'random', 'getdistance', 'getsquareroot'):
                return 'f'
            return 'f' if fn.ret == 'f' else 'i'
        raise CompileError('unknown expression ' + kind)

    # --- calls ---
    def call(self, node, value):
        _, ref, name, args, extra = node
        fn = lookup(name)
        self.calls.append(fn.name)
        if fn.name == 'getitemcount' and ref is not None and ref.casefold() == 'player' and args \
                and args[0][0] == 'str':
            # the player's inventory counts are game state the engine keeps (aw_state.c AW_ITEM)
            self.e.op('QUERY', QUERIES['ITEM_COUNT'], self.p.string(args[0][1].casefold()), pushes=1)
            self.flags |= SCRIPT_VOLATILE
            return 'i'
        if fn.name == 'positioncell':
            return self.position_cell(fn, ref, args)
        if fn.name in PLACE_FUNCTIONS:
            return self.place(fn, ref, args)
        if fn.name == 'drop':
            return self.drop(fn, ref, args)
        if fn.name in ('aifollowcell', 'aiescortcell'):
            return self.ai_cell(fn, ref, args)
        if fn.name == 'aifollow':
            self.follower(ref, args)
        if fn.name in HOST:
            return self.hostcall(fn, ref, args)
        if not fn.run:
            return self.notyet(fn, ref, args, value)
        n = fn.name
        s = lambda i: args[i][1] if i < len(args) and args[i][0] == 'str' else ''   # noqa: E731
        # OpenMW: DontSaveObject and Fall do nothing, Xbox reads 0 (miscextensions.cpp): no code, a constant
        if n in ('dontsaveobject', 'fall'):
            return None
        if n == 'xbox':
            return self.push_const(('int', 0))
        if n == 'getpccell':
            # the player's cell: no reference (OpenMW reads the player's), a table row, not VOLATILE: the engine
            # moves the state generation when the player's cell changes (aw_mwhost.c)
            self.e.op('GETPCCELL', self.p.pccell(s(0)), pushes=1)
            return 'i'
        if ref is not None and n not in ('additem', 'removeitem'):
            self.e.op('REF', self.p.object(ref))
        if n == 'getpos':
            axis = s(0).casefold()[:1]
            if axis not in ('x', 'y', 'z'):
                self.warnings.append('GetPos with no axis %r: reads 0 (OpenMW)' % s(0))
                return self.push_const(('float', 0.0))
            self.e.op('GETPOS', 'xyz'.index(axis), pushes=1); self.flags |= SCRIPT_VOLATILE
            return 'f'
        if n in ('getcurrentaipackage', 'getaipackagedone'):
            # rules from OpenMW apps/openmw/mwscript/aiextensions.cpp OpGetCurrentAIPackage and OpGetAiPackageDone;
            # not VOLATILE: the ambient tables move the state generation when a package starts or ends
            self.e.op('AIPACKAGE', 0 if n == 'getcurrentaipackage' else 1, pushes=1)
            return 'i'
        if n in ('getcommondisease', 'getblightdisease'):
            self.e.op('SPELL', SPELL_VERBS['common_disease' if n == 'getcommondisease' else 'blight_disease'], 0,
                      pushes=1)
            self.flags |= SCRIPT_ACTOR
            return 'i'
        # audio: rules from OpenMW apps/openmw/mwscript/soundextensions.cpp (OpPlaySound, OpPlaySoundVP,
        # OpPlaySound3D, OpPlaySoundVP3D, OpStopSound, OpGetSoundPlaying, OpSay, OpSayDone, OpStreamMusic); a sound
        # names a SOUN record, Say a voice file, StreamMusic a music file: each resolved here to the media pool file
        # (media.py), so the engine reads indexes only
        if n in ('playsound', 'playsound3d', 'playloopsound3d', 'stopsound', 'getsoundplaying'):
            index = self.p.sound(s(0), self.ident)
            op = {'playsound': 'PLAYSOUND', 'playsound3d': 'PLAYSOUND3D', 'playloopsound3d': 'PLAYLOOP3D',
                  'stopsound': 'STOPSOUND', 'getsoundplaying': 'SOUNDPLAYING'}[n]
            self.e.op(op, index, pushes=1 if op == 'SOUNDPLAYING' else 0)
            return 'i' if op == 'SOUNDPLAYING' else None
        if n in ('playsoundvp', 'playsound3dvp', 'playloopsound3dvp'):
            index = self.p.sound(s(0), self.ident)
            for a in args[1:3]:
                self.convert(self.expr(a), 'f')
            self.e.op({'playsoundvp': 'PLAYSOUNDVP', 'playsound3dvp': 'PLAYSOUND3DVP',
                       'playloopsound3dvp': 'PLAYLOOP3DVP'}[n], index, pops=2)
            return None
        if n in ('say', 'say3d'):
            self.e.op('SAY', self.p.voice(s(0), self.ident), self.p.string(s(1)))
            return None
        if n == 'saydone':
            self.e.op('SAYDONE', pushes=1); self.flags |= SCRIPT_VOLATILE
            return 'i'
        if n == 'streammusic':
            self.e.op('STREAMMUSIC', self.p.track(s(0), self.ident))
            return None
        if n in ('journal', 'setjournalindex'):
            self.convert(self.expr(args[1]), 'i')
            self.e.op('JOURNAL' if n == 'journal' else 'SETJ', self.p.topic(s(0)), pops=1)
            return None
        if n == 'getjournalindex':
            self.e.op('GETJ', self.p.topic(s(0)), pushes=1)
            return 'i'
        if n == 'getsecondspassed':
            self.e.op('SECONDS', pushes=1); self.flags |= SCRIPT_VOLATILE
            return 'f'
        if n == 'random':
            self.convert(self.expr(args[0]), 'i')
            self.e.op('RANDOM', pops=1, pushes=1); self.flags |= SCRIPT_VOLATILE
            return 'f'
        if n == 'menumode':
            self.e.op('MENUMODE', pushes=1); self.flags |= SCRIPT_VOLATILE
            return 'i'
        if n == 'cellchanged':
            # not VOLATILE (v0.0.54): CellChanged reads 1 only on the run after the object was attached or came into
            # range, and the interpreter runs a quiet script on exactly those frames (aw_mwvm.c AWI_CELLCHANGED);
            # the sound markers ("if CellChanged ... GetSoundPlaying ... PlayLoopSound") were most of every frame's
            # work and now run once, and again when their sound ends (the host wakes them: aw_mwhost.c)
            self.e.op('CELLCHANGED', pushes=1)
            return 'i'
        if n in ('startscript', 'stopscript', 'scriptrunning'):
            key = s(0).casefold()
            if key not in self.p.scripts.index:
                self.warnings.append('%s of an unknown script %r: not compiled' % (n, s(0)))
                if n == 'scriptrunning':
                    return self.push_const(('int', 0))
                return None
            index = self.p.scripts.index[key]
            if n == 'startscript':
                self.p.scripts.rows[index]['started'] = True
            op = {'startscript': 'STARTSCRIPT', 'stopscript': 'STOPSCRIPT', 'scriptrunning': 'SCRIPTRUNNING'}[n]
            self.e.op(op, index, pushes=1 if op == 'SCRIPTRUNNING' else 0)
            if op == 'SCRIPTRUNNING':
                self.flags |= SCRIPT_VOLATILE
            return 'i' if op == 'SCRIPTRUNNING' else None
        if n == 'getdistance':
            self.e.op('DISTANCE', self.p.object(s(0)), pushes=1); self.flags |= SCRIPT_VOLATILE
            return 'f'
        if n == 'getsquareroot':
            self.convert(self.expr(args[0]), 'f')
            self.e.op('SQRT')
            return 'f'
        if n in ('enable', 'disable', 'unlock'):
            self.e.op(n.upper())
            return None
        if n in ('getdisabled', 'getlocked'):
            self.e.op(n.upper(), pushes=1); self.flags |= SCRIPT_VOLATILE
            return 'i'
        if n == 'onactivate':
            # the object's use goes to this script from now on (the original's rule); read every frame
            self.e.op('ONACTIVATE', pushes=1); self.flags |= SCRIPT_VOLATILE | SCRIPT_ONACTIVATE
            return 'i'
        if n == 'activate':
            self.e.op('ACTIVATE')
            return None
        if n == 'messagebox':
            # the text, its numbers (each pushed as a number with a fraction; %d formats the whole part), the buttons
            numbers = args[1:1 + extra['nargs']]
            for a in numbers:
                self.convert(self.expr(a), 'f')
            buttons = [self.p.string(b) for b in extra['buttons']]
            if len(numbers) > 0x1F or len(buttons) > 0xFF:
                raise CompileError('messagebox with too many numbers or buttons')
            self.e.op('MESSAGEBOX', self.p.string(extra['format']), len(numbers), len(buttons), *buttons,
                      layout='HBB' + 'H' * len(buttons), pops=len(numbers))
            return None
        if n == 'getbuttonpressed':
            self.e.op('GETBUTTONPRESSED', pushes=1); self.flags |= SCRIPT_VOLATILE
            return 'i'
        if n == 'lock':
            # Lock [level]: without a number the lock takes the level it had (-1 to the engine)
            numbers = [a for a in args if a[0] != 'str']
            if numbers:
                self.convert(self.expr(numbers[0]), 'i')
            else:
                self.push_const(('int', -1))
            self.e.op('LOCK', pops=1)
            return None
        # --- the actor record (engine/aga/src/aw_actorstate.h; docs/ACTOR_STATE.md) ---
        if n in ACTOR_CALLS:
            verb, stat = ACTOR_CALLS[n]
            whole = stat in WHOLE_STATS and verb != VERBS['ratio']
            if verb in (VERBS['set'], VERBS['mod'], VERBS['modcurrent']):
                self.convert(self.expr(args[0] if args else ('int', 0)), 'i' if whole else 'f')
                self.e.op('ACTOR', verb, stat, pops=1)
                return None
            self.e.op('ACTOR', verb, stat, pushes=1)
            self.flags |= SCRIPT_ACTOR
            return 'i' if whole else 'f'
        if n in ('additem', 'removeitem', 'getitemcount'):
            item = self.p.item(s(0))
            if n == 'getitemcount':
                self.e.op('ITEM', 0, item, pushes=1)
                self.flags |= SCRIPT_ACTOR
                return 'i'
            self.convert(self.expr(args[1] if len(args) > 1 else ('int', 1)), 'i')
            # the reference after the count (CRIME-FINE-GOLD-NOT-TAKEN-62): a function call in the count ("Player->
            # RemoveItem Gold_001 GetPCCrimeLevel", the guards' fine) resets the target, so a reference set before it
            # made the speaker, not the player, give the gold
            if ref is not None:
                self.e.op('REF', self.p.object(ref))
            self.e.op('ITEM', 1 if n == 'additem' else 2, item, pops=1)
            return None
        if n in ('addspell', 'removespell', 'getspell'):
            spell = self.p.spell(s(0))
            if n == 'getspell':
                self.e.op('SPELL', 0, spell, pushes=1)
                self.flags |= SCRIPT_ACTOR
                return 'i'
            self.e.op('SPELL', 1 if n == 'addspell' else 2, spell)
            return None
        if n in ('startcombat', 'stopcombat'):
            self.e.op('COMBAT', 0 if n == 'startcombat' else 1, self.p.object(s(0)) if n == 'startcombat' else NONE)
            return None
        if n == 'aiwander':
            # range, duration, time and then up to 10 more, each a whole number (OpenMW OpAiWander truncates the
            # first three); the engine reads them as OpenMW does (aw_mwhost.c)
            numbers = [a for a in args if a[0] != 'str'][:13]
            while len(numbers) < 3:
                numbers.append(('int', 0))
            for a in numbers:
                self.convert(self.expr(a), 'i')
            self.e.op('AIWANDER', len(numbers) - 3, pops=len(numbers))
            return None
        if n == 'getdeadcount':
            row = self.p.actors.actor(s(0))
            self.e.op('DEADCOUNT', NONE if row is None else row, pushes=1)
            self.flags |= SCRIPT_ACTOR
            return 'i'
        raise CompileError('run function without code: ' + n)

    def hostcall(self, fn, ref, args):
        """A function the engine carries out through the import route (functions.HOST, v0.0.57): the NOTYET form,
        but the reference becomes a REF before it (the host gets the target as for every other call, not an id
        string) and the script is not marked NOTYET. A read wakes with the state generation (the host moves it when
        a script changes the standing), so it is not VOLATILE."""
        if fn.name == 'cast':
            # v0.0.57: on the player, the cures and the spells whose every effect is a Fortify, Drain, Damage or
            # Restore of an attribute, a skill, health, magicka or fatigue (SPELL-EFFECTS-57, the first slice: the
            # spell's SPFX row as the number); any other Cast stays "not yet"
            strs = [a[1].casefold() for a in args if a[0] == 'str']
            spell, who = (strs + ['', ''])[:2]
            if who != 'player':
                return self.notyet(fn, ref, args, None)
            if not any(c in spell for c in CURES):
                row = self.p.spell_effects(spell)
                if row is None:
                    return self.notyet(fn, ref, args, None)
                if ref is not None:
                    self.e.op('REF', self.p.object(ref))
                return self.notyet(fn, None, [('str', spell), ('str', who), ('int', row)], None, carried=True)
        if fn.name in ('gettarget', 'getstandingpc', 'getangle', 'getdetected', 'getlos', 'getlineofsight',
                       'onknockout', 'getcurrentweather', 'getpcsneaking', 'getweapondrawn', 'getpcinjail',
                       'hassoulgem', 'hitonme') or \
                (fn.name.startswith('getresist') and fn.name[3:] in RESISTS):
            # a fight starts without the state generation moving: the script asks every frame; so do the angles, the
            # detection, the line of sight, a knockdown and the weather (v0.0.62), as GetPos does
            self.flags |= SCRIPT_VOLATILE
        if fn.name == 'geteffect':
            # v0.0.57: the effect's number (0 none known) as the call's number; the engine reads the active effects
            name = args[0][1].casefold() if args and args[0][0] == 'str' else ''
            name = name[7:] if name.startswith('seffect') else name
            folded = [n.casefold() for n in EFFECT_NAMES]
            number = folded.index(name) if name in folded else -1
            if number < 0:
                self.warnings.append('GetEffect of an unknown effect %r: reads 0' % name)
                return self.push_const(('int', 0))
            if ref is not None:
                self.e.op('REF', self.p.object(ref))
            return self.notyet(fn, None, [('int', number)], None, carried=True)
        if fn.name == 'addtopic':
            # the topic's TOPC row as the number (the engine keeps one bit per row); a name no DIAL topic has does
            # nothing, as OpenMW logs and skips it
            name = args[0][1] if args and args[0][0] == 'str' else ''
            row = self.p.topic_rows().get(name.casefold())
            if row is None:
                self.warnings.append('AddTopic of an unknown topic %r: nothing' % name)
                return None
            return self.notyet(fn, None, [('int', row)], None, carried=True)
        if fn.name in ('changeweather', 'modregion'):
            # v0.0.62 (MWSCRIPT-COMPLETE-LANDMARK): the region's index in the region catalogue (sorted Morrowind.esm
            # region ids, as the weather table orders them) as the first number, then the weather or the chances (at
            # most ten; OpenMW reads them in the weathers' order). A region the image has not (Mournhold, Solstheim):
            # no code, as OpenMW's weather manager finds no such region and does nothing
            name = next((a[1] for a in args if a[0] == 'str'), '')
            regions = sorted(getattr(self.p.data, 'base_regions', ()) or ())
            if name.casefold() not in regions:
                self.warnings.append('%s of %r, a region the image has not: nothing' % (fn.name, name))
                return None
            nums = [a for a in args if a[0] != 'str'][:1 if fn.name == 'changeweather' else 10]
            if fn.name == 'changeweather' and not nums:
                return self.notyet(fn, ref, args, None)
            return self.notyet(fn, None, [('int', regions.index(name.casefold()))] + nums, None, carried=True)
        if ref is not None:
            self.e.op('REF', self.p.object(ref))
        return self.notyet(fn, None, args, None, carried=True)

    def position_cell(self, fn, ref, args):
        """PositionCell (OpenMW transformationextensions.cpp OpPositionCell). The player: a PMOV row (PLAYERMOVE), or
        "not yet" when it cannot be worked out here (a number not constant, a room this build lacks). Anything else:
        the host's call (v0.0.62, MWSCRIPT-POSITIONCELL-ACTORS-62) with the numbers x, y, z, yaw, kind, room number
        (actor_move) and the cell's name; the room's possible visitors noted (VISI). A cell the game has not: no
        code, as OpenMW does nothing for anything but the player."""
        from .opcodes import PLAYERMOVE_KINDS
        if ref is not None and ref.casefold() == 'player':
            move = self.p.player_move(args)
            if move is None:
                return self.notyet(fn, ref, args, None)
            self.e.op('PLAYERMOVE', move)
            return None
        move = self.p.actor_move(args)
        if move is None:
            return self.notyet(fn, ref, args, None)
        cell = [a[1] for a in args if a[0] == 'str'][0]
        if move == 'unknown':
            self.warnings.append('PositionCell into %r, a cell the game has not: nothing (OpenMW)' % cell)
            return None
        kind, number, x, y, z, yaw = move
        if kind == PLAYERMOVE_KINDS['room']:
            self.p.visitor(number, ref, self.ident)
        if ref is not None:
            self.e.op('REF', self.p.object(ref))
        return self.notyet(fn, None, [('float', x), ('float', y), ('float', z), ('float', yaw), ('str', cell),
                                      ('int', kind), ('int', number)], None, carried=True)

    def place(self, fn, ref, args):
        """PlaceAtPC, PlaceAtMe, PlaceItem, PlaceItemCell (v0.0.62, MWSCRIPT-PLACE-OBJECTS-62; OpenMW
        transformationextensions.cpp OpPlaceAt, OpPlaceItem, OpPlaceItemCell). An object the engine can make
        (Program.placed) goes to the host with its PLAC row as the last number: PlaceAtPC and PlaceAtMe with count,
        distance (game units) and direction (0 front, 1 back, 2 left, 3 right), PlaceAtMe on REF's object or the
        script's own; PlaceItem with x, y, z (game units, the player's cell) and the rotation in degrees; PlaceItemCell
        with the cell worked out here as PositionCell's (x, y, z in a room map's own units for an actor, game units for
        an item; Quake's yaw; the kind and the room's number). Anything else stays "not yet"; a PlaceItemCell into a
        cell the game has not is no code (OpenMW reports it and does nothing)."""
        from .opcodes import PLAYERMOVE_KINDS
        strs = [a[1] for a in args if a[0] == 'str']
        nums = [a for a in args if a[0] != 'str']
        if not strs:
            return self.notyet(fn, ref, args, None)
        row = self.p.placed(strs[0])
        if row is None:
            return self.notyet(fn, ref, args, None)
        ident = ('str', strs[0])
        n = fn.name
        if n in ('placeatpc', 'placeatme'):
            nums = (nums + [('int', 1), ('float', 0.0), ('int', 0)][len(nums):])[:3]
            if n == 'placeatme' and ref is not None:
                self.e.op('REF', self.p.object(ref))
            return self.notyet(fn, None, [ident] + nums + [('int', row)], None, carried=True)
        if n == 'placeitem':
            nums = (nums + [('float', 0.0)] * 4)[:4]
            return self.notyet(fn, None, [ident] + nums + [('int', row)], None, carried=True)
        # placeitemcell: the cell at build time
        if len(strs) < 2 or len(nums) < 4 or not all(_const(fold(a)) for a in nums[:4]):
            return self.notyet(fn, ref, args, None)
        cell = strs[1]
        x, y, z, rot = (float(fold(a)[1]) for a in nums[:4])
        yaw = round((-rot) % 360.0, 5) % 360.0
        actor = self.p.place_rows()[row]['kind'] != PLACE_KINDS['item']    # an actor or an object: the room's units
        key = cell.casefold()
        if key in self.p.data.interior_numbers:
            number = self.p.data.interior_numbers[key]
            at = (x, y, z)
            if actor:
                room = (self.p.rooms or {}).get(key) or {}
                offset = room.get('offset') or (0.0, 0.0, 0.0)
                at = tuple(round((v - offset[k]) * 0.25, 5) for k, v in enumerate((x, y, z)))
            kind = PLAYERMOVE_KINDS['room']
        elif key in self.p.exterior_names():
            number, at, kind = 0, (x, y, z), PLAYERMOVE_KINDS['outdoors']
        else:
            self.warnings.append('PlaceItemCell into %r, a cell the game has not: nothing (OpenMW)' % cell)
            return None
        return self.notyet(fn, None, [ident, ('str', cell)] + [('float', v) for v in at] +
                           [('float', yaw), ('int', kind), ('int', number), ('int', row)], None, carried=True)

    def drop(self, fn, ref, args):
        """Drop ITEM COUNT (v0.0.62, MWSCRIPT-GAP-FUNCTIONS-62; OpenMW 0.51 miscextensions.cpp OpDrop: the actor's
        COUNT of the item leave its inventory and lie on the ground at its feet). An item the engine can make in the
        world (Program.placed: a carried item's PLAC row) and the inventory knows (its AITM row) goes to the host
        with the numbers count, AITM row, PLAC row; anything else stays "not yet"."""
        strs = [a[1] for a in args if a[0] == 'str']
        nums = [a for a in args if a[0] != 'str']
        if not strs:
            return self.notyet(fn, ref, args, None)
        row = self.p.placed(strs[0])
        item = self.p.item(strs[0])
        if row is None or item is None or self.p.place_rows()[row]['kind'] != PLACE_KINDS['item']:
            return self.notyet(fn, ref, args, None)
        if ref is not None:
            self.e.op('REF', self.p.object(ref))
        count = (nums + [('int', 1)])[0]
        return self.notyet(fn, None, [('str', strs[0]), count, ('int', item), ('int', row)], None, carried=True)

    def follower(self, ref, args):
        """An AIFollow / AIFollowCell whose target is the player: the follower crosses doors with the player (OpenMW
        actionteleport.cpp getFollowers), so it may stand in any room; a VISI row with the room VISI_ANY (the actor,
        its home room's map) lets a room it was left in, or a saved game, spawn it there again."""
        target = next((a[1] for a in args if a[0] == 'str'), '')
        if target.casefold() == 'player':
            self.p.visitor(VISI_ANY, ref, self.ident)

    def ai_cell(self, fn, ref, args):
        """AIFollowCell / AIEscortCell (v0.0.62, MWSCRIPT-POSITIONCELL-ACTORS-62; rules from OpenMW 0.51
        aiextensions.cpp OpAiFollowCell / OpAiEscortCell, aifollow.cpp, aiescort.cpp). The destination is worked out
        here once, as PositionCell's (actor_move): an interior cell by its name (its stable number, the point in that
        room map's own units), else the outdoors or a cell the game has not (the number 0: OpenMW's follow is then
        never done by its position, an escort walks outdoors only). An AIEscortCell into a cell the game has not
        compiles to nothing, as OpenMW starts no package then. The host gets the numbers duration, x, y, z, kind, the
        room's number and the strings target, cell; the reset argument is not passed (its value does not matter,
        OpenMW). Numbers that are not constants stay "not yet"."""
        from .opcodes import PLAYERMOVE_KINDS
        strs = [a[1] for a in args if a[0] == 'str']
        numbers = [fold(a) for a in args if a[0] != 'str'][:4]
        if len(strs) < 2 or len(numbers) < 4 or not all(_const(n) for n in numbers):
            return self.notyet(fn, ref, args, None)
        target, cell = strs[0], strs[1]
        duration, x, y, z = (float(n[1]) for n in numbers)
        move = self.p.actor_move([('float', x), ('float', y), ('float', z), ('float', 0.0), ('str', cell)])
        if move == 'unknown' or move is None:
            if fn.name == 'aiescortcell':
                self.warnings.append('AIEscortCell into %r, a cell the game has not: nothing (OpenMW)' % cell)
                return None
            kind, number, at = PLAYERMOVE_KINDS['outdoors'], 0, (x, y, z)
        else:
            kind, number = move[0], move[1]
            at = move[2:5] if kind == PLAYERMOVE_KINDS['room'] else (x, y, z)
            if kind != PLAYERMOVE_KINDS['room']:
                number = 0
        if fn.name == 'aifollowcell':
            self.follower(ref, args)
        if ref is not None:
            self.e.op('REF', self.p.object(ref))
        return self.notyet(fn, None, [('str', target), ('str', cell), ('float', duration), ('float', at[0]),
                                      ('float', at[1]), ('float', at[2]), ('int', kind), ('int', number)], None,
                           carried=True)

    def notyet(self, fn, ref, args, value, carried=False):
        """NOTYET: the numeric arguments pushed, the strings as indexes; logged once by the engine."""
        if not carried:
            self.flags |= SCRIPT_NOTYET
            self.notyet_names.append(fn.name)
        numeric = 0
        strings = []
        if ref is not None:
            strings.append(self.p.string(ref))
        letters = fn.args.replace('/', '')
        for i, a in enumerate(args):
            if a[0] == 'str':
                strings.append(self.p.string(a[1]))
            else:
                kind = self.expr(a)
                if carried:
                    # the host reads each number as the function declares it (a fraction or a whole number)
                    self.convert(kind, 'f' if i < len(letters) and letters[i] == 'f' else 'i')
                numeric += 1
        returns = fn.ret != '-'
        if numeric > 0x1F or len(strings) > 0xFF:
            raise CompileError('%s with too many arguments' % fn.name)
        flags = numeric | (0x80 if returns else 0) | (0x40 if fn.ret == 'f' else 0) | (0x20 if ref is not None else 0)
        layout = 'HHBB' + 'H' * len(strings)
        self.e.op('NOTYET', fn.number, self.p.string(fn.name), flags, len(strings), *strings, layout=layout,
                  pops=numeric, pushes=1 if returns else 0)
        if returns:
            # NOTYET reads 0 (a constant until the engine carries the function out, by its number through the host's
            # call() or with its own opcode): it does not make the script VOLATILE
            return 'f' if fn.ret == 'f' else 'i'
        return None

    def member(self, owner, var):
        table = self.p.locals_of(owner)
        if table is None or var.casefold() not in table:
            self.warnings.append('member %s.%s not found: reads 0, writes are dropped' % (owner, var))
            return None
        letter, slot = table[var.casefold()]
        return self.p.object(owner), slot, letter

    # --- statements ---
    def block(self, stmts):
        for st in stmts:
            self.statement(st)

    def statement(self, st):
        kind = st[0]
        if kind == 'set':
            _, line, target, value = st
            if target[0] == 'local':
                letter, slot = self.locals[target[1]]
                self.convert(self.expr(value), 'f' if letter == 'f' else 'i')
                self.e.op('SETLS' if letter == 's' else 'SETL', slot, pops=1)
            elif target[0] == 'global':
                index = self.p.globals.index[target[1]]
                letter = self.p.globals.rows[index]['type']
                self.convert(self.expr(value), 'f' if letter == 'f' else 'i')
                self.e.op('SETGS' if letter == 's' else 'SETG', index, pops=1)
            else:
                found = self.member(target[1], target[2])
                if found is None:
                    return
                obj, slot, letter = found
                self.convert(self.expr(value), 'f' if letter == 'f' else 'i')
                self.e.op('SETMS' if letter == 's' else 'SETM', obj, slot, pops=1)
            return
        if kind == 'do':
            t = self.call(st[2], value=False)
            if t is not None:
                self.e.op('POP', pops=1)
            return
        if kind == 'return':
            self.e.op('RET')
            return
        if kind == 'if':
            _, line, branches, otherwise = st
            live = []
            for cond, body in branches:
                c = fold(cond)
                if _const(c):
                    if c[1]:
                        live.append((None, body))   # always true: what follows is dead code
                        break
                    continue                        # always false: dropped
                live.append((c, body))
            tail = live and live[-1][0] is None
            ends = []
            for i, (c, body) in enumerate(live):
                if c is None:
                    self.block(body)
                    break
                skip = self.branch_false(c)
                self.block(body)
                # no jump over nothing: the last test with no else after it falls through
                if i < len(live) - 1 or (otherwise and not tail):
                    ends.append(self.e.jump('JMP'))
                self.e.patch(skip)
            if not tail:
                self.block(otherwise)
            for at in ends:
                self.e.patch(at)
            return
        if kind == 'while':
            _, line, cond, body = st
            c = fold(cond)
            if _const(c) and not c[1]:
                return
            top = len(self.e.code)
            out = self.branch_false(c)
            self.block(body)
            back = self.e.jump('JMP')
            self.e.patch(back, top)
            self.e.patch(out)
            self.loops += 1
            return
        raise CompileError('unknown statement ' + kind)

    def condition(self, node):
        t = self.expr(node)
        if t == 'f':
            self.e.op('PUSHB', 0, pushes=1); self.e.op('I2F'); self.e.op('NEF', pops=2, pushes=1)

    def branch_false(self, node):
        """The test of an if or while and its jump past the body; returns the jump's patch position. With SQUEEZE, a
        whole number tested against a constant of -128..127 is one opcode (JNEB for ==, else JCMPB) instead of
        PUSHB, the comparison and JZ (docs/MWSCRIPT_BYTECODE.md "What it squeezes")."""
        if SQUEEZE and node[0] == 'cmp' and node[3][0] == 'int' and -128 <= node[3][1] <= 127 \
                and self.typeof(node[2]) == 'i':
            self.expr(node[2])
            if node[1] == '==':
                self.e.op('JNEB', node[3][1], 0, pops=1)
            else:
                self.e.op('JCMPB', CMP_CODES[node[1]], node[3][1], 0, pops=1)
            return len(self.e.code) - 2
        self.condition(node)
        return self.e.jump('JZ')

    def compile(self):
        self.block(self.tree[2])
        self.e.op('END')
        return bytes(self.e.code)
