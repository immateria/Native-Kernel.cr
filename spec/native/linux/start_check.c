/* Original MIT startup-only oracle. NOT proof of Crystal's unmanaged boundary.
 * Linked with start-*.S using -nostdlib; never linked with the default CRT. */
typedef unsigned long u64;
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
        if (equal(env[i],"NK_ELF_PROOF=stack-arguments")) return 0;
    return 124;
}
