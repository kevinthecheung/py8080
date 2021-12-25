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

from typing import List, Optional, Union


class CPM_Disk:

    def __init__(self,
                 image_file: str,
                 sector_size: int,
                 sectors_per_track: int,
                 num_tracks: int,
                 skew: Union[int, List[int]],
                 write_protect: bool = False):
        self.image_file: str = image_file
        self.sector_size: int = sector_size
        self.sectors_per_track: int = sectors_per_track
        self.write_protect: bool = write_protect
        self.disk_tracks: List[List[bytes]] = []
        self.skew_table: List[int]

        with open(image_file, 'rb') as f:
            disk_bytes = f.read()
        total_bytes = sector_size * sectors_per_track * num_tracks
        disk_bytes += bytes([0xe5 for _ in range(total_bytes - len(disk_bytes))])
        for _ in range(num_tracks):
            tmp_track: List[bytes] = []
            for _ in range(sectors_per_track):
                tmp_sect = disk_bytes[0:sector_size]
                disk_bytes = disk_bytes[sector_size:]
                tmp_track.append(tmp_sect)
            self.disk_tracks.append(tmp_track)
        
        if isinstance(skew, int):
            self.skew_table = make_skew_table(sectors_per_track, skew)
        else:
            self.skew_table = skew
    

    def get_sector(self, track: int, sector: int) -> bytes:
        raw_sector = self.skew_table[sector - 1] - 1
        return self.disk_tracks[track][raw_sector]
    

    def set_sector(self, track: int, sector: int, sector_data: bytes) -> None:
        if not self.write_protect:
            raw_sector = self.skew_table[sector - 1] - 1
            self.disk_tracks[track][raw_sector] = sector_data
    

    def save_image(self, image_file: Optional[str] = None) -> None:
        if image_file is None:
            image_file = self.image_file
        with open(image_file, 'wb') as f:
            for track in self.disk_tracks:
                for sector in track:
                    f.write(sector)


def make_skew_table(num_sectors: int, skew_factor: int) -> List[int]:
    skew_table = [0]
    while len(skew_table) < num_sectors:
        sec = (skew_table[-1] + skew_factor) % num_sectors
        sec = sec + 1 if sec in skew_table else sec
        skew_table.append(sec)
    return [n + 1 for n in skew_table]


if __name__ == '__main__':
    skew_table = make_skew_table(26, 6)
    assert(skew_table == [1,7,13,19,25,5,11,17,23,3,9,15,21,2,8,14,20,26,6,12,18,24,4,10,16,22])
