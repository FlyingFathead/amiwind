/* SPDX-License-Identifier: GPL-2.0-or-later
 * Asynchronous sequential file reads for streams the main loop must never
 * wait on (HANG-IDLE-DUSK-35). On AmigaOS a read is one ACTION_READ packet
 * sent to the file's handler with the reader's own reply port and collected
 * later with GetMsg(), never with WaitPort()/WaitPkt(): a reply that comes
 * late, or never, cannot stop the game. Host builds (tests) read at once.
 */
#ifndef AW_AREAD_H
#define AW_AREAD_H

/* One request reads at most this many bytes into the reader's own buffer. */
#define AW_AREAD_BUFFER 16384
/* Readers in the pool: one live stream plus readers whose request was
 * abandoned and whose reply has not come back yet (their buffer, packet and
 * reply port stay owned by the handler until it does). */
#define AW_AREAD_MAX 3

#define AW_AREAD_IDLE 0     /* no request outstanding */
#define AW_AREAD_PENDING 1  /* request sent, no reply yet */
#define AW_AREAD_DONE 2     /* reply arrived, data waiting in the buffer */
#define AW_AREAD_FAILED 3   /* reply arrived with an error */

typedef struct aw_aread_s aw_aread_t;

/* Open a file for sequential asynchronous reads (the open itself is a normal
 * DOS call). NULL when the file is missing or every reader is in use. */
aw_aread_t *AW_AReadOpen(const char *path);
/* Send one read of length bytes (1..AW_AREAD_BUFFER) from the current file
 * position. 0 when the reader is busy or the length is out of range. */
int AW_AReadStart(aw_aread_t *r,long length);
/* Look for the reply without waiting; returns the reader state. */
int AW_AReadPoll(aw_aread_t *r);
/* After AW_AREAD_DONE/AW_AREAD_FAILED: the byte count (negative on error)
 * and the data; the reader is idle again. */
long AW_AReadTake(aw_aread_t *r,const unsigned char **data);
/* Close a reader. With a request outstanding the reader is abandoned instead:
 * its file is closed when the reply finally arrives (AW_AReadService). */
void AW_AReadClose(aw_aread_t *r);
/* Collect late replies of abandoned readers; returns how many still wait. */
int AW_AReadService(void);
/* Program exit: wait a bounded time for outstanding replies, then leave the
 * remaining ones to the handler (their memory is never freed under it). */
void AW_AReadShutdown(void);

#ifndef AMIGA
/* Host test control: while set, finished reads stay AW_AREAD_PENDING (a reply
 * that is late or never comes). */
extern int aw_aread_hold;
#endif

#endif
