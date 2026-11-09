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
#define AWM_NOTYET 0x2F        /* u16 function number (tools/mwscript/functions.py FUNCTION_NUMBERS), u16 name,
                                  u8 flags (low 5 bits: numbers popped; 0x80 pushes, 0x40 a fraction, 0x20 had a
                                  reference), u8 strings, u16 per string: counted by number, logged once, handed to
                                  the host's call() (the import route) */
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
/* object state (the object REF names, else the script's own; host object()): */
#define AWM_ENABLE 0x49
#define AWM_DISABLE 0x4A
#define AWM_GETDISABLED 0x4B   /* -> whole */
#define AWM_LOCK 0x4C          /* pops the level (-1: the level it had) */
#define AWM_UNLOCK 0x4D
#define AWM_GETLOCKED 0x4E     /* -> whole */
/* activation (host object()): a script that reads OnActivate takes over its object's use */
#define AWM_ONACTIVATE 0x4F    /* -> whole: 1 once after the player used the script's object */
#define AWM_ACTIVATE 0x50      /* the object's own use (a door opens), on REF's object or the script's */
/* messages (host message() and button()) */
#define AWM_MESSAGEBOX 0x51    /* u16 text, u8 numbers popped (fractions), u8 buttons, u16 per button (as NOTYET) */
#define AWM_GETBUTTONPRESSED 0x52 /* -> whole: the button the player chose, once; -1 until then */
/* the actor record (host actor(), item(), spell(), combat(), dead_count(); aw_actorstate.h AWA_* and AWV_*) */
#define AWM_ACTOR 0x53         /* u8 verb, u8 stat: GET/RATIO push, SET/MOD/MODCURRENT pop */
#define AWM_ITEM 0x54          /* u8 verb (0 count -> whole, 1 add, 2 remove: pop the count), u16 item */
#define AWM_SPELL 0x55         /* u8 verb (0 has -> whole, 1 add, 2 remove, 3 has a common disease -> whole, 4 has a
                                  blight disease -> whole), u16 spell (0 for 3 and 4) */
#define AWM_COMBAT 0x56        /* u8 verb (0 StartCombat, 1 StopCombat), u16 the other object (0xFFFF the player) */
#define AWM_DEADCOUNT 0x57     /* u16 actor row -> whole */
#define AWM_AIWANDER 0x58      /* u8 extra arguments: pops 3 + extra whole numbers (host wander()) */
/* the squeeze: a whole number against a small constant, and the branch, in one opcode (pops the number) */
#define AWM_JNEB 0x59          /* s8 k, s16: jumps when the number is not k */
#define AWM_JCMPB 0x5A         /* u8 test (0 == 1 != 2 < 3 <= 4 > 5 >=), s8 k, s16: jumps when "number test k" fails */
/* the world and cell lookups (host player_cell() and position()) */
#define AWM_GETPCCELL 0x5B     /* u16 PCEL row -> whole: 1 when the player stands in a cell of the row */
#define AWM_GETPOS 0x5C        /* u8 axis (0 x, 1 y, 2 z) -> fraction: REF's object's or the script's own, game units */
#define AWM_PLAYERMOVE 0x5D    /* u16 PMOV row: the player's PositionCell worked out at build time (host player_move()) */
#define AWM_AIPACKAGE 0x5E     /* u8 verb (0 the current package, OpenMW's numbers, -1 none; 1 done) -> whole (host ai_package()) */
#define AWM_MOVE_OUTDOORS 1
#define AWM_MOVE_ROOM 2
#define AWM_SPELL_COMMON_DISEASE 3
#define AWM_SPELL_BLIGHT_DISEASE 4
#define AWM_FUNCTIONS 640      /* the most function numbers NOTYET carries (tools/mwscript/opcodes.py FUNCTIONS_MAX) */
/* Function numbers the host's call() carries out (v0.0.57; tools/mwscript/functions.py HOST and FUNCTION_NUMBERS,
 * checked by tests/test_mwscript.py) */
#define AWF_ADDTOPIC 6
#define AWF_CHOICE 22
#define AWF_CLEARINFOACTOR 27
#define AWF_SHOWMAP 448
#define AWF_SHOWRESTMENU 449
/* the menus a script turns on (CENSUS-INTRO-SCRIPTS-62; OpenMW guiextensions.cpp OpEnableWindow, OpShowDialogue) */
#define AWF_ENABLEBIRTHMENU 44
#define AWF_ENABLECLASSMENU 45
#define AWF_ENABLEINVENTORYMENU 46
#define AWF_ENABLEMAGICMENU 49
#define AWF_ENABLEMAPMENU 50
#define AWF_ENABLESTATREVIEWMENU 60
#define AWF_ENABLESTATSMENU 61
#define AWF_GETPCSLEEP 160
#define AWF_MODFACTIONREACTION 260
#define AWF_SETFACTIONREACTION 390
#define AWF_GOODBYE 219
#define AWF_AIFOLLOW 10
#define AWF_AITRAVEL 12
#define AWF_AIESCORT 8
#define AWF_AIESCORTCELL 9
#define AWF_AIFOLLOWCELL 11
#define AWF_GETSTANDINGPC 201
#define AWF_POSITION 345
#define AWF_POSITIONCELL 346
#define AWF_PLACEATME 333
#define AWF_PLACEATPC 334
#define AWF_PLACEITEM 335
#define AWF_PLACEITEMCELL 336
#define AWF_CAST 17
#define AWF_FORCEGREETING 74
#define AWF_GETEFFECT 114
#define AWF_GETTARGET 208
#define AWF_ROTATE 359
#define AWF_GETPCCRIMELEVEL 154
#define AWF_GETPCFACREP 155
#define AWF_GETPCRANK 158
#define AWF_GETRACE 172
#define AWF_GETREPUTATION 173
#define AWF_LOOPGROUP 231
#define AWF_PLAYGROUP 338
#define AWF_MODPCCRIMELEVEL 281
#define AWF_MODPCFACREP 282
#define AWF_MODREPUTATION 286
#define AWF_PCCLEAREXPELLED 324
#define AWF_PCEXPELL 325
#define AWF_PCEXPELLED 326
#define AWF_PCJOINFACTION 330
#define AWF_PCLOWERRANK 331
#define AWF_PCRAISERANK 332
#define AWF_RAISERANK 348
#define AWF_LOWERRANK 232
#define AWF_SETPCCRIMELEVEL 413
#define AWF_SETPCFACREP 414
#define AWF_SETREPUTATION 418
/* v0.0.62: the player's control switches (aw_story.h AW_Control*, MWSCRIPT-PLAYER-CONTROL-62) */
#define AWF_DISABLELEVITATION 31
#define AWF_DISABLEPLAYERCONTROLS 32
#define AWF_DISABLEPLAYERFIGHTING 33
#define AWF_DISABLEPLAYERJUMPING 34
#define AWF_DISABLEPLAYERLOOKING 35
#define AWF_DISABLEPLAYERMAGIC 36
#define AWF_DISABLEPLAYERVIEWSWITCH 37
#define AWF_DISABLETELEPORTING 38
#define AWF_DISABLEVANITYMODE 39
#define AWF_ENABLELEVITATION 48
#define AWF_ENABLEPLAYERCONTROLS 52
#define AWF_ENABLEPLAYERFIGHTING 53
#define AWF_ENABLEPLAYERJUMPING 54
#define AWF_ENABLEPLAYERLOOKING 55
#define AWF_ENABLEPLAYERMAGIC 56
#define AWF_ENABLEPLAYERVIEWSWITCH 57
#define AWF_ENABLETELEPORTING 62
#define AWF_ENABLEVANITYMODE 63
#define AWF_GETPLAYERCONTROLSDISABLED 165
#define AWF_GETPLAYERFIGHTINGDISABLED 166
#define AWF_GETPLAYERJUMPINGDISABLED 167
#define AWF_GETPLAYERLOOKINGDISABLED 168
#define AWF_GETPLAYERMAGICDISABLED 169
#define AWF_GETPLAYERVIEWSWITCHDISABLED 170
#define AWF_GETVANITYMODEDISABLED 210
/* v0.0.62: the small functions (aw_mwhost.c, MWSCRIPT-SMALL-FUNCTIONS-62) */
#define AWF_FACE 66
#define AWF_GETANGLE 85
#define AWF_GETCURRENTWEATHER 106
/* v0.0.62 (MWSCRIPT-COMPLETE-LANDMARK): a region's weather and its chances (aw_weather.c AW_WeatherScript*) */
#define AWF_CHANGEWEATHER 21
#define AWF_MODREGION 285
#define AWF_GETDETECTED 110
#define AWF_GETINTERIOR 134
#define AWF_GETLINEOFSIGHT 140
#define AWF_GETLOS 143
#define AWF_GETPCSNEAKING 161
#define AWF_GETWEAPONDRAWN 214
#define AWF_ROTATEWORLD 360
#define AWF_SETDELETE 385
#define AWF_MOVE 314
#define AWF_MOVEWORLD 315
#define AWF_ONKNOCKOUT 318
#define AWF_SETANGLE 371
#define AWF_SETATSTART 375
#define AWF_SETPOS 417
#define AWF_WAKEUPPC 502
/* v0.0.62: the crimes (aw_crime.c, CRIME-59) */
#define AWF_GETPCINJAIL 156
#define AWF_GOTOJAIL 220
#define AWF_ONMURDER 319
#define AWF_PAYFINE 322
#define AWF_PAYFINETHIEF 323
/* v0.0.62: the fades, the forced sneak, the resistances (aw_mwhost.c, MWSCRIPT-GAP-FUNCTIONS-62) */
#define AWF_FADEIN 67
#define AWF_FADEOUT 68
#define AWF_FADETO 69
#define AWF_CLEARFORCESNEAK 26
#define AWF_FORCESNEAK 78
#define AWF_GETFORCESNEAK 126
#define AWF_GETRESISTBLIGHT 174
#define AWF_GETRESISTCORPRUS 175
#define AWF_GETRESISTDISEASE 176
#define AWF_GETRESISTFIRE 177
#define AWF_GETRESISTFROST 178
#define AWF_GETRESISTMAGICKA 179
#define AWF_GETRESISTNORMALWEAPONS 180
#define AWF_GETRESISTPARALYSIS 181
#define AWF_GETRESISTPOISON 182
#define AWF_GETRESISTSHOCK 183
#define AWF_MODRESISTBLIGHT 287
#define AWF_MODRESISTCORPRUS 288
#define AWF_MODRESISTDISEASE 289
#define AWF_MODRESISTFIRE 290
#define AWF_MODRESISTFROST 291
#define AWF_MODRESISTMAGICKA 292
#define AWF_MODRESISTNORMALWEAPONS 293
#define AWF_MODRESISTPARALYSIS 294
#define AWF_MODRESISTPOISON 295
#define AWF_MODRESISTSHOCK 296
#define AWF_SETRESISTBLIGHT 419
#define AWF_SETRESISTCORPRUS 420
#define AWF_SETRESISTDISEASE 421
#define AWF_SETRESISTFIRE 422
#define AWF_SETRESISTFROST 423
#define AWF_SETRESISTMAGICKA 424
#define AWF_SETRESISTNORMALWEAPONS 425
#define AWF_SETRESISTPARALYSIS 426
#define AWF_SETRESISTPOISON 427
#define AWF_SETRESISTSHOCK 428
#define AWF_HASSOULGEM 222
#define AWF_REMOVESOULGEM 354
#define AWF_HURTSTANDINGACTOR 227
/* v0.0.63 (MW-CONSOLE-COMMANDS-62): the not-yet functions with call sites (aw_mwhost.c gap_call) */
#define AWF_GETWATERLEVEL 212
#define AWF_GETCOLLIDINGPC 101
#define AWF_HURTCOLLIDINGACTOR 226
#define AWF_GETWEAPONTYPE 215
#define AWF_GETSTAT 204
/* v0.0.63 (MWSCRIPT-GAPS-63): functions no game script calls, for the console and add-on content (aw_mwhost.c
 * resists[], uncalled_call) */
#define AWF_GETCHAMELEON 99
#define AWF_SETCHAMELEON 382
#define AWF_MODCHAMELEON 250
#define AWF_GETWATERWALKING 213
#define AWF_SETWATERWALKING 444
#define AWF_MODWATERWALKING 312
#define AWF_GETSWIMSPEED 207
#define AWF_SETSWIMSPEED 440
#define AWF_MODSWIMSPEED 308
#define AWF_GETSUPERJUMP 206
#define AWF_SETSUPERJUMP 439
#define AWF_MODSUPERJUMP 307
#define AWF_GETFLYING 122
#define AWF_SETFLYING 394
#define AWF_MODFLYING 264
#define AWF_GETARMORBONUS 86
#define AWF_SETARMORBONUS 372
#define AWF_MODARMORBONUS 241
#define AWF_GETCASTPENALTY 98
#define AWF_SETCASTPENALTY 381
#define AWF_MODCASTPENALTY 249
#define AWF_GETSILENCE 190
#define AWF_SETSILENCE 433
#define AWF_MODSILENCE 301
#define AWF_GETBLINDNESS 94
#define AWF_SETBLINDNESS 378
#define AWF_MODBLINDNESS 246
#define AWF_GETPARALYSIS 152
#define AWF_SETPARALYSIS 412
#define AWF_MODPARALYSIS 280
#define AWF_GETINVISIBLE 135
#define AWF_SETINVISIBLE 401
#define AWF_MODINVISIBLE 271
#define AWF_GETATTACKBONUS 90
#define AWF_SETATTACKBONUS 376
#define AWF_MODATTACKBONUS 244
#define AWF_GETDEFENDBONUS 108
#define AWF_SETDEFENDBONUS 384
#define AWF_MODDEFENDBONUS 255
#define AWF_GETCURRENTTIME 105
#define AWF_GETMASSERPHASE 148
#define AWF_GETSECUNDAPHASE 187
#define AWF_GETSTARTINGPOS 203
#define AWF_GETSTARTINGANGLE 202
#define AWF_PCGET3RDPERSON 329
#define AWF_PCFORCE1STPERSON 327
#define AWF_PCFORCE3RDPERSON 328
#define AWF_GETPCJUMPING 157
#define AWF_GETSPELLREADIED 198
#define AWF_GETSTANDINGACTOR 200
#define AWF_GETCOLLIDINGACTOR 100
/* batch 2 */
#define AWF_GETPCRUNNING 159
#define AWF_FORCEJUMP 75
#define AWF_CLEARFORCEJUMP 23
#define AWF_FORCEMOVEJUMP 76
#define AWF_CLEARFORCEMOVEJUMP 24
#define AWF_GETFORCEJUMP 123
#define AWF_GETFORCEMOVEJUMP 124
#define AWF_GETARMORTYPE 88
#define AWF_SAMEFACTION 361
#define AWF_GETFACTIONREACTION 117
#define AWF_REMOVEEFFECTS 350
#define AWF_REMOVESPELLEFFECTS 356
#define AWF_ADDSOULGEM 2
#define AWF_DROPSOULGEM 42
#define AWF_ENABLELEVELUPMENU 47
/* batch 3: the console group, as script functions too (aw_mwhost.c console_group_call) */
#define AWF_SHOW 447
#define AWF_SHOWVARS 451
#define AWF_SV 460
#define AWF_TOGGLESCRIPTS 482
#define AWF_TOGGLEAI 472
#define AWF_TAI 461
#define AWF_RESETACTORS 357
#define AWF_RA 347
#define AWF_OUTPUTREFINFO 321
#define AWF_ORI 320
#define AWF_USER1 498
#define AWF_USER2 499
#define AWF_USER3 500
#define AWF_USER4 501
#define AWF_TOGGLECOLLISION 474
#define AWF_TCL 465
#define AWF_TOGGLEGODMODE 479
#define AWF_TGM 470
#define AWF_TOGGLEMENUS 480
#define AWF_TM 471
#define AWF_TOGGLEVANITYMODE 484
#define AWF_TVM 492
#define AWF_CENTERONCELL 19
#define AWF_COC 28
#define AWF_CENTERONEXTERIOR 20
#define AWF_COE 29
#define AWF_FIXME 73
#define AWF_DROP 41
#define AWF_RESURRECT 358
#define AWF_PLAYBINK 337
#define AWF_HITONME 225
/* v0.0.63: Water Breathing read, set and changed as the resistances are (aw_mwhost.c, UNDERWATER-BREATH-62) */
#define AWF_GETWATERBREATHING 211
#define AWF_MODWATERBREATHING 310
#define AWF_SETWATERBREATHING 442
#define AWF_TURNMOONRED 490
#define AWF_TURNMOONWHITE 491
#define AWF_HASITEMEQUIPPED 221
#define AWF_FORCERUN 77
#define AWF_CLEARFORCERUN 25
#define AWF_GETFORCERUN 125
#define AWF_EXPLODESPELL 65
#define AWF_GETATTACKED 91
#define AWF_GETSPELLEFFECTS 197
#define AWF_BECOMEWEREWOLF 15
#define AWF_UNDOWEREWOLF 496
#define AWF_ISWEREWOLF 228
#define AWF_SETWEREWOLFACROBATICS 445
#define AWF_GETWEREWOLFKILLS 216
#define AWF_GETPCTRAVELING 162
#define AWF_SETSCALE 430
#define AWF_ENABLENAMEMENU 51
#define AWF_ENABLERACEMENU 58
#define AWF_ENABLEREST 59
#define AWF_GETSCALE 185
#define AWF_MODSCALE 298
#define AWM_VERB_GET 0
#define AWM_VERB_SET 1
#define AWM_VERB_MOD 2
#define AWM_VERB_MODCURRENT 3
#define AWM_VERB_RATIO 4

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
#define AWS_ONACTIVATE 128     /* reads OnActivate: the player's use of its object goes to the script */

/* Binding flags (BIND rows). */
#define AWB_INTERIOR 1
#define AWB_ACTOR 2
#define AWB_EDICT 4
/* MWSCRIPT-INVENTORY-HITONME-62 (tools/mwscript/compiler.py BIND_HELD, held_key): an item a placed container, NPC or
 * creature holds; its reference is AWB_HELD_BIT, the item's ordinal in bits 24-29 and the holder's reference below */
#define AWB_HELD 8
#define AWB_HELD_BIT 0x40000000u
#define AWB_HELD_KEY(r) (((r)&AWB_HELD_BIT)!=0)
#define AWB_HELD_HOLDER(r) ((r)&0xFFFFFFu)
#endif
