/*
 * m68k.c - a small 68000 interpreter for the test harness (tools/amiga.c).
 * The user-mode instruction set of the 68000 without BCD and MOVEP; one
 * stack pointer; timings are rough (4 cycles a word of memory traffic).
 * It calls hook(pc) before every instruction and illg(op) for anything
 * it does not know (an F-line, A-line or TRAP is an error in this game).
 */
#include <stdint.h>
#include "m68k.h"

static uint32_t D[8], A[8], PC, PPC, SR, USP;
static int cyc, budget, stopnow;

#define FX 0x10
#define FN 0x08
#define FZ 0x04
#define FV 0x02
#define FC 0x01

static uint32_t MASK(int s) { return s == 1 ? 0xff : s == 2 ? 0xffff : 0xffffffffu; }
static uint32_t MSB(int s) { return s == 1 ? 0x80 : s == 2 ? 0x8000 : 0x80000000u; }
static int32_t SX(uint32_t v, int s) { return s == 1 ? (int8_t)v : s == 2 ? (int16_t)v : (int32_t)v; }

static uint32_t rd(uint32_t a, int s) {
	cyc += s == 4 ? 8 : 4;
	if (s == 1) return m68k_read_memory_8(a) & 0xff;
	if (s == 2) return m68k_read_memory_16(a) & 0xffff;
	return m68k_read_memory_32(a);
}
static void wr(uint32_t a, int s, uint32_t v) {
	cyc += s == 4 ? 8 : 4;
	if (s == 1) m68k_write_memory_8(a, v & 0xff);
	else if (s == 2) m68k_write_memory_16(a, v & 0xffff);
	else m68k_write_memory_32(a, v);
}
static uint32_t f16(void) { uint32_t v = m68k_read_memory_16(PC) & 0xffff; PC += 2; cyc += 4; return v; }
static uint32_t f32(void) { uint32_t v = f16() << 16; return v | f16(); }

static void bad(int op) { illg(op); stopnow = 1; }

typedef struct { int k; int r; uint32_t a; uint32_t v; } EA;  /* k: 0 Dn 1 An 2 memory 3 immediate */

static uint32_t idx(uint32_t base) {
	uint32_t e = f16();
	int r = (e >> 12) & 7;
	uint32_t x = (e & 0x8000) ? A[r] : D[r];
	if (!(e & 0x800)) x = (uint32_t)(int16_t)x;
	cyc += 2;
	return base + (int8_t)(e & 0xff) + x;
}
static int resolve(EA *e, int mode, int reg, int s) {
	int inc = (s == 1 && reg == 7) ? 2 : s;
	switch (mode) {
	case 0: e->k = 0; e->r = reg; return 1;
	case 1: e->k = 1; e->r = reg; return 1;
	case 2: e->k = 2; e->a = A[reg]; return 1;
	case 3: e->k = 2; e->a = A[reg]; A[reg] += inc; return 1;
	case 4: A[reg] -= inc; e->k = 2; e->a = A[reg]; cyc += 2; return 1;
	case 5: e->k = 2; e->a = A[reg] + (int16_t)f16(); return 1;
	case 6: e->k = 2; e->a = idx(A[reg]); return 1;
	case 7:
		switch (reg) {
		case 0: e->k = 2; e->a = (uint32_t)(int16_t)f16(); return 1;
		case 1: e->k = 2; e->a = f32(); return 1;
		case 2: { uint32_t b = PC; e->k = 2; e->a = b + (int16_t)f16(); return 1; }
		case 3: { uint32_t b = PC; e->k = 2; e->a = idx(b); return 1; }
		case 4: e->k = 3; e->v = s == 4 ? f32() : (f16() & MASK(s)); return 1;
		}
	}
	return 0;
}
static uint32_t get(EA *e, int s) {
	switch (e->k) {
	case 0: return D[e->r] & MASK(s);
	case 1: return A[e->r] & MASK(s);
	case 2: return rd(e->a, s);
	default: return e->v & MASK(s);
	}
}
static void put(EA *e, int s, uint32_t v) {
	switch (e->k) {
	case 0: D[e->r] = (D[e->r] & ~MASK(s)) | (v & MASK(s)); break;
	case 1: A[e->r] = v; break;
	case 2: wr(e->a, s, v); break;
	}
}

static void nz(uint32_t v, int s) {
	SR &= ~(FN | FZ | FV | FC);
	if (v & MSB(s)) SR |= FN;
	if (!(v & MASK(s))) SR |= FZ;
}
static uint32_t addf(uint32_t d, uint32_t src, int s, int x, int setx) {
	uint32_t m = MASK(s);
	uint64_t r64 = (uint64_t)(d & m) + (src & m) + (x ? 1 : 0);
	uint32_t r = (uint32_t)r64 & m;
	int c = (r64 >> (s * 8)) & 1;
	int v = ((~(d ^ src)) & (d ^ r) & MSB(s)) != 0;
	uint32_t keepz = SR & FZ;
	SR &= ~(FN | FZ | FV | FC | (setx ? FX : 0));
	if (r & MSB(s)) SR |= FN;
	if (!r) SR |= (setx == 2 ? keepz : FZ);
	if (v) SR |= FV;
	if (c) SR |= FC | (setx ? FX : 0);
	return r;
}
static uint32_t subf(uint32_t d, uint32_t src, int s, int x, int setx) {   /* d - src */
	uint32_t m = MASK(s);
	d &= m; src &= m;
	uint64_t r64 = (uint64_t)d - src - (x ? 1 : 0);
	uint32_t r = (uint32_t)r64 & m;
	int c = (uint64_t)src + (x ? 1 : 0) > d;
	int v = ((d ^ src) & (d ^ r) & MSB(s)) != 0;
	uint32_t keepz = SR & FZ;
	SR &= ~(FN | FZ | FV | FC | (setx ? FX : 0));
	if (r & MSB(s)) SR |= FN;
	if (!r) SR |= (setx == 2 ? keepz : FZ);
	if (v) SR |= FV;
	if (c) SR |= FC | (setx ? FX : 0);
	return r;
}
static int cc(int c) {
	int n = !!(SR & FN), z = !!(SR & FZ), v = !!(SR & FV), C = !!(SR & FC);
	switch (c) {
	case 0: return 1; case 1: return 0;
	case 2: return !C && !z; case 3: return C || z;
	case 4: return !C; case 5: return C;
	case 6: return !z; case 7: return z;
	case 8: return !v; case 9: return v;
	case 10: return !n; case 11: return n;
	case 12: return n == v; case 13: return n != v;
	case 14: return !z && n == v; default: return z || n != v;
	}
}
static int szcode(int c) { return c == 0 ? 1 : c == 1 ? 2 : c == 2 ? 4 : 0; }
static void push32(uint32_t v) { A[7] -= 4; wr(A[7], 4, v); }
static uint32_t pop32(void) { uint32_t v = rd(A[7], 4); A[7] += 4; return v; }

static void bitop(int type, uint32_t bit, int mode, int reg, int op) {
	if (mode == 0) {
		bit &= 31;
		uint32_t m = 1u << bit;
		if (D[reg] & m) SR &= ~FZ; else SR |= FZ;
		if (type == 1) D[reg] ^= m; else if (type == 2) D[reg] &= ~m; else if (type == 3) D[reg] |= m;
		return;
	}
	EA e; if (!resolve(&e, mode, reg, 1)) { bad(op); return; }
	bit &= 7;
	uint32_t v = get(&e, 1), m = 1u << bit;
	if (v & m) SR &= ~FZ; else SR |= FZ;
	if (type == 0) return;
	if (type == 1) v ^= m; else if (type == 2) v &= ~m; else v |= m;
	put(&e, 1, v);
}

static void shift(int type, int left, int cnt, uint32_t *pv, int s) {
	uint32_t v = *pv & MASK(s), m = MSB(s);
	int vflag = 0, c = 0;
	for (int i = 0; i < cnt; i++) {
		if (left) {
			c = (v & m) != 0;
			uint32_t nv = (v << 1) & MASK(s);
			if (type == 2) nv |= (SR & FX) ? 1 : 0;
			if (type == 3) nv |= c;
			if (type == 0 && ((nv ^ v) & m)) vflag = 1;
			v = nv;
		} else {
			c = v & 1;
			uint32_t nv = v >> 1;
			if (type == 0) nv |= v & m;
			if (type == 2 && (SR & FX)) nv |= m;
			if (type == 3 && c) nv |= m;
			v = nv;
		}
		if (type != 3) { if (c) SR |= FX; else SR &= ~FX; }
	}
	cyc += 2 * cnt;
	SR &= ~(FN | FZ | FV | FC);
	if (cnt == 0) { if (type == 2 && (SR & FX)) SR |= FC; }
	else if (c) SR |= FC;
	if (vflag) SR |= FV;
	if (v & m) SR |= FN;
	if (!v) SR |= FZ;
	*pv = v;
}

static void exec(uint32_t op) {
	int mode = (op >> 3) & 7, reg = op & 7, rx = (op >> 9) & 7;
	EA e, f;
	switch (op >> 12) {
	case 0x0: {
		if ((op & 0x100) && mode != 1) { bitop((op >> 6) & 3, D[rx], mode, reg, op); return; }
		if (op & 0x100) { bad(op); return; }         /* MOVEP */
		int kind = rx;
		if (kind == 4) { uint32_t b = f16() & 0xff; bitop((op >> 6) & 3, b, mode, reg, op); return; }
		int s = szcode((op >> 6) & 3);
		if (!s) { bad(op); return; }
		if ((op & 0x3f) == 0x3c && (kind == 0 || kind == 1 || kind == 5)) {   /* to CCR / SR */
			uint32_t im = f16();
			uint32_t m = s == 1 ? 0x1f : 0xffff, cur = SR & m;
			uint32_t r = kind == 0 ? cur | im : kind == 1 ? cur & im : cur ^ im;
			SR = (SR & ~m) | (r & m);
			return;
		}
		uint32_t im = s == 4 ? f32() : (f16() & MASK(s));
		if (!resolve(&e, mode, reg, s)) { bad(op); return; }
		uint32_t d = get(&e, s), r;
		switch (kind) {
		case 0: r = d | im; nz(r, s); put(&e, s, r); return;
		case 1: r = d & im; nz(r, s); put(&e, s, r); return;
		case 2: r = subf(d, im, s, 0, 1); put(&e, s, r); return;
		case 3: r = addf(d, im, s, 0, 1); put(&e, s, r); return;
		case 5: r = d ^ im; nz(r, s); put(&e, s, r); return;
		case 6: subf(d, im, s, 0, 0); return;
		}
		bad(op); return;
	}
	case 0x1: case 0x2: case 0x3: {
		int s = (op >> 12) == 1 ? 1 : (op >> 12) == 3 ? 2 : 4;
		if (!resolve(&e, mode, reg, s)) { bad(op); return; }
		uint32_t v = get(&e, s);
		int dm = (op >> 6) & 7;
		if (dm == 1) { A[rx] = s == 2 ? (uint32_t)(int16_t)v : v; return; }
		if (!resolve(&f, dm, rx, s)) { bad(op); return; }
		put(&f, s, v);
		uint32_t x = SR & FX; nz(v, s); SR |= x;
		return;
	}
	case 0x4: {
		if (op == 0x4e75) { PC = pop32(); return; }
		if (op == 0x4e71) return;
		if (op == 0x4e73) { SR = rd(A[7], 2); A[7] += 2; PC = pop32(); return; }
		if (op == 0x4e77) { SR = (SR & 0xff00) | (rd(A[7], 2) & 0x1f); A[7] += 2; PC = pop32(); return; }
		if ((op & 0xfff8) == 0x4e50) { int16_t d = f16(); push32(A[reg]); A[reg] = A[7]; A[7] += d; return; }
		if ((op & 0xfff8) == 0x4e58) { A[7] = A[reg]; A[reg] = pop32(); return; }
		if ((op & 0xfff0) == 0x4e60) { if (op & 8) A[reg] = A[7]; else A[7] = A[reg]; return; }
		if ((op & 0xffc0) == 0x4e80 || (op & 0xffc0) == 0x4ec0) {
			if (!resolve(&e, mode, reg, 4) || e.k != 2) { bad(op); return; }
			if ((op & 0xffc0) == 0x4e80) push32(PC);
			PC = e.a; return;
		}
		if ((op & 0xf1c0) == 0x41c0) {
			if (!resolve(&e, mode, reg, 4) || e.k != 2) { bad(op); return; }
			A[rx] = e.a; return;
		}
		if ((op & 0xfff8) == 0x4840) { uint32_t v = (D[reg] << 16) | (D[reg] >> 16); D[reg] = v; uint32_t x = SR & FX; nz(v, 4); SR |= x; return; }
		if ((op & 0xffc0) == 0x4840) {
			if (!resolve(&e, mode, reg, 4) || e.k != 2) { bad(op); return; }
			push32(e.a); return;
		}
		if ((op & 0xfff8) == 0x4880) { D[reg] = (D[reg] & 0xffff0000) | ((uint32_t)(int8_t)D[reg] & 0xffff); uint32_t x = SR & FX; nz(D[reg], 2); SR |= x; return; }
		if ((op & 0xfff8) == 0x48c0) { D[reg] = (uint32_t)(int16_t)D[reg]; uint32_t x = SR & FX; nz(D[reg], 4); SR |= x; return; }
		if ((op & 0xfb80) == 0x4880) {      /* MOVEM */
			int s = (op & 0x40) ? 4 : 2, tomem = !(op & 0x400);
			uint32_t msk = f16();
			uint32_t *R[16]; for (int i = 0; i < 8; i++) { R[i] = &D[i]; R[i + 8] = &A[i]; }
			if (tomem) {
				if (mode == 4) {
					uint32_t a = A[reg];
					for (int k = 0; k < 16; k++) if (msk & (1 << k)) { a -= s; wr(a, s, *R[15 - k]); }
					A[reg] = a;
				} else {
					if (!resolve(&e, mode, reg, s) || e.k != 2) { bad(op); return; }
					uint32_t a = e.a;
					for (int k = 0; k < 16; k++) if (msk & (1 << k)) { wr(a, s, *R[k]); a += s; }
				}
			} else {
				uint32_t a;
				if (mode == 3) a = A[reg];
				else { if (!resolve(&e, mode, reg, s) || e.k != 2) { bad(op); return; } a = e.a; }
				for (int k = 0; k < 16; k++) if (msk & (1 << k)) {
					uint32_t v = rd(a, s); if (s == 2) v = (uint32_t)(int16_t)v;
					*R[k] = v; a += s;
				}
				if (mode == 3) A[reg] = a;
			}
			return;
		}
		if ((op & 0xffc0) == 0x40c0) { if (!resolve(&e, mode, reg, 2)) { bad(op); return; } put(&e, 2, SR); return; }
		if ((op & 0xffc0) == 0x44c0) { if (!resolve(&e, mode, reg, 2)) { bad(op); return; } SR = (SR & 0xff00) | (get(&e, 2) & 0x1f); return; }
		if ((op & 0xffc0) == 0x46c0) { if (!resolve(&e, mode, reg, 2)) { bad(op); return; } SR = get(&e, 2); return; }
		if ((op & 0xffc0) == 0x4ac0) {      /* TAS */
			if (!resolve(&e, mode, reg, 1)) { bad(op); return; }
			uint32_t v = get(&e, 1); uint32_t x = SR & FX; nz(v, 1); SR |= x; put(&e, 1, v | 0x80); return;
		}
		int s = szcode((op >> 6) & 3);
		int grp = op & 0xff00;
		if (s && (grp == 0x4000 || grp == 0x4200 || grp == 0x4400 || grp == 0x4600 || grp == 0x4a00)) {
			if (!resolve(&e, mode, reg, s)) { bad(op); return; }
			uint32_t d = grp == 0x4200 ? 0 : get(&e, s), r, x = SR & FX;
			switch (grp) {
			case 0x4000: r = subf(0, d, s, (SR & FX) != 0, 2); put(&e, s, r); return;
			case 0x4200: nz(0, s); SR |= x; put(&e, s, 0); return;
			case 0x4400: r = subf(0, d, s, 0, 1); put(&e, s, r); return;
			case 0x4600: r = ~d & MASK(s); nz(r, s); SR |= x; put(&e, s, r); return;
			case 0x4a00: nz(d, s); SR |= x; return;
			}
		}
		bad(op); return;
	}
	case 0x5: {
		int c = (op >> 8) & 15;
		if (((op >> 6) & 3) == 3) {
			if (mode == 1) {           /* DBcc */
				uint32_t b = PC; int16_t d = f16();
				if (!cc(c)) {
					uint32_t w = (D[reg] - 1) & 0xffff;
					D[reg] = (D[reg] & 0xffff0000) | w;
					if (w != 0xffff) PC = b + d;
				}
				return;
			}
			if (!resolve(&e, mode, reg, 1)) { bad(op); return; }
			put(&e, 1, cc(c) ? 0xff : 0); return;
		}
		int s = szcode((op >> 6) & 3);
		uint32_t q = rx ? rx : 8;
		if (mode == 1) { if (op & 0x100) A[reg] -= q; else A[reg] += q; return; }
		if (!resolve(&e, mode, reg, s)) { bad(op); return; }
		uint32_t d = get(&e, s);
		put(&e, s, (op & 0x100) ? subf(d, q, s, 0, 1) : addf(d, q, s, 0, 1));
		return;
	}
	case 0x6: {
		int c = (op >> 8) & 15;
		uint32_t b = PC;
		int32_t d = (int8_t)(op & 0xff);
		if (d == 0) d = (int16_t)f16();
		if (c == 1) { push32(PC); PC = b + d; return; }
		if (cc(c)) PC = b + d;
		return;
	}
	case 0x7: {
		if (op & 0x100) { bad(op); return; }
		D[rx] = (uint32_t)(int8_t)(op & 0xff);
		uint32_t x = SR & FX; nz(D[rx], 4); SR |= x; return;
	}
	case 0x8: case 0xc: {
		int line = op >> 12;
		if ((op & 0x1c0) == 0x0c0 || (op & 0x1c0) == 0x1c0) {
			if (!resolve(&e, mode, reg, 2)) { bad(op); return; }
			uint32_t src = get(&e, 2);
			int sgn = (op & 0x100) != 0;
			uint32_t x = SR & FX;
			if (line == 0xc) {
				uint32_t r = sgn ? (uint32_t)((int32_t)(int16_t)D[rx] * (int32_t)(int16_t)src) : (D[rx] & 0xffff) * src;
				D[rx] = r; nz(r, 4); SR |= x; cyc += 60; return;
			}
			cyc += 136;
			if (src == 0) { bad(op); return; }
			if (!sgn) {
				uint32_t q = D[rx] / src, rm = D[rx] % src;
				if (q > 0xffff) { SR |= FV; SR &= ~FC; return; }
				D[rx] = (rm << 16) | q; nz(q, 2); SR |= x; return;
			} else {
				int32_t dv = (int32_t)D[rx], sv = (int16_t)src;
				int32_t q = dv / sv, rm = dv % sv;
				if (q > 32767 || q < -32768) { SR |= FV; SR &= ~FC; return; }
				D[rx] = ((uint32_t)(rm & 0xffff) << 16) | (q & 0xffff); nz(q, 2); SR |= x; return;
			}
		}
		if ((op & 0x1f0) == 0x100) { bad(op); return; }        /* ABCD / SBCD */
		if (line == 0xc && ((op & 0x1f8) == 0x140 || (op & 0x1f8) == 0x148 || (op & 0x1f8) == 0x188)) {
			uint32_t t;
			if ((op & 0x1f8) == 0x140) { t = D[rx]; D[rx] = D[reg]; D[reg] = t; }
			else if ((op & 0x1f8) == 0x148) { t = A[rx]; A[rx] = A[reg]; A[reg] = t; }
			else { t = D[rx]; D[rx] = A[reg]; A[reg] = t; }
			return;
		}
		int s = szcode((op >> 6) & 3);
		if (!s) { bad(op); return; }
		if (!resolve(&e, mode, reg, s)) { bad(op); return; }
		uint32_t a = get(&e, s), d = D[rx], r, x = SR & FX;
		r = line == 8 ? (a | d) : (a & d);
		nz(r, s); SR |= x;
		if (op & 0x100) put(&e, s, r); else D[rx] = (D[rx] & ~MASK(s)) | (r & MASK(s));
		return;
	}
	case 0x9: case 0xd: {
		int add = (op >> 12) == 0xd;
		int om = (op >> 6) & 7;
		if (om == 3 || om == 7) {
			int s = om == 3 ? 2 : 4;
			if (!resolve(&e, mode, reg, s)) { bad(op); return; }
			uint32_t v = get(&e, s); if (s == 2) v = (uint32_t)(int16_t)v;
			if (add) A[rx] += v; else A[rx] -= v;
			return;
		}
		int s = szcode(om & 3);
		if ((om & 4) && (mode == 0 || mode == 1)) {      /* ADDX / SUBX */
			uint32_t sv, dv; int x = (SR & FX) != 0;
			if (mode == 0) { sv = D[reg]; dv = D[rx]; }
			else { resolve(&e, 4, reg, s); sv = get(&e, s); resolve(&f, 4, rx, s); dv = get(&f, s); }
			uint32_t r = add ? addf(dv, sv, s, x, 2) : subf(dv, sv, s, x, 2);
			if (mode == 0) D[rx] = (D[rx] & ~MASK(s)) | r; else put(&f, s, r);
			return;
		}
		if (!resolve(&e, mode, reg, s)) { bad(op); return; }
		uint32_t a = get(&e, s), d = D[rx] & MASK(s), r;
		if (om & 4) { r = add ? addf(a, d, s, 0, 1) : subf(a, d, s, 0, 1); put(&e, s, r); }
		else { r = add ? addf(d, a, s, 0, 1) : subf(d, a, s, 0, 1); D[rx] = (D[rx] & ~MASK(s)) | r; }
		return;
	}
	case 0xb: {
		int om = (op >> 6) & 7;
		if (om == 3 || om == 7) {
			int s = om == 3 ? 2 : 4;
			if (!resolve(&e, mode, reg, s)) { bad(op); return; }
			uint32_t v = get(&e, s); if (s == 2) v = (uint32_t)(int16_t)v;
			subf(A[rx], v, 4, 0, 0); return;
		}
		int s = szcode(om & 3);
		if (om & 4) {
			if (mode == 1) {         /* CMPM */
				resolve(&e, 3, reg, s); uint32_t sv = get(&e, s);
				resolve(&f, 3, rx, s); uint32_t dv = get(&f, s);
				subf(dv, sv, s, 0, 0); return;
			}
			if (!resolve(&e, mode, reg, s)) { bad(op); return; }
			uint32_t r = get(&e, s) ^ D[rx], x = SR & FX;
			nz(r, s); SR |= x; put(&e, s, r); return;
		}
		if (!resolve(&e, mode, reg, s)) { bad(op); return; }
		subf(D[rx], get(&e, s), s, 0, 0); return;
	}
	case 0xe: {
		if (((op >> 6) & 3) == 3) {
			int type = (op >> 9) & 3, left = (op >> 8) & 1;
			if (op & 0x800) { bad(op); return; }
			if (!resolve(&e, mode, reg, 2)) { bad(op); return; }
			uint32_t v = get(&e, 2);
			shift(type, left, 1, &v, 2);
			put(&e, 2, v); return;
		}
		int s = szcode((op >> 6) & 3);
		int cnt = (op & 0x20) ? (int)(D[rx] & 63) : (rx ? rx : 8);
		int type = (op >> 3) & 3, left = (op >> 8) & 1;
		uint32_t v = D[reg] & MASK(s);
		shift(type, left, cnt, &v, s);
		D[reg] = (D[reg] & ~MASK(s)) | (v & MASK(s));
		return;
	}
	default:
		bad(op); return;
	}
}

void m68k_init(void) {}
void m68k_set_cpu_type(int t) { (void)t; }
void m68k_pulse_reset(void) {
	for (int i = 0; i < 8; i++) D[i] = A[i] = 0;
	SR = 0x2700; PC = 0; USP = 0;
}
int m68k_execute(int n) {
	budget = n; cyc = 0; stopnow = 0;
	while (cyc < budget && !stopnow) {
		PPC = PC;
		hook(PC);
		uint32_t op = f16();
		exec(op);
	}
	return cyc;
}
int m68k_cycles_run(void) { return cyc; }
void m68k_end_timeslice(void) { stopnow = 1; }
unsigned int m68k_get_reg(void *ctx, int r) {
	(void)ctx;
	if (r >= M68K_REG_D0 && r <= M68K_REG_D7) return D[r - M68K_REG_D0];
	if (r >= M68K_REG_A0 && r <= M68K_REG_A7) return A[r - M68K_REG_A0];
	switch (r) {
	case M68K_REG_PC: return PC;
	case M68K_REG_SR: return SR;
	case M68K_REG_SP: case M68K_REG_USP: case M68K_REG_ISP: return A[7];
	case M68K_REG_PPC: return PPC;
	}
	return 0;
}
void m68k_set_reg(int r, unsigned int v) {
	if (r >= M68K_REG_D0 && r <= M68K_REG_D7) { D[r - M68K_REG_D0] = v; return; }
	if (r >= M68K_REG_A0 && r <= M68K_REG_A7) { A[r - M68K_REG_A0] = v; return; }
	switch (r) {
	case M68K_REG_PC: PC = v; break;
	case M68K_REG_SR: SR = v & 0xffff; break;
	case M68K_REG_SP: case M68K_REG_USP: case M68K_REG_ISP: A[7] = v; break;
	case M68K_REG_PPC: PPC = v; break;
	}
}
