/* Test-only serial seam. Link real consult.c, never serial.c or GTK. */
#include "consult.h"
#include <string.h>

typedef void (*write_cb)(const uint8_t *, size_t);
typedef size_t (*read_cb)(uint8_t *, size_t, double);
typedef double (*clock_cb)(void);
typedef void (*sleep_cb)(double);
static write_cb writer;
static read_cb reader;
static clock_cb clock_now;
static sleep_cb sleeper;
static serial_t port;
static consult_t client;

void bridge_bind(write_cb w, read_cb r, clock_cb t, sleep_cb s)
{
    writer = w; reader = r; clock_now = t; sleeper = s;
    memset(&port, 0, sizeof port);
    memset(&client, 0, sizeof client);
    client.s = &port;
}
double mono(void) { return clock_now(); }
void sleep_s(double seconds) { sleeper(seconds); }
void serial_write(serial_t *s, const uint8_t *data, size_t n)
{ (void)s; writer(data, n); }
size_t serial_read(serial_t *s, uint8_t *out, size_t n, double timeout)
{ (void)s; return reader(out, n, timeout); }
void serial_note(serial_t *s, const char *fmt, ...)
{ (void)s; (void)fmt; }
size_t serial_drain(serial_t *s, double quiet, double limit)
{
    uint8_t buf[256];
    size_t total = 0, n;
    double end = mono() + limit;
    while (mono() < end) {
        n = serial_read(s, buf, sizeof buf, quiet);
        total += n;
        if (!n) break;
    }
    return total;
}
int bridge_memory(const uint16_t *addresses, int n, uint8_t *out)
{ return consult_read_memory(&client, addresses, n, out); }
int bridge_frame(int expected, double timeout, uint8_t *out)
{ return consult_read_frame(&client, expected, timeout, out); }
int bridge_command(const uint8_t *data, size_t n, int retries)
{ return consult_command(&client, data, n, retries); }
int bridge_stop(double timeout, uint8_t *ack)
{ return consult_stop(&client, timeout, ack); }
