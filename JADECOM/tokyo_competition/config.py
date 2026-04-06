from __future__ import annotations

from pathlib import Path


BASE_DATA_DIR = Path("/Users/itotsubasa/Downloads/jadecom/4:6/東京")
SHP_PATH = BASE_DATA_DIR / "r2ka13.shp"
DEMAND_CSV = BASE_DATA_DIR / "003_13_町丁目別医療需要者数.csv"
CAR30_TOWN_CSV = Path("/Users/itotsubasa/Downloads/aj.csv")

BASE_DIR = Path(__file__).resolve().parent
OUT_ROOT = BASE_DIR / "out"

DEFAULT_PASSWORD = "shibaura2026"
TOP_FACILITY_USERS = 60
TOP_K_HEATMAP = 10
TOP_K_EXCLUDING_TARGET = 5
TOP_TOWNS_FOR_GRAPH = 60

PREFECTURES = {
    "東京都": {
        "label": "東京都",
        "base_data_dir": BASE_DATA_DIR,
        "shp_path": SHP_PATH,
        "demand_csv": DEMAND_CSV,
        "car30_town_csv": CAR30_TOWN_CSV,
        "facilities": [
            {
                "key": "furusato",
                "label": "古里診療所",
                "folder_name": "古里診療所",
                "target_keyword": "古里診療所",
                "car30_name": "古里診療所",
                # 奥多摩町小丹波の町丁目重心。古里診療所の至近町丁目として採用。
                "ref_lat": 35.82025415160783,
                "ref_lon": 139.14030023168286,
            },
        ],
    }
}
