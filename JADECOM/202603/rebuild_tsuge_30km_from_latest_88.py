from __future__ import annotations

import math
import re
import unicodedata
from pathlib import Path

import pandas as pd

SRC_DIR = Path('/Users/itotsubasa/Library/CloudStorage/OneDrive-SIT/L3S（社会システム科学研究室） - ドキュメント/0共-地域医療振興協会/2025年度/88医療機関のKLA集計結果')
TEMPLATE_XLSX = Path('/Users/itotsubasa/Downloads/jadecom/202603:西村先生MTG/都祁診療所周辺の町丁目_各医療施設利用数_30km.xlsx')
CENTROID_CSV = Path('/Users/itotsubasa/Downloads/jadecom/柘植診療所到達件30分以内超長目/out/重心人口_人口重心付き.csv')
OUT_DIR = Path('/Users/itotsubasa/Downloads/jadecom/20260319MTG修正後')
OUT_XLSX = OUT_DIR / '都祁診療所周辺の町丁目_各医療施設利用数_30km_最新KLA.xlsx'
OUT_CSV = OUT_DIR / '都祁診療所周辺の町丁目_各医療施設利用数_30km_最新KLA.csv'
OUT_LOG = OUT_DIR / '都祁30km_最新KLA_施設名対応ログ.csv'

REF_LAT = 34.60399219055155
REF_LON = 135.95722209432466

META_COLS = ['CITY_NAME_from_master', 'S_NAME_from_master', 'town_name_show', 'dist_km', 'LON', 'LAT']


def ntext(v: str) -> str:
    return unicodedata.normalize('NFKC', str(v)).replace('　', '').replace(' ', '').strip()


def normalize_facility_name(v: str) -> str:
    s = ntext(v)
    s = s.replace('（', '(').replace('）', ')')
    s = s.replace('旧ひまわりクリニック_奈良東病院', '旧ひまわりクリニック')
    return s


def parse_city_sname(full_town: str) -> tuple[str, str]:
    s = ntext(full_town)
    m = re.match(r'^(.+?[市区町村])(.*)$', s)
    if m:
        return m.group(1), m.group(2)
    return '', s


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0088
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def facility_name_from_dirname(name: str) -> str:
    s = unicodedata.normalize('NFKC', name)
    for token in ['_国内居住者・来訪者居住地分析', '_国内居住者・来訪者居住地']:
        if token in s:
            s = s.split(token)[0]
            break
    s = re.sub(r'_建物ポリゴン$', '', s)
    s = re.sub(r'_\d+$', '', s)
    s = s.strip('_ ').strip()
    if s.startswith('旧ひまわりクリニック'):
        s = '旧ひまわりクリニック'
    return s


def read_towns_csv(p: Path) -> pd.DataFrame:
    df = pd.read_csv(p, encoding='cp932')
    need = {'町丁目名', '人数'}
    if not need.issubset(df.columns):
        return pd.DataFrame(columns=['CITY_NAME_from_master', 'S_NAME_from_master', '人数'])
    out = df[['町丁目名', '人数']].copy()
    out['人数'] = pd.to_numeric(out['人数'], errors='coerce').fillna(0)
    cs = out['町丁目名'].map(parse_city_sname)
    out['CITY_NAME_from_master'] = [x[0] for x in cs]
    out['S_NAME_from_master'] = [x[1] for x in cs]
    out = out.groupby(['CITY_NAME_from_master', 'S_NAME_from_master'], as_index=False)['人数'].sum()
    return out


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    base = pd.read_excel(TEMPLATE_XLSX)
    facility_cols = [c for c in base.columns if c not in META_COLS + ['total_87']]

    # 人数列をゼロ初期化して、最新KLAから埋め直す
    for c in facility_cols:
        base[c] = 0.0

    base['CITY_NAME_from_master'] = base['CITY_NAME_from_master'].astype(str).str.strip()
    base['S_NAME_from_master'] = base['S_NAME_from_master'].astype(str).str.strip()
    keys = list(zip(base['CITY_NAME_from_master'], base['S_NAME_from_master']))

    norm_to_col = {normalize_facility_name(c): c for c in facility_cols}
    logs = []

    dirs = sorted([d for d in SRC_DIR.iterdir() if d.is_dir()])
    for d in dirs:
        town_files = sorted(d.glob('3_Towns_*.csv'))
        if not town_files:
            logs.append({'folder': d.name, 'parsed_name': '', 'mapped_col': '', 'status': 'skip_no_town_csv'})
            continue

        parsed = facility_name_from_dirname(d.name)
        n = normalize_facility_name(parsed)
        mapped = norm_to_col.get(n, '')
        if not mapped:
            logs.append({'folder': d.name, 'parsed_name': parsed, 'mapped_col': '', 'status': 'unmatched_facility_name'})
            continue

        t = read_towns_csv(town_files[0])
        if t.empty:
            logs.append({'folder': d.name, 'parsed_name': parsed, 'mapped_col': mapped, 'status': 'skip_empty_town'})
            continue

        s = t.set_index(['CITY_NAME_from_master', 'S_NAME_from_master'])['人数']
        add_vals = [float(s.get(k, 0.0)) for k in keys]
        base[mapped] = pd.to_numeric(base[mapped], errors='coerce').fillna(0) + pd.Series(add_vals)
        logs.append({'folder': d.name, 'parsed_name': parsed, 'mapped_col': mapped, 'status': 'ok'})

    # LON/LAT欠損時のみ重心で補完
    cent = pd.read_csv(CENTROID_CSV)
    cent = cent.rename(columns={'CITY_NAME': 'CITY_NAME_cent', 'TOWN_NAME': 'S_NAME_cent'})
    cent['key'] = (cent['CITY_NAME_cent'].astype(str) + cent['S_NAME_cent'].astype(str)).map(ntext)
    cent_map_lon = dict(zip(cent['key'], cent['LON']))
    cent_map_lat = dict(zip(cent['key'], cent['LAT']))

    bkey = (base['CITY_NAME_from_master'].astype(str) + base['S_NAME_from_master'].astype(str)).map(ntext)
    miss_lon = base['LON'].isna()
    miss_lat = base['LAT'].isna()
    base.loc[miss_lon, 'LON'] = bkey[miss_lon].map(cent_map_lon)
    base.loc[miss_lat, 'LAT'] = bkey[miss_lat].map(cent_map_lat)

    # 距離は毎回再計算
    base['dist_km'] = base.apply(
        lambda r: haversine_km(REF_LAT, REF_LON, float(r['LAT']), float(r['LON'])) if pd.notna(r['LAT']) and pd.notna(r['LON']) else float('nan'),
        axis=1,
    )

    base[facility_cols] = base[facility_cols].apply(pd.to_numeric, errors='coerce').fillna(0)
    base['total_87'] = base[facility_cols].sum(axis=1)

    # テンプレート列順を維持
    ordered_cols = META_COLS + facility_cols + ['total_87']
    out = base[ordered_cols].copy()

    out.to_csv(OUT_CSV, index=False, encoding='utf-8-sig')
    with pd.ExcelWriter(OUT_XLSX, engine='openpyxl') as w:
        out.to_excel(w, index=False, sheet_name='Sheet1')

    pd.DataFrame(logs).to_csv(OUT_LOG, index=False, encoding='utf-8-sig')

    ok = sum(1 for r in logs if r['status'] == 'ok')
    ng = sum(1 for r in logs if r['status'] == 'unmatched_facility_name')
    print('rows:', len(out))
    print('facility_cols:', len(facility_cols))
    print('mapped_ok:', ok, 'unmatched_name:', ng)
    print('saved:', OUT_XLSX)
    print('saved:', OUT_CSV)
    print('saved:', OUT_LOG)


if __name__ == '__main__':
    main()
