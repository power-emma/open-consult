#!/usr/bin/env python3
"""Test whether missing low RPM bits explain fuel coefficient residuals."""
exec(open('tools/analyze_fuel_trace.py').read().split('for addr in [')[0])
import math,json
s=[d for d in a if d['base_0ac7_raw']>16384]
results=[]
for rpmoffset in [0,.25,.5,.75,1]:
 for loadoffset in [-.5,0,.5]:
  for rounding in ['floor','nearest','ceil']:
   errors=[];possible=0
   for d in s:
    addr=0x1800 if d['mode_0dcf_raw']==0 else 0x1700
    pred=lookup(addr,d['rpm_index_raw']+rpmoffset,d['calculated_load']+loadoffset)/128
    rnd=math.floor if rounding=='floor' else math.ceil if rounding=='ceil' else lambda x:math.floor(x+.5)
    errors.append(rnd(pred)-d['base_0ac7_raw']/128)
   results.append(dict(rpm_offset=rpmoffset,load_offset=loadoffset,rounding=rounding,exact=sum(e==0 for e in errors)/len(errors),mae=statistics.mean(abs(e) for e in errors)))
results.sort(key=lambda d:-d['exact']);print(json.dumps(results[:5],indent=2))
# Does any of the four possible true RPM values explain each sample?
for rounding in ['floor','nearest']:
 rnd=math.floor if rounding=='floor' else lambda x:math.floor(x+.5)
 n=0
 for d in s:
  addr=0x1800 if d['mode_0dcf_raw']==0 else 0x1700
  n+=any(rnd(lookup(addr,d['rpm_index_raw']+f,d['calculated_load'])/128)==d['base_0ac7_raw']/128 for f in [0,.25,.5,.75])
 print(rounding,'possible matches with lost RPM bits',n,len(s))
Path('docs/rom-baseline/fuel-precision-candidates.json').write_text(json.dumps(results,indent=2)+'\n')
