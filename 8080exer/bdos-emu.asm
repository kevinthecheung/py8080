;
; Emulate CP/M BDOS calls 2 and 9
;
ioport  equ     1
;
;
        .8080
;
        .org 0000h
        hlt             ; Halt on warm reboot
;
        .org 0005h
        jmp bdos
;
        .org 0f000h
bdos:
        mov a,c
        cpi 2
        jz outc
        cpi 9
        jz outs
        ret
;
;
outc:
        mov a,e
        out ioport
        ret
;
;
outs:
        ldax d
        cpi '$'
        rz
        out ioport
        inx d
        jmp outs
;