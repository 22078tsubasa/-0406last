from __future__ import annotations

import math
from pathlib import Path

import geopandas as gpd
import pandas as pd


IN_MAIN_CSV = Path("/Users/itotsubasa/IdeaProjects/pythoN/JADECOM/大阪年齢別需要者数/main_with_age_osaka_h03_27_main_with_age.csv")
TOWN_SHP = Path("/Users/itotsubasa/Downloads/jadecom/大阪赤十字病院/r2ka27.shp")
HOSP_SHP = Path("/Users/itotsubasa/Downloads/jadecom/大阪赤十字病院/osaka_red_cross_hospital_point.shp")

OUT_DIR = Path("/Users/itotsubasa/Downloads/jadecom/大阪赤十字病院")
OUT_CSV = OUT_DIR / "main_with_age_osaka_h03_27_with_lonlat_dist.csv"
OUT_XLSX = OUT_DIR / "main_with_age_osaka_h03_27_with_lonlat_dist.xlsx"
OUT_UNMATCHED = OUT_DIR / "main_with_age_osaka_h03_27_lonlat_unmatched.csv"


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0088
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2.0) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2.0) ** 2
    return r * 2 * math.asin(math.sqrt(a))


def main() -> None:
    df = pd.read_csv(IN_MAIN_CSV, dtype={"CITY_CODE": str, "TOWN_CODE": str, "TOWN_CODE_11": str})
    df["TOWN_CODE_11"] = df["TOWN_CODE_11"].fillna("").astype(str).str.zfill(11)

    gdf = gpd.read_file(TOWN_SHP)
    gdf = gdf[gdf["S_NAME"].notna()].copy()
    gdf["TOWN_CODE_11"] = gdf["KEY_CODE"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(11)

    # polygon centroid in lon/lat
    gdf_m = gdf.to_crs(3857)
    cent = gdf_m.geometry.centroid
    cent_ll = gpd.GeoSeries(cent, crs=3857).to_crs(4326)
    gdf["LON"] = cent_ll.x
    gdf["LAT"] = cent_ll.y

    key_geo = (
        gdf[["TOWN_CODE_11", "PREF_NAME", "CITY_NAME", "S_NAME", "LON", "LAT"]]
        .drop_duplicates("TOWN_CODE_11")
        .rename(
            columns={
                "PREF_NAME": "PREF_NAME_from_shp",
                "CITY_NAME": "CITY_NAME_from_shp",
                "S_NAME": "S_NAME_from_shp",
            }
        )
    )

    hosp = gpd.read_file(HOSP_SHP).to_crs(4326)
    hlon = float(hosp.geometry.iloc[0].x)
    hlat = float(hosp.geometry.iloc[0].y)

    out = df.drop(columns=[c for c in ["LON", "LAT", "dist_km"] if c in df.columns]).merge(key_geo, on="TOWN_CODE_11", how="left")
    out["dist_km"] = out.apply(
        lambda r: haversine_km(hlat, hlon, float(r["LAT"]), float(r["LON"])) if pd.notna(r["LAT"]) and pd.notna(r["LON"]) else float("nan"),
        axis=1,
    )

    front = [
        "CITY_CODE",
        "TOWN_CODE",
        "TOWN_CODE_11",
        "CITY_NAME",
        "S_NAME",
        "CITY_NAME_from_master",
        "S_NAME_from_master",
        "town_name_show",
        "LON",
        "LAT",
        "dist_km",
    ]
    remain = [c for c in out.columns if c not in front]
    out = out[front + remain].sort_values(["dist_km", "CITY_NAME", "S_NAME"], na_position="last").reset_index(drop=True)

    unmatched = out[out["LON"].isna() | out["LAT"].isna()][["TOWN_CODE_11", "CITY_NAME", "S_NAME"]].copy()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    with pd.ExcelWriter(OUT_XLSX, engine="openpyxl") as w:
        out.to_excel(w, index=False, sheet_name="Sheet1")
    unmatched.to_csv(OUT_UNMATCHED, index=False, encoding="utf-8-sig")

    print("rows:", len(out))
    print("lon/lat matched:", int(out["LON"].notna().sum()), "/", len(out))
    print("unmatched:", len(unmatched))
    print("hospital lat/lon:", hlat, hlon)
    print("saved:", OUT_CSV)
    print("saved:", OUT_XLSX)
    print("saved:", OUT_UNMATCHED)


if __name__ == "__main__":
    main()
