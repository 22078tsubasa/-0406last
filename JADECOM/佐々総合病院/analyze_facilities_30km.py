import math
from pathlib import Path

import pandas as pd

INPUT_CSV = Path('/Users/itotsubasa/Downloads/医療介護情報局 医療機関情報.csv')
OUT_DIR = Path('/Users/itotsubasa/IdeaProjects/pythoN/JADECOM/佐々総合病院')
OUT_DIR.mkdir(parents=True, exist_ok=True)

TARGET_KEY = '佐々総合病院'
RADIUS_KM = 30.0


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0088
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def main():
    df = pd.read_csv(INPUT_CSV, encoding='cp932')
    need = ['医療機関名', '都道府県名', '市区町村名', '所在地', '緯度', '経度', '保険区分', '診療科目']
    for c in need:
        if c not in df.columns:
            raise KeyError(f'必要列がありません: {c}')

    df['緯度'] = pd.to_numeric(df['緯度'], errors='coerce')
    df['経度'] = pd.to_numeric(df['経度'], errors='coerce')
    df = df.dropna(subset=['緯度', '経度']).copy()

    target = df[df['医療機関名'].astype(str).str.contains(TARGET_KEY, na=False)].copy()
    if target.empty:
        raise ValueError(f'対象病院が見つかりません: {TARGET_KEY}')

    # 同名が複数でも最初を採用
    t = target.iloc[0]
    t_lat, t_lon = float(t['緯度']), float(t['経度'])

    df['distance_km'] = [haversine_km(t_lat, t_lon, la, lo) for la, lo in zip(df['緯度'], df['経度'])]
    within = df[df['distance_km'] <= RADIUS_KM].copy()
    within = within.sort_values('distance_km').reset_index(drop=True)

    # 保存
    out_cols = ['医療機関名', '保険区分', '都道府県名', '市区町村名', '所在地', '緯度', '経度', 'distance_km', '診療科目']
    out_csv = OUT_DIR / '佐々総合病院_30km圏_医療機関一覧.csv'
    within[out_cols].to_csv(out_csv, index=False, encoding='utf-8-sig')

    summary_pref = within['都道府県名'].value_counts().rename_axis('都道府県名').reset_index(name='件数')
    summary_pref.to_csv(OUT_DIR / '佐々総合病院_30km圏_都道府県別件数.csv', index=False, encoding='utf-8-sig')

    summary_type = within['保険区分'].fillna('不明').value_counts().rename_axis('保険区分').reset_index(name='件数')
    summary_type.to_csv(OUT_DIR / '佐々総合病院_30km圏_保険区分別件数.csv', index=False, encoding='utf-8-sig')

    txt = OUT_DIR / '佐々総合病院_30km圏_サマリー.txt'
    with txt.open('w', encoding='utf-8') as f:
        f.write(f'対象病院: {t["医療機関名"]}\n')
        f.write(f'所在地: {t["所在地"]}\n')
        f.write(f'座標: {t_lat}, {t_lon}\n')
        f.write(f'半径: {RADIUS_KM}km\n\n')
        f.write(f'30km圏内医療機関数: {len(within)}\n\n')
        f.write('都道府県別件数\n')
        f.write(summary_pref.to_string(index=False))
        f.write('\n\n保険区分別件数\n')
        f.write(summary_type.to_string(index=False))

    print('target:', t['医療機関名'])
    print('coord:', t_lat, t_lon)
    print('within_30km:', len(within))
    print('saved:', out_csv)


if __name__ == '__main__':
    main()
