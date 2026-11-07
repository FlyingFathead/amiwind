/* SPDX-License-Identifier: GPL-2.0-or-later
 * Frame spikes: "chim spikes MS" prints one line for every frame of MS ms or more,
 * with the work that ran in it (aw_spike.h). Times are this machine's (in an
 * emulator: relative); the attribution is the comparable part.
 */
#include "quakedef.h"
#include "aw_spike.h"

static int		threshold;		/* ms; 0: off */
int				aw_spike_on;
void			(*aw_chim_spike_counts)(unsigned long *out, int count);

static const char	*slot_name[AW_SP_SLOTS] =
	{"spawn", "mapfile", "index", "chimbegin", "clinfo", "prime", "tick", "link", "read", "sound", "prefetch",
	 "cbuf", "server", "client", "screen", "snd", "scene", "save", "window",
	 "modal", "mwscript", "ticks", "pstart", "ents", "companion", "combat", "ambient", "room", "items", "magic",
	 "lava", "runclients", "sendmsg", "ambscan", "ambaggro", "ambchoose", "ambwalk",
	 "input", "remote", "net", "hostcon", "audiox", "tail"};
static double	frame_time[AW_SP_SLOTS];
static double	ent_worst;		/* the slowest entity of this frame's physics loop */
static int		ent_worst_num;

void AW_SpikeEnt (int num, double seconds)
{
	if (seconds > ent_worst)
	{
		ent_worst = seconds;
		ent_worst_num = num;
	}
}
static long		frame_bytes[AW_SP_SLOTS], frame_calls[AW_SP_SLOTS];
static unsigned long	chim_last[AW_SPIKE_CHIM_COUNTS];
static double	last_frame;
/* Totals since the last report: frames, spikes by size, their time, and the
 * spike time per slot. */
#define BANDS	4
static const int	band_ms[BANDS] = {100, 300, 700, 1500};
static unsigned long	frames, band_count[BANDS];
static double	band_time[BANDS], spike_slot[AW_SP_SLOTS], worst;

/* ARRIVAL-LONG-FRAME-DEV6-59: this frame's file work (aw_spike.h AW_SpikeFile), always counted, and the longest
 * frame since the last report with its file work (the line kept as text). */
#define FILE_NAMES	4
typedef struct {unsigned long finds, misses, reads, bytes; int names; struct {char name[40]; unsigned long n;} name[FILE_NAMES];} files_t;
static files_t		fw;
static double		longest;
static char			longest_line[400];	/* FRAME-WAIT-COUNTERS-59: room for the waits */
/* the order of a frame's file lookups with their time into the frame, printed under a "Long frame" line: the gaps
 * between them show where a long frame spends its time */
#define TRACE	48
static struct {char name[32]; int ms;} trace[TRACE];
static int			traced;
static double		frame_start;

/* FRAME-WAIT-COUNTERS-59: this frame's waits (aw_spike.h AW_WAIT_*), their sums since the last report */
double				aw_wait_time[AW_WAITS];
int					aw_disk_depth;
static double		wait_sum[AW_WAITS], wait_frames_time;
static unsigned long	wait_frames;
static const char	*wait_name[AW_WAITS] = {"disk", "c2p", "vbl"};

/* ", disk 12.3 ms, c2p 8.1 ms, vbl 0.0 ms" (tenths of a ms: no float printing needed) */
static int WaitText (char *out, int size, const double *t)
{
	int i, used = 0;
	out[0] = 0;
	for (i=0 ; i<AW_WAITS && used < size - 24 ; i++)
	{
		long tenths = (long)(t[i] * 10000 + .5);
		used += snprintf (out + used, size - used, "%s%s %ld.%ld ms", i ? ", " : "", wait_name[i], tenths / 10, tenths % 10);
	}
	return used;
}

unsigned long aw_file_finds;	/* every file looked up by name since the start (aw_view.c: what an assembly read) */
unsigned long aw_file_reads;	/* every file read since the start (BENCH-RESULT-FILE-62) */
double aw_disk_total;			/* the disk wait of every finished frame since the start (BENCH-RESULT-FILE-62) */
void AW_SpikeFile (const char *name, int found)
{
	int i;
	aw_file_finds++;
	if (traced < TRACE && name)
	{
		Q_strncpy (trace[traced].name, (char *)name, sizeof(trace[0].name) - 1);
		trace[traced].name[sizeof(trace[0].name) - 1] = 0;
		trace[traced++].ms = frame_start > 0 ? (int)((Sys_FloatTime () - frame_start) * 1000) : -1;
	}
	fw.finds++;
	if (!found)
		fw.misses++;
	if (!name)
		return;
	for (i=0 ; i<fw.names ; i++)
		if (!strncmp (fw.name[i].name, name, sizeof(fw.name[i].name) - 1))
		{
			fw.name[i].n++;
			return;
		}
	if (fw.names < FILE_NAMES)
	{
		Q_strncpy (fw.name[fw.names].name, (char *)name, sizeof(fw.name[0].name) - 1);
		fw.name[fw.names].name[sizeof(fw.name[0].name) - 1] = 0;
		fw.name[fw.names++].n = 1;
	}
}

void AW_SpikeFileRead (long bytes)
{
	aw_file_reads++;
	fw.reads++;
	if (bytes > 0)
		fw.bytes += (unsigned long)bytes;
}

/* " files F found/M missed, reads R/K: name xN, ..." into OUT (empty when the frame touched no file) */
static int FilesText (char *out, int size)
{
	int i, used;
	out[0] = 0;
	if (!fw.finds && !fw.reads)
		return 0;
	used = snprintf (out, size, " files %lu (%lu missed), reads %lu/%luK", fw.finds, fw.misses, fw.reads, (fw.bytes + 1023)/1024);
	for (i=0 ; i<fw.names && used < size - 48 ; i++)
		used += snprintf (out + used, size - used, "%s%s x%lu", i ? ", " : ": ", fw.name[i].name, fw.name[i].n);
	return used;
}

void AW_SpikeAdd (int slot, double seconds, long bytes)
{
	if (slot < 0 || slot >= AW_SP_SLOTS || seconds < 0)
		return;
	frame_time[slot] += seconds;
	frame_bytes[slot] += bytes;
	frame_calls[slot]++;
}

static void Clear (void)
{
	memset (frame_time, 0, sizeof(frame_time));
	memset (frame_bytes, 0, sizeof(frame_bytes));
	memset (frame_calls, 0, sizeof(frame_calls));
	ent_worst = 0;
	ent_worst_num = -1;
}

void AW_SpikeFrame (void)
{
	double now = Sys_FloatTime (), dt = last_frame > 0 ? now - last_frame : 0;
	unsigned long counts[AW_SPIKE_CHIM_COUNTS], d[AW_SPIKE_CHIM_COUNTS];
	char line[512], files[200], waits[64];
	int i, used, ms = (int)(dt * 1000 + .5);

	/* ARRIVAL-LONG-FRAME-DEV6-59: the stages are timed always (a clock read per stage), so a "Long frame" line names
	 * where its time went with spikes off too; the spike lines and totals still only with "chim spikes MS" */
	aw_spike_on = 1;
	last_frame = now;
	/* FRAME-WAIT-COUNTERS-59: the frame's waits, always; the rest of the frame is the processor's own work */
	WaitText (waits, sizeof(waits), aw_wait_time);
	if (dt > 0)
	{
		for (i=0 ; i<AW_WAITS ; i++)
			wait_sum[i] += aw_wait_time[i];
		wait_frames++;
		wait_frames_time += dt;
	}
	aw_disk_total += aw_wait_time[AW_WAIT_DISK];
	memset (aw_wait_time, 0, sizeof(aw_wait_time));
	aw_disk_depth = 0;		/* never inside a file call here; a Sys_Error longjmp out of one is forgotten */
	/* ARRIVAL-LONG-FRAME-DEV6-59: the frame's file work, always */
	FilesText (files, sizeof(files));
	if (dt > 0 && ms >= AW_SPIKE_LONG_MS)
	{
		char st[200];
		int u = 0;
		st[0] = 0;
		for (i=0 ; i<AW_SP_SLOTS && u < (int)sizeof(st) - 24 ; i++)
			if (frame_calls[i] && frame_time[i] >= .05)
				u += snprintf (st + u, sizeof(st) - u, " %s %ld", slot_name[i], (long)(frame_time[i]*1000 + .5));
		Con_Printf ("Long frame %d ms f%ld stages:%s\n", ms, (long)host_framecount, st[0] ? st : " none timed");
	}
	if (dt > longest)
	{
		longest = dt;
		snprintf (longest_line, sizeof(longest_line), "%d ms f%ld %s (%s):%s", ms, (long)host_framecount,
			sv.active ? sv.name : "-", waits, files[0] ? files : " no file work");
	}
	if (dt > 0 && ms >= AW_SPIKE_LONG_MS && (threshold <= 0 || ms < threshold))
		Con_Printf ("Long frame %d ms f%ld %s (%s):%s\n", ms, (long)host_framecount, sv.active ? sv.name : "-",
			waits, files[0] ? files : " no file work");
	if (dt > 0 && ms >= AW_SPIKE_LONG_MS && traced)
	{
		char t[480];
		int k, u = 0;
		for (k=0 ; k<traced && u < (int)sizeof(t) - 48 ; k++)
			u += snprintf (t + u, sizeof(t) - u, " +%d %s", trace[k].ms, trace[k].name);
		Con_Printf ("  its files in order (ms into the frame):%s\n", t);
	}
	traced = 0;
	frame_start = now;
	memset (&fw, 0, sizeof(fw));
	memset (counts, 0, sizeof(counts));
	if (aw_chim_spike_counts)
		aw_chim_spike_counts (counts, AW_SPIKE_CHIM_COUNTS);
	for (i=0 ; i<AW_SPIKE_CHIM_COUNTS ; i++)
	{
		d[i] = counts[i] >= chim_last[i] ? counts[i] - chim_last[i] : counts[i];
		chim_last[i] = counts[i];
	}
	if (threshold <= 0 || dt <= 0)
	{
		Clear ();
		return;
	}
	frames++;
	if (ms >= threshold)
	{
		for (i=BANDS-1 ; i>=0 && ms < band_ms[i] ; i--)
			;
		if (i >= 0)
		{
			band_count[i]++;
			band_time[i] += dt;
		}
		if (dt > worst)
			worst = dt;
		used = snprintf (line, sizeof(line), "spike %ld ms f%ld %s @%ld %ld:", (long)ms, (long)host_framecount,
			sv.active ? sv.name : "-", (long)r_refdef.vieworg[0], (long)r_refdef.vieworg[1]);
		for (i=0 ; i<AW_SP_SLOTS && used < (int)sizeof(line) - 40 ; i++)
		{
			if (!frame_calls[i] || (i >= AW_SP_CBUF && frame_time[i] < .002))
				continue;
			spike_slot[i] += frame_time[i];
			used += snprintf (line + used, sizeof(line) - used, " %s %ld", slot_name[i], (long)(frame_time[i]*1000 + .5));
			if (frame_bytes[i])
				used += snprintf (line + used, sizeof(line) - used, "/%ldK", (frame_bytes[i] + 1023)/1024);
			if (frame_calls[i] > 1)
				used += snprintf (line + used, sizeof(line) - used, "x%ld", frame_calls[i]);
		}
		if (ent_worst_num >= 0 && ent_worst >= .002 && sv.active && ent_worst_num < sv.num_edicts
			&& used < (int)sizeof(line) - 160)
		{
			edict_t *e = EDICT_NUM (ent_worst_num);
			used += snprintf (line + used, sizeof(line) - used, " | slowest ent %d %s %ld", ent_worst_num,
				e->free ? "(free)" : pr_strings + e->v.classname, (long)(ent_worst*1000 + .5));
		}
		if (used < (int)sizeof(line) - 120)
			snprintf (line + used, sizeof(line) - used, " | chim rd %luK/%lu mdl %lu tex %lu chk %lu ev %lu pf %lu/%luK",
				(d[0] + 1023)/1024, d[1], d[2], d[3], d[4], d[5], d[6], (d[7] + 1023)/1024);
		Con_Printf ("%s | %s%s%s\n", line, waits, files[0] ? " |" : "", files);
	}
	Clear ();
}

void AW_SpikeSet (int ms)
{
	threshold = ms > 0 ? ms : 0;
}

int AW_SpikeThreshold (void)
{
	return threshold;
}

void AW_SpikeReport (void)
{
	int i;
	Con_Printf ("spikes since the last report: %lu frames, worst %ld ms (chim spikes %ld)\n", frames,
		(long)(worst*1000 + .5), (long)threshold);
	if (longest_line[0])		/* ARRIVAL-LONG-FRAME-DEV6-59: kept with spikes off too */
		Con_Printf ("  longest frame: %s\n", longest_line);
	longest = 0;
	longest_line[0] = 0;
	if (wait_frames)		/* FRAME-WAIT-COUNTERS-59: every frame, spikes on or off */
	{
		char waits[64];
		double busy = wait_frames_time - wait_sum[AW_WAIT_DISK] - wait_sum[AW_WAIT_C2P] - wait_sum[AW_WAIT_VBL];
		WaitText (waits, sizeof(waits), wait_sum);
		Con_Printf ("  waits in %lu frames (%ld ms): %s; the rest %ld ms\n", wait_frames,
			(long)(wait_frames_time*1000 + .5), waits, (long)(busy*1000 + .5));
	}
	memset (wait_sum, 0, sizeof(wait_sum));
	wait_frames = 0;
	wait_frames_time = 0;
	for (i=0 ; i<BANDS ; i++)
		Con_Printf ("  >= %4ld ms: %lu frames, %ld ms in all\n", (long)band_ms[i], band_count[i],
			(long)(band_time[i]*1000 + .5));
	for (i=0 ; i<AW_SP_SLOTS ; i++)
		if (spike_slot[i] > 0)
			Con_Printf ("  in spikes: %-9s %ld ms\n", slot_name[i], (long)(spike_slot[i]*1000 + .5));
	frames = 0;
	worst = 0;
	memset (band_count, 0, sizeof(band_count));
	memset (band_time, 0, sizeof(band_time));
	memset (spike_slot, 0, sizeof(spike_slot));
}

void AW_SpikeInit (void)
{
	threshold = 0;
}
