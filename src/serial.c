#define _GNU_SOURCE
#include "serial.h"

#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/select.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>

double mono(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec / 1e9;
}

void sleep_s(double secs)
{
    struct timespec ts = {(time_t)secs, (long)((secs - (time_t)secs) * 1e9)};
    while (nanosleep(&ts, &ts) < 0 && errno == EINTR)
        ;
}

static void log_line(serial_t *s, const char *tag, const char *text)
{
    if (!s->log)
        return;
    fprintf(s->log, "%10.6f %s %s\n", mono() - s->t0, tag, text);
    fflush(s->log);
}

static void log_hex(serial_t *s, const char *tag, const uint8_t *buf, size_t n)
{
    char text[3 * 256 + 1];
    size_t o = 0;
    for (size_t i = 0; i < n && i < 256; i++)
        o += sprintf(text + o, i ? " %02x" : "%02x", buf[i]);
    text[o] = '\0';
    log_line(s, tag, text);
}

void serial_note(serial_t *s, const char *fmt, ...)
{
    char text[512];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(text, sizeof text, fmt, ap);
    va_end(ap);
    log_line(s, "##", text);
}

int serial_open(serial_t *s, const char *dev, const char *log_path)
{
    struct termios t;
    int lines = TIOCM_DTR | TIOCM_RTS;
    char when[32];
    time_t now = time(NULL);

    memset(s, 0, sizeof *s);
    s->fd = open(dev, O_RDWR | O_NOCTTY | O_NONBLOCK);
    if (s->fd < 0)
        return -errno;

    /* Raw mode, 9600 8N1, no flow control (CONSULT_PROTOCOL.md §2).
     * No HUPCL, so closing the port doesn't toggle DTR either. */
    if (tcgetattr(s->fd, &t) < 0)
        goto fail;
    t.c_iflag = 0;
    t.c_oflag = 0;
    t.c_lflag = 0;
    t.c_cflag = CS8 | CREAD | CLOCAL;
    t.c_cc[VMIN] = 0;
    t.c_cc[VTIME] = 0;
    cfsetispeed(&t, B9600);
    cfsetospeed(&t, B9600);
    if (tcsetattr(s->fd, TCSANOW, &t) < 0)
        goto fail;

    /* Linux raises DTR and RTS on open; drop them to match Windows (.NET SerialPort /
     * ECUTalk), which is the setup verified on the car. */
    if (ioctl(s->fd, TIOCMBIC, &lines) < 0)
        goto fail;
    tcflush(s->fd, TCIOFLUSH);

    s->t0 = mono();
    s->log = log_path ? fopen(log_path, "a") : NULL;
    strftime(when, sizeof when, "%Y-%m-%dT%H:%M:%S", localtime(&now));
    serial_note(s, "open %s at %s", dev, when);
    return 0;

fail:;
    int err = errno;
    close(s->fd);
    s->fd = -1;
    return -err;
}

void serial_close(serial_t *s)
{
    if (s->fd < 0)
        return;
    serial_note(s, "close");
    close(s->fd);
    s->fd = -1;
    if (s->log)
        fclose(s->log);
    s->log = NULL;
}

static int wait_fd(int fd, int for_write, double timeout)
{
    fd_set set;
    struct timeval tv = {(time_t)timeout, (suseconds_t)((timeout - (time_t)timeout) * 1e6)};
    FD_ZERO(&set);
    FD_SET(fd, &set);
    return select(fd + 1, for_write ? NULL : &set, for_write ? &set : NULL, NULL, &tv);
}

void serial_write(serial_t *s, const uint8_t *buf, size_t n)
{
    log_hex(s, "TX", buf, n);
    while (n > 0) {
        ssize_t m = write(s->fd, buf, n);
        if (m < 0) {
            if (errno == EINTR)
                continue;
            if (errno == EAGAIN && wait_fd(s->fd, 1, 1.0) > 0)
                continue;
            s->error = errno;
            serial_note(s, "write failed: %s", strerror(errno));
            return;
        }
        buf += m;
        n -= (size_t)m;
    }
    tcdrain(s->fd);
}

size_t serial_read(serial_t *s, uint8_t *buf, size_t n, double timeout)
{
    size_t got = 0;
    while (got < n) {
        int k = wait_fd(s->fd, 0, timeout);
        if (k < 0 && errno == EINTR)
            continue;
        if (k <= 0)
            break;
        ssize_t m = read(s->fd, buf + got, n - got);
        if (m < 0 && (errno == EAGAIN || errno == EINTR))
            continue;
        if (m <= 0) {
            /* Readable but no data: the device has gone away. */
            s->error = m < 0 ? errno : EIO;
            serial_note(s, "read failed: %s", strerror(s->error));
            break;
        }
        log_hex(s, "RX", buf + got, (size_t)m);
        got += (size_t)m;
    }
    return got;
}

size_t serial_drain(serial_t *s, double quiet, double limit)
{
    uint8_t buf[256];
    size_t total = 0, n;
    double end = mono() + limit;
    while (mono() < end && (n = serial_read(s, buf, sizeof buf, quiet)) > 0)
        total += n;
    return total;
}
