/* SPDX-License-Identifier: GPL-2.0-or-later
 * The game heap for this start (aw_heapsize.c, ENGINE-HEAP-FIXED-SIZE-43).
 */
#ifndef AW_HEAPSIZE_H
#define AW_HEAPSIZE_H

#include <string.h>

#define AW_HEAP_GROW_MIN_MB		8	/* the room must hold the built heap plus this before it grows */
#define AW_HEAP_AUTO_MAX_MB		24	/* the most it grows to on its own (-heapmb goes further) */

/* MiB for this start; *grown 1 when it is larger than built_mb. */
int AW_HeapAuto (int built_mb, int asked_mb, unsigned long largest, unsigned long total, int off, int *grown);
/* 1 when config.cfg's text holds aw_autoram 0. */
int AW_HeapAutoOff (const char *config_text);

#endif
