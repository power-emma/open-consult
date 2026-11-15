#include <math.h>

#include "registers.h"

/* 1998 Maxima (ID ED, 23710-2L904). Left out on purpose: 17 (AAC) is unsupported and
 * would fail the whole command. 08 (coolant) only streams alongside other registers,
 * which it always does here. Sensors marked extra are only in the full list; their
 * scalings marked PLMS come from the 1999 A32 notes and are unchecked on this car
 * (ROM_ANALYSIS.md §2). */
const sensor_t SENSORS[N_SENSORS] = {
    {"Engine speed",        {0x00, 0x01}, 2, 12.5,   0, 0, "rpm",   0},
    {"Coolant temp",        {0x08},       1, 1,    -50, 0, "°C",    0},
    {"Intake air temp",     {0x11},       1, 1,    -50, 0, "°C",    0},
    {"Battery",             {0x0C},       1, 0.08,   0, 2, "V",     0},
    {"Throttle position",   {0x0D},       1, 20,     0, 0, "mV",    0},
    {"Mass air flow",       {0x04, 0x05}, 2, 5,      0, 0, "mV",    0},
    {"O2 sensor LH",        {0x09},       1, 10,     0, 0, "mV",    0},
    {"O2 sensor RH",        {0x0A},       1, 10,     0, 0, "mV",    0},
    {"Vehicle speed",       {0x0B},       1, 2,      0, 0, "km/h",  0},
    {"Injector LH",         {0x14, 0x15}, 2, 0.01,   0, 2, "ms",    0},
    {"Injector RH",         {0x22, 0x23}, 2, 0.01,   0, 2, "ms",    0},
    {"Ignition timing",     {0x16},       1, -1,   110, 0, "°BTDC", 0},
    {"A/F alpha LH",        {0x1A},       1, 1,      0, 0, "%",     0},
    {"A/F alpha RH",        {0x1B},       1, 1,      0, 0, "%",     0},
    {"Self-learn LH",       {0x1C},       1, 1,      0, 0, "%",     1},
    {"Self-learn RH",       {0x1D},       1, 1,      0, 0, "%",     1},
    {"IACV-AAC valve",      {0x18},       1, 1,      0, 0, "step",  1},
    {"Purge volume valve",  {0x29},       1, 1,      0, 0, "step",  1},
    {"Load (CAL/LD)",     {0x33, 0x34}, 2, 1.0 / 256, 0, 1, "%",  1},
    {"Absolute throttle", {0x37},       1, 1 / 2.55, 0, 0, "%",   1},
    {"Rear O2 sensor",    {0x35},       1, 10,     0, 0, "mV",    1},
    {"Abs. pressure sensor", {0x4A},    1, 20,     0, 0, "mV",    1},
};

size_t sensor_payload(uint8_t *out, int full)
{
    size_t o = 0;
    for (int i = 0; i < N_SENSORS; i++) {
        if (SENSORS[i].extra && !full)
            continue;
        for (int j = 0; j < SENSORS[i].nregs; j++) {
            out[o++] = 0x5A;
            out[o++] = SENSORS[i].regs[j];
        }
    }
    return o;
}

int sensor_frame_len(int full)
{
    int n = 0;
    for (int i = 0; i < N_SENSORS; i++)
        if (full || !SENSORS[i].extra)
            n += SENSORS[i].nregs;
    return n;
}

void sensor_decode(const uint8_t *frame, int full, double *values)
{
    for (int i = 0; i < N_SENSORS; i++) {
        unsigned raw = 0;
        if (SENSORS[i].extra && !full) {
            values[i] = NAN;
            continue;
        }
        for (int j = 0; j < SENSORS[i].nregs; j++)
            raw = (raw << 8) | *frame++;
        values[i] = raw * SENSORS[i].scale + SENSORS[i].offset;
    }
}

/* D1 code byte -> P-code and name for this ECU (23710-2L904), from the ROM's slot tables
 * ($9E0E code bytes, $E086 P-codes) and the FSM DTC index. Generated together with
 * consult/dtcs.py; see ROM_ANALYSIS.md. */
static const struct { uint8_t code; const char *name; } DTCS[] = {
    {0x11, "P0340 Camshaft position sensor (PHASE) circuit"},
    {0x12, "P0100 Mass air flow sensor circuit"},
    {0x13, "P0115 Coolant temp sensor circuit"},
    {0x14, "P0500 Vehicle speed sensor circuit"},
    {0x16, "P1210 (generic slot, not used on this car)"},
    {0x19, "P1230 (generic slot, not used on this car)"},
    {0x1A, "P1125 (generic slot, not used on this car)"},
    {0x1B, "P1447 EVAP purge flow monitoring"},
    {0x1C, "P1165 (generic slot, not used on this car)"},
    {0x1D, "P1443 (generic slot, not used on this car)"},
    {0x1E, "P0172 Fuel system too rich B1 (right bank)"},
    {0x1F, "P0171 Fuel system too lean B1 (right bank)"},
    {0x21, "P1320 Ignition signal, primary circuit"},
    {0x22, "P1200 (generic slot, not used on this car)"},
    {0x23, "P0510 Closed throttle position switch circuit"},
    {0x25, "P0505 IACV-AAC valve circuit"},
    {0x26, "P0235 (generic slot, not used on this car)"},
    {0x29, "P0175 Fuel system too rich B2 (left bank)"},
    {0x2A, "P0174 Fuel system too lean B2 (left bank)"},
    {0x2B, "P1910 (generic slot, not used on this car)"},
    {0x2C, "P0330 (generic slot, not used on this car)"},
    {0x2D, "P1440 EVAP small leak"},
    {0x2E, "P1444 EVAP canister purge volume control valve"},
    {0x2F, "P1446 EVAP canister vent control valve (stuck closed)"},
    {0x31, "P0605 ECM"},
    {0x32, "P0400 EGR system function"},
    {0x33, "P0150 Front O2 sensor B2 (left bank) circuit"},
    {0x34, "P0325 Knock sensor circuit"},
    {0x35, "P1401 EGR temp sensor circuit"},
    {0x36, "P0402 EGRC-BPT valve function"},
    {0x37, "P1148 Closed loop control B1 (right bank)"},
    {0x38, "P1168 Closed loop control B2 (left bank)"},
    {0x39, "P1448 EVAP canister vent control valve (stuck open)"},
    {0x3B, "P1491 Vacuum cut valve bypass valve"},
    {0x3C, "P1493 EVAP canister purge control valve and solenoid valve"},
    {0x3D, "P0158 (generic slot, not used on this car)"},
    {0x3E, "P0157 (generic slot, not used on this car)"},
    {0x3F, "P0160 (generic slot, not used on this car)"},
    {0x41, "P0110 Intake air temp sensor circuit"},
    {0x42, "P0180 Tank fuel temp sensor circuit"},
    {0x43, "P0120 Throttle position sensor circuit"},
    {0x46, "P1120 (generic slot, not used on this car)"},
    {0x47, "P1335 Crankshaft position sensor (REF) circuit"},
    {0x49, "P0153 Front O2 sensor B2 (left bank) slow response"},
    {0x4A, "P0152 Front O2 sensor B2 (left bank) rich shift"},
    {0x4B, "P0151 Front O2 sensor B2 (left bank) lean shift"},
    {0x4C, "P0154 Front O2 sensor B2 (left bank) high voltage"},
    {0x4D, "P0133 Front O2 sensor B1 (right bank) slow response"},
    {0x4E, "P0132 Front O2 sensor B1 (right bank) rich shift"},
    {0x4F, "P0131 Front O2 sensor B1 (right bank) lean shift"},
    {0x51, "P1200 (generic slot, not used on this car)"},
    {0x52, "P1065 (generic slot, not used on this car)"},
    {0x53, "P0130 Front O2 sensor B1 (right bank) circuit"},
    {0x54, "P0600 A/T communication line"},
    {0x55, "No malfunction"},
    {0x59, "P0134 Front O2 sensor B1 (right bank) high voltage"},
    {0x5A, "P0138 Rear O2 sensor maximum voltage"},
    {0x5B, "P0137 Rear O2 sensor minimum voltage"},
    {0x5C, "P0140 Rear O2 sensor high voltage"},
    {0x5D, "P1776 (generic slot, not used on this car)"},
    {0x5E, "P1402 EGR system (early flow)"},
    {0x61, "P0308 (generic slot, not used on this car)"},
    {0x62, "P0307 (generic slot, not used on this car)"},
    {0x63, "P0306 Cylinder 6 misfire"},
    {0x64, "P0305 Cylinder 5 misfire"},
    {0x65, "P0304 Cylinder 4 misfire"},
    {0x66, "P0303 Cylinder 3 misfire"},
    {0x67, "P0302 Cylinder 2 misfire"},
    {0x68, "P0301 Cylinder 1 misfire"},
    {0x71, "P0300 Multiple cylinder misfire"},
    {0x72, "P0420 Catalyst efficiency"},
    {0x73, "P0430 (generic slot, not used on this car)"},
    {0x74, "P0450 EVAP system pressure sensor"},
    {0x75, "P0440 EVAP small leak"},
    {0x76, "P0170 (generic slot, not used on this car)"},
    {0x77, "P0139 Rear O2 sensor slow response"},
    {0x78, "P0159 (generic slot, not used on this car)"},
    {0x81, "P1490 Vacuum cut valve bypass valve circuit"},
    {0x82, "P0335 Crankshaft position sensor (POS) circuit"},
    {0x83, "P0105 Absolute pressure sensor circuit"},
    {0x84, "P1605 A/T diagnosis communication line"},
    {0x85, "P1110 (generic slot, not used on this car)"},
    {0x86, "P0173 (generic slot, not used on this car)"},
    {0x87, "P1492 EVAP canister purge control solenoid valve circuit"},
    {0x88, "P0505 IACV-AAC valve circuit"},
    {0x91, "P0135 Front O2 sensor heater B1 (right bank)"},
    {0x92, "P0141 Rear O2 sensor heater"},
    {0x93, "P0446 EVAP canister vent control valve circuit"},
    {0x94, "P1775 (generic slot, not used on this car)"},
    {0x95, "P1336 Crankshaft position sensor (POS) cog"},
    {0x96, "P0410 (generic slot, not used on this car)"},
    {0x97, "P1460 (generic slot, not used on this car)"},
    {0x98, "P0125 Coolant temp sensor (slow to warm up)"},
    {0xA1, "P0155 Front O2 sensor heater B2 (left bank)"},
    {0xA2, "P0161 (generic slot, not used on this car)"},
    {0xA3, "P1706 Park/neutral position switch circuit"},
    {0xA4, "P1130 (generic slot, not used on this car)"},
    {0xA5, "P1400 EGRC solenoid valve circuit"},
    {0xA6, "P0412 (generic slot, not used on this car)"},
    {0xA7, "P1460 (generic slot, not used on this car)"},
    {0xA8, "P0443 EVAP canister purge volume control valve circuit"},
    {0xB1, "P0705 A/T inhibitor switch circuit"},
    {0xB2, "P0720 A/T vehicle speed sensor circuit"},
    {0xB3, "P0731 A/T 1st gear function"},
    {0xB4, "P0732 A/T 2nd gear function"},
    {0xB5, "P0733 A/T 3rd gear function"},
    {0xB6, "P0734 A/T 4th gear function"},
    {0xB7, "P0744 A/T TCC solenoid function"},
    {0xB8, "P0750 A/T shift solenoid A circuit"},
    {0xC1, "P0755 A/T shift solenoid B circuit"},
    {0xC3, "P1760 A/T overrun clutch solenoid circuit"},
    {0xC4, "P0740 A/T TCC solenoid circuit"},
    {0xC5, "P0745 A/T line pressure solenoid circuit"},
    {0xC6, "P1705 A/T throttle position sensor circuit"},
    {0xC7, "P0725 A/T engine speed signal"},
    {0xC8, "P0710 A/T fluid temp sensor circuit"},
    {0xD1, "P1135 (generic slot, not used on this car)"},
    {0xD2, "P1105 MAP/BARO switch solenoid valve circuit"},
    {0xD3, "P1140 (generic slot, not used on this car)"},
    {0xD4, "P1145 (generic slot, not used on this car)"},
    {0xD5, "P1220 (generic slot, not used on this car)"},
    {0xD6, "P0243 (generic slot, not used on this car)"},
    {0xD7, "P0247 (generic slot, not used on this car)"},
    {0xD8, "P1900 (generic slot, not used on this car)"},
};

const char *dtc_name(uint8_t code)
{
    for (size_t i = 0; i < sizeof DTCS / sizeof DTCS[0]; i++)
        if (DTCS[i].code == code)
            return DTCS[i].name;
    return NULL;
}

const active_test_t ACTIVE_TESTS[N_ACTIVE_TESTS] = {
    {"Cooling fan (low)",   0x93, 0,   0,   0,   0, "",          0, 0},
    {"Cooling fan (high)",  0x94, 0,   0,   0,   0, "",          0, 0},
    {"Coolant temp override", 0x80, 1, 20, 110, 100, "°C",       0, 0},
    {"Fuel trim",           0x81, 1, -10,  10,   6, "%",         1, 0},
    {"Ignition timing",     0x82, 1,  -5,   5,   2, "°",         1, 0},
    {"Cut cylinder",        0x88, 1,   1,   6,   1, "cylinder",  1, 1},
};

uint8_t active_encode(const active_test_t *t, int arg)
{
    switch (t->reg) {
    case 0x80: return (uint8_t)(arg + 50);
    case 0x81: return (uint8_t)(0x64 + arg);
    case 0x82: return (uint8_t)arg;             /* signed degrees */
    /* Bitmask per Issue 6 (bit 0 = cylinder 1). For cylinders 1 and 2 the bitmask and
     * the cylinder-number encoding give the same byte; checklist 4.4 is still open. */
    case 0x88: return (uint8_t)(1u << (arg - 1));
    default:   return 0x01;                     /* on */
    }
}

const bcm_test_t BCM_TESTS[N_BCM_TESTS] = {
    {"Door locks (lock while held)",  0x23, 0x00},   /* unlocks again when it stops */
    {"Trunk release",                 0x03, 0x03},
    {"Wipers",                        0x53, 0x01},
    {"Rear defogger",                 0x63, 0x01},
    {"Step lamp RH",                  0xE3, 0x02},
    {"Step lamp LH",                  0xE3, 0x01},   /* not seen: that bulb is out */
    {"Interior lamp",                 0x93, 0x01},   /* rear dome lamp seen */
    {"Chime 73",                      0x73, 0x01},   /* 73/83/B3 all give 2 beeps: */
    {"Chime 83",                      0x83, 0x01},   /* key, light and seat-belt */
    {"Chime B3",                      0xB3, 0x01},   /* warning, not yet told apart */
    {"Hazard lamps",                  0x03, 0x04},   /* held solid, not flashing */
    {"Horn + headlights",             0xC3, 0x01},
    {"Panic (horn + lights)",         0x03, 0x06},
};

const char *const BCM_WINDOW_NAMES[N_BCM_WINDOWS] = {
    "Driver", "Front passenger", "Rear right", "Rear left",
};

uint8_t bcm_window_value(int window, int down)
{
    return (uint8_t)(1 + 2 * window + (down ? 1 : 0));    /* odd = up, even = down */
}
