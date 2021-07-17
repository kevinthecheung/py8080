# This is free and unencumbered software released into the public domain.
#
# Anyone is free to copy, modify, publish, use, compile, sell, or
# distribute this software, either in source code form or as a compiled
# binary, for any purpose, commercial or non-commercial, and by any
# means.
#
# In jurisdictions that recognize copyright laws, the author or authors
# of this software dedicate any and all copyright interest in the
# software to the public domain. We make this dedication for the benefit
# of the public at large and to the detriment of our heirs and
# successors. We intend this dedication to be an overt act of
# relinquishment in perpetuity of all present and future rights to this
# software under copyright law.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# For more information, please refer to <https://unlicense.org>

"""Rough emulation of a generic CP/M machine.

Emulated machine has 16 8" 250 KB floppy disk drives and an ADM-3A terminal."""


import argparse
import os

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame
from pygame.locals import *

from virtual8080 import Virtual8080
from cpm_disk import CPM_Disk


class CPM_Machine:

    def __init__(self, vm, disk_images=[]):
        self.vm = vm

        self.input_buffer = b''
        self.output_char = -1

        self.dma_addr = 0
        self.disk_controller_error = 0

        self.current_drive = 0
        self.drive_status = [{'track': 0, 'sector': 0} for _ in range(16)]
        self.disk_image = [None for _ in range(16)]
        for i, fn in enumerate(disk_images):
            if fn is not None:
                self.drive_status[i] = {'track': 0, 'sector': 0}
                self.disk_image[i] = CPM_Disk(fn, 128, 26, 77, 1, write_protect=False)

        boot_sector = self.read_disk(0, 0, 1)
        self.vm.load(boot_sector)


    def read_disk(self, drive, track, sector):
        return self.disk_image[drive].get_sector(track, sector)


    def write_disk(self, drive, track, sector, sector_data):
        self.disk_image[drive].set_sector(track, sector, sector_data)
        self.disk_image[drive].save_image()


    def get_input(self, port_addr):
        if port_addr == 0:
            # Console status
            if len(self.input_buffer) > 0:
                return 0xff
            else:
                return 0x00
        elif port_addr == 1:
            # Console input
            if len(self.input_buffer) > 0:
                c = self.input_buffer[0]
                self.input_buffer = self.input_buffer[1:]
                return c
            else:
                self.vm.registers['pc'] -= 2  # Loop again with same PC
                return
        elif port_addr == 2:
            # List device status
            return 1  # Ready
        elif port_addr == 0xf9:
            # Disk error status
            return self.disk_controller_error
        raise Exception


    def send_output(self, port_addr, val):
        if port_addr == 1:
            # Console output
            self.output_char = val
            return
        elif port_addr == 3:
            # List device output
            print(chr(val), end='', flush=True)
            return
        elif port_addr == 0xf9:
            # Disk read/write commands
            if val == 0:
                # Read current drive/track/sector into [dma]
                if self.disk_image[self.current_drive] is not None:
                    data = self.read_disk(self.current_drive,
                                          self.drive_status[self.current_drive]['track'],
                                          self.drive_status[self.current_drive]['sector'])
                    for i in range(len(data)):
                        self.vm.memory[self.dma_addr + i] = data[i]
                    self.disk_controller_error = 0x00  # OK
                else:
                    self.disk_controller_error = 0xff  # Error
                return
            elif val == 1:
                # Write [dma] to current drive/track/sector
                if self.disk_image[self.current_drive] is not None:
                    sector_size = self.disk_image[self.current_drive].sector_size
                    sector_data = bytes(self.vm.memory[self.dma_addr:self.dma_addr+sector_size])
                    self.write_disk(self.current_drive,
                                    self.drive_status[self.current_drive]['track'],
                                    self.drive_status[self.current_drive]['sector'],
                                    sector_data)
                    self.disk_controller_error = 0x00  # OK
                else:
                    self.disk_controller_error = 0xff  # Error
                return
        elif port_addr == 0xfa:
            # Disk drive select
            self.current_drive = val
            return
        elif port_addr == 0xfb:
            # Track select
            self.drive_status[self.current_drive]['track'] = val
            return
        elif port_addr == 0xfc:
            # Sector select
            self.drive_status[self.current_drive]['sector'] = val
            return
        elif port_addr == 0xfd:
            # Set DMA address high byte
            self.dma_addr = (self.dma_addr & 0x00ff) | (val << 8)
            return
        elif port_addr == 0xfe:
            # Set DMA address low byte
            self.dma_addr = (self.dma_addr & 0xff00) | (val & 0x00ff)
            return
        raise Exception


class CPM_TTY:

    background = (0, 0, 0)
    foreground = (200, 200, 200)
    margin = 5

    shift_keymap = {
        ord('`'): ord('~'),
        ord('1'): ord('!'),
        ord('2'): ord('@'),
        ord('3'): ord('#'),
        ord('4'): ord('$'),
        ord('5'): ord('%'),
        ord('6'): ord('^'),
        ord('7'): ord('&'),
        ord('8'): ord('*'),
        ord('9'): ord('('),
        ord('0'): ord(')'),
        ord('-'): ord('_'),
        ord('='): ord('+'),
        ord('['): ord('{'),
        ord(']'): ord('}'),
        ord(';'): ord(':'),
        ord("'"): ord('"'),
        ord(','): ord('<'),
        ord('.'): ord('>'),
        ord('/'): ord('?'),
    }

    def __init__(self, disk_images=[]):
        self.disk_images = disk_images

        self.buffer = bytearray([32 for _ in range(80 * 24)])
        self.cursor = 0
        self.esc_sequence = b''

        pygame.init()
        pygame.display.set_caption('8080 Emulator')
        self.screen = pygame.display.set_mode((80 * 10 + 10, 24 * 20 + 10))
        self.font = pygame.font.Font('ter-u20n.bdf', 20)


    def putch(self, ch):
        ## ADM-3A cursor control
        ch = ch & 0b01111111
        if ch == 27:      # Esc
            self.esc_sequence = b'\x1b'
        elif len(self.esc_sequence) > 0:
            self.esc_sequence += bytes([ch])
            if self.esc_sequence.startswith(b'\x1b=') and len(self.esc_sequence) >= 4:
                y = self.esc_sequence[2] - 0x20
                x = self.esc_sequence[3] - 0x20
                self.cursor = 80 * y + x
                self.esc_sequence = b''

        elif ch == 8:         # ^H
            self.cursor = max(0, self.cursor - 1)
        elif ch == 10:         # ^J, \n
            self.cursor = self.cursor + 80
            if self.cursor >= 80 * 24 - 1:
                self.buffer = self.buffer[80:] + bytearray([32 for _ in range(80)])
                self.cursor = 80 * 23
        elif ch == 11:         # ^K
            self.cursor = max(0, self.cursor - 80)
        elif ch == 12:         # ^L
            self.cursor = min(80 * 24 - 1, self.cursor + 1)
        elif ch == 13:      # \r
            self.cursor = self.cursor // 80 * 80
        elif ch == 26:      # ^Z
            self.buffer = bytearray([32 for _ in range(80 * 24)])
            self.cursor = 0
        elif ch == 30:      # Home
            self.cursor = 0

        elif 32 <= ch < 127: # Printable
            if self.cursor >= 80 * 24 - 1:
                self.buffer = self.buffer[80:] + bytearray([32 for _ in range(80)])
                self.cursor = 80 * 23
            self.buffer[self.cursor] = ch
            self.cursor += 1
        else:
            # print(f'{ch} {ch & 0x7f}')
            print(chr(ch & 0x7f), end='', flush=True)


    def render_buffer(self):
        img = self.font.render('█', False, self.foreground)
        col = self.cursor % 80
        row = self.cursor // 80
        rect = img.get_rect()
        rect.topleft = (col * 10 + self.margin, row * 20 + self.margin)
        rect.size = img.get_size()
        blits = [(img, rect)]

        for row in range(24):
            img = self.font.render(bytes(self.buffer[80*row:80*row+80]), False, self.foreground)
            rect = img.get_rect()
            rect.topleft = (self.margin, row * 20 + self.margin)
            rect.size = img.get_size()
            blits += [(img, rect)]
        return blits


    def run(self):
        vm = Virtual8080()
        vm.io = CPM_Machine(vm, self.disk_images)

        work_ms = 1000 // 60    # Allow ~17ms of emulation time to maintain ~60fps.
        vm.halted = False
        while not vm.halted:
            work_until = pygame.time.get_ticks() + work_ms
            while pygame.time.get_ticks() < work_until:
                if not vm.halted:
                    vm.step()
                ch = vm.io.output_char
                if ch != -1:
                    self.putch(ch)
                    vm.io.output_char = -1

            for event in pygame.event.get():
                if event.type == QUIT:
                    vm.halted = True
                
                if event.type == KEYDOWN:
                    if 0 <= event.key <= 255: 
                        key = event.key
                        if 97 <= key <= 122 and event.mod & KMOD_SHIFT: # A-Z
                            key -= 32
                        elif event.mod & KMOD_SHIFT:                    # Other
                            key = self.shift_keymap[key]
                        elif 97 <= key <= 122 and event.mod & KMOD_CTRL: # ^A - ^Z
                            key -= 96
                        vm.io.input_buffer += bytes([key])

            self.screen.fill(self.background)
            self.screen.blits(self.render_buffer())
            pygame.display.update()

        pygame.quit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for d in range(ord('a'), ord('a') + 16):
        parser.add_argument(f'-d{chr(d)}', f'--drive_{chr(d)}', type=str, default=None,
                            help=f'disk image for drive {chr(d)}')
    args = parser.parse_args()

    tty = CPM_TTY(disk_images=[getattr(args, f'drive_{chr(d)}')
                               for d in range(ord('a'), ord('a') + 16)])
    tty.run()
