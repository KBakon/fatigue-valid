"""Final recursive output manifest, on-disk hashes and verified save status."""
from common import *
import platform
import numpy,matplotlib
excluded={'verification/OUTPUT_MANIFEST.csv','verification/SAVE_STATUS.json'}
rows=[]
for p in sorted(WP.rglob('*')):
    if p.is_file() and p.relative_to(WP).as_posix() not in excluded:
        rows.append(dict(path=p.relative_to(WP).as_posix(),bytes=p.stat().st_size,sha256=digest(p)))
manifest=WP/'verification/OUTPUT_MANIFEST.csv';write(manifest,rows)
for r in rows:assert digest(WP/r['path'])==r['sha256']
checks=json.loads((WP/'verification/verification_results.json').read_text());integrity=json.loads((WP/'verification/existing_files_check.json').read_text())
assert checks['status']==integrity['status']=='PASS'
stage1=json.loads((WP/'verification/stage1_manifest.json').read_text())
assert digest(WP/'WP05_REGIME_TABLE_FROZEN.csv')==stage1['regime_sha256']
assert digest(WP/'WP05_METHOD_SPEC.md')==stage1['method_spec_sha256']
status=dict(status='VERIFIED_SAVED',output_path=str(WP),listed_files=len(rows),manifest_sha256=digest(manifest),python=platform.python_version(),numpy=numpy.__version__,matplotlib=matplotlib.__version__,executor='Codex, GPT-6-based agent per runtime instructions; exact served model and reasoning effort not exposed; no subagents',baseline_reproduction='PASS',clean_rerun='PASS',structural_access_audit='PASS',participant_block_bootstrap_audit='PASS',existing_project_file_integrity='PASS',existing_files_preserved=integrity['existing_files'],model_magnitude='NOT_TESTABLE: frozen observed-transition magnitudes absent',self_referential_unlisted_files=sorted(excluded))
save(WP/'verification/SAVE_STATUS.json',status);print(json.dumps(status,indent=2))
