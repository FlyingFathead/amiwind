/* SPDX-License-Identifier: GPL-2.0-or-later
 * Actual asset readers, OST and mixer under deterministic synthetic IO delay.
 * This is a controlled disk-rate experiment, not a native performance claim. */
#include "../engine/aga/src/model.c"
#include <assert.h>
#include <sys/stat.h>
extern int sound_started,soundtime;
extern cvar_t _snd_mixahead;
client_static_t cls;client_state_t cl;
static double now;
static int slow,rate,late,max_read,asset_calls,music_calls;
static FILE *asset;
static byte data[512*1024+1];
static short pcm[32768];
void AW_TestLoadPath(void);
size_t __real_fread(void *,size_t,size_t,FILE *);
size_t __wrap_fread(void *p,size_t size,size_t n,FILE *f){
 if(slow){now+=(double)(size*n)/rate;if(f==asset){asset_calls++;if(n>max_read)max_read=n;}else music_calls++;}
 return __real_fread(p,size,n,f);
}
double Sys_FloatTime(void){return now;}
double realtime;
int SNDDMA_GetSamples(void){return (int)(now*11015);}
int SNDDMA_GetDMAPos(void){return (SNDDMA_GetSamples()*2)&32767;}
void SNDDMA_Submit(void){}
void SCR_LoadingUpdate(void){}
void AW_AudioLate(int n){late+=n;}
void AW_SpeechStop(int a,int b){}
int AW_MovieActive(void){return 0;}
int AW_MovieDebugActive(void){return 0;}
int AW_MovieDebugPending(void){return 0;}
void AW_MoviePaint(portable_samplepair_t *p,int n,int start){assert(0);}
sfxcache_t *S_LoadSound(sfx_t *s){assert(0);return NULL;}
void Con_Printf(char *fmt,...){}
int AW_DebugOverlaysEnabled(void){return 0;}
void Cmd_AddCommand(char *n,void (*fn)(void)){}
int Cmd_Argc(void){return 0;}char *Cmd_Argv(int i){return "";}
void Sys_Error(char *fmt,...){fprintf(stderr,"%s\n",fmt);abort();}
void Sys_Printf(char *fmt,...){}
int Sys_FileTime(char *path){assert(!strcmp(path,"./asset.bin"));return 1;}
int Sys_FileOpenRead(char *path,int *handle){assert(!strcmp(path,"./asset.bin"));rewind(asset);*handle=17;return sizeof(data)-1;}
void Sys_FileClose(int h){assert(h==17);}
int Sys_FileRead(int h,void *p,int n){assert(h==17);return __wrap_fread(p,1,n,asset);}
void Sys_FileSeek(int h,int n){assert(0);}
int Sys_FileOpenWrite(char *path){assert(0);return -1;}
int Sys_FileWrite(int h,void *p,int n){assert(0);return 0;}
void Sys_mkdir(char *path){assert(0);}
void *Z_Malloc(int n){assert(0);return NULL;}
void *Hunk_AllocName(int n,char *name){assert(0);return NULL;}
void *Hunk_TempAlloc(int n){assert(0);return NULL;}
void *Cache_Alloc(cache_user_t *c,int n,char *name){assert(0);return NULL;}
void Draw_BeginDisc(void){}
void Draw_EndDisc(void){}
static void input(void){
 FILE *f;int i;byte block[16384];
 byte h[16]={'M','W','A','1',43,7,32,0,0,32,0,0,0,0,1,0};
 assert(!mkdir("music",0700));f=fopen("music/playlist.txt","w");assert(f);fputs("1 0\n1 0\n",f);fclose(f);
 f=fopen("music/track00.mws","wb");assert(f);assert(fwrite(h,1,16,f)==16);
 memset(block,3,sizeof(block));for(i=0;i<256;i++)assert(fwrite(block,1,sizeof(block),f)==sizeof(block));fclose(f);
 asset=tmpfile();assert(asset);memset(data,17,sizeof(data));assert(fwrite(data,1,sizeof(data)-1,asset)==sizeof(data)-1);rewind(asset);memset(data,0,sizeof(data));
}
int main(int argc,char **argv){
 dma_t dma;int i,ordinary,expected;
 assert(argc==5);rate=atoi(argv[1]);ordinary=!strcmp(argv[3],"ordinary");expected=atoi(argv[4]);
 AW_TestLoadPath();
 memset(&dma,0,sizeof(dma));dma.channels=2;dma.samplebits=16;dma.samples=32768;dma.speed=11015;dma.buffer=(byte*)pcm;
 shm=&dma;sound_started=1;volume.value=bgmvolume.value=1;_snd_mixahead.value=.1;
 input();assert(CDAudio_Init()==0);for(i=0;i<16;i++)CDAudio_Update();
 aw_loading_music=true;aw_load_audio_tick=S_LoadingUpdate;now=1;paintedtime=soundtime=11015;S_LoadingUpdate();late=0;
 slow=1;aw_loading_music=!ordinary;
 if(!strcmp(argv[2],"model"))assert(AW_LoadRead(data,sizeof(data)-1,asset)==sizeof(data)-1);
 else {assert(COM_LoadStackFile("asset.bin",data,sizeof(data))==data);assert(data[sizeof(data)-1]==0);}
 for(i=0;i<sizeof(data)-1;i++)assert(data[i]==17);
 printf("reader=%s rate=%d bytes=%lu max_read=%d asset_calls=%d music_calls=%d missed_samples=%d elapsed=%.3f\n",argv[2],rate,(unsigned long)sizeof(data)-1,max_read,asset_calls,music_calls,late,now-1);
 assert(max_read==(ordinary?16384:expected));
 if(!ordinary && rate>=32768){if(expected==4096)assert(!late);else if(rate==32768)assert(late>40000);}
 if(ordinary)assert(!music_calls && !late);
 else for(i=0;i<32768;i++)assert(pcm[i]==768); /* Actual OST survives the load. */
 CDAudio_Shutdown();fclose(asset);return 0;
}
