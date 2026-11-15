#ifndef _WIN32
#define _GNU_SOURCE
#endif
#include "serial.h"

#include <errno.h>
#include <stdarg.h>
#include <string.h>
#include <time.h>

#ifdef _WIN32
#include <windows.h>
#include <timeapi.h>
#else
#include <fcntl.h>
#include <sys/ioctl.h>
#include <sys/select.h>
#include <termios.h>
#include <unistd.h>
#endif

/* ---- shared: logging ---- */

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

/* Binary mode, so the log has LF line ends on Windows too (same bytes as on Linux). */
static FILE *open_log(const char *path)
{
    if (!path)
        return NULL;
#ifdef _WIN32
    /* The path is UTF-8 (it comes from GLib); fopen would read it as the ANSI code page. */
    wchar_t wpath[MAX_PATH * 2];
    if (MultiByteToWideChar(CP_UTF8, 0, path, -1, wpath, (int)(sizeof wpath / sizeof *wpath)))
        return _wfopen(wpath, L"ab");
#endif
    return fopen(path, "ab");
}

static void log_opened(serial_t *s, const char *dev, const char *log_path)
{
    char when[32];
    time_t now = time(NULL);
    s->t0 = mono();
    s->log = open_log(log_path);
    strftime(when, sizeof when, "%Y-%m-%dT%H:%M:%S", localtime(&now));
    serial_note(s, "open %s at %s", dev, when);
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

#ifdef _WIN32

/* ---- Windows: Win32 comm API ---- */

double mono(void)
{
    static LARGE_INTEGER freq;
    LARGE_INTEGER now;
    if (!freq.QuadPart)
        QueryPerformanceFrequency(&freq);
    QueryPerformanceCounter(&now);
    return (double)now.QuadPart / (double)freq.QuadPart;
}

/* serial_open raises the system timer to 1 ms (timeBeginPeriod), so Sleep() is good
 * to about a millisecond while the port is open: enough for the 280/70 ms init gaps. */
void sleep_s(double secs)
{
    if (secs > 0)
        Sleep((DWORD)(secs * 1000 + 0.5));
}

static const char *win_error(DWORD code)
{
    static __thread char text[256];
    DWORD n = FormatMessageA(FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_IGNORE_INSERTS, NULL,
                             code, 0, text, sizeof text, NULL);
    while (n > 0 && (text[n - 1] == '\r' || text[n - 1] == '\n' || text[n - 1] == ' '))
        text[--n] = '\0';
    if (n == 0)
        snprintf(text, sizeof text, "Windows error %lu", (unsigned long)code);
    return text;
}

static int errno_from(DWORD code)
{
    switch (code) {
    case ERROR_FILE_NOT_FOUND:
    case ERROR_PATH_NOT_FOUND:
        return ENOENT;
    case ERROR_ACCESS_DENIED:       /* what Windows says when another program has the port */
    case ERROR_SHARING_VIOLATION:
        return EACCES;
    default:
        return EIO;
    }
}

/* Give ReadFile select()-like behaviour: return as soon as any byte is there, or after
 * `timeout` with nothing. (ReadIntervalTimeout and ReadTotalTimeoutMultiplier both
 * MAXDWORD, constant > 0: documented in the COMMTIMEOUTS remarks.) */
static int set_read_timeout(serial_t *s, double timeout)
{
    unsigned ms = timeout > 0 ? (unsigned)(timeout * 1000 + 0.5) : 0;
    COMMTIMEOUTS t = {0};

    if (timeout > 0 && ms == 0)
        ms = 1;
    if (ms == s->rto_ms)
        return 1;
    t.ReadIntervalTimeout = MAXDWORD;
    t.ReadTotalTimeoutMultiplier = ms ? MAXDWORD : 0;
    t.ReadTotalTimeoutConstant = ms;
    t.WriteTotalTimeoutConstant = 1000;
    if (!SetCommTimeouts(s->h, &t))
        return 0;
    s->rto_ms = ms;
    return 1;
}

int serial_open(serial_t *s, const char *dev, const char *log_path)
{
    char path[64];
    DCB dcb = {0};
    DWORD err;

    memset(s, 0, sizeof *s);
    /* COM10 and up only open as \\.\COM10; the prefix works for COM1-9 too. */
    if (strncmp(dev, "\\\\", 2) == 0)
        snprintf(path, sizeof path, "%s", dev);
    else
        snprintf(path, sizeof path, "\\\\.\\%s", dev);
    s->h = CreateFileA(path, GENERIC_READ | GENERIC_WRITE, 0, NULL, OPEN_EXISTING, 0, NULL);
    if (s->h == INVALID_HANDLE_VALUE) {
        s->h = NULL;
        return -errno_from(GetLastError());
    }

    /* Raw 9600 8N1, no flow control, DTR and RTS off: the .NET SerialPort defaults that
     * ECUTalk uses, which is the setup verified on the car. */
    dcb.DCBlength = sizeof dcb;
    if (!GetCommState(s->h, &dcb))
        goto fail;
    dcb.BaudRate = CBR_9600;
    dcb.ByteSize = 8;
    dcb.Parity = NOPARITY;
    dcb.StopBits = ONESTOPBIT;
    dcb.fBinary = TRUE;
    dcb.fParity = FALSE;
    dcb.fOutxCtsFlow = FALSE;
    dcb.fOutxDsrFlow = FALSE;
    dcb.fDtrControl = DTR_CONTROL_DISABLE;
    dcb.fDsrSensitivity = FALSE;
    dcb.fOutX = FALSE;
    dcb.fInX = FALSE;
    dcb.fErrorChar = FALSE;
    dcb.fNull = FALSE;
    dcb.fRtsControl = RTS_CONTROL_DISABLE;
    dcb.fAbortOnError = FALSE;
    if (!SetCommState(s->h, &dcb))
        goto fail;
    s->rto_ms = ~0u;
    if (!set_read_timeout(s, 0))
        goto fail;
    PurgeComm(s->h, PURGE_RXCLEAR | PURGE_TXCLEAR | PURGE_RXABORT | PURGE_TXABORT);
    timeBeginPeriod(1);

    log_opened(s, dev, log_path);
    return 0;

fail:
    err = GetLastError();
    CloseHandle(s->h);
    s->h = NULL;
    return -errno_from(err);
}

void serial_close(serial_t *s)
{
    if (!s->h)
        return;
    serial_note(s, "close");
    CloseHandle(s->h);
    s->h = NULL;
    timeEndPeriod(1);
    if (s->log)
        fclose(s->log);
    s->log = NULL;
}

void serial_write(serial_t *s, const uint8_t *buf, size_t n)
{
    log_hex(s, "TX", buf, n);
    while (n > 0) {
        DWORD m = 0;
        if (!WriteFile(s->h, buf, (DWORD)n, &m, NULL) || m == 0) {
            DWORD code = m == 0 ? ERROR_TIMEOUT : GetLastError();
            s->error = EIO;
            serial_note(s, "write failed: %s", win_error(code));
            return;
        }
        buf += m;
        n -= m;
    }
    FlushFileBuffers(s->h);     /* like tcdrain */
}

size_t serial_read(serial_t *s, uint8_t *buf, size_t n, double timeout)
{
    size_t got = 0;
    while (got < n) {
        DWORD m = 0;
        if (!set_read_timeout(s, timeout) || !ReadFile(s->h, buf + got, (DWORD)(n - got), &m, NULL)) {
            /* The FTDI driver fails reads once the dongle has gone away. */
            s->error = EIO;
            serial_note(s, "read failed: %s", win_error(GetLastError()));
            break;
        }
        if (m == 0)
            break;
        log_hex(s, "RX", buf + got, m);
        got += m;
    }
    return got;
}

#else

/* ---- Linux: termios ---- */

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

int serial_open(serial_t *s, const char *dev, const char *log_path)
{
    struct termios t;
    int lines = TIOCM_DTR | TIOCM_RTS;

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

    log_opened(s, dev, log_path);
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

#endif
