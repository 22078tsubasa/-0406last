from __future__ import annotations

from pathlib import Path


BASE_DATA_DIR = Path("/Users/itotsubasa/Downloads/jadecom/4:6/群馬")
SHP_PATH = BASE_DATA_DIR / "r2ka10.shp"
CAR30_TOWN_CSV = Path("/Users/itotsubasa/Downloads/aj.csv")

BASE_DIR = Path(__file__).resolve().parent
DEMAND_CSV = BASE_DIR / "data" / "h03_10_町丁目別医療需要者数_main_with_age.csv"
OUT_ROOT = BASE_DIR / "out"

DEFAULT_PASSWORD = "shibaura2026"
TOP_FACILITY_USERS = 60
TOP_K_HEATMAP = 10
TOP_K_EXCLUDING_TARGET = 5
TOP_TOWNS_FOR_GRAPH = 60

PREFECTURES = {
    "群馬県": {
        "label": "群馬県",
        "base_data_dir": BASE_DATA_DIR,
        "shp_path": SHP_PATH,
        "demand_csv": DEMAND_CSV,
        "car30_town_csv": CAR30_TOWN_CSV,
        "facilities": [
            {
                "key": "kuni",
                "label": "六合診療所",
                "folder_name": "六合診療所",
                "target_keyword": "六合診療所",
                "car30_name": "六合医療センター（六合診療所）",
                "ref_lat": 36.64952,
                "ref_lon": 138.6516,
            },
            {
                "key": "tsumagoi",
                "label": "嬬恋村国民健康保険診療所",
                "folder_name": "嬬恋村国民健康保険診療所",
                "target_keyword": "嬬恋村国民健康保険診療所",
                "car30_name": "嬬恋村国民健康保険診療所",
                "ref_lat": 36.53502,
                "ref_lon": 138.5498,
            },
        ],
    }
}
