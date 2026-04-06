from __future__ import annotations

from pathlib import Path


BASE_DATA_DIR = Path("/Users/itotsubasa/Downloads/jadecom/4:6/神奈川")
SHP_PATH = BASE_DATA_DIR / "r2ka14.shp"
CAR30_TOWN_CSV = Path("/Users/itotsubasa/Downloads/aj.csv")

BASE_DIR = Path(__file__).resolve().parent
DEMAND_CSV = BASE_DIR / "data" / "h03_14_町丁目別医療需要者数_main_with_age.csv"
OUT_ROOT = BASE_DIR / "out"

DEFAULT_PASSWORD = "shibaura2026"
TOP_FACILITY_USERS = 60
TOP_K_HEATMAP = 10
TOP_K_EXCLUDING_TARGET = 5
TOP_TOWNS_FOR_GRAPH = 60

PREFECTURES = {
    "神奈川県": {
        "label": "神奈川県",
        "base_data_dir": BASE_DATA_DIR,
        "shp_path": SHP_PATH,
        "demand_csv": DEMAND_CSV,
        "car30_town_csv": CAR30_TOWN_CSV,
        "facilities": [
            {
                "key": "yamakita",
                "label": "山北町立山北診療所",
                "folder_name": "山北町立山北診療所",
                "target_keyword": "山北町立山北診療所",
                "car30_name": "山北町立山北診療所",
                "ref_lat": 35.3644966,
                "ref_lon": 139.0366779,
            },
            {
                "key": "manazuru",
                "label": "真鶴町国民健康保険診療所",
                "folder_name": "真鶴町国民健康保険診療所",
                "target_keyword": "真鶴町国民健康保険診療所",
                "car30_name": "真鶴町国民健康保険診療所",
                "ref_lat": 35.1574694,
                "ref_lon": 139.1345361,
            },
        ],
    }
}
