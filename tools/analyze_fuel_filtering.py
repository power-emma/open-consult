#!/usr/bin/env python3
"""Test explicit filtered-load hypotheses; scores do not establish firmware behavior."""
exec(open('tools/analyze_fuel_trace.py').read().split('for addr in [')[0])
import math,json
results=[]
for alpha in [0.125,0.25,0.5,0.75,1.0]:
    filtered=a[0]['calculated_load']
    groups={'early':[], 'late':[]}
    for d in a:
        filtered += alpha*(d['calculated_load']-filtered)
        if d['base_0ac7_raw']<=16384:
            continue
        addr=0x1800 if d['mode_0dcf_raw']==0 else 0x1700
        prediction=math.floor(lookup(addr,d['rpm_index_raw'],filtered)/128+.5)
        error=prediction-d['base_0ac7_raw']/128
        groups['early' if d['seconds']<300 else 'late'].append(error)
    record={'alpha':alpha}
    for name,errors in groups.items():
        record[name]={'n':len(errors),'mae':statistics.mean(abs(e) for e in errors),
                      'exact':sum(e==0 for e in errors)/len(errors)}
    results.append(record)
print(json.dumps(results,indent=2))
Path('docs/rom-baseline/fuel-filtering-candidates.json').write_text(json.dumps(results,indent=2)+'\n')
