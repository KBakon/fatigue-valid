"""Hash existing project files, excluding only this new WP directory and git internals."""
from pathlib import Path
import hashlib,json,sys
root=Path(__file__).resolve().parents[2]
out=root/'wp04_source_alignment/verification/existing_files_before.json'
def snapshot():
    return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file() and 'wp04_source_alignment' not in p.relative_to(root).parts and '.git' not in p.relative_to(root).parts}
current=snapshot()
if '--check' in sys.argv:
    old=json.loads(out.read_text()); changes=[k for k in old.keys()|current.keys() if old.get(k)!=current.get(k)]
    result={'existing_files':len(old),'changed_added_deleted_outside_wp04':changes,'status':'PASS' if not changes else 'FAIL','git_diff_limitation':'Project root has no .git; full file SHA-256 snapshot used instead.'}
    (out.parent/'existing_files_check.json').write_text(json.dumps(result,indent=2)+'\n'); print(result)
    assert not changes
else:
    assert not out.exists();out.write_text(json.dumps(current,indent=2)+'\n'); print({'snapshotted':len(current)})
