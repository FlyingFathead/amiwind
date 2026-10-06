/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Synthetic audio.device declarations for the Linux source fixture only. */
#include <stdlib.h>
typedef int BOOL;
typedef unsigned char UBYTE;
typedef unsigned short UWORD;
typedef unsigned long ULONG;
#define FALSE 0
#define TRUE 1
#define MEMF_CHIP 1
#define MEMF_PUBLIC 2
#define MEMF_CLEAR 4
#define REALLY_PAL 1
#define ADIOF_PERVOL 1
#define CMD_WRITE 1
#define AUDIONAME "audio.device"
struct MsgPort{int unused;};
struct Unit{int unused;};
struct Node{int ln_Pri;};
struct Message{struct MsgPort *mn_ReplyPort;struct Node mn_Node;};
struct IORequest{struct Message io_Message;int io_Command,io_Flags;struct Unit *io_Unit;};
struct IOAudio{struct IORequest ioa_Request;void *ioa_Data;ULONG ioa_Length;UWORD ioa_Period,ioa_Volume,ioa_Cycles,ioa_AllocKey;};
struct GfxBase{int DisplayFlags;};
extern struct GfxBase *GfxBase;
void AbortIO(struct IORequest *);
void WaitPort(struct MsgPort *);
void *GetMsg(struct MsgPort *);
void BeginIO(struct IORequest *);
void *AllocMem(ULONG,int);
void FreeMem(void *,ULONG);
struct MsgPort *CreateMsgPort(void);
int OpenDevice(const char *,int,struct IORequest *,int);
void CloseDevice(struct IORequest *);
void DeleteMsgPort(struct MsgPort *);
