#!/bin/sh
# setup.sh - build the Stronkie Soft Amiga tools once per session (about 1 minute).
#   . /path/to/amiga-toolkit/setup.sh      (puts bin/ on the PATH)
TK="$(cd "$(dirname "${0:-.}")" 2>/dev/null && pwd)"
[ -f "$TK/setup.sh" ] || TK="$(pwd)"
mkdir -p "$TK/bin"
if [ ! -x "$TK/bin/vasmm68k_mot" ]; then
  (cd "$TK/vasm" && make CPU=m68k SYNTAX=mot >/dev/null 2>&1 && cp vasmm68k_mot vobjdump "$TK/bin/" 2>/dev/null)
fi
gcc -O2 -w -o "$TK/tools/pack/lz" "$TK/tools/pack/lz.c"
gcc -O2 -w -I"$TK/tools" -o "$TK/tools/pack/harness" "$TK/tools/pack/harness.c" "$TK/tools/m68k.c"
python3 "$TK/tools/asm68k.py" "$TK/tools/pack/stub.s" -o "$TK/tools/pack/stub.exe" -map "$TK/tools/pack/stub.map" >/dev/null
export PATH="$TK/bin:$PATH"
export AMIGA_TK="$TK"
echo "amiga-toolkit ready: $(ls "$TK/bin" | tr '\n' ' ') + packer"
