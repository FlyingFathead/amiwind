/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "sound.h"
#include <assert.h>
viddef_t vid;int soundtime,paintedtime,sound_started,snd_blocked;keydest_t key_dest;
static int titles,music_samples,paused,begins,ends,flushes;static cvar_t *overlay;
static void (*playvid_command)(void);
static char *cmdargs[2];static int cmdargc;
void AW_MusicTitle(void){titles++;}
int Q_strcasecmp(char *a,char *b){unsigned char x,y;do{x=(unsigned char)*a++;y=(unsigned char)*b++;if(tolower(x)!=tolower(y))return (int)tolower(x)-(int)tolower(y);}while(x&&y);return 0;}
void AW_MusicPaint(portable_samplepair_t *dst,int n){int i;music_samples+=n;for(i=0;i<n;i++)dst[i].left=1234;}
void Cvar_RegisterVariable(cvar_t *c){overlay=c;c->value=atof(c->string);}
static byte card[16+768+64000];static int card_length;
static int menus;void Cbuf_AddText(char *s){assert(!strcmp(s,"aw_main_menu\n"));menus++;}
volatile dma_t *shm;static dma_t device;
cvar_t volume={"volume","1",false,false,1};
static byte file[800+128000+2205];static int length,starts,clears,pauses;static FILE *last_media_file;
double Sys_FloatTime(void){return soundtime/11025.0;}
void Con_Printf(char *s,...){
    static int finished;
    /* Production console printing can redraw immediately after the movie
     * closes. The destination must already have selected its loading style. */
    if(!strcmp(s,"Intro movie: %s.\n")){
        assert(starts+menus>finished);finished=starts+menus;
    }
}
void S_StopAllSounds(qboolean clear){clears++;}
void IN_AWClearButtons(void){}
void AW_IntroBegin(void){starts++;}
void CDAudio_Pause(void){pauses++;paused=1;}
void CDAudio_Resume(void){paused=0;}
int CDAudio_IsPaused(void){return paused;}
void S_MovieAudioBegin(void){begins++;}
void S_MovieAudioEnd(void){ends++;}
void S_ClearBuffer(void){flushes++;}
int Cmd_Argc(void){return cmdargc;}
char *Cmd_Argv(int n){return n<cmdargc?cmdargs[n]:"";}
void Cmd_AddCommand(char *name,void(*fn)(void)){if(!strcmp(name,"playvid"))playvid_command=fn;}
void Key_ClearStates(void){}
void V_UpdatePalette(void){}
int COM_FOpenFile(char *path,FILE **out){
    if(!strcmp(path,"intro/videos.awl")){
        const char *list="AWVC1\n1 mw_logo intro/video/01.awv\n";int n=(int)strlen(list);
        *out=tmpfile();assert(*out);fwrite(list,1,n,*out);rewind(*out);return n;
    }
    if(!strcmp(path,"intro/opening.awt")){
        if(!card_length){*out=NULL;return -1;}
        *out=tmpfile();assert(*out);fwrite(card,1,card_length,*out);rewind(*out);return card_length;
    }
    if(!length){*out=NULL;return -1;}
    *out=tmpfile();assert(*out);assert(fwrite(file,1,length,*out)==length);rewind(*out);last_media_file=*out;return length;
}
static void fixture(void){
    memset(file,0,sizeof(file));memcpy(file,"AWV1",4);file[5]=160;file[7]=100;file[9]=10;
    file[10]=43;file[11]=17;file[15]=2;file[18]=8;file[19]=157;
    file[32]=42;memset(file+800,3,16000);memset(file+16800,7,16000);
    memset(file+32800,64,2205);length=800+32000+2205;
}
int main(void){
    byte pixels[64002];portable_samplepair_t paint[16];int i;
    AW_MovieInit();assert(overlay && overlay->value==1 && playvid_command);
    device.speed=11025;shm=&device;soundtime=paintedtime=100;
    assert(!AW_MovieStart() && !AW_MovieActive());
    fixture();length--;assert(!AW_MovieStart());fixture();file[20]=1;assert(!AW_MovieStart());
    fixture();device.speed=8000;assert(!AW_MovieStart());device.speed=11025;
    fixture();assert(AW_MovieStart());assert(pauses==1 && AW_MoviePalette()[0]==42);
    memset(pixels,0xa5,sizeof(pixels));vid.buffer=pixels+1;vid.width=320;vid.height=200;vid.rowbytes=320;
    AW_MovieDraw();assert(pixels[0]==0xa5 && pixels[64001]==0xa5);
    for(i=1;i<64001;i++)assert(pixels[i]==3);
    memset(paint,0,sizeof(paint));AW_MoviePaint(paint,16,100);
    assert(paint[0].left==16384 && paint[15].right==16384);
    soundtime=1203;AW_MovieUpdate();AW_MovieDraw();assert(pixels[1]==7 && pixels[64000]==7);
    assert(AW_MovieKey('x',1) && AW_MovieActive());
    assert(AW_MovieKey(K_ESCAPE,0) && AW_MovieActive());
    assert(AW_MovieKey(K_ESCAPE,1) && !AW_MovieActive() && starts==1);
    assert(AW_MoviePalette()==NULL && !AW_MovieKey('x',1));
    soundtime=paintedtime=5000;assert(AW_MovieStart());soundtime=7205;AW_MovieUpdate();
    assert(starts==2 && !AW_MovieActive());
    for(i=0;i<3;i++){
        int before=clears,paused_before=pauses;
        AW_MovieStartup();assert(AW_MovieActive() && titles==0 && pauses==paused_before);
        memset(paint,0,sizeof(paint));AW_MoviePaint(paint,16,paintedtime);
        assert(paint[0].left==1234 && music_samples==(i+1)*16);
        AW_MovieKey(i==0?K_SPACE:i==1?K_ENTER:K_ESCAPE,1);
        assert(!AW_MovieActive() && clears==before+1); /* no DMA clear on menu handoff */
    }
    assert(menus==3 && starts==2);
    fixture();file[4]=1;file[5]=64;file[7]=200;
    memset(file+800,11,64000);memset(file+64800,15,64000);memset(file+128800,64,2205);length=sizeof(file);
    soundtime=paintedtime=100;assert(AW_MovieStart());AW_MovieDraw();
    assert(pixels[1]==11 && pixels[64000]==11 && pixels[0]==0xa5 && pixels[64001]==0xa5);
    soundtime=1203;AW_MovieUpdate();AW_MovieDraw();assert(pixels[1]==15 && pixels[64000]==15);
    AW_MovieKey(K_ESCAPE,1);
    memset(card,0,sizeof(card));memcpy(card,"AWT1",4);card[11]=1;card[16]=99;
    memset(card+784,23,64000);card_length=sizeof(card);
    soundtime=paintedtime=100;assert(AW_MovieStart());AW_MovieDraw();
    assert(AW_MoviePalette()[0]==99 && pixels[1]==23 && pixels[64000]==23);
    overlay->value=0;AW_MovieDraw();assert(AW_MoviePalette()[0]==42 && pixels[1]==11);
    overlay->value=1;soundtime=1203;AW_MovieUpdate();AW_MovieDraw();
    assert(AW_MoviePalette()[0]==42 && pixels[1]==15);
    AW_MovieKey(K_ESCAPE,1);card[11]=3;
    assert(AW_MovieStart());assert(AW_MoviePalette()[0]==42);AW_MovieKey(K_ESCAPE,1);
    fixture();file[4]=2;assert(!AW_MovieStart());
    /* Pending debug playback waits for queued DMA audio, then owns the mixer. */
    fixture();sound_started=1;snd_blocked=0;paused=0;soundtime=200;paintedtime=300;
    cmdargc=2;cmdargs[0]="playvid";cmdargs[1]="1";playvid_command();
    assert(AW_MovieActive() && AW_MovieDebugActive() && AW_MovieDebugPending());
    assert(!paused && begins==0 && ends==0 && AW_MoviePalette()==NULL);
    memset(pixels,0x5a,sizeof(pixels));AW_MovieDraw();assert(pixels[1]==0x5a);
    soundtime=250;AW_MovieUpdate();assert(AW_MovieDebugPending() && begins==0 && !paused);
    soundtime=paintedtime=300;AW_MovieUpdate();assert(!AW_MovieDebugPending() && begins==1 && paused && flushes==1);
    soundtime=paintedtime=500;assert(AW_MovieKey(K_ESCAPE,1) && !AW_MovieActive());
    assert(ends==1 && !paused);
    paused=1;soundtime=paintedtime=600;playvid_command();AW_MovieUpdate();
    assert(AW_MovieDebugActive() && !AW_MovieDebugPending() && paused);
    AW_MovieKey(K_ESCAPE,1);assert(!AW_MovieActive() && paused && ends==2);
    paused=0;key_dest=key_console;soundtime=paintedtime=800;playvid_command();AW_MovieUpdate();
    assert(AW_MovieDebugActive() && paused);
    soundtime=3005;AW_MovieUpdate();assert(!AW_MovieActive() && !paused && key_dest==key_console && ends==3);
    key_dest=key_console;soundtime=paintedtime=4000;playvid_command();AW_MovieUpdate();
    assert(AW_MovieDebugActive() && paused && last_media_file);
#ifndef _WIN32
    assert(freopen("/dev/null","rb",last_media_file)==last_media_file);
    AW_MoviePaint(paint,1,4000);assert(AW_MovieActive());
    AW_MovieUpdate();assert(!AW_MovieActive() && !paused && key_dest==key_console && ends==4);
#endif
    puts("movie headers, PCM, frame clock, bounds, EOF, Esc, debug command, drained start, completion/error return and music pause restore passed");return 0;
}
