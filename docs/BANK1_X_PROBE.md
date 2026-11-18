# Fixed-X bank-1 helper probe

`tools/bank1_x_probe.py` prepares a 20-address C9 request for the unknown
`JSL $015AD1` at bank-0 `$8A85`. The request builder plants `$080A=$0E`,
`$080B=$08`, and a chosen byte at `$080D`. The bank-0 history shift loads
`X=$080E` and moves the chosen byte into `$080E`. The offline instruction
trace stops before the JSL; it does not model the call's gate, the bank-1
helper, or scheduling. A live session may never take the helper call.
Recorded engine-off RAM dumps did show the gate active and a counter value of
four; see [cross-generation pointer comparison](BANK1_POINTER_COMPARISON.md).

```sh
python3 tools/bank1_x_probe.py --dry-run --pointee 31
python3 tools/bank1_x_probe.py --dry-run --pointee A7
```

Both previews should show `X=$080E`, `A(low)=$0A`, and `$080E` equal to the
selected byte. The live path is explicitly gated by `--run` and accepts only
ECU identity `23710-2L904` with RPM zero and `$088B.0` set. That bit enables
the call counter at `$8A65`; if it is clear, the script sends no mutation.
It takes one mutation attempt per
process, requires its stop acknowledgment, then reinitializes and reads
`$080A-$0810` and `$0C9D`. It records two streaming samples of `$080F`, plus
a JSON report and timestamped raw serial log. A second chosen byte requires a
separate invocation and a fresh baseline.

```sh
python3 tools/bank1_x_probe.py --pointee 31 --run
python3 tools/bank1_x_probe.py --pointee A7 --run
```

Compare the two reports' `stream_080f`, post-stop `080F` and `0C9D`, and
post-stop `080E`. Dependence on the chosen byte suggests the helper consumes
that byte, but does not distinguish an indirect `X` read from a fixed `$080E`
read. A change in `$080E` beyond the normal shift would be stronger evidence
of a store. The stream tap is sampled at frame construction time, not exactly
at the call. Post-stop values may also reflect ordinary ECU tasks. Neither
observation alone establishes arbitrary memory access.
The decision paths after the first hardware result are in
[BANK1_X_CONTINGENCY_PLAN.md](BANK1_X_CONTINGENCY_PLAN.md).

## Reference images (secondary evidence)

The repository contains stock 1996 A32 images, including
`rom/reference/nistune-2.14/extracted/app/ROM_Pack/Type34/A32_VQ30DE/A32_VQ30DE_54U01_1996_MT_BANK2.bin`.
It also contains `A32_VQ30DE_0L701_MT_1997.bin`, whose bank-0 history shift
matches this call site and calls bank 1 at `$015DC9` twice. The exact history
shift byte sequence and the `$015DC9` calls are absent from the 1996 images
checked. Those images are useful for 1996 architecture and stock-versus-FP2
comparison, but do not contain the body of the 1997/98 bank-1 helper.

The modified FP2 bank-2 ENT was retrieved from Nistune's [FP2 ROM Pack
2.22](https://www.nistune.com/support/software-downloads) and saved at
`rom/reference/nistune-fp2-2.22/A32_VQ30DE_54U0F_1996_MT_BANK2_Mod_FP.ent`.
The installer SHA-256 is
`f2cea4db593d84030183f3558a690b58885eb37b9f67c52d1f312065fd19c14e`;
the extracted ENT SHA-256 is
`b96f3923e0d3fc02f81d5a2a7d8023707d34998236e416d3c1ffdfaba70d9162`.
Against the repository's 1996 `54U03` bank-2 ENT, exactly 11 of 8192
eight-byte blocks differ, at `$4778`, `$5228`, `$5888`, `$5890`, `$5898`,
`$BC00`, and `$FFD8-$FFFF`. This is an encrypted-block comparison; those
offsets alone do not identify the modified instructions or their effects.
The FP2 comparison does not resolve `$015AD1` or validate the live probe.
