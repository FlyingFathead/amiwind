# SPDX-License-Identifier: GPL-3.0-only
"""The conversation greeting an NPC opens a talk with, from the original dialogue records.

Rule (OpenMW 0.51 apps/openmw/mwdialogue/dialoguemanagerimp.cpp, DialogueManager::startDialogue):
the Dialogue records of type Greeting are scanned in the store's order (the store sorts them by
ID, apps/openmw/mwworld/store.cpp Store<ESM::Dialogue>::setUp: "Greeting 0" .. "Greeting 9");
in each, the first INFO in record order that passes the filter is the greeting (Filter::search
without the Info Refusal fallback). The filter (apps/openmw/mwdialogue/filter.cpp) tests, in
this order: the speaker (testActor: actor ID, race, class, faction and its rank, sex), the
player (testPlayer: player faction and rank, the player's cell), the conditions (SCVR,
testSelectStructs) and the disposition (testDisposition: disposition >= the INFO's).

This is an independent implementation evaluated at build time against a stated start-of-game
state (FIXTURE below). A condition the build cannot know (the player character's own race,
sex, attributes, skills, clothing value, the weather, the speaker's awareness...) is UNKNOWN:
the INFO is passed over as if it failed, and the result says it was not fully determined and
by which INFO, so nothing is guessed silently.
"""
import struct

from .esm import first, string, text

# Function numbers of the SCVR '1' conditions: the order of ESM::DialogueCondition::Function
# (OpenMW components/esm3/dialoguecondition.hpp), 0 .. 73.
FUNCTIONS = ("FacReactionLowest FacReactionHighest RankRequirement Reputation Health_Percent PcReputation "
             "PcLevel PcHealthPercent PcMagicka PcFatigue PcStrength PcBlock PcArmorer PcMediumArmor "
             "PcHeavyArmor PcBluntWeapon PcLongBlade PcAxe PcSpear PcAthletics PcEnchant PcDestruction "
             "PcAlteration PcIllusion PcConjuration PcMysticism PcRestoration PcAlchemy PcUnarmored "
             "PcSecurity PcSneak PcAcrobatics PcLightArmor PcShortBlade PcMarksman PcMercantile "
             "PcSpeechcraft PcHandToHand PcGender PcExpelled PcCommonDisease PcBlightDisease "
             "PcClothingModifier PcCrimeLevel SameSex SameRace SameFaction FactionRankDifference Detected "
             "Alarmed Choice PcIntelligence PcWillpower PcAgility PcSpeed PcEndurance PcPersonality PcLuck "
             "PcCorprus Weather PcVampire Level Attacked TalkedToPc PcHealth CreatureTarget FriendHit Fight "
             "Hello Alarm Flee ShouldAttack Werewolf PcWerewolfKills").split()
UNKNOWN = None
RUNTIME = 'runtime'      # Context.static: decided while the game runs, not at build time

# The start-of-game state the build evaluates against (a new character who has not yet met the
# speaker): no faction, level 1, no bounty, reputation 0, no disease, vampirism, corprus or
# werewolf kills, full health, every journal at 0 and nobody dead; globals hold the values their
# GLOB records give; an actor's script locals start at 0 (OpenMW testFunctionLocal reads 0 from
# empty locals). The disposition fixture is the one the voice lines already use (50).
FIXTURE = {'PcLevel': 1, 'PcCrimeLevel': 0, 'PcReputation': 0, 'PcHealthPercent': 100,
           'Health_Percent': 100, 'PcExpelled': 0, 'PcCommonDisease': 0, 'PcBlightDisease': 0,
           'PcCorprus': 0, 'PcVampire': 0, 'PcWerewolfKills': 0, 'Werewolf': 0, 'SameFaction': 0,
           'FacReactionLowest': 0, 'FacReactionHighest': 0, 'Attacked': 0, 'Alarmed': 0,
           'TalkedToPc': 0, 'FriendHit': 0, 'CreatureTarget': 0,
           # awarenessCheck (OpenMW mechanicsmanagerimp.cpp): a player who is not sneaking and has no
           # chameleon or invisibility is always detected (target = -observer term <= 0)
           'Detected': 1}
DISPOSITION = 50
# Player-dependent or moment-dependent: not known when the game is built.
NOT_KNOWN = {'PcGender', 'SameSex', 'SameRace', 'PcMagicka', 'PcFatigue',
             'PcHealth', 'Detected', 'ShouldAttack', 'RankRequirement', 'Weather'} | {
    f for f in FUNCTIONS if f.startswith('Pc') and f not in FIXTURE and f not in (
        'PcGender', 'PcClothingModifier')}


def starting_clothing_value(kinds):
    """PcClothingModifier of a new character: the summed value of the clothing and armour in the
    'player' NPC record's inventory (the starting shirt, pants and shoes, worn from the start;
    filter.cpp sums the value of every worn slot except the hands)."""
    total = 0
    for tag, data in kinds['NPC_'].get('player', []):
        if tag != 'NPCO' or len(data) != 36:
            continue
        item = string(data[4:], 'NPCO', errors='replace').casefold()
        if item in kinds.get('CLOT', {}):
            raw = first(kinds['CLOT'][item], 'CTDT')
            total += struct.unpack_from('<h', raw, 8)[0] if len(raw) >= 10 else 0
        elif item in kinds.get('ARMO', {}):
            raw = first(kinds['ARMO'][item], 'AODT')
            total += struct.unpack_from('<i', raw, 8)[0] if len(raw) >= 12 else 0
    return total


def _compare(value, op, against):
    return {'0': value == against, '1': value != against, '2': value > against, '3': value >= against,
            '4': value < against, '5': value <= against}[op]


def _int(fields, tag, offset, fmt):
    raw = first(fields, tag)
    return struct.unpack_from(fmt, raw, offset)[0] if len(raw) >= offset + struct.calcsize(fmt) else 0


def speaker(kinds, actor_id):
    """What the filter reads of an NPC record: id, race, class, faction, its rank, sex, level,
    reputation, behaviour settings and script."""
    npc = kinds['NPC_'][actor_id.casefold()]
    stats = first(npc, 'NPDT')
    if len(stats) == 52:                      # level, attributes, skills, ..., disposition, reputation, rank
        level, reputation, rank = struct.unpack_from('<h', stats)[0], stats[45], stats[46]
    elif len(stats) == 12:                    # auto-calculated: level, disposition, reputation, rank
        level, reputation, rank = struct.unpack_from('<h', stats)[0], stats[3], stats[4]
    else:
        raise ValueError('Malformed NPC NPDT for ' + actor_id)
    ai = first(npc, 'AIDT')
    hello, fight, flee, alarm = (struct.unpack_from('<HBBB', ai) if len(ai) >= 5 else (0, 0, 0, 0))
    return {'id': actor_id.casefold(), 'race': text(npc, 'RNAM').casefold(), 'class': text(npc, 'CNAM').casefold(),
            'faction': text(npc, 'ANAM').casefold(), 'rank': rank, 'level': level, 'reputation': reputation,
            'female': bool(struct.unpack('<I', first(npc, 'FLAG'))[0] & 1),
            'ai': {'Hello': hello, 'Fight': fight, 'Flee': flee, 'Alarm': alarm},
            'script': text(npc, 'SCRI').casefold()}


def script_locals(source):
    """{name: type} of the local variables a script declares (short / long / float lines)."""
    names = {}
    for line in (source or '').splitlines():
        words = line.split(';', 1)[0].replace(',', ' ').split()
        if len(words) >= 2 and words[0].casefold() in ('short', 'long', 'float'):
            names[words[1].casefold()] = words[0].casefold()[0]
    return names


def globals_of(kinds):
    """{name: value} of the GLOB records (OpenMW keeps every global as a float)."""
    out = {}
    for name, fields in kinds.get('GLOB', {}).items():
        raw = first(fields, 'FLTV')
        out[name] = struct.unpack('<f', raw)[0] if len(raw) == 4 else 0.0
    return out


def conditions(fields):
    """[(function, variable, op, value)] of an INFO's SCVR conditions (with their INTV/FLTV value)."""
    out, pending = [], None
    for tag, data in fields:
        if tag == 'SCVR':
            rule = string(data, 'SCVR', errors='replace')
            if len(rule) < 5 or rule[4] not in '012345':
                pending = None; out.append(('Invalid', rule, '0', 0)); continue
            kind = rule[1]
            if kind == '1':
                code = int(rule[2:4]) if rule[2:4].isdigit() else -1
                function = FUNCTIONS[code] if 0 <= code < len(FUNCTIONS) else 'Invalid'
            else:
                function = {'2': 'Global', '3': 'Local', '4': 'Journal', '5': 'Item', '6': 'Dead', '7': 'NotId',
                            '8': 'NotFaction', '9': 'NotClass', 'A': 'NotRace', 'B': 'NotCell',
                            'C': 'NotLocal'}.get(kind, 'Invalid')
            pending = [function, rule[5:].casefold(), rule[4], None]
            out.append(pending)
        elif tag in ('INTV', 'FLTV') and pending is not None and pending[3] is None and len(data) == 4:
            pending[3] = struct.unpack('<i' if tag == 'INTV' else '<f', data)[0]
    return [(f, v, op, 0 if value is None else value) for f, v, op, value in out]


_PARSED = {}


def _parsed(fields):
    """What compile() reads of an INFO, parsed once per INFO list object (a build compiles every INFO for
    thousands of speakers): (disposition, rank, gender, pcrank, actor, race, class, faction, player faction,
    cell, conditions), or None for a malformed DATA. The list itself is kept with its entry, so an id is
    never reused while the entry exists."""
    hit = _PARSED.get(id(fields))
    if hit is not None and hit[0] is fields:
        return hit[1]
    raw = first(fields, 'DATA')
    if len(raw) != 12:
        value = None
    else:
        _, disposition, rank, gender, pcrank, _ = struct.unpack('<iibbbb', raw)
        value = (disposition, rank, gender, pcrank) + tuple(
            text(fields, tag).casefold() for tag in ('ONAM', 'RNAM', 'CNAM', 'FNAM', 'DNAM', 'ANAM')) + (
            tuple(conditions(fields)),)
    _PARSED[id(fields)] = (fields, value)
    return value


class Context:
    """The build-time game state one speaker is evaluated in (FIXTURE + the data's own values)."""

    def __init__(self, kinds, actor_id, cell=None, disposition=DISPOSITION, talked_to=False):
        self.npc = speaker(kinds, actor_id)
        self.globals = kinds.get('_globals')
        if self.globals is None:
            self.globals = kinds['_globals'] = globals_of(kinds)
        source = text(kinds.get('SCPT', {}).get(self.npc['script'], []), 'SCTX') if self.npc['script'] else ''
        self.locals = script_locals(source) if self.npc['script'] else None
        self.cell = cell.casefold() if cell else None
        self.disposition = disposition
        self.talked_to = talked_to
        if '_clothing' not in kinds:
            kinds['_clothing'] = starting_clothing_value(kinds)
        self.clothing = kinds['_clothing']

    def local(self, name, op, value):
        # OpenMW testFunctionLocal: no script or no such variable = false; empty locals read as 0.
        if self.locals is None or name not in self.locals:
            return False
        return _compare(0, op, value)

    def condition(self, function, variable, op, value):
        """True, False or UNKNOWN for one condition."""
        npc = self.npc
        if function == 'Invalid':
            return False                                   # OpenMW drops invalid rules at load; be strict
        if function == 'Global':
            if variable == 'random100':
                return UNKNOWN                             # rolled every frame by the Main script
            if variable not in self.globals:
                return True                                # filter.cpp: a missing global is ignored
            return _compare(self.globals[variable], op, value)
        if function == 'Local':
            return self.local(variable, op, value)
        if function == 'NotLocal':
            return not self.local(variable, op, value)
        if function in ('Journal', 'Dead'):
            return _compare(0, op, value)
        if function == 'Item':
            return UNKNOWN if variable == 'gold_001' else _compare(0, op, value)
        if function == 'NotId':
            return npc['id'] != variable
        if function == 'NotFaction':
            return npc['faction'] != variable
        if function == 'NotClass':
            return npc['class'] != variable
        if function == 'NotRace':
            return npc['race'] != variable
        if function == 'NotCell':
            return UNKNOWN if self.cell is None else not self.cell.startswith(variable)
        if function == 'Choice':
            return False                                   # filter.cpp: no choice open at the greeting
        if function == 'TalkedToPc':
            return _compare(int(self.talked_to), op, value)
        if function == 'PcClothingModifier':
            return _compare(self.clothing, op, value)
        if function in FIXTURE:
            return _compare(FIXTURE[function], op, value)
        if function == 'Level':
            return _compare(npc['level'], op, value)
        if function == 'Reputation':
            return _compare(npc['reputation'], op, value)
        if function in npc['ai']:
            return _compare(npc['ai'][function], op, value)
        if function == 'FactionRankDifference':
            # the player holds no rank (-1) in the speaker's faction; no faction = 0
            return _compare(-1 - npc['rank'] if npc['faction'] else 0, op, value)
        return UNKNOWN                                     # NOT_KNOWN and anything else

    def static(self, function, variable, op, value):
        """True or False for a condition that only reads the speaker's record (its id, race, class, faction,
        level, reputation, Hello/Fight/Flee/Alarm settings, the locals its script declares) or is fixed (Choice, a missing global);
        RUNTIME for one whose value can change while the game runs (globals, journal, items, the dead, the
        player, the speaker's health, disposition, locals' values, the cell when not known)."""
        npc = self.npc
        if function == 'Invalid':
            return False                                   # OpenMW drops invalid rules at load; be strict
        if function == 'Global':
            if variable != 'random100' and variable not in self.globals:
                return True                                # filter.cpp: a missing global is ignored
            return RUNTIME
        if function in ('Local', 'NotLocal'):
            # OpenMW testFunctionLocal: no script or no such variable = false (NotLocal: true)
            if self.locals is None or variable not in self.locals:
                return function == 'NotLocal'
            return RUNTIME
        if function == 'NotId':
            return npc['id'] != variable
        if function == 'NotFaction':
            return npc['faction'] != variable
        if function == 'NotClass':
            return npc['class'] != variable
        if function == 'NotRace':
            return npc['race'] != variable
        if function == 'NotCell':
            return RUNTIME if self.cell is None else not self.cell.startswith(variable)
        if function == 'Choice':
            return False                                   # filter.cpp: no choice open at the greeting
        if function == 'Level':
            return _compare(npc['level'], op, value)
        if function == 'Reputation':
            return _compare(npc['reputation'], op, value)
        if function in npc['ai']:
            return _compare(npc['ai'][function], op, value)
        return RUNTIME

    def compile(self, fields):
        """One INFO split into what the build decides and what the game decides (OpenMW's order of tests:
        testActor, testPlayer, testSelectStructs, testDisposition): None when a test that only reads the
        speaker's record fails (the INFO can never be said by this speaker); otherwise the list of conditions
        left for run time, each (function, variable, op, value) as conditions() gives them, plus
        ('PcFaction', faction, '3', rank) for the player's faction test (faction '': the speaker's own),
        ('Cell', name, '0', 1) for the
        cell test when the cell is not known, and ('Disposition', '', '3', value) when the INFO needs a
        disposition above 0. An empty list: the INFO always passes for this speaker."""
        parsed = _parsed(fields)
        if parsed is None:
            return None
        disposition, rank, gender, pcrank, actor, race, cls, faction, pc_faction, cell, rules = parsed
        npc = self.npc
        # testActor
        if actor and actor != npc['id']:
            return None
        if race and race != npc['race']:
            return None
        if cls and cls != npc['class']:
            return None
        if faction == 'ffff':                              # "no faction" marker (ESM::DialInfo mFactionLess)
            if npc['faction']:
                return None
        elif faction:
            if faction != npc['faction'] or npc['rank'] < rank:
                return None
        elif rank != -1 and npc['rank'] < rank:
            return None
        if gender == (0 if npc['female'] else 1):         # 0 male-only, 1 female-only, -1 either
            return None
        runtime = []
        # testPlayer: the player's faction and rank (the speaker's faction when only a rank is given)
        if pc_faction or pcrank != -1:
            if not pc_faction and not npc['faction']:
                return None                                # no faction to be ranked in: never
            runtime.append(('PcFaction', pc_faction, '3', pcrank))   # '': the speaker's faction
        if cell:
            if self.cell is None:
                runtime.append(('Cell', cell, '0', 1))
            elif not self.cell.startswith(cell):
                return None
        # testSelectStructs
        for condition in rules:
            result = self.static(*condition)
            if result is False:
                return None
            if result is RUNTIME:
                runtime.append(condition)
        # testDisposition (0 always passes)
        if disposition > 0:
            runtime.append(('Disposition', '', '3', disposition))
        return runtime

    def evaluate(self, function, variable, op, value):
        """True, False or UNKNOWN for one run-time condition of compile() in this context (the build-time
        fixture: a new character with no faction, the start-of-game values)."""
        if function == 'PcFaction':
            return False                                   # the new character belongs to no faction
        if function == 'Cell':
            return UNKNOWN
        if function == 'Disposition':
            return self.disposition >= value
        return self.condition(function, variable, op, value)

    def info(self, fields):
        """True, False or UNKNOWN for one INFO, in OpenMW's order of tests (compile(), then its run-time
        conditions evaluated against the fixture)."""
        runtime = self.compile(fields)
        if runtime is None:
            return False
        unknown = False
        for condition in runtime:
            result = self.evaluate(*condition)
            if result is False:
                return False
            if result is UNKNOWN:
                unknown = True
        return UNKNOWN if unknown else True


def greeting_topics(topics, types=None):
    """The Greeting dialogue topics in OpenMW's store order (sorted by ID)."""
    names = [t for t in topics if (types.get(t) == 2 if types else t.startswith('greeting '))]
    return sorted(names)


def conversation_greeting(kinds, topics, actor_id, cell=None, disposition=DISPOSITION, talked_to=False):
    """The INFO an NPC opens a conversation with: {'topic','info','text','voice','determined','unknown_before'}
    or None when no Greeting INFO matches. UNKNOWN INFOs are passed over; every one passed over before
    the pick is listed in unknown_before (the pick is then not fully determined)."""
    context = Context(kinds, actor_id, cell, disposition, talked_to)
    passed = []
    for topic in greeting_topics(topics, kinds.get('DIAL')):
        for fields in topics[topic]:
            result = context.info(fields)
            if result is True:
                return {'topic': topic, 'info': text(fields, 'INAM'), 'text': text(fields, 'NAME'),
                        'voice': text(fields, 'SNAM'), 'determined': not passed, 'unknown_before': passed}
            if result is UNKNOWN:
                passed.append(topic + ':' + text(fields, 'INAM'))
    return None


# Text defines (OpenMW components/interpreter/defines.cpp, dialogue column; matched without case):
# the speaker's are filled in at build time, the player's are left for the engine, which expands
# exactly %PCName, %PCRace and %PCClass (aw_reader.c AW_ExpandDialogue).
PLAYER_DEFINES = {'pcname': '%PCName', 'pcrace': '%PCRace', 'pcclass': '%PCClass'}
SPEAKER_DEFINES = ('name', 'class', 'race', 'faction', 'rank', 'cell')


def _display(kinds, tag, identifier):
    return text(kinds.get(tag, {}).get(identifier.casefold(), []), 'FNAM') if identifier else ''


def _rank_name(kinds, faction, rank):
    names = [string(data, 'RNAM', errors='replace') for tag, data in kinds.get('FACT', {}).get(faction, [])
             if tag == 'RNAM']
    return names[rank] if 0 <= rank < len(names) else ''


def fill_defines(kinds, actor_id, line, cell=None):
    """The greeting text with the speaker's defines filled in and the player's in the engine's
    spelling; None when it holds a define this cannot fill (it is then not used)."""
    npc = speaker(kinds, actor_id)
    values = {'name': text(kinds['NPC_'][npc['id']], 'FNAM'), 'class': _display(kinds, 'CLAS', npc['class']),
              'race': _display(kinds, 'RACE', npc['race']), 'faction': _display(kinds, 'FACT', npc['faction']),
              'rank': _rank_name(kinds, npc['faction'], npc['rank']), 'cell': cell or ''}
    out, i = [], 0
    while i < len(line):
        if line[i] != '%':
            out.append(line[i]); i += 1; continue
        rest = line[i + 1:].casefold()
        # longest name first, as defines.cpp sorts them (pcname before name)
        key = next((k for k in sorted(list(PLAYER_DEFINES) + list(SPEAKER_DEFINES), key=len, reverse=True)
                    if rest.startswith(k)), None)
        if key is None:
            return None
        if key in PLAYER_DEFINES:
            out.append(PLAYER_DEFINES[key])
        else:
            if not values[key]:
                return None
            out.append(values[key])
        i += 1 + len(key)
    return ''.join(out)


def talk_greeting(kinds, topics, actor_id, cell=None):
    """The entity fields for a manual talk: {'first': text, 'again': text or '', 'record': {...}}.
    first = the greeting of a first meeting (TalkedToPc 0), again = the one after (TalkedToPc 1)
    when it differs. Empty texts when no Greeting INFO matches or a define cannot be filled."""
    record = {}
    texts = {}
    for key, talked in (('first', False), ('again', True)):
        pick = conversation_greeting(kinds, topics, actor_id, cell=cell, talked_to=talked)
        filled = fill_defines(kinds, actor_id, pick['text'], cell) if pick else None
        record[key] = None if pick is None else {
            'topic': pick['topic'], 'info': pick['info'], 'determined': pick['determined'],
            'unknown_before': pick['unknown_before'], 'filled': filled is not None}
        texts[key] = filled or ''
    if texts['again'] == texts['first']:
        texts['again'] = ''
    return {'first': texts['first'], 'again': texts['again'], 'record': record}


def exterior_cell_names(kinds, cells):
    """{(x, y): name} for exterior cells as the filter sees them (OpenMW World::getCellName): the
    cell's own name, else its region's name, else the region ID."""
    out = {}
    for cell in cells:
        if cell['flags'] & 1:
            continue
        name = cell['name']
        if not name and cell.get('region'):
            name = _display(kinds, 'REGN', cell['region']) or cell['region']
        out[(cell['x'], cell['y'])] = name
    return out


DIALOGUE_KINDS = ('GLOB', 'SCPT', 'CLAS', 'FACT', 'REGN')


def dialogue_records(path, kinds):
    """kinds plus what the conversation greeting reads beside mwad.npc.load_master's records: GLOB,
    SCPT (keyed by its SCHD name), CLAS, FACT, REGN and the DIAL types ('DIAL': {topic: type}).
    A new dict (the given one is not changed); one more pass over the master, records only."""
    from .esm import is_deleted, records, subrecords
    out = dict(kinds)
    for tag in DIALOGUE_KINDS + ('DIAL',):
        out[tag] = {}
    for tag, flags, raw in records(path.read_bytes()):
        if tag not in out or tag not in DIALOGUE_KINDS + ('DIAL',):
            continue
        fields = list(subrecords(raw))
        if tag == 'DIAL':
            kind = first(fields, 'DATA')
            out['DIAL'][text(fields, 'NAME').casefold()] = kind[0] if kind else None
            continue
        if is_deleted(flags, fields):
            continue
        name = string(first(fields, 'SCHD')[:32], 'SCHD') if tag == 'SCPT' else text(fields, 'NAME')
        out[tag][name.casefold()] = fields
    return out
