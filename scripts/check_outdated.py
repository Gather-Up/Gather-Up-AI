import sys
import os
import re
import json
import urllib.request
from packaging import version

PYPI_URL = "https://pypi.org/pypi/{package}/json"

REQ_PATTERN = re.compile(r"^(?P<name>[A-Za-z0-9_.-]+)\s*(?P<spec>(==|>=|<=|~=|>|<).+)?\s*(#.*)?$")


def fetch_latest(package: str) -> str | None:
    url = PYPI_URL.format(package=package)
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("info", {}).get("version")
    except Exception:
        return None


def parse_requirements(path: str):
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = REQ_PATTERN.match(line)
            if not m:
                continue
            name = m.group("name")
            spec = (m.group("spec") or "").strip()
            current = None
            if spec.startswith("=="):
                current = spec[2:].strip()
            elif spec.startswith((">=","<=","~=",">","<")):
                # pinned version unknown; treat as current unknown
                current = None
            entries.append({"name": name, "spec": spec, "current": current, "raw": line})
    return entries


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/check_outdated.py <requirements.txt>")
        sys.exit(1)

    req_path = sys.argv[1]
    if not os.path.exists(req_path):
        print(f"File not found: {req_path}")
        sys.exit(1)

    entries = parse_requirements(req_path)
    report = []
    for e in entries:
        latest = fetch_latest(e["name"]) or "unknown"
        status = "unknown"
        if e["current"] and latest != "unknown":
            try:
                status = "outdated" if version.parse(latest) > version.parse(e["current"]) else "up-to-date"
            except Exception:
                status = "unknown"
        report.append({
            "package": e["name"],
            "declared": e["current"] or e["spec"] or "(any)",
            "latest": latest,
            "status": status,
        })

    print(f"\nOutdated report for {req_path}:")
    for r in report:
        print(f"- {r['package']}: declared {r['declared']} -> latest {r['latest']} [{r['status']}]")


if __name__ == "__main__":
    main()
