/* SPDX-License-Identifier: GPL-2.0-or-later
 * Quick test builds (tools/build.py --exclude): the marker id1/excluded-content.txt
 * (aw_excluded.c) and the missing-movie paths of aw_movie.c. A complete build has
 * no marker and keeps every old message; a quick test build prints one friendly
 * line and goes straight on (New Game starts the ship, no black wait).
 */
#include "quakedef.h"
#include "sound.h"
#include <assert.h>
viddef_t vid;int soundtime,paintedtime,sound_started,snd_blocked;keydest_t key_dest;
volatile dma_t *shm;static dma_t device;
cvar_t volume={"volume","1",false,false,1};
static void (*playvid_command)(void);
static char *cmdargs[2];static int cmdargc;
static const char *marker;          /* excluded-content.txt contents, NULL: absent */
static int marker_opens,starts,menus;
static char printed[16][160];static int lines;
void AW_MusicTitle(void){}
void AW_MusicPaint(portable_samplepair_t *dst,int n){(void)dst;(void)n;}
int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
void Cvar_RegisterVariable(cvar_t *c){c->value=atof(c->string);}
void Cbuf_AddText(char *s){assert(!strcmp(s,"aw_main_menu\n"));menus++;}
double Sys_FloatTime(void){return 0;}
void Con_Printf(char *s,...){
    va_list ap;assert(lines<16);
    va_start(ap,s);vsnprintf(printed[lines++],sizeof(printed[0]),s,ap);va_end(ap);
}
void S_StopAllSounds(qboolean clear){(void)clear;}
void IN_AWClearButtons(void){}
void AW_IntroBegin(void){starts++;}
void CDAudio_Pause(void){}
void CDAudio_Resume(void){}
int CDAudio_IsPaused(void){return 0;}
void S_MovieAudioBegin(void){}
void S_MovieAudioEnd(void){}
void S_ClearBuffer(void){}
int Cmd_Argc(void){return cmdargc;}
char *Cmd_Argv(int n){return n<cmdargc?cmdargs[n]:"";}
void Cmd_AddCommand(char *name,void(*fn)(void)){if(!strcmp(name,"playvid"))playvid_command=fn;}
void Key_ClearStates(void){}
void V_UpdatePalette(void){}
/* No video file exists at all: the build left them out (or never had them). */
int COM_FOpenFile(char *path,FILE **out){
    int n;
    *out=NULL;
    if(!strcmp(path,"excluded-content.txt")){
        marker_opens++;
        if(!marker)return -1;
        n=(int)strlen(marker);*out=tmpfile();assert(*out);
        fwrite(marker,1,n,*out);rewind(*out);return n;
    }
    return -1;
}
static void clear(void){lines=0;memset(printed,0,sizeof(printed));}
static int said(const char *text){int i;for(i=0;i<lines;i++)if(!strcmp(printed[i],text))return 1;return 0;}
static void use_marker(const char *text){marker=text;AW_ExcludedReset();marker_opens=0;}
#define MOVIES "This build was made without the intro movies (quick test build).\n"

int main(void){
    AW_MovieInit();assert(playvid_command);
    device.speed=11025;shm=&device;

    /* Complete build: no marker, nothing excluded, the old messages, no startup line. */
    use_marker(NULL);clear();
    assert(!AW_ContentExcluded("video") && !AW_ContentExcludedNotice("video"));
    assert(!AW_ContentExcludedSay("music",0) && lines==0);
    assert(!AW_MovieStart() && starts==0);
    assert(said("Video not found; skipping optional movie.\n") && !said(MOVIES));
    clear();AW_MovieStartup();assert(lines==1 && said("Video not found; skipping optional movie.\n") && menus==1);
    clear();cmdargc=2;cmdargs[0]="playvid";cmdargs[1]="1";playvid_command();
    assert(lines==1 && said("Video is absent or the optional catalogue is invalid.\n"));
    assert(marker_opens==1); /* the file is looked for once, then remembered */

    /* Quick test build without videos, music and interiors. */
    use_marker("AWX1\nvideo the intro movies\nmusic the music\ninteriors the interiors\n");clear();
    AW_MovieStartup();
    assert(said("Quick test build, made without the intro movies, the music and the interiors.\n"));
    assert(said("Video not found; skipping optional movie.\n")); /* the logo is never excluded */
    assert(menus==2 && lines==2);
    assert(AW_ContentExcluded("video") && AW_ContentExcluded("music") && AW_ContentExcluded("interiors"));
    assert(!AW_ContentExcluded("voice") && !AW_ContentExcluded("vid") && !AW_ContentExcluded(""));
    assert(!strcmp(AW_ContentExcludedNotice("music"),"the music"));
    /* New Game: no movie -> one friendly line, straight on to the ship (no repair message). */
    clear();assert(!AW_MovieStart());
    assert(lines==1 && said(MOVIES));
    clear();assert(!AW_MovieStart() && lines==0); /* once per session for automatic events */
    /* An explicit playvid says it every time. */
    clear();playvid_command();assert(lines==1 && said(MOVIES));
    clear();playvid_command();assert(lines==1 && said(MOVIES));
    /* Music: one line the first time the game notices, then silence. */
    clear();assert(AW_ContentExcludedSay("music",0) && said("This build was made without the music (quick test build).\n"));
    clear();assert(AW_ContentExcludedSay("music",0) && lines==0);
    assert(marker_opens==1);

    /* Voice only: the startup line names it; videos keep the old message. */
    use_marker("AWX1\nvoice the recorded dialogue voices\n");clear();
    AW_ContentExcludedStartup();assert(lines==1 && said("Quick test build, made without the recorded dialogue voices.\n"));
    clear();assert(!AW_MovieStart() && said("Video not found; skipping optional movie.\n"));

    /* Invalid markers are not trusted: wrong magic, upper case, missing newline, control bytes, empty notice. */
    {
        static const char *bad[]={"AWX2\nvideo the intro movies\n","AWX1\nVideo the intro movies\n",
            "AWX1\nvideo the intro movies","AWX1\nvideo the\tintro\n","AWX1\nvideo \n","AWX1\nvideo\n",
            "AWX1\nvideo the intro movies\nmusic\n","AWX1\nthis-group-name-is-far-too-long-for-the-table x\n"};
        int i;
        for(i=0;i<(int)(sizeof(bad)/sizeof(bad[0]));i++){
            use_marker(bad[i]);clear();
            assert(!AW_ContentExcluded("video") && !AW_ContentExcluded("music"));
            AW_ContentExcludedStartup();assert(lines==0);
        }
    }
    puts("quick test build marker, startup line, missing movie, playvid, once-per-group notice and invalid markers passed");
    return 0;
}
