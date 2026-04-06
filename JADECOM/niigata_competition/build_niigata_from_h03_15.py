from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from config import DEMAND_CSV, DEMAND_XLSX, H03_CSV


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
    x = s.astype(float)
    return np.floor(x + 0.5)


def cat4(pref: pd.Series, city: pd.Series, oaza: pd.Series, chome: pd.Series) -> pd.Series:
    a = pref.fillna("").astype(str).str.strip()
    b = city.fillna("").astype(str).str.strip()
    c = oaza.fillna("").astype(str).str.strip()
    d = chome.fillna("").astype(str).str.strip()
    return (a + b + c + d).str.replace("nan", "", regex=False)


def main() -> None:
    df = pd.read_csv(H03_CSV, encoding="cp932", header=4)

    rename_map = {
        "Unnamed: 8": "都道府県名",
        "Unnamed: 9": "市区町村名",
        "Unnamed: 10": "大字・町名",
        "Unnamed: 11": "字・丁目名",
    }
    df = df.rename(columns=rename_map)

    use = df[(df["都道府県名"] == "新潟県") & (df["男女"] == "総数") & (df["地域階層レベル"] == 4)].copy()

    use["CITY_CODE"] = zfill_series(use["市区町村コード"], 5)
    use["TOWN_CODE"] = zfill_series(use["町丁字コード"], 6)
    use["TOWN_CODE_11"] = use["CITY_CODE"] + use["TOWN_CODE"]
    use["CITY_NAME"] = use["市区町村名"]
    use["S_NAME"] = (
        use["大字・町名"].fillna("").astype(str).str.strip() +
        use["字・丁目名"].fillna("").astype(str).str.strip()
    ).replace("", np.nan)
    use["TOWN_NAME_4COL"] = cat4(use["都道府県名"], use["市区町村名"], use["大字・町名"], use["字・丁目名"])
    use["POP"] = to_num(use["総数"])
    use["__srcfile"] = H03_CSV.name

    out = use[["CITY_CODE", "TOWN_CODE", "TOWN_CODE_11", "CITY_NAME", "S_NAME", "TOWN_NAME_4COL", "POP", "__srcfile"]].copy()

    age_raw: dict[str, pd.Series] = {}
    for c in AGE_COLS:
        age_raw[c] = to_num(use[c])
        out[c] = age_raw[c].fillna(0)

    raw_cols = []
    rnd_cols = []
    for c in AGE_COLS:
        rc = f"{c}_受容者(小数)"
        kc = f"{c}_受容者(四捨五入)"
        out[rc] = out[c] * COEFFS[c]
        out[kc] = round_half_up(out[rc])
        raw_cols.append(rc)
        rnd_cols.append(kc)

    out["SUM_受容者(小数)"] = out[raw_cols].sum(axis=1)
    out["SUM_受容者(四捨五入)"] = out[rnd_cols].sum(axis=1)

    raw_all_nan = pd.DataFrame(age_raw).isna().all(axis=1)
    unmatched = out.loc[
        raw_all_nan,
        ["CITY_CODE", "TOWN_CODE", "TOWN_CODE_11", "CITY_NAME", "S_NAME", "TOWN_NAME_4COL", "POP", "__srcfile"],
    ].copy()

    out["CITY_NAME_from_master"] = out["CITY_NAME"]
    out["S_NAME_from_master"] = out["S_NAME"]
    out["town_name_show"] = out["CITY_NAME"].fillna("").astype(str) + out["S_NAME"].fillna("").astype(str)
    out["LON"] = np.nan
    out["LAT"] = np.nan
    out["dist_km"] = np.nan

    DEMAND_XLSX.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(DEMAND_XLSX, engine="openpyxl") as writer:
        out.to_excel(writer, sheet_name="main_with_age", index=False)
        unmatched.to_excel(writer, sheet_name="unmatched", index=False)

    out.to_csv(DEMAND_CSV, index=False, encoding="utf-8-sig")
    unmatched.to_csv(DEMAND_XLSX.with_name(DEMAND_XLSX.stem + "_unmatched.csv"), index=False, encoding="utf-8-sig")

    print(f"input rows: {len(df)}")
    print(f"niigata town rows(level=4): {len(out)}")
    print(f"unmatched rows: {len(unmatched)}")
    print(f"saved: {DEMAND_XLSX}")
    print(f"saved: {DEMAND_CSV}")


if __name__ == "__main__":
    main()
