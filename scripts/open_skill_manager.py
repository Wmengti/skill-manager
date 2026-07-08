#!/usr/bin/env python3
"""Refresh the Skill Manager dashboard and optionally serve it over localhost."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
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


def write_dashboard(plugin_root: Path) -> dict:
    scanner = load_scanner(plugin_root / "scripts" / "skill_manager_mcp.py")
    inventory = scanner.scan_skills()
    output = plugin_root / "assets" / "skill-dashboard.html"
    dashboard = scanner.write_dashboard_file(inventory, output)
    return {
        "path": dashboard["path"],
        "url": dashboard["url"],
        "summary": inventory["summary"],
    }


def serve_dashboard(plugin_root: Path, host: str, port: int) -> None:
    assets_dir = plugin_root / "assets"
    os.chdir(assets_dir)
    server = ThreadingHTTPServer((host, port), SimpleHTTPRequestHandler)
    local_url = f"http://{host}:{server.server_port}/skill-dashboard.html"
    print(json.dumps({"url": local_url, "root": str(assets_dir.resolve())}, ensure_ascii=False, indent=2), flush=True)
    server.serve_forever()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh the Skill Manager dashboard.")
    parser.add_argument("--serve", action="store_true", help="Serve the dashboard over localhost after refreshing it.")
    parser.add_argument("--host", default="127.0.0.1", help="Host for --serve.")
    parser.add_argument("--port", type=int, default=8765, help="Port for --serve. Use 0 for a random free port.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    plugin_root = Path(__file__).resolve().parents[1]
    result = write_dashboard(plugin_root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.serve:
        serve_dashboard(plugin_root, args.host, args.port)


if __name__ == "__main__":
    main()
