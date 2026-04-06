from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import requests
from playwright.sync_api import sync_playwright


BASE_DIR = Path(__file__).resolve().parent
PROFILE_DIR = BASE_DIR / ".playwright_profile"
MAP_URL = "https://kla.kddi.ne.jp/map/"
GROUP_TREE_API = "https://kla.kddi.ne.jp/api/place/store/group/tree"
PLACE_FETCH_API = "https://kla.kddi.ne.jp/api/place/store/fetch"


def build_session_from_context(storage_state: dict) -> requests.Session:
    session = requests.Session()
    session.headers.update({"Referer": MAP_URL})
    for c in storage_state.get("cookies", []):
        session.cookies.set(c["name"], c["value"], domain=c.get("domain"), path=c.get("path"))
    return session


def main() -> None:
    parser = argparse.ArgumentParser(description="KDDI分析値リストグループ配下の施設一覧を取得")
    parser.add_argument("--group-name", required=True)
    parser.add_argument("--output", required=True, help="CSV or JSON output path")
    args = parser.parse_args()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not PROFILE_DIR.exists():
        raise FileNotFoundError(f"profile not found: {PROFILE_DIR}. 先に kddi_login_once.py を実行してください。")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=True,
            viewport={"width": 1440, "height": 900},
        )
        storage_state = context.storage_state()
        context.close()

    session = build_session_from_context(storage_state)
    tree = session.get(GROUP_TREE_API, timeout=60).json()
    all_places_raw = session.get(PLACE_FETCH_API, timeout=60).json()
    all_places = all_places_raw.get("items", all_places_raw) if isinstance(all_places_raw, dict) else all_places_raw

    target_group = next((g for g in tree if g.get("name") == args.group_name), None)
    if not target_group:
        raise RuntimeError(f"group not found: {args.group_name}")

    id_to_place = {str(p["id"]): p for p in all_places}
    rows: list[dict] = []
    store_ids = target_group.get("store_ids", target_group.get("stores", []))
    for pid in store_ids:
        place = id_to_place.get(str(pid))
        if not place:
            continue
        rows.append(
            {
                "group_name": args.group_name,
                "place_id": str(place.get("id", "")),
                "place_name": str(place.get("name", "")),
                "address": str(place.get("address", "")),
                "prefecture": str(place.get("pref", "")),
                "city": str(place.get("city", "")),
            }
        )

    if out_path.suffix.lower() == ".json":
        out_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        pd.DataFrame(rows).to_csv(out_path, index=False, encoding="utf-8-sig")

    print(f"group: {args.group_name}")
    print(f"places: {len(rows)}")
    print(f"saved: {out_path}")


if __name__ == "__main__":
    main()
