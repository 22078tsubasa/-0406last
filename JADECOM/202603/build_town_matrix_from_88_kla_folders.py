from __future__ import annotations

import math
import re
import unicodedata
from pathlib import Path

import pandas as pd

SRC_DIR = Path('/Users/itotsubasa/Library/CloudStorage/OneDrive-SIT/L3S（社会システム科学研究室） - ドキュメント/0共-地域医療振興協会/2025年度/88医療機関のKLA集計結果')
CENTROID_CSV = Path('/Users/itotsubasa/Downloads/jadecom/柘植診療所到達件30分以内超長目/out/重心人口_人口重心付き.csv')
OUT_DIR = Path('/Users/itotsubasa/Downloads/jadecom/20260319MTG修正後')
OUT_CSV = OUT_DIR / '88医療機関_町丁目別患者数マトリクス.csv'
OUT_XLSX = OUT_DIR / '88医療機関_町丁目別患者数マトリクス.xlsx'
OUT_UNMATCHED = OUT_DIR / '88医療機関_町丁目_座標未結合一覧.csv'

# 奈良市都祁診療所（既存分析で使用している起点）
REF_LAT = 34.60399219055155
REF_LON = 135.95722209432466


def ntext(v: str) -> str:
    return unicodedata.normalize('NFKC', str(v)).replace('　', '').replace(' ', '').strip()


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0088
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def parse_city_sname(full_town: str) -> tuple[str, str]:
    s = ntext(full_town)
    m = re.match(r'^(.+?[市区町村])(.*)$', s)
    if m:
        return m.group(1), m.group(2)
    return '', s


def facility_name_from_dirname(name: str, used: set[str]) -> str:
    s = unicodedata.normalize('NFKC', name)
    for token in ['_国内居住者・来訪者居住地分析', '_国内居住者・来訪者居住地']:
        if token in s:
            s = s.split(token)[0]
            break
    s = re.sub(r'_建物ポリゴン$', '', s)
    s = re.sub(r'_\d+$', '', s)
    s = s.strip('_ ').strip()
    if s not in used:
        used.add(s)
        return s
    i = 2
    while f'{s}_{i}' in used:
        i += 1
    s2 = f'{s}_{i}'
    used.add(s2)
    return s2


def read_towns_csv(p: Path) -> pd.DataFrame:
    df = pd.read_csv(p, encoding='cp932')
    need = {'コード', '町丁目名', '人数'}
    if not need.issubset(set(df.columns)):
        return pd.DataFrame(columns=['コード', '町丁目名', '人数'])
    out = df[['コード', '町丁目名', '人数']].copy()
    out['コード'] = out['コード'].astype(str)
    out['町丁目名'] = out['町丁目名'].astype(str)
    out['人数'] = pd.to_numeric(out['人数'], errors='coerce').fillna(0)
    return out


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    dirs = sorted([d for d in SRC_DIR.iterdir() if d.is_dir()])
    if not dirs:
        raise FileNotFoundError(f'施設フォルダが見つかりません: {SRC_DIR}')

    used_names: set[str] = set()
    base: pd.DataFrame | None = None
    facility_cols: list[str] = []

    for d in dirs:
        town_files = sorted(d.glob('3_Towns_*.csv'))
        if not town_files:
            continue
        fcol = facility_name_from_dirname(d.name, used_names)

        df_t = read_towns_csv(town_files[0])
        if df_t.empty:
            continue

        df_t = df_t.groupby(['コード', '町丁目名'], as_index=False)['人数'].sum().rename(columns={'人数': fcol})
        facility_cols.append(fcol)

        if base is None:
            base = df_t
        else:
            base = base.merge(df_t, on=['コード', '町丁目名'], how='outer')

    if base is None:
        raise RuntimeError('有効な3_Townsデータを読み込めませんでした')

    base = base.fillna(0)

    city_sname = base['町丁目名'].map(parse_city_sname)
    base['CITY_NAME_from_master'] = [x[0] for x in city_sname]
    base['S_NAME_from_master'] = [x[1] for x in city_sname]
    base['town_name_show'] = base['S_NAME_from_master']

    cent = pd.read_csv(CENTROID_CSV)
    cent = cent.rename(columns={'CITY_NAME': 'CITY_NAME_cent', 'TOWN_NAME': 'S_NAME_cent'})
    cent['key'] = (cent['CITY_NAME_cent'].astype(str) + cent['S_NAME_cent'].astype(str)).map(ntext)

    base['key'] = (base['CITY_NAME_from_master'].astype(str) + base['S_NAME_from_master'].astype(str)).map(ntext)
    base = base.merge(cent[['key', 'LON', 'LAT']], on='key', how='left')

    base['dist_km'] = base.apply(
        lambda r: haversine_km(REF_LAT, REF_LON, float(r['LAT']), float(r['LON'])) if pd.notna(r['LAT']) and pd.notna(r['LON']) else float('nan'),
        axis=1,
    )

    base[facility_cols] = base[facility_cols].apply(pd.to_numeric, errors='coerce').fillna(0)
    base['total_87'] = base[facility_cols].sum(axis=1)

    out = base[['CITY_NAME_from_master', 'S_NAME_from_master', 'town_name_show', 'dist_km', 'LON', 'LAT'] + facility_cols + ['total_87']].copy()
    out = out.sort_values(['dist_km', 'CITY_NAME_from_master', 'S_NAME_from_master'], na_position='last').reset_index(drop=True)

    out.to_csv(OUT_CSV, index=False, encoding='utf-8-sig')
    with pd.ExcelWriter(OUT_XLSX, engine='openpyxl') as w:
        out.to_excel(w, index=False, sheet_name='Sheet1')

    unmatched = out[out['LON'].isna() | out['LAT'].isna()][['CITY_NAME_from_master', 'S_NAME_from_master', 'town_name_show']].copy()
    unmatched.to_csv(OUT_UNMATCHED, index=False, encoding='utf-8-sig')

    print('facility columns:', len(facility_cols))
    print('town rows:', len(out))
    print('geo matched:', len(out) - len(unmatched), '/', len(out))
    print('saved:', OUT_CSV)
    print('saved:', OUT_XLSX)
    print('saved:', OUT_UNMATCHED)


if __name__ == '__main__':
    main()
