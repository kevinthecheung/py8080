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

"""Rough emulation of an Altair 8800 with a 2SIO board.

Good enough to run 4K BASIC, 8K BASIC, and Extended BASIC."""


import argparse
from typing import Optional

from kbhit import KBHit

from virtual8080 import Virtual8080
from virtual_device import VirtualDevice


class AltairWithTerminal(VirtualDevice):

    def __init__(self):
        self.input_buffer: bytes = b''
        self.output_char: int = -1

    def get_input(self, port_addr: int) -> int:
        if port_addr == 0xff:
            # Altair "sense switches". 0b0000xxxx means the console is on a
            # 2SIO configured with the console status/control register on port
            # 0x10 and the console I/O register on port 0x11. 0bxxxx0000
            # configures the loader device, which we don't use because we're
            # cheaters.
            return 0b00000000
        elif port_addr == 0x10:
            # Status register
            input_ready = 1 if len(self.input_buffer) > 0 else 0
            output_ready = 1
            status = 0b00000000
            status = status | (input_ready << 0)
            status = status | (output_ready << 1)
            return status
        elif port_addr == 0x11:
            # I/O register
            if len(self.input_buffer) > 0:
                ch = self.input_buffer[0]
                self.input_buffer = self.input_buffer[1:]
                return ch
            return 0  # Okay?
        else:
            return 0

    def send_output(self, port_addr: int, value: int) -> None:
        if port_addr == 0x10:
            # Control register
            pass
        elif port_addr == 0x11:
            # I/O register
            self.output_char = value & 0b01111111


def console_run(program_file: str, autorun_file: Optional[str] = None, init_str: str = ''):
    vm = Virtual8080()
    vm.io = AltairWithTerminal()
    with open(program_file, 'rb') as pf:
        program = pf.read()
    vm.load(program)

    if autorun_file is not None:
        init_buffer = init_str
        with open(autorun_file, 'r') as af:
            for line in af.readlines():
                init_buffer += line.replace('\n', '\r')
        vm.io.input_buffer = init_buffer.encode(encoding='ascii')

    kb = KBHit()
    try:
        vm.halted = False
        while not vm.halted:
            ch = vm.io.output_char
            if ch != -1 and ch != 13:
                print(bytes([ch]).decode(encoding='ascii'), end='', flush=True)
            vm.io.output_char = -1
            if kb.kbhit():
                ch = ord(kb.getch())
                if ch == 10:
                    vm.io.input_buffer += bytes([13, 0])
                elif ch == 27:
                    # Break on ESC
                    vm.io.input_buffer += bytes([3])
                else:
                    vm.io.input_buffer += bytes([ch])
            vm.step()
    finally:
        kb.set_normal_term()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    basic_ver = parser.add_mutually_exclusive_group()
    basic_ver.add_argument('-4', '--4k', action='store_const', dest='version',
                           const=('altair_basic_bin/4kbas40.bin', '65529\r\rY\r'),
                           help='Load 4K BASIC')
    basic_ver.add_argument('-8', '--8k', action='store_const', dest='version',
                           const=('altair_basic_bin/8kbas.bin', '65529\r\rY\r'),
                           help='Load 8K BASIC')
    basic_ver.add_argument('-e', '--extended', action='store_const', dest='version',
                           const=('altair_basic_bin/exbas.bin', '65529\rY\r'),
                           help='Load Extended BASIC')
    parser.add_argument('-f', '--autorun_file',
                        type=str, default=None,
                        help='File (BASIC) to run on startup')
    parser.set_defaults(version=('altair_basic_bin/8kbas.bin', '65529\r\rY\r'))
    args = parser.parse_args()

    ### Terminal interface
    program = args.version[0]
    init = args.version[1]
    console_run(program, autorun_file=args.autorun_file, init_str=init)
