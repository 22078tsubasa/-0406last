from __future__ import annotations

from pathlib import Path


BASE_DATA_DIR = Path("/Users/itotsubasa/Downloads/jadecom/4:6/北海道")
SHP_PATH = BASE_DATA_DIR / "r2ka01.shp"
CAR30_TOWN_CSV = Path("/Users/itotsubasa/Downloads/北青.csv")

BASE_DIR = Path(__file__).resolve().parent
DEMAND_CSV = BASE_DIR / "data" / "h03_01_町丁目別医療需要者数_main_with_age.csv"
OUT_ROOT = BASE_DIR / "out"

DEFAULT_PASSWORD = "shibaura2026"
TOP_FACILITY_USERS = 60
TOP_K_HEATMAP = 10
TOP_K_EXCLUDING_TARGET = 5
TOP_TOWNS_FOR_GRAPH = 60

PREFECTURES = {
    "北海道": {
        "label": "北海道",
        "base_data_dir": BASE_DATA_DIR,
        "shp_path": SHP_PATH,
        "demand_csv": DEMAND_CSV,
        "car30_town_csv": CAR30_TOWN_CSV,
        "facilities": [
            {
                "key": "toyokoro",
                "label": "豊頃町立豊頃医院",
                "folder_name": "豊頃町立豊頃医院",
                "target_keyword": "豊頃町立豊頃医院",
                "car30_name": "豊頃町立豊頃医院",
                "ref_lat": 42.79445488,
                "ref_lon": 143.5133782,
            },
        ],
    }
}
