/* Serial transport for the Consult dongle: raw 9600 8N1, read timeouts, and a
 * timestamped log of every TX/RX byte. Linux only (termios). C port of
 * consult/transport.py; the log format is the same. */
#ifndef SERIAL_H
#define SERIAL_H

#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

typedef struct {
    int fd;
    int error;          /* errno of a failed read/write, e.g. EIO when the dongle drops off USB */
    FILE *log;
    double t0;
} serial_t;

double mono(void);
void sleep_s(double secs);

/* Returns 0, or -errno if the port can't be opened or configured. */
int serial_open(serial_t *s, const char *dev, const char *log_path);
void serial_close(serial_t *s);

/* Free-text line in the log. */
void serial_note(serial_t *s, const char *fmt, ...) __attribute__((format(printf, 2, 3)));

void serial_write(serial_t *s, const uint8_t *buf, size_t n);

/* Read up to n bytes, giving up `timeout` seconds after the last byte arrived. */
size_t serial_read(serial_t *s, uint8_t *buf, size_t n, double timeout);

/* Read and discard everything until the line has been silent for `quiet` seconds. */
size_t serial_drain(serial_t *s, double quiet, double limit);

#endif
