from __future__ import annotations

import argparse
import re
import time
from pathlib import Path

import pandas as pd
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Frame, Page, TimeoutError, sync_playwright


BASE_DIR = Path(__file__).resolve().parent
TARGETS_CSV = BASE_DIR / "kddi_batch_targets.csv"
RAW_DIR = BASE_DIR / "kddi_raw_exports"
PROFILE_DIR = BASE_DIR / ".playwright_profile"
KDDI_URL = "https://kla.kddi.ne.jp/map/"
STATUS_CSV = BASE_DIR / "kddi_auto_download_status.csv"
DEBUG_DIR = BASE_DIR / "kddi_debug"


def _all_contexts(page: Page) -> list[Page | Frame]:
    contexts: list[Page | Frame] = [page]
    for fr in page.frames:
        contexts.append(fr)
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


def _fill_date_range(page: Page, start_date: str, end_date: str) -> bool:
    for ctx in _all_contexts(page):
        try:
            date_inputs = ctx.locator("input[type='date']")
            if date_inputs.count() >= 2:
                date_inputs.nth(0).fill(start_date)
                date_inputs.nth(1).fill(end_date)
                return True
        except Exception:
            continue

    start_ok = fill_first(
        page,
        [
            "input[placeholder*='開始']",
            "input[placeholder*='from']",
            "input[name*='startDate']",
            "input[id*='start']",
        ],
        start_date,
    )
    end_ok = fill_first(
        page,
        [
            "input[placeholder*='終了']",
            "input[placeholder*='to']",
            "input[name*='endDate']",
            "input[id*='end']",
        ],
        end_date,
    )
    return start_ok and end_ok


def _safe_name(s: str) -> str:
    return re.sub(r"[^0-9A-Za-zぁ-んァ-ヶ一-龥ー_]+", "_", s).strip("_")


def capture_debug(page: Page, facility_name: str, step: str) -> None:
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    base = DEBUG_DIR / f"{ts}_{_safe_name(facility_name)}_{step}"

    try:
        page.screenshot(path=str(base.with_suffix(".png")), full_page=True)
    except Exception:
        pass

    try:
        frame_txt = []
        for i, fr in enumerate(page.frames):
            frame_txt.append(f"[{i}] name={fr.name} url={fr.url}")
        base.with_suffix(".frames.txt").write_text("\n".join(frame_txt), encoding="utf-8")
    except Exception:
        pass
    try:
        base.with_suffix(".html").write_text(page.content(), encoding="utf-8")
    except Exception:
        pass


def set_conditions(page: Page) -> bool:
    changed = False

    changed = wait_and_click_text(page, r"条件|詳細条件|設定") or changed
    time.sleep(0.8)

    changed = wait_and_click_text(page, r"月ユニーク") or changed
    time.sleep(0.3)

    changed = _fill_date_range(page, "2024-04-01", "2025-03-31") or changed
    time.sleep(0.3)

    changed = wait_and_click_text(page, r"期間全体") or changed
    time.sleep(0.2)

    changed = fill_first(
        page,
        ["input[placeholder*='開始時刻']", "input[placeholder*='from time']", "input[name*='startTime']"],
        "05:00",
    ) or changed
    changed = fill_first(
        page,
        ["input[placeholder*='終了時刻']", "input[placeholder*='to time']", "input[name*='endTime']"],
        "29:00",
    ) or changed
    time.sleep(0.2)

    changed = wait_and_click_text(page, r"1日以上") or changed
    time.sleep(0.2)

    changed = wait_and_click_text(page, r"120分以下") or changed
    time.sleep(0.2)

    changed = click_first(
        page,
        [
            "button:has-text('分析')",
            "button:has-text('集計')",
            "button:has-text('適用')",
            "button:has-text('表示')",
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
    # 候補リストUI向けフォールバック（存在する場合のみ）
    if click_first(
        page,
        [
            "[role='option']",
            "ul li",
            ".pac-item",
            ".autocomplete-suggestion",
            ".ui-menu-item",
        ],
        timeout_ms=1200,
    ):
        return True
    # キーボードで候補1件目を選択
    try:
        page.keyboard.press("ArrowDown")
        page.keyboard.press("Enter")
        return True
    except Exception:
        return False


def _open_left_tools(page: Page) -> None:
    # 画面左の導線（施設追加/設定）を先に開いておく
    click_first(
        page,
        [
            "button:has-text('施設追加')",
            "a:has-text('施設追加')",
            "div:has-text('施設追加')",
        ],
        timeout_ms=1200,
    )
    time.sleep(0.4)
    click_first(
        page,
        [
            "button:has-text('設定')",
            "a:has-text('設定')",
            "div:has-text('設定')",
            "button[title*='設定']",
            "button[aria-label*='設定']",
        ],
        timeout_ms=1200,
    )
    time.sleep(0.4)


def run_one(page: Page, facility_name: str, out_csv: Path, slow_sec: float) -> str:
    page.goto(KDDI_URL, wait_until="domcontentloaded", timeout=90000)
    time.sleep(1.2 + slow_sec)
    _open_left_tools(page)

    click_first(
        page,
        [
            "button[aria-label*='検索']",
            "button[title*='検索']",
            "button:has-text('検索')",
            "a:has-text('検索')",
        ],
        timeout_ms=1500,
    )

    ok = fill_first(
        page,
        [
            "input[placeholder*='施設名']",
            "input[placeholder*='キーワード']",
            "input[placeholder*='検索']",
            "input[aria-label*='検索']",
            "input[type='search']",
            "input[type='text']",
        ],
        facility_name,
    )
    if not ok:
        capture_debug(page, facility_name, "search_input_not_found")
        return "search_input_not_found"

    page.keyboard.press("Enter")
    time.sleep(1.6 + slow_sec)

    selected = _select_facility(page, facility_name)
    if not selected:
        _choose_first_suggestion(page)
        time.sleep(0.8 + slow_sec)
        selected = _select_facility(page, facility_name)
        if not selected:
            # 地図上ピンに遷移できていれば後続の分析メニュー操作は可能な場合がある
            capture_debug(page, facility_name, "facility_not_selected_continue")

    time.sleep(1.0 + slow_sec)

    opened = click_first(
        page,
        [
            "button:has-text('来訪者居住地分析')",
            "a:has-text('来訪者居住地分析')",
            "div:has-text('来訪者居住地分析')",
            "button:has-text('居住地分析')",
            "a:has-text('居住地分析')",
            "button:has-text('来訪者分析')",
            "a:has-text('来訪者分析')",
        ],
        timeout_ms=8000,
    ) or wait_and_click_text(page, r"来訪者居住地分析|居住地分析|来訪者")
    if not opened:
        capture_debug(page, facility_name, "analysis_menu_not_found")
        return "analysis_menu_not_found"

    time.sleep(1.0 + slow_sec)
    set_ok = set_conditions(page)
    time.sleep(1.5 + slow_sec)
    if not set_ok:
        capture_debug(page, facility_name, "conditions_may_not_applied")

    try:
        with page.expect_download(timeout=40000) as dl_info:
            clicked = click_first(
                page,
                [
                    "button:has-text('CSV')",
                    "a:has-text('CSV')",
                    "button:has-text('ダウンロード')",
                    "a:has-text('ダウンロード')",
                ],
                timeout_ms=12000,
            )
            if not clicked:
                capture_debug(page, facility_name, "download_button_not_found")
                return "download_button_not_found"

        download = dl_info.value
        download.save_as(str(out_csv))
    except TimeoutError:
        capture_debug(page, facility_name, "download_timeout")
        return "download_timeout"
    except Exception:
        capture_debug(page, facility_name, "download_error")
        return "download_error"

    return "ok"


def cleanup_profile_singleton_locks(profile_dir: Path) -> None:
    # Chromiumの異常終了で残るロックファイルを除去
    for name in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
        p = profile_dir / name
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass


def main() -> None:
    parser = argparse.ArgumentParser(description="KDDI来訪者居住地分析の自動CSV取得")
    parser.add_argument("--limit", type=int, default=0, help="先頭N件だけ実行。0は全件")
    parser.add_argument("--slow-sec", type=float, default=0.6, help="各操作後の待機秒を増やす")
    parser.add_argument("--headless", action="store_true", help="ヘッドレス実行")
    parser.add_argument("--skip-existing", action="store_true", help="CSVが既にある施設はスキップ")
    args = parser.parse_args()

    if not TARGETS_CSV.exists():
        raise FileNotFoundError(f"targets not found: {TARGETS_CSV}")
    if not PROFILE_DIR.exists():
        raise FileNotFoundError(
            f"login profile not found: {PROFILE_DIR}. 先に kddi_login_once.py を実行してください。"
        )

    targets = pd.read_csv(TARGETS_CSV)
    if args.limit > 0:
        targets = targets.head(args.limit).copy()

    logs: list[dict] = []
    with sync_playwright() as p:
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(PROFILE_DIR),
                headless=args.headless,
                viewport={"width": 1440, "height": 900},
                accept_downloads=True,
            )
        except PlaywrightError as e:
            msg = str(e)
            if "ProcessSingleton" in msg or "SingletonLock" in msg:
                cleanup_profile_singleton_locks(PROFILE_DIR)
                time.sleep(0.5)
                context = p.chromium.launch_persistent_context(
                    user_data_dir=str(PROFILE_DIR),
                    headless=args.headless,
                    viewport={"width": 1440, "height": 900},
                    accept_downloads=True,
                )
            else:
                raise
        page = context.new_page()

        for _, r in targets.iterrows():
            facility = str(r["facility_name"])
            out_folder = Path(str(r["output_folder"]))
            out_folder.mkdir(parents=True, exist_ok=True)
            out_csv = out_folder / "kddi_export.csv"

            if args.skip_existing and out_csv.exists():
                status = "skipped_existing"
            else:
                status = run_one(page, facility, out_csv, args.slow_sec)

            logs.append(
                {
                    "facility_id": r.get("facility_id", ""),
                    "facility_name": facility,
                    "output_csv": str(out_csv),
                    "status": status,
                }
            )
            print(f"{facility} -> {status}")

        context.close()

    pd.DataFrame(logs).to_csv(STATUS_CSV, index=False, encoding="utf-8-sig")
    print(f"saved status: {STATUS_CSV}")


if __name__ == "__main__":
    main()
