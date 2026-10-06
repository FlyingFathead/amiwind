/*
Copyright (C) 1996-1997 Id Software, Inc.

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.

*/
// snd_mix.c -- portable code to mix sounds for snd_dma.c

#include "quakedef.h"

#ifdef AMIGA
#include <proto/exec.h>
#include <exec/memory.h>
#endif

#ifdef _WIN32
#include "winquake.h"
#else
#define DWORD	unsigned long
#endif

#define	PAINTBUFFER_SIZE	512
portable_samplepair_t paintbuffer[PAINTBUFFER_SIZE];
int		snd_scaletable[32][256];
int	*snd_p, snd_linear_count, snd_vol;
short	*snd_out;

void Snd_WriteLinearBlastStereo16 (void);

#if	!id386
void Snd_WriteLinearBlastStereo16 (void)
{
	int		i;
	int		val;

	for (i=0 ; i<snd_linear_count ; i+=2)
	{
		val = (snd_p[i]*snd_vol)>>8;
		if (val > 0x7fff)
			snd_out[i] = 0x7fff;
		else if (val < (short)0x8000)
			snd_out[i] = (short)0x8000;
		else
			snd_out[i] = val;

		val = (snd_p[i+1]*snd_vol)>>8;
		if (val > 0x7fff)
			snd_out[i+1] = 0x7fff;
		else if (val < (short)0x8000)
			snd_out[i+1] = (short)0x8000;
		else
			snd_out[i+1] = val;
	}
}
#endif

void S_TransferStereo16 (int endtime)
{
	int		lpos;
	int		lpaintedtime;
	DWORD	*pbuf;
#ifdef _WIN32
	int		reps;
	DWORD	dwSize,dwSize2;
	DWORD	*pbuf2;
	HRESULT	hresult;
#endif

	snd_vol = volume.value*256;

	snd_p = (int *) paintbuffer;
	lpaintedtime = paintedtime;

#ifdef _WIN32
	if (pDSBuf)
	{
		reps = 0;

		while ((hresult = pDSBuf->lpVtbl->Lock(pDSBuf, 0, gSndBufSize, &pbuf, &dwSize,
									   &pbuf2, &dwSize2, 0)) != DS_OK)
		{
			if (hresult != DSERR_BUFFERLOST)
			{
				Con_Printf ("S_TransferStereo16: DS::Lock Sound Buffer Failed\n");
				S_Shutdown ();
				S_Startup ();
				return;
			}

			if (++reps > 10000)
			{
				Con_Printf ("S_TransferStereo16: DS: couldn't restore buffer\n");
				S_Shutdown ();
				S_Startup ();
				return;
			}
		}
	}
	else
#endif
	{
		pbuf = (DWORD *)shm->buffer;
	}

	while (lpaintedtime < endtime)
	{
	// handle recirculating buffer issues
		lpos = lpaintedtime & ((shm->samples>>1)-1);

		snd_out = (short *) pbuf + (lpos<<1);

		snd_linear_count = (shm->samples>>1) - lpos;
		if (lpaintedtime + snd_linear_count > endtime)
			snd_linear_count = endtime - lpaintedtime;

		snd_linear_count <<= 1;

	// write a linear blast of samples
		Snd_WriteLinearBlastStereo16 ();

		snd_p += snd_linear_count;
		lpaintedtime += (snd_linear_count>>1);
	}

#ifdef _WIN32
	if (pDSBuf)
		pDSBuf->lpVtbl->Unlock(pDSBuf, pbuf, dwSize, NULL, 0);
#endif
}

void S_TransferPaintBuffer(int endtime)
{
	int	out_idx;
	int	count;
	int	out_mask;
	int	*p;
	int	step;
	int		val;
	int		snd_vol;

#ifdef AMIGA
	int	offset;
	extern	int using_ahi;

	if (using_ahi) { /* using AHI, two 16-bit channels */

		short *out;
		int val2;

		out = (short *)shm->buffer;
		p = (int *) paintbuffer;
		count = endtime - paintedtime;
		out_mask = shm->samples - 1;
		out_idx = (paintedtime << 1) & out_mask;
		snd_vol = volume.value * 256;
		while (count--) {

			val = (*p++ * snd_vol) >> 8;
			if (val > 32767)
				val = 32767;
			else if (val < -32768)
				val = -32768;

			val2 = (*p++ * snd_vol) >> 8;
			if (val2 > 32767)
				val2 = 32767;
			else if (val2 < -32768)
				val2 = -32768;

			*(int *)&out[out_idx] = (val << 16) | val2;

			out_idx = (out_idx + 2) & out_mask;

		}

	} else {	/* using audio.device, two 8-bit channels */

#define NEXTVAL                               \
		val = (*p++ * snd_vol) >> 16; \
		if (val > 127)                \
			val = 127;            \
		else if (val < -128)          \
			val = -128

		p = (int *) paintbuffer;
		count = endtime - paintedtime;
		offset = shm->samples >> 1;
		out_mask = offset - 1;
		out_idx = paintedtime & out_mask;
		snd_vol = volume.value * 256;
		{
			unsigned char *out = (unsigned char *)shm->buffer;
			int lval1, lval2;
			while ((out_idx & 3) != 0 && count > 0)
			{
				NEXTVAL;
				out[out_idx] = val;

				NEXTVAL;
				out[out_idx + offset] = val;

				out_idx = (out_idx + 1) & out_mask;
				count--;
			}
			while (count >= 4)
			{
				NEXTVAL;
				lval1 = val;
				NEXTVAL;
				lval2 = val;
				NEXTVAL;
				lval1 = (lval1 << 8) | (val & 255);
				NEXTVAL;
				lval2 = (lval2 << 8) | (val & 255);
				NEXTVAL;
				lval1 = (lval1 << 8) | (val & 255);
				NEXTVAL;
				lval2 = (lval2 << 8) | (val & 255);
				NEXTVAL;
				lval1 = (lval1 << 8) | (val & 255);
				NEXTVAL;
				lval2 = (lval2 << 8) | (val & 255);

				*(int *)(&out[out_idx]) = lval1;
				*(int *)(&out[out_idx + offset]) = lval2;

				out_idx = (out_idx + 4) & out_mask;

				count -= 4;
			}
			while (count > 0)
			{
				NEXTVAL;
				out[out_idx] = val;

				NEXTVAL;
				out[out_idx + offset] = val;

				out_idx = (out_idx + 1) & out_mask;
				count--;
			}
		}
	}
#else
	DWORD	*pbuf;
#ifdef _WIN32
	int		reps;
	DWORD	dwSize,dwSize2;
	DWORD	*pbuf2;
	HRESULT	hresult;
#endif

	if (shm->samplebits == 16 && shm->channels == 2)
	{
		S_TransferStereo16 (endtime);
		return;
	}

	p = (int *) paintbuffer;
	count = (endtime - paintedtime) * shm->channels;
	out_mask = shm->samples - 1;
	out_idx = paintedtime * shm->channels & out_mask;
	step = 3 - shm->channels;
	snd_vol = volume.value*256;

#ifdef _WIN32
	if (pDSBuf)
	{
		reps = 0;

		while ((hresult = pDSBuf->lpVtbl->Lock(pDSBuf, 0, gSndBufSize, &pbuf, &dwSize,
									   &pbuf2,&dwSize2, 0)) != DS_OK)
		{
			if (hresult != DSERR_BUFFERLOST)
			{
				Con_Printf ("S_TransferPaintBuffer: DS::Lock Sound Buffer Failed\n");
				S_Shutdown ();
				S_Startup ();
				return;
			}

			if (++reps > 10000)
			{
				Con_Printf ("S_TransferPaintBuffer: DS: couldn't restore buffer\n");
				S_Shutdown ();
				S_Startup ();
				return;
			}
		}
	}
	else
#endif
	{
		pbuf = (DWORD *)shm->buffer;
	}

	if (shm->samplebits == 16)
	{
		short *out = (short *) pbuf;
		while (count--)
		{
			val = (*p * snd_vol) >> 8;
			p+= step;
			if (val > 0x7fff)
				val = 0x7fff;
			else if (val < (short)0x8000)
				val = (short)0x8000;
			out[out_idx] = val;
			out_idx = (out_idx + 1) & out_mask;
		}
	}
	else if (shm->samplebits == 8)
	{
		unsigned char *out = (unsigned char *) pbuf;
		while (count--)
		{
			val = (*p * snd_vol) >> 8;
			p+= step;
			if (val > 0x7fff)
				val = 0x7fff;
			else if (val < (short)0x8000)
				val = (short)0x8000;
			out[out_idx] = (val>>8) + 128;
			out_idx = (out_idx + 1) & out_mask;
		}
	}

#ifdef _WIN32
	if (pDSBuf) {
		DWORD dwNewpos, dwWrite;
		int il = paintedtime;
		int ir = endtime - paintedtime;

		ir += il;

		pDSBuf->lpVtbl->Unlock(pDSBuf, pbuf, dwSize, NULL, 0);

		pDSBuf->lpVtbl->GetCurrentPosition(pDSBuf, &dwNewpos, &dwWrite);

//		if ((dwNewpos >= il) && (dwNewpos <= ir))
//			Con_Printf("%d-%d p %d c\n", il, ir, dwNewpos);
	}
#endif
#endif
}


/*
===============================================================================

CHANNEL MIXING

===============================================================================
*/

void SND_PaintChannelFrom8 (channel_t *ch, sfxcache_t *sc, int endtime);
void SND_PaintChannelFrom16 (channel_t *ch, sfxcache_t *sc, int endtime);

static int dialogue_sound(const sfx_t *sfx)
{
    return sfx && (!strncmp(sfx->name,"npc/",4) || !strncmp(sfx->name,"intro/",6));
}
static void paint_channel_gain(channel_t *ch,sfxcache_t *sc,int count,float gain)
{
    channel_t mixed=*ch;
    if(!(gain>=0))gain=0;
    if(gain>1)gain=1;
    mixed.leftvol=(int)(mixed.leftvol*gain);
    mixed.rightvol=(int)(mixed.rightvol*gain);
    if(sc->width==1)SND_PaintChannelFrom8(&mixed,sc,count);
    else SND_PaintChannelFrom16(&mixed,sc,count);
    /* Keep the source's spatial gain and advance muted channels normally.
     * Changing a bus level never restarts a sound or accumulates attenuation. */
    ch->pos=mixed.pos;
}

/* A scene handoff owns a copy of the unpainted part of speech. The ordinary
 * cache, sfx and entity arrays can all disappear while the loader runs.
 * At most four allocations, including their sample headers, total 128 KiB.
 * Keep already queued DMA samples and gains; never restart or re-spatialize
 * the detached voice using a new map's entity numbers. */
#define SCENE_VOICE_SLOTS 4
#define SCENE_VOICE_BYTES (128 * 1024)
typedef struct {
    sfxcache_t *sample;
    channel_t channel;
    int next, end, speed;
    unsigned bytes;
} scene_voice_t;
static scene_voice_t scene_voices[SCENE_VOICE_SLOTS];
static unsigned scene_voice_bytes,scene_voice_peak,scene_voice_rejected;
static int scene_voice_handoff;
static int movie_audio_paused,movie_audio_painted_start,movie_audio_sound_start;
extern int sound_started,soundtime;

/* The target SDK malloc can trap before returning NULL. These short-lived
 * copies must fail normally and must never fall back to hardware Chip RAM. */
static void *scene_voice_alloc(unsigned bytes)
{
#ifdef AMIGA
    return AllocMem((ULONG)bytes,MEMF_FAST|MEMF_PUBLIC);
#else
    return malloc(bytes);
#endif
}
static void scene_voice_free(void *sample,unsigned bytes)
{
#ifdef AMIGA
    FreeMem(sample,(ULONG)bytes);
#else
    (void)bytes;
    free(sample);
#endif
}
static void scene_voice_release(scene_voice_t *v)
{
    if(v->sample){scene_voice_free(v->sample,v->bytes);scene_voice_bytes-=v->bytes;}
    v->sample=NULL;v->bytes=0;
}
void S_MovieAudioBegin(void)
{
    if(movie_audio_paused)return;
    movie_audio_paused=1;movie_audio_painted_start=paintedtime;movie_audio_sound_start=soundtime;
}
void S_MovieAudioEnd(void)
{
    int i,painted_elapsed,sound_elapsed;
    channel_t *ch;scene_voice_t *v;
    if(!movie_audio_paused)return;
    painted_elapsed=paintedtime-movie_audio_painted_start;
    sound_elapsed=soundtime-movie_audio_sound_start;
    if(painted_elapsed<0)painted_elapsed=0;
    if(sound_elapsed<0)sound_elapsed=0;
    for(i=0,ch=channels;i<total_channels;i++,ch++)
        if(ch->sfx && ch->end>movie_audio_painted_start)ch->end+=painted_elapsed;
    for(i=0;i<SCENE_VOICE_SLOTS;i++){
        v=&scene_voices[i];if(!v->sample)continue;
        v->next+=painted_elapsed;v->end+=sound_elapsed;
    }
    AW_SpeechShiftTiming(sound_elapsed,movie_audio_sound_start);
    movie_audio_paused=0;
}
void S_CancelSceneVoice(void)
{
    int i;
    for(i=0;i<SCENE_VOICE_SLOTS;i++)scene_voice_release(&scene_voices[i]);
    memset(scene_voices,0,sizeof(scene_voices));scene_voice_handoff=0;
}
int S_PreserveSceneVoice(void)
{
    return scene_voice_handoff && aw_loading_music;
}
void S_EndSceneVoice(void)
{
    scene_voice_handoff=0;
}
double S_SceneVoiceRemaining(void)
{
    int i;double remaining=0,d;
    for(i=0;i<SCENE_VOICE_SLOTS;i++){
        scene_voice_t *v=&scene_voices[i];
        if(v->end>soundtime && v->speed>0){
            d=(double)(v->end-soundtime)/v->speed;
            if(d>remaining)remaining=d;
        }
    }
    return remaining;
}
void S_SceneVoiceReport(void)
{
    int i,n=0;
    for(i=0;i<SCENE_VOICE_SLOTS;i++)if(scene_voices[i].end>soundtime)n++;
    Con_Printf("Scene voices: %d tails, %lu/%lu owned bytes, peak %lu, refused %lu, handoff %d\n",
        n,(unsigned long)scene_voice_bytes,(unsigned long)SCENE_VOICE_BYTES,
        (unsigned long)scene_voice_peak,(unsigned long)scene_voice_rejected,scene_voice_handoff);
}
void S_BeginSceneVoice(void)
{
    int i,j,remaining;unsigned bytes;channel_t *ch;sfxcache_t *sc;
    scene_voice_t *v;const char *reason;
    if(!sound_started || !shm || shm->speed<=0){S_CancelSceneVoice();return;}
    scene_voice_handoff=1;
    for(i=0;i<SCENE_VOICE_SLOTS;i++)if(scene_voices[i].end<=soundtime){
        scene_voice_release(&scene_voices[i]);memset(&scene_voices[i],0,sizeof(scene_voices[i]));
    }
    for(i=NUM_AMBIENTS;i<NUM_AMBIENTS+MAX_DYNAMIC_CHANNELS;i++){
        ch=&channels[i];
        if(!dialogue_sound(ch->sfx))continue;
        if(ch->end<=paintedtime || (!ch->leftvol && !ch->rightvol))continue;
        reason="unavailable or unsupported cached sample";
        /* No S_LoadSound: loading here could evict another live cache entry. */
        sc=Cache_Check(&ch->sfx->cache);
        if(!sc || sc->loopstart!=-1 || sc->stereo || sc->speed!=shm->speed ||
           (sc->width!=1 && sc->width!=2) || ch->pos<0 || ch->pos>=sc->length ||
           ch->leftvol<0 || ch->rightvol<0 || ch->leftvol>65535 || ch->rightvol>65535)goto refused;
        remaining=sc->length-ch->pos;
        /* Both clocks must describe the same nonlooping, already-playing tail. */
        if(ch->end-paintedtime!=remaining)goto refused;
        reason="128 KiB total tail budget exceeded";
        if(remaining>(SCENE_VOICE_BYTES-(int)sizeof(*sc))/sc->width)goto refused;
        bytes=sizeof(*sc)+(unsigned)remaining*sc->width;
        if(bytes>SCENE_VOICE_BYTES-scene_voice_bytes)goto refused;
        reason="four detached voice slots occupied";
        for(j=0;j<SCENE_VOICE_SLOTS;j++)if(!scene_voices[j].end)break;
        if(j==SCENE_VOICE_SLOTS)goto refused;
        v=&scene_voices[j];reason="tail allocation failed";
        v->sample=(sfxcache_t *)scene_voice_alloc(bytes);if(!v->sample)goto refused;
        memcpy(v->sample,sc,sizeof(*sc));v->sample->length=remaining;
        memcpy(v->sample->data,sc->data+(size_t)ch->pos*sc->width,(size_t)remaining*sc->width);
        memset(&v->channel,0,sizeof(v->channel));
        v->channel.leftvol=ch->leftvol;v->channel.rightvol=ch->rightvol;
        v->next=paintedtime;v->end=ch->end;v->speed=sc->speed;v->bytes=bytes;
        scene_voice_bytes+=bytes;if(scene_voice_bytes>scene_voice_peak)scene_voice_peak=scene_voice_bytes;
        AW_SpeechStop(ch->entnum,ch->entchannel);
        ch->sfx=NULL; /* Ownership moves exactly once, including repeated crossings. */
        continue;
refused:
        scene_voice_rejected++;
        Con_Printf("Scene voice not retained (%s): %s\n",reason,ch->sfx->name);
    }
}
static void S_PaintSceneVoice(int start,int end)
{
    int i,count,skip;scene_voice_t *v;
    for(i=0;i<SCENE_VOICE_SLOTS;i++){
        v=&scene_voices[i];if(!v->sample)continue;
        if(!shm || v->speed!=shm->speed || start<v->next){
            scene_voice_release(v);v->end=0;continue;
        }
        /* A DMA underrun advances the audio clock; don't replay missed samples. */
        skip=start-v->next;
        count=v->sample->length-v->channel.pos;
        if(skip>=count){scene_voice_release(v);continue;}
        v->channel.pos+=skip;
        count=v->sample->length-v->channel.pos;
        if(count>end-start)count=end-start;
        paint_channel_gain(&v->channel,v->sample,count,dialoguevolume.value);
        v->next=end;
        if(v->channel.pos==v->sample->length)scene_voice_release(v);
    }
}


void S_PaintChannels(int endtime)
{
	int	i;
	int	end;
    int debug_movie;
	channel_t *ch;
	sfxcache_t	*sc;
	int		ltime, count;

	debug_movie=AW_MovieDebugActive();
	while (paintedtime < endtime)
	{
	// if paintbuffer is smaller than DMA buffer
		end = endtime;
		if (endtime - paintedtime > PAINTBUFFER_SIZE)
			end = paintedtime + PAINTBUFFER_SIZE;

	// clear the paint buffer
		Q_memset(paintbuffer, 0, (end - paintedtime) * sizeof(portable_samplepair_t));

	if(AW_MovieActive())AW_MoviePaint(paintbuffer,end-paintedtime,paintedtime);
    else if(!debug_movie)AW_MusicPaint(paintbuffer, end-paintedtime);
    if(!debug_movie)S_PaintSceneVoice(paintedtime,end);

	// paint in the channels.
		ch = channels;
		for (i=0; !debug_movie && !aw_loading_music && i<total_channels ; i++, ch++)
		{
			if (!ch->sfx)
				continue;
			if (!ch->leftvol && !ch->rightvol)
				continue;
			sc = S_LoadSound (ch->sfx);
			if (!sc)
				continue;

			ltime = paintedtime;

			while (ltime < end)
			{	// paint up to end
				if (ch->end < end)
					count = ch->end - ltime;
				else
					count = end - ltime;

				if (count > 0)
				{
                    paint_channel_gain(ch,sc,count,dialogue_sound(ch->sfx)?dialoguevolume.value:effectsvolume.value);

					ltime += count;
				}

			// if at end of loop, restart
				if (ltime >= ch->end)
				{
					if (sc->loopstart >= 0)
					{
						ch->pos = sc->loopstart;
						ch->end = ltime + sc->length - ch->pos;
					}
					else
					{	// channel just stopped
						ch->sfx = NULL;
						break;
					}
				}
			}

		}

	// transfer out according to DMA format
		S_TransferPaintBuffer(end);
		paintedtime = end;
	}
}

void SND_InitScaletable (void)
{
	int		i, j;

	for (i=0 ; i<32 ; i++)
		for (j=0 ; j<256 ; j++)
			snd_scaletable[i][j] = ((signed char)j) * i * 8;
}


#if	!id386

void SND_PaintChannelFrom8 (channel_t *ch, sfxcache_t *sc, int count)
{
	int	data;
	int		*lscale, *rscale;
	unsigned char *sfx;
	int		i;

	if (ch->leftvol > 255)
		ch->leftvol = 255;
	if (ch->rightvol > 255)
		ch->rightvol = 255;

	lscale = snd_scaletable[ch->leftvol >> 3];
	rscale = snd_scaletable[ch->rightvol >> 3];
	sfx = (signed char *)sc->data + ch->pos;

	for (i=0 ; i<count ; i++)
	{
		data = sfx[i];
		paintbuffer[i].left += lscale[data];
		paintbuffer[i].right += rscale[data];
	}

	ch->pos += count;
}

#endif	// !id386


void SND_PaintChannelFrom16 (channel_t *ch, sfxcache_t *sc, int count)
{
	int data;
	int left, right;
	int leftvol, rightvol;
	signed short *sfx;
	int	i;

	leftvol = ch->leftvol;
	rightvol = ch->rightvol;
	sfx = (signed short *)sc->data + ch->pos;

	for (i=0 ; i<count ; i++)
	{
		data = sfx[i];
		left = (data * leftvol) >> 8;
		right = (data * rightvol) >> 8;
		paintbuffer[i].left += left;
		paintbuffer[i].right += right;
	}

	ch->pos += count;
}
