/* SPDX-License-Identifier: GPL-2.0-or-later
 * Host oracle: generated samples only. Included player is the runtime source.
 */
#include "aw_music.c"
#include <assert.h>
int main(int argc,char **argv) {
    portable_samplepair_t sample;
    unsigned long position=0, old_total=0, offset;
    int track=-1, j, k, loops=0;
    FILE *check;
    byte *raw=NULL;
    long size;
    char path[1200];
    assert(argc==3);strcpy(com_gamedir,argv[1]);
    if(!strcmp(argv[2],"invalid")) {assert(CDAudio_Init()==-1);return 0;}
    assert(CDAudio_Init()==0);rng=42;
    if(!strcmp(argv[2],"demo-missing")) {
        assert(!AW_MusicStartTrack(4));assert(available && music && current!=4);
        CDAudio_Shutdown();return 0;
    }
    if(!strcmp(argv[2],"demo")) {
        assert(AW_MusicStartTrack(4));assert(current==4 && mode==0 && !paused && played==0);
        assert(length[0]==1 && cursor[0]==0 && history[0][0]==4);
        assert(left[0]==counts[0]-1);
        for(j=0;j<left[0];j++)assert(bags[0][j]!=4);
        assert(!AW_MusicStartTrack(98));assert(current==4);
    }
    if(!strcmp(argv[2],"truncated")) {
        memset(&sample,0,sizeof(sample));AW_MusicPaint(&sample,1);
        assert(errors==1 && !available && !music);
        assert(sample.left==0 && sample.right==0);CDAudio_Shutdown();return 0;
    }
    while(completions<18) {
        for(k=0;k<3;k++)CDAudio_Update();
        for(k=0;k<997;k++) {
            memset(&sample,0,sizeof(sample));AW_MusicPaint(&sample,1);
            if(track!=current) {
                if(raw) {assert(position==old_total);free(raw);}
                track=current;old_total=total;position=0;
                sprintf(path,"%s/music/track%02d.mws",com_gamedir,track);
                check=fopen(path,"rb");assert(check);fseek(check,0,SEEK_END);
                size=ftell(check);rewind(check);raw=malloc(size);assert(raw);
                assert(fread(raw,1,size,check)==(size_t)size);fclose(check);
            }
            offset=position/8192*16384+16+position%8192;
            assert(sample.left==((signed char)raw[offset+8192])*256);
            assert(sample.right==((signed char)raw[offset])*256);
            position++;assert(position==played);
        }
        assert(++loops<100000);
    }
    assert(errors==0 && manual_changes==0);
    for(j=1;j<opened_count;j++)assert(opened[j]!=opened[j-1]);
    {int a=current,b;music_next();b=current;music_previous();assert(current==a);music_next();assert(current==b);}
    music_mode();assert(mode==1);
    for(j=0;j<30;j++){int old=current;music_next();assert(current!=old);}
    music_mode();assert(mode==0);
    if(!strcmp(argv[2],"demo")) {
        music_mode();assert(mode==1);CDAudio_Pause();
        assert(AW_MusicStartTrack(4));assert(current==4 && mode==0 && !paused);
    }
    assert(reads*4096==bytes_read);
    CDAudio_Shutdown();free(raw);return 0;
}
