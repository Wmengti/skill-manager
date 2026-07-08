#!/usr/bin/env python3
"""Refresh the Skill Manager dashboard and print a browser-friendly URL."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from urllib.parse import quote


def load_scanner(script_path: Path):
    spec = importlib.util.spec_from_file_location("skill_manager_mcp", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load scanner: {script_path}")
    module = importlib.util.module_from_spec(spec)
    import sys

    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def file_url(path: Path) -> str:
    return "file://" + quote(str(path.resolve()))


def main() -> None:
    plugin_root = Path(__file__).resolve().parents[1]
    scanner = load_scanner(plugin_root / "scripts" / "skill_manager_mcp.py")
    inventory = scanner.scan_skills()
    output = plugin_root / "assets" / "skill-dashboard.html"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(scanner.dashboard_html(inventory), encoding="utf-8")
    result = {
        "path": str(output),
        "url": file_url(output),
        "summary": inventory["summary"],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
