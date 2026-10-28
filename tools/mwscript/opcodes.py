# SPDX-License-Identifier: GPL-3.0-only
"""The shared opcode table of AmiWind's compiled game logic (docs/MWSCRIPT_BYTECODE.md "The opcode table").

One encoding for every compiled condition and script: MWScript (this compiler) and the NPC greeting and dialogue
conditions (the greetings table) use the same opcodes for the same things: globals, journal indexes, the
speaker's disposition and the player's state. engine/aga/src/aw_mwcode.h holds the same numbers for the engine;
tests/test_mwscript.py checks the two agree.

A stack machine of 32-bit cells. Operands follow their opcode, big-endian. Whole numbers and numbers with a
fraction have their own opcodes (the compiler knows every type), so a 68040 without a busy FPU path runs the
whole-number scripts on integer instructions only.
"""

# name: (code, operand layout). Layout letters: b s8, B u8, h s16 (relative jump: from the end of the operand), H u16,
# i s32, f f32, "N" = a MESSAGEBOX argument list and "F" = a NOTYET call (see below).
OPCODES = {
    # control
    'END': (0x00, ''), 'RET': (0x01, ''), 'JMP': (0x02, 'h'), 'JZ': (0x03, 'h'),
    # constants
    'PUSHB': (0x04, 'b'), 'PUSHW': (0x05, 'h'), 'PUSHL': (0x06, 'i'), 'PUSHF': (0x07, 'f'),
    # variables: L this object's locals (slot), G globals (index), M another object's or script's locals
    'GETL': (0x08, 'B'), 'SETL': (0x09, 'B'), 'SETLS': (0x0A, 'B'),
    'GETG': (0x0B, 'H'), 'SETG': (0x0C, 'H'), 'SETGS': (0x0D, 'H'),
    'GETM': (0x0E, 'HB'), 'SETM': (0x0F, 'HB'), 'SETMS': (0x10, 'HB'),
    # journal (topic index)
    'GETJ': (0x11, 'H'), 'SETJ': (0x12, 'H'), 'JOURNAL': (0x13, 'H'),
    # conversions and arithmetic
    'I2F': (0x14, ''), 'F2I': (0x15, ''),
    'ADDI': (0x16, ''), 'SUBI': (0x17, ''), 'MULI': (0x18, ''), 'DIVI': (0x19, ''), 'NEGI': (0x1A, ''),
    'ADDF': (0x1B, ''), 'SUBF': (0x1C, ''), 'MULF': (0x1D, ''), 'DIVF': (0x1E, ''), 'NEGF': (0x1F, ''),
    'EQI': (0x20, ''), 'NEI': (0x21, ''), 'LTI': (0x22, ''), 'LEI': (0x23, ''), 'GTI': (0x24, ''), 'GEI': (0x25, ''),
    'EQF': (0x26, ''), 'NEF': (0x27, ''), 'LTF': (0x28, ''), 'LEF': (0x29, ''), 'GTF': (0x2A, ''), 'GEF': (0x2B, ''),
    'POP': (0x2C, ''),
    # the object the next call acts on (object table index; 0xFFFF the player)
    'REF': (0x2D, 'H'),
    # an engine query (QUERIES below) with one operand -> pushes a whole number
    'QUERY': (0x2E, 'BH'),
    # a function the engine does not carry out yet (the import route): counted by its number and logged once, its
    # numeric arguments handed to the host's call() with its strings and then popped, 0 pushed if it has a value
    # (or what call() answers once the engine carries it out by number)
    'NOTYET': (0x2F, 'F'),
    # audio (sound table index, voice table index, music table index)
    'PLAYSOUND': (0x30, 'H'), 'PLAYSOUNDVP': (0x31, 'H'), 'PLAYSOUND3D': (0x32, 'H'), 'PLAYSOUND3DVP': (0x33, 'H'),
    'PLAYLOOP3D': (0x34, 'H'), 'PLAYLOOP3DVP': (0x35, 'H'), 'STOPSOUND': (0x36, 'H'), 'SOUNDPLAYING': (0x37, 'H'),
    'SAY': (0x38, 'HH'), 'SAYDONE': (0x39, ''), 'STREAMMUSIC': (0x3A, 'H'),
    # the interpreter's own
    'SECONDS': (0x40, ''), 'RANDOM': (0x41, ''), 'MENUMODE': (0x42, ''), 'CELLCHANGED': (0x43, ''),
    'STARTSCRIPT': (0x44, 'H'), 'STOPSCRIPT': (0x45, 'H'), 'SCRIPTRUNNING': (0x46, 'H'), 'DISTANCE': (0x47, 'H'),
    'SQRT': (0x48, ''),
    # object state (the object REF names, else the script's own): disabled, and a lock's level (Lock pops it; -1 is
    # "the level it had", as Lock without a number); GETDISABLED and GETLOCKED push a whole number
    'ENABLE': (0x49, ''), 'DISABLE': (0x4A, ''), 'GETDISABLED': (0x4B, ''),
    'LOCK': (0x4C, ''), 'UNLOCK': (0x4D, ''), 'GETLOCKED': (0x4E, ''),
    # activation (the original's rule: a script that reads OnActivate takes over its object's use): ONACTIVATE pushes
    # 1 once after the player used the object; ACTIVATE carries out the object's own use (a door opens)
    'ONACTIVATE': (0x4F, ''), 'ACTIVATE': (0x50, ''),
    # messages: MESSAGEBOX shows a text (its numbers formatted in) with its buttons; GETBUTTONPRESSED pushes the
    # button the player chose, once (-1 until then)
    'MESSAGEBOX': (0x51, 'N'), 'GETBUTTONPRESSED': (0x52, ''),
    # the actor record (engine/aga/src/aw_actorstate.h; docs/ACTOR_STATE.md), on the object REF names, else the
    # script's own: ACTOR u8 verb u8 stat (GET and RATIO push, SET MOD MODCURRENT pop; the value is a whole number
    # for WHOLE_STATS, else a number with a fraction); ITEM u8 verb (0 count: pushes, 1 add, 2 remove: pop the count)
    # u16 item (the actor table's AITM row); SPELL u8 verb (0 has: pushes, 1 add, 2 remove) u16 spell (ASPT row);
    # COMBAT u8 verb (0 StartCombat, 1 StopCombat) u16 the other object (0xFFFF the player); DEADCOUNT u16 the
    # actor (ACTB row, 0xFFFF none: 0) pushes a whole number
    'ACTOR': (0x53, 'BB'), 'ITEM': (0x54, 'BH'), 'SPELL': (0x55, 'BH'), 'COMBAT': (0x56, 'BH'),
    'DEADCOUNT': (0x57, 'H'),
    # AIWander (the ambient tables' wander, engine/aga/src/aw_ambient.h): u8 the arguments after the first three;
    # pops 3 + that many whole numbers (range, duration, time, then OpenMW's argument list), in order
    'AIWANDER': (0x58, 'B'),
    # the squeeze (v0.0.54): an "if" or "while" testing a whole number against a small constant, in one opcode
    # instead of PUSHB, the comparison and JZ: JNEB s8 k, s16 pops a whole number and jumps when it is not k;
    # JCMPB u8 test (CMP_CODES), s8 k, s16 jumps when "value test k" is false. Offsets from the end of the operand.
    'JNEB': (0x59, 'bh'), 'JCMPB': (0x5A, 'Bbh'),
    # the world and cell lookups (v0.0.54): GETPCCELL u16 a row of the PCEL section (the cells a GetPCCell name
    # matches, made at build time) pushes 1 when the player stands in one; GETPOS u8 axis (0 x, 1 y, 2 z) pushes the
    # position of REF's object or the script's own, in game units (a fraction)
    'GETPCCELL': (0x5B, 'H'), 'GETPOS': (0x5C, 'B'),
    # PositionCell of the player with constant numbers (v0.0.54): u16 a row of the PMOV section, the move worked out at
    # build time (into a room: its map and the arrival in the map's units; outdoors: the original's coordinates)
    'PLAYERMOVE': (0x5D, 'H'),
    # the AI package of REF's actor or the script's own (v0.0.54): u8 verb, 0 GetCurrentAIPackage (OpenMW's numbers:
    # -1 none, 0 Wander, 1 Travel, 2 Escort, 3 Follow, 4 Activate), 1 GetAIPackageDone; pushes a whole number
    'AIPACKAGE': (0x5E, 'B'),
}
PLAYERMOVE_KINDS = {'outdoors': 1, 'room': 2}
# SPELL verbs beyond has/add/remove: 3 has a common disease, 4 has a blight disease (any spell of that type; the
# operand is not used)
SPELL_VERBS = {'has': 0, 'add': 1, 'remove': 2, 'common_disease': 3, 'blight_disease': 4}
# The most functions the engine counts (aw_mwcode.h AWM_FUNCTIONS); functions.py has fewer (a test checks).
FUNCTIONS_MAX = 640
CMP_CODES = {'==': 0, '!=': 1, '<': 2, '<=': 3, '>': 4, '>=': 5}
# The actor record's stats and the ACTOR verbs: the same numbers as aw_actorstate.h (AWA_*, AWV_*), checked by
# tests/test_mwscript.py.
ACTOR_STATS = {'attribute': 0, 'skill': 8, 'health': 35, 'magicka': 36, 'fatigue': 37, 'level': 38, 'hello': 39,
               'fight': 40, 'flee': 41, 'alarm': 42, 'disposition': 43, 'ondeath': 44, 'dead': 45}
WHOLE_STATS = {38, 39, 40, 41, 42, 43, 44, 45}
VERBS = {'get': 0, 'set': 1, 'mod': 2, 'modcurrent': 3, 'ratio': 4}
# NOTYET operands (layout "F"): u16 the function's number (functions.py FUNCTION_NUMBERS), u16 its name (string
# index, for the log), u8 numeric arguments popped (bit 7: pushes a value, bit 6: the value is a number with a
# fraction, bit 5: had a reference), u8 string arguments, then one u16 string index per string argument (the
# reference's id first when it had one).
# MESSAGEBOX (layout "N"): u16 the text (string index), u8 numbers popped (each a number with a fraction),
# u8 buttons, then one u16 string index per button.

# QUERY numbers: the engine facts a condition or a script asks for, with their u16 operand. Shared with the NPC
# greeting conditions (INFO records' function conditions); 0 means "not available yet" and is logged once.
QUERIES = {
    'DISPOSITION': 1,      # the speaker's disposition toward the player (operand unused)
    'PC_LEVEL': 2,         # the player's level
    'PC_SEX': 3,           # the player's sex (0 male, 1 female)
    'PC_REPUTATION': 4,    # the player's reputation
    'PC_CRIME': 5,         # the player's crime level (bounty)
    'PC_HEALTH_PCT': 6,    # the player's health, percent of the maximum
    'PC_RANK': 7,          # the player's rank in a faction (operand: faction string index; 0xFFFF the speaker's)
    'PC_EXPELLED': 8,      # the player is expelled from a faction (operand as PC_RANK)
    'PC_SPELL': 9,         # the player knows a spell (operand: spell id string index)
    'ITEM_COUNT': 10,      # the player carries this many of an item (operand: item id string index)
    'DEAD_COUNT': 11,      # how many of this id are dead (operand: actor id string index)
    'PC_GOLD': 12,         # the player's gold
    'PC_CLOTHING_MOD': 13, # the player's clothing value
    'SAME_FACTION': 14,    # the speaker and the player share a faction
    'SPEAKER_RANK': 15,    # the speaker's rank in its faction
    'PC_WEREWOLF': 16,     # the player is a werewolf
    'PC_VAMPIRE': 17,      # the player is a vampire (PCVampire global in the game; kept for conditions)
    'TALKED_TO_PC': 18,    # the speaker has talked to the player before
    'PC_ATTRIBUTE': 19,    # a player attribute (operand: attribute number 0-7)
    'PC_SKILL': 20,        # a player skill (operand: skill number 0-26)
    'WEATHER': 21,         # the current weather number
    'HOUR': 22,            # the game hour, whole hours
}

CODE = {name: code for name, (code, _) in OPCODES.items()}
NAME = {code: name for name, (code, _) in OPCODES.items()}
LAYOUT = {code: layout for _, (code, layout) in OPCODES.items()}
if len(NAME) != len(OPCODES):
    raise ValueError('Duplicate opcode numbers')

NONE = 0xFFFF          # "no index": the player as a REF/DISTANCE target, an unmapped sound
CMP_I = {'==': 'EQI', '!=': 'NEI', '<': 'LTI', '<=': 'LEI', '>': 'GTI', '>=': 'GEI'}
CMP_F = {'==': 'EQF', '!=': 'NEF', '<': 'LTF', '<=': 'LEF', '>': 'GTF', '>=': 'GEF'}
ARITH_I = {'+': 'ADDI', '-': 'SUBI', '*': 'MULI', '/': 'DIVI'}
ARITH_F = {'+': 'ADDF', '-': 'SUBF', '*': 'MULF', '/': 'DIVF'}
