# Bank-1 helper: hardware follow-up plan

Scope: 1998 ECU `23710-2L904`, key on and engine off. This plan starts after
the first fixed-X trial in `tools/bank1_x_probe.py`. Every mutation is a
separate verified session: identity and zero RPM first, one modeled request
without retry, acknowledged STOP, immediate independent readback, and raw/JSON
logs. A missing acknowledgment or unexpected RAM change ends mutation work
until a read-only baseline has been recovered.

## If the fixed-X trial is negative or inconclusive

1. Classify the failure before changing a payload. A bad echo, missing frame,
   missing STOP acknowledgment, inactive `$088B.0`, and unchanged helper output
   are different outcomes. Preserve the raw log and do not replay the request.
2. Use ordinary eight-address C9 reads to measure `$0717` counter cadence,
   `$088B/$092A/$0CA5` gate state, and natural variation in `$080A-$0810` and
   `$0C9D`. Confirm zero RPM throughout. This establishes whether two stream
   frames could have covered a call at all.
3. If timing is the only gap, change the frame count only after an offline
   model and a review of how long the request remains active. Run one fresh
   trial, with the same stop/readback gates. If the planted bytes disappear
   before the call, redesign the observation slot offline before another
   mutation.
4. If the call is likely reached but the output does not depend on the chosen
   byte, treat `$015AD1` as an unproven pointer candidate. Compare read-only
   natural sample/output traces with a numeric difference/filter model. Shift
   the bank-1 acquisition effort to a full chip image or another independently
   validated read path; do not infer a pointer from the packed `X` register.

## If the output changes with the chosen byte

1. Repeat once in a fresh session with a second byte, after measuring the
   no-mutation output range. Dependence on `[$080E]` is **not** proof of a read
   through `X`: the helper could read `$080E` as a fixed global.
2. Build an offline-validated control that changes `X` while holding the byte
   at `$080E` and other call inputs constant. Use only addresses in the
   sacrificial sample buffer. A response that follows the new `X` target is
   evidence for an indirect read; a response fixed to `$080E` is evidence for
   a global read. If the control cannot isolate those variables, report the
   ambiguity instead of claiming a pointer primitive.
3. Check independent RAM readback for a store at the candidate `X` address.
   Compare against the visible history-shift stores and natural background
   changes. A reproducible extra store within the sample buffer would justify
   a separate, bounded write-capability study; an output change alone would
   not.
4. If an indirect read is established, resolve its address space with known,
   harmless RAM and ROM sentinels. A 16-bit `X` value alone does not establish
   bank-1 access. Only after bank selection is demonstrated should a bounded
   bank-1 read and two matching hashes be attempted. Disassemble `$015AD1`
   from that image before considering any broader write path.

No engine-running trial or persistent calibration write follows automatically
from either branch. Those require a separate model and test plan.
