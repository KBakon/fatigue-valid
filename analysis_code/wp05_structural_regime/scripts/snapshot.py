"""Preserve every existing non-Git project file, including all WP-04 outputs."""
from common import *
def current():
    return {p.relative_to(ROOT).as_posix():digest(p) for p in sorted(ROOT.rglob('*')) if p.is_file() and 'wp05_structural_regime' not in p.relative_to(ROOT).parts and '.git' not in p.relative_to(ROOT).parts}
out=WP/'verification/existing_files_before.json';now=current()
if '--check' in sys.argv:
    old=json.loads(out.read_text());changed=sorted(k for k in old.keys()|now.keys() if old.get(k)!=now.get(k))
    record=dict(status='PASS' if not changed else 'FAIL',existing_files=len(old),changed_added_deleted_outside_wp05=changed,root_git_diff='Unavailable: root .git absent. Full SHA-256 comparison used. Nested Git metadata left untouched.')
    save(WP/'verification/existing_files_check.json',record);print(json.dumps(record,indent=2));assert not changed
else:
    assert not out.exists();save(out,now);print('Existing-file snapshot:',len(now))
