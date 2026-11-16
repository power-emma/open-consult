/* Proposed contracts only. No definitions or live callers yet.
 * Existing serial.h/consult.h APIs remain the production interfaces.
 * Keep semantics aligned with consult/hardening.py during implementation. */
#ifndef CONSULT_HARDENING_H
#define CONSULT_HARDENING_H

#include <stddef.h>
#include <stdint.h>

typedef enum {
    CH_COMPLETE, CH_DEADLINE, CH_CANCELLED, CH_DISCONNECTED, CH_OS_ERROR
} ch_completion_t;

typedef enum {
    CH_DRAIN_UNKNOWN, CH_DRAIN_COMPLETE, CH_DRAIN_FAILED, CH_DRAIN_DEADLINE
} ch_drain_t;

typedef struct {
    size_t requested;
    size_t accepted;       /* OS-accepted prefix; never an ECU execution claim */
    ch_completion_t completion;
    ch_drain_t drain;
    uint32_t os_error;    /* native errno / Windows error; 0 when absent */
} ch_write_result_t;

typedef enum { CH_OBSERVATION, CH_ACTIVE_TEST, CH_MUTATION } ch_operation_t;
typedef enum {
    CH_IDLE, CH_COMMAND, CH_STREAMING, CH_STOPPING, CH_UNCERTAIN, CH_LINK_DISCONNECTED
} ch_link_t;
typedef enum {
    CH_NOT_ATTEMPTED, CH_UNVERIFIED, CH_UNKNOWN, CH_VERIFIED, CH_MISMATCH
} ch_mutation_t;

typedef struct {
    ch_operation_t operation;
    int repeatable;
    ch_link_t link;
    int baseline_verified;
    unsigned retries_used;
    unsigned max_retries;
} ch_retry_context_t;

/* Opaque future adapter: deadline is absolute monotonic seconds.
 * Every call, including any OS drain, must honor or explicitly disclaim bounds.
 * Adapter implementation must return partial progress on every failure. */
typedef struct ch_transport ch_transport_t;
ch_write_result_t ch_write_all(ch_transport_t *transport,
                               const uint8_t *data, size_t length,
                               double deadline);

/* Future implementation must reject mutation/active-test automatic replay.
 * This declaration does not change consult_command() retry behavior. */
int ch_may_retry(const ch_retry_context_t *context);

#endif
