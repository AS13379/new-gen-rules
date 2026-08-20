#!/usr/bin/env python3
"""Fail if the committed routing report no longer matches a fresh simulation.

Without this check the report could keep stating an old pass count after the
rules or scenarios changed.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path


def load_simulator(root: Path):
    path = root / "scripts" / "simulate_routing.py"
    spec = importlib.util.spec_from_file_location("simulate_routing_check", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load simulator: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()

    simulator = load_simulator(root)
    scenarios = json.loads(
        (root / "tests" / "fixtures" / "routing-scenarios.json").read_text(encoding="utf-8")
    )
    results = simulator.run_matrix(root, scenarios)
    expected = simulator.render_markdown(results, root / "reports" / "review-notes.md")

    report_path = root / "reports" / "mainland-strict-routing-report.md"
    if not report_path.is_file():
        print(f"Report is missing: {report_path.relative_to(root)}")
        return 1
    if report_path.read_text(encoding="utf-8") != expected:
        print(f"Report is stale: {report_path.relative_to(root)}")
        print("Regenerate with: python3 scripts/simulate_routing.py --report " + str(report_path.relative_to(root)))
        return 1
    print("Report is current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
