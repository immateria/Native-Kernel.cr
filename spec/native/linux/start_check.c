/* Original MIT startup-only oracle. NOT proof of Crystal's unmanaged boundary.
 * Linked with start-*.S using -nostdlib; never linked with the default CRT. */
typedef unsigned long u64;
extern void *memset(void *destination, int value, unsigned long size);

static int check_memset(void) {
    unsigned char bytes[19];
    void *(*volatile fill)(void *, int, unsigned long) = memset;
    for (unsigned i = 0; i < sizeof(bytes); ++i) bytes[i] = 0x5a;
    if (fill(bytes + 2, 0x1ab, sizeof(bytes) - 4) != bytes + 2) return 125;
    for (unsigned i = 0; i < sizeof(bytes); ++i) {
        unsigned char expected = i >= 2 && i < sizeof(bytes) - 2 ? 0xab : 0x5a;
        if (bytes[i] != expected) return 126;
    }
    if (fill(bytes, 0, 0) != bytes) return 127;
    return 0;
}

static int equal(const char *a, const char *b) {
    unsigned i = 0;
    while (i < 1024) { if (a[i] != b[i]) return 0; if (!a[i]) return 1; ++i; }
    return 0;
}
int main(int argc, char **argv, u64 *stack, u64 call_stack) {
    if (argc != 4 || *stack != 4 || (u64)argv != (u64)stack + 8) return 121;
    if (((u64)stack & 15) || (call_stack & 15) || argv[argc]) return 122;
    if (!equal(argv[1],"startup") || !equal(argv[2],"ELF-argument")) return 123;
    char **env = argv + argc + 1;
    for (unsigned i=0; i<256 && env[i]; ++i)
        if (equal(env[i],"NK_ELF_PROOF=stack-arguments")) return check_memset();
    return 124;
}
