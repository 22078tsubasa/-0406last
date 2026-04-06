from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pandas as pd


BASE_DIR = Path("/Users/itotsubasa/IdeaProjects/pythoN/JADECOM/佐々総合病院/競合分析")
ASSOC_ZIP_DIR = Path(
    "/Users/itotsubasa/Library/CloudStorage/OneDrive-SIT/L3S（社会システム科学研究室） - ドキュメント/0共-地域医療振興協会/2025年度/佐々総合病院_競合分析_KLA集計結果/佐々総合_競合_KLA_協会修正後"
)
TEMPLATE_CSV = BASE_DIR / "佐々総合病院周辺の町丁目_各医療施設利用数_KLA統合_tokyo_car30_match_with_dist.csv"
OUT_DIR = Path("/Users/itotsubasa/IdeaProjects/pythoN/JADECOM/佐々総合病院/協会修正後")

OUT_MATRIX_CSV = OUT_DIR / "佐々総合病院周辺の町丁目_各医療施設利用数_KLA統合_tokyo_car30_match_with_dist_協会修正後.csv"
OUT_MATRIX_XLSX = OUT_DIR / "佐々総合病院周辺の町丁目_各医療施設利用数_KLA統合_tokyo_car30_match_with_dist_協会修正後.xlsx"
OUT_FAC_MISS = OUT_DIR / "協会修正後_facility_unmatched_list.csv"

SUFFIX = "_国内居住者・来訪者居住地分析_20240401_20250331"
META_COLS = {
    "town",
    "town_norm",
    "CITY_NAME_from_master",
    "S_NAME_from_master",
    "LON",
    "LAT",
    "dist_km",
    "total_87",
}


def normalize_text(s: str) -> str:
    return str(s).replace("　", "").replace(" ", "").strip()


def parse_facility_name(name: str) -> str:
    n = name
    if n.endswith(SUFFIX):
        n = n[: -len(SUFFIX)]
    return n.strip()


def parse_city_sname_from_town(town: str) -> tuple[str, str]:
    s = normalize_text(town)
    m = re.match(r"^(.+?[市区町村])(.*)$", s)
    if m:
        return m.group(1), m.group(2)
    return "", s


def read_towns_zip(zp: Path) -> pd.DataFrame:
    # zip解凍せずCSV読み込み
    import zipfile
    from io import BytesIO

    with zipfile.ZipFile(zp) as zf:
        members = [n for n in zf.namelist() if "3_Towns" in Path(n).name]
        if not members:
            return pd.DataFrame(columns=["key", "人数"])
        b = zf.read(members[0])

    df = pd.read_csv(BytesIO(b), encoding="cp932")
    need = {"町丁目名", "人数"}
    if not need.issubset(df.columns):
        return pd.DataFrame(columns=["key", "人数"])

    out = df[["町丁目名", "人数"]].copy()
    out["人数"] = pd.to_numeric(out["人数"], errors="coerce").fillna(0)
    cs = out["町丁目名"].map(parse_city_sname_from_town)
    out["CITY_NAME_from_master"] = [x[0] for x in cs]
    out["S_NAME_from_master"] = [x[1] for x in cs]
    out["key"] = (out["CITY_NAME_from_master"].astype(str) + out["S_NAME_from_master"].astype(str)).map(normalize_text)
    out = out.groupby("key", as_index=False)["人数"].sum()
    return out


def rebuild_matrix() -> tuple[pd.DataFrame, list[str]]:
    base = pd.read_csv(TEMPLATE_CSV)
    facility_cols = [c for c in base.columns if c not in META_COLS]

    base["key"] = (
        base["CITY_NAME_from_master"].fillna("").astype(str)
        + base["S_NAME_from_master"].fillna("").astype(str)
    ).map(normalize_text)

    # 初期化
    for c in facility_cols:
        base[c] = 0.0

    matched_facilities: list[str] = []
    for zp in sorted(ASSOC_ZIP_DIR.glob("*.zip")):
        fcol = parse_facility_name(zp.stem)
        if fcol not in facility_cols:
            continue
        t = read_towns_zip(zp)
        if t.empty:
            continue
        s = t.set_index("key")["人数"]
        base[fcol] = base["key"].map(s).fillna(0)
        matched_facilities.append(fcol)

    base["total_87"] = base[facility_cols].sum(axis=1)
    base = base.drop(columns=["key"])
    return base, sorted(set(matched_facilities))


def run_visualization_with_new_input() -> None:
    script_path = BASE_DIR / "build_sasa_usersTop60_tsuge_style_fix60.py"
    spec = importlib.util.spec_from_file_location("fix60_mod", script_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)

    # 入出力先を差し替え
    mod.MATRIX_CSV = OUT_MATRIX_CSV
    mod.DOWNLOAD_OUT_DIR = OUT_DIR
    mod.OUT_TERRITORY_TOP60_PNG = OUT_DIR / "dominant_territory_sasa_car30_usersTop60_allLegend.png"
    mod.OUT_TERRITORY_TOP60_CSV = OUT_DIR / "dominant_territory_sasa_car30_usersTop60_allLegend_result.csv"
    mod.OUT_TERRITORY_PLUS5_PNG = OUT_DIR / "dominant_territory_sasa_car30_sasaPlus5_other_allLegend.png"
    mod.OUT_TERRITORY_PLUS5_CSV = OUT_DIR / "dominant_territory_sasa_car30_sasaPlus5_other_allLegend_result.csv"
    mod.OUT_MATRIX_TOP3_PNG = OUT_DIR / "sasa_car30_usersTop60_town_med_matrix_上位3_町丁目60.png"
    mod.OUT_MATRIX_TOP3_CSV = OUT_DIR / "sasa_car30_usersTop60_town_med_matrix_上位3のみ_町丁目60.csv"
    mod.OUT_HEATMAP_TOP10_PNG = OUT_DIR / "sasa_car30_usersTop60_town_med_heatmap_上位10_町丁目60.png"
    mod.OUT_HEATMAP_TOP10_CSV = OUT_DIR / "sasa_car30_usersTop60_town_med_matrix_上位10_町丁目60.csv"
    mod.OUT_RANK_CSV = OUT_DIR / "sasa_car30_usersTop60_facility_rank_summary.csv"
    mod.OUT_SELECTED_FACILITIES_CSV = OUT_DIR / "sasa_car30_usersTop60_selected_facilities.csv"
    mod.main()


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rebuilt, matched_facilities = rebuild_matrix()
    rebuilt.to_csv(OUT_MATRIX_CSV, index=False, encoding="utf-8-sig")
    with pd.ExcelWriter(OUT_MATRIX_XLSX, engine="openpyxl") as w:
        rebuilt.to_excel(w, index=False, sheet_name="Sheet1")

    facility_cols = [c for c in rebuilt.columns if c not in META_COLS]
    miss = sorted(set(facility_cols) - set(matched_facilities))
    pd.DataFrame({"matched_facility": matched_facilities}).to_csv(OUT_DIR / "協会修正後_facility_matched_list.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame({"unmatched_facility": miss}).to_csv(OUT_FAC_MISS, index=False, encoding="utf-8-sig")

    run_visualization_with_new_input()

    print("saved:", OUT_MATRIX_CSV)
    print("saved:", OUT_MATRIX_XLSX)
    print("matched facility count:", len(matched_facilities))
    print("unmatched facility count:", len(miss))
    print("saved visuals dir:", OUT_DIR)


if __name__ == "__main__":
    main()
