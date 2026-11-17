#!/usr/bin/env python3
"""Compare fuel interpolation hypotheses without claiming firmware equivalence."""
exec(open('tools/analyze_fuel_trace.py').read().split('for addr in [')[0])
import math,json
samples=[(i,d) for i,d in enumerate(a) if d['base_0ac7_raw']>16384]
results=[]
for loadwhole in [False,True]:
 for order in ['bilinear','rows-first','columns-first']:
  for rounding in ['floor','nearest','ceil']:
   for delay in [-1,0,1]:
    errors=[];stable=[]
    for i,d in samples:
     q=a[max(0,min(len(a)-1,i+delay))];addr=0x1800 if d['mode_0dcf_raw']==0 else 0x1700
     r=q['rpm_index_raw'];c=math.floor(q['calculated_load']) if loadwhole else q['calculated_load']
     ri,rf=interval(get(0x1910,16),r);ci,cf=interval(get(0x1900,16),c);t=get(addr,256)
     v00=t[ri*16+ci];v10=t[(ri+1)*16+ci];v01=t[ri*16+ci+1];v11=t[(ri+1)*16+ci+1]
     rnd=math.floor if rounding=='floor' else math.ceil if rounding=='ceil' else lambda x:math.floor(x+0.5)
     if order=='bilinear':pred=rnd(v00*(1-rf)*(1-cf)+v10*rf*(1-cf)+v01*(1-rf)*cf+v11*rf*cf)
     elif order=='rows-first':pred=rnd(rnd(v00*(1-rf)+v10*rf)*(1-cf)+rnd(v01*(1-rf)+v11*rf)*cf)
     else:pred=rnd(rnd(v00*(1-cf)+v01*cf)*(1-rf)+rnd(v10*(1-cf)+v11*cf)*rf)
     err=pred-d['base_0ac7_raw']/128;errors.append(err)
     if i>0 and i+1<len(a) and abs(a[i-1]['calculated_load']-d['calculated_load'])<1 and abs(a[i+1]['calculated_load']-d['calculated_load'])<1 and a[i-1]['rpm_index_raw']==d['rpm_index_raw']==a[i+1]['rpm_index_raw']:stable.append(err)
    results.append(dict(load_whole_byte=loadwhole,order=order,rounding=rounding,delay_frames=delay,mae=statistics.mean(abs(x) for x in errors),exact=sum(x==0 for x in errors)/len(errors),n=len(errors),stable_n=len(stable),stable_exact=sum(x==0 for x in stable)/len(stable) if stable else None))
results.sort(key=lambda d:-d['exact'])
print(json.dumps(results[:8],indent=2))
Path('docs/rom-baseline/fuel-rounding-candidates.json').write_text(json.dumps(results,indent=2)+'\n')
