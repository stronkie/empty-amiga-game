#include <sys/stat.h>
/*
 * amiga.c - a small Amiga 500 test harness (Ghost Zappers: Tycoon, Stronkie's Baseball)
 *
 * 68000 (Musashi) + 512K chip + 512K slow (trapdoor) RAM, the custom chip
 * registers the game uses, CIA-A keyboard/mouse button, a copper + bitplane +
 * sprite renderer for screenshots, and stubs for the few exec / graphics /
 * dos / intuition calls a Workbench 1.3 program makes.
 *
 * It also checks for the mistakes that only show up on a real machine:
 *   - word/long access at an odd address (address error on a 68000)
 *   - writes to the vector table (0..$3ff)
 *   - chip DMA pointers (copper, bitplanes, sprites, audio) outside chip RAM
 *   - memory accesses outside RAM / custom / CIA
 *
 * usage: amiga <exe> <diskdir> <script> [outdir]
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include "m68k.h"

#define CHIPSIZE 0x80000
#define SLOWBASE 0xC00000
#define SLOWSIZE 0x100000

static uint8_t chip[CHIPSIZE];
static uint8_t slow[SLOWSIZE];
static uint16_t cregs[256];          /* custom register shadow (writes) */
static int errors = 0, warnlimit = 60;
static char outdir[512] = ".";
static char diskdir[512] = ".";

/* beam */
#define CYC_LINE 454
#define LINES 313
static long long totalcyc = 0;       /* cycles at start of current slice */
static int vpos = 0;
static long long frames = 0;
static long long linestart = 0;

static int dmacon = 0x03f0, intena = 0, intreq = 0, adkcon = 0;
/* Paula, for recording what the music player does */
typedef struct { int on; uint32_t ptr, left; double frac; int8_t cur; } Aud;
static Aud aud[4];
static FILE *wavf = NULL; static long wavn = 0;
static void aud_start(int c) {
	aud[c].on = 1; aud[c].ptr = (cregs[(0xa0 + c * 16) >> 1] << 16) | cregs[(0xa2 + c * 16) >> 1];
	aud[c].left = cregs[(0xa4 + c * 16) >> 1] * 2; if (!aud[c].left) aud[c].left = 131072; aud[c].frac = 0;
}
static void aud_frame(void) {
	if (!wavf) return;
	const int N = 441;   /* 22050 Hz */
	for (int i = 0; i < N; i++) {
		int mix = 0;
		for (int c = 0; c < 4; c++) {
			if (!aud[c].on || !(dmacon & 0x200) || !(dmacon & (1 << c))) continue;
			int per = cregs[(0xa6 + c * 16) >> 1]; if (per < 64) per = 64;
			double step = 3546895.0 / per / 22050.0;
			aud[c].frac += step;
			while (aud[c].frac >= 1.0) {
				aud[c].frac -= 1.0;
				aud[c].cur = (int8_t)(aud[c].ptr < CHIPSIZE ? chip[aud[c].ptr] : 0);
				aud[c].ptr++;
				if (--aud[c].left == 0) aud_start(c);
			}
			int vol = cregs[(0xa8 + c * 16) >> 1]; if (vol > 64) vol = 64;
			mix += aud[c].cur * vol;
		}
		int16_t v = mix * 2; fwrite(&v, 2, 1, wavf); wavn++;
	}
}
static uint32_t cop1lc = 0;

/* input */
static uint8_t mousex = 0, mousey = 0;
static int lmb = 0, rmb = 0, fire2 = 0;
static uint16_t joy1 = 0;
static uint8_t cia_icr = 0, cia_sdr = 0, cia_cra = 0;
static int keyq[256], keyqn = 0, keyqh = 0;
static int keywait = 0;

static const char *symname(uint32_t a, uint32_t *off);
static uint32_t rd32(uint32_t a);
static void err(const char *fmt, uint32_t a, uint32_t b) {
	errors++;
	if (warnlimit-- > 0) {
		uint32_t pc = m68k_get_reg(NULL, M68K_REG_PPC), off = 0;
		const char *n = symname(pc, &off);
		fprintf(stderr, "!! ");
		fprintf(stderr, fmt, a, b);
		fprintf(stderr, "  (pc=%06x %s+%u frame=%lld)\n", pc, n, off, frames);
		if (warnlimit > 55) {   /* first errors: a rough call stack */
			uint32_t sp = m68k_get_reg(NULL, M68K_REG_A7);
			fprintf(stderr, "     stack:");
			for (int i = 0; i < 48; i++) { uint32_t v = rd32(sp + i * 4); if (v >= 0xc00000 && v < 0xc80000) { uint32_t o; const char *nm = symname(v, &o); fprintf(stderr, " %s+%u", nm, o); } }
			fprintf(stderr, "\n     d0=%08x d1=%08x a0=%08x a1=%08x a2=%08x\n", m68k_get_reg(NULL,M68K_REG_D0), m68k_get_reg(NULL,M68K_REG_D1), m68k_get_reg(NULL,M68K_REG_A0), m68k_get_reg(NULL,M68K_REG_A1), m68k_get_reg(NULL,M68K_REG_A2));
		}
	}
}

/* ---------- symbols ---------- */
typedef struct { char name[64]; uint32_t addr; } Sym;
static Sym syms[20000]; static int nsyms = 0;
static uint32_t sym(const char *n0) {
	char n[128]; strncpy(n, n0, 127); n[127] = 0; int off = 0; char *p = strchr(n, '+'); if (p) { off = atoi(p + 1); *p = 0; }
	for (int i = 0; i < nsyms; i++) if (!strcmp(syms[i].name, n)) return syms[i].addr + off;
	if (n[0] >= '0' && n[0] <= '9') return (uint32_t)strtoul(n, 0, 0) + off;
	fprintf(stderr, "unknown symbol %s\n", n); exit(2);
}
static const char *symname(uint32_t a, uint32_t *off) {
	int best = -1; uint32_t bd = 0xffffffff;
	for (int i = 0; i < nsyms; i++) if (syms[i].addr <= a && a - syms[i].addr < bd) { bd = a - syms[i].addr; best = i; }
	if (best < 0) return "?";
	*off = bd; return syms[best].name;
}

/* ---------- fake OS ---------- */
#define EXECBASE 0x7F000
#define GFXBASE  0x7F400
#define DOSBASE  0x7F800
#define INTBASE  0x7FA00
#define PROCADDR 0x7FC00
#define EXITADDR 0x7FE00
#define SERVRET 0x7FE10   /* a vertical blank server returns here */
static uint32_t vb_code = 0, vb_data = 0; static int vb_in = 0; static uint32_t vb_regs[18];
#define GFXCOPINIT 0x7FE10
#define CIAARES  0x7FD80   /* ciaa.resource: AbleICR -18, SetICR -24 (Kickstart-friendly keyboard reading) */
static uint8_t ciares_acc = 0, ciares_mask = 0x0f;

static int osused = 0;
static FILE *fh[16];

static uint8_t *memptr(uint32_t a) {
	a &= 0xffffff;
	if (a < CHIPSIZE) return chip + a;
	if (a >= SLOWBASE && a < SLOWBASE + SLOWSIZE) return slow + (a - SLOWBASE);
	return NULL;
}
static uint32_t rd32(uint32_t a) { uint8_t *p = memptr(a); return p ? (p[0]<<24)|(p[1]<<16)|(p[2]<<8)|p[3] : 0; }
static uint16_t rd16(uint32_t a) { uint8_t *p = memptr(a); return p ? (p[0]<<8)|p[1] : 0; }
static void wr32(uint32_t a, uint32_t v) { uint8_t *p = memptr(a); if (p) { p[0]=v>>24; p[1]=v>>16; p[2]=v>>8; p[3]=v; } }
static void wr16(uint32_t a, uint16_t v) { uint8_t *p = memptr(a); if (p) { p[0]=v>>8; p[1]=v; } }

static void readstr(uint32_t a, char *buf, int n) {
	int i; for (i = 0; i < n - 1; i++) { uint8_t *p = memptr(a + i); if (!p || !*p) break; buf[i] = *p; } buf[i] = 0;
}

static int done = 0;
static int whd = 0; static uint32_t resbase = 0;
static int dos_writes = 0;
static long blits = 0;
static char conq[16][128]; static int conq_n = 0, conq_h = 0;
static long long delayframes = 0;

static void hostpath(const char *amiganame, char *out) {
	const char *n = amiganame;
	if (!strncasecmp(n, "PROGDIR:", 8)) n += 8;
	const char *c = strchr(n, ':'); if (c) n = c + 1;
	snprintf(out, 512, "%s/%s", diskdir, n);
}

static int os_call(uint32_t pc) {
	uint32_t d1 = m68k_get_reg(NULL, M68K_REG_D1), d2 = m68k_get_reg(NULL, M68K_REG_D2), d3 = m68k_get_reg(NULL, M68K_REG_D3);
	uint32_t a1 = m68k_get_reg(NULL, M68K_REG_A1);
	int lvo; uint32_t res = 0;
	if (pc >= EXECBASE - 1024 && pc < EXECBASE) {
		lvo = EXECBASE - pc;
		switch (lvo) {
		case 294: res = PROCADDR; break;                    /* FindTask */
		case 408: case 552: {                               /* OldOpenLibrary / OpenLibrary */
			char nm[64]; readstr(a1, nm, 64);
			if (!strcmp(nm, "graphics.library")) res = GFXBASE;
			else if (!strcmp(nm, "dos.library")) res = DOSBASE;
			else if (!strcmp(nm, "intuition.library")) res = INTBASE;
			else res = 0; break; }
		case 414: case 132: case 138: case 378: case 336: case 450: res = 0; break;
		case 384: case 372: res = 0; break;
		case 330: res = 12; break;                           /* AllocSignal */
		case 198: { uint32_t n = (m68k_get_reg(NULL, M68K_REG_D0) + 7) & ~7; uint32_t req = m68k_get_reg(NULL, M68K_REG_D1);
			extern uint32_t harness_alloc(uint32_t, int); res = harness_alloc(n, req & 2); break; }
		case 210: res = 0; break;                            /* FreeMem */
		case 498: { char nm[64]; readstr(a1, nm, 64); res = !strcmp(nm, "ciaa.resource") ? CIAARES : 0; break; } /* OpenResource */
		case 444: res = 0; break;                            /* OpenDevice ok */
		case 168: if (m68k_get_reg(NULL, M68K_REG_D0) == 5) { vb_code = rd32(a1 + 18); vb_data = rd32(a1 + 14); } res = 0; break;  /* AddIntServer (VERTB) */
		case 174: vb_code = 0; res = 0; break;               /* RemIntServer */
		case 456: res = 0; break;                            /* DoIO */
		default: err("exec LVO -%d not emulated%s", lvo, 0); break;
		}
	} else if (pc >= CIAARES - 64 && pc < CIAARES) {
		uint8_t m = m68k_get_reg(NULL, M68K_REG_D0) & 0xff;
		lvo = CIAARES - pc;
		ciares_acc |= cia_icr; cia_icr = 0;                  /* the resource reads the hardware ICR */
		if (lvo == 18) { res = ciares_mask; if (m & 0x80) ciares_mask |= m & 0x7f; else ciares_mask &= ~m; }   /* AbleICR */
		else if (lvo == 24) { res = ciares_acc; if (m & 0x80) ciares_acc |= m & 0x7f; else ciares_acc &= ~m; } /* SetICR */
		else err("ciaa.resource LVO -%d not emulated%s", lvo, 0);
	} else if (pc >= GFXBASE - 1024 && pc < GFXBASE) {
		lvo = GFXBASE - pc;
		if (lvo != 222 && lvo != 270 && lvo != 228 && lvo != 456 && lvo != 462) err("gfx LVO -%d not emulated%s", lvo, 0);
	} else if (pc >= INTBASE - 512 && pc < INTBASE) {
		lvo = INTBASE - pc;
	} else if (pc >= DOSBASE - 1024 && pc < DOSBASE) {
		lvo = DOSBASE - pc;
		if (lvo == 30 && ({ char cn[8]; readstr(d1, cn, 8); !strncasecmp(cn, "CON:", 4); })) {
			res = 0x200; fprintf(stderr, "   dos Open CON\n");
		} else if ((lvo == 48 || lvo == 42) && d1 == 0x200) {
			if (lvo == 48) { for (uint32_t k = 0; k < d3; k++) { uint8_t *p = memptr(d2 + k); if (p) fputc(*p, stdout); } fflush(stdout); res = d3; }
			else { const char *l = conq_n > conq_h ? conq[conq_h++] : ""; uint32_t n = 0; while (l[n] && n + 1 < d3) { *memptr(d2 + n) = l[n]; n++; } *memptr(d2 + n) = 10; res = n + 1; printf("%s\n", l); }
		} else if (lvo == 36 && d1 == 0x200) { res = 0;
		} else if (lvo == 84) { char nm[128], hp[512]; struct stat st; readstr(d1, nm, 128); hostpath(nm, hp);
			res = stat(hp, &st) == 0 ? 0x300 : 0; fprintf(stderr, "   dos Lock %s -> %s\n", nm, res ? "ok" : "fail");
		} else if (lvo == 90) { res = 0;
		} else if (lvo == 120) { char nm[128], hp[512]; readstr(d1, nm, 128); hostpath(nm, hp);
			res = mkdir(hp, 0755) == 0 ? 0x300 : 0; fprintf(stderr, "   dos CreateDir %s -> %s\n", nm, res ? "ok" : "fail");
		} else if (lvo == 30) {
			char nm[128], hp[512]; readstr(d1, nm, 128); hostpath(nm, hp);
			FILE *f = fopen(hp, d2 == 1006 ? "wb" : (d2 == 1004 ? "r+b" : "rb"));
			res = 0;
			if (f) for (int i = 1; i < 16; i++) if (!fh[i]) { fh[i] = f; res = i * 4 + 0x100; break; }
			fprintf(stderr, "   dos Open %s mode %d -> %s\n", nm, d2, res ? "ok" : "fail");
		} else if (lvo == 36) {
			int i = (d1 - 0x100) / 4; if (i > 0 && i < 16 && fh[i]) { fclose(fh[i]); fh[i] = 0; }
		} else if (lvo == 42 || lvo == 48) {
			int i = (d1 - 0x100) / 4; res = (uint32_t)-1;
			if (i > 0 && i < 16 && fh[i]) {
				long n = 0;
				for (uint32_t k = 0; k < d3; k++) {
					uint8_t *p = memptr(d2 + k); if (!p) { err("dos IO outside RAM %06x%s", d2 + k, 0); break; }
					if (lvo == 42) { int c = fgetc(fh[i]); if (c == EOF) break; *p = c; } else { fputc(*p, fh[i]); }
					n++;
				}
				res = n; if (lvo == 48) dos_writes++;
			}
		} else if (lvo == 198) { delayframes += d1; }
		else if (lvo == 150) { char nm[128], hp[512]; readstr(d1, nm, 128); hostpath(nm, hp);
			extern uint32_t harness_loadseg(const char *); res = harness_loadseg(hp);
			fprintf(stderr, "   dos LoadSeg %s -> %s\n", nm, res ? "ok" : "fail"); }
		else if (lvo == 156) { res = 0; }
		else err("dos LVO -%d not emulated%s", lvo, 0);
	} else if (pc == EXITADDR) {
		done = 1; m68k_end_timeslice(); return 1;
	} else return 0;
	m68k_set_reg(M68K_REG_D0, res);
	return 1;
}

static uint32_t poll_addr = 0; static long long poll_frame = -10;
static void resload_call(uint32_t off) {
	uint32_t d0 = m68k_get_reg(NULL, M68K_REG_D0), d1 = m68k_get_reg(NULL, M68K_REG_D1);
	uint32_t a0 = m68k_get_reg(NULL, M68K_REG_A0), a1 = m68k_get_reg(NULL, M68K_REG_A1);
	char nm[128], hp[512]; FILE *f; uint32_t res = 0;
	switch (off) {
	case 4: {   /* Abort: (sp) = reason after the rts popped the address */
		uint32_t sp = m68k_get_reg(NULL, M68K_REG_A7);
		fprintf(stderr, "   resload_Abort reason %d\n", (int)rd32(sp));
		done = 1; m68k_end_timeslice(); return; }
	case 32: break;                                       /* FlushCache */
	case 36: readstr(a0, nm, 128); hostpath(nm, hp);      /* GetFileSize */
		f = fopen(hp, "rb"); if (f) { fseek(f, 0, SEEK_END); res = ftell(f); fclose(f); }
		fprintf(stderr, "   resload_GetFileSize %s -> %u\n", nm, res); break;
	case 12: readstr(a0, nm, 128); hostpath(nm, hp);      /* SaveFile d0 size a1 addr */
		f = fopen(hp, "wb"); if (f) { for (uint32_t k = 0; k < d0; k++) { uint8_t *p = memptr(a1 + k); fputc(p ? *p : 0, f); } fclose(f); res = 1; }
		dos_writes++; fprintf(stderr, "   resload_SaveFile %s %u bytes\n", nm, d0); break;
	case 76: readstr(a0, nm, 128); hostpath(nm, hp);      /* LoadFileOffset d0 size d1 offset a1 dest */
		f = fopen(hp, "rb"); if (!f) { err("resload_LoadFileOffset: no %s%s", nm, 0); break; }
		fseek(f, d1, SEEK_SET);
		for (uint32_t k = 0; k < d0; k++) { int c = fgetc(f); if (c == EOF) break; uint8_t *p = memptr(a1 + k); if (!p) { err("resload load outside RAM %06x%s", a1 + k, 0); break; } *p = c; res++; }
		fclose(f); break;
	default: err("resload offset %d not emulated%s", off, 0);
	}
	m68k_set_reg(M68K_REG_D0, res);
}
/* a simple profiler: instructions executed per code address */
static int prof_on = 0;
static unsigned int prof[0x40000];
void hook(unsigned int pc) {
	if (prof_on && pc >= 0xc00000 && pc < 0xc80000) prof[(pc - 0xc00000) >> 1]++;
	if (pc == poll_addr) poll_frame = frames;
	if (whd) {
		if (pc >= resbase && pc < resbase + 256) resload_call(pc - resbase);
		return;
	}
	if (pc == SERVRET && vb_in) {          /* the server is done: back to where we were */
		for (int i = 0; i < 16; i++) m68k_set_reg(M68K_REG_D0 + i, vb_regs[i]);
		m68k_set_reg(M68K_REG_SR, vb_regs[17]);
		m68k_set_reg(M68K_REG_PC, vb_regs[16]);
		vb_in = 0;
		return;
	}
	if (pc >= 0x7E000 && pc < 0x80000) {
		if (!osused) osused = 1;
		os_call(pc);
	}
}
/* at the start of a frame: call the vertical blank server, as exec would */
static void vb_interrupt(void) {
	if (!vb_code || vb_in) return;
	for (int i = 0; i < 16; i++) vb_regs[i] = m68k_get_reg(NULL, M68K_REG_D0 + i);
	vb_regs[16] = m68k_get_reg(NULL, M68K_REG_PC);
	vb_regs[17] = m68k_get_reg(NULL, M68K_REG_SR);
	uint32_t sp = vb_regs[15] - 64;
	sp -= 4; wr32(sp, SERVRET);
	m68k_set_reg(M68K_REG_A7, sp);
	m68k_set_reg(M68K_REG_A1, vb_data);
	m68k_set_reg(M68K_REG_PC, vb_code);
	vb_in = 1;
}

/* ---------- custom chips ---------- */
static uint16_t beam_vhpos(void) {
	long long c = totalcyc + m68k_cycles_run() - linestart;
	int v = vpos, h = (int)(c / 2);
	while (h >= 227) { h -= 227; v = (v + 1) % LINES; }
	return ((v & 0xff) << 8) | h;
}
static uint16_t beam_vpos(void) {
	long long c = totalcyc + m68k_cycles_run() - linestart;
	int v = vpos; while (c >= CYC_LINE) { c -= CYC_LINE; v = (v + 1) % LINES; }
	return (v >> 8) & 1;
}

static void chipptr_check(int reg, uint32_t v) {
	(void)reg;
	if (v >= CHIPSIZE) err("DMA pointer register $%03x set outside chip RAM: %06x", reg, v);
}

static uint16_t custom_read(uint32_t off) {
	switch (off) {
	case 0x002: return dmacon & 0x07ff;
	case 0x004: return beam_vpos();
	case 0x006: return beam_vhpos();
	case 0x00a: return (mousey << 8) | mousex;
	case 0x00c: return joy1;
	case 0x010: return adkcon;
	case 0x016: return 0xff00 & ~(rmb ? 0x0400 : 0) & ~(fire2 ? 0x4000 : 0);
	case 0x01c: return intena;
	case 0x01e: return intreq;
	default: return 0;
	}
}
static void custom_write(uint32_t off, uint16_t v) {
	off &= 0x1fe;
	cregs[off >> 1] = v;
	switch (off) {
	case 0x096: { int old = dmacon; if (v & 0x8000) dmacon |= v & 0x7fff; else dmacon &= ~v;
		for (int c = 0; c < 4; c++) { if ((dmacon & (1 << c)) && !(old & (1 << c))) aud_start(c); if (!(dmacon & (1 << c))) aud[c].on = 0; } break; }
	case 0x09a: if (v & 0x8000) intena |= v & 0x7fff; else intena &= ~v; break;
	case 0x09c: if (v & 0x8000) intreq |= v & 0x7fff; else intreq &= ~v; break;
	case 0x09e: if (v & 0x8000) adkcon |= v & 0x7fff; else adkcon &= ~v; break;
	case 0x080: cop1lc = (cop1lc & 0xffff) | (v << 16); break;
	case 0x082: cop1lc = (cop1lc & 0xffff0000) | v; chipptr_check(0x80, cop1lc); break;
	case 0x058: {   /* blitter: D-only fill (minterm 00 / ff) and A->D copy (09f0) */
		int h = v >> 6, w = v & 63; if (!h) h = 1024; if (!w) w = 64;
		uint16_t c0 = cregs[0x40 >> 1], c1 = cregs[0x42 >> 1];
		uint32_t dp = ((cregs[0x54 >> 1] << 16) | cregs[0x56 >> 1]) & 0xfffffe, ap = ((cregs[0x50 >> 1] << 16) | cregs[0x52 >> 1]) & 0xfffffe;
		int dmod = (int16_t)cregs[0x66 >> 1], amod = (int16_t)cregs[0x64 >> 1];
		if (c1 != 0) { err("blitter BLTCON1 %04x not emulated%s", c1, 0); break; }
		if ((c0 & 0x0f00) == 0x0100 && ((c0 & 0xff) == 0 || (c0 & 0xff) == 0xff)) {
			uint16_t fv = (c0 & 0xff) ? 0xffff : 0;
			for (int y = 0; y < h; y++) { for (int x = 0; x < w; x++) { if (dp >= CHIPSIZE) { err("blit outside chip %06x%s", dp, 0); return; } wr16(dp, fv); dp += 2; } dp += dmod; }
		} else if (c0 == 0x09f0) {
			for (int y = 0; y < h; y++) { for (int x = 0; x < w; x++) { if (dp >= CHIPSIZE || ap >= CHIPSIZE) { err("blit outside chip %06x%s", dp, 0); return; } wr16(dp, rd16(ap)); dp += 2; ap += 2; } dp += dmod; ap += amod; }
		} else err("blitter mode BLTCON0=%04x not emulated%s", c0, 0);
		blits++;
		break; }
	}
	/* audio location low words */
	if (off == 0x0a2 || off == 0x0b2 || off == 0x0c2 || off == 0x0d2) {
		uint32_t a = (cregs[(off - 2) >> 1] << 16) | v;
		if (a >= CHIPSIZE) err("audio pointer reg $%03x outside chip RAM: %06x", off - 2, a);
	}
}

/* ---------- CIA ---------- */
static uint8_t cia_read(uint32_t a) {
	if (a == 0xbfe001) {
		uint8_t v = 0xff;
		if (lmb) v &= ~0x40;
		if (fire2) v &= ~0x80;
		return v;
	}
	if (a == 0xbfed01) { uint8_t r = cia_icr; cia_icr = 0; return r; }
	if (a == 0xbfec01) return cia_sdr;
	if (a == 0xbfee01) return cia_cra;
	if (a == 0xbfe801) return (uint8_t)frames;   /* TOD: counts the vertical syncs */
	return 0xff;
}
static void cia_write(uint32_t a, uint8_t v) {
	if (a == 0xbfee01) cia_cra = v;
}

/* ---------- memory callbacks ---------- */
static int inrange_ok(uint32_t a) {
	return memptr(a) != NULL;
}
static void check_vec_write(uint32_t a) {
	if (a < 0x400 && !(whd && a >= 4 && a < 8)) err("write to vector table at %06x%s", a, 0);
}
unsigned int m68k_read_memory_8(unsigned int a) {
	a &= 0xffffff;
	uint8_t *p = memptr(a); if (p) return *p;
	if ((a & 0xfff000) == 0xbfe000 || (a & 0xfff000) == 0xbfd000) return cia_read(a);
	if ((a & 0xfff000) == 0xdff000) { uint16_t w = custom_read(a & 0x1fe); return (a & 1) ? (w & 0xff) : (w >> 8); }
	if (a >= 0xf80000) return 0;
	err("byte read outside RAM %06x%s", a, 0); return 0;
}
unsigned int m68k_read_memory_16(unsigned int a) {
	a &= 0xffffff;
	if (a & 1) err("word read at odd address %06x (address error)%s", a, 0);
	uint8_t *p = memptr(a); if (p) return (p[0] << 8) | p[1];
	if ((a & 0xfff000) == 0xdff000) return custom_read(a & 0x1fe);
	if (a >= 0xf80000) return 0;
	err("word read outside RAM %06x%s", a, 0); return 0;
}
unsigned int m68k_read_memory_32(unsigned int a) {
	a &= 0xffffff;
	if (a & 1) err("long read at odd address %06x (address error)%s", a, 0);
	if ((a & 0xfff000) == 0xdff000) return (custom_read(a & 0x1fe) << 16) | custom_read((a + 2) & 0x1fe);
	uint8_t *p = memptr(a); if (p && inrange_ok(a + 3)) return (p[0]<<24)|(p[1]<<16)|(p[2]<<8)|p[3];
	err("long read outside RAM %06x%s", a, 0); return 0;
}
unsigned int m68k_read_disassembler_16(unsigned int a) { return rd16(a); }
unsigned int m68k_read_disassembler_32(unsigned int a) { return rd32(a); }
static uint32_t watch_ad[8]; static char watch_nm[8][32]; static int nwatch;
void m68k_write_memory_8(unsigned int a, unsigned int v) {
	if (nwatch) { extern void watch_byte(unsigned int, unsigned int); watch_byte(a & 0xffffff, v); }
	a &= 0xffffff;
	uint8_t *p = memptr(a); if (p) { check_vec_write(a); *p = v; return; }
	if ((a & 0xfff000) == 0xbfe000 || (a & 0xfff000) == 0xbfd000) { cia_write(a, v); return; }
	if ((a & 0xfff000) == 0xdff000) { err("byte write to custom %06x%s", a, 0); return; }
	err("byte write outside RAM %06x%s", a, 0);
}
static void watch_hit(unsigned int a, unsigned int v);
void m68k_write_memory_16(unsigned int a, unsigned int v) {
	a &= 0xffffff;
	if (nwatch) watch_hit(a, v);
	if (a & 1) err("word write at odd address %06x (address error)%s", a, 0);
	uint8_t *p = memptr(a); if (p) { check_vec_write(a); p[0] = v >> 8; p[1] = v; return; }
	if ((a & 0xfff000) == 0xdff000) { custom_write(a & 0x1fe, v); return; }
	err("word write outside RAM %06x%s", a, 0);
}
void m68k_write_memory_32(unsigned int a, unsigned int v);
void m68k_write_memory_32(unsigned int a, unsigned int v) {
	a &= 0xffffff;
	if (nwatch) { watch_hit(a, v >> 16); watch_hit(a + 2, v & 0xffff); }
	if (a & 1) err("long write at odd address %06x (address error)%s", a, 0);
	if ((a & 0xfff000) == 0xdff000) { custom_write(a & 0x1fe, v >> 16); custom_write((a + 2) & 0x1fe, v & 0xffff); return; }
	uint8_t *p = memptr(a); if (p) { check_vec_write(a); p[0]=v>>24; p[1]=v>>16; p[2]=v>>8; p[3]=v; return; }
	err("long write outside RAM %06x%s", a, 0);
}
int illg(int op) { err("illegal instruction %04x%s", op, 0); done = 2; m68k_end_timeslice(); return 0; }

/* ---------- hunk loader ---------- */
static uint32_t hunkbase[64], hunksize[64]; static int nhunks;
static uint32_t chipalloc = 0x10000, slowalloc = SLOWBASE + 0x8000;
static uint32_t chipused = 0, otherused = 0;

static uint32_t be32(FILE *f) { uint8_t b[4]; if (fread(b, 1, 4, f) != 4) return 0xffffffff; return (b[0]<<24)|(b[1]<<16)|(b[2]<<8)|b[3]; }

static int load_exe(const char *fn) {
	FILE *f = fopen(fn, "rb"); if (!f) { perror(fn); return 0; }
	if (be32(f) != 0x3f3) { fprintf(stderr, "not a hunk exe\n"); exit(1); }
	while (be32(f)) ;     /* resident library names (none) */
	uint32_t tab = be32(f), first = be32(f), last = be32(f); (void)tab;
	nhunks = last - first + 1;
	for (int i = 0; i < nhunks; i++) {
		uint32_t s = be32(f); uint32_t bytes = (s & 0x3fffffff) * 4;
		int ischip = (s >> 30) == 1;
		uint32_t need = bytes + 8;
		if (ischip) { hunkbase[i] = chipalloc; chipalloc += (need + 7) & ~7; chipused += need; }
		else {
			if (slowalloc + need > SLOWBASE + SLOWSIZE) { hunkbase[i] = chipalloc; chipalloc += (need + 7) & ~7; chipused += need; fprintf(stderr, "   hunk %d (%u bytes) did not fit in slow RAM -> chip\n", i, bytes); }
			else { hunkbase[i] = slowalloc; slowalloc += (need + 7) & ~7; otherused += need; }
		}
		hunksize[i] = bytes;
		fprintf(stderr, "   hunk %2d %s %7u bytes at %06x\n", i, ischip ? "CHIP" : "any ", bytes, hunkbase[i]);
	}
	if (chipalloc > EXECBASE - 0x2000) { fprintf(stderr, "!! chip RAM overflow\n"); errors++; }
	int h = -1;
	for (;;) {
		uint32_t t = be32(f); if (t == 0xffffffff) break;
		t &= 0x3fffffff;
		if (t == 0x3e9 || t == 0x3ea) {
			uint32_t n = be32(f) * 4; h++;
			if (fread(memptr(hunkbase[h]), 1, n, f) != n) { fprintf(stderr, "short read\n"); exit(1); }
		} else if (t == 0x3eb) { be32(f); h++; }
		else if (t == 0x3ec) {
			for (;;) { uint32_t n = be32(f); if (!n) break; uint32_t th = be32(f);
				for (uint32_t k = 0; k < n; k++) { uint32_t o = be32(f); wr32(hunkbase[h] + o, rd32(hunkbase[h] + o) + hunkbase[th]); } }
		} else if (t == 0x3f0) {
			for (;;) { uint32_t n = be32(f); if (!n) break; char nm[256] = {0};
				if (fread(nm, 1, n * 4, f) != n * 4) break; uint32_t v = be32(f);
				if (nsyms < 20000) { strncpy(syms[nsyms].name, nm, 63); syms[nsyms].addr = hunkbase[h] + v; nsyms++; } }
		} else if (t == 0x3f1) { uint32_t n = be32(f); fseek(f, n * 4, SEEK_CUR); }
		else if (t == 0x3f2) { }
		else { fprintf(stderr, "unknown hunk %x\n", t); exit(1); }
	}
	fclose(f);
	fprintf(stderr, "   memory: chip %u bytes, other %u bytes\n", chipused, otherused);
	return 1;
}
static void find_syms(void);
uint32_t harness_loadseg(const char *fn) {
	if (!load_exe(fn)) return 0;
	find_syms();
	return (hunkbase[0] - 4) >> 2;
}
uint32_t harness_alloc(uint32_t n, int chipreq) {
	uint32_t a;
	if (!chipreq && slowalloc + n < SLOWBASE + SLOWSIZE) { a = slowalloc; slowalloc += n; otherused += n; }
	else { a = chipalloc; chipalloc += n; chipused += n; }
	for (uint32_t i = 0; i < n; i++) { uint8_t *p = memptr(a + i); if (p) *p = 0; }
	fprintf(stderr, "   AllocMem %u %s -> %06x\n", n, chipreq ? "chip" : "any", a);
	return a;
}

static void setup_os(void) {
	wr32(4, EXECBASE);
	for (uint32_t a = EXECBASE - 1024; a < EXECBASE; a += 2) wr16(a, 0x4e75);
	for (uint32_t a = GFXBASE - 1024; a < GFXBASE; a += 2) wr16(a, 0x4e75);
	for (uint32_t a = DOSBASE - 1024; a < DOSBASE; a += 2) wr16(a, 0x4e75);
	for (uint32_t a = INTBASE - 512; a < INTBASE; a += 2) wr16(a, 0x4e75);
	for (uint32_t a = CIAARES - 64; a < CIAARES; a += 2) wr16(a, 0x4e75);
	wr16(EXITADDR, 0x4e75);
	wr16(SERVRET, 0x4e71);
	wr16(DOSBASE + 20, 34);       /* lib_Version 34 = 1.3 */
	wr16(EXECBASE + 20, 34);
	wr32(GFXBASE + 38, GFXCOPINIT);
	wr32(GFXCOPINIT, 0xfffffffe);
	wr32(PROCADDR + 172, 0x1234);  /* pr_CLI: started from the CLI (startup-sequence) */
}

/* ---------- display renderer ---------- */
static uint32_t frame_rgb[256][320];

static void render(void) {
	uint16_t r[256]; memcpy(r, cregs, sizeof r);
	uint32_t bplpt[6]; for (int i = 0; i < 6; i++) bplpt[i] = (r[(0xe0 >> 1) + i * 2] << 16) | r[(0xe2 >> 1) + i * 2];
	uint32_t pc = cop1lc;
	int copwait = 0, wv = 0, wh = 0, wvm = 0, whm = 0, copdone = 0;
	/* sprite state */
	uint32_t sprpt[8]; int sprvs[8], sprve[8], sprhs[8], sprst[8]; uint16_t sprda[8], sprdb[8], sprctl[8];
	for (int s = 0; s < 8; s++) { sprpt[s] = 0; sprst[s] = 0; sprvs[s] = sprve[s] = -1; sprctl[s] = 0; }
	for (int v = 0; v < 313; v++) {
		/* copper up to the end of this line */
		while (!copdone) {
			if (copwait) {
				int cv = v & wvm, cw = wv & wvm;
				if (cv > cw || (cv == cw && (226 & whm) >= (wh & whm))) {
					copwait = 0;
					if (cv == cw && (wh & whm) >= 0xd8) break;   /* the rest runs on the next line */
				} else break;
			}
			if (pc >= CHIPSIZE) { copdone = 1; break; }
			uint16_t i1 = rd16(pc), i2 = rd16(pc + 2); pc += 4;
			if (!(i1 & 1)) {
				int reg = i1 & 0x1fe;
				if (reg < 0x40 && !(r[0x2e >> 1] & 2)) { copdone = 1; break; }
				r[reg >> 1] = i2;
				if (reg >= 0xe0 && reg < 0xf8) { int p = (reg - 0xe0) / 4; if (reg & 2) bplpt[p] = (bplpt[p] & 0xffff0000) | i2; else bplpt[p] = (bplpt[p] & 0xffff) | (i2 << 16); if (reg & 2) chipptr_check(reg - 2, bplpt[p]); }
				if (reg >= 0x120 && reg < 0x140) { int s = (reg - 0x120) / 4; if (reg & 2) { sprpt[s] = (sprpt[s] & 0xffff0000) | i2; chipptr_check(reg - 2, sprpt[s]); sprst[s] = 1; } else sprpt[s] = (sprpt[s] & 0xffff) | (i2 << 16); }
			} else {
				if (i1 == 0xffff && i2 == 0xfffe) { copdone = 1; break; }
				wv = i1 >> 8; wh = i1 & 0xfe; wvm = ((i2 >> 8) & 0x7f) | 0x80; whm = i2 & 0xfe;
				if (i2 & 1) { /* skip */
					int cv = v & wvm, cw = wv & wvm;
					if (cv > cw || (cv == cw && 0 >= (wh & whm))) pc += 4;
				} else copwait = 1;
			}
		}
		/* sprites: fetch control words */
		for (int s = 0; s < 8; s++) {
			if (sprst[s] == 1 && sprpt[s]) {
				uint16_t pos = rd16(sprpt[s]), ctl = rd16(sprpt[s] + 2);
				sprvs[s] = (pos >> 8) | ((ctl & 4) << 6); sprve[s] = (ctl >> 8) | ((ctl & 2) << 7);
				sprhs[s] = ((pos & 0xff) << 1) | (ctl & 1); sprctl[s] = ctl;
				sprpt[s] += 4; sprst[s] = 2;
				if (pos == 0 && ctl == 0) sprst[s] = 3;
			}
			if (sprst[s] == 2 && v >= sprvs[s] && v < sprve[s]) { sprda[s] = rd16(sprpt[s]); sprdb[s] = rd16(sprpt[s] + 2); sprpt[s] += 4; if (v + 1 == sprve[s]) sprst[s] = 1; }
			else if (sprst[s] == 2 && v >= sprve[s]) sprst[s] = 1;
		}
		int y = v - 0x2c;
		int nplanes = (r[0x100 >> 1] >> 12) & 7;
		if (y >= 0 && y < 256) {
			int ddfs = r[0x92 >> 1] & 0xfc; int early = (0x38 - ddfs) / 8 * 16; if (early < 0) early = 0;
			int dl1 = r[0x102 >> 1] & 15, dl2 = (r[0x102 >> 1] >> 4) & 15;
			int dual = r[0x100 >> 1] & 0x400, pf2pri = r[0x104 >> 1] & 0x40;
			for (int x = 0; x < 320; x++) {
				int col = 0;
				if (dmacon & 0x100) for (int p = 0; p < nplanes; p++) {
					int bx = x + early - ((p & 1) ? dl2 : dl1);
					if (bx < 0) continue;
					uint32_t a = bplpt[p] + (bx >> 3);
					if (a < CHIPSIZE && (chip[a] & (0x80 >> (bx & 7)))) col |= 1 << p;
				}
				if (dual) {
					int v1 = (col & 1) | ((col >> 1) & 2) | ((col >> 2) & 4);
					int v2 = ((col >> 1) & 1) | ((col >> 2) & 2) | ((col >> 3) & 4);
					if (pf2pri) col = v2 ? 8 + v2 : v1; else col = v1 ? v1 : (v2 ? 8 + v2 : 0);
				}
				/* sprites: pairs, the lower number in front; odd sprite attached = 15 colours */
				if (dmacon & 0x20) for (int pr = 3; pr >= 0; pr--) {
					int bb[2] = {0, 0};
					for (int k = 0; k < 2; k++) {
						int s = pr * 2 + k;
						if (v >= sprvs[s] && v < sprve[s] && sprst[s] != 3) {
							int dx = (x + 0x80) - sprhs[s];
							if (dx >= 0 && dx < 16) bb[k] = ((sprda[s] >> (15 - dx)) & 1) | (((sprdb[s] >> (15 - dx)) & 1) << 1);
						}
					}
					if (sprctl[pr * 2 + 1] & 0x80) { int val = bb[0] | (bb[1] << 2); if (val) col = 16 + val; }
					else if (bb[0]) col = 16 + pr * 4 + bb[0];
					else if (bb[1]) col = 16 + pr * 4 + bb[1];
				}
				uint16_t c = r[(0x180 >> 1) + col];
				frame_rgb[y][x] = ((c >> 8 & 15) * 17 << 16) | ((c >> 4 & 15) * 17 << 8) | ((c & 15) * 17);
			}
			int mod = (int16_t)r[0x108 >> 1], mod2 = (int16_t)r[0x10a >> 1];
			int fetch = (((r[0x094 >> 1] & 0xfc) - (r[0x092 >> 1] & 0xfc)) / 8 + 1) * 2;
			if (fetch <= 0 || fetch > 60) fetch = 40;
			if (dmacon & 0x100) for (int p = 0; p < nplanes; p++) bplpt[p] += fetch + ((p & 1) ? mod2 : mod);
		}
	}
}

static void shot(const char *name) {
	render();
	char fn[700]; snprintf(fn, sizeof fn, "%s/%s", outdir, name);
	FILE *f = fopen(fn, "wb"); fprintf(f, "P6\n320 256\n255\n");
	for (int y = 0; y < 256; y++) for (int x = 0; x < 320; x++) { uint32_t c = frame_rgb[y][x]; fputc(c >> 16, f); fputc(c >> 8, f); fputc(c, f); }
	fclose(f);
	fprintf(stderr, "   shot %s\n", name);
}

/* ---------- running ---------- */
static int target_mx = -1, target_my = -1;
static uint32_t sym_mx = 0, sym_my = 0, sym_fc = 0;
static long long max_line_cycles = 0;

static void run_frame(void) {
	vb_interrupt();
	for (int l = 0; l < LINES && !done; l++) {
		linestart = totalcyc;
		int c = m68k_execute(CYC_LINE);
		totalcyc += c;
		vpos = (vpos + 1) % LINES;
		/* keep in step: leftover cycles go to the next line */
		linestart = totalcyc;
	}
	frames++;
	aud_frame();
	/* input per frame */
	if (keywait > 0) keywait--;
	if (keyqh < keyqn && keywait == 0 && !((cia_icr | ciares_acc) & 8)) {
		int k = keyq[keyqh++];
		uint8_t x = (uint8_t)k; uint8_t rolx = (x << 1) | (x >> 7);
		cia_sdr = ~rolx; cia_icr |= 8; keywait = 3;
	}
	if (target_mx >= 0 && sym_mx) {
		int cx = (int16_t)rd16(sym_mx), cy = (int16_t)rd16(sym_my);
		int dx = target_mx - cx, dy = target_my - cy;
		if (dx > 20) dx = 20; if (dx < -20) dx = -20; if (dy > 20) dy = 20; if (dy < -20) dy = -20;
		mousex += dx; mousey += dy;
		if (!dx && !dy) target_mx = -1;
	}
}

static void find_syms(void) {
	for (int i = 0; i < nsyms; i++) { if (!strcmp(syms[i].name, "MouseX")) sym_mx = syms[i].addr; if (!strcmp(syms[i].name, "MouseY")) sym_my = syms[i].addr; if (!strcmp(syms[i].name, "FrameCount")) sym_fc = syms[i].addr; if (!strcmp(syms[i].name, "PollInput")) poll_addr = syms[i].addr; }
}
static void watch_hit(unsigned int a, unsigned int v) {
	for (int i = 0; i < nwatch; i++) if (a == watch_ad[i]) {
		int old = (int16_t)rd16(a);
		if (old == (int16_t)v) return;
		uint32_t off; uint32_t pc = m68k_get_reg(NULL, M68K_REG_PPC); const char *n = symname(pc, &off);
		printf("W f=%lld %s %d->%d at %s+%u\n", frames, watch_nm[i], old, (int16_t)v, n, off);
	}
}
void watch_byte(unsigned int a, unsigned int v) {
	for (int i = 0; i < nwatch; i++) if ((a & ~1u) == watch_ad[i]) {
		uint8_t *p = memptr(a); if (p && *p == (uint8_t)v) return;
		uint32_t off; uint32_t pc = m68k_get_reg(NULL, M68K_REG_PPC); const char *n = symname(pc, &off);
		printf("B f=%lld %s byte %06x <- %02x at %s+%u  d0-d7 %x %x %x %x %x %x %x %x a0 %x a1 %x sp %x\n", frames, watch_nm[i], a, v & 0xff, n, off,
			m68k_get_reg(NULL,M68K_REG_D0),m68k_get_reg(NULL,M68K_REG_D1),m68k_get_reg(NULL,M68K_REG_D2),m68k_get_reg(NULL,M68K_REG_D3),
			m68k_get_reg(NULL,M68K_REG_D4),m68k_get_reg(NULL,M68K_REG_D5),m68k_get_reg(NULL,M68K_REG_D6),m68k_get_reg(NULL,M68K_REG_D7),
			m68k_get_reg(NULL,M68K_REG_A0),m68k_get_reg(NULL,M68K_REG_A1),m68k_get_reg(NULL,M68K_REG_A7));
		{ uint32_t sp = m68k_get_reg(NULL,M68K_REG_A7); for (int k = 0; k < 40; k++) { uint32_t w = rd32(sp + k * 2); uint32_t o2; if (w >= 0xc00000 && w < 0xc80000) { printf("   stack+%d -> %s+%u\n", k*2, symname(w,&o2), o2); } } }
	}
}
static void runframes(int n) { for (int i = 0; i < n && !done; i++) run_frame(); }

static int keycode(const char *s) {
	struct { const char *n; int c; } t[] = {
		{"ESC",0x45},{"SPACE",0x40},{"RETURN",0x44},{"BACK",0x41},{"DEL",0x46},{"UP",0x4c},{"DOWN",0x4d},{"RIGHT",0x4e},{"LEFT",0x4f},
		{"F1",0x50},{"F2",0x51},{"F3",0x52},{"F4",0x53},{"F5",0x54},{"F6",0x55},{"F7",0x56},{"F8",0x57},{"F9",0x58},{"F10",0x59},{"HELP",0x5f},{"TAB",0x42},{0,0}};
	for (int i = 0; t[i].n; i++) if (!strcasecmp(s, t[i].n)) return t[i].c;
	const char *row1 = "1234567890", *rq = "QWERTYUIOP", *ra = "ASDFGHJKL", *rz = "ZXCVBNM";
	char c = s[0]; if (c >= 'a' && c <= 'z') c -= 32;
	const char *p;
	if ((p = strchr(row1, c))) return 1 + (p - row1);
	if ((p = strchr(rq, c))) return 0x10 + (p - rq);
	if ((p = strchr(ra, c))) return 0x20 + (p - ra);
	if ((p = strchr(rz, c))) return 0x31 + (p - rz);
	return -1;
}
static void pushkey(int k) { if (keyqh == keyqn) keyqh = keyqn = 0; if (keyqn < 250) { keyq[keyqn++] = k; keyq[keyqn++] = k | 0x80; } }

int main(int argc, char **argv) {
	if (argc < 4) { fprintf(stderr, "usage: amiga exe diskdir script [outdir]\n"); return 1; }
	strcpy(diskdir, argv[2]); if (argc > 4) strcpy(outdir, argv[4]);
	m68k_init(); m68k_set_cpu_type(M68K_CPU_TYPE_68000);
	whd = strstr(argv[1], ".slave") != NULL;
	if (whd) {
		/* WHDLoad: the slave gets the resident loader in a0, runs in
		   supervisor mode, and has chip memory 0..BaseMemSize */
		load_exe(argv[1]);
		uint32_t base = hunkbase[0];
		if (rd32(base + 4) != 0x5748444c) { fprintf(stderr, "not a WHDLoad slave\n"); return 1; }
		uint32_t expsize = rd32(base + 32);
		uint32_t exp = harness_alloc(expsize, 0);
		wr32(base + 32, exp);
		resbase = harness_alloc(256, 0);
		for (int i = 0; i < 256; i += 2) wr16(resbase + i, 0x4e75);
		uint16_t gl = rd16(base + 24);
		fprintf(stderr, "   WHDLoad slave v%d, base mem %x, exp mem %x at %06x, loader +%x\n", rd16(base + 12), rd32(base + 16), expsize, exp, gl);
		m68k_init(); m68k_set_cpu_type(M68K_CPU_TYPE_68000);
		m68k_pulse_reset();
		m68k_set_reg(M68K_REG_PC, base + gl);
		m68k_set_reg(M68K_REG_SR, 0x2700);
		m68k_set_reg(M68K_REG_A7, SLOWBASE + SLOWSIZE - 16);
		m68k_set_reg(M68K_REG_A0, resbase);
		goto script;
	}
	load_exe(argv[1]);
	setup_os();
	uint32_t sp = SLOWBASE + SLOWSIZE - 16;
	/* stack: in real life it's the CLI stack; return address -> EXITADDR */
	sp -= 4; wr32(sp, EXITADDR);
	wr32(0, sp); wr32(4, EXECBASE);
	m68k_pulse_reset();
	m68k_set_reg(M68K_REG_SP, sp); m68k_set_reg(M68K_REG_A7, sp);
	m68k_set_reg(M68K_REG_PC, hunkbase[0]);
	m68k_set_reg(M68K_REG_SR, 0x0000);   /* user mode like a real program */
	m68k_set_reg(M68K_REG_USP, sp);
	m68k_set_reg(M68K_REG_A6, EXECBASE);
	wr32(0, 0); wr32(4, EXECBASE);
	find_syms();
script:;
	FILE *sc = fopen(argv[3], "r"); if (!sc) { perror(argv[3]); return 1; }
	char line[512];
	while (fgets(line, sizeof line, sc) && !done) {
		char cmd[64] = "", a[256] = "", b[64] = "", c[64] = "", d[64] = "";
		if (sscanf(line, "%63s %255s %63s %63s %63s", cmd, a, b, c, d) < 1 || cmd[0] == '#') continue;
		if (!strcmp(cmd, "run")) runframes(atoi(a));
		else if (!strcmp(cmd, "settle")) {
			long long start = frames; int quiet = 0;
			while (!done && frames - start < 3000) { long long pf = poll_frame; run_frame(); if (poll_frame > pf && poll_frame == frames - 1) quiet++; else quiet = 0; if (quiet >= 3) break; }
		}
		else if (!strcmp(cmd, "mouse")) { target_mx = atoi(a); target_my = atoi(b); for (int i = 0; i < 40 && target_mx >= 0; i++) run_frame(); runframes(2); }
		else if (!strcmp(cmd, "click")) { lmb = 1; runframes(3); lmb = 0; runframes(atoi(a) > 0 ? atoi(a) : 4); }
		else if (!strcmp(cmd, "clickat")) { target_mx = atoi(a); target_my = atoi(b); for (int i = 0; i < 40 && target_mx >= 0; i++) run_frame(); runframes(2); lmb = 1; runframes(3); lmb = 0; runframes(c[0] ? atoi(c) : 6); }
		else if (!strcmp(cmd, "tap")) { target_mx = atoi(a); target_my = atoi(b); for (int i = 0; i < 40 && target_mx >= 0; i++) run_frame(); runframes(2); lmb = 1; runframes(3); lmb = 0; runframes(2);
			long long start = frames; int quiet = 0;
			while (!done && frames - start < 3000) { long long pf = poll_frame; run_frame(); if (poll_frame > pf && poll_frame == frames - 1) quiet++; else quiet = 0; if (quiet >= 3) break; }
			fprintf(stderr, "   tap %s,%s settled after %lld frames\n", a, b, frames - start); }
		else if (!strcmp(cmd, "mdelta")) { int dx = atoi(a), dy = atoi(b); for (int k = 0; k < 8; k++) { mousex += dx / 8; mousey += dy / 8; run_frame(); } }
		else if (!strcmp(cmd, "lhold")) { lmb = 1; runframes(atoi(a)); lmb = 0; runframes(2); }
		else if (!strcmp(cmd, "conline")) { if (conq_n < 16) { snprintf(conq[conq_n++], 128, "%s", a); } }
		else if (!strcmp(cmd, "down")) { int k = keycode(a); if (keyqh == keyqn) keyqh = keyqn = 0; keyq[keyqn++] = k; runframes(4); }
		else if (!strcmp(cmd, "up")) { int k = keycode(a); if (keyqh == keyqn) keyqh = keyqn = 0; keyq[keyqn++] = k | 0x80; runframes(4); }
		else if (!strcmp(cmd, "rclick")) { rmb = 1; runframes(3); rmb = 0; runframes(4); }
		else if (!strcmp(cmd, "key")) { int k = keycode(a); if (k < 0) { fprintf(stderr, "bad key %s\n", a); } else { pushkey(k); runframes(10);
			long long start = frames; int quiet = 0;
			while (!done && frames - start < 3000) { long long pf = poll_frame; run_frame(); if (poll_frame > pf && poll_frame == frames - 1) quiet++; else quiet = 0; if (quiet >= 3) break; } } }
		else if (!strcmp(cmd, "press")) { int k = keycode(a); if (k >= 0) { pushkey(k); runframes(2); } }
		else if (!strcmp(cmd, "type")) { for (char *p = a; *p; p++) { int k = (*p == '_') ? 0x40 : keycode((char[]){*p, 0}); if (k >= 0) pushkey(k); } runframes(8 * strlen(a) + 10); }
		else if (!strcmp(cmd, "shot")) shot(a);
		else if (!strcmp(cmd, "peek")) {
			uint32_t ad = sym(a); int v = !strcmp(b, "l") ? (int)rd32(ad) : !strcmp(b, "b") ? *memptr(ad) : (int16_t)rd16(ad);
			printf("%s = %d\n", a, v); fflush(stdout);
		}
		else if (!strcmp(cmd, "poke")) {
			uint32_t ad = sym(a); long v = strtol(c, 0, 0);
			if (!strcmp(b, "l")) wr32(ad, v); else if (!strcmp(b, "b")) *memptr(ad) = v; else wr16(ad, v);
		}
		else if (!strcmp(cmd, "expect")) {
			uint32_t ad = sym(a); int v = !strcmp(b, "l") ? (int)rd32(ad) : !strcmp(b, "b") ? *memptr(ad) : (int16_t)rd16(ad);
			long want = strtol(c, 0, 0);
			if (v != want) { fprintf(stderr, "!! expect %s = %ld, got %d (frame %lld)\n", a, want, v, frames); errors++; }
			else printf("ok %s = %d\n", a, v);
		}
		else if (!strcmp(cmd, "until")) {   /* until SYMBOL size value maxframes */
			uint32_t ad = sym(a); long want = strtol(c, 0, 0); int mx = atoi(d); int i;
			for (i = 0; i < mx && !done; i++) { int v = !strcmp(b, "l") ? (int)rd32(ad) : !strcmp(b, "b") ? *memptr(ad) : (int16_t)rd16(ad); if (v == want) break; run_frame(); }
			if (i >= mx) { fprintf(stderr, "!! until %s == %ld timed out\n", a, want); errors++; }
		}
		else if (!strcmp(cmd, "audio")) {
			char fn[700]; snprintf(fn, sizeof fn, "%s/%s", outdir, a); wavf = fopen(fn, "wb");
			uint8_t h[44] = {0}; fwrite(h, 1, 44, wavf); wavn = 0;
		}
		else if (!strcmp(cmd, "audioend")) {
			uint32_t bytes = wavn * 2; fseek(wavf, 0, SEEK_SET);
			fwrite("RIFF", 1, 4, wavf); uint32_t x = bytes + 36; fwrite(&x, 4, 1, wavf); fwrite("WAVEfmt ", 1, 8, wavf);
			x = 16; fwrite(&x, 4, 1, wavf); uint16_t w = 1; fwrite(&w, 2, 1, wavf); w = 1; fwrite(&w, 2, 1, wavf);
			x = 22050; fwrite(&x, 4, 1, wavf); x = 44100; fwrite(&x, 4, 1, wavf); w = 2; fwrite(&w, 2, 1, wavf); w = 16; fwrite(&w, 2, 1, wavf);
			fwrite("data", 1, 4, wavf); fwrite(&bytes, 4, 1, wavf); fclose(wavf); wavf = NULL;
		}
		else if (!strcmp(cmd, "echo")) { printf("%s", line + 5); fflush(stdout); }
		else if (!strcmp(cmd, "fire")) { fire2 = 1; runframes(atoi(a)); fire2 = 0; }
		else if (!strcmp(cmd, "joy")) {      /* joy left|right|up|down|none frames [fire] */
			joy1 = !strcmp(a, "right") ? 0x0003 : !strcmp(a, "left") ? 0x0300 : !strcmp(a, "up") ? 0x0100 :
			       !strcmp(a, "down") ? 0x0001 : 0;
			if (c[0] == 'f') fire2 = 1;
			runframes(atoi(b)); joy1 = 0; fire2 = 0;
		}
		else if (!strcmp(cmd, "hold")) {     /* hold KEY frames */
			int k = keycode(a); if (keyqh == keyqn) keyqh = keyqn = 0; keyq[keyqn++] = k; runframes(atoi(b)); keyq[keyqn++] = k | 0x80; runframes(6);
		}
		else if (!strcmp(cmd, "dumpw")) {   /* dumpw SYMBOL count: signed words */
			uint32_t ad = sym(a); int n = atoi(b);
			for (int i = 0; i < n; i++) printf("%d%c", (int16_t)rd16(ad + i * 2), (i % 16 == 15) ? '\n' : ' ');
			printf("\n");
		}
		else if (!strcmp(cmd, "profon")) { prof_on = 1; memset(prof, 0, sizeof prof); }
		else if (!strcmp(cmd, "profoff")) prof_on = 0;
		else if (!strcmp(cmd, "profdump")) {
			/* per symbol (ignoring local labels: symname gives the nearest one) */
			static char names[4000][64]; static double cnt[4000]; int nn = 0; double tot = 0;
			for (int i = 0; i < 0x40000; i++) if (prof[i]) {
				uint32_t off; const char *n = symname(0xc00000 + i * 2, &off); int k;
				for (k = 0; k < nn; k++) if (!strcmp(names[k], n)) break;
				if (k == nn && nn < 4000) { strncpy(names[nn], n, 63); cnt[nn] = 0; nn++; }
				if (k < 4000) cnt[k] += prof[i]; tot += prof[i];
			}
			for (int r = 0; r < 25 && r < nn; r++) { int b = 0; for (int k = 1; k < nn; k++) if (cnt[k] > cnt[b]) b = k;
				printf("%6.2f%%  %s\n", cnt[b] * 100 / tot, names[b]); cnt[b] = -1; }
		}
		else if (!strcmp(cmd, "watch")) { if (nwatch < 8) { watch_ad[nwatch] = sym(a) & 0xffffff; snprintf(watch_nm[nwatch], 32, "%s", a); nwatch++; } }
		else if (!strcmp(cmd, "where")) { uint32_t off; uint32_t pc = m68k_get_reg(NULL, M68K_REG_PC); const char *n = symname(pc, &off); printf("pc=%06x %s+%u\n", pc, n, off); }
		else fprintf(stderr, "unknown command %s\n", cmd);
	}
	if (sym_fc) printf("frames run %lld, game frames %u\n", frames, rd32(sym_fc));
	if (done == 1) printf("program exited normally\n");
	if (done == 2) { uint32_t off; uint32_t pc = m68k_get_reg(NULL, M68K_REG_PPC); printf("CRASH at %06x %s+%u\n", pc, symname(pc, &off), off); }
	printf("errors: %d, dos writes: %d\n", errors, dos_writes);
	return errors ? 3 : 0;
}
