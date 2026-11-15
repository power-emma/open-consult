/* Build-time tool: pack <dir> onto <launcher.exe>, writing <out.exe>.
 *   pack launcher.exe dist/consult-gui-windows dist/consult-gui.exe */
#include <dirent.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <zlib.h>

#include "onefile.h"

static FILE *out;
static uint64_t hash = ONEFILE_FNV_INIT;
static uint32_t count;

static void put(const void *p, size_t n)
{
    if (fwrite(p, 1, n, out) != n) {
        perror("write");
        exit(1);
    }
    hash = onefile_fnv(hash, p, n);
}

static unsigned char *slurp(const char *path, size_t *n)
{
    FILE *f = fopen(path, "rb");
    unsigned char *buf;
    long len;
    if (!f || fseek(f, 0, SEEK_END) || (len = ftell(f)) < 0 || fseek(f, 0, SEEK_SET)) {
        perror(path);
        exit(1);
    }
    buf = malloc((size_t)len + 1);
    if (!buf || fread(buf, 1, (size_t)len, f) != (size_t)len) {
        perror(path);
        exit(1);
    }
    fclose(f);
    *n = (size_t)len;
    return buf;
}

static void add_file(const char *full, const char *rel)
{
    size_t n;
    unsigned char *raw = slurp(full, &n);
    uLongf zn = compressBound((uLong)n);
    unsigned char *z = malloc(zn);
    uint16_t plen = (uint16_t)strlen(rel);
    uint32_t sizes[2];

    if (!z || compress2(z, &zn, raw, (uLong)n, 9) != Z_OK) {
        fprintf(stderr, "compress failed: %s\n", full);
        exit(1);
    }
    sizes[0] = (uint32_t)n;
    sizes[1] = (uint32_t)zn;
    put(&plen, sizeof plen);
    put(rel, plen);
    put(sizes, sizeof sizes);
    put(z, zn);
    count++;
    free(raw);
    free(z);
}

static void add_dir(const char *root, const char *rel)
{
    char path[1024], sub[1024];
    DIR *d;
    struct dirent *e;

    snprintf(path, sizeof path, "%s%s%s", root, *rel ? "/" : "", rel);
    if (!(d = opendir(path))) {
        perror(path);
        exit(1);
    }
    while ((e = readdir(d))) {
        struct stat st;
        char full[2048];
        if (!strcmp(e->d_name, ".") || !strcmp(e->d_name, ".."))
            continue;
        snprintf(sub, sizeof sub, "%s%s%s", rel, *rel ? "/" : "", e->d_name);
        snprintf(full, sizeof full, "%s/%s", root, sub);
        if (stat(full, &st)) {
            perror(full);
            exit(1);
        }
        if (S_ISDIR(st.st_mode))
            add_dir(root, sub);
        else
            add_file(full, sub);
    }
    closedir(d);
}

int main(int argc, char **argv)
{
    size_t n;
    unsigned char *stub;
    onefile_footer_t f = {0};

    if (argc != 4) {
        fprintf(stderr, "usage: %s launcher.exe dir out.exe\n", argv[0]);
        return 2;
    }
    stub = slurp(argv[1], &n);
    if (!(out = fopen(argv[3], "wb"))) {
        perror(argv[3]);
        return 1;
    }
    fwrite(stub, 1, n, out);
    f.payload_offset = n;
    add_dir(argv[2], "");
    f.hash = hash;
    f.count = count;
    memcpy(f.magic, ONEFILE_MAGIC, sizeof f.magic);
    fwrite(&f, sizeof f, 1, out);
    if (fclose(out)) {
        perror(argv[3]);
        return 1;
    }
    printf("packed %u files into %s\n", count, argv[3]);
    return 0;
}
