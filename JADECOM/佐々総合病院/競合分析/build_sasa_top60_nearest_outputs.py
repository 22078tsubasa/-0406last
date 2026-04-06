from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager
from matplotlib.patches import Patch, Rectangle
from shapely.geometry import Point

matplotlib.use("Agg")

available_fonts = {f.name for f in font_manager.fontManager.ttflist}
font_candidates = [
    "Hiragino Sans",
    "Hiragino Kaku Gothic ProN",
    "Yu Gothic",
    "MS Gothic",
    "Noto Sans CJK JP",
    "IPAexGothic",
]
selected_font = next((f for f in font_candidates if f in available_fonts), "sans-serif")
plt.rcParams["font.family"] = selected_font
plt.rcParams["axes.unicode_minus"] = False

BASE_DIR = Path("/Users/itotsubasa/IdeaProjects/pythoN/JADECOM/佐々総合病院/競合分析")
MATRIX_CSV = BASE_DIR / "佐々総合病院周辺の町丁目_各医療施設利用数_KLA統合_tokyo_car30_match_with_dist.csv"
SHP_PATH = BASE_DIR / "tokyo_car30_target_towns_from_r2ka13.shp"
DOWNLOAD_OUT_DIR = Path("/Users/itotsubasa/Downloads/jadecom/東京佐々総合病院/競合分析上位60の医療機関")

TOP_FACILITY_NEAREST = 60
TOP_K_HEATMAP = 10
TARGET_FACILITY_KEYWORD = "佐々総合病院"
TOWN_COL = "S_NAME_from_master"
REF_LAT = 35.72977
REF_LON = 139.5388
PARTIAL_MATCH_CITIES: set[str] = set()

ID_COLS = [
    "town",
    "town_norm",
    "CITY_NAME_from_master",
    "S_NAME_from_master",
    "LON",
    "LAT",
    "dist_km",
    "total_87",
]

OUT_TERRITORY_PNG = DOWNLOAD_OUT_DIR / "dominant_territory_sasa_car30_usersTop60_only.png"
OUT_TERRITORY_CSV = DOWNLOAD_OUT_DIR / "dominant_territory_sasa_car30_usersTop60_only_result.csv"
OUT_MATRIX_TOP3_PNG = DOWNLOAD_OUT_DIR / "sasa_car30_usersTop60_town_med_matrix_上位3_町丁目半分.png"
OUT_MATRIX_TOP3_CSV = DOWNLOAD_OUT_DIR / "sasa_car30_usersTop60_town_med_matrix_上位3のみ_町丁目半分.csv"
OUT_HEATMAP_TOP10_PNG = DOWNLOAD_OUT_DIR / "sasa_car30_usersTop60_town_med_heatmap_上位10_町丁目半分.png"
OUT_HEATMAP_TOP10_CSV = DOWNLOAD_OUT_DIR / "sasa_car30_usersTop60_town_med_matrix_上位10_町丁目半分.csv"
OUT_RANK_CSV = DOWNLOAD_OUT_DIR / "sasa_car30_usersTop60_facility_rank_summary.csv"
OUT_SELECTED_FACILITIES_CSV = DOWNLOAD_OUT_DIR / "sasa_car30_usersTop60_selected_facilities.csv"


def normalize_name(s: pd.Series) -> pd.Series:
    s = s.astype(str)
    s = s.str.replace("　", "", regex=False).str.replace(" ", "", regex=False).str.strip()
    s = s.str.replace(r"（.*?）", "", regex=True).str.replace(r"\(.*?\)", "", regex=True)
    s = s.str.replace("大字", "", regex=False)
    return s


def strip_yamabe_gun_only(s: pd.Series) -> pd.Series:
    s = s.astype(str)
    mask = s.str.contains("山辺郡", na=False) | s.str.contains("山辺群", na=False)
    s.loc[mask] = s.loc[mask].str.replace("山辺郡", "", regex=False).str.replace("山辺群", "", regex=False)
    return s


def choose_top60_by_total_users(df: pd.DataFrame, facility_cols: list[str]) -> list[str]:
    facility_total = df[facility_cols].sum(axis=0).sort_values(ascending=False)
    selected = facility_total.head(TOP_FACILITY_NEAREST).index.tolist()
    out = pd.DataFrame(
        {
            "rank": np.arange(1, len(selected) + 1),
            "施設名_実データ列": selected,
            "利用者数合計": facility_total.loc[selected].values,
        }
    )
    out.to_csv(OUT_SELECTED_FACILITIES_CSV, index=False, encoding="utf-8-sig")
    return selected


def prepare_matrix_data() -> tuple[pd.DataFrame, list[str], list[str], pd.DataFrame]:
    df = pd.read_csv(MATRIX_CSV)
    df.columns = [str(c).strip() for c in df.columns]

    if "CITY_NAME_from_master" in df.columns:
        df["CITY_NAME_from_master"] = strip_yamabe_gun_only(df["CITY_NAME_from_master"])
    if "S_NAME_from_master" in df.columns:
        df["S_NAME_from_master"] = strip_yamabe_gun_only(df["S_NAME_from_master"])
    if "town" in df.columns:
        df["town"] = strip_yamabe_gun_only(df["town"])

    id_cols_existing = [c for c in ID_COLS if c in df.columns]
    facility_cols = [c for c in df.columns if c not in id_cols_existing]

    for c in facility_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    if "dist_km" in df.columns:
        df["dist_km"] = pd.to_numeric(df["dist_km"], errors="coerce")
        df = df.sort_values(["dist_km", "CITY_NAME_from_master", TOWN_COL], na_position="last").reset_index(drop=True)

    top60 = choose_top60_by_total_users(df, facility_cols)
    top60 = [c for c in top60 if c in df.columns]
    df_top60 = df[id_cols_existing + top60].copy()

    half_n = max(1, len(df_top60) // 2)
    df_half = df_top60.iloc[:half_n].copy()
    return df_top60, top60, id_cols_existing, df_half


def plot_dominant_territory(df_top60: pd.DataFrame, top60: list[str]) -> None:
    gdf = gpd.read_file(SHP_PATH)
    gdf["_city_"] = normalize_name(gdf["CITY_NAME"])
    gdf["_sname_"] = normalize_name(gdf["S_NAME"])
    gdf["_pair_"] = list(zip(gdf["_city_"], gdf["_sname_"]))

    df = df_top60.copy()
    df["_city_"] = normalize_name(df["CITY_NAME_from_master"])
    df["_sname_"] = normalize_name(df["S_NAME_from_master"])
    df["_pair_"] = list(zip(df["_city_"], df["_sname_"]))

    df["max_count"] = df[top60].max(axis=1)
    df["dominant"] = df[top60].idxmax(axis=1)
    df.loc[df["max_count"] <= 0, "dominant"] = np.nan

    pairs_set = set(df["_pair_"])
    gdf30 = gdf[gdf["_pair_"].isin(pairs_set)].copy()

    hit_cities = sorted(gdf30["_city_"].unique().tolist())
    gdf_city = gdf[gdf["_city_"].isin(hit_cities)].copy()
    city_outline = gdf_city.dissolve(by="_city_", as_index=False)

    df_by_city = defaultdict(list)
    for _, r in df.iterrows():
        df_by_city[r["_city_"]].append(r)

    best_rows = []
    for idx, grow in gdf30.iterrows():
        city = grow["_city_"]
        sname = grow["_sname_"]
        candidates = df_by_city.get(city, [])

        best = None
        best_score = None
        match_type2 = "no_match"

        for crow in candidates:
            if crow["_sname_"] == sname:
                best = crow
                match_type2 = "exact"
                break

        if best is None and city in PARTIAL_MATCH_CITIES:
            for crow in candidates:
                c_sname = crow["_sname_"]
                if (sname in c_sname) or (c_sname in sname):
                    score = abs(len(c_sname) - len(sname))
                    if (best_score is None) or (score < best_score):
                        best_score = score
                        best = crow
                        match_type2 = "partial"

        if best is None:
            best_rows.append({"_gidx_": idx, "dominant": np.nan, "max_count": np.nan, "match_type2": match_type2})
        else:
            best_rows.append({"_gidx_": idx, "dominant": best["dominant"], "max_count": best["max_count"], "match_type2": match_type2})

    df_best = pd.DataFrame(best_rows)
    gdf30m = gdf30.merge(df_best, left_index=True, right_on="_gidx_", how="left").drop(columns=["_gidx_"])

    missing_label = "未結合(利用者数TOP60施設の利用0 or データなし)"
    gdf30m["dominant_plot"] = gdf30m["dominant"].fillna(missing_label)
    cats = gdf30m["dominant_plot"].unique().tolist()
    cats_sorted = [c for c in cats if c != missing_label] + [missing_label]

    cmap = matplotlib.colormaps.get_cmap("turbo").resampled(len(cats_sorted))
    color_map = {cats_sorted[i]: cmap(i) for i in range(len(cats_sorted))}
    color_map[missing_label] = "#dddddd"
    gdf30m["_color_"] = gdf30m["dominant_plot"].map(color_map)

    fig, ax = plt.subplots(figsize=(14, 14))
    city_outline.plot(ax=ax, color="#f5f5f5", edgecolor="#aaaaaa", linewidth=0.6)
    gdf30m.plot(ax=ax, color=gdf30m["_color_"], linewidth=0.2)

    clinic = gpd.GeoDataFrame(
        {"name": [TARGET_FACILITY_KEYWORD]},
        geometry=[Point(REF_LON, REF_LAT)],
        crs="EPSG:4326",
    ).to_crs(gdf30m.crs)

    clinic.plot(ax=ax, color="white", marker="*", markersize=260, zorder=999)
    clinic.plot(ax=ax, color="black", marker="*", markersize=180, zorder=1000)

    minx, miny, maxx, maxy = gdf30m.total_bounds
    padx = (maxx - minx) * 0.10
    pady = (maxy - miny) * 0.10
    ax.set_xlim(minx - padx, maxx + padx)
    ax.set_ylim(miny - pady, maxy + pady)
    ax.set_title("佐々総合病院 車30分圏内: 町丁目別 勢力圏（利用者数TOP60のみ）")
    ax.axis("off")

    legend_cats = cats_sorted[:25]
    if missing_label not in legend_cats and missing_label in cats_sorted:
        legend_cats.append(missing_label)
    handles = [Patch(facecolor=color_map[c], edgecolor="none", label=c) for c in legend_cats]
    ax.legend(handles=handles, loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=True, fontsize=8, ncol=1, title="凡例(先頭25件)")

    plt.subplots_adjust(right=0.74)
    plt.savefig(OUT_TERRITORY_PNG, dpi=350, bbox_inches="tight")
    plt.close()

    out_cols = ["CITY_NAME", "S_NAME", "dominant", "max_count", "match_type2", "dist_km"]
    keep_cols = [c for c in out_cols if c in gdf30m.columns]
    gdf30m[keep_cols].to_csv(OUT_TERRITORY_CSV, index=False, encoding="utf-8-sig")


def plot_top3_matrix(df_half: pd.DataFrame, facility_cols: list[str], id_cols_existing: list[str], towns: list[str]) -> None:
    values = df_half[facility_cols].to_numpy(dtype=float)
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

    out_df = df_half[id_cols_existing].copy()
    out_matrix = pd.DataFrame(values_top3, columns=facility_cols)
    pd.concat([out_df, out_matrix], axis=1).to_csv(OUT_MATRIX_TOP3_CSV, index=False, encoding="utf-8-sig")

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
    fill_mask = other_mask & (~already_colored)
    rgb[fill_mask, :] = np.array([0.92, 0.92, 0.92])

    fig_w = min(0.34 * n_cols + 10, 70)
    fig_h = min(0.24 * n_rows + 8, 120)

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.imshow(rgb, aspect="auto")

    ax.set_xticks(np.arange(n_cols))
    ax.set_xticklabels(facility_cols, rotation=90, fontsize=8)
    ax.set_yticks(np.arange(n_rows))
    ax.set_yticklabels(towns, fontsize=8)
    ax.set_title("町丁目 × 医療機関 マトリクス（利用者数TOP60・各町丁目の上位3のみ・町丁目半分）", fontsize=14)

    if n_rows * n_cols <= 15000:
        for i in range(n_rows):
            for j in range(n_cols):
                v = values_top3[i, j]
                if v > 0:
                    ax.text(j, i, f"{int(v)}", ha="center", va="center", fontsize=5)

    ax.set_xticks(np.arange(-0.5, n_cols, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, n_rows, 1), minor=True)
    ax.grid(which="minor", color="black", linestyle="-", linewidth=0.15)
    ax.tick_params(which="minor", bottom=False, left=False)

    desc = []
    if top1:
        desc.append(f"赤: 上位3に最頻出 1位 = {top1}")
    if top2:
        desc.append(f"橙: 上位3に最頻出 2位 = {top2}")
    if top3:
        desc.append(f"黄: 上位3に最頻出 3位 = {top3}")
    fig.text(0.01, 0.01, "\n".join(desc), fontsize=9)

    plt.subplots_adjust(left=0.24, right=0.99, bottom=0.21, top=0.95)
    plt.savefig(OUT_MATRIX_TOP3_PNG, dpi=320)
    plt.close()


def plot_top10_heatmap(df_half: pd.DataFrame, facility_cols: list[str], id_cols_existing: list[str], towns: list[str]) -> None:
    facility_total = df_half[facility_cols].sum(axis=0).sort_values(ascending=False)
    top_facilities = facility_total.head(TOP_K_HEATMAP).index.tolist()

    values_all = df_half[facility_cols].to_numpy(dtype=float)
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

    mat = df_half[top_facilities].to_numpy(dtype=float)
    mat_disp = np.where(mat >= 0, mat, 0)
    pd.concat(
        [df_half[id_cols_existing], pd.DataFrame(mat_disp, columns=top_facilities)],
        axis=1,
    ).to_csv(OUT_HEATMAP_TOP10_CSV, index=False, encoding="utf-8-sig")

    mat_for_color = np.log1p(mat_disp)
    fig_w = min(1.15 * TOP_K_HEATMAP + 10, 28)
    fig_h = min(0.24 * len(towns) + 8, 120)

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    im = ax.imshow(mat_for_color, aspect="auto")

    ax.set_xticks(np.arange(len(top_facilities)))
    ax.set_xticklabels(top_facilities, rotation=90, fontsize=11)
    ax.set_yticks(np.arange(len(towns)))
    ax.set_yticklabels(towns, fontsize=8)
    ax.set_title("佐々総合病院 車30分圏内: ヒートマップ（利用者数TOP60の中の上位10・町丁目半分）", fontsize=14)

    if mat_disp.shape[0] * mat_disp.shape[1] <= 9000:
        for i in range(mat_disp.shape[0]):
            for j in range(mat_disp.shape[1]):
                v = mat_disp[i, j]
                if v > 0:
                    ax.text(j, i, f"{int(v)}", ha="center", va="center", fontsize=5)

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

    plt.subplots_adjust(left=0.24, right=0.99, bottom=0.19, top=0.96)
    plt.savefig(OUT_HEATMAP_TOP10_PNG, dpi=320)
    plt.close()


def main() -> None:
    DOWNLOAD_OUT_DIR.mkdir(parents=True, exist_ok=True)

    df_top60, top60, id_cols_existing, df_half = prepare_matrix_data()

    towns = []
    for _, r in df_half.iterrows():
        label = f"{str(r.get(TOWN_COL, ''))}"
        if pd.notna(r.get("dist_km", np.nan)):
            label = f"{label} ({float(r['dist_km']):.1f}km)"
        towns.append(label)

    plot_dominant_territory(df_top60, top60)
    plot_top3_matrix(df_half, top60, id_cols_existing, towns)
    plot_top10_heatmap(df_half, top60, id_cols_existing, towns)

    print("saved:", OUT_TERRITORY_PNG)
    print("saved:", OUT_TERRITORY_CSV)
    print("saved:", OUT_MATRIX_TOP3_PNG)
    print("saved:", OUT_MATRIX_TOP3_CSV)
    print("saved:", OUT_HEATMAP_TOP10_PNG)
    print("saved:", OUT_HEATMAP_TOP10_CSV)
    print("saved:", OUT_RANK_CSV)
    print("saved:", OUT_SELECTED_FACILITIES_CSV)
    print("selected facilities:", len(top60))
    print("town rows used for heatmap/matrix:", len(df_half), "/", len(df_top60))


if __name__ == "__main__":
    main()
