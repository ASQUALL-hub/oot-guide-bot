"""Minimal, self-contained reader for an Ocarina of Time N64 ROM.

Reads the DMA file table, decompresses Yaz0 files and exposes them by the
names the zeldaret/oot decompilation uses (from baseroms/<ver>/segments.csv).
"""
import struct
import csv
import os


def yaz0_decompress(src: bytes) -> bytes:
    assert src[:4] == b"Yaz0", "not a Yaz0 block"
    size = struct.unpack(">I", src[4:8])[0]
    dst = bytearray(size)
    s, d = 16, 0
    while d < size:
        code = src[s]
        s += 1
        for bit in range(8):
            if d >= size:
                break
            if code & (0x80 >> bit):
                dst[d] = src[s]
                d += 1
                s += 1
            else:
                b1, b2 = src[s], src[s + 1]
                s += 2
                dist = ((b1 & 0x0F) << 8 | b2) + 1
                n = b1 >> 4
                if n == 0:
                    n = src[s] + 0x12
                    s += 1
                else:
                    n += 2
                start = d - dist
                if dist >= n:
                    dst[d:d + n] = dst[start:start + n]
                    d += n
                else:
                    for i in range(n):
                        dst[d] = dst[start + i]
                        d += 1
    return bytes(dst)


class OotRom:
    def __init__(self, rom_path, segments_csv, dmadata_start):
        with open(rom_path, "rb") as f:
            self.rom = f.read()
        with open(segments_csv, newline="") as f:
            rows = list(csv.reader(f))[1:]
        self.names = [r[0] for r in rows]
        self.vram = {r[0]: (int(r[1], 16) if len(r) > 1 and r[1] else None) for r in rows}
        self.entries = []  # (name, vromStart, vromEnd, romStart, romEnd)
        off = dmadata_start
        i = 0
        while True:
            vs, ve, rs, re_ = struct.unpack(">IIII", self.rom[off:off + 16])
            if vs == 0 and ve == 0 and i > 0:
                break
            self.entries.append((self.names[i] if i < len(self.names) else f"file_{i}", vs, ve, rs, re_))
            off += 16
            i += 1
        self.by_name = {e[0]: e for e in self.entries}
        self.by_vrom = {e[1]: e for e in self.entries}
        self._cache = {}

    def file(self, name) -> bytes:
        if name in self._cache:
            return self._cache[name]
        _, vs, ve, rs, re_ = self.by_name[name]
        if re_ == 0:
            data = self.rom[rs:rs + (ve - vs)]
        else:
            data = yaz0_decompress(self.rom[rs:re_])
        self._cache[name] = data
        return data

    def file_at_vrom(self, vrom):
        return self.file(self.by_vrom[vrom][0])

    def name_at_vrom(self, vrom):
        e = self.by_vrom.get(vrom)
        return e[0] if e else None


def u8(b, o): return b[o]
def s8(b, o): return struct.unpack_from(">b", b, o)[0]
def u16(b, o): return struct.unpack_from(">H", b, o)[0]
def s16(b, o): return struct.unpack_from(">h", b, o)[0]
def u32(b, o): return struct.unpack_from(">I", b, o)[0]
