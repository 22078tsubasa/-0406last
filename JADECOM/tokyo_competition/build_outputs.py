from __future__ import annotations

import json
import math
import os
import re
import unicodedata
import zipfile
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager
from matplotlib.colors import Normalize
from matplotlib.patches import Patch
from shapely.geometry import Point

from config import (
    DEFAULT_PASSWORD,
    OUT_ROOT,
    PREFECTURES,
    TOP_FACILITY_USERS,
    TOP_K_EXCLUDING_TARGET,
    TOP_K_HEATMAP,
    TOP_TOWNS_FOR_GRAPH,
)

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

META_COLS = {
    "都道府県名",
    "市区町村名",
    "大字・町名",
    "字・丁目名",
    "町丁目名",
    "市区町村コード",
    "町丁字コード",
    "町丁字コード6桁",
    "TOWN_CODE_11",
    "地域階層レベル",
    "総数",
    "医療需要者数合計",
    "CITY_NAME_from_master",
    "S_NAME_from_master",
    "town_name_show",
    "KEY_CODE",
    "LON",
    "LAT",
    "dist_km",
}


def ntext(v: object) -> str:
    return unicodedata.normalize("NFKC", str(v)).replace("　", "").replace(" ", "").strip()


def clean_facility_name(name: str) -> str:
    s = unicodedata.normalize("NFKC", name)
    for token in ["_国内居住者・来訪者居住地分析", "_国内居住者・来訪者居住地"]:
        if token in s:
            s = s.split(token)[0]
            break
    s = re.sub(r"_\d+$", "", s).strip("_ ").strip()
    return s


def normalize_name(s: pd.Series) -> pd.Series:
    s = s.astype(str)
    s = s.str.replace("　", "", regex=False).str.replace(" ", "", regex=False).str.strip()
    s = s.str.replace(r"（.*?）", "", regex=True).str.replace(r"\(.*?\)", "", regex=True)
    s = s.str.replace("大字", "", regex=False)
    return s


def normalize_key_code(value: object) -> str:
    code = str(value).replace(".0", "").strip()
    if not code or code.lower() == "nan":
        return ""
    if not code.isdigit():
        code = re.sub(r"\D", "", code)
    if len(code) <= 2:
        return ""
    if len(code) < 11:
        return code.ljust(11, "0")
    return code[:11]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0088
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def read_town_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="cp932")
    need = {"コード", "町丁目名", "人数"}
    if not need.issubset(df.columns):
        return pd.DataFrame(columns=["TOWN_CODE_11", "town_name_show", "人数"])
    out = df[["コード", "町丁目名", "人数"]].copy()
    out["TOWN_CODE_11"] = (
        out["コード"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(11)
    )
    out["town_name_show"] = out["町丁目名"].astype(str).str.strip()
    out["人数"] = pd.to_numeric(out["人数"], errors="coerce").fillna(0)
    return out[["TOWN_CODE_11", "town_name_show", "人数"]]


def read_town_csv_from_zip(zip_path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(zip_path) as zf:
        candidates = sorted([name for name in zf.namelist() if re.search(r"(^|/)3_Towns_.*\.csv$", name)])
        if not candidates:
            return pd.DataFrame(columns=["TOWN_CODE_11", "town_name_show", "人数"])
        with zf.open(candidates[0]) as f:
            df = pd.read_csv(f, encoding="cp932")
    need = {"コード", "町丁目名", "人数"}
    if not need.issubset(df.columns):
        return pd.DataFrame(columns=["TOWN_CODE_11", "town_name_show", "人数"])
    out = df[["コード", "町丁目名", "人数"]].copy()
    out["TOWN_CODE_11"] = (
        out["コード"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(11)
    )
    out["town_name_show"] = out["町丁目名"].astype(str).str.strip()
    out["人数"] = pd.to_numeric(out["人数"], errors="coerce").fillna(0)
    return out[["TOWN_CODE_11", "town_name_show", "人数"]]


def collect_facility_frames(group_dir: Path) -> tuple[pd.DataFrame, list[str]]:
    base: pd.DataFrame | None = None
    facility_cols: list[str] = []
    used_names: set[str] = set()

    entries = sorted(group_dir.iterdir(), key=lambda p: p.name)
    for child in entries:
        if child.name.startswith("_") or child.name in {".DS_Store", "test"}:
            continue

        facility = clean_facility_name(child.stem if child.is_file() else child.name)
        if not facility:
            continue
        if facility in used_names:
            i = 2
            while f"{facility}_{i}" in used_names:
                i += 1
            facility = f"{facility}_{i}"
        used_names.add(facility)

        if child.is_dir():
            town_files = sorted(child.glob("*3_Towns_*.csv"))
            if not town_files:
                continue
            t = read_town_csv(town_files[0])
        elif child.is_file() and child.suffix.lower() == ".zip":
            t = read_town_csv_from_zip(child)
        else:
            continue

        if t.empty:
            continue
        t = (
            t.groupby(["TOWN_CODE_11", "town_name_show"], as_index=False)["人数"]
            .sum()
            .rename(columns={"人数": facility})
        )
        base = t if base is None else base.merge(t, on=["TOWN_CODE_11", "town_name_show"], how="outer")
        facility_cols.append(facility)

    if base is None:
        raise RuntimeError(f"3_Towns data not found: {group_dir}")
    return base, facility_cols


def load_demand_master(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"TOWN_CODE_11": str})
    if "TOWN_CODE_11" in df.columns:
        df["TOWN_CODE_11"] = df["TOWN_CODE_11"].fillna("").astype(str).str.zfill(11)
    elif {"市区町村コード", "町丁字コード"}.issubset(df.columns):
        city = (
            df["市区町村コード"]
            .fillna("")
            .astype(str)
            .str.replace(r"\.0$", "", regex=True)
            .str.zfill(5)
        )
        town = (
            df["町丁字コード"]
            .fillna("")
            .astype(str)
            .str.replace(r"\.0$", "", regex=True)
            .str.zfill(6)
        )
        df["TOWN_CODE_11"] = city + town
    else:
        raise RuntimeError(f"TOWN_CODE_11 columns missing: {path}")
    df["CITY_NAME_from_master"] = df["市区町村名"].fillna("").astype(str).str.strip()
    df["S_NAME_from_master"] = (df["大字・町名"].fillna("").astype(str) + df["字・丁目名"].fillna("").astype(str)).str.strip()
    df["town_name_show"] = df["町丁目名"].fillna("").astype(str).str.strip()
    if "地域階層レベル" in df.columns:
        df["地域階層レベル"] = pd.to_numeric(df["地域階層レベル"], errors="coerce")
        df = df.sort_values(["TOWN_CODE_11", "地域階層レベル"], ascending=[True, False], na_position="last")
    df = df.drop_duplicates("TOWN_CODE_11", keep="first").reset_index(drop=True)
    return df


def build_shp_lookup(shp_path: Path) -> pd.DataFrame:
    shp = gpd.read_file(shp_path)[["KEY_CODE", "CITY_NAME", "S_NAME"]].copy()
    shp["TOWN_CODE_11"] = shp["KEY_CODE"].map(normalize_key_code)
    shp["_city_"] = normalize_name(shp["CITY_NAME"])
    shp["_sname_"] = normalize_name(shp["S_NAME"])
    shp = shp[shp["TOWN_CODE_11"].ne("") & shp["S_NAME"].notna()].copy()
    return shp[["TOWN_CODE_11", "_city_", "_sname_"]].drop_duplicates()


def load_car30_town_codes(car30_csv: Path, shp_path: Path, facility_name: str, pref_name: str) -> set[str]:
    df = pd.read_csv(car30_csv, dtype={"KEYCODE1": str}, encoding="utf-8-sig")
    if "Name" not in df.columns or "KEYCODE1" not in df.columns:
        raise RuntimeError(f"car30 csv columns missing: {car30_csv}")
    name_mask = df["Name"].astype(str).str.contains(facility_name, regex=False, na=False)
    break_mask = (
        pd.to_numeric(df.get("FromBreak"), errors="coerce").fillna(-1).eq(0)
        & pd.to_numeric(df.get("ToBreak"), errors="coerce").fillna(-1).eq(30)
    )
    pref_mask = df.get("PREF_NAME", pd.Series("", index=df.index)).astype(str).eq(pref_name)
    picked = df[name_mask & break_mask & pref_mask].copy()
    if picked.empty:
        raise RuntimeError(f"car30 towns not found for: {facility_name}")
    picked["_city_"] = normalize_name(picked["CITY_NAME"])
    picked["_sname_"] = normalize_name(picked["S_NAME"])
    town_lookup = build_shp_lookup(shp_path)
    merged = picked.merge(town_lookup, on=["_city_", "_sname_"], how="left")
    codes = merged["TOWN_CODE_11"].fillna("").astype(str).tolist()
    out = {c for c in codes if c and c != "00000000000"}
    if not out:
        raise RuntimeError(f"car30 town-code match failed for: {facility_name}")
    return out


def build_matrix(pref_cfg: dict, facility_cfg: dict) -> tuple[pd.DataFrame, list[str]]:
    group_dir = pref_cfg["base_data_dir"] / facility_cfg["folder_name"]
    counts, facility_cols = collect_facility_frames(group_dir)
    demand = load_demand_master(pref_cfg["demand_csv"])

    shp = gpd.read_file(pref_cfg["shp_path"])[["KEY_CODE", "CITY_NAME", "S_NAME", "geometry"]].copy()
    shp["TOWN_CODE_11"] = shp["KEY_CODE"].map(normalize_key_code)
    shp = shp[shp["TOWN_CODE_11"].ne("") & shp["S_NAME"].notna()].copy()
    car30_codes = load_car30_town_codes(
        pref_cfg["car30_town_csv"],
        pref_cfg["shp_path"],
        facility_cfg["car30_name"],
        pref_cfg["label"],
    )
    shp = shp[shp["TOWN_CODE_11"].isin(car30_codes)].copy()
    shp = shp.drop_duplicates("TOWN_CODE_11").reset_index(drop=True)

    base = shp[["TOWN_CODE_11", "CITY_NAME", "S_NAME"]].copy()
    base["CITY_NAME_from_master"] = base["CITY_NAME"].fillna("").astype(str).str.strip()
    base["S_NAME_from_master"] = base["S_NAME"].fillna("").astype(str).str.strip()
    base["town_name_show"] = (base["CITY_NAME_from_master"] + base["S_NAME_from_master"]).str.strip()

    merged = base.merge(
        demand.drop(columns=["CITY_NAME_from_master", "S_NAME_from_master", "town_name_show"], errors="ignore"),
        on="TOWN_CODE_11",
        how="left",
    )
    merged["CITY_NAME_from_master"] = merged["CITY_NAME_from_master"].fillna(base["CITY_NAME_from_master"])
    merged["S_NAME_from_master"] = merged["S_NAME_from_master"].fillna(base["S_NAME_from_master"])
    merged["town_name_show"] = merged["town_name_show"].fillna(base["town_name_show"])
    merged = merged.merge(
        counts.drop(columns=["town_name_show"], errors="ignore"),
        on="TOWN_CODE_11",
        how="left",
    )
    for col in facility_cols:
        merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0)

    cent = shp.to_crs(6677).copy()
    cent["geometry"] = cent.geometry.centroid
    cent = cent.to_crs(4326)
    cent["LON"] = cent.geometry.x
    cent["LAT"] = cent.geometry.y

    merged = merged.merge(cent[["TOWN_CODE_11", "LON", "LAT"]], on="TOWN_CODE_11", how="left")
    merged["dist_km"] = merged.apply(
        lambda r: haversine_km(
            facility_cfg["ref_lat"],
            facility_cfg["ref_lon"],
            float(r["LAT"]),
            float(r["LON"]),
        )
        if pd.notna(r["LAT"]) and pd.notna(r["LON"])
        else np.nan,
        axis=1,
    )
    merged["total_patients"] = merged[facility_cols].sum(axis=1)
    merged["town"] = merged["town_name_show"]
    merged["town_norm"] = normalize_name(merged["town_name_show"]).astype(str)
    merged["match_type"] = "code_in_car30"
    merged = merged.sort_values(["dist_km", "CITY_NAME_from_master", "S_NAME_from_master"], na_position="last").reset_index(drop=True)
    return merged, facility_cols


def choose_top60_by_total_users(df: pd.DataFrame, facility_cols: list[str], target_keyword: str) -> tuple[list[str], pd.DataFrame]:
    totals = df[facility_cols].sum(axis=0).sort_values(ascending=False)
    selected = totals.head(TOP_FACILITY_USERS).index.tolist()
    target_candidates = [c for c in totals.index if target_keyword in str(c)]
    if target_candidates:
        target = target_candidates[0]
        if target not in selected and selected:
            selected = selected[:-1] + [target]
    rank = pd.DataFrame({"施設名": selected, "利用者数合計": totals.reindex(selected).fillna(0).values})
    rank = rank.sort_values("利用者数合計", ascending=False).reset_index(drop=True)
    rank.insert(0, "rank", np.arange(1, len(rank) + 1))
    rank["対象施設フラグ"] = rank["施設名"].astype(str).str.contains(target_keyword).astype(int)
    return rank["施設名"].tolist(), rank


def build_geo_join(df: pd.DataFrame, shp_path: Path, value_col: str, max_col: str) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    gdf = gpd.read_file(shp_path).copy()
    gdf["TOWN_CODE_11"] = gdf["KEY_CODE"].map(normalize_key_code)
    gdf["_city_"] = normalize_name(gdf["CITY_NAME"])
    gdf["_sname_"] = normalize_name(gdf["S_NAME"])
    gdf = gdf[gdf["TOWN_CODE_11"].ne("") & gdf["S_NAME"].notna()].copy()

    work = df.copy()
    work["TOWN_CODE_11"] = work["TOWN_CODE_11"].fillna("").astype(str).str.zfill(11)
    selected_cols = [c for c in df.columns if c not in META_COLS]
    work[value_col] = work[selected_cols].idxmax(axis=1)
    work[max_col] = work[selected_cols].max(axis=1)
    work.loc[work[max_col] <= 0, value_col] = np.nan

    m = work[["TOWN_CODE_11", value_col, max_col, "dist_km"]].drop_duplicates("TOWN_CODE_11")
    gdfm = gdf.merge(m, on="TOWN_CODE_11", how="inner")
    hit_cities = sorted(gdfm["_city_"].dropna().unique().tolist())
    city_outline = gdf[gdf["_city_"].isin(hit_cities)].dissolve(by="_city_", as_index=False)
    return gdfm, city_outline


def make_color_map(labels: list[str]) -> dict[str, tuple[float, float, float, float]]:
    cmap = plt.get_cmap("tab20", max(len(labels), 1))
    return {label: cmap(i) for i, label in enumerate(labels)}


def draw_territory(
    gdfm: gpd.GeoDataFrame,
    city_outline: gpd.GeoDataFrame,
    plot_col: str,
    title: str,
    out_png: Path,
    color_map: dict[str, object],
    ref_lon: float,
    ref_lat: float,
    target_label: str,
    legend_categories: list[str] | None = None,
) -> None:
    fig, ax = plt.subplots(figsize=(15, 15))
    if not city_outline.empty:
        city_outline.plot(ax=ax, color="#f5f5f5", edgecolor="#aaaaaa", linewidth=0.6)
    facecolors = gdfm[plot_col].map(color_map).fillna("#d9d9d9")
    gdfm.plot(ax=ax, color=facecolors, edgecolor="#d4d4d4", linewidth=0.18)

    clinic = gpd.GeoDataFrame({"name": [target_label]}, geometry=[Point(ref_lon, ref_lat)], crs="EPSG:4326").to_crs(gdfm.crs)
    clinic.plot(ax=ax, color="white", marker="*", markersize=260, zorder=999)
    clinic.plot(ax=ax, color="black", marker="*", markersize=180, zorder=1000)

    target_mask = gdfm[plot_col].astype(str).str.contains(target_label, na=False)
    if target_mask.any():
        gdfm[target_mask].boundary.plot(ax=ax, color="white", linewidth=3.0, zorder=19)
        gdfm[target_mask].boundary.plot(ax=ax, color="red", linewidth=2.0, zorder=20)

    cats = legend_categories if legend_categories is not None else list(color_map.keys())
    handles = [Patch(facecolor=color_map[c], edgecolor="none", label=c) for c in cats if c in color_map]
    ncol = 2 if len(handles) > 30 else 1
    fs = 7 if len(handles) > 20 else 8
    right_margin = 0.56 if ncol == 2 else 0.72
    ax.legend(
        handles=handles,
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
        fontsize=fs,
        ncol=ncol,
        frameon=True,
    )
    ax.set_title(title)
    ax.axis("off")
    ax.set_aspect("equal")
    plt.subplots_adjust(right=right_margin)
    plt.savefig(out_png, dpi=350, bbox_inches="tight")
    plt.close()


def render_top10_heatmap(
    df_part: pd.DataFrame,
    facility_cols: list[str],
    out_png: Path,
    out_csv: Path,
    target_keyword: str,
) -> None:
    totals = df_part[facility_cols].sum(axis=0).sort_values(ascending=False)
    top = totals.head(TOP_K_HEATMAP).index.tolist()
    mat = df_part[top].to_numpy(dtype=float)
    mat_for_color = np.log1p(np.clip(mat, a_min=0, a_max=None))

    pd.concat([df_part[["town_name_show", "dist_km"]], pd.DataFrame(mat, columns=top)], axis=1).to_csv(
        out_csv, index=False, encoding="utf-8-sig"
    )

    fig, ax = plt.subplots(figsize=(min(1.15 * TOP_K_HEATMAP + 10, 28), min(0.24 * len(df_part) + 8, 120)))
    vmax = float(np.nanmax(mat_for_color)) if mat_for_color.size else 1.0
    im = ax.imshow(mat_for_color, aspect="auto", norm=Normalize(vmin=0, vmax=vmax if vmax > 0 else 1))
    ax.set_xticks(np.arange(len(top)))
    ax.set_xticklabels(top, rotation=90, fontsize=11)
    labels = [
        f"{t} ({d:.1f}km)" if pd.notna(d) else t
        for t, d in zip(df_part["town_name_show"].astype(str), df_part["dist_km"])
    ]
    ax.set_yticks(np.arange(len(labels)))
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_title("自動車30分圏内: ヒートマップ（利用者数TOP60の中の上位10・上位60町丁目）", fontsize=14)
    if mat.shape[0] * mat.shape[1] <= 9000:
        for i in range(mat.shape[0]):
            for j in range(mat.shape[1]):
                v = mat[i, j]
                if v > 0:
                    ax.text(j, i, f"{int(v)}", ha="center", va="center", fontsize=5)
    ax.set_xticks(np.arange(-0.5, len(top), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(labels), 1), minor=True)
    ax.grid(which="minor", linewidth=0.18)
    ax.tick_params(which="minor", bottom=False, left=False)
    target_cols = [i for i, name in enumerate(top) if target_keyword in str(name)]
    for j in target_cols:
        ax.add_patch(plt.Rectangle((j - 0.5, -0.5), 1, len(labels), fill=False, linewidth=2.5, edgecolor="black"))
    cbar = fig.colorbar(im, ax=ax, fraction=0.02, pad=0.02)
    cbar.set_label("log(1 + 人数)", fontsize=10)
    plt.subplots_adjust(left=0.24, right=0.99, bottom=0.19, top=0.96)
    plt.savefig(out_png, dpi=320)
    plt.close()


def render_top3_matrix(df_part: pd.DataFrame, facility_cols: list[str], out_png: Path, out_csv: Path) -> None:
    values = df_part[facility_cols].to_numpy(dtype=float)
    top3_mask = np.zeros_like(values, dtype=bool)
    for i, row in enumerate(values):
        pos = np.where(row > 0)[0]
        if len(pos) == 0:
            continue
        top = pos[np.argsort(row[pos])[::-1]][:3]
        top3_mask[i, top] = True
    values_top3 = np.where(top3_mask, values, 0)

    pd.concat([df_part[["town_name_show", "dist_km"]], pd.DataFrame(values_top3, columns=facility_cols)], axis=1).to_csv(
        out_csv, index=False, encoding="utf-8-sig"
    )

    rgb = np.ones((values_top3.shape[0], values_top3.shape[1], 3), dtype=float)
    ranked = np.argsort(top3_mask.sum(axis=0))[::-1]
    palette = [np.array([1.00, 0.35, 0.35]), np.array([1.00, 0.70, 0.25]), np.array([1.00, 0.90, 0.35])]
    for idx, color in zip(ranked[:3], palette):
        mask = values_top3[:, idx] > 0
        rgb[mask, idx, :] = color
    gray_mask = (values_top3 > 0) & np.all(np.isclose(rgb, 1.0), axis=2)
    rgb[gray_mask, :] = np.array([0.92, 0.92, 0.92])

    fig, ax = plt.subplots(figsize=(min(0.34 * len(facility_cols) + 10, 70), min(0.24 * len(df_part) + 8, 120)))
    ax.imshow(rgb, aspect="auto")
    ax.set_xticks(np.arange(len(facility_cols)))
    ax.set_xticklabels(facility_cols, rotation=90, fontsize=8)
    labels = [
        f"{t} ({d:.1f}km)" if pd.notna(d) else t
        for t, d in zip(df_part["town_name_show"].astype(str), df_part["dist_km"])
    ]
    ax.set_yticks(np.arange(len(labels)))
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_title("町丁目 × 医療機関 マトリクス（利用者数TOP60・各町丁目の上位3のみ・上位60町丁目）", fontsize=14)
    ax.set_xticks(np.arange(-0.5, len(facility_cols), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(labels), 1), minor=True)
    ax.grid(which="minor", color="#222222", linewidth=0.35)
    ax.tick_params(which="minor", bottom=False, left=False)
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(0.8)
        spine.set_edgecolor("black")
    if values_top3.shape[0] * values_top3.shape[1] <= 15000:
        for i in range(values_top3.shape[0]):
            for j in range(values_top3.shape[1]):
                v = values_top3[i, j]
                if v > 0:
                    ax.text(j, i, f"{int(v)}", ha="center", va="center", fontsize=5)
    plt.subplots_adjust(left=0.24, right=0.98, bottom=0.18, top=0.95)
    plt.savefig(out_png, dpi=320)
    plt.close()


def render_graph(df: pd.DataFrame, facility_cols: list[str], out_png: Path, title: str) -> None:
    df60 = df.sort_values("dist_km", na_position="last").head(TOP_TOWNS_FOR_GRAPH).copy()
    totals = df60[facility_cols].sum(axis=0).sort_values(ascending=False)
    top_cols = totals.head(15).index.tolist()
    df60["その他"] = df60[facility_cols].sum(axis=1) - df60[top_cols].sum(axis=1)
    stack_cols = top_cols + ["その他"]

    labels = [
        f"{t} ({d:.1f}km)" if pd.notna(d) else t
        for t, d in zip(df60["town_name_show"].astype(str), df60["dist_km"])
    ]
    x = np.arange(len(df60))
    bottom = np.zeros(len(df60), dtype=float)
    cmap = plt.get_cmap("tab20")
    colors = [cmap(i % 20) for i in range(len(stack_cols) - 1)] + ["#d9d9d9"]

    fig, ax = plt.subplots(figsize=(20, 8))
    for i, col in enumerate(stack_cols):
        vals = df60[col].to_numpy(dtype=float)
        ax.bar(x, vals, bottom=bottom, label=col, color=colors[i], width=0.8)
        bottom += vals
    ax.set_title(title)
    ax.set_ylabel("人数")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=70, ha="right", fontsize=7)
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), frameon=True, fontsize=8)
    plt.tight_layout()
    plt.savefig(out_png, dpi=300)
    plt.close()


def build_top3_frequency(df_part: pd.DataFrame, facility_cols: list[str]) -> pd.Series:
    values = df_part[facility_cols].to_numpy(dtype=float)
    top3_mask = np.zeros_like(values, dtype=bool)
    for i, row in enumerate(values):
        pos = np.where(row > 0)[0]
        if len(pos) == 0:
            continue
        top = pos[np.argsort(row[pos])[::-1]][:3]
        top3_mask[i, top] = True
    return pd.Series(top3_mask.sum(axis=0), index=facility_cols).sort_values(ascending=False)


def export_for_facility(pref_key: str, pref_cfg: dict, facility_cfg: dict) -> dict:
    out_dir = OUT_ROOT / pref_key / facility_cfg["key"]
    out_dir.mkdir(parents=True, exist_ok=True)

    matrix, facility_cols = build_matrix(pref_cfg, facility_cfg)
    selected, selected_rank = choose_top60_by_total_users(matrix, facility_cols, facility_cfg["target_keyword"])

    matrix_path = out_dir / "town_facility_matrix.csv"
    rank_path = out_dir / "facility_rank_summary.csv"
    selected_path = out_dir / "selected_facilities.csv"
    base_matrix_path = out_dir / "base_matrix_readable.csv"
    graph_path = out_dir / "town_med_graph_top60.png"
    map_all_png = out_dir / "dominant_territory_all.png"
    map_all_csv = out_dir / "dominant_territory_all_result.csv"
    map_plus5_png = out_dir / "dominant_territory_target_plus5.png"
    map_plus5_csv = out_dir / "dominant_territory_target_plus5_result.csv"
    heatmap_png = out_dir / "town_med_heatmap_top10.png"
    heatmap_csv = out_dir / "town_med_heatmap_top10.csv"
    matrix_top3_png = out_dir / "town_med_matrix_top3.png"
    matrix_top3_csv = out_dir / "town_med_matrix_top3_only.csv"

    matrix.to_csv(matrix_path, index=False, encoding="utf-8-sig")
    selected_rank.to_csv(selected_path, index=False, encoding="utf-8-sig")

    df_top60 = matrix[["town_name_show", "CITY_NAME_from_master", "S_NAME_from_master", "TOWN_CODE_11", "dist_km", "LON", "LAT"] + selected].copy()
    df_part = df_top60.sort_values("dist_km", na_position="last").head(TOP_TOWNS_FOR_GRAPH).copy()
    facility_total_part = df_part[selected].sum(axis=0).sort_values(ascending=False)
    top3_frequency = build_top3_frequency(df_part, selected)
    rank = pd.DataFrame(
        {
            "facility": facility_total_part.index,
            "total_patients": facility_total_part.values,
            "top3_frequency": top3_frequency.reindex(facility_total_part.index).fillna(0).values,
        }
    )
    rank.to_csv(rank_path, index=False, encoding="utf-8-sig")
    df_part.to_csv(base_matrix_path, index=False, encoding="utf-8-sig")

    gdf_all, city_outline = build_geo_join(df_top60, pref_cfg["shp_path"], "dominant", "max_count")
    missing_label = "未結合(利用者数TOP施設の利用0 or データなし)"
    gdf_all["plot_label"] = gdf_all["dominant"].fillna(missing_label)
    all_labels = [c for c in gdf_all["plot_label"].dropna().astype(str).value_counts().index.tolist() if c != missing_label] + [missing_label]
    color_map_all = make_color_map(all_labels[:-1])
    color_map_all[missing_label] = "#dddddd"
    draw_territory(
        gdf_all,
        city_outline,
        "plot_label",
        f"{facility_cfg['label']} 競合分析 全体勢力図",
        map_all_png,
        color_map_all,
        facility_cfg["ref_lon"],
        facility_cfg["ref_lat"],
        facility_cfg["target_keyword"],
        legend_categories=all_labels,
    )
    gdf_all[["CITY_NAME", "S_NAME", "dominant", "max_count", "dist_km", "plot_label"]].to_csv(map_all_csv, index=False, encoding="utf-8-sig")

    top_other = [c for c in selected if facility_cfg["target_keyword"] not in c][:TOP_K_EXCLUDING_TARGET]
    target_candidates = [c for c in selected if facility_cfg["target_keyword"] in c]
    selected_plus5 = target_candidates[:1] + top_other
    if not selected_plus5:
        selected_plus5 = selected[: min(len(selected), TOP_K_EXCLUDING_TARGET + 1)]
    df_plus5 = matrix[["town_name_show", "CITY_NAME_from_master", "S_NAME_from_master", "TOWN_CODE_11", "dist_km", "LON", "LAT"] + selected_plus5].copy()
    gdf_plus5, city_outline_plus5 = build_geo_join(df_plus5, pref_cfg["shp_path"], "dominant_sel6", "max_count_sel6")
    other_label = "その他(6施設すべて0人)"
    gdf_plus5["plot_label"] = gdf_plus5["dominant_sel6"].fillna(other_label)
    plus5_labels = selected_plus5 + [other_label]
    color_map_plus5 = make_color_map(selected_plus5)
    color_map_plus5[other_label] = "#bbbbbb"
    draw_territory(
        gdf_plus5,
        city_outline_plus5,
        "plot_label",
        f"{facility_cfg['label']} + 上位5勢力図",
        map_plus5_png,
        color_map_plus5,
        facility_cfg["ref_lon"],
        facility_cfg["ref_lat"],
        facility_cfg["target_keyword"],
        legend_categories=plus5_labels,
    )
    gdf_plus5[["CITY_NAME", "S_NAME", "dominant_sel6", "max_count_sel6", "dist_km", "plot_label"]].to_csv(
        map_plus5_csv, index=False, encoding="utf-8-sig"
    )

    render_top10_heatmap(df_part, selected, heatmap_png, heatmap_csv, facility_cfg["target_keyword"])
    render_top3_matrix(df_part, selected, matrix_top3_png, matrix_top3_csv)
    render_graph(df_top60, selected, graph_path, f"{facility_cfg['label']} 近い順上位60町丁目 × 医療機関利用")

    manifest = {
        "prefecture": pref_cfg["label"],
        "facility": facility_cfg["label"],
        "scope": "自動車30分圏内の町丁目",
        "password_default": DEFAULT_PASSWORD,
        "images": {
            "全体勢力図": str(map_all_png),
            "対象施設+上位5勢力図": str(map_plus5_png),
            "上位10ヒートマップ図": str(heatmap_png),
            "上位3マトリクス図": str(matrix_top3_png),
            "グラフ": str(graph_path),
        },
        "csvs": {
            "全体勢力図データ": str(map_all_csv),
            "対象施設+上位5勢力図データ": str(map_plus5_csv),
            "上位10マトリクスCSV": str(heatmap_csv),
            "上位3マトリクスCSV": str(matrix_top3_csv),
            "施設ランキングCSV": str(rank_path),
            "選定施設CSV": str(selected_path),
            "表示用ベース行列CSV": str(base_matrix_path),
            "町丁目×医療機関統合CSV": str(matrix_path),
        },
        "car30_town_count": int(len(matrix)),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    registry: dict[str, dict] = {}
    for pref_key, pref_cfg in PREFECTURES.items():
        registry[pref_key] = {"label": pref_cfg["label"], "facilities": []}
        for facility_cfg in pref_cfg["facilities"]:
            manifest = export_for_facility(pref_key, pref_cfg, facility_cfg)
            registry[pref_key]["facilities"].append(
                {
                    "key": facility_cfg["key"],
                    "label": facility_cfg["label"],
                    "manifest": str(OUT_ROOT / pref_key / facility_cfg["key"] / "manifest.json"),
                }
            )
            print("saved:", manifest["facility"])
    (OUT_ROOT / "registry.json").write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
    print("registry:", OUT_ROOT / "registry.json")


if __name__ == "__main__":
    main()
