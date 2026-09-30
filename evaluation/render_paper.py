import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "evaluation/reports/latest.json"
OUT = ROOT / "docs/paper-filled.md"

text = (ROOT / "docs/paper.md").read_text(encoding="utf-8")
if not REPORT.exists():
    raise SystemExit("Run evaluation first: python evaluation/run_eval.py")
report = json.loads(REPORT.read_text(encoding="utf-8"))
rows = []
for language, scores in report["by_language"].items():
    rows.append(f"| {language} | {scores['faithfulness']:.3f} | {scores['answer_relevancy']:.3f} | {scores['context_precision']:.3f} | {scores['context_recall']:.3f} |")
text = text.replace("| Generated from evaluation | — | — | — | — |", "\n".join(rows))
OUT.write_text(text, encoding="utf-8")
print(OUT)
