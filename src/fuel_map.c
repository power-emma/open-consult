#include "fuel_map.h"

#include <json-glib/json-glib.h>
#include <math.h>
#include <string.h>

struct fuel_map {
    guint nrpm, nload;
    double *rpm, *load, *cells;
};

void fuel_map_free(fuel_map_t *map)
{
    if (!map)
        return;
    g_free(map->rpm);
    g_free(map->load);
    g_free(map->cells);
    g_free(map);
}

static gboolean map_error(GError **error, const char *message)
{
    g_set_error_literal(error, G_IO_ERROR, G_IO_ERROR_INVALID_DATA, message);
    return FALSE;
}

static gboolean number(JsonNode *node, double min, double max, double *out)
{
    if (!node || !JSON_NODE_HOLDS_VALUE(node))
        return FALSE;
    GType type = json_node_get_value_type(node);
    if (type != G_TYPE_INT64 && type != G_TYPE_DOUBLE)
        return FALSE;
    *out = json_node_get_double(node);
    return isfinite(*out) && *out >= min && *out <= max;
}

static JsonArray *array(JsonNode *node)
{
    return node && JSON_NODE_HOLDS_ARRAY(node) ? json_node_get_array(node) : NULL;
}

static gboolean read_axis(JsonObject *obj, const char *name, double max,
                          double **axis, guint *count, GError **error)
{
    JsonArray *values = array(json_object_get_member(obj, name));
    *count = values ? json_array_get_length(values) : 0;
    if (*count >= 2) {
        *axis = g_new(double, *count);
        for (guint i = 0; i < *count; i++) {
            if (!number(json_array_get_element(values, i), 0, max, &(*axis)[i]) ||
                (i && (*axis)[i] <= (*axis)[i - 1]))
                goto invalid;
        }
        return TRUE;
    }
invalid:
    g_set_error(error, G_IO_ERROR, G_IO_ERROR_INVALID_DATA,
                "%s needs at least two strictly increasing numbers in 0..%.0f", name, max);
    return FALSE;
}

static gboolean read_cells(JsonObject *obj, fuel_map_t *map, GError **error)
{
    gboolean offsets = json_object_has_member(obj, "fuel_offset_percent");
    gboolean native = json_object_has_member(obj, "fuel_percent");
    if (offsets == native)
        return map_error(error, "Provide exactly one of fuel_percent or fuel_offset_percent");

    JsonArray *rows = array(json_object_get_member(obj, offsets ? "fuel_offset_percent" : "fuel_percent"));
    if (!rows || json_array_get_length(rows) != map->nload)
        return map_error(error, "The fuel grid needs one row per load breakpoint");

    /* Check dimensions before allocating a rectangular grid from file input. */
    for (guint y = 0; y < map->nload; y++) {
        JsonArray *row = array(json_array_get_element(rows, y));
        if (!row || json_array_get_length(row) != map->nrpm)
            return map_error(error, "Each fuel row needs one cell per RPM breakpoint");
    }
    if (map->nload > G_MAXSIZE / sizeof(double) / map->nrpm)
        return map_error(error, "The fuel grid is too large");
    map->cells = g_try_new(double, (gsize)map->nload * map->nrpm);
    if (!map->cells)
        return map_error(error, "Could not allocate the fuel grid");

    for (guint y = 0; y < map->nload; y++) {
        JsonArray *row = json_array_get_array_element(rows, y);
        for (guint x = 0; x < map->nrpm; x++) {
            JsonNode *node = json_array_get_element(row, x);
            double value = NAN;
            if (!JSON_NODE_HOLDS_NULL(node)) {
                if (!number(node, offsets ? -25 : 75, offsets ? 25 : 125, &value))
                    return map_error(error, offsets ? "Fuel offsets must be null or numbers in -25..25"
                                                    : "Fuel percentages must be null or numbers in 75..125");
                if (offsets)
                    value += 100;
            }
            map->cells[(gsize)y * map->nrpm + x] = value;
        }
    }
    return TRUE;
}

fuel_map_t *fuel_map_load(GFile *file, GError **error)
{
    char *contents = NULL;
    gsize len;
    if (!g_file_load_contents(file, NULL, &contents, &len, NULL, error))
        return NULL;

    JsonParser *parser = json_parser_new();
    gboolean parsed = json_parser_load_from_data(parser, contents, len, error);
    g_free(contents);
    fuel_map_t *map = NULL;
    if (parsed) {
        JsonNode *root = json_parser_get_root(parser);
        if (!root || !JSON_NODE_HOLDS_OBJECT(root)) {
            map_error(error, "The fuel map must be a JSON object");
        } else {
            JsonObject *obj = json_node_get_object(root);
            map = g_new0(fuel_map_t, 1);
            if (!read_axis(obj, "rpm_axis", 100000, &map->rpm, &map->nrpm, error) ||
                !read_axis(obj, "load_code_axis", 65535, &map->load, &map->nload, error) ||
                !read_cells(obj, map, error))
                g_clear_pointer(&map, fuel_map_free);
        }
    }
    g_object_unref(parser);
    return map;
}

fuel_map_t *fuel_map_dandymax_candidate(void)
{
    /* Raw load bounds bracket the high-throttle samples from the 2L904 fuel
     * trace. Outside this RPM/load rectangle the ECU retains feedback control.
     * Cells are nominal feedback requests, pending loaded wideband validation. */
    const double rpm[] = {3999, 4000, 4500, 5000, 5500, 5501};
    const double load[] = {27999, 28000, 32000, 32001};
    const double cells[] = {
        NAN, NAN, NAN, NAN, NAN, NAN,
        NAN,  94,  93,  94,  94, NAN,
        NAN,  94,  93,  94,  94, NAN,
        NAN, NAN, NAN, NAN, NAN, NAN,
    };
    fuel_map_t *map = g_new0(fuel_map_t, 1);
    map->nrpm = G_N_ELEMENTS(rpm);
    map->nload = G_N_ELEMENTS(load);
    map->rpm = g_memdup2(rpm, sizeof rpm);
    map->load = g_memdup2(load, sizeof load);
    map->cells = g_memdup2(cells, sizeof cells);
    return map;
}

void fuel_map_dimensions(const fuel_map_t *map, guint *rpm, guint *load)
{
    *rpm = map->nrpm;
    *load = map->nload;
}

double fuel_map_rpm(const fuel_map_t *map, guint column)
{
    return map->rpm[column];
}

double fuel_map_load_code(const fuel_map_t *map, guint row)
{
    return map->load[row];
}

double fuel_map_offset(const fuel_map_t *map, guint row, guint column)
{
    return map->cells[(gsize)row * map->nrpm + column] - 100;
}

static guint interval(const double *axis, guint count, double value, double *fraction)
{
    guint lo = 0, hi = count - 1;
    value = CLAMP(value, axis[lo], axis[hi]);
    while (hi - lo > 1) {
        guint mid = lo + (hi - lo) / 2;
        if (value >= axis[mid])
            lo = mid;
        else
            hi = mid;
    }
    *fraction = (value - axis[lo]) / (axis[hi] - axis[lo]);
    return lo;
}

int fuel_map_lookup(const fuel_map_t *map, double rpm, unsigned load)
{
    double fx, fy, total = 0;
    guint x = interval(map->rpm, map->nrpm, rpm, &fx);
    guint y = interval(map->load, map->nload, load, &fy);
    const double *row = map->cells + (gsize)y * map->nrpm + x;
    const double values[] = {row[0], row[1], row[map->nrpm], row[map->nrpm + 1]};
    const double weights[] = {(1-fx)*(1-fy), fx*(1-fy), (1-fx)*fy, fx*fy};
    for (guint i = 0; i < G_N_ELEMENTS(values); i++) {
        if (weights[i] == 0)
            continue;
        if (isnan(values[i]))
            return 0;
        total += values[i] * weights[i];
    }
    return (int)(total + 0.5);
}

static const uint8_t telemetry[] = {
    0xC9, 0x09, 0x95, 0xC9, 0x09, 0x94, /* RPM high/low */
    0xC9, 0x0A, 0xBE, 0xC9, 0x0A, 0xBD, /* raw load high/low */
    0xC9, 0x07, 0x30, 0xC9, 0x07, 0x31, /* bank A/B alpha */
    0xC9, 0x0D, 0xAA, 0xC9, 0x0D, 0xA9, /* injector A high/low */
    0xC9, 0x0D, 0xAC, 0xC9, 0x0D, 0xAB, /* injector B high/low */
    0xC9, 0x07, 0xB7, 0xC9, 0x07, 0x70, /* active flags, test value */
    0xC9, 0x09, 0x8B, /* speed */
    0xC9, 0x07, 0x0D, 0xC9, 0x02, 0x13, /* knock fail-safe / system OK */
    0xC9, 0x0D, 0xC7, /* pending knock event count */
    0xC9, 0x0D, 0xB8, 0xC9, 0x0D, 0xB7 /* signed knock retard word, high/low */
};
enum {
    BANK_A = 4, BANK_B = 5, INJECTOR_A = 6, INJECTOR_B = 8, FLAGS = 10, TEST_VALUE = 11,
    SPEED = 12, KNOCK_FAILSAFE = 13, KNOCK_HEALTH = 14, KNOCK_EVENTS = 15, KNOCK_RETARD = 16,
    TELEMETRY_BYTES = sizeof telemetry / 3
};
_Static_assert(2 * TELEMETRY_BYTES + 2 <= 40, "fuel telemetry exceeds the ECU argument buffer");

static gboolean knock_detected(consult_t *c, const uint8_t *frame)
{
    const char *reason;
    if (frame[KNOCK_FAILSAFE] & 0x80)
        reason = "ECU knock fail-safe is latched.";
    else if (!(frame[KNOCK_HEALTH] & 0x08))
        reason = "ECU reports that the knock system is unavailable.";
    else if (frame[KNOCK_EVENTS] || (frame[KNOCK_RETARD] & 0x80))
        reason = "ECU reported a knock event or knock retard.";
    else
        return FALSE;

    g_strlcpy(c->err, reason, sizeof c->err);
    serial_note(c->s, "%s 070D=%02X 0213=%02X 0DC7=%02X 0DB8:0DB7=%02X%02X",
                reason, frame[KNOCK_FAILSAFE], frame[KNOCK_HEALTH], frame[KNOCK_EVENTS],
                frame[KNOCK_RETARD], frame[KNOCK_RETARD + 1]);
    return TRUE;
}

static gboolean stop_fuel(consult_t *c)
{
    if (consult_stop(c, 0.5, NULL))
        return TRUE;
    g_strlcpy(c->err, "Consult STOP was not acknowledged", sizeof c->err);
    return FALSE;
}

static int checked_read(consult_t *c, const uint8_t *payload, size_t size,
                        int expected, uint8_t *frame)
{
    int len = -1;
    if (consult_command_once(c, payload, size))
        len = consult_read_frame(c, expected, 1.0, frame);
    return stop_fuel(c) ? len : -1;
}

static unsigned word(const uint8_t *data)
{
    return ((unsigned)data[0] << 8) | data[1];
}

static gboolean stopping(consult_t *c, const atomic_int *abort)
{
    return atomic_load(abort) || (c->cancel && atomic_load(c->cancel));
}

static gboolean control_ecu(consult_t *c, fuel_status_fn status)
{
    uint8_t frame[CONSULT_MAX_FRAME];
    const uint8_t identify = 0xD0;
    int length = checked_read(c, &identify, 1, -1, frame);
    if (length < 0) {
        status(c->err);
        return FALSE;
    }
    if (length < 5 || memcmp(frame + length - 5, "2L904", 5) != 0) {
        status("Fuel and timing control require ECU 23710-2L904.");
        return FALSE;
    }

    return TRUE;
}

static gboolean log_fuel_frame(consult_t *c, FILE *csv, double elapsed, int percent,
                               const uint8_t *frame)
{
    if (!csv)
        return TRUE;

    char seconds[G_ASCII_DTOSTR_BUF_SIZE], rpm[G_ASCII_DTOSTR_BUF_SIZE], requested[8] = "";
    g_ascii_formatd(seconds, sizeof seconds, "%.4f", elapsed);
    g_ascii_formatd(rpm, sizeof rpm, "%.1f", word(frame) * 12.5);
    if (percent > 0)
        g_snprintf(requested, sizeof requested, "%d", percent);

    unsigned inj_a = word(frame + INJECTOR_A), inj_b = word(frame + INJECTOR_B);
    unsigned retard = word(frame + KNOCK_RETARD);
    int signed_retard = retard >= 0x8000 ? (int)retard - 0x10000 : (int)retard;
    if (fprintf(csv, "%s,%s,%s,%u,%s,%u,%u,%u.%02u,%u.%02u,%u,%u,%u,%u,%u,%d,%d\n",
                seconds, percent < 0 ? "baseline" : "stream", rpm, word(frame + 2),
                requested, frame[BANK_A], frame[BANK_B], inj_a / 100, inj_a % 100,
                inj_b / 100, inj_b % 100, frame[FLAGS], frame[TEST_VALUE], frame[SPEED] * 2u,
                !!(frame[KNOCK_FAILSAFE] & 0x80), !!(frame[KNOCK_HEALTH] & 0x08),
                frame[KNOCK_EVENTS], signed_retard) >= 0 && fflush(csv) == 0)
        return TRUE;

    g_strlcpy(c->err, "Could not write the fuel session CSV.", sizeof c->err);
    return FALSE;
}

gboolean fuel_map_stream(consult_t *c, const fuel_map_t *map, double seconds,
                         const atomic_int *abort, fuel_status_fn status, fuel_sample_fn sample, FILE *csv)
{
    uint8_t frame[CONSULT_MAX_FRAME];
    if (csv && (fputs("elapsed_seconds,phase,rpm,load_code,requested_percent,alpha_a,alpha_b,"
                      "injector_a_ms,injector_b_ms,active_flags,raw_test_value,speed_kmh,"
                      "knock_failsafe,knock_system_ok,knock_events,knock_retard_raw\n", csv) == EOF ||
                fflush(csv) != 0)) {
        status("Could not initialize the fuel session CSV.");
        return FALSE;
    }
    if (!control_ecu(c, status))
        return FALSE;

    if (isinf(seconds))
        serial_note(c->s, "fuel map duration: until stopped");
    else
        serial_note(c->s, "fuel map duration: %.0f seconds", seconds);
    const double start = mono(), end = start + seconds;
    gboolean ok = TRUE, attempted = FALSE, override_attempted = FALSE, verified = FALSE;
    while (!stopping(c, abort) && mono() < end) {
        if (checked_read(c, telemetry, sizeof telemetry, TELEMETRY_BYTES, frame) < 0 ||
            !log_fuel_frame(c, csv, mono() - start, -1, frame)) {
            ok = FALSE;
            break;
        }
        if (!word(frame)) {
            g_strlcpy(c->err, "Engine is stopped.", sizeof c->err);
            ok = FALSE;
            break;
        }
        if (stopping(c, abort) || mono() >= end)
            break;

        int percent = fuel_map_lookup(map, word(frame) * 12.5, word(frame + 2));
        uint8_t payload[3 + sizeof telemetry] = {CONSULT_ACTIVE, 0x81, percent};
        memcpy(payload + 3, telemetry, sizeof telemetry);
        attempted = TRUE;
        override_attempted |= percent != 0;
        verified = FALSE;
        ok = consult_command_once(c, percent ? payload : telemetry,
                                 percent ? sizeof payload : sizeof telemetry);
        const double settle = mono() + 1.0;
        double next_sample = 0;
        unsigned consecutive = 0;
        while (ok && !stopping(c, abort) && mono() < end) {
            if (consult_read_frame(c, TELEMETRY_BYTES, 1.0, frame) < 0) {
                ok = stopping(c, abort);
                break;
            }
            if (!log_fuel_frame(c, csv, mono() - start, percent, frame)) {
                ok = FALSE;
                break;
            }
            if (!word(frame)) {
                g_strlcpy(c->err, "Engine stopped during fuel streaming.", sizeof c->err);
                ok = FALSE;
                break;
            }
            double rpm = word(frame) * 12.5;
            unsigned load = word(frame + 2);
            double now = mono();
            if (sample && now >= next_sample) {
                sample(rpm, load, percent);
                next_sample = now + 0.1;
            }
            gboolean active = (frame[FLAGS] & 2) != 0;
            gboolean matches = percent ? active && frame[TEST_VALUE] == percent &&
                                         frame[BANK_A] == percent && frame[BANK_B] == percent
                                       : !active;
            consecutive = matches ? consecutive + 1 : 0;
            if (consecutive >= 3) {
                if (!verified) {
                    char message[128];
                    if (percent)
                        g_snprintf(message, sizeof message, "Verified fuel offset %+.0f%% on both banks.",
                                   (double)percent - 100);
                    else
                        g_strlcpy(message, "Map uses normal ECU feedback at the current RPM and load.", sizeof message);
                    status(message);
                    verified = TRUE;
                }
                if (fuel_map_lookup(map, rpm, load) != percent)
                    break;
            } else if (!matches && mono() > settle) {
                g_strlcpy(c->err, "Fuel feedback did not match the requested state.", sizeof c->err);
                ok = FALSE;
            }
        }
        char stream_error[sizeof c->err];
        g_strlcpy(stream_error, ok ? "" : c->err, sizeof stream_error);
        if (!stop_fuel(c)) {
            char message[sizeof c->err + 96];
            g_snprintf(message, sizeof message, "%s%sFuel override release could not be verified. "
                       "Turn the ignition off.", stream_error, *stream_error ? " " : "");
            status(message);
            return FALSE;
        }
        if (!ok)
            break;
    }

    char reason[sizeof c->err];
    g_strlcpy(reason, c->err, sizeof reason);
    if (attempted) {
        /* Even on application shutdown, verify release after the acknowledged STOP. */
        atomic_int *cancel = c->cancel;
        c->cancel = NULL;
        int length = checked_read(c, telemetry + FLAGS * 3, 3, 1, frame);
        c->cancel = cancel;
        if (length < 0 || (frame[0] & 2)) {
            char message[sizeof c->err + 96];
            g_snprintf(message, sizeof message, "%s%sFuel override release could not be verified. "
                       "Turn the ignition off.", ok ? "" : reason, ok ? "" : " ");
            status(message);
            return FALSE;
        }
    }
    char message[sizeof c->err + 96];
    if (!ok) {
        g_snprintf(message, sizeof message, "%s%s", reason,
                   override_attempted ? " Fuel override released." : "");
    } else {
        char ending[80];
        if (stopping(c, abort))
            g_strlcpy(ending, "Fuel map session stopped.", sizeof ending);
        else
            g_snprintf(ending, sizeof ending, "Fuel map session reached its %.0f-second limit.", seconds);
        const char *result = " No fuel override was requested.";
        if (override_attempted)
            result = verified ? " Fuel override released."
                              : " Last request unverified. Fuel override released.";
        g_snprintf(message, sizeof message, "%s%s", ending, result);
    }
    serial_note(c->s, "%s", message);
    status(message);
    return ok;
}


gboolean timing_probe(consult_t *c, uint8_t raw, const atomic_int *abort,
                      fuel_status_fn status)
{
    enum { TIMING_REPORTED = 6, TIMING_RAW = TELEMETRY_BYTES, TIMING_BYTES = TELEMETRY_BYTES + 1 };
    _Static_assert(2 * TIMING_BYTES + 2 <= 40, "timing telemetry exceeds the ECU argument buffer");
    uint8_t frame[CONSULT_MAX_FRAME];
    uint8_t payload[3 + TIMING_BYTES * 3] = {CONSULT_ACTIVE, 0x82, raw};
    uint8_t *reads = payload + 3;
    memcpy(reads, telemetry, sizeof telemetry);
    /* Substitute reported timing for the first injector read and append 82's byte. */
    reads[TIMING_REPORTED * 3 + 1] = 0x07;
    reads[TIMING_REPORTED * 3 + 2] = 0x32;
    reads[TIMING_RAW * 3] = 0xC9;
    reads[TIMING_RAW * 3 + 1] = 0x07;
    reads[TIMING_RAW * 3 + 2] = 0x71;

    if (raw > 3) {
        status("Timing probe accepts raw bytes 00 through 03.");
        return FALSE;
    }
    if (!control_ecu(c, status))
        return FALSE;
    if (checked_read(c, reads, TIMING_BYTES * 3, TIMING_BYTES, frame) < 0 ||
        knock_detected(c, frame)) {
        status(c->err);
        return FALSE;
    }
    if (!word(frame) || word(frame) * 12.5 > 1200 || frame[SPEED] || (frame[FLAGS] & 6)) {
        status("Timing probe requires a stationary engine idling at or below 1,200 RPM with overrides cleared.");
        return FALSE;
    }
    if (stopping(c, abort)) {
        status("Timing probe cancelled.");
        return TRUE;
    }

    int baseline = 110 - frame[TIMING_REPORTED], measured = baseline;
    unsigned matching = 0;
    gboolean ok = consult_command_once(c, payload, sizeof payload);
    double end = mono() + 2.0;
    while (ok && !stopping(c, abort) && mono() < end) {
        if (consult_read_frame(c, TIMING_BYTES, 1.0, frame) < 0) {
            ok = stopping(c, abort);
            break;
        }
        if (knock_detected(c, frame)) {
            ok = FALSE;
            break;
        }
        if (!word(frame) || word(frame) * 12.5 > 1200 || frame[SPEED]) {
            g_strlcpy(c->err, "Timing probe cancelled because the engine left stationary idle.", sizeof c->err);
            ok = FALSE;
            break;
        }
        if ((frame[FLAGS] & 4) && frame[TIMING_RAW] == raw) {
            matching++;
            measured = 110 - frame[TIMING_REPORTED];
        } else {
            matching = 0;
        }
    }

    char reason[sizeof c->err];
    g_strlcpy(reason, c->err, sizeof reason);
    if (!stop_fuel(c)) {
        status("Timing override STOP was not acknowledged. Turn the ignition off.");
        return FALSE;
    }
    atomic_int *cancel = c->cancel;
    c->cancel = NULL;
    int length = checked_read(c, telemetry + FLAGS * 3, 3, 1, frame);
    c->cancel = cancel;
    if (length < 0 || (frame[0] & 4)) {
        status("Timing override release could not be verified. Turn the ignition off.");
        return FALSE;
    }
    char message[sizeof c->err + 64];
    if (!ok)
        g_snprintf(message, sizeof message, "%s Timing override released.", reason);
    else if (matching < 3)
        g_strlcpy(message, "Timing probe ended before raw request verification. Override released.", sizeof message);
    else
        g_snprintf(message, sizeof message,
                   "Raw 0x%02X accepted. ECU reported %d° BTDC before and %d° BTDC during the probe. Override released.",
                   raw, baseline, measured);
    status(message);
    return ok;
}
