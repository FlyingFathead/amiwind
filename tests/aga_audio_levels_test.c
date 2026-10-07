/* SPDX-License-Identifier: GPL-2.0-or-later
 * Actual mixer + music streamer + archived cvars, synthetic PCM only. */
#define main previous_scene_voice_fixture_main
#define AW_MusicPaint unused_music_stub
#include "aga_scene_voice_test.c"
#undef AW_MusicPaint
#undef main
#include <sys/stat.h>
char com_gamedir[MAX_OSPATH]=".";
server_t sv;
double Sys_FloatTime(void){return 1;}
double realtime;
int AW_DebugOverlaysEnabled(void){return 0;}
void Cmd_AddCommand(char *name,void (*fn)(void)){}
qboolean Cmd_Exists(char *name){return false;}
int Cmd_Argc(void){return 0;}char *Cmd_Argv(int i){return "";}
void *Z_Malloc(int n){return calloc(1,n);}void Z_Free(void *p){free(p);}
void SV_BroadcastPrintf(char *fmt,...){assert(0);}
int Q_strlen(char *s){return (int)strlen(s);}
int Q_strcmp(char *a,char *b){return strcmp(a,b);}
void Q_strcpy(char *a,char *b){strcpy(a,b);}
float Q_atof(char *s){return strtof(s,NULL);}
int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
static void music_input(void){
 FILE *f;int i;byte h[16]={'M','W','A','1',43,7,32,0,0,0,32,0,0,0,0,1};
 assert(!mkdir("music",0700));f=fopen("music/playlist.txt","w");assert(f);fputs("1 0\n1 0\n",f);fclose(f);
 f=fopen("music/track00.mws","wb");assert(f);assert(fwrite(h,1,16,f)==16);
 for(i=0;i<16384;i++)fputc(i<8192?1:2,f);fclose(f);
 assert(CDAudio_Init()==0);for(i=0;i<4;i++)CDAudio_Update();
}
static void fixed_source(int id,int width,const char *name){
 channel_t *ch=source(id,2000,width,name,0);sfxcache_t *sc=samples[id].cache.data;int i;
 for(i=0;i<2000;i++)if(width==1)sc->data[i]=16;else ((short*)sc->data)[i]=4096;
 assert(ch->leftvol==128 && ch->rightvol==64);
}
static void expect(int left,int right){
 int start=paintedtime,i;S_PaintChannels(start+32);
 for(i=start;i<start+32;i++){assert(dma_samples[i*2]==left);assert(dma_samples[i*2+1]==right);}
}
int main(void){
 FILE *f;char text[512];int n,width;float nan_value;
 Cvar_RegisterVariable(&volume);Cvar_RegisterVariable(&bgmvolume);Cvar_RegisterVariable(&effectsvolume);Cvar_RegisterVariable(&dialoguevolume);
 assert(effectsvolume.archive && dialoguevolume.archive && effectsvolume.value==.75f && dialoguevolume.value==1);
 Cvar_Set("effectsvolume","-4");Cvar_Set("dialoguevolume","8");assert(effectsvolume.value==0 && dialoguevolume.value==1);
 Cvar_Set("effectsvolume","0.25");Cvar_Set("dialoguevolume","0.5");
 f=tmpfile();assert(f);Cvar_WriteVariables(f);rewind(f);n=fread(text,1,sizeof(text)-1,f);text[n]=0;fclose(f);
 assert(strstr(text,"effectsvolume \"0.25\"") && strstr(text,"dialoguevolume \"0.5\""));
 reset();music_input();SND_InitScaletable();bgmvolume.value=1;
 for(width=1;width<=2;width++){
   memset(channels,0,sizeof(channel_t)*MAX_CHANNELS);discard_sources();
   fixed_source(0,width,"env/effect.wav");fixed_source(1,width,width==1?"npc/voice.wav":"intro/voice.wav");
   effectsvolume.value=dialoguevolume.value=1;volume.value=1;expect(4608,2304);
   effectsvolume.value=0;expect(2560,1280); /* dialogue + music */
   dialoguevolume.value=0;expect(512,256); /* music alone */
   bgmvolume.value=0;expect(0,0);
   effectsvolume.value=1;expect(2048,1024); /* effects without music/dialogue */
   effectsvolume.value=0;dialoguevolume.value=1;expect(2048,1024); /* dialogue alone */
   bgmvolume.value=effectsvolume.value=1;volume.value=0;expect(0,0);
   volume.value=.5f;expect(2304,1152);volume.value=1;
   effectsvolume.value=.5f;dialoguevolume.value=.25f;expect(2048,1024);
   /* Existing spatial gains survive all edits; both muted sources advanced. */
   assert(channels[NUM_AMBIENTS].pos==288 && channels[NUM_AMBIENTS+1].pos==288);
   assert(channels[NUM_AMBIENTS].leftvol==128 && channels[NUM_AMBIENTS+1].rightvol==64);
   effectsvolume.value=-1;dialoguevolume.value=2;expect(2560,1280);
   nan_value=strtof("nan",NULL);effectsvolume.value=nan_value;dialoguevolume.value=0;expect(512,256);
   /* The copied voice retains its bus and timing through an actual handoff. */
   S_BeginSceneVoice();assert(!channels[NUM_AMBIENTS+1].sfx);discard_sources();
   memset(channels,0,sizeof(channel_t)*MAX_CHANNELS);aw_loading_music=true;
   dialoguevolume.value=1;expect(2560,1280);dialoguevolume.value=0;expect(512,256);
   dialoguevolume.value=.5f;expect(1536,768);S_CancelSceneVoice();aw_loading_music=false;
 }
 CDAudio_Shutdown();f=fopen("music-profile.txt","r");assert(f);n=fread(text,1,sizeof(text)-1,f);text[n]=0;fclose(f);
 assert(strstr(text,"track_opens=1\n") && strstr(text,"manual_changes=0\n") && strstr(text,"synchronous_fills=0\n"));
 puts("Independent buses, master, 8/16-bit PCM, muted clocks, retained voices, config persistence and no music restart passed");return 0;
}
