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

"""Run 8080EX1 to test emulation correctness."""


import datetime
import time
from virtual8080 import Virtual8080


class StubIO:

    def get_input(self, port_addr):
        return 0

    def send_output(self, port_addr, val):
        ch = val & 0b01111111
        print(bytes([ch]).decode(encoding='ascii'), end='', flush=True)


def run(program_file, bdos_file):
    vm = Virtual8080()
    vm.io = StubIO()

    with open(program_file, 'r') as f:
        program = f.read()
    vm.load_hex(program)

    with open(bdos_file, 'r') as f:
        bdos = f.read()
    vm.load_hex(bdos)

    vm.registers['pc'] = 0x0100 
    vm.run()


if __name__ == '__main__':
    program_file = './8080exer/8080EX1.HEX'
    bdos_file = './8080exer/bdos-emu.hex'

    start_time = time.time()
    start_time_str = time.strftime('%H:%M:%S', time.localtime(start_time))
    print(f'Starting the exerciser at {start_time_str}. This is going to take'
           ' a while.\n')

    run(program_file, bdos_file)

    end_time = time.time()
    end_time_str = time.strftime('%H:%M:%S', time.localtime(end_time))
    elapsed_time = datetime.timedelta(seconds=(end_time - start_time))
    print(f'\nFinished at {end_time_str} (elapsed time: {elapsed_time}).')
