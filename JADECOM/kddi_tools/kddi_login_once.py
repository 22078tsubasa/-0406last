from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright


BASE_DIR = Path(__file__).resolve().parent
PROFILE_DIR = BASE_DIR / ".playwright_profile"
KDDI_URL = "https://kla.kddi.ne.jp/map/"


def main() -> None:
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            viewport={"width": 1440, "height": 900},
            accept_downloads=True,
        )
        page = context.new_page()
        page.goto(KDDI_URL, wait_until="domcontentloaded")
        print("ブラウザでKDDIアナライザにログインしてください。")
        input("ログイン完了後、Enterを押してください > ")
        context.close()
    print(f"saved profile: {PROFILE_DIR}")


if __name__ == "__main__":
    main()
