from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle

mpl.rcParams["font.family"] = "Hiragino Sans"
mpl.rcParams["axes.unicode_minus"] = False

INPUT_XLSX = Path("/Users/itotsubasa/Downloads/jadecom/20260319MTG修正後/都祁診療所周辺の町丁目_各医療施設利用数_30km_最新KLA.xlsx")
OUT_DIR = Path("/Users/itotsubasa/Downloads/jadecom/20260319MTG修正後")
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_TOP3_PNG = OUT_DIR / "town_med_matrix_top3.png"
OUT_TOP3_CSV = OUT_DIR / "town_med_matrix_top3_only.csv"
OUT_TOP10_PNG = OUT_DIR / "town_med_heatmap_top10.png"
OUT_TOP10_CSV = OUT_DIR / "town_med_matrix_top10.csv"
OUT_RANK_CSV = OUT_DIR / "facility_rank_summary.csv"

TARGET_FACILITY_KEYWORD = "奈良市都祁診療所"
TOP_K_FACILITIES = 10
TOP_TOWNS = 60
ID_COLS = [
    "CITY_NAME_from_master",
    "S_NAME_from_master",
    "town_name_show",
    "dist_km",
    "LON",
    "LAT",
    "total_87",
]


def plot_top3_matrix(df: pd.DataFrame, facility_cols: list[str], towns: list[str]) -> None:
    values = df[facility_cols].to_numpy(dtype=float)
    top3_mask = np.zeros_like(values, dtype=bool)

    for i in range(values.shape[0]):
        row = values[i]
        pos_idx = np.where(row > 0)[0]
        if len(pos_idx) == 0:
            continue
        sorted_idx = pos_idx[np.argsort(row[pos_idx])[::-1]]
        top3_mask[i, sorted_idx[:3]] = True

    values_top3 = np.where(top3_mask, values, 0)
    out_df = pd.concat([df[ID_COLS], pd.DataFrame(values_top3, columns=facility_cols)], axis=1)
    out_df.to_csv(OUT_TOP3_CSV, index=False, encoding="utf-8-sig")

    freq = top3_mask.sum(axis=0)
    rank_idx = np.argsort(freq)[::-1]
    top_ranked_cols = [facility_cols[i] for i in rank_idx[:3]]
    top1, top2, top3 = (top_ranked_cols + [None, None, None])[:3]

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
    already_colored = (rgb[:, :, 0] != 1.0) | (rgb[:, :, 1] != 1.0) | (rgb[:, :, 2] != 1.0)
    rgb[other_mask & (~already_colored), :] = np.array([0.92, 0.92, 0.92])

    fig_w = min(0.28 * n_cols + 6, 50)
    fig_h = min(0.22 * n_rows + 4, 60)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.imshow(rgb, aspect="auto")
    ax.set_xticks(np.arange(n_cols))
    ax.set_xticklabels(facility_cols, rotation=90, fontsize=8)
    ax.set_yticks(np.arange(n_rows))
    ax.set_yticklabels(towns, fontsize=8)
    ax.set_title("町丁目 × 医療機関 マトリクス（各町丁目の上位3のみ）", fontsize=14)

    for i in range(n_rows):
        for j in range(n_cols):
            v = values_top3[i, j]
            if v > 0:
                ax.text(j, i, f"{int(v)}", ha="center", va="center", fontsize=6)

    ax.set_xticks(np.arange(-0.5, n_cols, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, n_rows, 1), minor=True)
    ax.grid(which="minor", color="black", linestyle="-", linewidth=0.15)
    ax.tick_params(which="minor", bottom=False, left=False)

    plt.tight_layout()
    plt.savefig(OUT_TOP3_PNG, dpi=300)
    plt.close()


def plot_top10_heatmap(df: pd.DataFrame, facility_cols: list[str], towns: list[str]) -> None:
    facility_total = df[facility_cols].sum(axis=0).sort_values(ascending=False)
    top_facilities = facility_total.head(TOP_K_FACILITIES).index.tolist()

    values_all = df[facility_cols].to_numpy(dtype=float)
    top3_mask = np.zeros_like(values_all, dtype=bool)
    for i in range(values_all.shape[0]):
        row = values_all[i]
        pos_idx = np.where(row > 0)[0]
        if len(pos_idx) == 0:
            continue
        sorted_idx = pos_idx[np.argsort(row[pos_idx])[::-1]]
        top3_mask[i, sorted_idx[:3]] = True
    freq_top3 = pd.Series(top3_mask.sum(axis=0), index=facility_cols).sort_values(ascending=False)

    rank_df = pd.DataFrame(
        {
            "施設名": facility_total.index,
            "患者数合計": facility_total.values,
            "上位3頻出回数": freq_top3.reindex(facility_total.index).values,
        }
    )
    rank_df.to_csv(OUT_RANK_CSV, index=False, encoding="utf-8-sig")

    mat = df[top_facilities].to_numpy(dtype=float)
    mat_disp = np.where(mat >= 0, mat, 0)
    out_matrix_df = pd.concat([df[ID_COLS], pd.DataFrame(mat_disp, columns=top_facilities)], axis=1)
    out_matrix_df.to_csv(OUT_TOP10_CSV, index=False, encoding="utf-8-sig")

    mat_for_color = np.log1p(mat_disp)
    fig_w = min(0.8 * TOP_K_FACILITIES + 6, 20)
    fig_h = min(0.22 * len(towns) + 4, 60)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    im = ax.imshow(mat_for_color, aspect="auto")
    ax.set_xticks(np.arange(len(top_facilities)))
    ax.set_xticklabels(top_facilities, rotation=90, fontsize=10)
    ax.set_yticks(np.arange(len(towns)))
    ax.set_yticklabels(towns, fontsize=8)
    ax.set_title(f"都祁診療所周辺60町丁目 × 医療機関（患者数ヒートマップ：上位{TOP_K_FACILITIES}）", fontsize=14)

    for i in range(mat_disp.shape[0]):
        for j in range(mat_disp.shape[1]):
            v = mat_disp[i, j]
            if v > 0:
                ax.text(j, i, f"{int(v)}", ha="center", va="center", fontsize=6)

    ax.set_xticks(np.arange(-0.5, len(top_facilities), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(towns), 1), minor=True)
    ax.grid(which="minor", linewidth=0.18)
    ax.tick_params(which="minor", bottom=False, left=False)

    target_cols = [i for i, name in enumerate(top_facilities) if TARGET_FACILITY_KEYWORD in name]
    for j in target_cols:
        rect = Rectangle((j - 0.5, -0.5), 1, len(towns), fill=False, linewidth=2.5)
        ax.add_patch(rect)

    cbar = plt.colorbar(im, ax=ax, fraction=0.02, pad=0.02)
    cbar.set_label("log(1 + 人数)", fontsize=10)
    plt.tight_layout()
    plt.savefig(OUT_TOP10_PNG, dpi=300)
    plt.close()


def main() -> None:
    df = pd.read_excel(INPUT_XLSX)
    df.columns = [str(c).strip() for c in df.columns]
    id_cols_existing = [c for c in ID_COLS if c in df.columns]
    facility_cols = [c for c in df.columns if c not in id_cols_existing]

    for c in facility_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    if "dist_km" in df.columns:
        df["dist_km"] = pd.to_numeric(df["dist_km"], errors="coerce")
        df = df.sort_values(["dist_km", "CITY_NAME_from_master", "S_NAME_from_master"], na_position="last").reset_index(drop=True)
    df = df.head(TOP_TOWNS).copy()

    towns = []
    for _, r in df.iterrows():
        label = f"{str(r.get('town_name_show', r.get('S_NAME_from_master', '')))}"
        if pd.notna(r.get("dist_km", np.nan)):
            label = f"{label} ({float(r['dist_km']):.1f}km)"
        towns.append(label)

    plot_top3_matrix(df, facility_cols, towns)
    plot_top10_heatmap(df, facility_cols, towns)

    print("saved:", OUT_TOP3_PNG)
    print("saved:", OUT_TOP3_CSV)
    print("saved:", OUT_TOP10_PNG)
    print("saved:", OUT_TOP10_CSV)
    print("saved:", OUT_RANK_CSV)


if __name__ == "__main__":
    main()
