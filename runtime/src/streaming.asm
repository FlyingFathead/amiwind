; Kickstart 1.3 DOS reads + queued audio.device writes. No MP3 decoding.
; Three stereo buffers, each 8192 signed-byte samples per side (48 KiB total).
        section code,code
STREAM_FRAMES equ 8192
STREAM_BYTES equ 16384
AUDIO_SIZE equ 68
PAIR_SIZE equ 136

system_open:
        move.l  4.w,a6
        lea     dos_name,a1
        moveq   #0,d0
        jsr     -552(a6)
        move.l  d0,stream_dos
        beq     .failed
        moveq   #-1,d0
        jsr     -330(a6)            ; AllocSignal, available on 1.3
        move.b  d0,stream_signal
        bmi     .failed
        lea     stream_port,a2
        move.b  #4,8(a2)            ; NT_MSGPORT, PA_SIGNAL
        move.b  d0,15(a2)
        suba.l  a1,a1
        jsr     -294(a6)            ; FindTask(NULL)
        move.l  d0,16(a2)
        lea     24(a2),a0
        move.l  a0,20(a2)           ; NewList
        clr.l   24(a2)
        lea     20(a2),a0
        move.l  a0,28(a2)
        lea     disk_port,a0
        move.b  #4,8(a0)
        move.b  stream_signal,15(a0)
        move.l  16(a2),16(a0)
        lea     24(a0),a1
        move.l  a1,20(a0)
        lea     20(a0),a1
        move.l  a1,28(a0)
        lea     audio_master,a1
        move.l  a2,14(a1)
        move.w  #AUDIO_SIZE,18(a1)
        move.b  #127,9(a1)          ; Allocate all four channels, no stealing
        move.b  #$41,30(a1)         ; QUICK | NOWAIT
        move.l  #audio_mask,34(a1)
        move.l  #1,38(a1)
        lea     audio_name,a0
        moveq   #0,d0
        moveq   #0,d1
        jsr     -444(a6)            ; OpenDevice
        tst.l   d0
        bne     .failed
        move.w  #1,audio_open
        lea     input_request,a1
        move.l  #stream_port,14(a1)
        move.w  #48,18(a1)
        lea     input_name,a0
        moveq   #0,d0
        moveq   #0,d1
        jsr     -444(a6)
        tst.l   d0
        bne     .failed
        move.w  #1,input_open
        lea     input_request,a1
        move.w  #9,28(a1)           ; IND_ADDHANDLER
        move.l  #input_handler,40(a1)
        jsr     -456(a6)
        tst.b   input_request+31
        bne     .failed
        move.w  #1,input_installed
        moveq   #1,d0
        rts
.failed:
        moveq   #0,d0
        rts

; Input device acknowledges the keyboard. Consume only keys/mouse while active;
; disk/timer events continue to their normal handlers. a0=list, returns d0=list.
input_events:
        movem.l d1-d2/a0-a2,-(sp)
        move.l  a0,d0
        tst.w   input_active
        beq.s   .done
        move.l  a0,a2
.next:
        tst.l   d0
        beq.s   .return
        cmp.b   #1,4(a0)            ; IECLASS_RAWKEY
        bne.s   .mouse
        moveq   #0,d1
        move.w  6(a0),d1
        cmp.w   #$ff,d1
        bhi.s   .advance
        moveq   #1,d2
        btst    #7,d1
        beq.s   .down
        moveq   #0,d2
.down:
        and.w   #$7f,d1
        lea     keys,a1
        move.b  d2,0(a1,d1.w)
        clr.b   4(a0)              ; IECLASS_NULL: don't type into the CLI
        bra.s   .advance
.mouse:
        cmp.b   #2,4(a0)
        bne.s   .advance
        clr.b   4(a0)              ; Mouse hardware counters read by renderer
.advance:
        move.l  (a0),a0
        move.l  a0,d0
        bra.s   .next
.return:
        move.l  a2,d0
.done:
        movem.l (sp)+,d1-d2/a0-a2
        rts

; d7 = slot. All file reads happen in task context with interrupts enabled.
stream_fill:
        movem.l d2-d6/a2-a4/a6,-(sp)
        bsr     read_ticks
        move.l  d0,d6
        tst.l   stream_blocks
        bne.s   .read
        bsr     stream_next_file
        tst.l   d0
        beq     .bad
.read:
        move.l  d7,d4
        mulu.w  #STREAM_BYTES,d4
        lea     music_buffers,a2
        adda.l  d4,a2
        move.l  stream_dos,a6
        move.l  stream_file,d1
        move.l  a2,d2
        move.l  #STREAM_BYTES,d3
        jsr     -42(a6)
        cmp.l   #STREAM_BYTES,d0
        bne.s   .bad
        subq.l  #1,stream_blocks
        addq.l  #1,stream_reads
        move.w  d7,d0
        add.w   d0,d0
        lea     slot_tracks,a0
        move.w  stream_track,0(a0,d0.w)
        bsr     read_ticks
        sub.l   d6,d0
        and.l   #$ffffff,d0
        bsr     profile_read
        cmp.l   stream_max_read,d0
        bls.s   .ok
        move.l  d0,stream_max_read
.ok:
        moveq   #1,d0
        bra.s   .done
.bad:
        addq.w  #1,stream_errors
        clr.w   stream_enabled
        moveq   #0,d0
.done:
        movem.l (sp)+,d2-d6/a2-a4/a6
        rts

stream_next_file:
        move.l  stream_dos,a6
        move.l  stream_file,d1
        beq.s   .select
        jsr     -36(a6)
        clr.l   stream_file
.select:
        move.w  stream_selected,d0
        bpl.s   .selected
        moveq   #0,d0               ; Automatic selection uses a shuffled bag
        move.w  stream_track,d1
        bsr     music_choose
.selected:
        move.w  d0,stream_track
        move.w  #-1,stream_selected
.open:
        moveq   #0,d0
        move.w  stream_track,d0
        lsl.w   #2,d0
        lea     music_paths,a0
        move.l  0(a0,d0.w),d1
        move.l  #1005,d2            ; MODE_OLDFILE
        jsr     -30(a6)
        move.l  d0,stream_file
        beq     .bad
        move.l  d0,d1
        move.l  #stream_header,d2
        moveq   #16,d3
        jsr     -42(a6)
        cmp.l   #16,d0
        bne     .bad
        cmp.l   #$4d574131,stream_header ; MWA1
        bne     .bad
        cmp.w   #11015,stream_header+4
        bne     .bad
        cmp.w   #STREAM_FRAMES,stream_header+6
        bne     .bad
        move.l  stream_header+8,d0
        beq     .bad
        cmp.l   #$10000000,d0       ; Reject overflow/unbounded header values
        bhi     .bad
        add.l   #STREAM_FRAMES-1,d0
        lsr.l   #8,d0
        lsr.l   #5,d0
        cmp.l   stream_header+12,d0
        bne     .bad
        move.l  d0,stream_blocks
        addq.w  #1,stream_tracks_opened
        move.w  music_trace_count,d0
        cmp.w   #64,d0
        bhs.s   .traced
        addq.w  #1,music_trace_count
        add.w   d0,d0
        lea     music_trace,a0
        move.w  stream_track,0(a0,d0.w)
.traced:
        moveq   #1,d0
        rts
.bad:
        moveq   #0,d0
        rts

; a1=request, d0=one channel, a2=PCM, d2=byte length.
queue_audio:
        move.l  #stream_port,14(a1)
        move.w  #AUDIO_SIZE,18(a1)
        move.l  audio_master+20,20(a1)
        move.l  d0,24(a1)
        move.w  #3,28(a1)           ; CMD_WRITE
        move.b  #$10,30(a1)         ; ADIOF_PERVOL
        clr.b   31(a1)
        move.w  audio_master+32,32(a1)
        move.l  a2,34(a1)
        move.l  d2,38(a1)
        move.w  audio_period,42(a1)
        move.w  music_volume,44(a1)
        cmp.w   #4,d0
        blo.s   .music
        move.w  #56,44(a1)
.music:
        move.w  #1,46(a1)
        move.l  20(a1),a6
        jsr     -30(a6)             ; BeginIO preserves ADIOF_PERVOL; SendIO clears it
        rts

stream_queue:
        move.l  d7,d0
        mulu.w  #PAIR_SIZE,d0
        lea     music_requests,a3
        adda.l  d0,a3
        move.l  d7,d0
        mulu.w  #STREAM_BYTES,d0
        lea     music_buffers,a2
        adda.l  d0,a2
        move.l  a3,a1
        moveq   #1,d0               ; Right = channel 0
        move.l  #STREAM_FRAMES,d2
        bsr     queue_audio
        lea     AUDIO_SIZE(a3),a1
        adda.l  #STREAM_FRAMES,a2
        moveq   #2,d0               ; Left = channel 1
        move.l  #STREAM_FRAMES,d2
        bsr     queue_audio
        lea     slot_active,a0
        move.b  #1,0(a0,d7.w)
        rts

; d0=CMD_STOP(6)/CMD_START(7), d1=channel mask; no pending master request.
audio_control:
        lea     audio_master,a1
        move.w  d0,28(a1)
        move.l  d1,24(a1)
        clr.b   30(a1)
        move.l  4.w,a6
        jsr     -456(a6)
        rts

stream_begin:
        moveq   #6,d0
        moveq   #3,d1
        bsr     audio_control
        moveq   #0,d7
.fill:
        bsr     stream_fill
        tst.l   d0
        beq.s   .failed
        addq.w  #1,d7
        cmp.w   #3,d7
        blo.s   .fill
        moveq   #0,d7
.queue:
        bsr     stream_queue
        addq.w  #1,d7
        cmp.w   #3,d7
        blo.s   .queue
        clr.w   stream_head
        move.w  #1,stream_enabled
        moveq   #7,d0
        moveq   #3,d1
        bsr     audio_control
        rts
.failed:
        bsr     stream_stop
        rts

stream_pump:
        bsr     read_ticks
        move.l  d0,stream_pump_stamp
        tst.w   stream_enabled
        beq     .done
        tst.w   disk_pending
        bne     .async_wait
        move.l  4.w,a6
        moveq   #0,d7
        move.w  stream_head,d7
        move.l  d7,d0
        mulu.w  #PAIR_SIZE,d0
        lea     music_requests,a3
        adda.l  d0,a3
        move.l  a3,a1
        jsr     -468(a6)
        tst.l   d0
        beq     .done
        lea     AUDIO_SIZE(a3),a1
        jsr     -468(a6)
        tst.l   d0
        beq     .done
        move.l  a3,a1
        jsr     -474(a6)
        lea     AUDIO_SIZE(a3),a1
        jsr     -474(a6)
        tst.b   31(a3)
        bne     .error
        tst.b   AUDIO_SIZE+31(a3)
        bne     .error
        lea     slot_active,a0
        clr.b   0(a0,d7.w)
        tst.w   stream_mode
        beq.s   .sync
        bsr     stream_async_begin
        bra     .done
.sync:
        bsr     stream_fill
        tst.l   d0
        beq     .done
        bra     .check_starvation
.async_wait:
        move.l  4.w,a6
        lea     disk_port,a0
        jsr     -372(a6)            ; GetMsg, never wait in the render loop
        tst.l   d0
        beq     .done
        clr.w   disk_pending
        cmp.l   #READ_SLICE,disk_packet+12
        bne     .error
        add.l   #READ_SLICE,disk_offset
        cmp.l   #STREAM_BYTES,disk_offset
        beq.s   .complete
        moveq   #0,d7
        move.w  stream_head,d7
        bsr     stream_async_send
        bra     .done
.complete:
        moveq   #0,d7
        move.w  stream_head,d7
        subq.l  #1,stream_blocks
        addq.l  #1,stream_reads
        move.w  d7,d0
        add.w   d0,d0
        lea     slot_tracks,a0
        move.w  stream_track,0(a0,d0.w)
        bsr     read_ticks
        sub.l   disk_started,d0
        and.l   #$ffffff,d0
        bsr     profile_read
        cmp.l   stream_max_read,d0
        bls.s   .check_starvation
        move.l  d0,stream_max_read
.check_starvation:
        ; If even the newest queued pair completed, playback ran out of data.
        move.w  d7,d0
        addq.w  #2,d0
        cmp.w   #3,d0
        blo.s   .last
        subq.w  #3,d0
.last:
        mulu.w  #PAIR_SIZE,d0
        lea     music_requests,a1
        adda.l  d0,a1
        move.l  4.w,a6
        jsr     -468(a6)
        tst.l   d0
        beq.s   .queue
        addq.w  #1,stream_underruns
.queue:
        bsr     stream_queue
        addq.w  #1,d7
        cmp.w   #3,d7
        blo.s   .head
        moveq   #0,d7
.head:
        move.w  d7,stream_head
        bra.s   .done
.error:
        addq.w  #1,stream_errors
        bsr     stream_stop
.done:
        rts

; Long render passes must not postpone every async slice until the next frame.
; Poll at depth/row boundaries after 80 ms (PAL). Preserve all renderer state.
stream_render_service:
        tst.w   stream_enabled
        beq.s   .done
        tst.w   stream_mode
        beq.s   .done
        movem.l d0-d7/a0-a6,-(sp)
        bsr     read_ticks
        sub.l   stream_pump_stamp,d0
        and.l   #$ffffff,d0
        cmp.l   #4,d0
        blo.s   .restore
        bsr     stream_pump
.restore:
        movem.l (sp)+,d0-d7/a0-a6
.done:
        rts

stream_async_begin:
        bsr     read_ticks
        move.l  d0,disk_started
        clr.l   disk_offset
        tst.l   stream_blocks
        bne     stream_async_send
        bsr     stream_next_file
        tst.l   d0
        bne     stream_async_send
        addq.w  #1,stream_errors
        clr.w   stream_enabled
        rts

stream_async_send:
        move.l  stream_file,d0
        lsl.l   #2,d0               ; AmigaDOS BPTR -> FileHandle address
        move.l  d0,a2
        lea     disk_message,a1
        move.b  #5,8(a1)
        move.l  #disk_packet,10(a1) ; Message name links the DosPacket
        move.w  #68,18(a1)
        lea     disk_packet,a0
        move.l  a1,(a0)
        move.l  #disk_port,4(a0)
        move.l  #82,8(a0)           ; ACTION_READ
        clr.l   12(a0)
        clr.l   16(a0)
        move.l  36(a2),20(a0)       ; fh_Arg1, NOT the file handle BPTR
        move.l  d7,d0
        mulu.w  #STREAM_BYTES,d0
        add.l   #music_buffers,d0
        add.l   disk_offset,d0
        move.l  d0,24(a0)
        move.l  #READ_SLICE,28(a0)
        move.w  #1,disk_pending
        move.l  8(a2),a0            ; fh_Type = filesystem handler port
        move.l  4.w,a6
        jsr     -366(a6)            ; PutMsg
        rts
stream_wait_disk:
        tst.w   disk_pending
        beq.s   .done
        move.l  4.w,a6
        lea     disk_port,a0
        jsr     -384(a6)            ; WaitPort before close/seek/reusing a buffer
        lea     disk_port,a0
        jsr     -372(a6)
        clr.w   disk_pending
.done:
        rts

; Stop/collect every request before any buffer is reused or executable unloaded.
stream_stop:
        bsr     stream_wait_disk
        clr.w   stream_enabled
        move.l  4.w,a6
        moveq   #0,d7
.next:
        lea     slot_active,a0
        tst.b   0(a0,d7.w)
        beq.s   .advance
        clr.b   0(a0,d7.w)
        move.l  d7,d0
        mulu.w  #PAIR_SIZE,d0
        lea     music_requests,a3
        adda.l  d0,a3
        move.l  a3,a1
        jsr     -480(a6)
        move.l  a3,a1
        jsr     -474(a6)
        lea     AUDIO_SIZE(a3),a1
        jsr     -480(a6)
        lea     AUDIO_SIZE(a3),a1
        jsr     -474(a6)
.advance:
        addq.w  #1,d7
        cmp.w   #3,d7
        blo.s   .next
        rts

; d0 direction (+1/-1), d1 current track. Return canonical track index in d0.
; Changing groups selects the first/last entry. A singleton repeats by necessity.
music_choose:
        tst.w   d0
        beq     music_shuffle_choose
        move.w  music_mode,d2
        lsl.w   #2,d2
        lea     music_playlists,a0
        move.l  0(a0,d2.w),a0
        move.w  (a0)+,d2
        moveq   #0,d3
.find:
        move.w  d3,d4
        add.w   d4,d4
        cmp.w   0(a0,d4.w),d1
        beq.s   .found
        addq.w  #1,d3
        cmp.w   d2,d3
        blo.s   .find
        tst.w   d0
        bmi.s   .last
        moveq   #0,d3
        bra.s   .get
.found:
        add.w   d0,d3
        bmi.s   .last
        cmp.w   d2,d3
        blo.s   .get
        moveq   #0,d3
        bra.s   .get
.last:
        move.w  d2,d3
        subq.w  #1,d3
.get:
        add.w   d3,d3
        moveq   #0,d0
        move.w  0(a0,d3.w),d0
        rts

; Each playlist has a bounded bag. Consume all candidates before reshuffling.
; d1 is the last queued/audible canonical identity, not a filename alias.
music_shuffle_choose:
        move.w  d1,music_previous
        move.w  music_mode,d2
        add.w   d2,d2
        lea     music_bag_counts,a1
        adda.w  d2,a1
        move.w  music_mode,d2
        mulu.w  #198,d2
        lea     music_bags,a2
        adda.w  d2,a2
        move.w  (a1),d3
        beq.s   .refill
        cmp.w   #1,d3
        bne.s   .pop
        cmp.w   (a2),d1
        bne.s   .pop
.refill:
        move.w  music_mode,d2
        lsl.w   #2,d2
        lea     music_playlists,a0
        move.l  0(a0,d2.w),a0
        move.w  (a0)+,d3
        move.w  d3,(a1)
        move.w  d3,d4
        subq.w  #1,d4
        move.l  a2,a3
.copy:
        move.w  (a0)+,(a3)+
        dbra    d4,.copy
        move.w  d3,d4
        subq.w  #1,d4
        beq.s   .pop
.shuffle:
        moveq   #0,d0
        move.w  music_rng,d0
        lsr.w   #1,d0
        bcc.s   .random
        eori.w  #$b400,d0
.random:
        move.w  d0,music_rng
        move.w  d4,d2
        addq.w  #1,d2
        divu.w  d2,d0
        swap    d0
        add.w   d0,d0
        move.w  d4,d2
        add.w   d2,d2
        move.w  0(a2,d0.w),d5
        move.w  0(a2,d2.w),0(a2,d0.w)
        move.w  d5,0(a2,d2.w)
        subq.w  #1,d4
        bne.s   .shuffle
.pop:
        subq.w  #1,d3
        move.w  d3,d2
        add.w   d2,d2
        move.w  0(a2,d2.w),d0
        cmp.w   music_previous,d0
        bne.s   .chosen
        tst.w   d3
        beq.s   .chosen             ; Singleton playlist must repeat
        move.w  (a2),d0
        move.w  music_previous,0(a2,d2.w)
        move.w  d0,0(a2,d2.w)
        move.w  music_previous,(a2)
.chosen:
        move.w  d3,(a1)
        rts

music_keys:
        moveq   #0,d0
        tst.b   keys+$55            ; F6 next track
        beq.s   .prev
        moveq   #1,d0
.prev:
        tst.b   keys+$56            ; F7 previous track
        beq.s   .mode
        moveq   #-1,d0
.mode:
        tst.b   keys+$57            ; F8: exploration/battle audition, no combat yet
        beq.s   .edge
        moveq   #2,d0
.edge:
        move.w  music_key,d1
        move.w  d0,music_key
        tst.w   d1
        bne.s   .done
        tst.w   d0
        beq.s   .done
        move.w  stream_head,d1
        add.w   d1,d1
        lea     slot_tracks,a0
        move.w  0(a0,d1.w),d1
        cmp.w   #2,d0
        bne.s   .choose
        eori.w  #1,music_mode
        moveq   #1,d0
.choose:
        bsr     music_choose
        move.w  d0,stream_selected
        bsr     stream_stop
        clr.l   stream_blocks
        bsr     stream_begin
.done:
        rts

start_voice:
        moveq   #6,d0
        moveq   #12,d1
        bsr     audio_control
        lea     voice_requests,a1
        lea     voice,a2
        moveq   #4,d0
        move.l  #VOICE_WORDS*2,d2
        bsr     queue_audio
        lea     voice_requests+AUDIO_SIZE,a1
        lea     voice,a2
        moveq   #8,d0
        move.l  #VOICE_WORDS*2,d2
        bsr     queue_audio
        move.w  #1,voice_active
        move.w  #24,d0
        bsr     music_set_volume
        moveq   #7,d0
        moveq   #12,d1
        bsr     audio_control
        rts

voice_poll:
        tst.w   voice_active
        beq.s   .done
        move.l  4.w,a6
        lea     voice_requests,a1
        jsr     -468(a6)
        tst.l   d0
        beq.s   .done
        lea     voice_requests+AUDIO_SIZE,a1
        jsr     -468(a6)
        tst.l   d0
        beq.s   .done
        bsr     voice_stop
        moveq   #40,d0
        bsr     music_set_volume
.done:
        rts

voice_stop:
        tst.w   voice_active
        beq.s   .done
        clr.w   voice_active
        move.l  4.w,a6
        lea     voice_requests,a1
        jsr     -480(a6)
        lea     voice_requests,a1
        jsr     -474(a6)
        lea     voice_requests+AUDIO_SIZE,a1
        jsr     -480(a6)
        lea     voice_requests+AUDIO_SIZE,a1
        jsr     -474(a6)
.done:
        rts

music_set_volume:
        move.w  d0,music_volume
        lea     music_requests,a0
        moveq   #5,d1
.queue:
        move.w  d0,44(a0)
        adda.w  #AUDIO_SIZE,a0
        dbra    d1,.queue
        ; All channels allocated at maximum priority; only volume registers here.
        move.w  d0,$a8(a5)
        move.w  d0,$b8(a5)
        rts

system_close:
        clr.w   input_active
        tst.w   audio_open
        beq.s   .input
        bsr     stream_stop
        bsr     voice_stop
        move.l  4.w,a6
        lea     audio_master,a1
        move.l  #15,24(a1)
        jsr     -450(a6)
        clr.w   audio_open
.input:
        tst.w   input_installed
        beq.s   .input_close
        lea     input_request,a1
        move.w  #10,28(a1)
        move.l  #input_handler,40(a1)
        move.l  4.w,a6
        jsr     -456(a6)
        clr.w   input_installed
.input_close:
        tst.w   input_open
        beq.s   .file
        lea     input_request,a1
        move.l  4.w,a6
        jsr     -450(a6)
        clr.w   input_open
.file:
        move.l  stream_file,d1
        beq.s   .dos
        move.l  stream_dos,a6
        jsr     -36(a6)
        clr.l   stream_file
.dos:
        move.l  stream_dos,d0
        beq.s   .signal
        move.l  d0,a1
        move.l  4.w,a6
        jsr     -414(a6)
        clr.l   stream_dos
.signal:
        moveq   #0,d0
        move.b  stream_signal,d0
        bmi.s   .done
        move.l  4.w,a6
        jsr     -336(a6)
        move.b  #-1,stream_signal
.done:
        rts

report_stream:
        move.l  stream_reads,d0
        lea     text_reads,a0
        bsr     decimal5
        move.l  stream_max_read,d0
        lea     text_latency,a0
        bsr     decimal5
        moveq   #0,d0
        move.w  stream_underruns,d0
        lea     text_underruns,a0
        bsr     decimal5
        moveq   #0,d0
        move.w  stream_errors,d0
        lea     text_errors,a0
        bsr     decimal5
        moveq   #0,d0
        move.w  stream_tracks_opened,d0
        lea     text_tracks,a0
        bsr     decimal5
        move.l  stream_dos,a6
        jsr     -60(a6)
        move.l  d0,d1
        beq.s   .done
        move.l  #stream_text,d2
        move.l  #stream_text_end-stream_text,d3
        jsr     -48(a6)
.done:
        rts

        section stream_data,data
stream_mode: dc.w STREAM_ASYNC
disk_pending: dc.w 0
disk_started: dc.l 0
disk_offset: dc.l 0
stream_pump_stamp: dc.l 0
stream_dos: dc.l 0
stream_file: dc.l 0
stream_blocks: dc.l 0
stream_reads: dc.l 0
stream_max_read: dc.l 0
stream_track: dc.w -1
stream_head: dc.w 0
stream_tracks_opened: dc.w 0
stream_underruns: dc.w 0
stream_errors: dc.w 0
stream_enabled: dc.w 0
music_volume: dc.w 40
music_key: dc.w 0
music_mode: dc.w 0
stream_selected: dc.w MUSIC_TITLE
music_trace_count: dc.w 0
music_previous: dc.w -1
music_rng: dc.w $ace1
music_bag_counts: dc.w 0,0
voice_active: dc.w 0
audio_open: dc.w 0
input_open: dc.w 0
input_installed: dc.w 0
input_active: dc.w 0
stream_signal: dc.b -1
audio_mask: dc.b 15
input_handler:
        dc.l 0,0
        dc.b 2,51                  ; NT_INTERRUPT, priority above Intuition
        dc.l input_name
        dc.l 0,input_events
audio_name: dc.b "audio.device",0
input_name: dc.b "input.device",0
stream_text:
        dc.b "Music: 16KiB reads="
text_reads: dc.b "00000",10,"Max read ticks="
text_latency: dc.b "00000","  starvations="
text_underruns: dc.b "00000",10,"Track opens="
text_tracks: dc.b "00000","  errors="
text_errors: dc.b "00000",10
stream_text_end:
        even
        section stream_work,bss
disk_port: ds.b 34
        cnop 0,4
disk_message: ds.b 20
disk_packet: ds.b 48
stream_port: ds.b 34
audio_master: ds.b AUDIO_SIZE
input_request: ds.b 48
music_requests: ds.b AUDIO_SIZE*6
voice_requests: ds.b AUDIO_SIZE*2
stream_header: ds.b 16
slot_tracks: ds.w 3
slot_active: ds.b 4
music_bags: ds.w 198
music_trace: ds.w 64
        section music_dma,bss_c
music_buffers: ds.b STREAM_BYTES*3
        include "music-assets.i"
