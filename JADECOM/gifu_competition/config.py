from __future__ import annotations

from pathlib import Path


BASE_DATA_DIR = Path("/Users/itotsubasa/Downloads/jadecom/4:6/岐阜")
SHP_PATH = BASE_DATA_DIR / "r2ka21.shp"
CAR30_TOWN_CSV = Path("/Users/itotsubasa/Downloads/aj.csv")

BASE_DIR = Path(__file__).resolve().parent
DEMAND_CSV = BASE_DIR / "data" / "h03_21_町丁目別医療需要者数_main_with_age.csv"
OUT_ROOT = BASE_DIR / "out"

DEFAULT_PASSWORD = "shibaura2026"
TOP_FACILITY_USERS = 60
TOP_K_HEATMAP = 10
TOP_K_EXCLUDING_TARGET = 5
TOP_TOWNS_FOR_GRAPH = 60

PREFECTURES = {
    "岐阜県": {
        "label": "岐阜県",
        "base_data_dir": BASE_DATA_DIR,
        "shp_path": SHP_PATH,
        "demand_csv": DEMAND_CSV,
        "car30_town_csv": CAR30_TOWN_CSV,
        "facilities": [
            {
                "key": "kasuga",
                "label": "揖斐川町春日診療所",
                "folder_name": "揖斐川町春日診療所",
                "target_keyword": "揖斐川町春日診療所",
                "car30_name": "揖斐川町春日診療所",
                "ref_lat": 35.46789871,
                "ref_lon": 136.487841,
            },
            {
                "key": "tanigumi",
                "label": "揖斐川町谷汲中央診療所",
                "folder_name": "揖斐川町谷汲中央診療所_20260406",
                "target_keyword": "揖斐川町谷汲中央診療所",
                "car30_name": "揖斐川町谷汲中央診療所",
                "ref_lat": 35.5266975,
                "ref_lon": 136.6102667,
            },
            {
                "key": "tsubogawa",
                "label": "関市国民健康保険津保川診療所",
                "folder_name": "関市国民健康保険津保川診療所",
                "target_keyword": "関市国民健康保険津保川診療所",
                "car30_name": "関市国民健康保険津保川診療所",
                "ref_lat": 35.58341397,
                "ref_lon": 137.0137903,
            },
            {
                "key": "yamaoka",
                "label": "恵那市国民健康保険山岡診療所",
                "folder_name": "恵那市国民健康保険山岡診療所_競合リスト",
                "target_keyword": "恵那市国民健康保険山岡診療所",
                "car30_name": "恵那市国民健康保険山岡診療所",
                "ref_lat": 35.35311498,
                "ref_lon": 137.3806404,
            },
            {
                "key": "ibigawa",
                "label": "いびがわ診療所",
                "folder_name": "いびがわ診療所_競合リスト",
                "target_keyword": "いびがわ診療所",
                "car30_name": "いびがわ診療所",
                "ref_lat": 35.48287457,
                "ref_lon": 136.5740091,
            },
        ],
    }
}
