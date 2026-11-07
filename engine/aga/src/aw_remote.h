/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef AW_REMOTE_H
#define AW_REMOTE_H
/* Remote console for headless test sessions (aw_remote.c). */
void AW_RemoteInit(void);
void AW_RemotePoll(void);
void AW_RemoteBusy(double now);              /* long work inside a frame, modal key loops: state file only */int AW_RemoteLogging(void);
const char *AW_RemoteConsoleLog(void);
/* The console copy in console.log, collected and appended in one write at the poll, on the heartbeat, when full
 * and at exit (SESSION-STALL-AFTER-LONG-FRAME-62). */
void AW_RemoteLog(const char *msg);
void AW_RemoteLogFlush(void);
int AW_LampLitCount(void);
int AW_LampCachedCount(void);
int AW_LampDroppedCount(void);
void AW_FogLocationInit(void);
#endif
