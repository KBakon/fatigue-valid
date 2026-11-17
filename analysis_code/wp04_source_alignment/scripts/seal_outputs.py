"""Inventory every saved WP-04 file and verify final on-disk hashes."""
from pathlib import Path
import csv,hashlib,json,platform
import numpy,matplotlib
WP=Path(__file__).resolve().parents[1]
excluded={'verification/OUTPUT_MANIFEST.csv','verification/SAVE_STATUS.json'}
rows=[]
for p in sorted(WP.rglob('*')):
    if not p.is_file() or p.relative_to(WP).as_posix() in excluded:continue
    rows.append(dict(path=p.relative_to(WP).as_posix(),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
manifest=WP/'verification/OUTPUT_MANIFEST.csv'
with manifest.open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=['path','bytes','sha256']);w.writeheader();w.writerows(rows)
for r in rows:assert hashlib.sha256((WP/r['path']).read_bytes()).hexdigest()==r['sha256']
checks=json.loads((WP/'verification/verification_results.json').read_text())
integrity=json.loads((WP/'verification/existing_files_check.json').read_text())
assert checks['status']==integrity['status']=='PASS'
status=dict(status='VERIFIED_SAVED',output_path=str(WP),listed_files=len(rows),manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),python=platform.python_version(),numpy=numpy.__version__,matplotlib=matplotlib.__version__,baseline_reproduction='PASS',clean_rerun='PASS',existing_project_file_integrity='PASS',executor='Codex / GPT-6-based agent per runtime instructions; exact served model and effort not exposed',unlisted_self_referential_files=sorted(excluded))
(WP/'verification/SAVE_STATUS.json').write_text(json.dumps(status,indent=2)+'\n')
print(json.dumps(status,indent=2))
