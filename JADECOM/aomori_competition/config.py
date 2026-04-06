from __future__ import annotations

from pathlib import Path


BASE_DATA_DIR = Path("/Users/itotsubasa/Downloads/jadecom/4:6/青森")
SHP_PATH = BASE_DATA_DIR / "r2ka02.shp"
CAR30_TOWN_CSV = Path("/Users/itotsubasa/Downloads/北青.csv")

BASE_DIR = Path(__file__).resolve().parent
DEMAND_CSV = BASE_DIR / "data" / "h03_02_町丁目別医療需要者数_main_with_age.csv"
OUT_ROOT = BASE_DIR / "out"

DEFAULT_PASSWORD = "shibaura2026"
TOP_FACILITY_USERS = 60
TOP_K_HEATMAP = 10
TOP_K_EXCLUDING_TARGET = 5
TOP_TOWNS_FOR_GRAPH = 60

PREFECTURES = {
    "青森県": {
        "label": "青森県",
        "base_data_dir": BASE_DATA_DIR,
        "shp_path": SHP_PATH,
        "demand_csv": DEMAND_CSV,
        "car30_town_csv": CAR30_TOWN_CSV,
        "facilities": [
            {
                "key": "shiranuka",
                "label": "白糠診療所",
                "folder_name": "白糠診療所",
                "target_keyword": "白糠診療所",
                "car30_name": "白糠診療所",
                "ref_lat": 41.1455479,
                "ref_lon": 141.3854703,
            },
            {
                "key": "higashidori",
                "label": "東通地域医療センター(東通村保健福祉センター・東通村診療所・介護老人保健施設のはなしょうぶ)",
                "folder_name": "東通地域医療センター(東通村保健福祉センター・東通村診療所・介護老人保健施設のはなしょうぶ)",
                "target_keyword": "東通地域医療センター",
                "car30_name": "東通地域医療センター",
                "ref_lat": 41.27693,
                "ref_lon": 141.3346803,
            },
        ],
    }
}
