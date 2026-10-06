/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Real scheduling/mixing, independently advanced synthetic playback clock. */
#define main original_loading_fixture_main
#include "aga_loading_audio_test.c"
#undef main
extern int soundtime;
void S_Update_(void);
static int hardware_frames,cancellations;
int SNDDMA_GetSamples(void){return hardware_frames;}
void __real_S_CancelSceneVoice(void);
void __wrap_S_CancelSceneVoice(void){cancellations++;__real_S_CancelSceneVoice();}
static void hardware(int frames_now){hardware_frames=frames_now;position=(frames_now*2)&32767;}
int main(int argc,char **argv)
{
    dma_t dma;byte buffer[65536];sfx_t sound;int gap,was_painted,was_late,i;
    assert(argc==2);
    memset(&dma,0,sizeof dma);dma.channels=2;dma.samplebits=16;
    dma.samples=32768;dma.speed=11025;dma.buffer=buffer;
    shm=&dma;sound_started=1;volume.value=1;_snd_mixahead.value=.1;
    total_channels=0;aw_loading_music=false;hardware(0);S_Update_();
    assert(soundtime==0 && paintedtime==1102);
    if(!strcmp(argv[1],"reset") || !strcmp(argv[1],"epoch")){
        hardware(!strcmp(argv[1],"epoch")?1073739824:5000);S_Update_();
        channels[0].sfx=&sound;channels[0].end=paintedtime+100;
        memset(buffer,0x57,sizeof buffer);cancellations=0;
        /* Loading must not suppress reset clearing/cancellation. */
        aw_loading_music=true;hardware(200);S_Update_();
        assert(soundtime==200 && paintedtime==200+11025);
        assert(cancellations>0 && !channels[0].sfx);
        assert(((short*)buffer)[400]==321 && ((short*)buffer)[401]==-321);
        for(i=0;i<400;i++)assert(buffer[i]==0);
        puts("clock reset/epoch cancels old channels, clears old PCM and primes current cursor");
        return 0;
    }
    hardware(551);S_Update_();was_painted=paintedtime;was_late=late;
    gap=atoi(argv[1]);assert(gap>0 && gap<100000);
    memset(buffer,0x57,sizeof buffer);hardware(551+gap);S_Update_();
    assert(soundtime==551+gap && paintedtime==soundtime+1102);
    assert(late-was_late==(soundtime>was_painted?soundtime-was_painted:0));
    if(soundtime>=was_painted){
        assert(((short*)buffer)[position]==321 && ((short*)buffer)[(position+1)&32767]==-321);
    }
    printf("gap=%d, soundtime=%d, late=%d, current-cursor PCM repainted, mixahead=%d\n",
        gap,soundtime,late-was_late,paintedtime-soundtime);
    return 0;
}
