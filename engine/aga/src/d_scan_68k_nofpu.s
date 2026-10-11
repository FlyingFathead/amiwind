; AmiWind: upstream AmiQuake (TerribleFire's GCC port, Stephen Leary), src/d_scan_68k_nofpu.s at revision
; 9c62d905151614af3e788ae3145a0d4ecc8a7bb8, GPL v2 (docs/LICENSING_AND_CREDITS.md). Linked only by the
; upstream engine profile (docs/ENGINE_PROFILES.md); unchanged below this header except the lines
; marked "AmiWind:" (same machine code, no assembler notices).
;
; D_DrawSpans8_NoFPU - Pure fixed-point span drawing for non-FPU builds
; Based on NovaCoder's FPU-optimized version (d_scan_68k.s)
; Converted to use 16.16 and 22.10 fixed-point arithmetic
;
; Performance: ~2× slower than FPU version, but ~1.6× faster than C
;

	XDEF	_D_DrawSpans8

	; External Quake globals (C code)
	XREF	_d_zistepu_fp
	XREF	_d_zistepv_fp
	XREF	_d_ziorigin_fp
	XREF	_d_sdivzstepu_fp
	XREF	_d_sdivzstepv_fp
	XREF	_d_tdivzstepu_fp
	XREF	_d_tdivzstepv_fp
	XREF	_d_sdivzorigin_fp
	XREF	_d_tdivzorigin_fp
	XREF	_cacheblock
	XREF	_d_viewbuffer
	XREF	_screenwidth
	XREF	_d_pzbuffer
	XREF	_d_zwidth
	XREF	_sadjust
	XREF	_tadjust
	XREF	_bbextents
	XREF	_bbextentt
	XREF	_cachewidth

	; Fixed-point math library
	XREF	_FixedMul_Internal
	XREF	_FixedMul_22_10_Internal
	XREF	_FixedDiv_Internal

	section	text,code

;
; D_DrawSpans8 - Main 8-bit span drawer (non-FPU version)
;
; Entry: a0 = espan_t *pspan (linked list of spans)
;
; espan_t structure:
;   +0: u (int)
;   +4: v (int)
;   +8: count (int)
;   +12: pnext (espan_t *)
;
_D_DrawSpans8:
	; Save registers (no FPU registers needed)
	movem.l	d2-d7/a2-a6,-(sp)

	movea.l	a0,a6			; a6 = pspan pointer

	; Calculate and save izistep for later use
	; izistep = zistepu_fp << 15 (16.16 format to z-buffer format)
	move.l	(_d_zistepu_fp),d0	; d0 = zistepu (16.16)
	lsl.l	#8,d0
	lsl.l	#7,d0			; d0 = izistep (total shift of 15)
	move.l	d0,-(sp)		; Save izistep on stack

	; Load base pointers
	movea.l	(_cacheblock),a0	; a0 = texture base pointer
	movea.l	(_bbextents),a4		; a4 = bbextents (s clamp limit)
	movea.l	(_bbextentt),a5		; a5 = bbextentt (t clamp limit)

.span_loop:
	; Get span pixel count
	move.l	8(a6),d7		; d7 = pspan->count
	ble.w	.next_span		; Skip empty spans

	; Load span u, v coordinates
	move.l	(a6),d0			; d0 = u (integer)
	move.l	4(a6),d1		; d1 = v (integer)

	;=== Calculate framebuffer pointer ===
	; framebuffer = d_viewbuffer + v*screenwidth + u
	movea.l	(_d_viewbuffer),a1	; a1 = framebuffer base
	move.l	d1,d2
	mulu.l	(_screenwidth),d2	; d2 = v * screenwidth
	adda.l	d0,a1			; a1 += u
	adda.l	d2,a1			; a1 = final framebuffer pointer

	;=== Calculate z-buffer pointer ===
	; z-buffer = d_pzbuffer + (v*d_zwidth + u)*2
	movea.l	(_d_pzbuffer),a2	; a2 = z-buffer base
	move.l	d1,d2			; d2 = v
	mulu.l	(_d_zwidth),d2		; d2 = v * d_zwidth
	add.l	d0,d2			; d2 = v * d_zwidth + u
	add.l	d2,d2			; d2 *= 2 (word offset)
	adda.l	d2,a2			; a2 = z-buffer pointer

	;=== Calculate zi using fixed-point (16.16 format) ===
	; zi = u * zistepu + v * zistepv + ziorigin
	; u and v are integers, need to convert to 16.16
	; NOTE: Since they're screen coordinates (0-640), no overflow

	; Save u for later use
	move.l	(a6),-(sp)		; Push u
	move.l	4(a6),-(sp)		; Push v

	; u * zistepu (both in 16.16 after conversion)
	move.l	4(sp),d0		; d0 = u (from stack)
	swap	d0
	clr.w	d0			; d0 = u << 16 (convert to 16.16)
	move.l	(_d_zistepu_fp),d1	; d1 = zistepu (16.16)
	bsr	_FixedMul_Internal	; d0 = u * zistepu (16.16)
	move.l	d0,-(sp)		; Save partial result

	; v * zistepv
	move.l	4(sp),d0		; d0 = v (from stack)
	swap	d0
	clr.w	d0			; d0 = v << 16 (convert to 16.16)
	move.l	(_d_zistepv_fp),d1	; d1 = zistepv (16.16)
	bsr	_FixedMul_Internal	; d0 = v * zistepv (16.16)

	; zi = u*zistepu + v*zistepv + ziorigin
	add.l	(sp)+,d0		; d0 += u*zistepu (pop partial result)
	add.l	(_d_ziorigin_fp),d0	; d0 = zi (16.16)

	; Convert zi to izi for z-buffer (shift left by 15)
	move.l	d0,d6			; d6 = zi (16.16)
	lsl.l	#8,d6
	lsl.l	#7,d6			; d6 = izi (shift 15) - will be used for z-buffer

	;=== Perspective divide ===
	; z = 65536 / zi (both in 16.16)
	bsr	_FixedDiv_Internal	; d0 = z (16.16)

	; Clean up stack (pop u and v)
	addq.l	#8,sp			; Pop v and u

	; z is already in 16.16 format, save it
	move.l	d0,-(sp)		; Save z on stack

	;=== Calculate s coordinate (16.16 format) ===
	; s = (u * sdivzstepu + v * sdivzstepv + sdivzorigin) * z + sadjust

	; u * sdivzstepu (16.16)
	move.l	(a6),d0			; d0 = u (integer)
	swap	d0
	clr.w	d0			; d0 = u << 16 (convert to 16.16)
	move.l	(_d_sdivzstepu_fp),d1	; d1 = sdivzstepu (16.16)
	bsr	_FixedMul_Internal		; d0 =u * sdivzstepu (16.16)
	move.l	d0,d2			; Save partial result

	; v * sdivzstepv (16.16)
	move.l	4(a6),d0		; d0 = v (integer)
	swap	d0
	clr.w	d0			; d0 = v << 16 (convert to 16.16)
	move.l	(_d_sdivzstepv_fp),d1	; d1 = sdivzstepv (16.16)
	bsr	_FixedMul_Internal		; d0 =v * sdivzstepv (16.16)

	; sdivz = u*sdivzstepu + v*sdivzstepv + sdivzorigin
	add.l	d2,d0			; d0 += u*sdivzstepu
	add.l	(_d_sdivzorigin_fp),d0	; d0 = sdivz (16.16)

	; s = sdivz * z
	move.l	(sp),d1			; d1 = z (16.16)
	bsr	_FixedMul_Internal		; d0 =sdivz * z (16.16)
	add.l	(_sadjust),d0		; d0 += sadjust
	move.l	d0,d2			; d2 = s (16.16)

	; Clamp s to [0, bbextents]
	cmp.l	a4,d2
	ble.s	.s_ok
	move.l	a4,d2
	bra.s	.s_clamped
.s_ok:
	tst.l	d2
	bpl.s	.s_clamped
	moveq	#0,d2
.s_clamped:

	;=== Calculate t coordinate (16.16 format) ===
	; t = (u * tdivzstepu + v * tdivzstepv + tdivzorigin) * z + tadjust

	; u * tdivzstepu (16.16)
	move.l	(a6),d0			; d0 = u (integer)
	swap	d0
	clr.w	d0			; d0 = u << 16 (convert to 16.16)
	move.l	(_d_tdivzstepu_fp),d1	; d1 = tdivzstepu (16.16)
	bsr	_FixedMul_Internal		; d0 =u * tdivzstepu (16.16)
	move.l	d0,d3			; Save partial result

	; v * tdivzstepv (16.16)
	move.l	4(a6),d0		; d0 = v (integer)
	swap	d0
	clr.w	d0			; d0 = v << 16 (convert to 16.16)
	move.l	(_d_tdivzstepv_fp),d1	; d1 = tdivzstepv (16.16)
	bsr	_FixedMul_Internal		; d0 =v * tdivzstepv (16.16)

	; tdivz = u*tdivzstepu + v*tdivzstepv + tdivzorigin
	add.l	d3,d0			; d0 += u*tdivzstepu
	add.l	(_d_tdivzorigin_fp),d0	; d0 = tdivz (16.16)

	; t = tdivz * z
	move.l	(sp),d1			; d1 = z (16.16)
	bsr	_FixedMul_Internal		; d0 =tdivz * z (16.16)
	add.l	(_tadjust),d0		; d0 += tadjust
	move.l	d0,d3			; d3 = t (16.16)

	; Clamp t to [0, bbextentt]
	cmp.l	a5,d3
	ble.s	.t_ok
	move.l	a5,d3
	bra.s	.t_clamped
.t_ok:
	tst.l	d3
	bpl.s	.t_clamped
	moveq	#0,d3
.t_clamped:

	;=== Calculate sstep and tstep for span ===
	; Need to calculate s,t at end of span, then sstep = (send - s) / (count - 1)

	; Save current s,t values
	move.l	d2,-(sp)		; Save s
	move.l	d3,-(sp)		; Save t
	move.l	d7,-(sp)		; Save count

	; Calculate position at end of span: u + count - 1
	move.l	(a6),d0			; d0 = u
	add.l	d7,d0
	subq.l	#1,d0			; d0 = u + count - 1

	; Calculate zi at end of span
	swap	d0
	clr.w	d0			; d0 = (u+count-1) << 16 (convert to 16.16)
	move.l	(_d_zistepu_fp),d1
	bsr	_FixedMul_Internal	; d0 = (u+count-1) * zistepu
	move.l	d0,d2			; Save partial

	move.l	4(a6),d0		; d0 = v
	swap	d0
	clr.w	d0			; d0 = v << 16
	move.l	(_d_zistepv_fp),d1
	bsr	_FixedMul_Internal	; d0 = v * zistepv
	add.l	d2,d0			; d0 = zi_end
	add.l	(_d_ziorigin_fp),d0

	; Perspective divide for z_end
	bsr	_FixedDiv_Internal	; d0 = z_end (16.16)
	move.l	d0,-(sp)		; Save z_end

	; Calculate send = sdivz_end * z_end + sadjust
	move.l	(a6),d0			; d0 = u
	move.l	(sp)+,d1		; d1 = z_end (pop from stack)
	move.l	d1,-(sp)		; Save z_end again
	add.l	8(sp),d0		; d0 = u + count - 1
	swap	d0
	clr.w	d0			; d0 = (u+count-1) << 16
	move.l	(_d_sdivzstepu_fp),d1
	bsr	_FixedMul_Internal		; d0 =(u+count-1) * sdivzstepu
	move.l	d0,d2			; Save partial

	move.l	4(a6),d0		; d0 = v
	swap	d0
	clr.w	d0
	move.l	(_d_sdivzstepv_fp),d1
	bsr	_FixedMul_Internal
	add.l	d2,d0			; d0 = sdivz_end
	add.l	(_d_sdivzorigin_fp),d0

	move.l	(sp)+,d1		; d1 = z_end
	bsr	_FixedMul_Internal		; d0 =send
	add.l	(_sadjust),d0

	; Clamp send
	cmp.l	a4,d0
	ble.s	.send_ok
	move.l	a4,d0
	bra.s	.send_clamped
.send_ok:
	cmp.l	#8,d0
	bge.s	.send_clamped
	moveq	#8,d0
.send_clamped:

	; Calculate sstep = (send - s) / (count - 1)
	move.l	4(sp),d1		; d1 = s (from stack)
	sub.l	d1,d0			; d0 = send - s
	move.l	(sp),d1			; d1 = count
	subq.l	#1,d1
	ble.s	.no_sstep_divide
	divs.l	d1,d0		; d0 = sstep (AmiWind: was divsl.l d1,d0:d0, the same instruction; vasm notice 2066)
.no_sstep_divide:
	move.l	d0,d4			; d4 = sstep

	; Calculate tend = tdivz_end * z_end + tadjust
	; Note: z_end was already used, need to recalculate from zi_end
	; Actually, let's save it before using it for send

	; Recalculate z_end (we need it again)
	move.l	4(a6),d0		; d0 = v
	lsl.l	#8,d0
	lsl.l	#2,d0
	move.l	(_d_zistepv_fp),d1
	bsr	_FixedMul_22_10_Internal
	move.l	d0,d1			; Save v*zistepv

	move.l	(a6),d0			; d0 = u
	add.l	(sp),d0			; Add count
	subq.l	#1,d0			; d0 = u + count - 1
	lsl.l	#8,d0
	lsl.l	#2,d0
	move.l	(_d_zistepu_fp),d2
	move.l	d2,d3
	move.l	d0,d2
	move.l	d3,d1
	move.l	d2,d0
	bsr	_FixedMul_22_10_Internal
	add.l	d1,d0
	add.l	(_d_ziorigin_fp),d0
	bsr	_FixedDiv_Internal
	asl.l	#6,d0			; d0 = z_end (16.16)
	move.l	d0,-(sp)		; Save z_end

	; Calculate tend
	move.l	(a6),d0			; d0 = u
	add.l	8(sp),d0		; d0 = u + count - 1
	swap	d0
	clr.w	d0
	move.l	(_d_tdivzstepu_fp),d1
	bsr	_FixedMul_Internal
	move.l	d0,d2

	move.l	4(a6),d0
	swap	d0
	clr.w	d0
	move.l	(_d_tdivzstepv_fp),d1
	bsr	_FixedMul_Internal
	add.l	d2,d0
	add.l	(_d_tdivzorigin_fp),d0

	move.l	(sp)+,d1		; d1 = z_end
	bsr	_FixedMul_Internal
	add.l	(_tadjust),d0

	; Clamp tend
	cmp.l	a5,d0
	ble.s	.tend_ok
	move.l	a5,d0
	bra.s	.tend_clamped
.tend_ok:
	cmp.l	#8,d0
	bge.s	.tend_clamped
	moveq	#8,d0
.tend_clamped:

	; Calculate tstep = (tend - t) / (count - 1)
	move.l	4(sp),d1		; d1 = t (from stack)
	sub.l	d1,d0
	move.l	(sp),d1			; d1 = count
	subq.l	#1,d1
	ble.s	.no_tstep_divide
	divs.l	d1,d0		; AmiWind: was divsl.l d1,d0:d0, the same instruction (vasm notice 2066)
.no_tstep_divide:
	move.l	d0,d5			; d5 = tstep

	; Restore s, t, count
	addq.l	#4,sp			; Pop count
	move.l	(sp)+,d3		; Restore t
	move.l	(sp)+,d2		; Restore s
	addq.l	#4,sp			; Pop z from earlier

	; Note: izistep is at bottom of stack (saved at function start)
	; We'll reload it from stack each iteration since d1 gets clobbered

	;=== CRITICAL INNER LOOP - Called for every pixel ===
.pixel_loop:
	; Get texture coordinate (s >> 16, t >> 16)
	move.l	d2,d0
	swap	d0			; d0.w = s integer part

	; Fetch texel: pbase[s>>16 + (t>>16)*cachewidth]
	move.l	d3,d1
	swap	d1			; d1.w = t integer part
	mulu.w	(_cachewidth),d1	; d1 = (t>>16) * cachewidth
	add.w	d1,d0			; d0 = offset into texture
	movea.l	a0,a3
	adda.w	d0,a3
	move.b	(a3),d1			; d1 = texel color

	; Transparency check
	moveq	#-1,d0
	cmp.b	d0,d1
	beq.s	.skip_pixel

	; Z-buffer depth test
	; Compare upper 16 bits of izi with z-buffer value
	move.l	d6,d0
	swap	d0			; d0 = upper 16 bits of izi
	cmp.w	(a2),d0
	ble.s	.skip_pixel		; Skip if existing pixel is closer

	; Write z-buffer and pixel
	move.w	d0,(a2)			; Update z-buffer (d0 already has upper 16 bits)
	move.b	d1,(a1)			; Write pixel

.skip_pixel:
	; Advance to next pixel
	add.l	d4,d2			; s += sstep
	add.l	d5,d3			; t += tstep
	add.l	(sp),d6			; izi += izistep (reload from stack)
	addq.l	#2,a2			; z-buffer++ (word)
	addq.l	#1,a1			; framebuffer++ (byte)
	subq.l	#1,d7			; count--
	bgt.s	.pixel_loop
	;=== END INNER LOOP ===

.next_span:
	; Move to next span in linked list
	lea	12(a6),a6		; a6 = &pspan->pnext
	moveq	#-128,d0
	cmp.l	8(a6),d0		; Check for end marker
	bne.w	.span_loop

	; Clean up stack and return
	addq.l	#4,sp			; Pop izistep
	movem.l	(sp)+,d2-d7/a2-a6
	rts

;
; D_DrawTurbulent8Span - Turbulent water pixel loop (inner hot path)
; Processes r_turb_spancount pixels with sine-table distortion
;
; C equivalent:
;   sturb = ((r_turb_s + r_turb_turb[(r_turb_t>>16)&127])>>16)&63;
;   tturb = ((r_turb_t + r_turb_turb[(r_turb_s>>16)&127])>>16)&63;
;   *r_turb_pdest++ = *(r_turb_pbase + (tturb<<6) + sturb);
;   r_turb_s += r_turb_sstep; r_turb_t += r_turb_tstep;
;
; Note: This is identical to FPU version - turbulent rendering uses
; only fixed-point integer math, no FPU operations
;
	XDEF	_D_DrawTurbulent8Span

	; External turbulence globals (set by Turbulent8)
	XREF	_r_turb_pbase
	XREF	_r_turb_pdest
	XREF	_r_turb_s
	XREF	_r_turb_t
	XREF	_r_turb_sstep
	XREF	_r_turb_tstep
	XREF	_r_turb_turb
	XREF	_r_turb_spancount

_D_DrawTurbulent8Span:
	movem.l	d2-d7/a2-a3,-(sp)

	; Load globals into registers (minimize memory access)
	move.l	(_r_turb_s),d2		; d2 = r_turb_s (16.16 fixed)
	move.l	(_r_turb_t),d3		; d3 = r_turb_t (16.16 fixed)
	move.l	(_r_turb_sstep),d4	; d4 = r_turb_sstep
	move.l	(_r_turb_tstep),d5	; d5 = r_turb_tstep
	move.l	(_r_turb_spancount),d7	; d7 = loop counter
	movea.l	(_r_turb_pbase),a0	; a0 = texture base
	movea.l	(_r_turb_pdest),a1	; a1 = dest framebuffer
	movea.l	(_r_turb_turb),a2	; a2 = sine table pointer

	; Pre-calculate constants
	moveq	#127,d6			; d6 = CYCLE-1 mask (128-1)

.turb_pixel_loop:
	; sturb = ((r_turb_s + r_turb_turb[(r_turb_t>>16)&127])>>16)&63
	move.l	d3,d0			; d0 = r_turb_t
	swap	d0			; d0 = r_turb_t >> 16
	and.l	d6,d0			; d0 = (r_turb_t>>16) & 127
	lsl.l	#2,d0			; d0 *= 4 (int array)
	move.l	(a2,d0.l),d0		; d0 = r_turb_turb[index]
	add.l	d2,d0			; d0 = r_turb_s + turb
	swap	d0			; d0 = (r_turb_s + turb) >> 16
	and.w	#63,d0			; d0 = sturb (0-63)

	; tturb = ((r_turb_t + r_turb_turb[(r_turb_s>>16)&127])>>16)&63
	move.l	d2,d1			; d1 = r_turb_s
	swap	d1			; d1 = r_turb_s >> 16
	and.l	d6,d1			; d1 = (r_turb_s>>16) & 127
	lsl.l	#2,d1			; d1 *= 4 (int array)
	move.l	(a2,d1.l),d1		; d1 = r_turb_turb[index]
	add.l	d3,d1			; d1 = r_turb_t + turb
	swap	d1			; d1 = (r_turb_t + turb) >> 16
	and.w	#63,d1			; d1 = tturb (0-63)

	; Calculate texture offset: tturb*64 + sturb
	lsl.w	#6,d1			; d1 = tturb << 6
	add.w	d0,d1			; d1 = (tturb<<6) + sturb

	; Fetch texel and write
	move.b	(a0,d1.w),d0		; d0 = texture[offset]
	move.b	d0,(a1)+		; *r_turb_pdest++ = texel

	; Update coordinates
	add.l	d4,d2			; r_turb_s += r_turb_sstep
	add.l	d5,d3			; r_turb_t += r_turb_tstep

	; Loop control
	subq.l	#1,d7			; --r_turb_spancount
	bgt.s	.turb_pixel_loop

	; Write back updated globals
	move.l	d2,(_r_turb_s)
	move.l	d3,(_r_turb_t)
	move.l	a1,(_r_turb_pdest)

	movem.l	(sp)+,d2-d7/a2-a3
	rts

	end
