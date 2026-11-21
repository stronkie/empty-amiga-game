;------------------------------------------------------------------------------
;  whdload_slave.s - WHDLoad slave for Stronkie's Slot Machine
;
;  Runs SSlots.game from the install drawer without the Kickstart:
;  the slave loads the game's hunks itself (chip hunks into BaseMem, the rest
;  into ExpMem) and gives it a tiny exec, graphics and dos of its own: the
;  game only opens its libraries, takes the hardware over, and reads and
;  writes its high score file SSlots.hi (these go through resload).
;  F10 quits (the game passes the key on: it reads the keyboard itself),
;  as does QUIT TO WORKBENCH in the menu.
;
;  One code hunk, everything PC-relative, no relocations.
;  Created By Mark Stronks, Stronkie Soft 2026
;------------------------------------------------------------------------------

WHDLF_NoError	equ	1<<1
WHDLF_ClearMem	equ	1<<12
TDREASON_OK	equ	-1
TDREASON_FAILMSG equ	43
resload_Abort	equ	$04
resload_LoadFile equ	$08
resload_SaveFile equ	$0c
resload_FlushCache equ	$20
resload_GetFileSize equ	$24
resload_SaveFileOffset equ $38
resload_LoadFileOffset equ $4c

BASEMEM		equ	$80000		; 512K chip: the game's chip hunks need 330K
EXPMEM		equ	$7a000		; its other hunks need 478K
CHIPSTART	equ	$1000		; chip hunks from here
COPEND		equ	$400		; a copper list that only ends (gfx copinit)
BUFADDR		equ	$70000		; read buffer in BaseMem
BUFSIZE		equ	$4000
MAXHUNKS	equ	16
QUITKEY		equ	$59		; F10

	section	code,code
base:
	moveq	#-1,d0			; ws_Security
	rts
	dc.b	'WHDLOADS'		; ws_ID
	dc.w	17			; ws_Version
	dc.w	WHDLF_NoError|WHDLF_ClearMem	; ws_Flags
	dc.l	BASEMEM			; ws_BaseMemSize
	dc.l	0			; ws_ExecInstall
	dc.w	start-base		; ws_GameLoader
	dc.w	0			; ws_CurrentDir: the install drawer
	dc.w	0			; ws_DontCache
	dc.b	0			; ws_keydebug
	dc.b	QUITKEY			; ws_keyexit
expmem	dc.l	EXPMEM			; ws_ExpMem (WHDLoad puts the address here)
	dc.w	name-base		; ws_name
	dc.w	copy-base		; ws_copy
	dc.w	info-base		; ws_info
	dc.w	0			; ws_kickname: no Kickstart
	dc.l	0			; ws_kicksize
	dc.w	0			; ws_kickcrc
	dc.w	0			; ws_config

name	dc.b	"Stronkie's Slot Machine",0
copy	dc.b	'2026 Mark Stronks, Stronkie Soft',0
info	dc.b	'Installed by Mark Stronks',10
	include	"slave_ver.i"		; dc.b 'Version x.y (date)',10 (tools/build.sh)
	dc.b	'F10 quits',0
gamename dc.b	'SSlots.game',0
badgame	dc.b	'SSlots.game is missing or damaged',0
	even

;------------------------------------------------------------------------------
start:					; a0 = resload
	lea	resload(pc),a1
	move.l	a0,(a1)
	lea	stack_save(pc),a1
	move.l	sp,(a1)

	lea	COPEND,a0		; a copper list for gfxbase->copinit
	move.l	#$fffffffe,(a0)

	bsr	make_libs
	bsr	load_game
	tst.l	d0
	beq	fail

	move.l	resload(pc),a2		; new code: flush the caches
	jsr	resload_FlushCache(a2)

	lea	execbase(pc),a0		; ExecBase
	move.l	a0,4.w
	lea	hunk_base(pc),a0
	move.l	(a0),a1			; the game starts at its first hunk
	lea	quit(pc),a0		; F10 in the game comes here
	move.l	#'WHDL',d7
	jsr	(a1)
quit	move.l	stack_save(pc),sp	; QUIT TO WORKBENCH or F10
	pea	TDREASON_OK
	move.l	resload(pc),a0
	jmp	resload_Abort(a0)

fail	pea	badgame(pc)
	pea	TDREASON_FAILMSG
	move.l	resload(pc),a0
	jmp	resload_Abort(a0)

;------------------------------------------------------------------------------
; the libraries: jump tables of JMP abs.l, filled in at run time (PC-relative)
NSLOTS		equ	100		; LVO -6 .. -600

make_libs:
	lea	exec_tab(pc),a0
	bsr	fill_tab
	lea	gfx_tab(pc),a0
	bsr	fill_tab
	lea	dos_tab(pc),a0
	bsr	fill_tab
	lea	execbase(pc),a2		; exec
	lea	ex_findtask(pc),a1
	move.w	#-294,d0
	bsr	set_lvo
	lea	ex_openlib(pc),a1
	move.w	#-552,d0
	bsr	set_lvo
	lea	ex_openlib(pc),a1	; OldOpenLibrary
	move.w	#-408,d0
	bsr	set_lvo
	lea	gfxbase(pc),a2		; graphics
	lea	gfx_waittof(pc),a1
	move.w	#-270,d0
	bsr	set_lvo
	lea	gfx_waitblit(pc),a1
	move.w	#-228,d0
	bsr	set_lvo
	lea	COPEND,a0		; copinit (38) and ActiView (34)
	move.l	a0,38(a2)
	clr.l	34(a2)
	lea	dosbase(pc),a2		; dos
	lea	dos_open(pc),a1
	move.w	#-30,d0
	bsr	set_lvo
	lea	dos_close(pc),a1
	move.w	#-36,d0
	bsr	set_lvo
	lea	dos_read(pc),a1
	move.w	#-42,d0
	bsr	set_lvo
	lea	dos_write(pc),a1
	move.w	#-48,d0
	bsr	set_lvo
	lea	fake_task(pc),a0	; a CLI task: no Workbench message to wait for
	move.l	#1,172(a0)
	rts

fill_tab:				; a0 = table: every slot returns 0
	lea	ret0(pc),a1
	move.w	#NSLOTS-1,d0
.l	move.w	#$4ef9,(a0)+		; JMP abs.l
	move.l	a1,(a0)+
	dbf	d0,.l
	rts

set_lvo:				; a2 = library base, d0.w = LVO, a1 = function
	move.w	#$4ef9,(a2,d0.w)
	move.l	a1,2(a2,d0.w)
	rts

ret0	moveq	#0,d0
	rts

;------------------------------------------------------------------ exec
ex_findtask:
	lea	fake_task(pc),a0
	move.l	a0,d0
	rts

ex_openlib:				; a1 = name: graphics.library or dos.library
	lea	gfxbase(pc),a0
	cmp.b	#'g',(a1)
	beq.s	.r
	lea	dosbase(pc),a0
	cmp.b	#'d',(a1)
	beq.s	.r
	moveq	#0,d0
	rts
.r	move.l	a0,d0
	rts

;------------------------------------------------------------------ graphics
gfx_waittof:				; wait for the next frame
.w1	move.l	$dff004,d0
	and.l	#$1ff00,d0
	cmp.l	#303<<8,d0
	bne.s	.w1
.w2	move.l	$dff004,d0
	and.l	#$1ff00,d0
	cmp.l	#303<<8,d0
	beq.s	.w2
	rts

gfx_waitblit:
	tst.w	$dff002
.w	btst	#6,$dff002
	bne.s	.w
	rts

;------------------------------------------------------------------ dos
; one file at a time (the game reads or writes SSlots.hi and closes it)
dos_open:				; d1 = name, d2 = mode -> d0 = handle
	movem.l	d1-d2/a0-a2,-(sp)
	lea	fh(pc),a2
	move.l	d1,(a2)			; fh_name
	clr.l	4(a2)			; fh_pos
	clr.l	8(a2)			; fh_size
	cmp.l	#1006,d2		; MODE_NEWFILE: written on the first Write
	beq.s	.ok
	move.l	d1,a0
	move.l	resload(pc),a1
	jsr	resload_GetFileSize(a1)
	move.l	d0,8(a2)
	beq.s	.none
.ok	move.l	a2,d0
	bra.s	.x
.none	moveq	#0,d0
.x	movem.l	(sp)+,d1-d2/a0-a2
	rts

dos_close:
	moveq	#-1,d0
	rts

dos_read:				; d1 = handle, d2 = buffer, d3 = length -> d0 = bytes
	movem.l	d1-d4/a0-a3,-(sp)
	move.l	d1,a2
	move.l	8(a2),d4		; what is left
	sub.l	4(a2),d4
	cmp.l	d3,d4
	bls.s	.n
	move.l	d3,d4
.n	tst.l	d4
	ble.s	.zero
	move.l	d4,d0			; size
	move.l	4(a2),d1		; offset
	move.l	(a2),a0			; name
	move.l	d2,a1			; to
	move.l	resload(pc),a3
	jsr	resload_LoadFileOffset(a3)
	add.l	d4,4(a2)
	move.l	d4,d0
	bra.s	.x
.zero	moveq	#0,d0
.x	movem.l	(sp)+,d1-d4/a0-a3
	rts

dos_write:				; d1 = handle, d2 = buffer, d3 = length -> d0 = bytes
	movem.l	d1-d3/a0-a3,-(sp)
	move.l	d1,a2
	move.l	d3,d0			; size
	move.l	(a2),a0			; name
	move.l	d2,a1			; from
	move.l	resload(pc),a3
	tst.l	4(a2)
	bne.s	.off
	jsr	resload_SaveFile(a3)	; the start: the file is made new
	bra.s	.done
.off	move.l	4(a2),d1
	jsr	resload_SaveFileOffset(a3)
.done	add.l	d3,4(a2)
	move.l	d3,d0
	movem.l	(sp)+,d1-d3/a0-a3
	rts

;------------------------------------------------------------------------------
; load_game: SSlots.game, hunk by hunk -> d0 = 0 when it failed
load_game:
	lea	gamename(pc),a0
	move.l	resload(pc),a2
	jsr	resload_GetFileSize(a2)
	lea	file_size(pc),a0
	move.l	d0,(a0)
	beq	.bad
	lea	file_pos(pc),a0
	clr.l	(a0)
	lea	buf_left(pc),a0
	clr.l	(a0)
	lea	chip_next(pc),a0
	move.l	#CHIPSTART,(a0)
	lea	fast_next(pc),a0
	move.l	expmem(pc),(a0)

	bsr	get_long
	cmp.l	#$3f3,d0
	bne	.bad
	bsr	get_long		; no resident library names
	tst.l	d0
	bne	.bad
	bsr	get_long
	cmp.l	#MAXHUNKS,d0
	bhi	.bad
	lea	nhunks(pc),a0
	move.w	d0,(a0)
	bsr	get_long		; first
	bsr	get_long		; last
	moveq	#0,d7
.alloc	cmp.w	nhunks(pc),d7		; place the hunks: chip or fast, 8 aligned
	bhs.s	.hunks
	bsr	get_long
	move.l	d0,d2
	and.l	#$3fffffff,d0
	lsl.l	#2,d0
	addq.l	#7,d0
	and.w	#$fff8,d0
	lea	fast_next(pc),a0
	btst	#30,d2
	beq.s	.f
	lea	chip_next(pc),a0
.f	move.l	(a0),d1			; here
	add.l	d0,(a0)
	lea	hunk_base(pc),a1
	move.w	d7,d3
	lsl.w	#2,d3
	move.l	d1,(a1,d3.w)
	addq.w	#1,d7
	bra.s	.alloc
.hunks	move.l	chip_next(pc),d0	; does it fit?
	cmp.l	#BUFADDR,d0
	bhi	.bad
	move.l	expmem(pc),d0
	add.l	#EXPMEM,d0
	cmp.l	fast_next(pc),d0
	blo	.bad
	moveq	#0,d7			; current hunk
.type	cmp.w	nhunks(pc),d7
	bhs	.done
	bsr	get_long
	and.l	#$3fffffff,d0
	cmp.l	#$3e9,d0
	beq.s	.data
	cmp.l	#$3ea,d0
	beq.s	.data
	cmp.l	#$3eb,d0
	beq.s	.bss
	cmp.l	#$3ec,d0
	beq.s	.reloc
	cmp.l	#$3f2,d0
	beq.s	.end
	cmp.l	#$3f0,d0		; symbols: skipped
	beq.s	.sym
	cmp.l	#$3f1,d0		; debug: skipped
	beq.s	.dbg
	bra	.bad
.data	bsr	get_long
	lsl.l	#2,d0
	move.l	d0,d1
	lea	hunk_base(pc),a0
	move.w	d7,d3
	lsl.w	#2,d3
	move.l	(a0,d3.w),a0
	bsr	read_block
	bra.s	.type
.bss	bsr	get_long		; ClearMem: already zero
	bra.s	.type
.end	addq.w	#1,d7
	bra.s	.type
.sym	bsr	get_long		; name length (longs), 0 = the end
	tst.l	d0
	beq.s	.type
	move.l	d0,d6
.s1	bsr	get_long
	subq.l	#1,d6
	bpl.s	.s1			; the name and the value
	bra.s	.sym
.dbg	bsr	get_long
	move.l	d0,d6
	bra.s	.d2
.d1	bsr	get_long
.d2	subq.l	#1,d6
	bpl.s	.d1
	bra	.type
.reloc	lea	hunk_base(pc),a0
	move.w	d7,d3
	lsl.w	#2,d3
	move.l	(a0,d3.w),a2		; this hunk
.rl	bsr	get_long
	tst.l	d0
	beq	.type
	move.l	d0,d6			; count
	bsr	get_long
	cmp.w	nhunks(pc),d0
	bhs.s	.bad
	lsl.w	#2,d0
	lea	hunk_base(pc),a0
	move.l	(a0,d0.w),d5		; target base
.ro	bsr	get_long
	add.l	d5,(a2,d0.l)
	subq.l	#1,d6
	bne.s	.ro
	bra.s	.rl
.done	moveq	#1,d0
	rts
.bad	moveq	#0,d0
	rts

; get_long: the next long of the file -> d0
get_long:
	moveq	#3,d1
	moveq	#0,d0
.l	lsl.l	#8,d0
	move.l	d0,-(sp)
	bsr	get_byte
	or.l	(sp)+,d0
	dbf	d1,.l
	rts

; get_byte -> d0 (0..255); keeps d1-d7/a0-a6
get_byte:
	movem.l	d1/a0-a1,-(sp)
	move.l	buf_left(pc),d0
	bne.s	.have
	bsr	refill
.have	lea	buf_left(pc),a0
	subq.l	#1,(a0)
	lea	buf_ptr(pc),a0
	move.l	(a0),a1
	moveq	#0,d0
	move.b	(a1)+,d0
	move.l	a1,(a0)
	movem.l	(sp)+,d1/a0-a1
	rts

; refill: the next part of the file into the buffer (past the end: zeros)
refill:
	movem.l	d0-d2/a0-a2,-(sp)
	move.l	file_size(pc),d0
	sub.l	file_pos(pc),d0
	cmp.l	#BUFSIZE,d0
	bls.s	.n
	move.l	#BUFSIZE,d0
.n	tst.l	d0
	bgt.s	.rd
	lea	BUFADDR,a0		; nothing left: a zero long
	clr.l	(a0)
	moveq	#4,d0
	bra.s	.set
.rd	move.l	d0,d2
	move.l	file_pos(pc),d1
	lea	gamename(pc),a0
	lea	BUFADDR,a1
	move.l	resload(pc),a2
	jsr	resload_LoadFileOffset(a2)
	lea	file_pos(pc),a0
	add.l	d2,(a0)
	move.l	d2,d0
.set	lea	buf_left(pc),a0
	move.l	d0,(a0)
	lea	buf_ptr(pc),a0
	move.l	#BUFADDR,(a0)
	movem.l	(sp)+,d0-d2/a0-a2
	rts

; read_block: a0 = to, d1 = bytes (from the buffer, the rest straight from the file)
read_block:
	movem.l	d0-d3/a0-a3,-(sp)
	move.l	a0,a3
	move.l	d1,d3
.b	tst.l	d3			; first what is in the buffer
	beq.s	.x
	move.l	buf_left(pc),d0
	beq.s	.direct
	bsr	get_byte
	move.b	d0,(a3)+
	subq.l	#1,d3
	bra.s	.b
.direct	move.l	d3,d0			; the rest in one go
	move.l	file_pos(pc),d1
	lea	gamename(pc),a0
	move.l	a3,a1
	move.l	resload(pc),a2
	jsr	resload_LoadFileOffset(a2)
	lea	file_pos(pc),a0
	add.l	d3,(a0)
.x	movem.l	(sp)+,d0-d3/a0-a3
	rts

;------------------------------------------------------------------------------
resload	dc.l	0
stack_save dc.l	0
file_size dc.l	0
file_pos dc.l	0
buf_left dc.l	0
buf_ptr	dc.l	0
chip_next dc.l	0
fast_next dc.l	0
nhunks	dc.w	0
	even
hunk_base ds.l	MAXHUNKS
fh	ds.l	3			; name, position, size
fake_task ds.b	200
exec_tab ds.b	NSLOTS*6
execbase ds.b	600			; the library bodies (34, 38 used in graphics)
gfx_tab	ds.b	NSLOTS*6
gfxbase	ds.b	64
dos_tab	ds.b	NSLOTS*6
dosbase	ds.b	64
