import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'v02'))
import grade_acceptance as G
G.TASKS = json.loads((Path(__file__).parent / 'prompts.json').read_text())['acceptance']
src, dst = Path(sys.argv[1]), Path(sys.argv[2]); dst.mkdir(parents=True, exist_ok=True)
import concurrent.futures as cf
files = [f for f in sorted(src.glob('AC*.json')) if not (dst / f.name).exists()]
with cf.ThreadPoolExecutor(5) as pool:
    for name, result in pool.map(G.grade, files):
        print(name, 'ok' if result else 'FAILED', flush=True)
        if result: (dst / f'{name}.json').write_text(json.dumps(result, ensure_ascii=False, indent=1))
