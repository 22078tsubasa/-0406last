from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd


IN_CSV = Path('/Users/itotsubasa/Downloads/h03_27.csv')
OUT_DIR = Path('/Users/itotsubasa/IdeaProjects/pythoN/JADECOM/大阪年齢別需要者数')
OUT_XLSX = OUT_DIR / 'main_with_age_osaka_h03_27.xlsx'
OUT_MAIN_CSV = OUT_DIR / 'main_with_age_osaka_h03_27_main_with_age.csv'
OUT_UNMATCHED_CSV = OUT_DIR / 'main_with_age_osaka_h03_27_unmatched.csv'

AGE_COLS = [
    '0～4歳', '5～9歳', '10～14歳', '15～19歳', '20～24歳', '25～29歳', '30～34歳', '35～39歳',
    '40～44歳', '45～49歳', '50～54歳', '55～59歳', '60～64歳', '65～69歳', '70～74歳', '75～79歳',
    '80～84歳', '85～89歳', '90～94歳', '95～99歳', '100歳以上'
]

COEFFS = {
    '0～4歳': 0.0379,
    '5～9歳': 0.05196,
    '10～14歳': 0.0368,
    '15～19歳': 0.02459,
    '20～24歳': 0.02367,
    '25～29歳': 0.02837,
    '30～34歳': 0.03201,
    '35～39歳': 0.03353,
    '40～44歳': 0.03501,
    '45～49歳': 0.03912,
    '50～54歳': 0.04395,
    '55～59歳': 0.05751,
    '60～64歳': 0.0632,
    '65～69歳': 0.08101,
    '70～74歳': 0.09395,
    '75～79歳': 0.11197,
    '80～84歳': 0.1201,
    '85～89歳': 0.11483,
    '90～94歳': 0.10021,
    '95～99歳': 0.10021,
    '100歳以上': 0.10021,
}


def to_num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.replace({'X': np.nan, '-': np.nan}), errors='coerce')


def zfill_series(s: pd.Series, width: int) -> pd.Series:
    return s.fillna('').astype(str).str.replace(r'\.0$', '', regex=True).str.zfill(width)


def round_half_up(s: pd.Series) -> pd.Series:
    x = s.astype(float)
    return np.floor(x + 0.5)


def cat4(pref: pd.Series, city: pd.Series, oaza: pd.Series, chome: pd.Series) -> pd.Series:
    a = pref.fillna('').astype(str).str.strip()
    b = city.fillna('').astype(str).str.strip()
    c = oaza.fillna('').astype(str).str.strip()
    d = chome.fillna('').astype(str).str.strip()
    return (a + b + c + d).str.replace('nan', '', regex=False)


def main() -> None:
    df = pd.read_csv(IN_CSV, encoding='cp932', header=4)

    rename_map = {
        'Unnamed: 8': '都道府県名',
        'Unnamed: 9': '市区町村名',
        'Unnamed: 10': '大字・町名',
        'Unnamed: 11': '字・丁目名',
    }
    df = df.rename(columns=rename_map)

    use = df[(df['都道府県名'] == '大阪府') & (df['男女'] == '総数') & (df['地域階層レベル'] == 4)].copy()

    use['CITY_CODE'] = zfill_series(use['市区町村コード'], 5)
    use['TOWN_CODE'] = zfill_series(use['町丁字コード'], 6)
    use['TOWN_CODE_11'] = use['CITY_CODE'] + use['TOWN_CODE']
    use['CITY_NAME'] = use['市区町村名']
    use['S_NAME'] = (
        use['大字・町名'].fillna('').astype(str).str.strip() +
        use['字・丁目名'].fillna('').astype(str).str.strip()
    ).replace('', np.nan)
    use['TOWN_NAME_4COL'] = cat4(use['都道府県名'], use['市区町村名'], use['大字・町名'], use['字・丁目名'])
    use['POP'] = to_num(use['総数'])
    use['__srcfile'] = IN_CSV.name

    out = use[['CITY_CODE', 'TOWN_CODE', 'TOWN_CODE_11', 'CITY_NAME', 'S_NAME', 'TOWN_NAME_4COL', 'POP', '__srcfile']].copy()

    # unmatched は 0 扱いにするため、年齢列の欠損を 0 補完
    age_raw = {}
    for c in AGE_COLS:
        age_raw[c] = to_num(use[c])
        out[c] = age_raw[c].fillna(0)

    raw_cols = []
    rnd_cols = []
    for c in AGE_COLS:
        rc = f'{c}_受容者(小数)'
        kc = f'{c}_受容者(四捨五入)'
        out[rc] = out[c] * COEFFS[c]
        out[kc] = round_half_up(out[rc])
        raw_cols.append(rc)
        rnd_cols.append(kc)

    out['SUM_受容者(小数)'] = out[raw_cols].sum(axis=1)
    out['SUM_受容者(四捨五入)'] = out[rnd_cols].sum(axis=1)

    # 監査用: 元データ上で年齢列が全欠損だった町丁目（計算は0で実施）
    raw_all_nan = pd.DataFrame(age_raw).isna().all(axis=1)
    unmatched = out.loc[raw_all_nan, ['CITY_CODE', 'TOWN_CODE', 'TOWN_CODE_11', 'CITY_NAME', 'S_NAME', 'TOWN_NAME_4COL', 'POP', '__srcfile']].copy()

    # 後続処理用の共通列（座標はマスタ結合で追記予定）
    out['CITY_NAME_from_master'] = out['CITY_NAME']
    out['S_NAME_from_master'] = out['S_NAME']
    out['town_name_show'] = out['S_NAME']
    out['LON'] = np.nan
    out['LAT'] = np.nan
    out['dist_km'] = np.nan

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(OUT_XLSX, engine='openpyxl') as writer:
        out.to_excel(writer, sheet_name='main_with_age', index=False)
        unmatched.to_excel(writer, sheet_name='unmatched', index=False)

    out.to_csv(OUT_MAIN_CSV, index=False, encoding='utf-8-sig')
    unmatched.to_csv(OUT_UNMATCHED_CSV, index=False, encoding='utf-8-sig')

    print(f'input rows: {len(df)}')
    print(f'osaka town rows(level=4): {len(out)}')
    print(f'unmatched rows: {len(unmatched)}')
    print(f'saved: {OUT_XLSX}')
    print(f'saved: {OUT_MAIN_CSV}')
    print(f'saved: {OUT_UNMATCHED_CSV}')


if __name__ == '__main__':
    main()
