; ---------------------------------------------------------------------------
; Stronkie Soft boot intro  -  "SSIntro"
; Created By Mark Stronks, Stronkie Soft (c) 2026
; Music: "intro numma" by Animal of Superior Art Creations (1996), used with credit
;
; Amiga 500, 68000, Kickstart 1.3 - 3.1, 512K+ chip. Runs from the
; startup-sequence before a game, then gives the system back.
; Mouse button, fire button or any key skips it.
;
; vasmm68k_mot -m68000 -Fhunkexe -kick1hunks -nosym -o SSIntro intro.s
; ---------------------------------------------------------------------------

CUSTOM		equ	$dff000
PLSZ		equ	40*256			; one bitplane
DMACON		equ	$96
INTENA		equ	$9a
INTREQ		equ	$9c
COP1LC		equ	$80
COPJMP1		equ	$88

; copper list layout (see buildcop)
COPCOLS		equ	76			; offset of the 32 colour moves
COPLINES	equ	204			; offset of the 256 line entries
COPSIZE		equ	COPLINES+256*16+4+4

; timeline (frames, 50 per second)
T_MASCOT	equ	16
T_WORD1		equ	60
T_WORD2		equ	100
T_PRES		equ	150
T_CREDITS	equ	200
T_SHINE		equ	140
T_FADE		equ	500			; fade out after 10 seconds

; channel structure of the music player
CH_SPTR		equ	0
CH_SLEN		equ	4
CH_LPTR		equ	6
CH_LLEN		equ	10
CH_VOL		equ	12
CH_PER		equ	14
CH_TPT		equ	16
CH_TPS		equ	18
CH_VIBPOS	equ	20
CH_VIBCMD	equ	21
CH_CMD		equ	22
CH_SMP		equ	24
CH_SIZE		equ	32

	section	code,code

start:	move.l	4.w,a6
	lea	gfxname(pc),a1
	moveq	#0,d0
	jsr	-552(a6)			; OpenLibrary
	move.l	d0,gfxbase
	beq	.nogfx
	move.l	d0,a6
	move.l	34(a6),oldview
	move.l	38(a6),oldcop
	sub.l	a1,a1
	jsr	-222(a6)			; LoadView(0)
	jsr	-270(a6)			; WaitTOF
	jsr	-270(a6)
	move.l	4.w,a6
	jsr	-132(a6)			; Forbid
	lea	CUSTOM,a5
	move.w	$1c(a5),oldint
	move.w	$02(a5),olddma
	move.w	#$7fff,INTENA(a5)
	move.w	#$7fff,INTREQ(a5)
	bsr	waitvb
	move.w	#$7fff,DMACON(a5)
	move.w	#$000f,DMACON(a5)

	bsr	init
	move.b	$bfe801,lasttod
	move.l	frontcop,COP1LC(a5)
	move.w	d0,COPJMP1(a5)
	move.w	#$83c0,DMACON(a5)		; DMA on: bitplanes, copper, blitter

	bsr	mainloop

	bsr	mt_end
	bsr	waitvb
	move.w	#$7fff,DMACON(a5)
	move.l	oldcop,COP1LC(a5)
	move.w	d0,COPJMP1(a5)
	move.w	olddma,d0
	or.w	#$8000,d0
	move.w	d0,DMACON(a5)
	move.w	#$7fff,INTREQ(a5)
	move.w	oldint,d0
	or.w	#$c000,d0
	move.w	d0,INTENA(a5)
	move.l	gfxbase,a6
	move.l	oldview,a1
	jsr	-222(a6)			; LoadView(old)
	jsr	-270(a6)
	jsr	-270(a6)
	move.l	4.w,a6
	jsr	-138(a6)			; Permit
	move.l	gfxbase,a1
	jsr	-414(a6)			; CloseLibrary
.nogfx	moveq	#0,d0
	rts

; wait for raster line 300 (bottom border, just before vertical blank)
waitvb:
.w	move.l	4(a5),d0
	and.l	#$1ff00,d0
	cmp.l	#300<<8,d0
	bne.s	.w
	rts

; ---------------------------------------------------------------------------
init:	lea	coplistA,a0
	move.l	a0,frontcop
	bsr	buildcop
	lea	coplistB,a0
	move.l	a0,backcop
	bsr	buildcop
	; stars
	lea	stars,a0
	move.l	#$2c81a37f,d1			; random seed
	moveq	#47,d7
.s	mulu.w	#25173,d1
	add.l	#13849,d1
	move.l	d1,d0
	swap	d0
	and.w	#$1ff,d0
	cmp.w	#320,d0
	blo.s	.sx
	sub.w	#192,d0
.sx	move.w	d0,(a0)+			; x
	move.w	d7,d0
	mulu.w	#5,d0				; spread the rows 0..240
	add.w	d1,d0
	and.w	#3,d0
	move.w	d7,d2
	mulu.w	#5,d2
	add.w	d0,d2
	mulu.w	#40,d2
	move.w	d2,(a0)+			; row offset
	move.w	d7,d0
	and.w	#3,d0
	lsr.w	#1,d0
	addq.w	#1,d0
	btst	#0,d7
	beq.s	.sp
	addq.w	#1,d0
.sp	move.w	d0,(a0)+			; speed 1..3
	dbra	d7,.s
	; objects not drawn yet
	move.w	#-1000,obj_mascot+8
	move.w	#-1000,obj_word1+8
	move.w	#-1000,obj_word2+8
	bra	mt_init

; build one copper list at a0
buildcop:
	move.l	#$01005200,(a0)+		; 5 bitplanes, colour
	move.l	#$01020000,(a0)+
	move.l	#$01040000,(a0)+
	move.l	#$008e2c81,(a0)+		; display window
	move.l	#$00902cc1,(a0)+
	move.l	#$00920038,(a0)+		; data fetch
	move.l	#$009400d0,(a0)+
	move.l	#$01080000,(a0)+		; modulos
	move.l	#$010a0000,(a0)+
	move.l	#screen,d0
	move.w	#$00e0,d1
	moveq	#4,d2
.p	move.w	d1,(a0)+
	swap	d0
	move.w	d0,(a0)+
	addq.w	#2,d1
	move.w	d1,(a0)+
	swap	d0
	move.w	d0,(a0)+
	addq.w	#2,d1
	add.l	#PLSZ,d0
	dbra	d2,.p
	move.w	#$0180,d1
	moveq	#31,d2
.c	move.w	d1,(a0)+
	clr.w	(a0)+
	addq.w	#2,d1
	dbra	d2,.c
	moveq	#0,d3
.l	cmp.w	#212,d3
	bne.s	.nw
	move.l	#$ffdffffe,(a0)+		; past line 255
.nw	move.w	d3,d0
	add.w	#$2c,d0
	lsl.w	#8,d0
	or.w	#$07,d0
	move.w	d0,(a0)+
	move.w	#$fffe,(a0)+
	move.l	#$01800000,(a0)+
	move.l	#$01840000,(a0)+
	move.l	#$01880000,(a0)+
	addq.w	#1,d3
	cmp.w	#256,d3
	bne.s	.l
	move.l	#$fffffffe,(a0)+
	rts

; ---------------------------------------------------------------------------
mainloop:
	bsr	waitvb
	move.l	backcop,d0			; show the list built last frame
	move.l	d0,COP1LC(a5)
	move.l	frontcop,backcop
	move.l	d0,frontcop
	move.b	$bfe801,d0			; CIA-A TOD counts the frames
	sub.b	lasttod,d0
	add.b	d0,lasttod
	and.w	#$ff,d0
	bne.s	.d1
	moveq	#1,d0
.d1	cmp.w	#4,d0
	bls.s	.d2
	moveq	#4,d0
.d2	subq.w	#1,d0
	move.w	d0,-(sp)
.tick	bsr	mt_music			; music and fades keep real time,
	move.w	mt_trig,d0			; even if a frame took too long
	or.w	d0,trigacc
	bsr	fadelogic
	addq.w	#1,frame
	subq.w	#1,(sp)
	bpl.s	.tick
	addq.l	#2,sp
	bsr	input
	bsr	logic
	bsr	movestars
	bsr	makebars
	bsr	updcop
	tst.w	quit
	beq.s	mainloop
	rts

; mouse button / fire / any key -> skip (only after everything was let go once)
input:	moveq	#0,d1				; d1 = something pressed
	move.b	$bfe001,d0
	not.b	d0
	and.b	#$c0,d0
	beq.s	.nob
	moveq	#1,d1
.nob	move.b	$bfed01,d0			; keyboard: CIA-A ICR
	btst	#3,d0
	beq.s	.nok
	move.b	$bfec01,d2
	bset	#6,$bfee01			; handshake
	moveq	#2,d3
.h1	move.b	6(a5),d0
.h2	cmp.b	6(a5),d0
	beq.s	.h2
	dbra	d3,.h1
	bclr	#6,$bfee01
	not.b	d2
	ror.b	#1,d2
	btst	#7,d2
	bne.s	.nok				; key released
	moveq	#2,d1				; a key went down
.nok	tst.w	armed
	bne.s	.arm
	tst.w	d1
	bne.s	.x
	move.w	#1,armed			; all let go: skipping allowed now
	rts
.arm	cmp.w	#2,d1				; keys only arrive when pressed
	beq.s	.skip
	tst.w	d1
	beq.s	.x
.skip	tst.w	fading
	beq.s	.f
	move.w	#1,fspeed			; already fading: go faster
	rts
.f	move.w	#1,fading
	move.w	#1,fspeed
.x	rts

; ---------------------------------------------------------------------------
fadelogic:
	move.w	frame,d6
	tst.w	fading
	bne.s	.fo
	cmp.w	#T_FADE,d6
	blo.s	.fi
	move.w	#1,fading
	move.w	#3,fspeed
	bra.s	.fo
.fi	move.w	d6,d0
	lsr.w	#1,d0
	cmp.w	#16,d0
	bls.s	.g
	moveq	#16,d0
.g	move.w	d0,glevel
	bra.s	.fdone
.fo	addq.w	#1,fcount
	move.w	fcount,d0
	cmp.w	fspeed,d0
	blo.s	.fdone
	clr.w	fcount
	tst.w	glevel
	beq.s	.end
	subq.w	#1,glevel
	bra.s	.fdone
.end	move.w	#1,quit
.fdone	move.w	glevel,d0
	lsl.w	#2,d0
	move.w	d0,mt_master			; music follows the fade
	rts

logic:	move.w	frame,d6
	; --- the mascot drops in
	move.w	d6,d0
	sub.w	#T_MASCOT,d0
	bmi.s	.nom
	cmp.w	#MASCOTN,d0
	blo.s	.m1
	move.w	#MASCOTN-1,d0
.m1	add.w	d0,d0
	lea	mascot_y,a0
	move.w	(a0,d0.w),d0
	lea	obj_mascot,a3
	bsr	moveobj
.nom	; --- STRONKIE rises
	move.w	d6,d0
	sub.w	#T_WORD1,d0
	bmi.s	.now1
	cmp.w	#WORDN,d0
	blo.s	.w1
	move.w	#WORDN-1,d0
.w1	add.w	d0,d0
	lea	word1_y,a0
	move.w	(a0,d0.w),d0
	lea	obj_word1,a3
	bsr	moveobj
.now1	; --- SOFT rises
	move.w	d6,d0
	sub.w	#T_WORD2,d0
	bmi.s	.now2
	cmp.w	#WORDN,d0
	blo.s	.w2
	move.w	#WORDN-1,d0
.w2	add.w	d0,d0
	lea	word2_y,a0
	move.w	(a0,d0.w),d0
	lea	obj_word2,a3
	bsr	moveobj
.now2	; --- PRESENTS types itself (one letter every 5 frames)
	move.w	d6,d0
	sub.w	#T_PRES,d0
	bmi.s	.nop
	ext.l	d0
	divu.w	#5,d0
	cmp.w	#8,d0
	bhs.s	.nop
	swap	d0
	tst.w	d0
	bne.s	.nop
	swap	d0
	add.w	d0,d0
	add.w	#12,d0				; byte column
	move.w	d0,d1
	move.w	#168,d0				; rows 168..187
	moveq	#20,d2
	moveq	#1,d3				; 1 word wide
	bsr	reveal
.nop	; --- credits: put them on screen, then fade them in
	cmp.w	#T_CREDITS,d6
	bne.s	.noc
	move.w	#218,d0
	moveq	#0,d1
	moveq	#28,d2
	moveq	#20,d3
	bsr	reveal
.noc	cmp.w	#T_CREDITS,d6
	blo.s	.nocf
	move.w	d6,d0
	sub.w	#T_CREDITS,d0
	lsr.w	#1,d0
	cmp.w	#16,d0
	bls.s	.cf
	moveq	#16,d0
.cf	move.w	d0,clevel
.nocf	; --- blink every 160 frames once the mascot has landed
	cmp.w	#120,d6
	blo.s	.nobl
	move.w	d6,d0
	sub.w	#120,d0
	ext.l	d0
	divu.w	#160,d0
	swap	d0
	tst.w	d0
	bne.s	.bl2
	lea	eyes_closed,a0
	bsr	eyes
	bra.s	.nobl
.bl2	cmp.w	#7,d0
	bne.s	.nobl
	lea	final+102*40,a0			; eyes open again
	bsr	eyesfinal
.nobl	; --- music sync: kick drum lights the antenna, snare starts the shine
	move.w	trigacc,d0
	clr.w	trigacc
	btst	#0,d0
	beq.s	.nosync
	lea	mt_chan,a0
	move.w	CH_SMP(a0),d1
	cmp.w	#4,d1
	bne.s	.nokick
	move.w	#8,bulb
.nokick	cmp.w	#3,d1
	bne.s	.nosync
	cmp.w	#T_SHINE,d6
	blo.s	.nosync
	tst.w	shinegap
	bne.s	.nosync
	move.w	#56,shiney
	move.w	#45,shinegap
.nosync	tst.w	bulb
	beq.s	.b0
	subq.w	#1,bulb
.b0	tst.w	shinegap
	beq.s	.s0
	subq.w	#1,shinegap
.s0	cmp.w	#200,shiney
	bhs.s	.s1
	addq.w	#4,shiney
.s1	rts

; move a picture part from the final picture to row d0 (a3 = object)
; object: bx (bytes), words, top row, height, current row
moveobj:
	movem.l	d0-d7/a0-a4,-(sp)
	move.w	8(a3),d7			; current
	cmp.w	d0,d7
	beq	.done
	move.w	6(a3),d6			; height
	move.w	d0,d5				; new top
	move.w	2(a3),d2
	lsr.w	#1,d2				; longs per row
	cmp.w	#-1000,d7
	beq.s	.draw
	; clear the old rows that the new position does not cover
	move.w	d6,d4
	subq.w	#1,d4
	move.w	d7,d3				; row
	move.w	d5,a4
	add.w	d6,a4				; new bottom + 1
.cl	cmp.w	d5,d3
	blt.s	.doc
	cmp.w	a4,d3
	blt.s	.nc
.doc	tst.w	d3
	bmi.s	.nc
	cmp.w	#256,d3
	bge.s	.nc
	move.w	d3,d0
	mulu.w	#40,d0
	add.w	(a3),d0
	lea	screen,a1
	add.l	d0,a1
	bsr	clearrowl
.nc	addq.w	#1,d3
	dbra	d4,.cl
.draw	move.w	4(a3),d0			; first source row
	mulu.w	#40,d0
	add.w	(a3),d0
	lea	final,a0
	add.l	d0,a0
	move.w	d5,d0
	muls.w	#40,d0
	add.w	(a3),d0
	ext.l	d0
	lea	screen,a1
	add.l	d0,a1
	move.w	d6,d4
	subq.w	#1,d4
	move.w	d5,d3				; screen row
.dr	tst.w	d3
	bmi.s	.nd
	cmp.w	#256,d3
	bge.s	.dd
	bsr	copyrowl
.nd	lea	40(a0),a0
	lea	40(a1),a1
	addq.w	#1,d3
	dbra	d4,.dr
.dd	move.w	d5,8(a3)
.done	movem.l	(sp)+,d0-d7/a0-a4
	rts

; copy d2 longs x 4 planes from a0 to a1 (registers kept)
copyrowl:
	movem.l	d0/a0-a2,-(sp)
	move.l	a1,a2
	move.w	d2,d0
	subq.w	#1,d0
.p0	move.l	(a0),(a2)
	move.l	PLSZ(a0),PLSZ(a2)
	move.l	2*PLSZ(a0),2*PLSZ(a2)
	move.l	3*PLSZ(a0),3*PLSZ(a2)
	addq.l	#4,a0
	addq.l	#4,a2
	dbra	d0,.p0
	movem.l	(sp)+,d0/a0-a2
	rts

clearrowl:
	movem.l	d0-d1/a1,-(sp)
	moveq	#0,d1
	move.w	d2,d0
	subq.w	#1,d0
.c	move.l	d1,(a1)
	move.l	d1,PLSZ(a1)
	move.l	d1,2*PLSZ(a1)
	move.l	d1,3*PLSZ(a1)
	addq.l	#4,a1
	dbra	d0,.c
	movem.l	(sp)+,d0-d1/a1
	rts

; copy d2 words x 4 planes from a0 (final) to a1 (screen)
copyrow:
	movem.l	d0-d1/a0-a1,-(sp)
	moveq	#3,d1
.p	movem.l	a0-a1,-(sp)
	move.w	d2,d0
	subq.w	#1,d0
.w	move.w	(a0)+,(a1)+
	dbra	d0,.w
	movem.l	(sp)+,a0-a1
	lea	PLSZ(a0),a0
	lea	PLSZ(a1),a1
	dbra	d1,.p
	movem.l	(sp)+,d0-d1/a0-a1
	rts

clearrow:
	movem.l	d0-d1/a1,-(sp)
	moveq	#3,d1
.p	move.l	a1,-(sp)
	move.w	d2,d0
	subq.w	#1,d0
.w	clr.w	(a1)+
	dbra	d0,.w
	move.l	(sp)+,a1
	lea	PLSZ(a1),a1
	dbra	d1,.p
	movem.l	(sp)+,d0-d1/a1
	rts

; copy a block from the final picture: d0 top row, d1 byte column,
; d2 rows, d3 words wide
reveal:	movem.l	d0-d4/a0-a1,-(sp)
	move.w	d2,d4
	subq.w	#1,d4
	move.w	d3,d2
.r	move.w	d0,d3
	mulu.w	#40,d3
	add.w	d1,d3
	lea	final,a0
	add.l	d3,a0
	lea	screen,a1
	add.l	d3,a1
	bsr	copyrow
	addq.w	#1,d0
	dbra	d4,.r
	movem.l	(sp)+,d0-d4/a0-a1
	rts

; eyes: copy 8 rows x 12 bytes (planes stored one after another) to rows 102..109
eyes:	lea	screen+102*40,a1
	moveq	#3,d1
.p	moveq	#7,d2
	move.l	a1,a2
.r	move.l	(a0)+,(a2)
	move.l	(a0)+,4(a2)
	move.l	(a0)+,8(a2)
	lea	40(a2),a2
	dbra	d2,.r
	lea	PLSZ(a1),a1
	dbra	d1,.p
	rts
eyesfinal:
	move.w	#102,d0
	moveq	#0,d1
	moveq	#8,d2
	moveq	#6,d3
	bra	reveal

; ---------------------------------------------------------------------------
; stars in bitplane 5 (they only show where the picture is empty)
movestars:
	lea	stars,a0
	lea	screen+4*PLSZ,a1
	moveq	#47,d7
.s	move.w	(a0)+,d0			; x
	move.w	(a0)+,d1			; row offset
	move.w	(a0)+,d2			; speed
	move.w	d0,d3
	lsr.w	#3,d3
	add.w	d1,d3
	moveq	#7,d4
	and.w	d0,d4
	eor.w	#7,d4
	bclr	d4,(a1,d3.w)
	sub.w	d2,d0
	bpl.s	.ok
	add.w	#320,d0
.ok	move.w	d0,-6(a0)
	move.w	d0,d3
	lsr.w	#3,d3
	add.w	d1,d3
	moveq	#7,d4
	and.w	d0,d4
	eor.w	#7,d4
	bset	d4,(a1,d3.w)
	dbra	d7,.s
	rts

; raster bars: background gradient + three bouncing bars into linebuf
makebars:
	lea	basegrad,a0
	lea	linebuf,a1
	move.w	#127,d0
.c	move.l	(a0)+,(a1)+
	dbra	d0,.c
	lea	sinetab,a2
	lea	bar1,a0
	move.w	frame,d0
	mulu.w	#3,d0
	moveq	#100,d1
	bsr	.bar
	lea	bar2,a0
	move.w	frame,d0
	mulu.w	#5,d0
	add.w	#85,d0
	moveq	#90,d1
	bsr	.bar
	lea	bar3,a0
	move.w	frame,d0
	lsl.w	#2,d0
	add.w	#170,d0
	moveq	#105,d1
.bar	and.w	#255,d0
	add.w	d0,d0
	move.w	(a2,d0.w),d0
	muls.w	d1,d0
	add.l	d0,d0
	swap	d0				; -amp..amp
	add.w	#120,d0				; top line of the bar
	add.w	d0,d0
	lea	linebuf,a1
	add.w	d0,a1
	moveq	#14,d2
.b	move.w	(a0)+,(a1)+
	dbra	d2,.b
	rts

; colour d0 ($0RGB) faded with table a2 (16 bytes) -> d0
fadec:	move.w	d0,d1
	and.w	#$f,d1
	move.b	(a2,d1.w),d1
	move.w	d0,d2
	lsr.w	#4,d2
	and.w	#$f,d2
	move.b	(a2,d2.w),d2
	lsl.w	#4,d2
	or.w	d2,d1
	lsr.w	#8,d0
	and.w	#$f,d0
	move.b	(a2,d0.w),d0
	lsl.w	#8,d0
	or.w	d1,d0
	rts

; write all colours of this frame into the back copper list
updcop:	move.l	backcop,a3
	lea	fadetab,a2
	move.w	glevel,d0
	lsl.w	#4,d0
	add.w	d0,a2				; a2 = global fade
	lea	fadetab,a4
	move.w	clevel,d0
	cmp.w	glevel,d0
	bls.s	.cl
	move.w	glevel,d0
.cl	lsl.w	#4,d0
	add.w	d0,a4				; a4 = credits fade
	; header colours
	lea	palette,a0
	lea	COPCOLS+2(a3),a1
	moveq	#0,d7
.col	move.w	(a0)+,d0
	move.w	d7,d3
	and.w	#15,d3
	cmp.w	#8,d3				; antenna bulb
	bne.s	.nb
	lea	bulbtab,a6
	move.w	bulb,d0
	add.w	d0,d0
	move.w	(a6,d0.w),d0
.nb	cmp.w	#10,d3
	beq.s	.cr
	cmp.w	#11,d3
	beq.s	.cr
	bsr	fadec
	bra.s	.st
.cr	move.l	a2,-(sp)
	move.l	a4,a2
	bsr	fadec
	move.l	(sp)+,a2
.st	move.w	d0,(a1)
	addq.l	#4,a1
	addq.w	#1,d7
	cmp.w	#32,d7
	bne.s	.col
	; faded yellow / orange and the shine band
	move.w	palette+4,d0
	bsr	fadec
	move.w	d0,fc2
	move.w	palette+8,d0
	bsr	fadec
	move.w	d0,fc4
	lea	shine2,a0
	lea	shinef,a1
	moveq	#19,d7
.sh	move.w	(a0)+,d0
	bsr	fadec
	move.w	d0,(a1)+
	dbra	d7,.sh
	; the 256 lines
	lea	COPLINES+6(a3),a1
	lea	linebuf,a0
	move.w	shiney,d5
	moveq	#0,d7
.ln	cmp.w	#212,d7
	bne.s	.n1
	addq.l	#4,a1
.n1	move.w	(a0)+,d0
	cmp.w	#16,glevel
	beq.s	.nf
	bsr	fadec
.nf	move.w	d0,(a1)
	move.w	d7,d1
	sub.w	d5,d1				; line inside the shine band?
	bmi.s	.plain
	cmp.w	#10,d1
	bhs.s	.plain
	add.w	d1,d1
	lea	shinef,a6
	move.w	(a6,d1.w),4(a1)
	move.w	20(a6,d1.w),8(a1)
	bra.s	.nx
.plain	move.w	fc2,4(a1)
	move.w	fc4,8(a1)
.nx	lea	16(a1),a1
	addq.w	#1,d7
	cmp.w	#256,d7
	bne.s	.ln
	rts

; ===========================================================================
; small ProTracker player (effects 0,1,2,3,4,5,6,A,B,C,D,F)
; ===========================================================================
mt_init:
	lea	mod,a0
	moveq	#0,d0
	move.b	950(a0),d0
	move.w	d0,mt_songlen
	lea	952(a0),a1
	moveq	#127,d1
	moveq	#0,d2
.o	move.b	(a1)+,d0
	cmp.b	d2,d0
	bls.s	.o2
	move.b	d0,d2
.o2	dbra	d1,.o
	addq.w	#1,d2
	mulu.w	#1024,d2
	lea	1084(a0),a1
	add.l	d2,a1				; first sample
	lea	20(a0),a2			; sample headers
	lea	mt_samples,a3
	moveq	#30,d7
.smp	moveq	#0,d0
	move.w	22(a2),d0			; length in words
	move.l	a1,(a3)				; start
	moveq	#0,d1
	move.b	25(a2),d1			; volume
	move.w	d1,8(a3)
	moveq	#0,d1
	move.w	26(a2),d1			; repeat start (words)
	moveq	#0,d2
	move.w	28(a2),d2			; repeat length (words)
	cmp.w	#1,d2
	bls.s	.noloop
	move.l	a1,d3
	add.l	d1,d3
	add.l	d1,d3
	move.l	d3,10(a3)			; loop start
	move.w	d2,14(a3)			; loop length
	add.w	d2,d1
	move.w	d1,4(a3)			; play length = start + loop
	bra.s	.nx
.noloop	move.l	#mt_null,10(a3)
	move.w	#1,14(a3)
	move.w	d0,4(a3)
.nx	add.l	d0,a1
	add.l	d0,a1
	lea	30(a2),a2
	lea	16(a3),a3
	dbra	d7,.smp
	move.w	#6,mt_speed
	move.w	#6,mt_count
	clr.w	mt_pos
	clr.w	mt_row
	move.w	#64,mt_master
	rts

mt_end:	moveq	#0,d0
	move.w	d0,$a8(a5)
	move.w	d0,$b8(a5)
	move.w	d0,$c8(a5)
	move.w	d0,$d8(a5)
	move.w	#$000f,DMACON(a5)
	rts

mt_music:
	clr.w	mt_trig
	addq.w	#1,mt_count
	move.w	mt_count,d0
	cmp.w	mt_speed,d0
	blo	mt_effects
	clr.w	mt_count
; --- a new row
	lea	mod,a0
	move.w	mt_pos,d0
	lea	952(a0),a2
	move.b	(a2,d0.w),d0
	and.w	#$ff,d0
	mulu.w	#1024,d0
	lea	1084(a0),a2
	add.l	d0,a2
	move.w	mt_row,d0
	lsl.w	#4,d0
	add.w	d0,a2				; a2 = row data
	lea	mt_chan,a1
	moveq	#0,d7				; channels to start
	moveq	#0,d6				; channel number
	clr.w	mt_break
.ch	move.l	(a2)+,d0
	move.w	d0,d2
	and.w	#$0fff,d2
	move.w	d2,CH_CMD(a1)
	move.l	d0,d1
	swap	d1
	move.w	d1,d3
	and.w	#$0fff,d3			; period
	and.w	#$f000,d1
	lsr.w	#8,d1
	move.w	d0,d4
	lsr.w	#8,d4
	lsr.w	#4,d4
	or.w	d4,d1				; sample number
	beq.s	.nos
	move.w	d1,CH_SMP(a1)
	subq.w	#1,d1
	lsl.w	#4,d1
	lea	mt_samples,a3
	add.w	d1,a3
	move.l	(a3),CH_SPTR(a1)
	move.w	4(a3),CH_SLEN(a1)
	move.w	8(a3),CH_VOL(a1)
	move.l	10(a3),CH_LPTR(a1)
	move.w	14(a3),CH_LLEN(a1)
.nos	move.w	d2,d4
	and.w	#$0f00,d4
	tst.w	d3
	beq.s	.nop
	cmp.w	#$0300,d4
	beq.s	.tp
	cmp.w	#$0500,d4
	beq.s	.tp
	move.w	d3,CH_PER(a1)
	clr.b	CH_VIBPOS(a1)
	bset	d6,d7
	bra.s	.nop
.tp	move.w	d3,CH_TPT(a1)
.nop	moveq	#0,d5
	move.b	d2,d5				; parameter
	lsr.w	#8,d4				; effect
	cmp.w	#$c,d4
	bne.s	.e1
	cmp.w	#64,d5
	bls.s	.v
	moveq	#64,d5
.v	move.w	d5,CH_VOL(a1)
	bra	.edone
.e1	cmp.w	#$f,d4
	bne.s	.e2
	tst.w	d5
	beq	.edone
	cmp.w	#32,d5
	bhs	.edone
	move.w	d5,mt_speed
	bra	.edone
.e2	cmp.w	#3,d4
	bne.s	.e3
	tst.w	d5
	beq	.edone
	move.w	d5,CH_TPS(a1)
	bra	.edone
.e3	cmp.w	#4,d4
	bne.s	.e4
	move.b	CH_VIBCMD(a1),d0
	move.b	d5,d1
	and.b	#$0f,d1
	beq.s	.v1
	and.b	#$f0,d0
	or.b	d1,d0
.v1	move.b	d5,d1
	and.b	#$f0,d1
	beq.s	.v2
	and.b	#$0f,d0
	or.b	d1,d0
.v2	move.b	d0,CH_VIBCMD(a1)
	bra	.edone
.e4	cmp.w	#$d,d4
	bne.s	.e5
	move.w	d5,d0
	lsr.w	#4,d0
	mulu.w	#10,d0
	and.w	#$f,d5
	add.w	d5,d0
	move.w	d0,mt_brow
	move.w	#1,mt_break
	bra	.edone
.e5	cmp.w	#$b,d4
	bne	.edone
	subq.w	#1,d5
	move.w	d5,mt_pos			; next row goes to d5
	clr.w	mt_brow
	move.w	#1,mt_break
.edone	lea	CH_SIZE(a1),a1
	addq.w	#1,d6
	cmp.w	#4,d6
	bne	.ch
	move.w	d7,mt_trig
; --- start the new notes
	move.w	d7,DMACON(a5)			; stop them
	lea	mt_chan,a1
	lea	$a0(a5),a3
	moveq	#0,d6
.hw	btst	d6,d7
	beq.s	.h1
	move.l	CH_SPTR(a1),(a3)
	move.w	CH_SLEN(a1),4(a3)
.h1	move.w	CH_PER(a1),6(a3)
	bsr	mt_vol
	lea	CH_SIZE(a1),a1
	lea	$10(a3),a3
	addq.w	#1,d6
	cmp.w	#4,d6
	bne.s	.hw
	tst.w	d7
	beq.s	.nodma
	bsr	mt_wait
	move.w	d7,d0
	or.w	#$8000,d0
	move.w	d0,DMACON(a5)
	bsr	mt_wait
	lea	mt_chan,a1
	lea	$a0(a5),a3
	moveq	#0,d6
.lp	btst	d6,d7
	beq.s	.l1
	move.l	CH_LPTR(a1),(a3)
	move.w	CH_LLEN(a1),4(a3)
.l1	lea	CH_SIZE(a1),a1
	lea	$10(a3),a3
	addq.w	#1,d6
	cmp.w	#4,d6
	bne.s	.lp
.nodma	; --- next row
	tst.w	mt_break
	beq.s	.nb
	move.w	mt_brow,mt_row
	bra.s	.np
.nb	addq.w	#1,mt_row
	cmp.w	#64,mt_row
	blo.s	.r
	clr.w	mt_row
.np	addq.w	#1,mt_pos
	move.w	mt_pos,d0
	cmp.w	mt_songlen,d0
	blo.s	.r
	clr.w	mt_pos
	move.w	#1,mt_ended
.r	rts

; volume of channel a1 into hardware a3, scaled by the master volume
mt_vol:	move.w	CH_VOL(a1),d0
	mulu.w	mt_master,d0
	lsr.w	#6,d0
	move.w	d0,8(a3)
	rts

; let the audio DMA pick up the new sample (a few raster lines)
mt_wait:
	moveq	#4,d1
.a	move.b	6(a5),d0
.b	cmp.b	6(a5),d0
	beq.s	.b
	dbra	d1,.a
	rts

; --- the ticks between rows
mt_effects:
	lea	mt_chan,a1
	lea	$a0(a5),a3
	moveq	#3,d7
.ch	move.w	CH_CMD(a1),d2
	moveq	#0,d5
	move.b	d2,d5				; parameter
	move.w	d2,d4
	lsr.w	#8,d4				; effect
	move.w	CH_PER(a1),d3
	beq	.next
	tst.w	d4
	bne.s	.f1
	tst.w	d5				; 0: arpeggio
	beq	.out
	moveq	#0,d0
	move.w	mt_count,d0
	divu.w	#3,d0
	swap	d0
	tst.w	d0
	beq	.out
	cmp.w	#1,d0
	bne.s	.a2
	lsr.w	#4,d5
	bra.s	.a3
.a2	and.w	#$f,d5
.a3	lea	mt_periods,a0
	moveq	#0,d0
.fi	cmp.w	(a0,d0.w),d3
	bhs.s	.fo
	addq.w	#2,d0
	cmp.w	#35*2,d0
	blo.s	.fi
.fo	add.w	d5,d5
	add.w	d5,d0
	cmp.w	#35*2,d0
	bls.s	.a4
	moveq	#35*2,d0
.a4	move.w	(a0,d0.w),6(a3)
	bra	.vol
.f1	cmp.w	#1,d4
	bne.s	.f2
	sub.w	d5,d3
	cmp.w	#113,d3
	bge.s	.s1
	moveq	#113,d3
.s1	move.w	d3,CH_PER(a1)
	bra	.out
.f2	cmp.w	#2,d4
	bne.s	.f3
	add.w	d5,d3
	cmp.w	#856,d3
	ble.s	.s1
	move.w	#856,d3
	bra.s	.s1
.f3	cmp.w	#3,d4
	beq.s	.tp
	cmp.w	#5,d4
	bne.s	.f4
	bsr	.tp0
	bra	.vs
.tp	bsr	.tp0
	bra	.vol
.f4	cmp.w	#4,d4
	beq.s	.vib
	cmp.w	#6,d4
	bne.s	.f5
	bsr	.vib0
	bra	.vs
.vib	bsr	.vib0
	bra	.vol
.f5	cmp.w	#$a,d4
	beq	.vs
	bra	.out
; tone portamento
.tp0	move.w	CH_TPT(a1),d0
	beq.s	.tpx
	move.w	CH_TPS(a1),d1
	cmp.w	d0,d3
	beq.s	.tpx
	blo.s	.up
	sub.w	d1,d3
	cmp.w	d0,d3
	bge.s	.tps
	move.w	d0,d3
	bra.s	.tps
.up	add.w	d1,d3
	cmp.w	d0,d3
	ble.s	.tps
	move.w	d0,d3
.tps	move.w	d3,CH_PER(a1)
.tpx	move.w	d3,6(a3)
	rts
; vibrato
.vib0	moveq	#0,d0
	move.b	CH_VIBPOS(a1),d0
	move.w	d0,d1
	and.w	#31,d1
	lea	mt_vibtab,a0
	moveq	#0,d6
	move.b	(a0,d1.w),d6
	moveq	#0,d1
	move.b	CH_VIBCMD(a1),d1
	and.w	#$f,d1
	mulu.w	d1,d6
	lsr.w	#7,d6
	btst	#5,d0
	beq.s	.vp
	neg.w	d6
.vp	add.w	d3,d6
	move.w	d6,6(a3)
	move.b	CH_VIBCMD(a1),d1
	lsr.b	#4,d1
	add.b	d1,d0
	and.b	#63,d0
	move.b	d0,CH_VIBPOS(a1)
	rts
; volume slide (A, also for 5 and 6)
.vs	move.w	d5,d0
	lsr.w	#4,d0
	beq.s	.vd
	add.w	d0,CH_VOL(a1)
	cmp.w	#64,CH_VOL(a1)
	bls.s	.vol
	move.w	#64,CH_VOL(a1)
	bra.s	.vol
.vd	and.w	#$f,d5
	sub.w	d5,CH_VOL(a1)
	bpl.s	.vol
	clr.w	CH_VOL(a1)
	bra.s	.vol
.out	move.w	CH_PER(a1),6(a3)
.vol	bsr	mt_vol
.next	lea	CH_SIZE(a1),a1
	lea	$10(a3),a3
	dbra	d7,.ch
	rts

mt_periods:
	dc.w	856,808,762,720,678,640,604,570,538,508,480,453
	dc.w	428,404,381,360,339,320,302,285,269,254,240,226
	dc.w	214,202,190,180,170,160,151,143,135,127,120,113
mt_vibtab:
	dc.b	0,24,49,74,97,120,141,161,180,197,212,224,235,244,250,253
	dc.b	255,253,250,244,235,224,212,197,180,161,141,120,97,74,49,24

gfxname	dc.b	"graphics.library",0
	dc.b	"$VER: SSIntro 1.0 (27.11.2026) Stronkie Soft boot intro",0
	even

; --- objects: byte column, words, top row in the final picture, height, current row
obj_mascot:	dc.w	0,6,70,80,0
obj_word1:	dc.w	12,14,70,40,0
obj_word2:	dc.w	12,14,110,40,0

bulbtab:	dc.w	$fe2,$fe4,$fe6,$fe8,$ffa,$ffb,$ffc,$ffe,$fff
shine2:		dc.w	$fe4,$ff7,$ffa,$ffd,$fff,$fff,$ffd,$ffa,$ff7,$fe4
shine4:		dc.w	$ea2,$fb5,$fc8,$fdb,$fee,$fee,$fdb,$fc8,$fb5,$ea2

	include	"tables_gen.s"
	even

	section	pics,data
final:		incbin	"../build/final.bin"
eyes_closed:	incbin	"../build/eyes.bin"

	section	vars,bss
gfxbase		ds.l	1
oldview		ds.l	1
oldcop		ds.l	1
frontcop	ds.l	1
backcop		ds.l	1
oldint		ds.w	1
olddma		ds.w	1
frame		ds.w	1
trigacc		ds.w	1
lasttod		ds.b	1
	even
quit		ds.w	1
armed		ds.w	1
fading		ds.w	1
fspeed		ds.w	1
fcount		ds.w	1
glevel		ds.w	1
clevel		ds.w	1
bulb		ds.w	1
shiney		ds.w	1
shinegap	ds.w	1
fc2		ds.w	1
fc4		ds.w	1
shinef		ds.w	20
linebuf		ds.w	256+32
stars		ds.w	48*3
mt_songlen	ds.w	1
mt_speed	ds.w	1
mt_count	ds.w	1
mt_pos		ds.w	1
mt_row		ds.w	1
mt_break	ds.w	1
mt_brow		ds.w	1
mt_trig		ds.w	1
mt_master	ds.w	1
mt_ended	ds.w	1
mt_samples	ds.b	31*16
mt_chan		ds.b	4*CH_SIZE

	section	chipdata,data_c
mod:		incbin	"../intro.mod"
	even
mt_null:	dc.l	0

	section	chipbss,bss_c
coplistA	ds.b	COPSIZE
coplistB	ds.b	COPSIZE
screen		ds.b	5*PLSZ
