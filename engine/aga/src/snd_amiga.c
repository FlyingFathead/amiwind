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
// snd_null.c -- include this instead of all the other snd_* files to have
// no sound code whatsoever

#include "quakedef.h"

#include <proto/exec.h>
#include <proto/graphics.h>
#include <graphics/gfxbase.h>

#include <devices/audio.h>


static double real_speed;

static struct MsgPort *audio_mp = NULL;
static struct IOAudio *audio_io = NULL;
static BOOL audio_is_open = FALSE;
static UWORD period;



struct channel_info {
  struct MsgPort *audio_mp;
  struct IOAudio *audio_io;
  double starttime;
  BOOL sound_in_progress;
};

// max number of Amiga sound channels
static struct channel_info channel_info[4] = {
  {NULL, NULL, 0.0, FALSE},
  {NULL, NULL, 0.0, FALSE},
  {NULL, NULL, 0.0, FALSE},
  {NULL, NULL, 0.0, FALSE},
};

//8192 /4 = 2048 @ 11025
static ULONG sampleCount = 0;

// Quake 1 default sample quality is 11025.
#define AMIGA_SOUND_FREQUENCY   11025


/**********************************************************************/
// Stops an audio.device sound channel.

static void stopsound (int cnum)
{
  if (!audio_is_open)
    return;

  if (channel_info[cnum].sound_in_progress) {
    AbortIO ((struct IORequest *)channel_info[cnum].audio_io);
    WaitPort (channel_info[cnum].audio_mp);
    GetMsg (channel_info[cnum].audio_mp);
    channel_info[cnum].sound_in_progress = FALSE;
  }
}

/**********************************************************************/
// Starts an audio.device sound in a particular sound channel.

static int startsound (int cnum, char *buffer, int length)
{
  struct channel_info *c;

  if (!audio_is_open)
    return 1;

  stopsound (cnum);
  c = &channel_info[cnum];
  c->audio_io->ioa_Request.io_Command = CMD_WRITE;
  c->audio_io->ioa_Request.io_Flags = ADIOF_PERVOL;
  c->audio_io->ioa_Data = buffer;
  c->audio_io->ioa_Length = length;
  c->audio_io->ioa_Period = period;
  c->audio_io->ioa_Volume = 64;
  c->audio_io->ioa_Cycles = 0;
  BeginIO ((struct IORequest *)c->audio_io);
  c->starttime = Sys_FloatTime();
  c->sound_in_progress = TRUE;

  return cnum;
}






/*
==================
SNDDM_Init

Try to find a sound device to mix for.
Returns false if nothing is found.
Returns true and fills in the "shm" structure with information for the mixer.
==================
*/
qboolean SNDDMA_Init(void)
{
  int i;
  struct channel_info *c;
  UBYTE chans[1];
  ULONG clock_constant;


    if ((shm = (dma_t *)malloc (sizeof(dma_t))) == NULL) {
        Sys_Error ("Could not allocate enough memory for sound structure");
    }

    memset((void*)shm, 0, sizeof(dma_t));

    // Determine the sample buffer size. We want it to store enough data for
    // at least 1/16th of a second (though at most 8192 samples). Note
    // that it must be a power of two. So e.g. at 22050 Hz, we request a
    // sample buffer size of 2048.
    sampleCount = 8192;
    while ((sampleCount * 16) > (AMIGA_SOUND_FREQUENCY * 2)) {
        sampleCount >>= 1;
    }

    sampleCount = sampleCount * 32; /* 32 KiB stereo DMA ring. */

    if ((shm->buffer = AllocMem (sampleCount, MEMF_CHIP | MEMF_CLEAR)) == NULL) {
        Sys_Error ("Could not allocate enough CHIP memory for the sound buffer");
    }

    shm->channels = 2;
    shm->speed = AMIGA_SOUND_FREQUENCY;
    shm->samplebits = 8;
    shm->samples = sampleCount / (shm->samplebits / 8);
    shm->submission_chunk = 1;

    if ((audio_mp = CreateMsgPort()) == NULL) {
        Sys_Error ("Native CreateMsgPort() failed");
    }

    if ((audio_io = (struct IOAudio *)AllocMem(sizeof(struct IOAudio), MEMF_PUBLIC | MEMF_CLEAR)) == NULL) {
        Sys_Error ("Could not allocate enough memory for the IOAudio");
    }

    chans[0] = (1 << shm->channels) - 1; /* shm->channels Amiga audio channels */
    audio_io->ioa_Request.io_Message.mn_ReplyPort = audio_mp;
    audio_io->ioa_Request.io_Message.mn_Node.ln_Pri = 127;
    audio_io->ioa_AllocKey = 0;
    audio_io->ioa_Data = chans;
    audio_io->ioa_Length = sizeof(chans);

    if (OpenDevice (AUDIONAME, 0, (struct IORequest *)audio_io, 0) != 0) {
        Sys_Error("OpenDevice(\"audio.device\") failed");
    }

    audio_is_open = TRUE;

    for (i = 0; i < shm->channels; i++) {
        c = &channel_info[i];
        if ((c->audio_mp = CreateMsgPort ()) == NULL ||
          (c->audio_io = (struct IOAudio *)AllocMem(sizeof(struct IOAudio),
                                             MEMF_PUBLIC | MEMF_CLEAR)) == NULL) {
            Sys_Error ("CreateMsgPort() or AllocMem() failed");
        }

        *c->audio_io = *audio_io;
        c->audio_io->ioa_Request.io_Message.mn_ReplyPort = c->audio_mp;
        c->audio_io->ioa_Request.io_Unit = (struct Unit *)(1 << i);
    }

    if ((GfxBase->DisplayFlags & REALLY_PAL) == 0)
      clock_constant = 3579545;   /* NTSC */
    else
      clock_constant = 3546895;   /* PAL */

    period = ((clock_constant << 1) + shm->speed) / ((shm->speed) << 1);

    real_speed = (double)clock_constant / period;

    startsound (0, shm->buffer, sampleCount >> 1);
    startsound (1, shm->buffer + (sampleCount >> 1), sampleCount >> 1);

    Con_Printf ("Using Native 8 bit Stereo Audio\n");

    return true;
}

/* The audio device keeps looping while the game is busy. Derive an absolute
 * sample-pair clock from the same EClock estimate used by this driver, not
 * from how many ring wraps the mixer happened to observe. The rare epoch
 * rollover is a multiple of the ring length and fits signed mixer counters. */
int SNDDMA_GetSamples(void) {
    double frames;
    if (!shm || !shm->buffer || !channel_info[0].sound_in_progress)
        return 0;
    frames = (Sys_FloatTime() - channel_info[0].starttime) * real_speed;
    if (!(frames >= 0) || !isfinite(frames))
        return 0;
    if (frames >= 1073741824.0)
        frames = fmod(frames,1073741824.0);
    return (int)frames;
}

int SNDDMA_GetDMAPos(void) {

    if (shm == NULL || shm->buffer == NULL) {
        return 0;
    }


    shm->samplepos = (SNDDMA_GetSamples() * shm->channels) & (sampleCount - 1);


    return shm->samplepos;
}

void SNDDMA_Shutdown(void) {

    int i;



    if (audio_is_open) {
        if (shm != NULL) {
          for (i = 0; i < shm->channels; i++)
            stopsound (i);

          audio_io->ioa_Request.io_Unit = (struct Unit *)((1 << shm->channels) - 1);
        }

        CloseDevice ((struct IORequest *)audio_io);
        audio_is_open = FALSE;
    }

    for (i = 0; i < 4; i++) {
        if (channel_info[i].audio_io != NULL) {
          FreeMem (channel_info[i].audio_io, sizeof(struct IOAudio));
          channel_info[i].audio_io = NULL;
        }

        if (channel_info[i].audio_mp != NULL) {
          DeleteMsgPort (channel_info[i].audio_mp);
          channel_info[i].audio_mp = NULL;
        }
    }

    if (audio_io != NULL) {
        FreeMem (audio_io, sizeof(struct IOAudio));
        audio_io = NULL;
    }

    if (audio_mp != NULL) {
        DeleteMsgPort (audio_mp);
        audio_mp = NULL;
    }

    if (shm != NULL) {
        if (shm->buffer != NULL) {
            FreeMem (shm->buffer, sampleCount);

        shm->buffer = NULL;
    }

    free ((char *)shm);
    shm = NULL;
  }
}

// GCC build compatibility: AHI not supported in NovaCoder's simplified version
int using_ahi = FALSE;

void SNDDMA_Submit (void)
{
    // NovaCoder's version doesn't need explicit submit - audio handled in startsound
}
