# Control-flow references to/from `$0740–$083F`

Checked 2026-11-16 against the decoded engine ROM 23710-2L904. The range is
inclusive and means **bank 0**, i.e. `$000740–$00083F`.

| Check | Matches |
|---|---:|
| Branch/jump/call destination inside the range | 0 |
| Branch/jump/call instruction address inside the range | 0 |
| Resolved jump-table destination inside the range | 0 |
| Interrupt-vector destination inside the range | 0 |
| Recorded dynamic-transfer instruction address inside the range | 0 |

**No decoded control-flow transfer to or from this range was found.**

This is the Consult payload / active-test / diagnostic-state RAM window, not
code recovered by the ROM disassembler. The ROM image starts at `$1000`, so
there are no decoded source instructions from this RAM window. This does not
prove that runtime RAM execution is impossible. Outgoing transfers from missing
bank-1 code, the untrusted local-ROM hole, or other processor code are unknown;
stack-dependent return destinations are not statically resolved.

`BBC`/`BBS` can **read a RAM address in this range as a branch condition**
without transferring control there. For example, `$40D0` tests `$0808` and
branches to `$4137`; `$4F1A` tests `$071C` and branches to `$4F2F`. These are
data references, not jumps into RAM. Likewise, reading a pointer from `$07A0`
in the direct-data reply path is a data dereference, not an indirect jump.

Evidence: [every resolved control-flow edge](rom-inventory/control_flow.csv),
[destination index](rom-inventory/JUMP_XREFS.md), and
[dynamic transfers](rom-inventory/dynamic_transfers.csv).
The result inherits the decoder's coverage and width-tracking limitations.

To repeat the check after regenerating with `python3 tools/rom_control_flow.py`:

```python
import csv
from pathlib import Path

root = Path('docs/rom-inventory')
for filename, fields in [
    ('control_flow.csv', ('source', 'target')),
    ('dynamic_transfers.csv', ('source',)),
]:
    with (root / filename).open() as stream:
        matches = [row for row in csv.DictReader(stream)
                   if any(0x0740 <= int(row[field], 16) <= 0x083F
                          for field in fields)]
    print(filename, len(matches), matches)
```
