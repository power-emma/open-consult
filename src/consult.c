#include "consult.h"

#include <string.h>

const uint8_t CONSULT_ENGINE_IDS[2] = {CONSULT_ENGINE_ALT, CONSULT_ENGINE};

static int cancelled(consult_t *c)
{
    return c->cancel && atomic_load(c->cancel);
}

/* Serial reads use idle timeouts. One byte per call enforces a shared deadline. */
static size_t read_until(consult_t *c, uint8_t *out, size_t n, double end)
{
    size_t got = 0;
    while (got < n && !c->s->error) {
        double remaining = end - mono();
        if (remaining <= 0 || serial_read(c->s, out + got, 1, remaining) != 1)
            break;
        got++;
    }
    return got;
}

static void hex(char *out, size_t outlen, const uint8_t *buf, size_t n)
{
    size_t o = 0;
    out[0] = '\0';
    for (size_t i = 0; i < n && o + 4 < outlen; i++)
        o += (size_t)snprintf(out + o, outlen - o, i ? " %02x" : "%02x", buf[i]);
    if (n == 0)
        snprintf(out, outlen, "(none)");
}

/* Number of argument bytes that follow each command byte (echoed verbatim). */
static size_t nargs(uint8_t cmd)
{
    switch (cmd) {
    case 0x5A: return 1;
    case 0xC9: return 2;
    case 0x0A: return 2;
    default:   return 0;
    }
}

static size_t expected_echo(const uint8_t *p, size_t n, uint8_t *out)
{
    size_t o = 0;
    for (size_t i = 0; i < n;) {
        size_t k = nargs(p[i]);
        out[o++] = (uint8_t)~p[i];
        for (size_t j = 1; j <= k && i + j < n; j++)
            out[o++] = p[i + j];
        i += 1 + k;
    }
    return o;
}

/* Send a payload and read its echo (want, wn bytes) into got. The BCM answers FE to a
 * command list sent in one burst, so a paced unit gets one byte at a time, each after
 * its echo, stopping at the first wrong one. Returns the number of echo bytes read. */
static size_t xfer(consult_t *c, const uint8_t *payload, size_t n, const uint8_t *want,
                   size_t wn, uint8_t *got)
{
    size_t gn = 0;

    if (!c->paced) {
        serial_write(c->s, payload, n);
        return serial_read(c->s, got, wn, 0.5);
    }
    for (size_t i = 0; i < n && gn < wn; i++) {
        serial_write(c->s, &payload[i], 1);
        if (serial_read(c->s, &got[gn], 1, 0.3) != 1 || got[gn++] != want[i])
            break;
    }
    return gn;
}

int consult_stop(consult_t *c, double timeout, uint8_t *ack)
{
    uint8_t b = CONSULT_STOP;
    double end;

    serial_write(c->s, &b, 1);
    if (c->desynchronized)
        return 0;
    end = mono() + timeout;
    while (mono() < end && !c->s->error) {
        if (c->frame_started) {
            c->frame_started = 0;
            b = 0xFF;
        } else if (read_until(c, &b, 1, end) != 1)
            break;
        if (b == 0xFF) {
            /* Skip a whole frame, so a data byte of CF or FE isn't taken for the ack.
             * Only whole frames come before the ack (checklist 1.5). */
            uint8_t n, skip[CONSULT_MAX_FRAME];
            if (read_until(c, &n, 1, end) != 1 || read_until(c, skip, n, end) != n) {
                c->desynchronized = 1;
                return 0;
            }
            continue;
        }
        if (b == 0xCF || b == 0xFE) {
            if (ack)
                *ack = b;
            return 1;
        }
    }
    return 0;
}

int consult_init(consult_t *c, const uint8_t *ids, int nids, int tries, uint8_t *id_out)
{
    const uint8_t ff = 0xFF;

    for (int n = 0; n < tries * nids; n++) {
        uint8_t ecu = ids[n % nids], b;
        double sent;

        if (cancelled(c) || c->s->error)
            break;
        consult_stop(c, 0.5, NULL);
        serial_drain(c->s, 0.2, 3.0);
        serial_write(c->s, &ff, 1);
        sleep_s(0.28);
        serial_write(c->s, &ff, 1);
        sleep_s(0.07);
        serial_write(c->s, &ecu, 1);
        sent = mono();
        while (mono() - sent < 2.0 && !c->s->error) {
            if (serial_read(c->s, &b, 1, 0.2) != 1)
                continue;
            if (b == (uint8_t)~ecu) {
                serial_note(c->s, "init ok id=%02X attempt=%d secs=%.3f",
                            ecu, n / nids + 1, mono() - sent);
                *id_out = ecu;
                c->frame_started = 0;
                c->desynchronized = 0;
                return 1;
            }
        }
    }
    snprintf(c->err, sizeof c->err, "no reply to init");
    return 0;
}

int consult_command(consult_t *c, const uint8_t *payload, size_t n, int retries)
{
    uint8_t want[2 * 64], got[2 * 64];
    char a[96], b[96];
    size_t wn;

    if (!n || n > 64 || retries < 0 || c->desynchronized) {
        snprintf(c->err, sizeof c->err, "invalid command or desynchronized stream");
        return 0;
    }
    size_t c9_count = 0;
    for (size_t i = 0; i < n;) {
        uint8_t cmd = payload[i];
        size_t k = nargs(cmd);
        if (i + 1 + k > n) {
            snprintf(c->err, sizeof c->err, "incomplete command arguments");
            return 0;
        }
        if (cmd == 0xC9) c9_count++;
        if (cmd != 0xC9 && cmd != 0x5A && cmd != 0xD0 && cmd != 0xD1)
            retries = 0;
        i += 1 + k;
    }
    if (c9_count > 8) retries = 0;
    wn = expected_echo(payload, n, want);
    for (int t = 0; t <= retries && !c->s->error; t++) {
        size_t gn = xfer(c, payload, n, want, wn, got);
        if (gn == wn && memcmp(got, want, wn) == 0) {
            uint8_t go = CONSULT_GO, first;
            size_t fn;
            serial_write(c->s, &go, 1);
            fn = serial_read(c->s, &first, 1, 0.5);
            if (fn == 1 && first == 0xFF) {
                c->frame_started = 1;
                return 1;
            }
            hex(a, sizeof a, &first, fn);
            snprintf(c->err, sizeof c->err, "F0 answered with %s", a);
        } else {
            hex(a, sizeof a, got, gn);
            hex(b, sizeof b, want, wn);
            snprintf(c->err, sizeof c->err, "bad echo %s, expected %s", a, b);
        }
        serial_note(c->s, "command try %d failed: %s", t + 1, c->err);
        consult_stop(c, 0.5, NULL);
        serial_drain(c->s, 0.1, 3.0);
    }
    return 0;
}

int consult_read_frame(consult_t *c, int expected_len, double timeout, uint8_t *out)
{
    double end = mono() + timeout;
    if (c->desynchronized) {
        snprintf(c->err, sizeof c->err, "stream desynchronized; explicit recovery required");
        return -1;
    }
    while (mono() < end && !cancelled(c) && !c->s->error) {
        uint8_t b, n;
        if (c->frame_started) {
            c->frame_started = 0;
        } else {
            if (read_until(c, &b, 1, end) != 1)
                break;
            if (b != 0xFF)
                continue;
        }
        if (read_until(c, &n, 1, end) != 1) {
            c->desynchronized = 1;
            break;
        }
        if (read_until(c, out, n, end) != n) {
            c->desynchronized = 1;
            break;
        }
        if (expected_len < 0 || n == expected_len)
            return n;
    }
    snprintf(c->err, sizeof c->err, "no frame");
    return -1;
}

int consult_one_shot(consult_t *c, const uint8_t *payload, size_t n, uint8_t *out)
{
    int len;
    if (!consult_command(c, payload, n, 2))
        return -1;
    len = consult_read_frame(c, -1, 1.0, out);
    consult_stop(c, 2.0, NULL);
    return len;
}

int consult_part_number(consult_t *c, char *out, size_t outlen)
{
    const uint8_t cmd = 0xD0;
    uint8_t d[CONSULT_MAX_FRAME];
    int n = consult_one_shot(c, &cmd, 1, d);

    if (n >= 5) {
        /* 1998 Maxima: 32-byte frame ending in ASCII, e.g. "2L904" = 23710-2L904 */
        const uint8_t *tail = d + n - 5;
        int ascii = 1;
        for (int i = 0; i < 5; i++)
            ascii &= tail[i] >= 0x30 && tail[i] < 0x5B;
        if (ascii) {
            snprintf(out, outlen, "23710-%.5s", (const char *)tail);
            return 1;
        }
    }
    if (n >= 22) {
        snprintf(out, outlen, "%02X%02X 23710-%X%02X%02X", d[2], d[3], d[19], d[20], d[21]);
        return 1;
    }
    if (n >= 0)
        snprintf(c->err, sizeof c->err, "unrecognised D0 frame (%d bytes)", n);
    return 0;
}

int consult_dtcs(consult_t *c, consult_dtc_t *out, int max)
{
    const uint8_t cmd = 0xD1;
    uint8_t d[CONSULT_MAX_FRAME];
    int n = consult_one_shot(c, &cmd, 1, d), k = 0;

    if (n < 0)
        return -1;
    for (int i = 0; i + 1 < n && k < max; i += 2, k++) {
        out[k].code = d[i];
        out[k].starts = d[i + 1];
    }
    return k;
}

int consult_read_memory(consult_t *c, const uint16_t *addrs, int n, uint8_t *out)
{
    uint8_t payload[3 * 8], d[CONSULT_MAX_FRAME];
    int len;

    if (n < 1 || n > 8) {
        snprintf(c->err, sizeof c->err, "C9 takes 1..8 addresses");
        return 0;
    }
    for (int i = 0; i < n; i++) {
        payload[3 * i] = 0xC9;
        payload[3 * i + 1] = addrs[i] >> 8;
        payload[3 * i + 2] = addrs[i] & 0xFF;
    }
    len = consult_one_shot(c, payload, 3 * (size_t)n, d);
    if (len != n) {
        if (len >= 0)
            snprintf(c->err, sizeof c->err, "C9 frame of %d bytes, expected %d", len, n);
        return 0;
    }
    memcpy(out, d, (size_t)n);
    return 1;
}

int consult_clear_dtcs(consult_t *c, consult_dtc_t *out, int max, int *cleared)
{
    const uint8_t cmd = 0xC1;
    uint8_t d[CONSULT_MAX_FRAME];
    char why[sizeof c->err];
    int n = consult_one_shot(c, &cmd, 1, d), k;

    *cleared = n >= 0;
    if (n >= 0)
        serial_note(c->s, "C1 accepted, %d-byte frame", n);
    else
        serial_note(c->s, "C1 failed: %s", c->err);
    snprintf(why, sizeof why, "%s", c->err);
    if (c->s->error)
        return -1;
    k = consult_dtcs(c, out, max);
    if (!*cleared)
        snprintf(c->err, sizeof c->err, "%s", why);   /* keep the C1 failure for the caller */
    return k;
}

int consult_active_test(consult_t *c, uint8_t test, uint8_t value, double hold,
                        atomic_int *abort, uint8_t *ack, double *held)
{
    uint8_t payload[3] = {CONSULT_ACTIVE, test, value}, want[3], got[3], buf[64];
    size_t gn;
    int ran = 0;

    if (held)
        *held = 0;
    expected_echo(payload, sizeof payload, want);
    gn = xfer(c, payload, sizeof payload, want, sizeof want, got);
    if (gn == sizeof got && memcmp(got, want, sizeof want) == 0) {
        uint8_t go = CONSULT_GO;
        double start;
        serial_write(c->s, &go, 1);
        serial_note(c->s, "active test %02X=%02X on, holding %.1f s", test, value, hold);
        start = mono();
        while (mono() - start < hold && !cancelled(c) && !(abort && atomic_load(abort)) &&
               !c->s->error)
            serial_read(c->s, buf, sizeof buf, 0.2);
        if (held)
            *held = mono() - start;
        ran = 1;
    } else {
        char a[16], b[16];
        hex(a, sizeof a, got, gn);
        hex(b, sizeof b, want, sizeof want);
        snprintf(c->err, sizeof c->err, "bad echo %s, expected %s", a, b);
    }

    for (int i = 0; i < 3; i++)
        if (consult_stop(c, 2.0, ack)) {
            serial_note(c->s, "active test %02X stopped, ack %02X", test, *ack);
            return ran;
        }
    serial_note(c->s, "active test %02X: NO stop ack", test);
    snprintf(c->err, sizeof c->err, "no stop ack");
    return -1;
}
