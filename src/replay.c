#include "replay.h"
#include <math.h>
#include <stdio.h>
#include <string.h>

GArray *replay_load(const char *path, GError **error)
{
    gchar *text;
    if (!g_file_get_contents(path, &text, NULL, error)) return NULL;
    GArray *frames = g_array_new(FALSE, FALSE, sizeof(replay_frame_t));
    guint8 request[512], regs[256], data[256];
    int nq = 0, nr = 0, state = 0, length = 0, got = 0, engine = 0;
    gboolean overflow = FALSE;
    double last = 0, offset = 0, origin = -1;
    char *line = text;
    while (line && *line) {
        char *next = strchr(line, '\n');
        if (next) *next++ = 0;
        double t;
        char tag[3];
        int consumed = 0;
        if (sscanf(line, " %lf %2s %n", &t, tag, &consumed) != 2 || !isfinite(t) || t < 0) {
            line = next; continue;
        }
        if (t < last) {
            offset += last;
            nq = nr = state = engine = 0;
            overflow = FALSE;
        }
        last = t;
        t += offset;
        char *p = line + consumed;
        if (!strcmp(tag, "##")) {
            if (g_str_has_prefix(p, "open ")) {
                nq = nr = state = engine = 0;
                overflow = FALSE;
            }
            char *id = strstr(p, "init ok id=");
            if (id) {
                engine = g_ascii_strncasecmp(id + 11, "ED", 2) == 0;
                nq = nr = state = 0;
                overflow = FALSE;
            }
        } else if (!strcmp(tag, "TX") || !strcmp(tag, "RX")) {
            while (*p) {
                while (g_ascii_isspace(*p)) p++;
                if (!*p) break;
                char *end;
                guint64 byte = g_ascii_strtoull(p, &end, 16);
                if (end == p || byte > 255 || (*end && !g_ascii_isspace(*end))) break;
                p = end;
                if (!strcmp(tag, "TX")) {
                    /* A command interrupts the previous stream, including partial frames. */
                    nr = state = 0;
                    if (byte == 0x30) { nq = 0; overflow = FALSE; }
                    else if (byte == 0xf0) {
                        if (engine && !overflow && nq > 0 && nq % 2 == 0) {
                            for (int i = 0; i < nq; i += 2) {
                                if (request[i] != 0x5a) { nr = 0; break; }
                                regs[nr++] = request[i + 1];
                            }
                        }
                        nq = 0; overflow = FALSE;
                    } else if (nq < (int)sizeof request) request[nq++] = byte;
                    else overflow = TRUE;
                } else if (nr) {
                    if (state == 0) { if (byte == 0xff) state = 1; }
                    else if (state == 1) {
                        length = byte; got = 0;
                        state = length ? 2 : 0;
                    } else {
                        data[got++] = byte;
                        if (got == length) {
                            state = 0;
                            if (length != nr) continue;
                            replay_frame_t f;
                            if (origin < 0) origin = t;
                            f.time = t - origin;
                            for (int i = 0; i < N_SENSORS; i++) {
                                unsigned raw = 0;
                                gboolean found = TRUE;
                                for (int j = 0; j < SENSORS[i].nregs; j++) {
                                    int k;
                                    for (k = 0; k < nr; k++) if (regs[k] == SENSORS[i].regs[j]) break;
                                    if (k == nr) { found = FALSE; break; }
                                    raw = (raw << 8) | data[k];
                                }
                                f.values[i] = found ? raw * SENSORS[i].scale + SENSORS[i].offset : NAN;
                            }
                            g_array_append_val(frames, f);
                        }
                    }
                }
            }
        }
        line = next;
    }
    g_free(text);
    if (!frames->len) {
        g_array_unref(frames);
        g_set_error_literal(error, G_FILE_ERROR, G_FILE_ERROR_FAILED,
                            "No complete engine sensor frames found in this log.");
        return NULL;
    }
    return frames;
}
