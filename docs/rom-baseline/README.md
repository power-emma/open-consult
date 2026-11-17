# A32 fuel baseline comparison

Compared the official Nistune ROM Pack 2.14 file `A32_VQ30DE_0L701_MT_1997.bin` (65536 bytes, addressed from zero) with the existing hardware dump `rom/23710-2L904_1000-FFFF.bin` (61440 bytes, addressed from 0x1000). Region names follow ROM_ANALYSIS.md section 8 and the PLMS 1999 A32 register research; they are candidate semantics, not newly traced consumers.

The MAF curve region, VE table and axes, both fuel tables, fuel axes, and timing axes match exactly. Normal timing differs in 53/256 bytes and knock timing in 64/256. This establishes shared calibration bytes, not identical firmware or identical resulting AFR. Earlier 1995/96 images do not share this layout at these offsets; applying these offsets to them is invalid.

Raw CSV exports preserve storage order. Row/column physical interpretation, axis conversion, table selection, flag bits and fuel-value scaling still require lookup-code tracing or a verified matching definition. ENT files in the pack are binary program files, not readable map definitions. Do not interpret raw fuel values as native Consult feedback percentages or measured AFR. The repeated axis bytes are 08,10,18,20,28,30,38,40,48,50,58,60,68,70,78,80 (hex).

The recorded baseline has 27458 frames over about 843 seconds. At high throttle (4180 mV), observed feedback values include 100/100; an example at 5912.5 RPM has injector pulses 13.41/13.46 ms and timing 16 degrees BTDC. Those observations establish commanded operating behavior but do not identify the active table cell. cal_ld is a different coordinate from the laptop controller raw load_code; no conversion is established here. Narrowband O2 cannot establish full-load AFR.

Correction to earlier conversation: calibration data is already present in the existing dump. The missing bank-1 lookup code limits interpretation, not access to these particular bytes. Leave the laptop override map unchanged until coordinates and correction behavior are verified.

Sources: https://nistune.com/releases/Nistune_ROM_Pack_2.14.exe and https://plmsdevelopments.com/files/1999_a32_maxima_obd2_registers.pdf

## Axis research

Nistune Mapping Guide v1.6 describes fuel maps indexed by RPM and TP load (not throttle percentage or manifold pressure). It also documents a naturally aspirated full-throttle rule that can force the last load column. This supports RPM rows / load columns as an interpretation, but is not proof of storage orientation for 2L904. VE tables can use adjusted TPS instead of TP load.

The official software package's readable A32_VQ30_512_96_E.adr declares RPM_SCALE_FUEL with multiplier 50 and TP_SCALE_FUEL with multiplier 1. However its axis addresses are F6E0/F6F0, not our 1900/1910, so it is not a matching definition. Applying raw*50 to our candidate fuel RPM axis would produce 400,800,...,6400 RPM. Treat these as proposed labels pending an exact definition or consumer-code confirmation. Do not automatically apply the earlier definition's scales or generic fuel-value flag interpretation to this later layout. GUI remains raw to avoid presenting hypotheses as measurements.

## Definition and code audit

Extracted official Nistune 1.4.19 setup into /tmp/nistune-definitions without executing the installer. Searched readable .adr files for 2L904, 0L701, and the candidate axis/table addresses. No matching 1997/1998 A32 definition was found. A32 1996 definitions place normal/high fuel at E600/E700 (inherited BASE_VQ30_512_E.ADR) and fuel axes at F6E0/F6F0; these do not explain our low-ROM tables. A superficially matching REG_FUEL=1700 in BASE_RB25_512_E.adr belongs to a different layout: axes at 15E0/15F0 and second fuel table at 1600. It must not be applied to our A32.

Disassembled the 1997 0L701 file as bank 0 using the repository disassembler into /tmp/a32-1997.asm. Literal-byte matches for candidate map addresses did not establish map consumers: for example 10 19 at 6AB4 is a BPL branch, not a reference to the 1910 RPM axis. This excludes naive two-byte address searching as sufficient decoding evidence. The missing lookup code remains unresolved.

Generic Nistune fuel flag rules are not established for these tables: the guide distinguishes later fuel/VE coefficient handling from earlier embedded O2 flags. All fuel bytes being at least 0x80 is not proof that every cell is closed-loop. Similarly timing values FE/F8 in the first stored row might be signed values or flags; masking or converting them without the consumer would invent semantics.

## Verified downstream units (2L904 code)

The existing decoded RPM routine independently establishes a 50-RPM coordinate: 5681 loads the Consult RPM word into A, 5682/5683 shift it right twice, and 5685 stores its low byte at 09B1. Since the Consult word unit is 12.5 RPM, 09B1 is floor(RPM_word/4) modulo 256 in units of 50 RPM. This proves an internal coordinate, not that the unknown table consumer uses it. The earlier definition multiplier is therefore consistent with real 2L904 code, but the axis-to-coordinate link remains missing.

The final timing path is demonstrably signed before conversion to output units: 47C6 branches on sign; 47C8..47DD apply separate signed/positive limits from 20D8/20D7. At 47B3 the base term 0BA6 is combined with knock term 0DB8 and other corrections. At 47E9 the additional 0DB6 term is added; 47EC..47F0 negate the sum and add calibration 20D4. Slew limits then modify the final output. Thus even a decoded base timing table cannot be equated directly to the logged final timing. This does not prove whether individual table bytes are signed or flagged, because the missing reader could transform them before writing 0BA6.

At 5CC9 the high byte of raw load word 0ABD/0ABE is copied into load history 0E6B..0E6D. At 67B0..67C5 the full word is doubled with saturation, its high byte indexes an 8-entry 1D interpolation at 1A30. These are verified load transformations in surrounding code, not evidence that the 16x16 map axis equals CAL/LD percent or load_code/256.

## Reproducible identity audit

Run `python3 tools/audit_rom_tables.py rom/23710-2L904_1000-FFFF.bin --base 0x1000 --reference rom/reference/nistune-2.14/extracted/app/ROM_Pack/Type34/A32_VQ30DE/A32_VQ30DE_0L701_MT_1997.bin`. `identity-audit.json` records input and region hashes and every mismatching address. Normal fuel raw values span 128..184 and alternate fuel 128..174; these ranges alone cannot determine richer/leaner direction. An alternate table with lower values also cautions against assuming generic higher-byte-means-richer behavior without proving the table identities and selection.

Bank-1 calls adjacent to feedback adaptation are at 4CEE->016FA7 and 4CF2->017005; additional per-bank calls 4D20->017A14 and 4D52->017989 follow feedback work. These are candidate investigation boundaries, not identified 2D consumers. The accessible dump ends at 00FFFF and contains none of these target addresses. No complete later A32 bank-1 image was found in the downloaded ROM pack or targeted public searches. Further static consumer tracing requires that missing code or another authoritative matching definition; current logs lack the intermediate table outputs needed to independently discriminate coefficient/flag hypotheses.

## Next measurement: intermediate RAM trace

`python3 tools/table_trace.py --dev /dev/ttyUSB0 --seconds 120 --run` captures a read-only C9 stream, CSV plus raw log, and prints at 5 Hz while storing every received frame. It requests 20 bytes (40 argument bytes), checks ECU identity 23710-2L904 and sends no active tests or writes. Default without --run is an offline preview. Hardware streaming with this exact list has not yet been verified.

The stream includes RPM and its 50-RPM index, raw load, TPS, base timing 0BA6, knock term 0DB8, mode 0DCF, fuel intermediates 0A74/0A70, both injector pulse widths, both alpha feedback values, reported timing and active flags. A separate signed candidate column preserves raw timing bytes rather than declaring signed interpretation proven. Register words use storage-specific byte order: load/RPM and injector bytes are requested high-first; 0A74/0A75 is an ordinary little-endian word. Samples are serial snapshots, not atomic CPU-state captures.

Start with warm steady idle/light-load operating points and a few stable RPM points; high-load testing is not required for the initial axis/encoding investigation. Matching the base term against interpolated candidate maps can reject hypotheses, but a correlation alone is not proof of a unique formula or table selection. Exact semantics still require missing consumer code or measurements sufficient to distinguish the alternatives.

## Hardware traces received November 17

Six table-trace CSVs contain 21436 frames. Active-test flags remain zero. RPM spans 762.5..4750; highest TPS is 2140 mV, so these are not full-throttle captures. Trace hardware support is now demonstrated for this request list.

`python3 tools/analyze_table_trace.py` reproduces a comparison of both timing tables, both orientations, three value interpretations (unsigned, signed, low-seven-bit), and load divisors 128/256/512. The primary comparison excludes idle/closed throttle (TPS>=700 mV and RPM>=1500), leaving 7666 samples. Full results are in trace-model-candidates.json. These are hypothesis tests, not exhaustive possible ECU algorithms.

The strongest tested model uses table 1E00, row coordinate RPM/50 (logged 09B1), column coordinate load_code/256, and timing value byte & 0x7F. Bilinear interpolation yields MAE 0.5512 degrees versus the logged 0BA6 base timing; 97.965% are within 2 degrees. The same interpretation using 1D00 yields MAE 2.0143 degrees and 71.445% within 2 degrees. Best transposed candidates have MAE>=8.71 degrees. This is strong observational support for RPM rows and load columns and the low-seven-bit timing encoding in the operating region sampled. It is not proof of bit-7 meaning, exact integer interpolation/rounding, signed-value handling at idle, all operating regions, or table selection conditions.

For 2777 frames with knock byte FC, reported timing equals base timing minus 4 degrees exactly in 92.258% and within one degree in 97.623%. This supports the signed -4 interpretation of FC and the downstream correction path. It does not establish whether the correction arose from detected knock or fail-safe. Mode 0DCF is predominantly 0C, but the observed table match alone does not establish individual mode-bit meanings.

The fuel intermediates remain undecoded: 0A74 word ranges 0..19 and 0A70 13..88 across the captures. Neither is demonstrably a direct fuel-table byte (fuel bytes span 128..184). These are transformed intermediate values, so assigning a fuel multiplier from these ranges would be unsupported.

## Load coordinate resolved at the register level

Correction to earlier notes: `load_code` and `cal_ld` are not independent coordinates. The actual 2L904 Consult pointer table at 1000 contains BE 0A at offset 33*2 (1066), and BD 0A at 34*2 (1068): register 33 reads RAM 0ABE (whole component), and register 34 reads RAM 0ABD (fraction). The logger assembles load_code=(0ABE<<8)|0ABD. The existing cal_ld decoder assembles the exact same register word and divides by 256. Thus under the existing fixed-point convention, cal_ld = load_code/256 before display rounding. The successful timing-model load divisor 256 therefore corresponds directly to the exposed calculated-load channel, not a different hidden TP coordinate.

PLMS calls this CAL/LD percent for the related 1999 A32, with a fractional divisor of 255; our code uses the binary fixed-point divisor 256. Their difference is at most 1/256 of a load unit. The exact normalization/reference underlying 100 percent remains untraced, so the percentage label does not imply throttle angle, manifold pressure, or percent of current maximum torque. Production of 0ABD/0ABE is absent from decoded bank-0 stores and appears to require the missing bank. The byte identity and numeric conversion are stronger evidence than a generic Nissan TP description.
