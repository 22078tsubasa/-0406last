from __future__ import annotations

import re
import zipfile
from collections import Counter
from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd

ZIP_DIR = Path('/Users/itotsubasa/Library/CloudStorage/OneDrive-SIT/L3S（社会システム科学研究室） - ドキュメント/0共-地域医療振興協会/2025年度/佐々総合病院_競合分析_KLA集計結果/佐々総合_競合_KLA')
REF_TOKYO_AGE = Path('/Users/itotsubasa/Downloads/jadecom/20260212/年齢別医療受容者数/main_with_age_tokyo_h03_13_main_with_age.csv')
OUT_DIR = Path('/Users/itotsubasa/IdeaProjects/pythoN/JADECOM/佐々総合病院/競合分析')
OUT_XLSX = OUT_DIR / '佐々総合病院周辺の町丁目_各医療施設利用数_KLA統合.xlsx'
OUT_CSV = OUT_DIR / '佐々総合病院周辺の町丁目_各医療施設利用数_KLA統合.csv'
OUT_UNMATCHED = OUT_DIR / '佐々総合病院周辺の町丁目_city_sname_unmatched.csv'

SUFFIX = '_国内居住者・来訪者居住地分析_20240401_20250331'


def normalize_text(s: str) -> str:
    return str(s).replace('　', '').replace(' ', '').strip()


def parse_city_sname_from_town(town: str) -> tuple[str, str]:
    s = normalize_text(town)
    m = re.match(r'^(.+?[市区町村])(.*)$', s)
    if m:
        return m.group(1), m.group(2)
    return '', s


def read_towns_from_zip(zp: Path) -> pd.DataFrame:
    with zipfile.ZipFile(zp) as zf:
        town_members = [n for n in zf.namelist() if '3_Towns' in Path(n).name]
        if not town_members:
            return pd.DataFrame(columns=['コード', '町丁目名', '人数'])
        b = zf.read(town_members[0])
    df = pd.read_csv(BytesIO(b), encoding='cp932')
    need = [c for c in ['コード', '町丁目名', '人数'] if c in df.columns]
    if len(need) < 3:
        return pd.DataFrame(columns=['コード', '町丁目名', '人数'])
    out = df[['コード', '町丁目名', '人数']].copy()
    out['コード'] = out['コード'].astype(str)
    out['町丁目名'] = out['町丁目名'].astype(str)
    out['人数'] = pd.to_numeric(out['人数'], errors='coerce').fillna(0)
    return out


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    zips = sorted(ZIP_DIR.glob('*.zip'))
    if not zips:
        raise FileNotFoundError(f'zip not found: {ZIP_DIR}')

    base: pd.DataFrame | None = None
    used_names = set()
    facility_count = 0

    for zp in zips:
        facility = zp.stem
        if facility.endswith(SUFFIX):
            facility = facility[: -len(SUFFIX)]
        facility = facility.strip()
        if facility in used_names:
            i = 2
            name = f'{facility}_{i}'
            while name in used_names:
                i += 1
                name = f'{facility}_{i}'
            facility = name
        used_names.add(facility)

        df_t = read_towns_from_zip(zp)
        if df_t.empty:
            continue
        df_t = df_t.groupby(['コード', '町丁目名'], as_index=False)['人数'].sum().rename(columns={'人数': facility})

        if base is None:
            base = df_t
        else:
            base = base.merge(df_t, on=['コード', '町丁目名'], how='outer')
        facility_count += 1

    if base is None:
        raise RuntimeError('有効な3_Townsデータがありませんでした')

    base = base.fillna(0)

    # 町丁目 -> CITY_NAME/S_NAME を補完（東京年齢別ファイルを優先マッチ）
    ref = pd.read_csv(REF_TOKYO_AGE)
    ref['key'] = (ref['CITY_NAME'].fillna('').astype(str) + ref['S_NAME'].fillna('').astype(str)).map(normalize_text)
    key_to_city = dict(zip(ref['key'], ref['CITY_NAME']))
    key_to_sname = dict(zip(ref['key'], ref['S_NAME']))

    base['town_name_show'] = base['町丁目名'].astype(str)
    key = base['town_name_show'].map(normalize_text)

    base['CITY_NAME_from_master'] = key.map(key_to_city)
    base['S_NAME_from_master'] = key.map(key_to_sname)

    # マッチできないものは文字列分解で補完
    miss = base['CITY_NAME_from_master'].isna() | base['S_NAME_from_master'].isna()
    parsed = base.loc[miss, 'town_name_show'].map(parse_city_sname_from_town)
    base.loc[miss, 'CITY_NAME_from_master'] = [x[0] for x in parsed]
    base.loc[miss, 'S_NAME_from_master'] = [x[1] for x in parsed]

    # 先頭メタ列を揃える（都祁テーブル互換に寄せる）
    facility_cols = [c for c in base.columns if c not in ['コード', '町丁目名', 'town_name_show', 'CITY_NAME_from_master', 'S_NAME_from_master']]

    out = base[['town_name_show', 'CITY_NAME_from_master', 'S_NAME_from_master'] + facility_cols].copy()
    out = out.rename(columns={'town_name_show': 'town'})
    out['town_norm'] = out['town'].map(normalize_text)
    out['total_87'] = out[facility_cols].sum(axis=1)

    # 列順（都祁形式に近づける）
    out = out[['town', 'town_norm', 'CITY_NAME_from_master', 'S_NAME_from_master', 'total_87'] + facility_cols]

    with pd.ExcelWriter(OUT_XLSX, engine='openpyxl') as w:
        out.to_excel(w, sheet_name='Sheet1', index=False)

    out.to_csv(OUT_CSV, index=False, encoding='utf-8-sig')

    unmatched = out[(out['CITY_NAME_from_master'].fillna('') == '') | (out['S_NAME_from_master'].fillna('') == '')][['town', 'CITY_NAME_from_master', 'S_NAME_from_master']]
    unmatched.to_csv(OUT_UNMATCHED, index=False, encoding='utf-8-sig')

    print(f'zip files: {len(zips)}')
    print(f'facility columns: {facility_count}')
    print(f'towns rows: {len(out)}')
    print(f'matched city/sname: {len(out)-len(unmatched)} / {len(out)}')
    print(f'saved: {OUT_XLSX}')
    print(f'saved: {OUT_CSV}')
    print(f'saved: {OUT_UNMATCHED}')


if __name__ == '__main__':
    main()
