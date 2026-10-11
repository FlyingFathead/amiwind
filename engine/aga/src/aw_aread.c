/* SPDX-License-Identifier: GPL-2.0-or-later
 * Asynchronous sequential file reads (aw_aread.h, HANG-IDLE-DUSK-35).
 *
 * AmigaOS: the standard packet-level pattern (the one asyncio.library uses):
 * Open() the file, then send ACTION_READ packets to the handler port in the
 * file handle (fh_Type, argument fh_Arg1) with SendPkt() and our own reply
 * port, and collect each reply with GetMsg() on a later frame. Nothing here
 * ever waits on a reply except AW_AReadShutdown(), which waits a bounded time.
 * A request whose reply does not come back keeps its packet, port and buffer
 * (the handler may still write into the buffer); the reader is abandoned and
 * closed only when the reply arrives.
 */
#include "aw_aread.h"
#include <string.h>

#ifdef AMIGA
#include <proto/exec.h>
#include <exec/memory.h>
#include <exec/ports.h>
#include <proto/dos.h>
#include <dos/dos.h>
#include <dos/dosextens.h>
#else
#include <stdio.h>
#include <stdlib.h>
int aw_aread_hold;
#endif

struct aw_aread_s {
    int used, abandoned, state;
    long result;
    unsigned char *buffer;
#ifdef AMIGA
    BPTR file;
    struct MsgPort *port;
    /* AllocDosObject(DOS_STDPKT) returns the DosPacket part of a StandardPacket
     * (dp_Link already points at its Message), not the StandardPacket itself
     * (CHIM-DEV3-MAPLOAD-CRASH-36). */
    struct DosPacket *packet;
#else
    FILE *file;
#endif
};
static struct aw_aread_s readers[AW_AREAD_MAX];

static int prepare(struct aw_aread_s *r) {
#ifdef AMIGA
    if(!r->buffer)r->buffer=(unsigned char *)AllocMem(AW_AREAD_BUFFER,MEMF_PUBLIC);
    if(!r->port)r->port=CreateMsgPort();
    if(!r->packet)r->packet=(struct DosPacket *)AllocDosObject(DOS_STDPKT,NULL);
    return r->buffer && r->port && r->packet;
#else
    if(!r->buffer)r->buffer=(unsigned char *)malloc(AW_AREAD_BUFFER);
    return r->buffer!=NULL;
#endif
}
static void close_file(struct aw_aread_s *r) {
#ifdef AMIGA
    if(r->file)Close(r->file);
    r->file=0;
#else
    if(r->file)fclose(r->file);
    r->file=NULL;
#endif
    r->used=r->abandoned=0;r->state=AW_AREAD_IDLE;r->result=0;
}
aw_aread_t *AW_AReadOpen(const char *path) {
    struct aw_aread_s *r=NULL;int i;
    for(i=0;i<AW_AREAD_MAX;i++)if(!readers[i].used){r=&readers[i];break;}
    if(!r || !prepare(r))return NULL;
#ifdef AMIGA
    r->file=Open((STRPTR)path,MODE_OLDFILE);
    if(!r->file)return NULL;
    /* NIL: and similar handles have no handler to send packets to. */
    if(!((struct FileHandle *)BADDR(r->file))->fh_Type){Close(r->file);r->file=0;return NULL;}
#else
    r->file=fopen(path,"rb");
    if(!r->file)return NULL;
#endif
    r->used=1;r->abandoned=0;r->state=AW_AREAD_IDLE;r->result=0;
    return r;
}
int AW_AReadStart(aw_aread_t *r,long length) {
#ifdef AMIGA
    struct FileHandle *fh;struct DosPacket *dp;
#endif
    if(!r || !r->used || r->abandoned || r->state!=AW_AREAD_IDLE || length<1 || length>AW_AREAD_BUFFER)return 0;
#ifdef AMIGA
    fh=(struct FileHandle *)BADDR(r->file);dp=r->packet;
    dp->dp_Type=ACTION_READ;dp->dp_Arg1=fh->fh_Arg1;dp->dp_Arg2=(LONG)r->buffer;dp->dp_Arg3=length;
    dp->dp_Res1=dp->dp_Res2=0;
    SendPkt(dp,fh->fh_Type,r->port);
#else
    r->result=(long)fread(r->buffer,1,(size_t)length,r->file);
    if(r->result!=length && ferror(r->file))r->result=-1;
#endif
    r->state=AW_AREAD_PENDING;
    return 1;
}
int AW_AReadPoll(aw_aread_t *r) {
    if(!r || !r->used)return AW_AREAD_IDLE;
    if(r->state!=AW_AREAD_PENDING)return r->state;
#ifdef AMIGA
    if(!GetMsg(r->port))return AW_AREAD_PENDING;
    r->result=r->packet->dp_Res1;
#else
    if(aw_aread_hold)return AW_AREAD_PENDING;
#endif
    r->state=r->result<0?AW_AREAD_FAILED:AW_AREAD_DONE;
    return r->state;
}
long AW_AReadTake(aw_aread_t *r,const unsigned char **data) {
    long n;
    if(data)*data=NULL;
    if(!r || (r->state!=AW_AREAD_DONE && r->state!=AW_AREAD_FAILED))return -1;
    n=r->result;r->state=AW_AREAD_IDLE;r->result=0;
    if(data && n>0)*data=r->buffer;
    return n;
}
void AW_AReadClose(aw_aread_t *r) {
    if(!r || !r->used)return;
    if(AW_AReadPoll(r)==AW_AREAD_PENDING){r->abandoned=1;return;}
    close_file(r);
}
int AW_AReadService(void) {
    int i,waiting=0;
    for(i=0;i<AW_AREAD_MAX;i++) {
        if(!readers[i].used || !readers[i].abandoned)continue;
        if(AW_AReadPoll(&readers[i])==AW_AREAD_PENDING)waiting++;
        else close_file(&readers[i]);
    }
    return waiting;
}
void AW_AReadShutdown(void) {
    int i,tries;
    for(i=0;i<AW_AREAD_MAX;i++) {
        struct aw_aread_s *r=&readers[i];
        if(!r->used){
#ifdef AMIGA
            if(r->buffer)FreeMem(r->buffer,AW_AREAD_BUFFER);
            if(r->port)DeleteMsgPort(r->port);
            if(r->packet)FreeDosObject(DOS_STDPKT,r->packet);
            r->port=NULL;r->packet=NULL;
#else
            free(r->buffer);
#endif
            r->buffer=NULL;continue;
        }
#ifdef AMIGA
        /* Up to one second for a late reply; then the handler keeps the
         * request: the port ignores its arrival and nothing it can still
         * write to is ever freed (deliberately left allocated). */
        for(tries=0;tries<50 && AW_AReadPoll(r)==AW_AREAD_PENDING;tries++)Delay(1);
        if(r->state==AW_AREAD_PENDING){r->port->mp_Flags=PA_IGNORE;continue;}
#else
        (void)tries;
        if(r->state==AW_AREAD_PENDING)continue;
#endif
        close_file(r);
#ifdef AMIGA
        FreeMem(r->buffer,AW_AREAD_BUFFER);DeleteMsgPort(r->port);FreeDosObject(DOS_STDPKT,r->packet);
        r->port=NULL;r->packet=NULL;
#else
        free(r->buffer);
#endif
        r->buffer=NULL;
    }
}
