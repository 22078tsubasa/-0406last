# KDDI Downloader

KDDIアナライザの来訪者居住地分析CSVを、後から対象施設と保存先を差し替えて取得するための汎用ツールです。

認証情報はコードに埋めず、ログイン済みブラウザプロファイルを使います。

## 構成

- `kddi_login_once.py`
  ログイン済みセッションを Playwright プロファイルに保存
- `kddi_list_group_places.py`
  分析値リストグループ配下の施設一覧を取得
- `build_kddi_targets.py`
  取得対象施設CSVを作成
- `kddi_download_residence_exports.py`
  来訪者居住地分析ZIPをダウンロードし、CSVを施設別フォルダへ展開

## 前提

- Playwright が使えること
- 初回のみ `playwright install chromium` が必要な環境あり

## 1. ログイン状態を保存

```bash
cd /Users/itotsubasa/IdeaProjects/pythoN
python3 JADECOM/kddi_tools/kddi_login_once.py
```

ブラウザが開くので、KDDIアナライザへログインして Enter を押します。

## 2. グループ配下の施設一覧を取得

```bash
python3 JADECOM/kddi_tools/kddi_list_group_places.py \
  --group-name "いなずさ診療所_競合" \
  --output /tmp/kddi_group_places.csv
```

## 3. ダウンロード対象CSVを作成

```bash
python3 JADECOM/kddi_tools/build_kddi_targets.py \
  --places-csv /tmp/kddi_group_places.csv \
  --output-dir /tmp/kddi_exports \
  --target-names "佐倉医院" "公益社団法人地域医療振興協会　いなずさ診療所"
```

全件対象なら `--target-names` を省略します。

## 4. 来訪者居住地分析を自動取得

```bash
python3 JADECOM/kddi_tools/kddi_download_residence_exports.py \
  --targets-csv /tmp/kddi_exports/kddi_batch_targets.csv \
  --output-dir /tmp/kddi_exports \
  --headless \
  --skip-existing
```

`--town-only` を付けると `3_Towns` だけ保存します。

## 出力

- `kddi_batch_targets.csv`
- `_summary.json`
- `*_status.csv`
- 施設別フォルダ配下のCSV

## 補足

- 施設指定や保存先は後から差し替える前提です
- KDDI画面が変わるとセレクタ調整が必要です
