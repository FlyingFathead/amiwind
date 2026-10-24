/* SPDX-License-Identifier: GPL-2.0-or-later
 * The shared opcode table of AmiWind's compiled game logic (docs/MWSCRIPT_BYTECODE.md).
 *
 * One encoding for every compiled script and condition: the MWScript compiler (tools/mwscript/opcodes.py) and the
 * NPC greeting and dialogue conditions use the same numbers for globals, journal indexes, the speaker's
 * disposition and the player's state. tests/test_mwscript.py checks this file against opcodes.py.
 * A stack machine of 32-bit cells; operands big-endian after their opcode. */
#ifndef AW_MWCODE_H
#define AW_MWCODE_H

#define AWM_END 0x00
#define AWM_RET 0x01
#define AWM_JMP 0x02           /* s16: from the end of the operand */
#define AWM_JZ 0x03            /* s16: pops a whole number */
#define AWM_PUSHB 0x04         /* s8 */
#define AWM_PUSHW 0x05         /* s16 */
#define AWM_PUSHL 0x06         /* s32 */
#define AWM_PUSHF 0x07         /* f32 */
#define AWM_GETL 0x08          /* u8 slot */
#define AWM_SETL 0x09          /* u8 slot */
#define AWM_SETLS 0x0A         /* u8 slot: stored as a short (wraps at 16 bits) */
#define AWM_GETG 0x0B          /* u16 global */
#define AWM_SETG 0x0C          /* u16 global */
#define AWM_SETGS 0x0D         /* u16 global: a short */
#define AWM_GETM 0x0E          /* u16 object, u8 slot: another object's or script's local */
#define AWM_SETM 0x0F          /* u16 object, u8 slot */
#define AWM_SETMS 0x10         /* u16 object, u8 slot: a short */
#define AWM_GETJ 0x11          /* u16 topic -> whole */
#define AWM_SETJ 0x12          /* u16 topic: pops the index (SetJournalIndex) */
#define AWM_JOURNAL 0x13       /* u16 topic: pops the index (Journal: only forward, adds the entry) */
#define AWM_I2F 0x14
#define AWM_F2I 0x15
#define AWM_ADDI 0x16
#define AWM_SUBI 0x17
#define AWM_MULI 0x18
#define AWM_DIVI 0x19
#define AWM_NEGI 0x1A
#define AWM_ADDF 0x1B
#define AWM_SUBF 0x1C
#define AWM_MULF 0x1D
#define AWM_DIVF 0x1E
#define AWM_NEGF 0x1F
#define AWM_EQI 0x20
#define AWM_NEI 0x21
#define AWM_LTI 0x22
#define AWM_LEI 0x23
#define AWM_GTI 0x24
#define AWM_GEI 0x25
#define AWM_EQF 0x26
#define AWM_NEF 0x27
#define AWM_LTF 0x28
#define AWM_LEF 0x29
#define AWM_GTF 0x2A
#define AWM_GEF 0x2B
#define AWM_POP 0x2C
#define AWM_REF 0x2D           /* u16 object (0xFFFF the player): the next call acts on it */
#define AWM_QUERY 0x2E         /* u8 query, u16 operand -> whole */
#define AWM_NOTYET 0x2F        /* u16 name, u8 flags (low 5 bits: numbers popped; 0x80 pushes, 0x40 a fraction,
                                  0x20 had a reference), u8 strings, u16 per string */
#define AWM_PLAYSOUND 0x30     /* u16 sound */
#define AWM_PLAYSOUNDVP 0x31   /* u16 sound; pops pitch, volume */
#define AWM_PLAYSOUND3D 0x32
#define AWM_PLAYSOUND3DVP 0x33
#define AWM_PLAYLOOP3D 0x34
#define AWM_PLAYLOOP3DVP 0x35
#define AWM_STOPSOUND 0x36
#define AWM_SOUNDPLAYING 0x37  /* -> whole */
#define AWM_SAY 0x38           /* u16 voice, u16 text */
#define AWM_SAYDONE 0x39       /* -> whole */
#define AWM_STREAMMUSIC 0x3A   /* u16 music */
#define AWM_SECONDS 0x40       /* -> fraction */
#define AWM_RANDOM 0x41        /* pops n -> fraction 0..n-1 */
#define AWM_MENUMODE 0x42
#define AWM_CELLCHANGED 0x43
#define AWM_STARTSCRIPT 0x44   /* u16 script */
#define AWM_STOPSCRIPT 0x45
#define AWM_SCRIPTRUNNING 0x46
#define AWM_DISTANCE 0x47      /* u16 object (0xFFFF the player) -> fraction */
#define AWM_SQRT 0x48

/* QUERY numbers (shared with the greeting conditions). */
#define AWQ_DISPOSITION 1
#define AWQ_PC_LEVEL 2
#define AWQ_PC_SEX 3
#define AWQ_PC_REPUTATION 4
#define AWQ_PC_CRIME 5
#define AWQ_PC_HEALTH_PCT 6
#define AWQ_PC_RANK 7
#define AWQ_PC_EXPELLED 8
#define AWQ_PC_SPELL 9
#define AWQ_ITEM_COUNT 10
#define AWQ_DEAD_COUNT 11
#define AWQ_PC_GOLD 12
#define AWQ_PC_CLOTHING_MOD 13
#define AWQ_SAME_FACTION 14
#define AWQ_SPEAKER_RANK 15
#define AWQ_PC_WEREWOLF 16
#define AWQ_PC_VAMPIRE 17
#define AWQ_TALKED_TO_PC 18
#define AWQ_PC_ATTRIBUTE 19
#define AWQ_PC_SKILL 20
#define AWQ_WEATHER 21
#define AWQ_HOUR 22
#define AWQ_COUNT 23

#define AWM_NONE 0xFFFF

/* Script flags (SCRP rows, tools/mwscript/codegen.py). */
#define AWS_VOLATILE 1
#define AWS_NOTYET 2
#define AWS_START 4
#define AWS_BROKEN 8
#define AWS_GLOBAL 16
#define AWS_HANDWRITTEN 32     /* the engine carries this behaviour by hand today (config/mwscript.json) */
#define AWS_INERT 64           /* nothing it can do today is seen outside its own values: not attached */

/* Binding flags (BIND rows). */
#define AWB_INTERIOR 1
#define AWB_ACTOR 2
#define AWB_EDICT 4
#endif
