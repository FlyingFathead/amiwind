/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Diagnostic awlog_logs held in memory; see aw_log.h (BOOT-VOLUME-NOT-VALIDATED-33).
 * Plain C and stdio only: no console, no zone memory, so the console copy and
 * the heap audit can use it, and host tests can link it alone. */
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include "aw_log.h"

#define awlog_STREAM_WRITE 'w'   /* live: opened once per session, kept open */
#define awlog_STREAM_APPEND 'a'  /* live: appended and closed per line */
#define awlog_SNAPSHOT 's'       /* live: rewritten whole between Begin and End */

typedef struct {
    const char *path;
    char kind;
    unsigned long capacity;
    char *buffer;
    unsigned long used;
    unsigned long dropped;
    const char *header;
    FILE *file;            /* live file */
    int failed;            /* live open failed: no retry (and never fatal) */
    int started;           /* the file was written this session (header in place) */
    int dirty;             /* snapshot: new contents since the last flush */
    int snapshot_live;     /* snapshot: this Begin..End goes straight to disk */
} aw_log_t;

static char awlog_b_debug[8192], awlog_b_walk[6144], awlog_b_stalls[2048], awlog_b_frame[1024], awlog_b_heap[12288],
    awlog_b_cell_load[2048], awlog_b_cell_visible[1024], awlog_b_bsp[2048], awlog_b_music_events[2048],
    awlog_b_music_profile[1024], awlog_b_history[4096];
#define awlog_SLOT(path, kind, buffer) {path, kind, sizeof(buffer), buffer, 0, 0, NULL, NULL, 0, 0, 0, 0}
static aw_log_t awlog_logs[AW_LOG_COUNT] = {
    awlog_SLOT("DEBUG.TXT", awlog_STREAM_WRITE, awlog_b_debug),
    awlog_SLOT("walk-profile.csv", awlog_STREAM_WRITE, awlog_b_walk),
    awlog_SLOT("frame-stalls.csv", awlog_STREAM_WRITE, awlog_b_stalls),
    awlog_SLOT("frame-profile.txt", awlog_SNAPSHOT, awlog_b_frame),
    awlog_SLOT("heap-audit.log", awlog_STREAM_APPEND, awlog_b_heap),
    awlog_SLOT("cell-load-profile.tsv", awlog_STREAM_APPEND, awlog_b_cell_load),
    awlog_SLOT("cell-visible-profile.tsv", awlog_STREAM_APPEND, awlog_b_cell_visible),
    awlog_SLOT("bsp-load-profile.txt", awlog_SNAPSHOT, awlog_b_bsp),
    awlog_SLOT("music-events.csv", awlog_STREAM_WRITE, awlog_b_music_events),
    awlog_SLOT("music-profile.txt", awlog_SNAPSHOT, awlog_b_music_profile),
    awlog_SLOT("console-history.txt", awlog_SNAPSHOT, awlog_b_history),
};
static const float *awlog_live_switch;
static int awlog_bound, awlog_mode_live = -1;

static int awlog_valid(int log) {return log >= 0 && log < AW_LOG_COUNT;}

int AW_LogLive(void)
{
    /* Unbound (host tools and tests): live, as the engine always was. */
    return !awlog_bound || (awlog_live_switch && *awlog_live_switch != 0.0f);
}

void AW_LogUseSwitch(const float *live) {awlog_live_switch = live; awlog_bound = 1; awlog_mode_live = -1;}

void AW_LogSetPath(int log, const char *path) {if (awlog_valid(log) && path) awlog_logs[log].path = path;}
const char *AW_LogPath(int log) {return awlog_valid(log) ? awlog_logs[log].path : "";}

/* Keep the newest whole lines: drop from the front up to a line end, at least
 * a quarter of the buffer at a time so the copying stays rare. */
static void awlog_make_room(aw_log_t *l, unsigned long need)
{
    unsigned long cut, i;
    if (l->used + need <= l->capacity) return;
    cut = l->used + need - l->capacity;
    if (cut < l->capacity / 4) cut = l->capacity / 4;
    if (cut >= l->used) {
        for (i = 0; i < l->used; i++) if (l->buffer[i] == '\n') l->dropped++;
        if (l->used && l->buffer[l->used - 1] != '\n') l->dropped++;
        l->used = 0;
        return;
    }
    while (cut < l->used && l->buffer[cut - 1] != '\n') cut++;
    for (i = 0; i < cut; i++) if (l->buffer[i] == '\n') l->dropped++;
    memmove(l->buffer, l->buffer + cut, l->used - cut);
    l->used -= cut;
}

static void awlog_buffer_text(aw_log_t *l, const char *text, unsigned long n)
{
    if (n >= l->capacity) {
        /* One write larger than the buffer: keep its newest whole lines. */
        const char *start = text + n - (l->capacity - 1);
        const char *line = memchr(start, '\n', (size_t)(text + n - start));
        unsigned long i;
        for (i = 0; i < l->used; i++) if (l->buffer[i] == '\n') l->dropped++;
        for (i = 0; text + i < start; i++) if (text[i] == '\n') l->dropped++;
        if (line && line + 1 < text + n) start = line + 1;
        l->used = 0;
        n = (unsigned long)(text + n - start);
        text = start;
    } else {
        awlog_make_room(l, n);
    }
    memcpy(l->buffer + l->used, text, n);
    l->used += n;
}

static FILE *awlog_open_live(aw_log_t *l, const char *mode)
{
    FILE *f;
    if (l->failed) return NULL;
    f = fopen(l->path, mode);
    if (!f) l->failed = 1;
    return f;
}

/* Live stream file: today's behaviour. 'w' awlog_logs open once (header first) and
 * stay open; 'a' awlog_logs append and close. After a flush this session the file
 * already holds the header, so it is appended to. */
static void awlog_live_stream(aw_log_t *l, const char *text, unsigned long n)
{
    if (l->kind == awlog_STREAM_APPEND) {
        FILE *f = awlog_open_live(l, "a");
        if (f) {fwrite(text, 1, n, f); fclose(f); l->started = 1;}
        return;
    }
    if (!l->file) {
        l->file = awlog_open_live(l, l->started ? "a" : "w");
        if (!l->file) return;
        if (!l->started && l->header) fputs(l->header, l->file);
        l->started = 1;
    }
    fwrite(text, 1, n, l->file);
}

static void awlog_close_live(void)
{
    int i;
    for (i = 0; i < AW_LOG_COUNT; i++)
        if (awlog_logs[i].file && awlog_logs[i].kind != awlog_SNAPSHOT) {fclose(awlog_logs[i].file); awlog_logs[i].file = NULL;}
}

/* Follow the switch: going live first writes what is buffered, so the live
 * files continue it; leaving live mode closes the live files. */
static void awlog_sync_mode(void)
{
    int live = AW_LogLive();
    if (live == awlog_mode_live) return;
    if (awlog_mode_live == 0 && live) {awlog_mode_live = 1; AW_LogFlushAll();}
    else if (awlog_mode_live == 1 && !live) awlog_close_live();
    awlog_mode_live = live;
}

void AW_LogHeader(int log, const char *header)
{
    aw_log_t *l;
    if (!awlog_valid(log)) return;
    l = &awlog_logs[log];
    l->header = header;
    awlog_sync_mode();
    /* Live: the file appears with its header at once, as before. */
    if (awlog_mode_live && l->kind == awlog_STREAM_WRITE && !l->file && !l->started) awlog_live_stream(l, "", 0);
}

void AW_LogWrite(int log, const char *text)
{
    aw_log_t *l;
    unsigned long n;
    if (!awlog_valid(log) || !text) return;
    l = &awlog_logs[log];
    n = (unsigned long)strlen(text);
    if (l->kind == awlog_SNAPSHOT) {
        if (l->snapshot_live) {if (l->file) fwrite(text, 1, n, l->file);}
        else {awlog_buffer_text(l, text, n); l->dirty = 1;}
        return;
    }
    awlog_sync_mode();
    if (awlog_mode_live) awlog_live_stream(l, text, n);
    else awlog_buffer_text(l, text, n);
}

void AW_LogPrintf(int log, const char *format, ...)
{
    char text[1536];
    va_list args;
    va_start(args, format);
    vsnprintf(text, sizeof text, format, args);
    va_end(args);
    text[sizeof text - 1] = 0;
    AW_LogWrite(log, text);
}

void AW_LogStreamClose(int log)
{
    if (awlog_valid(log) && awlog_logs[log].kind != awlog_SNAPSHOT && awlog_logs[log].file) {
        fclose(awlog_logs[log].file);
        awlog_logs[log].file = NULL;
    }
}

void AW_LogBegin(int log)
{
    aw_log_t *l;
    if (!awlog_valid(log)) return;
    l = &awlog_logs[log];
    awlog_sync_mode();
    if (l->file) {fclose(l->file); l->file = NULL;}
    l->snapshot_live = awlog_mode_live;
    if (awlog_mode_live) {l->failed = 0; l->file = awlog_open_live(l, "w");}
    else {l->used = 0; l->dirty = 1;}
}

void AW_LogEnd(int log)
{
    aw_log_t *l;
    if (!awlog_valid(log)) return;
    l = &awlog_logs[log];
    if (l->file) {fclose(l->file); l->file = NULL;}
    l->snapshot_live = 0;
}

int AW_LogFlushAll(void)
{
    int i, written = 0;
    for (i = 0; i < AW_LOG_COUNT; i++) {
        aw_log_t *l = &awlog_logs[i];
        FILE *f;
        if (l->kind == awlog_SNAPSHOT) {
            if (!l->dirty || l->snapshot_live) continue;
            f = fopen(l->path, "w");
            if (!f) continue;
            fwrite(l->buffer, 1, l->used, f);
            fclose(f);
            l->dirty = 0;
            written++;
            continue;
        }
        if (!l->used && (l->started || !l->header)) continue;
        if (l->file) fflush(l->file);
        /* First write of the session: 'w' awlog_logs start fresh with their header;
         * later flushes append, then the buffer is emptied (nothing twice). */
        f = l->file ? l->file : fopen(l->path, (l->kind == awlog_STREAM_WRITE && !l->started) ? "w" : "a");
        if (!f) continue;
        if (l->kind == awlog_STREAM_WRITE && !l->started && l->header) fputs(l->header, f);
        fwrite(l->buffer, 1, l->used, f);
        if (f != l->file) fclose(f); else fflush(f);
        l->started = 1;
        l->used = 0;
        written++;
    }
    return written;
}

void AW_LogClose(void)
{
    int i;
    for (i = 0; i < AW_LOG_COUNT; i++)
        if (awlog_logs[i].file) {fclose(awlog_logs[i].file); awlog_logs[i].file = NULL;}
}

unsigned long AW_LogDroppedLines(int log) {return awlog_valid(log) ? awlog_logs[log].dropped : 0;}
unsigned long AW_LogBufferedBytes(int log) {return awlog_valid(log) ? awlog_logs[log].used : 0;}
unsigned long AW_LogCapacity(int log) {return awlog_valid(log) ? awlog_logs[log].capacity : 0;}
unsigned long AW_LogTotalCapacity(void)
{
    unsigned long total = 0;
    int i;
    for (i = 0; i < AW_LOG_COUNT; i++) total += awlog_logs[i].capacity;
    return total;
}
