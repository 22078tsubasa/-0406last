from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
import zipfile
from io import BytesIO
from pathlib import Path

import pandas as pd
import requests
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Frame, Page, TimeoutError, sync_playwright


BASE_DIR = Path(__file__).resolve().parent
PROFILE_DIR = Path(os.environ.get("KDDI_PROFILE_DIR", str(BASE_DIR / ".playwright_profile")))
KDDI_URL = "https://kla.kddi.ne.jp/map/"
LOGIN_URL = "https://kla.kddi.ne.jp/account/login/?next=/map/"


def _all_contexts(page: Page) -> list[Page | Frame]:
    contexts: list[Page | Frame] = [page]
    contexts.extend(page.frames)
    return contexts


def click_first(page: Page, locators: list[str], timeout_ms: int = 4000) -> bool:
    for ctx in _all_contexts(page):
        for sel in locators:
            try:
                loc = ctx.locator(sel).first
                if loc.count() > 0:
                    loc.click(timeout=timeout_ms)
                    return True
            except Exception:
                continue
    return False


def fill_first(page: Page, locators: list[str], value: str, timeout_ms: int = 4000) -> bool:
    for ctx in _all_contexts(page):
        for sel in locators:
            try:
                loc = ctx.locator(sel).first
                if loc.count() > 0:
                    loc.click(timeout=timeout_ms)
                    loc.fill("")
                    loc.fill(value, timeout=timeout_ms)
                    return True
            except Exception:
                continue
    return False


def wait_and_click_text(page: Page, text_pattern: str, timeout_ms: int = 8000) -> bool:
    for ctx in _all_contexts(page):
        try:
            ctx.get_by_text(re.compile(text_pattern), exact=False).first.click(timeout=timeout_ms)
            return True
        except Exception:
            continue
    return False


def _wait_for_ready(page: Page, timeout_ms: int = 20000) -> None:
    try:
        page.wait_for_load_state("networkidle", timeout=timeout_ms)
    except Exception:
        pass


def _dismiss_trial_modal(page: Page) -> bool:
    clicked = wait_and_click_text(page, r"利用を開始|閉じる|OK", timeout_ms=5000)
    if clicked:
        time.sleep(1.0)
    return clicked


def _login_with_env(page: Page) -> bool:
    org = os.environ.get("KDDI_ORGANIZATION", "").strip()
    identifier = os.environ.get("KDDI_IDENTIFIER", "").strip()
    password = os.environ.get("KDDI_PASSWORD", "").strip()
    if not (org and identifier and password):
        return False
    page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=90000)
    try:
        page.locator("input[name='organization']").fill(org)
        page.locator("input[name='identifier']").fill(identifier)
        page.locator("input[name='password']").fill(password)
        page.locator("button[type='submit'], input[type='submit']").first.click(timeout=5000)
        page.wait_for_timeout(5000)
        return "/map/" in page.url and "ログイン" not in page.title()
    except Exception:
        return False


def _open_places_drawer(page: Page) -> bool:
    for _ in range(3):
        for sel in [
            ".mcpToggler .nav-link",
            ".mcpToggler button",
            "button:has-text('施設追加')",
            "a:has-text('施設追加')",
            ".btn-info",
        ]:
            try:
                loc = page.locator(sel).first
                if loc.count() > 0:
                    loc.click(timeout=3000, force=True)
                    time.sleep(0.8)
            except Exception:
                continue
        try:
            drawer = page.locator(".placesDrawer")
            if drawer.count() > 0 and drawer.first.is_visible():
                return True
        except Exception:
            pass
    return False


def _filter_places_drawer(page: Page, facility_name: str) -> bool:
    selectors = [
        ".placesDrawer input[placeholder*='フリーワード']",
        ".placesDrawer input[type='text']",
    ]
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if loc.count() == 0 or not loc.is_visible():
                continue
            loc.click(timeout=3000)
            loc.fill("")
            loc.fill(facility_name, timeout=5000)
            time.sleep(1.0)
            return True
        except Exception:
            continue
    return False


def _select_facility_in_drawer(page: Page, facility_name: str) -> bool:
    patterns = [
        rf"^\s*{re.escape(facility_name)}\s*$",
        re.escape(facility_name),
    ]
    for pattern in patterns:
        for sel in [
            f".placesDrawer .list-group-item:has-text('{facility_name}')",
            ".placesDrawer .list-group-item",
        ]:
            try:
                if ":has-text(" in sel:
                    loc = page.locator(sel).first
                else:
                    loc = page.locator(sel).filter(has_text=re.compile(pattern)).first
                if loc.count() > 0 and loc.is_visible():
                    loc.click(timeout=5000)
                    time.sleep(1.0)
                    return True
            except Exception:
                continue
    return False


def _open_analysis_from_selected_place(page: Page) -> bool:
    locators = [
        "button:has-text('来訪者居住地分析')",
        "a:has-text('来訪者居住地分析')",
        "button:has-text('居住地分析')",
        "a:has-text('居住地分析')",
        ".infoWindow button",
        ".infoWindow a",
    ]
    opened = click_first(page, locators, timeout_ms=8000) or wait_and_click_text(page, r"来訪者居住地分析|居住地分析", timeout_ms=8000)
    if opened:
        time.sleep(1.2)
    return opened


def _fill_date_range(page: Page, start_date: str, end_date: str) -> bool:
    for ctx in _all_contexts(page):
        try:
            datepicker_inputs = ctx.locator("input.datepicker-input")
            if datepicker_inputs.count() >= 2:
                for idx, value in enumerate([start_date, end_date]):
                    inp = datepicker_inputs.nth(idx)
                    inp.click()
                    inp.press("Meta+a")
                    inp.type(value, delay=30)
                    ctx.page.keyboard.press("Tab")
                    time.sleep(0.3)
                return True
        except Exception:
            continue
    for ctx in _all_contexts(page):
        try:
            date_inputs = ctx.locator("input[type='date']")
            if date_inputs.count() >= 2:
                for idx, value in enumerate([start_date, end_date]):
                    inp = date_inputs.nth(idx)
                    inp.click()
                    inp.press("Meta+a")
                    inp.type(value, delay=30)
                    ctx.page.keyboard.press("Tab")
                    time.sleep(0.3)
                return True
        except Exception:
            continue
    return False


def _safe_name(s: str) -> str:
    return re.sub(r"[^0-9A-Za-zぁ-んァ-ヶ一-龥ー_]+", "_", s).strip("_")


def capture_debug(page: Page, debug_dir: Path, facility_name: str, step: str) -> None:
    debug_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    base = debug_dir / f"{ts}_{_safe_name(facility_name)}_{step}"
    try:
        page.screenshot(path=str(base.with_suffix(".png")), full_page=True)
    except Exception:
        pass
    try:
        base.with_suffix(".html").write_text(page.content(), encoding="utf-8")
    except Exception:
        pass


def set_conditions(
    page: Page,
    start_date: str,
    end_date: str,
    time_start: str,
    time_end: str,
    stay_end: str,
    use_monthly_unique: bool,
) -> bool:
    changed = False
    changed = wait_and_click_text(page, r"条件|詳細条件|設定") or changed
    time.sleep(0.8)

    if use_monthly_unique:
        changed = wait_and_click_text(page, r"全人口推計\(月ユニーク\)|月ユニーク") or changed
        time.sleep(0.3)

    changed = _fill_date_range(page, start_date, end_date) or changed
    time.sleep(0.3)
    changed = wait_and_click_text(page, r"期間全体") or changed
    time.sleep(0.2)

    for ctx in _all_contexts(page):
        try:
            selects = ctx.locator("select.form-select.form-select-sm")
            if selects.count() >= 6:
                selects.nth(0).select_option(time_start)
                selects.nth(1).select_option(time_end)
                selects.nth(2).select_option("1")
                try:
                    selects.nth(3).select_option("")
                except Exception:
                    pass
                try:
                    selects.nth(4).select_option("")
                except Exception:
                    pass
                selects.nth(5).select_option(stay_end)
                changed = True
                break
        except Exception:
            continue
    time.sleep(0.4)

    changed = click_first(
        page,
        [
            "button:has-text('分析')",
            "button:has-text('集計')",
            "button:has-text('適用')",
            "button:has-text('表示')",
            "button:has-text('上記の条件で集計を再実行')",
        ],
        timeout_ms=6000,
    ) or changed
    return changed


def _select_facility(page: Page, facility_name: str) -> bool:
    for ctx in _all_contexts(page):
        try:
            ctx.get_by_text(re.compile(rf"^\s*{re.escape(facility_name)}\s*$")).first.click(timeout=5000)
            return True
        except Exception:
            continue
    for ctx in _all_contexts(page):
        try:
            ctx.get_by_text(re.compile(re.escape(facility_name))).first.click(timeout=5000)
            return True
        except Exception:
            continue
    return False


def _choose_first_suggestion(page: Page) -> bool:
    if click_first(page, ["[role='option']", "ul li", ".autocomplete-suggestion"], timeout_ms=1200):
        return True
    try:
        page.keyboard.press("ArrowDown")
        page.keyboard.press("Enter")
        return True
    except Exception:
        return False


def extract_zip_to_facility_folder(zip_bytes: bytes, facility_dir: Path, town_only: bool) -> list[str]:
    facility_dir.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []
    zf = zipfile.ZipFile(BytesIO(zip_bytes))
    for member in zf.infolist():
        if member.is_dir() or not member.filename.lower().endswith(".csv"):
            continue
        base = Path(member.filename).name
        if town_only and "_3_Towns_" not in base:
            continue
        out = facility_dir / base
        with zf.open(member) as src, open(out, "wb") as dst:
            shutil.copyfileobj(src, dst)
        saved.append(str(out))
    return saved


def _build_requests_session_from_page(page: Page, referer: str) -> requests.Session:
    session = requests.Session()
    session.headers.update({"Referer": referer, "User-Agent": page.evaluate("() => navigator.userAgent")})
    for c in page.context.cookies():
        session.cookies.set(c["name"], c["value"], domain=c.get("domain"), path=c.get("path"))
    return session


def cleanup_profile_singleton_locks(profile_dir: Path) -> None:
    for name in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
        p = profile_dir / name
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass


def run_one(
    page: Page,
    place_id: str,
    facility_name: str,
    output_dir: Path,
    debug_dir: Path,
    slow_sec: float,
    start_date: str,
    end_date: str,
    time_start: str,
    time_end: str,
    stay_end: str,
    use_monthly_unique: bool,
    town_only: bool,
) -> dict:
    print(f"[start] {facility_name}", flush=True)
    if place_id:
        print(f"[nav] {facility_name} -> target page", flush=True)
        page.goto(f"https://kla.kddi.ne.jp/app/target/r/{place_id}/", wait_until="domcontentloaded", timeout=90000)
        _wait_for_ready(page, timeout_ms=15000)
        time.sleep(2.0 + slow_sec)

    if "メイン" in page.title() or page.locator("button:has-text('利用を開始')").count() > 0:
        print(f"[modal] {facility_name}", flush=True)
        _dismiss_trial_modal(page)
        _wait_for_ready(page, timeout_ms=15000)

    if "ログイン" in page.title():
        print(f"[login] {facility_name}", flush=True)
        _login_with_env(page)
        if place_id:
            page.goto(f"https://kla.kddi.ne.jp/app/target/r/{place_id}/", wait_until="domcontentloaded", timeout=90000)
            _wait_for_ready(page, timeout_ms=15000)
            time.sleep(2.0 + slow_sec)
        if "ログイン" in page.title():
            capture_debug(page, debug_dir, facility_name, "login_required")
            return {"status": "login_required", "saved_files": []}

    if "来訪者居住地分析" not in page.title():
        print(f"[fallback] {facility_name}", flush=True)
        page.goto(KDDI_URL, wait_until="domcontentloaded", timeout=90000)
        time.sleep(1.2 + slow_sec)
        _dismiss_trial_modal(page)
        _wait_for_ready(page, timeout_ms=15000)

        opened_drawer = _open_places_drawer(page)
        if not opened_drawer:
            capture_debug(page, debug_dir, facility_name, "places_drawer_not_found")
            return {"status": "places_drawer_not_found", "saved_files": []}

        filtered = _filter_places_drawer(page, facility_name)
        if not filtered:
            capture_debug(page, debug_dir, facility_name, "drawer_filter_not_found")
            return {"status": "drawer_filter_not_found", "saved_files": []}

        selected = _select_facility_in_drawer(page, facility_name)
        if not selected:
            capture_debug(page, debug_dir, facility_name, "facility_not_selected")
            return {"status": "facility_not_selected", "saved_files": []}

        opened = _open_analysis_from_selected_place(page)
        if not opened:
            capture_debug(page, debug_dir, facility_name, "analysis_menu_not_found")
            return {"status": "analysis_menu_not_found", "saved_files": []}

    time.sleep(1.0 + slow_sec)
    print(f"[conditions] {facility_name}", flush=True)
    set_conditions(page, start_date, end_date, time_start, time_end, stay_end, use_monthly_unique)
    time.sleep(1.5 + slow_sec)

    try:
        print(f"[download-wait] {facility_name}", flush=True)
        button = None
        for _ in range(60):
            for sel in [
                "button:has-text('CSV')",
                "a:has-text('CSV')",
                "button:has-text('ダウンロード')",
                "a:has-text('ダウンロード')",
            ]:
                loc = page.locator(sel).first
                if loc.count() > 0:
                    button = loc
                    break
            if button and button.count() > 0:
                try:
                    if button.is_enabled() and button.get_attribute("disabled") is None:
                        break
                except Exception:
                    pass
            time.sleep(2)
        if not button or button.count() == 0:
            capture_debug(page, debug_dir, facility_name, "download_button_not_found")
            return {"status": "download_button_not_found", "saved_files": []}
        if place_id:
            referer = f"https://kla.kddi.ne.jp/app/target/r/{place_id}/"
            session = _build_requests_session_from_page(page, referer)
            print(f"[csv-fetch] {facility_name}", flush=True)
            resp = session.get(f"https://kla.kddi.ne.jp/csv/target/r/{place_id}/", timeout=120)
            if resp.status_code != 200 or ("zip" not in resp.headers.get("content-type", "") and not resp.content.startswith(b"PK")):
                capture_debug(page, debug_dir, facility_name, "csv_fetch_failed")
                return {"status": "csv_fetch_failed", "saved_files": []}
            tmp_path = output_dir / "kddi_export.zip"
            tmp_path.write_bytes(resp.content)
            saved_files = extract_zip_to_facility_folder(resp.content, output_dir, town_only)
            return {"status": "ok", "saved_files": saved_files}
        with page.expect_download(timeout=40000) as dl_info:
            button.click(timeout=12000)
        download = dl_info.value
        tmp_path = output_dir / "kddi_export.zip"
        download.save_as(str(tmp_path))
        saved_files = extract_zip_to_facility_folder(tmp_path.read_bytes(), output_dir, town_only)
        return {"status": "ok", "saved_files": saved_files}
    except TimeoutError:
        capture_debug(page, debug_dir, facility_name, "download_timeout")
        return {"status": "download_timeout", "saved_files": []}
    except Exception:
        capture_debug(page, debug_dir, facility_name, "download_error")
        return {"status": "download_error", "saved_files": []}


def main() -> None:
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass
    parser = argparse.ArgumentParser(description="KDDI来訪者居住地分析ZIPを施設別に取得")
    parser.add_argument("--targets-csv", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--slow-sec", type=float, default=0.6)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--town-only", action="store_true")
    parser.add_argument("--start-date", default="2024-04-01")
    parser.add_argument("--end-date", default="2025-03-31")
    parser.add_argument("--time-start", default="05:00")
    parser.add_argument("--time-end", default="29:00")
    parser.add_argument("--stay-end", default="120")
    parser.add_argument("--daily-unique", action="store_true")
    args = parser.parse_args()

    targets_csv = Path(args.targets_csv)
    output_root = Path(args.output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    debug_dir = output_root / "_debug"
    status_csv = output_root / "kddi_download_status.csv"
    summary_json = output_root / "_summary.json"

    if not targets_csv.exists():
        raise FileNotFoundError(f"targets not found: {targets_csv}")
    if not PROFILE_DIR.exists():
        if os.environ.get("KDDI_ORGANIZATION") and os.environ.get("KDDI_IDENTIFIER") and os.environ.get("KDDI_PASSWORD"):
            PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        else:
            raise FileNotFoundError(f"profile not found: {PROFILE_DIR}. 先に kddi_login_once.py を実行してください。")

    targets = pd.read_csv(targets_csv, dtype=str).fillna("")
    if args.limit > 0:
        targets = targets.head(args.limit).copy()

    logs: list[dict] = []
    summaries: list[dict] = []

    with sync_playwright() as p:
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(PROFILE_DIR),
                headless=args.headless,
                viewport={"width": 1440, "height": 900},
                accept_downloads=True,
            )
        except PlaywrightError as e:
            if "ProcessSingleton" in str(e) or "SingletonLock" in str(e):
                cleanup_profile_singleton_locks(PROFILE_DIR)
                context = p.chromium.launch_persistent_context(
                    user_data_dir=str(PROFILE_DIR),
                    headless=args.headless,
                    viewport={"width": 1440, "height": 900},
                    accept_downloads=True,
                )
            else:
                raise
        page = context.new_page()
        _login_with_env(page)

        for _, r in targets.iterrows():
            facility = str(r["facility_name"])
            place_id = str(r.get("place_id", "")).strip()
            folder = output_root / Path(str(r["output_folder"])).name
            folder.mkdir(parents=True, exist_ok=True)
            existing_csvs = list(folder.glob("*.csv"))

            if args.skip_existing and existing_csvs:
                result = {"status": "skipped_existing", "saved_files": [str(p) for p in existing_csvs]}
            else:
                result = run_one(
                    page=page,
                    place_id=place_id,
                    facility_name=facility,
                    output_dir=folder,
                    debug_dir=debug_dir,
                    slow_sec=args.slow_sec,
                    start_date=args.start_date,
                    end_date=args.end_date,
                    time_start=args.time_start,
                    time_end=args.time_end,
                    stay_end=args.stay_end,
                    use_monthly_unique=not args.daily_unique,
                    town_only=args.town_only,
                )

            logs.append(
                {
                    "facility_id": r.get("facility_id", ""),
                    "facility_name": facility,
                    "output_folder": str(folder),
                    "status": result["status"],
                    "saved_file_count": len(result["saved_files"]),
                }
            )
            summaries.append(
                {
                    "id": r.get("facility_id", ""),
                    "name": facility,
                    "ok": result["status"] in {"ok", "skipped_existing"},
                    "status": result["status"],
                    "saved_files": result["saved_files"],
                }
            )
            print(f"{facility} -> {result['status']}")

        context.close()

    pd.DataFrame(logs).to_csv(status_csv, index=False, encoding="utf-8-sig")
    summary_json.write_text(json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved: {status_csv}")
    print(f"saved: {summary_json}")


if __name__ == "__main__":
    main()
