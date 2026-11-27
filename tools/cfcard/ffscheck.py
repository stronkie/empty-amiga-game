import sys, struct
import os; exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ffs.py')).read())
fs=FFS(sys.argv[1],206,1899)
used={fs.root}|set(fs.bmblocks); bad=[]; files=0; dup=[]
def chk(b,blk,o=20):
    if sum(struct.unpack('>128I',b))&0xffffffff: bad.append(blk)
def mark(x):
    if x in used: dup.append(x)
    used.add(x)
def walk(d):
    global files
    for name,h,t in fs.entries(d):
        mark(h); e=fs.blk(h); chk(e,h)
        if t==2: walk(h)
        else:
            files+=1; cur=e
            while True:
                for i in range(fs.L(cur,8)): mark(fs.L(cur,24+(71-i)*4))
                ext=fs.L(cur,504)
                if not ext: break
                mark(ext); cur=fs.blk(ext); chk(cur,ext)
chk(fs.blk(fs.root),fs.root); walk(fs.root)
free={b for b in range(2,fs.n) if fs.isfree(b)}
print(sys.argv[1], 'files',files,'bad checksums',bad[:5],'double used',dup[:5],'used but free',len(used&free),'lost (not free, not used)',len(set(range(2,fs.n))-free-used))
