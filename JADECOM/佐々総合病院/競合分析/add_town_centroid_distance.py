from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd

TABLE_IN = Path('/Users/itotsubasa/IdeaProjects/pythoN/JADECOM/佐々総合病院/競合分析/佐々総合病院周辺の町丁目_各医療施設利用数_KLA統合_tokyo_car30_match.xlsx')
SHP_IN = Path('/Users/itotsubasa/IdeaProjects/pythoN/JADECOM/佐々総合病院/競合分析/tokyo_car30_target_towns_from_r2ka13.shp')
TABLE_OUT_XLSX = Path('/Users/itotsubasa/IdeaProjects/pythoN/JADECOM/佐々総合病院/競合分析/佐々総合病院周辺の町丁目_各医療施設利用数_KLA統合_tokyo_car30_match_with_dist.xlsx')
TABLE_OUT_CSV = TABLE_OUT_XLSX.with_suffix('.csv')

HOSP_LAT = 35.72977
HOSP_LON = 139.5388


def norm(s: str) -> str:
    return str(s).replace('　', '').replace(' ', '').strip().replace('大字', '')


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0088
    lat1 = np.radians(lat1)
    lon1 = np.radians(lon1)
    lat2 = np.radians(lat2)
    lon2 = np.radians(lon2)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    c = 2 * np.arcsin(np.sqrt(a))
    return r * c


def main() -> None:
    df = pd.read_excel(TABLE_IN)
    gdf = gpd.read_file(SHP_IN)

    gdf = gdf.dropna(subset=['CITY_NAME', 'S_NAME']).copy()
    gdf['_city_'] = gdf['CITY_NAME'].astype(str).map(norm)
    gdf['_sname_'] = gdf['S_NAME'].astype(str).map(norm)

    # centroid in lon/lat (projected CRSで重心計算してからWGS84へ戻す)
    gdf_m = gdf.to_crs(3857)
    cent_m = gdf_m.geometry.centroid
    cent_ll = gpd.GeoSeries(cent_m, crs=3857).to_crs(4326)
    gdf['_lon_'] = cent_ll.x
    gdf['_lat_'] = cent_ll.y

    key_geo = (
        gdf[['CITY_NAME', 'S_NAME', '_city_', '_sname_', '_lon_', '_lat_']]
        .drop_duplicates(['_city_', '_sname_'])
        .rename(columns={'CITY_NAME': 'CITY_NAME_poly', 'S_NAME': 'S_NAME_poly'})
    )

    df['_city_'] = df['CITY_NAME_from_master'].fillna('').astype(str).map(norm)
    df['_sname_'] = df['S_NAME_from_master'].fillna('').astype(str).map(norm)

    out = df.merge(key_geo, on=['_city_', '_sname_'], how='left')
    out['LON'] = out['_lon_']
    out['LAT'] = out['_lat_']
    out['dist_km'] = haversine_km(HOSP_LAT, HOSP_LON, out['LAT'], out['LON'])
    out.loc[out['LON'].isna() | out['LAT'].isna(), 'dist_km'] = np.nan

    # Put geo cols near town columns
    geo_cols = ['LON', 'LAT', 'dist_km']
    front = ['town', 'town_norm', 'CITY_NAME_from_master', 'S_NAME_from_master']
    remain = [c for c in out.columns if c not in front + geo_cols + ['_city_', '_sname_', '_lon_', '_lat_', 'CITY_NAME_poly', 'S_NAME_poly']]
    out2 = out[front + geo_cols + remain].copy()

    with pd.ExcelWriter(TABLE_OUT_XLSX, engine='openpyxl') as w:
        out2.to_excel(w, index=False, sheet_name='Sheet1')
    out2.to_csv(TABLE_OUT_CSV, index=False, encoding='utf-8-sig')

    print('rows:', len(out2))
    print('dist non-null:', out2['dist_km'].notna().sum())
    print('dist min/max:', float(out2['dist_km'].min()), float(out2['dist_km'].max()))
    print('saved:', TABLE_OUT_XLSX)
    print('saved:', TABLE_OUT_CSV)


if __name__ == '__main__':
    main()
