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
# i s32, f f32, and "N" = a NOTYET argument list (see below).
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
    # a function the engine cannot carry out yet: logged once, its numeric arguments popped, 0 pushed if it has a value
    'NOTYET': (0x2F, 'N'),
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
}
# NOTYET operands: u16 the function's name (string index), u8 numeric arguments popped (bit 7: pushes a value,
# bit 6: the value is a number with a fraction), u8 string arguments, then one u16 string index per string argument.
# MESSAGEBOX has the same layout: u16 the text (string index), u8 numbers popped (each a number with a fraction),
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
