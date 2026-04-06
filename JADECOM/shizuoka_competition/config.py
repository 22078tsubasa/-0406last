from __future__ import annotations

from pathlib import Path


BASE_DATA_DIR = Path("/Users/itotsubasa/Downloads/jadecom/4:6/静岡県")
SHP_PATH = BASE_DATA_DIR / "A002005212020DDSWC22" / "r2ka22.shp"
DEMAND_CSV = BASE_DATA_DIR / "h03_22_町丁目別医療需要者数.csv"
CAR30_TOWN_CSV = Path("/Users/itotsubasa/Downloads/aj.csv")

BASE_DIR = Path(__file__).resolve().parent
OUT_ROOT = BASE_DIR / "out"

DEFAULT_PASSWORD = "shibaura2026"
TOP_FACILITY_USERS = 60
TOP_K_HEATMAP = 10
TOP_K_EXCLUDING_TARGET = 5
TOP_TOWNS_FOR_GRAPH = 60

PREFECTURES = {
    "静岡県": {
        "label": "静岡県",
        "base_data_dir": BASE_DATA_DIR,
        "shp_path": SHP_PATH,
        "demand_csv": DEMAND_CSV,
        "car30_town_csv": CAR30_TOWN_CSV,
        "facilities": [
            {
                "key": "nishiizu_arari",
                "label": "西伊豆町安良里診療所",
                "folder_name": "西伊豆町安良里診療所",
                "target_keyword": "西伊豆町安良里診療所",
                "car30_name": "西伊豆町安良里診療所",
                "ref_lat": 34.8268216,
                "ref_lon": 138.7694751,
            },
            {
                "key": "nishiizu_tago",
                "label": "西伊豆町田子診療所",
                "folder_name": "西伊豆町田子診療所",
                "target_keyword": "西伊豆町田子診療所",
                "car30_name": "西伊豆町田子診療所",
                "ref_lat": 34.8101498,
                "ref_lon": 138.7674985,
            },
            {
                "key": "inasa",
                "label": "いなずさ診療所",
                "folder_name": "いなずさ",
                "target_keyword": "いなずさ診療所",
                "car30_name": "いなずさ診療所",
                "ref_lat": 34.7228742,
                "ref_lon": 138.9306068,
            },
            {
                "key": "kamikawazu",
                "label": "上河津診療所",
                "folder_name": "上河津診療所",
                "target_keyword": "上河津診療所",
                "car30_name": "上河津診療所",
                "ref_lat": 34.7728066,
                "ref_lon": 138.9567634,
            },
            {
                "key": "heda",
                "label": "戸田診療所",
                "folder_name": "戸田診療所",
                "target_keyword": "戸田診療所",
                "car30_name": "戸田診療所",
                "ref_lat": 34.9735981,
                "ref_lon": 138.7779243,
            },
            {
                "key": "izushimoda",
                "label": "伊豆下田診療所",
                "folder_name": "伊豆下田診療所",
                "target_keyword": "伊豆下田診療所",
                "car30_name": "伊豆下田診療所",
                "ref_lat": 34.6809408,
                "ref_lon": 138.9406929,
            },
        ],
    }
}
