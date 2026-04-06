import os
from collections import defaultdict

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import geopandas as gpd
from matplotlib.patches import Patch
from matplotlib import font_manager
from shapely.geometry import Point


# 画面不要で保存だけ行う
matplotlib.use("Agg")

# =========================
# 日本語フォント（利用可能なものを自動選択）
# =========================
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

# =========================
# パス
# =========================
TABLE_PATH = "/Users/itotsubasa/Downloads/jadecom/202603:西村先生MTG/都祁診療所周辺の町丁目_各医療施設利用数_30km.xlsx"
SHP_DIR = "/Users/itotsubasa/Downloads/jadecom/小地域_tuge"
OUT_DIR = "/Users/itotsubasa/IdeaProjects/pythoN/JADECOM/202603"
OUT_PNG = os.path.join(OUT_DIR, "dominant_territory_tsuge_30km.png")
OUT_CSV = os.path.join(OUT_DIR, "dominant_territory_tsuge_30km_result.csv")
OUT_TOP7_PNG = os.path.join(OUT_DIR, "dominant_territory_tsuge_30km_top7.png")
OUT_TOP7_CSV = os.path.join(OUT_DIR, "dominant_territory_tsuge_30km_top7_result.csv")
OUT_TOP7_ONLY_PNG = os.path.join(OUT_DIR, "dominant_territory_tsuge_30km_top7only.png")
OUT_TOP7_ONLY_CSV = os.path.join(OUT_DIR, "dominant_territory_tsuge_30km_top7only_result.csv")
OUT_TSUGE_PLUS5_PNG = os.path.join(OUT_DIR, "dominant_territory_tsuge_30km_tsuge_plus5.png")
OUT_TSUGE_PLUS5_CSV = os.path.join(OUT_DIR, "dominant_territory_tsuge_30km_tsuge_plus5_result.csv")

# =========================
# 都祁診療所（起点）座標
# =========================
REF_LAT = 34.60399219055155
REF_LON = 135.95722209432466

# =========================
# ハイライト対象（dominantがこの施設の町丁目を赤枠 + 町丁目名print）
# =========================
TARGET_FACILITY = "奈良市都祁診療所"

# =========================
# 部分一致を許す市区町村
# =========================
PARTIAL_MATCH_CITIES = {"山添村", "宇陀市"}
TOP_N = 7
TOP_K_EXCLUDING_TARGET = 5


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


def load_table(path: str) -> pd.DataFrame:
    ext = os.path.splitext(path)[1].lower()
    if ext in [".xlsx", ".xlsm", ".xls"]:
        return pd.read_excel(path)
    return pd.read_csv(path, encoding="utf-8-sig")


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)

    # 0) SHP読み込み
    shp_files = [f for f in os.listdir(SHP_DIR) if f.lower().endswith(".shp")]
    if not shp_files:
        raise FileNotFoundError("SHP_DIRの中に .shp が見つかりませんでした")
    shp_path = os.path.join(SHP_DIR, shp_files[0])
    print("使用SHP:", shp_path)

    gdf = gpd.read_file(shp_path)
    if "CITY_NAME" not in gdf.columns or "S_NAME" not in gdf.columns:
        print("SHP columns:", list(gdf.columns))
        raise KeyError("SHP側に CITY_NAME / S_NAME 列が必要です")

    gdf["_city_"] = normalize_name(gdf["CITY_NAME"])
    gdf["_sname_"] = normalize_name(gdf["S_NAME"])
    gdf["_pair_"] = list(zip(gdf["_city_"], gdf["_sname_"]))

    # 1) 30kmテーブル読み込み
    df = load_table(TABLE_PATH)
    print("30kmテーブル rows:", len(df), "cols:", len(df.columns))
    need_cols = {"CITY_NAME_from_master", "S_NAME_from_master"}
    if not need_cols.issubset(set(df.columns)):
        raise KeyError("30kmテーブルに CITY_NAME_from_master と S_NAME_from_master が必要です")

    # CSV側だけ「山辺郡/山辺群」を削除
    df["CITY_NAME_from_master"] = strip_yamabe_gun_only(df["CITY_NAME_from_master"])
    df["S_NAME_from_master"] = strip_yamabe_gun_only(df["S_NAME_from_master"])
    if "town" in df.columns:
        df["town"] = strip_yamabe_gun_only(df["town"])

    df["_city_"] = normalize_name(df["CITY_NAME_from_master"])
    df["_sname_"] = normalize_name(df["S_NAME_from_master"])
    df["_pair_"] = list(zip(df["_city_"], df["_sname_"]))

    # 2) 30kmテーブルの町丁目だけSHPを残す
    pairs_set = set(df["_pair_"])
    gdf30 = gdf[gdf["_pair_"].isin(pairs_set)].copy()
    print("SHP全体:", len(gdf), "=> 30km町丁目一致:", len(gdf30))

    hit_cities = sorted(gdf30["_city_"].unique().tolist())
    gdf_city = gdf[gdf["_city_"].isin(hit_cities)].copy()
    city_outline = gdf_city.dissolve(by="_city_", as_index=False)

    # 3) 施設列抽出
    meta_cols = {
        "town", "town_name_show", "town_norm", "match_type", "dist_km", "LON", "LAT",
        "CITY_NAME_from_master", "S_NAME_from_master",
        "total_87", "_pair_", "_city_", "_sname_",
    }
    facility_cols = [c for c in df.columns if c not in meta_cols]
    if len(facility_cols) == 0:
        raise ValueError("施設列が抽出できませんでした。meta_colsの見直しが必要です。")

    df[facility_cols] = df[facility_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
    df["max_count"] = df[facility_cols].max(axis=1)
    df["dominant"] = df[facility_cols].idxmax(axis=1)
    df.loc[df["max_count"] <= 0, "dominant"] = np.nan

    # 4) 結合（exact優先 + 指定市区町村のみpartial）
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

    print("\n=== 結合方式内訳 ===")
    print(gdf30m["match_type2"].value_counts(dropna=False))

    # 5) 集計
    total_areas = len(gdf30m)
    colored_areas = int(gdf30m["dominant"].notna().sum())
    print(f"\n塗られた地域数: {colored_areas} / {total_areas} ({(colored_areas / total_areas if total_areas else 0):.1%})")
    facility_used_counts = gdf30m["dominant"].value_counts(dropna=True)
    print("\ndominantとして出た施設数:", facility_used_counts.shape[0])
    print(facility_used_counts.head(20))

    # 6) 都祁診療所dominant
    if TARGET_FACILITY not in facility_cols:
        maybe = [c for c in facility_cols if "都祁" in c]
        print("\n[注意] TARGET_FACILITY が施設列に見つかりません。候補:", maybe)

    gdf_tsuge_dom = gdf30m[gdf30m["dominant"] == TARGET_FACILITY].copy()
    print("\n=== 都祁診療所がdominantになった町丁目 ===")
    print("件数:", len(gdf_tsuge_dom))
    if len(gdf_tsuge_dom) > 0:
        town_list = gdf_tsuge_dom[["_city_", "S_NAME"]].drop_duplicates().sort_values(["_city_", "S_NAME"])
        print(town_list.to_string(index=False))
    else:
        print("該当なし")

    # 7) 欠損町丁目
    gdf_no_data = gdf30m[gdf30m["dominant"].isna()].copy()
    print("\n=== データがない町丁目（dominant欠損） ===")
    print("件数:", len(gdf_no_data))
    if len(gdf_no_data) > 0:
        table_no_data = (
            gdf_no_data[["_city_", "S_NAME", "match_type2"]]
            .drop_duplicates()
            .sort_values(["_city_", "S_NAME"])
            .reset_index(drop=True)
        )
        print(table_no_data.to_string(index=False))
    else:
        print("該当なし")

    # 8) 可視化
    missing_label = "未結合(最大人数0 or データなし)"
    gdf30m["dominant_plot"] = gdf30m["dominant"].fillna(missing_label)
    cats = gdf30m["dominant_plot"].unique().tolist()
    cats_sorted = [c for c in cats if c != missing_label] + [missing_label]

    n = len(cats_sorted)
    cmap = matplotlib.colormaps.get_cmap("turbo").resampled(n)
    color_map = {cats_sorted[i]: cmap(i) for i in range(n)}
    color_map[missing_label] = "#dddddd"
    gdf30m["_color_"] = gdf30m["dominant_plot"].map(color_map)

    fig, ax = plt.subplots(figsize=(12, 12))
    city_outline.plot(ax=ax, color="#f5f5f5", edgecolor="#aaaaaa", linewidth=0.6)
    gdf30m.plot(ax=ax, color=gdf30m["_color_"], linewidth=0.2)

    clinic = gpd.GeoDataFrame(
        {"name": [TARGET_FACILITY]},
        geometry=[Point(REF_LON, REF_LAT)],
        crs="EPSG:4326",
    ).to_crs(gdf30m.crs)

    clinic.plot(ax=ax, color="white", marker="*", markersize=260, zorder=999)
    clinic.plot(ax=ax, color="black", marker="*", markersize=180, zorder=1000)

    cx = clinic.geometry.x.iloc[0]
    cy = clinic.geometry.y.iloc[0]
    ax.annotate(
        TARGET_FACILITY,
        xy=(cx, cy),
        xytext=(60, 40),
        textcoords="offset points",
        fontsize=11,
        color="black",
        zorder=1001,
        bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="black", lw=0.8, alpha=0.95),
        arrowprops=dict(arrowstyle="->", color="black", lw=1.2, shrinkA=0, shrinkB=0),
    )

    if len(gdf_tsuge_dom) > 0:
        gdf_tsuge_dom.boundary.plot(ax=ax, color="white", linewidth=3.0, zorder=19)
        gdf_tsuge_dom.boundary.plot(ax=ax, color="red", linewidth=1.8, zorder=20)

    minx, miny, maxx, maxy = gdf30m.total_bounds
    padx = (maxx - minx) * 0.10
    pady = (maxy - miny) * 0.10
    ax.set_xlim(minx - padx, maxx + padx)
    ax.set_ylim(miny - pady, maxy + pady)

    ax.set_title("奈良市都祁診療所 30km圏内: 町丁目別 医療機関勢力圏（最大人数・全87施設）")
    ax.axis("off")

    handles = [Patch(facecolor=color_map[c], edgecolor="none", label=c) for c in cats_sorted]
    ax.legend(handles=handles, loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=True, fontsize=8, ncol=1)
    plt.subplots_adjust(right=0.72)
    plt.savefig(OUT_PNG, dpi=350, bbox_inches="tight")
    plt.close()

    # 出力テーブル
    out_cols = ["CITY_NAME", "S_NAME", "_city_", "_sname_", "dominant", "max_count", "match_type2", "dist_km"]
    keep_cols = [c for c in out_cols if c in gdf30m.columns]
    gdf30m[keep_cols].to_csv(OUT_CSV, index=False, encoding="utf-8-sig")

    print("\n保存PNG:", OUT_PNG)
    print("保存CSV:", OUT_CSV)

    # 9) 上位N施設版（それ以外は「その他」）
    top_facilities = facility_used_counts.head(TOP_N).index.tolist()
    missing_label = "未結合(最大人数0 or データなし)"
    other_label = f"その他(上位{TOP_N}以外)"

    gdf_top = gdf30m.copy()
    gdf_top["dominant_top"] = gdf_top["dominant"]
    gdf_top.loc[gdf_top["dominant_top"].isna(), "dominant_top"] = missing_label
    gdf_top.loc[
        ~gdf_top["dominant_top"].isin(top_facilities + [missing_label]),
        "dominant_top",
    ] = other_label

    cats_top = top_facilities + [other_label, missing_label]
    cmap_top = matplotlib.colormaps.get_cmap("tab10").resampled(len(cats_top))
    color_map_top = {cats_top[i]: cmap_top(i) for i in range(len(cats_top))}
    color_map_top[missing_label] = "#dddddd"
    color_map_top[other_label] = "#bbbbbb"
    gdf_top["_color_top_"] = gdf_top["dominant_top"].map(color_map_top)

    fig2, ax2 = plt.subplots(figsize=(12, 12))
    city_outline.plot(ax=ax2, color="#f5f5f5", edgecolor="#aaaaaa", linewidth=0.6)
    gdf_top.plot(ax=ax2, color=gdf_top["_color_top_"], linewidth=0.2)

    clinic.plot(ax=ax2, color="white", marker="*", markersize=260, zorder=999)
    clinic.plot(ax=ax2, color="black", marker="*", markersize=180, zorder=1000)
    ax2.annotate(
        TARGET_FACILITY,
        xy=(cx, cy),
        xytext=(60, 40),
        textcoords="offset points",
        fontsize=11,
        color="black",
        zorder=1001,
        bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="black", lw=0.8, alpha=0.95),
        arrowprops=dict(arrowstyle="->", color="black", lw=1.2, shrinkA=0, shrinkB=0),
    )
    if len(gdf_tsuge_dom) > 0:
        gdf_tsuge_dom.boundary.plot(ax=ax2, color="white", linewidth=3.0, zorder=19)
        gdf_tsuge_dom.boundary.plot(ax=ax2, color="red", linewidth=1.8, zorder=20)

    ax2.set_xlim(minx - padx, maxx + padx)
    ax2.set_ylim(miny - pady, maxy + pady)
    ax2.set_title(f"奈良市都祁診療所 30km圏内: 町丁目別 勢力圏（上位{TOP_N}施設）")
    ax2.axis("off")

    handles2 = [Patch(facecolor=color_map_top[c], edgecolor="none", label=c) for c in cats_top]
    ax2.legend(handles=handles2, loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=True, fontsize=8, ncol=1)
    plt.subplots_adjust(right=0.72)
    plt.savefig(OUT_TOP7_PNG, dpi=350, bbox_inches="tight")
    plt.close()

    top_out_cols = ["CITY_NAME", "S_NAME", "dominant", "dominant_top", "max_count", "match_type2", "dist_km"]
    keep_top_cols = [c for c in top_out_cols if c in gdf_top.columns]
    gdf_top[keep_top_cols].to_csv(OUT_TOP7_CSV, index=False, encoding="utf-8-sig")

    print("保存PNG(top7):", OUT_TOP7_PNG)
    print("保存CSV(top7):", OUT_TOP7_CSV)

    # 10) 上位N施設だけで再計算した勢力図
    df_top_source = df.copy()
    df_top_source["topN_max_count"] = df_top_source[top_facilities].max(axis=1)
    df_top_source["topN_dominant"] = df_top_source[top_facilities].idxmax(axis=1)
    df_top_source.loc[df_top_source["topN_max_count"] <= 0, "topN_dominant"] = np.nan

    top_map = (
        df_top_source[["_city_", "_sname_", "topN_dominant", "topN_max_count"]]
        .drop_duplicates(subset=["_city_", "_sname_"])
        .set_index(["_city_", "_sname_"])
    )
    gdf_top_only = gdf30m.copy()
    gdf_top_only = gdf_top_only.join(top_map, on=["_city_", "_sname_"])

    top_only_missing = f"未結合(上位{TOP_N}施設の利用0)"
    gdf_top_only["dominant_top_only_plot"] = gdf_top_only["topN_dominant"].fillna(top_only_missing)
    cats_only = top_facilities + [top_only_missing]
    cmap_only = matplotlib.colormaps.get_cmap("tab10").resampled(len(cats_only))
    color_map_only = {cats_only[i]: cmap_only(i) for i in range(len(cats_only))}
    color_map_only[top_only_missing] = "#dddddd"
    gdf_top_only["_color_top_only_"] = gdf_top_only["dominant_top_only_plot"].map(color_map_only)

    fig3, ax3 = plt.subplots(figsize=(12, 12))
    city_outline.plot(ax=ax3, color="#f5f5f5", edgecolor="#aaaaaa", linewidth=0.6)
    gdf_top_only.plot(ax=ax3, color=gdf_top_only["_color_top_only_"], linewidth=0.2)
    clinic.plot(ax=ax3, color="white", marker="*", markersize=260, zorder=999)
    clinic.plot(ax=ax3, color="black", marker="*", markersize=180, zorder=1000)
    ax3.annotate(
        TARGET_FACILITY,
        xy=(cx, cy),
        xytext=(60, 40),
        textcoords="offset points",
        fontsize=11,
        color="black",
        zorder=1001,
        bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="black", lw=0.8, alpha=0.95),
        arrowprops=dict(arrowstyle="->", color="black", lw=1.2, shrinkA=0, shrinkB=0),
    )

    gdf_tsuge_dom_top_only = gdf_top_only[gdf_top_only["topN_dominant"] == TARGET_FACILITY].copy()
    if len(gdf_tsuge_dom_top_only) > 0:
        gdf_tsuge_dom_top_only.boundary.plot(ax=ax3, color="white", linewidth=3.0, zorder=19)
        gdf_tsuge_dom_top_only.boundary.plot(ax=ax3, color="red", linewidth=1.8, zorder=20)

    ax3.set_xlim(minx - padx, maxx + padx)
    ax3.set_ylim(miny - pady, maxy + pady)
    ax3.set_title(f"奈良市都祁診療所 30km圏内: 町丁目別 勢力圏（上位{TOP_N}施設のみで再計算）")
    ax3.axis("off")

    handles3 = [Patch(facecolor=color_map_only[c], edgecolor="none", label=c) for c in cats_only]
    ax3.legend(handles=handles3, loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=True, fontsize=8, ncol=1)
    plt.subplots_adjust(right=0.72)
    plt.savefig(OUT_TOP7_ONLY_PNG, dpi=350, bbox_inches="tight")
    plt.close()

    top_only_cols = [
        "CITY_NAME",
        "S_NAME",
        "dominant",
        "max_count",
        "topN_dominant",
        "topN_max_count",
        "match_type2",
        "dist_km",
    ]
    keep_top_only_cols = [c for c in top_only_cols if c in gdf_top_only.columns]
    gdf_top_only[keep_top_only_cols].to_csv(OUT_TOP7_ONLY_CSV, index=False, encoding="utf-8-sig")

    print("保存PNG(top7only):", OUT_TOP7_ONLY_PNG)
    print("保存CSV(top7only):", OUT_TOP7_ONLY_CSV)

    # 11) 都祁診療所 + 上位5施設（都祁を除外して上位抽出）で再計算
    top_ex_target = [f for f in facility_used_counts.index.tolist() if f != TARGET_FACILITY][:TOP_K_EXCLUDING_TARGET]
    selected_facilities = [TARGET_FACILITY] + top_ex_target
    selected_facilities = [f for f in selected_facilities if f in facility_cols]

    df_sel = df.copy()
    df_sel["sel_max_count"] = df_sel[selected_facilities].max(axis=1)
    df_sel["sel_dominant"] = df_sel[selected_facilities].idxmax(axis=1)
    df_sel.loc[df_sel["sel_max_count"] <= 0, "sel_dominant"] = np.nan

    sel_map = (
        df_sel[["_city_", "_sname_", "sel_dominant", "sel_max_count"]]
        .drop_duplicates(subset=["_city_", "_sname_"])
        .set_index(["_city_", "_sname_"])
    )
    gdf_sel = gdf30m.copy().join(sel_map, on=["_city_", "_sname_"])

    sel_missing = "未結合(都祁+上位5の利用0)"
    gdf_sel["sel_plot"] = gdf_sel["sel_dominant"].fillna(sel_missing)
    sel_cats = selected_facilities + [sel_missing]
    cmap_sel = matplotlib.colormaps.get_cmap("tab10").resampled(len(sel_cats))
    color_map_sel = {sel_cats[i]: cmap_sel(i) for i in range(len(sel_cats))}
    color_map_sel[sel_missing] = "#dddddd"
    gdf_sel["_color_sel_"] = gdf_sel["sel_plot"].map(color_map_sel)

    fig4, ax4 = plt.subplots(figsize=(12, 12))
    city_outline.plot(ax=ax4, color="#f5f5f5", edgecolor="#aaaaaa", linewidth=0.6)
    gdf_sel.plot(ax=ax4, color=gdf_sel["_color_sel_"], linewidth=0.2)
    clinic.plot(ax=ax4, color="white", marker="*", markersize=260, zorder=999)
    clinic.plot(ax=ax4, color="black", marker="*", markersize=180, zorder=1000)
    ax4.annotate(
        TARGET_FACILITY,
        xy=(cx, cy),
        xytext=(60, 40),
        textcoords="offset points",
        fontsize=11,
        color="black",
        zorder=1001,
        bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="black", lw=0.8, alpha=0.95),
        arrowprops=dict(arrowstyle="->", color="black", lw=1.2, shrinkA=0, shrinkB=0),
    )

    gdf_tsuge_sel = gdf_sel[gdf_sel["sel_dominant"] == TARGET_FACILITY].copy()
    if len(gdf_tsuge_sel) > 0:
        gdf_tsuge_sel.boundary.plot(ax=ax4, color="white", linewidth=3.0, zorder=19)
        gdf_tsuge_sel.boundary.plot(ax=ax4, color="red", linewidth=1.8, zorder=20)

    ax4.set_xlim(minx - padx, maxx + padx)
    ax4.set_ylim(miny - pady, maxy + pady)
    ax4.set_title("奈良市都祁診療所 30km圏内: 勢力圏（都祁診療所 + 上位5施設で再計算）")
    ax4.axis("off")

    handles4 = [Patch(facecolor=color_map_sel[c], edgecolor="none", label=c) for c in sel_cats]
    ax4.legend(handles=handles4, loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=True, fontsize=8, ncol=1)
    plt.subplots_adjust(right=0.72)
    plt.savefig(OUT_TSUGE_PLUS5_PNG, dpi=350, bbox_inches="tight")
    plt.close()

    sel_cols = [
        "CITY_NAME",
        "S_NAME",
        "dominant",
        "max_count",
        "sel_dominant",
        "sel_max_count",
        "match_type2",
        "dist_km",
    ]
    keep_sel_cols = [c for c in sel_cols if c in gdf_sel.columns]
    gdf_sel[keep_sel_cols].to_csv(OUT_TSUGE_PLUS5_CSV, index=False, encoding="utf-8-sig")

    print("対象施設(都祁+上位5):", selected_facilities)
    print("保存PNG(tsuge_plus5):", OUT_TSUGE_PLUS5_PNG)
    print("保存CSV(tsuge_plus5):", OUT_TSUGE_PLUS5_CSV)


if __name__ == "__main__":
    main()
