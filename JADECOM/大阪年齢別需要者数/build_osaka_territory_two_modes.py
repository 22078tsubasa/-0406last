from __future__ import annotations

import os
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

MATRIX_CSV = Path("/Users/itotsubasa/Downloads/jadecom/大阪赤十字病院/大阪赤十字病院周辺の町丁目_各医療施設利用数_KLA統合_osaka_car30_match.csv")
SHP_PATH = Path("/Users/itotsubasa/Downloads/jadecom/大阪赤十字病院/r2ka27.shp")

OUT_ROOT = Path("/Users/itotsubasa/Downloads/jadecom/大阪赤十字病院/勢力図分析")
OUT_READABLE = OUT_ROOT / "見やすい版"
OUT_ALL = OUT_ROOT / "全町丁目版"

TOP_FACILITY_USERS = 60
TOP_K_HEATMAP = 10
TOP_K_EXCLUDING_TARGET = 5
READABLE_TOWN_ROWS = 60
TARGET_FACILITY_KEYWORD = "大阪赤十字病院"
TOWN_COL = "S_NAME_from_master"
REF_LAT = 34.66401
REF_LON = 135.52516

ID_COLS = [
    "town",
    "town_norm",
    "match_type",
    "CITY_NAME_from_master",
    "S_NAME_from_master",
    "town_name_show",
    "TOWN_CODE_11",
    "LON",
    "LAT",
    "dist_km",
    "total_215",
]


def normalize_name(s: pd.Series) -> pd.Series:
    s = s.astype(str)
    s = s.str.replace("　", "", regex=False).str.replace(" ", "", regex=False).str.strip()
    s = s.str.replace(r"（.*?）", "", regex=True).str.replace(r"\(.*?\)", "", regex=True)
    s = s.str.replace("大字", "", regex=False)
    return s


def load_matrix() -> tuple[pd.DataFrame, list[str], list[str]]:
    df = pd.read_csv(MATRIX_CSV, dtype={"TOWN_CODE_11": str})
    df.columns = [str(c).strip() for c in df.columns]
    id_cols_existing = [c for c in ID_COLS if c in df.columns]
    facility_cols = [c for c in df.columns if c not in id_cols_existing]
    for c in facility_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    if "dist_km" in df.columns:
        df["dist_km"] = pd.to_numeric(df["dist_km"], errors="coerce")
        df = df.sort_values(["dist_km", "CITY_NAME_from_master", "S_NAME_from_master"], na_position="last").reset_index(drop=True)
    return df, facility_cols, id_cols_existing


def choose_top60_by_total_users(df: pd.DataFrame, facility_cols: list[str]) -> tuple[list[str], pd.DataFrame]:
    facility_total = df[facility_cols].sum(axis=0).sort_values(ascending=False)
    selected = facility_total.head(TOP_FACILITY_USERS).index.tolist()
    target_candidates = [c for c in facility_total.index if TARGET_FACILITY_KEYWORD in str(c)]
    if target_candidates:
        target = target_candidates[0]
        if target not in selected and len(selected) >= 1:
            selected = selected[:-1] + [target]
    selected_total = facility_total.reindex(selected).fillna(0)
    rank = pd.DataFrame({"施設名_実データ列": selected, "利用者数合計": selected_total.values}).sort_values("利用者数合計", ascending=False).reset_index(drop=True)
    rank.insert(0, "rank", np.arange(1, len(rank) + 1))
    rank["大阪赤十字病院フラグ"] = rank["施設名_実データ列"].str.contains(TARGET_FACILITY_KEYWORD).astype(int)
    return rank["施設名_実データ列"].tolist(), rank


def build_geo_join(df_src: pd.DataFrame, selected_cols: list[str], value_col: str, max_col: str) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    gdf = gpd.read_file(SHP_PATH)
    gdf = gdf[gdf["S_NAME"].notna()].copy()
    gdf["TOWN_CODE_11"] = gdf["KEY_CODE"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(11)
    gdf["_city_"] = normalize_name(gdf["CITY_NAME"])

    df = df_src.copy()
    df["TOWN_CODE_11"] = df["TOWN_CODE_11"].fillna("").astype(str).str.zfill(11)
    df[value_col] = df[selected_cols].idxmax(axis=1)
    df[max_col] = df[selected_cols].max(axis=1)
    df.loc[df[max_col] <= 0, value_col] = np.nan

    m = df[["TOWN_CODE_11", value_col, max_col, "dist_km"]].drop_duplicates("TOWN_CODE_11")
    gdfm = gdf.merge(m, on="TOWN_CODE_11", how="inner")

    hit_cities = sorted(gdfm["_city_"].unique().tolist())
    gdf_city = gdf[gdf["_city_"].isin(hit_cities)].copy()
    city_outline = gdf_city.dissolve(by="_city_", as_index=False)
    return gdfm, city_outline


def draw_territory(gdfm: gpd.GeoDataFrame, city_outline: gpd.GeoDataFrame, plot_col: str, title: str, out_png: Path, color_map: dict[str, object], legend_title: str, legend_categories: list[str] | None = None) -> None:
    fig, ax = plt.subplots(figsize=(15, 15))
    city_outline.plot(ax=ax, color="#f5f5f5", edgecolor="#aaaaaa", linewidth=0.6)
    gdfm.plot(ax=ax, color=gdfm[plot_col].map(color_map), linewidth=0.2)

    clinic = gpd.GeoDataFrame({"name": [TARGET_FACILITY_KEYWORD]}, geometry=[Point(REF_LON, REF_LAT)], crs="EPSG:4326").to_crs(gdfm.crs)
    clinic.plot(ax=ax, color="white", marker="*", markersize=260, zorder=999)
    clinic.plot(ax=ax, color="black", marker="*", markersize=180, zorder=1000)

    cx = clinic.geometry.x.iloc[0]
    cy = clinic.geometry.y.iloc[0]
    ax.annotate(
        TARGET_FACILITY_KEYWORD,
        xy=(cx, cy),
        xytext=(60, 40),
        textcoords="offset points",
        fontsize=11,
        color="black",
        zorder=1001,
        bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="black", lw=0.8, alpha=0.95),
        arrowprops=dict(arrowstyle="->", color="black", lw=1.2, shrinkA=0, shrinkB=0),
    )

    target_labels = [c for c in gdfm[plot_col].dropna().unique().tolist() if TARGET_FACILITY_KEYWORD in str(c)]
    if target_labels:
        gdf_target = gdfm[gdfm[plot_col].isin(target_labels)].copy()
        gdf_target.boundary.plot(ax=ax, color="white", linewidth=3.4, zorder=19)
        gdf_target.boundary.plot(ax=ax, color="red", linewidth=2.1, zorder=20)

    minx, miny, maxx, maxy = gdfm.total_bounds
    padx = (maxx - minx) * 0.10
    pady = (maxy - miny) * 0.10
    ax.set_xlim(minx - padx, maxx + padx)
    ax.set_ylim(miny - pady, maxy + pady)
    ax.set_title(title)
    ax.axis("off")

    cats_sorted = legend_categories if legend_categories is not None else list(dict.fromkeys(gdfm[plot_col].tolist()))
    handles = [Patch(facecolor=color_map[c], edgecolor="none", label=c) for c in cats_sorted if c in color_map]
    ncol = 2 if len(handles) > 30 else 1
    fs = 7 if len(handles) > 20 else 8
    right_margin = 0.56 if ncol == 2 else 0.72
    ax.legend(handles=handles, loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=True, fontsize=fs, ncol=ncol, title=legend_title)
    plt.subplots_adjust(right=right_margin)
    plt.savefig(out_png, dpi=320, bbox_inches="tight")
    plt.close()


def plot_top3_matrix(df_part: pd.DataFrame, facility_cols: list[str], id_cols_existing: list[str], out_dir: Path, suffix: str) -> None:
    values = df_part[facility_cols].to_numpy(dtype=float)
    top3_mask = np.zeros_like(values, dtype=bool)
    for i in range(values.shape[0]):
        row = values[i]
        pos_idx = np.where(row > 0)[0]
        if len(pos_idx) == 0:
            continue
        sorted_idx = pos_idx[np.argsort(row[pos_idx])[::-1]]
        top3_mask[i, sorted_idx[:3]] = True
    values_top3 = np.where(top3_mask, values, 0)

    out_matrix_csv = out_dir / f"osaka_car30_usersTop60_town_med_matrix_上位3のみ_{suffix}.csv"
    pd.concat([df_part[id_cols_existing], pd.DataFrame(values_top3, columns=facility_cols)], axis=1).to_csv(out_matrix_csv, index=False, encoding="utf-8-sig")

    n_rows, n_cols = values_top3.shape
    rgb = np.ones((n_rows, n_cols, 3), dtype=float)
    freq = top3_mask.sum(axis=0)
    rank_idx = np.argsort(freq)[::-1]
    top_ranked_cols = [facility_cols[i] for i in rank_idx[:3]]
    top1, top2, top3 = (top_ranked_cols + [None, None, None])[:3]

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

    fig_w = min(0.34 * n_cols + 10, 70)
    fig_h = min(0.22 * n_rows + 6, 140)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.imshow(rgb, aspect="auto")
    ax.set_xticks(np.arange(n_cols))
    ax.set_xticklabels(facility_cols, rotation=90, fontsize=8)

    ylabels = df_part[TOWN_COL].astype(str).fillna("").tolist()
    if "dist_km" in df_part.columns:
        ylabels = [f"{t} ({d:.1f}km)" if pd.notna(d) else t for t, d in zip(ylabels, df_part["dist_km"])]
    ax.set_yticks(np.arange(n_rows))
    ax.set_yticklabels(ylabels, fontsize=6 if n_rows > 1200 else 8)
    ax.set_title(f"町丁目 × 医療機関 マトリクス（利用者数TOP60・各町丁目の上位3のみ・{suffix}）", fontsize=14)

    ax.set_xticks(np.arange(-0.5, n_cols, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, n_rows, 1), minor=True)
    ax.grid(which="minor", color="black", linestyle="-", linewidth=0.10)
    ax.tick_params(which="minor", bottom=False, left=False)

    out_png = out_dir / f"osaka_car30_usersTop60_town_med_matrix_上位3_{suffix}.png"
    plt.subplots_adjust(left=0.22, right=0.99, bottom=0.20, top=0.95)
    plt.savefig(out_png, dpi=300)
    plt.close()


def plot_top10_heatmap(df_part: pd.DataFrame, facility_cols: list[str], id_cols_existing: list[str], out_dir: Path, suffix: str) -> None:
    facility_total = df_part[facility_cols].sum(axis=0).sort_values(ascending=False)
    top_facilities = facility_total.head(TOP_K_HEATMAP).index.tolist()
    mat = df_part[top_facilities].to_numpy(dtype=float)
    mat_disp = np.where(mat >= 0, mat, 0)
    mat_for_color = np.log1p(mat_disp)

    out_matrix_csv = out_dir / f"osaka_car30_usersTop60_town_med_matrix_上位10_{suffix}.csv"
    pd.concat([df_part[id_cols_existing], pd.DataFrame(mat_disp, columns=top_facilities)], axis=1).to_csv(out_matrix_csv, index=False, encoding="utf-8-sig")

    rank_df = pd.DataFrame({"施設名": facility_total.index, "患者数合計": facility_total.values})
    rank_df.to_csv(out_dir / f"osaka_car30_usersTop60_facility_rank_summary_{suffix}.csv", index=False, encoding="utf-8-sig")

    fig_w = min(1.15 * TOP_K_HEATMAP + 10, 30)
    fig_h = min(0.22 * len(df_part) + 6, 140)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    im = ax.imshow(mat_for_color, aspect="auto")
    ax.set_xticks(np.arange(len(top_facilities)))
    ax.set_xticklabels(top_facilities, rotation=90, fontsize=10)
    ylabels = df_part[TOWN_COL].astype(str).fillna("").tolist()
    if "dist_km" in df_part.columns:
        ylabels = [f"{t} ({d:.1f}km)" if pd.notna(d) else t for t, d in zip(ylabels, df_part["dist_km"])]
    ax.set_yticks(np.arange(len(ylabels)))
    ax.set_yticklabels(ylabels, fontsize=6 if len(df_part) > 1200 else 8)
    ax.set_title(f"大阪赤十字病院 車20分圏内: ヒートマップ（利用者数TOP60内の上位10・{suffix}）", fontsize=14)
    ax.set_xticks(np.arange(-0.5, len(top_facilities), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(ylabels), 1), minor=True)
    ax.grid(which="minor", linewidth=0.15)
    ax.tick_params(which="minor", bottom=False, left=False)

    target_cols = [i for i, name in enumerate(top_facilities) if TARGET_FACILITY_KEYWORD in name]
    for j in target_cols:
        rect = Rectangle((j - 0.5, -0.5), 1, len(ylabels), fill=False, linewidth=2.5)
        ax.add_patch(rect)

    cbar = plt.colorbar(im, ax=ax, fraction=0.02, pad=0.02)
    cbar.set_label("log(1 + 人数)", fontsize=10)
    out_png = out_dir / f"osaka_car30_usersTop60_town_med_heatmap_上位10_{suffix}.png"
    plt.subplots_adjust(left=0.22, right=0.99, bottom=0.18, top=0.96)
    plt.savefig(out_png, dpi=300)
    plt.close()


def run_mode(df_top60: pd.DataFrame, top60: list[str], id_cols_existing: list[str], out_dir: Path, suffix: str, use_half: bool) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    df_part = df_top60.iloc[:READABLE_TOWN_ROWS].copy() if use_half else df_top60.copy()

    value_col = "dominant_top60"
    max_col = "max_count_top60"
    gdfm, city_outline = build_geo_join(df_top60, top60, value_col, max_col)
    missing_label = "未結合(利用者数TOP60施設の利用0 or データなし)"
    gdfm["plot_label"] = gdfm[value_col].fillna(missing_label)
    cats_sorted = [c for c in gdfm["plot_label"].dropna().unique().tolist() if c != missing_label] + [missing_label]
    cmap = matplotlib.colormaps.get_cmap("turbo").resampled(len(cats_sorted))
    color_map = {cats_sorted[i]: cmap(i) for i in range(len(cats_sorted))}
    color_map[missing_label] = "#dddddd"
    draw_territory(
        gdfm,
        city_outline,
        "plot_label",
        f"大阪赤十字病院 車20分圏内: 町丁目別 勢力圏（利用者数TOP60・{suffix}）",
        out_dir / f"dominant_territory_osaka_car30_usersTop60_{suffix}.png",
        color_map,
        "凡例(全施設)",
    )
    gdfm[["CITY_NAME", "S_NAME", value_col, max_col, "dist_km", "plot_label"]].to_csv(out_dir / f"dominant_territory_osaka_car30_usersTop60_{suffix}_result.csv", index=False, encoding="utf-8-sig")

    facility_total = df_top60[top60].sum(axis=0).sort_values(ascending=False)
    target = next((c for c in top60 if TARGET_FACILITY_KEYWORD in str(c)), None)
    top_ex_target = [f for f in facility_total.index.tolist() if f != target][:TOP_K_EXCLUDING_TARGET]
    selected = [f for f in [target] + top_ex_target if f is not None]
    value_col2 = "dominant_sel6"
    max_col2 = "max_count_sel6"
    gdfm2, city_outline2 = build_geo_join(df_top60, selected, value_col2, max_col2)
    other_label = "その他(6施設すべて0人)"
    gdfm2["plot_label"] = gdfm2[value_col2].fillna(other_label)
    cats = selected + [other_label]
    cmap2 = matplotlib.colormaps.get_cmap("tab10").resampled(len(cats))
    color_map2 = {cats[i]: cmap2(i) for i in range(len(cats))}
    color_map2[other_label] = "#bbbbbb"
    draw_territory(
        gdfm2,
        city_outline2,
        "plot_label",
        f"大阪赤十字病院 車20分圏内: 勢力圏（大阪赤十字病院+上位5、0人はその他・{suffix}）",
        out_dir / f"dominant_territory_osaka_car30_osakaPlus5_other_{suffix}.png",
        color_map2,
        "凡例(7種類固定)",
        legend_categories=cats,
    )
    gdfm2[["CITY_NAME", "S_NAME", value_col2, max_col2, "dist_km", "plot_label"]].to_csv(out_dir / f"dominant_territory_osaka_car30_osakaPlus5_other_{suffix}_result.csv", index=False, encoding="utf-8-sig")

    plot_top3_matrix(df_part, top60, id_cols_existing, out_dir, suffix)
    plot_top10_heatmap(df_part, top60, id_cols_existing, out_dir, suffix)
    df_part.to_csv(out_dir / f"osaka_car30_usersTop60_base_matrix_{suffix}.csv", index=False, encoding="utf-8-sig")


def main() -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    df, facility_cols, id_cols_existing = load_matrix()
    top60, rank = choose_top60_by_total_users(df, facility_cols)
    df_top60 = df[id_cols_existing + top60].copy()

    rank.to_csv(OUT_ROOT / "osaka_car30_usersTop60_selected_facilities.csv", index=False, encoding="utf-8-sig")

    run_mode(df_top60, top60, id_cols_existing, OUT_READABLE, "見やすい版", use_half=True)
    run_mode(df_top60, top60, id_cols_existing, OUT_ALL, "全町丁目版", use_half=False)

    print("saved root:", OUT_ROOT)
    print("selected facilities:", len(top60))
    print("town rows all:", len(df_top60))
    print("town rows readable:", min(READABLE_TOWN_ROWS, len(df_top60)))


if __name__ == "__main__":
    main()
