/* SPDX-License-Identifier: GPL-2.0-or-later
 * The player's standing (v0.0.57): crime level (bounty), reputation, and per faction the rank, the expelled mark and
 * the faction reputation, as the scripts read and change them (docs/MWSCRIPT_BYTECODE.md). The rules are OpenMW's
 * (apps/openmw/mwscript/statsextensions.cpp OpGetPCCrimeLevel .. OpPcClearExpelled, dialogueextensions.cpp
 * OpGetReputation; apps/openmw/mwmechanics/npcstats.cpp getFactionRank, joinFaction, setFactionRank, setReputation),
 * written independently. A fixed table, no allocation; faction ids are compared without case.
 *
 * Pure C, no engine headers (native tests: tests/test_mwscript.py StandingTests). */
#ifndef AW_PCSTANDING_H
#define AW_PCSTANDING_H

#define AW_STANDING_FACTIONS 32    /* factions the player can belong to or be known by at once */
#define AW_STANDING_RANKS 10       /* rank slots of a faction record (FACT RNAM), so the highest rank is 9 */

void AW_StandingReset(void);
int AW_StandingCrime(void);                      /* GetPCCrimeLevel: the bounty */
void AW_StandingSetCrime(int bounty);            /* SetPCCrimeLevel (as given) */
void AW_StandingModCrime(int change);            /* ModPCCrimeLevel: never below 0 */
int AW_StandingReputation(void);
void AW_StandingSetReputation(int value);        /* clamped to 0..255 as in the original */
/* Factions: FACTION an id (any case). Rank -1: not a member. */
int AW_StandingRank(const char *faction);
void AW_StandingJoin(const char *faction);       /* PCJoinFaction: rank 0 when not a member */
void AW_StandingRaise(const char *faction);      /* PCRaiseRank: joins when not a member, else one rank up (capped) */
void AW_StandingLower(const char *faction);      /* PCLowerRank: one down; below 0 leaves and clears the expelled mark */
int AW_StandingExpelled(const char *faction);
void AW_StandingSetExpelled(const char *faction,int expelled);
int AW_StandingFactionReputation(const char *faction);
void AW_StandingSetFactionReputation(const char *faction,int value);
/* 1 when the table had no room for a new faction (the call did nothing) since the last reset. */
int AW_StandingFull(void);
/* Saved games: the standing as a byte block (AWPS1); Export returns the bytes (-1 too small), Import 1 or 0 for a
 * bad block (then the standing is empty). */
int AW_StandingExport(unsigned char *out,int capacity);
int AW_StandingImport(const unsigned char *data,int bytes);
#endif
