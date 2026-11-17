#!/usr/bin/env python3
"""Compare fuel-table hypotheses with the November 17 fuel trace; run from repo root."""
import csv,statistics
from pathlib import Path
from bisect import bisect_right
b=Path('rom/23710-2L904_1000-FFFF.bin').read_bytes();get=lambda a,n:list(b[a-0x1000:a-0x1000+n])
a=[{k:float(v) for k,v in d.items() if k!='raw_hex'} for d in csv.DictReader(open('logs/2026-11-17_135145_304875_fuel-trace.csv'))]
def interval(axis,x):
 i=max(0,min(14,bisect_right(axis,x)-1));return i,max(0,min(1,(x-axis[i])/(axis[i+1]-axis[i])))
def lookup(addr,r,c,transpose=False):
 i,fi=interval(get(0x1910,16),r);j,fj=interval(get(0x1900,16),c);t=get(addr,256)
 def v(i,j):return t[j*16+i] if transpose else t[i*16+j]
 return (v(i,j)*(1-fi)*(1-fj)+v(i+1,j)*fi*(1-fj)+v(i,j+1)*(1-fi)*fj+v(i+1,j+1)*fi*fj)*128
for addr in [0x1700,0x1800]:
 for coord in ['load','atps','last']:
  errors=[]
  for d in a:
   c=d['calculated_load'] if coord=='load' else d['adjusted_tps_raw'] if coord=='atps' else 128
   pred=lookup(addr,d['rpm_index_raw'],c)
   errors.append(pred-d['base_0ac7_raw'])
  print(hex(addr),coord,'MAE',statistics.mean(abs(e) for e in errors),'within128',sum(abs(e)<=128 for e in errors)/len(errors))
print('enriched',sum(d['base_0ac7_raw']>16384 for d in a),'fullthrottle',sum(d['tps_mv']>=4000 for d in a))
s=[d for d in a if d['base_0ac7_raw']>16384]
for addr in [0x1700,0x1800]:
 for coord in ['load','atps','last']:
  errors=[lookup(addr,d['rpm_index_raw'],d['calculated_load'] if coord=='load' else d['adjusted_tps_raw'] if coord=='atps' else 128)-d['base_0ac7_raw'] for d in s]
  print('ENRICH',hex(addr),coord,'MAE',statistics.mean(abs(e) for e in errors),'within128',sum(abs(e)<=128 for e in errors)/len(errors))
print('composite equals base',sum(d['composite_0a56_raw']==d['base_0ac7_raw'] for d in a),len(a))
for d in sorted(s,key=lambda d:d['base_0ac7_raw'],reverse=True)[:1]:print('max',d)
