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
	 "cbuf", "server", "client", "screen", "snd", "scene", "save", "window"};
static double	frame_time[AW_SP_SLOTS];
static long		frame_bytes[AW_SP_SLOTS], frame_calls[AW_SP_SLOTS];
static unsigned long	chim_last[AW_SPIKE_CHIM_COUNTS];
static double	last_frame;
/* Totals since the last report: frames, spikes by size, their time, and the
 * spike time per slot. */
#define BANDS	4
static const int	band_ms[BANDS] = {100, 300, 700, 1500};
static unsigned long	frames, band_count[BANDS];
static double	band_time[BANDS], spike_slot[AW_SP_SLOTS], worst;

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
}

void AW_SpikeFrame (void)
{
	double now = Sys_FloatTime (), dt = last_frame > 0 ? now - last_frame : 0;
	unsigned long counts[AW_SPIKE_CHIM_COUNTS], d[AW_SPIKE_CHIM_COUNTS];
	char line[512];
	int i, used, ms = (int)(dt * 1000 + .5);

	aw_spike_on = threshold > 0;
	last_frame = now;
	memset (counts, 0, sizeof(counts));
	if (aw_chim_spike_counts)
		aw_chim_spike_counts (counts, AW_SPIKE_CHIM_COUNTS);
	for (i=0 ; i<AW_SPIKE_CHIM_COUNTS ; i++)
	{
		d[i] = counts[i] >= chim_last[i] ? counts[i] - chim_last[i] : counts[i];
		chim_last[i] = counts[i];
	}
	if (!aw_spike_on || dt <= 0)
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
		if (used < (int)sizeof(line) - 120)
			snprintf (line + used, sizeof(line) - used, " | chim rd %luK/%lu mdl %lu tex %lu chk %lu ev %lu pf %lu/%luK",
				(d[0] + 1023)/1024, d[1], d[2], d[3], d[4], d[5], d[6], (d[7] + 1023)/1024);
		Con_Printf ("%s\n", line);
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
