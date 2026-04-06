from __future__ import annotations

from pathlib import Path


BASE_DATA_DIR = Path("/Users/itotsubasa/Downloads/jadecom/4:6/三重")
SHP_PATH = BASE_DATA_DIR / "r2ka24.shp"
CAR30_TOWN_CSV = Path("/Users/itotsubasa/Downloads/aj.csv")

BASE_DIR = Path(__file__).resolve().parent
DEMAND_CSV = BASE_DIR / "data" / "h03_24_町丁目別医療需要者数_main_with_age.csv"
OUT_ROOT = BASE_DIR / "out"

DEFAULT_PASSWORD = "shibaura2026"
TOP_FACILITY_USERS = 60
TOP_K_HEATMAP = 10
TOP_K_EXCLUDING_TARGET = 5
TOP_TOWNS_FOR_GRAPH = 60

PREFECTURES = {
    "三重県": {
        "label": "三重県",
        "base_data_dir": BASE_DATA_DIR,
        "shp_path": SHP_PATH,
        "demand_csv": DEMAND_CSV,
        "car30_town_csv": CAR30_TOWN_CSV,
        "facilities": [
            {
                "key": "nagaoka",
                "label": "鳥羽市立長岡診療所",
                "folder_name": "鳥羽市立長岡診療所",
                "target_keyword": "鳥羽市立長岡診療所",
                "car30_name": "鳥羽市立長岡診療所",
                "ref_lat": 34.38959874,
                "ref_lon": 136.9022996,
            },
            {
                "key": "hamajima",
                "label": "志摩市立国民健康保険浜島診療所",
                "folder_name": "志摩市立国民健康保険浜島診療所",
                "target_keyword": "志摩市立国民健康保険浜島診療所",
                "car30_name": "志摩市立国民健康保険浜島診療所",
                "ref_lat": 34.29827,
                "ref_lon": 136.7489,
            },
        ],
    }
}
