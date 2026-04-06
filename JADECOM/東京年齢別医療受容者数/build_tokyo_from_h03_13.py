from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd


IN_CSV = Path('/Users/itotsubasa/Downloads/h03_13.csv')
OUT_XLSX = Path('/Users/itotsubasa/Downloads/jadecom/20260212/年齢別医療受容者数/main_with_age_tokyo_h03_13.xlsx')
OUT_MAIN_CSV = OUT_XLSX.with_name(OUT_XLSX.stem + '_main_with_age.csv')
OUT_UNMATCHED_CSV = OUT_XLSX.with_name(OUT_XLSX.stem + '_unmatched.csv')

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
    # 国勢調査の秘匿記号 X / - を欠損にする
    return pd.to_numeric(s.replace({'X': np.nan, '-': np.nan}), errors='coerce')


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

    # 列名整理（このCSV特有の Unnamed を意味名に置換）
    rename_map = {
        'Unnamed: 8': '都道府県名',
        'Unnamed: 9': '市区町村名',
        'Unnamed: 10': '大字・町名',
        'Unnamed: 11': '字・丁目名',
    }
    df = df.rename(columns=rename_map)

    # 東京都 + 男女総数 + 町丁目レベル（4）
    use = df[(df['都道府県名'] == '東京都') & (df['男女'] == '総数') & (df['地域階層レベル'] == 4)].copy()

    use['CITY_NAME'] = use['市区町村名']
    use['S_NAME'] = (
        use['大字・町名'].fillna('').astype(str).str.strip() +
        use['字・丁目名'].fillna('').astype(str).str.strip()
    ).replace('', np.nan)
    use['TOWN_NAME_4COL'] = cat4(use['都道府県名'], use['市区町村名'], use['大字・町名'], use['字・丁目名'])
    use['POP'] = to_num(use['総数'])
    use['__srcfile'] = IN_CSV.name

    out = use[['CITY_NAME', 'S_NAME', 'TOWN_NAME_4COL', 'POP', '__srcfile']].copy()

    # 年齢別人口
    for c in AGE_COLS:
        out[c] = to_num(use[c])

    # 受容者数: 小数 / 四捨五入
    raw_cols = []
    rnd_cols = []
    for c in AGE_COLS:
        rc = f'{c}_受容者(小数)'
        kc = f'{c}_受容者(四捨五入)'
        out[rc] = out[c] * COEFFS[c]
        out[kc] = round_half_up(out[rc])
        out.loc[out[c].isna(), [rc, kc]] = np.nan
        raw_cols.append(rc)
        rnd_cols.append(kc)

    out['SUM_受容者(小数)'] = out[raw_cols].sum(axis=1, min_count=1)
    out['SUM_受容者(四捨五入)'] = out[rnd_cols].sum(axis=1, min_count=1)

    unmatched = out[out[AGE_COLS].isna().all(axis=1)][['CITY_NAME', 'S_NAME', 'TOWN_NAME_4COL', 'POP', '__srcfile']].copy()

    OUT_XLSX.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(OUT_XLSX, engine='openpyxl') as writer:
        out.to_excel(writer, sheet_name='main_with_age', index=False)
        unmatched.to_excel(writer, sheet_name='unmatched', index=False)

    out.to_csv(OUT_MAIN_CSV, index=False, encoding='utf-8-sig')
    unmatched.to_csv(OUT_UNMATCHED_CSV, index=False, encoding='utf-8-sig')

    print(f'input rows: {len(df)}')
    print(f'tokyo town rows(level=4): {len(out)}')
    print(f'unmatched rows: {len(unmatched)}')
    print(f'saved: {OUT_XLSX}')
    print(f'saved: {OUT_MAIN_CSV}')
    print(f'saved: {OUT_UNMATCHED_CSV}')


if __name__ == '__main__':
    main()
