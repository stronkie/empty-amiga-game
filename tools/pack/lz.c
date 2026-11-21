/* lz.c - the Stronkie Soft packer (byte-flag LZSS, 64 KB window).
 *
 * Stream: a flag byte gives 8 tokens, top bit first. 0 = one literal byte.
 * 1 = a match: byte b.
 *   b < $80: length (b>>4)+3 (3..10), offset ((b&15)<<8 | next byte)+1 (1..4096)
 *   b >= $80: length (b&$7f)+3 (3..130), offset (next word, big endian)+1 (1..65536)
 * Unpacking stops when the output is full.
 *
 * usage: lz in out      -> prints "packed_size margin" (margin = bytes the
 *                          packed data must sit above the output for an in-place unpack)
 *        lz -d in out size
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define WIN 65536
#define HBITS 16
#define MAXCH 4096

static unsigned char *in, *out;
static long n, op;
static int *head, *prev;

static unsigned hsh(long i) { return ((in[i] << 16 | in[i + 1] << 8 | in[i + 2]) * 2654435761u) >> (32 - HBITS); }

static void ins(long i) {
	if (i + 2 >= n) return;
	unsigned h = hsh(i);
	prev[i & (WIN - 1)] = head[h];
	head[h] = (int)i;
}

static int best(long i, long *boff) {
	if (i + 2 >= n) return 0;
	int bl = 0, ch = MAXCH;
	long maxl = n - i < 130 ? n - i : 130;
	int p = head[hsh(i)];
	while (p >= 0 && i - p <= WIN && ch--) {
		if (in[p + bl] == in[i + bl] && in[p] == in[i]) {
			int l = 0;
			while (l < maxl && in[p + l] == in[i + l]) l++;
			long off = i - p;
			/* a short token (2 bytes) only reaches 4096 back and 10 long */
			int cost_ok = !(l == 3 && off > 4096);
			if (cost_ok && l > bl) { bl = l; *boff = off; if (l == maxl) break; }
		}
		int q = prev[p & (WIN - 1)];
		if (q >= p) break;
		p = q;
	}
	return bl >= 3 ? bl : 0;
}

/* token cost in bits (incl. its flag bit) */
static int cost(int l, long off) {
	if (!l) return 9;
	return (l <= 10 && off <= 4096) ? 17 : 25;
}

int main(int argc, char **argv) {
	if (argc >= 5 && !strcmp(argv[1], "-d")) {
		FILE *f = fopen(argv[2], "rb"); fseek(f, 0, 2); long pn = ftell(f); rewind(f);
		unsigned char *p = malloc(pn + 8); fread(p, 1, pn, f); fclose(f);
		long un = atol(argv[4]); unsigned char *u = malloc(un + 200);
		long ip = 0, o = 0; int fl = 0, fb = 0;
		while (o < un) {
			if (!fb) { fl = p[ip++]; fb = 8; }
			int bit = fl & 0x80; fl <<= 1; fb--;
			if (!bit) { u[o++] = p[ip++]; continue; }
			int b = p[ip++]; long len, off;
			if (b < 0x80) { len = (b >> 4) + 3; off = (((b & 15) << 8) | p[ip++]) + 1; }
			else { len = (b & 0x7f) + 3; off = ((p[ip] << 8) | p[ip + 1]) + 1; ip += 2; }
			while (len--) { u[o] = u[o - off]; o++; }
		}
		f = fopen(argv[3], "wb"); fwrite(u, 1, un, f); fclose(f);
		return 0;
	}
	FILE *f = fopen(argv[1], "rb"); fseek(f, 0, 2); n = ftell(f); rewind(f);
	in = malloc(n + 300); memset(in, 0, n + 300); fread(in, 1, n, f); fclose(f);
	out = malloc(n * 2 + 100);
	head = malloc(sizeof(int) << HBITS); memset(head, 0xff, sizeof(int) << HBITS);
	prev = malloc(sizeof(int) * WIN);
	long i = 0, flagpos = -1; int fbits = 8;
	long margin = 0;
	op = 0;
	while (i < n) {
		long off = 0, off2 = 0;
		int l = best(i, &off);
		if (l && l < 130) { /* lazy: a better match one byte later? */
			ins(i);
			int l2 = best(i + 1, &off2);
			if (l2 > l + 1 || (l2 > l && cost(l2, off2) <= cost(l, off))) l = 0; /* emit a literal now */
		} else ins(i);
		if (fbits == 8) { flagpos = op++; out[flagpos] = 0; fbits = 0; }
		if (!l) {
			out[op++] = in[i]; fbits++; i++;
		} else {
			out[flagpos] |= 0x80 >> fbits; fbits++;
			if (l <= 10 && off <= 4096) {
				out[op++] = ((l - 3) << 4) | ((off - 1) >> 8);
				out[op++] = (off - 1) & 0xff;
			} else {
				out[op++] = 0x80 | (l - 3);
				out[op++] = (off - 1) >> 8;
				out[op++] = (off - 1) & 0xff;
			}
			for (long k = 1; k < l; k++) ins(i + k);
			i += l;
		}
		/* in-place: output written so far (i) must stay below unread input (op) */
		if (i - op > margin) margin = i - op;
	}
	f = fopen(argv[2], "wb"); fwrite(out, 1, op, f); fclose(f);
	printf("%ld %ld\n", op, margin);
	return 0;
}
