"""Write-once kinematic projection and feature freeze. No downstream imports."""
from pathlib import Path
import csv, hashlib, json, sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'wp04_source_alignment'
DATA=ROOT/'data/wp01b_sources/MxD_Data_User_Study'
MAPPING={1:'right_upper_arm',2:'right_lower_arm',3:'left_upper_arm',4:'left_lower_arm',5:'chest'}
COLS=['Time']+[f'IMU_{i}_{a}_dps_' for i in MAPPING for a in ('gx','gy','gz')]
EPS=np.finfo(np.float64).tiny
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,rows,fields=None):
    with (OUT/name).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields or list(rows[0]));w.writeheader();w.writerows(rows)
def main():
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'verification').mkdir(exist_ok=True)
    target=OUT/'WP04_MECHANISM_FEATURES_FROZEN.csv'
    assert not target.exists(), 'Write-once freeze exists; use a separate clean-rerun directory'
    # Only mapping lines of the non-outcome dictionary are retained and checked.
    dictionary=ROOT/'artifacts/dataset_dictionary.md'
    mapping_lines=[s for s in dictionary.read_text(encoding='utf-8').splitlines() if s.startswith('| `IMU_')]
    for i,term in zip(MAPPING,('right upper arm','right lower arm','left upper arm','left lower arm','chest')):
        assert any(f'IMU_{i}_' in s and term in s for s in mapping_lines)
    paths=sorted(DATA.rglob('Rep[1-5]_*.csv'))
    assert paths
    inventory=[]; sources=[]; headers={}
    for p in paths:
        with p.open(encoding='utf-8-sig',newline='') as f: h=next(csv.reader(f))
        headers[p]=h
        sources.append({'source_file':p.relative_to(ROOT).as_posix(),'sha256':digest(p)})
        for col in COLS:
            i=int(col[4]) if col.startswith('IMU_') else 0
            inventory.append(dict(source_file=p.relative_to(ROOT).as_posix(),column=col,present=int(col in h),column_index=h.index(col) if col in h else '',location=MAPPING.get(i,'common_time'),unit='degrees/s' if i else 'milliseconds',mapping_authority='artifacts/dataset_dictionary.md:22-26' if i else 'artifacts/dataset_dictionary.md:12'))
    # Inventory is saved before any signal computation.
    write('WP04_SENSOR_COLUMN_INVENTORY.csv',inventory)
    rows=[];audit=[]
    for p in paths:
        task={'composite':'Composite','ziptie':'Harnessing'}[p.parents[1].name]
        base=dict(participant_id=p.parent.name[:4],task=task,segment_id=p.name.split('_')[0],source_file=p.relative_to(ROOT).as_posix())
        h=headers[p];reason='';n=0
        if not all(c in h for c in COLS):reason='MISSING_REQUIRED_CHANNEL'
        else:
            # Parser converts/returns ONLY the explicitly selected numeric fields.
            try: x=np.loadtxt(p,delimiter=',',skiprows=1,usecols=[h.index(c) for c in COLS],ndmin=2,encoding='utf-8-sig')
            except ValueError: reason='NONNUMERIC_REQUIRED_CHANNEL'
            if not reason:
                n=len(x)
                if n<2:reason='TOO_FEW_SAMPLES'
                elif not np.isfinite(x).all():reason='NONFINITE_REQUIRED_CHANNEL'
                elif not (np.diff(x[:,0])>0).all():reason='INVALID_COMMON_TIME'
        audit.append(base|dict(sample_rows=n,eligible=int(not reason),exclusion_reason=reason))
        if reason:continue
        mag=np.sqrt(np.sum(x[:,1:].reshape(n,5,3)**2,axis=2))
        m=np.sqrt(np.mean(mag**2,axis=0)); arm=float(np.mean(m[:4]));right=float(np.mean(m[:2]));left=float(np.mean(m[2:4]))
        sync=float(np.corrcoef(mag[:,0],mag[:,2])[0,1]) if np.std(mag[:,0])>0 and np.std(mag[:,2])>0 else ''
        rows.append(base|dict(sample_rows=n,**{f'M_{MAPPING[i]}':float(m[i-1]) for i in MAPPING},arm_mean=arm,arm_dominance=arm/(arm+float(m[4])+EPS),bilateral_asymmetry=abs(right-left)/(right+left+EPS),bilateral_synchrony=sync,zero_arm_torso_denominator=int(arm+m[4]==0),zero_bilateral_denominator=int(right+left==0)))
    assert rows
    write('WP04_MECHANISM_FEATURES_FROZEN.csv',rows)
    write('verification/stage1_source_files.csv',sources)
    write('verification/stage1_segment_eligibility.csv',audit)
    sha=digest(target)
    (OUT/'WP04_MECHANISM_FEATURES_FROZEN.sha256').write_text(sha+'  '+target.name+'\n')
    record=dict(status='PASS',source_files=len(paths),eligible_segments=len(rows),excluded_segments=len(paths)-len(rows),selected_columns=COLS,mapping=MAPPING,mapping_lines=mapping_lines,mapping_authority_sha256=digest(dictionary),script_sha256=digest(Path(__file__)),method_spec_sha256=digest(ROOT/'wp04_source_alignment/WP04_METHOD_SPEC.md'),feature_sha256=sha,epsilon=float(EPS),secondary_synchrony_constructible=True,synchrony_missing_segments=sum(r['bilateral_synchrony']=='' for r in rows),verification_statement='Stage 1 imported only pathlib/csv/hashlib/json/sys/numpy. It opened only active-segment source CSVs and the sensor dictionary; projected numerical access was limited to the explicit Time + 15 gyroscope allowlist. No outcome field was selected, converted, evaluated, or joined; no empirical-result or prediction file was opened. Mixed-container bytes were read by the parser/hash for projection/provenance only.',formulas='M=sqrt(mean(gx^2+gy^2+gz^2)); arm_dominance=mean(M1..M4)/(mean(M1..M4)+M5+epsilon); asymmetry=abs(mean(M1,M2)-mean(M3,M4))/(mean(M1,M2)+mean(M3,M4)+epsilon); synchrony=Pearson(magnitude1,magnitude3) at common Time, zero lag')
    (OUT/'verification/stage1_manifest.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({k:record[k] for k in ('status','source_files','eligible_segments','excluded_segments','feature_sha256','synchrony_missing_segments')},indent=2))
if __name__=='__main__':main()
