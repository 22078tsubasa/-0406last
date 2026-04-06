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


def read_csv_any(path: Path) -> pd.DataFrame:
    for enc in ["cp932", "utf-8-sig", "utf-8"]:
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            continue
    raise RuntimeError(f"read failed: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="競合リストCSVからKDDI取得用の施設別フォルダを作成")
    parser.add_argument("--input-csv", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--group-name", default="")
    args = parser.parse_args()

    input_csv = Path(args.input_csv)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = read_csv_any(input_csv).fillna("")
    if "Facility_N" not in df.columns:
        raise RuntimeError(f"Facility_N column missing: {input_csv}")

    dedup_key = "Medical_ID" if "Medical_ID" in df.columns else "Facility_N"
    df = df[df["Facility_N"].astype(str).str.strip() != ""].copy()
    df = df.drop_duplicates(subset=[dedup_key], keep="first").reset_index(drop=True)

    rows: list[dict] = []
    for i, r in df.iterrows():
        facility_name = str(r.get("Facility_N", "")).strip()
        folder_name = f"{i+1:03d}_{safe_name(facility_name)}"
        folder_path = output_dir / folder_name
        folder_path.mkdir(parents=True, exist_ok=True)

        readme = folder_path / "README_手動取得条件.txt"
        readme.write_text(
            "\n".join(
                [
                    f"施設名: {facility_name}",
                    f"医療機関ID: {str(r.get('Medical_ID', '')).strip()}",
                    f"住所: {str(r.get('Address', '')).strip()}",
                    "",
                    "このフォルダにKDDI来訪者居住地分析のCSVを格納する。",
                    "必要に応じて ZIP 展開後の 1_Condition / 2_Cities / 3_Towns / 4_Prefectures を保存する。",
                ]
            ),
            encoding="utf-8",
        )

        rows.append(
            {
                "seq": i + 1,
                "facility_id": str(r.get("Medical_ID", "")).strip(),
                "facility_name": facility_name,
                "prefecture": str(r.get("Prefecture", "")).strip(),
                "city": str(r.get("City_name", "")).strip(),
                "address": str(r.get("Address", "")).strip(),
                "group_name": args.group_name,
                "output_folder": str(folder_path),
                "kddi_query_name": facility_name,
                "status": "pending",
            }
        )

    targets_csv = output_dir / "kddi_batch_targets.csv"
    pd.DataFrame(rows).to_csv(targets_csv, index=False, encoding="utf-8-sig")

    summary = {
        "input_csv": str(input_csv),
        "group_name": args.group_name,
        "facility_count": len(rows),
        "targets_csv": str(targets_csv),
    }
    (output_dir / "_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"facilities: {len(rows)}")
    print(f"saved: {targets_csv}")


if __name__ == "__main__":
    main()
