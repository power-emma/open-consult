/* Engine live-data sensors and fault-code names (CONSULT_PROTOCOL.md §6, §9).
 * C port of consult/registers.py, limited to registers this ECU supports. */
#ifndef REGISTERS_H
#define REGISTERS_H

#include <stddef.h>
#include <stdint.h>

#define N_SENSORS 22

typedef struct {
    const char *name;
    uint8_t regs[2];        /* MSB first */
    int nregs;
    double scale, offset;   /* value = raw * scale + offset */
    int decimals;
    const char *unit;
    int extra;              /* left out of the core list (see sensor_payload) */
} sensor_t;

extern const sensor_t SENSORS[N_SENSORS];

/* Indexes into SENSORS used by the active-test checks. */
enum { SENSOR_RPM = 0, SENSOR_COOLANT = 1, SENSOR_INJ_LH = 9, SENSOR_INJ_RH = 10,
       SENSOR_TIMING = 11 };

/* 5A <reg> for every sensor register in table order (full = 1), or only the core
 * sensors (full = 0: 18 registers, the size proven on the car; the full list is 27,
 * inside the ROM's limit of 40 but untested). Returns the payload length. */
size_t sensor_payload(uint8_t *out, int full);

/* Data bytes in one frame of that stream. */
int sensor_frame_len(int full);

/* Frame (in request order) to scaled values, one per sensor. Sensors left out of a
 * core stream are set to NAN. */
void sensor_decode(const uint8_t *frame, int full, double *values);

/* Name of a D1 code byte read as hex digits, or NULL if it's not in the list. */
const char *dtc_name(uint8_t code);

#define DTC_NO_FAULT 0x55

/* Active tests (CONSULT_PROTOCOL.md §8), limited to values inside the normal ranges.
 * Same set and limits as ACTIVE_TESTS in consult/__main__.py. */
#define N_ACTIVE_TESTS 5

typedef struct {
    const char *name;
    uint8_t reg;
    int has_value, min, max, def;
    const char *unit;
    int needs_idle;     /* refused unless the engine idles at 400..1500 rpm */
    int needs_warm;     /* refused below 60 °C coolant */
} active_test_t;

extern const active_test_t ACTIVE_TESTS[N_ACTIVE_TESTS];

/* The value byte for a test argument (already within min..max). */
uint8_t active_encode(const active_test_t *t, int arg);

/* BCM (IVMS, unit DA) active tests: 0A <item> <value> F0, found on the car on
 * 2026-11-14 (CAR_TEST_CHECKLIST.md §8). An output runs only while the test is held. */
#define N_BCM_TESTS 13
#define BCM_WINDOWS 0x13    /* value 1 + 2 * window + down, see bcm_window_value() */

typedef struct {
    const char *name;
    uint8_t item, value;
} bcm_test_t;

extern const bcm_test_t BCM_TESTS[N_BCM_TESTS];

/* Window 0..3 = driver, front passenger, rear right, rear left. */
#define N_BCM_WINDOWS 4
extern const char *const BCM_WINDOW_NAMES[N_BCM_WINDOWS];
uint8_t bcm_window_value(int window, int down);

/* BCM switch block (5A FF, 18 data bytes; BCM.md "Switch block"). Each input is one
 * bit; `on` is shown when the bit is set, `off` when it's clear. */
#define BCM_SWITCH_LEN  18
#define BCM_WIPER_KNOB  17      /* byte 17: intermittent wiper knob, analog 01..E4 */

typedef struct {
    const char *group, *name;
    uint8_t byte, mask;
    const char *on, *off;
} bcm_input_t;

#define N_BCM_GROUPS 5
extern const char *const BCM_GROUPS[N_BCM_GROUPS];
#define N_BCM_INPUTS 29
extern const bcm_input_t BCM_INPUTS[N_BCM_INPUTS];

#endif
