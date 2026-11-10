/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_loadtrace.c: the load trace (CHIM-SEYDA-BALMORA-LOAD-HANG-43, LOAD-HANG-WATCHDOG-62). Off by default
 * (aw_loadtrace 0). When on, every fopen, fread, fseek and fclose the engine makes (the disk wait wrappers in
 * aw_spike.h) goes into a fixed ring in memory: the operation, the file, the bytes asked and the answer, the time it
 * started and ended (or "not finished"), and the load stage (the heap audit phase). Nothing is written while a
 * load runs: a stop is one file call that never gets its reply, so a file write during the load could itself be
 * the call that stops. The ring is printed (the last lines and every unfinished call) and written in full to
 * RAM:amiwind-loadtrace.txt when the scene is ready, and on demand (dbg loadtrace dump). On a stop the ring is read
 * from memory by the smoke's stall examination: the console line "Load trace on: ring at $ADDR" names it, and
 * its header starts with the eight bytes AWLTRACE (layout below, read by tools/engine_smoke.py STALL_PY).
 *
 * Ring layout (big-endian, offsets in bytes): header magic[8] "AWLTRACE", count (calls traced since on), entries
 * (128), entry size (64), started (ms of the clock at on); then 128 entries of 64 bytes: t0 ms, t1 ms (0xFFFFFFFF =
 * not finished), bytes asked, result, op (1 open, 2 read, 3 seek, 4 close), stage[11], name[36] (the path's last 35
 * characters). Entry k holds call number count - ((count - 1 - k) mod 128) .. : the call numbered N is in entry
 * (N - 1) mod 128.
 *
 * Cost: off, one test of aw_loadtrace_on per file call; on, two clock reads and a 64-byte write per call, a name
 * copy on open, a 16-slot lookup on read, seek and close. Memory: 8,216 bytes of ring + 16 x 40 bytes of open file
 * names, static, at any Fast RAM size.
 */
#define AW_DISKWAIT_NO_WRAP		/* the dump's own file must not trace itself */
#ifndef AW_LOADTRACE_HOST_TEST
#include "quakedef.h"
#include "aw_spike.h"
#else
#include <stdio.h>
#include <string.h>
double Sys_FloatTime (void);
void Con_Printf (char *fmt, ...);
#endif

void AW_LoadTraceSet (int on);
unsigned long AW_LoadTraceBegin (int op, const void *file, const char *name, long bytes);
void AW_LoadTraceEnd (unsigned long seq, long result, const void *file);
void AW_LoadTraceStage (const char *phase, int cvar_on);
int AW_LoadTraceFormat (unsigned long seq, char *out, int size);
unsigned long AW_LoadTraceCount (void);
void AW_LoadTraceDump (const char *why, int lines);
void AW_LoadTraceSceneReady (const char *why);
int AW_LoadTraceCvar (void);
void AW_LoadTraceInit (void);

#define LT_ENTRIES	128
#define LT_FILES	16
#define LT_OPEN		0xFFFFFFFFUL
#define LT_FILE		"RAM:amiwind-loadtrace.txt"

typedef struct
{
	unsigned long	t0, t1;
	long			bytes, result;
	unsigned char	op;
	char			stage[11];
	char			name[36];
} lt_entry_t;

typedef struct
{
	char			magic[8];
	unsigned long	count, entries, entry_size, started;
	lt_entry_t		e[LT_ENTRIES];
} lt_ring_t;

#ifndef AW_LOADTRACE_HOST_TEST	/* the layout stall.py reads (32-bit longs): 64-byte entries after a 24-byte header */
typedef char lt_entry_is_64_bytes[sizeof (lt_entry_t) == 64 ? 1 : -1];
typedef char lt_header_is_24_bytes[sizeof (lt_ring_t) == 24 + 64 * LT_ENTRIES ? 1 : -1];
#endif

int aw_loadtrace_on;
static lt_ring_t ring;
static struct {const void *file; char name[36];} files[LT_FILES];
static int file_next, busy, dumped;
static double started;
static char stage[11] = "boot";
static const char *const op_names[] = {"?", "open", "read", "seek", "close"};

static void copy_tail (char *out, int size, const char *in)
{
	int n = in ? (int)strlen (in) : 0;
	if (n > size - 1)
		in += n - (size - 1);
	strncpy (out, in ? in : "", size - 1);
	out[size - 1] = 0;
}

static unsigned long now_ms (void)
{
	unsigned long ms = (unsigned long)((Sys_FloatTime () - started) * 1000.0);
	return ms == LT_OPEN ? ms - 1 : ms;
}

void AW_LoadTraceSet (int on)
{
	on = on ? 1 : 0;
	if (on && !aw_loadtrace_on)
	{
		memset (&ring, 0, sizeof (ring));
		memset (files, 0, sizeof (files));
		memcpy (ring.magic, "AWLTRACE", 8);
		ring.entries = LT_ENTRIES;
		ring.entry_size = sizeof (lt_entry_t);
		started = Sys_FloatTime ();
		file_next = dumped = 0;
		Con_Printf ("Load trace on: ring at $%08lX, %d calls of %d bytes; written to %s when a scene is ready\n",
			(unsigned long)&ring, LT_ENTRIES, (int)sizeof (lt_entry_t), LT_FILE);
	}
	else if (!on && aw_loadtrace_on)
		Con_Printf ("Load trace off (%lu calls traced)\n", ring.count);
	aw_loadtrace_on = on;
}

static const char *file_name (const void *file)
{
	int i;
	for (i = 0; i < LT_FILES; i++)
		if (files[i].file == file && file)
			return files[i].name;
	return "?";
}

/* one traced call begins: its number (0 = not traced) */
unsigned long AW_LoadTraceBegin (int op, const void *file, const char *name, long bytes)
{
	lt_entry_t *e;
	if (!aw_loadtrace_on || busy)
		return 0;
	e = &ring.e[ring.count % LT_ENTRIES];
	e->t0 = now_ms ();
	e->t1 = LT_OPEN;
	e->bytes = bytes;
	e->result = 0;
	e->op = (unsigned char)op;
	copy_tail (e->stage, sizeof (e->stage), stage);
	copy_tail (e->name, sizeof (e->name), name ? name : file_name (file));
	return ++ring.count;
}

/* the call numbered SEQ ended with RESULT; an open's FILE (NULL when it failed) is remembered by NAME, a close's forgotten */
void AW_LoadTraceEnd (unsigned long seq, long result, const void *file)
{
	lt_entry_t *e;
	int i;
	if (!seq || seq > ring.count || ring.count - seq >= LT_ENTRIES)
		return;
	e = &ring.e[(seq - 1) % LT_ENTRIES];
	e->t1 = now_ms ();
	e->result = result;
	if (e->op == 1 && file)
	{
		files[file_next].file = file;
		memcpy (files[file_next].name, e->name, sizeof (files[file_next].name));
		file_next = (file_next + 1) % LT_FILES;
	}
	else if (e->op == 4)
		for (i = 0; i < LT_FILES; i++)
			if (files[i].file == file)
				files[i].file = NULL;
}

/* the load stage for the next calls (the heap audit phase); a new load (outgoing, before-bsp) may dump again */
void AW_LoadTraceStage (const char *phase, int cvar_on)
{
	if (cvar_on != aw_loadtrace_on)
		AW_LoadTraceSet (cvar_on);
	if (!phase || !*phase)
		return;
	copy_tail (stage, sizeof (stage), phase);
	if (!strcmp (phase, "outgoing") || !strcmp (phase, "before-bsp"))
		dumped = 0;
}

/* the line of the call numbered SEQ; 0 when the ring no longer holds it */
int AW_LoadTraceFormat (unsigned long seq, char *out, int size)
{
	const lt_entry_t *e;
	if (!seq || seq > ring.count || ring.count - seq >= LT_ENTRIES || size < 2)
		return 0;
	e = &ring.e[(seq - 1) % LT_ENTRIES];
	if (e->t1 == LT_OPEN)
		snprintf (out, size, "LT %lu %s %s %s %ld bytes, at %lu ms, NOT FINISHED", seq, e->stage,
			op_names[e->op < 5 ? e->op : 0], e->name, e->bytes, e->t0);
	else
		snprintf (out, size, "LT %lu %s %s %s %ld bytes -> %ld, at %lu ms, %lu ms", seq, e->stage,
			op_names[e->op < 5 ? e->op : 0], e->name, e->bytes, e->result, e->t0, e->t1 - e->t0);
	return 1;
}

unsigned long AW_LoadTraceCount (void) {return ring.count;}

/* the ring to the console (the last LINES calls and every unfinished one) and in full to LT_FILE */
void AW_LoadTraceDump (const char *why, int lines)
{
	unsigned long seq, first, last, open = 0;
	char line[160];
	FILE *f;
	if (!aw_loadtrace_on)
	{
		Con_Printf ("Load trace is off (dbg loadtrace on)\n");
		return;
	}
	busy = 1;		/* the console log's own file calls during the dump are not traced */
	last = ring.count;
	first = last > LT_ENTRIES ? last - LT_ENTRIES + 1 : 1;
	for (seq = first; seq <= last; seq++)
		if (ring.e[(seq - 1) % LT_ENTRIES].t1 == LT_OPEN)
			open++;
	Con_Printf ("Load trace (%s): %lu calls since on, %lu kept, %lu not finished; stage %s; ring at $%08lX; %s\n",
		why, last, last - first + 1, open, stage, (unsigned long)&ring, LT_FILE);
	for (seq = first; seq <= last; seq++)
		if ((seq + lines > last || ring.e[(seq - 1) % LT_ENTRIES].t1 == LT_OPEN)
			&& AW_LoadTraceFormat (seq, line, sizeof (line)))
			Con_Printf ("%s\n", line);
	f = fopen (LT_FILE, "w");
	if (f)
	{
		fprintf (f, "AmiWind load trace (%s): %lu calls since on, stage %s\n", why, last, stage);
		for (seq = first; seq <= last; seq++)
			if (AW_LoadTraceFormat (seq, line, sizeof (line)))
				fprintf (f, "%s\n", line);
		fclose (f);
	}
	busy = 0;
}

/* once per load, when the scene is ready (aw_scene.c) or first presented (aw_stream.c) */
void AW_LoadTraceSceneReady (const char *why)
{
	if (!aw_loadtrace_on || dumped)
		return;
	dumped = 1;
	AW_LoadTraceDump (why, 8);
}

#ifndef AW_LOADTRACE_HOST_TEST
static cvar_t loadtrace_cvar = {"aw_loadtrace", "0"};

static void loadtrace_command (void)
{
	const char *a = Cmd_Argc () > 1 ? Cmd_Argv (1) : "";
	if (!strcmp (a, "on") || !strcmp (a, "1"))
		Cvar_SetValue ("aw_loadtrace", 1);
	else if (!strcmp (a, "off") || !strcmp (a, "0"))
		Cvar_SetValue ("aw_loadtrace", 0);
	AW_LoadTraceSet ((int)loadtrace_cvar.value);
	if (!strcmp (a, "dump"))
		AW_LoadTraceDump ("on demand", 32);
	else if (!*a)
		Con_Printf ("Load trace %s, %lu calls traced (dbg loadtrace on/off/dump; console aw_loadtrace 0/1)\n",
			aw_loadtrace_on ? "on" : "off", ring.count);
}

int AW_LoadTraceCvar (void) {return loadtrace_cvar.value != 0;}

void AW_LoadTraceInit (void)
{
	Cvar_RegisterVariable (&loadtrace_cvar);
	Cmd_AddCommand ("aw_loadtrace_cmd", loadtrace_command);
}
#endif
