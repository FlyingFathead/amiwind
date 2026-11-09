/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_reset.h: the one game-state reset (NEWGAME-STATE-RESET-62, DBG-RESTARTGAME-62). New Game and dbg restartgame
 * both run AW_ResetAll; nothing else resets a game.
 *
 * EVERY MODULE THAT KEEPS GAME STATE (anything a game changes that a fresh boot does not have: story, globals, the
 * world change list, lights and fires, effects, script state, placed or taken objects, followers, message boxes)
 * REGISTERS HERE, at its init, with AW_ResetRegister(name, reset, digest):
 *   reset(new_game): put the module back to what a fresh boot has (new_game 1: New Game, 0: dbg restartgame);
 *   digest(): a hash of that state (NULL when it has nothing to compare), so the reset check can tell a state that
 *   survives: AW_ResetDigest at boot and right after New Game must be the same (dbg resetcheck; tests/aga_reset_test.c).
 * The rules have no engine dependencies and are host-tested (tests/aga_reset_test.c); docs/GAME_STATE_RESET.md. */
#ifndef AW_RESET_H
#define AW_RESET_H

#define AW_RESET_MODULES 32

typedef void (*aw_reset_fn)(int new_game);
typedef unsigned long (*aw_reset_digest_fn)(void);

/* 1: registered (the same reset again: its name and digest replaced); 0: the table is full or no reset given */
int AW_ResetRegister(const char *name, aw_reset_fn reset, aw_reset_digest_fn digest);
int AW_ResetModules(void);
/* every reset, in the order registered; returns how many ran */
int AW_ResetAll(int new_game);
/* the digest of module I (0 without one); its name; -1/NULL past the table */
unsigned long AW_ResetModuleDigest(int i);
const char *AW_ResetModuleName(int i);
/* FNV-1a over BYTES, chained from SEED (start with AW_RESET_SEED): for the modules' digests */
#define AW_RESET_SEED 2166136261UL
unsigned long AW_ResetHash(unsigned long seed, const void *bytes, unsigned long size);
/* The boot digests kept (AW_ResetMarkBoot) and the modules whose state differs from them now: their names written
 * into OUT (comma separated), the count returned. */
void AW_ResetMarkBoot(void);
int AW_ResetCompareBoot(char *out, int capacity);

#endif
