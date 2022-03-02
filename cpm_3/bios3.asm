;
;	CP/M 3.0 BIOS for Python emulator
;
false	equ 0
true	equ not false
;
vers	equ 30		;version 3.0
banked	equ true
;
	maclib	cpm3
	maclib	modebaud
	extrn	@civec,@covec,@aivec,@aovec,@lovec
	extrn	@date, @hour, @min, @sec
	extrn	@mxtpa
;
;
constp	equ 0		;console status port
coniop	equ 1		;console i/o port
;
lststp	equ 2		;list status port
lstiop	equ 3		;list i/o port
;
clock	equ 010h	;base address of clock
ckdayh	equ clock+0
ckdayl	equ clock+1
ckhour	equ clock+2
ckmin	equ clock+3
cksec	equ clock+4
;
bnksel	equ 020h	;get/set current bank
;
disk	equ 0f9h	;base address of disk ports
dstat	equ disk	;status port
dcom	equ disk	;command port: 0 = read, 1 = write
ddisk	equ disk+1	;disk port
dtrack	equ disk+2	;track port
dsect	equ disk+3	;sector port
ddmahi	equ disk+4	;DMA address (high) port
ddmalo	equ disk+5	;DMA address (low) port
ddmabk	equ disk+6	;DMA bank port
;
bdos	equ 5
;
;	jump vector for individual subroutines
  if banked
	cseg
  endif
	jmp	boot		;cold start
wboote:	jmp	wboot		;warm start
	jmp	conist		;console status
	jmp	conin		;console character in
	jmp	conout		;console character out
	jmp	lptout		;list character out
	jmp	auxout		;aux character out
	jmp	auxin		;aux character in
	jmp	home		;move head to home position
	jmp	seldsk		;select disk
	jmp	settrk		;set track number
	jmp	setsec		;set sector number
	jmp	setdma		;set dma address
	jmp	rddsk		;read disk
	jmp	wridsk		;write disk
	jmp	lptst		;return list status
	jmp	sectrn		;sector translate
;
	jmp	conost
	jmp	auxist
	jmp	auxost
	jmp	devtbl
	jmp	devini
	jmp	drvtbl
	jmp	multio
	jmp	flush
	jmp	move
	jmp	time
	jmp	selmem
	jmp	setbnk
	jmp	xmove
;
	jmp	0
	jmp	0
	jmp	0
;
;	character device tables
tblchr	db	'PYGAME'
	db	mb$in$out
	db	baud$none
	db	'PYSTDO'
	db	mb$output
	db	baud$none
	db	0
;
;	disk tables
tbldrv	dw	dph0,dph1,dph2,dph3
	dw	dph4,dph5,dph6,dph7
	dw	dph8,dph9,dpha,dphb
	dw	dphc,dphd,dphe,dphf
;
dph0	dph	tbltrn,dpbstd
dph1	dph	tbltrn,dpbstd
dph2	dph	tbltrn,dpbstd
dph3	dph	tbltrn,dpbstd
dph4	dph	tbltrn,dpbstd
dph5	dph	tbltrn,dpbstd
dph6	dph	tbltrn,dpbstd
dph7	dph	tbltrn,dpbstd
dph8	dph	tbltrn,dpbstd
dph9	dph	tbltrn,dpbstd
dpha	dph	tbltrn,dpbstd
dphb	dph	tbltrn,dpbstd
dphc	dph	tbltrn,dpbstd
dphd	dph	tbltrn,dpbstd
dphe	dph	tbltrn,dpbstd
dphf	dph	tbltrn,dpbstd
;
dpbstd	dpb	128,26,77,1024,64,2
;
tbltrn	skew	26,6,1
;
;	fcb for ccp.com
fcbccp	db	1,'CCP     ','COM',0,0,0,0
	dw	0,0,0,0,0,0,0,0
fcbnr	db	0,0,0
;
;	individual subroutines to perform each function
boot:
	lxi	h,8000h		;assign console to PYGAME device
	shld	@civec
	shld	@covec
;
	lxi	h,4000h
	shld	@lovec		;assign printer to STDOUT device
;
	lxi	h,0000h
	shld	@aivec		;no aux device
	shld	@aovec
;
	; continue to wboot
;
wboot:
  if banked
	mvi	a,1
	out	bnksel
  endif
	mvi	a,0C3h		;8080 "jump" opcode
	sta	0		;store in 1st byte of warm boot vector
	sta	bdos		;and 1st byte of BDOS entry vector
;
	lxi	h,wboote	;get the warm boot jump address
	shld	1		;and put it after the jump
;
	lhld	@mxtpa		;BDOS entry address
	shld	bdos+1		;put it after the jump opcode
ldcpm:
	lxi	sp,bstack
;
	xra	a		;zero the extent
	sta	fcbccp+15
	lxi	h,0		;start at beginning of file
	shld	fcbnr
;
	lxi	d,fcbccp	;DE->FCB to open CCP.COM
	mvi	c,15
	call	bdos
;
	lxi	d,0100h		;set load address to the TPA (0100h)
	mvi	c,26
	call	bdos
;
	mvi	e,128		;read up to 16K
	mvi	c,44		;set multiple-record read
	call	bdos
;
	lxi	d,fcbccp	;DE->FCB to read CCP.COM
	mvi	c,20		;read CCP.COM into memory
	call	bdos
;
	jmp	0100h		;run the CCP
;
;	i/o handlers
;
conist:	;console input status
	lhld	@civec
	mov	a,h	;A<-input vector high byte
	ani	80h
	jz	cinst0
	call	pygist
	ret
cinst0:
	mvi	a,0
	ret
;
conin:	;console character into register a
	lhld	@civec
	mov	a,h	;A<-input vector high byte
	ani	80h
	jz	cin0
	call	pygin
	ret
cin0:
	mvi	a,0
	ret
;
conost:	;console output status
	mvi	a,0ffh
	ret
;
conout: ;console character output from register c
	lhld	@covec
	mov	a,h	;A<-output vector high byte
	ani	80h
	jz	costd
	call	pygout
costd:
	lhld	@covec
	mov	a,h	;A<-output vector high byte
	ani	40h
	jz	cofin
	call 	stdout
cofin:
	ret
;
lptout:	;list character from register c
	lhld	@lovec
	mov	a,h	;A<-output vector high byte
	ani	80h
	jz	lostd
	call	pygout
lostd:
	lhld	@lovec
	mov	a,h	;A<-output vector high byte
	ani	40h
	jz	lofin
	call 	stdout
lofin:
	ret
;
lptst:	;return list status (0 if not ready, 1 if ready)
	mvi	a,1
	ret
;
pygist:	;pygame input status, return 0ffh if character ready, 00h if not
	in	constp
	ret
;
pygost:
	mvi	a,0ffh
	ret
;
pygin:	;character from pygame into register a
	in	coniop
	ret
;
pygout: ;pygame character output from register c
	mov	a,c	;get to accumulator
	out	coniop
	ret
;
stdout:	;print() character from register c to python stdout
	mov	a,c	;character to register a
	out	lstiop
	ret
;
stdst:	;return list status (0 if not ready, 1 if ready)
	in	lststp
	ret
;
auxout:	;aux character from register c
	mov	a,c	;character to register a
	ret		;null subroutine
;
auxin: ;read character into register a from aux device
	mvi	a,1ah	;enter end of file for now (replace later)
	; ani	7fh	;remember to strip parity bit
	ret
;
auxist:
	mvi	a,0ffh
	ret
;
auxost:
	mvi	a,0ffh
	ret
;
devtbl:
	lxi	h,tblchr
	ret
;
devini:
	ret
;
;	i/o drivers for the disk follow
;
  if banked
	dseg
  endif
;
home:	;move to the track 00 position of current drive
;	translate this call into a settrk call with parameter 00
	mvi	c,0	;select track 0
	call	settrk
	ret
;
seldsk:	;select disk given by register C
	mov	a,c
	out	ddisk
;
	lxi	h,dph0
	cpi	0
	rz
	lxi	h,dph1
	cpi	1
	rz
	lxi	h,dph2
	cpi	2
	rz
	lxi	h,dph3
	cpi	3
	rz
	lxi	h,dph4
	cpi	4
	rz
	lxi	h,dph5
	cpi	5
	rz
	lxi	h,dph6
	cpi	6
	rz
	lxi	h,dph7
	cpi	7
	rz
	lxi	h,dph8
	cpi	8
	rz
	lxi	h,dph9
	cpi	9
	rz
	lxi	h,dpha
	cpi	10
	rz
	lxi	h,dphb
	cpi	11
	rz
	lxi	h,dphc
	cpi	12
	rz
	lxi	h,dphd
	cpi	13
	rz
	lxi	h,dphe
	cpi	14
	rz
	lxi	h,dphf
	cpi	15
	rz
;
	lxi	h,0
	ret
;
settrk:	;set track given by register c
	mov	a,c
	out	dtrack
	ret
;
setsec:	;set sector given by register c
	mov	a,c
	out	dsect
	ret
;
sectrn:	;translate the sector given by BC using the
	;translate table given by DE
	xchg		;HL=.trans
	dad	b	;HL=.trans(sector)
	mov	l,m	;L = trans(sector)
	mvi	h,0	;HL= trans(sector)
	ret		;with value in HL
;
setdma:	;set dma address given by registers b and c
	mov	a,c	;low order address
	out	ddmalo
	mov	a,b	;high order address
	out	ddmahi
	ret
;
rddsk:	;perform read operation
	mvi	a,0
	out	dcom
	in	dstat
	ret
;
wridsk:	;perform a write operation
	mvi	a,1
	out	dcom
	in	dstat
	ret
;
drvtbl:
	lxi	h,tbldrv
	ret
;
multio:
	ret
;
flush:
	xra	a
	ret
;
  if banked
	cseg
  endif
;
;	memory functions
move:
	ldax	d
	mov	m,a
	inx	d
	inx	h
	dcx	b
	mov	a,b
	ora	c
	jnz	move
	ret
;
selmem:
  if banked
	out	bnksel
  endif
	ret
;
setbnk:
  if banked
	out	ddmabk
  endif
	ret
;
xmove:
	ret
;
;	clock function
time:
	mov	a,c
	ora	a	;set flags
	jz	getime
setime:
	push	h
;
	lhld	@date
	mov	a,h
	out	ckdayh
	mov	a,l
	out	ckdayl
;
	lda	@hour
	out	ckhour
	lda	@min
	out	ckmin
	lda	@sec
	out	cksec
;
	pop	h
	ret
getime:
	push	h
;
	in	ckdayh
	mov	h,a
	in	ckdayl
	mov	l,a
	shld	@date
;
	in	ckhour
	sta	@hour
	in	ckmin
	sta	@min
	in	cksec
	sta	@sec
;
	pop	h
	ret
;
;	uninitialized memory
  if banked
	cseg
  endif
	ds	32
bstack:
;
	end
;