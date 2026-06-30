import re
from pathlib import Path


def normalize_report(path: Path) -> str:
    lines = path.read_text(encoding='utf-8').splitlines()
    normalized = []
    for line in lines:
        if line.startswith('# 📄 PDF Scan Analytics Execution Report'):
            continue
        if line.startswith('* **Execution Performance:**'):
            continue
        if line.startswith('* **Total Storage Volume:**'):
            normalized.append('* **Total Storage Volume:** <normalized>')
            continue
        normalized.append(line)
    return "\n".join(normalized).strip() + "\n"


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print('Usage: normalize_report.py <report_path>')
        raise SystemExit(1)
    report_path = Path(sys.argv[1])
    print(normalize_report(report_path))
