from __future__ import annotations

from pathlib import Path


BASE_DATA_DIR = Path("/Users/itotsubasa/Downloads/jadecom/4:6/山口")
SHP_PATH = BASE_DATA_DIR / "r2ka35.shp"
CAR30_TOWN_CSV = Path("/Users/itotsubasa/Downloads/aj.csv")

BASE_DIR = Path(__file__).resolve().parent
DEMAND_CSV = BASE_DIR / "data" / "h03_35_町丁目別医療需要者数_main_with_age.csv"
OUT_ROOT = BASE_DIR / "out"

DEFAULT_PASSWORD = "shibaura2026"
TOP_FACILITY_USERS = 60
TOP_K_HEATMAP = 10
TOP_K_EXCLUDING_TARGET = 5
TOP_TOWNS_FOR_GRAPH = 60

PREFECTURES = {
    "山口県": {
        "label": "山口県",
        "base_data_dir": BASE_DATA_DIR,
        "shp_path": SHP_PATH,
        "demand_csv": DEMAND_CSV,
        "car30_town_csv": CAR30_TOWN_CSV,
        "facilities": [
            {
                "key": "tokuji",
                "label": "山口市徳地診療所",
                "folder_name": "山口市徳地診療所_競合リスト_20260406_040854",
                "target_keyword": "山口市徳地診療所",
                "car30_name": "山口市徳地診療所（とくぢ地域医療センター）",
                "ref_lat": 34.1908912,
                "ref_lon": 131.65798,
            },
        ],
    }
}
