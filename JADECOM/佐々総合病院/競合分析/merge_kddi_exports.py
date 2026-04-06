from __future__ import annotations

from pathlib import Path
import pandas as pd

BASE_DIR = Path('/Users/itotsubasa/IdeaProjects/pythoN/JADECOM/佐々総合病院/競合分析')
RAW_DIR = BASE_DIR / 'kddi_raw_exports'
TARGETS = BASE_DIR / 'kddi_batch_targets.csv'
OUT_MERGED = BASE_DIR / 'kddi_来訪者居住地分析_全施設統合.csv'
OUT_LOG = BASE_DIR / 'kddi_取得状況ログ.csv'


def read_csv_any(path: Path) -> pd.DataFrame:
    for enc in ['utf-8-sig', 'cp932', 'shift_jis', 'utf-8']:
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            continue
    raise ValueError(f'CSV read failed: {path}')


def main() -> None:
    targets = pd.read_csv(TARGETS)
    merged = []
    logs = []

    for _, r in targets.iterrows():
        folder = Path(r['output_folder'])
        csvs = sorted(folder.glob('*.csv'))

        if not csvs:
            logs.append({
                'facility_id': r['facility_id'],
                'facility_name': r['facility_name'],
                'status': 'missing_csv',
                'csv_file': '',
                'rows': 0,
            })
            continue

        for c in csvs:
            try:
                df = read_csv_any(c)
                df['facility_id'] = r['facility_id']
                df['facility_name'] = r['facility_name']
                df['prefecture'] = r['prefecture']
                df['city'] = r['city']
                df['source_csv'] = str(c)
                merged.append(df)
                logs.append({
                    'facility_id': r['facility_id'],
                    'facility_name': r['facility_name'],
                    'status': 'ok',
                    'csv_file': str(c),
                    'rows': len(df),
                })
            except Exception as e:
                logs.append({
                    'facility_id': r['facility_id'],
                    'facility_name': r['facility_name'],
                    'status': f'error:{type(e).__name__}',
                    'csv_file': str(c),
                    'rows': 0,
                })

    log_df = pd.DataFrame(logs)
    log_df.to_csv(OUT_LOG, index=False, encoding='utf-8-sig')

    if merged:
        out = pd.concat(merged, ignore_index=True)
        out.to_csv(OUT_MERGED, index=False, encoding='utf-8-sig')
        print('merged rows:', len(out))
        print('saved:', OUT_MERGED)
    else:
        print('no csv merged')

    print('saved log:', OUT_LOG)


if __name__ == '__main__':
    main()
