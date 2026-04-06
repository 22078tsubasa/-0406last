from __future__ import annotations

from pathlib import Path


BASE_DATA_DIR = Path("/Users/itotsubasa/Downloads/jadecom/4:6/新潟")
SHP_PATH = BASE_DATA_DIR / "r2ka15.shp"
H03_CSV = BASE_DATA_DIR / "h03_15.csv"

BASE_DIR = Path(__file__).resolve().parent
OUT_ROOT = BASE_DIR / "out"

DEFAULT_PASSWORD = "shibaura2026"
TOP_FACILITY_USERS = 60
TOP_K_HEATMAP = 10
TOP_K_EXCLUDING_TARGET = 5
TOP_TOWNS_FOR_GRAPH = 60

DEMAND_XLSX = BASE_DIR / "main_with_age_niigata_h03_15.xlsx"
DEMAND_CSV = BASE_DIR / "main_with_age_niigata_h03_15_main_with_age.csv"

PREFECTURES = {
    "新潟県": {
        "label": "新潟県",
        "base_data_dir": BASE_DATA_DIR,
        "shp_path": SHP_PATH,
        "h03_csv": H03_CSV,
        "demand_csv": DEMAND_CSV,
        "facilities": [
            {
                "key": "yukiakari",
                "label": "公益社団法人 地域医療振興協会 今泉記念館 ゆきあかり診療所",
                "folder_name": "公益社団法人　地域医療振興協会　今泉記念館　ゆきあかり診療所",
                "target_keyword": "ゆきあかり診療所",
                "car30_town_csv": Path("/Users/itotsubasa/Downloads/aj.csv"),
                "car30_name": "今泉記念館　ゆきあかり診療所",
                # 最短到達町丁目の重心を暫定採用
                "ref_lat": 36.998166744853435,
                "ref_lon": 138.82586439365926,
            },
        ],
    }
}
