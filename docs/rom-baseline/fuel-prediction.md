# Fuel prediction: evidence and remaining gaps

## Verified final bank calculation

In the 2L904 listing, 69B3..69F2 build separate bank correction sums from RAM 0B10/0B2E and either 0x6400 or learned words 0B44/0B5A. Branches depend on 0AC7 and 1207 bit 1. Both banks call 69F7.

For non-overflowing inputs, the shared 69F7..6A1F helper performs the following fixed-point computation:

- Add correction word 0CD2 to the incoming sum, subtract 0xC800.
- Multiply by the 16-bit working quantity at 0906; retain the product shifted right 15 (MPY, XAB, ASL B/ROL A). Overflow saturates to FFFF.
- Multiply that result by word 0A58; retain the product shifted right 14 (MPY, XAB, two ASL B/ROL A operations). Overflow saturates to FFFF.
- Add word 0A9C, again saturating to FFFF.
- Store the results at 0A8E and 0A8C.

This is integer math, not a floating-point physical model. Carry/borrow and branch states must be preserved for a bit-exact emulator; the description above is for the ordinary non-overflow path. The next routine, 6A20, alternates bank bases and applies signed per-cylinder trim words at 0A24 onward, with saturating addition/subtraction and cylinder skip masks. Thus these bank bases are upstream of the final reported injector times.

The upstream working quantity at 0906 is generated in 68F3..6962 from load word 0ABD and signed 0A54 corrections, then multiplied by 0A56. Other steps use 0A58, a cold/after-start minimum, and additive 0A9C. These dependencies demonstrate why RPM, load and a single table byte are insufficient to reproduce final pulse width.

## Tested and rejected shortcut

Using the same 7666 non-idle frames as the timing comparison, interpolate each candidate fuel grid using RPM/50 and load_code/256, in both orientations, then subtract 128. None predicts the logged 0A74 or 0A70 values. The best 0A74 candidate is alternate table 1800, normal orientation, with mean absolute error 5.0635 raw units and only 1.0175% of values within one unit. For 0A70 all candidates have mean absolute error above 52 raw units. Therefore neither logged variable can currently be called a direct decoded fuel-map value.

## Related manufacturer documentation

Nistune Mapping Guide v1.6, pages 17–19, documents a later fuel/VE strategy: fuel and adjusted-throttle VE coefficients interact, and an Alpha/N threshold can force the last fuel-load column. That establishes plausible missing dependencies, not proof that 2L904 uses an identical equation. Source: https://nistune.com/docs/Nistune_Mapping_Guide.pdf

## What is still required

Missing bank-1 code or a matching authoritative definition must establish the fuel table coefficient formula, VE indexing/contribution, full-throttle selection, and intermediate outputs. The current trace lacks 0A54/0A56/0A58/0A9C, both learned internal words, 0CD2, and individual cylinder trims. Current evidence supports tracing the downstream arithmetic, but does not support a complete table-to-injector prediction or measured AFR prediction.

## Further backward assembly trace

The main task order at 4C8E..4CC6 is important: calc_rpm; missing bank-1 call 016F18; TPS processing; 5B92; 5C79; 5CBD; call 5F1B in the untrusted forwarded-read window; cylinder corrections 644C; scaling 66BA; after-start minimum 683A; bank pulse builder 68F3; final injector adjustment 6A20. Thus there are two separate missing-code boundaries before the pulse calculation, not merely an unresolved named table routine. The 5F1B bytes in both the local and 1997 images exhibit repeated forwarding artifacts and cannot be trusted as executable code.

0A56 has an accessible producer at 5C79..5CB2: sum 0AC7+0ACD+0AE5+0ADB with saturation. When 092A bit 1 is set, multiply by a coefficient from calibration 1AA9 (high-byte component) with an effective right-shift of 14, again saturating. This is a composite correction quantity, not a direct map-cell copy.

0A54 is produced at 680F from signed 0A6C multiplied by the high-byte-aligned value drawn from 0A63; positive and negative branches preserve sign. That result enters 68F3, where it changes the load-derived working quantity before injector scaling. 0A6C itself comes from the difference between 0A6E and 0A72, multiplied by 0A70*8 with signed saturation (6746..67A3). This supports a dynamic correction path, not assigning these words directly to a 16x16 coefficient.

A literal STA search across both raw 64K images finds no absolute STA to 0A74, 0A70, 0A58, 0A9C or 0CD2. This does not exclude indexed/indirect stores or other store opcodes, but it reinforces that no direct producer has been identified. The readable consumers alone cannot establish the original table coefficient transformation.

Width caveat: 66BA is entered after the preceding routine restores 8-bit accumulator mode; 66C8 explicitly switches to 16 bits. Therefore the initial read of 0A74 and multiplication by 1AAB should not be interpreted automatically as two 16-bit operands. The logger preserves both bytes, but the consumer width must be represented in any future emulator.

## Executable partial formula

`consult/fuel_math.py` implements the reconstructed 69F7 helper arithmetic with raw-word inputs and explicit incoming ADC carry. Let S be the incoming bank sum, C=word[0CD2], Q=word[0906], F=word[0A58], D=word[0A9C], and k the incoming carry:

```text
coefficient = (((S + C + k) mod 65536) - 51200) mod 65536
first = floor(coefficient * Q / 32768)
if first > 65535: return 65535
second = floor(first * F / 16384)
if second > 65535: return 65535
return min(65535, second + D)
```

This preserves intermediate truncation and early saturation; multiplying all factors in one floating-point expression would not. Five focused unit checks cover unity scaling, first-stage early saturation, second-stage saturation, final addition saturation, and carry sensitivity/word validation. They validate the reconstructed arithmetic model, not hardware equivalence. Before describing a complete instruction-exact emulator, independently verify MPY flag semantics and caller states. The factory table-to-coefficient stage and the per-cylinder/output transformations remain outside this function.

## Processor semantics and final cylinder stage verified

The official Renesas 7700 Family Software Manual, PDF pages 142–143 (manual 4-58/4-59), specifies unsigned 16x16 MPY with B as upper half and A as lower half, and clears carry. This resolves the previously outstanding MPY semantics check. Source: https://www.renesas.com/en/document/mas/7700-family-software-manual . Caller mode, incoming carry, and Y must still be respected.

The per-cylinder calculation at 6A3B..6A8D is now implemented as `cylinder_pulse`: start with alternating base 0A8C/0A8E; unless the matching 0A97 bit is set, add signed trim word at 0A24+2*cylinder and saturate to 0..FFFF. Always subtract the signed word 12 bytes later (0A30+2*cylinder), again saturating. The mask skips only the first operation. Negative second trims therefore add pulse width. Saturation occurs between the operations, so combining trims before clamping is incorrect. Seven model checks now cover both helper stages.

At 6A9D..6AC5, selected computed pulse words at 0A3C/0A3E are copied directly to Consult backing words 0DAB/0DA9, except that bank mask bits at 0A90 can substitute 0A9C. No separate unit conversion is performed in this copy. Existing Consult decoding divides these output words by 100 to report milliseconds. Consequently a log can validate this final stage if it also records the relevant cylinder words and masks. Our existing trace does not record them.

## Additional upstream producer found: 0ACD

56A5..572F produces one of the four terms summed into 0A56. It is driven by temperature and RPM calibration, not a direct copy of the 16x16 fuel grid:

- When 092A bit 1 is set, 0981 indexes tables at 1990, 16F0 and 1970. Their outputs populate 0AD0, 0AD1 and 0ACB; 0ACF is reset to zero and 0ACC to FF. These state updates are conditional, so later results depend on history.
- 09AE (the capped 12.5-RPM coordinate) indexes table 1980. The result is multiplied by byte 0ACC, giving a 16-bit product stored at 090A.
- A byte of 80, or calibration byte 1ADF when 092A bit 0 is set, is multiplied by byte 0AD1, giving a second 16-bit product at 090C.
- In 16-bit mode, the products at 090A and 090C are multiplied and the result shifted right 13 (XAB followed by three ASL B/ROL A pairs). The result plus word 0ACF saturates to FFFF and is written to 0ACD.

Thus on the non-overflow path: 0ACD = min(65535, floor((interp1980(09AE)*byte[0ACC])*(selected_byte*byte[0AD1])/8192) + word[0ACF]). Interpolation itself must still follow the ECU helper, and inputs may have state from previous task cycles. This resolves a real upstream dependency without claiming a complete fuel-grid formula.

The reset/initialization path at 420B sets 0AC7=4000. At 4211..421D it sets the learned and bank correction words 0B44/0B5A/0B10/0B2E to 6400. These are initialization values, not proof that the values stay fixed while running. In particular 0AC7 contributes the nominal Q14-unity 4000 to the composite correction, while additional terms can change its value.

## Focused fuel measurement profile

`python3 tools/table_trace.py --profile fuel --dev /dev/ttyUSB0 --seconds 120 --run` records the unresolved composite multiplier 0A56, scaling factor 0A58, additive 0A9C, base term 0AC7, correction term 0ADB and 0CD2, plus 0A74/0A70, RPM index, load, TPS, adjusted TPS and mode. Ordinary words are requested little-endian; load is requested high-first to match prior logs. Outputs use a distinct `_fuel-trace` filename to prevent the timing analyzer ingesting a different schema. It stays within the 20-read/40-argument-byte request limit. Offline byte-order and scaling checks passed; this precise profile has not yet run against hardware.

This profile samples missing upstream dependencies rather than repeating the already measured timing correlation. It does not record all inputs needed to verify a final pulse prediction in a single frame, and serial snapshots are not atomic CPU-state captures. Warm steady idle and a few stable light-load operating points can test relationships without requiring full-load experiments.

## First fuel-profile hardware results

2026-11-17_135145_304875_fuel-trace.csv contains 31582 frames over 965.45 seconds, including 168 samples at TPS>=4000 mV. The composite 0A56 equals base 0AC7 in 31554 frames. Factor 0A58 remains 11702; additive 0A9C ranges 60..69; 0CD2 remains 25600 (6400 hex); 0ADB remains zero. Base 0AC7 ranges 16384..22272: dividing by 128 gives 128..174, matching the alternate fuel table coefficient range. Dividing by 16384 gives a candidate Q14 multiplier of 1..1.359375. This numeric relationship is supported by the existing scaling code but not yet a verified full coefficient decode.

`python3 tools/analyze_fuel_trace.py` compares bilinear normal/alternate tables with RPM index and candidate load coordinates. Critically, 31171 frames have the unity base 16384, so whole-log accuracy is dominated by uninformative flat cells. Among the 411 enriched frames, the 1800 alternate-table model indexed by RPM/50 and calculated load, scaled by 128, has MAE 99.84 raw units (0.78 table units), with 76.40% within 128 raw units. The 1700 normal-table model has MAE 613.69 (4.79 table units) and 32.36% within 128. Adjusted TPS and forced-last-column alternatives fit worse in enriched samples. These comparisons support but do not prove the alternate-table hypothesis; mode changes, serial skew, integer interpolation and other logic need further separation.

At one observed point, RPM index=87 (4350 RPM), calculated load=122.9258, TPS=4040 mV and 0AC7=0A56=22272, yielding the candidate multiplier 1.359375. This is a fuel correction coefficient, not a measured AFR and not proof of increased fuel relative to the entire factory calculation. The capture omits injector outputs and bank correction words, so cannot validate complete final pulse predictions.

Logger duration update: default --seconds=0 now records until Ctrl+C, with no maximum finite duration. Positive --seconds remains an optional explicit bound. Negative and nonfinite durations are rejected.

## Mode-conditioned fuel table result

All 31582 observed 0AC7 values are exact multiples of 128, supporting an integer table-like coefficient followed by a 7-bit left shift. Mode-conditioned analysis changes the earlier whole-log interpretation. Among 294 enriched frames with 0DCF=0, table 1800 fits with MAE 0.57884 coefficient units and 92.857% within one unit; table 1700 has MAE 6.58039. Among 117 enriched frames with 0DCF=12 (0C hex), table 1700 fits with MAE 0.30684 and 100% within one unit; table 1800 has MAE 1.28545. Selecting 1800 for observed mode 0 and 1700 for observed mode 12 yields MAE 0.50141 and 94.891% within one unit over all 411 enriched frames.

This empirical direction conflicts with assuming 0DCF bit 3 automatically selects the table labeled Knock at 1800. Do not assign bit-specific selection semantics or normal/knock labels from the old annotation alone. The trace has only two enriched mode groups, separated in time, and mode can correlate with another unmeasured condition; it is not a causal proof. The modes should be described numerically until the selector code is recovered.

Candidate formula at the coefficient stage:

```text
C = integer_lookup(selected fuel table, RPM_index, calculated_load)
0AC7 = C << 7
base correction multiplier = 0AC7 / 16384 = C / 128
```

Simple floor of floating-point bilinear interpolation exactly matches only 55.96% of enriched samples, so integer_lookup is intentionally unresolved. Residuals include rapid transitions (example at 182.43 seconds: current load 73.625 but retained coefficient 160), compatible with scheduling/filtering/serial skew rather than proving an alternate physical conversion. The coefficient capture alone does not isolate which timing relationship causes those residuals.

`python3 tools/refine_fuel_trace.py` reproduces group scores and worst residual examples. Neither this relationship nor the approximately 95% fit establishes the complete injector-pulse equation; table selection, exact lookup/rounding, dynamic inputs, final bank correction state and masks must still be verified together.

## Integer lookup hypothesis audit

`tools/analyze_fuel_rounding.py` tests 54 combinations: whole-byte versus fractional load, three interpolation orders (bilinear or two sequential 1D interpolations), floor/nearest/ceil rounding and -1/0/+1 sample alignment. Evaluation remains restricted to 411 enriched frames; flat unity samples are excluded. Results are stored in fuel-rounding-candidates.json.

The best tested candidate uses fractional load, nearest-integer rounding, column-first sequential interpolation and the current sample. It matches 80.292% exactly, with MAE 0.382 coefficient units; nearest rounding of ordinary bilinear interpolation matches 80.049% exactly with the same MAE. Among 149 locally stable frames (RPM index unchanged across adjacent frames and load changes under one unit), the column-first candidate matches 85.906% exactly. The tiny difference between interpolation orders is insufficient to establish actual order.

These results improve the prediction but do not identify an exact ECU algorithm. Residuals remain even in the stable subset, and mode-conditioned selection is still an empirical association. Candidate generation and evaluation use the same recording, so this is hypothesis ranking, not independent validation or proof. Reconstructing a complete production formula still requires unresolved coefficients/selector code or a capture including upstream and final-output terms together.

## Actual-byte execution check for the downstream helper

`python3 tools/verify_fuel_helper.py` independently executes the actual 2L904 bytes at 69F7..6A1F with a small explicit instruction interpreter (ADC/SBC, SEC, unsigned MPY, XAB, ASL B, ROL A, conditional branches, TYA and RTL). It checks the closed-form function against 10002 cases including 10000 deterministic random inputs and both incoming carry states. All cases agree. This validates the formula for that helper under its stated assumptions (16-bit mode, DT=0, Y=FFFF and supplied RAM inputs). It is not an independent validation of processor documentation, the entire disassembler, hardware timing, or the upstream table interpretation.

The previous rounding comparison also shows why the fractional load must be retained in current candidate predictions: the best whole-byte-only model matches only 59.85% of enriched samples exactly (43.62% in the stable subset), versus 80.29% (85.91% stable) for the best fractional-load candidate. The remaining error means it is still inappropriate to call the lookup formula exact.

## Readable interpolation helper traced

EA77/EA82/EA8D implement uniform 16/32/8-entry unsigned-byte interpolation. Inputs clamp at F0/F8/E0, respectively. Shifts split the coordinate into node index and fractional weight; increasing segments multiply the byte difference by the fraction and take the high byte, then add the lower endpoint. Decreasing segments negate the difference and fractional weight, multiply, take the high byte and add the upper endpoint. This is floor of linear interpolation in both directions, not ordinary nearest rounding. `interpolate_uniform_bytes` implements the result, with endpoint and rising/falling tests. Eight focused tests pass across fuel_math.py.

This helper consumes uniformly spaced implicit axes. The 16x16 grids have explicit axis arrays, and no call path from those grids to EA77 has been established. Therefore the nearest-rounding fit observed in fuel traces must not be asserted as actual MCU behavior; it could reflect an earlier coordinate quantization, a different lookup implementation, scheduling, or missing transformations. Conversely, the verified 1D flooring rule must not automatically be assigned to the missing 2D consumer.

## Missing RPM precision tested

The fuel capture stored only 09B1, losing the low two bits of the Consult RPM word (up to 37.5 RPM). `tools/analyze_fuel_precision.py` tests possible sub-index offsets and load offsets against the enriched frames. A +0.25 index offset (12.5 RPM) improves nearest-rounding exact matches only to 81.51%; therefore lost RPM precision alone does not resolve the algorithm. Even allowing each frame to choose whichever of four possible low-bit values fits best, only 377/411 enriched frames can match nearest-rounded interpolation, and 270/411 can match floor interpolation. This deliberately optimistic upper bound rejects that explanation as sufficient, without asserting a different formula.

Current explicit-load-index and interpolation hypotheses are incomplete. An exact formula cannot be established solely by further rounding adjustments to this recording. A direct decoded consumer or additional inputs/output timing evidence is needed. Searches of literal producers and immediate pointers into the unresolved coefficient words have not found the running 0AC7 producer in the readable listing. This is evidence about the current decode, not proof that the producer must live in bank 1.

## Residual investigation: sample delay and filtered load

Corrected a bug in the delay-only subsection of refine_fuel_trace.py: it had used the reverse of the empirically tested mode-to-address association. The group scores and final combined score were already using the intended association and are unchanged. After correction, unsmoothed mean absolute error is 0.5014 coefficient units at the current frame versus 0.5999 at the previous frame, 0.9034 at the next frame, and >=1.0395 for offsets of two or three frames. A uniform whole-frame delay is therefore not sufficient.

`tools/analyze_fuel_filtering.py` tests explicit first-order load filters across the recording, keeping early (mode 0 enriched, 294 frames) and late (mode 12 enriched, 117 frames) scores separate. Alpha=0.75 improves early MAE from 0.4762 to 0.3571 but worsens late MAE from 0.1453 to 0.1538 and exact matches from 85.47% to 84.62%. Stronger filters worsen both more substantially. There is no consistent evidence here for one fixed smoothing filter that resolves all residuals. This temporal split is diagnostic only, not independent confirmation of the empirically chosen mode selection.

These checks reject whole-frame lag and simple smoothing as complete explanations. The upstream producer/selector remains unidentified; additional arbitrary fitting would not establish an exact formula.
