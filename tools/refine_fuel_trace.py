#!/usr/bin/env python3
"""Test mode-conditioned fuel table hypotheses; run from repository root."""
exec(open('tools/analyze_fuel_trace.py').read().split('for addr in [')[0])
from collections import Counter
print('base residues',Counter(int(d['base_0ac7_raw'])%128 for d in a).most_common(8))
for mode in sorted(set(d['mode_0dcf_raw'] for d in a)):
 s=[d for d in a if d['base_0ac7_raw']>16384 and d['mode_0dcf_raw']==mode]
 if not s:continue
 print('MODE',mode,'samples',len(s),'times',s[0]['seconds'],s[-1]['seconds'])
 for addr in [0x1700,0x1800]:
  e=[lookup(addr,d['rpm_index_raw'],d['calculated_load'])/128-d['base_0ac7_raw']/128 for d in s]
  print(hex(addr),'MAE',statistics.mean(abs(x) for x in e),'within1',sum(abs(x)<=1 for x in e)/len(e))
s=[(i,d) for i,d in enumerate(a) if d['base_0ac7_raw']>16384]
for offset in [-3,-2,-1,0,1,2,3]:
 e=[]
 for i,d in s:
  j=max(0,min(len(a)-1,i+offset));q=a[j];addr=0x1800 if d['mode_0dcf_raw']==0 else 0x1700
  e.append(lookup(addr,q['rpm_index_raw'],q['calculated_load'])/128-d['base_0ac7_raw']/128)
 print('offset',offset,'mae',statistics.mean(abs(x) for x in e))
print('worst rows')
for i,d in sorted(s,key=lambda q:abs(lookup(0x1800,q[1]['rpm_index_raw'],q[1]['calculated_load'])/128-q[1]['base_0ac7_raw']/128),reverse=True)[:5]:print({k:d[k] for k in ['seconds','rpm_index_rpm','calculated_load','tps_mv','mode_0dcf_raw','base_0ac7_raw']},'prediction',lookup(0x1800,d['rpm_index_raw'],d['calculated_load'])/128)
errors=[]
for i,d in s:
 addr=0x1800 if d['mode_0dcf_raw']==0 else 0x1700
 pred=lookup(addr,d['rpm_index_raw'],d['calculated_load'])/128
 errors.append(pred-d['base_0ac7_raw']/128)
print('MODE SELECTED','MAE',statistics.mean(abs(e) for e in errors),'within1',sum(abs(e)<=1 for e in errors)/len(errors),'n',len(errors))
print('integer coefficient matches floor',sum(int(lookup(0x1800 if d['mode_0dcf_raw']==0 else 0x1700,d['rpm_index_raw'],d['calculated_load'])/128)==d['base_0ac7_raw']/128 for i,d in s)/len(s))
