from __future__ import annotations

from pathlib import Path

import pandas as pd


KLA_DIR = Path("/Users/itotsubasa/Library/CloudStorage/OneDrive-SIT/L3S（社会システム科学研究室） - ドキュメント/0共-地域医療振興協会/2025年度/大阪十字_KLA集計")
TOWN_MASTER = Path("/Users/itotsubasa/Downloads/jadecom/大阪赤十字病院/main_with_age_osaka_h03_27_with_lonlat_dist.csv")
OUT_DIR = Path("/Users/itotsubasa/Downloads/jadecom/大阪赤十字病院")

OUT_CSV = OUT_DIR / "大阪十字_町丁目別_各医療施設利用数_KLA統合.csv"
OUT_XLSX = OUT_DIR / "大阪十字_町丁目別_各医療施設利用数_KLA統合.xlsx"
OUT_UNMATCHED = OUT_DIR / "大阪十字_町丁目別_座標未結合一覧.csv"

SUFFIX = "_国内居住者・来訪者居住地分析_20240401_20250331"


def parse_facility_name(folder_name: str, used: set[str]) -> str:
    name = folder_name
    if name.endswith(SUFFIX):
        name = name[: -len(SUFFIX)]
    name = name.strip()
    if name not in used:
        used.add(name)
        return name
    i = 2
    while True:
        cand = f"{name}_{i}"
        if cand not in used:
            used.add(cand)
            return cand
        i += 1


def read_town_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="cp932")
    need = {"コード", "町丁目名", "人数"}
    if not need.issubset(df.columns):
        return pd.DataFrame(columns=["TOWN_CODE_11", "town_name_show", "人数"])
    out = df[["コード", "町丁目名", "人数"]].copy()
    out["TOWN_CODE_11"] = (
        out["コード"]
        .astype(str)
        .str.replace(r"\.0$", "", regex=True)
        .str.zfill(11)
    )
    out["town_name_show"] = out["町丁目名"].astype(str).str.strip()
    out["人数"] = pd.to_numeric(out["人数"], errors="coerce").fillna(0)
    return out[["TOWN_CODE_11", "town_name_show", "人数"]]


def split_city_sname(town_name_show: str) -> tuple[str, str]:
    s = str(town_name_show)
    for k in ["市", "区", "町", "村"]:
        idx = s.find(k)
        if idx >= 0:
            return s[: idx + 1], s[idx + 1 :]
    return "", s


def main() -> None:
    town_files = sorted(KLA_DIR.glob("*/3_Towns_*.csv"))
    if not town_files:
        raise FileNotFoundError(f"3_Towns csv not found: {KLA_DIR}")

    used_names: set[str] = set()
    base: pd.DataFrame | None = None
    facility_cols: list[str] = []

    for f in town_files:
        facility = parse_facility_name(f.parent.name, used_names)
        t = read_town_csv(f)
        if t.empty:
            continue
        t = t.groupby(["TOWN_CODE_11", "town_name_show"], as_index=False)["人数"].sum().rename(columns={"人数": facility})
        if base is None:
            base = t
        else:
            base = base.merge(t, on=["TOWN_CODE_11", "town_name_show"], how="outer")
        facility_cols.append(facility)

    if base is None:
        raise RuntimeError("有効なデータを作成できませんでした。")

    for c in facility_cols:
        base[c] = pd.to_numeric(base[c], errors="coerce").fillna(0)

    master = pd.read_csv(TOWN_MASTER, dtype={"TOWN_CODE_11": str})
    master["TOWN_CODE_11"] = master["TOWN_CODE_11"].fillna("").astype(str).str.zfill(11)
    mcols = [
        "TOWN_CODE_11",
        "CITY_NAME_from_master",
        "S_NAME_from_master",
        "LON",
        "LAT",
        "dist_km",
    ]
    m = master[mcols].drop_duplicates("TOWN_CODE_11")

    out = base.merge(m, on="TOWN_CODE_11", how="left")

    miss_city = out["CITY_NAME_from_master"].isna() | (out["CITY_NAME_from_master"].astype(str).str.strip() == "")
    parsed = out.loc[miss_city, "town_name_show"].map(split_city_sname)
    out.loc[miss_city, "CITY_NAME_from_master"] = [x[0] for x in parsed]
    out.loc[miss_city, "S_NAME_from_master"] = [x[1] for x in parsed]

    out["total_215"] = out[facility_cols].sum(axis=1)
    out = out[
        ["CITY_NAME_from_master", "S_NAME_from_master", "town_name_show", "TOWN_CODE_11", "dist_km", "LON", "LAT"] + facility_cols + ["total_215"]
    ].copy()
    out = out.sort_values(["dist_km", "CITY_NAME_from_master", "S_NAME_from_master"], na_position="last").reset_index(drop=True)

    unmatched = out[out["LON"].isna() | out["LAT"].isna()][
        ["CITY_NAME_from_master", "S_NAME_from_master", "town_name_show", "TOWN_CODE_11"]
    ].copy()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    with pd.ExcelWriter(OUT_XLSX, engine="openpyxl") as w:
        out.to_excel(w, index=False, sheet_name="Sheet1")
    unmatched.to_csv(OUT_UNMATCHED, index=False, encoding="utf-8-sig")

    print("town files:", len(town_files))
    print("facility cols:", len(facility_cols))
    print("town rows:", len(out))
    print("lon/lat matched:", int(out["LON"].notna().sum()), "/", len(out))
    print("saved:", OUT_CSV)
    print("saved:", OUT_XLSX)
    print("saved:", OUT_UNMATCHED)


if __name__ == "__main__":
    main()
