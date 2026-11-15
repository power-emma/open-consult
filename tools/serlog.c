// LD_PRELOAD logger: every read/write/ioctl/tcsetattr on /dev/ttyUSB0 (char 188:0),
// in the same "secs TAG text" format as consult/transport.py. Log path: $SERLOG.
#define _GNU_SOURCE
#include <dlfcn.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>
#include <pthread.h>

static pthread_mutex_t mu = PTHREAD_MUTEX_INITIALIZER;
static FILE *logf;
static struct timespec t0;

static int is_port(int fd) {
    struct stat st;
    if (fstat(fd, &st) || !S_ISCHR(st.st_mode)) return 0;
    return major(st.st_rdev) == 188 && minor(st.st_rdev) == 0;
}

static void logline(const char *tag, const char *fmt, ...) {
    pthread_mutex_lock(&mu);
    if (!logf) {
        const char *p = getenv("SERLOG");
        logf = fopen(p ? p : "/tmp/serlog.log", "a");
        clock_gettime(CLOCK_MONOTONIC, &t0);
        if (logf) fprintf(logf, "  0.000000 ## serlog attached pid=%d\n", getpid());
    }
    if (logf) {
        struct timespec now;
        clock_gettime(CLOCK_MONOTONIC, &now);
        double s = (now.tv_sec - t0.tv_sec) + (now.tv_nsec - t0.tv_nsec) / 1e9;
        fprintf(logf, "%10.6f %s ", s, tag);
        va_list ap;
        va_start(ap, fmt);
        vfprintf(logf, fmt, ap);
        va_end(ap);
        fputc('\n', logf);
        fflush(logf);
    }
    pthread_mutex_unlock(&mu);
}

static void loghex(const char *tag, const unsigned char *b, ssize_t n) {
    char buf[3 * 4096 + 1];
    int k = 0;
    for (ssize_t i = 0; i < n && i < 4096; i++) k += sprintf(buf + k, i ? " %02x" : "%02x", b[i]);
    buf[k] = 0;
    logline(tag, "%s", buf);
}

ssize_t write(int fd, const void *b, size_t n) {
    static ssize_t (*real)(int, const void *, size_t);
    if (!real) real = dlsym(RTLD_NEXT, "write");
    ssize_t r = real(fd, b, n);
    if (r > 0 && is_port(fd)) loghex("TX", b, r);
    return r;
}

ssize_t read(int fd, void *b, size_t n) {
    static ssize_t (*real)(int, void *, size_t);
    if (!real) real = dlsym(RTLD_NEXT, "read");
    ssize_t r = real(fd, b, n);
    if (r > 0 && is_port(fd)) loghex("RX", b, r);
    return r;
}

int ioctl(int fd, unsigned long req, ...) {
    static int (*real)(int, unsigned long, ...);
    if (!real) real = dlsym(RTLD_NEXT, "ioctl");
    va_list ap;
    va_start(ap, req);
    void *arg = va_arg(ap, void *);
    va_end(ap);
    int r = real(fd, req, arg);
    if (is_port(fd)) {
        unsigned v = 0;
        if (req == TIOCMBIS || req == TIOCMBIC || req == TIOCMSET || req == TIOCMGET) v = *(int *)arg;
        logline("##", "ioctl %#lx arg=%#x -> %d%s", req, v,  r,
                req == TIOCMBIS ? " (TIOCMBIS)" : req == TIOCMBIC ? " (TIOCMBIC)" :
                req == TIOCMSET ? " (TIOCMSET)" : req == TIOCMGET ? " (TIOCMGET)" :
                req == TIOCSBRK ? " (BREAK ON)" : req == TIOCCBRK ? " (BREAK OFF)" : "");
    }
    return r;
}

int tcsetattr(int fd, int act, const struct termios *t) {
    static int (*real)(int, int, const struct termios *);
    if (!real) real = dlsym(RTLD_NEXT, "tcsetattr");
    int r = real(fd, act, t);
    if (is_port(fd))
        logline("##", "tcsetattr iflag=%#x oflag=%#x cflag=%#x lflag=%#x ospeed=%u -> %d",
                t->c_iflag, t->c_oflag, t->c_cflag, t->c_lflag, cfgetospeed(t), r);
    return r;
}

int tcflush(int fd, int q) {
    static int (*real)(int, int);
    if (!real) real = dlsym(RTLD_NEXT, "tcflush");
    int r = real(fd, q);
    if (is_port(fd)) logline("##", "tcflush %d", q);
    return r;
}

int tcsendbreak(int fd, int d) {
    static int (*real)(int, int);
    if (!real) real = dlsym(RTLD_NEXT, "tcsendbreak");
    if (is_port(fd)) logline("##", "tcsendbreak %d", d);
    return real(fd, d);
}
