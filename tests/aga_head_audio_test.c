/* Private actual-C head loader / mixer timing fixture. Synthetic assets only. */
#include "quakedef.h"
#include "aw_character.h"
#include <assert.h>
extern int sound_started,soundtime;
extern cvar_t _snd_mixahead;
client_static_t cls;client_state_t cl;
static int sample_now,refills,late,opens,read_calls,max_read,short_read,bad_header;
static int expect_sliced;
static byte asset[6+480*82];
static dma_t dma;
static short pcm[32768];
size_t __real_fread(void *,size_t,size_t,FILE *);
size_t __wrap_fread(void *ptr,size_t size,size_t n,FILE *file){
    size_t got;
    assert(size==1);read_calls++;if((int)n>max_read)max_read=n;
    /* 100 KiB/s injected media latency. It is deliberately not a claim about
     * a native disk. Feed the actual mixer the corresponding DMA progress. */
    sample_now+=(int)((n*11015+102399)/102400);
    if(short_read && n>1)n--;
    got=__real_fread(ptr,size,n,file);return got;
}
int COM_FOpenFile(char *path,FILE **file){
    int id=-1;assert(sscanf(path,"character/h%d.awh",&id)==1 && id>=0 && id<384);
    opens++;*file=tmpfile();assert(*file);
    memset(asset,0,sizeof(asset));memcpy(asset,bad_header?"BAD!":"AWH1",4);
    asset[4]=480&255;asset[5]=480>>8;
    assert(fwrite(asset,1,sizeof(asset),*file)==sizeof(asset));rewind(*file);
    return sizeof(asset);
}
int SNDDMA_GetDMAPos(void){return (sample_now*2)&32767;}
void SNDDMA_Submit(void){}
void CDAudio_Update(void){refills++;}
void AW_AudioLate(int n){late+=n;}
void AW_SpeechStop(int a,int b){}
void Q_memset(void *p,int value,int n){memset(p,value,n);}
int AW_MovieActive(void){return 0;}
int AW_MovieDebugActive(void){return 0;}
int AW_MovieDebugPending(void){return 0;}
void AW_MoviePaint(portable_samplepair_t *p,int n,int start){assert(0);}
void AW_MusicPaint(portable_samplepair_t *p,int n){int i;for(i=0;i<n;i++){p[i].left=123;p[i].right=-123;}}
sfxcache_t *S_LoadSound(sfx_t *s){assert(0);return NULL;}
void Con_Printf(char *fmt,...){}
static void reset(void){
    AW_HeadClear();opens=read_calls=max_read=refills=late=short_read=bad_header=0;
    /* Keep the hardware clock monotonic through all fixture cases. */
    soundtime=sample_now;paintedtime=sample_now;S_ExtraUpdate();late=0;
}
int main(int argc,char **argv){
    int old_opens,old_reads,old_refills;
    expect_sliced=argc>1 && !strcmp(argv[1],"sliced");
    memset(&dma,0,sizeof(dma));dma.channels=2;dma.samplebits=16;
    dma.samples=32768;dma.speed=11015;dma.buffer=(byte *)pcm;
    shm=&dma;sound_started=1;volume.value=1;_snd_mixahead.value=.1;
    reset();assert(AW_HeadLoad(0,1));S_ExtraUpdate();
    printf("case=uncached mode=%s bytes=%lu calls=%d maximum_read=%d refills=%d missed_samples=%d\n",
           expect_sliced?"sliced":"baseline",(unsigned long)sizeof(asset)*2,read_calls,max_read,refills,late);
    if(expect_sliced){assert(max_read<=4096 && !late && refills>=20);}
    else {assert(max_read==(int)sizeof(asset) && late>7000 && refills==0);}
    old_opens=opens;old_reads=read_calls;old_refills=refills;
    assert(AW_HeadLoad(0,1));assert(opens==old_opens && read_calls==old_reads && refills==old_refills);
    reset();short_read=1;assert(!AW_HeadLoad(2,3));assert(opens==1);
    short_read=0;assert(AW_HeadLoad(2,3));assert(opens==3); /* Failed slot was not cached. */
    reset();bad_header=1;assert(!AW_HeadLoad(4,5));assert(opens==1);
    bad_header=0;assert(AW_HeadLoad(4,5));assert(opens==3);
    reset();assert(!AW_HeadLoad(-1,5) && !opens && !read_calls);
    assert(!AW_HeadLoad(384,5) && !opens && !read_calls);
    return 0;
}
