from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


INPUT_CSV = Path(
    "/Users/itotsubasa/IdeaProjects/pythoN/JADECOM/佐々総合病院/競合分析/佐々総合病院周辺の町丁目_各医療施設利用数_KLA統合_tokyo_car30_match_with_dist.csv"
)
OUT_DIR = Path(
    "/Users/itotsubasa/Library/CloudStorage/OneDrive-SIT/L3S（社会システム科学研究室） - ドキュメント/0共-地域医療振興協会/2025年度/佐々総合病院_競合分析_KLA集計結果/競合分析/一部抜粋（都祁診療所と同様の見せ方）"
)
OUT_PNG = OUT_DIR / "town_med_graph_top60.png"

TOP_TOWNS = 60
TOP_FACILITIES_FOR_STACK = 15

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


def main() -> None:
    plt.rcParams["font.family"] = "Hiragino Sans"
    plt.rcParams["axes.unicode_minus"] = False

    df = pd.read_csv(INPUT_CSV)
    df["dist_km"] = pd.to_numeric(df["dist_km"], errors="coerce")

    facility_cols = [c for c in df.columns if c not in META_COLS]
    for c in facility_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    # 都祁版と同様に「距離の近い順上位60町丁目」を可視化
    df60 = df.sort_values("dist_km", na_position="last").head(TOP_TOWNS).copy()

    # 積み上げは上位15施設 + その他
    totals = df60[facility_cols].sum(axis=0).sort_values(ascending=False)
    top_cols = totals.head(TOP_FACILITIES_FOR_STACK).index.tolist()
    df60["その他"] = df60[facility_cols].sum(axis=1) - df60[top_cols].sum(axis=1)
    stack_cols = top_cols + ["その他"]

    labels = []
    for _, r in df60.iterrows():
        town = str(r.get("S_NAME_from_master", r.get("town", "")))
        d = r.get("dist_km", np.nan)
        if pd.notna(d):
            labels.append(f"{town} ({float(d):.1f}km)")
        else:
            labels.append(town)

    x = np.arange(len(df60))
    bottom = np.zeros(len(df60), dtype=float)

    fig, ax = plt.subplots(figsize=(20, 8))
    cmap = plt.get_cmap("tab20")
    colors = [cmap(i % 20) for i in range(len(stack_cols) - 1)] + ["#d9d9d9"]

    for i, col in enumerate(stack_cols):
        v = df60[col].to_numpy(dtype=float)
        ax.bar(x, v, bottom=bottom, label=col, color=colors[i], width=0.8)
        bottom += v

    ax.set_title("佐々総合病院周辺（近い順上位60）× 医療機関利用（月人数）", fontsize=13)
    ax.set_ylabel("人数")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=70, ha="right", fontsize=7)
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), frameon=True, fontsize=9)
    plt.tight_layout()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUT_PNG, dpi=300)
    plt.close()

    print("rows:", len(df60))
    print("stack facilities:", len(stack_cols))
    print("saved:", OUT_PNG)


if __name__ == "__main__":
    main()
