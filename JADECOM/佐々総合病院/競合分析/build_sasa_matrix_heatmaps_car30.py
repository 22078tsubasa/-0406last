from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle


mpl.rcParams['font.family'] = 'Hiragino Sans'
mpl.rcParams['axes.unicode_minus'] = False

INPUT_XLSX = Path('/Users/itotsubasa/IdeaProjects/pythoN/JADECOM/佐々総合病院/競合分析/佐々総合病院周辺の町丁目_各医療施設利用数_KLA統合_tokyo_car30_match_with_dist.xlsx')
OUT_DIR = Path('/Users/itotsubasa/IdeaProjects/pythoN/JADECOM/佐々総合病院/競合分析')
OUT_DIR.mkdir(parents=True, exist_ok=True)

# output names
OUT_TOP3_PNG = OUT_DIR / 'sasa_car30_town_med_matrix_上位3.png'
OUT_TOP3_CSV = OUT_DIR / 'sasa_car30_town_med_matrix_上位3のみ.csv'
OUT_TOP10_PNG = OUT_DIR / 'sasa_car30_town_med_heatmap_上位10.png'
OUT_TOP10_CSV = OUT_DIR / 'sasa_car30_town_med_matrix_上位10.csv'
OUT_RANK_CSV = OUT_DIR / 'sasa_car30_facility_rank_summary.csv'

TOWN_COL = 'S_NAME_from_master'
ID_COLS = [
    'town', 'town_norm', 'CITY_NAME_from_master', 'S_NAME_from_master', 'LON', 'LAT', 'dist_km', 'total_87'
]
TARGET_FACILITY_KEYWORD = '佐々総合病院'
TOP_K_FACILITIES = 10


def plot_top3_matrix(df: pd.DataFrame, facility_cols: list[str], towns: list[str]) -> None:
    values = df[facility_cols].to_numpy(dtype=float)
    top3_mask = np.zeros_like(values, dtype=bool)

    for i in range(values.shape[0]):
        row = values[i]
        pos_idx = np.where(row > 0)[0]
        if len(pos_idx) == 0:
            continue
        sorted_idx = pos_idx[np.argsort(row[pos_idx])[::-1]]
        keep = sorted_idx[:3]
        top3_mask[i, keep] = True

    values_top3 = np.where(top3_mask, values, 0)

    freq = top3_mask.sum(axis=0)
    rank_idx = np.argsort(freq)[::-1]
    top_ranked_cols = [facility_cols[i] for i in rank_idx[:3]]
    top1, top2, top3 = (top_ranked_cols + [None, None, None])[:3]

    out_df = df[ID_COLS].copy()
    out_matrix = pd.DataFrame(values_top3, columns=facility_cols)
    out_df = pd.concat([out_df, out_matrix], axis=1)
    out_df.to_csv(OUT_TOP3_CSV, index=False, encoding='utf-8-sig')

    n_rows, n_cols = values_top3.shape
    rgb = np.ones((n_rows, n_cols, 3), dtype=float)

    def set_col_color(col_name: str | None, color_rgb: np.ndarray) -> None:
        if col_name is None:
            return
        j = facility_cols.index(col_name)
        mask = values_top3[:, j] > 0
        rgb[mask, j, :] = color_rgb

    set_col_color(top1, np.array([1.00, 0.35, 0.35]))
    set_col_color(top2, np.array([1.00, 0.65, 0.25]))
    set_col_color(top3, np.array([1.00, 0.90, 0.35]))

    other_mask = values_top3 > 0
    already_colored = (
        (rgb[:, :, 0] != 1.0) | (rgb[:, :, 1] != 1.0) | (rgb[:, :, 2] != 1.0)
    )
    fill_mask = other_mask & (~already_colored)
    rgb[fill_mask, :] = np.array([0.92, 0.92, 0.92])

    fig_w = min(0.34 * n_cols + 10, 90)
    fig_h = min(0.22 * n_rows + 8, 200)

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.imshow(rgb, aspect='auto')

    ax.set_xticks(np.arange(n_cols))
    ax.set_xticklabels(facility_cols, rotation=90, fontsize=9)
    ax.set_yticks(np.arange(n_rows))
    y_fs = 8 if n_rows <= 400 else 7
    ax.set_yticklabels(towns, fontsize=y_fs)
    ax.set_title('町丁目 × 医療機関 マトリクス（各町丁目の上位3のみ）', fontsize=14)

    # セル数が多い場合は可読性と速度のため注釈を省略
    if n_rows * n_cols <= 20000:
        for i in range(n_rows):
            for j in range(n_cols):
                v = values_top3[i, j]
                if v > 0:
                    ax.text(j, i, f'{int(v)}', ha='center', va='center', fontsize=5)

    ax.set_xticks(np.arange(-0.5, n_cols, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, n_rows, 1), minor=True)
    ax.grid(which='minor', color='black', linestyle='-', linewidth=0.15)
    ax.tick_params(which='minor', bottom=False, left=False)

    desc = []
    if top1:
        desc.append(f'赤: 上位3に最頻出 1位 = {top1}')
    if top2:
        desc.append(f'橙: 上位3に最頻出 2位 = {top2}')
    if top3:
        desc.append(f'黄: 上位3に最頻出 3位 = {top3}')
    fig.text(0.01, 0.01, '\n'.join(desc), fontsize=9)

    plt.subplots_adjust(left=0.22, right=0.99, bottom=0.22, top=0.95)
    plt.savefig(OUT_TOP3_PNG, dpi=350)
    plt.close()


def plot_top10_heatmap(df: pd.DataFrame, facility_cols_all: list[str], towns: list[str]) -> None:
    facility_total = df[facility_cols_all].sum(axis=0).sort_values(ascending=False)
    top_facilities = facility_total.head(TOP_K_FACILITIES).index.tolist()

    values_all = df[facility_cols_all].to_numpy(dtype=float)
    top3_mask = np.zeros_like(values_all, dtype=bool)
    for i in range(values_all.shape[0]):
        row = values_all[i]
        pos_idx = np.where(row > 0)[0]
        if len(pos_idx) == 0:
            continue
        sorted_idx = pos_idx[np.argsort(row[pos_idx])[::-1]]
        keep = sorted_idx[:3]
        top3_mask[i, keep] = True
    freq_top3 = pd.Series(top3_mask.sum(axis=0), index=facility_cols_all).sort_values(ascending=False)

    rank_df = pd.DataFrame({
        '施設名': facility_total.index,
        '患者数合計': facility_total.values,
        '上位3頻出回数': freq_top3.reindex(facility_total.index).values,
    })
    rank_df.to_csv(OUT_RANK_CSV, index=False, encoding='utf-8-sig')

    mat = df[top_facilities].to_numpy(dtype=float)
    mat_disp = np.where(mat >= 0, mat, 0)

    out_matrix_df = pd.concat([df[ID_COLS], pd.DataFrame(mat_disp, columns=top_facilities)], axis=1)
    out_matrix_df.to_csv(OUT_TOP10_CSV, index=False, encoding='utf-8-sig')

    mat_for_color = np.log1p(mat_disp)

    fig_w = min(1.15 * TOP_K_FACILITIES + 10, 28)
    fig_h = min(0.24 * len(towns) + 8, 220)

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    im = ax.imshow(mat_for_color, aspect='auto')

    ax.set_xticks(np.arange(len(top_facilities)))
    ax.set_xticklabels(top_facilities, rotation=90, fontsize=11)
    ax.set_yticks(np.arange(len(towns)))
    y_fs = 8 if len(towns) <= 400 else 7
    ax.set_yticklabels(towns, fontsize=y_fs)

    ax.set_title(f'佐々総合病院 車30分圏内: 町丁目×医療機関ヒートマップ（上位{TOP_K_FACILITIES}）', fontsize=14)

    if mat_disp.shape[0] * mat_disp.shape[1] <= 12000:
        for i in range(mat_disp.shape[0]):
            for j in range(mat_disp.shape[1]):
                v = mat_disp[i, j]
                if v > 0:
                    ax.text(j, i, f'{int(v)}', ha='center', va='center', fontsize=5)

    ax.set_xticks(np.arange(-0.5, len(top_facilities), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(towns), 1), minor=True)
    ax.grid(which='minor', linewidth=0.18)
    ax.tick_params(which='minor', bottom=False, left=False)

    target_cols = [i for i, name in enumerate(top_facilities) if TARGET_FACILITY_KEYWORD in name]
    for j in target_cols:
        rect = Rectangle((j - 0.5, -0.5), 1, len(towns), fill=False, linewidth=2.5)
        ax.add_patch(rect)

    cbar = plt.colorbar(im, ax=ax, fraction=0.02, pad=0.02)
    cbar.set_label('log(1 + 人数)', fontsize=10)

    note = [
        f'横軸は患者数合計が多い医療機関 上位{TOP_K_FACILITIES}',
        '色は人数（見やすさのため log(1+x) に変換）',
    ]
    if target_cols:
        note.append(f'太枠: {TARGET_FACILITY_KEYWORD} を含む医療機関列')
    fig.text(0.01, 0.01, '\n'.join(note), fontsize=9)

    plt.subplots_adjust(left=0.24, right=0.99, bottom=0.19, top=0.96)
    plt.savefig(OUT_TOP10_PNG, dpi=350)
    plt.close()


def main() -> None:
    df = pd.read_excel(INPUT_XLSX)
    df.columns = [str(c).strip() for c in df.columns]

    if 'dist_km' in df.columns:
        df['dist_km'] = pd.to_numeric(df['dist_km'], errors='coerce')
        df = df.sort_values(['dist_km', 'CITY_NAME_from_master', TOWN_COL], na_position='last').reset_index(drop=True)

    id_cols_existing = [c for c in ID_COLS if c in df.columns]
    facility_cols = [c for c in df.columns if c not in id_cols_existing]

    for c in facility_cols:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    towns = []
    for _, r in df.iterrows():
        label = f"{str(r.get(TOWN_COL,''))}"
        if pd.notna(r.get('dist_km', np.nan)):
            label = f"{label} ({float(r['dist_km']):.1f}km)"
        towns.append(label)

    plot_top3_matrix(df, facility_cols, towns)
    plot_top10_heatmap(df, facility_cols, towns)

    print('saved:', OUT_TOP3_PNG)
    print('saved:', OUT_TOP3_CSV)
    print('saved:', OUT_TOP10_PNG)
    print('saved:', OUT_TOP10_CSV)
    print('saved:', OUT_RANK_CSV)


if __name__ == '__main__':
    main()
