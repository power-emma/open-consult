/* consult-gui: read engine sensors, read and clear fault codes, and run active tests.
 *
 * The serial link runs on a worker thread that opens the port, inits the ECU and
 * then streams live data, reads or clears codes, or runs an active test as asked. It
 * closes the port when there's nothing left to do. Every session appends a raw TX/RX
 * log to logs/YYYY-MM-DD_gui.log. */
#include <errno.h>
#include <gtk/gtk.h>
#include <stdatomic.h>
#include <string.h>

#include "consult.h"
#include "registers.h"

#ifndef LOG_DIR
#define LOG_DIR "logs"
#endif

enum { MSG_STATUS, MSG_VALUES, MSG_DTCS, MSG_ACTIVE, MSG_DONE };

typedef struct {
    int kind;
    char text[256];
    double values[N_SENSORS];
    double fps;
    consult_dtc_t dtcs[CONSULT_MAX_DTCS];
    int ndtcs;
} msg_t;

static struct {
    GtkWidget *win, *dev, *live_btn, *dtc_btn, *clear_btn, *status, *fps, *dtc_grid, *dtc_note;
    GtkWidget *value[N_SENSORS];
    GtkWidget *test, *test_value, *test_unit, *test_hold, *test_btn, *test_result;
    GThread *thread;
    char devpath[256];
    GMutex lock;            /* guards the want_* flags and the active_* parameters */
    int want_live, want_dtc, want_clear, want_active;
    int active_idx, active_arg;
    double active_hold;
    atomic_int cancel;      /* set on quit */
    atomic_int abort_test;  /* "Stop test" pressed */
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

static void post_kind(int kind)
{
    msg_t *m = g_new0(msg_t, 1);
    m->kind = kind;
    post(m);
}

static void give_up(void)
{
    g_mutex_lock(&app.lock);
    app.want_live = app.want_dtc = app.want_clear = app.want_active = 0;
    g_mutex_unlock(&app.lock);
}

static const char *link_error(consult_t *c)
{
    return c->s->error ? "the dongle stopped responding (dropped off USB?)" : c->err;
}

/* Stream a few frames of the sensor list, show them, and return the last one. */
static int snapshot(consult_t *c, const uint8_t *payload, size_t plen, int flen, double *values)
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
        sensor_decode(frame, values);
        memcpy(m->values, values, sizeof m->values);
        post(m);
    }
    return ok;
}

static void run_active(consult_t *c, const uint8_t *payload, size_t plen, int flen,
                       int idx, int arg, double hold)
{
    const active_test_t *t = &ACTIVE_TESTS[idx];
    uint8_t value = active_encode(t, arg), ack = 0;
    double before[N_SENSORS], after[N_SENSORS], held;
    int rc;

    if (!snapshot(c, payload, plen, flen, before)) {
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
    if (!snapshot(c, payload, plen, flen, after)) {
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

static gpointer worker(gpointer unused)
{
    serial_t s;
    consult_t c = {.s = &s, .cancel = &app.cancel};
    uint8_t payload[64], frame[CONSULT_MAX_FRAME], id;
    size_t plen = sensor_payload(payload);
    int flen = sensor_frame_len(), streaming = 0, frames = 0, timeouts = 0;
    double t0 = 0, last_post = 0;
    char log[512], date[16], pn[32];
    GDateTime *now = g_date_time_new_now_local();
    int rc;

    (void)unused;
    g_snprintf(date, sizeof date, "%04d-%02d-%02d", g_date_time_get_year(now),
               g_date_time_get_month(now), g_date_time_get_day_of_month(now));
    g_date_time_unref(now);
    g_mkdir_with_parents(LOG_DIR, 0755);
    g_snprintf(log, sizeof log, "%s/%s_gui.log", LOG_DIR, date);

    rc = serial_open(&s, app.devpath, log);
    if (rc < 0) {
        if (rc == -EACCES)
            post_status("No permission for %s. Run `sudo usermod -aG uucp $USER`, "
                        "then log out and back in.", app.devpath);
        else if (rc == -ENOENT)
            post_status("%s not found. Is the dongle plugged in?", app.devpath);
        else
            post_status("Can't open %s: %s", app.devpath, g_strerror(-rc));
        give_up();
        post_kind(MSG_DONE);
        return NULL;
    }

    post_status("Connecting to the ECU…");
    if (!consult_init(&c, CONSULT_ENGINE_IDS, 2, 3, &id)) {
        if (!atomic_load(&app.cancel))
            post_status(s.error ? "Connection failed: %s"
                                : "No reply from the ECU (%s). Is the key at ON and the "
                                  "dongle plugged into the car?", link_error(&c));
        goto fail;
    }
    if (consult_part_number(&c, pn, sizeof pn))
        post_status("Connected: ECU %02X, %s", id, pn);
    else
        post_status("Connected: ECU %02X", id);

    while (!atomic_load(&app.cancel)) {
        int live, dtc, clear, active, idx, arg;
        double hold;
        g_mutex_lock(&app.lock);
        live = app.want_live;
        dtc = app.want_dtc;
        clear = app.want_clear;
        active = app.want_active;
        idx = app.active_idx;
        arg = app.active_arg;
        hold = app.active_hold;
        g_mutex_unlock(&app.lock);

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
            run_active(&c, payload, plen, flen, idx, arg, hold);
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
        if (!live)
            break;

        if (!streaming) {
            if (!consult_command(&c, payload, plen, 2)) {
                post_status("Live data failed: %s", link_error(&c));
                goto fail;
            }
            streaming = 1;
            frames = 0;
            t0 = last_post = mono();
            post_status("Streaming live data from ECU %02X", id);
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
            sensor_decode(frame, m->values);
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

static void start_worker(void)
{
    if (app.thread)
        return;
    g_strlcpy(app.devpath, gtk_editable_get_text(GTK_EDITABLE(app.dev)), sizeof app.devpath);
    app.thread = g_thread_new("consult", worker, NULL);
}

static void update_buttons(void)
{
    int live, dtc, clear, active;
    const active_test_t *t = &ACTIVE_TESTS[gtk_drop_down_get_selected(GTK_DROP_DOWN(app.test))];
    g_mutex_lock(&app.lock);
    live = app.want_live;
    dtc = app.want_dtc;
    clear = app.want_clear;
    active = app.want_active;
    g_mutex_unlock(&app.lock);
    gtk_button_set_label(GTK_BUTTON(app.live_btn), live ? "Stop live data" : "Start live data");
    gtk_widget_set_sensitive(app.dtc_btn, !dtc && !clear && !active);
    gtk_widget_set_sensitive(app.clear_btn, !dtc && !clear && !active);
    gtk_widget_set_sensitive(app.dev, app.thread == NULL);
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
    GDateTime *now = g_date_time_new_now_local();
    char *when = g_date_time_format(now, "%H:%M:%S");
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

    {
        char *note = g_strdup_printf("Read at %s. Names are from Nissan's 2-digit code list.",
                                     when);
        gtk_label_set_text(GTK_LABEL(app.dtc_note), note);
        g_free(note);
    }
    g_free(when);
    g_date_time_unref(now);
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
    case MSG_DONE:
        if (app.thread)
            g_thread_join(app.thread);
        app.thread = NULL;
        gtk_label_set_text(GTK_LABEL(app.fps), "");
        /* A button may have been pressed while the worker was finishing. */
        g_mutex_lock(&app.lock);
        int again = app.want_live || app.want_dtc || app.want_clear || app.want_active;
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

static void activate(GtkApplication *ga, gpointer u)
{
    GtkWidget *win, *root, *bar, *cols, *sensors, *grid, *codes, *right;
    (void)u;

    win = app.win = gtk_application_window_new(ga);
    gtk_window_set_title(GTK_WINDOW(win), "Consult");
    gtk_window_set_default_size(GTK_WINDOW(win), 760, 480);

    root = gtk_box_new(GTK_ORIENTATION_VERTICAL, 12);
    gtk_widget_set_margin_start(root, 12);
    gtk_widget_set_margin_end(root, 12);
    gtk_widget_set_margin_top(root, 12);
    gtk_widget_set_margin_bottom(root, 12);

    bar = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    app.dev = gtk_entry_new();
    gtk_editable_set_text(GTK_EDITABLE(app.dev),
                          g_file_test("/dev/consult", G_FILE_TEST_EXISTS) ? "/dev/consult"
                                                                          : "/dev/ttyUSB0");
    gtk_widget_set_hexpand(app.dev, TRUE);
    app.live_btn = gtk_button_new_with_label("Start live data");
    app.dtc_btn = gtk_button_new_with_label("Read fault codes");
    g_signal_connect(app.live_btn, "clicked", G_CALLBACK(on_live), NULL);
    g_signal_connect(app.dtc_btn, "clicked", G_CALLBACK(on_dtc), NULL);
    gtk_box_append(GTK_BOX(bar), label("Port", 0));
    gtk_box_append(GTK_BOX(bar), app.dev);
    gtk_box_append(GTK_BOX(bar), app.live_btn);
    gtk_box_append(GTK_BOX(bar), app.dtc_btn);
    gtk_box_append(GTK_BOX(root), bar);

    app.status = label("Key at ON (or engine running), then pick an action.", 0);
    gtk_label_set_wrap(GTK_LABEL(app.status), TRUE);
    gtk_box_append(GTK_BOX(root), app.status);

    cols = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 12);
    gtk_widget_set_vexpand(cols, TRUE);

    sensors = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    grid = gtk_grid_new();
    gtk_grid_set_column_spacing(GTK_GRID(grid), 24);
    gtk_grid_set_row_spacing(GTK_GRID(grid), 4);
    for (int i = 0; i < N_SENSORS; i++) {
        app.value[i] = label("–", 1);
        gtk_widget_add_css_class(app.value[i], "numeric");
        gtk_widget_set_hexpand(app.value[i], TRUE);
        gtk_grid_attach(GTK_GRID(grid), label(SENSORS[i].name, 0), 0, i, 1, 1);
        gtk_grid_attach(GTK_GRID(grid), app.value[i], 1, i, 1, 1);
    }
    app.fps = label("", 1);
    gtk_widget_add_css_class(app.fps, "dim-label");
    gtk_box_append(GTK_BOX(sensors), grid);
    gtk_box_append(GTK_BOX(sensors), app.fps);
    gtk_box_append(GTK_BOX(cols), framed("Engine sensors", sensors));

    codes = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    gtk_widget_set_hexpand(codes, TRUE);
    app.dtc_grid = gtk_grid_new();
    gtk_grid_set_column_spacing(GTK_GRID(app.dtc_grid), 16);
    gtk_grid_set_row_spacing(GTK_GRID(app.dtc_grid), 4);
    gtk_grid_attach(GTK_GRID(app.dtc_grid), label("Not read yet.", 0), 0, 0, 3, 1);
    app.dtc_note = label("", 0);
    gtk_label_set_wrap(GTK_LABEL(app.dtc_note), TRUE);
    gtk_widget_add_css_class(app.dtc_note, "dim-label");
    app.clear_btn = gtk_button_new_with_label("Clear codes…");
    gtk_widget_set_halign(app.clear_btn, GTK_ALIGN_END);
    g_signal_connect(app.clear_btn, "clicked", G_CALLBACK(on_clear), NULL);
    gtk_box_append(GTK_BOX(codes), app.dtc_grid);
    gtk_box_append(GTK_BOX(codes), app.dtc_note);
    gtk_box_append(GTK_BOX(codes), app.clear_btn);
    right = gtk_box_new(GTK_ORIENTATION_VERTICAL, 12);
    gtk_widget_set_hexpand(right, TRUE);
    gtk_box_append(GTK_BOX(right), framed("Fault codes", codes));

    {
        const char *names[N_ACTIVE_TESTS + 1];
        GtkWidget *tests = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
        GtkWidget *row = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
        GtkWidget *row2 = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
        GtkWidget *warn;

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

        warn = label("Changes how the engine runs. Parked, handbrake on, neutral. "
                     "Turning the key off always ends a test.", 0);
        gtk_label_set_wrap(GTK_LABEL(warn), TRUE);
        gtk_widget_add_css_class(warn, "dim-label");
        app.test_result = label("", 0);
        gtk_label_set_wrap(GTK_LABEL(app.test_result), TRUE);
        gtk_label_set_selectable(GTK_LABEL(app.test_result), TRUE);
        gtk_widget_add_css_class(app.test_result, "numeric");

        gtk_box_append(GTK_BOX(tests), row);
        gtk_box_append(GTK_BOX(tests), row2);
        gtk_box_append(GTK_BOX(tests), warn);
        gtk_box_append(GTK_BOX(tests), app.test_result);
        gtk_box_append(GTK_BOX(right), framed("Active tests", tests));

        g_signal_connect(app.test, "notify::selected", G_CALLBACK(on_test_selected), NULL);
        g_signal_connect(app.test_btn, "clicked", G_CALLBACK(on_test), NULL);
    }
    gtk_box_append(GTK_BOX(cols), right);

    gtk_box_append(GTK_BOX(root), cols);
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
