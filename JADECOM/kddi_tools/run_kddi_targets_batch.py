from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def has_done_file(folder: Path, date_prefix: str) -> bool:
    return any(folder.glob(f"1_Condition_{date_prefix}*.csv"))


def main() -> None:
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass

    parser = argparse.ArgumentParser(description="KDDI downloader を1施設ずつ安全に回すバッチラッパー")
    parser.add_argument("--targets-csv", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--profile-dir", required=True)
    parser.add_argument("--organization", required=True)
    parser.add_argument("--identifier", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--timeout-sec", type=int, default=240)
    parser.add_argument("--max-facilities", type=int, default=0)
    parser.add_argument("--date-prefix", default="20260406")
    parser.add_argument("--log-file", required=True)
    args = parser.parse_args()

    script_path = Path(__file__).resolve().parent / "kddi_download_residence_exports.py"
    targets_csv = Path(args.targets_csv)
    output_dir = Path(args.output_dir)
    log_file = Path(args.log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    with targets_csv.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    pending: list[dict] = []
    for row in rows:
        folder = output_dir / Path(row["output_folder"]).name
        if not has_done_file(folder, args.date_prefix):
            pending.append(row)

    if args.max_facilities > 0:
        pending = pending[: args.max_facilities]

    print(f"pending={len(pending)}")

    results: list[dict] = []
    for idx, row in enumerate(pending, start=1):
        facility = row["facility_name"]
        folder = output_dir / Path(row["output_folder"]).name
        folder.mkdir(parents=True, exist_ok=True)
        print(f"[{idx}/{len(pending)}] {facility}")

        with tempfile.NamedTemporaryFile("w", encoding="utf-8-sig", newline="", suffix=".csv", delete=False) as tmp:
            writer = csv.DictWriter(tmp, fieldnames=row.keys())
            writer.writeheader()
            writer.writerow(row)
            tmp_csv = tmp.name

        env = os.environ.copy()
        env["KDDI_PROFILE_DIR"] = args.profile_dir
        env["KDDI_ORGANIZATION"] = args.organization
        env["KDDI_IDENTIFIER"] = args.identifier
        env["KDDI_PASSWORD"] = args.password

        cmd = [
            sys.executable,
            str(script_path),
            "--targets-csv",
            tmp_csv,
            "--output-dir",
            str(output_dir),
            "--headless",
            "--start-date",
            "2024-04-01",
            "--end-date",
            "2025-03-31",
            "--time-start",
            "05:00",
            "--time-end",
            "29:00",
            "--stay-end",
            "120",
        ]

        started_at = time.time()
        try:
            proc = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=args.timeout_sec,
                check=False,
            )
            elapsed = round(time.time() - started_at, 1)
            status = "ok" if proc.returncode == 0 and has_done_file(folder, args.date_prefix) else "failed"
            results.append(
                {
                    "facility_name": facility,
                    "folder": str(folder),
                    "status": status,
                    "returncode": proc.returncode,
                    "elapsed_sec": elapsed,
                    "stdout": proc.stdout[-4000:],
                    "stderr": proc.stderr[-4000:],
                }
            )
        except subprocess.TimeoutExpired as e:
            elapsed = round(time.time() - started_at, 1)
            results.append(
                {
                    "facility_name": facility,
                    "folder": str(folder),
                    "status": "timeout",
                    "returncode": None,
                    "elapsed_sec": elapsed,
                    "stdout": (e.stdout or "")[-4000:],
                    "stderr": (e.stderr or "")[-4000:],
                }
            )
        finally:
            try:
                Path(tmp_csv).unlink()
            except Exception:
                pass

        log_file.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        last = results[-1]
        print(f"{facility} -> {last['status']} ({last['elapsed_sec']}s)")


if __name__ == "__main__":
    main()
