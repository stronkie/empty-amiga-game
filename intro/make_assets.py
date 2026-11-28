# make_assets.py - pictures, tables and palette for the Stronkie Soft boot intro
import math, struct
from PIL import Image
import os
TK=os.environ.get('AMIGA_TK','..')
W,H=320,256
img=[[0]*W for _ in range(H)]
logo=Image.open(TK+'/art/stronkiesoft_logo.png').convert('RGBA')
cmap={(10,10,30):1,(255,226,30):2,(40,200,240):3,(225,150,0):4,(20,130,190):5,(255,160,200):6,(255,255,255):7}
LX,LY=8,66
def lidx(x,y):
    r,g,b,a=logo.getpixel((x,y))
    if a==0: return 0
    i=cmap[(r,g,b)]
    if i==2 and y<=5 and x<30: i=8          # antenna bulb: own colour so it can flash
    return i
for y in range(44):
    for x in range(158):
        i=lidx(x,y)
        if i:
            for dy in (0,1):
                for dx in (0,1): img[LY+2*y+dy][LX+2*x+dx]=i
# ---- font 6x7 (own design)
FONT={
'A':[".####.","##..##","##..##","######","##..##","##..##","##..##"],
'B':["#####.","##..##","##..##","#####.","##..##","##..##","#####."],
'C':[".####.","##..##","##....","##....","##....","##..##",".####."],
'E':["######","##....","##....","#####.","##....","##....","######"],
'F':["######","##....","##....","#####.","##....","##....","##...."],
'I':["######","..##..","..##..","..##..","..##..","..##..","######"],
'L':["##....","##....","##....","##....","##....","##....","######"],
'M':["##...#","###.##","######","##.#.#","##...#","##...#","##...#"],
'N':["##..##","###.##","######","##.###","##..##","##..##","##..##"],
'O':[".####.","##..##","##..##","##..##","##..##","##..##",".####."],
'P':["#####.","##..##","##..##","#####.","##....","##....","##...."],
'R':["#####.","##..##","##..##","#####.","##.##.","##..##","##..##"],
'S':[".#####","##....","##....",".####.","....##","....##","#####."],
'T':["######","..##..","..##..","..##..","..##..","..##..","..##.."],
'U':["##..##","##..##","##..##","##..##","##..##","##..##",".####."],
'Y':["##..##","##..##","##..##",".####.","..##..","..##..","..##.."],
'1':["..##..",".###..","..##..","..##..","..##..","..##..",".####."],
'9':[".####.","##..##","##..##",".#####","....##","##..##",".####."],
'6':[".####.","##....","##....","#####.","##..##","##..##",".####."],
':':["......","..##..","..##..","......","..##..","..##..","......"],
'/':["....##","...##.","...##.","..##..",".##...",".##...","##...."],
'-':["......","......","......","######","......","......","......"],
' ':["......"]*7}
def text(s,x,y,col,shadow,scale=1):
    for k,ch in enumerate(s):
        g=FONT[ch]
        for gy,row in enumerate(g):
            for gx,c in enumerate(row):
                if c=='#':
                    for sy in range(scale):
                        for sx in range(scale):
                            px=x+k*8*scale+gx*scale+sx; py=y+gy*scale+sy
                            if shadow is not None:
                                for ox,oy in ((1,1),(scale,scale)):
                                    if img[py+oy][px+ox]==0: img[py+oy][px+ox]=shadow
                            img[py][px]=col
def center(s,scale): return (W-len(s)*8*scale)//2
PRES='PRESENTS'
text(PRES,96,170,9,1,2)                 # bytes 12..27, rows 170..185
L1='MUSIC: INTRO NUMMA BY ANIMAL'; L2='OF SUPERIOR ART CREATIONS 1996'
text(L1,center(L1,1)//8*8,220,10,11); text(L2,center(L2,1)//8*8,232,10,11)
# ---- planes
def planes(pix,w,h,n=4):
    out=bytearray()
    for p in range(n):
        for y in range(h):
            for bx in range(w//8):
                v=0
                for b in range(8):
                    if (pix[y][bx*8+b]>>p)&1: v|=0x80>>b
                out.append(v)
    return out
open('build/final.bin','wb').write(planes(img,W,H))
# eyes closed: mascot rows 1x 18..21 -> screen 102..109, bytes 0..11
eyes=[row[:96] for row in img[102:110]]
for y in range(8):
    for x in range(96):
        lx=(x-LX)//2; ly=18+y//2
        if 0<=lx<158 and (12<=lx<=15 or 24<=lx<=27):
            eyes[y][x]=3 if ly<20 else 1
open('build/eyes.bin','wb').write(planes(eyes,96,8))
Image.new('P',(W,H)).save
# ---- palette (12 bit)
def c12(r,g,b): return ((r*15+127)//255<<8)|((g*15+127)//255<<4)|((b*15+127)//255)
pal=[0]*32
pal[0]=0x000; pal[1]=0x113; pal[2]=c12(255,226,30); pal[3]=c12(40,200,240); pal[4]=c12(225,150,0)
pal[5]=c12(20,130,190); pal[6]=c12(255,160,200); pal[7]=0xFFF; pal[8]=c12(255,226,30)
pal[9]=0xFFF; pal[10]=0x9BF; pal[11]=0x113
for i in range(12,16): pal[i]=0
pal[16]=0xCCF
for i in range(17,32): pal[i]=pal[i-16]
# ---- tables
def drop(y0,y1,g=1.1,damp=0.42):
    y=float(y0); v=0.0; out=[]; b=0
    while True:
        v+=g; y+=v
        if y>=y1:
            y=y1; v=-v*damp; b+=1
            if b>=3 or abs(v)<1.5: out.append(y1); break
        out.append(int(round(y)))
    return out
def rise(y0,y1,n=34,s=1.9):
    out=[]
    for k in range(1,n+1):
        t=k/n; t-=1; e=t*t*((s+1)*t+s)+1   # ease out back
        out.append(int(round(y0+(y1-y0)*e)))
    return out
mascot=drop(-84,70); word1=rise(262,70); word2=rise(262,110,s=0)
sine=[int(round(math.sin(2*math.pi*i/256)*32767)) for i in range(256)]
base=[]                                    # background gradient behind everything
for y in range(256):
    t=y/255
    r,g,b=0,0,int(round(4*(1-t)+1*t))
    base.append((r<<8)|(g<<4)|b)
def ramp(cols):                            # 15-line bar from dark to bright to dark
    out=[]
    for k in range(15):
        f=1-abs(k-7)/7.5
        out.append(tuple(int(round(c*f)) for c in cols))
    return [(r<<8)|(g<<4)|b for r,g,b in out]
bars=[ramp((15,4,11)),ramp((4,13,15)),ramp((15,12,2))]
fadetab=[[(v*l+8)//16 for v in range(16)] for l in range(17)]
# song length in frames (speed changes taken into account)
mod=open('intro.mod','rb').read()
sl=mod[950]; order=mod[952:952+sl]
speed=6; frames=0
for pos in range(sl):
    for r in range(64):
        for c in range(4):
            o=1084+order[pos]*1024+r*16+c*4
            if mod[o+2]&15==15 and 0<mod[o+3]<32: speed=mod[o+3]
        frames+=speed
def dw(name,vals,per=16):
    s=f'{name}:\n'
    for i in range(0,len(vals),per): s+='\tdc.w\t'+','.join(str(v) for v in vals[i:i+per])+'\n'
    return s
s='; generated by make_assets.py\n'
s+=f'SONGFRAMES\tequ\t{frames}\nMASCOTN\tequ\t{len(mascot)}\nWORDN\tequ\t{len(word1)}\n\tsection\ttables,data\n'
s+=dw('palette',pal)+dw('mascot_y',mascot)+dw('word1_y',word1)+dw('word2_y',word2)+dw('sinetab',sine)+dw('basegrad',base)
s+=dw('bar1',bars[0])+dw('bar2',bars[1])+dw('bar3',bars[2])
s+='fadetab:\n'+''.join('\tdc.b\t'+','.join(map(str,row))+'\n' for row in fadetab)
open('src/tables_gen.s','w').write(s)
# preview picture
pv=Image.new('RGB',(W,H))
for y in range(H):
    for x in range(W):
        v=pal[img[y][x]]; pv.putpixel((x,y),(((v>>8)&15)*17,((v>>4)&15)*17,(v&15)*17))
pv.resize((640,512),0).save('build/final_preview.png')
print('frames',frames,'mascot',len(mascot),'word',len(word1))
