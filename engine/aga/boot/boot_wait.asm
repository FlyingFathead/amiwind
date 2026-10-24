; AmiWind startup preflight: console output and the timed waits. GPL-2.0-or-later.
; Included by bootcheck.asm, and by the host test that runs these routines
; (tests/test_heap_size.py). The includer provides dos_base, output_handle,
; input_handle, input_byte, countdown_value, report_buffer, note_buffer,
; fast_found_mb, countdown_format, countdown_done, fast_note and
; fast_countdown_format.

; Keep the successful preflight visible briefly without relying on console
; scrollback: five seconds, SPACE or ENTER skips.
countdown:
        movem.l d4/a4,-(sp)
        moveq   #5,d4
        lea     countdown_format(pc),a4
        bsr     countdown_run
        movem.l (sp)+,d4/a4
        rts

; RAM-REQUIREMENT-32MB-48: under the safe Fast RAM minimum, the maintainer's note
; with the measured size under the checklist's separator, then a countdown line
; under it: ten seconds, ENTER (or SPACE) skips. It never blocks the start, so
; unattended runs at 16 MB go on by themselves.
fast_wait:
        movem.l d4/a0-a4/a6,-(sp)
        move.l  4.w,a6
        lea     fast_note(pc),a0
        lea     fast_found_mb,a1
        lea     put_char(pc),a2
        lea     note_buffer,a3
        jsr     _LVORawDoFmt(a6)
        lea     note_buffer,a0
        bsr     puts
        moveq   #AW_FAST_WAIT_SECONDS,d4
        lea     fast_countdown_format(pc),a4
        bsr     countdown_run
        movem.l (sp)+,d4/a0-a4/a6
        rts

; d4 = seconds, a4 = the countdown row (RawDoFmt, one %ld, starts with a carriage
; return so it overwrites itself). WaitForChar uses DOS/timer time, so
; accelerated CPU/JIT execution does not collapse the delay into a tight busy
; loop. SPACE or ENTER ends the wait at once; at zero it goes on by itself.
countdown_run:
        movem.l d0-d4/a0-a3/a6,-(sp)
        move.l  dos_base,a6
        jsr     _LVOInput(a6)
        move.l  d0,input_handle
.loop:
        move.l  d4,countdown_value
        move.l  4.w,a6
        move.l  a4,a0
        lea     countdown_value,a1
        lea     put_char(pc),a2
        lea     report_buffer,a3
        jsr     _LVORawDoFmt(a6)
        lea     report_buffer,a0
        bsr     puts

        move.l  input_handle,d1
        beq.s   .no_input
        move.l  #1000000,d2
        move.l  dos_base,a6
        jsr     _LVOWaitForChar(a6)
        tst.l   d0
        beq.s   .next

        move.l  input_handle,d1
        lea     input_byte,a0
        move.l  a0,d2
        moveq   #1,d3
        jsr     _LVORead(a6)
        cmp.l   #1,d0
        bne.s   .next
        moveq   #0,d0
        move.b  input_byte,d0
        cmp.b   #' ',d0
        beq.s   .done
        cmp.b   #13,d0
        beq.s   .done
        cmp.b   #10,d0
        beq.s   .done
        bra.s   .next

.no_input:
        ; An inherited console normally supplies an input handle. If it does not,
        ; use dos.library Delay() as a non-busy one-second fallback.
        moveq   #50,d1
        move.l  dos_base,a6
        jsr     _LVODelay(a6)
.next:
        subq.l  #1,d4
        bne.w   .loop
.done:
        lea     countdown_done(pc),a0
        bsr     puts
        movem.l (sp)+,d0-d4/a0-a3/a6
        rts

; RawDoFmt callback includes the terminating zero byte.
put_char:
        move.b  d0,(a3)+
        rts

; Write a NUL-terminated message to the inherited CLI output.
puts:
        movem.l d0-d3/a0-a1/a6,-(sp)
        move.l  a0,d2
        moveq   #0,d3
.length:
        tst.b   (a0)+
        beq     .write
        addq.l  #1,d3
        bra     .length
.write:
        move.l  output_handle,d1
        move.l  dos_base,a6
        jsr     _LVOWrite(a6)
        movem.l (sp)+,d0-d3/a0-a1/a6
        rts
