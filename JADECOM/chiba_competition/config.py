from __future__ import annotations

from pathlib import Path


BASE_DATA_DIR = Path("/Users/itotsubasa/Downloads/jadecom/4:6/千葉県")
SHP_PATH = BASE_DATA_DIR / "r2ka12.shp"
CAR30_TOWN_CSV = Path("/Users/itotsubasa/Downloads/aj.csv")

BASE_DIR = Path(__file__).resolve().parent
DEMAND_CSV = BASE_DIR / "data" / "h03_12_町丁目別医療需要者数_main_with_age.csv"
OUT_ROOT = BASE_DIR / "out"

DEFAULT_PASSWORD = "shibaura2026"
TOP_FACILITY_USERS = 60
TOP_K_HEATMAP = 10
TOP_K_EXCLUDING_TARGET = 5
TOP_TOWNS_FOR_GRAPH = 60

PREFECTURES = {
    "千葉県": {
        "label": "千葉県",
        "base_data_dir": BASE_DATA_DIR,
        "shp_path": SHP_PATH,
        "demand_csv": DEMAND_CSV,
        "car30_town_csv": CAR30_TOWN_CSV,
        "facilities": [
            {
                "key": "obitsu",
                "label": "小櫃診療所",
                "folder_name": "君津市国保小櫃診療所",
                "target_keyword": "君津市国保小櫃診療所",
                "car30_name": "君津市国保小櫃診療所",
                "ref_lat": 35.3237543,
                "ref_lon": 140.0540861,
            },
            {
                "key": "matsuoka",
                "label": "君津市国保松丘診療所",
                "folder_name": "君津市国保松丘診療所",
                "target_keyword": "君津市国保松丘診療所",
                "car30_name": "君津市国保松丘診療所",
                "ref_lat": 35.2575789,
                "ref_lon": 140.0594351,
            },
        ],
    }
}
