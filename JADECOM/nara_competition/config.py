from __future__ import annotations

from pathlib import Path


BASE_DATA_DIR = Path("/Users/itotsubasa/Downloads/jadecom/4:6/奈良")
SHP_PATH = BASE_DATA_DIR / "r2ka29.shp"
CAR30_TOWN_CSV = Path("/Users/itotsubasa/Downloads/aj.csv")

BASE_DIR = Path(__file__).resolve().parent
DEMAND_CSV = BASE_DIR / "data" / "h03_29_町丁目別医療需要者数_main_with_age.csv"
OUT_ROOT = BASE_DIR / "out"

DEFAULT_PASSWORD = "shibaura2026"
TOP_FACILITY_USERS = 60
TOP_K_HEATMAP = 10
TOP_K_EXCLUDING_TARGET = 5
TOP_TOWNS_FOR_GRAPH = 60

PREFECTURES = {
    "奈良県": {
        "label": "奈良県",
        "base_data_dir": BASE_DATA_DIR,
        "shp_path": SHP_PATH,
        "demand_csv": DEMAND_CSV,
        "car30_town_csv": CAR30_TOWN_CSV,
        "facilities": [
            {
                "key": "tawara",
                "label": "奈良市立田原診療所",
                "folder_name": "奈良市立田原診療所_競合リスト",
                "target_keyword": "奈良市立田原診療所",
                "car30_name": "奈良市立田原診療所",
                "ref_lat": 34.65827498,
                "ref_lon": 135.9103214,
            },
            {
                "key": "tsukigase",
                "label": "奈良市立月ヶ瀬診療所",
                "folder_name": "奈良市立月ヶ瀬診療所_競合リスト",
                "target_keyword": "奈良市立月ヶ瀬診療所",
                "car30_name": "奈良市立月ヶ瀬診療所",
                "ref_lat": 34.71102276,
                "ref_lon": 136.0445641,
            },
            {
                "key": "koto",
                "label": "奈良市立興東診療所",
                "folder_name": "奈良市立興東診療所_競合リスト",
                "target_keyword": "奈良市立興東診療所",
                "car30_name": "奈良市立興東診療所",
                "ref_lat": 34.71617207,
                "ref_lon": 135.9227832,
            },
            {
                "key": "asuka",
                "label": "明日香村国民健康保険診療所",
                "folder_name": "明日香村国民健康保険診療所_競合リスト",
                "target_keyword": "明日香村国民健康保険診療所",
                "car30_name": "明日香村国民健康保険診療所",
                "ref_lat": 34.46794683,
                "ref_lon": 135.8142848,
            },
            {
                "key": "tsuge",
                "label": "奈良市立都祁診療所",
                "source_path": BASE_DATA_DIR / "都祁診療所周辺の町丁目_各医療施設利用数_30km.xlsx",
                "target_keyword": "都祁診療所",
                "car30_name": "奈良市立都祁診療所",
                "ref_lat": 34.60382273,
                "ref_lon": 135.9573753,
            },
        ],
    }
}
