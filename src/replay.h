#ifndef REPLAY_H
#define REPLAY_H
#include <glib.h>
#include "registers.h"
typedef struct { double time, values[N_SENSORS]; } replay_frame_t;
/* Parse raw timestamped TX/RX logs; returns complete engine sensor frames. */
GArray *replay_load(const char *path, GError **error);
#endif
