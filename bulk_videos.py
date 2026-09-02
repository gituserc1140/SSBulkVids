#!/usr/bin/env python3
"""Submit one Shotstack render for every row in a CSV file."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib import error, request

PLACEHOLDER = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")


def merge_template(template: str, row: dict[str, str]) -> dict[str, Any]:
    """Replace {{column}} values in a JSON template and parse the result."""
    missing = sorted({name for name in PLACEHOLDER.findall(template) if name not in row})
    if missing:
        raise ValueError("CSV is missing template columns: " + ", ".join(missing))
    merged = PLACEHOLDER.sub(lambda match: row[match.group(1)], template)
    try:
        return json.loads(merged)
    except json.JSONDecodeError as exc:
        raise ValueError(f"merged template is not valid JSON: {exc}") from exc


def api_call(url: str, api_key: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"x-api-key": api_key, "Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = request.Request(url, data=body, headers=headers, method="POST" if body else "GET")
    try:
        with request.urlopen(req, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Shotstack returned HTTP {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"could not reach Shotstack: {exc.reason}") from exc


def wait_for_render(status_url: str, api_key: str, interval: float, timeout: float) -> tuple[str, str]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = api_call(status_url, api_key)
        details = response.get("response", response)
        status = str(details.get("status", "unknown")).lower()
        if status in {"done", "failed"}:
            return status, str(details.get("url", ""))
        time.sleep(interval)
    return "timeout", ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_file", type=Path)
    parser.add_argument("template_file", type=Path)
    parser.add_argument("-o", "--manifest", type=Path, default=Path("render_manifest.csv"))
    parser.add_argument("--wait", action="store_true", help="poll each render until it completes")
    parser.add_argument("--interval", type=float, default=5, help="seconds between status checks")
    parser.add_argument("--timeout", type=float, default=1800, help="maximum wait per render")
    parser.add_argument("--dry-run", action="store_true", help="validate and print requests without submitting")
    parser.add_argument("--endpoint", default=os.getenv("SHOTSTACK_ENDPOINT", "https://api.shotstack.io/v1"))
    args = parser.parse_args()

    if args.interval <= 0 or args.timeout <= 0:
        parser.error("--interval and --timeout must be positive")
    api_key = os.getenv("SHOTSTACK_API_KEY", "")
    if not args.dry_run and not api_key:
        parser.error("set SHOTSTACK_API_KEY or use --dry-run")

    template = args.template_file.read_text(encoding="utf-8")
    manifest_rows: list[dict[str, str]] = []
    with args.csv_file.open(newline="", encoding="utf-8-sig") as csv_file:
        rows = csv.DictReader(csv_file)
        if not rows.fieldnames:
            parser.error("CSV must contain a header row")
        for row_number, row in enumerate(rows, start=1):
            result = {"row": str(row_number), "render_id": "", "status": "", "video_url": "", "error": ""}
            try:
                payload = merge_template(template, {key: value or "" for key, value in row.items()})
                if args.dry_run:
                    result["status"] = "validated"
                    print(json.dumps(payload, indent=2))
                else:
                    response = api_call(f"{args.endpoint.rstrip('/')}/render", api_key, payload)
                    details = response.get("response", response)
                    render_id = str(details.get("id", ""))
                    if not render_id:
                        raise RuntimeError("Shotstack response did not include a render id")
                    result["render_id"] = render_id
                    result["status"] = "submitted"
                    if args.wait:
                        result["status"], result["video_url"] = wait_for_render(
                            f"{args.endpoint.rstrip('/')}/render/{render_id}",
                            api_key,
                            args.interval,
                            args.timeout,
                        )
                print(f"row {row_number}: {result['status']}")
            except (OSError, ValueError, RuntimeError) as exc:
                result["status"] = "failed"
                result["error"] = str(exc)
                print(f"row {row_number}: failed: {exc}", file=sys.stderr)
            manifest_rows.append(result)

    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    with args.manifest.open("w", newline="", encoding="utf-8") as manifest_file:
        writer = csv.DictWriter(manifest_file, fieldnames=manifest_rows[0].keys() if manifest_rows else
                                ["row", "render_id", "status", "video_url", "error"])
        writer.writeheader()
        writer.writerows(manifest_rows)
    return 1 if any(item["status"] == "failed" for item in manifest_rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
