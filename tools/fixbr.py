import subprocess, re, sys
for it in range(300):
    r = subprocess.run(['python3','tools/asm68k.py','src/main.s','-I','build/demo','-I','build/gen','-I','src','-o','build/demo/test.game','-sym'],capture_output=True,text=True)
    out = r.stdout + r.stderr
    m = re.search(r'(src/\w+\.s):(\d+): short branch out of range', out)
    if not m:
        print(out[-1500:]); sys.exit(0 if "error" not in out else 1)
    f, ln = m.group(1), int(m.group(2))
    L = open(f).read().split('\n')
    L[ln-1] = re.sub(r'\b(b\w\w|bra|bsr)\.s\b', r'\1', L[ln-1], count=1)
    open(f,'w').write('\n'.join(L))
    print('fixed', f, ln)
