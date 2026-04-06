from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

INPUT_FACILITY_CSV = Path('/Users/itotsubasa/Downloads/jadecom/東京佐々総合病院/東京車20分/tokyo_sasa_car20_病院診療所のみ一覧_dedup.csv')
BASE_DIR = Path('/Users/itotsubasa/IdeaProjects/pythoN/JADECOM/佐々総合病院/競合分析')
RAW_DIR = BASE_DIR / 'kddi_raw_exports'


def safe_name(text: str) -> str:
    t = re.sub(r"[\\/:*?\"<>|\s]+", '_', str(text))
    t = re.sub(r'_+', '_', t).strip('_')
    return t[:80]


def main() -> None:
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(INPUT_FACILITY_CSV)
    if '医療機関番号' in df.columns:
        df = df.drop_duplicates(subset=['医療機関番号']).copy()
    else:
        df = df.drop_duplicates(subset=['医療機関名', '所在地']).copy()

    rows = []
    for i, r in df.reset_index(drop=True).iterrows():
        facility_id = str(r.get('医療機関番号', f'noid_{i+1}'))
        facility_name = str(r.get('医療機関名', ''))
        pref = str(r.get('都道府県名', ''))
        city = str(r.get('市区町村名', ''))

        folder_name = f"{i+1:03d}_{safe_name(facility_name)}"
        folder_path = RAW_DIR / folder_name
        folder_path.mkdir(parents=True, exist_ok=True)

        instruction = folder_path / 'README_手動取得条件.txt'
        instruction.write_text(
            "\n".join([
                f"施設名: {facility_name}",
                f"都道府県/市区町村: {pref} {city}",
                "",
                "KDDIアナライザ設定:",
                "- 分析メニュー: 来訪者居住地分析",
                "- 集計: 月ユニーク",
                "- 期間: 2024-04-01 ~ 2025-03-31",
                "- 日にち区分: 期間全体",
                "- 時間帯: 05:00 ~ 29:00",
                "- 来訪日数: 1日以上",
                "- 滞在時間: 120分以下",
                "",
                "このフォルダにCSVを保存してください。",
            ]),
            encoding='utf-8'
        )

        rows.append({
            'seq': i + 1,
            'facility_id': facility_id,
            'facility_name': facility_name,
            'prefecture': pref,
            'city': city,
            'output_folder': str(folder_path),
            'status': 'pending',
            'kddi_query_name': facility_name,
            'conditions': '来訪者居住地分析|月ユニーク|2024-04-01~2025-03-31|期間全体|05:00-29:00|1日以上|120分以下',
        })

    target_csv = BASE_DIR / 'kddi_batch_targets.csv'
    pd.DataFrame(rows).to_csv(target_csv, index=False, encoding='utf-8-sig')

    manual_guide = BASE_DIR / 'KDDI手動取得手順.md'
    manual_guide.write_text(
        "\n".join([
            '# KDDIアナライザ 手動取得手順',
            '',
            '1. `kddi_batch_targets.csv` の `facility_name` を順に検索',
            '2. 分析メニューで `来訪者居住地分析` を選択',
            '3. 条件を以下で統一',
            '   - 月ユニーク',
            '   - 2024-04-01 ~ 2025-03-31',
            '   - 日にち区分: 期間全体',
            '   - 時間帯: 05:00 ~ 29:00',
            '   - 来訪日数: 1日以上',
            '   - 滞在時間: 120分以下',
            '4. CSV出力後、該当施設フォルダへ保存',
            '5. 全施設完了後、`merge_kddi_exports.py` を実行',
        ]),
        encoding='utf-8'
    )

    print('created:', target_csv)
    print('facilities:', len(rows))
    print('raw folder:', RAW_DIR)


if __name__ == '__main__':
    main()
