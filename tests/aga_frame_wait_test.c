/* SPDX-License-Identifier: GPL-2.0-or-later
 * FRAME-WAIT-COUNTERS-59: the frame wait counters of aw_spike.h. Disk calls nested in each other (COM_FindFile ->
 * fopen, Sys_FileRead -> fread) count once, the outermost call's time; the c2p and vbl waits add each call. The
 * clock is a fake that moves only when the test says so. */
#define AMIGA 1
#include <stdio.h>
#include "aw_spike.h"

double aw_wait_time[AW_WAITS];
int aw_disk_depth;
static double now;
double Sys_FloatTime (void) { return now; }

static int failures;
static void expect (const char *what, double got, double want)
{
	if (got < want - 1e-9 || got > want + 1e-9)
	{
		printf ("FAIL %s: %.6f, expected %.6f\n", what, got, want);
		failures++;
	}
}

static void inner_read (double seconds)
{
	double t0;
	AW_DISK_BEGIN (t0);
	now += seconds;
	AW_DISK_END (t0);
}

int main (void)
{
	double t0, outer;
	now = 100.0;
	/* one plain read: 5 ms */
	inner_read (0.005);
	expect ("one read", aw_wait_time[AW_WAIT_DISK], 0.005);
	/* a lookup of 2 ms around two reads of 3 ms each: 8 ms, never 14 */
	AW_DISK_BEGIN (outer);
	now += 0.002;
	inner_read (0.003);
	inner_read (0.003);
	AW_DISK_END (outer);
	expect ("nested once", aw_wait_time[AW_WAIT_DISK], 0.013);
	if (aw_disk_depth != 0)
	{
		printf ("FAIL depth %d after the outermost end\n", aw_disk_depth);
		failures++;
	}
	/* time outside a disk call is not disk wait */
	now += 1.0;
	expect ("busy time is not disk", aw_wait_time[AW_WAIT_DISK], 0.013);
	/* c2p and vbl add every call */
	AW_WAIT_BEGIN (t0); now += 0.008; AW_WAIT_END (AW_WAIT_C2P, t0);
	AW_WAIT_BEGIN (t0); now += 0.008; AW_WAIT_END (AW_WAIT_C2P, t0);
	AW_WAIT_BEGIN (t0); now += 0.0005; AW_WAIT_END (AW_WAIT_VBL, t0);
	expect ("c2p", aw_wait_time[AW_WAIT_C2P], 0.016);
	expect ("vbl", aw_wait_time[AW_WAIT_VBL], 0.0005);
	expect ("disk unchanged", aw_wait_time[AW_WAIT_DISK], 0.013);
	if (failures)
		return 1;
	printf ("frame wait counters ok\n");
	return 0;
}
