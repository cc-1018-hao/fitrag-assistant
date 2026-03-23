from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(script_name: str) -> dict:
    python_exe = ROOT / ".venv" / "Scripts" / "python.exe"
    script_path = ROOT / "scripts" / script_name
    result = subprocess.run(
        [str(python_exe), str(script_path)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    payload = {
        "script": script_name,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }
    if result.returncode == 0:
        try:
            payload["json"] = json.loads(result.stdout)
        except Exception:  # noqa: BLE001
            payload["json"] = None
    return payload


def main() -> None:
    scripts = [
        "validate_index.py",
        "validate_point2.py",
        "validate_point3.py",
        "validate_point4.py",
        "validate_point5.py",
        "api_smoke_test.py",
    ]
    results = [_run(name) for name in scripts]

    checks = {}
    for item in results:
        key = item["script"]
        script_ok = item["returncode"] == 0
        parsed_ok = bool((item.get("json") or {}).get("passed", False))
        checks[key] = script_ok and parsed_ok

    output = {
        "passed": all(checks.values()),
        "checks": checks,
        "results": results,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.exit(main())
