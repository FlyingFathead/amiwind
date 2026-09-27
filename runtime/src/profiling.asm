; Compact counters/histograms for repeatable 50 Hz PAL measurements.
        section code,code
profile_read:
        add.l   d0,profile_read_ticks
        lea     profile_read_hist,a0
        bra.s   profile_bin
profile_frame:
        lea     profile_solid_hist,a0
        lea     profile_solid_max,a1
        tst.w   solid_mode
        bne.s   .max
        lea     profile_wire_hist,a0
        lea     profile_wire_max,a1
.max:
        cmp.l   (a1),d0
        bls.s   profile_bin
        move.l  d0,(a1)
profile_bin:
        move.l  d0,d1
        cmp.l   #63,d1
        bls.s   .bin
        moveq   #63,d1
.bin:
        lsl.w   #2,d1
        addq.l  #1,0(a0,d1.w)
        rts

profile_save:
        move.w  video_hz,profile_hz
        move.l  solid_stats,profile_solid_frames
        move.l  solid_stats+4,profile_solid_ticks
        move.l  wire_stats,profile_wire_frames
        move.l  wire_stats+4,profile_wire_ticks
        move.l  stream_reads,profile_reads
        move.l  stream_max_read,profile_read_max
        moveq   #0,d0
        move.w  stream_underruns,d0
        move.l  d0,profile_underruns
        move.w  stream_errors,d0
        move.l  d0,profile_errors
        move.w  stream_tracks_opened,d0
        move.l  d0,profile_tracks
        move.l  stream_dos,a6
        move.l  #profile_ram_name,d1
        tst.l   benchmark_limit
        beq.s   .open
        move.l  #profile_name,d1
.open:
        move.l  #1006,d2            ; MODE_NEWFILE: last run in this working image
        jsr     -30(a6)
        tst.l   d0
        beq.s   .done
        move.l  d0,d4
        move.l  d0,d1
        move.l  #profile_data,d2
        move.l  #profile_end-profile_data,d3
        jsr     -48(a6)
        tst.l   d0
        bpl.s   .written
        moveq   #0,d0
.written:
        move.l  d0,profile_written
        move.l  d4,d1
        jsr     -36(a6)
.done:
        move.l  profile_written,d0
        lea     profile_text_bytes,a0
        bsr     decimal5
        move.l  stream_dos,a6
        jsr     -60(a6)
        move.l  d0,d1
        beq.s   .return
        move.l  #profile_text,d2
        move.l  #profile_text_end-profile_text,d3
        jsr     -48(a6)
.return:
        bsr     music_trace_save
        rts

; First 64 successfully opened tracks, independent of the frame-profile format.
music_trace_save:
        move.w  music_trace_count,music_trace_header+4
        move.w  music_mode,music_trace_header+6
        move.l  stream_dos,a6
        move.l  #music_trace_name,d1
        tst.l   benchmark_limit
        beq.s   .open
        move.l  #music_trace_bench_name,d1
.open:
        move.l  #1006,d2
        jsr     -30(a6)
        tst.l   d0
        beq.s   .done
        move.l  d0,d4
        move.l  d0,d1
        move.l  #music_trace_header,d2
        moveq   #8,d3
        jsr     -48(a6)
        move.l  d4,d1
        move.l  #music_trace,d2
        move.l  #128,d3
        jsr     -48(a6)
        move.l  d4,d1
        jsr     -36(a6)
.done:
        rts

        section profile_tables,data
benchmark_start: dc.l 0
benchmark_limit: dc.l BENCHMARK_TICKS
profile_name: dc.b "PROFILE:MWPROFILE.BIN",0
profile_ram_name: dc.b "MWBOOT:MWPROFILE.BIN",0
music_trace_name: dc.b "MWBOOT:MWMUSIC.BIN",0
music_trace_bench_name: dc.b "PROFILE:MWMUSIC.BIN",0
        even
music_trace_header: dc.b "MWM1"
        dc.w 0,0
        cnop 0,4
profile_written: dc.l 0
profile_text: dc.b "Profile bytes written="
profile_text_bytes: dc.b "00000",10
profile_text_end:
        cnop 0,4
profile_data:
        dc.b "MWP1"
        dc.w 1
profile_hz: dc.w 50
        dc.l STREAM_ASYNC,BENCHMARK_TICKS
profile_solid_frames: dc.l 0
profile_solid_ticks: dc.l 0
profile_wire_frames: dc.l 0
profile_wire_ticks: dc.l 0
profile_reads: dc.l 0
profile_read_max: dc.l 0
profile_read_ticks: dc.l 0
profile_underruns: dc.l 0
profile_errors: dc.l 0
profile_tracks: dc.l 0
profile_solid_max: dc.l 0
profile_wire_max: dc.l 0
profile_read_hist: dcb.l 64,0
profile_solid_hist: dcb.l 64,0
profile_wire_hist: dcb.l 64,0
profile_end:
