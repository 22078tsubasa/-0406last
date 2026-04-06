from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


AGE_LABELS = [
    "0～4歳", "5～9歳", "10～14歳", "15～19歳", "20～24歳", "25～29歳", "30～34歳",
    "35～39歳", "40～44歳", "45～49歳", "50～54歳", "55～59歳", "60～64歳", "65～69歳",
    "70～74歳", "75～79歳", "80～84歳", "85～89歳", "90～94歳", "95～99歳", "100歳以上",
]

COEFFS = {
    "0～4歳": 0.0379,
    "5～9歳": 0.05196,
    "10～14歳": 0.0368,
    "15～19歳": 0.02459,
    "20～24歳": 0.02367,
    "25～29歳": 0.02837,
    "30～34歳": 0.03201,
    "35～39歳": 0.03353,
    "40～44歳": 0.03501,
    "45～49歳": 0.03912,
    "50～54歳": 0.04395,
    "55～59歳": 0.05751,
    "60～64歳": 0.0632,
    "65～69歳": 0.08101,
    "70～74歳": 0.09395,
    "75～79歳": 0.11197,
    "80～84歳": 0.1201,
    "85～89歳": 0.11483,
    "90～94歳": 0.10021,
    "95～99歳": 0.10021,
    "100歳以上": 0.10021,
}

# よくある入力列名の揺れに対応
AGE_INPUT_CANDIDATES = {
    "0～4歳": ["0～4歳", "pop_0_4", "0-4"],
    "5～9歳": ["5～9歳", "pop_5_9", "5-9"],
    "10～14歳": ["10～14歳", "pop_10_14", "10-14"],
    "15～19歳": ["15～19歳", "pop_15_19", "15-19"],
    "20～24歳": ["20～24歳", "pop_20_24", "20-24"],
    "25～29歳": ["25～29歳", "pop_25_29", "25-29"],
    "30～34歳": ["30～34歳", "pop_30_34", "30-34"],
    "35～39歳": ["35～39歳", "pop_35_39", "35-39"],
    "40～44歳": ["40～44歳", "pop_40_44", "40-44"],
    "45～49歳": ["45～49歳", "pop_45_49", "45-49"],
    "50～54歳": ["50～54歳", "pop_50_54", "50-54"],
    "55～59歳": ["55～59歳", "pop_55_59", "55-59"],
    "60～64歳": ["60～64歳", "pop_60_64", "60-64"],
    "65～69歳": ["65～69歳", "pop_65_69", "65-69"],
    "70～74歳": ["70～74歳", "pop_70_74", "70-74"],
    "75～79歳": ["75～79歳", "pop_75_79", "75-79"],
    "80～84歳": ["80～84歳", "pop_80_84", "80-84"],
    "85～89歳": ["85～89歳", "pop_85_89", "85-89"],
    "90～94歳": ["90～94歳", "pop_90_94", "90-94"],
    "95～99歳": ["95～99歳", "pop_95_99", "95-99"],
    "100歳以上": ["100歳以上", "pop_100-", "pop_100_plus", "100+"]
}


def read_input(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".xlsx", ".xlsm", ".xls"}:
        return pd.read_excel(path)
    return pd.read_csv(path)


def find_first_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def round_half_up(series: pd.Series) -> pd.Series:
    # 正値の四捨五入
    return np.floor(series.astype(float) + 0.5)


def build(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, str]]:
    city_col = find_first_col(df, ["CITY_NAME", "市区町村", "市区町村名"])
    town_col = find_first_col(df, ["S_NAME", "町丁目", "人口"])
    pop_col = find_first_col(df, ["POP", "合計人口", "総人口", "TPOP_EST"])
    src_col = find_first_col(df, ["__srcfile"])

    age_col_map: dict[str, str] = {}
    for age in AGE_LABELS:
        c = find_first_col(df, AGE_INPUT_CANDIDATES[age])
        if c:
            age_col_map[age] = c

    out = pd.DataFrame(index=df.index)
    out["CITY_NAME"] = df[city_col] if city_col else np.nan
    out["S_NAME"] = df[town_col] if town_col else np.nan
    out["POP"] = pd.to_numeric(df[pop_col], errors="coerce") if pop_col else np.nan
    out["__srcfile"] = df[src_col] if src_col else np.nan

    for age in AGE_LABELS:
        src = age_col_map.get(age)
        out[age] = pd.to_numeric(df[src], errors="coerce") if src else np.nan

    raw_cols = []
    round_cols = []
    for age in AGE_LABELS:
        raw_c = f"{age}_受容者(小数)"
        rnd_c = f"{age}_受容者(四捨五入)"
        out[raw_c] = out[age] * COEFFS[age]
        out[rnd_c] = round_half_up(out[raw_c])
        out.loc[out[age].isna(), [raw_c, rnd_c]] = np.nan
        raw_cols.append(raw_c)
        round_cols.append(rnd_c)

    out["SUM_受容者(小数)"] = out[raw_cols].sum(axis=1, min_count=1)
    out["SUM_受容者(四捨五入)"] = out[round_cols].sum(axis=1, min_count=1)

    unmatched = out[out[AGE_LABELS].isna().all(axis=1)][["CITY_NAME", "S_NAME", "POP", "__srcfile"]].copy()
    return out, unmatched, age_col_map


def main() -> None:
    parser = argparse.ArgumentParser(description="町丁目別 年齢別医療受容者数を作成")
    parser.add_argument("--input", required=True, help="東京都町丁目人口データ (xlsx/csv)")
    parser.add_argument("--output", required=True, help="出力xlsxパス")
    args = parser.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    df = read_input(in_path)
    out, unmatched, age_col_map = build(df)

    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        out.to_excel(writer, sheet_name="main_with_age", index=False)
        unmatched.to_excel(writer, sheet_name="unmatched", index=False)

    out.with_suffix = None
    out_csv = out_path.with_name(out_path.stem + "_main_with_age.csv")
    unmatched_csv = out_path.with_name(out_path.stem + "_unmatched.csv")
    out.to_csv(out_csv, index=False, encoding="utf-8-sig")
    unmatched.to_csv(unmatched_csv, index=False, encoding="utf-8-sig")

    print(f"input rows: {len(df)}")
    print(f"output rows: {len(out)}")
    print(f"unmatched rows: {len(unmatched)}")
    print(f"age columns detected: {age_col_map}")
    print(f"saved xlsx: {out_path}")
    print(f"saved csv : {out_csv}")
    print(f"saved csv : {unmatched_csv}")


if __name__ == "__main__":
    main()
