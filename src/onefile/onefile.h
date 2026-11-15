/* Single-file Windows build: launcher.exe with the dist folder appended.
 *
 *   [launcher.exe][entry]...[entry][footer]
 *   entry:  u16 path length, path (UTF-8, '/' separators), u32 size, u32 packed size,
 *           zlib data
 *   footer: see onefile_footer_t, the last bytes of the file
 *
 * On start the launcher unpacks the entries to %LOCALAPPDATA%\open-consult\gui-<hash>
 * (once per build) and runs consult-gui.exe from there. */
#ifndef ONEFILE_H
#define ONEFILE_H

#include <stdint.h>

#define ONEFILE_MAGIC "OCPACK01"
#define ONEFILE_MAIN_W L"consult-gui.exe"

typedef struct {
    uint64_t payload_offset;    /* where the first entry starts */
    uint64_t hash;              /* FNV-1a of the payload: names the unpack folder */
    uint32_t count;             /* number of entries */
    char magic[8];
} onefile_footer_t;

static inline uint64_t onefile_fnv(uint64_t h, const void *p, size_t n)
{
    const unsigned char *b = p;
    for (size_t i = 0; i < n; i++)
        h = (h ^ b[i]) * 0x100000001b3ull;
    return h;
}

#define ONEFILE_FNV_INIT 0xcbf29ce484222325ull

#endif
