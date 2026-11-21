"""adfput.py - replace files inside an OFS floppy image, in place.

Keeps every other block of the disk (bootblock, protection bits, dates,
comments, icons) as it is.  The new data reuses the file's old blocks in
their old order; blocks it no longer needs go back to the bitmap.  When a
file grows it takes free blocks next to its own.
"""
import struct

BS = 512


def u32(b, i): return struct.unpack_from('>I', b, i * 4)[0]
def p32(b, i, v): struct.pack_into('>I', b, i * 4, v & 0xffffffff)


def csum(b, at=5):
    s = 0
    for i in range(128):
        if i != at:
            s = (s + u32(b, i)) & 0xffffffff
    p32(b, at, -s)


class Disk:
    def __init__(self, path):
        self.d = bytearray(open(path, 'rb').read())
        assert self.d[:4] == b'DOS\0', 'only OFS disks'
        root = self.blk(880)
        self.bmblk = u32(root, 79)
        assert u32(root, 78) == 0xffffffff, 'bitmap not valid'

    def blk(self, n):
        return memoryview(self.d)[n * BS:(n + 1) * BS]

    # bitmap: bit set = free; block n is bit (n-2)
    def isfree(self, n):
        bm = self.blk(self.bmblk)
        i = n - 2
        return (u32(bm, 1 + i // 32) >> (i % 32)) & 1

    def setfree(self, n, free):
        bm = self.blk(self.bmblk)
        i = n - 2
        w = u32(bm, 1 + i // 32)
        w = w | (1 << (i % 32)) if free else w & ~(1 << (i % 32))
        p32(bm, 1 + i // 32, w)

    def freecount(self):
        return sum(self.isfree(n) for n in range(2, 1760))

    def find(self, path):
        cur = 880
        for part in path.split('/'):
            b = self.blk(cur)
            found = None
            for i in range(72):
                e = u32(b, 6 + i)
                while e:
                    eb = self.blk(e)
                    nm = bytes(eb[433:433 + eb[432]]).decode('latin1')
                    if nm.lower() == part.lower():
                        found = e
                        break
                    e = u32(eb, 124)
                if found:
                    break
            assert found, 'not on the disk: ' + path
            cur = found
        return cur

    def fileblocks(self, hdr):
        data, exts = [], []
        h = hdr
        while h:
            hb = self.blk(h)
            for i in range(u32(hb, 2)):
                data.append(u32(hb, 77 - i))
            h = u32(hb, 126)
            if h:
                exts.append(h)
        return data, exts

    def read(self, path):
        hdr = self.find(path)
        size = u32(self.blk(hdr), 81)
        data, _ = self.fileblocks(hdr)
        out = bytearray()
        for n in data:
            db = self.blk(n)
            out += db[24:24 + u32(db, 3)]
        return bytes(out[:size])

    def alloc_near(self, near):
        for dist in range(1, 1760):
            for n in (near + dist, near - dist):
                if 2 <= n < 1760 and n != 880 and self.isfree(n):
                    self.setfree(n, False)
                    return n
        raise SystemExit('the disk is full')

    def put(self, path, new):
        hdr = self.find(path)
        olddata, oldexts = self.fileblocks(hdr)
        need = max(1, (len(new) + 487) // 488) if new else 0
        nexts = max(0, (need - 1) // 72)
        blocks = olddata[:need]
        for n in olddata[need:]:
            self.setfree(n, True)
        while len(blocks) < need:
            blocks.append(self.alloc_near(blocks[-1] if blocks else hdr))
        exts = oldexts[:nexts]
        for n in oldexts[nexts:]:
            self.setfree(n, True)
        while len(exts) < nexts:
            exts.append(self.alloc_near(exts[-1] if exts else hdr))
        # data blocks
        for i, n in enumerate(blocks):
            chunk = new[i * 488:(i + 1) * 488]
            b = self.blk(n)
            b[:] = bytes(BS)
            p32(b, 0, 8)
            p32(b, 1, hdr)
            p32(b, 2, i + 1)
            p32(b, 3, len(chunk))
            p32(b, 4, blocks[i + 1] if i + 1 < len(blocks) else 0)
            b[24:24 + len(chunk)] = chunk
            csum(b)
        # header + extension blocks: 72 data pointers each, filled from the end
        groups = [blocks[i:i + 72] for i in range(0, len(blocks), 72)] or [[]]
        owners = [hdr] + exts
        for gi, own in enumerate(owners):
            b = self.blk(own)
            g = groups[gi] if gi < len(groups) else []
            for i in range(72):
                p32(b, 77 - i, g[i] if i < len(g) else 0)
            p32(b, 2, len(g))
            p32(b, 126, owners[gi + 1] if gi + 1 < len(owners) else 0)
            if gi == 0:
                p32(b, 4, blocks[0] if blocks else 0)
                p32(b, 81, len(new))
            else:
                p32(b, 0, 16)
                p32(b, 1, own)
                p32(b, 125, hdr)
                p32(b, 127, 0xfffffffd)
                p32(b, 4, 0)
            csum(b)
        csum(self.blk(self.bmblk), 0)

    def save(self, path):
        open(path, 'wb').write(self.d)
