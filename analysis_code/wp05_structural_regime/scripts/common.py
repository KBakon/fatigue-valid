"""File/provenance utilities; no scientific analysis or input reads on import."""
from pathlib import Path
import csv,hashlib,importlib.util,json,sys
ROOT=Path(__file__).resolve().parents[2]
WP=ROOT/'wp05_structural_regime'
KEYS=('participant_id','task','segment_j','segment_j_plus_1')
def digest(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def read(p):
    with Path(p).open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
def write(p,rows,fields=None):
    with Path(p).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields or list(rows[0]));w.writeheader();w.writerows(rows)
def save(p,data):Path(p).write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
def load_script(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/f'{name}.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def key(r):return tuple(r[k] for k in KEYS)
def output():
    p=Path(sys.argv[1]) if len(sys.argv)>1 else WP
    p.mkdir(parents=True,exist_ok=True);(p/'verification').mkdir(exist_ok=True);(p/'figures').mkdir(exist_ok=True);return p
