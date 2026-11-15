/* consult-gui: read engine sensors, read and clear fault codes, run engine active
 * tests, drive the body control module's outputs (windows, locks, wipers…), show its
 * switch inputs (doors, key, locks…) and read the knock fail-safe state.
 *
 * The serial link runs on a worker thread that opens the port, inits the unit it needs
 * (the engine ECU or the BCM, switching between them as asked) and then streams live
 * data, reads or clears codes, or runs an active test. It closes the port when there's
 * nothing left to do. Every session appends a raw TX/RX log to logs/YYYY-MM-DD_gui.log. */
#include <errno.h>
#include <math.h>
#include <gtk/gtk.h>
#include <stdatomic.h>
#include <stdlib.h>
#include <string.h>

#ifdef _WIN32
#define NOMINMAX
#include <windows.h>
#include <initguid.h>
#include <devguid.h>
#include <setupapi.h>
#endif

#include "consult.h"
#include "registers.h"

/* $CONSULT_LOG_DIR if set. Otherwise Linux: the Makefile sets LOG_DIR to the checkout's
 * logs/. Windows: logs/ next to consult-gui.exe (the checkout when built there, or the
 * unpacked dist folder). */
#if !defined(LOG_DIR) && !defined(_WIN32)
#define LOG_DIR "logs"
#endif

static char *log_dir(void)
{
    const char *env = g_getenv("CONSULT_LOG_DIR");     /* set by the single-file launcher */
    if (env && *env)
        return g_strdup(env);
#if defined(_WIN32) && !defined(LOG_DIR)
    char *base = g_win32_get_package_installation_directory_of_module(NULL);
    char *dir = g_build_filename(base ? base : ".", "logs", NULL);
    g_free(base);
    return dir;
#else
    return g_strdup(LOG_DIR);
#endif
}

enum { MSG_STATUS, MSG_VALUES, MSG_DTCS, MSG_ACTIVE, MSG_BCM, MSG_BODY, MSG_KNOCK, MSG_DONE };

#define WINDOW_MAX_HOLD 10.0    /* s; a window moves only while its button is held */

typedef struct {
    int kind;
    char text[256];
    double values[N_SENSORS];
    double fps;
    consult_dtc_t dtcs[CONSULT_MAX_DTCS];
    int ndtcs;
    uint8_t knock[3];       /* $070D, $0213, $0DB8 */
    uint8_t body[BCM_SWITCH_LEN];
    int body_ok;            /* 0: no switch block (lost or disconnected), show dashes */
} msg_t;

static struct {
    GtkWidget *win, *dev, *dev_list, *dev_scan, *live_btn, *dtc_btn, *clear_btn, *status, *fps, *dtc_grid;
    GtkWidget *value[N_SENSORS];
    GtkWidget *test, *test_value, *test_unit, *test_hold, *test_btn, *test_result;
    GtkWidget *bcm_btn[N_BCM_TESTS], *bcm_hold, *bcm_result, *bcm_latch;
    GtkWidget *body_val[N_BCM_INPUTS], *body_knob, *body_raw;
    GtkWidget *knock_btn, *knock_fs, *knock_ok, *knock_val, *knock_raw;
    GThread *thread;
    GPtrArray *dev_paths;   /* path per dev_list entry; the last entry is "Custom…" */
    char devpath[256];
    GMutex lock;            /* guards the want_* flags and the active_* and bcm_* parameters */
    int want_live, want_dtc, want_clear, want_active, want_bcm, want_knock;
    int want_latch;         /* stay connected to the BCM while idle */
    int active_idx, active_arg;
    double active_hold;
    char bcm_name[64];
    uint8_t bcm_item, bcm_value;
    double bcm_hold_s;
    atomic_int cancel;      /* set on quit */
    atomic_int abort_test;  /* "Stop test" pressed */
    atomic_int abort_bcm;   /* window button released */
} app;

/* ---- worker thread ---- */

static gboolean on_msg(gpointer p);

static void post(msg_t *m)
{
    g_idle_add(on_msg, m);
}

static void post_status(const char *fmt, ...) G_GNUC_PRINTF(1, 2);
static void post_status(const char *fmt, ...)
{
    msg_t *m = g_new0(msg_t, 1);
    va_list ap;
    m->kind = MSG_STATUS;
    va_start(ap, fmt);
    g_vsnprintf(m->text, sizeof m->text, fmt, ap);
    va_end(ap);
    post(m);
}

static void post_active(const char *fmt, ...) G_GNUC_PRINTF(1, 2);
static void post_active(const char *fmt, ...)
{
    msg_t *m = g_new0(msg_t, 1);
    va_list ap;
    m->kind = MSG_ACTIVE;
    va_start(ap, fmt);
    g_vsnprintf(m->text, sizeof m->text, fmt, ap);
    va_end(ap);
    post(m);
}

static void post_bcm(const char *fmt, ...) G_GNUC_PRINTF(1, 2);
static void post_bcm(const char *fmt, ...)
{
    msg_t *m = g_new0(msg_t, 1);
    va_list ap;
    m->kind = MSG_BCM;
    va_start(ap, fmt);
    g_vsnprintf(m->text, sizeof m->text, fmt, ap);
    va_end(ap);
    post(m);
}

static void post_kind(int kind)
{
    msg_t *m = g_new0(msg_t, 1);
    m->kind = kind;
    post(m);
}

static void give_up(void)
{
    g_mutex_lock(&app.lock);
    app.want_live = app.want_dtc = app.want_clear = app.want_active = app.want_bcm = 0;
    app.want_knock = 0;
    app.want_latch = 0;
    g_mutex_unlock(&app.lock);
}

static const char *link_error(consult_t *c)
{
    return c->s->error ? "the dongle stopped responding (dropped off USB?)" : c->err;
}

/* Stream a few frames of the sensor list, show them, and return the last one. */
static int snapshot(consult_t *c, const uint8_t *payload, size_t plen, int flen, int full,
                    double *values)
{
    uint8_t frame[CONSULT_MAX_FRAME];
    int ok = 0;
    if (!consult_command(c, payload, plen, 2))
        return 0;
    for (int i = 0; i < 5; i++)
        ok = consult_read_frame(c, flen, 1.0, frame) >= 0;
    consult_stop(c, 2.0, NULL);
    if (ok) {
        msg_t *m = g_new0(msg_t, 1);
        m->kind = MSG_VALUES;
        sensor_decode(frame, full, values);
        memcpy(m->values, values, sizeof m->values);
        post(m);
    }
    return ok;
}

static void run_active(consult_t *c, const uint8_t *payload, size_t plen, int flen, int full,
                       int idx, int arg, double hold)
{
    const active_test_t *t = &ACTIVE_TESTS[idx];
    uint8_t value = active_encode(t, arg), ack = 0;
    double before[N_SENSORS], after[N_SENSORS], held;
    int rc;

    if (!snapshot(c, payload, plen, flen, full, before)) {
        post_active("Not sent: couldn't read the engine first (%s).", link_error(c));
        return;
    }
    if (t->needs_idle && (before[SENSOR_RPM] < 400 || before[SENSOR_RPM] > 1500)) {
        post_active("Not sent: %s needs the engine idling (it's at %.0f rpm).", t->name,
                    before[SENSOR_RPM]);
        return;
    }
    if (t->needs_warm && before[SENSOR_COOLANT] < 60) {
        post_active("Not sent: %s needs a warm engine (coolant %.0f °C).", t->name,
                    before[SENSOR_COOLANT]);
        return;
    }

    post_status("Active test running: %s (0A %02X %02X), up to %.0f s", t->name, t->reg,
                value, hold);
    post_active("Running…");
    atomic_store(&app.abort_test, 0);
    rc = consult_active_test(c, t->reg, value, hold, &app.abort_test, &ack, &held);
    if (rc < 0) {
        post_active("WARNING: the ECU didn't acknowledge the stop. Turn the key off to be "
                    "sure the test has ended.");
        post_status("Active test: no stop ack");
        return;
    }
    if (rc == 0) {
        post_active("The ECU rejected %s (%s). Nothing was changed.", t->name, c->err);
        post_status("Active test rejected");
        return;
    }
    post_status("Active test finished and stopped (ack %02X)", ack);
    if (!snapshot(c, payload, plen, flen, full, after)) {
        post_active("%s ran for %.1f s and was stopped. Couldn't read the engine afterwards.",
                    t->name, held);
        return;
    }
    post_active("%s ran for %.1f s and was stopped.\n"
                "Before → just after:\n"
                "  %.0f → %.0f rpm\n"
                "  timing %.0f° → %.0f°\n"
                "  injector LH %.2f → %.2f ms, RH %.2f → %.2f ms",
                t->name, held, before[SENSOR_RPM], after[SENSOR_RPM],
                before[SENSOR_TIMING], after[SENSOR_TIMING],
                before[SENSOR_INJ_LH], after[SENSOR_INJ_LH],
                before[SENSOR_INJ_RH], after[SENSOR_INJ_RH]);
}

/* Init the engine ECU unless it's the unit already selected (*cur, 0 = none). */
static int use_engine(consult_t *c, uint8_t *cur)
{
    uint8_t id;
    char pn[32];

    if (*cur && *cur != CONSULT_BCM)
        return 1;
    c->paced = 0;
    *cur = 0;
    post_status("Connecting to the ECU…");
    if (!consult_init(c, CONSULT_ENGINE_IDS, 2, 3, &id)) {
        if (!atomic_load(&app.cancel))
            post_status(c->s->error ? "Connection failed: %s"
                                    : "No reply from the ECU (%s). Is the key at ON and the "
                                      "dongle plugged into the car?", link_error(c));
        return 0;
    }
    *cur = id;
    if (consult_part_number(c, pn, sizeof pn))
        post_status("Connected: ECU %02X, %s", id, pn);
    else
        post_status("Connected: ECU %02X", id);
    return 1;
}

/* Same for the BCM, which takes one byte at a time. */
static int use_bcm(consult_t *c, uint8_t *cur)
{
    static const uint8_t ids[1] = {CONSULT_BCM};
    uint8_t id;

    if (*cur == CONSULT_BCM)
        return 1;
    c->paced = 1;
    *cur = 0;
    post_status("Connecting to the BCM…");
    if (!consult_init(c, ids, 1, 3, &id)) {
        if (!atomic_load(&app.cancel))
            post_status("No reply from the BCM (%s). Is the key at ON?", link_error(c));
        return 0;
    }
    *cur = id;
    post_status("Connected: BCM %02X", id);
    return 1;
}

static void post_body(const uint8_t *frame)
{
    msg_t *m = g_new0(msg_t, 1);
    m->kind = MSG_BODY;
    if (frame) {
        memcpy(m->body, frame, sizeof m->body);
        m->body_ok = 1;
    }
    post(m);
}

/* Latched and idle: keep the BCM session open. A one-shot 5A FF read every 0.25 s
 * keeps it awake, feeds the body status panel and shows whether the link is still up
 * (it isn't after a key-off). Returns 0 when that read fails, so the caller
 * reconnects. */
static int bcm_keepalive(consult_t *c, double *last)
{
    static const uint8_t poll[2] = {0x5A, 0xFF};
    uint8_t frame[CONSULT_MAX_FRAME];

    sleep_s(0.02);
    if (mono() - *last < 0.25)
        return 1;
    *last = mono();
    if (consult_one_shot(c, poll, sizeof poll, frame) == BCM_SWITCH_LEN) {
        post_body(frame);
        return 1;
    }
    serial_note(c->s, "BCM keep-alive failed: %s", c->err);
    post_body(NULL);
    return 0;
}

static void run_bcm(consult_t *c, const char *name, uint8_t item, uint8_t value, double hold)
{
    uint8_t ack = 0;
    double held;
    int rc;

    if (atomic_load(&app.abort_bcm)) {
        post_bcm("%s: button released before the BCM was ready. Hold it down.", name);
        return;
    }
    post_status("BCM test running: %s (0A %02X %02X)", name, item, value);
    rc = consult_active_test(c, item, value, hold, &app.abort_bcm, &ack, &held);
    if (rc < 0) {
        post_bcm("WARNING: the BCM didn't acknowledge the stop. Turn the key off to be sure "
                 "%s has ended.", name);
        post_status("BCM test: no stop ack");
        return;
    }
    if (rc == 0) {
        post_bcm("The BCM rejected %s (%s). Nothing was changed.", name, c->err);
        post_status("BCM test rejected");
        return;
    }
    post_bcm("%s: ran for %.1f s and was stopped.", name, held);
    post_status("BCM test finished and stopped (ack %02X)", ack);
}

/* Knock fail-safe state (ROM_ANALYSIS.md §8b): $070D b7 = fail-safe latched, $0213 b3 =
 * knock system OK (from the second CPU), $0DB8 = knock retard term (signed). */
static int read_knock(consult_t *c)
{
    static const uint16_t addrs[3] = {0x070D, 0x0213, 0x0DB8};
    msg_t *m = g_new0(msg_t, 1);

    if (!consult_read_memory(c, addrs, 3, m->knock)) {
        g_free(m);
        post_status("Couldn't read the knock state: %s", link_error(c));
        return 0;
    }
    m->kind = MSG_KNOCK;
    post(m);
    post_status("Knock state read");
    return 1;
}

static gpointer worker(gpointer unused)
{
    serial_t s;
    consult_t c = {.s = &s, .cancel = &app.cancel};
    uint8_t payload[2 * 40], frame[CONSULT_MAX_FRAME], cur = 0;
    int full = 1;           /* drops to the core list if the ECU refuses the full one */
    size_t plen = sensor_payload(payload, full);
    int flen = sensor_frame_len(full), streaming = 0, frames = 0, timeouts = 0, latched = 0;
    double t0 = 0, last_post = 0, last_poll = 0;
    char log[512], date[16];
    GDateTime *now = g_date_time_new_now_local();
    int rc;

    (void)unused;
    g_snprintf(date, sizeof date, "%04d-%02d-%02d", g_date_time_get_year(now),
               g_date_time_get_month(now), g_date_time_get_day_of_month(now));
    g_date_time_unref(now);
    {
        char *dir = log_dir();
        g_mkdir_with_parents(dir, 0755);
        g_snprintf(log, sizeof log, "%s/%s_gui.log", dir, date);
        g_free(dir);
    }

    rc = serial_open(&s, app.devpath, log);
    if (rc < 0) {
        if (rc == -EACCES)
#ifdef _WIN32
            post_status("%s is busy or access is denied. Close ECUTalk or anything "
                        "else using it.", app.devpath);
#else
            post_status("No permission for %s. Run `sudo usermod -aG uucp $USER`, "
                        "then log out and back in.", app.devpath);
#endif
        else if (rc == -ENOENT)
            post_status("%s not found. Is the dongle plugged in?", app.devpath);
        else
            post_status("Can't open %s: %s", app.devpath, g_strerror(-rc));
        give_up();
        post_kind(MSG_DONE);
        return NULL;
    }

    while (!atomic_load(&app.cancel)) {
        int live, dtc, clear, active, bcm, latch, knock, idx, arg;
        double hold, bcm_hold;
        char bcm_name[sizeof app.bcm_name];
        uint8_t bcm_item, bcm_value;
        g_mutex_lock(&app.lock);
        live = app.want_live;
        dtc = app.want_dtc;
        clear = app.want_clear;
        active = app.want_active;
        bcm = app.want_bcm;
        latch = app.want_latch;
        knock = app.want_knock;
        idx = app.active_idx;
        arg = app.active_arg;
        hold = app.active_hold;
        g_strlcpy(bcm_name, app.bcm_name, sizeof bcm_name);
        bcm_item = app.bcm_item;
        bcm_value = app.bcm_value;
        bcm_hold = app.bcm_hold_s;
        g_mutex_unlock(&app.lock);

        if (bcm) {
            if (streaming)
                consult_stop(&c, 2.0, NULL);
            streaming = 0;
            if (use_bcm(&c, &cur))
                run_bcm(&c, bcm_name, bcm_item, bcm_value, bcm_hold);
            g_mutex_lock(&app.lock);
            app.want_bcm = 0;
            g_mutex_unlock(&app.lock);
            if (s.error)
                goto fail;
            continue;
        }

        if (clear || active || dtc || live || knock)
            latched = 0;
        if ((clear || active || dtc || live || knock) && !streaming && !use_engine(&c, &cur))
            goto fail;

        if (knock) {
            if (streaming)
                consult_stop(&c, 2.0, NULL);
            streaming = 0;
            read_knock(&c);
            g_mutex_lock(&app.lock);
            app.want_knock = 0;
            g_mutex_unlock(&app.lock);
            if (s.error)
                goto fail;
            continue;
        }

        if (clear) {
            msg_t *m = g_new0(msg_t, 1);
            int cleared, left = 0;
            if (streaming)
                consult_stop(&c, 2.0, NULL);
            streaming = 0;
            m->ndtcs = consult_clear_dtcs(&c, m->dtcs, CONSULT_MAX_DTCS, &cleared);
            g_mutex_lock(&app.lock);
            app.want_clear = 0;
            g_mutex_unlock(&app.lock);
            if (m->ndtcs < 0) {
                g_free(m);
                post_status("Couldn't clear fault codes: %s", link_error(&c));
                goto fail;
            }
            for (int i = 0; i < m->ndtcs; i++)
                left += m->dtcs[i].code != DTC_NO_FAULT;
            if (!cleared)
                post_status("The ECU didn't accept the clear command (%s). Codes re-read below.",
                            c.err);
            else if (left)
                post_status("Clear sent, but %d code(s) are still stored. A fault that's "
                            "still present sets its code again right away.", left);
            else
                post_status("Fault codes cleared.");
            m->kind = MSG_DTCS;
            post(m);
            continue;
        }

        if (active) {
            if (streaming)
                consult_stop(&c, 2.0, NULL);
            streaming = 0;
            run_active(&c, payload, plen, flen, full, idx, arg, hold);
            g_mutex_lock(&app.lock);
            app.want_active = 0;
            g_mutex_unlock(&app.lock);
            if (s.error)
                goto fail;
            continue;
        }

        if (dtc) {
            msg_t *m = g_new0(msg_t, 1);
            if (streaming)
                consult_stop(&c, 2.0, NULL);
            streaming = 0;
            m->ndtcs = consult_dtcs(&c, m->dtcs, CONSULT_MAX_DTCS);
            g_mutex_lock(&app.lock);
            app.want_dtc = 0;
            g_mutex_unlock(&app.lock);
            if (m->ndtcs < 0) {
                g_free(m);
                post_status("Couldn't read fault codes: %s", link_error(&c));
                if (s.error)
                    goto fail;
                continue;
            }
            m->kind = MSG_DTCS;
            post(m);
            continue;
        }
        if (!live) {
            if (!latch)
                break;
            if (streaming) {
                consult_stop(&c, 2.0, NULL);
                streaming = 0;
                post_status("Live data stopped");
            }
            if (!use_bcm(&c, &cur)) {
                g_mutex_lock(&app.lock);
                app.want_latch = 0;
                g_mutex_unlock(&app.lock);
                post_bcm("Couldn't stay connected to the BCM, so the latch is off.");
                if (s.error)
                    goto fail;
                continue;
            }
            if (!latched) {
                latched = 1;
                last_poll = mono();
                post_status("Connected to the BCM and staying connected");
            }
            if (!bcm_keepalive(&c, &last_poll)) {
                if (s.error)
                    goto fail;
                cur = 0;        /* reconnect on the next pass */
                latched = 0;
                post_status("Lost the BCM, reconnecting…");
            }
            continue;
        }

        if (!streaming) {
            if (!consult_command(&c, payload, plen, 2)) {
                if (full && !s.error) {
                    /* 27 registers is inside the ROM's limit but untested on the car */
                    serial_note(&s, "full sensor list refused (%s), using the core list", c.err);
                    full = 0;
                    plen = sensor_payload(payload, full);
                    flen = sensor_frame_len(full);
                    continue;
                }
                post_status("Live data failed: %s", link_error(&c));
                goto fail;
            }
            streaming = 1;
            frames = 0;
            t0 = last_post = mono();
            post_status("Streaming live data from ECU %02X (%s sensor list)", cur,
                        full ? "full" : "core");
        }

        if (consult_read_frame(&c, flen, 1.0, frame) < 0) {
            if (atomic_load(&app.cancel))
                break;
            if (s.error || ++timeouts > 3) {
                post_status("Lost the live data stream: %s", link_error(&c));
                goto fail;
            }
            serial_note(&s, "frame timeout, restarting the stream");
            consult_stop(&c, 0.5, NULL);
            serial_drain(&s, 0.1, 3.0);
            streaming = 0;
            continue;
        }
        frames++;
        if (mono() - last_post >= 0.1) {
            msg_t *m = g_new0(msg_t, 1);
            m->kind = MSG_VALUES;
            sensor_decode(frame, full, m->values);
            m->fps = frames / (mono() - t0);
            post(m);
            last_post = mono();
        }
    }

    if (streaming) {
        consult_stop(&c, 2.0, NULL);
        post_status("Live data stopped");
    }
    serial_close(&s);
    post_kind(MSG_DONE);
    return NULL;

fail:
    give_up();
    serial_close(&s);
    post_kind(MSG_DONE);
    return NULL;
}

/* ---- UI (main thread) ---- */

static void update_buttons(void);

static void start_worker(void)
{
    if (app.thread)
        return;
    g_strlcpy(app.devpath, gtk_editable_get_text(GTK_EDITABLE(app.dev)), sizeof app.devpath);
    if (!app.devpath[0]) {
        post_status("Pick a port, or choose Custom… and type its path.");
        give_up();
        update_buttons();
        return;
    }
    app.thread = g_thread_new("consult", worker, NULL);
}

static void update_buttons(void)
{
    int live, dtc, clear, active, bcm, latch, knock;
    const active_test_t *t = &ACTIVE_TESTS[gtk_drop_down_get_selected(GTK_DROP_DOWN(app.test))];
    g_mutex_lock(&app.lock);
    live = app.want_live;
    dtc = app.want_dtc;
    clear = app.want_clear;
    active = app.want_active;
    bcm = app.want_bcm;
    latch = app.want_latch;
    knock = app.want_knock;
    g_mutex_unlock(&app.lock);
    gtk_widget_set_sensitive(app.knock_btn, !knock && !active && !bcm);
    /* No-op (and no "toggled" signal) unless the worker dropped the latch. */
    gtk_toggle_button_set_active(GTK_TOGGLE_BUTTON(app.bcm_latch), latch);
    /* The window buttons stay sensitive: making a held button insensitive would cancel
     * the press, and the release is what stops the window. */
    for (int i = 0; i < N_BCM_TESTS; i++)
        gtk_widget_set_sensitive(app.bcm_btn[i], !bcm && !active);
    gtk_widget_set_sensitive(app.test_btn, active || !bcm);
    gtk_button_set_label(GTK_BUTTON(app.live_btn), live ? "Stop live data" : "Start live data");
    gtk_widget_set_sensitive(app.dtc_btn, !dtc && !clear && !active);
    gtk_widget_set_sensitive(app.clear_btn, !dtc && !clear && !active);
    gtk_widget_set_sensitive(app.dev_list, app.thread == NULL);
    gtk_widget_set_sensitive(app.dev_scan, app.thread == NULL);
    gtk_widget_set_sensitive(app.dev, app.thread == NULL &&
        gtk_drop_down_get_selected(GTK_DROP_DOWN(app.dev_list)) == app.dev_paths->len - 1);
    gtk_button_set_label(GTK_BUTTON(app.test_btn), active ? "Stop test" : "Run test…");
    gtk_widget_set_sensitive(app.test, !active);
    gtk_widget_set_sensitive(app.test_value, !active && t->has_value);
    gtk_widget_set_sensitive(app.test_hold, !active);
}

static GtkWidget *label(const char *text, float xalign)
{
    GtkWidget *l = gtk_label_new(text);
    gtk_label_set_xalign(GTK_LABEL(l), xalign);
    return l;
}

static void show_dtcs(const msg_t *m)
{
    GtkWidget *child;
    int row = 0;

    while ((child = gtk_widget_get_first_child(app.dtc_grid)))
        gtk_grid_remove(GTK_GRID(app.dtc_grid), child);

    for (int i = 0; i < m->ndtcs; i++) {
        const consult_dtc_t *d = &m->dtcs[i];
        const char *name = dtc_name(d->code);
        char code[8], *markup, starts[48];
        GtkWidget *c;

        if (d->code == DTC_NO_FAULT)
            continue;
        g_snprintf(code, sizeof code, "%02X", d->code);
        markup = g_markup_printf_escaped("<b>%s</b>", code);
        c = label(NULL, 0);
        gtk_label_set_markup(GTK_LABEL(c), markup);
        g_free(markup);
        if (d->starts == 0)
            g_snprintf(starts, sizeof starts, "last seen this start");
        else
            g_snprintf(starts, sizeof starts, "last seen %u start%s ago",
                       d->starts, d->starts == 1 ? "" : "s");

        gtk_grid_attach(GTK_GRID(app.dtc_grid), c, 0, row, 1, 1);
        gtk_grid_attach(GTK_GRID(app.dtc_grid), label(name ? name : "Unknown code", 0),
                        1, row, 1, 1);
        gtk_grid_attach(GTK_GRID(app.dtc_grid), label(starts, 0), 2, row, 1, 1);
        row++;
    }
    if (row == 0)
        gtk_grid_attach(GTK_GRID(app.dtc_grid), label("No fault codes stored.", 0), 0, 0, 3, 1);
}

/* Switch block to the body status panel; NULL blanks it. A set bit is shown in bold
 * (door open, switch pressed…) so changes stand out. */
static void show_body(const uint8_t *b)
{
    char buf[3 * BCM_SWITCH_LEN + 1];

    for (int i = 0; i < N_BCM_INPUTS; i++) {
        const bcm_input_t *in = &BCM_INPUTS[i];
        if (!b) {
            gtk_label_set_text(GTK_LABEL(app.body_val[i]), "–");
        } else if (b[in->byte] & in->mask) {
            char *markup = g_markup_printf_escaped("<b>%s</b>", in->on);
            gtk_label_set_markup(GTK_LABEL(app.body_val[i]), markup);
            g_free(markup);
        } else {
            gtk_label_set_text(GTK_LABEL(app.body_val[i]), in->off);
        }
    }
    if (!b) {
        gtk_label_set_text(GTK_LABEL(app.body_knob), "–");
        gtk_label_set_text(GTK_LABEL(app.body_raw), "–");
        return;
    }
    g_snprintf(buf, sizeof buf, "%02X", b[BCM_WIPER_KNOB]);
    gtk_label_set_text(GTK_LABEL(app.body_knob), buf);
    for (int i = 0; i < BCM_SWITCH_LEN; i++)
        g_snprintf(buf + 3 * i, sizeof buf - 3 * i, i ? " %02X" : "%02X", b[i]);
    gtk_label_set_text(GTK_LABEL(app.body_raw), buf);
}

static gboolean on_msg(gpointer p)
{
    msg_t *m = p;
    char buf[64];

    switch (m->kind) {
    case MSG_STATUS:
        gtk_label_set_text(GTK_LABEL(app.status), m->text);
        break;
    case MSG_VALUES:
        for (int i = 0; i < N_SENSORS; i++) {
            if (isnan(m->values[i]))
                g_snprintf(buf, sizeof buf, "–");
            else
                g_snprintf(buf, sizeof buf, "%.*f %s", SENSORS[i].decimals, m->values[i],
                           SENSORS[i].unit);
            gtk_label_set_text(GTK_LABEL(app.value[i]), buf);
        }
        if (m->fps > 0)
            g_snprintf(buf, sizeof buf, "%.0f frames/s", m->fps);
        else
            g_snprintf(buf, sizeof buf, "snapshot");
        gtk_label_set_text(GTK_LABEL(app.fps), buf);
        break;
    case MSG_DTCS:
        show_dtcs(m);
        break;
    case MSG_ACTIVE:
        gtk_label_set_text(GTK_LABEL(app.test_result), m->text);
        break;
    case MSG_BCM:
        gtk_label_set_text(GTK_LABEL(app.bcm_result), m->text);
        break;
    case MSG_BODY:
        show_body(m->body_ok ? m->body : NULL);
        break;
    case MSG_KNOCK: {
        int ret = m->knock[2] > 127 ? m->knock[2] - 256 : m->knock[2];
        gtk_label_set_text(GTK_LABEL(app.knock_fs), m->knock[0] & 0x80 ? "YES" : "no");
        gtk_label_set_text(GTK_LABEL(app.knock_ok), m->knock[1] & 0x08 ? "yes" : "NO");
        g_snprintf(buf, sizeof buf, "%+d", ret);
        gtk_label_set_text(GTK_LABEL(app.knock_val), buf);
        g_snprintf(buf, sizeof buf, "070D=%02X  0213=%02X  0DB8=%02X",
                   m->knock[0], m->knock[1], m->knock[2]);
        gtk_label_set_text(GTK_LABEL(app.knock_raw), buf);
        break;
    }
    case MSG_DONE:
        if (app.thread)
            g_thread_join(app.thread);
        app.thread = NULL;
        gtk_label_set_text(GTK_LABEL(app.fps), "");
        /* A button may have been pressed while the worker was finishing. */
        g_mutex_lock(&app.lock);
        int again = app.want_live || app.want_dtc || app.want_clear || app.want_active ||
                    app.want_bcm || app.want_latch || app.want_knock;
        g_mutex_unlock(&app.lock);
        if (again && !atomic_load(&app.cancel))
            start_worker();
        break;
    }
    update_buttons();
    g_free(m);
    return G_SOURCE_REMOVE;
}

static void on_live(GtkButton *b, gpointer u)
{
    int live;
    (void)b, (void)u;
    g_mutex_lock(&app.lock);
    live = app.want_live = !app.want_live;
    g_mutex_unlock(&app.lock);
    if (live)
        start_worker();
    update_buttons();
}

static void on_dtc(GtkButton *b, gpointer u)
{
    (void)b, (void)u;
    g_mutex_lock(&app.lock);
    app.want_dtc = 1;
    g_mutex_unlock(&app.lock);
    start_worker();
    update_buttons();
}

static void on_knock(GtkButton *b, gpointer u)
{
    (void)b, (void)u;
    g_mutex_lock(&app.lock);
    app.want_knock = 1;
    g_mutex_unlock(&app.lock);
    start_worker();
    update_buttons();
}

static void on_clear_confirmed(GObject *src, GAsyncResult *res, gpointer u)
{
    (void)u;
    if (gtk_alert_dialog_choose_finish(GTK_ALERT_DIALOG(src), res, NULL) != 1)
        return;
    g_mutex_lock(&app.lock);
    app.want_clear = 1;
    g_mutex_unlock(&app.lock);
    start_worker();
    update_buttons();
}

static void on_clear(GtkButton *b, gpointer u)
{
    const char *buttons[] = {"Cancel", "Clear codes", NULL};
    GtkAlertDialog *d = gtk_alert_dialog_new("Clear the stored fault codes?");
    (void)b, (void)u;
    gtk_alert_dialog_set_detail(d, "This erases the codes from the ECU, so note them down "
                                   "first. A fault that's still present will set its code "
                                   "again. Clearing also resets the OBD-II readiness "
                                   "monitors, which an emissions test checks; they take "
                                   "some driving to complete again.");
    gtk_alert_dialog_set_buttons(d, buttons);
    gtk_alert_dialog_set_cancel_button(d, 0);
    gtk_alert_dialog_set_default_button(d, 0);
    gtk_alert_dialog_choose(d, GTK_WINDOW(app.win), NULL, on_clear_confirmed, NULL);
    g_object_unref(d);
}

static void on_test_confirmed(GObject *src, GAsyncResult *res, gpointer u)
{
    int idx = (int)gtk_drop_down_get_selected(GTK_DROP_DOWN(app.test));
    (void)u;
    if (gtk_alert_dialog_choose_finish(GTK_ALERT_DIALOG(src), res, NULL) != 1)
        return;
    g_mutex_lock(&app.lock);
    app.want_active = 1;
    app.active_idx = idx;
    app.active_arg = gtk_spin_button_get_value_as_int(GTK_SPIN_BUTTON(app.test_value));
    app.active_hold = gtk_spin_button_get_value(GTK_SPIN_BUTTON(app.test_hold));
    g_mutex_unlock(&app.lock);
    gtk_label_set_text(GTK_LABEL(app.test_result), "Reading the engine first…");
    start_worker();
    update_buttons();
}

static void on_test(GtkButton *b, gpointer u)
{
    const active_test_t *t = &ACTIVE_TESTS[gtk_drop_down_get_selected(GTK_DROP_DOWN(app.test))];
    const char *buttons[] = {"Cancel", "Run test", NULL};
    GtkAlertDialog *d;
    int active;
    (void)b, (void)u;

    g_mutex_lock(&app.lock);
    active = app.want_active;
    g_mutex_unlock(&app.lock);
    if (active) {
        atomic_store(&app.abort_test, 1);
        return;
    }
    d = gtk_alert_dialog_new("Run “%s”?", t->name);
    gtk_alert_dialog_set_detail(d, "This changes how the engine runs. The car must be parked, "
                                   "handbrake on, in neutral, with hands clear of the fan "
                                   "and belts.");
    gtk_alert_dialog_set_buttons(d, buttons);
    gtk_alert_dialog_set_cancel_button(d, 0);
    gtk_alert_dialog_set_default_button(d, 0);
    gtk_alert_dialog_choose(d, GTK_WINDOW(app.win), NULL, on_test_confirmed, NULL);
    g_object_unref(d);
}

static void on_test_selected(GObject *o, GParamSpec *ps, gpointer u)
{
    const active_test_t *t = &ACTIVE_TESTS[gtk_drop_down_get_selected(GTK_DROP_DOWN(app.test))];
    (void)o, (void)ps, (void)u;
    gtk_spin_button_set_range(GTK_SPIN_BUTTON(app.test_value), t->min, t->max);
    gtk_spin_button_set_value(GTK_SPIN_BUTTON(app.test_value), t->def);
    gtk_label_set_text(GTK_LABEL(app.test_unit), t->unit);
    update_buttons();
}

static GtkWidget *framed(const char *title, GtkWidget *child);

/* Queue one BCM test, unless one is already queued or running. */
static void request_bcm(const char *name, uint8_t item, uint8_t value, double hold)
{
    int busy;
    atomic_store(&app.abort_bcm, 0);
    g_mutex_lock(&app.lock);
    busy = app.want_bcm || app.want_active;
    if (!busy) {
        app.want_bcm = 1;
        g_strlcpy(app.bcm_name, name, sizeof app.bcm_name);
        app.bcm_item = item;
        app.bcm_value = value;
        app.bcm_hold_s = hold;
    }
    g_mutex_unlock(&app.lock);
    if (busy)
        return;
    gtk_label_set_text(GTK_LABEL(app.bcm_result), "Connecting to the BCM…");
    start_worker();
    update_buttons();
}

static void on_latch(GtkToggleButton *b, gpointer u)
{
    int on = gtk_toggle_button_get_active(b), changed;
    (void)u;
    g_mutex_lock(&app.lock);
    changed = app.want_latch != on;
    app.want_latch = on;
    g_mutex_unlock(&app.lock);
    if (!changed)
        return;
    if (on) {
        gtk_label_set_text(GTK_LABEL(app.bcm_result), "Connecting to the BCM…");
        start_worker();
    } else {
        gtk_label_set_text(GTK_LABEL(app.bcm_result), "Disconnected from the BCM.");
        show_body(NULL);
    }
    update_buttons();
}

static void on_bcm(GtkButton *b, gpointer u)
{
    const bcm_test_t *t = &BCM_TESTS[GPOINTER_TO_INT(u)];
    (void)b;
    request_bcm(t->name, t->item, t->value,
                gtk_spin_button_get_value(GTK_SPIN_BUTTON(app.bcm_hold)));
}

/* u = window * 2 + down */
static void on_window_pressed(GtkGestureDrag *g, double x, double y, gpointer u)
{
    int w = GPOINTER_TO_INT(u) / 2, down = GPOINTER_TO_INT(u) % 2;
    char name[64];
    (void)g, (void)x, (void)y;
    g_snprintf(name, sizeof name, "%s window %s", BCM_WINDOW_NAMES[w], down ? "down" : "up");
    request_bcm(name, BCM_WINDOWS, bcm_window_value(w, down), WINDOW_MAX_HOLD);
}

static void on_window_released(GtkGestureDrag *g, double x, double y, gpointer u)
{
    (void)g, (void)x, (void)y, (void)u;
    atomic_store(&app.abort_bcm, 1);
}

static void on_window_cancel(GtkGesture *g, GdkEventSequence *seq, gpointer u)
{
    (void)g, (void)seq, (void)u;
    atomic_store(&app.abort_bcm, 1);
}

static GtkWidget *window_button(const char *text, int w, int down)
{
    GtkWidget *b = gtk_button_new_with_label(text);
    /* A drag gesture runs from press to release with no time limit (a click gesture
     * can give up on a long press and never report the release). */
    GtkGesture *g = gtk_gesture_drag_new();
    gpointer u = GINT_TO_POINTER(w * 2 + down);

    /* Capture phase: the button's own click gesture would otherwise take the press. */
    gtk_event_controller_set_propagation_phase(GTK_EVENT_CONTROLLER(g), GTK_PHASE_CAPTURE);
    g_signal_connect(g, "drag-begin", G_CALLBACK(on_window_pressed), u);
    g_signal_connect(g, "drag-end", G_CALLBACK(on_window_released), u);
    g_signal_connect(g, "cancel", G_CALLBACK(on_window_cancel), u);
    gtk_widget_add_controller(b, GTK_EVENT_CONTROLLER(g));
    return b;
}

/* Body status: one small frame per BCM_GROUPS entry, wrapping to the window width,
 * then the wiper knob and the raw switch block. Filled by show_body(). */
static GtkWidget *body_status(void)
{
    GtkWidget *box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8), *flow = gtk_flow_box_new();
    GtkWidget *grid = gtk_grid_new();

    gtk_flow_box_set_selection_mode(GTK_FLOW_BOX(flow), GTK_SELECTION_NONE);
    gtk_flow_box_set_homogeneous(GTK_FLOW_BOX(flow), FALSE);
    gtk_flow_box_set_max_children_per_line(GTK_FLOW_BOX(flow), N_BCM_GROUPS);
    gtk_flow_box_set_column_spacing(GTK_FLOW_BOX(flow), 8);
    gtk_flow_box_set_row_spacing(GTK_FLOW_BOX(flow), 8);
    for (int g = 0; g < N_BCM_GROUPS; g++) {
        GtkWidget *ggrid = gtk_grid_new();
        int row = 0;
        gtk_grid_set_column_spacing(GTK_GRID(ggrid), 16);
        gtk_grid_set_row_spacing(GTK_GRID(ggrid), 2);
        for (int i = 0; i < N_BCM_INPUTS; i++) {
            if (strcmp(BCM_INPUTS[i].group, BCM_GROUPS[g]))
                continue;
            app.body_val[i] = label("–", 0);
            gtk_widget_set_size_request(app.body_val[i], 70, -1);
            gtk_grid_attach(GTK_GRID(ggrid), label(BCM_INPUTS[i].name, 0), 0, row, 1, 1);
            gtk_grid_attach(GTK_GRID(ggrid), app.body_val[i], 1, row++, 1, 1);
        }
        gtk_widget_set_valign(ggrid, GTK_ALIGN_START);
        gtk_flow_box_append(GTK_FLOW_BOX(flow), framed(BCM_GROUPS[g], ggrid));
    }
    gtk_box_append(GTK_BOX(box), flow);

    app.body_knob = label("–", 0);
    app.body_raw = label("–", 0);
    gtk_widget_add_css_class(app.body_knob, "numeric");
    gtk_widget_add_css_class(app.body_raw, "numeric");
    gtk_label_set_selectable(GTK_LABEL(app.body_raw), TRUE);
    gtk_grid_set_column_spacing(GTK_GRID(grid), 16);
    gtk_grid_set_row_spacing(GTK_GRID(grid), 2);
    gtk_grid_attach(GTK_GRID(grid), label("Wiper INT knob (01–E4)", 0), 0, 0, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), app.body_knob, 1, 0, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), label("Switch block (5A FF)", 0), 0, 1, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), app.body_raw, 1, 1, 1, 1);
    gtk_box_append(GTK_BOX(box), grid);
    return framed("Body status (while connected)", box);
}

static GtkWidget *bcm_page(void)
{
    GtkWidget *page = gtk_box_new(GTK_ORIENTATION_VERTICAL, 12);
    GtkWidget *wins = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    GtkWidget *wgrid = gtk_grid_new(), *outs = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    GtkWidget *ogrid = gtk_grid_new(), *row = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    GtkWidget *cols = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 12);

    app.bcm_latch = gtk_toggle_button_new_with_label("Stay connected to the BCM "
                                                    "(shows body status)");
    gtk_widget_set_halign(app.bcm_latch, GTK_ALIGN_START);
    g_signal_connect(app.bcm_latch, "toggled", G_CALLBACK(on_latch), NULL);
    gtk_box_append(GTK_BOX(page), app.bcm_latch);

    gtk_grid_set_column_spacing(GTK_GRID(wgrid), 8);
    gtk_grid_set_row_spacing(GTK_GRID(wgrid), 6);
    for (int w = 0; w < N_BCM_WINDOWS; w++) {
        GtkWidget *l = label(BCM_WINDOW_NAMES[w], 0);
        gtk_widget_set_hexpand(l, TRUE);
        gtk_grid_attach(GTK_GRID(wgrid), l, 0, w, 1, 1);
        gtk_grid_attach(GTK_GRID(wgrid), window_button("Up", w, 0), 1, w, 1, 1);
        gtk_grid_attach(GTK_GRID(wgrid), window_button("Down", w, 1), 2, w, 1, 1);
    }
    gtk_box_append(GTK_BOX(wins), wgrid);
    gtk_widget_set_hexpand(wins, TRUE);
    gtk_box_append(GTK_BOX(cols), framed("Power windows", wins));

    gtk_grid_set_column_spacing(GTK_GRID(ogrid), 8);
    gtk_grid_set_row_spacing(GTK_GRID(ogrid), 6);
    gtk_grid_set_column_homogeneous(GTK_GRID(ogrid), TRUE);
    for (int i = 0; i < N_BCM_TESTS; i++) {
        app.bcm_btn[i] = gtk_button_new_with_label(BCM_TESTS[i].name);
        g_signal_connect(app.bcm_btn[i], "clicked", G_CALLBACK(on_bcm), GINT_TO_POINTER(i));
        gtk_grid_attach(GTK_GRID(ogrid), app.bcm_btn[i], i % 2, i / 2, 1, 1);
    }
    app.bcm_hold = gtk_spin_button_new_with_range(1, 10, 1);
    gtk_spin_button_set_value(GTK_SPIN_BUTTON(app.bcm_hold), 1);
    gtk_box_append(GTK_BOX(row), label("Run for", 0));
    gtk_box_append(GTK_BOX(row), app.bcm_hold);
    gtk_box_append(GTK_BOX(row), label("s", 0));
    gtk_box_append(GTK_BOX(outs), ogrid);
    gtk_box_append(GTK_BOX(outs), row);
    gtk_widget_set_hexpand(outs, TRUE);
    gtk_box_append(GTK_BOX(cols), framed("Other outputs", outs));
    gtk_box_append(GTK_BOX(page), cols);
    gtk_box_append(GTK_BOX(page), body_status());

    app.bcm_result = label("", 0);
    gtk_label_set_wrap(GTK_LABEL(app.bcm_result), TRUE);
    gtk_label_set_selectable(GTK_LABEL(app.bcm_result), TRUE);
    gtk_box_append(GTK_BOX(page), app.bcm_result);
    return page;
}

static GtkWidget *framed(const char *title, GtkWidget *child)
{
    GtkWidget *f = gtk_frame_new(title);
    gtk_widget_set_margin_start(child, 12);
    gtk_widget_set_margin_end(child, 12);
    gtk_widget_set_margin_top(child, 8);
    gtk_widget_set_margin_bottom(child, 12);
    gtk_frame_set_child(GTK_FRAME(f), child);
    return f;
}

/* ---- port list ---- */

#ifdef _WIN32

/* COM ports in number order: COM2 before COM10. */
static int by_com_number(gconstpointer a, gconstpointer b)
{
    const char *x = *(char *const *)a, *y = *(char *const *)b;
    long nx = g_ascii_strncasecmp(x, "COM", 3) == 0 ? strtol(x + 3, NULL, 10) : 0;
    long ny = g_ascii_strncasecmp(y, "COM", 3) == 0 ? strtol(y + 3, NULL, 10) : 0;
    return nx != ny ? (nx < ny ? -1 : 1) : g_strcmp0(x, y);
}

/* Every present serial port (Ports class in Device Manager), labelled with its
 * friendly name, e.g. "COM4  (USB Serial Port (COM4), FTDI)". */
static void find_ports(GPtrArray *found, GHashTable *ids)
{
    HDEVINFO set = SetupDiGetClassDevsW(&GUID_DEVCLASS_PORTS, NULL, NULL, DIGCF_PRESENT);
    SP_DEVINFO_DATA dev = {.cbSize = sizeof dev};

    if (set == INVALID_HANDLE_VALUE)
        return;
    for (DWORD i = 0; SetupDiEnumDeviceInfo(set, i, &dev); i++) {
        wchar_t wport[64] = L"", wname[256] = L"", wmfg[128] = L"";
        DWORD type, size = sizeof wport;
        HKEY key = SetupDiOpenDevRegKey(set, &dev, DICS_FLAG_GLOBAL, 0, DIREG_DEV, KEY_READ);
        char *port, *name, *mfg;

        if (key == INVALID_HANDLE_VALUE)
            continue;
        if (RegQueryValueExW(key, L"PortName", NULL, &type, (BYTE *)wport, &size) != ERROR_SUCCESS ||
            type != REG_SZ || _wcsnicmp(wport, L"COM", 3) != 0) {
            RegCloseKey(key);
            continue;       /* LPT ports are in the same class */
        }
        RegCloseKey(key);
        SetupDiGetDeviceRegistryPropertyW(set, &dev, SPDRP_FRIENDLYNAME, NULL, (BYTE *)wname,
                                          sizeof wname - sizeof *wname, NULL);
        SetupDiGetDeviceRegistryPropertyW(set, &dev, SPDRP_MFG, NULL, (BYTE *)wmfg,
                                          sizeof wmfg - sizeof *wmfg, NULL);
        port = g_utf16_to_utf8((gunichar2 *)wport, -1, NULL, NULL, NULL);
        name = g_utf16_to_utf8((gunichar2 *)wname, -1, NULL, NULL, NULL);
        mfg = g_utf16_to_utf8((gunichar2 *)wmfg, -1, NULL, NULL, NULL);
        if (port) {
            g_ptr_array_add(found, g_strdup(port));
            if (name && *name)
                g_hash_table_replace(ids, g_strdup(port),
                                     mfg && *mfg ? g_strdup_printf("%s, %s", name, mfg)
                                                 : g_strdup(name));
        }
        g_free(port);
        g_free(name);
        g_free(mfg);
    }
    SetupDiDestroyDeviceInfoList(set);
    g_ptr_array_sort(found, by_com_number);
}

#else

static int by_name(gconstpointer a, gconstpointer b)
{
    return g_strcmp0(*(char *const *)a, *(char *const *)b);
}

/* /dev/consult (udev link), then /dev/ttyUSB* and /dev/ttyACM*, each labelled with its
 * /dev/serial/by-id name when there is one. */
static void find_ports(GPtrArray *found, GHashTable *ids)
{
    GDir *d;
    const char *e;

    if ((d = g_dir_open("/dev/serial/by-id", 0, NULL))) {
        while ((e = g_dir_read_name(d))) {
            char *link = g_build_filename("/dev/serial/by-id", e, NULL), *real = realpath(link, NULL);
            if (real) {
                g_hash_table_replace(ids, g_strdup(real), g_strdup(e));
                free(real);
            }
            g_free(link);
        }
        g_dir_close(d);
    }
    if ((d = g_dir_open("/dev", 0, NULL))) {
        while ((e = g_dir_read_name(d)))
            if (g_str_has_prefix(e, "ttyUSB") || g_str_has_prefix(e, "ttyACM"))
                g_ptr_array_add(found, g_build_filename("/dev", e, NULL));
        g_dir_close(d);
    }
    g_ptr_array_sort(found, by_name);
    if (g_file_test("/dev/consult", G_FILE_TEST_EXISTS)) {
        char *real = realpath("/dev/consult", NULL);
        g_ptr_array_insert(found, 0, g_strdup("/dev/consult"));
        if (real) {
            g_hash_table_replace(ids, g_strdup("/dev/consult"),
                                 g_strdup_printf("udev link to %s", real));
            free(real);
        }
    }
}

#endif

/* Serial ports that may be the Consult cable (find_ports), each labelled when there is
 * one. Fills app.dev_paths and the drop-down, with "Custom…" last. */
static void scan_ports(void)
{
    GtkStringList *names = gtk_string_list_new(NULL);
    GPtrArray *found = g_ptr_array_new_with_free_func(g_free);
    GHashTable *ids = g_hash_table_new_full(g_str_hash, g_str_equal, g_free, g_free);

    find_ports(found, ids);

    if (app.dev_paths)
        g_ptr_array_unref(app.dev_paths);
    app.dev_paths = g_ptr_array_new_with_free_func(g_free);
    for (guint i = 0; i < found->len; i++) {
        const char *path = g_ptr_array_index(found, i), *id = g_hash_table_lookup(ids, path);
        char *text = id ? g_strdup_printf("%s  (%s)", path, id) : g_strdup(path);
        gtk_string_list_append(names, text);
        g_free(text);
        g_ptr_array_add(app.dev_paths, g_strdup(path));
    }
    gtk_string_list_append(names, "Custom…");
    g_ptr_array_add(app.dev_paths, g_strdup(""));

    gtk_drop_down_set_model(GTK_DROP_DOWN(app.dev_list), G_LIST_MODEL(names));
    gtk_drop_down_set_selected(GTK_DROP_DOWN(app.dev_list), 0);    /* first port, or Custom… */
    g_object_unref(names);
    g_ptr_array_unref(found);
    g_hash_table_unref(ids);
}

/* A port picked: show its path; Custom… makes the path editable. */
static void on_port_selected(GObject *o, GParamSpec *ps, gpointer u)
{
    guint i = gtk_drop_down_get_selected(GTK_DROP_DOWN(app.dev_list));
    int custom;
    (void)o, (void)ps, (void)u;
    if (!app.dev_paths || i >= app.dev_paths->len)
        return;
    custom = i == app.dev_paths->len - 1;
    if (!custom)
        gtk_editable_set_text(GTK_EDITABLE(app.dev), g_ptr_array_index(app.dev_paths, i));
    else if (!gtk_editable_get_text(GTK_EDITABLE(app.dev))[0])
        gtk_editable_set_text(GTK_EDITABLE(app.dev), SERIAL_DEFAULT_DEV);
    gtk_widget_set_sensitive(app.dev, custom && app.thread == NULL);
    if (custom)
        gtk_widget_grab_focus(app.dev);
}

static void on_port_scan(GtkButton *b, gpointer u)
{
    (void)b, (void)u;
    scan_ports();
    gtk_label_set_text(GTK_LABEL(app.status),
                       app.dev_paths->len > 1 ? "Ports rescanned."
                                              : "No serial ports found. Is the cable plugged in?");
}

/* A tab page: padded vertical box. */
static GtkWidget *page_box(void)
{
    GtkWidget *b = gtk_box_new(GTK_ORIENTATION_VERTICAL, 12);
    gtk_widget_set_margin_start(b, 12);
    gtk_widget_set_margin_end(b, 12);
    gtk_widget_set_margin_top(b, 12);
    gtk_widget_set_margin_bottom(b, 12);
    return b;
}

static GtkWidget *engine_page(void)
{
    GtkWidget *page = page_box(), *row = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    GtkWidget *grid = gtk_grid_new();
    int rows = (N_SENSORS + 1) / 2;

    app.live_btn = gtk_button_new_with_label("Start live data");
    g_signal_connect(app.live_btn, "clicked", G_CALLBACK(on_live), NULL);
    app.fps = label("", 1);
    gtk_widget_add_css_class(app.fps, "dim-label");
    gtk_widget_set_hexpand(app.fps, TRUE);
    gtk_box_append(GTK_BOX(row), app.live_btn);
    gtk_box_append(GTK_BOX(row), app.fps);
    gtk_box_append(GTK_BOX(page), row);

    /* Two columns of name / value pairs. */
    gtk_grid_set_column_spacing(GTK_GRID(grid), 24);
    gtk_grid_set_row_spacing(GTK_GRID(grid), 4);
    for (int i = 0; i < N_SENSORS; i++) {
        int col = i / rows * 2, r = i % rows;
        app.value[i] = label("–", 1);
        gtk_widget_add_css_class(app.value[i], "numeric");
        gtk_widget_set_hexpand(app.value[i], TRUE);
        gtk_grid_attach(GTK_GRID(grid), label(SENSORS[i].name, 0), col, r, 1, 1);
        gtk_grid_attach(GTK_GRID(grid), app.value[i], col + 1, r, 1, 1);
    }
    gtk_box_append(GTK_BOX(page), framed("Engine sensors", grid));
    return page;
}

static GtkWidget *codes_page(void)
{
    GtkWidget *page = page_box(), *codes = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    GtkWidget *row = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);

    app.dtc_btn = gtk_button_new_with_label("Read fault codes");
    g_signal_connect(app.dtc_btn, "clicked", G_CALLBACK(on_dtc), NULL);
    app.clear_btn = gtk_button_new_with_label("Clear codes…");
    g_signal_connect(app.clear_btn, "clicked", G_CALLBACK(on_clear), NULL);
    gtk_box_append(GTK_BOX(row), app.dtc_btn);
    gtk_box_append(GTK_BOX(row), app.clear_btn);
    gtk_box_append(GTK_BOX(page), row);

    app.dtc_grid = gtk_grid_new();
    gtk_grid_set_column_spacing(GTK_GRID(app.dtc_grid), 16);
    gtk_grid_set_row_spacing(GTK_GRID(app.dtc_grid), 4);
    gtk_grid_attach(GTK_GRID(app.dtc_grid), label("Not read yet.", 0), 0, 0, 3, 1);
    gtk_box_append(GTK_BOX(codes), app.dtc_grid);
    gtk_box_append(GTK_BOX(page), framed("Stored codes", codes));
    return page;
}

static GtkWidget *tests_page(void)
{
    const char *names[N_ACTIVE_TESTS + 1];
    GtkWidget *page = page_box(), *tests = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    GtkWidget *row = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    GtkWidget *row2 = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);

    for (int i = 0; i < N_ACTIVE_TESTS; i++)
        names[i] = ACTIVE_TESTS[i].name;
    names[N_ACTIVE_TESTS] = NULL;
    app.test = gtk_drop_down_new_from_strings(names);
    gtk_widget_set_hexpand(app.test, TRUE);
    app.test_value = gtk_spin_button_new_with_range(0, 1, 1);
    app.test_unit = label("", 0);
    gtk_box_append(GTK_BOX(row), app.test);
    gtk_box_append(GTK_BOX(row), app.test_value);
    gtk_box_append(GTK_BOX(row), app.test_unit);

    app.test_hold = gtk_spin_button_new_with_range(1, 30, 1);
    gtk_spin_button_set_value(GTK_SPIN_BUTTON(app.test_hold), 5);
    app.test_btn = gtk_button_new_with_label("Run test…");
    gtk_widget_set_hexpand(app.test_btn, TRUE);
    gtk_widget_set_halign(app.test_btn, GTK_ALIGN_END);
    gtk_box_append(GTK_BOX(row2), label("Hold for", 0));
    gtk_box_append(GTK_BOX(row2), app.test_hold);
    gtk_box_append(GTK_BOX(row2), label("s", 0));
    gtk_box_append(GTK_BOX(row2), app.test_btn);

    app.test_result = label("", 0);
    gtk_label_set_wrap(GTK_LABEL(app.test_result), TRUE);
    gtk_label_set_selectable(GTK_LABEL(app.test_result), TRUE);
    gtk_widget_add_css_class(app.test_result, "numeric");

    gtk_box_append(GTK_BOX(tests), row);
    gtk_box_append(GTK_BOX(tests), row2);
    gtk_box_append(GTK_BOX(tests), app.test_result);
    gtk_box_append(GTK_BOX(page), framed("Engine active tests", tests));

    g_signal_connect(app.test, "notify::selected", G_CALLBACK(on_test_selected), NULL);
    g_signal_connect(app.test_btn, "clicked", G_CALLBACK(on_test), NULL);
    return page;
}

static GtkWidget *other_page(void)
{
    GtkWidget *page = page_box(), *knock = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    GtkWidget *grid = gtk_grid_new();
    static const char *rows[] = {"Fail-safe latched", "Knock system OK (second CPU)",
                                 "Knock retard term", "Raw"};
    GtkWidget **vals[] = {&app.knock_fs, &app.knock_ok, &app.knock_val, &app.knock_raw};

    app.knock_btn = gtk_button_new_with_label("Read knock status");
    gtk_widget_set_halign(app.knock_btn, GTK_ALIGN_START);
    g_signal_connect(app.knock_btn, "clicked", G_CALLBACK(on_knock), NULL);
    gtk_box_append(GTK_BOX(knock), app.knock_btn);

    gtk_grid_set_column_spacing(GTK_GRID(grid), 24);
    gtk_grid_set_row_spacing(GTK_GRID(grid), 4);
    for (int i = 0; i < 4; i++) {
        *vals[i] = label("–", 0);
        gtk_widget_add_css_class(*vals[i], "numeric");
        gtk_grid_attach(GTK_GRID(grid), label(rows[i], 0), 0, i, 1, 1);
        gtk_grid_attach(GTK_GRID(grid), *vals[i], 1, i, 1, 1);
    }
    gtk_box_append(GTK_BOX(knock), grid);
    gtk_box_append(GTK_BOX(page), framed("Knock control", knock));
    return page;
}

static void activate(GtkApplication *ga, gpointer u)
{
    GtkWidget *win, *root, *bar, *split, *side, *stack, *body;
    struct { const char *id, *name; GtkWidget *page; } pages[5];
    (void)u;

    win = app.win = gtk_application_window_new(ga);
    gtk_window_set_title(GTK_WINDOW(win), "Consult");
    gtk_window_set_default_size(GTK_WINDOW(win), 1050, 650);

    root = page_box();
    bar = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    app.dev_list = gtk_drop_down_new(NULL, NULL);
    gtk_widget_set_hexpand(app.dev_list, TRUE);
    app.dev = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(app.dev), SERIAL_DEFAULT_DEV);
    gtk_widget_set_size_request(app.dev, 200, -1);
    app.dev_scan = gtk_button_new_with_label("Rescan");
    g_signal_connect(app.dev_list, "notify::selected", G_CALLBACK(on_port_selected), NULL);
    g_signal_connect(app.dev_scan, "clicked", G_CALLBACK(on_port_scan), NULL);
    gtk_box_append(GTK_BOX(bar), label("Port", 0));
    gtk_box_append(GTK_BOX(bar), app.dev_list);
    gtk_box_append(GTK_BOX(bar), app.dev);
    gtk_box_append(GTK_BOX(bar), app.dev_scan);
    scan_ports();
    on_port_selected(NULL, NULL, NULL);
    gtk_box_append(GTK_BOX(root), bar);

    app.status = label("", 0);
    gtk_label_set_wrap(GTK_LABEL(app.status), TRUE);
    gtk_box_append(GTK_BOX(root), app.status);

    body = bcm_page();
    gtk_widget_set_margin_start(body, 12);
    gtk_widget_set_margin_end(body, 12);
    gtk_widget_set_margin_top(body, 12);
    gtk_widget_set_margin_bottom(body, 12);
    pages[0].id = "engine"; pages[0].name = "Engine readouts"; pages[0].page = engine_page();
    pages[1].id = "codes";  pages[1].name = "Fault codes";     pages[1].page = codes_page();
    pages[2].id = "tests";  pages[2].name = "Engine tests";    pages[2].page = tests_page();
    pages[3].id = "bcm";    pages[3].name = "Body (BCM)";      pages[3].page = body;
    pages[4].id = "other";  pages[4].name = "Other";           pages[4].page = other_page();

    /* Left: the page list. Right: the selected page, one at a time, scrolling when it
     * doesn't fit. */
    split = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 0);
    gtk_widget_set_vexpand(split, TRUE);
    stack = gtk_stack_new();
    gtk_widget_set_hexpand(stack, TRUE);
    for (int i = 0; i < 5; i++) {
        GtkWidget *scroll = gtk_scrolled_window_new();
        gtk_scrolled_window_set_child(GTK_SCROLLED_WINDOW(scroll), pages[i].page);
        gtk_stack_add_titled(GTK_STACK(stack), scroll, pages[i].id, pages[i].name);
    }
    gtk_stack_set_visible_child_name(GTK_STACK(stack), "engine");
    side = gtk_stack_sidebar_new();
    gtk_stack_sidebar_set_stack(GTK_STACK_SIDEBAR(side), GTK_STACK(stack));
    gtk_widget_set_size_request(side, 170, -1);
    gtk_box_append(GTK_BOX(split), side);
    gtk_box_append(GTK_BOX(split), gtk_separator_new(GTK_ORIENTATION_VERTICAL));
    gtk_box_append(GTK_BOX(split), stack);
    gtk_box_append(GTK_BOX(root), split);

    gtk_window_set_child(GTK_WINDOW(win), root);
    on_test_selected(NULL, NULL, NULL);
    gtk_window_present(GTK_WINDOW(win));
}

static void on_shutdown(GtkApplication *ga, gpointer u)
{
    (void)ga, (void)u;
    atomic_store(&app.cancel, 1);
    if (app.thread)
        g_thread_join(app.thread);
    app.thread = NULL;
}

int main(int argc, char **argv)
{
    GtkApplication *ga = gtk_application_new("org.openconsult.gui", G_APPLICATION_DEFAULT_FLAGS);
    int rc;
    g_mutex_init(&app.lock);
    g_signal_connect(ga, "activate", G_CALLBACK(activate), NULL);
    g_signal_connect(ga, "shutdown", G_CALLBACK(on_shutdown), NULL);
    rc = g_application_run(G_APPLICATION(ga), argc, argv);
    g_object_unref(ga);
    return rc;
}
