/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Diagnostic logs held in memory (BOOT-VOLUME-NOT-VALIDATED-33).
 *
 * The engine's diagnostic logs used to be written to the boot volume while the
 * game ran, which kept the volume "being written" about 15 % of play time; an
 * emulator closed in such a moment makes AmigaOS validate the whole volume at
 * the next boot. Each log now has a fixed buffer (no growth; the oldest lines
 * drop when it is full) and is written to disk once at exit, on a fatal error
 * and on demand (dbg savelogs). Saves and settings are not logs and are written
 * as before.
 *
 * Live mode (aw_logs_live 1, dbg logs live on, builder --live-logs) writes the
 * logs as they happen, exactly as before, for benchmarks and diagnostics.
 * Without a bound switch (host tools and tests) logs are live as well.
 *
 * Kinds: a stream log collects lines (optionally under a header line); a
 * snapshot log is rewritten whole between AW_LogBegin and AW_LogEnd. */
#ifndef AW_LOG_H
#define AW_LOG_H

enum {
    AW_LOG_DEBUG,          /* DEBUG.TXT: copy of the console */
    AW_LOG_WALK,           /* walk-profile.csv */
    AW_LOG_STALLS,         /* frame-stalls.csv */
    AW_LOG_FRAME,          /* frame-profile.txt (snapshot) */
    AW_LOG_HEAP,           /* heap-audit.log */
    AW_LOG_CELL_LOAD,      /* cell-load-profile.tsv */
    AW_LOG_CELL_VISIBLE,   /* cell-visible-profile.tsv */
    AW_LOG_BSP_LOAD,       /* bsp-load-profile.txt (snapshot) */
    AW_LOG_MUSIC_EVENTS,   /* music-events.csv */
    AW_LOG_MUSIC_PROFILE,  /* music-profile.txt (snapshot) */
    AW_LOG_HISTORY,        /* console-history.txt (snapshot; path set by AW_LogSetPath) */
    AW_LOG_COUNT
};

/* Engine: point at the aw_logs_live cvar value (non-zero = live). */
void AW_LogUseSwitch(const float *live);
int AW_LogLive(void);
/* Override the file name of a log (console history lives in the game folder). */
void AW_LogSetPath(int log, const char *path);
const char *AW_LogPath(int log);
/* Stream logs. The header (a string that must stay valid) starts the file. */
void AW_LogHeader(int log, const char *header);
void AW_LogWrite(int log, const char *text);
void AW_LogPrintf(int log, const char *format, ...);
/* Live mode: close a stream log's open file now (its owner shut down). */
void AW_LogStreamClose(int log);
/* Snapshot logs. */
void AW_LogBegin(int log);
void AW_LogEnd(int log);
/* Write every buffered log to disk; returns the number of files written. */
int AW_LogFlushAll(void);
/* Close live files (exit). */
void AW_LogClose(void);
/* Accounting for messages and tests. */
unsigned long AW_LogDroppedLines(int log);
unsigned long AW_LogBufferedBytes(int log);
unsigned long AW_LogCapacity(int log);
unsigned long AW_LogTotalCapacity(void);

#endif
