#ifndef FUEL_MAP_H
#define FUEL_MAP_H

#include <gio/gio.h>
#include "consult.h"

typedef struct fuel_map fuel_map_t;

fuel_map_t *fuel_map_load(GFile *file, GError **error);
fuel_map_t *fuel_map_dandymax_candidate(void);
void fuel_map_free(fuel_map_t *map);
void fuel_map_dimensions(const fuel_map_t *map, guint *rpm, guint *load);
double fuel_map_rpm(const fuel_map_t *map, guint column);
double fuel_map_load_code(const fuel_map_t *map, guint row);
/* NaN denotes normal ECU feedback. */
double fuel_map_offset(const fuel_map_t *map, guint row, guint column);
/* Zero denotes normal ECU feedback. Nonzero values are native percentages. */
int fuel_map_lookup(const fuel_map_t *map, double rpm, unsigned load);

typedef void (*fuel_status_fn)(const char *message);
typedef void (*fuel_sample_fn)(double rpm, unsigned load, int percent);
/* Pass INFINITY for no time limit. csv, when supplied, receives every decoded fuel frame. */
gboolean fuel_map_stream(consult_t *c, const fuel_map_t *map, double seconds,
                         const atomic_int *abort, fuel_status_fn status, fuel_sample_fn sample, FILE *csv);

gboolean timing_probe(consult_t *c, uint8_t raw, const atomic_int *abort,
                      fuel_status_fn status);

#endif
