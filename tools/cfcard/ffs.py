"""Small FFS (DOS\\1) writer for the CF image partitions: read, delete, create files and dirs."""
import struct, time
class FFS:
    def __init__(s, path, lowcyl, highcyl, heads=16, bpt=63):
        s.f=open(path,'r+b'); s.off=lowcyl*heads*bpt*512; s.n=(highcyl-lowcyl+1)*heads*bpt
        s.root=(s.n-1+2)//2
        r=s.blk(s.root); assert s.L(r,0)==2 and s.sl(r,508)==1, 'not a root block'
        assert s.sl(r,312)==-1, 'bitmap not valid'
        s.bmblocks=[]
        for i in range(25):
            b=s.L(r,316+i*4)
            if b: s.bmblocks.append(b)
        ext=s.L(r,416)
        while ext:
            e=s.blk(ext)
            for i in range(127):
                b=s.L(e,i*4)
                if b: s.bmblocks.append(b)
            ext=s.L(e,508)
        s.bm=[bytearray(s.blk(b)) for b in s.bmblocks]
    L=staticmethod(lambda b,o: struct.unpack('>I',b[o:o+4])[0])
    sl=staticmethod(lambda b,o: struct.unpack('>i',b[o:o+4])[0])
    @staticmethod
    def P(b,o,v): b[o:o+4]=struct.pack('>I',v & 0xffffffff)
    def blk(s,b): s.f.seek(s.off+b*512); return s.f.read(512)
    def wblk(s,b,data): assert len(data)==512; s.f.seek(s.off+b*512); s.f.write(bytes(data))
    # ---- bitmap (bit set = free), covers blocks 2 .. n-1
    def _bit(s,b):
        i=b-2; per=(512-4)*8; return i//per, 4+((i%per)//32)*4, (i%per)%32
    def isfree(s,b):
        k,o,bit=s._bit(b); return (s.L(s.bm[k],o)>>bit)&1
    def setfree(s,b,free):
        k,o,bit=s._bit(b); v=s.L(s.bm[k],o)
        v = v|(1<<bit) if free else v&~(1<<bit); s.P(s.bm[k],o,v)
    def alloc(s,count,near=None):
        out=[]; b=near or s.root+1
        tried=0
        while len(out)<count:
            if b>=s.n: b=2
            if s.isfree(b): s.setfree(b,False); out.append(b)
            b+=1; tried+=1
            assert tried<=s.n, 'disk full'
        return out
    def flush_bitmap(s):
        for blkno,bm in zip(s.bmblocks,s.bm):
            s.P(bm,0,0); t=sum(struct.unpack('>128I',bytes(bm)))&0xffffffff; s.P(bm,0,(-t)&0xffffffff); s.wblk(blkno,bm)
    # ---- headers
    @staticmethod
    def csum(b,o=20):
        b[o:o+4]=b'\0\0\0\0'; t=sum(struct.unpack('>128I',bytes(b)))&0xffffffff; b[o:o+4]=struct.pack('>I',(-t)&0xffffffff)
    @staticmethod
    def hashname(name):
        h=len(name)
        for c in name.encode('latin-1'):
            if 97<=c<=122: c-=32
            h=(h*13+c)&0x7ff
        return h%72
    def name(s,b): return b[433:433+b[432]].decode('latin-1')
    def date(s,b):
        t=time.time()-252460800  # since 1978-01-01
        days=int(t//86400); mins=int((t%86400)//60); ticks=int((t%60)*50)
        s.P(b,420,days); s.P(b,424,mins); s.P(b,428,ticks)
    def lookup(s,dirblk,name):
        d=s.blk(dirblk); h=s.L(d,24+s.hashname(name)*4)
        while h:
            e=s.blk(h)
            if s.name(e).lower()==name.lower(): return h
            h=s.L(e,496)
        return 0
    def path(s,p):
        b=s.root
        for part in [x for x in p.split('/') if x]:
            b=s.lookup(b,part); assert b, 'not found: '+part
        return b
    def entries(s,dirblk):
        d=s.blk(dirblk)
        for i in range(72):
            h=s.L(d,24+i*4)
            while h:
                e=s.blk(h); yield s.name(e), h, s.sl(e,508); h=s.L(e,496)
    def readfile(s,h):
        e=s.blk(h); size=s.L(e,324); blocks=[]; cur=e
        while True:
            n=s.L(cur,8)
            for i in range(n): blocks.append(s.L(cur,24+(71-i)*4))
            ext=s.L(cur,504)
            if not ext: break
            cur=s.blk(ext)
        return b''.join(s.blk(x) for x in blocks)[:size]
    def _link(s,dirblk,hdr,name):
        d=bytearray(s.blk(dirblk)); slot=24+s.hashname(name)*4
        h=s.L(d,slot)
        if h==0 or hdr<h:              # keep the chain in block order
            hb=bytearray(s.blk(hdr)); s.P(hb,496,h); s.csum(hb); s.wblk(hdr,hb)
            s.P(d,slot,hdr)
        else:
            prev=h
            while True:
                pb=bytearray(s.blk(prev)); nxt=s.L(pb,496)
                if nxt==0 or hdr<nxt:
                    hb=bytearray(s.blk(hdr)); s.P(hb,496,nxt); s.csum(hb); s.wblk(hdr,hb)
                    s.P(pb,496,hdr); s.csum(pb); s.wblk(prev,pb); break
                prev=nxt
        s.date(d); s.csum(d); s.wblk(dirblk,d)
    def _unlink(s,dirblk,hdr,name):
        d=bytearray(s.blk(dirblk)); slot=24+s.hashname(name)*4
        nxt=s.L(s.blk(hdr),496); h=s.L(d,slot)
        if h==hdr: s.P(d,slot,nxt)
        else:
            while h:
                pb=bytearray(s.blk(h))
                if s.L(pb,496)==hdr: s.P(pb,496,nxt); s.csum(pb); s.wblk(h,pb); break
                h=s.L(pb,496)
            else: raise Exception('not in chain')
        s.date(d); s.csum(d); s.wblk(dirblk,d)
    def delete(s,dirblk,name):
        h=s.lookup(dirblk,name)
        if not h: return False
        e=s.blk(h); assert s.sl(e,508)==-3, 'only files'
        cur=e; blocks=[h]
        while True:
            for i in range(s.L(cur,8)): s.setfree(s.L(cur,24+(71-i)*4),True)
            ext=s.L(cur,504)
            if not ext: break
            s.setfree(ext,True); cur=s.blk(ext)
        s._unlink(dirblk,h,name); s.setfree(h,True)
        return True
    @staticmethod
    def checkname(name):
        # AmigaDOS file/drawer names are at most 30 characters (longer names break
        # DOS and AGS2: "error copying" and back to Workbench)
        assert 0<len(name)<=30 and '/' not in name and ':' not in name, 'bad AmigaDOS name (max 30 chars): '+name
    def mkdir(s,dirblk,name):
        s.checkname(name)
        h=s.lookup(dirblk,name)
        if h: return h
        h,=s.alloc(1)
        b=bytearray(512); s.P(b,0,2); s.P(b,4,h); s.P(b,500,dirblk); s.P(b,508,2)
        nb=name.encode('latin-1'); b[432]=len(nb); b[433:433+len(nb)]=nb; s.date(b); s.csum(b); s.wblk(h,b)
        s._link(dirblk,h,name); return h
    def create(s,dirblk,name,data,comment=b''):
        s.checkname(name)
        s.delete(dirblk,name)
        nd=(len(data)+511)//512; next_=(max(0,nd-72)+71)//72
        blocks=s.alloc(1+nd+next_)
        h=blocks[0]; data_blocks=blocks[1:1+nd]; exts=blocks[1+nd:]
        for i,db in enumerate(data_blocks):
            chunk=data[i*512:(i+1)*512]; s.wblk(db,chunk+bytes(512-len(chunk)))
        hb=bytearray(512); s.P(hb,0,2); s.P(hb,4,h); s.P(hb,500,dirblk); s.P(hb,508,(-3)&0xffffffff)
        s.P(hb,324,len(data)); nb=name.encode('latin-1'); hb[432]=len(nb); hb[433:433+len(nb)]=nb; s.date(hb)
        if comment: hb[328]=len(comment); hb[329:329+len(comment)]=comment
        groups=[data_blocks[i:i+72] for i in range(0,max(nd,1),72)] if nd else [[]]
        holders=[(h,hb)]+[(x,None) for x in exts]
        for gi,(blkno,hdr) in enumerate(holders):
            g=groups[gi] if gi<len(groups) else []
            if hdr is None:
                hdr=bytearray(512); s.P(hdr,0,16); s.P(hdr,4,blkno); s.P(hdr,500,h); s.P(hdr,508,(-3)&0xffffffff)
            s.P(hdr,8,len(g))
            for i,x in enumerate(g): s.P(hdr,24+(71-i)*4,x)
            if g and gi==0: s.P(hdr,16,g[0])
            s.P(hdr,504,holders[gi+1][0] if gi+1<len(holders) else 0)
            s.csum(hdr); s.wblk(blkno,hdr)
        s._link(dirblk,h,name)
        return h
    def close(s):
        s.flush_bitmap()
        r=bytearray(s.blk(s.root)); s.date(r)  # disk altered (420..) is root's own date field area
        s.csum(r); s.wblk(s.root,r); s.f.close()
