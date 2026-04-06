# 都祁診療所競合分析 - 公開手順

## 1. 事前準備
- このフォルダ配下に以下があることを確認
  - `streamlit_report.py`
  - `dominant_territory_tsuge_30km.png`
  - `dominant_territory_tsuge_30km_tsuge_plus5.png`
  - `town_med_matrix_top3.png`
  - `town_med_heatmap_top10.png`
  - 各CSVファイル
- ルートの `requirements.txt` に `streamlit` と `pandas` を追加済み

## 2. GitHub に push
1. このプロジェクトを GitHub リポジトリに push
2. `JADECOM/202603/streamlit_report.py` が repo 上にある状態にする

## 3. Streamlit Community Cloud で公開
1. https://share.streamlit.io/ に GitHub アカウントでログイン
2. `New app` を押す
3. 設定
   - Repository: このプロジェクトのリポジトリ
   - Branch: `main`（使っているブランチ）
   - Main file path: `JADECOM/202603/streamlit_report.py`
4. `Deploy` を押す

### パスワード保護を有効化する
1. デプロイ後、アプリ画面右上の `⋯` から `Settings` を開く
2. `Secrets` に以下を設定して保存

```toml
APP_PASSWORD = "ここに任意のパスワード"
```

3. 再起動後、アプリ閲覧時にパスワード入力が必要になる

※ ローカル起動時は環境変数でも可:
```bash
export APP_PASSWORD='ここに任意のパスワード'
streamlit run JADECOM/202603/streamlit_report.py
```

## 4. 先方共有
- デプロイ後に発行される `https://xxxx.streamlit.app` を先方へ送る
- このURLは `localhost` と違って、先方PCからも見られる

## 5. 更新時
- 画像やCSV、`streamlit_report.py` を更新して GitHub に push
- 同じ URL で自動反映（反映に少し時間がかかることあり）

## 補足
- Streamlit Cloud がスリープしても、アクセス時に自動で再起動される
- 完全に常時稼働が必要なら、Render / Railway / VPS などの常時ホスティングも選択可
