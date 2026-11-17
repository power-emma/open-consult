# Jump destination cross-reference

Generated from the annotated 23710-2L904 engine ROM; all addresses are hexadecimal.
Six-digit addresses include the bank: `004EF5` is bank 0, `017B08` is bank 1.

**2,980 destinations; 4,670 incoming references; 4,662 source locations.**

Includes taken conditional branches (`BBC`/`BBS` too), `BRA`/`BRL`, jumps, calls,
long bank transfers, all nine entries of the annotated `$CBAB` jump table,
and vector pointers. A vector source is the pointer location, not an executed instruction.
Table edges are possible destinations selected at runtime; they are not all taken together.

Does not include ordinary fall-through. Returns depend on the runtime stack;
they are listed separately in [dynamic_transfers.csv](dynamic_transfers.csv).
Missing bank-1 code and the untrusted `$5D40–$623F` region cannot supply outgoing edges.
Decoded source coverage inherits the disassembler’s width-tracking limitations.

Files: [every edge](control_flow.csv), [destinations](jump_targets.csv),
[sources](jumps_from.csv). Existing `transfers.csv` is a narrower call/jump inventory.

Regenerate: `python3 tools/rom_control_flow.py`.
Query one target: `python3 tools/rom_control_flow.py --target 4EF5`.

| Destination | Label | Status | Sources (instruction address + operation) |
|---|---|---|---|
| `003D00` | L_3D00 | decoded | `005A07` JSL |
| `003D09` | L_3D09 | decoded | `003D05` BCC |
| `003D5E` | L_3D5E | decoded | `003D52` BCC |
| `003D72` | L_3D72 | decoded | `003D5C` BRA |
| `003D74` | L_3D74 | decoded | `003D3E` BEQ |
| `003D75` | reset | decoded | `00FFFE` VECTOR |
| `003D99` | L_3D99 | decoded | `003D8F` BBC |
| `003D9C` | L_3D9C | decoded | `003D97` BRA |
| `003DAD` | L_3DAD | decoded | `003DB3` BNE |
| `003DB8` | L_3DB8 | decoded | `003DBE` BNE |
| `003E0B` | L_3E0B | decoded | `003E05` BNE |
| `003E14` | L_3E14 | decoded | `003E0B` BBC |
| `003E18` | L_3E18 | decoded | `00BCE2` JMP |
| `003EB0` | L_3EB0 | decoded | `003EB6` BNE |
| `003F8F` | L_3F8F | decoded | `003F87` BBS |
| `003F9B` | bram_verify | decoded | `003F95` BEQ |
| `003FA8` | L_3FA8 | decoded | `003FAF` BCC |
| `003FB8` | L_3FB8 | decoded | `003FA1` BNE |
| `003FCF` | L_3FCF | decoded | `003FE1` BCC |
| `003FFD` | L_3FFD | decoded | `003F97` JMP<br>`003FB4` BNE<br>`003FD5` BCS<br>`003FDA` BCC<br>`003FF2` BCS |
| `004002` | adc_task | decoded | `003F8C` JMP<br>`003FB6` BRA<br>`003FFB` BCC |
| `004065` | L_4065 | decoded | `00405C` BBC |
| `00408B` | L_408B | decoded | `004086` BCS |
| `00409E` | L_409E | decoded | `00409A` BEQ |
| `0040C8` | L_40C8 | decoded | `0040C0` BBS |
| `0040E1` | L_40E1 | decoded | `0040DC` BEQ |
| `0040F5` | L_40F5 | decoded | `0040E7` BCC<br>`0040EF` BCC |
| `00410A` | L_410A | decoded | `004116` BRA |
| `004118` | L_4118 | decoded | `004112` BCS |
| `00412F` | L_412F | decoded | `004135` BCC |
| `004137` | L_4137 | decoded | `0040D0` BBS<br>`004125` BBC |
| `004167` | L_4167 | decoded | `004162` BCC |
| `00416C` | L_416C | decoded | `00416F` BNE |
| `0041CD` | L_41CD | decoded | `0041C6` BCS |
| `0041D0` | L_41D0 | decoded | `0041CB` BCC |
| `0041EB` | L_41EB | decoded | `0041E6` BCC |
| `0042CA` | L_42CA | decoded | `0042BD` BBC |
| `00430A` | L_430A | decoded | `004306` BCC |
| `00430F` | L_430F | decoded | `0042F1` BBC<br>`0042F6` BBC |
| `00431D` | L_431D | decoded | `0042DF` BBC<br>`00430D` BRA |
| `00432B` | L_432B | decoded | `004321` BBS |
| `00432E` | L_432E | decoded | `004326` BBC |
| `004361` | L_4361 | decoded | `004358` BBS |
| `00436B` | L_436B | decoded | `004361` BBC |
| `004383` | L_4383 | decoded | `004371` BCC<br>`004378` BCC<br>`00437C` BCS |
| `004386` | L_4386 | decoded | `004369` BRA<br>`004381` BRA |
| `0043AF` | L_43AF | decoded | `0043A2` BBC |
| `0043FD` | L_43FD | decoded | `0043F4` BBC |
| `00441A` | L_441A | decoded | `004406` BBC<br>`00440B` BBC |
| `00442C` | L_442C | decoded | `00441A` BBC |
| `004433` | L_4433 | decoded | `00442C` BBC |
| `00443A` | L_443A | decoded | `004433` BBC |
| `004441` | L_4441 | decoded | `00443A` BBC |
| `004471` | L_4471 | decoded | `004469` BBS |
| `004476` | isr_zero_div | decoded | `00FFFC` VECTOR |
| `00447B` | VEC_DBC | decoded | `00FFF8` VECTOR |
| `00447C` | isr_unused | decoded | `004491` JMP<br>`00FFD4` VECTOR<br>`00FFDC` VECTOR<br>`00FFE0` VECTOR<br>`00FFE2` VECTOR<br>`00FFEA` VECTOR<br>`00FFEC` VECTOR<br>`00FFF0` VECTOR<br>`00FFF2` VECTOR<br>`00FFF6` VECTOR<br>`00FFFA` VECTOR |
| `004495` | isr_ta3_coils | decoded | `00FFE6` VECTOR |
| `0044AE` | L_44AE | decoded | `00449A` BBC<br>`0044A2` BEQ |
| `0044B6` | isr_tb2 | decoded | `00FFDE` VECTOR |
| `0044C4` | L_44C4 | decoded | `0044BB` BBS |
| `0044D4` | L_44D4 | decoded | `0044CB` BBS |
| `0044DD` | L_44DD | decoded | `0044C4` BBC |
| `0044F2` | L_44F2 | decoded | `004525` BBC |
| `00451A` | L_451A | decoded | `0044E3` BBS |
| `004525` | L_4525 | decoded | `0044E8` BBC |
| `00452A` | L_452A | decoded | `00451E` BBC |
| `004530` | L_4530 | decoded | `0044ED` BBC<br>`004523` BRA |
| `004534` | L_4534 | decoded | `0044DE` BBC<br>`004518` BRA<br>`00452E` BRA |
| `004538` | L_4538 | decoded | `0044FB` BCC |
| `004540` | isr_ta4 | decoded | `00FFE4` VECTOR |
| `004558` | L_4558 | decoded | `004553` BCC |
| `004565` | L_4565 | decoded | `00455E` BBS |
| `004572` | L_4572 | decoded | `004545` BBC |
| `004576` | L_4576 | decoded | `00454B` JSL |
| `004579` | L_4579 | decoded | `0044D5` JSL |
| `0046C0` | isr_ta2 | decoded | `00FFE8` VECTOR |
| `0046D0` | L_46D0 | decoded | `0046C5` BBC |
| `0046DE` | L_46DE | decoded | `0046D0` BBC |
| `0046EC` | L_46EC | decoded | `0046DE` BBC |
| `0046F7` | L_46F7 | decoded | `0046EC` BBC |
| `004702` | L_4702 | decoded | `0046F7` BBC |
| `00470D` | L_470D | decoded | `004702` BBC |
| `004711` | L_4711 | decoded | `0046E8` JMP |
| `00471A` | L_471A | decoded | `004715` BNE |
| `00471B` | L_471B | decoded | `0046DA` JMP |
| `004730` | L_4730 | decoded | `00472D` BNE |
| `00473B` | L_473B | decoded | `004735` BCC |
| `00473F` | isr_nmi | decoded | `00FFF4` VECTOR |
| `004757` | L_4757 | decoded | `00474A` BBS |
| `00475C` | L_475C | decoded | `004755` BEQ |
| `004772` | L_4772 | decoded | `00475C` BBC<br>`004767` BNE |
| `00477E` | L_477E | decoded | `004775` BBS |
| `004782` | L_4782 | decoded | `00A45F` JSL<br>`00A485` JSL |
| `004788` | L_4788 | decoded | `00477A` JSL<br>`00A4D2` JSL |
| `004797` | isr_int2_ref | decoded | `00FFEE` VECTOR |
| `0047A8` | L_47A8 | decoded | `00479C` BBC |
| `0047B2` | L_47B2 | decoded | `0047AB` BBC |
| `0047C6` | L_47C6 | decoded | `0047BE` BBC |
| `0047D3` | L_47D3 | decoded | `0047CC` BPL |
| `0047D8` | L_47D8 | decoded | `0047C6` BPL |
| `0047E0` | L_47E0 | decoded | `0047D1` BCS<br>`0047D6` BRA<br>`0047DB` BCC |
| `0047F9` | L_47F9 | decoded | `0047F5` BCC |
| `0047FF` | L_47FF | decoded | `0047FB` BCS |
| `004816` | L_4816 | decoded | `004806` BCC |
| `004827` | L_4827 | decoded | `00480B` BCC<br>`00481C` BCC |
| `00482A` | L_482A | decoded | `0047A4` JMP<br>`004814` BRA<br>`004825` BRA |
| `004849` | L_4849 | decoded | `00483F` BEQ |
| `00486C` | L_486C | decoded | `004866` BEQ |
| `004873` | L_4873 | decoded | `00486C` BBS |
| `00488B` | L_488B | decoded | `004852` BPL<br>`004873` BBC |
| `00488F` | L_488F | decoded | `004871` BRA<br>`004885` BCC |
| `00489A` | L_489A | decoded | `00482D` BBC |
| `00489C` | L_489C | decoded | `004895` BBS |
| `0048AC` | L_48AC | decoded | `00489C` BBC |
| `0048AE` | L_48AE | decoded | `0048A8` BCC |
| `0048B1` | L_48B1 | decoded | `004838` BCS<br>`00489A` BRA |
| `0048BB` | L_48BB | decoded | `0048B4` BBS |
| `0048BF` | L_48BF | decoded | `0048B9` BRA |
| `0048CF` | L_48CF | decoded | `0048BF` BBC |
| `0048DB` | L_48DB | decoded | `0048D7` BCC |
| `0048F6` | L_48F6 | decoded | `0048F1` BCC |
| `004912` | L_4912 | decoded | `0048FE` BEQ |
| `004917` | L_4917 | decoded | `004900` BCC |
| `004922` | L_4922 | decoded | `004910` BRA<br>`004915` BRA |
| `004949` | L_4949 | decoded | `004945` BNE |
| `004956` | L_4956 | decoded | `004951` BCS |
| `004966` | L_4966 | decoded | `004961` BCC |
| `00497A` | L_497A | decoded | `004973` BBS |
| `004992` | L_4992 | decoded | `00496E` BBS<br>`004978` BRA |
| `0049A7` | L_49A7 | decoded | `0049A2` BCS |
| `0049BC` | L_49BC | decoded | `0049B8` BCS |
| `0049C8` | L_49C8 | decoded | `0049BF` BBC |
| `0049D2` | L_49D2 | decoded | `0049F1` BBC |
| `0049E0` | L_49E0 | decoded | `0049D5` BNE<br>`0049F9` BNE |
| `0049EA` | L_49EA | decoded | `0049E6` BCC |
| `0049ED` | L_49ED | decoded | `0049CD` BBC |
| `0049F1` | L_49F1 | decoded | `0049C8` BBC |
| `004A18` | L_4A18 | decoded | `004A12` BNE |
| `004A20` | L_4A20 | decoded | `004A1A` BNE |
| `004A22` | L_4A22 | decoded | `004A16` BRA<br>`004A1E` BRA |
| `004A29` | L_4A29 | decoded | `0049C4` JMP |
| `004A3E` | L_4A3E | decoded | `004A5E` BNE |
| `004A48` | L_4A48 | decoded | `004A44` BCC |
| `004A6C` | L_4A6C | decoded | `004A30` BEQ |
| `004A76` | L_4A76 | decoded | `004A72` BCC |
| `004A7B` | L_4A7B | decoded | `004A6A` BRA |
| `004A8F` | L_4A8F | decoded | `0049ED` JMP<br>`004A32` BCC<br>`004A79` BNE |
| `004A91` | L_4A91 | decoded | `004A8D` BRA |
| `004AC0` | L_4AC0 | decoded | `004ABA` BNE |
| `004AC3` | L_4AC3 | decoded | `004ABE` BRA |
| `004AC7` | L_4AC7 | decoded | `004AB1` BBC |
| `004AE0` | L_4AE0 | decoded | `004ADA` BEQ |
| `004AEB` | L_4AEB | decoded | `004AE0` BBC |
| `004AEE` | L_4AEE | decoded | `00D3F2` JMP |
| `004AF6` | L_4AF6 | decoded | `004AF2` BMI |
| `004B13` | L_4B13 | decoded | `004B06` BBC |
| `004B15` | L_4B15 | decoded | `004B11` BCC |
| `004B32` | L_4B32 | decoded | `004B23` BEQ |
| `004B45` | L_4B45 | decoded | `004B3E` BBC |
| `004B5C` | L_4B5C | decoded | `004B57` BCS |
| `004B60` | L_4B60 | decoded | `004B39` BBC<br>`004B43` BRA |
| `004B6C` | L_4B6C | decoded | `004B68` BCC |
| `004B79` | L_4B79 | decoded | `004B6F` BBS |
| `004B83` | L_4B83 | decoded | `004B7F` BCC |
| `004B95` | L_4B95 | decoded | `004B8D` BNE |
| `004B98` | L_4B98 | decoded | `004B89` BPL<br>`004B93` BRA |
| `004BA9` | L_4BA9 | decoded | `004BA0` BBC |
| `004BC2` | sched_tick | decoded | `00FFDA` VECTOR |
| `004BE0` | L_4BE0 | decoded | `004BD2` BEQ |
| `004C0B` | L_4C0B | decoded | `004BEA` BCC |
| `004C1D` | L_4C1D | decoded | `004C0E` BBC |
| `004C2E` | L_4C2E | decoded | `004C1B` BRA<br>`004C20` BNE<br>`004C28` BEQ |
| `004C3A` | L_4C3A | decoded | `004C2E` BBC<br>`004E42` JMP |
| `004C4D` | L_4C4D | decoded | `004C49` BCC |
| `004C58` | L_4C58 | decoded | `004C52` BCC |
| `004C69` | L_4C69 | decoded | `004C63` BEQ |
| `004C6F` | L_4C6F | decoded | `004C5B` BEQ<br>`004C5F` BEQ |
| `004C73` | task_dispatch | decoded | `004BB2` JMP<br>`004C67` BNE<br>`004C6D` BRA<br>`004C82` BRA<br>`004CD6` BRA<br>`004D6B` JMP<br>`004E36` JMP |
| `004C84` | L_4C84 | decoded | `004C74` BBC |
| `004CD8` | L_4CD8 | decoded | `004C84` BBC |
| `004CE1` | L_4CE1 | decoded | `004CD8` BBS |
| `004D28` | L_4D28 | decoded | `004CFC` BEQ |
| `004D5E` | L_4D5E | decoded | `004D32` BEQ |
| `004D6B` | L_4D6B | decoded | `004D5E` BBC |
| `004D6F` | L_4D6F | decoded | `004CDD` JMP |
| `004D78` | L_4D78 | decoded | `004D6F` BBS |
| `004DD8` | L_4DD8 | decoded | `004DD2` BEQ |
| `004DE3` | L_4DE3 | decoded | `004DD8` BBC |
| `004DEB` | L_4DEB | decoded | `004DE1` BRA |
| `004DF6` | L_4DF6 | decoded | `004DF0` BEQ |
| `004E3A` | L_4E3A | decoded | `004D74` JMP |
| `004E46` | L_4E46 | decoded | `004E3D` BEQ |
| `004E4E` | L_4E4E | decoded | `004D0F` JSL<br>`004D41` JSL |
| `004E61` | L_4E61 | decoded | `004E32` JSL |
| `004EC6` | L_4EC6 | decoded | `004EBF` BBS |
| `004ED6` | L_4ED6 | decoded | `004EB8` BBC |
| `004EF5` | consult_isr | decoded | `00FFD6` VECTOR<br>`00FFD8` VECTOR |
| `004F03` | cs_rx_entry | decoded | `004EFA` BBC |
| `004F2F` | cs_tx_next | decoded | `004F1A` BBS |
| `004F48` | L_4F48 | decoded | `004F40` BBS |
| `004F50` | L_4F50 | decoded | `004F3C` BCC<br>`004F3E` BEQ |
| `004F5F` | L_4F5F | decoded | `004F2D` BRA |
| `004F61` | cs_rx_check | decoded | `004F13` BEQ<br>`004F15` BBC |
| `004F8A` | L_4F8A | decoded | `004FA9` BBS<br>`004FB1` BNE |
| `004F94` | L_4F94 | decoded | `004F81` BBS |
| `004F9C` | L_4F9C | decoded | `004F77` BBS<br>`004F7F` BNE |
| `004FA0` | L_4FA0 | decoded | `004F65` BEQ<br>`004F6C` BEQ<br>`004F92` BRA |
| `004FA4` | cs_wait_id | decoded | `004F72` BBC |
| `004FBF` | cs_have_init | decoded | `004FA4` BBC |
| `004FC8` | cs_cmd_byte | decoded | `004FBF` BBS |
| `004FD6` | cs_parse_cmd | decoded | `004FCD` BBC |
| `004FDB` | cs_cmd_ff | decoded | `005355` JMP<br>`0053FD` JMP |
| `004FE6` | L_4FE6 | decoded | `004FDB` BBC |
| `004FEE` | L_4FEE | decoded | `004FD9` BNE |
| `004FF3` | cs_cmd_stop | decoded | `00535E` JMP<br>`00540F` JMP |
| `004FF7` | L_4FF7 | decoded | `004FE4` BRA |
| `004FFD` | cs_check_c9 | decoded | `004FF1` BNE |
| `005008` | cs_check_5a | decoded | `005000` BNE |
| `005013` | cs_check_0a | decoded | `00500B` BNE |
| `00501C` | L_501C | decoded | `005006` BRA<br>`005011` BRA |
| `005020` | L_5020 | decoded | `004FFB` BRA<br>`00509B` BRA |
| `005024` | cs_check_noarg | decoded | `005016` BNE |
| `005038` | cs_reject | decoded | `004FC8` BBS<br>`0051E3` JMP<br>`00527C` JMP<br>`00533E` JMP |
| `00503C` | cs_cmd_51 | decoded | `005027` BEQ<br>`0053BB` JMP |
| `00508F` | cs_store_cmd | decoded | `00502C` BEQ<br>`005031` BEQ<br>`005036` BEQ |
| `00509D` | cs_arg_byte | decoded | `004FD2` JMP |
| `0050C2` | cs_c9_addr_done | decoded | `0050B5` BBS |
| `0050D2` | cs_arg_5a | decoded | `00509D` BBC |
| `0050DC` | L_50DC | decoded | `0050F4` BEQ<br>`00511B` BCC<br>`005120` BCS<br>`005135` BEQ |
| `0050E0` | L_50E0 | decoded | `0050DA` BCC |
| `005109` | L_5109 | decoded | `0050D0` BRA |
| `00510D` | cs_arg_0a | decoded | `0050D2` BBC |
| `005148` | L_5148 | decoded | `005144` BCC |
| `005163` | L_5163 | decoded | `005189` BRA |
| `005169` | cs_0a_direct | decoded | `005115` BCC |
| `005174` | L_5174 | decoded | `005180` BRA |
| `005182` | L_5182 | decoded | `005178` BEQ |
| `00518B` | cs_0a_value | decoded | `00510D` BBS |
| `0051A4` | L_51A4 | decoded | `00515D` BCC |
| `0051A7` | cs_arg_done | decoded | `005109` JMP<br>`0051C0` BRA<br>`005339` JMP |
| `0051AF` | cs_echo_arg | decoded | `0050BE` JMP<br>`005167` BRA |
| `0051B7` | L_51B7 | decoded | `00518B` BBS |
| `0051C0` | L_51C0 | decoded | `00522E` JMP |
| `0051C2` | L_51C2 | decoded | `0051BA` BNE |
| `0051C6` | L_51C6 | decoded | `0051BC` JMP |
| `0051E7` | L_51E7 | decoded | `0051CA` BBS |
| `0051F0` | L_51F0 | decoded | `0051CF` BBS |
| `0051F9` | L_51F9 | decoded | `0051D4` BBS |
| `005202` | L_5202 | decoded | `0051D9` BBS |
| `00520B` | L_520B | decoded | `0051DE` BBS |
| `005212` | L_5212 | decoded | `0051EE` BRA<br>`0051F7` BRA<br>`005200` BRA<br>`005209` BRA |
| `005223` | L_5223 | decoded | `005237` BRA |
| `005232` | L_5232 | decoded | `00522B` BNE |
| `005239` | L_5239 | decoded | `0051C2` JMP |
| `005248` | L_5248 | decoded | `005240` BCS |
| `005250` | L_5250 | decoded | `005246` BRA |
| `00527C` | L_527C | decoded | `005287` BCS<br>`00529A` BCS<br>`0052A9` BCS<br>`0052B3` BCS<br>`0052C2` BCS<br>`0052CC` BCS<br>`0052DA` BCS<br>`0052E3` BCS<br>`0052F1` BCS<br>`0052FA` BCS |
| `005280` | L_5280 | decoded | `005263` BBS |
| `005293` | L_5293 | decoded | `005289` BBS |
| `005298` | L_5298 | decoded | `005280` BBS |
| `0052A2` | L_52A2 | decoded | `005268` BBS |
| `0052B1` | L_52B1 | decoded | `0052A2` BBS |
| `0052BB` | L_52BB | decoded | `00526D` BBS |
| `0052CA` | L_52CA | decoded | `0052BB` BBS |
| `0052D3` | L_52D3 | decoded | `005272` BBS |
| `0052E1` | L_52E1 | decoded | `0052D3` BBS |
| `0052EA` | L_52EA | decoded | `005277` BBS |
| `0052F8` | L_52F8 | decoded | `0052EA` BBS |
| `0052FF` | L_52FF | decoded | `0052F6` BRA |
| `005309` | L_5309 | decoded | `005301` BEQ<br>`005305` BEQ |
| `00530D` | L_530D | decoded | `005291` BRA<br>`005296` BRA<br>`00529F` JMP<br>`0052AE` JMP<br>`0052B8` JMP<br>`0052C7` JMP<br>`0052D1` BRA<br>`0052DF` BRA<br>`0052E8` BRA<br>`005307` BRA |
| `00533D` | L_533D | decoded | `005325` BEQ<br>`00532F` BEQ |
| `005342` | cs_after_cmd | decoded | `004FC4` JMP |
| `00534B` | L_534B | decoded | `005342` BBS |
| `005359` | L_5359 | decoded | `005353` BNE |
| `005362` | L_5362 | decoded | `00535C` BNE |
| `00538A` | L_538A | decoded | `005381` BBC |
| `00538E` | L_538E | decoded | `005365` BNE |
| `0053A0` | L_53A0 | decoded | `005391` BNE |
| `0053A9` | cs_reply_fe | decoded | `005038` JMP<br>`0050DC` JMP<br>`00534B` BBS<br>`005398` BCS<br>`0053C4` BCS<br>`0053CB` BBS<br>`0053D9` BNE<br>`0053DB` BBS<br>`0053F3` BBS<br>`005404` BNE |
| `0053B6` | L_53B6 | decoded | `0053A3` BEQ |
| `0053BF` | L_53BF | decoded | `0053A7` BEQ<br>`0053B9` BNE |
| `0053D6` | L_53D6 | decoded | `0053C9` BNE |
| `0053E4` | L_53E4 | decoded | `00539E` BRA<br>`0053D4` BRA |
| `0053EE` | cs_streaming | decoded | `005347` JMP |
| `005401` | L_5401 | decoded | `0053FB` BNE |
| `00540F` | L_540F | decoded | `005406` BBC |
| `005413` | cs_echo_cmd | decoded | `005020` JMP<br>`0053EC` BRA |
| `005417` | cs_echo_complement | decoded | `004FBB` JMP<br>`004FEA` JMP |
| `00541A` | cs_send | decoded | `0051B3` JMP<br>`0053B4` BRA |
| `005423` | L_5423 | decoded | `00541A` BBS |
| `005430` | L_5430 | decoded | `00541F` BBS |
| `005437` | cs_isr_exit | decoded | `004FA0` JMP<br>`00538A` JMP<br>`0053EE` BBC<br>`00542E` BRA |
| `00543F` | c9_find_hidden | decoded | `005386` JSL |
| `005451` | L_5451 | decoded | `0054C4` BCC |
| `00547E` | L_547E | decoded | `005472` BCS |
| `00548D` | L_548D | decoded | `00547C` BRA |
| `0054B7` | L_54B7 | decoded | `00546D` BCC<br>`00547E` BBC<br>`005486` BCC<br>`00548B` BCS |
| `0054C7` | consult_reset | decoded | `004F26` JSL<br>`004FF7` JSL<br>`0053AD` JSL<br>`005430` JSL<br>`00998B` JSL |
| `0054EC` | L_54EC | decoded | `0054E1` BBC |
| `0054F0` | L_54F0 | decoded | `0054EA` BRA |
| `005513` | L_5513 | decoded | `00550A` BBS |
| `00551E` | L_551E | decoded | `0054CD` BBC |
| `00551F` | adc_read_maf | decoded | `004C7E` JSL |
| `005526` | L_5526 | decoded | `005526` BBC |
| `005531` | L_5531 | decoded | `0040B0` JSL |
| `00553B` | L_553B | decoded | `005536` BCS |
| `005575` | L_5575 | decoded | `005584` BCC |
| `00557F` | L_557F | decoded | `005570` BBC |
| `0055A8` | L_55A8 | decoded | `005593` BCS |
| `0055B0` | L_55B0 | decoded | `00559E` BCC<br>`0055A6` BRA |
| `0055D7` | L_55D7 | decoded | `0055D1` BCS |
| `0055E1` | L_55E1 | decoded | `00557D` BRA<br>`0055B0` BBC<br>`0055B5` BBC<br>`0055BF` BCC<br>`0055DB` BCC |
| `005600` | L_5600 | decoded | `004C8E` JSL |
| `005613` | L_5613 | decoded | `00560E` BCS |
| `005620` | L_5620 | decoded | `005605` BCC |
| `005624` | calc_rpm | decoded | `004C92` JSL |
| `00562B` | L_562B | decoded | `005634` BNE |
| `005640` | L_5640 | decoded | `00563D` BCC |
| `005665` | L_5665 | decoded | `005662` BCC |
| `00566F` | L_566F | decoded | `00566C` BCC |
| `00567C` | L_567C | decoded | `005679` BCC |
| `00569E` | L_569E | decoded | `00568A` BBC<br>`00568F` BBS |
| `0056A5` | L_56A5 | decoded | `004C9A` JSL |
| `0056DA` | L_56DA | decoded | `0056A5` BBC |
| `0056F9` | L_56F9 | decoded | `0056F1` BBC |
| `005722` | L_5722 | decoded | `005711` BCS<br>`005716` BCS<br>`00571B` BCS |
| `005725` | L_5725 | decoded | `005720` BCC |
| `005730` | L_5730 | decoded | `004CA2` JSL |
| `00573B` | L_573B | decoded | `005736` BEQ |
| `00577D` | L_577D | decoded | `005778` BCC |
| `005781` | L_5781 | decoded | `00573B` BBC<br>`005740` BBS<br>`00574A` BCC<br>`00574F` BNE |
| `005786` | L_5786 | decoded | `005758` BCS |
| `0057A0` | L_57A0 | decoded | `005789` BCS |
| `0057A5` | L_57A5 | decoded | `00578F` BCC |
| `0057A7` | L_57A7 | decoded | `00579E` BRA<br>`0057A3` BRA |
| `0057DA` | L_57DA | decoded | `00579A` BCC<br>`00579C` BEQ |
| `0057EB` | L_57EB | decoded | `0057AD` BCC |
| `0057EF` | L_57EF | decoded | `005784` BRA<br>`0057B5` BCC<br>`0057B7` BBC<br>`0057C3` BCS<br>`0057C8` BEQ<br>`0057CA` BCC<br>`0057D2` BCC<br>`0057D4` BEQ<br>`0057E9` BRA |
| `0057FF` | L_57FF | decoded | `0057F9` BCS |
| `005808` | L_5808 | decoded | `005802` BCC |
| `00581D` | L_581D | decoded | `005825` BNE |
| `005830` | L_5830 | decoded | `005838` BNE |
| `00586B` | L_586B | decoded | `005860` BBC |
| `005876` | L_5876 | decoded | `00586B` BBC |
| `00588A` | L_588A | decoded | `0057FB` JMP<br>`005804` JMP |
| `0058A2` | L_58A2 | decoded | `00589A` BCS |
| `0058AF` | L_58AF | decoded | `0058A0` BRA<br>`0058A7` BCC |
| `0058B3` | L_58B3 | decoded | `00585E` BNE |
| `0058C7` | L_58C7 | decoded | `005869` BRA<br>`005874` BRA<br>`00587B` BBC |
| `0058CF` | L_58CF | decoded | `005876` BBC<br>`005888` BRA |
| `0058DD` | L_58DD | decoded | `0058D2` BBC |
| `0058E5` | L_58E5 | decoded | `0058DB` BRA<br>`0058E0` BCC |
| `0058FC` | L_58FC | decoded | `0058E9` BBC |
| `005906` | L_5906 | decoded | `0058FA` BRA |
| `005929` | L_5929 | decoded | `005926` BEQ |
| `00593E` | L_593E | decoded | `00592F` BEQ |
| `00593F` | L_593F | decoded | `00593C` BCC |
| `005973` | L_5973 | decoded | `0059CF` BBC |
| `00597D` | L_597D | decoded | `0059DC` BBS |
| `00598E` | L_598E | decoded | `005988` BCC |
| `0059A3` | L_59A3 | decoded | `005997` BMI |
| `0059B4` | L_59B4 | decoded | `00599D` BCC<br>`0059A1` BRA<br>`0059B0` BCS |
| `0059BB` | L_59BB | decoded | `00598C` BCS<br>`005991` BEQ<br>`0059E1` BBC |
| `0059C5` | L_59C5 | decoded | `00597B` BRA<br>`0059BB` BBS |
| `0059CF` | L_59CF | decoded | `00596E` BBC |
| `0059E6` | L_59E6 | decoded | `0059B7` BCC<br>`0059B9` BEQ<br>`0059C0` BBC<br>`0059DA` BCS |
| `0059FC` | L_59FC | decoded | `0059F9` BCC |
| `005A2D` | L_5A2D | decoded | `005A29` BCC |
| `005A41` | L_5A41 | decoded | `005A3D` BCC |
| `005A49` | L_5A49 | decoded | `0059CB` JMP<br>`005A0E` BBC<br>`005A13` BBC<br>`005A44` BCS |
| `005A58` | L_5A58 | decoded | `005A52` BCS |
| `005A61` | L_5A61 | decoded | `005A58` BBS |
| `005A8C` | L_5A8C | decoded | `005A61` BBC<br>`005A66` BBS<br>`005A6B` BBC<br>`005A75` BCC<br>`005A7C` BCC<br>`005A84` BCC |
| `005A90` | L_5A90 | decoded | `005A8A` BRA |
| `005A91` | L_5A91 | decoded | `0040A1` JSL<br>`0058CB` JSL |
| `005AD4` | L_5AD4 | decoded | `0040A5` JSL |
| `005AEB` | L_5AEB | decoded | `005AE6` BCC |
| `005AF0` | L_5AF0 | decoded | `005884` JSL |
| `005B05` | L_5B05 | decoded | `005AF8` BCS |
| `005B0A` | L_5B0A | decoded | `005B03` BRA |
| `005B1F` | L_5B1F | decoded | `005B1B` BEQ |
| `005B25` | L_5B25 | decoded | `005B44` BCC<br>`005B46` BEQ<br>`005B53` BCC<br>`005B55` BEQ<br>`005B62` BCC<br>`005B64` BEQ |
| `005B36` | L_5B36 | decoded | `005B27` BBC |
| `005B3E` | L_5B3E | decoded | `005B30` BCC<br>`005B34` BRA<br>`005B3A` BCS |
| `005B50` | L_5B50 | decoded | `005B4B` BCS |
| `005B5F` | L_5B5F | decoded | `005B5A` BCS |
| `005B6A` | L_5B6A | decoded | `005B8C` BCC<br>`005B8E` BEQ |
| `005B7D` | L_5B7D | decoded | `005B6C` BBC |
| `005B86` | L_5B86 | decoded | `005B76` BCC<br>`005B7B` BRA<br>`005B81` BCS |
| `005B92` | L_5B92 | decoded | `004CA6` JSL |
| `005BC5` | L_5BC5 | decoded | `005BC1` BCC |
| `005BCA` | L_5BCA | decoded | `005BB9` BCC |
| `005BD7` | L_5BD7 | decoded | `005BD3` BCC |
| `005BE0` | L_5BE0 | decoded | `005BBD` BCC<br>`005BCF` BCC |
| `005BE4` | L_5BE4 | decoded | `005BC8` BRA |
| `005BE8` | L_5BE8 | decoded | `005B9A` BCC<br>`005BDE` BRA |
| `005C07` | L_5C07 | decoded | `005BF9` BCC |
| `005C0A` | L_5C0A | decoded | `005C01` BEQ<br>`005C05` BRA |
| `005C1F` | L_5C1F | decoded | `005C1B` BCC |
| `005C25` | L_5C25 | decoded | `005C1D` BNE |
| `005C2B` | L_5C2B | decoded | `005BEF` BCC |
| `005C44` | L_5C44 | decoded | `005C36` BCC |
| `005C47` | L_5C47 | decoded | `005C3E` BEQ<br>`005C42` BRA |
| `005C5C` | L_5C5C | decoded | `005C58` BCC |
| `005C62` | L_5C62 | decoded | `005C5A` BNE |
| `005C66` | L_5C66 | decoded | `005C23` BRA<br>`005C29` BRA<br>`005C60` BRA |
| `005C75` | L_5C75 | decoded | `005C70` BCS |
| `005C79` | L_5C79 | decoded | `004CAA` JSL |
| `005C8D` | L_5C8D | decoded | `005C81` BCS<br>`005C86` BCS |
| `005C90` | L_5C90 | decoded | `005C8B` BCC |
| `005CAF` | L_5CAF | decoded | `005CA8` BCS |
| `005CB2` | L_5CB2 | decoded | `005C93` BBC<br>`005CAD` BCC |
| `005CBD` | L_5CBD | decoded | `004CAE` JSL |
| `005CE7` | L_5CE7 | decoded | `005CDB` BNE |
| `005CEF` | L_5CEF | decoded | `005CE5` BCC |
| `005D0C` | L_5D0C | decoded | `005D09` BCC |
| `005D0D` | L_5D0D | decoded | `005D03` BCC |
| `005D0E` | L_5D0E | decoded | `005CFD` BCC |
| `005D1A` | L_5D1A | decoded | `005CED` BRA |
| `005D23` | L_5D23 | decoded | `005CCF` BBC |
| `005D2B` | L_5D2B | decoded | `005D21` BRA |
| `005ED2` | L_5ED2 | untrusted_dump_hole | `005D23` JSL |
| `005F1B` | L_5F1B | untrusted_dump_hole | `004CB2` JSL |
| `00644C` | L_644C | decoded | `004CB6` JSL |
| `006455` | L_6455 | decoded | `00644C` BBS |
| `006469` | L_6469 | decoded | `00645C` BCC<br>`006461` BCC |
| `00646D` | L_646D | decoded | `006467` BRA |
| `006478` | L_6478 | decoded | `0065E8` JMP |
| `006497` | L_6497 | decoded | `006489` BEQ |
| `0064CA` | L_64CA | decoded | `0064C5` BCS |
| `0064CC` | L_64CC | decoded | `0064B6` BBS<br>`0064BE` BMI |
| `0064D1` | L_64D1 | decoded | `00649E` BCC<br>`0064AE` BCC |
| `0064DA` | L_64DA | decoded | `0064CF` BRA |
| `0064E6` | L_64E6 | decoded | `0064E1` BPL |
| `0064F7` | L_64F7 | decoded | `0064EC` BBC |
| `0064FA` | L_64FA | decoded | `0064F5` BRA |
| `006511` | L_6511 | decoded | `006519` BRA |
| `00651B` | L_651B | decoded | `006514` BEQ |
| `00652E` | L_652E | decoded | `00651E` BEQ |
| `006531` | L_6531 | decoded | `006527` BCC<br>`00652C` BRA |
| `00654C` | L_654C | decoded | `006540` BCS<br>`006545` BCS |
| `00654F` | L_654F | decoded | `00654A` BCC |
| `006586` | L_6586 | decoded | `00657A` BCS<br>`00657F` BCS |
| `00658B` | L_658B | decoded | `00655A` BCC |
| `0065B8` | L_65B8 | decoded | `0065AC` BCS<br>`0065B1` BCS |
| `0065BB` | L_65BB | decoded | `0065B6` BCC |
| `0065BF` | L_65BF | decoded | `006584` BCC<br>`006589` BRA |
| `0065D6` | L_65D6 | decoded | `006493` JMP<br>`0064D6` JMP |
| `0065DE` | L_65DE | decoded | `0065D4` BRA |
| `0065EC` | L_65EC | decoded | `0065E6` BEQ |
| `006607` | L_6607 | decoded | `006451` JMP<br>`0065FE` BEQ |
| `006626` | L_6626 | decoded | `006608` BBS |
| `006643` | L_6643 | decoded | `006624` BRA |
| `006648` | L_6648 | decoded | `00661C` BPL<br>`00663B` BPL |
| `006652` | L_6652 | decoded | `00661E` BBS<br>`00663D` BBS<br>`00664B` BCC |
| `006656` | L_6656 | decoded | `006646` BRA<br>`006650` BRA |
| `006660` | L_6660 | decoded | `0064D2` JSL |
| `006686` | L_6686 | decoded | `00667F` BCS |
| `00668B` | L_668B | decoded | `006663` BCS |
| `0066B0` | L_66B0 | decoded | `0066A9` BCS |
| `0066B3` | L_66B3 | decoded | `0066AE` BCC |
| `0066B7` | L_66B7 | decoded | `006684` BCC<br>`006689` BRA |
| `0066BA` | L_66BA | decoded | `004CBA` JSL |
| `0066EA` | L_66EA | decoded | `0066D6` BNE |
| `0066ED` | L_66ED | decoded | `0066E8` BRA |
| `006700` | L_6700 | decoded | `0066F5` BBC |
| `006708` | L_6708 | decoded | `0066FE` BRA<br>`006703` BEQ |
| `00670D` | L_670D | decoded | `006728` BCS |
| `006722` | L_6722 | decoded | `006708` BBS |
| `006732` | L_6732 | decoded | `006720` BRA |
| `00677C` | L_677C | decoded | `006771` BNE |
| `006781` | L_6781 | decoded | `006763` BCC |
| `0067A0` | L_67A0 | decoded | `006791` BNE |
| `0067A3` | L_67A3 | decoded | `00674A` BBS<br>`00677A` BRA<br>`00677F` BRA<br>`00679E` BRA |
| `0067BF` | L_67BF | decoded | `0067B4` BCS |
| `0067C2` | L_67C2 | decoded | `0067BD` BRA |
| `0067D7` | L_67D7 | decoded | `0067D3` BCS |
| `0067E6` | L_67E6 | decoded | `0067AD` BPL<br>`0067E1` BCS |
| `006809` | L_6809 | decoded | `0067F7` BPL |
| `00680F` | L_680F | decoded | `006807` BRA |
| `006822` | L_6822 | decoded | `006815` BPL |
| `006827` | L_6827 | decoded | `006817` BBS |
| `00682B` | L_682B | decoded | `006825` BCS |
| `00682E` | L_682E | decoded | `006820` BRA<br>`006829` BRA |
| `00683A` | L_683A | decoded | `004CBE` JSL |
| `006854` | L_6854 | decoded | `00683A` BBC |
| `006864` | L_6864 | decoded | `00683F` BBS |
| `006870` | L_6870 | decoded | `006852` BRA<br>`00685B` BNE<br>`00686A` BCC |
| `006885` | L_6885 | decoded | `006881` BCC |
| `0068C5` | L_68C5 | decoded | `0068C1` BCS |
| `0068D1` | L_68D1 | decoded | `0068CD` BCC |
| `0068EB` | L_68EB | decoded | `0068B0` BCS<br>`0068B5` BCS |
| `0068EE` | L_68EE | decoded | `006861` JMP<br>`0068E9` BCC |
| `0068F3` | L_68F3 | decoded | `004CC2` JSL |
| `006911` | L_6911 | decoded | `006901` BCS |
| `006915` | L_6915 | decoded | `0068FA` BPL |
| `006926` | L_6926 | decoded | `006916` BCS |
| `006927` | L_6927 | decoded | `00690F` BCS<br>`006913` BRA<br>`006924` BCC |
| `006953` | L_6953 | decoded | `006930` BEQ<br>`006945` BCS |
| `006962` | L_6962 | decoded | `006951` BRA |
| `006980` | L_6980 | decoded | `006974` BCS<br>`006979` BCS |
| `006981` | L_6981 | decoded | `00697E` BCC |
| `006990` | L_6990 | decoded | `006989` BCC |
| `006998` | L_6998 | decoded | `00698B` BBC<br>`006993` BCS |
| `0069A0` | L_69A0 | decoded | `006998` BBS |
| `0069CA` | L_69CA | decoded | `0069BD` BEQ<br>`0069BF` BBS |
| `0069CD` | L_69CD | decoded | `0069C8` BRA |
| `0069EB` | L_69EB | decoded | `0069DE` BEQ<br>`0069E0` BBS |
| `0069EE` | L_69EE | decoded | `0069E9` BRA |
| `0069F7` | L_69F7 | decoded | `0069CD` JSL<br>`0069EE` JSL |
| `006A1E` | L_6A1E | decoded | `006A07` BCS<br>`006A12` BCS<br>`006A17` BCS |
| `006A1F` | L_6A1F | decoded | `006A1C` BCC |
| `006A20` | calc_injection | decoded | `004CC6` JSL |
| `006A2D` | L_6A2D | decoded | `006A99` JMP |
| `006A3B` | L_6A3B | decoded | `006A36` BNE |
| `006A5A` | L_6A5A | decoded | `006A45` BPL |
| `006A67` | L_6A67 | decoded | `006A53` BCS<br>`006A58` BRA<br>`006A62` BCC |
| `006A68` | L_6A68 | decoded | `006A41` BNE |
| `006A7E` | L_6A7E | decoded | `006A6D` BPL |
| `006A89` | L_6A89 | decoded | `006A82` BCC |
| `006A8D` | L_6A8D | decoded | `006A77` BCC<br>`006A7C` BRA<br>`006A87` BRA |
| `006A9D` | L_6A9D | decoded | `006A97` BCS |
| `006AB2` | L_6AB2 | decoded | `006AA8` BBS |
| `006AB5` | L_6AB5 | decoded | `006AB0` BRA |
| `006AC2` | L_6AC2 | decoded | `006AB8` BBS |
| `006AC5` | L_6AC5 | decoded | `006AC0` BRA |
| `006AC9` | L_6AC9 | decoded | `004CCA` JSL |
| `006AD3` | L_6AD3 | decoded | `006ACE` BCC |
| `006AEC` | L_6AEC | decoded | `006ADD` BBC |
| `006AFA` | L_6AFA | decoded | `006AE3` BBC |
| `006AFE` | L_6AFE | decoded | `006B2B` BRA |
| `006B1A` | L_6B1A | decoded | `006B10` BCS<br>`006B15` BCS |
| `006B1C` | L_6B1C | decoded | `006B04` BNE |
| `006B1F` | L_6B1F | decoded | `006B1A` BRA |
| `006B2D` | L_6B2D | decoded | `006AF8` BRA<br>`006B26` BCS |
| `006B4D` | L_6B4D | decoded | `006B43` BBC |
| `006B57` | L_6B57 | decoded | `006B4B` BRA |
| `006B5D` | L_6B5D | decoded | `006B59` BCC |
| `006B87` | L_6B87 | decoded | `006B82` BCS |
| `006BAB` | L_6BAB | decoded | `006BA7` BEQ |
| `006BBC` | L_6BBC | decoded | `006BB8` BCS |
| `006BCF` | L_6BCF | decoded | `006BC9` BEQ |
| `006BD2` | L_6BD2 | decoded | `006BC4` BCS |
| `006BD7` | L_6BD7 | decoded | `006BCD` BRA |
| `006BDA` | L_6BDA | decoded | `006BD5` BCC |
| `006C0F` | L_6C0F | decoded | `004CE6` JSL |
| `006C23` | L_6C23 | decoded | `006C17` BNE |
| `006C2F` | L_6C2F | decoded | `006C21` BRA<br>`006C25` BNE |
| `006C3C` | L_6C3C | decoded | `006C2F` BBS<br>`006C37` BEQ |
| `006C57` | L_6C57 | decoded | `006C41` BCS |
| `006C6A` | L_6C6A | decoded | `006C62` BNE |
| `006C6D` | L_6C6D | decoded | `006C46` BCC<br>`006C4C` BNE<br>`006C55` BRA<br>`006C5B` BCS<br>`006C68` BRA |
| `006C73` | L_6C73 | decoded | `004CEA` JSL |
| `006C79` | L_6C79 | decoded | `006C73` BBS |
| `006C86` | L_6C86 | decoded | `006C80` BEQ |
| `006C8F` | L_6C8F | decoded | `006C89` BEQ |
| `006C98` | L_6C98 | decoded | `006C92` BEQ |
| `006CA0` | L_6CA0 | decoded | `006C9B` BNE |
| `006CA9` | L_6CA9 | decoded | `006CA4` BEQ |
| `006CB2` | L_6CB2 | decoded | `006CAC` BEQ |
| `006CBB` | L_6CBB | decoded | `006CB5` BEQ |
| `006CC4` | L_6CC4 | decoded | `006CBE` BEQ |
| `006CCC` | L_6CCC | decoded | `006CC7` BNE |
| `006CD5` | L_6CD5 | decoded | `006CD0` BEQ |
| `006CFD` | L_6CFD | decoded | `006CD5` BBC |
| `006D01` | L_6D01 | decoded | `006CDA` BBC<br>`006CE9` BCC<br>`006CF1` BCC<br>`006CF9` BCC |
| `006D06` | L_6D06 | decoded | `006CFB` BRA |
| `006D17` | L_6D17 | decoded | `006D01` BBC |
| `006D34` | L_6D34 | decoded | `006D17` BBC<br>`006D22` BCC<br>`006D2A` BCC |
| `006D38` | L_6D38 | decoded | `006D06` BBS<br>`006D15` BRA<br>`006D32` BCS |
| `006D42` | L_6D42 | decoded | `006D38` BBS |
| `006D4A` | L_6D4A | decoded | `006D45` BNE |
| `006D54` | L_6D54 | decoded | `006D3D` BBC |
| `006D64` | L_6D64 | decoded | `006D4D` BNE<br>`006D52` BRA |
| `006D65` | fuel_feedback | decoded | `004D15` JSL<br>`004D47` JSL |
| `006D75` | L_6D75 | decoded | `006D6D` BBC |
| `006D80` | L_6D80 | decoded | `006D78` BCC |
| `006D8F` | L_6D8F | decoded | `006D87` BBC |
| `006D9A` | L_6D9A | decoded | `006D92` BCC |
| `006D9E` | L_6D9E | decoded | `006D7E` BRA<br>`006D98` BRA<br>`006D9E` BBC |
| `006DC1` | L_6DC1 | decoded | `006DB3` BBC |
| `006DD5` | L_6DD5 | decoded | `006DC1` BBS<br>`006DC6` BBS<br>`006DCB` BBC |
| `006DDD` | L_6DDD | decoded | `006DD0` BBC |
| `006DE2` | L_6DE2 | decoded | `006DDB` BRA |
| `006DE8` | L_6DE8 | decoded | `006DDD` BBS |
| `006DFA` | L_6DFA | decoded | `006DF3` BBS |
| `006E09` | L_6E09 | decoded | `006DEC` BBS<br>`006DFD` BNE<br>`006DFF` BBC |
| `006E0D` | L_6E0D | decoded | `006E04` BBC |
| `006E23` | L_6E23 | decoded | `006E1F` BCS |
| `006E29` | L_6E29 | decoded | `006E25` BCC |
| `006E35` | L_6E35 | decoded | `006E15` BBC |
| `006E3A` | L_6E3A | decoded | `007266` JMP |
| `006E49` | L_6E49 | decoded | `006E44` BNE |
| `006E55` | L_6E55 | decoded | `006E35` BBC |
| `006E5E` | L_6E5E | decoded | `006E55` BBC |
| `006E71` | L_6E71 | decoded | `006E68` BBC |
| `006E79` | L_6E79 | decoded | `006E73` BEQ |
| `006E81` | L_6E81 | decoded | `006E7B` BEQ |
| `006E96` | L_6E96 | decoded | `006E81` BBC<br>`006E8C` BCC |
| `006EAA` | L_6EAA | decoded | `006EA0` BCC |
| `006EB0` | L_6EB0 | decoded | `006E94` BCS<br>`006EA8` BRA |
| `006EBE` | L_6EBE | decoded | `006EB5` BCS |
| `006EC4` | L_6EC4 | decoded | `006EC0` BEQ |
| `006ED1` | L_6ED1 | decoded | `006EBA` BCC |
| `006EDC` | L_6EDC | decoded | `006ECF` BRA |
| `006EE9` | L_6EE9 | decoded | `006EDE` BBC |
| `006EED` | L_6EED | decoded | `006EE7` BRA |
| `006F09` | L_6F09 | decoded | `006E75` JMP<br>`006E7D` JMP<br>`006EA6` BCC<br>`006EAE` BCC<br>`006EBC` BRA |
| `006F0E` | L_6F0E | decoded | `006EC2` BRA<br>`006ED3` BNE |
| `006F14` | L_6F14 | decoded | `006E5A` JMP |
| `006F1D` | L_6F1D | decoded | `006F14` BBS |
| `006F21` | L_6F21 | decoded | `006E6D` JMP |
| `006F3D` | L_6F3D | decoded | `006F33` BBC |
| `006F40` | L_6F40 | decoded | `006F3B` BRA |
| `006F54` | L_6F54 | decoded | `006F12` BRA<br>`0073D7` JMP |
| `006F67` | L_6F67 | decoded | `006F5B` BBC<br>`0070FA` JMP |
| `006F77` | L_6F77 | decoded | `006F67` BBC |
| `006F89` | L_6F89 | decoded | `006F82` BCC<br>`006F92` BCS<br>`006F97` BCS |
| `006F8E` | L_6F8E | decoded | `006F7C` BCC |
| `006F99` | L_6F99 | decoded | `006F52` BRA<br>`006F87` BCS<br>`006F8C` BRA |
| `006FAC` | L_6FAC | decoded | `006F9B` BBS |
| `006FB1` | L_6FB1 | decoded | `006F05` JMP<br>`006F19` JMP |
| `006FC8` | L_6FC8 | decoded | `006FB5` BBC |
| `006FD1` | L_6FD1 | decoded | `006FC8` BBS |
| `006FD9` | L_6FD9 | decoded | `006FD3` BEQ |
| `006FF0` | L_6FF0 | decoded | `006FE8` BCS |
| `006FF4` | L_6FF4 | decoded | `006FEE` BRA |
| `007003` | L_7003 | decoded | `006FD9` BBC |
| `00700C` | L_700C | decoded | `006FE0` BNE<br>`007090` JMP<br>`00709D` JMP |
| `007022` | L_7022 | decoded | `00701B` BNE |
| `007027` | L_7027 | decoded | `007011` BBS<br>`00701D` BBS |
| `00703D` | L_703D | decoded | `007038` BCS |
| `007054` | L_7054 | decoded | `00704F` BCC |
| `007060` | L_7060 | decoded | `00700C` BBS<br>`007022` BBC<br>`00702C` BCC |
| `007070` | L_7070 | decoded | `007065` BEQ |
| `007080` | L_7080 | decoded | `007070` BBS<br>`007078` BEQ |
| `007087` | L_7087 | decoded | `006FCD` JMP |
| `007094` | L_7094 | decoded | `007087` BBS |
| `0070A1` | L_70A1 | decoded | `007098` BBS |
| `0070B8` | L_70B8 | decoded | `0070AE` BBS |
| `0070BD` | L_70BD | decoded | `00707E` BRA |
| `0070C4` | L_70C4 | decoded | `00706E` BRA<br>`007083` BNE |
| `0070C8` | L_70C8 | decoded | `006E51` JMP<br>`006FC4` JMP<br>`0070C2` BRA |
| `0070CD` | L_70CD | decoded | `006FD5` JMP<br>`00708E` BNE |
| `0070D8` | L_70D8 | decoded | `0070B6` BRA<br>`0070BB` BRA<br>`0070D0` BBS |
| `0070DA` | L_70DA | decoded | `006FFF` JMP<br>`0070CB` BRA |
| `0070E2` | L_70E2 | decoded | `007127` BRA<br>`007139` BRA<br>`0071B4` JMP |
| `0070F6` | L_70F6 | decoded | `0070ED` BBC |
| `0070FE` | L_70FE | decoded | `007085` BRA |
| `007108` | L_7108 | decoded | `0070FE` BBS<br>`00710C` BBS |
| `00710C` | L_710C | decoded | `007103` BBS |
| `007129` | L_7129 | decoded | `007111` BBS |
| `00713B` | L_713B | decoded | `007130` BEQ |
| `00714E` | L_714E | decoded | `00713B` BBS |
| `007154` | L_7154 | decoded | `007150` BPL |
| `00715F` | L_715F | decoded | `007159` BCC |
| `00716C` | L_716C | decoded | `00715F` BBS |
| `00717D` | L_717D | decoded | `00716C` BBC |
| `007183` | L_7183 | decoded | `007152` BRA<br>`00716A` BRA |
| `00719E` | L_719E | decoded | `007194` BBC |
| `0071A1` | L_71A1 | decoded | `00719C` BRA |
| `0071A5` | L_71A5 | decoded | `00717B` BRA |
| `0071B8` | L_71B8 | decoded | `007108` JMP |
| `0071D0` | L_71D0 | decoded | `007181` BRA<br>`0071C3` BBC |
| `0071E8` | L_71E8 | decoded | `0071DE` BBC |
| `0071ED` | L_71ED | decoded | `0071D9` BBS |
| `0071EF` | L_71EF | decoded | `0071CE` BRA<br>`0071E6` BRA<br>`0071EB` BRA |
| `0071F5` | L_71F5 | decoded | `00715B` JMP<br>`007187` BCC<br>`0071D0` BBC |
| `007200` | L_7200 | decoded | `0071FC` BCS |
| `007208` | L_7208 | decoded | `007202` BCC |
| `00720A` | L_720A | decoded | `007206` BRA |
| `007212` | L_7212 | decoded | `00720E` BCS |
| `007226` | L_7226 | decoded | `00721D` BCS |
| `007229` | L_7229 | decoded | `007222` BEQ<br>`007224` BCC |
| `007231` | L_7231 | decoded | `00722C` BCS |
| `007249` | L_7249 | decoded | `007234` BBS |
| `007257` | L_7257 | decoded | `007247` BRA |
| `00726A` | L_726A | decoded | `007240` BCC<br>`007242` BBC<br>`007250` BCC<br>`007252` BBC |
| `00726E` | L_726E | decoded | `00725F` BCS |
| `007278` | L_7278 | decoded | `007272` BCS |
| `007284` | L_7284 | decoded | `00727D` BBC |
| `00728A` | L_728A | decoded | `007278` BBS |
| `007292` | L_7292 | decoded | `007288` BRA |
| `0072A4` | L_72A4 | decoded | `00729A` BBS |
| `0072A7` | L_72A7 | decoded | `0072A2` BRA |
| `0072AD` | L_72AD | decoded | `007292` BBS |
| `0072B1` | L_72B1 | decoded | `0072AB` BRA |
| `0072BB` | L_72BB | decoded | `0072B1` BBS |
| `0072C1` | L_72C1 | decoded | `0072B9` BRA |
| `0072DD` | L_72DD | decoded | `0072D9` BCS |
| `0072E7` | L_72E7 | decoded | `007282` BRA |
| `0072F3` | L_72F3 | decoded | `0072EE` BCS |
| `007304` | L_7304 | decoded | `0072FF` BCC |
| `007308` | L_7308 | decoded | `007274` JMP |
| `007316` | L_7316 | decoded | `00730D` BBS |
| `00731C` | L_731C | decoded | `007308` BBS |
| `007324` | L_7324 | decoded | `00731A` BRA |
| `007336` | L_7336 | decoded | `00732C` BBS |
| `007339` | L_7339 | decoded | `007334` BRA |
| `00733F` | L_733F | decoded | `007324` BBS |
| `007343` | L_7343 | decoded | `00733D` BRA |
| `007351` | L_7351 | decoded | `007343` BBC |
| `00735B` | L_735B | decoded | `007351` BBS |
| `007361` | L_7361 | decoded | `00734F` BRA<br>`007359` BRA |
| `007367` | L_7367 | decoded | `007312` JMP |
| `007373` | L_7373 | decoded | `00736E` BCC |
| `007384` | L_7384 | decoded | `007304` JMP<br>`00737F` BCS |
| `00738E` | L_738E | decoded | `007384` BBS |
| `007391` | L_7391 | decoded | `007389` BBC |
| `0073CA` | L_73CA | decoded | `0073BC` BNE |
| `0073D7` | L_73D7 | decoded | `0073C6` JMP<br>`0073CD` BNE |
| `0073DB` | L_73DB | decoded | `007396` BCC |
| `0073DF` | L_73DF | decoded | `00705C` JMP |
| `0073F5` | L_73F5 | decoded | `0073E9` BCS |
| `0073F8` | L_73F8 | decoded | `0073F3` BRA<br>`00740E` BRA<br>`007413` BRA |
| `0073FF` | L_73FF | decoded | `0073DF` BBS |
| `007410` | L_7410 | decoded | `007404` BCS |
| `007415` | L_7415 | decoded | `006E31` JMP<br>`0073EE` BCS<br>`0073FD` BRA<br>`007409` BCS |
| `00742E` | L_742E | decoded | `007415` BBC<br>`00741F` BNE |
| `007431` | L_7431 | decoded | `007426` BCC<br>`00742C` BRA |
| `007439` | L_7439 | decoded | `006DBD` JMP<br>`006FAD` JMP |
| `00743B` | L_743B | decoded | `007434` BBC |
| `007451` | L_7451 | decoded | `007440` BBC |
| `00745B` | L_745B | decoded | `00744F` BRA |
| `00747C` | L_747C | decoded | `007284` JSL<br>`007316` JSL |
| `00748E` | L_748E | decoded | `00728E` JSL<br>`007320` JSL<br>`00747E` BPL |
| `0074A7` | L_74A7 | decoded | `00749B` BBC |
| `0074BD` | L_74BD | decoded | `0074B2` BBC |
| `0074C1` | L_74C1 | decoded | `0074BB` BRA |
| `0074D0` | L_74D0 | decoded | `0074C3` BBC |
| `0074D5` | L_74D5 | decoded | `0074CE` BRA |
| `0074DF` | L_74DF | decoded | `0074DB` BNE |
| `0074E3` | L_74E3 | decoded | `0072A7` JSL<br>`007339` JSL |
| `0074EC` | L_74EC | decoded | `0072AD` JSL<br>`00733F` JSL |
| `0074F9` | L_74F9 | decoded | `0074F0` BBS |
| `00750D` | L_750D | decoded | `00748E` JSL |
| `00751A` | L_751A | decoded | `007513` BBC |
| `007533` | L_7533 | decoded | `00753A` BCS |
| `007537` | L_7537 | decoded | `007529` BBS |
| `00753C` | L_753C | decoded | `007531` BCC<br>`007535` BRA |
| `007553` | L_7553 | decoded | `007548` BCC |
| `007563` | L_7563 | decoded | `007558` BCS |
| `007569` | L_7569 | decoded | `007541` BCC |
| `00756A` | L_756A | decoded | `006E0D` JSL |
| `0075A9` | L_75A9 | decoded | `007586` BEQ<br>`007588` BCC<br>`00758A` BBC |
| `0075BE` | L_75BE | decoded | `0075A7` BRA<br>`007616` JMP |
| `0075C3` | L_75C3 | decoded | `007575` BBC |
| `0075D5` | L_75D5 | decoded | `0075C9` BCC<br>`0075CB` BBS |
| `0075DF` | L_75DF | decoded | `0075D0` BBC |
| `0075FA` | L_75FA | decoded | `0075E6` BBS |
| `007606` | L_7606 | decoded | `0075F7` JMP |
| `007619` | L_7619 | decoded | `0075DC` JMP<br>`0075E4` BCC |
| `007635` | L_7635 | decoded | `00762F` BCC |
| `007639` | L_7639 | decoded | `00762A` BCC |
| `00763D` | L_763D | decoded | `007625` BCC |
| `007654` | L_7654 | decoded | `007650` BCC |
| `007656` | L_7656 | decoded | `00764B` BCC |
| `007658` | L_7658 | decoded | `007646` BCC |
| `00766F` | L_766F | decoded | `007665` BBS |
| `00767E` | L_767E | decoded | `007675` BBS |
| `0076AC` | L_76AC | decoded | `007691` BBS<br>`007696` BBS |
| `0076B8` | L_76B8 | decoded | `0076AA` BRA |
| `0076C5` | L_76C5 | decoded | `0076BB` BBC |
| `0076C8` | L_76C8 | decoded | `0076C3` BRA |
| `0076DF` | L_76DF | decoded | `0076D6` BCC |
| `0076E8` | L_76E8 | decoded | `0076DB` BCS |
| `0076EB` | L_76EB | decoded | `0076DD` BRA<br>`0076E6` BCC |
| `007705` | L_7705 | decoded | `0076FA` BCC<br>`007701` BCC |
| `00771D` | L_771D | decoded | `007714` BBC |
| `00772F` | L_772F | decoded | `00772A` BCC |
| `007732` | L_7732 | decoded | `0075BF` JMP |
| `007740` | L_7740 | decoded | `007735` BBC |
| `007743` | L_7743 | decoded | `00773E` BRA |
| `007765` | L_7765 | decoded | `00775E` BCS |
| `007768` | L_7768 | decoded | `007763` BCC |
| `00777B` | L_777B | decoded | `007776` BCC |
| `007792` | L_7792 | decoded | `00778A` BBS |
| `0077AF` | L_77AF | decoded | `0077A6` BBC |
| `0077BA` | L_77BA | decoded | `007785` BBC<br>`0077B5` BNE |
| `0077CB` | L_77CB | decoded | `0077C2` BBC |
| `0077CF` | L_77CF | decoded | `00739A` JSL |
| `0077DA` | L_77DA | decoded | `0077D6` BNE |
| `0077F9` | L_77F9 | decoded | `0077E7` BBC |
| `007804` | L_7804 | decoded | `007800` BEQ |
| `00780F` | L_780F | decoded | `00780B` BNE |
| `007826` | L_7826 | decoded | `007802` BCS |
| `007842` | L_7842 | decoded | `007834` BBC<br>`007839` BBS |
| `00784D` | L_784D | decoded | `007849` BNE |
| `007862` | L_7862 | decoded | `007804` BBC<br>`00780F` BBC<br>`00781C` BNE<br>`007820` BNE<br>`007824` BRA<br>`007829` BCC<br>`00782E` BCS<br>`007842` BBC<br>`00784D` BBC<br>`00785A` BNE<br>`00785E` BNE |
| `00786C` | L_786C | decoded | `006C27` JSL |
| `007892` | L_7892 | decoded | `00786C` BBC |
| `00789F` | L_789F | decoded | `007898` BCS |
| `0078A9` | L_78A9 | decoded | `0078A6` BEQ |
| `0078AC` | L_78AC | decoded | `007890` BRA<br>`00789D` BRA |
| `0078B2` | L_78B2 | decoded | `0078AC` BBC |
| `0078C5` | L_78C5 | decoded | `0078BA` BBS |
| `0078C9` | L_78C9 | decoded | `0078C3` BRA |
| `0078D9` | L_78D9 | decoded | `0078B5` BBC |
| `0078E0` | L_78E0 | decoded | `0078D7` BRA |
| `0078E8` | L_78E8 | decoded | `0078E3` BNE |
| `0078F0` | L_78F0 | decoded | `0078EB` BNE |
| `0078FF` | L_78FF | decoded | `0078F0` BBS |
| `007908` | L_7908 | decoded | `0078FF` BBS |
| `007929` | L_7929 | decoded | `007918` BCC |
| `00792E` | L_792E | decoded | `0078FD` BRA<br>`007963` BCC |
| `007935` | L_7935 | decoded | `00792C` BCC |
| `007942` | L_7942 | decoded | `007927` BRA |
| `00794B` | L_794B | decoded | `007945` BCS |
| `007950` | L_7950 | decoded | `00790D` BBS |
| `007965` | L_7965 | decoded | `00795B` BCS |
| `00796F` | L_796F | decoded | `007950` BBS |
| `007970` | L_7970 | decoded | `007908` BBS |
| `007986` | L_7986 | decoded | `007976` BCC |
| `007992` | L_7992 | decoded | `007984` BRA |
| `0079A0` | L_79A0 | decoded | `00799D` BNE |
| `0079AA` | L_79AA | decoded | `0079A7` BNE |
| `0079AD` | L_79AD | decoded | `007947` JMP<br>`007978` BBS<br>`007986` BBC |
| `0079AE` | L_79AE | decoded | `0078D0` JSL |
| `0079C6` | L_79C6 | decoded | `0079CD` BNE |
| `0079CF` | L_79CF | decoded | `0079C4` BEQ |
| `0079D2` | L_79D2 | decoded | `0074F5` JSL |
| `0079E1` | L_79E1 | decoded | `0079D2` BBC<br>`0079D7` BBS |
| `0079E7` | L_79E7 | decoded | `0079DC` BBC |
| `0079F3` | L_79F3 | decoded | `0079E7` BBC |
| `0079FD` | L_79FD | decoded | `0079F1` BRA |
| `007A08` | L_7A08 | decoded | `0079FD` BBS |
| `007A0C` | L_7A0C | decoded | `007A06` BRA |
| `007A54` | L_7A54 | decoded | `0079F3` BBC |
| `007A5D` | L_7A5D | decoded | `0079EC` BBC<br>`0079F8` BBC |
| `007A65` | L_7A65 | decoded | `0079E5` BRA<br>`007A5B` BEQ |
| `007A6B` | L_7A6B | decoded | `007A16` BBC<br>`007A21` BCC<br>`007A29` BCC<br>`007A31` BEQ<br>`007A33` BCC<br>`007A3B` BCC<br>`007A3D` BBS<br>`007A48` BCC<br>`007A52` BRA<br>`007A63` BRA |
| `007A7E` | L_7A7E | decoded | `007A77` BCC |
| `007A83` | L_7A83 | decoded | `007A0C` JSL |
| `007A8A` | L_7A8A | decoded | `007A83` BBS |
| `007A9A` | L_7A9A | decoded | `007A90` BCC<br>`007A92` BEQ |
| `007AA5` | L_7AA5 | decoded | `007A88` BRA<br>`007A9D` BCS |
| `007AA6` | L_7AA6 | decoded | `007A4E` JSL |
| `007AAD` | L_7AAD | decoded | `007AA6` BBS |
| `007ABD` | L_7ABD | decoded | `007AB3` BCC<br>`007AB5` BEQ |
| `007AC8` | L_7AC8 | decoded | `007AAB` BRA<br>`007AC0` BCS |
| `007AC9` | L_7AC9 | decoded | `007A02` JSL |
| `007AF0` | L_7AF0 | decoded | `007AD9` BCC |
| `007AFF` | L_7AFF | decoded | `007AE9` BCS<br>`007AEE` BRA<br>`007AFA` BCC |
| `007B1B` | L_7B1B | decoded | `007B0B` BCS<br>`007B16` BCC |
| `007B24` | L_7B24 | decoded | `007A08` JSL |
| `007B45` | L_7B45 | decoded | `007B2C` BBS |
| `007B4D` | L_7B4D | decoded | `007B2A` BCS |
| `007B66` | L_7B66 | decoded | `007B4D` BBC |
| `007B6C` | L_7B6C | decoded | `007B4B` BRA |
| `007B79` | L_7B79 | decoded | `007B70` BBC |
| `007B8C` | L_7B8C | decoded | `007B87` BCS |
| `007BA6` | L_7BA6 | decoded | `007B92` BBC |
| `007BB5` | L_7BB5 | decoded | `007B9F` BCC<br>`007BA4` BRA<br>`007BB0` BCS |
| `007BB9` | L_7BB9 | decoded | `007B43` BRA<br>`007B64` BRA |
| `007BC4` | L_7BC4 | decoded | `007BB5` JSL<br>`007FA0` JSL |
| `007BCC` | L_7BCC | decoded | `007B3F` JSL<br>`007B60` JSL |
| `007BDB` | L_7BDB | decoded | `007BCF` BCC |
| `007BDE` | L_7BDE | decoded | `007BD9` BRA |
| `007BE1` | L_7BE1 | decoded | `007BD4` BCC |
| `007BE2` | L_7BE2 | decoded | `007C64` JSL |
| `007C0B` | L_7C0B | decoded | `007A4A` JSL |
| `007C1A` | L_7C1A | decoded | `007C11` BCS |
| `007C1F` | L_7C1F | decoded | `007C13` BBC |
| `007C23` | L_7C23 | decoded | `007C18` BRA<br>`007C1A` BBC |
| `007C36` | L_7C36 | decoded | `007C30` BCS |
| `007C42` | L_7C42 | decoded | `007C37` BCS<br>`007C3A` BCS |
| `007C45` | L_7C45 | decoded | `007C40` BRA |
| `007C84` | L_7C84 | decoded | `007C74` BCS<br>`007C7F` BCC |
| `007C8F` | L_7C8F | decoded | `007C1F` JMP |
| `007C90` | L_7C90 | decoded | `007BED` JSL<br>`007BFF` JSL |
| `007C9F` | L_7C9F | decoded | `007C93` BPL |
| `007CA8` | L_7CA8 | decoded | `007C9D` BRA |
| `007CC3` | L_7CC3 | decoded | `007CB1` BBS<br>`007CC0` BNE |
| `007CC7` | L_7CC7 | decoded | `004CCE` JSL |
| `007CD0` | L_7CD0 | decoded | `007CC7` BBS |
| `007D02` | L_7D02 | decoded | `007CF7` BBC |
| `007D0A` | L_7D0A | decoded | `007D00` BRA |
| `007D15` | L_7D15 | decoded | `007CD6` BCC<br>`007CDB` BCS<br>`007CE3` BCC<br>`007CE8` BCS<br>`007CF0` BCC<br>`007CF5` BCS |
| `007D1D` | L_7D1D | decoded | `007D0A` BBC |
| `007D25` | L_7D25 | decoded | `007D13` BRA |
| `007D49` | L_7D49 | decoded | `007D30` BCS |
| `007D4D` | L_7D4D | decoded | `007D38` BCC |
| `007D6A` | L_7D6A | decoded | `007D3A` BBC<br>`007D47` BRA<br>`007D5D` BBC |
| `007D70` | L_7D70 | decoded | `007D25` BBC |
| `007D7E` | L_7D7E | decoded | `007D53` BCC |
| `007D82` | L_7D82 | decoded | `007D5B` BCC<br>`007D6E` BRA<br>`007D7C` BRA |
| `007DA6` | L_7DA6 | decoded | `007D8D` BCS |
| `007DAA` | L_7DAA | decoded | `007D95` BCC |
| `007DC7` | L_7DC7 | decoded | `007D97` BBC<br>`007DA4` BRA<br>`007DBA` BBC |
| `007DCD` | L_7DCD | decoded | `007DB0` BCC |
| `007DD3` | L_7DD3 | decoded | `007D82` BBC |
| `007DDF` | L_7DDF | decoded | `007DB8` BCC<br>`007DCB` BRA<br>`007DD1` BRA |
| `007DF6` | L_7DF6 | decoded | `007DEB` BCS<br>`007DF0` BCS |
| `007E08` | L_7E08 | decoded | `007DDF` BBC<br>`007DFD` BCC<br>`007E02` BCC |
| `007E1F` | L_7E1F | decoded | `007E14` BCS<br>`007E19` BCS |
| `007E31` | L_7E31 | decoded | `007E08` BBC<br>`007E26` BCC<br>`007E2B` BCC |
| `007E5E` | L_7E5E | decoded | `007E3E` BBC |
| `007E62` | L_7E62 | decoded | `007E39` BBC<br>`007E49` BCS<br>`007E4F` BBC<br>`007E5C` BRA |
| `007E71` | L_7E71 | decoded | `007E6A` BBS |
| `007E7E` | L_7E7E | decoded | `007E68` BCC<br>`007E6F` BRA<br>`007E71` BBC |
| `007E86` | L_7E86 | decoded | `007E37` BCC |
| `007EB3` | L_7EB3 | decoded | `007E93` BBC |
| `007EB7` | L_7EB7 | decoded | `007E8E` BBC<br>`007E9E` BCS<br>`007EA4` BBC<br>`007EB1` BRA |
| `007EC6` | L_7EC6 | decoded | `007EBF` BBS |
| `007ED3` | L_7ED3 | decoded | `007EBD` BCC<br>`007EC4` BRA<br>`007EC6` BBC |
| `007EDB` | L_7EDB | decoded | `007E8C` BCC |
| `007EEE` | L_7EEE | decoded | `007EE2` BBC |
| `007F05` | L_7F05 | decoded | `007EF8` BBC<br>`007F01` BCS |
| `007F1B` | L_7F1B | decoded | `007F11` BEQ<br>`007F13` BCC |
| `007F1F` | L_7F1F | decoded | `007F19` BRA |
| `007F2F` | L_7F2F | decoded | `007F22` BBS<br>`007F2B` BCC |
| `007F45` | L_7F45 | decoded | `007F3B` BEQ<br>`007F3D` BCC |
| `007F49` | L_7F49 | decoded | `007F43` BRA |
| `007F53` | L_7F53 | decoded | `007F49` BBC |
| `007F66` | L_7F66 | decoded | `007F5A` BBC |
| `007F8B` | L_7F8B | decoded | `007F7B` BCS |
| `007F97` | L_7F97 | decoded | `007F84` BVC<br>`007F89` BRA<br>`007F92` BVC |
| `007F9C` | L_7F9C | decoded | `007F4E` BBC |
| `007FA0` | L_7FA0 | decoded | `007F9A` BRA |
| `007FBE` | L_7FBE | decoded | `007CCC` JMP |
| `007FBF` | L_7FBF | decoded | `004CD2` JSL |
| `007FE3` | L_7FE3 | decoded | `007FDD` BCC<br>`007FEC` BRA |
| `007FEE` | L_7FEE | decoded | `007FD7` BEQ<br>`007FE3` BEQ |
| `008016` | L_8016 | decoded | `008010` BCC<br>`00801F` BRA |
| `008021` | L_8021 | decoded | `00800A` BEQ<br>`008016` BEQ |
| `008035` | L_8035 | decoded | `008028` BBC |
| `008039` | L_8039 | decoded | `008032` JMP |
| `008044` | L_8044 | decoded | `00802D` BBC |
| `00804F` | L_804F | decoded | `00804A` BCS |
| `008065` | L_8065 | decoded | `008054` BNE |
| `008074` | L_8074 | decoded | `00806F` BCS |
| `008098` | L_8098 | decoded | `008067` BNE |
| `0080A7` | L_80A7 | decoded | `0080A2` BCS |
| `0080D1` | L_80D1 | decoded | `00809A` BNE |
| `008101` | L_8101 | decoded | `008041` JMP<br>`00804C` JMP<br>`008062` JMP<br>`008071` JMP<br>`008095` JMP<br>`0080A4` JMP<br>`0080CE` JMP<br>`0080D7` BCC |
| `008102` | L_8102 | decoded | `004D5A` JSL |
| `008118` | L_8118 | decoded | `008113` BNE |
| `008122` | L_8122 | decoded | `008102` BBC |
| `00812B` | L_812B | decoded | `00811B` BNE<br>`008120` BRA |
| `008133` | L_8133 | decoded | `008107` BBC<br>`008122` BBS<br>`00812E` BNE |
| `008149` | L_8149 | decoded | `008144` BNE |
| `008153` | L_8153 | decoded | `008133` BBC |
| `00815C` | L_815C | decoded | `00814C` BNE<br>`008151` BRA |
| `008164` | L_8164 | decoded | `008138` BBC<br>`008153` BBS<br>`00815F` BNE |
| `008165` | L_8165 | decoded | `007502` JSL |
| `008171` | L_8171 | decoded | `008167` BBS |
| `008182` | L_8182 | decoded | `008175` BCS |
| `008187` | L_8187 | decoded | `008180` BRA |
| `0081A2` | L_81A2 | decoded | `008191` BBS |
| `0081AB` | L_81AB | decoded | `0081A6` BCC |
| `0081B3` | L_81B3 | decoded | `00819B` BCS<br>`0081A0` BRA<br>`0081AE` BCC |
| `0081B8` | L_81B8 | decoded | `00893E` JSL |
| `0081E8` | L_81E8 | decoded | `0081E1` BCS |
| `0081ED` | L_81ED | decoded | `0081BE` BCC<br>`0081C3` BCS<br>`0081CB` BCC<br>`0081D0` BCS<br>`0081D8` BCC |
| `0081F8` | L_81F8 | decoded | `0081E6` BCC<br>`0081EB` BRA<br>`0081F4` BCS |
| `0081FC` | L_81FC | decoded | `004E22` JSL |
| `00823C` | L_823C | decoded | `008202` BCC<br>`008207` BCS<br>`00820F` BCC<br>`008214` BCS<br>`00821C` BCC<br>`008221` BCS |
| `008249` | L_8249 | decoded | `008240` BBC |
| `00824D` | L_824D | decoded | `008223` BBS<br>`00823A` BRA |
| `008273` | L_8273 | decoded | `008257` BCC |
| `008288` | L_8288 | decoded | `008259` BBS<br>`00825E` BBS<br>`008271` BRA<br>`008277` BBS |
| `008289` | L_8289 | decoded | `00824D` JSL |
| `0082B7` | L_82B7 | decoded | `0082B0` BCS |
| `0082BC` | L_82BC | decoded | `0082A5` BCS |
| `0082C1` | L_82C1 | decoded | `00829A` BCS |
| `0082E7` | L_82E7 | decoded | `0082E3` BCS |
| `0082E9` | L_82E9 | decoded | `0082D8` BCS |
| `0082EB` | L_82EB | decoded | `0082CD` BCS |
| `008305` | L_8305 | decoded | `0082F3` BBS<br>`0082FB` BEQ |
| `008309` | L_8309 | decoded | `0070AA` JSL |
| `008320` | L_8320 | decoded | `008311` BBC |
| `00832A` | L_832A | decoded | `008326` BCS |
| `008335` | L_8335 | decoded | `008330` BCC |
| `008354` | L_8354 | decoded | `008348` BBC |
| `008358` | L_8358 | decoded | `008352` BRA |
| `008361` | L_8361 | decoded | `00835B` BCC |
| `008369` | L_8369 | decoded | `00830F` BEQ<br>`008316` BBS<br>`00831B` BBS |
| `00836A` | L_836A | decoded | `007460` JSL |
| `00837E` | L_837E | decoded | `00836F` BBC |
| `00838C` | L_838C | decoded | `00837F` BBC |
| `008391` | L_8391 | decoded | `00838A` BRA |
| `008392` | L_8392 | decoded | `00836A` BBS<br>`008374` BBS |
| `008393` | L_8393 | decoded | `008379` BBC |
| `00839F` | L_839F | decoded | `00839A` BCC |
| `0083AC` | L_83AC | decoded | `0083B5` BRA |
| `0083B7` | L_83B7 | decoded | `0083AC` BEQ |
| `0083CA` | L_83CA | decoded | `0083C4` BCS |
| `0083D5` | L_83D5 | decoded | `0083DB` BNE |
| `0083E5` | L_83E5 | decoded | `00839F` BBC |
| `0083ED` | L_83ED | decoded | `0083F6` BRA |
| `0083F8` | L_83F8 | decoded | `0083ED` BEQ |
| `00840B` | L_840B | decoded | `008405` BCS |
| `008416` | L_8416 | decoded | `00841C` BNE |
| `008424` | L_8424 | decoded | `0083E3` BRA |
| `008426` | L_8426 | decoded | `004D7D` JSL |
| `00842E` | L_842E | decoded | `008429` BNE |
| `008435` | L_8435 | decoded | `009500` JSL |
| `00843F` | L_843F | decoded | `008433` BCS |
| `008440` | calc_switches | decoded | `004054` JSL<br>`004D81` JSL |
| `008451` | L_8451 | decoded | `00844A` BBS |
| `00845C` | L_845C | decoded | `008451` BBS |
| `00846E` | L_846E | decoded | `008460` BBC<br>`008469` BCS |
| `008476` | L_8476 | decoded | `008472` BCC |
| `008488` | L_8488 | decoded | `00847A` BBC<br>`008483` BCS |
| `008490` | L_8490 | decoded | `00848C` BCC |
| `008492` | L_8492 | decoded | `00845A` BEQ |
| `0084A0` | L_84A0 | decoded | `00849B` BCS |
| `0084AC` | L_84AC | decoded | `0084A2` BBC |
| `0084AF` | L_84AF | decoded | `0084AA` BRA |
| `0084BE` | L_84BE | decoded | `008474` BNE<br>`00848E` BNE |
| `0084C6` | L_84C6 | decoded | `008490` BRA<br>`0084BA` BCC<br>`0084BC` BEQ |
| `0084D0` | L_84D0 | decoded | `0084C4` BRA |
| `0084DA` | L_84DA | decoded | `0084D3` BBC |
| `0084E7` | L_84E7 | decoded | `0084E1` BCC |
| `0084F0` | L_84F0 | decoded | `0084EA` BCS |
| `0084F7` | L_84F7 | decoded | `0084F0` BBC |
| `00850A` | L_850A | decoded | `0084F7` BBS<br>`0084FC` BBC<br>`008504` BEQ |
| `00850E` | L_850E | decoded | `008508` BRA |
| `00851A` | L_851A | decoded | `00850F` BBC |
| `008539` | L_8539 | decoded | `00852A` BBS<br>`008535` BEQ |
| `00853D` | L_853D | decoded | `008525` BBS<br>`008537` BCS |
| `008550` | L_8550 | decoded | `008544` BBC |
| `00856B` | L_856B | decoded | `008555` BBS |
| `00857A` | L_857A | decoded | `00856B` BBS<br>`008576` BEQ |
| `00857E` | L_857E | decoded | `008578` BCS |
| `008583` | L_8583 | decoded | `008549` BBS |
| `008589` | L_8589 | decoded | `008550` BBC |
| `00859F` | L_859F | decoded | `008589` BBC |
| `0085A4` | L_85A4 | decoded | `00854E` BRA |
| `0085A8` | L_85A8 | decoded | `008581` BNE<br>`008587` BRA<br>`0085A2` BNE |
| `0085D2` | L_85D2 | decoded | `0085A8` BBS<br>`0085CA` BCS |
| `0085D6` | L_85D6 | decoded | `0085D0` BRA |
| `008600` | L_8600 | decoded | `0085D6` BBS<br>`0085F8` BCS |
| `008604` | L_8604 | decoded | `0085FE` BRA |
| `00862E` | L_862E | decoded | `008604` BBS<br>`008626` BCS |
| `008632` | L_8632 | decoded | `00862C` BRA |
| `008650` | L_8650 | decoded | `008642` BBC<br>`008647` BBS |
| `00865E` | L_865E | decoded | `008650` BBC<br>`008655` BBS |
| `00866C` | L_866C | decoded | `00865E` BBC<br>`008663` BBS |
| `008675` | L_8675 | decoded | `00866C` BBC |
| `00867E` | L_867E | decoded | `008675` BBC |
| `008687` | L_8687 | decoded | `00867E` BBC |
| `008690` | L_8690 | decoded | `008687` BBS |
| `00869D` | L_869D | decoded | `004D85` JSL |
| `0086C0` | L_86C0 | decoded | `0086BC` BEQ |
| `0086E6` | L_86E6 | decoded | `0086E3` BCC |
| `0086F6` | L_86F6 | decoded | `0086F3` BCC |
| `008717` | L_8717 | decoded | `0086F9` BBS<br>`0086FF` BBC<br>`008705` BBC<br>`00870B` BBS |
| `008720` | L_8720 | decoded | `008711` BBC |
| `008737` | L_8737 | decoded | `00872F` BCC |
| `00873C` | L_873C | decoded | `008727` BCC |
| `008771` | L_8771 | decoded | `008759` BCS |
| `008774` | L_8774 | decoded | `008735` BRA |
| `00877E` | L_877E | decoded | `00876B` BCS<br>`00876F` BRA<br>`00877B` BCC |
| `00879A` | L_879A | decoded | `00878A` BCC<br>`008795` BCS |
| `00879E` | L_879E | decoded | `00871C` JMP<br>`00873A` BRA<br>`008746` BCC<br>`00874E` BCC<br>`008753` BCS |
| `00879F` | L_879F | decoded | `004D89` JSL |
| `0087B0` | L_87B0 | decoded | `00879F` BBC |
| `0087C9` | L_87C9 | decoded | `0087BA` BBS |
| `0087D1` | L_87D1 | decoded | `0087C7` BRA<br>`0087CC` BNE<br>`0087EC` BCS<br>`0087F8` BEQ<br>`008800` BCS |
| `0087D7` | L_87D7 | decoded | `0087B5` BBC |
| `0087F0` | L_87F0 | decoded | `0087D7` BBC |
| `0087F5` | L_87F5 | decoded | `0087EE` BRA |
| `008806` | L_8806 | decoded | `0087B0` BBC<br>`0087D5` BRA<br>`0087F0` BBC |
| `00880E` | L_880E | decoded | `008809` BNE |
| `008816` | L_8816 | decoded | `008811` BEQ |
| `00881E` | L_881E | decoded | `008819` BEQ |
| `008826` | L_8826 | decoded | `008821` BEQ |
| `00882E` | L_882E | decoded | `008829` BEQ |
| `008836` | L_8836 | decoded | `008831` BNE |
| `00883E` | L_883E | decoded | `008839` BNE |
| `008846` | L_8846 | decoded | `008841` BNE |
| `008851` | L_8851 | decoded | `00884D` BCS |
| `00885C` | L_885C | decoded | `008857` BNE |
| `00887A` | L_887A | decoded | `008875` BCS |
| `00887D` | L_887D | decoded | `00886F` BEQ |
| `00887E` | L_887E | decoded | `00885C` BBS |
| `00888D` | L_888D | decoded | `00887E` BBS |
| `008891` | L_8891 | decoded | `008886` BNE<br>`00888B` BRA |
| `00889C` | L_889C | decoded | `008899` BNE |
| `0088B3` | L_88B3 | decoded | `0088A4` BBS |
| `0088B7` | L_88B7 | decoded | `00889F` BBC<br>`0088A9` BBC<br>`0088AE` BBS |
| `0088C6` | L_88C6 | decoded | `0088BF` BEQ |
| `0088DA` | L_88DA | decoded | `0088D1` BBS |
| `0088FA` | L_88FA | decoded | `0088B7` BBC<br>`0088C4` BRA<br>`0088C6` BBC<br>`0088CB` BBS |
| `008911` | L_8911 | decoded | `0088FB` BBS<br>`008906` BCC |
| `008913` | L_8913 | decoded | `00890C` BNE<br>`00890F` BRA |
| `008922` | L_8922 | decoded | `008919` BBC |
| `008939` | L_8939 | decoded | `008933` BNE |
| `00893A` | L_893A | decoded | `00892F` BEQ |
| `008958` | L_8958 | decoded | `008953` BNE |
| `008961` | L_8961 | decoded | `008946` BBS<br>`00894B` BBC<br>`00895C` BEQ |
| `008969` | L_8969 | decoded | `008964` BEQ |
| `008971` | L_8971 | decoded | `00896C` BNE |
| `00897F` | L_897F | decoded | `008979` BEQ |
| `008988` | L_8988 | decoded | `008982` BEQ |
| `008996` | L_8996 | decoded | `008990` BEQ |
| `00899F` | L_899F | decoded | `008999` BEQ |
| `0089A7` | L_89A7 | decoded | `0089A2` BNE |
| `0089AF` | L_89AF | decoded | `008971` BBC<br>`008988` BBS<br>`0089AA` BNE |
| `0089B7` | L_89B7 | decoded | `0089B2` BNE |
| `0089C5` | L_89C5 | decoded | `0089C0` BNE |
| `0089CD` | L_89CD | decoded | `0089C8` BNE |
| `0089DB` | L_89DB | decoded | `0089D6` BNE |
| `0089E3` | L_89E3 | decoded | `0089DE` BNE |
| `0089EB` | L_89EB | decoded | `0089E6` BNE |
| `0089FA` | L_89FA | decoded | `0089EB` BBC |
| `0089FE` | L_89FE | decoded | `0089F3` BNE<br>`0089F8` BRA |
| `008A05` | L_8A05 | decoded | `008A02` BNE |
| `008A10` | L_8A10 | decoded | `008A0B` BNE |
| `008A17` | L_8A17 | decoded | `008A14` BNE |
| `008A28` | L_8A28 | decoded | `008A1A` BBC |
| `008A2C` | L_8A2C | decoded | `008A1F` BBS |
| `008A3C` | L_8A3C | decoded | `008A37` BCS |
| `008A50` | L_8A50 | decoded | `008A48` BCC |
| `008A65` | L_8A65 | decoded | `008A28` JMP |
| `008A70` | L_8A70 | decoded | `008A65` BBS |
| `008A77` | L_8A77 | decoded | `008A74` BNE |
| `008AC6` | L_8AC6 | decoded | `008A6E` BRA<br>`008A7C` BCC |
| `008AD3` | L_8AD3 | decoded | `008AC6` BBS |
| `008AE1` | L_8AE1 | decoded | `008ADB` BCS |
| `008AE9` | L_8AE9 | decoded | `008AD1` BRA<br>`008AE4` BCC |
| `008B06` | L_8B06 | decoded | `008B02` BCS |
| `008B09` | L_8B09 | decoded | `008AF6` BBS |
| `008B11` | L_8B11 | decoded | `008B0C` BNE |
| `008B19` | L_8B19 | decoded | `008B14` BNE |
| `008B21` | L_8B21 | decoded | `008B1C` BNE |
| `008B29` | L_8B29 | decoded | `008B24` BNE |
| `008B31` | L_8B31 | decoded | `008B2C` BNE |
| `008B39` | L_8B39 | decoded | `008B34` BNE |
| `008B41` | L_8B41 | decoded | `008B3C` BNE |
| `008B49` | L_8B49 | decoded | `008B44` BNE |
| `008B51` | L_8B51 | decoded | `008B4C` BNE |
| `008B59` | L_8B59 | decoded | `008B54` BNE |
| `008B68` | L_8B68 | decoded | `008B5E` BCC<br>`008B63` BNE |
| `008BAC` | L_8BAC | decoded | `008B68` BBC<br>`008B73` BCC<br>`008B7B` BCC<br>`008B83` BEQ<br>`008B85` BCC<br>`008B8D` BCC<br>`008B8F` BBS<br>`008B9A` BCC<br>`008BA7` BNE |
| `008BAE` | L_8BAE | decoded | `008BA2` BCC |
| `008BC0` | L_8BC0 | decoded | `008BB1` BBC |
| `008BC4` | L_8BC4 | decoded | `008BB9` BNE<br>`008BBE` BRA |
| `008BD3` | L_8BD3 | decoded | `008BC4` BBC |
| `008BD7` | L_8BD7 | decoded | `008BCC` BNE<br>`008BD1` BRA |
| `008BDF` | L_8BDF | decoded | `008BDA` BNE |
| `008BE7` | L_8BE7 | decoded | `008BE2` BNE |
| `008BEF` | L_8BEF | decoded | `008BEA` BNE |
| `008C02` | L_8C02 | decoded | `008BFC` BEQ |
| `008C0A` | L_8C0A | decoded | `008BEF` BBC<br>`008BF4` BBS<br>`008C05` BNE |
| `008C1D` | L_8C1D | decoded | `008C17` BEQ |
| `008C25` | L_8C25 | decoded | `008C0A` BBC<br>`008C0F` BBS<br>`008C20` BNE |
| `008C2D` | L_8C2D | decoded | `008C28` BNE |
| `008C35` | L_8C35 | decoded | `008C30` BNE |
| `008C3D` | L_8C3D | decoded | `008C38` BNE |
| `008C45` | L_8C45 | decoded | `008C40` BNE |
| `008C4D` | L_8C4D | decoded | `008C48` BNE |
| `008C55` | L_8C55 | decoded | `008C50` BNE |
| `008C63` | L_8C63 | decoded | `008C5E` BNE |
| `008C6B` | L_8C6B | decoded | `008C66` BNE |
| `008C73` | L_8C73 | decoded | `008C6E` BNE |
| `008C81` | L_8C81 | decoded | `008C7C` BNE |
| `008C8F` | L_8C8F | decoded | `008C8A` BNE |
| `008C97` | L_8C97 | decoded | `008C92` BNE |
| `008C9F` | L_8C9F | decoded | `008C9A` BNE |
| `008CA7` | L_8CA7 | decoded | `008CA2` BNE |
| `008CAF` | L_8CAF | decoded | `008CAA` BNE |
| `008CB7` | L_8CB7 | decoded | `008CB2` BNE |
| `008CBF` | L_8CBF | decoded | `008CBA` BNE |
| `008CC7` | L_8CC7 | decoded | `008CC2` BNE |
| `008CCF` | L_8CCF | decoded | `008CCA` BNE |
| `008CD7` | L_8CD7 | decoded | `008CD2` BNE |
| `008CDF` | L_8CDF | decoded | `008CDA` BNE |
| `008CFA` | L_8CFA | decoded | `008CEF` BBC |
| `008CFD` | L_8CFD | decoded | `008CE7` BCC<br>`008CF8` BEQ |
| `008D09` | L_8D09 | decoded | `008D06` BNE |
| `008D0F` | L_8D0F | decoded | `008CFD` BBC |
| `008D17` | L_8D17 | decoded | `008D12` BNE |
| `008D25` | L_8D25 | decoded | `008D1A` BBS |
| `008D27` | L_8D27 | decoded | `008D20` BNE<br>`008D23` BRA |
| `008D32` | L_8D32 | decoded | `008D2D` BNE |
| `008D3A` | L_8D3A | decoded | `008D35` BNE |
| `008D42` | L_8D42 | decoded | `008D3D` BNE |
| `008D4A` | L_8D4A | decoded | `008D45` BNE |
| `008D52` | L_8D52 | decoded | `008D4D` BNE |
| `008D5A` | L_8D5A | decoded | `008D55` BNE |
| `008D62` | L_8D62 | decoded | `008D5D` BNE |
| `008D6A` | L_8D6A | decoded | `008D65` BNE |
| `008D72` | L_8D72 | decoded | `008D6D` BNE |
| `008D7E` | L_8D7E | decoded | `008D75` BPL<br>`008D79` BEQ |
| `008D86` | L_8D86 | decoded | `008D81` BNE |
| `008D8E` | L_8D8E | decoded | `008D89` BNE |
| `008D96` | L_8D96 | decoded | `008D91` BNE |
| `008D9E` | L_8D9E | decoded | `008D99` BNE |
| `008DA6` | L_8DA6 | decoded | `008DA1` BNE |
| `008DAE` | L_8DAE | decoded | `008DA9` BNE |
| `008DB6` | L_8DB6 | decoded | `008DB1` BNE |
| `008DBE` | L_8DBE | decoded | `008DB9` BNE |
| `008DC7` | L_8DC7 | decoded | `008DC2` BEQ |
| `008DD0` | L_8DD0 | decoded | `008DCB` BEQ |
| `008DE4` | L_8DE4 | decoded | `008DE7` BBS<br>`008DF6` BCC |
| `008DE7` | L_8DE7 | decoded | `008DD0` BBS |
| `008E1C` | L_8E1C | decoded | `008E14` BCC |
| `008E2C` | L_8E2C | decoded | `008E1A` BRA |
| `008E41` | L_8E41 | decoded | `008E37` BCC |
| `008E46` | L_8E46 | decoded | `008DEC` BBS |
| `008E6F` | L_8E6F | decoded | `008E65` BCS |
| `008E72` | L_8E72 | decoded | `008E30` BCC<br>`008E44` BRA<br>`008E5E` BCS |
| `008E7D` | L_8E7D | decoded | `008DE4` JMP<br>`008E78` BCS |
| `008E97` | L_8E97 | decoded | `008E92` BNE |
| `008E9F` | L_8E9F | decoded | `008E9A` BNE |
| `008EA7` | L_8EA7 | decoded | `008EA2` BNE |
| `008EAF` | L_8EAF | decoded | `008EAA` BNE |
| `008EB7` | L_8EB7 | decoded | `008EB2` BNE |
| `008EBF` | L_8EBF | decoded | `008EBA` BNE |
| `008ECB` | L_8ECB | decoded | `008EC6` BNE |
| `008ED3` | L_8ED3 | decoded | `008ECE` BNE |
| `008EE6` | L_8EE6 | decoded | `008EDE` BEQ |
| `008EF3` | L_8EF3 | decoded | `008E89` BCC<br>`008EE4` BRA<br>`008EE6` BBC<br>`008EEE` BNE |
| `008F19` | L_8F19 | decoded | `008F0B` BBC |
| `008F1F` | L_8F1F | decoded | `008EF3` BBS<br>`008EFD` BCC<br>`008F04` BCC<br>`008F06` BBC |
| `008F23` | L_8F23 | decoded | `008935` JMP<br>`008F10` BBS<br>`008F1D` BRA |
| `008F2B` | L_8F2B | decoded | `008F26` BNE |
| `008F33` | L_8F33 | decoded | `008F2E` BNE |
| `008F49` | L_8F49 | decoded | `008F39` BBC<br>`008F3E` BBS |
| `008F4C` | L_8F4C | decoded | `008F47` BEQ |
| `008F54` | L_8F54 | decoded | `008F4F` BNE |
| `008F5C` | L_8F5C | decoded | `008F57` BNE |
| `008F6B` | L_8F6B | decoded | `008F62` BCC |
| `008F6F` | L_8F6F | decoded | `008F67` BEQ<br>`008F69` BCC |
| `008F77` | L_8F77 | decoded | `008F72` BNE |
| `008F7F` | L_8F7F | decoded | `008F7A` BNE |
| `008F87` | L_8F87 | decoded | `008F82` BNE |
| `008F8F` | L_8F8F | decoded | `008F8A` BNE |
| `008F97` | L_8F97 | decoded | `008F92` BNE |
| `008FA3` | L_8FA3 | decoded | `008F9E` BNE |
| `008FB0` | L_8FB0 | decoded | `008FA3` BBC<br>`008FAB` BNE |
| `008FB8` | L_8FB8 | decoded | `008FB3` BNE |
| `008FC0` | L_8FC0 | decoded | `008FBB` BNE |
| `008FC8` | L_8FC8 | decoded | `008FC3` BNE |
| `008FD0` | L_8FD0 | decoded | `008FCB` BNE |
| `008FD8` | L_8FD8 | decoded | `008FD3` BNE |
| `008FE0` | L_8FE0 | decoded | `008FDB` BNE |
| `008FE8` | L_8FE8 | decoded | `008FE3` BNE |
| `008FF0` | L_8FF0 | decoded | `008FEB` BNE |
| `008FF8` | L_8FF8 | decoded | `008FF3` BNE |
| `009000` | L_9000 | decoded | `008FFB` BNE |
| `009008` | L_9008 | decoded | `009003` BNE |
| `009010` | L_9010 | decoded | `00900B` BNE |
| `009018` | L_9018 | decoded | `009013` BNE |
| `00901F` | L_901F | decoded | `00901C` BNE |
| `009029` | L_9029 | decoded | `009026` BNE |
| `009034` | L_9034 | decoded | `00902F` BNE |
| `00903C` | L_903C | decoded | `009037` BNE |
| `009044` | L_9044 | decoded | `00903F` BNE |
| `00904C` | L_904C | decoded | `009047` BNE |
| `009053` | L_9053 | decoded | `009050` BNE |
| `009061` | L_9061 | decoded | `00905C` BNE |
| `009068` | L_9068 | decoded | `009065` BNE |
| `009076` | L_9076 | decoded | `009071` BNE |
| `009083` | L_9083 | decoded | `009076` BBS<br>`00907E` BNE |
| `00908B` | L_908B | decoded | `009086` BNE |
| `009093` | L_9093 | decoded | `00908E` BNE |
| `00909B` | L_909B | decoded | `009096` BNE |
| `0090A3` | L_90A3 | decoded | `00909E` BNE |
| `0090AB` | L_90AB | decoded | `0090A6` BNE |
| `0090B3` | L_90B3 | decoded | `0090AE` BNE |
| `0090BB` | L_90BB | decoded | `0090B6` BNE |
| `0090C3` | L_90C3 | decoded | `0090BE` BNE |
| `0090CA` | L_90CA | decoded | `0090C7` BNE |
| `0090D4` | L_90D4 | decoded | `0090D1` BNE |
| `0090DE` | L_90DE | decoded | `0090DB` BNE |
| `0090E8` | L_90E8 | decoded | `0090E1` BBS |
| `0090F0` | L_90F0 | decoded | `0090E6` BRA<br>`0090EB` BNE |
| `0090FF` | L_90FF | decoded | `0090F0` BBC<br>`0090F8` BEQ<br>`0090FD` BRA |
| `009113` | L_9113 | decoded | `009101` BBS |
| `009117` | L_9117 | decoded | `009106` BBC<br>`009111` BRA |
| `00911A` | L_911A | decoded | `00910F` BEQ |
| `009122` | L_9122 | decoded | `00911D` BNE |
| `00912A` | L_912A | decoded | `009125` BEQ |
| `00913F` | L_913F | decoded | `00913A` BCS |
| `009147` | L_9147 | decoded | `009143` BCC |
| `00914A` | L_914A | decoded | `00912A` BBC |
| `009169` | L_9169 | decoded | `009164` BCS |
| `00916D` | L_916D | decoded | `00914D` BBS |
| `009176` | L_9176 | decoded | `00916D` BBS |
| `00917D` | L_917D | decoded | `009174` BRA<br>`00917A` BNE |
| `00918D` | L_918D | decoded | `009180` BBS<br>`009188` BNE |
| `009196` | L_9196 | decoded | `009190` BEQ |
| `0091B5` | L_91B5 | decoded | `00919B` BBS<br>`0091A0` BBC<br>`0091A5` BBS |
| `0091B8` | L_91B8 | decoded | `0091AA` BBC<br>`0091B3` BEQ |
| `0091C1` | L_91C1 | decoded | `0091B8` BBS |
| `0091C8` | L_91C8 | decoded | `0091BF` BRA<br>`0091C5` BNE |
| `0091D8` | L_91D8 | decoded | `0091CB` BBS<br>`0091D3` BNE |
| `0091E1` | L_91E1 | decoded | `0091DB` BEQ |
| `009200` | L_9200 | decoded | `0091E6` BBS<br>`0091EB` BBC<br>`0091F0` BBS |
| `009203` | L_9203 | decoded | `0091F5` BBC<br>`0091FE` BEQ |
| `00920B` | L_920B | decoded | `009206` BEQ |
| `009229` | L_9229 | decoded | `009224` BNE |
| `009231` | L_9231 | decoded | `00922C` BNE |
| `009239` | L_9239 | decoded | `009234` BNE |
| `009241` | L_9241 | decoded | `00923C` BEQ |
| `009249` | L_9249 | decoded | `009244` BNE |
| `009251` | L_9251 | decoded | `00924C` BNE |
| `009259` | L_9259 | decoded | `009254` BNE |
| `009261` | L_9261 | decoded | `00925C` BNE |
| `009269` | L_9269 | decoded | `009264` BNE |
| `009271` | L_9271 | decoded | `00926C` BNE |
| `009279` | L_9279 | decoded | `009274` BNE |
| `009281` | L_9281 | decoded | `00927C` BNE |
| `009289` | L_9289 | decoded | `009284` BNE |
| `009291` | L_9291 | decoded | `00928C` BNE |
| `009299` | L_9299 | decoded | `009294` BNE |
| `0092A1` | L_92A1 | decoded | `00929C` BNE |
| `0092A9` | L_92A9 | decoded | `0092A4` BNE |
| `0092B1` | L_92B1 | decoded | `0092AC` BNE |
| `0092B9` | L_92B9 | decoded | `0092B4` BNE |
| `0092C1` | L_92C1 | decoded | `0092BC` BNE |
| `0092C9` | L_92C9 | decoded | `0092C4` BNE |
| `0092D1` | L_92D1 | decoded | `0092CC` BNE |
| `0092D9` | L_92D9 | decoded | `0092D4` BNE |
| `0092E1` | L_92E1 | decoded | `0092DC` BNE |
| `0092E9` | L_92E9 | decoded | `0092E4` BNE |
| `0092F1` | L_92F1 | decoded | `0092EC` BEQ |
| `009307` | L_9307 | decoded | `009304` BNE |
| `00930A` | L_930A | decoded | `0092F1` BBC<br>`0092F6` BBC<br>`0092FB` BBC |
| `009312` | L_9312 | decoded | `00930D` BNE |
| `00931A` | L_931A | decoded | `009315` BNE |
| `009322` | L_9322 | decoded | `00931D` BNE |
| `00932A` | L_932A | decoded | `009325` BNE |
| `009332` | L_9332 | decoded | `00932D` BEQ |
| `00933A` | L_933A | decoded | `009335` BNE |
| `00934E` | L_934E | decoded | `00933A` BBC<br>`00933F` BBS |
| `009352` | L_9352 | decoded | `009347` BNE<br>`00934C` BRA |
| `009366` | L_9366 | decoded | `009352` BBC<br>`009357` BBS |
| `00936A` | L_936A | decoded | `00935F` BNE<br>`009364` BRA |
| `009372` | L_9372 | decoded | `00936D` BNE |
| `00937A` | L_937A | decoded | `009375` BNE |
| `009382` | L_9382 | decoded | `00937D` BNE |
| `009391` | L_9391 | decoded | `009382` BBS |
| `009395` | L_9395 | decoded | `00938A` BNE<br>`00938F` BRA |
| `009396` | L_9396 | decoded | `00893A` JSL |
| `0093A5` | L_93A5 | decoded | `009396` BBS<br>`00939B` BBC |
| `0093AA` | L_93AA | decoded | `0093A0` BBS |
| `0093BD` | L_93BD | decoded | `0093B9` BCC |
| `0093DE` | L_93DE | decoded | `0093D9` BCS |
| `0093FA` | L_93FA | decoded | `0093AA` BBS |
| `0093FD` | L_93FD | decoded | `0093A8` BRA |
| `009415` | L_9415 | decoded | `00940E` BBS |
| `00941D` | L_941D | decoded | `009419` BCC |
| `009425` | L_9425 | decoded | `009413` BRA<br>`009420` BCC |
| `00943F` | L_943F | decoded | `009434` BCS |
| `009450` | L_9450 | decoded | `009436` BBS |
| `009453` | L_9453 | decoded | `0093F0` BCS<br>`0093F8` BRA<br>`00944E` BCS |
| `00946D` | L_946D | decoded | `009468` BCS |
| `009479` | L_9479 | decoded | `00946E` BCS<br>`009471` BCS |
| `00947C` | L_947C | decoded | `009477` BRA |
| `009488` | purge_stepper_out | decoded | `004D8D` JSL |
| `009492` | L_9492 | decoded | `009488` BBS |
| `009496` | L_9496 | decoded | `0094A8` BCC<br>`0094B6` BNE |
| `0094A0` | L_94A0 | decoded | `00948D` BBC |
| `0094B3` | L_94B3 | decoded | `0094AF` BCC |
| `0094C5` | L_94C5 | decoded | `0094BC` BBS |
| `0094DA` | L_94DA | decoded | `0094E1` BCC |
| `0094F5` | L_94F5 | decoded | `009504` BBC<br>`00950C` BRA |
| `0094FD` | L_94FD | decoded | `0094FE` BNE |
| `00950E` | L_950E | decoded | `004DC5` JSL |
| `009515` | L_9515 | decoded | `00950E` BBC |
| `009522` | L_9522 | decoded | `00951A` BCC |
| `009526` | L_9526 | decoded | `009520` BRA |
| `009534` | L_9534 | decoded | `00952B` BBC |
| `009548` | L_9548 | decoded | `009539` BBC |
| `00954C` | L_954C | decoded | `009546` BRA |
| `009550` | L_9550 | decoded | `009513` BRA<br>`009526` BBS<br>`009534` BBC |
| `009554` | L_9554 | decoded | `009710` JMP |
| `00955D` | L_955D | decoded | `009554` BBC |
| `009566` | L_9566 | decoded | `00955D` BBS |
| `009572` | L_9572 | decoded | `009569` BNE<br>`00956B` BBS |
| `009588` | L_9588 | decoded | `00957E` BCC |
| `00958E` | L_958E | decoded | `00957A` BMI |
| `009598` | L_9598 | decoded | `009590` BCC |
| `0095A0` | L_95A0 | decoded | `009570` BRA<br>`009572` BBC |
| `0095F1` | L_95F1 | decoded | `00958C` BRA<br>`009596` BRA<br>`0095A7` BNE<br>`0095AF` BNE<br>`0095B7` BNE<br>`0095BF` BNE<br>`0095C7` BNE<br>`0095CF` BNE<br>`0095D7` BNE<br>`0095DF` BNE<br>`0095E7` BNE |
| `0095F4` | L_95F4 | decoded | `009562` JMP<br>`0095EF` BEQ |
| `0095FB` | L_95FB | decoded | `0095F4` BBS |
| `0095FF` | L_95FF | decoded | `009559` JMP |
| `009608` | L_9608 | decoded | `0095FF` BBS |
| `009629` | L_9629 | decoded | `009620` BBS |
| `00962B` | L_962B | decoded | `009627` BRA |
| `009630` | L_9630 | decoded | `00960D` BCC |
| `00964F` | L_964F | decoded | `0095F2` BRA<br>`0095F9` BRA<br>`009678` BEQ |
| `009653` | L_9653 | decoded | `009648` BCS |
| `009663` | L_9663 | decoded | `009630` BBC |
| `00966D` | L_966D | decoded | `009663` BBC |
| `009670` | L_9670 | decoded | `00966B` BRA |
| `00967A` | L_967A | decoded | `009584` JMP<br>`00959C` JMP<br>`0095FB` JMP<br>`009612` BPL<br>`00962E` BRA<br>`009644` BCC<br>`00964D` BCC<br>`009655` BCC<br>`009673` BEQ<br>`0096AB` BCC<br>`0096B9` BCC<br>`0096CB` BCC<br>`0096CE` BCC |
| `00967E` | L_967E | decoded | `009604` JMP |
| `009694` | L_9694 | decoded | `0096C7` BRA<br>`0096DC` BRA |
| `0096A6` | L_96A6 | decoded | `00969C` BCC |
| `0096B4` | L_96B4 | decoded | `00963A` BNE<br>`00968E` BCC |
| `0096B8` | L_96B8 | decoded | `0096B2` BCC |
| `0096C9` | L_96C9 | decoded | `0096AF` BCS |
| `0096DE` | L_96DE | decoded | `0096C1` BCS<br>`0096D6` BCS |
| `0096E0` | L_96E0 | decoded | `009530` JMP |
| `0096FE` | L_96FE | decoded | `0096F7` BBC |
| `009710` | L_9710 | decoded | `0096E0` BBS<br>`0096ED` BCC<br>`0096FC` BRA |
| `009714` | L_9714 | decoded | `00967A` JMP |
| `00971A` | L_971A | decoded | `00964F` JMP<br>`0096DE` BRA |
| `00971E` | L_971E | decoded | `0096B4` JMP<br>`009718` BRA |
| `00971F` | L_971F | decoded | `0096A2` JSL |
| `009722` | L_9722 | decoded | `00972A` BNE |
| `00972C` | L_972C | decoded | `009779` BRA |
| `009744` | L_9744 | decoded | `009724` BNE |
| `00974B` | L_974B | decoded | `009772` BNE<br>`009777` BNE |
| `009759` | L_9759 | decoded | `00974D` BCC<br>`009755` BNE |
| `00977B` | L_977B | decoded | `00976A` BNE |
| `009784` | L_9784 | decoded | `009789` BRA |
| `00978B` | L_978B | decoded | `009786` BCS |
| `0097D4` | L_97D4 | decoded | `009740` JMP |
| `0097FE` | L_97FE | decoded | `00411D` JSL<br>`004DB5` JSL |
| `009807` | L_9807 | decoded | `009813` BCC |
| `009810` | L_9810 | decoded | `009866` JMP |
| `00981B` | L_981B | decoded | `009829` BRA |
| `00982B` | L_982B | decoded | `009825` BCS |
| `00982C` | L_982C | decoded | `00980A` BNE<br>`00985F` BCC |
| `009858` | L_9858 | decoded | `009840` BCC |
| `00985A` | L_985A | decoded | `009834` BEQ |
| `00986A` | calc_monitor_admission | decoded | `004DB9` JSL |
| `009875` | L_9875 | decoded | `00986E` BBS |
| `009879` | L_9879 | decoded | `009873` BRA |
| `009883` | L_9883 | decoded | `00987F` BCC |
| `009887` | L_9887 | decoded | `009881` BRA |
| `009891` | L_9891 | decoded | `00988D` BCC |
| `009895` | L_9895 | decoded | `00988F` BRA |
| `00989F` | L_989F | decoded | `00989B` BCC |
| `0098A3` | L_98A3 | decoded | `00989D` BRA |
| `0098B2` | L_98B2 | decoded | `0098A9` BCC<br>`0098AE` BCS |
| `0098B6` | L_98B6 | decoded | `0098B0` BRA |
| `0098C2` | L_98C2 | decoded | `0098BB` BBC |
| `0098C6` | L_98C6 | decoded | `0098B6` BBC<br>`0098C0` BRA |
| `0098CD` | L_98CD | decoded | `0098C6` BBC |
| `0098D1` | L_98D1 | decoded | `0098CB` BRA |
| `0098DB` | L_98DB | decoded | `0098D7` BEQ |
| `0098DD` | L_98DD | decoded | `0098D9` BCS |
| `0098E1` | L_98E1 | decoded | `0098DB` BRA |
| `0098E6` | L_98E6 | decoded | `0098E1` JSL |
| `0098ED` | L_98ED | decoded | `0098FA` BCC |
| `009900` | L_9900 | decoded | `0098EE` BCS |
| `00990F` | L_990F | decoded | `0098FE` BRA |
| `00991B` | L_991B | decoded | `004DBD` JSL |
| `00992A` | L_992A | decoded | `00991B` BBC |
| `00992E` | L_992E | decoded | `009928` BRA |
| `009943` | L_9943 | decoded | `00992E` BBC |
| `009952` | L_9952 | decoded | `009941` BRA |
| `009956` | L_9956 | decoded | `009938` BBS<br>`009948` BBS |
| `009961` | L_9961 | decoded | `009936` BEQ<br>`009943` BBS |
| `009965` | L_9965 | decoded | `00994D` BBC<br>`009959` BNE |
| `009969` | L_9969 | decoded | `00995F` BRA |
| `00996A` | consult_task | decoded | `004DE3` JSL |
| `009986` | L_9986 | decoded | `00997B` BBC |
| `009992` | L_9992 | decoded | `00996A` BBC |
| `009996` | L_9996 | decoded | `009977` BCC<br>`009979` BEQ<br>`009984` BRA<br>`009990` BRA |
| `0099A1` | L_99A1 | decoded | `009997` BBC |
| `0099A3` | consult_build_reply | decoded | `00999C` BBC |
| `0099B7` | consult_reply_d0 | decoded | `0099A9` BEQ |
| `0099C0` | L_99C0 | decoded | `0099CC` BCC |
| `0099D2` | consult_reply_c1 | decoded | `0099AD` BEQ |
| `0099DF` | consult_reply_d1 | decoded | `0099B1` BEQ<br>`0099D2` BBS |
| `0099EA` | L_99EA | decoded | `009A26` BRA |
| `0099F6` | L_99F6 | decoded | `009AB0` JMP |
| `0099FA` | L_99FA | decoded | `009A0A` BCC |
| `009A03` | L_9A03 | decoded | `0099FD` BEQ |
| `009A15` | L_9A15 | decoded | `009AB4` JMP |
| `009A1F` | L_9A1F | decoded | `009A13` BEQ<br>`009AAC` JMP |
| `009A28` | L_9A28 | decoded | `009A19` BNE |
| `009A2E` | L_9A2E | decoded | `0099FF` JMP<br>`009A9C` JMP |
| `009A3C` | L_9A3C | decoded | `009A36` BNE |
| `009A77` | L_9A77 | decoded | `009A61` BEQ |
| `009A7A` | L_9A7A | decoded | `009A71` BCC |
| `009A95` | L_9A95 | decoded | `009A38` JMP<br>`009A75` BRA |
| `009AA0` | L_9AA0 | decoded | `009A9A` BCS |
| `009AB0` | L_9AB0 | decoded | `009AA4` BCC |
| `009AB4` | L_9AB4 | decoded | `009AAA` BEQ |
| `009AB8` | L_9AB8 | decoded | `009A1B` JMP<br>`009A93` BCS |
| `009AC2` | consult_reply_no_codes | decoded | `009ABC` BEQ |
| `009AD2` | L_9AD2 | decoded | `009AC0` BRA |
| `009AD6` | consult_reply_data | decoded | `0099B3` JMP |
| `009AE2` | L_9AE2 | decoded | `009AD9` BBS |
| `009AEB` | consult_reply_c9 | decoded | `009AE5` BNE |
| `009AF1` | L_9AF1 | decoded | `009B26` BCC |
| `009B14` | L_9B14 | decoded | `009AFE` BCC<br>`009B05` BBC<br>`009B0D` BCC |
| `009B19` | L_9B19 | decoded | `009B03` BCC<br>`009B12` BCC |
| `009B3F` | L_9B3F | decoded | `009B34` BBS |
| `009B6A` | L_9B6A | decoded | `009B3D` BRA |
| `009B6C` | L_9B6C | decoded | `009B68` BNE |
| `009B89` | L_9B89 | decoded | `009B2A` BBC<br>`009B2F` BBS |
| `009B8D` | consult_reply_5a | decoded | `009ADE` JMP |
| `009BA1` | L_9BA1 | decoded | `009BC6` BCC |
| `009BAF` | L_9BAF | decoded | `009BCD` BCC<br>`009BD6` BRA |
| `009BB9` | L_9BB9 | decoded | `009BDB` BRA |
| `009BCA` | L_9BCA | decoded | `009BA9` BBC |
| `009BD8` | L_9BD8 | decoded | `009BD2` BCC<br>`009BD4` BEQ |
| `009BDD` | L_9BDD | decoded | `009B8D` BBC |
| `009BE6` | consult_reply_finish | decoded | `009AE7` JMP<br>`009B8B` BRA<br>`009B95` BEQ<br>`009BC8` BRA<br>`009BDD` BBC |
| `009C00` | L_9C00 | decoded | `009BF0` BNE<br>`009BF5` BNE<br>`009BFA` BNE |
| `009C04` | consult_reply_51 | decoded | `009BEB` BEQ |
| `009C3A` | L_9C3A | decoded | `009C07` BNE<br>`009C0C` BNE<br>`009C11` BNE<br>`009C16` BNE<br>`009C1B` BNE<br>`009C20` BNE<br>`009C25` BNE<br>`009C2A` BNE<br>`009C2F` BNE<br>`009C34` BNE |
| `009C48` | L_9C48 | decoded | `009CA8` JMP |
| `009C67` | L_9C67 | decoded | `009C61` BBC |
| `009C91` | L_9C91 | decoded | `009C4E` BEQ<br>`009C85` BCC |
| `009C9A` | L_9C9A | decoded | `009C94` BCC |
| `009CA3` | L_9CA3 | decoded | `009C9D` BCS |
| `009CA7` | L_9CA7 | decoded | `009C9F` JMP |
| `009CAC` | L_9CAC | decoded | `009C96` JMP |
| `009CB7` | L_9CB7 | decoded | `009CB0` BBC |
| `009CBC` | consult_send_frame | decoded | `0099CE` JMP<br>`009A2A` JMP<br>`009AD2` JMP<br>`009C00` JMP<br>`009C36` JMP<br>`009C8D` JMP |
| `009CD4` | L_9CD4 | decoded | `009CCB` BBC |
| `009CDB` | L_9CDB | decoded | `009CC6` BBC<br>`009CCF` BBS |
| `009CDC` | L_9CDC | decoded | `009BFC` JMP |
| `009CDD` | consult_reply_direct | decoded | `009BE2` JSL |
| `009CF0` | L_9CF0 | decoded | `009D0D` BRA |
| `009D07` | L_9D07 | decoded | `009D03` BCC |
| `009D0F` | L_9D0F | decoded | `009CEE` BNE<br>`009D38` BRA |
| `009D23` | L_9D23 | decoded | `009D18` BBS |
| `009D29` | L_9D29 | decoded | `009D21` BRA<br>`009D23` BEQ |
| `009D34` | L_9D34 | decoded | `009D30` BCC |
| `009D3A` | L_9D3A | decoded | `009D05` BRA<br>`009D32` BRA |
| `009D3F` | calc_outputs | decoded | `009B97` JSL<br>`00CC52` JSL |
| `009D57` | L_9D57 | decoded | `009D4E` BBS |
| `009D59` | L_9D59 | decoded | `009D55` BRA |
| `009D65` | L_9D65 | decoded | `009D5E` BBC |
| `009D71` | L_9D71 | decoded | `009D6A` BBC |
| `009D78` | L_9D78 | decoded | `009D71` BBS |
| `009D7F` | L_9D7F | decoded | `009D78` BBC |
| `009D86` | L_9D86 | decoded | `009D7F` BBC |
| `009D92` | L_9D92 | decoded | `009D8B` BBC |
| `009D9B` | L_9D9B | decoded | `009D92` BBS |
| `009D9D` | L_9D9D | decoded | `009D99` BRA |
| `009DA4` | L_9DA4 | decoded | `009D9D` BBC |
| `009DB6` | L_9DB6 | decoded | `009DAC` BBC |
| `009DB8` | L_9DB8 | decoded | `009DB1` BBC |
| `009DBF` | L_9DBF | decoded | `009DB8` BBC |
| `009DC6` | L_9DC6 | decoded | `009DBF` BBC |
| `009DD2` | L_9DD2 | decoded | `009DC6` BBC<br>`009DCB` BBS |
| `009DD9` | L_9DD9 | decoded | `009DD2` BBC |
| `009DE0` | L_9DE0 | decoded | `009DD9` BBC |
| `009DEC` | L_9DEC | decoded | `009DE0` BBC<br>`009DE5` BBC |
| `009E08` | L_9E08 | decoded | `009DFE` BBC |
| `009E0A` | L_9E0A | decoded | `009E03` BBC |
| `009E0D` | L_9E0D | decoded | `009DEF` BBC<br>`009DF4` BBS |
| `009EA6` | L_9EA6 | decoded | `004DE7` JSL |
| `009EB7` | L_9EB7 | decoded | `009ED0` BCC |
| `009EC3` | L_9EC3 | decoded | `009EBF` BEQ |
| `009EC9` | L_9EC9 | decoded | `009EBB` BCC<br>`009EC1` BCS |
| `009ED4` | L_9ED4 | decoded | `009EAA` BBC<br>`009EAF` BBC<br>`009ED2` BRA |
| `009ED8` | L_9ED8 | decoded | `009EC7` BRA |
| `009EDA` | L_9EDA | decoded | `004DF6` JSL |
| `009EE6` | L_9EE6 | decoded | `009EDD` BBC |
| `009EFF` | L_9EFF | decoded | `009EF3` BNE |
| `009F13` | L_9F13 | decoded | `009F02` BNE |
| `009F22` | L_9F22 | decoded | `009EFD` BRA<br>`009F11` BRA<br>`009F27` BBC<br>`00A4AA` JMP<br>`00A4D7` JMP |
| `009F27` | L_9F27 | decoded | `009EE6` BBS<br>`009EEB` BBS |
| `009F37` | L_9F37 | decoded | `009F2F` BBC |
| `009F42` | L_9F42 | decoded | `009F3A` BCC |
| `009F46` | L_9F46 | decoded | `009F40` BRA |
| `009F64` | L_9F64 | decoded | `009F25` BRA<br>`009F49` BBC<br>`009F4E` BBS<br>`009F53` BBC<br>`009F58` BBC |
| `009F70` | L_9F70 | decoded | `009F5D` BBS |
| `009F7B` | L_9F7B | decoded | `009F62` BRA |
| `009F8B` | L_9F8B | decoded | `009F83` BBC |
| `009F9F` | L_9F9F | decoded | `009F93` BBC<br>`009F9B` BCC |
| `009FAA` | L_9FAA | decoded | `009F8E` BCC<br>`009FA2` BCC |
| `009FBC` | L_9FBC | decoded | `009F7B` BBS<br>`009FA8` BRA |
| `009FCB` | L_9FCB | decoded | `009FC1` BBS |
| `009FCF` | L_9FCF | decoded | `009FBC` BBS |
| `009FE6` | L_9FE6 | decoded | `009FC6` BBS |
| `009FEF` | L_9FEF | decoded | `009FE6` BBS |
| `00A006` | L_A006 | decoded | `00A001` BCC |
| `00A011` | L_A011 | decoded | `009FF3` BBS |
| `00A028` | L_A028 | decoded | `00A016` BNE |
| `00A05D` | L_A05D | decoded | `00A063` BCC |
| `00A061` | L_A061 | decoded | `00A056` BMI |
| `00A065` | L_A065 | decoded | `00A05B` BCS |
| `00A077` | L_A077 | decoded | `00A072` BCC |
| `00A094` | L_A094 | decoded | `00A08E` BPL |
| `00A0B7` | L_A0B7 | decoded | `00A0B1` BPL |
| `00A0EF` | L_A0EF | decoded | `00A0D9` BBS |
| `00A0FD` | L_A0FD | decoded | `00A0E6` BCS<br>`00A0ED` BRA<br>`00A0F6` BCC |
| `00A100` | L_A100 | decoded | `009FEB` JMP |
| `00A117` | L_A117 | decoded | `00A10F` BBC |
| `00A121` | L_A121 | decoded | `00A119` BCC |
| `00A12E` | L_A12E | decoded | `00A103` BBC<br>`00A11F` BRA |
| `00A136` | L_A136 | decoded | `00A12E` BBC |
| `00A139` | L_A139 | decoded | `009FE2` JMP |
| `00A13D` | L_A13D | decoded | `00A05D` JMP<br>`00A0FE` BRA |
| `00A14D` | L_A14D | decoded | `00A13D` BBS |
| `00A156` | L_A156 | decoded | `00A14B` BRA |
| `00A168` | L_A168 | decoded | `00A142` BBC<br>`00A14D` BBS |
| `00A185` | L_A185 | decoded | `00A166` BRA<br>`00A168` BBC |
| `00A1B0` | L_A1B0 | decoded | `00A198` BPL |
| `00A1BC` | L_A1BC | decoded | `00A1AE` BRA |
| `00A1BF` | L_A1BF | decoded | `00A196` BEQ<br>`00A1A1` BCC<br>`00A1B3` BCC |
| `00A1CF` | L_A1CF | decoded | `00A1C8` BCS |
| `00A1D7` | L_A1D7 | decoded | `00A1CD` BRA<br>`00A1D2` BCC |
| `00A1DE` | L_A1DE | decoded | `009F77` JMP |
| `00A1F4` | L_A1F4 | decoded | `00A1ED` BNE |
| `00A1F8` | L_A1F8 | decoded | `00A1EF` BBC |
| `00A208` | L_A208 | decoded | `00A1FF` BBS |
| `00A229` | L_A229 | decoded | `00A221` BBC |
| `00A22D` | L_A22D | decoded | `00A250` BCS |
| `00A244` | L_A244 | decoded | `00A23F` BCC |
| `00A260` | L_A260 | decoded | `00A266` BCC |
| `00A268` | L_A268 | decoded | `00A25D` BEQ |
| `00A27D` | L_A27D | decoded | `00A277` BBC |
| `00A291` | L_A291 | decoded | `00A287` BCS |
| `00A298` | L_A298 | decoded | `00A28B` BCS<br>`00A28F` BRA<br>`00A294` BCC |
| `00A2AF` | L_A2AF | decoded | `00A2AB` BCS |
| `00A2B6` | L_A2B6 | decoded | `00A29F` BCS |
| `00A2BE` | L_A2BE | decoded | `00A2B2` BEQ<br>`00A2B4` BCC |
| `00A2C8` | L_A2C8 | decoded | `00A2C1` BEQ<br>`00A2D4` BCS |
| `00A2CE` | L_A2CE | decoded | `00A2BC` BRA<br>`00A2C6` BNE |
| `00A2DA` | L_A2DA | decoded | `00A2CC` BRA |
| `00A302` | L_A302 | decoded | `00A2E3` BCC<br>`00A2EB` BCS |
| `00A30C` | L_A30C | decoded | `00A305` BEQ |
| `00A312` | L_A312 | decoded | `00A2DE` BCC |
| `00A31D` | L_A31D | decoded | `00A300` BRA |
| `00A321` | L_A321 | decoded | `00A30A` BNE<br>`00A310` BRA |
| `00A328` | L_A328 | decoded | `00A338` BRA |
| `00A33A` | L_A33A | decoded | `00A334` BCS |
| `00A346` | L_A346 | decoded | `00A350` BCC |
| `00A352` | L_A352 | decoded | `00A349` BCC |
| `00A361` | L_A361 | decoded | `00A355` BCS<br>`00A35D` BCC |
| `00A364` | L_A364 | decoded | `00A4CD` JSL |
| `00A378` | L_A378 | decoded | `00A36C` BEQ |
| `00A37A` | L_A37A | decoded | `00A370` BCC |
| `00A380` | L_A380 | decoded | `00A372` BEQ |
| `00A386` | L_A386 | decoded | `00A09D` JSL<br>`00A0A7` JSL<br>`00A0C0` JSL<br>`00A0CE` JSL |
| `00A397` | L_A397 | decoded | `00A391` BPL |
| `00A398` | L_A398 | decoded | `00A0E2` JSL<br>`00A0F2` JSL |
| `00A3AC` | L_A3AC | decoded | `009F04` JSL |
| `00A432` | L_A432 | decoded | `00A3CA` JSL<br>`00A3D1` JSL<br>`00A417` JSL<br>`00A425` JSL |
| `00A438` | checksum_add | decoded | `00A3B5` JSL<br>`00A3BC` JSL<br>`00A3C3` JSL<br>`00A3D8` JSL<br>`00A3DF` JSL<br>`00A3E6` JSL<br>`00A3ED` JSL<br>`00A3F4` JSL<br>`00A3FB` JSL<br>`00A402` JSL<br>`00A409` JSL<br>`00A410` JSL<br>`00A41E` JSL |
| `00A43B` | L_A43B | decoded | `00A436` BRA |
| `00A447` | L_A447 | decoded | `009EE2` JMP |
| `00A469` | L_A469 | decoded | `00A454` BNE |
| `00A46F` | L_A46F | decoded | `00A44F` BEQ |
| `00A478` | L_A478 | decoded | `00A46F` BBC |
| `00A48D` | L_A48D | decoded | `00A46D` BRA |
| `00A495` | L_A495 | decoded | `00A447` BBS |
| `00A4A3` | L_A4A3 | decoded | `00A49A` BBS |
| `00A4AA` | L_A4AA | decoded | `00A493` BRA |
| `00A4AE` | L_A4AE | decoded | `00A495` BBC |
| `00A4C6` | L_A4C6 | decoded | `00A4B6` BCC<br>`00A4BC` BCC<br>`00A4C2` BCC |
| `00A4DB` | diag_task_a4db | decoded | `004DFA` JSL |
| `00A4EA` | L_A4EA | decoded | `00A4E0` BBC |
| `00A4F2` | L_A4F2 | decoded | `00A504` BBS<br>`00A513` BCC |
| `00A500` | L_A500 | decoded | `00A4DB` BBS |
| `00A504` | L_A504 | decoded | `00A4E5` BBS |
| `00A519` | L_A519 | decoded | `00A509` BBS |
| `00A522` | L_A522 | decoded | `00A519` BBC |
| `00A537` | L_A537 | decoded | `00A52B` BBC<br>`00A533` BCC |
| `00A546` | L_A546 | decoded | `00A53E` BCC<br>`00A540` BEQ |
| `00A555` | L_A555 | decoded | `00A549` BBC<br>`00A551` BCC |
| `00A564` | L_A564 | decoded | `00A55C` BCC<br>`00A55E` BEQ |
| `00A573` | L_A573 | decoded | `00A567` BBC<br>`00A56F` BCC |
| `00A582` | L_A582 | decoded | `00A57A` BCC<br>`00A57C` BEQ |
| `00A5A5` | L_A5A5 | decoded | `00A588` BBC<br>`00A58D` BBS<br>`00A599` BCS |
| `00A5B3` | L_A5B3 | decoded | `00A5A9` BBC |
| `00A5CE` | L_A5CE | decoded | `00A5A7` BNE<br>`00A5AE` BBS<br>`00A5B3` BBS |
| `00A5D4` | L_A5D4 | decoded | `00A5B8` BBC<br>`00A5CA` BEQ<br>`00A5CC` BCC |
| `00A5D8` | L_A5D8 | decoded | `00A5D2` BRA |
| `00A5F3` | L_A5F3 | decoded | `00A5E7` BBS<br>`00A5EF` BCC |
| `00A5FA` | L_A5FA | decoded | `00A5F6` BEQ |
| `00A609` | L_A609 | decoded | `00A5F8` BCS |
| `00A60D` | L_A60D | decoded | `00A5D8` BBS<br>`00A5FE` BBS |
| `00A611` | L_A611 | decoded | `00A5A3` BRA<br>`00A607` BRA |
| `00A62E` | L_A62E | decoded | `00A623` BEQ |
| `00A638` | L_A638 | decoded | `00A62C` BRA |
| `00A657` | L_A657 | decoded | `00A648` BNE<br>`00A651` BCC |
| `00A684` | L_A684 | decoded | `00A65A` BBC<br>`00A65F` BBS<br>`00A667` BNE<br>`00A66C` BEQ<br>`00A671` BEQ<br>`00A676` BEQ |
| `00A688` | L_A688 | decoded | `00A67E` BCC |
| `00A6AC` | L_A6AC | decoded | `00A6A2` BEQ |
| `00A6B6` | L_A6B6 | decoded | `00A693` BNE |
| `00A6C0` | L_A6C0 | decoded | `00A6B9` BEQ |
| `00A6CD` | L_A6CD | decoded | `00A6C3` BEQ |
| `00A6D7` | L_A6D7 | decoded | `00A6BE` BNE |
| `00A6F6` | L_A6F6 | decoded | `00A6EC` BEQ |
| `00A700` | L_A700 | decoded | `00A6DA` BNE |
| `00A712` | L_A712 | decoded | `00A698` BEQ<br>`00A69D` BCS<br>`00A6DC` BBS<br>`00A6E7` BCS |
| `00A716` | L_A716 | decoded | `00A710` BCS |
| `00A723` | L_A723 | decoded | `00A719` BEQ |
| `00A729` | L_A729 | decoded | `00A6B0` BCS<br>`00A6D1` BCS<br>`00A6FA` BCS |
| `00A72B` | L_A72B | decoded | `00A703` BNE |
| `00A748` | L_A748 | decoded | `00A740` BEQ |
| `00A750` | L_A750 | decoded | `00A705` BBC |
| `00A75F` | L_A75F | decoded | `00A753` BEQ |
| `00A769` | L_A769 | decoded | `00A712` JMP<br>`00A72E` BNE<br>`00A730` BBS<br>`00A73B` BCC |
| `00A76D` | L_A76D | decoded | `00A6A8` JMP<br>`00A6C9` JMP<br>`00A6F2` JMP<br>`00A71F` JMP<br>`00A746` BRA<br>`00A75D` BRA |
| `00A771` | L_A771 | decoded | `00A6B2` JMP<br>`00A6D3` JMP<br>`00A6FC` JMP<br>`00A727` BCC<br>`00A74E` BRA<br>`00A765` BCC |
| `00A776` | L_A776 | decoded | `00A653` JMP<br>`00A680` JMP<br>`00A729` BRA<br>`00A74C` BCS<br>`00A767` BRA |
| `00A790` | L_A790 | decoded | `00A51E` JMP<br>`00A77A` BBC<br>`00A77F` BBC |
| `00A7A0` | L_A7A0 | decoded | `00A774` BRA |
| `00A7B2` | L_A7B2 | decoded | `00A7A2` BNE |
| `00A7BC` | L_A7BC | decoded | `00A7B0` BRA<br>`00A7B6` BNE |
| `00A7D3` | L_A7D3 | decoded | `00A7BE` BNE<br>`00A7C0` BBC |
| `00A7DD` | L_A7DD | decoded | `00A7D1` BRA<br>`00A7D7` BNE |
| `00A7F8` | L_A7F8 | decoded | `00A7F3` BCS |
| `00A827` | L_A827 | decoded | `00A80D` BEQ |
| `00A82D` | L_A82D | decoded | `00A7FD` BBS<br>`00A802` BBC<br>`00A809` BEQ |
| `00A831` | L_A831 | decoded | `00A82B` BRA |
| `00A839` | L_A839 | decoded | `00A80F` BBC<br>`00A825` BRA |
| `00A842` | L_A842 | decoded | `00A839` BBC |
| `00A85E` | L_A85E | decoded | `00A856` BBC |
| `00A879` | L_A879 | decoded | `00A844` BNE |
| `00A899` | L_A899 | decoded | `00A891` BBC |
| `00A8B4` | L_A8B4 | decoded | `00A881` BBS |
| `00A8C2` | L_A8C2 | decoded | `00A8BA` BCC |
| `00A8C5` | L_A8C5 | decoded | `00A84A` BBS<br>`00A877` BRA<br>`00A8B2` BRA<br>`00A8C0` BRA |
| `00A8CB` | L_A8CB | decoded | `00A83E` JMP<br>`00A87B` BNE |
| `00A8E2` | L_A8E2 | decoded | `00A79C` JMP<br>`00A8CD` BNE<br>`00A8D5` BCC<br>`00A8D7` BBS |
| `00A8E6` | L_A8E6 | decoded | `00A8E0` BRA |
| `00A8EE` | L_A8EE | decoded | `00A8C9` BRA |
| `00A8FF` | L_A8FF | decoded | `00A8FA` BNE |
| `00A907` | L_A907 | decoded | `00A902` BNE |
| `00A90F` | L_A90F | decoded | `00A8F5` BNE<br>`00A907` BBC |
| `00A916` | L_A916 | decoded | `00A90F` BBC |
| `00A91E` | L_A91E | decoded | `00A500` JMP<br>`00A914` BRA<br>`00A916` BBC |
| `00A91F` | L_A91F | decoded | `00A87D` JSL<br>`00A8E6` JSL |
| `00A932` | L_A932 | decoded | `00A927` BEQ<br>`00A92D` BCS |
| `00A937` | L_A937 | decoded | `00A846` JSL<br>`00A8EA` JSL |
| `00A93B` | L_A93B | decoded | `00A8BC` JSL |
| `00A94A` | L_A94A | decoded | `00A93F` BEQ<br>`00A945` BCS |
| `00A94F` | L_A94F | decoded | `00A867` JSL<br>`00A8A2` JSL |
| `00A965` | L_A965 | decoded | `00A958` BCC<br>`00A960` BCC |
| `00A976` | L_A976 | decoded | `00A96B` BCC<br>`00A972` BCC |
| `00A9A0` | L_A9A0 | decoded | `00A8EE` JSL |
| `00A9AA` | L_A9AA | decoded | `00A9A0` BBC |
| `00A9B5` | L_A9B5 | decoded | `00A9A8` BRA<br>`00A9B0` BCS |
| `00A9B9` | L_A9B9 | decoded | `004DFE` JSL |
| `00A9D7` | L_A9D7 | decoded | `00A9C1` BPL |
| `00A9DD` | L_A9DD | decoded | `00A9BC` BEQ<br>`00A9C9` BCS |
| `00A9DF` | L_A9DF | decoded | `00A9D5` BRA<br>`00A9DB` BRA |
| `00A9EF` | L_A9EF | decoded | `004E02` JSL |
| `00A9FE` | L_A9FE | decoded | `00A9EF` BBS |
| `00AA04` | L_AA04 | decoded | `00A9F7` BNE<br>`00A9FC` BRA |
| `00AA19` | L_AA19 | decoded | `00AA0F` BCS |
| `00AA2A` | L_AA2A | decoded | `00AA23` BCC |
| `00AA2D` | L_AA2D | decoded | `00AA28` BRA |
| `00AA32` | L_AA32 | decoded | `00AA17` BCS |
| `00AA62` | L_AA62 | decoded | `00AA02` BRA<br>`00AA1F` BCC<br>`00AA30` BCS<br>`00AA38` BCC<br>`00AA3D` BCS<br>`00AA45` BCC<br>`00AA4A` BCS<br>`00AA7C` BCC<br>`00AA81` BCS<br>`00AA9D` BCS<br>`00AACF` BCS |
| `00AA76` | L_AA76 | decoded | `00AA04` BBS<br>`00AA60` BRA |
| `00AA90` | L_AA90 | decoded | `00AA8B` BCS |
| `00AA99` | L_AA99 | decoded | `00AA94` BCC |
| `00AAB6` | L_AAB6 | decoded | `00AAAA` BCS<br>`00AAAC` BBS |
| `00AAB9` | L_AAB9 | decoded | `00AAB4` BRA |
| `00AAC0` | L_AAC0 | decoded | `00AA9F` BBS |
| `00AACC` | L_AACC | decoded | `00AAC6` BCS |
| `00AAF4` | L_AAF4 | decoded | `00AAE6` BNE |
| `00AAFA` | L_AAFA | decoded | `00AADB` BEQ |
| `00AB02` | L_AB02 | decoded | `00AAD9` BCC |
| `00AB18` | L_AB18 | decoded | `00AAF8` BRA<br>`00AB00` BRA |
| `00AB25` | L_AB25 | decoded | `00AB20` BCC |
| `00AB42` | L_AB42 | decoded | `00AB35` BBC |
| `00AB48` | L_AB48 | decoded | `00AB44` BCC |
| `00AB4F` | L_AB4F | decoded | `00AB3C` BCC<br>`00AB40` BRA |
| `00AB52` | L_AB52 | decoded | `00AB26` BBC |
| `00AB5B` | L_AB5B | decoded | `00AAC8` JMP |
| `00AB72` | L_AB72 | decoded | `00AB6E` BCC |
| `00AB82` | L_AB82 | decoded | `00AB77` BBS |
| `00AB85` | L_AB85 | decoded | `00AB80` BRA |
| `00AB9D` | L_AB9D | decoded | `00AB97` BEQ<br>`00AB99` BCC |
| `00ABAA` | L_ABAA | decoded | `00AB59` BRA<br>`00AB9B` BRA |
| `00ABC1` | L_ABC1 | decoded | `00ABB5` BMI |
| `00ABCC` | L_ABCC | decoded | `00ABC7` BCC |
| `00ABCF` | L_ABCF | decoded | `00ABBA` BCC<br>`00ABBF` BRA |
| `00ABD6` | L_ABD6 | decoded | `00AA72` JMP |
| `00ABF2` | L_ABF2 | decoded | `00ABE8` BNE<br>`00ABED` BEQ |
| `00AC09` | L_AC09 | decoded | `00ABFC` BBS |
| `00AC1F` | L_AC1F | decoded | `00AC09` BBS |
| `00AC41` | L_AC41 | decoded | `00AC34` BEQ |
| `00AC47` | L_AC47 | decoded | `00ABF2` BBC<br>`00ABF7` BBC<br>`00AC07` BCC |
| `00AC4F` | L_AC4F | decoded | `00AC1F` BBC<br>`00AC24` BBS<br>`00AC2F` BCC<br>`00AC3F` BCC |
| `00AC53` | L_AC53 | decoded | `00AC45` BRA |
| `00AC54` | idle_control | decoded | `004E06` JSL |
| `00AC60` | L_AC60 | decoded | `00AC54` BBC |
| `00AC66` | L_AC66 | decoded | `00AC70` BNE |
| `00AC79` | L_AC79 | decoded | `00AC59` BBS<br>`00AC69` BEQ |
| `00AC8A` | L_AC8A | decoded | `00AC5E` BRA |
| `00AC9C` | L_AC9C | decoded | `00AC9A` BEQ |
| `00ACA5` | L_ACA5 | decoded | `00ACAE` BBS |
| `00ACAE` | L_ACAE | decoded | `00ACA0` BBC |
| `00ACC1` | L_ACC1 | decoded | `00ACAC` BRA<br>`00ACBD` BCC |
| `00ACC5` | L_ACC5 | decoded | `00ACB3` BBC |
| `00ACDA` | L_ACDA | decoded | `00ACC9` BBC |
| `00ACE4` | L_ACE4 | decoded | `00ACDD` BEQ |
| `00ACE8` | L_ACE8 | decoded | `00ACD8` BRA<br>`00ACE2` BRA |
| `00AD08` | L_AD08 | decoded | `00ACFD` BEQ |
| `00AD0F` | L_AD0F | decoded | `00AD08` BBC |
| `00AD15` | L_AD15 | decoded | `00AD06` BRA<br>`00AD0D` BRA |
| `00AD19` | L_AD19 | decoded | `00AD13` BRA |
| `00AD2E` | L_AD2E | decoded | `00AD2A` BCC |
| `00AD36` | L_AD36 | decoded | `00AD31` BCC |
| `00AD39` | L_AD39 | decoded | `00ACEB` BEQ<br>`00AD19` BEQ |
| `00AD42` | L_AD42 | decoded | `00AD21` BEQ |
| `00AD46` | L_AD46 | decoded | `00AD34` BRA<br>`00AD37` BRA<br>`00AD40` BRA |
| `00AD4A` | L_AD4A | decoded | `00AD2C` BNE |
| `00AD71` | L_AD71 | decoded | `00AD5B` BCC |
| `00AD75` | L_AD75 | decoded | `00AD63` BCC |
| `00AD78` | L_AD78 | decoded | `00AD6F` BRA |
| `00AD8B` | L_AD8B | decoded | `00AD80` BCS<br>`00AD82` BBC |
| `00AD92` | L_AD92 | decoded | `00AD8B` BBC |
| `00ADA6` | L_ADA6 | decoded | `00AD90` BRA<br>`00AD92` BBS<br>`00AD9C` BCC |
| `00ADC1` | L_ADC1 | decoded | `00ADA6` BBC |
| `00ADD0` | L_ADD0 | decoded | `00ADBF` BRA<br>`00ADC6` BBS |
| `00ADDC` | L_ADDC | decoded | `00ADD3` BMI |
| `00ADE0` | L_ADE0 | decoded | `00ADD5` BNE |
| `00ADE2` | L_ADE2 | decoded | `00ADDA` BRA<br>`00ADDE` BRA |
| `00ADE9` | L_ADE9 | decoded | `00ADCE` BRA |
| `00ADF1` | L_ADF1 | decoded | `00ADC1` BBS |
| `00AE03` | L_AE03 | decoded | `00AE36` BNE |
| `00AE0D` | L_AE0D | decoded | `00AE74` JMP |
| `00AE19` | L_AE19 | decoded | `00ADF1` BBC |
| `00AE1D` | L_AE1D | decoded | `00ADF6` BBS |
| `00AE29` | L_AE29 | decoded | `00AE24` BNE |
| `00AE38` | L_AE38 | decoded | `00AE29` BBS<br>`00AE34` BCC |
| `00AE55` | L_AE55 | decoded | `00AE38` BBS |
| `00AE74` | L_AE74 | decoded | `00AE67` BCC |
| `00AE78` | L_AE78 | decoded | `00AE5B` BCS<br>`00AE72` BCS |
| `00AE8A` | L_AE8A | decoded | `00AE85` BCC |
| `00AEAE` | L_AEAE | decoded | `00AEAA` BCS |
| `00AED2` | L_AED2 | decoded | `00AEB8` BBC |
| `00AEE5` | L_AEE5 | decoded | `00AED0` BRA |
| `00AEEC` | L_AEEC | decoded | `00AE99` BBC<br>`00AE9E` BBC<br>`00AEBD` BBS<br>`00AED2` BBC |
| `00AF01` | L_AF01 | decoded | `00AEF6` BBC |
| `00AF09` | L_AF09 | decoded | `00AEF1` BBC |
| `00AF13` | L_AF13 | decoded | `00AEEF` BNE<br>`00AEFF` BRA<br>`00AF07` BCC |
| `00AF17` | L_AF17 | decoded | `00AF2C` BEQ<br>`00AF4A` BCS<br>`00AF6B` BRA |
| `00AF1B` | L_AF1B | decoded | `00AF0C` BEQ<br>`00AF0E` BBS |
| `00AF3E` | L_AF3E | decoded | `00AF38` BCC |
| `00AF59` | L_AF59 | decoded | `00AF52` BCS |
| `00AF5C` | L_AF5C | decoded | `00AF57` BRA |
| `00AF67` | L_AF67 | decoded | `00AF44` BCC |
| `00AF6D` | L_AF6D | decoded | `00AF2E` BCC |
| `00AF84` | L_AF84 | decoded | `00AF76` BBC<br>`00AF7E` BNE |
| `00AF8B` | L_AF8B | decoded | `00AF74` BCC |
| `00AF9A` | L_AF9A | decoded | `00AF93` BCS |
| `00AFA4` | L_AFA4 | decoded | `00AF9D` BCS |
| `00AFA7` | L_AFA7 | decoded | `00AF98` BRA<br>`00AFA2` BRA |
| `00AFB0` | L_AFB0 | decoded | `00AF60` BCC<br>`00AF65` BRA<br>`00AFAB` BCS |
| `00AFB7` | L_AFB7 | decoded | `00AE19` JMP<br>`00AF17` JMP<br>`00AF8E` BCC |
| `00AFEF` | L_AFEF | decoded | `00AFE3` BBC |
| `00B01A` | L_B01A | decoded | `00B012` BMI |
| `00B01C` | L_B01C | decoded | `00B014` BEQ<br>`00B018` BRA |
| `00B031` | L_B031 | decoded | `00B025` BCC |
| `00B038` | L_B038 | decoded | `00B02B` BCC<br>`00B02F` BRA<br>`00B034` BCS |
| `00B042` | L_B042 | decoded | `00B03B` BEQ<br>`00B03D` BCC |
| `00B054` | L_B054 | decoded | `00ACC1` JMP<br>`00ADED` JMP<br>`00B04F` BCS |
| `00B061` | L_B061 | decoded | `00B05C` BCC |
| `00B06E` | L_B06E | decoded | `00B056` BEQ<br>`00B062` BBC |
| `00B07F` | L_B07F | decoded | `00B071` BBC |
| `00B08F` | L_B08F | decoded | `00B07D` BCS |
| `00B0AB` | L_B0AB | decoded | `00B0A1` BNE<br>`00B0A6` BNE |
| `00B0BC` | L_B0BC | decoded | `00B0B1` BCC<br>`00B0B3` BBS |
| `00B0BE` | L_B0BE | decoded | `00B092` BCC |
| `00B0D7` | L_B0D7 | decoded | `00B0CE` BMI |
| `00B0E9` | L_B0E9 | decoded | `00B0E4` BPL |
| `00B0ED` | L_B0ED | decoded | `00B0C9` BCC<br>`00B0D0` BNE<br>`00B0D5` BNE<br>`00B0DA` BEQ |
| `00B0F7` | L_B0F7 | decoded | `00B0EB` BCC |
| `00B106` | L_B106 | decoded | `00B0FC` BNE<br>`00B101` BNE |
| `00B112` | L_B112 | decoded | `00B08B` JMP<br>`00B0BC` BRA<br>`00B0DC` BBS<br>`00B0F5` BRA<br>`00B10C` BCC |
| `00B121` | L_B121 | decoded | `00B11A` BMI |
| `00B127` | L_B127 | decoded | `00B11F` BNE |
| `00B13B` | L_B13B | decoded | `00B134` BCS |
| `00B144` | L_B144 | decoded | `00B112` BBC |
| `00B152` | L_B152 | decoded | `00B149` BBC |
| `00B15A` | L_B15A | decoded | `00B125` BRA<br>`00B142` BRA<br>`00B144` BBC |
| `00B16F` | L_B16F | decoded | `00B17D` BEQ |
| `00B178` | L_B178 | decoded | `00ADA2` JMP<br>`00B15F` BEQ |
| `00B17F` | L_B17F | decoded | `00B165` BNE<br>`00B16D` BNE<br>`00B16F` BBC |
| `00B183` | L_B183 | decoded | `00B158` BRA |
| `00B192` | L_B192 | decoded | `00B18A` BNE |
| `00B1A3` | L_B1A3 | decoded | `00B198` BBC |
| `00B1A8` | L_B1A8 | decoded | `00B1A4` BCC |
| `00B1B6` | L_B1B6 | decoded | `00B192` BCS |
| `00B1C5` | L_B1C5 | decoded | `00B1BA` BBC |
| `00B1CA` | L_B1CA | decoded | `00B1C6` BCC |
| `00B1D0` | L_B1D0 | decoded | `00B1AE` BCC<br>`00B1B0` BEQ<br>`00B1B4` BRA<br>`00B1CC` BNE |
| `00B1D9` | L_B1D9 | decoded | `00B1D0` BBS |
| `00B1DC` | L_B1DC | decoded | `00B190` BRA<br>`00B1A1` BRA<br>`00B1C3` BRA |
| `00B1EA` | L_B1EA | decoded | `00AD87` JMP<br>`00B14E` JMP<br>`00B174` JMP |
| `00B1FC` | L_B1FC | decoded | `00B1F2` BCC |
| `00B21D` | calc_idle_speed_target | decoded | `00ACC5` JSL |
| `00B23D` | L_B23D | decoded | `00B239` BCC |
| `00B242` | L_B242 | decoded | `00B22C` BMI |
| `00B248` | L_B248 | decoded | `00B244` BCC |
| `00B24E` | L_B24E | decoded | `00B220` BEQ<br>`00B22E` BBS<br>`00B23B` BNE<br>`00B246` BNE |
| `00B256` | L_B256 | decoded | `00B240` BRA |
| `00B25A` | L_B25A | decoded | `00B24C` BRA |
| `00B289` | L_B289 | decoded | `00B26E` BCC |
| `00B28C` | L_B28C | decoded | `00B287` BRA |
| `00B299` | L_B299 | decoded | `00B27A` BNE<br>`00B27F` BCS |
| `00B29B` | L_B29B | decoded | `00B297` BRA |
| `00B2A7` | L_B2A7 | decoded | `00B2A3` BCC |
| `00B2C0` | L_B2C0 | decoded | `00B2AC` BBS<br>`00B2B1` BBS |
| `00B2C8` | L_B2C8 | decoded | `00B2A7` BBC<br>`00B2B9` BCS<br>`00B2BE` BRA<br>`00B2C3` BCS |
| `00B2E1` | L_B2E1 | decoded | `00B2CD` BBS<br>`00B2D2` BBS |
| `00B2E9` | L_B2E9 | decoded | `00B2C8` BBC<br>`00B2DA` BCS<br>`00B2DF` BRA<br>`00B2E4` BCS |
| `00B2F6` | L_B2F6 | decoded | `00B2E9` BBC<br>`00B2F1` BCS |
| `00B303` | L_B303 | decoded | `00B2F6` BBC<br>`00B2FE` BCS |
| `00B317` | L_B317 | decoded | `00B308` BBS |
| `00B31F` | L_B31F | decoded | `00B303` BBC<br>`00B310` BCS<br>`00B315` BRA<br>`00B31A` BCS |
| `00B32B` | L_B32B | decoded | `00B324` BBC |
| `00B33D` | L_B33D | decoded | `00B333` BCS |
| `00B346` | L_B346 | decoded | `00B329` BRA<br>`00B342` BCC |
| `00B355` | L_B355 | decoded | `00B350` BCS |
| `00B371` | L_B371 | decoded | `00B35D` BCC<br>`00B367` BCS<br>`00B36C` BCS |
| `00B379` | L_B379 | decoded | `00B371` BBC |
| `00B38D` | L_B38D | decoded | `00B37E` BBS |
| `00B39A` | L_B39A | decoded | `00B379` BBS<br>`00B386` BCC<br>`00B38B` BRA<br>`00B38D` BBS<br>`00B395` BCS |
| `00B3A8` | L_B3A8 | decoded | `00B39A` BBC<br>`00B3A4` BCC |
| `00B3AC` | L_B3AC | decoded | `00AD4D` JSL |
| `00B3D5` | L_B3D5 | decoded | `00B3C6` BBS |
| `00B3E4` | L_B3E4 | decoded | `00B3D5` BBC<br>`00B3DA` BBS |
| `00B3E7` | L_B3E7 | decoded | `00B3E2` BRA |
| `00B3F8` | L_B3F8 | decoded | `00B3EA` BBS |
| `00B407` | L_B407 | decoded | `00B3D3` BRA |
| `00B409` | L_B409 | decoded | `00B3F6` BRA |
| `00B40C` | L_B40C | decoded | `00B405` BCS |
| `00B422` | L_B422 | decoded | `00B413` BBS |
| `00B43D` | L_B43D | decoded | `00B42F` BBS |
| `00B44C` | L_B44C | decoded | `00B420` BRA |
| `00B44E` | L_B44E | decoded | `00B43B` BRA |
| `00B451` | L_B451 | decoded | `00B44A` BCS |
| `00B467` | L_B467 | decoded | `00B458` BBS |
| `00B482` | L_B482 | decoded | `00B474` BBS |
| `00B491` | L_B491 | decoded | `00B465` BRA |
| `00B493` | L_B493 | decoded | `00B480` BRA |
| `00B496` | L_B496 | decoded | `00B48F` BCS |
| `00B4A8` | L_B4A8 | decoded | `00B49D` BBC |
| `00B4B6` | L_B4B6 | decoded | `00B4A8` BBS |
| `00B4C5` | L_B4C5 | decoded | `00B4A6` BRA |
| `00B4C7` | L_B4C7 | decoded | `00B4B4` BRA |
| `00B4CA` | L_B4CA | decoded | `00B4C3` BCS |
| `00B4F9` | L_B4F9 | decoded | `00B4F2` BEQ |
| `00B4FE` | L_B4FE | decoded | `00B4EE` BEQ |
| `00B500` | L_B500 | decoded | `00B4F7` BRA<br>`00B4FC` BRA |
| `00B521` | L_B521 | decoded | `00B517` BBC |
| `00B526` | L_B526 | decoded | `00B511` BEQ |
| `00B533` | L_B533 | decoded | `00B52C` BEQ |
| `00B538` | L_B538 | decoded | `00B50C` BEQ |
| `00B545` | L_B545 | decoded | `00B53A` BEQ |
| `00B54A` | L_B54A | decoded | `00B51F` BRA<br>`00B524` BRA<br>`00B536` BRA |
| `00B556` | L_B556 | decoded | `00B506` BEQ<br>`00B515` BEQ |
| `00B558` | L_B558 | decoded | `00B531` BRA<br>`00B543` BRA<br>`00B548` BRA |
| `00B55B` | L_B55B | decoded | `00B554` BCS |
| `00B594` | L_B594 | decoded | `00B56F` BCS<br>`00B574` BCS<br>`00B579` BCS<br>`00B57E` BCS<br>`00B583` BCS<br>`00B588` BCS<br>`00B58D` BCS |
| `00B596` | L_B596 | decoded | `00B592` BCC |
| `00B59D` | L_B59D | decoded | `00AFB7` JSL |
| `00B5AE` | L_B5AE | decoded | `00B5A4` BBC |
| `00B5B1` | L_B5B1 | decoded | `00B59F` BBC<br>`00B5A9` BBC |
| `00B5BE` | L_B5BE | decoded | `00B5B1` BBC<br>`00B5BA` BCC |
| `00B5C2` | L_B5C2 | decoded | `00AD51` JSL |
| `00B5DA` | L_B5DA | decoded | `00B5D2` BBS |
| `00B5E2` | L_B5E2 | decoded | `00B5DE` BCC |
| `00B5F1` | L_B5F1 | decoded | `00B5EA` BCC |
| `00B5F3` | L_B5F3 | decoded | `00B5EF` BCS |
| `00B5F7` | L_B5F7 | decoded | `00ADFB` JSL |
| `00B60F` | L_B60F | decoded | `00B609` BCS |
| `00B624` | L_B624 | decoded | `00B60D` BRA<br>`00B61C` BEQ |
| `00B633` | L_B633 | decoded | `00B622` BRA |
| `00B634` | L_B634 | decoded | `00B631` BRA |
| `00B63E` | L_B63E | decoded | `00B634` BBC |
| `00B645` | L_B645 | decoded | `00B63C` BCC |
| `00B64C` | L_B64C | decoded | `00AE1D` JSL |
| `00B65B` | L_B65B | decoded | `00B653` BBC |
| `00B675` | L_B675 | decoded | `00B65E` BCC |
| `00B679` | L_B679 | decoded | `00B671` BCC |
| `00B67E` | L_B67E | decoded | `00B673` BRA |
| `00B686` | L_B686 | decoded | `00AF3A` JSL |
| `00B694` | L_B694 | decoded | `00B690` BEQ |
| `00B6A9` | L_B6A9 | decoded | `00B69D` BCS<br>`00B6A2` BCS |
| `00B6AC` | L_B6AC | decoded | `00B6A7` BCC |
| `00B6B7` | L_B6B7 | decoded | `00B6B2` BCC |
| `00B6B8` | L_B6B8 | decoded | `00AF46` JSL |
| `00B6F4` | L_B6F4 | decoded | `00B6EA` BMI |
| `00B6F9` | L_B6F9 | decoded | `00B6EF` BPL |
| `00B6FE` | L_B6FE | decoded | `00B6F2` BRA<br>`00B6F7` BPL |
| `00B704` | L_B704 | decoded | `00B6FC` BEQ |
| `00B70B` | L_B70B | decoded | `00AF84` JSL |
| `00B716` | L_B716 | decoded | `00B70B` BBS |
| `00B733` | L_B733 | decoded | `00B714` BRA<br>`00B719` BPL<br>`00B721` BCC<br>`00B72E` BCC |
| `00B738` | L_B738 | decoded | `00AFBB` JSL |
| `00B754` | L_B754 | decoded | `00B748` BBS |
| `00B76F` | L_B76F | decoded | `00B768` BCS |
| `00B774` | L_B774 | decoded | `00B76D` BRA |
| `00B77F` | L_B77F | decoded | `00B774` BBS |
| `00B782` | L_B782 | decoded | `00B77D` BRA |
| `00B791` | L_B791 | decoded | `00B788` BCC<br>`00B78A` BEQ |
| `00B799` | L_B799 | decoded | `00B74E` BBC |
| `00B7A1` | L_B7A1 | decoded | `00B738` BBC |
| `00B7A7` | L_B7A7 | decoded | `00B73D` BBS<br>`00B742` BBS |
| `00B7AB` | L_B7AB | decoded | `00B7A5` BRA |
| `00B7C5` | L_B7C5 | decoded | `00B78F` BRA<br>`00B797` BRA<br>`00B79F` BRA<br>`00B7C0` BCS |
| `00B7D4` | L_B7D4 | decoded | `00B7CB` BBC |
| `00B7E7` | L_B7E7 | decoded | `00B7E0` BMI |
| `00B7FC` | L_B7FC | decoded | `00B7E5` BCS |
| `00B80E` | L_B80E | decoded | `00B808` BCC |
| `00B821` | L_B821 | decoded | `00B7F5` BCC<br>`00B7FA` BRA<br>`00B81C` BCS |
| `00B829` | L_B829 | decoded | `00B7D2` BRA<br>`00BC11` JSL |
| `00B863` | L_B863 | decoded | `00B85C` BPL |
| `00B879` | L_B879 | decoded | `00B874` BCC |
| `00B880` | L_B880 | decoded | `00B82C` BMI |
| `00B892` | L_B892 | decoded | `00B87E` BRA<br>`00B887` BEQ |
| `00B895` | L_B895 | decoded | `00B80A` JMP<br>`00B82E` BBS<br>`00B87C` BCS<br>`00B88F` BCC |
| `00B897` | L_B897 | decoded | `00AFC3` JSL |
| `00B8A3` | L_B8A3 | decoded | `00B89B` BCS<br>`00B89E` BCS |
| `00B8A5` | L_B8A5 | decoded | `00B8A1` BCC |
| `00B8C8` | L_B8C8 | decoded | `00B8AF` BBC<br>`00B8B4` BBS<br>`00B8BF` BCC<br>`00B8C1` BBS |
| `00B8D4` | L_B8D4 | decoded | `00B8DD` BCC<br>`00B8E5` BCC |
| `00B8D5` | L_B8D5 | decoded | `00B8C6` BRA |
| `00B902` | L_B902 | decoded | `00B939` BBC |
| `00B916` | L_B916 | decoded | `00B90F` BCS |
| `00B91E` | L_B91E | decoded | `00B8D5` BBS |
| `00B93E` | L_B93E | decoded | `00B91E` BBS<br>`00B929` BCC<br>`00B932` BCS<br>`00B937` BCS |
| `00B955` | L_B955 | decoded | `00B94F` BEQ |
| `00B95C` | L_B95C | decoded | `00B914` BCC<br>`00B91C` BRA<br>`00B951` BCS |
| `00B963` | L_B963 | decoded | `00B8EA` BCS<br>`00B8F3` BCS<br>`00B8F8` BCS |
| `00B964` | add16 | decoded | `00AF5C` JSL<br>`00B7F1` JSL<br>`00B90B` JSL |
| `00B97A` | sub16_x4 | decoded | `00B130` JSL<br>`00B401` JSL<br>`00B446` JSL<br>`00B48B` JSL<br>`00B4BF` JSL<br>`00B550` JSL |
| `00B986` | sub16 | decoded | `00AFA7` JSL<br>`00B66D` JSL<br>`00B818` JSL<br>`00B94B` JSL |
| `00B98D` | L_B98D | decoded | `00B984` BRA |
| `00B99C` | L_B99C | decoded | `00B3B2` JSL<br>`00B3BF` JSL<br>`00B428` JSL<br>`00B46D` JSL<br>`00B4D7` JSL<br>`00B4E4` JSL |
| `00B9AB` | L_B9AB | decoded | `00B9A4` BCS |
| `00B9AD` | L_B9AD | decoded | `00B9A9` BCC |
| `00B9AE` | L_B9AE | decoded | `00B1F8` JSL |
| `00B9B7` | L_B9B7 | decoded | `00B9B2` BEQ |
| `00B9CF` | L_B9CF | decoded | `00B9C7` BBC |
| `00B9DC` | L_B9DC | decoded | `00B9D6` BCC |
| `00B9E7` | L_B9E7 | decoded | `00B9DF` BBC |
| `00B9F4` | L_B9F4 | decoded | `00B9EE` BCS |
| `00BA03` | L_BA03 | decoded | `00B9FF` BCC |
| `00BA07` | L_BA07 | decoded | `00B9F7` BBC |
| `00BA10` | L_BA10 | decoded | `00BA0A` BCC |
| `00BA5B` | L_BA5B | decoded | `00BA54` BBC |
| `00BA72` | L_BA72 | decoded | `00BA66` BEQ |
| `00BA87` | L_BA87 | decoded | `00BA10` BBC<br>`00BA15` BBS<br>`00BA20` BCC<br>`00BA22` BBC<br>`00BA27` BBC<br>`00BA2C` BBS<br>`00BA31` BBS<br>`00BA36` BBS<br>`00BA3B` BBS<br>`00BA40` BBC<br>`00BA45` BBC<br>`00BA4A` BBS<br>`00BA4F` BBC<br>`00BA59` BRA<br>`00BA5B` BBS<br>`00BA68` BBS<br>`00BA70` BNE<br>`00BA75` BNE<br>`00BA9B` BCS |
| `00BA8B` | L_BA8B | decoded | `00BAA3` BCC |
| `00BA93` | L_BA93 | decoded | `00BA7E` BCC |
| `00BA9D` | L_BA9D | decoded | `00BA83` BEQ<br>`00BA85` BCC<br>`00BA99` BEQ |
| `00BABC` | L_BABC | decoded | `00BAAC` BMI |
| `00BAD2` | L_BAD2 | decoded | `00BABA` BRA |
| `00BAE7` | L_BAE7 | decoded | `00BAEC` BRA |
| `00BAEE` | L_BAEE | decoded | `00BAE7` BEQ |
| `00BAFB` | L_BAFB | decoded | `00BAF2` BEQ<br>`00BAF4` BCC |
| `00BB12` | L_BB12 | decoded | `00BB02` BMI |
| `00BB1E` | L_BB1E | decoded | `00BB1A` BNE |
| `00BB29` | L_BB29 | decoded | `00BB22` BCS |
| `00BB2C` | L_BB2C | decoded | `00BB27` BCC |
| `00BB30` | L_BB30 | decoded | `00BB0B` BCC<br>`00BB10` BRA |
| `00BB46` | L_BB46 | decoded | `00BB40` BCC<br>`00BB42` BEQ |
| `00BB48` | L_BB48 | decoded | `00BB44` BRA |
| `00BB4C` | L_BB4C | decoded | `00BB75` BCC |
| `00BB50` | L_BB50 | decoded | `00BB59` BBS<br>`00BB6B` BEQ<br>`00BB83` BCC |
| `00BB55` | L_BB55 | decoded | `00BB6D` BCS |
| `00BB69` | L_BB69 | decoded | `00BB3D` BPL |
| `00BB6F` | L_BB6F | decoded | `00BB4A` BRA |
| `00BB92` | L_BB92 | decoded | `00BB67` BRA |
| `00BBB6` | L_BBB6 | decoded | `00BBB1` BCC |
| `00BBCE` | L_BBCE | decoded | `00BBC7` BCC |
| `00BBD1` | L_BBD1 | decoded | `00BBCC` BCS |
| `00BBD3` | L_BBD3 | decoded | `00BBC1` BCS |
| `00BBDE` | L_BBDE | decoded | `00BBD7` BCS |
| `00BBE1` | L_BBE1 | decoded | `00BBD1` BRA<br>`00BBDC` BCC |
| `00BBEF` | L_BBEF | decoded | `00BBE9` BCS |
| `00BC05` | L_BC05 | decoded | `00BBF8` BCS |
| `00BC0E` | L_BC0E | decoded | `00BBFE` BCC<br>`00BC03` BRA<br>`00BC09` BCS |
| `00BC15` | L_BC15 | decoded | `00BA8F` JMP<br>`00BB51` JMP |
| `00BC21` | L_BC21 | decoded | `00BAF7` JMP |
| `00BC22` | L_BC22 | decoded | `00ACA5` JSL |
| `00BC29` | L_BC29 | decoded | `003E14` JSL |
| `00BC47` | L_BC47 | decoded | `00BC42` BCS |
| `00BC4F` | L_BC4F | decoded | `00BC4A` BCC |
| `00BC63` | L_BC63 | decoded | `00BC5E` BCC |
| `00BC6B` | L_BC6B | decoded | `00BC66` BCS |
| `00BC6D` | L_BC6D | decoded | `004E12` JSL |
| `00BC95` | L_BC95 | decoded | `00BC80` BBS |
| `00BCA4` | L_BCA4 | decoded | `00BC6D` BBC<br>`00BC7E` BCS<br>`00BC85` BBS<br>`00BC8A` BBC<br>`00BC95` BBC |
| `00BCA8` | L_BCA8 | decoded | `00BC93` BRA |
| `00BCA9` | L_BCA9 | decoded | `00BC77` BCS |
| `00BCC6` | L_BCC6 | decoded | `00BCC2` BCC |
| `00BCC9` | L_BCC9 | decoded | `00BCA2` BRA<br>`00BCAE` BBC<br>`00BCB9` BCS |
| `00BCE6` | L_BCE6 | decoded | `00BCCA` JSL |
| `00BD00` | purge_control | decoded | `004E0A` JSL |
| `00BD09` | L_BD09 | decoded | `00BD00` BBC |
| `00BD18` | L_BD18 | decoded | `00BD09` BBC<br>`00BD0E` BBC |
| `00BD22` | L_BD22 | decoded | `00BD13` BBC |
| `00BD26` | L_BD26 | decoded | `00BD20` BRA |
| `00BD33` | L_BD33 | decoded | `00BD26` BBS |
| `00BD39` | L_BD39 | decoded | `00BD31` BCC |
| `00BD82` | L_BD82 | decoded | `00BD7B` BCS |
| `00BD85` | L_BD85 | decoded | `00BD37` BRA<br>`00BD40` BEQ<br>`00BD80` BCC |
| `00BD94` | L_BD94 | decoded | `00BD8F` BEQ |
| `00BD9C` | L_BD9C | decoded | `00BD89` BCC<br>`00BD92` BRA |
| `00BDAF` | L_BDAF | decoded | `00BDA2` BBC |
| `00BDB9` | L_BDB9 | decoded | `00BDB3` BEQ |
| `00BDCB` | L_BDCB | decoded | `00BDBD` BBS<br>`00BDC2` BBC |
| `00BDD9` | L_BDD9 | decoded | `00BDD1` BBS |
| `00BDE7` | L_BDE7 | decoded | `00BDE3` BCC<br>`00BDF3` BRA |
| `00BDF5` | L_BDF5 | decoded | `00BDEA` BCC |
| `00BDFA` | L_BDFA | decoded | `00BDF0` BCS |
| `00BDFE` | L_BDFE | decoded | `00BDF8` BNE |
| `00BE21` | L_BE21 | decoded | `00BE18` BCS |
| `00BE31` | L_BE31 | decoded | `00BE29` BBS |
| `00BE34` | L_BE34 | decoded | `00BDFC` BRA |
| `00BE4B` | L_BE4B | decoded | `00BE3D` BCC |
| `00BE4F` | L_BE4F | decoded | `00BE3F` BBS<br>`00BE44` BBS |
| `00BE59` | L_BE59 | decoded | `00BE49` BRA |
| `00BE5C` | L_BE5C | decoded | `00BE55` BEQ<br>`00BE57` BCC |
| `00BE6E` | L_BE6E | decoded | `00BE5F` BBS<br>`00BE64` BBS |
| `00BE73` | L_BE73 | decoded | `00BE69` BBC |
| `00BE82` | L_BE82 | decoded | `00BE71` BRA |
| `00BE89` | L_BE89 | decoded | `00BE73` BBC |
| `00BE8C` | L_BE8C | decoded | `00BDC7` JMP<br>`00BE85` BEQ<br>`00BE87` BCC |
| `00BE9A` | L_BE9A | decoded | `00BE92` BNE |
| `00BEAE` | L_BEAE | decoded | `00BEC1` BRA |
| `00BEB3` | L_BEB3 | decoded | `00BE9E` BCC |
| `00BEC3` | L_BEC3 | decoded | `00BE98` BRA<br>`00BEA7` BCS<br>`00BEAC` BCS<br>`00BEB1` BRA<br>`00BEBA` BCC<br>`00BEBF` BCC |
| `00BED6` | L_BED6 | decoded | `00BDAB` JMP<br>`00BEC6` BNE<br>`00BEC8` BBS<br>`00BECD` BBC |
| `00BED9` | L_BED9 | decoded | `00BDB5` JMP |
| `00BEE9` | L_BEE9 | decoded | `00BEE4` BCC |
| `00BEF0` | L_BEF0 | decoded | `00BEEC` BEQ |
| `00BF2D` | L_BF2D | decoded | `00BF23` BBS |
| `00BF30` | L_BF30 | decoded | `00BF2B` BRA |
| `00BF36` | L_BF36 | decoded | `00BF30` BCS |
| `00BF3A` | L_BF3A | decoded | `00BF01` BBS |
| `00BF40` | L_BF40 | decoded | `00BEEE` BCS<br>`00BEF6` BCC<br>`00BEF8` BBS |
| `00BF4A` | L_BF4A | decoded | `00BF15` BBS<br>`00BF1A` BBS |
| `00BF50` | L_BF50 | decoded | `00BF06` BBS<br>`00BF0B` BBC<br>`00BF10` BBS |
| `00BF54` | L_BF54 | decoded | `00BF4E` BRA |
| `00BF5D` | L_BF5D | decoded | `00BF3E` BRA<br>`00BF48` BRA |
| `00BF5F` | L_BF5F | decoded | `00BF34` BCC<br>`00BF38` BRA<br>`00BF5B` BCS |
| `00BF62` | L_BF62 | decoded | `00BD05` JMP |
| `00BF6F` | L_BF6F | decoded | `00BF67` BCS<br>`00BF69` BBS |
| `00BF85` | L_BF85 | decoded | `00BF91` BNE<br>`00BF9F` BNE |
| `00BF89` | L_BF89 | decoded | `00BF6F` BBS |
| `00BF97` | L_BF97 | decoded | `00BF89` BBS |
| `00BFA9` | L_BFA9 | decoded | `00BF97` BBC |
| `00BFB3` | L_BFB3 | decoded | `00BFA9` BBS |
| `00BFC5` | L_BFC5 | decoded | `00BFB3` BBC |
| `00BFCF` | L_BFCF | decoded | `00BFB1` BRA<br>`00BFBE` BCC<br>`00BFC3` BRA |
| `00BFD7` | L_BFD7 | decoded | `00BFC5` BBC |
| `00BFE1` | L_BFE1 | decoded | `00BFD7` BBC |
| `00BFEB` | L_BFEB | decoded | `00BFE1` BBC |
| `00BFF5` | L_BFF5 | decoded | `00BFEB` BBC |
| `00BFFF` | L_BFFF | decoded | `00BFF5` BBC |
| `00C007` | L_C007 | decoded | `00BFCD` BRA<br>`00BFDF` BRA<br>`00BFE9` BRA<br>`00BFF3` BRA<br>`00BFFD` BRA |
| `00C014` | L_C014 | decoded | `00BFFF` BBC |
| `00C029` | L_C029 | decoded | `00C022` BBC |
| `00C038` | L_C038 | decoded | `00C018` BBS<br>`00C01D` BBS |
| `00C044` | L_C044 | decoded | `00C027` BRA<br>`00C029` BBS<br>`00C02E` BBS<br>`00C033` BBS |
| `00C047` | L_C047 | decoded | `00BFD3` JMP<br>`00C007` BBS<br>`00C012` BRA<br>`00C042` BRA |
| `00C04D` | L_C04D | decoded | `00C049` BCC |
| `00C05A` | L_C05A | decoded | `00C052` BEQ |
| `00C06C` | L_C06C | decoded | `00BF85` JMP<br>`00C058` BRA<br>`00C05A` BBC<br>`00C062` BNE |
| `00C08A` | L_C08A | decoded | `00C07F` BBC |
| `00C091` | L_C091 | decoded | `00C077` BCC |
| `00C0A0` | L_C0A0 | decoded | `00C095` BBC |
| `00C0AF` | L_C0AF | decoded | `00C079` BEQ |
| `00C0B3` | L_C0B3 | decoded | `00BF81` JMP<br>`00C088` BRA<br>`00C08F` BRA<br>`00C09E` BRA<br>`00C0A8` BCC<br>`00C0AD` BRA |
| `00C0C9` | L_C0C9 | decoded | `004E0E` JSL |
| `00C0DC` | L_C0DC | decoded | `00C0C9` BBC |
| `00C0E0` | L_C0E0 | decoded | `00C0DA` BRA |
| `00C0E5` | L_C0E5 | decoded | `00C0CE` JSL |
| `00C10D` | L_C10D | decoded | `00C101` BBS |
| `00C112` | L_C112 | decoded | `00C10B` BRA |
| `00C11E` | L_C11E | decoded | `00C0F7` BBC<br>`00C0FC` BBC<br>`00C106` BBS<br>`00C10D` BBS |
| `00C139` | L_C139 | decoded | `00C11E` BBC<br>`00C123` BBS<br>`00C128` BBC |
| `00C152` | L_C152 | decoded | `00C11C` BRA<br>`00C137` BRA |
| `00C158` | L_C158 | decoded | `00C0EB` BCS<br>`00C0ED` BBC<br>`00C0F2` BBS<br>`00C139` BBC<br>`00C13E` BBS<br>`00C143` BBC |
| `00C15C` | L_C15C | decoded | `00C156` BRA |
| `00C16C` | L_C16C | decoded | `00C15C` BBS |
| `00C16F` | L_C16F | decoded | `00C16A` BRA |
| `00C183` | L_C183 | decoded | `00C165` BBC<br>`00C17B` BCS |
| `00C18B` | L_C18B | decoded | `00C181` BRA |
| `00C18C` | L_C18C | decoded | `00C0D2` JSL |
| `00C199` | L_C199 | decoded | `00C190` BBC |
| `00C1AF` | L_C1AF | decoded | `00C199` BBC |
| `00C1BE` | L_C1BE | decoded | `00C1B2` BBC<br>`00C1BA` BCC |
| `00C1C9` | L_C1C9 | decoded | `00C1C1` BCS |
| `00C1CD` | L_C1CD | decoded | `00C1C7` BRA |
| `00C1DC` | L_C1DC | decoded | `00C1D0` BBC<br>`00C1D8` BCC |
| `00C1E7` | L_C1E7 | decoded | `00C1DF` BCS |
| `00C1EB` | L_C1EB | decoded | `00C1E5` BRA |
| `00C1FA` | L_C1FA | decoded | `00C1EE` BBC<br>`00C1F6` BCC |
| `00C205` | L_C205 | decoded | `00C1FD` BCS |
| `00C209` | L_C209 | decoded | `00C203` BRA |
| `00C218` | L_C218 | decoded | `00C20C` BBC<br>`00C214` BCC |
| `00C223` | L_C223 | decoded | `00C21B` BCS |
| `00C227` | L_C227 | decoded | `00C221` BRA |
| `00C236` | L_C236 | decoded | `00C22A` BBC<br>`00C232` BCC |
| `00C241` | L_C241 | decoded | `00C239` BCS |
| `00C245` | L_C245 | decoded | `00C23F` BRA |
| `00C254` | L_C254 | decoded | `00C248` BBC<br>`00C250` BCC |
| `00C25F` | L_C25F | decoded | `00C257` BCS |
| `00C263` | L_C263 | decoded | `00C25D` BRA |
| `00C283` | L_C283 | decoded | `00C27C` BBC |
| `00C28F` | L_C28F | decoded | `00C288` BBC |
| `00C29B` | L_C29B | decoded | `00C28F` BBC<br>`00C294` BBC |
| `00C2BA` | L_C2BA | decoded | `00C263` BBC<br>`00C268` BBS<br>`00C26D` BBC<br>`00C272` BBS<br>`00C277` BBS<br>`00C281` BRA<br>`00C283` BBC<br>`00C28D` BRA<br>`00C299` BRA |
| `00C2BE` | L_C2BE | decoded | `00C29F` BBC<br>`00C2AA` BCC<br>`00C2B2` BCC |
| `00C2C8` | L_C2C8 | decoded | `00C2B8` BRA |
| `00C2E8` | L_C2E8 | decoded | `00C2CD` BEQ |
| `00C2ED` | L_C2ED | decoded | `00C2D2` BMI |
| `00C308` | L_C308 | decoded | `00C333` BNE |
| `00C317` | L_C317 | decoded | `00C30B` BBS<br>`00C313` BCS |
| `00C322` | L_C322 | decoded | `00C31A` BCS |
| `00C326` | L_C326 | decoded | `00C320` BRA |
| `00C330` | L_C330 | decoded | `00C2D7` BCC<br>`00C2F3` BCC<br>`00C2F8` BPL<br>`00C300` BCC |
| `00C335` | L_C335 | decoded | `00C2DC` BMI<br>`00C2E1` BCC<br>`00C326` BBC |
| `00C33C` | L_C33C | decoded | `00C2E6` BRA<br>`00C2EB` BRA<br>`00C32E` BRA |
| `00C35B` | L_C35B | decoded | `00C34C` BCC |
| `00C368` | L_C368 | decoded | `00C33F` BBC |
| `00C371` | L_C371 | decoded | `00C352` BCC<br>`00C357` BCC<br>`00C35F` BCS<br>`00C364` BCS |
| `00C374` | L_C374 | decoded | `00C2C4` JMP<br>`00C34A` BEQ<br>`00C359` BRA<br>`00C366` BRA<br>`00C36F` BRA |
| `00C38E` | L_C38E | decoded | `00C387` BCC |
| `00C39D` | L_C39D | decoded | `00C377` BBS<br>`00C37C` BBS |
| `00C3A3` | L_C3A3 | decoded | `00C38C` BCC |
| `00C3A7` | L_C3A7 | decoded | `00C397` BCC<br>`00C3A1` BRA |
| `00C3A8` | L_C3A8 | decoded | `00C0D6` JSL |
| `00C3C6` | L_C3C6 | decoded | `00C3CC` BCC |
| `00C3C9` | L_C3C9 | decoded | `00C3BD` BCC |
| `00C3CE` | L_C3CE | decoded | `00C3C2` BCC<br>`00C3C4` BEQ |
| `00C3E0` | L_C3E0 | decoded | `00C3DC` BCC |
| `00C411` | L_C411 | decoded | `00C408` BBS |
| `00C417` | L_C417 | decoded | `00C3A8` BBC<br>`00C3B3` BNE<br>`00C3C7` BRA<br>`00C3DE` BNE<br>`00C3E8` BCC<br>`00C3EA` BBC<br>`00C3EF` BBS |
| `00C41B` | L_C41B | decoded | `00C3FA` BCC |
| `00C41F` | L_C41F | decoded | `00C402` BCC |
| `00C427` | L_C427 | decoded | `00C415` BRA |
| `00C43F` | L_C43F | decoded | `00C434` BCS |
| `00C443` | L_C443 | decoded | `00C43D` BRA |
| `00C460` | L_C460 | decoded | `00C44A` BBC |
| `00C47D` | L_C47D | decoded | `00C457` BCC<br>`00C45E` BRA<br>`00C476` BCS |
| `00C495` | L_C495 | decoded | `00C48E` BCC<br>`00C490` BEQ |
| `00C4A3` | L_C4A3 | decoded | `00C49E` BCS |
| `00C4AE` | L_C4AE | decoded | `00C40D` JMP<br>`00C423` JMP |
| `00C4AF` | L_C4AF | decoded | `00C0E0` JSL |
| `00C4B8` | L_C4B8 | decoded | `00C4AF` BBC |
| `00C4C5` | L_C4C5 | decoded | `00C4C1` BEQ |
| `00C4D8` | L_C4D8 | decoded | `00C4E4` BCS |
| `00C4DC` | L_C4DC | decoded | `00C4C3` BCS<br>`00C4D6` BCS |
| `00C4E0` | L_C4E0 | decoded | `00C4D1` BCS |
| `00C4E6` | L_C4E6 | decoded | `00C4C8` BCC |
| `00C4E8` | L_C4E8 | decoded | `00C4DA` BCC<br>`00C4DE` BRA |
| `00C4F9` | L_C4F9 | decoded | `00C4B6` BRA |
| `00C502` | L_C502 | decoded | `0044AA` JSL<br>`004A66` JSL |
| `00C50A` | L_C50A | decoded | `006603` JSL |
| `00C511` | L_C511 | decoded | `0049DC` JSL<br>`004A25` JSL<br>`00C508` BRA |
| `00C52C` | L_C52C | decoded | `00C51C` BBS |
| `00C530` | L_C530 | decoded | `00C52A` BRA |
| `00C545` | L_C545 | decoded | `00C540` BCS |
| `00C54F` | L_C54F | decoded | `00C521` BBC<br>`00C530` BBS<br>`00C535` BBC |
| `00C552` | L_C552 | decoded | `00C548` BCC<br>`00C54D` BRA |
| `00C57D` | L_C57D | decoded | `00C56E` BBS |
| `00C58B` | L_C58B | decoded | `00C57B` BRA |
| `00C58E` | L_C58E | decoded | `00C514` BBC<br>`00C565` BBS<br>`00C573` BBS |
| `00C5A6` | L_C5A6 | decoded | `00C596` BBS |
| `00C5AA` | L_C5AA | decoded | `00C5A4` BRA |
| `00C5BF` | L_C5BF | decoded | `00C5BA` BCS |
| `00C5C9` | L_C5C9 | decoded | `00C59B` BBC<br>`00C5AA` BBS<br>`00C5AF` BBC |
| `00C5CC` | L_C5CC | decoded | `00C5C2` BCC<br>`00C5C7` BRA |
| `00C5F7` | L_C5F7 | decoded | `00C5E8` BBS |
| `00C605` | L_C605 | decoded | `00C5F5` BRA |
| `00C608` | L_C608 | decoded | `00C58E` BBC<br>`00C5DF` BBS<br>`00C5ED` BBS |
| `00C620` | L_C620 | decoded | `00C610` BBS |
| `00C624` | L_C624 | decoded | `00C61E` BRA |
| `00C639` | L_C639 | decoded | `00C634` BCS |
| `00C643` | L_C643 | decoded | `00C615` BBC<br>`00C624` BBS<br>`00C629` BBC |
| `00C646` | L_C646 | decoded | `00C63C` BCC<br>`00C641` BRA |
| `00C671` | L_C671 | decoded | `00C662` BBS |
| `00C67F` | L_C67F | decoded | `00C66F` BRA |
| `00C682` | L_C682 | decoded | `00C608` BBC<br>`00C659` BBS<br>`00C667` BBS |
| `00C69A` | L_C69A | decoded | `00C68A` BBS |
| `00C69E` | L_C69E | decoded | `00C698` BRA |
| `00C6B3` | L_C6B3 | decoded | `00C6AE` BCS |
| `00C6BD` | L_C6BD | decoded | `00C68F` BBC<br>`00C69E` BBS<br>`00C6A3` BBC |
| `00C6C0` | L_C6C0 | decoded | `00C6B6` BCC<br>`00C6BB` BRA |
| `00C6EB` | L_C6EB | decoded | `00C6DC` BBS |
| `00C6F9` | L_C6F9 | decoded | `00C6E9` BRA |
| `00C6FC` | L_C6FC | decoded | `00C682` BBC<br>`00C6D3` BBS<br>`00C6E1` BBS |
| `00C714` | L_C714 | decoded | `00C704` BBS |
| `00C718` | L_C718 | decoded | `00C712` BRA |
| `00C72D` | L_C72D | decoded | `00C728` BCS |
| `00C737` | L_C737 | decoded | `00C709` BBC<br>`00C718` BBS<br>`00C71D` BBC |
| `00C73A` | L_C73A | decoded | `00C730` BCC<br>`00C735` BRA |
| `00C765` | L_C765 | decoded | `00C756` BBS |
| `00C773` | L_C773 | decoded | `00C763` BRA |
| `00C776` | L_C776 | decoded | `00C6FC` BBC<br>`00C74D` BBS<br>`00C75B` BBS |
| `00C78E` | L_C78E | decoded | `00C77E` BBS |
| `00C792` | L_C792 | decoded | `00C78C` BRA |
| `00C7A7` | L_C7A7 | decoded | `00C7A2` BCS |
| `00C7B1` | L_C7B1 | decoded | `00C783` BBC<br>`00C792` BBS<br>`00C797` BBC |
| `00C7B4` | L_C7B4 | decoded | `00C7AA` BCC<br>`00C7AF` BRA |
| `00C7DF` | L_C7DF | decoded | `00C7D0` BBS |
| `00C7ED` | L_C7ED | decoded | `00C7DD` BRA |
| `00C7F0` | L_C7F0 | decoded | `00C776` BBC<br>`00C7C7` BBS<br>`00C7D5` BBS |
| `00C7F5` | mailbox_receive | decoded | `004DD4` JSL |
| `00C7FB` | L_C7FB | decoded | `00C7F5` BBS |
| `00C801` | L_C801 | decoded | `00C7FB` BBC |
| `00C807` | L_C807 | decoded | `00C801` BBS |
| `00C840` | L_C840 | decoded | `00C823` BBC |
| `00C8E2` | L_C8E2 | decoded | `00C8D7` BBC |
| `00C92C` | L_C92C | decoded | `00C8E7` BNE |
| `00C964` | L_C964 | decoded | `00C92E` BNE |
| `00C97E` | L_C97E | decoded | `00C966` BNE |
| `00C9A8` | L_C9A8 | decoded | `00C99D` BBC |
| `00C9AC` | L_C9AC | decoded | `00C9A6` BRA |
| `00C9C7` | L_C9C7 | decoded | `00C9AC` BBS<br>`00C9B9` BBS<br>`00C9BE` BBC |
| `00C9D4` | L_C9D4 | decoded | `00C9C7` BBS |
| `00C9E8` | L_C9E8 | decoded | `00C980` BNE |
| `00CA20` | L_CA20 | decoded | `00C9EA` BNE |
| `00CA58` | L_CA58 | decoded | `00CA22` BNE |
| `00CA90` | L_CA90 | decoded | `00CA5A` BNE |
| `00CAC4` | L_CAC4 | decoded | `00C929` JMP<br>`00C960` JMP<br>`00C97A` JMP<br>`00C9E4` JMP<br>`00CA1C` JMP<br>`00CA54` JMP<br>`00CA8C` JMP<br>`00CA92` BNE |
| `00CAD2` | L_CAD2 | decoded | `00CACC` BEQ |
| `00CAD7` | L_CAD7 | decoded | `00C859` JSL |
| `00CAE2` | L_CAE2 | decoded | `00CAEF` BRA |
| `00CAF1` | L_CAF1 | decoded | `00CAE5` BEQ |
| `00CAF4` | L_CAF4 | decoded | `00CADA` BEQ<br>`00CAEB` BCS |
| `00CB01` | L_CB01 | decoded | `00CAF1` JMP (pointer=00CBAB; X=00) |
| `00CB15` | L_CB15 | decoded | `00CB01` BBS |
| `00CB24` | L_CB24 | decoded | `00CAF1` JMP (pointer=00CBAD; X=02) |
| `00CB33` | L_CB33 | decoded | `00CAF1` JMP (pointer=00CBAF; X=04) |
| `00CB42` | L_CB42 | decoded | `00CAF1` JMP (pointer=00CBB1; X=06) |
| `00CB51` | L_CB51 | decoded | `00CAF1` JMP (pointer=00CBB3; X=08) |
| `00CB60` | L_CB60 | decoded | `00CAF1` JMP (pointer=00CBB5; X=0A) |
| `00CB6F` | L_CB6F | decoded | `00CAF1` JMP (pointer=00CBB7; X=0C) |
| `00CB7E` | L_CB7E | decoded | `00CAF1` JMP (pointer=00CBB9; X=0E) |
| `00CB8D` | L_CB8D | decoded | `00CAF1` JMP (pointer=00CBBB; X=10) |
| `00CB99` | L_CB99 | decoded | `00CB12` JMP<br>`00CB21` JMP<br>`00CB30` JMP<br>`00CB3F` JMP<br>`00CB4E` JMP<br>`00CB5D` JMP<br>`00CB6C` JMP<br>`00CB7B` JMP<br>`00CB8A` JMP |
| `00CBBD` | L_CBBD | decoded | `004DC9` JSL |
| `00CBC4` | L_CBC4 | decoded | `00CBC4` BBC |
| `00CBE1` | L_CBE1 | decoded | `00CBDD` BCS |
| `00CC3F` | L_CC3F | decoded | `00CC22` BBS |
| `00CC51` | L_CC51 | decoded | `00CC3F` BBC<br>`00CC4A` BCC<br>`00CC4C` BEQ |
| `00CC52` | mailbox_send | decoded | `004DF2` JSL |
| `00CC6B` | L_CC6B | decoded | `00CC5B` BBC<br>`00CC60` BBS |
| `00CC88` | L_CC88 | decoded | `00CC56` BBC<br>`00CC70` BNE |
| `00CC8C` | L_CC8C | decoded | `00CC80` BEQ<br>`00CC86` BRA |
| `00CC8D` | L_CC8D | decoded | `00CC72` BBS |
| `00CC96` | L_CC96 | decoded | `00CC8D` BBC |
| `00CCA6` | L_CCA6 | decoded | `00CC65` BBC<br>`00CC9E` BEQ |
| `00CD62` | L_CD62 | decoded | `00CD59` BBC |
| `00CDAC` | L_CDAC | decoded | `00CD94` BBC |
| `00CDEB` | L_CDEB | decoded | `00CDE4` BBC |
| `00CDEF` | L_CDEF | decoded | `00CDDF` BBC<br>`00CDE9` BRA |
| `00CDFF` | L_CDFF | decoded | `00CDF6` BBC |
| `00CE0B` | L_CE0B | decoded | `00CDF4` BNE |
| `00CE18` | L_CE18 | decoded | `00CE0F` BBC |
| `00CE24` | L_CE24 | decoded | `00CE0D` BNE |
| `00CE31` | L_CE31 | decoded | `00CE28` BBC |
| `00CE51` | L_CE51 | decoded | `00CE3D` BBS |
| `00CE54` | L_CE54 | decoded | `00CE26` BNE |
| `00CE66` | L_CE66 | decoded | `00CE5D` BBC |
| `00CE8E` | L_CE8E | decoded | `00CE58` BBS |
| `00CE91` | L_CE91 | decoded | `00CE56` BNE |
| `00CE9E` | L_CE9E | decoded | `00CE95` BBC |
| `00CEC9` | L_CEC9 | decoded | `00CE93` BNE |
| `00CED6` | L_CED6 | decoded | `00CECD` BBC |
| `00CF01` | L_CF01 | decoded | `00CECB` BNE |
| `00CF0E` | L_CF0E | decoded | `00CF05` BBC |
| `00CF31` | L_CF31 | decoded | `00CF1D` BBS |
| `00CF34` | L_CF34 | decoded | `00CF03` BNE |
| `00CF41` | L_CF41 | decoded | `00CF38` BBC |
| `00CF55` | L_CF55 | decoded | `00CE08` JMP<br>`00CE21` JMP<br>`00CE51` JMP<br>`00CE8E` JMP<br>`00CEC6` JMP<br>`00CEFE` JMP<br>`00CF31` JMP<br>`00CF36` BNE |
| `00CF5A` | L_CF5A | decoded | `004DA5` JSL |
| `00CF70` | L_CF70 | decoded | `00CF69` BBC |
| `00CF77` | L_CF77 | decoded | `00CF70` BBC |
| `00CF92` | L_CF92 | decoded | `00CF8B` BBC |
| `00CF99` | L_CF99 | decoded | `00CF92` BBC |
| `00CFB3` | L_CFB3 | decoded | `00CF5A` BBS<br>`00CF5F` BBS<br>`00CF64` BBS<br>`00CF6E` BRA<br>`00CF75` BRA<br>`00CF77` BBS<br>`00CF7C` BBS<br>`00CF81` BBS<br>`00CF86` BBS<br>`00CF90` BRA<br>`00CF97` BRA<br>`00CF99` BBS<br>`00CF9E` BBS<br>`00CFA3` BBS<br>`00CFA8` BBS |
| `00CFB7` | L_CFB7 | decoded | `00CFB1` BRA |
| `00CFCD` | L_CFCD | decoded | `00CFC6` BBC |
| `00CFD4` | L_CFD4 | decoded | `00CFCD` BBC |
| `00CFF8` | L_CFF8 | decoded | `00CFB7` BBS<br>`00CFBC` BBS<br>`00CFC1` BBS<br>`00CFCB` BRA<br>`00CFD2` BRA<br>`00CFD4` BBS<br>`00CFD9` BBS<br>`00CFDE` BBS<br>`00CFE3` BBS<br>`00CFE8` BBS<br>`00CFED` BBS |
| `00CFFC` | L_CFFC | decoded | `00CFF6` BRA |
| `00D06B` | L_D06B | decoded | `00CFFC` BBS<br>`00D001` BBS<br>`00D006` BBS<br>`00D00B` BBS<br>`00D010` BBS<br>`00D015` BBS<br>`00D01A` BBS<br>`00D01F` BBS<br>`00D024` BBS<br>`00D029` BBS<br>`00D02E` BBS<br>`00D033` BBS<br>`00D038` BBS<br>`00D03D` BBS<br>`00D042` BBS<br>`00D047` BBS<br>`00D04C` BBS<br>`00D051` BBS<br>`00D056` BBS<br>`00D05B` BBS<br>`00D060` BBS |
| `00D06F` | L_D06F | decoded | `00D069` BRA |
| `00D08D` | L_D08D | decoded | `00D06F` BBS<br>`00D074` BBS<br>`00D079` BBS<br>`00D07E` BBS |
| `00D095` | L_D095 | decoded | `00D08B` BRA |
| `00D0AA` | L_D0AA | decoded | `00D095` BBS<br>`00D09A` BBS<br>`00D09F` BBS |
| `00D0AE` | L_D0AE | decoded | `00D0A8` BRA |
| `00D0AF` | L_D0AF | decoded | `00CE04` JSL<br>`00CE1D` JSL<br>`00CE36` JSL |
| `00D0D6` | L_D0D6 | decoded | `00D0ED` BCC |
| `00D0E2` | L_D0E2 | decoded | `00D123` JMP |
| `00D0EF` | L_D0EF | decoded | `00D0E8` BCS |
| `00D0F3` | L_D0F3 | decoded | `00D0D9` BNE<br>`00D11B` JMP |
| `00D112` | L_D112 | decoded | `00D107` BCS |
| `00D114` | L_D114 | decoded | `00D0FB` BEQ |
| `00D11F` | L_D11F | decoded | `00D119` BCS |
| `00D127` | L_D127 | decoded | `00D0EF` JMP |
| `00D128` | dtc_task | decoded | `004D91` JSL |
| `00D139` | L_D139 | decoded | `00D13E` BRA |
| `00D140` | L_D140 | decoded | `00D12B` BEQ |
| `00D148` | L_D148 | decoded | `00D140` BBS |
| `00D150` | L_D150 | decoded | `00D13B` BCS |
| `00D163` | L_D163 | decoded | `00D17A` BRA |
| `00D16A` | L_D16A | decoded | `00D163` BBS |
| `00D16E` | L_D16E | decoded | `00D168` BRA |
| `00D174` | L_D174 | decoded | `00D15A` BBS |
| `00D17C` | L_D17C | decoded | `00D150` BBS<br>`00D155` BBC |
| `00D187` | L_D187 | decoded | `00D17C` BBS |
| `00D198` | L_D198 | decoded | `00D191` BBS |
| `00D1B4` | L_D1B4 | decoded | `00D185` BRA<br>`00D196` BRA |
| `00D1C8` | L_D1C8 | decoded | `00D1CB` BCC |
| `00D1CF` | L_D1CF | decoded | `00D1BB` BBS |
| `00D1D2` | L_D1D2 | decoded | `00D1CD` BRA |
| `00D1DC` | L_D1DC | decoded | `00D1C3` BEQ<br>`00D1D6` BCC |
| `00D1E7` | L_D1E7 | decoded | `00D145` JMP<br>`00D172` BRA |
| `00D1E8` | dtc_from_subcpu | decoded | `004D95` JSL |
| `00D1F1` | L_D1F1 | decoded | `00D1FD` BCC |
| `00D1F9` | L_D1F9 | decoded | `00D235` BRA |
| `00D200` | L_D200 | decoded | `00D1F4` BNE<br>`00D22F` BCC |
| `00D228` | L_D228 | decoded | `00D20E` BEQ<br>`00D212` BEQ<br>`00D216` BEQ<br>`00D21A` BEQ<br>`00D21E` BEQ<br>`00D222` BEQ |
| `00D22A` | L_D22A | decoded | `00D208` BEQ |
| `00D237` | dtc_from_subcpu_2 | decoded | `004D99` JSL |
| `00D244` | L_D244 | decoded | `00D23C` BEQ |
| `00D251` | L_D251 | decoded | `00D249` BEQ |
| `00D25E` | L_D25E | decoded | `00D256` BEQ |
| `00D26B` | L_D26B | decoded | `00D263` BEQ |
| `00D278` | L_D278 | decoded | `00D270` BEQ |
| `00D279` | L_D279 | decoded | `004D9D` JSL |
| `00D284` | L_D284 | decoded | `00D279` BBC |
| `00D28F` | L_D28F | decoded | `00D284` BBC |
| `00D29A` | L_D29A | decoded | `00D28F` BBC |
| `00D2A9` | L_D2A9 | decoded | `00D29A` BBC |
| `00D2B4` | L_D2B4 | decoded | `00D2A9` BBC |
| `00D2CA` | L_D2CA | decoded | `00D2B4` BBC<br>`00D2B9` BBC |
| `00D2CB` | L_D2CB | decoded | `004DA1` JSL |
| `00D2D6` | L_D2D6 | decoded | `00D2CB` BBC |
| `00D2E1` | L_D2E1 | decoded | `00D2D6` BBC |
| `00D2EC` | L_D2EC | decoded | `00D2E1` BBC |
| `00D2F7` | L_D2F7 | decoded | `00D2EC` BBC |
| `00D302` | L_D302 | decoded | `00D2F7` BBC |
| `00D30D` | L_D30D | decoded | `00D302` BBC |
| `00D318` | L_D318 | decoded | `00D30D` BBC |
| `00D323` | L_D323 | decoded | `00D318` BBC |
| `00D32E` | L_D32E | decoded | `00D323` BBC |
| `00D339` | L_D339 | decoded | `00D32E` BBC |
| `00D344` | L_D344 | decoded | `00D339` BBC |
| `00D34F` | L_D34F | decoded | `00D344` BBC |
| `00D35A` | L_D35A | decoded | `00D34F` BBC |
| `00D365` | L_D365 | decoded | `00D35A` BBC |
| `00D370` | L_D370 | decoded | `00D365` BBC |
| `00D371` | dtc_confirm | decoded | `0055A2` JSL<br>`0058AB` JSL<br>`00D280` JSL<br>`00D28B` JSL<br>`00D296` JSL<br>`00D2B0` JSL<br>`00D2C0` JSL<br>`00D2C6` JSL |
| `00D37E` | L_D37E | decoded | `00D375` BBC |
| `00D3D8` | L_D3D8 | decoded | `00D37A` JMP |
| `00D3DA` | L_D3DA | decoded | `004ADC` JMP |
| `00D3EF` | L_D3EF | decoded | `00D3E4` BBC |
| `00D3F2` | L_D3F2 | decoded | `00D3E0` BEQ |
| `00D3F6` | L_D3F6 | decoded | `00A1F4` JSL |
| `00D40E` | L_D40E | decoded | `00D406` BBC |
| `00D416` | L_D416 | decoded | `00D40E` BBC |
| `00D41E` | L_D41E | decoded | `00D416` BBC |
| `00D426` | L_D426 | decoded | `00D41E` BBC |
| `00D42E` | L_D42E | decoded | `00D426` BBC |
| `00D436` | L_D436 | decoded | `00D3F6` BBC<br>`00D42E` BBC |
| `00D43F` | L_D43F | decoded | `00D455` BCC |
| `00D44B` | L_D44B | decoded | `00D443` BCC |
| `00D44F` | L_D44F | decoded | `00D449` BRA |
| `00D457` | L_D457 | decoded | `00D43A` BEQ |
| `00D46A` | L_D46A | decoded | `004121` JSL<br>`004DC1` JSL |
| `00D473` | L_D473 | decoded | `00D47F` BCC |
| `00D47C` | L_D47C | decoded | `00D4D2` JMP |
| `00D487` | L_D487 | decoded | `00D495` BRA |
| `00D497` | L_D497 | decoded | `00D491` BCS |
| `00D498` | L_D498 | decoded | `00D476` BNE<br>`00D4CB` BCC |
| `00D4C4` | L_D4C4 | decoded | `00D4AC` BCS |
| `00D4C6` | L_D4C6 | decoded | `00D4A0` BEQ |
| `00D4D6` | L_D4D6 | decoded | `004DAD` JSL |
| `00D4E4` | L_D4E4 | decoded | `00D4DF` BCC |
| `00D4ED` | L_D4ED | decoded | `00D4E4` BBS |
| `00D4F8` | L_D4F8 | decoded | `00D4F3` BCC |
| `00D508` | L_D508 | decoded | `00D4FF` BCC<br>`00D503` BCC |
| `00D512` | L_D512 | decoded | `00D50D` BCC |
| `00D51C` | L_D51C | decoded | `00D512` BBS |
| `00D538` | L_D538 | decoded | `00D517` BBC<br>`00D51F` BBC<br>`00D529` BCS |
| `00D53C` | L_D53C | decoded | `00D531` BCC<br>`00D536` BRA |
| `00D546` | L_D546 | decoded | `00D53C` BBS |
| `00D55E` | L_D55E | decoded | `00D54B` BCC<br>`00D54F` BCS |
| `00D562` | L_D562 | decoded | `00D557` BCC<br>`00D55C` BRA |
| `00D57A` | L_D57A | decoded | `00D541` BBC |
| `00D57E` | L_D57E | decoded | `00D567` BCC<br>`00D56B` BCS |
| `00D582` | L_D582 | decoded | `00D573` BCC<br>`00D578` BRA |
| `00D587` | L_D587 | decoded | `0094B8` JSL |
| `00D599` | L_D599 | decoded | `00D58C` BBC |
| `00D5AB` | L_D5AB | decoded | `00D59E` BBC |
| `00D5B2` | L_D5B2 | decoded | `00D5AB` BBS |
| `00D5E3` | L_D5E3 | decoded | `00D587` BBC<br>`00D599` BBC<br>`00D5B0` BRA<br>`00D5B2` BBS |
| `00D5E4` | L_D5E4 | decoded | `00D5DB` JSL |
| `00D5EA` | L_D5EA | decoded | `00D5F9` BRA |
| `00D5F7` | L_D5F7 | decoded | `00D5F4` BCC |
| `00D5FB` | L_D5FB | decoded | `00D5A7` JSL |
| `00D604` | dtc_find_pcode | decoded | `00D610` BCC |
| `00D60D` | L_D60D | decoded | `00D652` JMP |
| `00D613` | L_D613 | decoded | `00D607` BNE<br>`00D64B` BCC |
| `00D643` | L_D643 | decoded | `00D627` BCC<br>`00D63C` BNE |
| `00D646` | L_D646 | decoded | `00D61B` BEQ |
| `00D656` | L_D656 | decoded | `00D5DF` JSL |
| `00D6C6` | L_D6C6 | decoded | `00D659` BNE<br>`00D65E` BNE<br>`00D663` BNE<br>`00D668` BNE<br>`00D66D` BNE<br>`00D674` BNE<br>`00D67B` BNE<br>`00D680` BNE<br>`00D685` BNE<br>`00D68A` BNE<br>`00D68F` BNE<br>`00D694` BNE<br>`00D699` BNE<br>`00D6A0` BNE<br>`00D6A7` BNE<br>`00D6AC` BNE<br>`00D6B1` BNE<br>`00D6B6` BNE<br>`00D6B8` BBS<br>`00D6BD` BBC |
| `00D6C7` | L_D6C7 | decoded | `00D591` JSL |
| `00D6D0` | L_D6D0 | decoded | `00D6C7` BBC |
| `00D6EE` | L_D6EE | decoded | `00D6E4` BBS |
| `00D6F6` | L_D6F6 | decoded | `00D6F1` BNE |
| `00D707` | L_D707 | decoded | `00D6D0` BBC |
| `00D70F` | L_D70F | decoded | `00D70A` BNE |
| `00D716` | L_D716 | decoded | `00D6DA` BBS<br>`00D6DF` BBS |
| `00D732` | L_D732 | decoded | `00D72C` BEQ |
| `00D736` | L_D736 | decoded | `00D716` BBS<br>`00D71B` BBC<br>`00D725` BNE<br>`00D730` BNE |
| `00D74E` | L_D74E | decoded | `00D6CC` JMP<br>`00D6D5` BBC<br>`00D6E9` BBC<br>`00D6FB` BCC<br>`00D705` BRA<br>`00D714` BCC |
| `00D74F` | L_D74F | decoded | `00D595` JSL |
| `00D758` | L_D758 | decoded | `00D74F` BBC |
| `00D776` | L_D776 | decoded | `00D76C` BBS |
| `00D77E` | L_D77E | decoded | `00D779` BNE |
| `00D78F` | L_D78F | decoded | `00D758` BBC |
| `00D797` | L_D797 | decoded | `00D792` BNE |
| `00D79E` | L_D79E | decoded | `00D762` BBS<br>`00D767` BBS |
| `00D7BA` | L_D7BA | decoded | `00D7B4` BEQ |
| `00D7BE` | L_D7BE | decoded | `00D79E` BBS<br>`00D7A3` BBC<br>`00D7AD` BNE<br>`00D7B8` BNE |
| `00D7D6` | L_D7D6 | decoded | `00D754` JMP<br>`00D75D` BBC<br>`00D771` BBC<br>`00D783` BCC<br>`00D78D` BRA<br>`00D79C` BCC |
| `00D7D7` | L_D7D7 | decoded | `00D5A3` JSL |
| `00D7DC` | L_D7DC | decoded | `00D82E` BCC |
| `00D7E0` | L_D7E0 | decoded | `00D7EC` BCC |
| `00D7EF` | L_D7EF | decoded | `00D7E3` BNE<br>`00D828` BCC |
| `00D805` | L_D805 | decoded | `00D801` BNE |
| `00D821` | L_D821 | decoded | `00D809` BCC |
| `00D823` | L_D823 | decoded | `00D7F7` BEQ |
| `00D831` | L_D831 | decoded | `00D5B7` JSL |
| `00D83E` | L_D83E | decoded | `00D839` BNE |
| `00D881` | L_D881 | decoded | `00D831` BBS<br>`00D843` BCC |
| `00D882` | L_D882 | decoded | `00D5BB` JSL |
| `00D894` | L_D894 | decoded | `00D88F` BNE |
| `00D8B7` | L_D8B7 | decoded | `00D8B1` BEQ |
| `00D8BB` | L_D8BB | decoded | `00D89B` BBS<br>`00D8A0` BBC<br>`00D8AA` BNE<br>`00D8B5` BNE |
| `00D8D3` | L_D8D3 | decoded | `00D882` BBS<br>`00D887` BBS<br>`00D899` BCC |
| `00D8D4` | L_D8D4 | decoded | `00D5BF` JSL |
| `00D8E6` | L_D8E6 | decoded | `00D8E1` BNE |
| `00D909` | L_D909 | decoded | `00D903` BEQ |
| `00D90D` | L_D90D | decoded | `00D8ED` BBS<br>`00D8F2` BBC<br>`00D8FC` BNE<br>`00D907` BNE |
| `00D925` | L_D925 | decoded | `00D8D4` BBS<br>`00D8D9` BBS<br>`00D8EB` BCC |
| `00D926` | L_D926 | decoded | `004DA9` JSL |
| `00D957` | L_D957 | decoded | `00D92F` BBS<br>`00D934` BBS<br>`00D939` BBS<br>`00D93E` BBS<br>`00D943` BBS<br>`00D948` BBS<br>`00D94D` BBS |
| `00D959` | L_D959 | decoded | `00D952` BBC |
| `00D963` | L_D963 | decoded | `00D959` BBS |
| `00D965` | L_D965 | decoded | `00D95E` BBC |
| `00D979` | L_D979 | decoded | `00D965` BBS<br>`00D96A` BBS<br>`00D96F` BBS |
| `00D97B` | L_D97B | decoded | `00D974` BBC |
| `00D985` | L_D985 | decoded | `00D97B` BBS |
| `00D987` | L_D987 | decoded | `00D980` BBC |
| `00D991` | L_D991 | decoded | `00D987` BBS |
| `00D993` | L_D993 | decoded | `00D98C` BBC |
| `00D9A4` | L_D9A4 | decoded | `00D99D` BBC |
| `00D9AB` | L_D9AB | decoded | `00D9A4` BBC |
| `00D9BC` | L_D9BC | decoded | `00D9B5` BBC |
| `00D9C8` | L_D9C8 | decoded | `00D9C1` BBC |
| `00D9CD` | L_D9CD | decoded | `00D993` BBS<br>`00D998` BBS<br>`00D9A2` BRA<br>`00D9A9` BRA<br>`00D9AB` BBS<br>`00D9B0` BBS<br>`00D9BA` BRA<br>`00D9BC` BBS<br>`00D9C6` BRA |
| `00D9CF` | L_D9CF | decoded | `00D9C8` BBC |
| `00D9D9` | L_D9D9 | decoded | `00D9D3` BNE |
| `00D9E8` | L_D9E8 | decoded | `00D9DF` BBS |
| `00D9EA` | L_D9EA | decoded | `00D9E6` BRA |
| `00D9F4` | L_D9F4 | decoded | `00D9EA` BBS |
| `00D9F6` | L_D9F6 | decoded | `00D9EF` BBC |
| `00DA02` | L_DA02 | decoded | `00D9F6` BBC<br>`00D9FB` BBC |
| `00DA0E` | L_DA0E | decoded | `00DA00` BRA<br>`00DA02` BBS<br>`00DA07` BBS |
| `00DA10` | L_DA10 | decoded | `00DA0C` BRA |
| `00DA1F` | L_DA1F | decoded | `00DA16` BBS |
| `00DA21` | L_DA21 | decoded | `00DA1D` BRA |
| `00DA29` | L_DA29 | decoded | `00DA25` BEQ |
| `00DA31` | L_DA31 | decoded | `00DA3A` BCC |
| `00DA3E` | L_DA3E | decoded | `00DA34` BNE |
| `00DA40` | L_DA40 | decoded | `00DA29` BBC<br>`00DA3C` BRA |
| `00DA5C` | L_DA5C | decoded | `00DA48` BBS<br>`00DA4D` BBS<br>`00DA52` BBS |
| `00DA5E` | L_DA5E | decoded | `00DA57` BBC |
| `00DA72` | L_DA72 | decoded | `00DA5E` BBS<br>`00DA63` BBS<br>`00DA68` BBS |
| `00DA74` | L_DA74 | decoded | `00DA6D` BBC |
| `00DA7B` | L_DA7B | decoded | `00DA77` BEQ |
| `00DA97` | L_DA97 | decoded | `00DA7E` BNE<br>`00DA83` BNE<br>`00DA8C` BNE |
| `00DA99` | L_DA99 | decoded | `00DA95` BEQ |
| `00DAA3` | L_DAA3 | decoded | `00DA99` BBS |
| `00DAA5` | L_DAA5 | decoded | `00DA9E` BBC |
| `00DAB7` | L_DAB7 | decoded | `00DAAD` BBS |
| `00DAB9` | L_DAB9 | decoded | `00DAB2` BBC |
| `00DAC3` | L_DAC3 | decoded | `00DAB9` BBS |
| `00DAC5` | L_DAC5 | decoded | `00DABE` BBC |
| `00DACF` | L_DACF | decoded | `00DAC5` BBS |
| `00DAD1` | L_DAD1 | decoded | `00DACA` BBC |
| `00DADB` | L_DADB | decoded | `00DAD1` BBS |
| `00DADD` | L_DADD | decoded | `00DAD6` BBC |
| `00DAE9` | L_DAE9 | decoded | `00DADD` BBC<br>`00DAE2` BBC |
| `00DAFC` | L_DAFC | decoded | `00DAF5` BNE |
| `00DAFE` | L_DAFE | decoded | `00DAF7` BBC |
| `00DB12` | L_DB12 | decoded | `00DAFE` BBS<br>`00DB03` BBS<br>`00DB08` BBS |
| `00DB14` | L_DB14 | decoded | `00DB0D` BBC |
| `00DB28` | L_DB28 | decoded | `00DB14` BBS<br>`00DB19` BBS<br>`00DB1E` BBS |
| `00DB2A` | L_DB2A | decoded | `00DB23` BBC |
| `00DB31` | L_DB31 | decoded | `00DB2A` BBC |
| `00DB3D` | L_DB3D | decoded | `00DB39` BCS |
| `00DB59` | L_DB59 | decoded | `00DB45` BBS<br>`00DB4A` BBS<br>`00DB4F` BBS |
| `00DB5B` | L_DB5B | decoded | `00DB54` BBC |
| `00DB62` | L_DB62 | decoded | `00DB5B` BBC |
| `00DB6C` | L_DB6C | decoded | `00DB62` BBS |
| `00DB6E` | L_DB6E | decoded | `00DB67` BBC |
| `00DB78` | L_DB78 | decoded | `00DB6E` BBS |
| `00DB7A` | L_DB7A | decoded | `00DB73` BBC |
| `00DB7E` | L_DB7E | decoded | `004D56` JSL |
| `00DB8A` | L_DB8A | decoded | `00DB83` BBC |
| `00DB9D` | L_DB9D | decoded | `00DB8A` BBC<br>`00DB91` BBC<br>`00DB96` BBS |
| `00DBA4` | L_DBA4 | decoded | `00DB9D` BBC |
| `00DBA8` | L_DBA8 | decoded | `004D24` JSL |
| `00DBB4` | L_DBB4 | decoded | `00DBAD` BBC |
| `00DBC7` | L_DBC7 | decoded | `00DBB4` BBC<br>`00DBBB` BBC<br>`00DBC0` BBS |
| `00DBD6` | L_DBD6 | decoded | `00DBCF` BBC |
| `00DC09` | L_DC09 | decoded | `00D1E3` JSL |
| `00DC15` | L_DC15 | decoded | `00DC09` BBS |
| `00DC1E` | L_DC1E | decoded | `00DC0E` BBC |
| `00DC28` | L_DC28 | decoded | `00D16E` JSL |
| `00DC37` | L_DC37 | decoded | `00D3BC` JSL<br>`00DF80` JSL |
| `00DC43` | L_DC43 | decoded | `00DC37` BBS |
| `00DC4C` | L_DC4C | decoded | `00DC3C` BBC |
| `00DC52` | ffrm_capture | decoded | `00DF1B` JSL |
| `00DC61` | L_DC61 | decoded | `00DC13` BRA<br>`00DC1C` BNE<br>`00DC28` BBS<br>`00DC41` BRA<br>`00DC4A` BNE<br>`00DC52` BBS |
| `00DC62` | L_DC62 | decoded | `00DC26` BRA<br>`00DC35` BRA<br>`00DC50` BRA<br>`00DC5F` BRA |
| `00DC9B` | L_DC9B | decoded | `00DC83` BBC |
| `00DC9E` | L_DC9E | decoded | `00DC94` BEQ<br>`00DC99` BRA |
| `00DCD3` | L_DCD3 | decoded | `00DCCD` BCC<br>`00DCD0` BNE |
| `00DCD7` | L_DCD7 | decoded | `00DCD4` BNE |
| `00DCE8` | L_DCE8 | decoded | `00DCE4` BCC |
| `00DCF9` | L_DCF9 | decoded | `00DCF5` BCC |
| `00DD0A` | L_DD0A | decoded | `00DD06` BCC |
| `00DD1E` | L_DD1E | decoded | `00DD1A` BCC |
| `00DD2C` | L_DD2C | decoded | `00DD28` BCC |
| `00DD34` | L_DD34 | decoded | `004DB1` JSL |
| `00DD71` | L_DD71 | decoded | `00DD6C` BCC |
| `00DD74` | L_DD74 | decoded | `00DD34` BBC |
| `00DD84` | L_DD84 | decoded | `00DD80` BEQ |
| `00DD88` | L_DD88 | decoded | `00DD39` BBS<br>`00DD82` BCS |
| `00DD8A` | L_DD8A | decoded | `00DD72` BRA<br>`00DD86` BRA |
| `00DDCA` | L_DDCA | decoded | `00DD93` BBC |
| `00DDCF` | L_DDCF | decoded | `00DD98` BBS<br>`00DD9D` BBS<br>`00DDA2` BBS<br>`00DDA7` BBS<br>`00DDAC` BBS<br>`00DDB1` BBS<br>`00DDB6` BBS<br>`00DDBB` BBS<br>`00DDC0` BBS<br>`00DDC5` BBS |
| `00DDD3` | L_DDD3 | decoded | `00DDCA` BBC |
| `00DDD5` | L_DDD5 | decoded | `00DDD1` BRA |
| `00DDE9` | L_DDE9 | decoded | `00DDD5` BBC |
| `00DDED` | L_DDED | decoded | `00DDDE` BBS |
| `00DDF1` | L_DDF1 | decoded | `00DDE7` BRA<br>`00DDEB` BRA |
| `00DDFA` | L_DDFA | decoded | `00DDF1` BBC |
| `00DE00` | L_DE00 | decoded | `00DDFC` BNE |
| `00DE40` | L_DE40 | decoded | `00DE09` BBC |
| `00DE45` | L_DE45 | decoded | `00DE0E` BBS<br>`00DE13` BBS<br>`00DE18` BBS<br>`00DE1D` BBS<br>`00DE22` BBS<br>`00DE27` BBS<br>`00DE2C` BBS<br>`00DE31` BBS<br>`00DE36` BBS<br>`00DE3B` BBS |
| `00DE49` | L_DE49 | decoded | `00DE40` BBC |
| `00DE4B` | L_DE4B | decoded | `00DE47` BRA |
| `00DE5F` | L_DE5F | decoded | `00DE4B` BBC |
| `00DE63` | L_DE63 | decoded | `00DE54` BBS |
| `00DE67` | L_DE67 | decoded | `00DE5D` BRA<br>`00DE61` BRA |
| `00DE70` | L_DE70 | decoded | `00DE67` BBC |
| `00DE76` | L_DE76 | decoded | `00DE72` BNE |
| `00DE7D` | dtc_clear_pending_state | decoded | `00C8DD` JSL<br>`00C9C3` JSL<br>`00D63F` JSL<br>`00D6C2` JSL<br>`00D732` JSL<br>`00D7BA` JSL<br>`00D8B7` JSL<br>`00D909` JSL |
| `00DE86` | dtc_detect | decoded | `00D224` JSL<br>`00D240` JSL<br>`00D24D` JSL<br>`00D25A` JSL<br>`00D267` JSL<br>`00D274` JSL<br>`00D2A5` JSL<br>`00D2D2` JSL<br>`00D2DD` JSL<br>`00D2E8` JSL<br>`00D2F3` JSL<br>`00D2FE` JSL<br>`00D309` JSL<br>`00D314` JSL<br>`00D31F` JSL<br>`00D32A` JSL<br>`00D335` JSL<br>`00D340` JSL<br>`00D34B` JSL<br>`00D356` JSL<br>`00D361` JSL<br>`00D36C` JSL<br>`00E34B` JSL<br>`00E4EB` JSL<br>`00F5EB` JSL<br>`00F66A` JSL<br>`00F7BF` JSL<br>`00F991` JSL |
| `00DE8A` | L_DE8A | decoded | `00DEAC` BBS |
| `00DE93` | L_DE93 | decoded | `00DE8A` BBC |
| `00DEC0` | L_DEC0 | decoded | `00DEBB` BEQ |
| `00DECF` | L_DECF | decoded | `00DECA` BEQ |
| `00DF00` | L_DF00 | decoded | `00DEF7` BBC |
| `00DF09` | L_DF09 | decoded | `00DF00` BBC |
| `00DF12` | L_DF12 | decoded | `00DF09` BBC |
| `00DF1B` | L_DF1B | decoded | `00DF12` BBC |
| `00DF21` | L_DF21 | decoded | `00DEFE` BEQ<br>`00DF07` BEQ<br>`00DF10` BEQ<br>`00DF19` BEQ |
| `00DF29` | L_DF29 | decoded | `00DF1F` BRA |
| `00DF2B` | L_DF2B | decoded | `00DEBD` JMP<br>`00DED9` BNE |
| `00DF65` | L_DF65 | decoded | `00DF5C` BBC |
| `00DF6E` | L_DF6E | decoded | `00DF65` BBC |
| `00DF77` | L_DF77 | decoded | `00DF6E` BBC |
| `00DF80` | L_DF80 | decoded | `00DF77` BBC |
| `00DF86` | L_DF86 | decoded | `00DF63` BEQ<br>`00DF6C` BEQ<br>`00DF75` BEQ<br>`00DF7E` BEQ |
| `00DF8E` | L_DF8E | decoded | `00DF84` BRA |
| `00DFA6` | L_DFA6 | decoded | `00DE8F` JMP<br>`00DECC` JMP<br>`00DF29` BRA |
| `00DFAC` | dtc_reset_counter | decoded | `00D1DD` JSL<br>`00D3C8` JSL<br>`00DFA2` JSL |
| `00DFBB` | dtc_snapshot | decoded | `00D371` JSL<br>`00DE86` JSL |
| `00E04F` | dtc_bit | decoded | `00D38F` JSL<br>`00D39B` JSL<br>`00D3B0` JSL<br>`00D3D0` JSL<br>`00DEA4` JSL<br>`00DEB5` JSL<br>`00DEC4` JSL<br>`00DED3` JSL<br>`00DEDF` JSL<br>`00DEEB` JSL<br>`00DF2F` JSL<br>`00DF3B` JSL<br>`00DF50` JSL<br>`00DF9A` JSL |
| `00E05E` | L_E05E | decoded | `00E063` BRA |
| `00E065` | L_E065 | decoded | `00E05E` BEQ |
| `00E066` | L_E066 | decoded | `004E16` JSL |
| `00E080` | L_E080 | decoded | `00E066` BBC<br>`00E06B` BBC<br>`00E070` BBS<br>`00E075` BBS |
| `00E084` | L_E084 | decoded | `00E07E` BRA |
| `00E1B6` | dtc_counter_ptr | decoded | `009838` JSL<br>`009A67` JSL<br>`00D0FF` JSL<br>`00D4A4` JSL<br>`00D61F` JSL<br>`00D7FB` JSL |
| `00E2F6` | p1320_monitor | decoded | `004E26` JSL |
| `00E30D` | L_E30D | decoded | `00E308` BNE |
| `00E323` | L_E323 | decoded | `00E317` BBS |
| `00E34F` | L_E34F | decoded | `00E2F6` BBC<br>`00E2FB` BBC<br>`00E300` BBS<br>`00E30D` BBC<br>`00E312` BBC<br>`00E321` BCC<br>`00E328` BCC |
| `00E351` | L_E351 | decoded | `00E343` BCC |
| `00E354` | L_E354 | decoded | `00E32F` BCC<br>`00E331` BBC |
| `00E355` | L_E355 | decoded | `004D63` JSL |
| `00E363` | L_E363 | decoded | `00E35C` BEQ<br>`00E35E` BCC |
| `00E36B` | L_E36B | decoded | `00E366` BCS |
| `00E382` | L_E382 | decoded | `00E377` BEQ<br>`00E379` BBS |
| `00E399` | L_E399 | decoded | `004D67` JSL |
| `00E3A7` | L_E3A7 | decoded | `00E3A0` BEQ<br>`00E3A2` BCC |
| `00E3AF` | L_E3AF | decoded | `00E3AA` BCS |
| `00E3C6` | L_E3C6 | decoded | `00E3BB` BEQ<br>`00E3BD` BBS |
| `00E3DD` | L_E3DD | decoded | `004E1A` JSL |
| `00E3F4` | L_E3F4 | decoded | `00E3E6` BBC<br>`00E3EB` BBC |
| `00E419` | L_E419 | decoded | `00E3E1` BBC<br>`00E3F4` BBS<br>`00E3F9` BBC<br>`00E402` BCS<br>`00E40D` BCS |
| `00E41D` | L_E41D | decoded | `00E415` BCC<br>`00E46F` BRA |
| `00E425` | L_E425 | decoded | `00E47D` BCC |
| `00E43D` | L_E43D | decoded | `00E404` BBS<br>`00E417` BRA |
| `00E471` | L_E471 | decoded | `00E44B` BEQ<br>`00E456` BEQ<br>`00E459` BBS<br>`00E464` BCS<br>`00E469` BEQ |
| `00E47F` | L_E47F | decoded | `00E472` BBS |
| `00E494` | L_E494 | decoded | `00E483` BBS |
| `00E49D` | L_E49D | decoded | `00E492` BRA<br>`00E498` BEQ |
| `00E4A7` | L_E4A7 | decoded | `00E4A0` BNE |
| `00E4AF` | L_E4AF | decoded | `00E4A8` BNE |
| `00E4B7` | L_E4B7 | decoded | `00E4B0` BNE |
| `00E4BF` | L_E4BF | decoded | `00E4B8` BNE |
| `00E4C7` | L_E4C7 | decoded | `00E4C0` BNE |
| `00E4CA` | L_E4CA | decoded | `00E4A5` BRA<br>`00E4AD` BRA<br>`00E4B5` BRA<br>`00E4BD` BRA<br>`00E4C5` BRA |
| `00E4E9` | L_E4E9 | decoded | `00E3F0` JMP |
| `00E4EF` | L_E4EF | decoded | `00E4DA` BBS |
| `00E4F9` | L_E4F9 | decoded | `00E4E7` BCC |
| `00E4FF` | L_E4FF | decoded | `00E439` JMP<br>`00E4D4` BCC<br>`00E4F7` BRA |
| `00E504` | L_E504 | decoded | `00E3DD` JSL |
| `00E512` | L_E512 | decoded | `00E518` BNE |
| `00E51A` | L_E51A | decoded | `00E510` BEQ |
| `00E51F` | L_E51F | decoded | `00E3FE` JSL |
| `00E532` | L_E532 | decoded | `00E51F` BBS |
| `00E53E` | L_E53E | decoded | `00E539` BCS |
| `00E54C` | L_E54C | decoded | `00E530` BRA<br>`00E542` BNE |
| `00E5A8` | L_E5A8 | decoded | `00E59E` BBS |
| `00E5B2` | L_E5B2 | decoded | `00E5A8` BBS |
| `00E5C3` | L_E5C3 | decoded | `00E54F` BCS<br>`00E551` BBS<br>`00E55C` BCC<br>`00E564` BCC<br>`00E569` BCS<br>`00E571` BCC<br>`00E576` BCS<br>`00E578` BBC<br>`00E57D` BBS<br>`00E587` BCS<br>`00E58D` BCS<br>`00E594` BCS<br>`00E59C` BCC<br>`00E5A3` BBC<br>`00E5AD` BBC<br>`00E5B2` BBS<br>`00E5B7` BBS<br>`00E5BC` BBS<br>`00E5DE` BRA<br>`00E601` BRA<br>`00E611` BRA<br>`00E62D` BRA<br>`00E63E` BRA<br>`00E654` JMP<br>`00E667` JMP |
| `00E5C5` | L_E5C5 | decoded | `00E5C1` BRA |
| `00E5DA` | L_E5DA | decoded | `00E5CA` BBS<br>`00E5CF` BBS |
| `00E5E0` | L_E5E0 | decoded | `00E5C5` BBS |
| `00E5F9` | L_E5F9 | decoded | `00E5E5` BBS<br>`00E5EA` BBC |
| `00E603` | L_E603 | decoded | `00E5E0` BBS |
| `00E60D` | L_E60D | decoded | `00E603` BBC |
| `00E613` | L_E613 | decoded | `00E608` BBS |
| `00E619` | L_E619 | decoded | `00E5D8` BRA<br>`00E5F7` BRA<br>`00E617` BRA |
| `00E629` | L_E629 | decoded | `00E61E` BBS |
| `00E62F` | L_E62F | decoded | `00E619` BBS |
| `00E63A` | L_E63A | decoded | `00E62F` BBC |
| `00E640` | L_E640 | decoded | `00E627` BRA<br>`00E638` BRA |
| `00E650` | L_E650 | decoded | `00E645` BBS |
| `00E658` | L_E658 | decoded | `00E640` BBS |
| `00E663` | L_E663 | decoded | `00E658` BBC |
| `00E66B` | L_E66B | decoded | `00E64E` BRA<br>`00E661` BRA |
| `00E66D` | L_E66D | decoded | `00E409` JSL |
| `00E677` | L_E677 | decoded | `00E673` BCS |
| `00E679` | L_E679 | decoded | `00E589` JSL |
| `00E680` | L_E680 | decoded | `00E679` BBC |
| `00E691` | L_E691 | decoded | `00E68A` BBC |
| `00E6A7` | L_E6A7 | decoded | `00E6A0` BBC |
| `00E6B3` | L_E6B3 | decoded | `00E67E` BRA<br>`00E680` BBS<br>`00E685` BBS<br>`00E68F` BRA<br>`00E691` BBS<br>`00E696` BBS<br>`00E69B` BBS<br>`00E6A5` BRA<br>`00E6A7` BBS<br>`00E6AC` BBS |
| `00E6B5` | L_E6B5 | decoded | `00E4CA` JSL |
| `00E6C6` | L_E6C6 | decoded | `00E6BE` BEQ<br>`00E6C0` BCC |
| `00E6D2` | L_E6D2 | decoded | `00E6CA` BEQ<br>`00E6CC` BCC |
| `00E6EC` | L_E6EC | decoded | `00E6E4` BEQ<br>`00E6E6` BCC |
| `00E6F9` | L_E6F9 | decoded | `00E6C4` BRA |
| `00E708` | L_E708 | decoded | `00E6D0` BRA<br>`00E6EA` BRA |
| `00E71B` | L_E71B | decoded | `00E701` BCC<br>`00E706` BRA<br>`00E716` BCS |
| `00E720` | L_E720 | decoded | `00E6F3` BEQ<br>`00E6F5` BCC |
| `00E739` | L_E739 | decoded | `00E71E` BRA |
| `00E73C` | L_E73C | decoded | `00E735` BEQ<br>`00E737` BCC |
| `00E73D` | L_E73D | decoded | `00E73A` BRA |
| `00E73F` | L_E73F | decoded | `00E4CF` JSL |
| `00E754` | L_E754 | decoded | `00E74B` BCS |
| `00E766` | L_E766 | decoded | `00E750` BCC<br>`00E752` BEQ |
| `00E76B` | L_E76B | decoded | `00E75F` BCS<br>`00E764` BCS |
| `00E76D` | L_E76D | decoded | `00E4FF` JSL |
| `00E78F` | L_E78F | decoded | `00E798` BRA |
| `00E79A` | L_E79A | decoded | `00E795` BCS |
| `00E79D` | L_E79D | decoded | `00E792` BEQ |
| `00E7A1` | L_E7A1 | decoded | `00E76D` BBC |
| `00E7A2` | switched_sensor_sequence | decoded | `004E1E` JSL |
| `00E7D4` | L_E7D4 | decoded | `00E7B0` BBC |
| `00E7F8` | L_E7F8 | decoded | `00E7D4` BBC |
| `00E812` | L_E812 | decoded | `00E7AB` BBS<br>`00E7BB` BCC<br>`00E7C1` BCS<br>`00E7D2` BRA<br>`00E7DF` BCC<br>`00E7E5` BCS<br>`00E7F6` BRA<br>`00E7F8` BBC<br>`00E803` BCC<br>`00E809` BCS |
| `00E819` | L_E819 | decoded | `00E7BD` JSL<br>`00E7E1` JSL<br>`00E805` JSL |
| `00E835` | L_E835 | decoded | `00E830` BEQ |
| `00E847` | L_E847 | decoded | `00E833` BRA |
| `00E848` | L_E848 | decoded | `004E2A` JSL |
| `00E8AB` | L_E8AB | decoded | `00E858` BBS<br>`00E85D` BBC<br>`00E867` BCC<br>`00E869` BBS |
| `00E8B7` | L_E8B7 | decoded | `00E8AB` BBC<br>`00E8B0` BBS |
| `00E8BA` | L_E8BA | decoded | `00E8B5` BRA |
| `00E8CA` | L_E8CA | decoded | `00E8C0` BCC |
| `00E8CC` | L_E8CC | decoded | `00E8C4` BCC<br>`00E8C8` BRA |
| `00E8E2` | L_E8E2 | decoded | `00E8DC` BEQ<br>`00E8DE` BCC |
| `00E8FF` | L_E8FF | decoded | `00E8F5` BEQ<br>`00E8F7` BCC |
| `00E90A` | L_E90A | decoded | `00E906` BCS |
| `00E914` | L_E914 | decoded | `00E8B7` JMP |
| `00E915` | sio_irq_ack | decoded | `0044AE` JSL<br>`004538` JSL<br>`005437` JSL |
| `00E91B` | L_E91B | decoded | `004B98` JSL |
| `00E923` | L_E923 | decoded | `00E919` BRA<br>`00E91B` BBS |
| `00E93B` | L_E93B | decoded | `00E915` BBC<br>`00E91F` BBC<br>`00E925` BBS<br>`00E929` BBC |
| `00E93C` | L_E93C | decoded | `005845` JSL<br>`00588A` JSL |
| `00E949` | L_E949 | decoded | `00E944` BCS |
| `00E95E` | L_E95E | decoded | `00E95A` BEQ |
| `00EA77` | interp16 | decoded | `003D32` JSL<br>`003D43` JSL<br>`0041B1` JSL<br>`00427F` JSL<br>`0042EA` JSL<br>`0056B0` JSL<br>`0056C1` JSL<br>`0056CE` JSL<br>`0056E0` JSL<br>`00576C` JSL<br>`005ADA` JSL<br>`006876` JSL<br>`006888` JSL<br>`006B53` JSL<br>`006F2C` JSL<br>`007877` JSL<br>`007C4C` JSL<br>`0086CF` JSL<br>`00A5E3` JSL<br>`00AC14` JSL<br>`00AC7F` JSL<br>`00AD6B` JSL<br>`00AE43` JSL<br>`00B260` JSL<br>`00B5C8` JSL<br>`00B5E2` JSL<br>`00B5FD` JSL<br>`00B8A8` JSL<br>`00B9BD` JSL<br>`00BE7E` JSL<br>`00FABA` JSL<br>`00FBBE` JSL |
| `00EA7D` | L_EA7D | decoded | `00EA79` BCC |
| `00EA82` | interp32 | decoded | `00ADE5` JSL<br>`00B048` JSL<br>`00C03E` JSL<br>`00E84E` JSL |
| `00EA88` | L_EA88 | decoded | `00EA84` BCC |
| `00EA8D` | interp8 | decoded | `004073` JSL<br>`00569A` JSL<br>`005A1E` JSL<br>`005A30` JSL<br>`0067C5` JSL<br>`0067DA` JSL<br>`0068D4` JSL<br>`008564` JSL<br>`008598` JSL<br>`0086A3` JSL<br>`0093C0` JSL<br>`00940A` JSL<br>`009480` JSL<br>`00AAEF` JSL<br>`00AB0F` JSL<br>`00E8E5` JSL |
| `00EA93` | L_EA93 | decoded | `00EA8F` BCC |
| `00EA99` | L_EA99 | decoded | `00EA80` BRA |
| `00EA9C` | L_EA9C | decoded | `00EA8B` BRA |
| `00EADB` | L_EADB | decoded | `00EAC1` BCS |
| `00EAEB` | L_EAEB | decoded | `00EAB8` BEQ<br>`00EABF` BEQ |
| `00EAEE` | L_EAEE | decoded | `00FAD1` JSL |
| `00EAF4` | L_EAF4 | decoded | `00EAF0` BCC |
| `00EB10` | L_EB10 | decoded | `00EAF7` BRA |
| `00EB63` | L_EB63 | decoded | `00EB46` BCS |
| `00EB76` | L_EB76 | decoded | `00EB2F` BEQ<br>`00EB44` BEQ |
| `00EB7C` | L_EB7C | decoded | `005542` JSL |
| `00EB87` | L_EB87 | decoded | `00EB97` BRA<br>`00EBA4` BRA |
| `00EB8C` | L_EB8C | decoded | `005954` JSL<br>`00F87E` JSL<br>`00F9BB` JSL |
| `00EB99` | L_EB99 | decoded | `008E02` JSL<br>`00A244` JSL<br>`00B20D` JSL<br>`00DD48` JSL |
| `00EBA6` | L_EBA6 | decoded | `00EBA0` BCC |
| `00EBA9` | L_EBA9 | decoded | `00EB93` BCC |
| `00EBB2` | L_EBB2 | decoded | `00EB83` BCC |
| `00EBE6` | L_EBE6 | decoded | `00EBDA` BCC |
| `00F19E` | read_tps | decoded | `004036` JSL<br>`004C9E` JSL |
| `00F1BF` | L_F1BF | decoded | `00F1B0` BBC<br>`00F1B5` BBC |
| `00F1DA` | L_F1DA | decoded | `00F1CB` BBC<br>`00F1D0` BBC |
| `00F1DE` | read_battery | decoded | `004050` JSL |
| `00F266` | L_F266 | decoded | `00F25B` BBC |
| `00F26A` | L_F26A | decoded | `00F264` BRA |
| `00F287` | L_F287 | decoded | `00F277` BNE |
| `00F28A` | L_F28A | decoded | `00F285` BRA |
| `00F29B` | L_F29B | decoded | `00F291` BCC |
| `00F29F` | L_F29F | decoded | `00F295` BCC<br>`00F297` BEQ |
| `00F2B0` | L_F2B0 | decoded | `00F2AC` BCC |
| `00F2C0` | L_F2C0 | decoded | `00F299` BRA<br>`00F29D` BCC<br>`00F2AE` BNE<br>`00F2B8` BCC |
| `00F2C4` | L_F2C4 | decoded | `00F2BE` BRA |
| `00F2FA` | L_F2FA | decoded | `00F2C4` BBC |
| `00F305` | L_F305 | decoded | `00F2C9` BBS<br>`00F2E6` BCC |
| `00F306` | adc_read | decoded | `004013` JSL<br>`00401C` JSL<br>`004025` JSL<br>`00403C` JSL<br>`00E7A4` JSL<br>`00F1A0` JSL<br>`00F1AC` JSL<br>`00F1C7` JSL<br>`00F1E1` JSL<br>`00F20E` JSL<br>`00F23B` JSL<br>`00F473` JSL<br>`00F701` JSL |
| `00F30B` | L_F30B | decoded | `00F30B` BBC |
| `00F318` | L_F318 | decoded | `00F1FD` JSL<br>`00F22A` JSL<br>`00F257` JSL |
| `00F329` | L_F329 | decoded | `00F324` BCS |
| `00F33B` | L_F33B | decoded | `00F332` BMI |
| `00F340` | L_F340 | decoded | `00F32C` BCS |
| `00F356` | L_F356 | decoded | `00F31B` BEQ<br>`00F344` BPL<br>`00F34B` BCS |
| `00F359` | L_F359 | decoded | `00F339` BCC<br>`00F33E` BRA |
| `00F468` | diag_task_f468 | decoded | `004E2E` JSL |
| `00F471` | L_F471 | decoded | `00F468` BBC |
| `00F4CD` | L_F4CD | decoded | `00F4C8` BEQ |
| `00F4D0` | L_F4D0 | decoded | `00F4C0` BBC |
| `00F4E7` | L_F4E7 | decoded | `00F4DF` BCC |
| `00F50D` | L_F50D | decoded | `00F4E5` BRA<br>`00F4ED` BCC<br>`00F4F5` BCS<br>`00F4FD` BCC<br>`00F504` BCC |
| `00F517` | L_F517 | decoded | `00F512` BCS |
| `00F51E` | L_F51E | decoded | `00F4D0` BBS |
| `00F557` | L_F557 | decoded | `00F539` BCC |
| `00F55E` | L_F55E | decoded | `00F4CA` JMP<br>`00F555` BCS |
| `00F571` | L_F571 | decoded | `00F50A` JMP<br>`00F557` BBS<br>`00F55E` BBS |
| `00F589` | L_F589 | decoded | `00F4CD` JMP<br>`00F531` BCS |
| `00F58D` | L_F58D | decoded | `00F51B` JMP<br>`00F525` BEQ<br>`00F529` BEQ<br>`00F53B` BBS<br>`00F546` BCS<br>`00F54D` BCC<br>`00F587` BRA |
| `00F59C` | L_F59C | decoded | `00F55C` BRA<br>`00F58D` BBC |
| `00F5B2` | L_F5B2 | decoded | `00F514` JMP<br>`00F56F` BRA<br>`00F577` BCC<br>`00F59A` BRA<br>`00F5A2` BCC |
| `00F5C4` | L_F5C4 | decoded | `00F5BF` BCS |
| `00F5C8` | L_F5C8 | decoded | `00F5B2` BBC |
| `00F5E2` | L_F5E2 | decoded | `00F5DC` BCS |
| `00F5F7` | L_F5F7 | decoded | `00F5C8` BBC<br>`00F5CD` BBC<br>`00F5D2` BBS<br>`00F5E0` BCS |
| `00F5FB` | L_F5FB | decoded | `00F5E7` BCC |
| `00F620` | L_F620 | decoded | `00F619` BBC |
| `00F625` | L_F625 | decoded | `00F5FB` BBC<br>`00F600` BBC<br>`00F605` BBS<br>`00F60A` BBS<br>`00F60F` BBS<br>`00F614` BBC<br>`00F61E` BRA |
| `00F62F` | L_F62F | decoded | `00F620` BBS |
| `00F63D` | L_F63D | decoded | `00F635` BCS |
| `00F647` | L_F647 | decoded | `00F63B` BRA |
| `00F655` | L_F655 | decoded | `00F64D` BCC |
| `00F65F` | L_F65F | decoded | `00F653` BRA |
| `00F676` | L_F676 | decoded | `00F62D` BRA<br>`00F65F` BBC |
| `00F677` | L_F677 | decoded | `00F643` JSL<br>`00F65B` JSL |
| `00F698` | L_F698 | decoded | `00F67C` BCC<br>`00F680` BCS<br>`00F687` BCC<br>`00F68B` BCS |
| `00F69D` | L_F69D | decoded | `00F692` BCC |
| `00F69E` | L_F69E | decoded | `00F4BC` JSL<br>`00F735` JSL |
| `00F6AB` | L_F6AB | decoded | `00F69E` BBC |
| `00F6FD` | L_F6FD | decoded | `00F6A9` BRA<br>`00F6AB` BBS<br>`00F6B6` BCC<br>`00F6BD` BCC<br>`00F6C1` BCS |
| `00F6FF` | L_F6FF | decoded | `00F46D` JMP |
| `00F749` | L_F749 | decoded | `00F73E` BCC<br>`00F743` BNE |
| `00F761` | L_F761 | decoded | `00F750` JSL |
| `00F798` | L_F798 | decoded | `00F75C` JSL |
| `00F7B6` | L_F7B6 | decoded | `00F7AD` BCS<br>`00F7B2` BCC |
| `00F7CB` | L_F7CB | decoded | `00F79D` BBC<br>`00F7A2` BBS<br>`00F7B4` BRA |
| `00F7CF` | L_F7CF | decoded | `00F798` BBC<br>`00F7BB` BCC |
| `00F816` | L_F816 | decoded | `00F80F` BBC |
| `00F826` | L_F826 | decoded | `00F7D4` BBC<br>`00F7D9` BBC<br>`00F7DE` BBS<br>`00F7E9` BCC<br>`00F7EE` BCS<br>`00F7F6` BCC<br>`00F7FE` BCC<br>`00F800` BBS<br>`00F805` BBS<br>`00F80A` BBS<br>`00F814` BRA<br>`00F81C` BCS |
| `00F82D` | L_F82D | decoded | `00F824` BCC |
| `00F835` | L_F835 | decoded | `00F7CF` BBC<br>`00F82B` BRA |
| `00F83E` | L_F83E | decoded | `00F833` BCS |
| `00F871` | L_F871 | decoded | `00F862` BEQ |
| `00F872` | L_F872 | decoded | `00F86F` BCC |
| `00F898` | L_F898 | decoded | `00F894` BCC |
| `00F89C` | L_F89C | decoded | `00F896` BNE |
| `00F8E6` | L_F8E6 | decoded | `00F8DF` BCS |
| `00F8E9` | L_F8E9 | decoded | `00F8E4` BCC |
| `00F8EA` | L_F8EA | decoded | `00F89A` BRA |
| `00F951` | L_F951 | decoded | `00F94A` BCS |
| `00F958` | L_F958 | decoded | `00F94F` BRA |
| `00F973` | L_F973 | decoded | `00F962` BCC |
| `00F980` | L_F980 | decoded | `00F968` BCC<br>`00F96D` BEQ<br>`00F96F` BCC<br>`00F977` BCS |
| `00F987` | L_F987 | decoded | `00F971` BRA<br>`00F97C` BEQ<br>`00F97E` BCC |
| `00F99D` | L_F99D | decoded | `00F83A` JMP<br>`00F985` BRA<br>`00F98D` BCC |
| `00F99E` | L_F99E | decoded | `005902` JSL<br>`00F845` JSL |
| `00F9AD` | L_F9AD | decoded | `0058F6` JSL<br>`00F9A8` BCS |
| `00F9B8` | L_F9B8 | decoded | `00F9B5` BEQ |
| `00F9C0` | L_F9C0 | decoded | `005909` JSL<br>`00F852` JSL |
| `00F9DD` | L_F9DD | decoded | `00F9CA` BBC<br>`00F9D0` BBC |
| `00F9F3` | L_F9F3 | decoded | `00F9DD` BBC |
| `00F9FF` | L_F9FF | decoded | `00F9F1` BCS |
| `00FA00` | L_FA00 | decoded | `00F9C4` BCS<br>`00F9FB` BCS |
| `00FA01` | L_FA01 | decoded | `00F9FD` BRA |
| `00FA02` | L_FA02 | decoded | `00F723` JSL<br>`00F8FF` JSL |
| `00FA13` | L_FA13 | decoded | `00FA0E` BCS |
| `00FA25` | L_FA25 | decoded | `00FA1C` BMI |
| `00FA2A` | L_FA2A | decoded | `00FA16` BCS |
| `00FA3D` | L_FA3D | decoded | `00FA05` BEQ<br>`00FA2E` BPL<br>`00FA35` BCS |
| `00FA40` | L_FA40 | decoded | `00FA23` BCC<br>`00FA28` BRA |
| `00FA43` | L_FA43 | decoded | `00FA3B` BRA |
| `00FA44` | L_FA44 | decoded | `00F758` JSL |
| `00FA4D` | L_FA4D | decoded | `00FA44` BBS |
| `00FA58` | L_FA58 | decoded | `00FA53` BCS |
| `00FA88` | L_FA88 | decoded | `00FA83` BCC |
| `00FA9E` | L_FA9E | decoded | `00FA99` BCC |
| `00FAA9` | L_FAA9 | decoded | `00FA62` BEQ |
| `00FAAC` | L_FAAC | decoded | `00FAA7` BCC |
| `00FAF3` | L_FAF3 | decoded | `00FAE6` BMI |
| `00FAFC` | L_FAFC | decoded | `00FAEC` BCC<br>`00FAF1` BRA<br>`00FAF7` BCS |
| `00FB07` | L_FB07 | decoded | `00FB03` BMI |
| `00FB09` | L_FB09 | decoded | `00FB05` BRA |
| `00FB21` | L_FB21 | decoded | `00FB1C` BCS |
| `00FB34` | L_FB34 | decoded | `00FB2B` BBC |
| `00FB3D` | L_FB3D | decoded | `00FB34` BBC |
| `00FB58` | L_FB58 | decoded | `00FB51` BBC |
| `00FB5F` | L_FB5F | decoded | `00FB58` BBC |
| `00FB76` | L_FB76 | decoded | `00FB6F` BBC |
| `00FBB0` | L_FBB0 | decoded | `00FA49` JMP<br>`00FB30` JMP<br>`00FB39` JMP<br>`00FB3D` BBS<br>`00FB42` BBS<br>`00FB47` BBS<br>`00FB4C` BBS<br>`00FB56` BRA<br>`00FB5D` BRA<br>`00FB65` BCS<br>`00FB6D` BCS<br>`00FB74` BRA<br>`00FB7C` BCC<br>`00FB92` BCS<br>`00FBA8` BCS |
| `00FBB8` | L_FBB8 | decoded | `00FBAE` BRA |
| `00FBF5` | L_FBF5 | decoded | `00FBE8` BCS |
| `00FBFA` | L_FBFA | decoded | `00FBF3` BRA |
| `00FC07` | L_FC07 | decoded | `00FC02` BCC |
| `00FC2A` | L_FC2A | decoded | `00FC1D` BNE |
| `00FC38` | L_FC38 | decoded | `00FC0B` BEQ<br>`00FC0D` BCC |
| `00FC3C` | L_FC3C | decoded | `00FC23` BCC<br>`00FC28` BRA<br>`00FC31` BCS<br>`00FC36` BRA |
| `00FC48` | L_FC48 | decoded | `00FBB4` JMP<br>`00FBCE` BCC |
| `00FC4A` | L_FC4A | decoded | `00FBDE` BCC |
| `00FC50` | L_FC50 | decoded | `00FBD5` BNE<br>`00FC46` BRA |
| `010000` |  | outside_image | `004472` JMP |
| `0100C0` |  | outside_image | `004069` JSL |
| `0101D0` |  | outside_image | `0040CC` JSL |
| `010801` |  | outside_image | `0041FF` JSL |
| `011019` |  | outside_image | `004143` JSL |
| `01310C` |  | outside_image | `0043AB` JSL |
| `01427A` |  | outside_image | `003FEE` JSL<br>`003FF7` JSL |
| `01428D` |  | outside_image | `003FE3` JSL |
| `015803` |  | outside_image | `003FFE` JSL |
| `0158EE` |  | outside_image | `00CD99` JSL |
| `015AD1` |  | outside_image | `008A85` JSL<br>`008A92` JSL |
| `016C84` |  | outside_image | `008891` JSL |
| `016D34` |  | outside_image | `008F97` JSL |
| `016E7E` |  | outside_image | `008942` JSL |
| `016F0E` |  | outside_image | `008EBF` JSL |
| `016F18` |  | outside_image | `004C96` JSL |
| `016FA7` |  | outside_image | `004CEE` JSL |
| `017005` |  | outside_image | `004CF2` JSL |
| `0170B5` |  | outside_image | `007464` JSL |
| `017272` |  | outside_image | `004C2A` JSL |
| `017311` |  | outside_image | `00DF86` JSL |
| `01732D` |  | outside_image | `00DF21` JSL |
| `0173B2` |  | outside_image | `004C17` JSL<br>`00DF25` JSL<br>`00DF8A` JSL |
| `0176AB` |  | outside_image | `006C2B` JSL |
| `017989` |  | outside_image | `004D52` JSL |
| `017A14` |  | outside_image | `004D20` JSL |
| `017A6B` |  | outside_image | `0074A9` JSL |
| `017ABC` |  | outside_image | `003E10` JSL |
| `017B08` |  | outside_image | `004EFF` JMP |
| `017B91` |  | outside_image | `004DDD` JSL |
