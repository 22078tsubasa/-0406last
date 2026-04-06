from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd


def safe_name(text: str) -> str:
    t = re.sub(r"[\\/:*?\"<>|\s]+", "_", str(text))
    t = re.sub(r"_+", "_", t).strip("_")
    return t[:80]


def main() -> None:
    parser = argparse.ArgumentParser(description="KDDI自動ダウンロード用の対象CSVを作成")
    parser.add_argument("--places-csv", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--group-name", default="")
    parser.add_argument("--target-names", nargs="*", default=[])
    args = parser.parse_args()

    places_csv = Path(args.places_csv)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(places_csv, dtype=str).fillna("")
    if "place_name" not in df.columns:
        raise RuntimeError(f"place_name column missing: {places_csv}")

    if args.target_names:
        wanted = set(args.target_names)
        df = df[df["place_name"].isin(wanted)].copy()

    if df.empty:
        raise RuntimeError("no target facilities found")

    rows: list[dict] = []
    for i, r in df.reset_index(drop=True).iterrows():
        facility_name = str(r.get("place_name", ""))
        folder_name = f"{i+1:03d}_{safe_name(facility_name)}"
        folder_path = output_dir / folder_name
        folder_path.mkdir(parents=True, exist_ok=True)

        rows.append(
            {
                "seq": i + 1,
                "place_id": str(r.get("place_id", "")),
                "facility_id": str(r.get("place_id", "")),
                "facility_name": facility_name,
                "prefecture": str(r.get("prefecture", "")),
                "city": str(r.get("city", "")),
                "address": str(r.get("address", "")),
                "group_name": args.group_name or str(r.get("group_name", "")),
                "output_folder": str(folder_path),
                "kddi_query_name": facility_name,
                "status": "pending",
            }
        )

    targets_csv = output_dir / "kddi_batch_targets.csv"
    pd.DataFrame(rows).to_csv(targets_csv, index=False, encoding="utf-8-sig")

    meta = {
        "group_name": args.group_name,
        "target_names": args.target_names,
        "count": len(rows),
        "targets_csv": str(targets_csv),
    }
    (output_dir / "_targets_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"facilities: {len(rows)}")
    print(f"saved: {targets_csv}")


if __name__ == "__main__":
    main()
