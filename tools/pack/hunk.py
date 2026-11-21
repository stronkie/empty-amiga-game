"""Parse and write AmigaOS hunk executables (just what these games use)."""
import struct

HUNK_CODE, HUNK_DATA, HUNK_BSS = 0x3E9, 0x3EA, 0x3EB
HUNK_RELOC32, HUNK_SYMBOL, HUNK_DEBUG, HUNK_END, HUNK_HEADER = 0x3EC, 0x3F0, 0x3F1, 0x3F2, 0x3F3
HUNK_DREL32, HUNK_RELOC32SHORT = 0x3F7, 0x3FC


class Hunk:
    def __init__(self, kind, memflags, alloc):
        self.kind = kind          # CODE / DATA / BSS
        self.memflags = memflags  # 0 any, 1 chip, 2 fast
        self.alloc = alloc        # bytes from the header table
        self.data = b''
        self.relocs = {}          # target hunk -> sorted list of offsets


def U(b, o):
    return struct.unpack_from('>I', b, o)[0]


def parse(b):
    assert U(b, 0) == HUNK_HEADER, 'not a hunk executable'
    o = 4
    while U(b, o):            # resident library names
        o += 4 + 4 * U(b, o)
    o += 4
    num, first, last = U(b, o), U(b, o + 4), U(b, o + 8)
    o += 12
    hunks = []
    for i in range(last - first + 1):
        v = U(b, o); o += 4
        f = v >> 30
        if f == 3:
            o += 4
        hunks.append(Hunk(None, f if f < 3 else 0, (v & 0x3FFFFFFF) * 4))
    cur = 0
    while o < len(b) and cur < len(hunks):
        t = U(b, o) & 0x3FFFFFFF; o += 4
        h = hunks[cur]
        if t in (HUNK_CODE, HUNK_DATA):
            n = U(b, o) * 4; o += 4
            h.kind = t; h.data = b[o:o + n]; o += n
        elif t == HUNK_BSS:
            o += 4; h.kind = t
        elif t == HUNK_RELOC32:
            while True:
                n = U(b, o); o += 4
                if not n:
                    break
                tgt = U(b, o); o += 4
                h.relocs.setdefault(tgt, []).extend(struct.unpack_from('>%dI' % n, b, o)); o += 4 * n
        elif t in (HUNK_RELOC32SHORT, HUNK_DREL32):
            while True:
                n = struct.unpack_from('>H', b, o)[0]; o += 2
                if not n:
                    break
                tgt = struct.unpack_from('>H', b, o)[0]; o += 2
                h.relocs.setdefault(tgt, []).extend(struct.unpack_from('>%dH' % n, b, o)); o += 2 * n
            if o % 4:
                o += 2
        elif t in (HUNK_SYMBOL,):
            while True:
                n = U(b, o); o += 4
                if not n:
                    break
                o += 4 * n + 4
        elif t == HUNK_DEBUG:
            o += 4 + 4 * U(b, o)
        elif t == HUNK_END:
            cur += 1
        else:
            raise ValueError('hunk type %x not handled' % t)
    for h in hunks:
        for k in h.relocs:
            h.relocs[k] = sorted(h.relocs[k])
    return hunks


def write(hunks):
    """hunks: list of dicts kind, memflags, alloc, data, relocs."""
    out = bytearray(struct.pack('>IIIII', HUNK_HEADER, 0, len(hunks), 0, len(hunks) - 1))
    for h in hunks:
        words = (h['alloc'] + 3) // 4
        out += struct.pack('>I', words | (h['memflags'] << 30))
    for h in hunks:
        if h['kind'] == HUNK_BSS:
            out += struct.pack('>II', HUNK_BSS, (h['alloc'] + 3) // 4)
        else:
            d = h['data'] + b'\0' * ((-len(h['data'])) % 4)
            out += struct.pack('>II', h['kind'], len(d) // 4) + d
        if h.get('relocs'):
            out += struct.pack('>I', HUNK_RELOC32)
            for tgt, offs in sorted(h['relocs'].items()):
                out += struct.pack('>II', len(offs), tgt) + struct.pack('>%dI' % len(offs), *offs)
            out += struct.pack('>I', 0)
        out += struct.pack('>I', HUNK_END)
    return bytes(out)


def loadseg(hunks, bases):
    """Simulate LoadSeg: returns list of bytearrays, memory images after relocation."""
    mem = []
    for h in hunks:
        m = bytearray(h.alloc)
        m[:len(h.data)] = h.data
        mem.append(m)
    for i, h in enumerate(hunks):
        for tgt, offs in h.relocs.items():
            for off in offs:
                v = (U(mem[i], off) + bases[tgt]) & 0xffffffff
                struct.pack_into('>I', mem[i], off, v)
    return mem
