/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef AW_ACTIVATED_H
#define AW_ACTIVATED_H
/* Placed objects the engine activates as func_wall edicts, found by their
 * original reference number (the "aw_ref" field; aw_opening.c). This is the
 * one list: the CHIM frame maps keep an edict for every reference named here
 * (tools/chim/frame_map.py activated_refs reads these lines), because a CHIM
 * frame otherwise draws and collides with placed objects in its chunks and
 * gives them no edict. One "#define AW_REF_<NAME> <number>" per line. */
#define AW_REF_COURTYARD_BARREL 172851
#define AW_REF_CENSUS_PAPERS 172859
#define AW_REF_CENSUS_HALL_DOOR 172860
#endif
