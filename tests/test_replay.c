/* Standalone GLib test: compile with replay.c and registers.c. */
#include "replay.h"
#include <glib/gstdio.h>
#include <math.h>
#include <unistd.h>

int main(void)
{
    char *path = NULL;
    int fd = g_file_open_tmp("consult-replay-XXXXXX", &path, NULL);
    g_assert_cmpint(fd, >=, 0);
    close(fd);
    /* Chunked RX, FF as data, reordered registers, interrupted frames, BCM,
     * and an appended session whose timestamps restart at zero. */
    const char *log =
        "0.0 ## open test\n0.1 ## init ok id=ED attempt=1\n"
        "0.2 TX 5a 08 5a 00 5a 01 f0\n"
        "0.3 RX a5 08 a5 00 a5 01 ff 03 64\n0.4 RX 00 34\n"
        "0.5 RX ff 03 ff 00 50\n"
        "0.6 RX ff 03 00\n0.7 TX 30\n0.8 RX 00 00\n"
        "0.9 ## init ok id=DA attempt=1\n1.0 TX 5a 08 f0\n1.1 RX ff 01 80\n"
        "0.0 ## open test\n0.1 ## init ok id=ED attempt=1\n"
        "0.2 TX 5a 08 f0\n0.3 RX ff 01 70\n0.4 RX ff 01\n";
    g_assert_true(g_file_set_contents(path, log, -1, NULL));
    GError *error = NULL;
    GArray *frames = replay_load(path, &error);
    g_assert_no_error(error);
    g_assert_nonnull(frames);
    g_assert_cmpuint(frames->len, ==, 3);
    replay_frame_t *f = &g_array_index(frames, replay_frame_t, 0);
    g_assert_cmpfloat(f->time, ==, 0);
    g_assert_cmpfloat(f->values[0], ==, 650);
    g_assert_cmpfloat(f->values[1], ==, 50);
    g_assert_true(isnan(f->values[2]));
    f = &g_array_index(frames, replay_frame_t, 1);
    g_assert_cmpfloat(f->values[1], ==, 205);
    f = &g_array_index(frames, replay_frame_t, 2);
    g_assert_cmpfloat(f->time, >, 0.1);
    g_assert_cmpfloat(f->values[1], ==, 62);
    g_assert_true(isnan(f->values[0]));
    g_array_unref(frames);
    g_assert_true(g_file_set_contents(path, "0.0 RX ff 01 00\n", -1, NULL));
    g_assert_null(replay_load(path, &error));
    g_assert_nonnull(error);
    g_clear_error(&error);
    g_unlink(path);
    g_free(path);
    return 0;
}
