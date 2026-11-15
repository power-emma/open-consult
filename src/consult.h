/* Consult-I protocol layer (CONSULT_PROTOCOL.md §4–5, §8). C port of consult/protocol.py.
 *
 * Read-side commands, active tests (0A) and DTC clear (C1). */
#ifndef CONSULT_H
#define CONSULT_H

#include <stdatomic.h>

#include "serial.h"

#define CONSULT_ENGINE      0xEF
#define CONSULT_ENGINE_ALT  0xED    /* the 1998 Maxima's engine ECU answers ED (reply 12), not EF */
#define CONSULT_BCM         0xDA    /* body control module (IVMS); needs c->paced */
#define CONSULT_STOP        0x30
#define CONSULT_GO          0xF0
#define CONSULT_ACTIVE      0x0A
#define CONSULT_MAX_FRAME   255
#define CONSULT_MAX_DTCS    32

/* ED first: after a wrong-ID init the ECU ignores everything, including 30, until it
 * gets a correct init. */
extern const uint8_t CONSULT_ENGINE_IDS[2];

typedef struct {
    uint8_t code;       /* Nissan 2-digit code, read as hex digits (0x21 = code 21) */
    uint8_t starts;     /* engine starts since the fault was last seen */
} consult_dtc_t;

typedef struct {
    serial_t *s;
    atomic_int *cancel;     /* optional: init and frame reads give up once it's set */
    int frame_started;      /* command() already consumed the first frame's FF */
    int paced;              /* send one byte at a time, each after its echo (the BCM) */
    char err[256];          /* why the last call failed */
} consult_t;

/* Send 30 and read until a stop ack (CF or FE), skipping whole frames. Returns 1 if
 * one came. */
int consult_stop(consult_t *c, double timeout, uint8_t *ack);

/* FF, 280 ms, FF, 70 ms, <id> (ECUTalk's Delay1/Delay2), trying each ID in turn on
 * each attempt, until ~id comes back. Returns 1 and sets *id_out on success. */
int consult_init(consult_t *c, const uint8_t *ids, int nids, int tries, uint8_t *id_out);

/* Send a command list, check the echo, then send F0 to start streaming. Retries
 * this ECU's FE FE echoes and F0 → FE replies. Returns 1 on success. */
int consult_command(consult_t *c, const uint8_t *payload, size_t n, int retries);

/* Read one FF <n> <data...> frame into out (CONSULT_MAX_FRAME bytes). Frames of a
 * different length are skipped unless expected_len < 0. Returns the length or -1. */
int consult_read_frame(consult_t *c, int expected_len, double timeout, uint8_t *out);

/* Command, read a single frame, stop. Returns the frame length or -1. */
int consult_one_shot(consult_t *c, const uint8_t *payload, size_t n, uint8_t *out);

/* D0: writes e.g. "23710-2L904". Returns 1 on success. */
int consult_part_number(consult_t *c, char *out, size_t outlen);

/* D1: returns the number of codes stored in out, or -1. */
int consult_dtcs(consult_t *c, consult_dtc_t *out, int max);

/* C1: clear stored codes, then re-read D1 into out. *cleared says whether the ECU
 * accepted C1. Returns the number of codes still stored, or -1. Issue 7 of the spec
 * says C1 may clear only one of three DTC sets, hence the re-read. */
int consult_clear_dtcs(consult_t *c, consult_dtc_t *out, int max, int *cleared);

/* 0A <test> <value> F0, hold for `hold` seconds (or until *abort or c->cancel is
 * set), then 30. No retries: a bad echo stops at once. The stop is resent up to 3
 * times. While a test is held the engine ECU sends only FF 00 (empty frames); the BCM
 * sends FF 01 xx (or FF 02 xx xx) for a valid value and FF 00 for one it ignores.
 * Returns 1 when the test ran and was stopped, 0 when the ECU rejected it, and -1
 * when no stop ack came back (turn the key off to be sure it has ended). */
int consult_active_test(consult_t *c, uint8_t test, uint8_t value, double hold,
                        atomic_int *abort, uint8_t *ack, double *held);

#endif
