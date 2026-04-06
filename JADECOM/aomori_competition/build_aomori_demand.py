from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
IN_CSV = Path("/Users/itotsubasa/Downloads/jadecom/4:6/青森/h03_02.csv")
OUT_CSV = BASE_DIR / "data" / "h03_02_町丁目別医療需要者数_main_with_age.csv"

AGE_COLS = [
    "0～4歳", "5～9歳", "10～14歳", "15～19歳", "20～24歳", "25～29歳", "30～34歳", "35～39歳",
    "40～44歳", "45～49歳", "50～54歳", "55～59歳", "60～64歳", "65～69歳", "70～74歳", "75～79歳",
    "80～84歳", "85～89歳", "90～94歳", "95～99歳", "100歳以上",
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


def to_num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.replace({"X": np.nan, "-": np.nan}), errors="coerce")


def zfill_series(s: pd.Series, width: int) -> pd.Series:
    return s.fillna("").astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(width)


def round_half_up(s: pd.Series) -> pd.Series:
    return np.floor(s.astype(float) + 0.5)


def main() -> None:
    df = pd.read_csv(IN_CSV, encoding="cp932", header=4)
    use = df[(df["都道府県名"] == "青森県") & (df["男女"] == "総数") & (df["地域階層レベル"] == 4)].copy()

    use["市区町村コード"] = zfill_series(use["市区町村コード"], 5)
    use["町丁字コード"] = zfill_series(use["町丁字コード"], 6)
    use["TOWN_CODE_11"] = use["市区町村コード"] + use["町丁字コード"]
    use["CITY_NAME_from_master"] = use["市区町村名"].fillna("").astype(str).str.strip()
    use["S_NAME_from_master"] = (
        use["大字・町名"].fillna("").astype(str).str.strip() +
        use["字・丁目名"].fillna("").astype(str).str.strip()
    )
    use["町丁目名"] = use["CITY_NAME_from_master"] + use["S_NAME_from_master"]
    use["town_name_show"] = use["市区町村名"].fillna("").astype(str).str.strip() + use["S_NAME_from_master"]
    use["総数"] = to_num(use["総数"]).fillna(0)

    for age in AGE_COLS:
        use[age] = to_num(use[age]).fillna(0)
        use[f"{age}_医療需要者数"] = round_half_up(use[age] * COEFFS[age])

    need_cols = [
        "都道府県名",
        "市区町村名",
        "大字・町名",
        "字・丁目名",
        "町丁目名",
        "市区町村コード",
        "町丁字コード",
        "地域階層レベル",
        "総数",
        "CITY_NAME_from_master",
        "S_NAME_from_master",
        "town_name_show",
        "TOWN_CODE_11",
    ]
    out = use[need_cols + AGE_COLS + [f"{age}_医療需要者数" for age in AGE_COLS]].copy()
    out["医療需要者数合計"] = out[[f"{age}_医療需要者数" for age in AGE_COLS]].sum(axis=1)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    print(f"saved: {OUT_CSV}")
    print(f"rows: {len(out)}")


if __name__ == "__main__":
    main()
