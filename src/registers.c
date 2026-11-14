#include "registers.h"

/* 18 registers, under the 20-register limit. Left out on purpose for the 1998 Maxima
 * (ID ED, 23710-2L904): 17 (AAC) is unsupported and would fail the whole command, and
 * 02/03 (CAS) × 8 isn't RPM. 08 (coolant) only streams alongside other registers,
 * which it always does here. Speed × 2 is still unverified (checklist 3.12). */
const sensor_t SENSORS[N_SENSORS] = {
    {"Engine speed",        {0x00, 0x01}, 2, 12.5,   0, 0, "rpm"},
    {"Coolant temp",        {0x08},       1, 1,    -50, 0, "°C"},
    {"Intake air temp",     {0x11},       1, 1,    -50, 0, "°C"},
    {"Battery",             {0x0C},       1, 0.08,   0, 2, "V"},
    {"Throttle position",   {0x0D},       1, 20,     0, 0, "mV"},
    {"Mass air flow",       {0x04, 0x05}, 2, 5,      0, 0, "mV"},
    {"O2 sensor LH",        {0x09},       1, 10,     0, 0, "mV"},
    {"O2 sensor RH",        {0x0A},       1, 10,     0, 0, "mV"},
    {"Vehicle speed",       {0x0B},       1, 2,      0, 0, "km/h"},
    {"Injector LH",         {0x14, 0x15}, 2, 0.01,   0, 2, "ms"},
    {"Injector RH",         {0x22, 0x23}, 2, 0.01,   0, 2, "ms"},
    {"Ignition timing",     {0x16},       1, -1,   110, 0, "°BTDC"},
    {"A/F alpha LH",        {0x1A},       1, 1,      0, 0, "%"},
    {"A/F alpha RH",        {0x1B},       1, 1,      0, 0, "%"},
};

size_t sensor_payload(uint8_t *out)
{
    size_t o = 0;
    for (int i = 0; i < N_SENSORS; i++)
        for (int j = 0; j < SENSORS[i].nregs; j++) {
            out[o++] = 0x5A;
            out[o++] = SENSORS[i].regs[j];
        }
    return o;
}

int sensor_frame_len(void)
{
    int n = 0;
    for (int i = 0; i < N_SENSORS; i++)
        n += SENSORS[i].nregs;
    return n;
}

void sensor_decode(const uint8_t *frame, double *values)
{
    for (int i = 0; i < N_SENSORS; i++) {
        unsigned raw = 0;
        for (int j = 0; j < SENSORS[i].nregs; j++)
            raw = (raw << 8) | *frame++;
        values[i] = raw * SENSORS[i].scale + SENSORS[i].offset;
    }
}

/* Classic Nissan 2-digit codes, names from openconsult. The code byte is read as hex
 * digits; ECUTalk agrees for this car's 21 and 34. */
static const struct { uint8_t code; const char *name; } DTCS[] = {
    {0x11, "Crankshaft position sensor (CAS) circuit"},
    {0x12, "Mass air flow sensor"},
    {0x13, "Engine coolant temp sensor"},
    {0x14, "Vehicle speed sensor"},
    {0x16, "Motor throttle switch"},
    {0x17, "ABS-TCS control unit"},
    {0x21, "Ignition signal"},
    {0x22, "Fuel pump"},
    {0x23, "Idle switch"},
    {0x24, "Throttle valve switch"},
    {0x25, "Idle speed control valve"},
    {0x26, "Turbo pressure sensor"},
    {0x28, "Overheat"},
    {0x31, "ECM"},
    {0x32, "EGR function"},
    {0x33, "Heated O2 sensor"},
    {0x34, "Knock sensor"},
    {0x35, "EGT sensor"},
    {0x36, "EGR back-pressure transducer"},
    {0x37, "Knock sensor"},
    {0x38, "RH bank closed loop (B2)"},
    {0x41, "Intake air temp sensor"},
    {0x42, "Fuel temp sensor"},
    {0x43, "Throttle position sensor"},
    {0x44, "ABS-TCS comm circuit"},
    {0x45, "Injector leak"},
    {0x46, "Throttle motor sensor"},
    {0x47, "Crankshaft position sensor"},
    {0x51, "Injector circuit"},
    {0x53, "O2 sensor"},
    {0x54, "A/T communication circuit"},
    {0x55, "No malfunction"},
    {0x63, "Cylinder 6 misfire"},
    {0x64, "Cylinder 5 misfire"},
    {0x65, "Cylinder 4 misfire"},
    {0x66, "Cylinder 3 misfire"},
    {0x67, "Cylinder 2 misfire"},
    {0x68, "Cylinder 1 misfire"},
    {0x71, "Random misfire"},
    {0x72, "TWC function RH bank"},
    {0x76, "Fuel injection system RH bank"},
    {0x77, "Rear heated O2 sensor"},
    {0x82, "Crankshaft position sensor (RH)"},
    {0x84, "A/T diag comm line"},
    {0x87, "Canister control solenoid"},
    {0x91, "Front HO2S heater RH"},
    {0x94, "TCC solenoid"},
    {0x95, "Crank position cog"},
    {0x98, "Coolant temp sensor"},
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
