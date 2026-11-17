from pathlib import Path
import hashlib
root=Path(__file__).resolve().parents[1]
lines=(root/"SHA256SUMS.txt").read_text(encoding="utf-8").splitlines()
for line in lines:
 digest,name=line.split("  ",1); path=root/name
 if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest: raise SystemExit("Mismatch: "+name)
print("PASS:",len(lines),"manifested files")
