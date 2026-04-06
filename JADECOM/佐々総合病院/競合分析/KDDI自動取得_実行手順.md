# KDDI来訪者居住地分析 自動取得（佐々総合病院 競合分析）

## 1) 初回ログイン状態の保存
```bash
cd /Users/itotsubasa/IdeaProjects/pythoN
./.venv/bin/python JADECOM/佐々総合病院/競合分析/kddi_login_once.py
```
- 開いたブラウザで `https://kla.kddi.ne.jp/map/` にログイン
- ターミナルで Enter を押して終了

## 2) 85施設の自動取得
```bash
cd /Users/itotsubasa/IdeaProjects/pythoN
./.venv/bin/python JADECOM/佐々総合病院/競合分析/kddi_auto_download.py --skip-existing
```

### テスト実行（先頭3件だけ）
```bash
./.venv/bin/python JADECOM/佐々総合病院/競合分析/kddi_auto_download.py --limit 3
```

## 3) 取得結果の統合
```bash
./.venv/bin/python JADECOM/佐々総合病院/競合分析/merge_kddi_exports.py
```

## 出力
- 取得ステータス: `kddi_auto_download_status.csv`
- 統合CSV: `kddi_来訪者居住地分析_全施設統合.csv`
- 取得ログ: `kddi_取得状況ログ.csv`

## 備考
- サイトUIが変わるとクリックセレクタの調整が必要
- 必要時は `kddi_auto_download.py` 内の `click_first / fill_first` 候補を追加
