from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd


R2KA27_SHP = Path("/Users/itotsubasa/Downloads/jadecom/大阪赤十字病院/r2ka27.shp")
CAR30_SHP = Path("/Users/itotsubasa/Downloads/jadecom/大阪赤十字病院/大阪到達圏n30分以内/oosakasekizyuzi.shp")
MATRIX_CSV = Path("/Users/itotsubasa/Downloads/jadecom/大阪赤十字病院/大阪十字_町丁目別_各医療施設利用数_KLA統合.csv")

OUT_DIR = Path("/Users/itotsubasa/Downloads/jadecom/大阪赤十字病院")
OUT_CSV = OUT_DIR / "大阪赤十字病院周辺の町丁目_各医療施設利用数_KLA統合_osaka_car30_match.csv"
OUT_XLSX = OUT_DIR / "大阪赤十字病院周辺の町丁目_各医療施設利用数_KLA統合_osaka_car30_match.xlsx"
OUT_TOWNS = OUT_DIR / "大阪赤十字病院_車30分圏_対象町丁目一覧.csv"


def normalize_text(s: str) -> str:
    return str(s).replace("　", "").replace(" ", "").strip().replace("大字", "")


def main() -> None:
    g_town = gpd.read_file(R2KA27_SHP)
    g_car = gpd.read_file(CAR30_SHP)

    # 到達圏ポリゴンを1つにまとめる
    car_union = g_car.to_crs(g_town.crs).unary_union
    g_town["in_car30"] = g_town.geometry.intersects(car_union)
    g30 = g_town[g_town["in_car30"]].copy()
    g30["TOWN_CODE_11"] = g30["KEY_CODE"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(11)

    # 重複コードは1つに
    g30 = g30.drop_duplicates("TOWN_CODE_11")
    keys = set(g30["TOWN_CODE_11"].tolist())

    m = pd.read_csv(MATRIX_CSV, dtype={"TOWN_CODE_11": str})
    m["TOWN_CODE_11"] = m["TOWN_CODE_11"].fillna("").astype(str).str.zfill(11)

    out = m[m["TOWN_CODE_11"].isin(keys)].copy()

    # 可視化スクリプト互換の列を追加
    out["town"] = out["town_name_show"]
    out["town_norm"] = out["town"].map(normalize_text)
    out["match_type"] = "code_in_car30"

    # 列順を寄せる
    front = [
        "town",
        "town_norm",
        "match_type",
        "CITY_NAME_from_master",
        "S_NAME_from_master",
        "town_name_show",
        "TOWN_CODE_11",
        "dist_km",
        "LON",
        "LAT",
    ]
    remain = [c for c in out.columns if c not in front]
    out = out[front + remain].sort_values(["dist_km", "CITY_NAME_from_master", "S_NAME_from_master"], na_position="last").reset_index(drop=True)

    towns = out[["CITY_NAME_from_master", "S_NAME_from_master", "town_name_show", "TOWN_CODE_11", "dist_km"]].drop_duplicates()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    with pd.ExcelWriter(OUT_XLSX, engine="openpyxl") as w:
        out.to_excel(w, index=False, sheet_name="Sheet1")
    towns.to_csv(OUT_TOWNS, index=False, encoding="utf-8-sig")

    print("r2ka27 rows:", len(g_town))
    print("car30 towns (polygon intersect):", len(g30))
    print("matrix rows:", len(m))
    print("matched rows:", len(out))
    print("saved:", OUT_CSV)
    print("saved:", OUT_XLSX)
    print("saved:", OUT_TOWNS)


if __name__ == "__main__":
    main()
