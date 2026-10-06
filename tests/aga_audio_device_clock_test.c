/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Compile the actual Paula driver against synthetic device calls. No device
 * is opened: the clock advances independently between game polling calls. */
#include "snd_amiga.c"
#include <assert.h>
#include <stdint.h>
volatile dma_t *shm;
static double now=10000.125001,device_started;
static int device_period,starts;
static struct GfxBase gfx;
struct GfxBase *GfxBase=&gfx;
double Sys_FloatTime(void){return now;}
void Sys_Error(char *text,...){fprintf(stderr,"%s\n",text);abort();}
void Con_Printf(char *text,...){}
void AbortIO(struct IORequest *request){}
void WaitPort(struct MsgPort *port){}
void *GetMsg(struct MsgPort *port){return port;}
void BeginIO(struct IORequest *request){
    struct IOAudio *audio=(struct IOAudio*)request;
    if((uintptr_t)request->io_Unit==1){device_started=now;device_period=audio->ioa_Period;}
    assert(audio->ioa_Cycles==0 && audio->ioa_Length==16384);starts++;
}
void *AllocMem(ULONG size,int flags){return calloc(1,size);}
void FreeMem(void *p,ULONG size){free(p);}
struct MsgPort *CreateMsgPort(void){return calloc(1,sizeof(struct MsgPort));}
int OpenDevice(const char *name,int unit,struct IORequest *request,int flags){return 0;}
void CloseDevice(struct IORequest *request){}
void DeleteMsgPort(struct MsgPort *port){free(port);}
int main(void){
    static const double gaps[]={.05,.12,1.5,3,5,3600};
    int pal,i,expected;double rate,elapsed;
    for(pal=0;pal<=1;pal++){
        gfx.DisplayFlags=pal?REALLY_PAL:0;starts=0;assert(SNDDMA_Init());
        assert(starts==2 && shm->samples==32768 && SNDDMA_GetSamples()==0);
        assert(device_period==(pal?322:325));rate=(pal?3546895.0:3579545.0)/device_period;
        for(i=0;i<6;i++){
            now+=gaps[i];elapsed=(now-device_started)*rate;
            expected=(int)fmod(elapsed,1073741824.0);
            assert(SNDDMA_GetSamples()==expected);
            assert(SNDDMA_GetDMAPos()==((expected*2)&32767));
        }
        now=device_started+(1073741824.0+300)/rate;
        expected=(int)fmod((now-device_started)*rate,1073741824.0);
        assert(expected>=299 && expected<=300 && SNDDMA_GetSamples()==expected);
        assert(SNDDMA_GetDMAPos()==((expected*2)&32767));
        now=device_started-1;assert(SNDDMA_GetSamples()==0);
        now=device_started+.5;assert(SNDDMA_GetSamples()==(int)(.5*rate));
        SNDDMA_Shutdown();assert(!shm && SNDDMA_GetSamples()==0);
    }
    puts("actual driver PAL/NTSC elapsed clock, long gaps, exact rate, epoch, time reset and shutdown passed");
    return 0;
}
