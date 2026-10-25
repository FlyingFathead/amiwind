/* SPDX-License-Identifier: GPL-2.0-or-later
 * Original AmiWind MWA1 player. Four bounded PCM blocks, independent shuffled
 * groups and Previous/Next history. Owned audio remains outside the source tree.
 */
#include "quakedef.h"
#include "aw_format.h"
#include "sound.h"
#include "aw_log.h"
#include "aw_aread.h"
#define FRAMES 8192
#define BYTES (FRAMES*2)
#define HISTORY 128
#define MUSIC_BLOCKS 4
/* The stream is read asynchronously (aw_aread.c, HANG-IDLE-DUSK-35): the main
 * loop and the mixer only look for finished reads and never wait for one. */
static aw_aread_t *music;
static int header_wait;      /* the 16-byte header read is outstanding */
static double read_started;  /* Sys_FloatTime() when the outstanding read was sent */
static int read_polls;       /* looks at the outstanding read without a reply */
static int stall_logged, stall_off, stall_told;
static unsigned long stalls, recoveries, abandons, underruns;
static int bad_headers;       /* consecutive streams with a bad header */
static int death_id=-1;       /* death track, looked up once at start (no catalogue read in play) */
/* A read is stalled when it has had no reply for MUSIC_STALL_SECONDS and at
 * least MUSIC_STALL_POLLS looks (one long frame alone is not a stall). The
 * buffered blocks play out, then the music is silent; after
 * MUSIC_ABANDON_SECONDS the stream is abandoned and the next track opened. */
#define MUSIC_STALL_SECONDS 2.0
#define MUSIC_STALL_POLLS 8
#define MUSIC_ABANDON_SECONDS 6.0
#define MUSIC_ABANDON_POLLS 24
static signed char blocks[MUSIC_BLOCKS][BYTES];
static int active, at, valid[MUSIC_BLOCKS], loading, loaded;
static unsigned long remaining, total, played, reads, bytes_read, errors, opens;
static unsigned long completions, manual_changes, sync_fills;
static int current=-1, mode, paused, available;
static int title_track=-1, title_playing;
static int groups[2][100], counts[2], bags[2][100], left[2];
static int history[2][HISTORY], length[2], cursor[2]={-1,-1};
static int opened[256], opened_count;
static unsigned int rng=0x41c64e6dU;
static int fade, previous_l, previous_r;
/* music-events.csv: an in-memory diagnostic log unless aw_logs_live (aw_log.c). */
static int events;
static char opened_file[12]="none";
/* dbg music on/off (ENGINE-MUSIC-NO-OFF-SWITCH-36): the background music switch,
 * default on, not saved. Off closes the stream: an outstanding read is
 * abandoned into its reader's own packet and buffer (aw_aread.c), and no new
 * stream is opened and no read sent until it is on again. */
static cvar_t music_switch={"aw_music","1"};
static int muted;
static unsigned long be32(byte *p) { return ((unsigned long)p[0]<<24)|((unsigned long)p[1]<<16)|((unsigned long)p[2]<<8)|p[3]; }
static int random_bounded(int n) { rng=rng*1664525U+1013904223U;return (rng>>16)%n; }
static void log_event(const char *why) {
    /* Buffer diagnostic writes; synchronous flushes do not belong in the mixer. */
    if(events) AW_LogPrintf(AW_LOG_MUSIC_EVENTS,"%ld,%s,%d,%d,%s,%lu,%lu\n",(long)(Sys_FloatTime()*1000),why,mode,current,opened_file,played,total);
}
void AW_MusicSceneEvent(const char *why) {log_event(why);}
unsigned long AW_MusicSilentSpans(void) {return underruns;}
static void close_music(void) {
    /* An outstanding read is abandoned, never waited for: its reader closes
     * when the late reply arrives (AW_AReadService). */
    if(music)AW_AReadClose(music);
    music=NULL;at=0;memset(valid,0,sizeof(valid));loaded=0;loading=-1;header_wait=0;stall_logged=0;
}
static void send_read(long bytes) {
    if(!AW_AReadStart(music,bytes))return;
    read_started=Sys_FloatTime();read_polls=0;
}
/* Check the header of the opened stream; 0 = not a valid MWA1 stream. */
static int take_header(const unsigned char *h,long n) {
    unsigned long count;
    header_wait=0;
    if(n!=16 || !h || memcmp(h,"MWA1",4) || h[6]!=32 || h[7]!=0 || (((int)h[4]<<8)|h[5])!=11015)return 0;
    total=remaining=be32((byte *)h+8);count=be32((byte *)h+12);
    if(!total || count!=(total+FRAMES-1)/FRAMES)return 0;
    bad_headers=0;return 1;
}
static int open_track(int id,const char *reason) {
    char path[MAX_OSPATH+64];
    close_music();
    if(muted)return 0;
    if(id<0 || id>98 || strlen(com_gamedir)+24>=sizeof(path)){errors++;return 0;}
    /* The selected Amiga sprintf reads %d as a word: it opened track00 for
     * every small 32-bit id. Build fixed-width digits without varargs. */
    strcpy(opened_file,"track00.mws");opened_file[5]='0'+id/10;opened_file[6]='0'+id%10;
    strcpy(path,com_gamedir);strcat(path,"/music/");strcat(path,opened_file);
    music=AW_AReadOpen(path);
    if(!music){errors++;return 0;}
    /* The header comes back like every other read. When it is already there
     * (host builds, a fast disk) it is checked here, else on a later frame. */
    total=remaining=0;header_wait=1;send_read(16);
    if(AW_AReadPoll(music)!=AW_AREAD_PENDING) {
        const unsigned char *h;long n=AW_AReadTake(music,&h);
        if(!take_header(h,n)){errors++;close_music();return 0;}
    }
    current=id;played=0;opens++;active=0;
    if(opened_count<256)opened[opened_count++]=id;
    log_event(reason);
    /* Routine track notices belong to the optional debug layer. Keep the
     * event log independent and leave explicit music_status queries visible. */
    if(AW_DebugOverlaysEnabled())
        Con_Printf("OST %s: track %02ld (%s)\n",mode?"battle":"explore",(long)id,reason);
    return 1;
}
static int shuffled(void) {
    int i,j,t;
    if(!left[mode]) {
        left[mode]=counts[mode];for(i=0;i<left[mode];i++)bags[mode][i]=groups[mode][i];
        for(i=left[mode]-1;i>0;i--){j=random_bounded(i+1);t=bags[mode][i];bags[mode][i]=bags[mode][j];bags[mode][j]=t;}
        if(left[mode]>1 && bags[mode][left[mode]-1]==current){t=bags[mode][0];bags[mode][0]=current;bags[mode][left[mode]-1]=t;}
    }
    return bags[mode][--left[mode]];
}
static int advance(const char *reason) {
    int id,tries;
    if(muted)return 0;   /* off is not a failure: the music stays available */
    if(title_playing){if(open_track(title_track,reason))return 1;available=0;return 0;}
    for(tries=0;tries<counts[mode];tries++) {
        if(cursor[mode]+1<length[mode])id=history[mode][++cursor[mode]];
        else {
            id=shuffled();
            if(length[mode]==HISTORY){memmove(history[mode],history[mode]+1,(HISTORY-1)*sizeof(int));length[mode]--;}
            cursor[mode]=length[mode];history[mode][length[mode]++]=id;
        }
        if(open_track(id,reason))return 1;
    }
    available=0;return 0;
}
/* One block read (16 KiB) outstanding at a time, sent and collected without
 * waiting (aw_aread.c). No decoder on Amiga. */
static double title_due=-1; /* AW_MusicTitleAfter: realtime when the title starts, -1 none */
/* Opening hold (MUSIC-OPENING-CLIP-31): silent and flushed until the opening
 * track starts; Quake's CD-track resume on map load must not restart the
 * previous stream's buffered blocks. */
static int held;
/* Stall handling: looked at only while a read is outstanding. */
static void music_stalled(void) {
    double age=Sys_FloatTime()-read_started;
    read_polls++;
    if(!stall_logged && age>=MUSIC_STALL_SECONDS && read_polls>=MUSIC_STALL_POLLS) {
        stall_logged=1;stalls++;log_event("read-stalled");
        if(!stall_told){stall_told=1;Con_Printf("music read stalled; the game goes on without music\n");}
    }
    if(age>=MUSIC_ABANDON_SECONDS && read_polls>=MUSIC_ABANDON_POLLS) {
        /* Give the stream up; its reader keeps the request until the reply
         * comes. The next track opens on a free reader, or the music stays
         * off until an abandoned read returns (CDAudio_Update). */
        abandons++;log_event("read-abandoned");close_music();
        if(!advance("stall")){stall_off=1;available=0;log_event("stall-off");}
    }
}
/* Take a finished read, store it, and send the next one. Never waits.
 * Returns 1 when a reply was taken or a read sent (progress), 0 otherwise. */
static int music_pump(void) {
    int target,state,took=0;long n;const unsigned char *data;
    if(!music)return 0;
    state=AW_AReadPoll(music);
    if(state==AW_AREAD_PENDING){music_stalled();return 0;}
    if(state==AW_AREAD_DONE || state==AW_AREAD_FAILED) {
        took=1;n=AW_AReadTake(music,&data);
        if(stall_logged){stall_logged=0;recoveries++;log_event("read-recovered");}
        if(header_wait) {
            if(!take_header(data,n)) {
                errors++;log_event("bad-header");close_music();
                /* Bounded: a playlist of bad streams turns the music off. */
                if(++bad_headers>counts[mode]+1 || !advance("bad-header"))available=0;
                return 1;
            }
        } else {
            if(n!=BYTES || loading<0){errors++;log_event("read-error");close_music();available=0;return 1;}
            memcpy(blocks[loading],data,BYTES);
            reads++;bytes_read+=BYTES;
            valid[loading]=remaining>FRAMES?FRAMES:(int)remaining;remaining-=valid[loading];loading=-1;loaded=0;
        }
    }
    if(!remaining || loading>=0)return took;
    /* Preserve stream order while filling the first empty slot ahead of play.
     * This queue belongs only to the OST; speech/SFX and DMA timing are unchanged. */
    for(target=0;target<MUSIC_BLOCKS;target++)if(!valid[(active+target)%MUSIC_BLOCKS])break;
    if(target==MUSIC_BLOCKS)return took;
    loading=(active+target)%MUSIC_BLOCKS;loaded=0;send_read(BYTES);
    return 1;
}
/* Follows aw_music: off closes the stream (a pending read is abandoned, never
 * waited for); on starts the title or the current group again. */
static void music_apply(void) {
    int off=music_switch.value==0;
    if(off==muted)return;
    muted=off;
    if(off){close_music();log_event("music-off");return;}
    fade=128;previous_l=previous_r=0;
    if(!available || held || !advance("music-on"))log_event("music-on");
}
void CDAudio_Update(void) {
    music_apply();
    /* Late replies of abandoned streams close their files here; when the
     * last one is back after the music went off, the music comes back. */
    if(!AW_AReadService() && stall_off) {
        stall_off=0;available=1;log_event("stall-recovered");
        /* advance() reopens the title track on the title screen. */
        if(!held && !muted && !advance("stall-recovered"))available=0;
    }
    if(title_due>=0 && realtime>=title_due)AW_MusicTitle();
    if(available && !paused)music_pump();
}
void AW_MusicPaint(portable_samplepair_t *dst,int n) {
    int i,take,l,r,next,gain=(int)(bgmvolume.value*256);
    if(!available || paused || muted)return;
    while(n>0) {
        if(at>=valid[active]) {
            valid[active]=0;at=0;
            next=(active+1)%MUSIC_BLOCKS;
            if(valid[next] || loading==next)active=next;
            else if(!remaining && loading<0 && !header_wait){completions++;log_event("complete");if(!advance("eof"))return;}
            if(!valid[active]) {
                /* Take replies that are already there (bounded, never waiting);
                 * with nothing ready the music is silent for this span. */
                int k;sync_fills++;
                for(k=0;k<MUSIC_BLOCKS+2 && !valid[active] && music_pump();k++){}
                if(!valid[active]){underruns++;fade=128;previous_l=previous_r=0;return;}
            }
        }
        take=valid[active]-at;if(take>n)take=n;
        for(i=0;i<take;i++) {
            l=blocks[active][FRAMES+at+i]*gain;r=blocks[active][at+i]*gain;
            if(fade){l=(l*(128-fade)+previous_l*fade)/128;r=(r*(128-fade)+previous_r*fade)/128;fade--;}
            dst[i].left+=l;dst[i].right+=r;previous_l=l;previous_r=r;
        }
        at+=take;played+=take;dst+=take;n-=take;
    }
}
/* Explicit debug selection only: no catalogue scan or validation in the mixer.
 * AWOST1 rows: decimal-ID group(0 explore/1 battle/2 special) token-alias.
 * Generated aliases are case-insensitive filename/stem names with spaces '_'. */
static int manual_id(const char *s,int *id) {
    int n=0;if(!*s)return 0;
    while(*s){if(*s<'0'||*s>'9')return 0;n=n*10+*s++-'0';if(n>98)return 0;}
    *id=n;return 1;
}
static int manual_alias_char(int c) {
    return (c>='a'&&c<='z') || (c>='A'&&c<='Z') ||
           (c>='0'&&c<='9') || c=='_' || c=='.' || c=='-' || c=='+';
}
static int manual_lookup(const char *query,int *group) {
    FILE *f;char path[MAX_OSPATH+64],line[160],*split,*alias,*end;
    int numeric,wanted=-1,id,g,found=-1,found_group=-1;
    numeric=manual_id(query,&wanted);
    if(strlen(com_gamedir)+24>=sizeof(path))return -1;
    strcpy(path,com_gamedir);strcat(path,"/music/catalogue.txt");
    f=fopen(path,"r");if(!f)return -1;
    if(!fgets(line,sizeof(line),f)){fclose(f);return -1;}
    end=strpbrk(line,"\r\n");if(end)*end=0;
    if(strcmp(line,"AWOST1")){fclose(f);return -1;}
    while(fgets(line,sizeof(line),f)) {
        if(strlen(line)==sizeof(line)-1){fclose(f);return -1;}
        end=strpbrk(line,"\r\n");if(end)*end=0;
        split=strchr(line,' ');if(!split){fclose(f);return -1;}
        *split++=0;
        if(!manual_id(line,&id) || split[0]<'0' || split[0]>'2' || split[1]!=' ') {fclose(f);return -1;}
        g=split[0]-'0';alias=split+2;
        if(!*alias || strlen(alias)>95){fclose(f);return -1;}
        for(end=alias;*end;end++)if(!manual_alias_char(*end)){fclose(f);return -1;}
        if((numeric && id==wanted) || (!numeric && !Q_strcasecmp((char *)query,alias))) {
            if(found>=0 && (found!=id || found_group!=g)){fclose(f);return -1;}
            found=id;found_group=g;
        }
    }
    if(ferror(f)){fclose(f);return -1;}
    fclose(f);if(found>=0)*group=found_group;return found;
}
static int manual_preflight(int id) {
    FILE *f;byte h[16];char path[MAX_OSPATH+64],name[12];
    unsigned long frames,count,expected;long size;int ok;
    if(id<0 || id>98 || strlen(com_gamedir)+24>=sizeof(path))return 0;
    strcpy(name,"track00.mws");name[5]='0'+id/10;name[6]='0'+id%10;
    strcpy(path,com_gamedir);strcat(path,"/music/");strcat(path,name);
    f=fopen(path,"rb");if(!f)return 0;
    if(fread(h,1,16,f)!=16 || memcmp(h,"MWA1",4) ||
       h[6]!=32 || h[7]!=0 || (((int)h[4]<<8)|h[5])!=11015) {fclose(f);return 0;}
    frames=be32(h+8);count=be32(h+12);
    /* Bound arithmetic and signed Amiga stdio offsets before multiplication. */
    if(!frames || count!=(frames-1)/FRAMES+1 || count>(0x7fffffffUL-16)/BYTES) {fclose(f);return 0;}
    expected=16+count*BYTES;
    ok=fseek(f,0,SEEK_END)==0;size=ok?ftell(f):-1;
    fclose(f);return size>=0 && (unsigned long)size==expected;
}
static void music_play(void) {
    char query[96];const char *word;int arg,n=0,id,g,i,old_mode;
    if(Cmd_Argc()<2){Con_Printf("Usage: dbg ost play <00..98 or source_filename_stem>\n");return;}
    if(muted){Con_Printf("Background music is off (dbg music on); music unchanged.\n");return;}
    for(arg=1;arg<Cmd_Argc();arg++) {
        if(arg>1){if(n>=95)break;query[n++]='_';}
        for(word=Cmd_Argv(arg);*word;word++) {
            if(n>=95 || (!manual_alias_char(*word) && *word!=' ')) {
                Con_Printf("OST name is invalid or too long; music unchanged.\n");return;
            }
            query[n++]=*word==' '?'_':*word;
        }
    }
    if(arg<Cmd_Argc()){Con_Printf("OST name too long; music unchanged.\n");return;}
    query[n]=0;
    id=manual_lookup(query,&g);
    if(id<0){Con_Printf("OST track unknown, ambiguous or catalogue unavailable; music unchanged.\n");return;}
    if(counts[0]<1 || counts[1]<1 || !manual_preflight(id)) {
        Con_Printf("OST stream missing/invalid or playlists unavailable; music unchanged.\n");return;
    }
    /* Preflight preserves playback on ordinary missing/invalid files. The
     * existing opener reopens the file: concurrent replacement/media removal
     * between these calls is not atomic and can still stop the old stream. */
    old_mode=mode;if(g<2)mode=g;
    if(!open_track(id,"manual-play")) {
        mode=old_mode;Con_Printf("OST reopen failed after validation; stream may have changed.\n");return;
    }
    title_playing=0;available=1;paused=0;manual_changes++;fade=128;
    if(g<2) {
        /* Manual choice branches the group's Previous/Next history. Remove
         * it from the current shuffle bag without reshuffling other tracks. */
        length[mode]=cursor[mode]+1;
        if(length[mode]==HISTORY){memmove(history[mode],history[mode]+1,(HISTORY-1)*sizeof(int));length[mode]--;}
        cursor[mode]=length[mode];history[mode][length[mode]++]=id;
        for(i=0;i<left[mode];i++)if(bags[mode][i]==id) {
            memmove(bags[mode]+i,bags[mode]+i+1,(left[mode]-i-1)*sizeof(int));left[mode]--;break;
        }
    }
    /* Special is one shot, outside world history. advance() resumes the
     * existing group at EOF instead of enabling the title-loop path. */
    Con_Printf("OST manual: track %02ld (%s)\n",(long)id,g==2?"special, then world playlist":g?"battle":"explore");
}

/* Combat (aw_combat.c, docs/COMBAT.md): the battle group plays while an NPC
 * fights the player and the explore group returns when the fight ends, each
 * switch starting a fresh track of the group (the original rule as OpenMW
 * 0.51 files/data-mw/scripts/omw/music/music.lua implements it: the battle
 * playlist outranks explore while any actor has combat targets). No switch
 * during the opening hold or on the title screen. */
static unsigned long combat_switches;
void AW_MusicCombat(int on) {
    int want=on?1:0;
    if(!available || held || title_playing || counts[want]<1 || (mode==want && music))return;
    mode=want;combat_switches++;fade=128;paused=0;
    advance(want?"combat":"combat-end");
}
/* The player died: the special death track once (music.lua playerDied),
 * then the current group's shuffle at its end. */
void AW_MusicDeath(void) {
    if(!available || held || death_id<0)return;
    /* No catalogue or preflight read here: the id was looked up at start and
     * the header is checked by the stream itself (HANG-IDLE-DUSK-35). */
    if(open_track(death_id,"death")){title_playing=0;paused=0;fade=128;}
    else advance("death-fallback");
}
/* StreamMusic from a compiled script (aw_mwhost.c): that track once, as the death track plays, then the
 * current group's shuffle at its end. TRACK: the soundtrack's own number (music/trackNN.mws). */
int AW_MusicScriptTrack(int track) {
    if(!available || held || track<0 || track>98)return 0;
    if(open_track(track,"script")){title_playing=0;paused=0;fade=128;return 1;}
    advance("script-fallback");return 0;
}
static void music_next(void) {if(available && !title_playing){manual_changes++;fade=128;advance("next");}}
static void music_previous(void) {
    if(!available || title_playing)return;
    manual_changes++;fade=128;
    if(cursor[mode]>0)cursor[mode]--;
    open_track(history[mode][cursor[mode]],"previous");
}
static void music_mode(void) {if(title_playing)return;mode=!mode;if(available){manual_changes++;fade=128;advance("mode");}}
/* dbg music [on/off, true/false or 1/0]: the switch (ENGINE-MUSIC-NO-OFF-SWITCH-36);
 * no argument: the switch and the stream status. */
static void music_status(void) {
    unsigned long queued=0;int i;char *text=Cmd_Argv(1);
    if(Cmd_Argc()>2 || (Cmd_Argc()==2 && Q_strcasecmp(text,"on") && Q_strcasecmp(text,"off") &&
       Q_strcasecmp(text,"true") && Q_strcasecmp(text,"false") && strcmp(text,"1") && strcmp(text,"0"))){
        Con_Printf("Usage: dbg music [on/off, true/false or 1/0]; no argument shows the status (not saved).\n");return;}
    if(Cmd_Argc()==2)Cvar_SetValue("aw_music",(float)(!Q_strcasecmp(text,"on") || !Q_strcasecmp(text,"true") || !strcmp(text,"1")));
    music_apply();
    Con_Printf("Background music %s%s\n",muted?"off":"on",available || muted?"":" (no playable soundtrack)");
    if(Cmd_Argc()==2)return;
    for(i=0;i<MUSIC_BLOCKS;i++)queued+=(unsigned long)valid[i];
    if(queued>=(unsigned long)at)queued-=(unsigned long)at;
    Con_Printf("OST group=%s track=%02ld played=%lu/%lu frames eof=%lu reads=%lu errors=%lu\n",title_playing?"title":mode?"battle":"explore",(long)current,played,total,completions,reads,errors);
    Con_Printf("OST read-ahead: %lu blocks / %lu bytes; queued %lu frames.\n",(unsigned long)MUSIC_BLOCKS,(unsigned long)sizeof(blocks),queued);
    Con_Printf("OST combat switches: %lu\n",combat_switches);
    Con_Printf("OST read stalls: %lu, recovered %lu, abandoned %lu, silent spans %lu\n",stalls,recoveries,abandons,underruns);
}
/* Deferred title start: lets the menu finish loading before the stream reads. */
void AW_MusicTitleAfter(double seconds) {
    if(title_playing && music && current==title_track && !paused)return;
    title_due=realtime+seconds;
}
void AW_MusicTitle(void) {
    title_due=-1;held=0;
    if(!available)return;
    /* Startup branding and its destination menu share the same title stream. */
    if(title_playing && music && current==title_track && !paused)return;
    title_playing=1;
    if(muted){paused=0;return;}   /* dbg music on starts the title */
    if(title_track<0 || !open_track(title_track,"main-menu")){paused=1;return;}
    paused=0;fade=0;previous_l=previous_r=0;
}
/* A deliberate demo opening followed by the remaining exploration shuffle.
 * Keep the chosen track in Previous/Next history and out of the first bag. */
int AW_MusicStartTrack(int id) {
    int i,j,t,n=0;
    held=0;
    if(!available)return 0;
    for(i=0;i<counts[0];i++)if(groups[0][i]==id)break;
    if(i==counts[0])return 0;
    mode=0;title_playing=0;
    if(muted)return 1;   /* dbg music on plays the exploration group */
    if(current==id && played==0 && music)log_event("early_game_demo_start_1");
    else if(!open_track(id,"early_game_demo_start_1")) {
        advance("demo-track-fallback");return 0;
    }
    paused=0;fade=0;previous_l=previous_r=0;
    length[0]=1;cursor[0]=0;history[0][0]=id;
    for(i=0;i<counts[0];i++)if(groups[0][i]!=id)bags[0][n++]=groups[0][i];
    for(i=n-1;i>0;i--){j=random_bounded(i+1);t=bags[0][i];bags[0][i]=bags[0][j];bags[0][j]=t;}
    left[0]=n;
    return 1;
}
void CDAudio_Play(byte track,qboolean looping) {(void)track;(void)looping;if(!held)paused=0;}
void CDAudio_Stop(void) {paused=1;}
void CDAudio_Pause(void) {paused=1;}
void CDAudio_Resume(void) {if(!held)paused=0;}
void AW_MusicHold(void) {
    held=1;paused=1;title_due=-1;title_playing=0;close_music();log_event("hold");
}
int CDAudio_IsPaused(void) {return paused!=0;}
int CDAudio_Init(void) {
    FILE *f;char path[MAX_OSPATH+64];int g,n,i,j,id;
    /* Registered first: dbg music answers even when the disk has no soundtrack. */
    Cvar_RegisterVariable(&music_switch);Cmd_AddCommand("aw_music_status",music_status);
    sprintf(path,"%s/music/playlist.txt",com_gamedir);f=fopen(path,"r");if(!f)return -1;
    for(g=0;g<2;g++) {
        if(Q_fscanf(f,"%d",&n)!=1 || n<1 || n>99){fclose(f);return -1;}
        counts[g]=0;
        for(i=0;i<n;i++) {
            if(Q_fscanf(f,"%d",&id)!=1 || id<0 || id>98){fclose(f);return -1;}
            for(j=0;j<counts[g];j++)if(groups[g][j]==id)break;
            if(j==counts[g])groups[g][counts[g]++]=id;
        }
    }
    /* Optional third line: converter-resolved canonical title track. Old
     * two-line playlists retain world playback without assuming track 00. */
    title_track=-1;title_playing=0;
    if(Q_fscanf(f,"%d",&id)==1 && id>=0 && id<=98)title_track=id;
    fclose(f);available=1;paused=0;mode=0;loading=-1;
    {int group;death_id=manual_lookup("mw_death",&group);}
    rng^=(unsigned int)(Sys_FloatTime()*1000000.0);
    AW_LogHeader(AW_LOG_MUSIC_EVENTS,"time_ms,event,mode,track,file,played_frames,total_frames\n");events=1;
    Cmd_AddCommand("aw_music_play",music_play);
    Cmd_AddCommand("aw_music_next",music_next);Cmd_AddCommand("aw_music_previous",music_previous);
    Cmd_AddCommand("aw_music_mode",music_mode);
    /* With a title track, stay silent until the main menu starts it: the startup
     * logo is silent, and a random world track must not play under it
     * (MUSIC-STARTUP-TRACK-31). Old playlists without one start the world shuffle. */
    if(title_track>=0){paused=1;return 0;}
    return advance("start")?0:-1;
}
void CDAudio_Shutdown(void) {
    int i;log_event("shutdown");close_music();AW_AReadShutdown();if(events){AW_LogStreamClose(AW_LOG_MUSIC_EVENTS);events=0;}
    AW_LogBegin(AW_LOG_MUSIC_PROFILE);
    AW_LogPrintf(AW_LOG_MUSIC_PROFILE,"read_slices=%lu\nbytes_read=%lu\nread_errors=%lu\ntrack_opens=%lu\nlast_track=%d\nnatural_completions=%lu\nmanual_changes=%lu\nsynchronous_fills=%lu\n",reads,bytes_read,errors,opens,current,completions,manual_changes,sync_fills);
    AW_LogPrintf(AW_LOG_MUSIC_PROFILE,"read_stalls=%lu\nread_recoveries=%lu\nread_abandons=%lu\nsilent_spans=%lu\n",stalls,recoveries,abandons,underruns);
    AW_LogPrintf(AW_LOG_MUSIC_PROFILE,"buffer_blocks=%lu\nbuffer_bytes=%lu\n",(unsigned long)MUSIC_BLOCKS,(unsigned long)sizeof(blocks));
    AW_LogWrite(AW_LOG_MUSIC_PROFILE,"track_history=");
    for(i=0;i<opened_count;i++)AW_LogPrintf(AW_LOG_MUSIC_PROFILE,"%s%d",i?",":"",opened[i]);
    AW_LogWrite(AW_LOG_MUSIC_PROFILE,"\n");
    AW_LogEnd(AW_LOG_MUSIC_PROFILE);
}
