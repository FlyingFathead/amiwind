/* SPDX-License-Identifier: GPL-2.0-or-later
 * Original AmiWind MWA1 player. Four bounded PCM blocks, independent shuffled
 * groups and Previous/Next history. Owned audio remains outside the source tree.
 */
#include "quakedef.h"
#include "aw_format.h"
#include "sound.h"
#include "aw_log.h"
#define FRAMES 8192
#define BYTES (FRAMES*2)
#define HISTORY 128
#define MUSIC_BLOCKS 4
static FILE *music;
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
static unsigned long be32(byte *p) { return ((unsigned long)p[0]<<24)|((unsigned long)p[1]<<16)|((unsigned long)p[2]<<8)|p[3]; }
static int random_bounded(int n) { rng=rng*1664525U+1013904223U;return (rng>>16)%n; }
static void log_event(const char *why) {
    /* Buffer diagnostic writes; synchronous flushes do not belong in the mixer. */
    if(events) AW_LogPrintf(AW_LOG_MUSIC_EVENTS,"%ld,%s,%d,%d,%s,%lu,%lu\n",(long)(Sys_FloatTime()*1000),why,mode,current,opened_file,played,total);
}
void AW_MusicSceneEvent(const char *why) {log_event(why);}
static void close_music(void) {
    if(music)fclose(music);
    music=NULL;at=0;memset(valid,0,sizeof(valid));loaded=0;loading=-1;
}
static int open_track(int id,const char *reason) {
    byte h[16];char path[MAX_OSPATH+64];unsigned long count;
    close_music();
    if(id<0 || id>98 || strlen(com_gamedir)+24>=sizeof(path)){errors++;return 0;}
    /* The selected Amiga sprintf reads %d as a word: it opened track00 for
     * every small 32-bit id. Build fixed-width digits without varargs. */
    strcpy(opened_file,"track00.mws");opened_file[5]='0'+id/10;opened_file[6]='0'+id%10;
    strcpy(path,com_gamedir);strcat(path,"/music/");strcat(path,opened_file);
    music=fopen(path,"rb");
    if(!music){errors++;return 0;}
    if(fread(h,1,16,music)!=16 || memcmp(h,"MWA1",4) || h[6]!=32 || h[7]!=0 || (((int)h[4]<<8)|h[5])!=11015) {errors++;close_music();return 0;}
    total=remaining=be32(h+8);count=be32(h+12);
    if(!total || count!=(total+FRAMES-1)/FRAMES){errors++;close_music();return 0;}
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
/* One 4 KiB read per service call. No heap allocation and no decoder on Amiga. */
static double title_due=-1; /* AW_MusicTitleAfter: realtime when the title starts, -1 none */
/* Opening hold (MUSIC-OPENING-CLIP-31): silent and flushed until the opening
 * track starts; Quake's CD-track resume on map load must not restart the
 * previous stream's buffered blocks. */
static int held;
static int refill(void) {
    int target,take,i;
    if(!music || !remaining)return 0;
    /* Preserve stream order while filling the first empty slot ahead of play.
     * This queue belongs only to the OST; speech/SFX and DMA timing are unchanged. */
    for(i=0;i<MUSIC_BLOCKS;i++){
        target=(active+i)%MUSIC_BLOCKS;
        if(!valid[target])break;
    }
    if(i==MUSIC_BLOCKS)return 0;
    if(loading<0){loading=target;loaded=0;}
    take=BYTES-loaded;if(take>4096)take=4096;
    if(fread(blocks[loading]+loaded,1,take,music)!=(size_t)take){errors++;log_event("read-error");close_music();available=0;return 0;}
    reads++;bytes_read+=take;loaded+=take;
    if(loaded==BYTES){valid[loading]=remaining>FRAMES?FRAMES:(int)remaining;remaining-=valid[loading];loading=-1;loaded=0;}
    return 1;
}
void CDAudio_Update(void) {
    if(title_due>=0 && realtime>=title_due)AW_MusicTitle();
    if(available && !paused)refill();
}
void AW_MusicPaint(portable_samplepair_t *dst,int n) {
    int i,take,l,r,next,gain=(int)(bgmvolume.value*256);
    if(!available || paused)return;
    while(n>0) {
        if(at>=valid[active]) {
            valid[active]=0;at=0;
            next=(active+1)%MUSIC_BLOCKS;
            if(valid[next] || loading==next)active=next;
            else if(!remaining && loading<0){completions++;log_event("complete");if(!advance("eof"))return;}
            if(!valid[active]) {sync_fills++;while(!valid[active] && refill()){}if(!valid[active])return;}
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
    int g,id;
    if(!available || held)return;
    id=manual_lookup("mw_death",&g);
    if(id<0 || !manual_preflight(id))return;
    if(open_track(id,"death")){title_playing=0;paused=0;fade=128;}
}
static void music_next(void) {if(available && !title_playing){manual_changes++;fade=128;advance("next");}}
static void music_previous(void) {
    if(!available || title_playing)return;
    manual_changes++;fade=128;
    if(cursor[mode]>0)cursor[mode]--;
    open_track(history[mode][cursor[mode]],"previous");
}
static void music_mode(void) {if(title_playing)return;mode=!mode;if(available){manual_changes++;fade=128;advance("mode");}}
static void music_status(void) {
    unsigned long queued=0;int i;
    for(i=0;i<MUSIC_BLOCKS;i++)queued+=(unsigned long)valid[i];
    if(queued>=(unsigned long)at)queued-=(unsigned long)at;
    Con_Printf("OST group=%s track=%02ld played=%lu/%lu frames eof=%lu reads=%lu errors=%lu\n",title_playing?"title":mode?"battle":"explore",(long)current,played,total,completions,reads,errors);
    Con_Printf("OST read-ahead: %lu blocks / %lu bytes; queued %lu frames.\n",(unsigned long)MUSIC_BLOCKS,(unsigned long)sizeof(blocks),queued);
    Con_Printf("OST combat switches: %lu\n",combat_switches);
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
    rng^=(unsigned int)(Sys_FloatTime()*1000000.0);
    AW_LogHeader(AW_LOG_MUSIC_EVENTS,"time_ms,event,mode,track,file,played_frames,total_frames\n");events=1;
    Cmd_AddCommand("aw_music_play",music_play);
    Cmd_AddCommand("aw_music_next",music_next);Cmd_AddCommand("aw_music_previous",music_previous);
    Cmd_AddCommand("aw_music_mode",music_mode);Cmd_AddCommand("aw_music_status",music_status);
    /* With a title track, stay silent until the main menu starts it: the startup
     * logo is silent, and a random world track must not play under it
     * (MUSIC-STARTUP-TRACK-31). Old playlists without one start the world shuffle. */
    if(title_track>=0){paused=1;return 0;}
    return advance("start")?0:-1;
}
void CDAudio_Shutdown(void) {
    int i;log_event("shutdown");close_music();if(events){AW_LogStreamClose(AW_LOG_MUSIC_EVENTS);events=0;}
    AW_LogBegin(AW_LOG_MUSIC_PROFILE);
    AW_LogPrintf(AW_LOG_MUSIC_PROFILE,"read_slices=%lu\nbytes_read=%lu\nread_errors=%lu\ntrack_opens=%lu\nlast_track=%d\nnatural_completions=%lu\nmanual_changes=%lu\nsynchronous_fills=%lu\n",reads,bytes_read,errors,opens,current,completions,manual_changes,sync_fills);
    AW_LogPrintf(AW_LOG_MUSIC_PROFILE,"buffer_blocks=%lu\nbuffer_bytes=%lu\n",(unsigned long)MUSIC_BLOCKS,(unsigned long)sizeof(blocks));
    AW_LogWrite(AW_LOG_MUSIC_PROFILE,"track_history=");
    for(i=0;i<opened_count;i++)AW_LogPrintf(AW_LOG_MUSIC_PROFILE,"%s%d",i?",":"",opened[i]);
    AW_LogWrite(AW_LOG_MUSIC_PROFILE,"\n");
    AW_LogEnd(AW_LOG_MUSIC_PROFILE);
}
