/* Offline A32 calibration viewer. No serial commands or ROM writes. */
static GtkWidget *rom_text, *rom_info, *rom_origin;

typedef struct { int start, end, shade; } rom_cell_t;

/* User-selected display rule; ECU semantics remain provisional. */
static int rom_timing_value(unsigned char raw)
{
    int value = raw & 127;
    return value >= 118 ? value - 128 : value;
}

/* Offsets are Unicode character offsets, as required by GtkTextBuffer. */
static void rom_append_cell(GString *text, GArray *cells, int value,
                            int low, int high, gboolean hex)
{
    rom_cell_t cell = { .start = g_utf8_strlen(text->str, -1) };
    if (hex && value < 0)
        g_string_append_printf(text, "-%02X ", (unsigned int)-value);
    else
        g_string_append_printf(text, hex ? " %02X " : " %3d ", value);
    cell.end = g_utf8_strlen(text->str, -1);
    cell.shade = high > low ? (value - low) * 100 / (high - low) : 0;
    g_array_append_val(cells, cell);
}

static void rom_color_cells(GtkTextBuffer *buffer, GArray *cells, gboolean offsets)
{
    GtkTextTagTable *table = gtk_text_buffer_get_tag_table(buffer);
    for (guint i = 0; i < cells->len; i++) {
        rom_cell_t cell = g_array_index(cells, rom_cell_t, i);
        char name[24];
        g_snprintf(name, sizeof name, "%s-heat-%d", offsets ? "fuel" : "rom", cell.shade);
        GtkTextTag *tag = gtk_text_tag_table_lookup(table, name);
        if (!tag) {
            double t = cell.shade / 100.0;
            GdkRGBA color = { .red = 0.35 + 0.60 * MIN(1.0, 2*t),
                             .green = 0.85 - 0.50 * MAX(0.0, 2*t-1),
                             .blue = 0.35, .alpha = 1.0 };
            if (offsets) {
                color.red = 0.16 + 0.33 * t;
                color.green = 0.34 - 0.15 * t;
                color.blue = 0.68 + 0.05 * t;
            }
            tag = gtk_text_buffer_create_tag(buffer, name, "background-rgba", &color,
                                            "foreground", offsets ? "#ffffff" : "#111111", NULL);
        }
        GtkTextIter start, end;
        gtk_text_buffer_get_iter_at_offset(buffer, &start, cell.start);
        gtk_text_buffer_get_iter_at_offset(buffer, &end, cell.end);
        gtk_text_buffer_apply_tag(buffer, tag, &start, &end);
    }
}

static void rom_opened(GtkNativeDialog *dialog, int response, gpointer unused)
{
    (void)unused;
    if (response == GTK_RESPONSE_ACCEPT) {
        GFile *file = gtk_file_chooser_get_file(GTK_FILE_CHOOSER(dialog));
        char *data = NULL;
        gsize size = 0;
        GError *error = NULL;
        GtkTextBuffer *buffer = gtk_text_view_get_buffer(GTK_TEXT_VIEW(rom_text));
        gtk_text_buffer_set_text(buffer, "", -1);
        if (!g_file_load_contents(file, NULL, &data, &size, NULL, &error)) {
            gtk_label_set_text(GTK_LABEL(rom_info), error->message);
        } else {
            guint selected = gtk_drop_down_get_selected(GTK_DROP_DOWN(rom_origin));
            gsize base = selected == 1 ? 0 : 0x1000;
            gboolean valid = selected == 0 ? (size == 0x10000 || size == 0xf000 || size == 0x7000)
                                             : (size >= 0x2000 - base && size <= 0x10000 - base);
            if (selected == 0 && size == 0x10000) base = 0;
            if (!valid) {
                gtk_label_set_text(GTK_LABEL(rom_info),
                    "Unsupported size. Auto accepts 64 KiB full images or 60/28 KiB dumps starting at 0x1000. Select an explicit origin for other contiguous dumps.");
            } else {
                static const struct { const char *name; guint address, axis1, axis2; } maps[] = {
                    {"Normal fuel", 0x1700, 0x1900, 0x1910},
                    {"Knock fuel", 0x1800, 0x1900, 0x1910},
                    {"Normal timing", 0x1d00, 0x1f00, 0x1f10},
                    {"Knock timing", 0x1e00, 0x1f00, 0x1f10},
                    {"Volumetric efficiency", 0x1400, 0x1500, 0x1510}
                };
                GArray *cells = g_array_new(FALSE, FALSE, sizeof(rom_cell_t));
                GString *text = g_string_new(
                    "TIMING — provisional display, not a verified firmware decode.\n"
                    "Rows: RPM; columns: internal load index (load_code / 256).\n"
                    "Cells: low 7 bits; values >= 118 subtract 128. Candidate degrees BTDC (provisional).\n"
                    "Bit 7 meaning, exact interpolation and table selection remain unverified.\n"
                    "Green = lower value; yellow = middle; red = higher. Colors do not indicate safety.\n\n");
                /* Share a scale between both timing maps for direct comparison. */
                int timing_low = 127, timing_high = -128;
                for (guint a = 0x1d00; a < 0x1f00; a++) {
                    int value = rom_timing_value((unsigned char)data[a-base]);
                    timing_low = MIN(timing_low, value); timing_high = MAX(timing_high, value);
                }
                for (guint m = 2; m <= 3; m++) {
                    g_string_append_printf(text, "%s — 0x%04X (interpreted)\n RPM / load ", maps[m].name, maps[m].address);
                    for (int c = 0; c < 16; c++)
                        g_string_append_printf(text, " %3u ", (unsigned char)data[0x1f10-base+c]);
                    g_string_append_c(text, '\n');
                    for (int r = 0; r < 16; r++) {
                        g_string_append_printf(text, " %5u RPM  ", 50u*(unsigned char)data[0x1f00-base+r]);
                        for (int c = 0; c < 16; c++)
                            rom_append_cell(text, cells, rom_timing_value((unsigned char)data[maps[m].address-base+r*16+c]),
                                            timing_low, timing_high, FALSE);
                        g_string_append_c(text, '\n');
                    }
                    g_string_append_c(text, '\n');
                }
                g_string_append(text,
                    "FUEL — provisional axis labels; cells remain raw hexadecimal coefficients.\n"
                    "Rows: RPM (axis byte x 50); columns: candidate internal load index.\n"
                    "Fuel axis orientation/conversion is not independently verified by the timing traces.\n"
                    "Load is not throttle percent. Cell values are not AFR or override percentages.\n\n");
                int fuel_low = 255, fuel_high = 0;
                for (guint a = 0x1700; a < 0x1900; a++) {
                    int value = (unsigned char)data[a-base];
                    fuel_low = MIN(fuel_low, value); fuel_high = MAX(fuel_high, value);
                }
                for (guint m = 0; m < 2; m++) {
                    g_string_append_printf(text, "%s — 0x%04X (provisional axes; HEX cells)\n RPM / load ", maps[m].name, maps[m].address);
                    for (int c = 0; c < 16; c++)
                        g_string_append_printf(text, "%3u ", (unsigned char)data[maps[m].axis1-base+c]);
                    g_string_append_c(text, '\n');
                    for (int r = 0; r < 16; r++) {
                        g_string_append_printf(text, " %5u RPM  ", 50u*(unsigned char)data[maps[m].axis2-base+r]);
                        for (int c = 0; c < 16; c++)
                            rom_append_cell(text, cells, (unsigned char)data[maps[m].address-base+r*16+c],
                                            fuel_low, fuel_high, TRUE);
                        g_string_append_c(text, '\n');
                    }
                    g_string_append_c(text, '\n');
                }
                g_string_append(text, "HEX TABLES — timing uses the same provisional conversion as decimal.\n"
                                      "Negative timing is signed hex magnitude (e.g. -08 = -8 decimal).\n"
                                      "Fuel/VE cells and axis bytes remain raw. Timing shares the decimal color scale.\n\n");
                for (guint m = 0; m < G_N_ELEMENTS(maps); m++) {
                    gboolean timing = m == 2 || m == 3;
                    int low = 255, high = -128;
                    for (int i = 0; i < 256; i++) {
                        int value = (unsigned char)data[maps[m].address-base+i];
                        if (timing) value = rom_timing_value(value);
                        low = MIN(low, value); high = MAX(high, value);
                    }
                    if (timing) { low = timing_low; high = timing_high; }
                    g_string_append_printf(text, "%s — 0x%04X (16 × 16, %s HEX cells)\n       ",
                                           maps[m].name, maps[m].address,
                                           timing ? "interpreted" : "raw");
                    for (int c = 0; c < 16; c++) g_string_append_printf(text, " %02X ", c);
                    g_string_append_c(text, '\n');
                    for (int r = 0; r < 16; r++) {
                        g_string_append_printf(text, "row %02X ", r);
                        for (int c = 0; c < 16; c++) {
                            int value = (unsigned char)data[maps[m].address - base + r * 16 + c];
                            rom_append_cell(text, cells, timing ? rom_timing_value(value) : value, low, high, TRUE);
                        }
                        g_string_append_c(text, '\n');
                    }
                    guint axes[] = {maps[m].axis1, maps[m].axis2};
                    for (int a = 0; a < 2; a++) {
                        g_string_append_printf(text, "Axis bytes at 0x%04X:", axes[a]);
                        for (int c = 0; c < 16; c++) g_string_append_printf(text, " %02X", (unsigned char)data[axes[a] - base + c]);
                        g_string_append_c(text, '\n');
                    }
                    g_string_append_c(text, '\n');
                }
                gtk_text_buffer_set_text(buffer, text->str, -1);
                rom_color_cells(buffer, cells, FALSE);
                g_array_unref(cells);
                g_string_free(text, TRUE);
                char *name = g_file_get_basename(file);
                char *info = g_strdup_printf("%s — %zu bytes, origin 0x%04zX. A32/PLMS candidate layout; compatibility is not auto-detected.", name, size, base);
                gtk_label_set_text(GTK_LABEL(rom_info), info);
                g_free(info); g_free(name);
            }
        }
        g_clear_error(&error); g_free(data); g_object_unref(file);
    }
    g_object_unref(dialog);
}

static void rom_open(GtkButton *button, gpointer unused)
{
    (void)button; (void)unused;
    GtkFileChooserNative *dialog = gtk_file_chooser_native_new("Open ROM dump",
        GTK_WINDOW(app.win), GTK_FILE_CHOOSER_ACTION_OPEN, "Open", "Cancel");
    g_signal_connect(dialog, "response", G_CALLBACK(rom_opened), NULL);
    gtk_native_dialog_show(GTK_NATIVE_DIALOG(dialog));
}

static GtkWidget *rom_page(void)
{
    GtkWidget *page = page_box();
    GtkWidget *row = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    GtkWidget *open = gtk_button_new_with_label("Open ROM dump…");
    const char *origins[] = {"Auto origin (known dump sizes)", "Origin 0x0000", "Origin 0x1000", NULL};
    rom_origin = gtk_drop_down_new_from_strings(origins);
    g_signal_connect(open, "clicked", G_CALLBACK(rom_open), NULL);
    gtk_box_append(GTK_BOX(row), open);
    gtk_box_append(GTK_BOX(row), rom_origin);
    gtk_box_append(GTK_BOX(page), row);
    GtkWidget *note = label("A32 / PLMS layout reference. Timing uses provisional decoding (low 7 bits; values >= 118 subtract 128); fuel axes are provisional, fuel cells and VE remain raw. Earlier ROM layouts may differ. Cell colors show numeric magnitude, not safe tuning settings.", 0);
    gtk_label_set_wrap(GTK_LABEL(note), TRUE);
    gtk_box_append(GTK_BOX(page), note);
    rom_info = label("Choose a contiguous ROM dump. Viewing is offline and read-only.", 0);
    gtk_label_set_wrap(GTK_LABEL(rom_info), TRUE);
    gtk_box_append(GTK_BOX(page), rom_info);
    rom_text = gtk_text_view_new();
    gtk_text_view_set_editable(GTK_TEXT_VIEW(rom_text), FALSE);
    gtk_text_view_set_monospace(GTK_TEXT_VIEW(rom_text), TRUE);
    gtk_text_view_set_cursor_visible(GTK_TEXT_VIEW(rom_text), FALSE);
    gtk_box_append(GTK_BOX(page), rom_text);
    return page;
}
