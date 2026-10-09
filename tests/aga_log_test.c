/* SPDX-License-Identifier: GPL-2.0-or-later */
/* In-memory diagnostic logs (engine/aga/src/aw_log.c, BOOT-VOLUME-NOT-VALIDATED-33):
 * bounded buffers, line order, flushes, the live switch and the readers' files.
 * Run in an empty scratch directory: "check" runs the unit checks, "profile"
 * writes benchmark files (argument 2: live or memory) for tools/profile_aga.py. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "aw_log.h"

static char text[65536];

static const char *slurp(const char *path)
{
    FILE *f = fopen(path, "rb");
    size_t n;
    if (!f) return NULL;
    n = fread(text, 1, sizeof text - 1, f);
    text[n] = 0;
    fclose(f);
    return text;
}

static int exists(const char *path) {FILE *f = fopen(path, "rb"); if (f) fclose(f); return f != NULL;}

static int count_lines(const char *s) {int n = 0; for (; *s; s++) if (*s == '\n') n++; return n;}

static void check(void)
{
    float live = 0.0f;
    const char *s;
    char line[64];
    int i, first;
    unsigned long total = AW_LogTotalCapacity();

    /* Fixed size: a few tens of KB in all, nothing grows. */
    assert(total >= 16384 && total <= 49152);

    /* Unbound (host tools): live, as before. */
    assert(AW_LogLive());
    AW_LogUseSwitch(&live);
    assert(!AW_LogLive());

    /* Memory mode: nothing reaches the disk while playing. */
    AW_LogHeader(AW_LOG_WALK, "frame,value\n");
    for (i = 0; i < 2000; i++) AW_LogPrintf(AW_LOG_WALK, "%d,%d\n", i, i * 3);
    AW_LogWrite(AW_LOG_DEBUG, "console line one\n");
    AW_LogPrintf(AW_LOG_HEAP, "format=AWH1 phase=%s\n", "first");
    AW_LogBegin(AW_LOG_FRAME); AW_LogWrite(AW_LOG_FRAME, "frames=1\n"); AW_LogEnd(AW_LOG_FRAME);
    AW_LogBegin(AW_LOG_FRAME); AW_LogWrite(AW_LOG_FRAME, "frames=2\n"); AW_LogEnd(AW_LOG_FRAME);
    assert(!exists("walk-profile.csv") && !exists("DEBUG.TXT") && !exists("heap-audit.log") &&
           !exists("frame-profile.txt") && !exists("music-events.csv"));

    /* Bounded: the buffer never exceeds its size; the oldest whole lines went. */
    assert(AW_LogBufferedBytes(AW_LOG_WALK) <= AW_LogCapacity(AW_LOG_WALK));
    assert(AW_LogDroppedLines(AW_LOG_WALK) > 0);

    /* Flush: header first, then the newest lines in order, all complete. */
    assert(AW_LogFlushAll() == 4);
    s = slurp("walk-profile.csv");
    assert(s && !strncmp(s, "frame,value\n", 12));
    assert(strstr(s, "1999,5997\n") && !strstr(s, "\n0,0\n"));
    first = atoi(s + 12);
    assert(first > 0);
    assert(count_lines(s) == 1 + (2000 - first));
    assert((unsigned long)count_lines(s) - 1 + AW_LogDroppedLines(AW_LOG_WALK) == 2000);
    s = slurp("frame-profile.txt");
    assert(s && !strcmp(s, "frames=2\n"));  /* a snapshot holds its latest contents */
    assert(AW_LogBufferedBytes(AW_LOG_WALK) == 0);

    /* A second flush adds only what is new: no line twice, header once. */
    AW_LogPrintf(AW_LOG_WALK, "%d,%d\n", 2000, 6000);
    assert(AW_LogFlushAll() == 1);
    s = slurp("walk-profile.csv");
    assert(strstr(s, "1999,5997\n2000,6000\n"));
    assert(!strstr(strstr(s, "frame,value") + 1, "frame,value"));
    assert(count_lines(s) == 2 + (2000 - first));
    assert(AW_LogFlushAll() == 0);           /* nothing new: nothing written */

    /* Append logs keep earlier sessions' lines and gain the new ones. */
    s = slurp("heap-audit.log");
    assert(!strcmp(s, "format=AWH1 phase=first\n"));

    /* One write larger than the buffer keeps its newest whole lines. */
    {
        static char big[20000];
        size_t at = 0;
        for (i = 0; at + 32 < sizeof big; i++) at += (size_t)sprintf(big + at, "big %05d\n", i);
        AW_LogWrite(AW_LOG_CELL_VISIBLE, big);
        assert(AW_LogBufferedBytes(AW_LOG_CELL_VISIBLE) < AW_LogCapacity(AW_LOG_CELL_VISIBLE));
        AW_LogFlushAll();
        s = slurp("cell-visible-profile.tsv");
        sprintf(line, "big %05d\n", i - 1);
        assert(!strncmp(s, "big ", 4) && strstr(s, line));
        assert(s[strlen(s) - 1] == '\n');
    }

    /* Switch on: the buffered lines go first, then lines are written as they come. */
    AW_LogWrite(AW_LOG_DEBUG, "console line two\n");
    live = 1.0f;
    AW_LogWrite(AW_LOG_DEBUG, "console line three\n");
    fflush(NULL);
    s = slurp("DEBUG.TXT");
    assert(s && strstr(s, "console line one\nconsole line two\nconsole line three\n"));
    AW_LogPrintf(AW_LOG_HEAP, "format=AWH1 phase=%s\n", "live");
    s = slurp("heap-audit.log");
    assert(!strcmp(s, "format=AWH1 phase=first\nformat=AWH1 phase=live\n"));
    AW_LogBegin(AW_LOG_FRAME); AW_LogWrite(AW_LOG_FRAME, "frames=3\n"); AW_LogEnd(AW_LOG_FRAME);
    assert(!strcmp(slurp("frame-profile.txt"), "frames=3\n"));
    /* A stream header in live mode creates the file at once, as before. */
    AW_LogHeader(AW_LOG_MUSIC_EVENTS, "time_ms,event\n");
    fflush(NULL);
    assert(!strcmp(slurp("music-events.csv"), "time_ms,event\n"));

    /* Switch off: later lines stay in memory until the next flush, then append. */
    live = 0.0f;
    AW_LogWrite(AW_LOG_DEBUG, "console line four\n");
    s = slurp("DEBUG.TXT");
    assert(!strstr(s, "four"));
    AW_LogFlushAll();
    s = slurp("DEBUG.TXT");
    assert(strstr(s, "console line three\nconsole line four\n") && count_lines(s) == 4);

    /* A live file that cannot be created is skipped, never fatal, not retried per line. */
    AW_LogSetPath(AW_LOG_STALLS, "no-such-folder/frame-stalls.csv");
    live = 1.0f;
    for (i = 0; i < 10; i++) AW_LogWrite(AW_LOG_STALLS, "1,2,3\n");
    assert(!exists("no-such-folder/frame-stalls.csv"));
    assert(!strcmp(AW_LogPath(AW_LOG_STALLS), "no-such-folder/frame-stalls.csv"));
    AW_LogClose();
    puts("aw_log ok");
}

/* Benchmark files as the engine writes them, for tools/profile_aga.py. */
static void profile(int live_mode)
{
    float live = live_mode ? 1.0f : 0.0f;
    int i;
    AW_LogUseSwitch(&live);
    AW_LogHeader(AW_LOG_WALK, "frame,elapsed_ms,frame_us,x100,y100,z100,yaw100,hunk_bytes,distance,world_us,map,server_us,surface_order\n");
    for (i = 10; i <= 3000; i += 10)
        AW_LogPrintf(AW_LOG_WALK, "%d,%d,%d,0,0,0,0,1000,540,100,maps/sn029.bsp,50,2\n", i, i * 70, 60000 + (i % 7) * 1000);
    AW_LogBegin(AW_LOG_FRAME);
    AW_LogPrintf(AW_LOG_FRAME, "frames=%d\nelapsed_ms=%d\nworst_frame_us=%d\nheap_used_bytes=%d\n", 3000, 210000, 90000, 1000);
    AW_LogPrintf(AW_LOG_FRAME, "audio_late_updates=0\nmissed_audio_frames=0\nsurface_overflow_frames=0\nedge_overflow_frames=0\n");
    AW_LogEnd(AW_LOG_FRAME);
    AW_LogBegin(AW_LOG_MUSIC_PROFILE);
    AW_LogPrintf(AW_LOG_MUSIC_PROFILE, "read_slices=4\nread_errors=0\n");
    AW_LogWrite(AW_LOG_MUSIC_PROFILE, "track_history=4,11,42\n");
    AW_LogEnd(AW_LOG_MUSIC_PROFILE);
    /* Exit game. */
    AW_LogFlushAll();
    AW_LogClose();
    puts("profile written");
}

int main(int argc, char **argv)
{
    if (argc > 1 && !strcmp(argv[1], "profile")) {profile(argc > 2 && !strcmp(argv[2], "live")); return 0;}
    check();
    return 0;
}
