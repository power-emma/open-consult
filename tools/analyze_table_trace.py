#!/usr/bin/env python3
"""Compare explicit timing hypotheses against table-trace CSVs; run from repo root.

Produces hypothesis scores, not a definitive firmware decoder.
"""
import csv,json,statistics
from pathlib import Path
from bisect import bisect_right
b=Path('rom/23710-2L904_1000-FFFF.bin').read_bytes()
get=lambda a,n:b[a-0x1000:a-0x1000+n]
a=[]
for p in sorted(Path('logs').glob('*table-trace.csv')):
 for d in csv.DictReader(p.open()):a.append({k:float(v) for k,v in d.items() if k!='raw_hex'})
signed=lambda x:x if x<128 else x-256
print('frames',len(a))
for k in [0,252]:
 s=[d for d in a if d['knock_term_raw']==k];e=[d['timing_btdc']-d['timing_base_signed_candidate']-signed(k) for d in s]
 print('knock',k,'n',len(s),'exact',sum(x==0 for x in e)/len(e),'within1',sum(abs(x)<=1 for x in e)/len(e),'median',statistics.median(e))
def interp(axis,x):
 i=max(0,min(len(axis)-2,bisect_right(axis,x)-1));return i,max(0,min(1,(x-axis[i])/(axis[i+1]-axis[i])))
def lookup(table,r,c,swap,conv):
 i,fi=interp(list(get(0x1f00,16)),r);j,fj=interp(list(get(0x1f10,16)),c)
 def cell(i,j):return conv(table[j*16+i] if swap else table[i*16+j])
 return cell(i,j)*(1-fi)*(1-fj)+cell(i+1,j)*fi*(1-fj)+cell(i,j+1)*(1-fi)*fj+cell(i+1,j+1)*fi*fj
# Exclude closed throttle/idle and compare separately; none of these are proven models.
s=[d for d in a if d['tps_mv']>=700 and d['rpm']>=1500]
results=[]
for addr in [0x1d00,0x1e00]:
 for swap in [False,True]:
  for name,conv in [('signed',signed),('low7',lambda x:x&127),('raw',lambda x:x)]:
   for divisor in [128,256,512]:
    e=[lookup(get(addr,256),d['rpm_index_raw'],d['load_code']/divisor,swap,conv)-d['timing_base_signed_candidate'] for d in s]
    results.append(dict(address=hex(addr),transpose=swap,encoding=name,load_divisor=divisor,n=len(e),mae=statistics.mean(abs(x) for x in e),within2=sum(abs(x)<=2 for x in e)/len(e)))
print('best candidate models',json.dumps(sorted(results,key=lambda d:d['mae'])[:8],indent=2))
Path('docs/rom-baseline/trace-model-candidates.json').write_text(json.dumps({'frames':len(a),'note':'Hypothesis comparison only; best fit does not establish ECU semantics.','models':sorted(results,key=lambda d:d['mae'])},indent=2)+'\n')
