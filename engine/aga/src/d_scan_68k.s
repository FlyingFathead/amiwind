; AmiWind: upstream AmiQuake (TerribleFire's GCC port, Stephen Leary), src/d_scan_68k.s at revision
; 9c62d905151614af3e788ae3145a0d4ecc8a7bb8, GPL v2 (docs/LICENSING_AND_CREDITS.md). Linked only by the
; upstream engine profile (docs/ENGINE_PROFILES.md); unchanged below this header except the lines
; marked "AmiWind:" (same machine code, no assembler notices).
;
; NovaCoder's Optimized Span Drawing Routines
; Extracted from AmiQuake v1.36 binary
; Direct translation from addresses 0x003746b8 - 0x00375158
;
; D_DrawSpans8: 68040 FPU-optimized 8-bit texture span drawer
; This is called for EVERY textured surface span - the hottest path in Quake
;

	XDEF	_D_DrawSpans8

	; External Quake globals (declared in C code)
	XREF	_d_zistepu
	XREF	_cacheblock
	XREF	_d_viewbuffer
	XREF	_screenwidth
	XREF	_d_pzbuffer
;	XREF	_d_zrowbytes	; AmiWind: never used here (vasm notice 62)
	XREF	_d_zwidth
	XREF	_d_sdivzorigin
	XREF	_d_tdivzorigin
	XREF	_d_ziorigin
	XREF	_d_sdivzstepu
	XREF	_d_tdivzstepu
	XREF	_d_sdivzstepv
	XREF	_d_tdivzstepv
	XREF	_d_zistepv
	XREF	_sadjust
	XREF	_tadjust
	XREF	_bbextents
;	XREF	_bbextentt	; AmiWind: never used here (vasm notice 62)
	XREF	_cachewidth

	section	text,code

; Macro for clamping s/t coordinates to texture bounds
; \1 = register with value
; \2 = register with limit
; \3 = minimum value
clamp_coord	macro
	cmp.l	\2,\1
	ble.s	.clamp_ok\@
	move.l	\2,\1
	bra.s	.clamp_done\@
.clamp_ok\@:
	cmp.l	#\3,\1
	bge.s	.clamp_done\@
	move.l	#\3,\1
.clamp_done\@:
	endm

;
; D_DrawSpans8 - Main 8-bit span drawer
; Entry: a0 = espan_t *pspan (linked list of spans)
;
; espan_t structure:
;   +0: u (int)
;   +4: v (int)
;   +8: count (int)
;   +12: pnext (espan_t *)
;
_D_DrawSpans8:
	; Save FPU and integer registers
	fmovem.x fp2-fp5,-(sp)
	movem.l	d2-d7/a2-a6,-(sp)

	; Get parameter from stack (GCC calling convention, not vbcc A0 register)
	; After prologue: SP -> [saved regs: 92 bytes][return addr: 4][param: 4]
	; Parameter offset = 92 + 4 + 4 = 100 bytes from current SP
	movea.l	(100,sp),a6		; a6 = pspan from stack

	; Load and prepare constants
	fmove.s	(_d_zistepu),fp2	; fp2 = d_zistepu
	fmove.s	#65536.0,fp3		; fp3 = constant for 1/z calc
	fdiv.x	fp2,fp3			; fp3 = 65536.0 / d_zistepu

	; Load base pointers
	movea.l	(_cacheblock),a0	; a0 = texture base pointer

	; Pre-multiply for z-buffer (matches Ghidra @ 003746dc)
	fmul.s	#32768.0,fp2		; fp2 = d_zistepu * 32768.0

	; Load bounds for coordinate clamping (matches Ghidra @ 003746e4-003746ea)
	movea.l	(_bbextents),a4		; a4 = bbextents (max S coordinate)
	movea.l	(_sadjust),a5		; a5 = sadjust (S offset)

	; Convert izi step to integer (matches Ghidra @ 003746f0)
	fmove.l	fp2,d6			; d6 = izistep for z-buffer

.span_loop:
	; Get span pixel count
	move.l	8(a6),d7		; d7 = pspan->count
	ble.w	.next_span		; Skip empty spans

	; Load span u, v coordinates
	move.l	(a6),d0			; d0 = pspan->u
	fmove.l	d0,fp4			; fp4 = (float)u
	fmove.s	(_d_sdivzstepu),fp0	; fp0 = d_sdivzstepu
	fmul.x	fp4,fp0			; fp0 = u * d_sdivzstepu

	move.l	4(a6),d1		; d1 = pspan->v
	fmove.l	d1,fp5			; fp5 = (float)v
	fmove.s	(_d_sdivzstepv),fp1	; fp1 = d_sdivzstepv
	fmul.x	fp5,fp1			; fp1 = v * d_sdivzstepv

	; Calculate framebuffer destination: d_viewbuffer + v*screenwidth + u
	movea.l	(_d_viewbuffer),a1	; a1 = framebuffer base
	move.l	d1,d2
	mulu.l	(_screenwidth),d2	; d2 = v * screenwidth
	adda.l	d0,a1			; a1 += u
	adda.l	d2,a1			; a1 = final framebuffer pointer

	; Complete s/z calculation
	fadd.x	fp1,fp0			; fp0 = u*d_sdivzstepu + v*d_sdivzstepv
	fadd.s	(_d_sdivzorigin),fp0	; fp0 = sdivz

	; Calculate t/z
	fmove.s	(_d_tdivzstepu),fp1
	fmul.x	fp4,fp1			; fp1 = u * d_tdivzstepu
	move.l	d1,d2			; d2 = v (for z-buffer calc)
	fmove.s	(_d_tdivzstepv),fp2
	fmul.x	fp5,fp2			; fp2 = v * d_tdivzstepv

	; Calculate z-buffer pointer: d_pzbuffer + (v*d_zwidth + u)*2 (matches Ghidra @ 0037475a-00374786)
	movea.l	(_d_pzbuffer),a2	; a2 = z-buffer base
	mulu.l	(_d_zwidth),d2		; d2 = v * d_zwidth
	moveq	#-1,d1			; d1 = -1 for transparency check later
	add.l	d0,d2			; d2 = v * d_zwidth + u
	add.l	d2,d2			; d2 *= 2 (word offset)
	adda.l	d2,a2			; a2 = z-buffer pointer

	fadd.x	fp2,fp1			; fp1 = u*d_tdivzstepu + v*d_tdivzstepv
	fadd.s	(_d_tdivzorigin),fp1	; fp1 = tdivz

	; Calculate initial 1/z
	fmove.s	(_d_zistepu),fp0
	fmul.x	fp4,fp0
	fmove.s	(_d_zistepv),fp1
	fmul.x	fp5,fp1
	fadd.x	fp1,fp0
	fadd.s	(_d_ziorigin),fp0	; fp0 = zi

	; Perspective divide: z = 65536.0 / zi
	fmove.s	#65536.0,fp1
	fdiv.x	fp0,fp1			; fp1 = z

	; Calculate texture coordinates (16.16 fixed point)
	; s = (int)(sdivz * z) + sadjust
	fmove.s	(_d_sdivzstepu),fp0
	fmul.x	fp4,fp0
	fmove.s	(_d_sdivzstepv),fp2
	fmul.x	fp5,fp2
	fadd.x	fp2,fp0
	fadd.s	(_d_sdivzorigin),fp0	; fp0 = sdivz
	fmul.x	fp1,fp0			; fp0 = sdivz * z
	fmove.l	fp0,d2			; d2 = s (16.16)
	add.l	(_sadjust),d2

	; Clamp s to texture bounds (A4 = bbextents)
	move.l	a4,d0
	cmp.l	d0,d2
	ble.s	.s_ok
	move.l	d0,d2
	bra.s	.s_clamped
.s_ok:
	tst.l	d2
	bpl.s	.s_clamped
	moveq	#0,d2
.s_clamped:

	; Calculate t = (int)(tdivz * z) + tadjust
	fmove.s	(_d_tdivzstepu),fp0
	fmul.x	fp4,fp0
	fmove.s	(_d_tdivzstepv),fp2
	fmul.x	fp5,fp2
	fadd.x	fp2,fp0
	fadd.s	(_d_tdivzorigin),fp0	; fp0 = tdivz
	fmul.x	fp1,fp0			; fp0 = tdivz * z
	fmove.l	fp0,d3			; d3 = t (16.16)
	add.l	(_tadjust),d3

	; Clamp t to texture bounds (A5 = bbextentt)
	move.l	a5,d0
	cmp.l	d0,d3
	ble.s	.t_ok
	move.l	d0,d3
	bra.s	.t_clamped
.t_ok:
	tst.l	d3
	bpl.s	.t_clamped
	moveq	#0,d3
.t_clamped:

	; Calculate next s,t for 8 pixels ahead
	fmove.s	(_d_sdivzstepu),fp5
	fmul.s	#8.0,fp5
	fmove.l	d7,fp4			; fp4 = spancount - 1
	fsub.s	#1.0,fp4
	fmul.x	fp4,fp5
	fmove.s	(_d_sdivzstepu),fp0
	fmul.x	fp4,fp0
	fmove.s	(_d_sdivzstepv),fp2
	fmul.x	fp5,fp2
	fadd.x	fp2,fp0
	fadd.s	(_d_sdivzorigin),fp0
	fmul.x	fp3,fp0			; Perspective divide
	fmove.l	fp0,d4			; d4 = snext
	add.l	(_sadjust),d4

	; Clamp snext (A4 = bbextents)
	move.l	a4,d0
	cmp.l	d0,d4
	ble.s	.snext_ok
	move.l	d0,d4
	bra.s	.snext_clamped
.snext_ok:
	cmp.l	#8,d4
	bge.s	.snext_clamped
	moveq	#8,d4
.snext_clamped:

	; Calculate s step: sstep = (snext - s) / (count - 1)
	move.l	d7,d0
	subq.l	#1,d0
	ble.s	.no_divide
	sub.l	d2,d4
	divs.l	d0,d4		; d4 = sstep (AmiWind: was divsl.l d0,d4:d4, the same instruction; vasm notice 2066)
.no_divide:

	; Load texture width
	move.l	(_cachewidth),d0

	; ===== CRITICAL INNER LOOP - Called for every pixel =====
.pixel_loop:
	; Get texture coordinate (s >> 16)
	move.l	d2,d0
	swap	d0			; d0.w = s integer part

	; Fetch texel: pbase[s>>16 + (t>>16)*cachewidth]
	move.l	d3,d1
	swap	d1			; d1.w = t integer part
	mulu.w	(_cachewidth),d1	; d1 = (t>>16) * cachewidth
	add.w	d1,d0			; d0 = offset into texture
	movea.l	a0,a3
	adda.w	d0,a3
	move.b	(a3),d3			; d3 = texel color (use D3 to match Ghidra)

	; Transparency check (matches Ghidra @ 0037480c)
	cmp.b	d1,d3			; Compare with -1 (transparent)
	beq.s	.skip_pixel

	; Z-buffer depth test (matches Ghidra @ 00374810)
	cmp.w	(a2),d6			; Compare *pz with izi
	ble.s	.skip_pixel		; Skip if existing pixel is closer

	; Write z-buffer and pixel (matches Ghidra @ 00374814-00374816)
	move.w	d6,(a2)			; Update z-buffer
	move.b	d3,(a1)			; Write pixel

.skip_pixel:
	; Advance to next pixel
	add.l	d4,d2			; s += sstep
	addq.l	#2,a2			; z-buffer++ (word)
	addq.l	#1,a1			; framebuffer++ (byte)
	subq.l	#1,d7			; count--
	bgt.s	.pixel_loop
	; ===== END INNER LOOP =====

.next_span:
	; Move to next span in linked list
	lea	12(a6),a6		; a6 = &pspan->pnext
	moveq	#-128,d0
	cmp.l	8(a6),d0		; Check for end marker
	bne.w	.span_loop

	; Restore and return
	movem.l	(sp)+,d2-d7/a2-a6
	fmovem.x (sp)+,fp2-fp5
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
